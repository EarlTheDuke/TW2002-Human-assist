"""The worker side of the beta: what a `tw2k serve` started by the lobby adds.

Every piece reads its own env value and does nothing when that value is unset:

* ``TW2K_SWITCH_OVERLAY`` - JSON ``{"V311_PROFILE": "v311", ...}`` set on ``constants`` at start.
* ``TW2K_PUBLIC_MODE=1`` - only the cockpit, the claim link, the player manual, the harness,
  static files, the health route and the (token-gated) spectator routes answer; ``/control/*``,
  ``/api/*`` and every other route answer only a loopback call carrying ``TW2K_LOBBY_SECRET``.
* ``TW2K_BASE_PATH=/g/<id>`` - pages, claim cookies and redirects work under the lobby prefix.
* ``TW2K_BRAND`` - the player-facing name on the cockpit and spectator pages.
* ``TW2K_SNAPSHOT_DIR`` - the game is snapshotted on every day roll, again once play has
  moved on, and every 5 minutes while it is quiet.
* ``TW2K_RESUME_SNAPSHOT`` - the game starts from that snapshot instead of a new universe.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from starlette.requests import Request

ENV_PUBLIC_MODE = "TW2K_PUBLIC_MODE"
ENV_LOBBY_SECRET = "TW2K_LOBBY_SECRET"
ENV_BASE_PATH = "TW2K_BASE_PATH"
ENV_BRAND = "TW2K_BRAND"
ENV_SWITCH_OVERLAY = "TW2K_SWITCH_OVERLAY"
ENV_SNAPSHOT_DIR = "TW2K_SNAPSHOT_DIR"
ENV_RESUME = "TW2K_RESUME_SNAPSHOT"
LOBBY_HEADER = "x-tw2k-lobby"

SNAPSHOT_EVERY_S = 300.0
SNAPSHOT_MOVE_GAP_S = 2.0
SNAPSHOT_KEEP = 3
CORRUPT_SAVE = "This game's save could not be read, so it was not started again."

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_BASE_RE = re.compile(r"^/g/[a-z0-9][a-z0-9-]{0,39}$")
_SWITCH_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,60}$")
_SWITCH_VALUE_RE = re.compile(r"^[a-z0-9_]{1,32}$")
OVERLAY_EXTRA = frozenset({"V311_PROFILE"})

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def public_mode() -> bool:
    return _env(ENV_PUBLIC_MODE).lower() in ("1", "true", "yes")


def lobby_secret() -> str:
    return _env(ENV_LOBBY_SECRET)


def base_path() -> str:
    raw = _env(ENV_BASE_PATH).rstrip("/")
    if raw and not _BASE_RE.match(raw):
        raise ValueError(f"{ENV_BASE_PATH} must look like /g/<id>, not {raw!r}")
    return raw


def brand() -> str:
    raw = _env(ENV_BRAND)
    if len(raw) > 40 or any(ch in raw for ch in "<>&\"'`$\\"):
        raise ValueError(f"{ENV_BRAND} must be plain text of 40 characters or fewer")
    return raw


# --------------------------------------------------------------------------- switches


def health_payload(runner) -> dict[str, Any]:
    """What the lobby reads from /healthz.

    A finished engine names the winner even while the scheduler is still
    unwinding a held turn. The day number stays the engine's day.
    """
    from ..engine import constants as K

    u = runner.state.universe
    spec = getattr(runner, "_spec", None)
    override = getattr(getattr(spec, "config", None), "starting_credits_override", None)
    turns_override = getattr(getattr(spec, "config", None), "turns_per_day_override", None)
    seat = next(iter(u.players.values()), None) if u is not None else None
    original_turns = int(seat.turns_per_day) if seat is not None else K.opening_original_turns()
    engine_done = bool(u is not None and getattr(u, "finished", False))
    winner = None
    reason = None
    if u is not None and (engine_done or runner.state.status == "finished"):
        reason = str(getattr(u, "win_reason", "") or "") or None
        wid = getattr(u, "winner_id", None)
        if wid and wid in u.players:
            winner = u.players[wid].name
    return {
        "ok": True,
        "status": runner.state.status,
        "day": int(u.day) if u is not None else None,
        "finished": runner.state.status == "finished" or engine_done,
        "holding_for_human": bool(getattr(runner, "_hold_until_human", False)),
        "starting_credits": K.starting_credits_line(override, K.opening_original_credits()),
        "turns_per_day": K.turns_per_day_line(turns_override, original_turns),
        "winner": winner,
        "win_reason": reason,
    }


def apply_playtest_clock_nudge() -> None:
    """Read PLAYTEST_CLOCK_NUDGE_MODE. Only ``on`` flips the switch. Unset stays legacy."""
    from ..engine import constants as K

    raw = os.environ.get("PLAYTEST_CLOCK_NUDGE_MODE", "").strip().lower()
    if raw == "on":
        K.PLAYTEST_CLOCK_NUDGE_MODE = "on"


def apply_switch_overlay(raw: str | None = None) -> dict[str, str]:
    """Set the per-game switches named in ``TW2K_SWITCH_OVERLAY`` (only ``*_MODE`` and
    ``V311_PROFILE`` names that exist and hold a string). Returns what was set."""
    from ..engine import constants as K

    text = _env(ENV_SWITCH_OVERLAY) if raw is None else raw.strip()
    if not text:
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{ENV_SWITCH_OVERLAY} must be a JSON object")
    applied: dict[str, str] = {}
    for name, value in data.items():
        if not isinstance(name, str) or not _SWITCH_NAME_RE.match(name):
            raise ValueError(f"{ENV_SWITCH_OVERLAY}: bad switch name {name!r}")
        if not (name.endswith("_MODE") or name in OVERLAY_EXTRA):
            raise ValueError(f"{ENV_SWITCH_OVERLAY}: {name} is not a switch")
        if not isinstance(getattr(K, name, None), str):
            raise ValueError(f"{ENV_SWITCH_OVERLAY}: no string switch named {name}")
        if not isinstance(value, str) or not _SWITCH_VALUE_RE.match(value):
            raise ValueError(f"{ENV_SWITCH_OVERLAY}: bad value for {name}")
        setattr(K, name, value)
        applied[name] = value
    return applied


# --------------------------------------------------------------------------- public lock

# The routes a seated player or a spectator needs. The spectator ones stay behind the
# spectator gate (TW2K_SPECTATOR_TOKEN); the harness checks the seat token itself.
OPEN_EXACT = frozenset({"/", "/bot", "/bot/claim", "/manual", "/healthz", "/spectate",
                        "/state", "/events", "/history", "/highlights", "/ws"})
OPEN_PREFIXES = ("/static/", "/harness/v1/")


def _headers(scope: Scope) -> dict[str, str]:
    return {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []}


def from_lobby(scope: Scope) -> bool:
    """A loopback call that carries the lobby secret."""
    secret = lobby_secret()
    client = (scope.get("client") or ("", 0))[0]
    presented = _headers(scope).get(LOBBY_HEADER, "")
    return bool(secret) and client in _LOOPBACK and bool(presented) and hmac.compare_digest(
        presented.encode("utf-8"), secret.encode("utf-8"))


def is_open_path(path: str) -> bool:
    return path in OPEN_EXACT or path.startswith(OPEN_PREFIXES)


class PublicLock:
    """TW2K_PUBLIC_MODE: everything outside the open list answers only the lobby."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        path = scope.get("path") or "/"
        if is_open_path(path) or from_lobby(scope):
            await self.app(scope, receive, send)
            return
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        body = b'{"detail":"not available in this game"}'
        await send({"type": "http.response.start", "status": 404,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode("latin-1"))]})
        await send({"type": "http.response.body", "body": body})


