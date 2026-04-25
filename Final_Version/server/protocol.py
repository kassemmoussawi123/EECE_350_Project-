"""Socket session helpers."""

from __future__ import annotations

import socket
import threading
from dataclasses import dataclass, field

from shared.messages import MessageReader, send_message


@dataclass
class ClientSession:
    socket: socket.socket
    address: tuple[str, int]
    username: str = ""
    reader: MessageReader = field(default_factory=MessageReader)
    alive: bool = True
    send_lock: threading.Lock = field(default_factory=threading.Lock)

    def send(self, payload: dict) -> None:
        with self.send_lock:
            send_message(self.socket, payload)

    def close(self) -> None:
        self.alive = False
        try:
            self.socket.close()
        except OSError:
            pass
