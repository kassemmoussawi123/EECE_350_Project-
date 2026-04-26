"""Screen classes for the pygame client."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

import pygame

from client.ui.widgets import Button, InputField, ListBox, Slider, Toggle, draw_paragraph
from shared.constants import MAP_CHOICES, MAX_TARGET_SCORE, SNAKE_SKINS, TARGET_SCORE_TO_WIN, USERNAME_MAX_LENGTH
from shared.helpers import clamp_target_score, parse_target_score, username_validation_error, valid_username


@dataclass
class BaseScreen:
    app: "GameClientApp"

    def on_enter(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        raise NotImplementedError


class SplashScreen(BaseScreen):
    def __init__(self, app: "GameClientApp") -> None:
        super().__init__(app)
        self.timer = 0.0
        self.continue_button = Button(pygame.Rect(540, 560, 200, 56), "Enter Arena", lambda: app.set_screen("menu"), app.theme)

    def handle_event(self, event: pygame.event.Event) -> None:
        self.continue_button.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.app.set_screen("menu")

    def update(self, dt: float) -> None:
        self.timer += dt

    def draw(self, surface: pygame.Surface) -> None:
        self.app.renderer.draw_background(surface, self.app.assets.get("background"), 70)
        glow = int(100 + 60 * (1 + math.sin(self.timer * 1.8)) / 2)
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((240, 146, 58, glow // 5))
        surface.blit(veil, (0, 0))
        self.continue_button.rect.centerx = surface.get_width() // 2
        self.continue_button.rect.y = 560
        hero = self.app.theme.fonts["hero"].render("\u03A0thon Arena", True, self.app.theme.colors["text"])
        tag = self.app.theme.fonts["small_title"].render("Networked Snake Battle", True, self.app.theme.colors["accent_soft"])
        surface.blit(hero, hero.get_rect(center=(surface.get_width() // 2, 250)))
        surface.blit(tag, tag.get_rect(center=(surface.get_width() // 2, 320)))
        draw_paragraph(surface, self.app.theme, "Choose your rival, tune your controls, and survive an authoritative client-server duel with chat, spectators, and arena blessings.", 300, 380, 680)
        self.continue_button.draw(surface)


class MainMenuScreen(BaseScreen):
    def __init__(self, app: "GameClientApp") -> None:
        super().__init__(app)
        self.menu_panel = pygame.Rect(96, 150, 330, 430)
        self.buttons = [
            Button(pygame.Rect(self.menu_panel.x + 30, self.menu_panel.y + 76 + i * 82, 270, 56), text, callback, app.theme)
            for i, (text, callback) in enumerate(
                [
                    ("Play", lambda: app.set_screen("connection")),
                    ("Settings", lambda: app.set_screen("settings")),
                    ("Help / How to Play", lambda: app.set_screen("help")),
                    ("Exit", app.request_quit),
                ]
            )
        ]

    def handle_event(self, event: pygame.event.Event) -> None:
        for button in self.buttons:
            button.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        self.app.renderer.draw_background(surface, self.app.assets.get("portrait"), 110)
        banner = self.app.theme.fonts["title"].render("\u03A0thon Arena", True, self.app.theme.colors["text"])
        subtitle = self.app.theme.fonts["caption"].render("Online Snake Battle", True, self.app.theme.colors["accent_soft"])
        surface.blit(banner, banner.get_rect(center=(surface.get_width() // 2, 56)))
        surface.blit(subtitle, subtitle.get_rect(center=(surface.get_width() // 2, 92)))
        self.app.renderer.draw_panel(surface, self.menu_panel, "Main Menu")
        for button in self.buttons:
            button.draw(surface)
        right = pygame.Rect(470, 132, 660, 448)
        self.app.renderer.draw_panel(surface, right, "Project Snapshot")
        text_end = draw_paragraph(surface, self.app.theme, "Two-player snake combat on a centralized server. The server owns movement, collisions, pies, power-ups, timing, and winner determination. Clients focus on rendering, input, and interface.", right.x + 26, right.y + 64, right.width - 52)
        text_end = draw_paragraph(surface, self.app.theme, "Advanced features include lobby chat, invite flow, spectator mode, live HUD, emoji reactions, and Arena Blessings power-ups that grant shield, boost, or drain effects.", right.x + 26, text_end + 16, right.width - 52)
        if self.app.assets.get("snake"):
            preview_frame = pygame.Rect(right.x + 126, max(right.y + 248, text_end + 22), 408, 170)
            pygame.draw.rect(surface, self.app.theme.colors["input"], preview_frame, border_radius=18)
            pygame.draw.rect(surface, self.app.theme.colors["panel_border"], preview_frame, 1, border_radius=18)
            snake = pygame.transform.smoothscale(self.app.assets["snake"], (376, 138))
            surface.blit(snake, snake.get_rect(center=preview_frame.center))


class ConnectionScreen(BaseScreen):
    def __init__(self, app: "GameClientApp") -> None:
        super().__init__(app)
        self.host = InputField(pygame.Rect(420, 220, 400, 48), app.theme, text=app.settings.data["connection"]["host"], placeholder="Server IP")
        self.port = InputField(pygame.Rect(420, 300, 400, 48), app.theme, text=str(app.settings.data["connection"]["port"]), placeholder="Port")
        self.username = InputField(pygame.Rect(420, 380, 400, 48), app.theme, text=app.settings.data["connection"]["username"], placeholder="Username")
        self.username.max_length = USERNAME_MAX_LENGTH
        self.buttons = [
            Button(pygame.Rect(420, 470, 180, 54), "Connect", self._connect, app.theme),
            Button(pygame.Rect(640, 470, 180, 54), "Back", lambda: app.set_screen("menu"), app.theme, accent="accent_2"),
        ]
        self.error = ""

    def _connect(self) -> None:
        self.error = ""
        try:
            port = int(self.port.text.strip())
        except ValueError:
            self.error = "Port must be numeric."
            return
        self.error = username_validation_error(self.username.text.strip())
        if self.error:
            return
        self.app.connect(self.host.text.strip() or "127.0.0.1", port, self.username.text.strip())

    def handle_event(self, event: pygame.event.Event) -> None:
        for field in (self.host, self.port, self.username):
            field.handle_event(event)
        for button in self.buttons:
            button.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._connect()

    def draw(self, surface: pygame.Surface) -> None:
        self.app.renderer.draw_background(surface, self.app.assets.get("background"), 110)
        self.buttons[0].disabled = not valid_username(self.username.text.strip())
        card = pygame.Rect(320, 120, 600, 500)
        self.app.renderer.draw_panel(surface, card, "Connection")
        for label, y in (("Server IP", 190), ("Port", 270), ("Username", 350)):
            text = self.app.theme.fonts["caption"].render(label, True, self.app.theme.colors["text"])
            surface.blit(text, (420, y))
        for field in (self.host, self.port, self.username):
            field.draw(surface)
        username_hint = self.app.theme.fonts["tiny"].render("3-12 characters: letters, numbers, underscore.", True, self.app.theme.colors["muted"])
        surface.blit(username_hint, (420, 435))
        for button in self.buttons:
            button.draw(surface)
        status = self.error or self.app.status_message
        if status:
            color = self.app.theme.colors["danger"] if self.error else self.app.theme.colors["accent_soft"]
            status_box = pygame.Rect(360, 520, 520, 92)
            pygame.draw.rect(surface, self.app.theme.colors["input"], status_box, border_radius=14)
            pygame.draw.rect(surface, color, status_box, 2, border_radius=14)
            icon = self.app.theme.fonts["small_title"].render("!", True, color)
            surface.blit(icon, icon.get_rect(center=(status_box.x + 28, status_box.y + 26)))
            title = self.app.theme.fonts["caption"].render("Connection Message", True, color)
            surface.blit(title, (status_box.x + 54, status_box.y + 12))
            draw_paragraph(surface, self.app.theme, status, status_box.x + 54, status_box.y + 36, status_box.width - 84)
        back_hint = self.app.theme.fonts["tiny"].render("Back returns to the main menu.", True, self.app.theme.colors["muted"])
        surface.blit(back_hint, (420, 605))


class LobbyScreen(BaseScreen):
    def __init__(self, app: "GameClientApp") -> None:
        super().__init__(app)
        self.refresh_timer = 0.0
        self.user_panel = pygame.Rect(40, 120, 300, 270)
        self.match_panel = pygame.Rect(360, 120, 320, 270)
        self.chat_panel = pygame.Rect(40, 420, 640, 210)
        self.user_list = ListBox(pygame.Rect(58, 168, 264, 198), app.theme)
        self.user_rows: list[dict] = []
        self.match_list = ListBox(pygame.Rect(378, 168, 284, 198), app.theme)
        self.chat_input = InputField(pygame.Rect(60, 570, 450, 40), app.theme, placeholder="Send a lobby message")
        self.private_input = InputField(pygame.Rect(742, 574, 328, 38), app.theme, placeholder="Private message")
        self.private_input.max_length = 120
        self.private_scroll = 0
        self.private_panel = pygame.Rect(700, 96, 460, 536)
        self.private_messages_rect = pygame.Rect(724, 170, 412, 348)
        self.private_minimize_rect = pygame.Rect(1082, 114, 24, 24)
        self.private_close_rect = pygame.Rect(1114, 114, 24, 24)
        self.private_send_rect = pygame.Rect(1082, 574, 58, 38)
        self.buttons = [
            Button(pygame.Rect(710, 150, 220, 48), "Invite Opponent", self._invite, app.theme),
            Button(pygame.Rect(710, 210, 220, 48), "Spectate Match", self._spectate, app.theme, accent="accent_2"),
            Button(pygame.Rect(710, 270, 220, 48), "Snake Setup", lambda: app.set_screen("customization"), app.theme),
            Button(pygame.Rect(710, 330, 220, 48), "Match Settings", lambda: app.set_screen("match_settings"), app.theme),
            Button(pygame.Rect(710, 390, 220, 48), "Refresh", app.request_lobby_refresh, app.theme, accent="accent_2"),
            Button(pygame.Rect(710, 450, 220, 48), "Disconnect", app.disconnect, app.theme, accent="danger"),
            Button(pygame.Rect(530, 570, 130, 40), "Send Chat", self._chat, app.theme),
        ]

    def on_enter(self) -> None:
        self.refresh_timer = 0.0
        self.app.request_lobby_refresh()

    def _invite(self) -> None:
        selected = self._selected_username()
        if not selected:
            return
        if self._selected_status() != "lobby":
            self.app.status_message = "Target player is busy."
            return
        self.app.send_invite(selected)

    def _spectate(self) -> None:
        selected = self.match_list.selected
        if not selected:
            return
        match_id = selected.split(" | ")[0]
        self.app.network.send({"type": "spectate_match", "match_id": match_id})

    def _chat(self) -> None:
        text = self.chat_input.text.strip()
        if text:
            self.app.network.send({"type": "send_lobby_chat", "text": text})
            self.chat_input.text = ""

    def _send_private(self) -> None:
        peer = self.app.private_chat_peer
        text = self.private_input.text.strip()
        if peer and text:
            self.app.send_private_message(peer, text)
            self.private_input.text = ""
            self.private_scroll = 0

    def handle_event(self, event: pygame.event.Event) -> None:
        if self._handle_private_chat_event(event):
            return
        clicked_user = self._clicked_username(event)
        self.user_list.handle_event(event)
        if clicked_user:
            self.app.open_private_chat(clicked_user)
            self.private_scroll = 0
            return
        self.match_list.handle_event(event)
        self.chat_input.handle_event(event)
        for button in self.buttons:
            button.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and self.chat_input.active:
            self._chat()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_y and self.app.incoming_inviter:
            self.app.network.send({"type": "respond_invite", "inviter": self.app.incoming_inviter, "accept": True})
            self.app.pending_invite_text = "Invite accepted. Waiting for match start..."
            self.app.awaiting_match_start = True
            self.app.request_lobby_refresh()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_n and self.app.incoming_inviter:
            self.app.network.send({"type": "respond_invite", "inviter": self.app.incoming_inviter, "accept": False})
            self.app.pending_invite_text = "Invite declined."
            self.app.awaiting_match_start = False
            self.app.incoming_inviter = ""
            self.app.request_lobby_refresh()

    def update(self, dt: float) -> None:
        # Poll lobby state regularly so other connected clients appear without manual refresh.
        self.refresh_timer += dt
        if self.refresh_timer >= 1.0:
            self.app.request_lobby_refresh()
            self.refresh_timer = 0.0
        self.user_rows = []
        for item in self.app.lobby_users:
            username = item["username"]
            if username == self.app.username:
                continue
            status = item.get("status", "lobby")
            status_label = self._status_label(status)
            self.user_rows.append({"username": username, "status": status, "status_label": status_label, "label": username})
        self.user_list.items = [item["label"] for item in self.user_rows]
        self.match_list.items = [
            f"{m['match_id']} | {' vs '.join(m['players'])} | {m.get('map', 'Desert')} | {m.get('target_score', TARGET_SCORE_TO_WIN)} pts"
            for m in self.app.active_matches
        ]

    def draw(self, surface: pygame.Surface) -> None:
        self.app.renderer.draw_background(surface, self.app.assets.get("background"), 115)
        self.app.renderer.draw_panel(surface, self.user_panel, "Online Users")
        self.user_list.draw(surface)
        self._draw_user_status_tags(surface)
        self._draw_private_badges(surface)
        self.app.renderer.draw_panel(surface, self.match_panel, "Live Matches")
        self.match_list.draw(surface)
        self.app.renderer.draw_panel(surface, self.chat_panel, "Lobby Chat")
        self.chat_input.draw(surface)
        users_count = self.app.theme.fonts["tiny"].render(f"{len(self.user_list.items)} online", True, self.app.theme.colors["muted"])
        matches_count = self.app.theme.fonts["tiny"].render(f"{len(self.match_list.items)} active", True, self.app.theme.colors["muted"])
        surface.blit(users_count, (self.user_panel.x + 178, self.user_panel.y + 18))
        surface.blit(matches_count, (self.match_panel.x + 196, self.match_panel.y + 18))
        for button in self.buttons:
            button.draw(surface)
        y = 468
        for line in self.app.lobby_messages[-4:]:
            label = self.app.theme.fonts["caption"].render(line[:68], True, self.app.theme.colors["text"])
            surface.blit(label, (60, y))
            y += 26
        status = self.app.pending_invite_text or self.app.status_message
        if self.app.incoming_inviter:
            status = f"{self.app.pending_invite_text} ({self.app.invite_seconds_left(incoming=True)}s)"
        if status:
            status_box = pygame.Rect(40, 72, 640, 40)
            pygame.draw.rect(surface, self.app.theme.colors["input"], status_box, border_radius=12)
            pygame.draw.rect(surface, self.app.theme.colors["accent_soft"], status_box, 1, border_radius=12)
            label = self.app.theme.fonts["tiny"].render(status[:92], True, self.app.theme.colors["accent_soft"])
            surface.blit(label, (54, 84))
        self._draw_private_chat(surface)

    def _selected_username(self) -> str:
        if not self.user_rows:
            return ""
        index = max(0, min(self.user_list.selected_index, len(self.user_rows) - 1))
        return self.user_rows[index]["username"]

    def _selected_status(self) -> str:
        if not self.user_rows:
            return ""
        index = max(0, min(self.user_list.selected_index, len(self.user_rows) - 1))
        return self.user_rows[index].get("status", "lobby")

    def _clicked_username(self, event: pygame.event.Event) -> str:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return ""
        if not self.user_list.rect.collidepoint(event.pos):
            return ""
        row = (event.pos[1] - self.user_list.rect.y - 12) // self.user_list.row_height
        if 0 <= row < len(self.user_rows):
            return self.user_rows[row]["username"]
        return ""

    def _handle_private_chat_event(self, event: pygame.event.Event) -> bool:
        peer = self.app.private_chat_peer
        if not peer:
            return False
        if self.app.private_chat_minimized:
            bar = pygame.Rect(self.private_panel.x, self.private_panel.bottom - 42, self.private_panel.width, 42)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and bar.collidepoint(event.pos):
                self.app.restore_private_chat()
                return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.private_close_rect.collidepoint(event.pos):
                self.app.close_private_chat()
                return True
            if self.private_minimize_rect.collidepoint(event.pos):
                self.app.minimize_private_chat()
                return True
            if self.private_send_rect.collidepoint(event.pos):
                self._send_private()
                return True
        if event.type == pygame.MOUSEWHEEL and self.private_messages_rect.collidepoint(pygame.mouse.get_pos()):
            history = self.app.private_chats.get(peer, [])
            max_scroll = max(0, len(history) - 10)
            self.private_scroll = max(0, min(max_scroll, self.private_scroll + event.y))
            return True
        if self.private_panel.collidepoint(pygame.mouse.get_pos()) or self.private_input.active:
            self.private_input.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and self.private_input.active:
                self._send_private()
                return True
            return event.type in {pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN, pygame.MOUSEWHEEL}
        return False

    def _draw_private_badges(self, surface: pygame.Surface) -> None:
        for index, row in enumerate(self.user_rows[:10]):
            unread = self.app.private_unread.get(row["username"], 0)
            if unread <= 0:
                continue
            row_rect = pygame.Rect(
                self.user_list.rect.x + 10,
                self.user_list.rect.y + 10 + index * self.user_list.row_height,
                self.user_list.rect.width - 20,
                self.user_list.row_height - 4,
            )
            badge_center = (row_rect.right - 42, row_rect.centery)
            pygame.draw.circle(surface, self.app.theme.colors["danger"], badge_center, 10)
            count = self.app.theme.fonts["tiny"].render(str(min(unread, 9)), True, self.app.theme.colors["text"])
            surface.blit(count, count.get_rect(center=badge_center))

    def _status_label(self, status: str) -> str:
        labels = {
            "lobby": "Online",
            "in_match": "In Match",
            "spectating": "Spectating",
            "offline": "Offline",
        }
        return labels.get(status, status.replace("_", " ").title())

    def _status_color(self, status: str) -> tuple[int, int, int]:
        colors = {
            "lobby": self.app.theme.colors["success"],
            "in_match": self.app.theme.colors["warning"],
            "spectating": self.app.theme.colors["accent_2"],
            "offline": self.app.theme.colors["muted"],
        }
        return colors.get(status, self.app.theme.colors["accent_soft"])

    def _draw_user_status_tags(self, surface: pygame.Surface) -> None:
        for index, row in enumerate(self.user_rows[:10]):
            row_rect = pygame.Rect(
                self.user_list.rect.x + 10,
                self.user_list.rect.y + 10 + index * self.user_list.row_height,
                self.user_list.rect.width - 20,
                self.user_list.row_height - 4,
            )
            status = row.get("status", "lobby")
            text = row.get("status_label", "Online")
            color = self._status_color(status)
            tag_width = 72 if status == "lobby" else 88 if status == "in_match" else 94
            tag = pygame.Rect(row_rect.right - tag_width - 10, row_rect.y + 6, tag_width, 20)
            pygame.draw.rect(surface, self.app.theme.colors["input"], tag, border_radius=8)
            pygame.draw.rect(surface, color, tag, 1, border_radius=8)
            dot = (tag.x + 10, tag.centery)
            pygame.draw.circle(surface, color, dot, 4)
            label = self.app.theme.fonts["tiny"].render(text, True, color)
            surface.blit(label, (tag.x + 18, tag.y + 3))

    def _draw_private_chat(self, surface: pygame.Surface) -> None:
        peer = self.app.private_chat_peer
        if not peer:
            return
        if self.app.private_chat_minimized:
            bar = pygame.Rect(self.private_panel.x, self.private_panel.bottom - 42, self.private_panel.width, 42)
            pygame.draw.rect(surface, self.app.theme.colors["panel"], bar, border_radius=14)
            pygame.draw.rect(surface, self.app.theme.colors["accent_2"], bar, 2, border_radius=14)
            unread = self.app.private_unread.get(peer, 0)
            suffix = f" ({unread})" if unread else ""
            label = self.app.theme.fonts["caption"].render(f"Private chat: {peer}{suffix}", True, self.app.theme.colors["text"])
            surface.blit(label, (bar.x + 18, bar.y + 11))
            return
        self.app.renderer.draw_panel(surface, self.private_panel, f"Private Chat: {peer}")
        for rect, text in ((self.private_minimize_rect, "-"), (self.private_close_rect, "x")):
            pygame.draw.rect(surface, self.app.theme.colors["input"], rect, border_radius=8)
            pygame.draw.rect(surface, self.app.theme.colors["panel_border"], rect, 1, border_radius=8)
            label = self.app.theme.fonts["caption"].render(text, True, self.app.theme.colors["text"])
            surface.blit(label, label.get_rect(center=rect.center))
        pygame.draw.rect(surface, self.app.theme.colors["input"], self.private_messages_rect, border_radius=12)
        pygame.draw.rect(surface, self.app.theme.colors["panel_border"], self.private_messages_rect, 1, border_radius=12)
        history = self.app.private_chats.get(peer, [])
        max_visible = 10
        max_scroll = max(0, len(history) - max_visible)
        self.private_scroll = max(0, min(max_scroll, self.private_scroll))
        end = len(history) - self.private_scroll
        start = max(0, end - max_visible)
        y = self.private_messages_rect.y + 12
        for entry in history[start:end]:
            timestamp = entry.get("timestamp", "")
            if entry.get("kind") == "status":
                line = f"[{timestamp}] {entry.get('text', '')}"
                color = self.app.theme.colors["warning"]
            else:
                line = f"[{timestamp}] {entry.get('sender', '')}: {entry.get('text', '')}"
                color = self.app.theme.colors["text"] if entry.get("sender") == self.app.username else self.app.theme.colors["accent_soft"]
            label = self.app.theme.fonts["tiny"].render(line[:72], True, color)
            surface.blit(label, (self.private_messages_rect.x + 12, y))
            y += 31
        hint = self.app.theme.fonts["tiny"].render("Mouse wheel scrolls history.", True, self.app.theme.colors["muted"])
        surface.blit(hint, (self.private_panel.x + 24, self.private_messages_rect.bottom + 10))
        self.private_input.draw(surface)
        pygame.draw.rect(surface, self.app.theme.colors["panel"], self.private_send_rect, border_radius=12)
        pygame.draw.rect(surface, self.app.theme.colors["accent"], self.private_send_rect, 2, border_radius=12)
        send_label = self.app.theme.fonts["tiny"].render("Send", True, self.app.theme.colors["text"])
        surface.blit(send_label, send_label.get_rect(center=self.private_send_rect.center))


class CustomizationScreen(BaseScreen):
    def __init__(self, app: "GameClientApp") -> None:
        super().__init__(app)
        # Layout constants keep spacing balanced without changing the screen logic.
        self.left_panel = pygame.Rect(80, 80, 360, 620)
        self.controls_panel = pygame.Rect(460, 80, 330, 620)
        self.preview_panel = pygame.Rect(820, 80, 320, 620)
        self.section_left = self.left_panel.x + 40
        self.controls_left = self.controls_panel.x + 40
        self.color_choices = ["Ember", "Azure", "Jade", "Onyx", "Gold"]
        selected_color = self.color_choices.index(app.profile["snake_color"].title()) if app.profile["snake_color"].title() in self.color_choices else 0
        self.color_list = ListBox(pygame.Rect(self.section_left, 208, 280, 184), app.theme, items=self.color_choices, selected_index=selected_color)
        selected_skin = SNAKE_SKINS.index(app.profile["snake_skin"]) if app.profile["snake_skin"] in SNAKE_SKINS else 0
        self.skin_list = ListBox(pygame.Rect(self.section_left, 458, 280, 110), app.theme, items=[skin.title() for skin in SNAKE_SKINS], selected_index=selected_skin)
        self.up = InputField(pygame.Rect(self.controls_left, 206, 210, 42), app.theme, text=app.controls["up"], placeholder="Up")
        self.down = InputField(pygame.Rect(self.controls_left, 294, 210, 42), app.theme, text=app.controls["down"], placeholder="Down")
        self.left = InputField(pygame.Rect(self.controls_left, 382, 210, 42), app.theme, text=app.controls["left"], placeholder="Left")
        self.right = InputField(pygame.Rect(self.controls_left, 470, 210, 42), app.theme, text=app.controls["right"], placeholder="Right")
        self.save_button = Button(pygame.Rect(self.section_left, 620, 130, 46), "Confirm", self._save, app.theme)
        self.back_button = Button(pygame.Rect(self.section_left + 150, 620, 130, 46), "Back", lambda: app.set_screen("lobby"), app.theme, accent="accent_2")

    def _save(self) -> None:
        self.app.profile["snake_color"] = self.color_list.selected.lower() or "ember"
        self.app.profile["snake_skin"] = self.skin_list.selected.lower() or "classic"
        self.app.controls.update(
            {
                "up": self.up.text.strip() or "w",
                "down": self.down.text.strip() or "s",
                "left": self.left.text.strip() or "a",
                "right": self.right.text.strip() or "d",
            }
        )
        self.app.push_profile()
        self.app.set_screen("lobby")

    def handle_event(self, event: pygame.event.Event) -> None:
        for field in (self.up, self.down, self.left, self.right):
            field.handle_event(event)
        # Keep selection state synchronized with the live preview.
        self.color_list.handle_event(event)
        self.skin_list.handle_event(event)
        self.app.profile["snake_color"] = self.color_list.selected.lower() or "ember"
        self.app.profile["snake_skin"] = self.skin_list.selected.lower() or "classic"
        self.save_button.handle_event(event)
        self.back_button.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        self.app.renderer.draw_background(surface, self.app.assets.get("portrait"), 110)
        self.app.renderer.draw_panel(surface, self.left_panel, "Snake Customization")
        self.app.renderer.draw_panel(surface, self.controls_panel, "Controls")
        self.app.renderer.draw_panel(surface, self.preview_panel, "Preview")
        for label, y in (("Snake Color", 172), ("Skin Style", 422)):
            text = self.app.theme.fonts["caption"].render(label, True, self.app.theme.colors["text"])
            surface.blit(text, (self.section_left, y))
        self.color_list.draw(surface)
        self.skin_list.draw(surface)
        for label, field in (("Up", self.up), ("Down", self.down), ("Left", self.left), ("Right", self.right)):
            text = self.app.theme.fonts["caption"].render(label, True, self.app.theme.colors["text"])
            surface.blit(text, (self.controls_left, field.rect.y - 30))
            field.draw(surface)
        self.save_button.draw(surface)
        self.back_button.draw(surface)
        self._draw_preview(surface, self.preview_panel)

    def _draw_preview(self, surface: pygame.Surface, preview: pygame.Rect) -> None:
        base_color = self.app.resolve_snake_color(self.color_list.selected.lower() or self.app.profile["snake_color"])
        selected_skin = self.skin_list.selected.lower() or "classic"
        size = 28 if selected_skin == "classic" else 30 if selected_skin == "viper" else 34
        for idx in range(5):
            segment = pygame.Rect(preview.x + 62 + idx * 34, preview.y + 224 + (idx % 2) * 8, size, 24 if selected_skin == "viper" else 28)
            pygame.draw.rect(surface, base_color, segment, border_radius=10)
        preview_title = self.app.theme.fonts["body"].render(self.skin_list.selected or self.app.profile["snake_skin"].title(), True, self.app.theme.colors["accent_soft"])
        surface.blit(preview_title, preview_title.get_rect(center=(preview.centerx, preview.y + 314)))
        info_box = pygame.Rect(preview.x + 42, preview.y + 364, 236, 126)
        pygame.draw.rect(surface, self.app.theme.colors["input"], info_box, border_radius=14)
        pygame.draw.rect(surface, self.app.theme.colors["panel_border"], info_box, 1, border_radius=14)
        info_title = self.app.theme.fonts["tiny"].render("Selected Setup", True, self.app.theme.colors["muted"])
        surface.blit(info_title, (info_box.x + 14, info_box.y + 10))
        color_chip = pygame.Rect(info_box.x + 14, info_box.y + 38, 18, 18)
        pygame.draw.rect(surface, base_color, color_chip, border_radius=5)
        color_label = self.app.theme.fonts["tiny"].render("Color", True, self.app.theme.colors["accent_soft"])
        surface.blit(color_label, (info_box.x + 44, info_box.y + 34))
        color_text = self.app.theme.fonts["caption"].render(self.color_list.selected, True, self.app.theme.colors["text"])
        surface.blit(color_text, (info_box.x + 44, info_box.y + 50))
        skin_label = self.app.theme.fonts["tiny"].render("Type", True, self.app.theme.colors["accent_soft"])
        surface.blit(skin_label, (info_box.x + 14, info_box.y + 82))
        skin_text = self.app.theme.fonts["caption"].render(self.skin_list.selected, True, self.app.theme.colors["text"])
        surface.blit(skin_text, (info_box.x + 14, info_box.y + 98))


class MatchSettingsScreen(BaseScreen):
    def __init__(self, app: "GameClientApp") -> None:
        super().__init__(app)
        selected_map = MAP_CHOICES.index(app.profile["map"]) if app.profile["map"] in MAP_CHOICES else 0
        self.panel = pygame.Rect(120, 56, 450, 664)
        self.hint_panel = pygame.Rect(620, 56, 500, 664)
        self.map_list = ListBox(pygame.Rect(160, 220, 280, 102), app.theme, items=list(MAP_CHOICES), selected_index=selected_map)
        self.duration_field = InputField(pygame.Rect(160, 378, 280, 46), app.theme, text=str(app.profile["duration"]), placeholder="Duration")
        self.target_field = InputField(pygame.Rect(160, 464, 280, 46), app.theme, text=str(app.profile["target_score"]), placeholder="Target Score")
        self.target_field.max_length = len(str(MAX_TARGET_SCORE))
        self.visual_field = InputField(pygame.Rect(160, 608, 280, 46), app.theme, text=app.profile["visual_mod"], placeholder="Visual Variation")
        self.save_button = Button(pygame.Rect(160, 666, 142, 42), "Confirm", self._save, app.theme)
        self.back_button = Button(pygame.Rect(318, 666, 122, 42), "Back", lambda: app.set_screen("lobby"), app.theme, accent="accent_2")

    def _sanitize_target_field(self) -> None:
        raw = "".join(ch for ch in self.target_field.text if ch.isdigit())
        if not raw:
            self.target_field.text = ""
            return
        self.target_field.text = str(clamp_target_score(int(raw)))

    def _save(self) -> None:
        try:
            duration = int(self.duration_field.text.strip())
        except ValueError:
            self.app.status_message = "Duration must be numeric."
            return
        target = parse_target_score(self.target_field.text)
        self.app.profile.update(
            {
                # Store the chosen map here before profile sync/network send.
                "map": self.map_list.selected or "Desert",
                "duration": duration,
                "target_score": target,
                "visual_mod": self.visual_field.text.strip() or "Classic Glow",
            }
        )
        if self.target_field.text.strip():
            self.target_field.text = str(target)
        self.app.push_profile()
        self.app.set_screen("lobby")

    def handle_event(self, event: pygame.event.Event) -> None:
        # Reflect the active map choice immediately in local screen state.
        self.map_list.handle_event(event)
        self.app.profile["map"] = self.map_list.selected or "Desert"
        for field in (self.duration_field, self.target_field, self.visual_field):
            field.handle_event(event)
        self._sanitize_target_field()
        self.save_button.handle_event(event)
        self.back_button.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        self.app.renderer.draw_background(surface, self.app.assets.get("background"), 120)
        self.app.renderer.draw_panel(surface, self.panel, "Match Settings")
        self.app.renderer.draw_panel(surface, self.hint_panel, "Map Preview")
        for label, y in (("Map", 184), ("Duration (minutes)", 346), ("Target Score", 432), ("Visual Variation", 576)):
            text = self.app.theme.fonts["caption"].render(label, True, self.app.theme.colors["text"])
            surface.blit(text, (160, y))
        self.map_list.draw(surface)
        selected_map_box = pygame.Rect(160, 330, 280, 28)
        pygame.draw.rect(surface, self.app.theme.colors["input"], selected_map_box, border_radius=10)
        pygame.draw.rect(surface, self.app.theme.colors["accent_soft"], selected_map_box, 1, border_radius=10)
        selected_map = self.app.theme.fonts["tiny"].render(f"Selected Map: {self.map_list.selected}", True, self.app.theme.colors["accent_soft"])
        surface.blit(selected_map, (174, 336))
        for field in (self.duration_field, self.target_field, self.visual_field):
            field.draw(surface)
        self.save_button.draw(surface)
        self.back_button.draw(surface)
        preview_map = self.map_list.selected or "Desert"
        map_previews = self.app.assets.get("map_previews", {})
        preview_surface = map_previews.get(preview_map) if isinstance(map_previews, dict) else None
        preview_box = pygame.Rect(self.hint_panel.x + 28, self.hint_panel.y + 56, 444, 252)
        pygame.draw.rect(surface, self.app.theme.colors["input"], preview_box, border_radius=18)
        pygame.draw.rect(surface, self.app.theme.colors["accent_soft"], preview_box, 1, border_radius=18)
        if preview_surface:
            surface.blit(preview_surface, (preview_box.x + 2, preview_box.y + 2))
        map_title = self.app.theme.fonts["title"].render(preview_map, True, self.app.theme.colors["accent_soft"])
        surface.blit(map_title, map_title.get_rect(center=(self.hint_panel.centerx, self.hint_panel.y + 356)))
        descriptions = {
            "Desert": "Warm dunes, earthy grid tones, and sandstone obstacle colors.",
            "Snow": "Icy scenery, cool board tones, and bright frosted object colors.",
            "Jungle": "Dense greenery, deep green board tones, and vivid natural accents.",
        }
        draw_paragraph(surface, self.app.theme, descriptions.get(preview_map, ""), self.hint_panel.x + 34, self.hint_panel.y + 392, self.hint_panel.width - 68)
        draw_paragraph(surface, self.app.theme, "The selected map is saved to your profile and sent to the server before matchmaking begins.", self.hint_panel.x + 34, self.hint_panel.y + 462, self.hint_panel.width - 68)
        target_note = pygame.Rect(160, 522, 280, 44)
        pygame.draw.rect(surface, self.app.theme.colors["input"], target_note, border_radius=12)
        pygame.draw.rect(surface, self.app.theme.colors["panel_border"], target_note, 1, border_radius=12)
        note_title = self.app.theme.fonts["tiny"].render("Score Limit", True, self.app.theme.colors["accent_soft"])
        note_body = self.app.theme.fonts["tiny"].render(f"Any value from 1 to {MAX_TARGET_SCORE}", True, self.app.theme.colors["muted"])
        surface.blit(note_title, (target_note.x + 12, target_note.y + 6))
        surface.blit(note_body, (target_note.x + 12, target_note.y + 22))


class MatchmakingScreen(BaseScreen):
    def __init__(self, app: "GameClientApp") -> None:
        super().__init__(app)
        self.timer = 0.0
        self.cancel_button = Button(pygame.Rect(540, 480, 200, 54), "Cancel Invite", self._cancel, app.theme, accent="danger")

    def _cancel(self) -> None:
        if self.app.pending_invite_target:
            self.app.network.send({"type": "cancel_invite", "target": self.app.pending_invite_target})
            self.app.pending_invite_target = ""
        self.app.set_screen("lobby")

    def handle_event(self, event: pygame.event.Event) -> None:
        self.cancel_button.handle_event(event)

    def update(self, dt: float) -> None:
        self.timer += dt

    def draw(self, surface: pygame.Surface) -> None:
        self.app.renderer.draw_background(surface, self.app.assets.get("background"), 120)
        panel = pygame.Rect(350, 180, 580, 280)
        self.app.renderer.draw_panel(surface, panel, "Waiting for Rival")
        dots = "." * (1 + int(self.timer * 2) % 3)
        title = self.app.theme.fonts["title"].render(f"Invite sent to {self.app.pending_invite_target}{dots}", True, self.app.theme.colors["text"])
        surface.blit(title, (390, 260))
        seconds_left = self.app.invite_seconds_left(incoming=False)
        waiting_text = self.app.pending_invite_text or "The lobby will update when your opponent responds."
        note = self.app.theme.fonts["caption"].render(f"{waiting_text} Expires in {seconds_left}s.", True, self.app.theme.colors["accent_soft"])
        surface.blit(note, (390, 320))
        self.cancel_button.draw(surface)


class SettingsScreen(BaseScreen):
    def __init__(self, app: "GameClientApp") -> None:
        super().__init__(app)
        ui = app.settings.data["ui"]
        self.music = Slider(pygame.Rect(150, 220, 320, 18), app.theme, 0, 100, ui["music_volume"], "Music")
        self.sfx = Slider(pygame.Rect(150, 320, 320, 18), app.theme, 0, 100, ui["sfx_volume"], "SFX")
        self.brightness = Slider(pygame.Rect(150, 420, 320, 18), app.theme, 50, 120, ui["brightness"], "Brightness")
        self.scale = Slider(pygame.Rect(150, 520, 320, 18), app.theme, 80, 120, ui["ui_scale"], "UI Scale")
        self.fullscreen = Toggle(pygame.Rect(620, 220, 220, 36), app.theme, ui["fullscreen"], "Fullscreen")
        self.mute = Toggle(pygame.Rect(620, 300, 220, 36), app.theme, ui["mute"], "Mute")
        self.apply_button = Button(pygame.Rect(620, 480, 170, 50), "Apply", self._apply, app.theme)
        self.cancel_button = Button(pygame.Rect(810, 480, 170, 50), "Cancel", self._cancel, app.theme, accent="accent_2")
        self.reset_button = Button(pygame.Rect(620, 550, 360, 50), "Reset", self._reset, app.theme, accent="danger")

    def _apply(self) -> None:
        self.app.settings.data["ui"].update(
            {
                "music_volume": self.music.value,
                "sfx_volume": self.sfx.value,
                "brightness": self.brightness.value,
                "ui_scale": self.scale.value,
                "fullscreen": self.fullscreen.value,
                "mute": self.mute.value,
            }
        )
        self.app.settings.save()
        self.app.apply_audio_volume()
        self.app.push_profile()
        self.app.set_screen("menu" if not self.app.connected else "lobby")

    def _cancel(self) -> None:
        self.app.set_screen("menu" if not self.app.connected else "lobby")

    def _reset(self) -> None:
        self.app.settings.reset_ui()
        self.__init__(self.app)

    def handle_event(self, event: pygame.event.Event) -> None:
        for widget in (self.music, self.sfx, self.brightness, self.scale, self.fullscreen, self.mute):
            widget.handle_event(event)
        for button in (self.apply_button, self.cancel_button, self.reset_button):
            button.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        self.app.renderer.draw_background(surface, self.app.assets.get("portrait"), 120)
        self.app.renderer.draw_panel(surface, pygame.Rect(100, 130, 1000, 520), "Settings")
        for widget in (self.music, self.sfx, self.brightness, self.scale, self.fullscreen, self.mute):
            widget.draw(surface)
        for button in (self.apply_button, self.cancel_button, self.reset_button):
            button.draw(surface)


class HelpScreen(BaseScreen):
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.set_screen("menu")

    def draw(self, surface: pygame.Surface) -> None:
        self.app.renderer.draw_background(surface, self.app.assets.get("background"), 120)
        panel = pygame.Rect(90, 90, 1020, 560)
        self.app.renderer.draw_panel(surface, panel, "How to Play")
        text = (
            "1. Connect to the server with a unique username.\n"
            "2. Adjust your snake color, skin, controls, and match preferences.\n"
            "3. Invite another user from the lobby or spectate an active match.\n"
            "4. During the match, move with your chosen keys and collect pies for score.\n"
            "5. Arena Blessings appear during battle. Shield blocks one crash, boost shortens your move interval, and drain weakens the opponent.\n"
            "6. First to the target score, last snake alive, or highest score when the timer expires wins."
        )
        y = 160
        for line in text.splitlines():
            label = self.app.theme.fonts["body"].render(line, True, self.app.theme.colors["text"])
            surface.blit(label, (130, y))
            y += 52
        hint = self.app.theme.fonts["caption"].render("Press Esc to return.", True, self.app.theme.colors["accent_soft"])
        surface.blit(hint, (130, 590))


class CreditsScreen(BaseScreen):
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.set_screen("menu")

    def draw(self, surface: pygame.Surface) -> None:
        self.app.renderer.draw_background(surface, self.app.assets.get("portrait"), 130)
        panel = pygame.Rect(280, 120, 640, 480)
        self.app.renderer.draw_panel(surface, panel, "Credits")
        lines = [
            "Project: Πthon Arena",
            "Course: EECE 350 Computing Networks",
            "Architecture: Python, Pygame, sockets, threads, JSON lines",
            "Original uploaded code: preserved and refactored into modular client/server flow",
            "Team members: Replace with final team names and IDs",
            "Assets: Uploaded screenshots and images reorganized for presentation",
        ]
        y = 190
        for line in lines:
            label = self.app.theme.fonts["body"].render(line, True, self.app.theme.colors["text"])
            surface.blit(label, (320, y))
            y += 52


class EndGameScreen(BaseScreen):
    def __init__(self, app: "GameClientApp") -> None:
        super().__init__(app)
        self.play_again_button = Button(pygame.Rect(420, 460, 170, 52), "Play Again", self._play_again, app.theme)
        self.back_button = Button(pygame.Rect(620, 460, 170, 52), "Back to Lobby", lambda: app.set_screen("lobby"), app.theme, accent="accent_2")

    def _play_again(self) -> None:
        if self.app.last_opponent:
            self.app.send_invite(self.app.last_opponent)

    def handle_event(self, event: pygame.event.Event) -> None:
        self.play_again_button.handle_event(event)
        self.back_button.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        self.app.renderer.draw_background(surface, self.app.assets.get("background"), 120)
        panel = pygame.Rect(340, 180, 540, 320)
        self.app.renderer.draw_panel(surface, panel, "Match Result")
        summary = self.app.match_result or {"winner": "Unknown", "scores": {}}
        winner = self.app.theme.fonts["title"].render(f"Winner: {summary['winner']}", True, self.app.theme.colors["accent_soft"])
        surface.blit(winner, (390, 250))
        target_value = self.app.match_snapshot.get("target_score", self.app.profile.get("target_score", TARGET_SCORE_TO_WIN))
        target = self.app.theme.fonts["caption"].render(f"Winning Score: {target_value}", True, self.app.theme.colors["muted"])
        surface.blit(target, (390, 294))
        if self.app.status_message:
            status = self.app.theme.fonts["caption"].render(self.app.status_message[:52], True, self.app.theme.colors["accent_soft"])
            surface.blit(status, (390, 320))
        y = 352
        for player, score in summary.get("scores", {}).items():
            label = self.app.theme.fonts["body"].render(f"{player}: {score}", True, self.app.theme.colors["text"])
            surface.blit(label, (390, y))
            y += 40
        self.play_again_button.draw(surface)
        self.back_button.draw(surface)


class GameScreen(BaseScreen):
    def __init__(self, app: "GameClientApp") -> None:
        super().__init__(app)
        self.chat_input = InputField(pygame.Rect(60, 640, 760, 40), app.theme, placeholder="Match chat")
        ui = app.settings.data["ui"]
        self.pause_button = Button(pygame.Rect(1010, 24, 150, 42), "Pause / Settings", self._toggle_pause, app.theme, accent="accent_2")
        self.resume_button = Button(pygame.Rect(440, 560, 220, 42), "Return to Game", self._resume_game, app.theme)
        self.quit_button = Button(pygame.Rect(680, 560, 220, 42), "Quit Match", self._open_leave_confirmation, app.theme, accent="danger")
        self.music_slider = Slider(pygame.Rect(452, 364, 300, 18), app.theme, 0, 100, ui["music_volume"], "Music")
        self.sfx_slider = Slider(pygame.Rect(452, 426, 300, 18), app.theme, 0, 100, ui["sfx_volume"], "SFX")
        self.mute_toggle = Toggle(pygame.Rect(452, 468, 300, 36), app.theme, ui["mute"], "Mute")
        self.confirm_leave = False

    def on_enter(self) -> None:
        ui = self.app.settings.data["ui"]
        self.music_slider.value = ui["music_volume"]
        self.sfx_slider.value = ui["sfx_volume"]
        self.mute_toggle.value = ui["mute"]
        self.confirm_leave = False

    def _toggle_pause(self) -> None:
        if self.app.match_snapshot.get("pause_state", {}).get("is_paused"):
            self.app.network.send({"type": "resume_pause"})
        else:
            self.app.network.send({"type": "request_pause"})

    def _resume_game(self) -> None:
        self.confirm_leave = False
        self.app.network.send({"type": "resume_pause"})

    def _open_leave_confirmation(self) -> None:
        self.confirm_leave = True

    def _sync_audio_controls(self) -> None:
        self.app.update_audio_settings(
            music=self.music_slider.value,
            sfx=self.sfx_slider.value,
            mute=self.mute_toggle.value,
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.app.match_snapshot.get("pause_state", {}).get("is_paused"):
                self.confirm_leave = False
                self.app.network.send({"type": "resume_pause"})
            else:
                self.app.network.send({"type": "request_pause"})
            return
        self.pause_button.handle_event(event)
        paused = self.app.match_snapshot.get("pause_state", {}).get("is_paused", False)
        if paused:
            self.resume_button.handle_event(event)
            self.quit_button.handle_event(event)
            self.music_slider.handle_event(event)
            self.sfx_slider.handle_event(event)
            self.mute_toggle.handle_event(event)
            self._sync_audio_controls()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                self.confirm_leave = True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                self.mute_toggle.value = not self.mute_toggle.value
                self._sync_audio_controls()
            elif self.confirm_leave and event.type == pygame.KEYDOWN and event.key == pygame.K_y:
                self.confirm_leave = False
                self.app.leave_match()
            elif self.confirm_leave and event.type == pygame.KEYDOWN and event.key == pygame.K_n:
                self.confirm_leave = False
            return
        self.chat_input.handle_event(event)
        if event.type == pygame.KEYDOWN:
            if self.chat_input.active:
                if event.key == pygame.K_RETURN and self.chat_input.text.strip():
                    self.app.network.send({"type": "send_match_chat", "text": self.chat_input.text.strip()})
                    self.chat_input.text = ""
                return
            action = self.app.key_to_action(event.key)
            if action:
                self.app.network.send({"type": "action", "action": action})
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                emoji = {pygame.K_1: "🔥", pygame.K_2: "🛡", pygame.K_3: "😵"}[event.key]
                self.app.network.send({"type": "emoji_reaction", "emoji": emoji})

    def draw(self, surface: pygame.Surface) -> None:
        paused = self.app.match_snapshot.get("pause_state", {}).get("is_paused", False)
        self.app.renderer.draw_game(surface, self.app.match_snapshot, self.app.username, self.app.assets, False, self.app.match_chat, paused)
        self.pause_button.draw(surface)
        self.chat_input.draw(surface)
        if paused:
            panel = pygame.Rect(surface.get_width() // 2 - 250, surface.get_height() // 2 - 190, 500, 380)
            self.music_slider.draw(surface)
            self.sfx_slider.draw(surface)
            self.mute_toggle.draw(surface)
            controls_title = self.app.theme.fonts["caption"].render("Controls", True, self.app.theme.colors["accent_soft"])
            surface.blit(controls_title, (panel.x + 30, panel.y + 116))
            controls = [
                f"Up: {self.app.controls['up'].upper()}",
                f"Down: {self.app.controls['down'].upper()}",
                f"Left: {self.app.controls['left'].upper()}",
                f"Right: {self.app.controls['right'].upper()}",
                "Chat: Enter",
                "Pause: Esc",
            ]
            for index, line in enumerate(controls):
                label = self.app.theme.fonts["tiny"].render(line, True, self.app.theme.colors["text"])
                col = index // 3
                row = index % 3
                surface.blit(label, (panel.x + 30 + col * 150, panel.y + 146 + row * 24))
            for button in (self.resume_button, self.quit_button):
                button.draw(surface)
            if self.confirm_leave:
                confirm_box = pygame.Rect(panel.x + 70, panel.y + 250, 360, 74)
                pygame.draw.rect(surface, self.app.theme.colors["input"], confirm_box, border_radius=14)
                pygame.draw.rect(surface, self.app.theme.colors["danger"], confirm_box, 2, border_radius=14)
                label = self.app.theme.fonts["caption"].render("Leave match and return to lobby? Y = Yes, N = No", True, self.app.theme.colors["text"])
                surface.blit(label, (confirm_box.x + 18, confirm_box.y + 26))


class SpectatorScreen(BaseScreen):
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.network.send({"type": "leave_spectate"})
            self.app.set_screen("lobby")

    def draw(self, surface: pygame.Surface) -> None:
        self.app.renderer.draw_game(surface, self.app.match_snapshot, self.app.username, self.app.assets, True, self.app.match_chat, False)
