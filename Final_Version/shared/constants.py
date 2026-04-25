"""Project-wide constants."""

from __future__ import annotations

APP_NAME = "\u03A0thon Arena"
VERSION = "1.0.0"

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 720
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 12
INVITE_TTL_SECONDS = 30
TARGET_SCORE_TO_WIN = 400
MAX_TARGET_SCORE = 4000

GRID_WIDTH = 36
GRID_HEIGHT = 24
TICK_RATE = 15
STATE_BROADCAST_RATE = 10

DEFAULT_UI_SETTINGS = {
    "music_volume": 70,
    "sfx_volume": 80,
    "brightness": 100,
    "fullscreen": False,
    "ui_scale": 100,
    "mute": False,
}

DEFAULT_CONTROLS = {
    "up": "w",
    "down": "s",
    "left": "a",
    "right": "d",
}

DEFAULT_PROFILE = {
    "snake_color": "ember",
    "snake_skin": "classic",
    "map": "Desert",
    "duration": 2,
    "target_score": TARGET_SCORE_TO_WIN,
    "visual_mod": "Classic Glow",
}

SNAKE_SKINS = ("classic", "viper", "titan")
MAP_CHOICES = ("Snow", "Jungle", "Desert")

MAPS = {
    "Desert": {
        "background_key": "desert",
        "palette": {
            "field": (62, 44, 27),
            "grid": (120, 92, 56),
            "obstacle": (114, 88, 61),
            "pie": (244, 188, 87),
            "panel_border": (201, 146, 78),
        },
        "obstacles": [(8, 5), (8, 6), (8, 7), (18, 9), (19, 9), (26, 16), (27, 16), (29, 7), (30, 7)],
    },
    "Snow": {
        "background_key": "snow",
        "palette": {
            "field": (46, 84, 120),
            "grid": (176, 216, 242),
            "obstacle": (134, 167, 199),
            "pie": (200, 236, 255),
            "panel_border": (148, 194, 231),
        },
        "obstacles": [(6, 8), (7, 8), (8, 8), (16, 4), (16, 5), (25, 12), (26, 12), (13, 18), (14, 18)],
    },
    "Jungle": {
        "background_key": "jungle",
        "palette": {
            "field": (28, 68, 38),
            "grid": (112, 156, 96),
            "obstacle": (95, 125, 74),
            "pie": (243, 215, 95),
            "panel_border": (104, 174, 103),
        },
        "obstacles": [(9, 13), (10, 13), (11, 13), (19, 6), (19, 7), (26, 5), (26, 6), (26, 7), (29, 17), (30, 17)],
    },
}

POWERUP_TYPES = ("shield", "boost", "drain")
MAX_LOBBY_MESSAGES = 24
MAX_MATCH_CHAT = 18
