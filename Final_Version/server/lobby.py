"""Lobby state helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from shared.constants import DEFAULT_CONTROLS, DEFAULT_PROFILE, DEFAULT_UI_SETTINGS, INVITE_TTL_SECONDS
from shared.helpers import now


@dataclass
class Invite:
    inviter: str
    target: str
    created_at: float

    def expires_in(self) -> float:
        return max(0.0, INVITE_TTL_SECONDS - (now() - self.created_at))


def default_profile() -> Dict:
    return {
        "profile": DEFAULT_PROFILE.copy(),
        "controls": DEFAULT_CONTROLS.copy(),
        "ui_settings": DEFAULT_UI_SETTINGS.copy(),
        "status": "lobby",
        "current_match": "",
    }


def serialize_users(profiles: Dict[str, Dict]) -> List[Dict]:
    users = []
    for username, data in sorted(profiles.items()):
        users.append(
            {
                "username": username,
                "status": data.get("status", "lobby"),
                "map": data.get("profile", {}).get("map", "Desert"),
            }
        )
    return users


def new_invite(inviter: str, target: str) -> Invite:
    return Invite(inviter=inviter, target=target, created_at=now())
