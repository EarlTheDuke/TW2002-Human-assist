"""Start the rendered-screen player for one lobby seat.

The child is `scripts/ai_cockpit_player.py`. It receives the same seat link a
person would open. This module does not pass engine objects, harness routes,
or a key on the command line. The stored switch stays legacy, so a caller
that has not turned AI_COCKPIT_SEAT_MODE on gets None and no process.
"""

from __future__ import annotations

import logging
import subprocess
import sys
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


def player_script() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "scripts" / "ai_cockpit_player.py"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("scripts/ai_cockpit_player.py")


def launch_player(
    *,
    base_url: str,
    gid: str,
    seat: str,
    token: str,
    run_dir: Path,
    provider: str = "scripted",
    max_turns: int = 40,
    min_interval: float = 1.0,
    python: str | None = None,
    popen=subprocess.Popen,
):
    """Spawn the browser player when the cockpit-seat switch is on.

    Returns None while AI_COCKPIT_SEAT_MODE is legacy. The log line names the
    seat and the provider. It does not include the token or an API key.
    """
    if not K.ai_cockpit_seat_on():
        return None
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    url = base_url.rstrip("/") + cockpit_seat_url(gid, seat, token)
    cmd = [
        python or sys.executable,
        str(player_script()),
        "--url", url,
        "--provider", provider,
        "--run-dir", str(run_dir),
        "--max-turns", str(int(max_turns)),
        "--min-interval", str(float(min_interval)),
    ]
    # The seat link has to reach the child. The log names the seat only.
    log.info("ai cockpit player seat=%s provider=%s", seat, provider)
    return popen(cmd)
