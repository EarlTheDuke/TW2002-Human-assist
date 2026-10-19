"""Cross-process reservation of localhost ports used by tests.

`port_is_free` binds and then closes. Two tests can both see the same port as
free and then both listen on it. `claim_ports` records the choice under a
lock so the next claim skips it, even before the listener has bound.

The lock file lives in the system temp directory. POSIX takes it with
`fcntl.flock`. Windows takes it with `msvcrt.locking`. `fcntl` is imported
only on POSIX, because Windows has no such module.
"""

from __future__ import annotations

import json
import os
import random
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

_THREAD = threading.Lock()
_DIR = Path(tempfile.gettempdir())
_PATH = _DIR / "tw2k-test-ports.lock"
_BOOK = _DIR / "tw2k-test-ports.json"
_HOLD_S = 180.0
_LOCK_WAIT_S = 120.0


def _open_lock():
    """Binary, unbuffered handle. Windows cannot lock a text-mode file."""
    _DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(os.fspath(_PATH), os.O_RDWR | os.O_CREAT, 0o666)
    return os.fdopen(fd, "r+b", buffering=0)


def _lock_byte(handle) -> None:
    """One locked byte. An empty file cannot be locked on Windows."""
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)


def _acquire(handle) -> None:
    if os.name == "nt":
        import msvcrt

        _lock_byte(handle)
        deadline = time.time() + _LOCK_WAIT_S
        while True:
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                if time.time() >= deadline:
                    raise TimeoutError("could not lock the test port book") from None
                time.sleep(0.05)
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _release(handle) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def port_lock():
    """One holder, in this process or another."""
    with _THREAD:
        handle = _open_lock()
        try:
            _acquire(handle)
            try:
                yield
            finally:
                _release(handle)
        finally:
            handle.close()


def _read() -> dict[str, float]:
    try:
        data = json.loads(_BOOK.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    now = time.time()
    return {k: float(v) for k, v in data.items() if float(v) > now}


def _write(data: dict[str, float]) -> None:
    tmp = _BOOK.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, _BOOK)


def claim_ports(n: int, *, low: int, high: int, avoid: set[int] | None = None, sequential: bool = False) -> int:
    """Return the base of `n` free ports in [low, high) and reserve them."""
    from tw2k.public.config import port_is_free

    avoid = avoid or set()
    if high - low < n:
        raise RuntimeError("port window is smaller than the block")
    rng = random.Random()
    with port_lock():
        taken = _read()
        reserved = {int(k) for k in taken}
        if sequential:
            candidates = range(low, high - n + 1)
        else:
            candidates = [rng.randrange(low, high - n + 1) for _ in range(400)]
        for base in candidates:
            ports = range(base, base + n)
            if any(p in avoid or p in reserved for p in ports):
                continue
            if all(port_is_free(p) for p in ports):
                until = time.time() + _HOLD_S
                for p in ports:
                    taken[str(p)] = until
                _write(taken)
                return base
    raise RuntimeError(f"no free port block of {n} in {low}-{high - 1}")


def release_ports(*ports: int) -> None:
    """Drop a claim once the listener has stopped, so the window can be reused."""
    if not ports:
        return
    with port_lock():
        data = _read()
        for port in ports:
            data.pop(str(int(port)), None)
        _write(data)
