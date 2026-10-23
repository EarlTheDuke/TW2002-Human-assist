"""_ephemeral_port skips a block that would run past port 65535."""

from contextlib import contextmanager
import socket

import tests._port_lock as port_lock_mod
from tests import _cu_host


class _FakeSock:
    handed = [65534, 40000]

    def __init__(self, *a, **k):
        self.port = None

    def bind(self, addr):
        port = addr[1]
        if port == 0:
            port = _FakeSock.handed.pop(0)
        if port > 65535:
            raise OverflowError("bind(): port must be 0-65535.")
        self.port = port

    def getsockname(self):
        return ("127.0.0.1", self.port)

    def close(self):
        pass


def test_block_near_top_is_skipped(monkeypatch):
    book = {}

    @contextmanager
    def fake_lock():
        yield

    monkeypatch.setattr(port_lock_mod, "port_lock", fake_lock)
    monkeypatch.setattr(port_lock_mod, "_read", lambda: dict(book))
    monkeypatch.setattr(port_lock_mod, "_write", lambda t: book.update(t))
    monkeypatch.setattr(socket, "socket", _FakeSock)
    _FakeSock.handed = [65534, 40000]

    assert _cu_host._ephemeral_port(count=4) == 40000
    assert set(book) == {"40000", "40001", "40002", "40003"}
