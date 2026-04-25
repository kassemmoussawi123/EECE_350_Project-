"""Small utilities for the server."""

from __future__ import annotations

import logging
from typing import Iterable


def build_logger() -> logging.Logger:
    logger = logging.getLogger("pithon-arena-server")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    return logger


def trim_messages(messages: list[str], limit: int) -> list[str]:
    return messages[-limit:]


def other_player(players: Iterable[str], username: str) -> str:
    return next((player for player in players if player != username), "")
