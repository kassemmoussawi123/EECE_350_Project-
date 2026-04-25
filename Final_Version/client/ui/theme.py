"""Visual theme and font registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import pygame


@dataclass
class Theme:
    colors: Dict[str, Tuple[int, int, int]]
    fonts: Dict[str, pygame.font.Font]


def build_theme(font_path: Path | None = None) -> Theme:
    def font(size: int, bold: bool = False) -> pygame.font.Font:
        if font_path and font_path.exists():
            return pygame.font.Font(str(font_path), size)
        face = pygame.font.SysFont("georgia", size, bold=bold)
        return face

    colors = {
        "bg": (8, 14, 24),
        "board": (20, 31, 46),
        "grid": (46, 68, 95),
        "panel": (14, 21, 34),
        "panel_border": (84, 120, 160),
        "accent": (240, 146, 58),
        "accent_soft": (255, 205, 120),
        "accent_2": (88, 193, 255),
        "success": (103, 214, 135),
        "danger": (232, 96, 103),
        "warning": (247, 203, 95),
        "text": (240, 244, 248),
        "muted": (164, 178, 194),
        "input": (16, 25, 40),
        "hover": (31, 47, 70),
        "obstacle": (92, 74, 56),
        "pie": (240, 176, 86),
        "power_shield": (70, 184, 255),
        "power_boost": (255, 120, 76),
        "power_drain": (167, 111, 255),
    }
    fonts = {
        "hero": font(62, bold=True),
        "title": font(38, bold=True),
        "small_title": font(24, bold=True),
        "body": font(22),
        "caption": font(18),
        "tiny": font(14),
    }
    return Theme(colors=colors, fonts=fonts)
