"""Reusable widgets for screen composition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, List

import pygame

from client.ui.theme import Theme


Callback = Callable[[], None]


@dataclass
class Button:
    rect: pygame.Rect
    text: str
    on_click: Callback
    theme: Theme
    accent: str = "accent"
    disabled: bool = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.disabled:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.on_click()

    def draw(self, surface: pygame.Surface) -> None:
        color = self.theme.colors["hover"] if self.rect.collidepoint(pygame.mouse.get_pos()) else self.theme.colors["panel"]
        if self.disabled:
            color = (45, 50, 58)
        pygame.draw.rect(surface, color, self.rect, border_radius=16)
        pygame.draw.rect(surface, self.theme.colors[self.accent], self.rect, 2, border_radius=16)
        label = self.theme.fonts["body"].render(self.text, True, self.theme.colors["text"])
        surface.blit(label, label.get_rect(center=self.rect.center))


@dataclass
class InputField:
    rect: pygame.Rect
    theme: Theme
    text: str = ""
    placeholder: str = ""
    active: bool = False
    max_length: int = 24

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        if not self.active:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                return
            elif len(self.text) < self.max_length and event.unicode.isprintable():
                self.text += event.unicode

    def draw(self, surface: pygame.Surface) -> None:
        color = self.theme.colors["hover"] if self.active else self.theme.colors["input"]
        pygame.draw.rect(surface, color, self.rect, border_radius=14)
        pygame.draw.rect(surface, self.theme.colors["accent_2"] if self.active else self.theme.colors["panel_border"], self.rect, 2, border_radius=14)
        shown = self.text or self.placeholder
        text_color = self.theme.colors["text"] if self.text else self.theme.colors["muted"]
        label = self.theme.fonts["caption"].render(shown, True, text_color)
        surface.blit(label, (self.rect.x + 14, self.rect.y + 12))


@dataclass
class Slider:
    rect: pygame.Rect
    theme: Theme
    minimum: int
    maximum: int
    value: int
    label: str
    dragging: bool = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.dragging = True
            self._update_value(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_value(event.pos[0])

    def _update_value(self, x: int) -> None:
        ratio = (x - self.rect.x) / max(1, self.rect.width)
        ratio = max(0.0, min(1.0, ratio))
        self.value = round(self.minimum + ratio * (self.maximum - self.minimum))

    def draw(self, surface: pygame.Surface) -> None:
        label = self.theme.fonts["caption"].render(f"{self.label}: {self.value}", True, self.theme.colors["text"])
        surface.blit(label, (self.rect.x, self.rect.y - 26))
        pygame.draw.rect(surface, self.theme.colors["panel"], self.rect, border_radius=12)
        fill = self.rect.copy()
        fill.width = int(self.rect.width * ((self.value - self.minimum) / max(1, (self.maximum - self.minimum))))
        pygame.draw.rect(surface, self.theme.colors["accent"], fill, border_radius=12)


@dataclass
class Toggle:
    rect: pygame.Rect
    theme: Theme
    value: bool
    label: str

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.value = not self.value

    def draw(self, surface: pygame.Surface) -> None:
        label = self.theme.fonts["caption"].render(self.label, True, self.theme.colors["text"])
        surface.blit(label, (self.rect.x, self.rect.y + 4))
        pill = pygame.Rect(self.rect.right - 70, self.rect.y, 70, self.rect.height)
        pygame.draw.rect(surface, self.theme.colors["success"] if self.value else self.theme.colors["panel"], pill, border_radius=18)
        knob = pygame.Rect(0, 0, 28, 28)
        knob.centery = pill.centery
        knob.centerx = pill.right - 18 if self.value else pill.left + 18
        pygame.draw.circle(surface, self.theme.colors["text"], knob.center, 14)


@dataclass
class ListBox:
    rect: pygame.Rect
    theme: Theme
    items: List[str] = field(default_factory=list)
    selected_index: int = 0
    hovered_index: int = -1
    row_height: int = 32

    @property
    def selected(self) -> str:
        if not self.items:
            return ""
        self.selected_index = max(0, min(self.selected_index, len(self.items) - 1))
        return self.items[self.selected_index]

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.hovered_index = -1
            if self.rect.collidepoint(event.pos):
                row = (event.pos[1] - self.rect.y - 12) // self.row_height
                if 0 <= row < len(self.items):
                    self.hovered_index = row
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            row = (event.pos[1] - self.rect.y - 12) // self.row_height
            if 0 <= row < len(self.items):
                self.selected_index = row
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN and self.items:
                self.selected_index = min(len(self.items) - 1, self.selected_index + 1)
            elif event.key == pygame.K_UP and self.items:
                self.selected_index = max(0, self.selected_index - 1)

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, self.theme.colors["input"], self.rect, border_radius=14)
        pygame.draw.rect(surface, self.theme.colors["panel_border"], self.rect, 2, border_radius=14)
        for index, item in enumerate(self.items[:10]):
            row = pygame.Rect(self.rect.x + 10, self.rect.y + 10 + index * self.row_height, self.rect.width - 20, self.row_height - 4)
            # Keep selection styling visual only: highlight, border, and a small check icon.
            if index == self.selected_index:
                pygame.draw.rect(surface, self.theme.colors["accent"], row, border_radius=10)
                inner = row.inflate(-2, -2)
                pygame.draw.rect(surface, self.theme.colors["hover"], inner, border_radius=9)
                pygame.draw.rect(surface, self.theme.colors["accent_soft"], inner, 1, border_radius=9)
            elif index == self.hovered_index:
                pygame.draw.rect(surface, self.theme.colors["hover"], row, border_radius=8)
            label = self.theme.fonts["caption"].render(item[:42], True, self.theme.colors["text"])
            surface.blit(label, (row.x + 12, row.y + 4))
            if index == self.selected_index:
                check = self.theme.fonts["caption"].render("✓", True, self.theme.colors["accent_soft"])
                surface.blit(check, (row.right - 18, row.y + 3))


def draw_paragraph(surface: pygame.Surface, theme: Theme, text: str, x: int, y: int, width: int) -> int:
    words = text.split()
    line = ""
    line_height = theme.fonts["caption"].get_height() + 6
    current_y = y
    for word in words:
        candidate = f"{line} {word}".strip()
        if theme.fonts["caption"].size(candidate)[0] > width and line:
            label = theme.fonts["caption"].render(line, True, theme.colors["muted"])
            surface.blit(label, (x, current_y))
            current_y += line_height
            line = word
        else:
            line = candidate
    if line:
        label = theme.fonts["caption"].render(line, True, theme.colors["muted"])
        surface.blit(label, (x, current_y))
        current_y += line_height
    return current_y
