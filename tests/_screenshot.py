"""Screenshot writes that survive a full pipe.

A viewport child is started with its output captured. Playwright's driver
pipe is non-blocking, and a long run fills it. The next screenshot then
raises BlockingIOError (Errno 11) instead of waiting. Put stdio back into
blocking mode, and retry the write.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path


def force_blocking_stdio() -> None:
    """Clear O_NONBLOCK on stdout and stderr when the parent left a pipe."""
    try:
        import fcntl
    except ImportError:
        return
    for stream in (sys.stdout, sys.stderr):
        try:
            fd = stream.fileno()
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        except (OSError, ValueError, AttributeError):
            continue
        if flags & os.O_NONBLOCK:
            fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)


def _again(exc: BaseException) -> bool:
    if isinstance(exc, BlockingIOError):
        return True
    text = f"{type(exc).__name__}: {exc}"
    return "BlockingIOError" in text or "EAGAIN" in text


def save_screenshot(page, dest: Path, *, attempts: int = 8) -> None:
    """Write one PNG, retrying when the driver pipe returns EAGAIN.

    The bytes come back from the page, then land in a sibling ``.png``.
    Playwright rejects a ``.part`` suffix, and a full pipe raises
    BlockingIOError on the write. The sibling is replaced onto dest only
    after the bytes are on disk.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    last: BaseException | None = None
    data: bytes | None = None
    for attempt in range(attempts):
        part = dest.with_name(f"{dest.stem}.{os.getpid()}.{attempt}.png")
        try:
            if data is None:
                data = page.screenshot(type="png")
            part.write_bytes(data)
            os.replace(part, dest)
            return
        except Exception as exc:
            if not _again(exc):
                raise
            last = exc
            time.sleep(0.05 * (attempt + 1))
        finally:
            if part.exists():
                try:
                    part.unlink()
                except OSError:
                    pass
    if last is not None:
        raise last
    raise BlockingIOError(11, "screenshot was not written")
