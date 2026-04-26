"""Incoming message handlers."""

from __future__ import annotations

from shared.helpers import username_validation_error, valid_username


def handle_message(server: "ArenaServer", session: "ClientSession", message: dict) -> None:
    msg_type = message.get("type")
    if msg_type == "join":
        username = message.get("username", "").strip()
        if not valid_username(username):
            session.send({"type": "error", "message": username_validation_error(username)})
            return
        server.register_session(session, username)
        return
    if not session.username:
        session.send({"type": "error", "message": "Join before sending commands."})
        return
    if msg_type == "save_profile":
        server.save_profile(session.username, message)
    elif msg_type == "request_lobby":
        server.send_lobby_state(session.username)
    elif msg_type == "send_lobby_chat":
        server.send_lobby_chat(session.username, message.get("text", ""))
    elif msg_type == "open_private_chat":
        server.open_private_chat(session.username, message.get("target", ""))
    elif msg_type == "send_private_lobby_chat":
        server.send_private_lobby_chat(session.username, message.get("target", ""), message.get("text", ""))
    elif msg_type in {"send_private_chat", "private_message", "direct_message"}:
        session.send({"type": "private_chat_error", "target": message.get("target", ""), "message": "Unsupported private chat message type."})
    elif msg_type == "invite_player":
        server.send_invite(session.username, message.get("target", ""))
    elif msg_type == "cancel_invite":
        server.cancel_invite(session.username, message.get("target", ""))
    elif msg_type == "respond_invite":
        server.respond_invite(session.username, message.get("inviter", ""), message.get("accept", False))
    elif msg_type == "spectate_match":
        server.start_spectating(session.username, message.get("match_id", ""))
    elif msg_type == "leave_spectate":
        server.stop_spectating(session.username)
    elif msg_type == "action":
        server.apply_action(session.username, message.get("action", ""))
    elif msg_type == "send_match_chat":
        server.send_match_chat(session.username, message.get("text", ""))
    elif msg_type == "emoji_reaction":
        server.send_reaction(session.username, message.get("emoji", ""))
    elif msg_type == "forfeit_match":
        server.forfeit_match(session.username)
    elif msg_type == "leave_match":
        server.leave_match(session.username)
    elif msg_type == "request_pause":
        server.request_pause(session.username)
    elif msg_type == "resume_pause":
        server.resume_pause(session.username)
