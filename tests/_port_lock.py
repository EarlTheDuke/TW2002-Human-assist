"""Cross-process reservation of localhost ports used by tests.

`port_is_free` binds and then closes. Two tests can both see the same port as
free and then both listen on it. `claim_ports` records the choice under a
lock so the next claim skips it, even before the listener has bound.
"""

from __future__ import annotations

import fcntl
import json
import random
import threading
import time
from contextlib import contextmanager
from pathlib import Path

_THREAD = threading.Lock()
_PATH = Path("/tmp/tw2k-test-ports.lock")
_BOOK = Path("/tmp/tw2k-test-ports.json")
_HOLD_S = 180.0


@contextmanager
def port_lock():
    """One holder, in this process or another."""
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    with _THREAD, _PATH.open("a") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read() -> dict[str, float]:
    try:
        data = json.loads(_BOOK.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    now = time.time()
    return {k: float(v) for k, v in data.items() if float(v) > now}


def _write(data: dict[str, float]) -> None:
    _BOOK.write_text(json.dumps(data), encoding="utf-8")


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