# --------------------------------------------------------------------------- page rewrite

_TEXT_TYPES = ("text/html", "javascript", "text/css")
_APP_JS_PATH = re.compile(r"""(["'`])/((?:state|events|history|highlights|bot)(?=[?"'`/])|control/|api/|static/)""")
_TAGLINE = re.compile(r"TradeWars 2002 .{1,3} AI Exhibition Match")
_SPECTATOR_TITLE = re.compile(r"<title>TW2K-AI .{1,3} Spectator</title>")
BRAND_LINE = "inspired by the classic BBS space-trading games"
TITLE_FRAME_OLD = "  TRADE WARS 2002     "


def _frame(name: str) -> str:
    inner = len(TITLE_FRAME_OLD)
    text = name.upper()[:inner - 2]
    return text.center(inner)


def _prefix_quoted_roots(text: str, base: str, roots: tuple[str, ...]) -> str:
    """Prefix root-absolute paths in quotes, including backtick template strings."""
    if not base:
        return text
    for quote in ('"', "'", "`"):
        for root in roots:
            text = text.replace(f"{quote}{root}", f"{quote}{base}{root}")
    return text


def _prefix_ws_host(text: str, base: str) -> str:
    """Keep the page host, and put the lobby prefix on the websocket path."""
    if not base:
        return text
    for marker in ("${location.host}/ws", "${window.location.host}/ws"):
        swapped = marker.replace("/ws", base + "/ws", 1)
        if swapped not in text:
            text = text.replace(marker, swapped)
    return text


