"""Shared JSON-line message encoding and decoding."""

from __future__ import annotations

import json
import socket
from typing import Dict, List


class MessageReader:
    def __init__(self) -> None:
        self.buffer = ""

    def feed(self, chunk: bytes) -> List[Dict]:
        self.buffer += chunk.decode("utf-8")
        messages: List[Dict] = []
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if not line.strip():
                continue
            messages.append(json.loads(line))
        return messages


def send_message(sock: socket.socket, payload: Dict) -> None:
    data = json.dumps(payload, separators=(",", ":")) + "\n"
    sock.sendall(data.encode("utf-8"))


def recv_available(sock: socket.socket) -> bytes | None:
    try:
        return sock.recv(4096)
    except TimeoutError:
        return None
    except socket.timeout:
        return None
