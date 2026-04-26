"""Music playback helpers for the pygame client."""

from __future__ import annotations

import math
from pathlib import Path
import struct

import pygame


class SoundManager:
    """Small music manager with safe fallbacks for missing or unsupported files."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.enabled = pygame.mixer.get_init() is not None
        self.fade_ms = 500
        self.current_track = ""
        self.current_context = ""
        self.last_error = ""
        sounds_dir = self.root / "assets" / "sounds"
        self.tracks = {
            "lobby": sounds_dir / "lobby_music.mp3",
            "battle": sounds_dir / "battle_music.mp3",
        }

    def sync_for_screen(self, screen_name: str) -> None:
        if screen_name in {"game", "spectator"}:
            self.play_track("battle")
            return
        if screen_name in {"splash", "menu", "connection", "lobby", "customization", "match_settings", "matchmaking", "settings", "help", "credits", "endgame"}:
            self.play_track("lobby")
            return
        self.stop()

    def play_track(self, track_name: str) -> None:
        if not self.enabled:
            return
        path = self.tracks.get(track_name)
        if not path or not path.exists():
            self.last_error = f"Missing audio file: {path.name if path else track_name}"
            return
        if self.current_track == track_name and pygame.mixer.music.get_busy():
            return
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(self.fade_ms)
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play(-1, fade_ms=self.fade_ms)
            self.current_track = track_name
            self.last_error = ""
        except pygame.error as exc:
            self.last_error = f"Audio playback unavailable for {path.name}: {exc}"
            self.current_track = ""

    def apply_volume(self, volume: float) -> None:
        if not self.enabled:
            return
        pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))

    def play_private_notification(self, volume: float) -> None:
        if not self.enabled:
            return
        try:
            frequency, sample_format, channels = pygame.mixer.get_init()
            sample_count = max(1, int(frequency * 0.08))
            amplitude = int(9000 * max(0.0, min(1.0, volume)))
            frames = bytearray()
            for index in range(sample_count):
                envelope = 1.0 - (index / sample_count)
                sample = int(amplitude * envelope * math.sin(2 * math.pi * 880 * index / frequency))
                packed = struct.pack("<h", sample)
                for _ in range(channels):
                    frames.extend(packed)
            pygame.mixer.Sound(buffer=bytes(frames)).play()
        except (pygame.error, ValueError, TypeError, struct.error):
            pass

    def stop(self) -> None:
        if not self.enabled:
            return
        try:
            pygame.mixer.music.fadeout(self.fade_ms)
        except pygame.error:
            pass
        self.current_track = ""
