"""Main pygame application controller."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict

import pygame

from client.audio import SoundManager
from client.network import NetworkClient
from client.renderer import ArenaRenderer
from client.settings import SettingsStore
from client.ui.assets_loader import AssetLoader
from client.ui.screens import (
    ConnectionScreen,
    CreditsScreen,
    CustomizationScreen,
    EndGameScreen,
    GameScreen,
    HelpScreen,
    LobbyScreen,
    MainMenuScreen,
    MatchSettingsScreen,
    MatchmakingScreen,
    SettingsScreen,
    SpectatorScreen,
    SplashScreen,
)
from client.ui.theme import build_theme
from shared.constants import DEFAULT_CONTROLS, DEFAULT_PROFILE, DEFAULT_UI_SETTINGS, MAPS, SCREEN_HEIGHT, SCREEN_WIDTH
from shared.helpers import clamp_target_score


class GameClientApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("\u03A0thon Arena")
        try:
            pygame.mixer.init()
        except pygame.error:
            pass
        self.root = Path(__file__).resolve().parents[1]
        self.settings = SettingsStore(self.root / ".client_settings.json")
        flags = pygame.SCALED
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        self.clock = pygame.time.Clock()
        self.theme = build_theme()
        self.assets = AssetLoader(self.root).load()
        self.sound = SoundManager(self.root)
        self.renderer = ArenaRenderer(self.theme)
        self.network = NetworkClient()
        self.running = True
        self.connected = False
        self.username = ""
        self.profile = DEFAULT_PROFILE.copy()
        self.profile.update(self.settings.data.get("profile", {}))
        self.profile["target_score"] = clamp_target_score(self.profile.get("target_score", 0))
        self.controls = DEFAULT_CONTROLS.copy()
        self.controls.update(self.settings.data.get("controls", {}))
        self.ui_settings = DEFAULT_UI_SETTINGS.copy()
        self.ui_settings.update(self.settings.data.get("ui", {}))
        self.status_message = ""
        self.pending_invite_text = ""
        self.pending_invite_target = ""
        self.pending_invite_deadline = 0.0
        self.incoming_inviter = ""
        self.incoming_invite_deadline = 0.0
        self.awaiting_match_start = False
        self.lobby_users: list[Dict] = []
        self.active_matches: list[Dict] = []
        self.lobby_messages: list[str] = []
        self.private_chats: dict[str, list[Dict]] = {}
        self.private_unread: dict[str, int] = {}
        self.private_chat_peer = ""
        self.private_chat_minimized = False
        self.match_snapshot: Dict = {
            "players": [],
            "snakes": {},
            "scores": {},
            "health": {},
            "time_left": 0,
            "map_palette": MAPS["Desert"]["palette"],
            "obstacles": [],
            "pies": [],
            "powerups": [],
            "announcements": [],
            "snake_colors": {},
            "buffs": {},
            "pause_state": {"is_paused": False, "paused_by": "", "pause_remaining": 0.0, "pauses_left": {}},
        }
        self.match_chat: list[str] = []
        self.match_result: Dict | None = None
        self.last_opponent = ""
        self.spectating = False
        self.screens = {
            "splash": SplashScreen(self),
            "menu": MainMenuScreen(self),
            "connection": ConnectionScreen(self),
            "lobby": LobbyScreen(self),
            "customization": CustomizationScreen(self),
            "match_settings": MatchSettingsScreen(self),
            "matchmaking": MatchmakingScreen(self),
            "settings": SettingsScreen(self),
            "help": HelpScreen(self),
            "credits": CreditsScreen(self),
            "game": GameScreen(self),
            "spectator": SpectatorScreen(self),
            "endgame": EndGameScreen(self),
        }
        self.current_screen = self.screens["splash"]
        self.apply_audio_volume()
        self.sound.sync_for_screen("splash")

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self._process_network()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.request_quit()
                else:
                    self.current_screen.handle_event(event)
            self.current_screen.update(dt)
            self.current_screen.draw(self.screen)
            pygame.display.flip()
        self.network.disconnect()
        pygame.quit()

    def set_screen(self, name: str) -> None:
        self.current_screen = self.screens[name]
        self.current_screen.on_enter()
        self.sound.sync_for_screen(name)
        if self.sound.last_error and not self.status_message:
            self.status_message = self.sound.last_error

    def connect(self, host: str, port: int, username: str) -> None:
        try:
            self.network.connect(host, port)
        except OSError as exc:
            self.status_message = (
                "Unable to connect to the server.\n"
                "Please check the IP address, port, and make sure the server is running."
            )
            return
        self.network.send({"type": "join", "username": username})
        self.settings.data["connection"].update({"host": host, "port": port, "username": username})
        self.settings.save()
        self.status_message = "Connecting..."

    def disconnect(self) -> None:
        self.network.disconnect()
        self.connected = False
        self.username = ""
        self.set_screen("menu")

    def request_quit(self) -> None:
        self.running = False

    def push_profile(self) -> None:
        self.profile["target_score"] = clamp_target_score(self.profile.get("target_score", 0))
        self.settings.data["profile"] = self.profile.copy()
        self.settings.data["controls"] = self.controls.copy()
        self.settings.save()
        if self.connected:
            self.network.send(
                {
                    "type": "save_profile",
                    "profile": self.profile,
                    "controls": self.controls,
                    "ui_settings": self.settings.data["ui"],
                }
            )

    def request_lobby_refresh(self) -> None:
        if self.connected:
            self.network.send({"type": "request_lobby"})

    def send_invite(self, target: str) -> None:
        self.pending_invite_target = target
        self.pending_invite_text = f"Invite pending for {target}."
        self.pending_invite_deadline = 0.0
        self.network.send({"type": "invite_player", "target": target})
        self.set_screen("matchmaking")

    def open_private_chat(self, peer: str) -> None:
        peer = peer.strip()
        if not peer or peer == self.username:
            self.status_message = "Choose another player for private chat."
            return
        self.private_chat_peer = peer
        self.private_chat_minimized = False
        self.private_chats.setdefault(peer, [])
        self.private_unread[peer] = 0
        if self.connected:
            self.network.send({"type": "open_private_chat", "target": peer})

    def close_private_chat(self) -> None:
        self.private_chat_peer = ""
        self.private_chat_minimized = False

    def minimize_private_chat(self) -> None:
        self.private_chat_minimized = True

    def restore_private_chat(self) -> None:
        if self.private_chat_peer:
            self.private_chat_minimized = False
            self.private_unread[self.private_chat_peer] = 0

    def send_private_message(self, peer: str, text: str) -> None:
        clean = text.strip()
        if not clean:
            return
        if peer == self.username:
            self.status_message = "Choose another player for private chat."
            return
        self.network.send({"type": "send_private_lobby_chat", "target": peer, "text": clean})

    def forfeit_match(self) -> None:
        self.network.send({"type": "forfeit_match"})
        self.set_screen("lobby")

    def leave_match(self) -> None:
        self.network.send({"type": "leave_match"})

    def update_audio_settings(self, music: int | None = None, sfx: int | None = None, mute: bool | None = None) -> None:
        if music is not None:
            self.settings.data["ui"]["music_volume"] = max(0, min(100, int(music)))
        if sfx is not None:
            self.settings.data["ui"]["sfx_volume"] = max(0, min(100, int(sfx)))
        if mute is not None:
            self.settings.data["ui"]["mute"] = bool(mute)
        self.settings.save()
        self.apply_audio_volume()

    def set_invite_deadline(self, seconds_remaining: int, incoming: bool) -> None:
        deadline = pygame.time.get_ticks() / 1000.0 + max(0, seconds_remaining)
        if incoming:
            self.incoming_invite_deadline = deadline
        else:
            self.pending_invite_deadline = deadline

    def invite_seconds_left(self, incoming: bool) -> int:
        deadline = self.incoming_invite_deadline if incoming else self.pending_invite_deadline
        if deadline <= 0:
            return 0
        remaining = deadline - (pygame.time.get_ticks() / 1000.0)
        return max(0, int(remaining + 0.999))

    def toggle_mute(self) -> None:
        current = self.settings.data["ui"]["mute"]
        self.settings.data["ui"]["mute"] = not current
        self.settings.save()
        self.apply_audio_volume()

    def adjust_music_volume(self, delta: int) -> None:
        value = self.settings.data["ui"]["music_volume"] + delta
        self.settings.data["ui"]["music_volume"] = max(0, min(100, value))
        self.settings.save()
        self.apply_audio_volume()

    def apply_audio_volume(self) -> None:
        volume = 0.0 if self.settings.data["ui"]["mute"] else self.settings.data["ui"]["music_volume"] / 100.0
        self.sound.apply_volume(volume)

    def key_to_action(self, key: int) -> str:
        arrow_map = {
            pygame.K_UP: "up",
            pygame.K_DOWN: "down",
            pygame.K_LEFT: "left",
            pygame.K_RIGHT: "right",
        }
        if key in arrow_map:
            return arrow_map[key]
        aliases = {
            "up": {"up", "w"},
            "down": {"down", "s"},
            "left": {"left", "a"},
            "right": {"right", "d"},
        }
        pressed = pygame.key.name(key).lower()
        for action, configured in self.controls.items():
            token = configured.lower().strip()
            if pressed == token or pressed in aliases.get(token, set()) or token in aliases.get(pressed, set()):
                return action
        return ""

    def resolve_snake_color(self, name: str) -> tuple[int, int, int]:
        palette = {
            "ember": (238, 126, 68),
            "azure": (80, 180, 255),
            "jade": (99, 208, 143),
            "onyx": (122, 132, 150),
            "gold": (235, 196, 84),
        }
        return palette.get(name.lower(), (238, 126, 68))

    def _process_network(self) -> None:
        for message in self.network.poll():
            self._handle_message(message)

    def _handle_message(self, message: Dict) -> None:
        msg_type = message.get("type")
        if msg_type == "joined":
            self.connected = True
            self.username = message["username"]
            self.profile.update(message.get("profile", {}))
            self.controls.update(message.get("controls", {}))
            self.status_message = f"Connected as {self.username}."
            self.push_profile()
            self.request_lobby_refresh()
            self.set_screen("lobby")
        elif msg_type == "error":
            self.status_message = message.get("message", "Unknown server error.")
            if self.current_screen is self.screens["matchmaking"]:
                self.set_screen("lobby")
        elif msg_type == "connection_closed":
            self.connected = False
            self.status_message = "Connection closed."
            if self.current_screen is not self.screens["menu"]:
                self.set_screen("menu")
        elif msg_type == "lobby_state":
            self.lobby_users = message.get("users", [])
            self.active_matches = message.get("active_matches", [])
            self.lobby_messages = message.get("messages", [])
            pending = message.get("incoming_invites", [])
            if pending:
                invite = pending[-1]
                self.incoming_inviter = invite["from"]
                self.set_invite_deadline(invite.get("expires_in", 0), incoming=True)
                self.pending_invite_text = f"{invite['from']} invited you. Press Y to accept or N to reject in lobby."
            elif not self.pending_invite_target and not self.awaiting_match_start:
                self.incoming_inviter = ""
                self.incoming_invite_deadline = 0.0
                self.pending_invite_text = ""
        elif msg_type == "lobby_chat":
            self.lobby_messages.append(f"{message['from']}: {message['text']}")
        elif msg_type == "private_chat_opened":
            peer = message.get("peer", "")
            if peer:
                self.private_chats.setdefault(peer, [])
        elif msg_type == "private_lobby_chat":
            sender = message.get("from", "")
            recipient = message.get("to", "")
            peer = recipient if sender == self.username else sender
            if not peer:
                return
            self._append_private_entry(
                peer,
                {
                    "kind": "message",
                    "timestamp": message.get("timestamp", self._private_timestamp()),
                    "sender": sender,
                    "text": message.get("text", ""),
                },
            )
            if sender != self.username:
                if self.private_chat_peer == peer and not self.private_chat_minimized and self.current_screen is self.screens["lobby"]:
                    self.private_unread[peer] = 0
                else:
                    self.private_unread[peer] = self.private_unread.get(peer, 0) + 1
                self.status_message = f"Private message from {peer}."
                if not self.settings.data["ui"].get("mute", False):
                    self.sound.play_private_notification(self.settings.data["ui"].get("sfx_volume", 80) / 100.0)
        elif msg_type == "private_chat_status":
            peer = message.get("peer", "")
            if peer:
                self._append_private_entry(
                    peer,
                    {
                        "kind": "status",
                        "timestamp": message.get("timestamp", self._private_timestamp()),
                        "sender": "",
                        "text": message.get("message", "Player disconnected"),
                    },
                )
                if not (self.private_chat_peer == peer and not self.private_chat_minimized and self.current_screen is self.screens["lobby"]):
                    self.private_unread[peer] = self.private_unread.get(peer, 0) + 1
                self.status_message = message.get("message", "Player disconnected")
        elif msg_type == "private_chat_error":
            target = message.get("target", "")
            error = message.get("message", "Private chat error.")
            self.status_message = error
            if target:
                self._append_private_entry(
                    target,
                    {
                        "kind": "status",
                        "timestamp": self._private_timestamp(),
                        "sender": "",
                        "text": error,
                    },
                )
        elif msg_type == "invite_sent":
            self.pending_invite_target = message.get("target", "")
            self.set_invite_deadline(message.get("expires_in", 0), incoming=False)
            self.pending_invite_text = f"Invite sent to {self.pending_invite_target}."
            self.set_screen("matchmaking")
        elif msg_type == "invite_received":
            self.awaiting_match_start = False
            self.incoming_inviter = message["from"]
            self.set_invite_deadline(message.get("expires_in", 0), incoming=True)
            self.pending_invite_text = f"{message['from']} invited you. Press Y to accept or N to reject."
            if self.current_screen not in (self.screens["game"], self.screens["spectator"], self.screens["matchmaking"]):
                self.set_screen("lobby")
            self.request_lobby_refresh()
        elif msg_type == "invite_cancelled":
            self.awaiting_match_start = False
            self.pending_invite_text = "Invite was cancelled."
            self.pending_invite_target = ""
            self.pending_invite_deadline = 0.0
            self.incoming_inviter = ""
            self.incoming_invite_deadline = 0.0
            self.set_screen("lobby")
        elif msg_type == "invite_expired":
            self.awaiting_match_start = False
            self.pending_invite_text = message.get("message", "Invitation expired")
            self.pending_invite_target = ""
            self.pending_invite_deadline = 0.0
            self.incoming_inviter = ""
            self.incoming_invite_deadline = 0.0
            if self.current_screen is self.screens["matchmaking"]:
                self.set_screen("lobby")
        elif msg_type == "invite_response":
            if message.get("status") == "accepted":
                self.awaiting_match_start = True
                self.pending_invite_target = ""
                self.pending_invite_deadline = 0.0
                self.pending_invite_text = "Invite accepted. Preparing match..."
            else:
                self.awaiting_match_start = False
                self.pending_invite_target = ""
                self.pending_invite_deadline = 0.0
                self.incoming_inviter = ""
                self.incoming_invite_deadline = 0.0
                self.pending_invite_text = f"Invite {message.get('status')}."
                self.set_screen("lobby")
        elif msg_type == "match_started":
            self.awaiting_match_start = False
            self.spectating = False
            self.last_opponent = next((name for name in message.get("players", []) if name != self.username), "")
            self.match_chat.clear()
            self.match_snapshot = message.get("snapshot", self.match_snapshot)
            self.pending_invite_deadline = 0.0
            self.incoming_invite_deadline = 0.0
            self.pending_invite_text = ""
            self.incoming_inviter = ""
            self.set_screen("game")
        elif msg_type == "spectate_started":
            self.spectating = True
            self.match_chat.clear()
            self.match_snapshot = message.get("snapshot", self.match_snapshot)
            self.set_screen("spectator")
        elif msg_type == "match_state":
            self.match_snapshot = message.get("snapshot", self.match_snapshot)
        elif msg_type == "match_chat":
            self.match_chat.append(f"{message['from']}: {message['text']}")
        elif msg_type == "reaction":
            self.match_chat.append(f"{message['from']} reacted {message['emoji']}")
        elif msg_type == "match_over":
            self.awaiting_match_start = False
            self.match_result = {"winner": message.get("winner", "Unknown"), "scores": message.get("scores", {})}
            self.match_snapshot = message.get("snapshot", self.match_snapshot)
            self.pending_invite_text = ""
            self.pending_invite_target = ""
            self.pending_invite_deadline = 0.0
            self.incoming_inviter = ""
            self.incoming_invite_deadline = 0.0
            if message.get("message"):
                self.status_message = message["message"]
            if message.get("reason") == "player_left" and message.get("left_by") == self.username:
                self.request_lobby_refresh()
                self.set_screen("lobby")
            else:
                self.set_screen("endgame")

    def _append_private_entry(self, peer: str, entry: Dict) -> None:
        history = self.private_chats.setdefault(peer, [])
        history.append(entry)
        self.private_chats[peer] = history[-120:]

    def _private_timestamp(self) -> str:
        return time.strftime("%H:%M")
