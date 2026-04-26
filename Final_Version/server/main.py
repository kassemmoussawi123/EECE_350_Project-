"""Server entry point for Πthon Arena."""

from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.game_state import Match
from server.handlers import handle_message
from server.lobby import default_profile, new_invite, serialize_users
from server.protocol import ClientSession
from server.utils import build_logger, other_player, trim_messages
from shared.constants import APP_NAME, MAX_LOBBY_MESSAGES, TICK_RATE
from shared.helpers import clamp_target_score
import math


class ArenaServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 5050) -> None:
        self.host = host
        self.port = port
        self.logger = build_logger()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lock = threading.RLock()
        self.sessions: dict[str, ClientSession] = {}
        self.profiles: dict[str, dict] = {}
        self.invites: dict[str, list] = {}
        self.active_matches: dict[str, Match] = {}
        self.spectator_lookup: dict[str, str] = {}
        self.private_chat_peers: dict[str, set[str]] = {}
        self.lobby_messages: list[str] = []

    def start(self) -> None:
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.logger.info("%s listening on %s:%s", APP_NAME, self.host, self.port)
        threading.Thread(target=self.match_loop, daemon=True).start()
        while True:
            client_socket, address = self.server_socket.accept()
            client_socket.settimeout(0.1)
            session = ClientSession(client_socket, address)
            threading.Thread(target=self.client_loop, args=(session,), daemon=True).start()

    def client_loop(self, session: ClientSession) -> None:
        self.logger.info("Connection from %s", session.address)
        try:
            while session.alive:
                try:
                    chunk = session.socket.recv(4096)
                except TimeoutError:
                    continue
                except socket.timeout:
                    continue
                if chunk == b"":
                    break
                for message in session.reader.feed(chunk):
                    handle_message(self, session, message)
        except OSError:
            pass
        finally:
            if session.username:
                self.remove_session(session.username)
            session.close()

    def register_session(self, session: ClientSession, username: str) -> None:
        with self.lock:
            if username in self.sessions:
                session.send({"type": "error", "message": "Username already in use."})
                return
            session.username = username
            self.sessions[username] = session
            self.profiles.setdefault(username, default_profile())
        session.send(
            {
                "type": "joined",
                "username": username,
                "profile": self.profiles[username]["profile"],
                "controls": self.profiles[username]["controls"],
            }
        )
        self.send_lobby_state()

    def remove_session(self, username: str) -> None:
        with self.lock:
            private_peers = list(self.private_chat_peers.pop(username, set()))
            for peer in private_peers:
                self.private_chat_peers.get(peer, set()).discard(username)
                peer_session = self.sessions.get(peer)
                if peer_session:
                    peer_session.send(
                        {
                            "type": "private_chat_status",
                            "peer": username,
                            "message": "Player disconnected",
                            "online": False,
                            "timestamp": self._chat_timestamp(),
                        }
                    )
            self.sessions.pop(username, None)
            self.invites.pop(username, None)
            self.stop_spectating(username)
            for target, invites in list(self.invites.items()):
                self.invites[target] = [invite for invite in invites if invite.inviter != username]
            profile = self.profiles.get(username)
            if profile:
                profile["status"] = "offline"
                profile["current_match"] = ""
        self.forfeit_match(username, disconnected=True)
        self.send_lobby_state()

    def save_profile(self, username: str, message: dict) -> None:
        with self.lock:
            profile = self.profiles.setdefault(username, default_profile())
            profile["profile"].update(message.get("profile", {}))
            profile["profile"]["target_score"] = clamp_target_score(profile["profile"].get("target_score", 0))
            profile["controls"].update(message.get("controls", {}))
            profile["ui_settings"].update(message.get("ui_settings", {}))
        self.send_lobby_state()

    def send_lobby_state(self, username: str | None = None) -> None:
        with self.lock:
            self._expire_invites_locked()
            payload = {
                "type": "lobby_state",
                "users": serialize_users({name: data for name, data in self.profiles.items() if name in self.sessions}),
                "messages": self.lobby_messages[-MAX_LOBBY_MESSAGES:],
                "active_matches": [
                    {
                        "match_id": match_id,
                        "players": match.players,
                        "spectators": len(match.spectators),
                        "map": match.map_name,
                        "target_score": match.target_score,
                    }
                    for match_id, match in self.active_matches.items()
                ],
            }
            if username:
                payload["incoming_invites"] = [
                    {"from": invite.inviter, "expires_in": max(0, math.ceil(invite.expires_in()))}
                    for invite in self.invites.get(username, [])
                ]
                session = self.sessions.get(username)
                if session:
                    session.send(payload)
                return
            for user, session in self.sessions.items():
                user_payload = dict(payload)
                user_payload["incoming_invites"] = [
                    {"from": invite.inviter, "expires_in": max(0, math.ceil(invite.expires_in()))}
                    for invite in self.invites.get(user, [])
                ]
                session.send(user_payload)

    def send_lobby_chat(self, username: str, text: str) -> None:
        clean = text.strip()[:120]
        if not clean:
            return
        with self.lock:
            self.lobby_messages.append(f"{username}: {clean}")
            self.lobby_messages = trim_messages(self.lobby_messages, MAX_LOBBY_MESSAGES)
            for session in self.sessions.values():
                session.send({"type": "lobby_chat", "from": username, "text": clean})

    def open_private_chat(self, username: str, target: str) -> None:
        with self.lock:
            if target == username:
                self.sessions[username].send({"type": "private_chat_error", "target": target, "message": "Cannot start private chat with yourself."})
                return
            if target not in self.sessions:
                self.sessions[username].send({"type": "private_chat_error", "target": target, "message": "Player is disconnected."})
                return
            self.private_chat_peers.setdefault(username, set()).add(target)
            self.private_chat_peers.setdefault(target, set()).add(username)
            self.sessions[username].send({"type": "private_chat_opened", "peer": target})

    def send_private_lobby_chat(self, username: str, target: str, text: str) -> None:
        clean = text.strip()[:240]
        if not clean:
            return
        with self.lock:
            if target == username:
                self.sessions[username].send({"type": "private_chat_error", "target": target, "message": "Cannot send private messages to yourself."})
                return
            sender_session = self.sessions.get(username)
            target_session = self.sessions.get(target)
            if not sender_session:
                return
            if not target_session:
                sender_session.send({"type": "private_chat_error", "target": target, "message": "Player is disconnected."})
                return
            self.private_chat_peers.setdefault(username, set()).add(target)
            self.private_chat_peers.setdefault(target, set()).add(username)
            payload = {
                "type": "private_lobby_chat",
                "from": username,
                "to": target,
                "text": clean,
                "timestamp": self._chat_timestamp(),
            }
            sender_session.send(payload)
            target_session.send(payload)

    def send_invite(self, inviter: str, target: str) -> None:
        with self.lock:
            self._expire_invites_locked()
            if target == inviter:
                self.sessions[inviter].send({"type": "error", "message": "Choose another player."})
                return
            if target not in self.sessions:
                self.sessions[inviter].send({"type": "error", "message": "Target player is not online."})
                return
            if self.profiles[target]["status"] != "lobby":
                self.sessions[inviter].send({"type": "error", "message": "Target player is busy."})
                return
            invite = new_invite(inviter, target)
            self.invites.setdefault(target, [])
            self.invites[target] = [item for item in self.invites[target] if item.inviter != inviter]
            self.invites[target].append(invite)
            expires_in = max(0, math.ceil(invite.expires_in()))
            self.sessions[inviter].send({"type": "invite_sent", "target": target, "expires_in": expires_in})
            self.sessions[target].send({"type": "invite_received", "from": inviter, "expires_in": expires_in})
        self.send_lobby_state()

    def cancel_invite(self, inviter: str, target: str) -> None:
        with self.lock:
            if target in self.invites:
                self.invites[target] = [invite for invite in self.invites[target] if invite.inviter != inviter]
                if target in self.sessions:
                    self.sessions[target].send({"type": "invite_cancelled", "from": inviter})
        self.send_lobby_state()

    def respond_invite(self, username: str, inviter: str, accept: bool) -> None:
        with self.lock:
            self._expire_invites_locked()
            invites = self.invites.get(username, [])
            matched = next((invite for invite in invites if invite.inviter == inviter), None)
            if not matched:
                self.sessions[username].send({"type": "error", "message": "Invite not found."})
                return
            if matched.expires_in() <= 0:
                self.invites[username] = [invite for invite in invites if invite.inviter != inviter]
                inviter_session = self.sessions.get(inviter)
                if inviter_session:
                    inviter_session.send({"type": "invite_expired", "role": "sender", "target": username, "message": "Invitation expired"})
                self.sessions[username].send({"type": "invite_expired", "role": "receiver", "from": inviter, "message": "Invitation expired"})
                self.send_lobby_state()
                return
            self.invites[username] = [invite for invite in invites if invite.inviter != inviter]
            if not accept:
                if inviter in self.sessions:
                    self.sessions[inviter].send({"type": "invite_response", "status": "declined", "by": username})
                self.send_lobby_state()
                return
            if inviter not in self.sessions:
                self.sessions[username].send({"type": "error", "message": "Inviter disconnected."})
                return
        self.start_match(inviter, username)

    def start_match(self, player_a: str, player_b: str) -> None:
        with self.lock:
            match_id = f"{player_a}_vs_{player_b}_{int(time.time())}"
            for player in (player_a, player_b):
                self.profiles[player]["status"] = "in_match"
                self.profiles[player]["current_match"] = match_id
            match = Match(match_id=match_id, players=[player_a, player_b], profiles=self.profiles)
            self.active_matches[match_id] = match
            snapshot = match.snapshot()
            self.sessions[player_a].send({"type": "invite_response", "status": "accepted", "by": player_b})
            self.sessions[player_b].send({"type": "invite_response", "status": "accepted", "by": player_a})
            self.sessions[player_a].send({"type": "match_started", "players": match.players, "snapshot": snapshot})
            self.sessions[player_b].send({"type": "match_started", "players": match.players, "snapshot": snapshot})
        self.send_lobby_state()

    def start_spectating(self, username: str, match_id: str) -> None:
        with self.lock:
            match = self.active_matches.get(match_id)
            if not match:
                self.sessions[username].send({"type": "error", "message": "Match not found."})
                return
            match.spectators.add(username)
            self.spectator_lookup[username] = match_id
            self.profiles[username]["status"] = "spectating"
            self.profiles[username]["current_match"] = match_id
            self.sessions[username].send({"type": "spectate_started", "snapshot": match.snapshot()})
        self.send_lobby_state()

    def stop_spectating(self, username: str) -> None:
        with self.lock:
            match_id = self.spectator_lookup.pop(username, "")
            if match_id and match_id in self.active_matches:
                self.active_matches[match_id].spectators.discard(username)
            if username in self.profiles and username in self.sessions:
                self.profiles[username]["status"] = "lobby"
                self.profiles[username]["current_match"] = ""

    def apply_action(self, username: str, action: str) -> None:
        with self.lock:
            match = self._match_for_user(username)
            if match:
                match.apply_action(username, action)

    def send_match_chat(self, username: str, text: str) -> None:
        clean = text.strip()[:120]
        if not clean:
            return
        with self.lock:
            match = self._match_for_user(username)
            if not match:
                return
            match.add_chat(f"{username}: {clean}")
            for recipient in match.players + list(match.spectators):
                session = self.sessions.get(recipient)
                if session:
                    session.send({"type": "match_chat", "from": username, "text": clean})

    def send_reaction(self, username: str, emoji: str) -> None:
        with self.lock:
            match = self._match_for_user(username)
            if not match:
                return
            match.add_reaction(username, emoji)
            for recipient in match.players + list(match.spectators):
                session = self.sessions.get(recipient)
                if session:
                    session.send({"type": "reaction", "from": username, "emoji": emoji})

    def request_pause(self, username: str) -> None:
        with self.lock:
            match = self._match_for_user(username)
            if match:
                match.request_pause(username)

    def resume_pause(self, username: str) -> None:
        with self.lock:
            match = self._match_for_user(username)
            if match:
                match.resume_pause(username)

    def forfeit_match(self, username: str, disconnected: bool = False) -> None:
        with self.lock:
            match = self._match_for_user(username)
            if not match:
                return
            opponent = other_player(match.players, username)
            match.over = True
            match.winner = opponent
            match.announcements.append(f"{username} {'disconnected' if disconnected else 'forfeited'}.")

    def leave_match(self, username: str) -> None:
        with self.lock:
            match = self._match_for_user(username)
            if not match:
                return
            opponent = other_player(match.players, username)
            match.over = True
            match.winner = opponent
            match.end_reason = "player_left"
            match.left_player = username
            match.announcements.append(f"{username} left the match.")

    def match_loop(self) -> None:
        interval = 1 / TICK_RATE
        while True:
            time.sleep(interval)
            finished: list[str] = []
            with self.lock:
                self._expire_invites_locked()
                connected = set(self.sessions)
                for match_id, match in self.active_matches.items():
                    match.step(interval, connected)
                    snapshot = match.snapshot()
                    for recipient in match.players + list(match.spectators):
                        session = self.sessions.get(recipient)
                        if session:
                            session.send({"type": "match_state", "snapshot": snapshot})
                    if match.over:
                        finished.append(match_id)
                for match_id in finished:
                    self._complete_match(match_id)

    def _complete_match(self, match_id: str) -> None:
        match = self.active_matches.pop(match_id, None)
        if not match:
            return
        snapshot = match.snapshot()
        for player in match.players:
            if player in self.profiles and player in self.sessions:
                self.profiles[player]["status"] = "lobby"
                self.profiles[player]["current_match"] = ""
            session = self.sessions.get(player)
            if session:
                payload = {
                    "type": "match_over",
                    "winner": match.winner,
                    "scores": match.scores,
                    "snapshot": snapshot,
                    "reason": match.end_reason,
                    "left_by": match.left_player,
                }
                if match.end_reason == "player_left":
                    payload["message"] = "You left the match." if player == match.left_player else "Opponent left match"
                session.send(payload)
        for spectator in list(match.spectators):
            if spectator in self.profiles and spectator in self.sessions:
                self.profiles[spectator]["status"] = "lobby"
                self.profiles[spectator]["current_match"] = ""
            session = self.sessions.get(spectator)
            if session:
                session.send(
                    {
                        "type": "match_over",
                        "winner": match.winner,
                        "scores": match.scores,
                        "snapshot": snapshot,
                        "reason": match.end_reason,
                        "left_by": match.left_player,
                        "message": "A player left the match." if match.end_reason == "player_left" else "",
                    }
                )
            self.spectator_lookup.pop(spectator, None)
        self.send_lobby_state()

    def _match_for_user(self, username: str) -> Match | None:
        profile = self.profiles.get(username)
        if not profile:
            return None
        match_id = profile.get("current_match", "")
        return self.active_matches.get(match_id)

    def _expire_invites_locked(self) -> None:
        expired: list[tuple[str, str]] = []
        for target, invites in list(self.invites.items()):
            active = []
            for invite in invites:
                if invite.expires_in() <= 0:
                    expired.append((invite.inviter, target))
                else:
                    active.append(invite)
            self.invites[target] = active
        for inviter, target in expired:
            inviter_session = self.sessions.get(inviter)
            if inviter_session:
                inviter_session.send({"type": "invite_expired", "role": "sender", "target": target, "message": "Invitation expired"})
            target_session = self.sessions.get(target)
            if target_session:
                target_session.send({"type": "invite_expired", "role": "receiver", "from": inviter, "message": "Invitation expired"})

    def _chat_timestamp(self) -> str:
        return time.strftime("%H:%M")


def main() -> None:
    ArenaServer().start()


if __name__ == "__main__":
    main()
