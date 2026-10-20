"""`tw2k lobby`: the closed-beta front door that starts, proxies and looks after game workers."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import json
import logging
import logging.handlers
import secrets
import shutil
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket

from . import pages
from . import worker as W
from .config import LobbyConfig, pick_port
from .proxy import Proxy
from .ai_seat import AiMemory, drive_seats, mask_key
from .security import (
    GUEST_COOKIE,
    GUEST_COOKIE_MAX_AGE,
    WATCH_COOKIE_PREFIX,
    FormError,
    RateLimiter,
    Secrets,
    client_ip,
    guest_id,
    home_planet_name,
    is_https,
    is_local_admin,
    new_guest_cookie,
    new_seat_token,
    parse_game_form,
    sha256_hex,
)
from .store import ACTIVE, LIVE, Store
from .workers import WorkerManager, admin_headers, ai_count, ai_seat_ids, cockpit_count, cockpit_seat_ids, seat_ids

log = logging.getLogger("tw2k.lobby")

SPECTATOR_PATHS = frozenset({"", "state", "events", "history", "highlights", "ws"})
BLOCKED_PATHS = frozenset({"spectate"})
STATUS_ORIGINS_ENV = "TW2K_STATUS_ORIGINS"
DEFAULT_STATUS_ORIGINS = ("https://thesingularity.netlify.app",)
_SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "referrer-policy": "same-origin",
    "x-frame-options": "DENY",
    "content-security-policy": "frame-ancestors 'none'",
}


class TooLarge(Exception):
    pass


def setup_logging(cfg: LobbyConfig) -> None:
    cfg.logs_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(cfg.logs_dir / "lobby.log", maxBytes=1_000_000, backupCount=5,
                                                   encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    for h in list(log.handlers):
        if isinstance(h, logging.handlers.RotatingFileHandler):
            log.removeHandler(h)
            h.close()
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False


class Lobby:
    def __init__(self, cfg: LobbyConfig, *, python: str | None = None, port_probe=None) -> None:
        self.cfg = cfg
        cfg.root.mkdir(parents=True, exist_ok=True)
        self.store = Store(cfg.db_path)
        self.secrets = Secrets(cfg.root)
        self.workers = WorkerManager(cfg, python=python)
        self.proxy = Proxy()
        self.limits = RateLimiter()
        self.live: dict[str, dict[str, Any]] = {}
        self.activity: dict[str, float] = {}
        self.open_ws: dict[str, int] = {}
        self.locks: dict[str, asyncio.Lock] = {}
        self.reserved_ports: set[int] = set()
        self._port_probe = port_probe
        self.ai_memory = AiMemory()
        self.ai_tasks: dict[str, asyncio.Task] = {}
        self.cockpit_rows: dict[str, dict[str, Any]] = {}
        self._task: asyncio.Task | None = None
        self._admin_csrf = hmac.new(secrets.token_bytes(32), b"admin", hashlib.sha256).hexdigest()
        self._shutdown_key = secrets.token_hex(24)
        origins = (W._env(STATUS_ORIGINS_ENV) or ",".join(DEFAULT_STATUS_ORIGINS)).split(",")
        self.status_origins = {o.strip().rstrip("/") for o in origins if o.strip()}

    # ------------------------------------------------------------------ helpers
    @property
    def brand(self) -> str:
        return self.cfg.brand

    @property
    def closed(self) -> bool:
        return self.store.flag("closed") == "1"

    def lock(self, gid: str) -> asyncio.Lock:
        return self.locks.setdefault(gid, asyncio.Lock())

    def invite_key(self, gid: str, seat: str) -> str:
        return self.secrets._derive("invite", f"{gid}:{seat}", 12)

    def live_games(self) -> int:
        return self.store.count_games(LIVE)

    def _worker_serves(self, g: dict[str, Any]) -> bool:
        """A running worker, or a finished one that is still up for the end screen."""
        w = self.workers.workers.get(g["id"])
        if w is None or not w.alive():
            return False
        return g["status"] in ("running", "finished")

    def full_for(self, humans: int) -> bool:
        return (self.live_games() >= self.cfg.max_games
                or self.store.count_human_seats(ACTIVE) + humans > self.cfg.max_human_seats)

    def tag(self, request: Request | WebSocket) -> str:
        """Log-safe caller label: an HMAC of the IP and the first 8 hex of the guest hash."""
        ip = client_ip(request.headers, request.client.host if request.client else None)
        gid = guest_id(request.cookies.get(GUEST_COOKIE)) or "-"
        return f"ip={self.secrets.ip_tag(ip)} guest={gid[:8]}"

    def ip(self, request: Request | WebSocket) -> str:
        return client_ip(request.headers, request.client.host if request.client else None)

    def guest(self, request: Request | WebSocket) -> dict[str, Any] | None:
        gid = guest_id(request.cookies.get(GUEST_COOKIE))
        if gid is None:
            return None
        return self.store.touch_guest(gid)

    def accepted(self, request: Request | WebSocket) -> dict[str, Any] | None:
        g = self.guest(request)
        return g if g and g.get("accepted_at") else None

    def watch_ok(self, request: Request | WebSocket, gid: str) -> bool:
        presented = request.cookies.get(WATCH_COOKIE_PREFIX + gid, "")
        return bool(presented) and hmac.compare_digest(presented, self.secrets.watch_cookie(gid))

    def secure(self, request: Request) -> bool:
        return is_https(request.headers, request.url.scheme)

    def html(self, text: str, status: int = 200, **kw) -> HTMLResponse:
        return HTMLResponse(text, status_code=status, headers=dict(_SECURITY_HEADERS), **kw)

    def msg(self, title: str, text: str, status: int, **kw) -> HTMLResponse:
        return self.html(pages.message(self.brand, title, text, **kw), status)

    async def read_body(self, request: Request) -> bytes:
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > self.cfg.body_limit:
            raise TooLarge()
        out = bytearray()
        async for chunk in request.stream():
            out += chunk
            if len(out) > self.cfg.body_limit:
                raise TooLarge()
        return bytes(out)

    async def read_form(self, request: Request) -> dict[str, str]:
        raw = await self.read_body(request)
        ctype = request.headers.get("content-type", "")
        if "application/json" in ctype:
            data = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(data, dict):
                raise FormError("expected a JSON object")
            return data
        parsed = parse_qs(raw.decode("utf-8"), keep_blank_values=True, max_num_fields=40)
        return {k: v[-1] for k, v in parsed.items()}

    def same_origin(self, request: Request) -> bool:
        origin = request.headers.get("origin")
        if not origin or origin == "null":
            return origin is None
        return urlsplit(origin).netloc.lower() == (request.headers.get("host") or "").lower()

    # ------------------------------------------------------------------ worker lifecycle
    def _probe(self, port: int) -> bool:
        from .config import port_is_free

        return (self._port_probe or port_is_free)(port)

    async def start_game(self, gid: str, *, resume: bool) -> bool:
        async with self.lock(gid):
            g = self.store.game(gid)
            if g is None:
                return False
            w = self.workers.workers.get(gid)
            if w is not None and w.alive():
                return True
            snap = W.latest_snapshot(self.workers.game_dir(gid) / "snapshots") if resume else None
            taken = self.workers.ports_in_use() | self.reserved_ports
            port = pick_port(self.cfg, taken, probe=self._probe)
            if port is None:
                log.warning("start game=%s: no free game port", gid)
                self.store.set_game(gid, status="failed", note="no free game port")
                return False
            self.reserved_ports.add(port)
            try:
                humans_n = int(g["settings"]["humans"])
                human_seats = seat_ids(humans_n)
                ai_seats = ai_seat_ids(humans_n, ai_count(g["settings"]))
                cock_seats = cockpit_seat_ids(humans_n, len(ai_seats), cockpit_count(g["settings"]))
                tokens = {seat: new_seat_token() for seat in [*human_seats, *ai_seats, *cock_seats]}
                for seat in human_seats:
                    self.store.set_seat_hash(gid, seat, None)
                if ai_seats:
                    self.ai_memory.hold_tokens(
                        gid, {seat: tokens[seat] for seat in ai_seats},
                        brain=str(g["settings"].get("ai_brain") or "heuristic"),
                    )
                if cock_seats:
                    settings = g["settings"]
                    self.cockpit_rows[gid] = {
                        "seat": cock_seats[0],
                        "token": tokens[cock_seats[0]],
                        "provider": str(settings.get("ai_cockpit_provider") or "scripted"),
                        "model": str(settings.get("ai_cockpit_model") or ""),
                        "proc": None,
                    }
                w = self.workers.spawn(gid, g["settings"], port, brand=self.brand,
                                       lobby_secret=self.secrets.lobby_secret(gid),
                                       spectator_token=self.secrets.spectator_token(gid),
                                       seat_tokens=tokens, resume=snap)
                del tokens
                self.store.set_game(gid, status="starting", port=port, pid=w.pid)
                log.info("start game=%s port=%s pid=%s resume=%s", gid, port, w.pid, "yes" if snap else "no")
                ok = await self.workers.wait_healthy(gid)
            finally:
                self.reserved_ports.discard(port)
            if ok:
                self.activity[gid] = time.time()
                self.store.set_game(gid, status="running", last_activity=time.time())
                self._launch_ai(gid)
                self._launch_cockpit(gid)
                return True
            log.warning("start game=%s: worker did not come up", gid)
            self._drop_cockpit(gid, forget=True)
            await self.workers.stop(gid, lobby_secret=self.secrets.lobby_secret(gid),
                                    spectator_token=self.secrets.spectator_token(gid), graceful=False)
            self.store.set_game(gid, status="failed", note="worker did not come up")
            return False

    def _drop_ai(self, gid: str) -> None:
        """Forget the key and stop the seat tasks. Safe to call more than once."""
        self.ai_memory.drop(gid)
        task = self.ai_tasks.pop(gid, None)
        if task is not None and not task.done():
            task.cancel()

    def _launch_ai(self, gid: str) -> None:
        from ..engine import constants as K

        if not K.lobby_ai_seat_on():
            return
        row = self.ai_memory.row(gid)
        w = self.workers.workers.get(gid)
        g = self.store.game(gid)
        if row is None or not row.tokens or w is None or g is None:
            return
        old = self.ai_tasks.pop(gid, None)
        if old is not None and not old.done():
            old.cancel()
        settings = g["settings"]
        days = int(settings.get("max_days") or 1)
        idle_s = max(600.0, float(settings.get("day_seconds") or 600) * 2)
        self.ai_tasks[gid] = asyncio.create_task(self._run_ai(
            gid, f"http://127.0.0.1:{w.port}", dict(row.tokens),
            brain=row.brain, key=row.key, url=row.url, days=days, idle_s=idle_s,
        ))

    def launch_browser_seat(self, gid: str, seat: str, token: str, *, run_dir: Path,
                            base_url: str, provider: str = "scripted", model: str = "",
                            max_turns: int = 40, min_interval: float = 1.0, path: str | None = None):
        """Start the rendered-screen player for this seat when the switch is on.

        The child opens the seat link and does not receive engine objects. The
        token is the seat link's token; this method does not log it.
        """
        from .ai_cockpit_launch import launch_player

        return launch_player(
            base_url=base_url, gid=gid, seat=seat, token=token, run_dir=Path(run_dir),
            provider=provider, model=model, max_turns=max_turns, min_interval=min_interval,
            path=path,
        )

    def _launch_cockpit(self, gid: str):
        """Start the browser player for a seat the new-game form asked for.

        The child opens the worker's /bot page, which is the same screen a
        person gets through the lobby. The harness AI list does not include
        this seat, so nothing else drives it.
        """
        from ..engine import constants as K
        from .ai_cockpit_launch import direct_seat_url

        if not K.ai_cockpit_seat_on():
            return None
        row = self.cockpit_rows.get(gid)
        w = self.workers.workers.get(gid)
        g = self.store.game(gid)
        if row is None or w is None or g is None:
            return None
        settings = g["settings"]
        try:
            days = max(1, int(settings.get("max_days") or 1))
            turns = max(1, int(settings.get("turns_per_day") or 1))
        except (TypeError, ValueError):
            days, turns = 1, 1
        proc = self.launch_browser_seat(
            gid, str(row["seat"]), str(row["token"]),
            run_dir=self.workers.game_dir(gid) / "ai-cockpit",
            base_url=f"http://127.0.0.1:{w.port}",
            provider=str(row["provider"] or "scripted"),
            model=str(row["model"] or ""),
            max_turns=max(80, days * turns * 2),
            min_interval=1.0,
            path=direct_seat_url(str(row["seat"]), str(row["token"])),
        )
        row["proc"] = proc
        return proc

    def cockpit_status(self, gid: str) -> str:
        """Status text for the lobby. Empty when this game has no cockpit seat."""
        from .ai_cockpit_launch import status_line

        row = self.cockpit_rows.get(gid)
        g = self.store.game(gid)
        settings = (g or {}).get("settings") or {}
        if row is None and not settings.get("ai_cockpit"):
            return ""
        provider = str((row or {}).get("provider") or settings.get("ai_cockpit_provider") or "scripted")
        model = str((row or {}).get("model") or settings.get("ai_cockpit_model") or "")
        proc = (row or {}).get("proc")
        running = proc is not None and proc.poll() is None
        return status_line(provider, model, running)

    def _drop_cockpit(self, gid: str, *, forget: bool = False) -> None:
        row = self.cockpit_rows.get(gid)
        if row is not None:
            proc = row.get("proc")
            if proc is not None and proc.poll() is None:
                proc.terminate()
            row["proc"] = None
        if forget:
            self.cockpit_rows.pop(gid, None)

    async def ai_seat_view(self, request: Request) -> Response:
        """Creator redirect to the cockpit seat. The token stays out of the lobby HTML."""
        gate = self._need_accept(request)
        if gate:
            return gate
        guest = self.accepted(request)
        gid = request.path_params["gid"]
        g = self.store.game(gid)
        if guest is None or g is None or g.get("creator") != guest["id"]:
            return self.msg("Not allowed", "That seat view is for the person who created the game.", 403)
        row = self.cockpit_rows.get(gid)
        if row is None:
            return self.msg("No AI seat", "This game has no AI cockpit seat.", 404)
        from .ai_cockpit_launch import cockpit_seat_url

        return RedirectResponse(cockpit_seat_url(gid, str(row["seat"]), str(row["token"])), status_code=303)

    async def _run_ai(self, gid: str, base: str, tokens: dict[str, str], *, brain: str, key: str,
                      url: str, days: int, idle_s: float) -> None:
        try:
            async with httpx.AsyncClient(base_url=base, timeout=60.0) as client:
                await drive_seats(client, tokens, brain=brain, key=key, url=url, days=days, idle_s=idle_s)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("ai seat game=%s stopped", gid)

    async def stop_game(self, gid: str, *, status: str, graceful: bool = True) -> None:
        async with self.lock(gid):
            self._drop_ai(gid)
            self._drop_cockpit(gid)
            await self.workers.stop(gid, lobby_secret=self.secrets.lobby_secret(gid),
                                    spectator_token=self.secrets.spectator_token(gid), graceful=graceful)
            self.store.set_game(gid, status=status, pid=None)
            self.live.pop(gid, None)
            log.info("stop game=%s status=%s", gid, status)

    async def worker_call(self, gid: str, method: str, path: str, body: dict | None = None) -> httpx.Response | None:
        w = self.workers.workers.get(gid)
        if w is None or not w.alive():
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                return await client.request(method, f"http://127.0.0.1:{w.port}{path}", json=body,
                                            headers=admin_headers(self.secrets.lobby_secret(gid),
                                                                  self.secrets.spectator_token(gid)))
        except httpx.HTTPError:
            return None

    async def hand_seat(self, gid: str, seat: str) -> str | None:
        """A fresh token for this seat, set on the worker; only its hash stays with the lobby."""
        token = new_seat_token()
        r = await self.worker_call(gid, "POST", "/control/seat-token", {"seat": seat, "token": token})
        if r is None or r.status_code != 200:
            return None
        self.store.set_seat_hash(gid, seat, sha256_hex(token))
        return token

    def claim_url(self, gid: str, seat: str, token: str) -> str:
        return f"/g/{gid}/bot/claim?seat={quote(seat)}&token={quote(token)}"

    async def tick(self) -> None:
        now = time.time()
        for g in self.store.games(LIVE):
            gid = g["id"]
            w = self.workers.workers.get(gid)
            if self.lock(gid).locked():
                continue
            if w is None or not w.alive():
                if w is not None and w.stopping:
                    continue
                if g["restarts"] < 1:
                    log.warning("crash game=%s: restarting once from the latest snapshot", gid)
                    self.store.set_game(gid, restarts=g["restarts"] + 1)
                    if w is not None:
                        self.workers.workers.pop(gid, None)
                    await self.start_game(gid, resume=True)
                else:
                    log.warning("crash game=%s: second crash, marked failed", gid)
                    self.workers.workers.pop(gid, None)
                    self.store.set_game(gid, status="failed", pid=None, note="stopped after a second crash")
                continue
            info = None
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    r = await client.get(f"http://127.0.0.1:{w.port}/healthz")
                    if r.status_code == 200:
                        info = r.json()
            except (httpx.HTTPError, ValueError):
                info = None
            if info:
                self.live[gid] = info
            # A finished game leaves the running list at once, while the worker
            # stays up so the end screen and the watch page keep loading.
            # set_game stamps updated_at, which is when the archive clock starts.
            if info and info.get("finished") and g["status"] == "running":
                self._drop_ai(gid)
                self.store.set_game(gid, status="finished")
                g = dict(g)
                g["status"] = "finished"
            last = max(self.activity.get(gid, 0.0), float(g["last_activity"] or 0.0))
            if self.open_ws.get(gid, 0) == 0 and now - last > self.cfg.idle_s:
                done = g["status"] == "finished" or bool(info and info.get("finished"))
                await self.stop_game(gid, status="finished" if done else "sleeping")
                continue
            if gid in self.activity and self.activity[gid] - float(g["last_activity"] or 0.0) > 30:
                self.store.set_game(gid, last_activity=self.activity[gid])
        for g in self.store.games(("finished",)):
            gid = g["id"]
            w = self.workers.workers.get(gid)
            if w is None or not w.alive() or self.lock(gid).locked():
                continue
            last = max(self.activity.get(gid, 0.0), float(g["last_activity"] or 0.0))
            if self.open_ws.get(gid, 0) == 0 and now - last > self.cfg.idle_s:
                await self.stop_game(gid, status="finished")
        for g in self.store.games(("finished", "failed", "sleeping", "stopped")):
            still = self.workers.workers.get(g["id"])
            # A tab on the end screen keeps the worker. An idle worker is the
            # reaper's job; once that clock has passed, the archive can move the files.
            if still is not None and still.alive() and self.open_ws.get(g["id"], 0) > 0:
                continue
            if now - float(g["updated_at"]) > self.cfg.archive_s:
                src = self.workers.game_dir(g["id"])
                dst = self.cfg.archive_dir / g["id"]
                try:
                    if src.exists():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(src), str(dst))
                except OSError:
                    continue
                self.store.set_game(g["id"], status="archived")
                log.info("archive game=%s", g["id"])

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.cfg.tick_s)
            try:
                await self.tick()
            except Exception:  # keep the lobby up
                log.exception("lobby tick failed")

    @property
    def shutdown_key_path(self) -> Path:
        return self.cfg.root / "lobby.shutdown.key"

    async def startup(self) -> None:
        setup_logging(self.cfg)
        self.shutdown_key_path.write_text(self._shutdown_key, encoding="ascii")
        log.info("lobby up port=%s games=%s-%s", self.cfg.port, self.cfg.game_ports.start, self.cfg.game_ports.stop - 1)
        restore = self.store.games(LIVE)
        for g in restore:
            log.info("restore game=%s from its latest snapshot", g["id"])
        await asyncio.gather(*(self.start_game(g["id"], resume=True) for g in restore))
        self._task = asyncio.create_task(self._loop())

    async def shutdown(self) -> None:
        for gid in list(self.ai_tasks):
            self._drop_ai(gid)
        self.ai_memory.drop_all()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task
        await asyncio.gather(*(self.workers.stop(gid, lobby_secret=self.secrets.lobby_secret(gid),
                                                 spectator_token=self.secrets.spectator_token(gid))
                               for gid in list(self.workers.workers)))
        self.workers.kill_all()
        with contextlib.suppress(OSError):
            self.shutdown_key_path.unlink()
        await self.proxy.close()
        log.info("lobby down")
        self.store.close()

    # ------------------------------------------------------------------ guest pages
    def _with_guest(self, request: Request, resp: Response) -> Response:
        if not guest_id(request.cookies.get(GUEST_COOKIE)):
            cookie = new_guest_cookie()
            self.store.touch_guest(sha256_hex(cookie))
            resp.set_cookie(GUEST_COOKIE, cookie, max_age=GUEST_COOKIE_MAX_AGE, httponly=True, samesite="lax",
                            secure=self.secure(request), path="/")
        return resp

    def _need_accept(self, request: Request) -> Response | None:
        if self.accepted(request):
            return None
        nxt = request.url.path + (("?" + request.url.query) if request.url.query else "")
        return self._with_guest(request, self.html(pages.disclaimer(self.brand, nxt)))

    def _listed(self) -> list[dict[str, Any]]:
        out = []
        for g in self.store.games(ACTIVE):
            if not g["listed"]:
                continue
            g["open_seats"] = sum(1 for s in self.store.seats(g["id"]) if not s["guest_id"])
            out.append(g)
        return out

    async def home(self, request: Request) -> Response:
        gate = self._need_accept(request)
        if gate:
            return gate
        guest = self.accepted(request)
        guest_id = guest["id"]
        games = self._listed()
        notes = {g["id"]: self.cockpit_status(g["id"]) for g in games}
        notes = {gid: text for gid, text in notes.items() if text}
        seat_links = {
            gid: f"/games/{gid}/ai-seat"
            for gid, row in self.cockpit_rows.items()
            if row and any(g["id"] == gid and g.get("creator") == guest_id for g in games)
        }
        return self.html(pages.lobby(
            self.brand, games=games, mine=self.store.guest_games(guest_id),
            owned=self.store.created_games(guest_id), closed=self.closed, full=self.full_for(1), live=self.live,
            notes=notes, seat_links=seat_links,
        ))

    async def about(self, request: Request) -> Response:
        return self.html(pages.about(self.brand))

    async def manual(self, request: Request) -> Response:
        from .manual import render

        return self.html(render(self.brand))

    async def accept(self, request: Request) -> Response:
        if not self.same_origin(request):
            return self.msg("Not allowed", "That form came from another site.", 403)
        try:
            form = await self.read_form(request)
        except (TooLarge, FormError, ValueError):
            form = {}
        cookie = request.cookies.get(GUEST_COOKIE)
        gid = guest_id(cookie)
        nxt = str(form.get("next") or "/")
        if not nxt.startswith("/") or nxt.startswith("//"):
            nxt = "/"
        if request.headers.get("content-type", "").startswith("application/json"):
            resp: Response = JSONResponse({"ok": True})
        else:
            resp = RedirectResponse(nxt, status_code=303)
        if gid is None:
            cookie = new_guest_cookie()
            gid = sha256_hex(cookie)
            resp.set_cookie(GUEST_COOKIE, cookie, max_age=GUEST_COOKIE_MAX_AGE, httponly=True, samesite="lax",
                            secure=self.secure(request), path="/")
        self.store.accept(gid)
        log.info("accept %s", self.tag(request))
        return resp

    def _waiting(self, request: Request) -> list[dict[str, Any]]:
        """Active games this guest can still open, so the new-game screen can point at them."""
        guest = self.accepted(request)
        if guest is None:
            return []
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for g in self.store.guest_games(guest["id"]):
            if g["status"] not in ACTIVE:
                continue
            rows.append({"id": g["id"], "name": g["name"], "href": f"/resume/{g['id']}"})
            seen.add(g["id"])
        for g in self.store.created_games(guest["id"]):
            if g["status"] not in ACTIVE or g["id"] in seen:
                continue
            rows.append({"id": g["id"], "name": g["name"], "href": f"/games/{g['id']}/join"})
        return rows

    async def new_form(self, request: Request) -> Response:
        gate = self._need_accept(request)
        if gate:
            return gate
        if self.closed:
            return self.msg("Closed", "New games are switched off right now.", 503)
        if self.full_for(1):
            return self.msg("Beta full", pages.FULL_TEXT, 503)
        return self.html(pages.new_game(self.brand, presets=self.cfg.day_presets, waiting=self._waiting(request)))

    async def create(self, request: Request) -> Response:
        api = request.url.path.startswith("/api/")
        guest = self.accepted(request)
        if guest is None:
            return self._api_or(api, 403, "Accept the test-game notice first.", request)
        if not self.same_origin(request):
            return self._api_or(api, 403, "That form came from another site.", request)
        form: dict = {}
        try:
            form = await self.read_form(request)
            parsed = parse_game_form(form, self.cfg.day_presets)
        except TooLarge:
            return self._api_or(api, 413, "That request is too large.", request)
        except (FormError, ValueError) as exc:
            if api:
                return JSONResponse({"detail": str(exc)}, status_code=400)
            public = {k: v for k, v in form.items() if k not in ("ai_key", "ai_endpoint")}
            return self.html(pages.new_game(self.brand, error=str(exc), values=public, presets=self.cfg.day_presets,
                                            waiting=self._waiting(request)),
                             400)
        if self.closed:
            return self._api_or(api, 503, "New games are switched off right now.", request)
        if self.full_for(parsed.humans):
            log.info("full %s", self.tag(request))
            return self._api_or(api, 503, pages.FULL_TEXT, request, title="Beta full")
        ip = self.ip(request)
        if not (self.limits.allow("new-ip", ip, self.cfg.new_games_per_hour, 3600)
                and self.limits.allow("new-guest", guest["id"], self.cfg.new_games_per_hour, 3600)):
            log.info("rate-limit new-game %s", self.tag(request))
            return self._api_or(api, 429, "You have started the most games allowed for one hour. Try again later.",
                                request, title="Slow down")
        gid = secrets.token_hex(4)
        settings = parsed.settings()
        secret = parsed.ai_key
        endpoint = parsed.ai_endpoint
        parsed.ai_key = ""
        parsed.ai_endpoint = ""
        self.store.add_game(gid, name=parsed.name, creator=guest["id"], settings=settings, listed=parsed.listed,
                            seats=seat_ids(parsed.humans))
        ai_n = int(settings.get("ai_opponents") or 0)
        if ai_n and settings.get("ai_brain") == "llm":
            self.ai_memory.remember(gid, key=secret, url=endpoint, brain="llm")
            log.info("ai seat game=%s brain=llm seats=%s %s", gid, ai_n, mask_key(secret))
        elif ai_n:
            self.ai_memory.remember(gid, key="", url="", brain="heuristic")
            log.info("ai seat game=%s brain=heuristic seats=%s", gid, ai_n)
        secret = ""
        endpoint = ""
        log.info("create game=%s rules=%s humans=%s bots=%s day=%s %s", gid, settings["rules"], settings["humans"],
                 settings["bots"], settings["day"], self.tag(request))
        ok = False
        try:
            ok = await self.start_game(gid, resume=False)
        finally:
            if not ok:
                self._drop_ai(gid)
                self._drop_cockpit(gid, forget=True)
        if not ok:
            return self._api_or(api, 503, "The game could not start. Please try again later.", request)
        g = self.store.game(gid)
        base = self._base_url(request)
        links = [(seat, f"{base}/join/{gid}/{seat}?k={self.invite_key(gid, seat)}") for seat in seat_ids(parsed.humans)]
        watch = f"{base}/g/{gid}/watch" + ("" if parsed.listed else f"?k={self.secrets.watch_key(gid)}")
        cockpit = None
        if self.cockpit_rows.get(gid):
            row = self.cockpit_rows[gid]
            cockpit = {
                "status": self.cockpit_status(gid),
                "seat": str(row["seat"]),
                "href": f"/games/{gid}/ai-seat",
            }
        if api:
            payload = {"id": gid, "name": parsed.name, "status": g["status"], "join_links": dict(links),
                       "watch_link": watch}
            if cockpit:
                payload["ai_cockpit"] = {"seat": cockpit["seat"], "status": cockpit["status"],
                                         "href": cockpit["href"]}
            return JSONResponse(payload)
        return self.html(pages.created(self.brand, game=g, join_links=links, watch_link=watch, cockpit=cockpit))

    def _base_url(self, request: Request) -> str:
        scheme = "https" if self.secure(request) else request.url.scheme
        return f"{scheme}://{request.headers.get('host') or request.url.netloc}"

    def _api_or(self, api: bool, status: int, text: str, request: Request, *, title: str | None = None) -> Response:
        if api:
            return JSONResponse({"detail": text}, status_code=status)
        title = title or {403: "Not allowed", 404: "Not found", 413: "Too large", 429: "Slow down",
                          503: "Not right now"}.get(status, "Sorry")
        return self.msg(title, text, status)

    async def join_link(self, request: Request) -> Response:
        gate = self._need_accept(request)
        if gate:
            return gate
        gid, seat = request.path_params["gid"], request.path_params["seat"]
        key = request.query_params.get("k", "")
        g = self.store.game(gid)
        if g is None or not hmac.compare_digest(key, self.invite_key(gid, seat)):
            return self.msg("Not found", "That join link is not valid.", 404)
        return self.html(pages.join_confirm(self.brand, game=g, seat=seat, key=key))

    async def join(self, request: Request) -> Response:
        api = request.url.path.startswith("/api/")
        guest = self.accepted(request)
        if guest is None:
            return self._api_or(api, 403, "Accept the test-game notice first.", request)
        if not self.same_origin(request):
            return self._api_or(api, 403, "That form came from another site.", request)
        gid = request.path_params["gid"]
        try:
            form = await self.read_form(request)
        except TooLarge:
            return self._api_or(api, 413, "That request is too large.", request)
        except (FormError, ValueError):
            form = {}
        try:
            home_planet_name(form.get("home_planet_name"))
        except FormError as exc:
            if api:
                return self._api_or(api, 400, str(exc), request)
            seat = str(form.get("seat") or "")
            key = str(form.get("k") or "")
            g = self.store.game(gid)
            if g is None:
                return self.msg("Not found", "That game is not open.", 404)
            return self.html(pages.join_confirm(self.brand, game=g, seat=seat, key=key, error=str(exc)), 400)
        g = self.store.game(gid)
        if g is None or g["status"] not in ACTIVE:
            return self._api_or(api, 404, "That game is not open.", request)
        if self.closed:
            return self._api_or(api, 503, "Joining is switched off right now.", request)
        if not (self.limits.allow("join-ip", self.ip(request), self.cfg.joins_per_10min, 600)
                and self.limits.allow("join-guest", guest["id"], self.cfg.joins_per_10min, 600)):
            log.info("rate-limit join game=%s %s", gid, self.tag(request))
            return self._api_or(api, 429, "Too many joins in ten minutes. Try again shortly.", request)
        seat = self.store.guest_seat(gid, guest["id"])
        if seat is None:
            want = str(form.get("seat") or "")
            key = str(form.get("k") or "")
            invited = bool(want) and hmac.compare_digest(key, self.invite_key(gid, want))
            if not (g["listed"] or invited or g["creator"] == guest["id"]):
                return self._api_or(api, 403, "This game is link-only; use the join link you were sent.", request)
            seat = self._claim(gid, guest["id"], want if invited else None)
            if seat is None:
                return self._api_or(api, 409, "No open seats are left in that game.", request)
            log.info("join game=%s seat=%s %s", gid, seat, self.tag(request))
        return await self._hand_over(request, g, seat, api)

    def _claim(self, gid: str, guest: str, want: str | None) -> str | None:
        return self.store.claim_seat(gid, guest, want)

    async def _hand_over(self, request: Request, g: dict[str, Any], seat: str, api: bool) -> Response:
        gid = g["id"]
        if g["status"] != "running" or not (self.workers.workers.get(gid) and self.workers.workers[gid].alive()):
            if g["status"] == "sleeping" or g["status"] == "running":
                if self.live_games() >= self.cfg.max_games and g["status"] == "sleeping":
                    return self._api_or(api, 503, pages.FULL_TEXT, request, title="Beta full")
                asyncio.create_task(self.start_game(gid, resume=True))
            if api:
                return JSONResponse({"detail": "the game is waking up; retry in a few seconds", "seat": seat},
                                    status_code=503, headers={"retry-after": "5"})
            resp = self.html(pages.waking(self.brand, g["name"]), 503)
            resp.headers["refresh"] = f"4;url=/resume/{gid}"
            return resp
        token = await self.hand_seat(gid, seat)
        if token is None:
            return self._api_or(api, 503, "The game did not answer. Try again in a moment.", request)
        self.activity[gid] = time.time()
        url = self.claim_url(gid, seat, token)
        resp: Response
        if api:
            resp = JSONResponse({"seat": seat, "claim_url": url}, headers={"cache-control": "no-store"})
        else:
            resp = RedirectResponse(url, status_code=303, headers={"cache-control": "no-store"})
        resp.delete_cookie(WATCH_COOKIE_PREFIX + gid, path=f"/g/{gid}/")
        return resp

    async def resume(self, request: Request) -> Response:
        api = request.url.path.startswith("/api/")
        if not api:
            gate = self._need_accept(request)
            if gate:
                return gate
        guest = self.accepted(request)
        if guest is None:
            return self._api_or(api, 403, "Accept the test-game notice first.", request)
        gid = request.path_params["gid"]
        g = self.store.game(gid)
        seat = self.store.guest_seat(gid, guest["id"]) if g else None
        if g is None or seat is None:
            return self._api_or(api, 404, "You do not have a seat in that game.", request)
        if g["status"] in ("finished", "failed", "archived", "stopped"):
            return self._api_or(api, 410 if api else 404, f"That game is {g['status']}.", request)
        if not self.limits.allow("join-guest", guest["id"], self.cfg.joins_per_10min, 600):
            log.info("rate-limit resume game=%s %s", gid, self.tag(request))
            return self._api_or(api, 429, "Too many joins in ten minutes. Try again shortly.", request)
        log.info("resume game=%s seat=%s %s", gid, seat, self.tag(request))
        return await self._hand_over(request, g, seat, api)

    def _confirmed(self, form: dict) -> bool:
        value = form.get("confirm")
        if value is True:
            return True
        return isinstance(value, str) and value.strip().lower() in {"true", "1", "yes", "on"}

    def _end_payload(self, response: Any) -> dict[str, Any]:
        raw = getattr(response, "json", None)
        if not callable(raw):
            return {}
        try:
            data = raw()
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    async def creator_view(self, request: Request) -> Response:
        """Whether this guest created the game, and which seat they hold. Others learn nothing."""
        guest = self.accepted(request)
        g = self.store.game(request.path_params["gid"])
        if guest is None or g is None or g["creator"] != guest["id"]:
            return JSONResponse({"creator": False})
        return JSONResponse({
            "creator": True,
            "seat": self.store.guest_seat(g["id"], guest["id"]),
            "name": g["name"],
            "status": g["status"],
            "ended_by": g.get("ended_by"),
        })

    async def end_game(self, request: Request) -> Response:
        """Creator-only end. confirm=true is sent after the dialog. Anyone else gets 403."""
        api = request.url.path.startswith("/api/") or "application/json" in request.headers.get("content-type", "")
        guest = self.accepted(request)
        if guest is None:
            return self._api_or(api, 403, "Accept the test-game notice first.", request)
        if not self.same_origin(request):
            return self._api_or(api, 403, "That form came from another site.", request)
        gid = request.path_params["gid"]
        g = self.store.game(gid)
        if g is None:
            return self._api_or(api, 404, "That game is not open.", request)
        if g["creator"] != guest["id"]:
            return self._api_or(api, 403, "Only the person who created this game can end it.", request)
        if g["status"] == "finished":
            return self._end_done(request, g, api=api, already=True)
        try:
            form = await self.read_form(request)
        except TooLarge:
            return self._api_or(api, 413, "That request is too large.", request)
        except (FormError, ValueError):
            form = {}
        if not self._confirmed(form):
            return self._api_or(api, 400, "Confirm the end first.", request)
        if g["status"] not in ("running", "starting"):
            return self._api_or(api, 409, "That game is not running.", request)
        response = await self.worker_call(gid, "POST", "/control/end", {})
        if response is None or getattr(response, "status_code", None) != 200:
            return self._api_or(api, 503, "The game did not answer. Try again in a moment.", request)
        payload = self._end_payload(response)
        # The worker stays up so the end screen keeps loading (the same finished
        # state a day-cap game already uses). The idle reaper stops the process.
        if payload.get("ended") is False:
            self.store.set_game(gid, status="finished")
        else:
            self.store.set_game(gid, status="finished", ended_by="creator")
        log.info("end game=%s by=creator", gid)
        return self._end_done(request, self.store.game(gid) or g, api=api, already=False)

    def _end_done(self, request: Request, g: dict[str, Any], *, api: bool, already: bool) -> Response:
        if api:
            return JSONResponse({
                "ok": True, "id": g["id"], "status": g["status"], "ended_by": g.get("ended_by"), "already": already,
            })
        return RedirectResponse("/", status_code=303)

    async def api_games(self, request: Request) -> Response:
        out = []
        for g in self._listed():
            out.append({"id": g["id"], "name": g["name"], "status": g["status"], "open_seats": g["open_seats"],
                        "rules": g["settings"]["rules"], "day": self.live.get(g["id"], {}).get("day")})
        return JSONResponse({"games": out})

    async def api_game(self, request: Request) -> Response:
        g = self.store.game(request.path_params["gid"])
        if g is None:
            return JSONResponse({"detail": "not found"}, status_code=404)
        info = self.live.get(g["id"], {})
        return JSONResponse({"id": g["id"], "name": g["name"], "status": g["status"], "day": info.get("day"),
                             "finished": info.get("finished"), "open_seats":
                             sum(1 for s in self.store.seats(g["id"]) if not s["guest_id"]),
                             "starting_credits": pages.credits_phrase(g["settings"]),
                             "turns_per_day": pages.turns_phrase(g["settings"])})

    async def status(self, request: Request) -> Response:
        open_seats = sum(1 for g in self._listed() for _ in range(g["open_seats"]))
        body = {"online": True, "brand": self.brand, "games_running": self.live_games(), "open_seats": open_seats,
                "full": self.full_for(1), "closed": self.closed}
        headers = {"cache-control": "no-store"}
        origin = (request.headers.get("origin") or "").rstrip("/")
        if origin and origin in self.status_origins:
            headers["access-control-allow-origin"] = origin
            headers["vary"] = "Origin"
        return JSONResponse(body, headers=headers)

    async def healthz(self, request: Request) -> Response:
        return JSONResponse({"ok": True})

    # ------------------------------------------------------------------ watch + proxy
    async def watch(self, request: Request) -> Response:
        gate = self._need_accept(request)
        if gate:
            return gate
        guest = self.accepted(request)
        gid = request.path_params["gid"]
        g = self.store.game(gid)
        if g is None or g["status"] == "archived":
            return self.msg("Not found", "That game does not exist.", 404)
        if self.store.guest_seat(gid, guest["id"]):
            return self.msg("You are playing", "Players seated in a game cannot watch it.", 403)
        if not g["listed"] and not hmac.compare_digest(request.query_params.get("k", ""), self.secrets.watch_key(gid)):
            return self.msg("Link only", "This game is link-only; use the watch link you were sent.", 403)
        resp = RedirectResponse(f"/g/{gid}/", status_code=303)
        resp.set_cookie(WATCH_COOKIE_PREFIX + gid, self.secrets.watch_cookie(gid), max_age=7 * 86400, httponly=True,
                        samesite="lax", secure=self.secure(request), path=f"/g/{gid}/")
        log.info("watch game=%s %s", gid, self.tag(request))
        return resp

    def _route_game(self, request: Request | WebSocket) -> tuple[dict[str, Any] | None, str]:
        gid = request.path_params["gid"]
        return self.store.game(gid), request.path_params.get("rest", "")

    def _spectator_extra(self, request: Request | WebSocket, gid: str, rest: str) -> tuple[bool, dict[str, str]]:
        if rest.rstrip("/") in SPECTATOR_PATHS:
            if not self.watch_ok(request, gid):
                return False, {}
            return True, {"authorization": f"Bearer {self.secrets.spectator_token(gid)}"}
        return True, {}

    async def game_http(self, request: Request) -> Response:
        g, rest = self._route_game(request)
        wants_html = "text/html" in request.headers.get("accept", "")
        if g is None:
            return self.msg("Not found", "That game does not exist.", 404) if wants_html else JSONResponse(
                {"detail": "no such game"}, status_code=404)
        gid = g["id"]
        if self.accepted(request) is None:
            if wants_html and request.method == "GET":
                return self._need_accept(request)
            return JSONResponse({"detail": "accept the test-game notice in the lobby first"}, status_code=403)
        if rest.split("/", 1)[0] in BLOCKED_PATHS:
            return self.msg("Not here", "Use the Watch button in the lobby.", 403)
        ok, extra = self._spectator_extra(request, gid, rest)
        if not ok:
            if wants_html:
                return self.msg("Watch from the lobby", "Use the Watch button in the lobby to see this game.", 403)
            return JSONResponse({"detail": "watch this game from the lobby"}, status_code=403)
        w = self.workers.workers.get(gid)
        if not self._worker_serves(g):
            return await self._not_running(request, g, wants_html)
        if request.method == "POST" and rest.startswith("harness/"):
            who = (guest_id(request.cookies.get(GUEST_COOKIE)) or "") + "|" + self.ip(request)
            if not self.limits.allow("action", who, self.cfg.actions_per_s, 1.0):
                log.info("rate-limit action game=%s %s", gid, self.tag(request))
                return JSONResponse({"detail": "too many actions at once; slow down a little"}, status_code=429,
                                    headers={"retry-after": "1"})
        try:
            body = await self.read_body(request)
        except TooLarge:
            return JSONResponse({"detail": "request too large"}, status_code=413)
        self.activity[gid] = time.time()
        resp = await self.proxy.http(request, w.port, rest, body=body, extra=extra)
        for k, v in _SECURITY_HEADERS.items():
            if k not in ("x-frame-options", "content-security-policy"):
                resp.headers.setdefault(k, v)
        resp.headers["x-frame-options"] = "SAMEORIGIN"
        if self.secure(request):
            resp.raw_headers = [(k, v + b"; Secure" if k == b"set-cookie" and b"secure" not in v.lower() else v)
                                for k, v in resp.raw_headers]
        return resp

    async def _not_running(self, request: Request, g: dict[str, Any], wants_html: bool) -> Response:
        gid = g["id"]
        if g["status"] in ("sleeping", "running", "starting"):
            if g["status"] == "sleeping" and self.live_games() >= self.cfg.max_games:
                return self.msg("Beta full", pages.FULL_TEXT, 503) if wants_html else JSONResponse(
                    {"detail": pages.FULL_TEXT}, status_code=503)
            if not self.lock(gid).locked():
                log.info("wake game=%s %s", gid, self.tag(request))
                asyncio.create_task(self.start_game(gid, resume=True))
            if wants_html:
                return self.html(pages.waking(self.brand, g["name"]), 503)
            return JSONResponse({"detail": "this game is waking up; retry in a few seconds"}, status_code=503,
                                headers={"retry-after": "5"})
        text = {"finished": "This game has finished.", "failed": "This game stopped working and was not restarted.",
                "stopped": "The host stopped this game.", "archived": "This game was archived."}.get(
            g["status"], "This game is not running.")
        return self.msg("Not running", text, 410) if wants_html else JSONResponse({"detail": text}, status_code=410)

    async def game_ws(self, ws: WebSocket) -> None:
        g, rest = self._route_game(ws)
        if g is None or self.accepted(ws) is None:
            await ws.close(code=1008)
            return
        gid = g["id"]
        ok, extra = self._spectator_extra(ws, gid, rest)
        w = self.workers.workers.get(gid)
        if not ok or not self._worker_serves(g):
            await ws.close(code=1008)
            return
        self.open_ws[gid] = self.open_ws.get(gid, 0) + 1
        self.activity[gid] = time.time()
        try:
            await self.proxy.websocket(ws, w.port, rest, extra=extra)
        finally:
            self.open_ws[gid] = max(0, self.open_ws.get(gid, 1) - 1)
            self.activity[gid] = time.time()

    # ------------------------------------------------------------------ admin (this PC only)
    def _admin_ok(self, request: Request) -> bool:
        return is_local_admin(request.headers, request.client.host if request.client else None)

    async def admin(self, request: Request) -> Response:
        if not self._admin_ok(request):
            return self.msg("Not found", "Nothing here.", 404)
        return self.html(pages.admin(self.brand, games=self.store.games(), workers=self.worker_stats(),
                                     closed=self.closed, csrf=self._admin_csrf))

    def worker_stats(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        try:
            import psutil
        except ImportError:
            psutil = None
        for gid, w in self.workers.workers.items():
            if not w.alive():
                continue
            row: dict[str, Any] = {"pid": w.pid, "port": w.port}
            if psutil is not None:
                try:
                    p = psutil.Process(w.pid)
                    row["cpu"] = f"{p.cpu_percent(interval=None):.1f}"
                    row["rss_mb"] = f"{p.memory_info().rss / 1e6:.0f}"
                except psutil.Error:
                    pass
            out[gid] = row
        return out

    async def _admin_form(self, request: Request) -> bool:
        if not self._admin_ok(request) or not self.same_origin(request):
            return False
        try:
            form = await self.read_form(request)
        except (TooLarge, FormError, ValueError):
            return False
        return hmac.compare_digest(str(form.get("csrf", "")), self._admin_csrf)

    async def admin_stop(self, request: Request) -> Response:
        if not await self._admin_form(request):
            return self.msg("Not found", "Nothing here.", 404)
        gid = request.path_params["gid"]
        sleep = request.url.path.endswith("/sleep")
        if self.store.game(gid):
            await self.stop_game(gid, status="sleeping" if sleep else "stopped")
        return RedirectResponse("/admin", status_code=303)

    async def admin_kill(self, request: Request) -> Response:
        if not await self._admin_form(request):
            return self.msg("Not found", "Nothing here.", 404)
        self.store.set_flag("closed", "1")
        log.warning("kill switch: stopping every game")
        for g in self.store.games(LIVE):
            await self.stop_game(g["id"], status="stopped")
        return RedirectResponse("/admin", status_code=303)

    async def admin_shutdown(self, request: Request) -> Response:
        """scripts/selfhost/stop.ps1: a graceful stop (snapshots every game first)."""
        presented = request.headers.get("x-lobby-shutdown", "")
        if not self._admin_ok(request) or not presented or not hmac.compare_digest(presented, self._shutdown_key):
            return self.msg("Not found", "Nothing here.", 404)
        import signal

        log.info("shutdown requested from this PC")
        asyncio.get_running_loop().call_later(0.2, signal.raise_signal, signal.SIGINT)
        return JSONResponse({"ok": True})

    async def admin_open(self, request: Request) -> Response:
        if not await self._admin_form(request):
            return self.msg("Not found", "Nothing here.", 404)
        self.store.set_flag("closed", "0")
        log.info("beta reopened")
        return RedirectResponse("/admin", status_code=303)


class _BodyCap:
    """Refuse oversized bodies before any handler runs (413)."""

    def __init__(self, app, limit: int) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http":
            for k, v in scope.get("headers") or []:
                if k == b"content-length" and v.isdigit() and int(v) > self.limit:
                    body = b'{"detail":"request too large"}'
                    await send({"type": "http.response.start", "status": 413,
                                "headers": [(b"content-type", b"application/json"),
                                            (b"content-length", str(len(body)).encode())]})
                    await send({"type": "http.response.body", "body": body})
                    return
        await self.app(scope, receive, send)


def _apply_lobby_ai_env() -> None:
    """Host switch. Unset leaves the stored default. Only ``on`` and ``off`` are read."""
    import os

    from ..engine import constants as K

    raw = os.environ.get("LOBBY_AI_SEAT_MODE", "").strip().lower()
    if raw in ("on", "off"):
        K.LOBBY_AI_SEAT_MODE = raw


def create_lobby_app(cfg: LobbyConfig | None = None, *, python: str | None = None, port_probe=None) -> Starlette:
    _apply_lobby_ai_env()
    cfg = cfg or LobbyConfig.from_env()
    lobby = Lobby(cfg, python=python, port_probe=port_probe)

    @contextlib.asynccontextmanager
    async def lifespan(app):
        await lobby.startup()
        try:
            yield
        finally:
            await lobby.shutdown()

    routes = [
        Route("/", lobby.home),
        Route("/about", lobby.about),
        Route("/manual", lobby.manual),
        Route("/accept", lobby.accept, methods=["POST"]),
        Route("/new", lobby.new_form, methods=["GET"]),
        Route("/new", lobby.create, methods=["POST"]),
        Route("/join/{gid:str}/{seat:str}", lobby.join_link),
        Route("/games/{gid:str}/join", lobby.join, methods=["POST"]),
        Route("/games/{gid:str}/ai-seat", lobby.ai_seat_view),
        Route("/games/{gid:str}/end", lobby.end_game, methods=["POST"]),
        Route("/resume/{gid:str}", lobby.resume),
        Route("/status", lobby.status),
        Route("/healthz", lobby.healthz),
        Route("/api/accept", lobby.accept, methods=["POST"]),
        Route("/api/games", lobby.api_games, methods=["GET"]),
        Route("/api/games", lobby.create, methods=["POST"]),
        Route("/api/games/{gid:str}", lobby.api_game, methods=["GET"]),
        Route("/api/games/{gid:str}/join", lobby.join, methods=["POST"]),
        Route("/api/games/{gid:str}/end", lobby.end_game, methods=["POST"]),
        Route("/api/games/{gid:str}/creator", lobby.creator_view, methods=["GET"]),
        Route("/api/games/{gid:str}/resume", lobby.resume, methods=["POST"]),
        Route("/admin", lobby.admin),
        Route("/admin/games/{gid:str}/stop", lobby.admin_stop, methods=["POST"]),
        Route("/admin/games/{gid:str}/sleep", lobby.admin_stop, methods=["POST"]),
        Route("/admin/kill", lobby.admin_kill, methods=["POST"]),
        Route("/admin/open", lobby.admin_open, methods=["POST"]),
        Route("/admin/shutdown", lobby.admin_shutdown, methods=["POST"]),
        Route("/g/{gid:str}/watch", lobby.watch),
        # Bare /g/<id> goes through the watch gate (cookie, then the spectator page).
        # /g/<id>/ is that page: /watch already 303s here, so sending it back to
        # /watch would loop. Without the cookie it stays the 403 from the lobby.
        Route("/g/{gid:str}", lambda r: RedirectResponse(f"/g/{r.path_params['gid']}/watch", status_code=307)),
        WebSocketRoute("/g/{gid:str}/{rest:path}", lobby.game_ws),
        Route("/g/{gid:str}/{rest:path}", lobby.game_http,
              methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]),
    ]
    app = Starlette(routes=routes, lifespan=lifespan)
    app.state.lobby = lobby
    app.add_middleware(_BodyCap, limit=cfg.body_limit)
    return app


def run(cfg: LobbyConfig | None = None) -> None:
    import uvicorn

    from .config import port_is_free

    cfg = cfg or LobbyConfig.from_env()
    if not port_is_free(cfg.port, cfg.host):
        raise SystemExit(f"port {cfg.port} is busy; the lobby will not start on it")
    uvicorn.run(create_lobby_app(cfg), host=cfg.host, port=cfg.port, access_log=False, log_level="warning",
                ws="websockets", proxy_headers=False, timeout_graceful_shutdown=5)
