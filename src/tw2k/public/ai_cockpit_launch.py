"""Start the rendered-screen player for one lobby seat.

The child is `scripts/ai_cockpit_player.py`. It receives the same seat link a
person would open. This module does not pass engine objects, harness routes,
or a key on the command line. The stored switch stays legacy, so a caller
that has not turned AI_COCKPIT_SEAT_MODE on gets None and no process.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import quote

from ..engine import constants as K

log = logging.getLogger(__name__)


def cockpit_seat_url(gid: str, seat: str, token: str) -> str:
    """The normal cockpit link: mode=cu and the redesign layout."""
    return (
        f"/g/{quote(gid, safe='')}/bot?seat={quote(seat, safe='')}"
        f"&mode=cu&token={quote(token, safe='')}&layout=redesign"
    )


def direct_seat_url(seat: str, token: str) -> str:
    """The worker's own cockpit path. The lobby proxies the public link above."""
    return (
        f"/bot?seat={quote(seat, safe='')}"
        f"&mode=cu&token={quote(token, safe='')}&layout=redesign"
    )


def status_line(provider: str, model: str, running: bool, *, seat: str = "", level: str = "") -> str:
    """Lobby text for one seat. It names the provider and whether the process is up.

    ``seat`` and ``level`` are omitted when empty, so a single scripted seat still
    reads "AI cockpit seat: scripted, running".
    """
    extra = f" {model}" if model else ""
    state = "running" if running else "stopped"
    who = f" {seat}" if seat else ""
    rank = f" {level}" if level else ""
    return f"AI cockpit seat{who}: {provider}{extra}{rank}, {state}"


def player_script() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "scripts" / "ai_cockpit_player.py"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("scripts/ai_cockpit_player.py")


def _append(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip("\n") + "\n")


def port_is_ready(base_url: str, timeout_s: float = 20) -> bool:
    """True once the worker answers /healthz.

    The lobby's health check can return before this process is spawned.
    A second look here is the gap where the child used to open a dead port,
    exit, and leave no log for the seat folder the test was not reading.
    """
    url = base_url.rstrip("/") + "/healthz"
    deadline = time.monotonic() + max(0.0, timeout_s)
    while True:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if int(getattr(resp, "status", 200) or 200) < 500:
                    return True
        except Exception:
            pass
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.25)


def launch_player(
    *,
    base_url: str,
    gid: str,
    seat: str,
    token: str,
    run_dir: Path,
    provider: str = "scripted",
    model: str = "",
    level: str = "",
    max_turns: int = 40,
    min_interval: float = 1.0,
    path: str | None = None,
    python: str | None = None,
    popen=subprocess.Popen,
):
    """Spawn the browser player when the cockpit-seat switch is on.

    Returns None while AI_COCKPIT_SEAT_MODE is legacy. The log line names the
    seat, the provider, and the model. It does not include the token or an API key.
    ``path`` defaults to the public lobby link. The lobby passes the worker's
    ``/bot`` path so the child does not need a lobby cookie.
    """
    if not K.ai_cockpit_seat_on():
        return None
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "player.log"
    # Written and closed before the child starts, so Windows can open the
    # same path. The child appends; the parent does not keep the handle.
    _append(log_path, f"spawned seat={seat}")
    url = base_url.rstrip("/") + (path or cockpit_seat_url(gid, seat, token))
    if popen is subprocess.Popen and not port_is_ready(base_url):
        _append(log_path, "worker port was not answering; starting anyway")
    cmd = [
        python or sys.executable,
        str(player_script()),
        "--url", url,
        "--provider", provider,
        "--run-dir", str(run_dir),
        "--max-turns", str(int(max_turns)),
        "--min-interval", str(float(min_interval)),
    ]
    if model:
        cmd.extend(["--model", model])
    if level:
        cmd.extend(["--level", level])
    # The seat link has to reach the child. The log names the seat only.
    log.info(
        "ai cockpit player seat=%s provider=%s model=%s level=%s",
        seat, provider, model or "-", level or "hard",
    )
    # stderr goes to player.err, a different file from player.log, so the
    # child can append the log on Windows without a sharing violation.
    # A windowless parent (the merge box) has no console for the child to
    # inherit; the same flags the game worker uses keep that from killing
    # the process before it can write.
    flags: dict = {}
    if os.name == "nt":
        flags["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        flags["start_new_session"] = True
    err = open(run_dir / "player.err", "ab", buffering=0)
    try:
        proc = popen(
            cmd,
            cwd=str(run_dir),
            stdin=subprocess.DEVNULL,
            stdout=err,
            stderr=subprocess.STDOUT,
            **flags,
        )
    except Exception:
        _append(log_path, "the player process did not start")
        raise
    finally:
        err.close()
    return proc
