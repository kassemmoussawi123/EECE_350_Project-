"""Network client handling the shared protocol."""

from __future__ import annotations

import queue
import socket
import threading
from typing import Dict, Optional

from shared.messages import MessageReader, recv_available, send_message


class NetworkClient:
    """Threaded TCP client with a message queue."""

    def __init__(self) -> None:
        self.socket: Optional[socket.socket] = None
        self.reader = MessageReader()
        self.queue: "queue.Queue[Dict]" = queue.Queue()
        self.running = False
        self.connected = False
        self._receiver: Optional[threading.Thread] = None
        self._send_lock = threading.Lock()

    def connect(self, host: str, port: int) -> None:
        self.disconnect()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        sock.settimeout(0.1)
        self.socket = sock
        self.connected = True
        self.running = True
        self._receiver = threading.Thread(target=self._recv_loop, daemon=True)
        self._receiver.start()

    def disconnect(self) -> None:
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass
        self.socket = None

    def send(self, message: Dict) -> None:
        if not self.socket or not self.connected:
            return
        with self._send_lock:
            try:
                send_message(self.socket, message)
            except OSError:
                self.queue.put({"type": "connection_closed", "reason": "send_failed"})
                self.disconnect()

    def poll(self) -> list[Dict]:
        messages: list[Dict] = []
        while True:
            try:
                messages.append(self.queue.get_nowait())
            except queue.Empty:
                return messages

    def _recv_loop(self) -> None:
        assert self.socket is not None
        while self.running and self.socket:
            try:
                chunk = recv_available(self.socket)
                if chunk is None:
                    continue
                if chunk == b"":
                    self.queue.put({"type": "connection_closed", "reason": "server_disconnected"})
                    break
                for message in self.reader.feed(chunk):
                    self.queue.put(message)
            except OSError:
                self.queue.put({"type": "connection_closed", "reason": "recv_failed"})
                break
        self.disconnect()