def rewrite_text(path: str, text: str, *, base: str, brand_name: str) -> str:
    """The prefix and the brand for one served page or script (no-op with both unset)."""
    from .share_url import rewrite_embedded_urls

    name = path.rsplit("/", 1)[-1].split("?", 1)[0]
    is_html = path in ("/", "/bot", "/bot2", "/play", "/manual") or name.endswith(".html")
    if base:
        if is_html:
            for attr in ('src="/', 'href="/', 'action="/'):
                text = text.replace(attr, attr[:-1] + base + "/")
        elif name.endswith(".js"):
            text = _prefix_quoted_roots(text, base, ("/harness/", "/static/"))
            text = _prefix_ws_host(text, base)
            if name in ("app.js", "play.js"):
                text = _APP_JS_PATH.sub(lambda m: f"{m.group(1)}{base}/{m.group(2)}", text)
        elif name.endswith(".css"):
            for opener in ("url(/static/", 'url("/static/', "url('/static/"):
                text = text.replace(opener, opener.replace("/static/", f"{base}/static/"))
    if brand_name:
        if is_html:
            text = text.replace("<title>Trade Wars 2002</title>", f"<title>{brand_name}</title>")
            text = text.replace(TITLE_FRAME_OLD, _frame(brand_name))
            text = _SPECTATOR_TITLE.sub(f"<title>{brand_name} - Spectator</title>", text)
            text = text.replace("<h1>TW2K-AI</h1>", f"<h1>{brand_name}</h1>")
            text = _TAGLINE.sub(BRAND_LINE, text)
        elif name == "app.js":
            text = text.replace("`TW2K - Day ", f"`{brand_name} - Day ")
    return rewrite_embedded_urls(text, base)


def rewrite_location(value: str, base: str) -> str:
    from .share_url import loopback_to_path

    value = loopback_to_path(value)
    if base and value.startswith("/") and not value.startswith("//") and not value.startswith(base + "/"):
        return base + value
    return value


def rewrite_cookie(value: str, base: str) -> str:
    if not base:
        return value
    return re.sub(r"(?i)(;\s*Path=)(/[^;]*)", lambda m: m.group(1) + base + m.group(2), value)


class AcceptBasePath:
    """Answer /g/<id>/... on this worker, not only on the lobby proxy.

    The lobby strips that prefix before it forwards. A browser that opens the
    worker's own /bot page, including the scripted cockpit seat, does not.
    The page already points at /g/<id>/static and /g/<id>/harness, so those
    requests have to land on the same routes. Lobby-only /control stays closed:
    the public lock still sees the path after this prefix is removed.
    """

    def __init__(self, app, *, base: str) -> None:
        self.app = app
        self.base = (base or "").rstrip("/")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.base and scope.get("type") in ("http", "websocket"):
            path = scope.get("path") or "/"
            prefix = self.base
            if path == prefix or path.startswith(prefix + "/"):
                scope = dict(scope)
                rest = path[len(prefix):] or "/"
                scope["path"] = rest
                raw = scope.get("raw_path")
                if isinstance(raw, (bytes, bytearray)):
                    mark = prefix.encode("ascii")
                    if raw == mark or raw.startswith(mark + b"/"):
                        scope["raw_path"] = raw[len(mark):] or b"/"
        await self.app(scope, receive, send)


