"""The worker side of the beta: what a `tw2k serve` started by the lobby adds.

Every piece reads its own env value and does nothing when that value is unset:

* ``TW2K_SWITCH_OVERLAY`` - JSON ``{"V311_PROFILE": "v311", ...}`` set on ``constants`` at start.
* ``TW2K_PUBLIC_MODE=1`` - only the cockpit, the claim link, the harness, static files, the
  health route and the (token-gated) spectator routes answer; ``/control/*``, ``/api/*`` and
  every other route answer only a loopback call carrying ``TW2K_LOBBY_SECRET``.
* ``TW2K_BASE_PATH=/g/<id>`` - pages, claim cookies and redirects work under the lobby prefix.
* ``TW2K_BRAND`` - the player-facing name on the cockpit and spectator pages.
* ``TW2K_SNAPSHOT_DIR`` - the game is snapshotted on every day roll and every 5 minutes.
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
SNAPSHOT_KEEP = 3

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
OPEN_EXACT = frozenset({"/", "/bot", "/bot/claim", "/healthz", "/spectate",
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


def rewrite_text(path: str, text: str, *, base: str, brand_name: str) -> str:
    """The prefix and the brand for one served page or script (no-op with both unset)."""
    name = path.rsplit("/", 1)[-1].split("?", 1)[0]
    is_html = path in ("/", "/bot", "/bot2", "/play") or name.endswith(".html")
    if base:
        if is_html:
            for attr in ('src="/', 'href="/', 'action="/'):
                text = text.replace(attr, attr[:-1] + base + "/")
        elif name == "redesign.js":
            text = text.replace('"/harness/v1"', f'"{base}/harness/v1"')
            text = text.replace('"/static/', f'"{base}/static/')
        elif name == "app.js":
            text = _APP_JS_PATH.sub(lambda m: f"{m.group(1)}{base}/{m.group(2)}", text)
            text = text.replace("${location.host}/ws", "${location.host}" + base + "/ws")
        elif name.endswith(".js"):
            text = text.replace('"/static/', f'"{base}/static/')
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
    return text


def rewrite_location(value: str, base: str) -> str:
    if base and value.startswith("/") and not value.startswith("//") and not value.startswith(base + "/"):
        return base + value
    return value


def rewrite_cookie(value: str, base: str) -> str:
    if not base:
        return value
    return re.sub(r"(?i)(;\s*Path=)(/[^;]*)", lambda m: m.group(1) + base + m.group(2), value)


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


def maybe_snapshot(runner, *, rolled: bool = False) -> None:
    """Snapshot on a day roll, or when the last one is 5 minutes old."""
    directory = getattr(runner, "_snapshot_dir", None)
    if directory is None:
        return
    last = float(getattr(runner, "_last_snapshot_at", 0.0) or 0.0)
    if rolled or time.time() - last >= SNAPSHOT_EVERY_S:
        try:
            write_snapshot(runner, "day roll" if rolled else "timer", directory)
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
            u = runner.state.universe
            return {"ok": True, "status": runner.state.status,
                    "day": int(u.day) if u is not None else None,
                    "finished": runner.state.status == "finished"}

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

        app.add_middleware(PublicLock)
    if base or brand_name:
        app.add_middleware(PageRewrite, base=base, brand_name=brand_name)
