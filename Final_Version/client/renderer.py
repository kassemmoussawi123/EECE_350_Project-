"""Rendering helpers for the game board and HUD."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

import pygame

from client.ui.theme import Theme
from shared.constants import GRID_HEIGHT, GRID_WIDTH
from shared.helpers import clamp, format_clock


class ArenaRenderer:
    """Centralized game rendering."""

    def __init__(self, theme: Theme) -> None:
        self.theme = theme

    def draw_background(self, surface: pygame.Surface, background: pygame.Surface | None, overlay_alpha: int = 120) -> None:
        if background:
            scaled = pygame.transform.smoothscale(background, surface.get_size())
            surface.blit(scaled, (0, 0))
        else:
            surface.fill(self.theme.colors["bg"])
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((*self.theme.colors["bg"], overlay_alpha))
        surface.blit(veil, (0, 0))

    def draw_panel(self, surface: pygame.Surface, rect: pygame.Rect, title: str = "") -> None:
        pygame.draw.rect(surface, self.theme.colors["panel"], rect, border_radius=18)
        pygame.draw.rect(surface, self.theme.colors["panel_border"], rect, 2, border_radius=18)
        if title:
            label = self.theme.fonts["small_title"].render(title, True, self.theme.colors["text"])
            surface.blit(label, (rect.x + 18, rect.y + 14))

    def draw_game(
        self,
        surface: pygame.Surface,
        snapshot: Dict,
        local_player: str,
        assets: Dict[str, pygame.Surface | None],
        spectator: bool = False,
        chat_lines: Iterable[str] = (),
        paused: bool = False,
    ) -> None:
        map_name = snapshot.get("map", "Desert")
        # Apply the authoritative server-selected map to the live game render.
        map_backgrounds = assets.get("map_backgrounds", {})
        self.draw_background(surface, map_backgrounds.get(map_name) if isinstance(map_backgrounds, dict) else assets.get("background"))
        width, height = surface.get_size()
        board_rect = pygame.Rect(36, 96, width - 340, height - 252)
        side_rect = pygame.Rect(width - 286, 96, 250, height - 252)
        chat_rect = pygame.Rect(36, height - 144, width - 340, 108)
        self.draw_panel(surface, board_rect)
        self.draw_panel(surface, side_rect, "Battle Feed")
        self.draw_panel(surface, chat_rect, "Match Chat")
        cell_w = board_rect.width / GRID_WIDTH
        cell_h = board_rect.height / GRID_HEIGHT

        palette = snapshot.get("map_palette", {})
        self._draw_grid(surface, board_rect, palette)
        self._draw_obstacles(surface, board_rect, cell_w, cell_h, snapshot.get("obstacles", []), palette.get("obstacle", self.theme.colors["obstacle"]))
        self._draw_obstacles(surface, board_rect, cell_w, cell_h, snapshot.get("pies", []), palette.get("pie", self.theme.colors["pie"]))
        self._draw_powerups(surface, board_rect, cell_w, cell_h, snapshot.get("powerups", []))
        for name, segments in snapshot.get("snakes", {}).items():
            accent = snapshot.get("snake_colors", {}).get(name, self.theme.colors["accent"])
            shielded = snapshot.get("buffs", {}).get(name, {}).get("shield", 0) > 0
            self._draw_snake(surface, board_rect, cell_w, cell_h, segments, accent, shielded)

        self._draw_hud(surface, snapshot, local_player, spectator)
        self._draw_feed(surface, side_rect, snapshot)
        self._draw_chat(surface, chat_rect, chat_lines)

        if paused:
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((6, 11, 20, 180))
            surface.blit(overlay, (0, 0))
            menu = pygame.Rect(width // 2 - 220, height // 2 - 170, 440, 340)
            self.draw_panel(surface, menu, "Pause")
            pause_state = snapshot.get("pause_state", {})
            if pause_state.get("is_paused"):
                info = self.theme.fonts["caption"].render(
                    f"{pause_state.get('paused_by', 'Player')} paused the match. {int(pause_state.get('pause_remaining', 0))}s left",
                    True,
                    self.theme.colors["accent_soft"],
                )
                surface.blit(info, (menu.x + 30, menu.y + 52))
            for index, line in enumerate(("Resume / Back", "Volume -", "Volume +", "Mute/Unmute", "Open Settings", "Quit Match")):
                label = self.theme.fonts["body"].render(line, True, self.theme.colors["text"])
                surface.blit(label, (menu.x + 30, menu.y + 92 + index * 38))

    def _draw_grid(self, surface: pygame.Surface, rect: pygame.Rect, palette: Dict) -> None:
        fill = palette.get("field", self.theme.colors["board"])
        pygame.draw.rect(surface, fill, rect.inflate(-10, -10), border_radius=16)
        for col in range(GRID_WIDTH + 1):
            x = rect.x + round(col * rect.width / GRID_WIDTH)
            pygame.draw.line(surface, palette.get("grid", self.theme.colors["grid"]), (x, rect.y + 6), (x, rect.bottom - 6), 1)
        for row in range(GRID_HEIGHT + 1):
            y = rect.y + round(row * rect.height / GRID_HEIGHT)
            pygame.draw.line(surface, palette.get("grid", self.theme.colors["grid"]), (rect.x + 6, y), (rect.right - 6, y), 1)

    def _draw_obstacles(self, surface: pygame.Surface, rect: pygame.Rect, cell_w: float, cell_h: float, cells: Iterable[Tuple[int, int]], color: Tuple[int, int, int]) -> None:
        for col, row in cells:
            box = pygame.Rect(rect.x + col * cell_w + 3, rect.y + row * cell_h + 3, cell_w - 6, cell_h - 6)
            pygame.draw.rect(surface, color, box, border_radius=10)

    def _draw_powerups(self, surface: pygame.Surface, rect: pygame.Rect, cell_w: float, cell_h: float, powerups: Iterable[Dict]) -> None:
        palette = {"shield": self.theme.colors["power_shield"], "boost": self.theme.colors["power_boost"], "drain": self.theme.colors["power_drain"]}
        for item in powerups:
            col, row = item["position"]
            center = (rect.x + int((col + 0.5) * cell_w), rect.y + int((row + 0.5) * cell_h))
            radius = max(6, int(min(cell_w, cell_h) * 0.35))
            pygame.draw.circle(surface, palette.get(item["kind"], self.theme.colors["accent"]), center, radius)
            pygame.draw.circle(surface, self.theme.colors["text"], center, max(2, radius // 3))

    def _draw_snake(self, surface: pygame.Surface, rect: pygame.Rect, cell_w: float, cell_h: float, snake: Iterable[Tuple[int, int]], color: Tuple[int, int, int], shielded: bool) -> None:
        for index, (col, row) in enumerate(snake):
            box = pygame.Rect(rect.x + col * cell_w + 2, rect.y + row * cell_h + 2, cell_w - 4, cell_h - 4)
            shade = tuple(clamp(channel - index * 6, 0, 255) for channel in color)
            pygame.draw.rect(surface, shade, box, border_radius=10)
            if index == 0:
                pygame.draw.rect(surface, self.theme.colors["text"], box.inflate(-box.width * 0.45, -box.height * 0.45), border_radius=6)
                if shielded:
                    pygame.draw.rect(surface, self.theme.colors["power_shield"], box.inflate(6, 6), 2, border_radius=12)

    def _draw_hud(self, surface: pygame.Surface, snapshot: Dict, local_player: str, spectator: bool) -> None:
        title = self.theme.fonts["title"].render("\u03A0thon Arena", True, self.theme.colors["text"])
        surface.blit(title, (36, 26))
        subtitle = "Spectator Mode" if spectator else f"Pilot: {local_player}"
        tag = self.theme.fonts["body"].render(subtitle, True, self.theme.colors["muted"])
        surface.blit(tag, (42, 66))

        timer = self.theme.fonts["small_title"].render(format_clock(snapshot.get("time_left", 0)), True, self.theme.colors["accent_soft"])
        surface.blit(timer, (surface.get_width() - 170, 30))

        scores = snapshot.get("scores", {})
        health = snapshot.get("health", {})
        buffs = snapshot.get("buffs", {})
        pauses_left = snapshot.get("pause_state", {}).get("pauses_left", {})
        left = 360
        for name in snapshot.get("players", []):
            label = self.theme.fonts["body"].render(
                f"{name}  Score {scores.get(name, 0)}  HP {health.get(name, 0)}",
                True,
                self.theme.colors["text"],
            )
            surface.blit(label, (left, 34))
            effects = []
            if buffs.get(name, {}).get("shield", 0) > 0:
                effects.append("Shield")
            if buffs.get(name, {}).get("boost", 0) > 0:
                effects.append("Boost")
            if effects:
                buff = self.theme.fonts["caption"].render(", ".join(effects), True, self.theme.colors["accent"])
                surface.blit(buff, (left, 60))
            pause_tag = self.theme.fonts["caption"].render(f"Pauses Left: {pauses_left.get(name, 3)}", True, self.theme.colors["warning"])
            surface.blit(pause_tag, (left, 82))
            left += 250

    def _draw_feed(self, surface: pygame.Surface, rect: pygame.Rect, snapshot: Dict) -> None:
        y = rect.y + 54
        announcements = list(snapshot.get("announcements", []))[-6:]
        for line in announcements:
            label = self.theme.fonts["caption"].render(line, True, self.theme.colors["accent_soft"])
            surface.blit(label, (rect.x + 18, y))
            y += 24

    def _draw_chat(self, surface: pygame.Surface, rect: pygame.Rect, chat_lines: Iterable[str]) -> None:
        y = rect.y + 48
        for line in list(chat_lines)[-2:]:
            label = self.theme.fonts["caption"].render(line[:96], True, self.theme.colors["text"])
            surface.blit(label, (rect.x + 18, y))
            y += 22
