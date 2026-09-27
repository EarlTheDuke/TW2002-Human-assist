"""Per-seat claim links - seat login without pasting secrets (grokbot-player G3).

The host writes one link per external seat to ``.tw2k/seat_links/<seat>.txt``
(gitignored, like ``spectator_link.txt``)::

    {base}/bot/claim?seat=P6&token=<seat token>

Opening it once sets an HttpOnly ``tw2k_seat_<SEAT>`` cookie scoped to
``/harness/`` and redirects to ``/bot?seat=P6&mode=cu``. The cockpit's harness
calls then authenticate with that cookie instead of a pasted bearer token;
the cookie carries the same per-seat token, so seat scope is unchanged.

Base URL resolution: ``TW2K_PUBLIC_BASE_URL`` > ``.tw2k/public_base_url.txt``
(written by the tunnel scripts) > ``TW2K_HARNESS_BASE_URL`` (the CLI sets it
to the bound port) > ``http://127.0.0.1:8000``. Quick-tunnel URLs change, so
re-run ``scripts/write_seat_links.py`` after re-exposing.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import quote

from .harness_tokens import _repo_root

ENV_DIR = "TW2K_SEAT_LINKS_DIR"
CLAIM_PATH = "/bot/claim"
COOKIE_PREFIX = "tw2k_seat_"
COOKIE_PATH = "/harness/"
# Browsers send this on cookie-authenticated writes; a cross-site form or
# fetch cannot set it without a CORS preflight the server never grants.
CSRF_HEADER = "x-tw2k-seat"


def cookie_name(player_id: str) -> str:
    return f"{COOKIE_PREFIX}{player_id.upper()}"


def links_dir(explicit: str | os.PathLike[str] | None = None) -> Path:
    raw = explicit or os.environ.get(ENV_DIR) or ""
    return Path(raw).expanduser() if raw else _repo_root() / ".tw2k" / "seat_links"


def base_url() -> str:
    env = (os.environ.get("TW2K_PUBLIC_BASE_URL") or "").strip()
    if env:
        return env.rstrip("/")
    try:
        public = (_repo_root() / ".tw2k" / "public_base_url.txt").read_text(encoding="utf-8").strip()
    except OSError:
        public = ""
    if public:
        return public.rstrip("/")
    harness = (os.environ.get("TW2K_HARNESS_BASE_URL") or "").strip()
    return harness.rstrip("/") if harness else "http://127.0.0.1:8000"


def claim_url(base: str, seat: str, token: str) -> str:
    return f"{base.rstrip('/')}{CLAIM_PATH}?seat={quote(seat.upper())}&token={quote(token, safe='')}"


def write_seat_links(
    tokens: Mapping[str, str],
    *,
    base: str | None = None,
    directory: str | os.PathLike[str] | None = None,
) -> dict[str, Path]:
    """Write ``<dir>/<SEAT>.txt`` (one claim URL each). Returns the paths written."""
    out_dir = links_dir(directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    root = base or base_url()
    written: dict[str, Path] = {}
    for seat, token in sorted(tokens.items()):
        if not token:
            continue
        path = out_dir / f"{seat.upper()}.txt"
        path.write_text(claim_url(root, seat, token) + "\n", encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        written[seat.upper()] = path
    return written


def cookie_token(cookies: Mapping[str, str], player_id: str | None = None) -> str:
    """Seat token from the claim cookies.

    With ``player_id``: that seat's cookie if present, else any other seat's
    cookie (so the caller answers 403 "wrong seat" rather than 401).
    """
    if player_id:
        tok = cookies.get(cookie_name(player_id))
        if tok:
            return tok.strip()
    for name in sorted(cookies):
        if name.startswith(COOKIE_PREFIX) and cookies[name]:
            return cookies[name].strip()
    return ""