class PageRewrite:
    """TW2K_BASE_PATH / TW2K_BRAND: rewrite pages, scripts, redirects and cookie paths."""

    def __init__(self, app, *, base: str, brand_name: str) -> None:
        self.app = app
        self.base = base
        self.brand = brand_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path") or "/"
        held: dict[str, Any] = {}
        chunks: list[bytes] = []

        async def wrapped(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = []
                text_body = False
                for k, v in message.get("headers") or []:
                    key = k.decode("latin-1").lower()
                    val = v.decode("latin-1")
                    if key == "location":
                        val = rewrite_location(val, self.base)
                    elif key == "set-cookie":
                        val = rewrite_cookie(val, self.base)
                    elif key == "content-type" and any(t in val for t in _TEXT_TYPES):
                        text_body = True
                    headers.append((k, val.encode("latin-1")))
                message = dict(message, headers=headers)
                if text_body:
                    held["start"] = message
                    return
                await send(message)
                return
            if message["type"] == "http.response.body" and "start" in held:
                chunks.append(message.get("body", b""))
                if message.get("more_body"):
                    return
                raw = b"".join(chunks)
                try:
                    body = rewrite_text(path, raw.decode("utf-8"), base=self.base,
                                        brand_name=self.brand).encode("utf-8")
                except UnicodeDecodeError:
                    body = raw
                start = held.pop("start")
                headers = [(k, v) for k, v in start["headers"] if k.decode("latin-1").lower() not in ("content-length", "etag")]
                headers.append((b"content-length", str(len(body)).encode("latin-1")))
                await send(dict(start, headers=headers))
                await send({"type": "http.response.body", "body": body})
                return
            await send(message)

        await self.app(scope, receive, wrapped)


# --------------------------------------------------------------------------- snapshots


def snapshot_dir() -> Path | None:
    raw = _env(ENV_SNAPSHOT_DIR)
    return Path(raw) if raw else None


def resume_path() -> str | None:
    raw = _env(ENV_RESUME)
    return raw or None


def write_snapshot(runner, reason: str, directory: Path | None = None) -> Path | None:
    """Write `snap-<ms>.jsonl` (a meta line, then the universe) atomically; keep the last 3."""
    target = directory or snapshot_dir()
    universe = runner.state.universe
    if target is None or universe is None:
        return None
    target.mkdir(parents=True, exist_ok=True)
    meta = {
        "version": 1,
        "saved_at": time.time(),
        "reason": reason,
        "day": int(universe.day),
        "day_started_at": float(getattr(runner, "_live_day_mark", 0.0) or 0.0) or None,
        "status": runner.state.status,
    }
    spec = getattr(runner, "_spec", None)
    override = getattr(getattr(spec, "config", None), "starting_credits_override", None)
    if override is not None:
        meta["starting_credits_override"] = int(override)
    from ..engine import constants as K

    meta["day_seconds"] = float(K.TURN_REGEN_DAY_SECONDS)
    stamp = int(meta["saved_at"] * 1000)
    final = target / f"snap-{stamp:015d}.jsonl"
    tmp = target / f".snap-{stamp:015d}.tmp"
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(meta, sort_keys=True) + "\n")
        fh.write(universe.model_dump_json() + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, final)
    for old in sorted(target.glob("snap-*.jsonl"))[:-SNAPSHOT_KEEP]:
        try:
            old.unlink()
        except OSError:
            pass
    runner._last_snapshot_at = time.time()
    events = getattr(universe, "events", None) or []
    runner._last_snapshot_seq = int(getattr(events[-1], "seq", 0) or 0) if events else 0
    return final


def latest_snapshot(directory: Path) -> Path | None:
    snaps = sorted(Path(directory).glob("snap-*.jsonl"))
    return snaps[-1] if snaps else None


def load_snapshot(path: str | os.PathLike[str]):
    """(meta, Universe) from a snapshot file."""
    from ..engine.models import Universe

    with Path(path).open("r", encoding="utf-8") as fh:
        meta = json.loads(fh.readline())
        universe = Universe.model_validate_json(fh.readline())
    return meta, universe


def choose_snapshot(directory: Path) -> tuple[Path | None, bool]:
    """Pick a snapshot that loads.

    ``(None, False)`` when the folder has no save yet, so the game starts new.
    ``(path, False)`` for the newest file that loads. An older file is used when
    a newer one is damaged. ``(None, True)`` when every file fails to load.
    """
    folder = Path(directory)
    if not folder.is_dir():
        return None, False
    snaps = sorted(folder.glob("snap-*.jsonl"))
    if not snaps:
        return None, False
    for path in reversed(snaps):
        try:
            load_snapshot(path)
        except Exception:
            continue
        return path, False
    return None, True


def maybe_snapshot(runner, *, rolled: bool = False) -> None:
    """Snapshot on a day roll, shortly after play moves on, or every 5 quiet minutes."""
    directory = getattr(runner, "_snapshot_dir", None)
    if directory is None:
        return
    now = time.time()
    last = float(getattr(runner, "_last_snapshot_at", 0.0) or 0.0)
    universe = getattr(getattr(runner, "state", None), "universe", None)
    events = getattr(universe, "events", None) or []
    seq = int(getattr(events[-1], "seq", 0) or 0) if events else 0
    prev = getattr(runner, "_last_snapshot_seq", None)
    moved = prev is not None and seq != int(prev)
    if rolled or now - last >= SNAPSHOT_EVERY_S or (moved and now - last >= SNAPSHOT_MOVE_GAP_S):
        try:
            reason = "day roll" if rolled else ("play" if moved else "timer")
            write_snapshot(runner, reason, directory)
        except OSError:
            runner._last_snapshot_at = time.time()


