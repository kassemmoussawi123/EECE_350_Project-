"""General helpers shared by client and server."""

from __future__ import annotations

import re
import time

from shared.constants import MAX_TARGET_SCORE, TARGET_SCORE_TO_WIN, USERNAME_MAX_LENGTH, USERNAME_MIN_LENGTH

USERNAME_RE = re.compile(rf"^[A-Za-z0-9_]{{{USERNAME_MIN_LENGTH},{USERNAME_MAX_LENGTH}}}$")


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


def username_validation_error(value: str) -> str:
    if not value:
        return "Username is required."
    if len(value) < USERNAME_MIN_LENGTH:
        return f"Username must be at least {USERNAME_MIN_LENGTH} characters."
    if len(value) > USERNAME_MAX_LENGTH:
        return f"Username must be at most {USERNAME_MAX_LENGTH} characters."
    if not re.fullmatch(r"[A-Za-z0-9_]+", value):
        return "Username can use only letters, numbers, and underscore."
    return ""


def clamp_target_score(value: int) -> int:
    return max(1, min(MAX_TARGET_SCORE, int(value)))


def parse_target_score(value: str) -> int:
    try:
        parsed = int(value.strip())
    except (TypeError, ValueError, AttributeError):
        parsed = TARGET_SCORE_TO_WIN
    return clamp_target_score(parsed)
