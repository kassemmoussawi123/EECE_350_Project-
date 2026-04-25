"""Client-side persistent settings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from shared.constants import DEFAULT_CONTROLS, DEFAULT_PROFILE, DEFAULT_UI_SETTINGS


class SettingsStore:
    """Small JSON-backed settings store."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = self._default_settings()
        self.load()

    def _default_settings(self) -> Dict[str, Any]:
        return {
            "connection": {
                "host": "127.0.0.1",
                "port": 5050,
                "username": "",
            },
            "profile": DEFAULT_PROFILE.copy(),
            "controls": DEFAULT_CONTROLS.copy(),
            "ui": DEFAULT_UI_SETTINGS.copy(),
        }

    def load(self) -> None:
        if not self.path.exists():
            self.save()
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            for key, value in payload.items():
                if key in self.data and isinstance(value, dict):
                    self.data[key].update(value)
                else:
                    self.data[key] = value
        except (OSError, ValueError, json.JSONDecodeError):
            self.data = self._default_settings()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def reset_ui(self) -> None:
        self.data["ui"] = DEFAULT_UI_SETTINGS.copy()
        self.save()
