"""General helpers shared by client and server."""

from __future__ import annotations

import re
import time


USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def now() -> float:
    return time.time()


def format_clock(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, remainder = divmod(total, 60)
    return f"{minutes:02d}:{remainder:02d}"


def valid_username(value: str) -> bool:
    return bool(USERNAME_RE.fullmatch(value))
