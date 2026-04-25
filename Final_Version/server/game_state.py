"""Authoritative server-side match state."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from shared.constants import GRID_HEIGHT, GRID_WIDTH, MAPS, MAX_MATCH_CHAT, POWERUP_TYPES
from shared.helpers import clamp, clamp_target_score


Cell = Tuple[int, int]


@dataclass
class Match:
    match_id: str
    players: List[str]
    profiles: Dict[str, Dict]
    spectators: set[str] = field(default_factory=set)
    pies: List[Cell] = field(default_factory=list)
    powerups: List[Dict] = field(default_factory=list)
    announcements: List[str] = field(default_factory=list)
    chat_log: List[str] = field(default_factory=list)
    end_reason: str = ""
    left_player: str = ""

    def __post_init__(self) -> None:
        # The inviter's saved profile is the authoritative source for the match map.
        game_map = self.profiles[self.players[0]]["profile"]["map"]
        duration = int(self.profiles[self.players[0]]["profile"]["duration"])
        target = clamp_target_score(self.profiles[self.players[0]]["profile"]["target_score"])
        self.map_name = game_map if game_map in MAPS else "Desert"
        self.palette = MAPS[self.map_name]["palette"]
        self.obstacles = list(MAPS[self.map_name]["obstacles"])
        self.target_score = target
        self.time_left = duration * 60.0
        self.snakes = {
            self.players[0]: [(4, GRID_HEIGHT // 2), (3, GRID_HEIGHT // 2), (2, GRID_HEIGHT // 2)],
            self.players[1]: [(GRID_WIDTH - 5, GRID_HEIGHT // 2), (GRID_WIDTH - 4, GRID_HEIGHT // 2), (GRID_WIDTH - 3, GRID_HEIGHT // 2)],
        }
        self.directions = {self.players[0]: (1, 0), self.players[1]: (-1, 0)}
        self.pending_directions = self.directions.copy()
        self.move_timers = {player: 0.0 for player in self.players}
        self.health = {player: 100 for player in self.players}
        self.scores = {player: 0 for player in self.players}
        self.alive = {player: True for player in self.players}
        self.buffs = {player: {"shield": 0.0, "boost": 0.0} for player in self.players}
        self.snake_colors = {player: self._resolve_color(self.profiles[player]["profile"].get("snake_color", "ember")) for player in self.players}
        self.spawn_timer = 0.0
        self.paused = False
        self.paused_by = ""
        self.pause_remaining = 0.0
        self.pauses_left = {player: 3 for player in self.players}
        self.over = False
        self.winner = ""
        for _ in range(6):
            self.pies.append(self._random_open_cell())
        self.announcements.append(f"{self.players[0]} vs {self.players[1]} started on {self.map_name}.")

    def apply_action(self, player: str, action: str) -> None:
        if player not in self.players:
            return
        lookup = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
        if action in lookup:
            proposed = lookup[action]
            current = self.directions[player]
            if proposed != (-current[0], -current[1]):
                self.pending_directions[player] = proposed

    def request_pause(self, player: str) -> None:
        if self.over or self.paused or player not in self.players:
            return
        if self.pauses_left[player] <= 0:
            self.announcements.append(f"{player} has no pauses left.")
            self.announcements[:] = self.announcements[-6:]
            return
        self.paused = True
        self.paused_by = player
        self.pause_remaining = 30.0
        self.pauses_left[player] -= 1
        self.announcements.append(f"{player} paused the match.")
        self.announcements[:] = self.announcements[-6:]

    def resume_pause(self, player: str) -> None:
        if not self.paused:
            return
        self.paused = False
        self.paused_by = ""
        self.pause_remaining = 0.0
        self.announcements.append(f"{player} resumed the match.")
        self.announcements[:] = self.announcements[-6:]

    def add_chat(self, line: str) -> None:
        self.chat_log.append(line)
        self.chat_log[:] = self.chat_log[-MAX_MATCH_CHAT:]

    def add_reaction(self, player: str, emoji: str) -> None:
        self.chat_log.append(f"{player} reacted {emoji}")
        self.chat_log[:] = self.chat_log[-MAX_MATCH_CHAT:]

    def step(self, dt: float, connected_players: set[str]) -> None:
        if self.over:
            return
        if self.paused:
            self.pause_remaining = max(0.0, self.pause_remaining - dt)
            if self.pause_remaining <= 0:
                self.paused = False
                self.paused_by = ""
                self.pause_remaining = 0.0
                self.announcements.append("Pause time expired. Match resumed.")
                self.announcements[:] = self.announcements[-6:]
            return
        self.time_left = max(0.0, self.time_left - dt)
        self.spawn_timer += dt
        for player in self.players:
            self.buffs[player]["shield"] = max(0.0, self.buffs[player]["shield"] - dt)
            self.buffs[player]["boost"] = max(0.0, self.buffs[player]["boost"] - dt)
            self.move_timers[player] += dt
        if self.spawn_timer >= 8.0 and len(self.powerups) < 2:
            self.spawn_timer = 0.0
            self.powerups.append({"position": self._random_open_cell(), "kind": random.choice(POWERUP_TYPES)})
            self.announcements.append("An Arena Blessing materialized.")
            self.announcements[:] = self.announcements[-6:]

        for player in self.players:
            if not self.alive[player]:
                continue
            interval = 0.14 if self.buffs[player]["boost"] > 0 else 0.18
            if self.move_timers[player] < interval:
                continue
            self.move_timers[player] = 0.0
            self.directions[player] = self.pending_directions[player]
            self._advance_player(player)

        for player in self.players:
            if player not in connected_players:
                self.over = True
                self.winner = self._other(player)
                self.announcements.append(f"{player} disconnected.")

        alive = [player for player in self.players if self.alive[player]]
        if len(alive) == 1:
            self.over = True
            self.winner = alive[0]
            return
        if not alive:
            self.over = True
            self.winner = max(self.players, key=lambda name: self.scores[name])
            return
        if self.time_left <= 0:
            self.over = True
            self.winner = max(alive, key=lambda name: self.scores[name])

    def snapshot(self) -> Dict:
        return {
            "match_id": self.match_id,
            "players": self.players,
            "map": self.map_name,
            "map_palette": self.palette,
            "obstacles": self.obstacles,
            "pies": self.pies,
            "powerups": self.powerups,
            "snakes": self.snakes,
            "scores": self.scores,
            "health": self.health,
            "alive": self.alive,
            "time_left": self.time_left,
            "target_score": self.target_score,
            "announcements": self.announcements[-6:],
            "snake_colors": self.snake_colors,
            "buffs": self.buffs,
            "pause_state": {
                "is_paused": self.paused,
                "paused_by": self.paused_by,
                "pause_remaining": self.pause_remaining,
                "pauses_left": self.pauses_left,
            },
        }

    def _advance_player(self, player: str) -> None:
        snake = self.snakes[player]
        dx, dy = self.directions[player]
        head_x, head_y = snake[0]
        new_head = (head_x + dx, head_y + dy)
        grow = False
        if new_head[0] < 0 or new_head[0] >= GRID_WIDTH or new_head[1] < 0 or new_head[1] >= GRID_HEIGHT:
            self._apply_collision(player, 14)
            return
        if new_head in snake[1:]:
            self._apply_collision(player, 16)
            return
        for other in self.players:
            if other != player and new_head in self.snakes[other]:
                if self.buffs[player]["shield"] > 0:
                    self.buffs[player]["shield"] = 0.0
                    self.announcements.append(f"{player}'s shield absorbed a crash.")
                else:
                    self._apply_collision(player, 18)
                return
        if new_head in self.obstacles:
            if self.buffs[player]["shield"] > 0:
                self.buffs[player]["shield"] = 0.0
                self.announcements.append(f"{player}'s shield blocked an obstacle hit.")
            else:
                self._apply_collision(player, 12)
            return
        snake.insert(0, new_head)
        if new_head in self.pies:
            self.pies.remove(new_head)
            self.pies.append(self._random_open_cell())
            self.scores[player] += 10
            self.health[player] = min(100, self.health[player] + 6)
            grow = True
        pickup = next((item for item in self.powerups if item["position"] == new_head), None)
        if pickup:
            self.powerups.remove(pickup)
            self._apply_powerup(player, pickup["kind"])
            self.scores[player] += 8
            grow = True
        if not grow:
            snake.pop()

    def _apply_powerup(self, player: str, kind: str) -> None:
        opponent = self._other(player)
        if kind == "shield":
            self.buffs[player]["shield"] = 8.0
            self.announcements.append(f"{player} gained a shield.")
        elif kind == "boost":
            self.buffs[player]["boost"] = 6.0
            self.announcements.append(f"{player} accelerated.")
        elif kind == "drain":
            self.health[opponent] = max(0, self.health[opponent] - 18)
            self.scores[player] += 5
            self.announcements.append(f"{player} drained {opponent}.")
            if self.health[opponent] <= 0:
                self.alive[opponent] = False
                self.over = True
                self.winner = player
        self.announcements[:] = self.announcements[-6:]

    def _apply_collision(self, player: str, damage: int) -> None:
        self.health[player] = max(0, self.health[player] - damage)
        self.scores[player] = max(0, self.scores[player] - 6)
        if self.health[player] <= 0:
            self.alive[player] = False
            self.over = True
            self.winner = self._other(player)
            self.announcements.append(f"{player} has been eliminated.")
        else:
            self.announcements.append(f"{player} crashed and lost momentum.")
        self.announcements[:] = self.announcements[-6:]

    def _random_open_cell(self) -> Cell:
        occupied = set(self.obstacles)
        for snake in self.snakes.values():
            occupied.update(snake)
        occupied.update(self.pies)
        occupied.update(item["position"] for item in self.powerups)
        while True:
            candidate = (random.randint(1, GRID_WIDTH - 2), random.randint(1, GRID_HEIGHT - 2))
            if candidate not in occupied:
                return candidate

    def _other(self, username: str) -> str:
        return next(player for player in self.players if player != username)

    def _resolve_color(self, name: str) -> Tuple[int, int, int]:
        palette = {
            "ember": (238, 126, 68),
            "azure": (80, 180, 255),
            "jade": (99, 208, 143),
            "onyx": (122, 132, 150),
            "gold": (235, 196, 84),
        }
        return palette.get(name.lower(), (238, 126, 68))
