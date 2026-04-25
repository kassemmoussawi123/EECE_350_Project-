"""Asset loading with safe fallbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pygame
from shared.constants import MAPS


class AssetLoader:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.assets: Dict[str, pygame.Surface | None] = {}

    def load(self) -> Dict[str, pygame.Surface | None]:
        self.assets["background"] = self._try_image(self.root / "assets" / "backgrounds" / "arena_landscape.jpg")
        self.assets["portrait"] = self._try_image(self.root / "assets" / "backgrounds" / "arena_portrait.jpg")
        self.assets["snake"] = self._try_image(self.root / "assets" / "images" / "snake_concept.jpg")
        self.assets["icon_orb"] = self._try_image(self.root / "assets" / "icons" / "icon_orb.jpg")
        self.assets["icon_shield"] = self._try_image(self.root / "assets" / "icons" / "icon_shield.jpg")
        self.assets["banner"] = self._try_image(self.root / "assets" / "images" / "banner_strip.jpg")
        self.assets["map_backgrounds"] = {name: self._build_map_background(name) for name in MAPS}
        self.assets["map_previews"] = {name: self._build_map_preview(name) for name in MAPS}
        return self.assets

    def _try_image(self, path: Path) -> pygame.Surface | None:
        try:
            return pygame.image.load(str(path)).convert_alpha()
        except (pygame.error, FileNotFoundError):
            return None

    def _build_map_background(self, map_name: str) -> pygame.Surface:
        """Generate themed backgrounds so each map renders distinctly in-game."""
        surface = pygame.Surface((1280, 720))
        colors = {
            "Desert": ((197, 146, 67), (120, 82, 35), (234, 204, 136)),
            "Snow": ((179, 215, 246), (83, 124, 171), (241, 250, 255)),
            "Jungle": ((64, 120, 63), (23, 58, 32), (148, 189, 103)),
        }
        top, bottom, accent = colors.get(map_name, colors["Desert"])
        for y in range(surface.get_height()):
            ratio = y / max(1, surface.get_height() - 1)
            color = tuple(int(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
            pygame.draw.line(surface, color, (0, y), (surface.get_width(), y))
        if map_name == "Desert":
            for x in range(0, surface.get_width(), 160):
                pygame.draw.circle(surface, accent, (x + 60, 560), 120, 0)
                pygame.draw.rect(surface, (156, 110, 57), (x + 24, 520, 10, 80), border_radius=4)
        elif map_name == "Snow":
            for x in range(0, surface.get_width(), 130):
                pygame.draw.polygon(surface, (214, 232, 248), [(x, 500), (x + 80, 320), (x + 160, 500)])
            for x in range(24, surface.get_width(), 70):
                pygame.draw.circle(surface, (245, 250, 255), (x, 120 + (x % 50)), 2)
        else:
            for x in range(0, surface.get_width(), 150):
                pygame.draw.rect(surface, (31, 74, 38), (x, 0, 20, surface.get_height()))
                pygame.draw.circle(surface, accent, (x + 10, 90), 80)
                pygame.draw.circle(surface, accent, (x + 46, 120), 72)
        return surface.convert()

    def _build_map_preview(self, map_name: str) -> pygame.Surface:
        preview = pygame.transform.smoothscale(self._build_map_background(map_name), (420, 230))
        frame = pygame.Surface((440, 250), pygame.SRCALPHA)
        frame.blit(preview, (10, 10))
        return frame