# --------------------------------------------------------------------------- lobby routes


def install(app, runner) -> None:
    """Add the public-mode lock, the lobby-only routes and the page rewrite (env-gated)."""
    import asyncio
    import signal

    from fastapi import HTTPException

    base = base_path()
    brand_name = brand()
    if public_mode():
        from ..server.spectator_gate import spectator_token

        if not spectator_token() or not lobby_secret():
            raise RuntimeError(f"{ENV_PUBLIC_MODE} needs TW2K_SPECTATOR_TOKEN and {ENV_LOBBY_SECRET}")

        def _lobby_only(request: Request) -> None:
            if not from_lobby(request.scope):
                raise HTTPException(status_code=404, detail="not available in this game")

        @app.get("/healthz")
        async def healthz() -> dict[str, Any]:
            return health_payload(runner)

        @app.post("/control/seat-token")
        async def seat_token(request: Request) -> dict[str, Any]:
            _lobby_only(request)
            from ..agents.external import ExternalAgent

            body = await request.json()
            seat = str(body.get("seat") or "").upper()
            token = str(body.get("token") or "")
            if len(token) < 32:
                raise HTTPException(status_code=400, detail="token too short")
            agent = next((a for a in runner.state.agents
                          if isinstance(a, ExternalAgent) and a.player_id == seat), None)
            if agent is None:
                raise HTTPException(status_code=404, detail="no such seat")
            agent.set_token(token)
            return {"ok": True, "seat": seat}

        @app.get("/control/seats")
        async def seats(request: Request) -> dict[str, Any]:
            _lobby_only(request)
            from ..agents.external import ExternalAgent

            out = {}
            for a in runner.state.agents:
                if isinstance(a, ExternalAgent):
                    st = a.status()
                    out[a.player_id] = {"last_client_seen_at": st.get("last_client_seen_at")}
            return {"seats": out}

        @app.post("/control/snapshot")
        async def snapshot(request: Request) -> dict[str, Any]:
            _lobby_only(request)
            path = write_snapshot(runner, "lobby", getattr(runner, "_snapshot_dir", None))
            return {"ok": path is not None, "file": path.name if path else None}

        @app.post("/control/shutdown")
        async def shutdown(request: Request) -> dict[str, Any]:
            _lobby_only(request)
            path = write_snapshot(runner, "shutdown", getattr(runner, "_snapshot_dir", None))
            asyncio.get_running_loop().call_later(0.3, signal.raise_signal, signal.SIGINT)
            return {"ok": True, "file": path.name if path else None}

        @app.post("/control/rewind-day")
        async def rewind_day(request: Request) -> dict[str, Any]:
            """Lobby-only. Move the day mark back one day length so the clock can roll.

            Answers 404 unless PLAYTEST_CLOCK_NUDGE_MODE is on. The turn loop
            itself is unchanged.
            """
            _lobby_only(request)
            from ..engine import constants as K

            if not K.playtest_clock_nudge_on():
                raise HTTPException(status_code=404, detail="not available")
            mark = float(getattr(runner, "_live_day_mark", 0.0) or 0.0)
            if not mark:
                raise HTTPException(status_code=409, detail="the day has not started")
            day_s = float(K.TURN_REGEN_DAY_SECONDS)
            runner._live_day_mark = mark - day_s - 1.0
            return {"ok": True, "day_started_at": runner._live_day_mark}

        @app.post("/control/end")
        async def end_for_creator(request: Request) -> dict[str, Any]:
            """Lobby-only. Finish the match so the end screen can load. The process stays up."""
            _lobby_only(request)
            if runner.state.universe is None:
                raise HTTPException(status_code=409, detail="no match")
            ended = runner.end_by_creator()
            return {"ok": True, "ended": bool(ended), "finished": True}

        app.add_middleware(PublicLock)
    if base or brand_name:
        app.add_middleware(PageRewrite, base=base, brand_name=brand_name)
    if base:
        app.add_middleware(AcceptBasePath, base=base)
