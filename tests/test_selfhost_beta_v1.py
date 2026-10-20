"""selfhost-beta-v1 (COMMANDER NOTE 61): lobby, guest seats, tunnel docs, disclaimer + brand,
snapshots and lifecycle, spectator watch links, Netlify plan.

Workers are faked here (no subprocess, no ports); tests/test_selfhost_beta_live_v1.py runs the
real lobby and worker processes on free ephemeral ports.

Tier S plants (each must turn a test red):
  ps1 PublicLock lets every path through        -> test_item2_public_mode_answers_only_the_lobby
  ps2 the lobby stores the seat token, not hash -> test_item2_seat_token_is_handed_over_once_and_only_hashed
  ps3 caps ignored (full_for returns False)      -> test_item1_the_eleventh_game_gets_beta_full
  ps4 watch cookie not checked                   -> test_item6_spectator_routes_need_the_watch_cookie
  ps5 rewrite always applies the brand           -> test_item4_unset_brand_and_base_leave_every_page_byte_for_byte
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.testclient import TestClient

import tw2k.engine.constants as K
from tw2k.public import config as C
from tw2k.public import pages
from tw2k.public import security as S
from tw2k.public import worker as W
from tw2k.public import workers as WM
from tw2k.public.lobby import create_lobby_app
from tw2k.public.proxy import strip_lobby_cookies, upstream_headers

REPO = Path(__file__).resolve().parents[1]
WEB = REPO / "web"


class FakeWorker:
    def __init__(self, port: int) -> None:
        self.port = port
        self.pid = 4242
        self.stopping = False
        self.up = True

    def alive(self) -> bool:
        return self.up


def _cfg(tmp_path: Path, holds: list[int], **kw) -> C.LobbyConfig:
    from tests._cu_host import LOBBY_FREE_START, free_port

    if "port" not in kw:
        kw["port"] = free_port(LOBBY_FREE_START)
        holds.append(kw["port"])
    if "game_ports" not in kw:
        base = free_port(LOBBY_FREE_START, count=10)
        kw["game_ports"] = range(base, base + 10)
        holds.extend(kw["game_ports"])
    base = dict(root=tmp_path / "selfhost", tick_s=3600.0)
    base.update(kw)
    return C.LobbyConfig(**base)


@pytest.fixture
def make_lobby(tmp_path, monkeypatch):
    for name in ("TW2K_PUBLIC_MODE", "TW2K_BRAND", "TW2K_BASE_PATH", "TW2K_SPECTATOR_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    made = []
    holds: list[int] = []

    def _make(client=("testclient", 50000), **kw):
        cfg = _cfg(tmp_path, holds, **kw)
        app = create_lobby_app(cfg, port_probe=lambda p: True)
        lob = app.state.lobby
        lob.started, lob.calls, lob.proxied = [], [], []
        games = list(cfg.game_ports)

        async def fake_start(gid, *, resume):
            lob.workers.workers[gid] = FakeWorker(games[len(lob.started)])
            lob.store.set_game(gid, status="running", port=lob.workers.workers[gid].port)
            lob.started.append((gid, resume))
            return True

        async def fake_call(gid, method, path, body=None):
            lob.calls.append((path, body))
            return SimpleNamespace(status_code=200)

        async def fake_proxy(request, port, rest, *, body, extra=None):
            lob.proxied.append((rest, extra))
            return Response("ok")

        async def fake_stop(gid, *, lobby_secret, spectator_token, graceful=True):
            lob.workers.workers.pop(gid, None)

        lob.start_game = fake_start
        lob.worker_call = fake_call
        lob.proxy.http = fake_proxy
        lob.workers.stop = fake_stop
        tc = TestClient(app, client=client)
        tc.__enter__()
        made.append(tc)
        return tc, lob

    yield _make
    for tc in made:
        tc.__exit__(None, None, None)
    from tests._port_lock import release_ports

    release_ports(*holds)


def _accept(c) -> None:
    assert c.post("/api/accept", json={}).status_code == 200


def _game(c, **kw) -> dict:
    body = {"name": "Test game", "humans": 1, "bots": 2}
    body.update(kw)
    r = c.post("/api/games", json=body)
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------ item 1: lobby + process model


def test_item1_ports_stay_inside_the_beta_range() -> None:
    with pytest.raises(ValueError, match="protected"):
        C.LobbyConfig(port=8058)
    with pytest.raises(ValueError, match="protected"):
        C.LobbyConfig(game_ports=range(8090, 8101))
    with pytest.raises(ValueError, match="loopback"):
        C.LobbyConfig(host="0.0.0.0")
    assert C.LobbyConfig().port == 8099 and C.LobbyConfig().game_ports == range(8100, 8120)
    assert C.parse_port_range("8100-8119") == range(8100, 8120)
    assert C.LobbyConfig(game_ports=range(8100, 8103), max_games=10).max_games == 3
    with pytest.raises(ValueError):
        C.parse_port_range("8100-9000")
    cfg = C.LobbyConfig(game_ports=range(8100, 8104))
    busy = {8100}
    assert C.pick_port(cfg, {8101}, probe=lambda p: p not in busy) == 8102
    assert C.pick_port(cfg, {8100, 8101, 8102, 8103}, probe=lambda p: True) is None
    with pytest.raises(RuntimeError):
        C.assert_lobby_port(cfg, 8045)


def test_item1_each_game_is_one_serve_worker_with_its_own_switches(tmp_path) -> None:
    form = S.parse_game_form({"name": "Alpha", "humans": 2, "bots": 3, "ferrengi": "off", "day": "1h"})
    st = form.settings()
    cmd = WM.serve_command(st, 8101, tmp_path)
    joined = " ".join(cmd)
    assert cmd[1:4] == ["-m", "tw2k.cli", "serve"]
    for part in ("--port 8101", "--agent-kind heuristic", "--external P1,P2", "--num-agents 5", "--day-seconds 3600",
                 "--universe-size 1000", "--no-ferrengi", "--external-idle-wait-s 3"):
        assert part in joined
    base = {"TW2002_HAGGLE_LIVE": "1", "TW2K_SPECTATOR_TOKEN": "x" * 40, "AI_COCKPIT_SEAT_MODE": "llm",
            "COCKPIT_LAYOUT": "legacy", "PATH": "p"}
    env = WM.worker_env(gid="ab12cd34", settings=st, game_dir=tmp_path, brand="Galaxy War Command",
                        lobby_secret="L" * 64, spectator_token="T" * 64, seat_tokens={"P1": "a" * 43, "P2": "b" * 43},
                        resume=None, base=base)
    assert "TW2002_HAGGLE_LIVE" not in env and "AI_COCKPIT_SEAT_MODE" not in env
    assert env["COCKPIT_LAYOUT"] == "redesign" and env["TW2K_PUBLIC_MODE"] == "1"
    assert json.loads(env["TW2K_SWITCH_OVERLAY"]) == {
        "DAY_ROLL_CLOCK_MODE": "live", "LEGACY_DAY_CLOCK_MODE": "live", "V311_PROFILE": "v311",
    }
    assert env["TW2K_BASE_PATH"] == "/g/ab12cd34" and env["TW2K_SPECTATOR_TOKEN"] == "T" * 64
    assert env["TW2K_EXTERNAL_TOKEN_P1"] == "a" * 43 and "a" * 43 not in joined
    legacy = S.parse_game_form({"name": "B", "rules": "legacy", "starting_package": "v311"}).settings()
    assert WM.switch_overlay(legacy) == {
        "DAY_ROLL_CLOCK_MODE": "live",
        "LEGACY_DAY_CLOCK_MODE": "live",
        "PORT_STOCK_FIDELITY_MODE": "live",
        "SEAT_IDLE_START_MODE": "live",
        "STARTING_PACKAGE_MODE": "live",
    }
    classic = S.parse_game_form({"name": "C", "rules": "legacy", "starting_package": "classic"}).settings()
    assert WM.switch_overlay(classic) == {
        "DAY_ROLL_CLOCK_MODE": "live",
        "LEGACY_DAY_CLOCK_MODE": "live",
        "PORT_STOCK_FIDELITY_MODE": "live",
        "SEAT_IDLE_START_MODE": "live",
    }


def test_item1_switch_overlay_sets_only_named_switches(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", K.V311_PROFILE)
    assert W.apply_switch_overlay('{"V311_PROFILE": "v311"}') == {"V311_PROFILE": "v311"}
    assert K.v311_profile()
    for bad in ('{"DEFAULT_UNIVERSE_SIZE": "5"}', '{"NOPE_MODE": "live"}', '{"V311_PROFILE": "x; rm"}', "[1]"):
        with pytest.raises(ValueError):
            W.apply_switch_overlay(bad)
    assert W.apply_switch_overlay("") == {}


def test_item1_new_game_screen_has_every_field_with_the_defaults(make_lobby) -> None:
    c, _ = make_lobby()
    _accept(c)
    html = c.get("/new").text
    for field in ("name", "rules", "universe_size", "max_days", "turns_per_day", "starting_package", "bots",
                  "ferrengi", "day", "humans", "visibility"):
        assert f'name="{field}"' in html
    assert '<option value="v311" selected>v3.11 (recommended)' in html
    assert '<option value="legacy">Legacy' in html
    assert '<option value="1000" selected>' in html and '<option value="30m" selected>' in html
    for preset in ("10m", "30m", "1h", "24h"):
        assert f'<option value="{preset}"' in html
    assert [f'<option value="{n}"' in html for n in range(6)] == [True] * 6


def test_item1_the_eleventh_game_gets_beta_full(make_lobby) -> None:
    c, lob = make_lobby(max_games=10, max_human_seats=10)
    _accept(c)
    lob.cfg.new_games_per_hour = 100
    for i in range(10):
        _game(c, name=f"G{i}")
    r = c.post("/api/games", json={"name": "Eleven", "humans": 1})
    assert r.status_code == 503 and r.json()["detail"] == "The beta is full right now, try again later"
    r = c.post("/new", data={"name": "Eleven"})
    assert r.status_code == 503 and "The beta is full right now, try again later" in r.text
    assert "The beta is full right now" in c.get("/").text


def test_item1_human_seat_cap_counts_open_seats(make_lobby) -> None:
    c, lob = make_lobby(max_human_seats=5)
    _accept(c)
    _game(c, name="Four", humans=4)
    assert c.post("/api/games", json={"name": "Two", "humans": 2}).status_code == 503
    assert c.post("/api/games", json={"name": "One", "humans": 1}).status_code == 200


@pytest.mark.skipif(os.name != "nt", reason="Windows job object")
def test_item1_workers_die_with_the_lobby_job_object() -> None:
    import ctypes

    job = WM.JobObject()
    assert job.handle is not None
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        assert job.assign(child)
        ctypes.WinDLL("kernel32").CloseHandle(ctypes.c_void_p(job.handle))
        child.wait(timeout=10)
        assert child.returncode is not None
    finally:
        if child.poll() is None:
            child.kill()


# ------------------------------------------------------------------ item 2: guest join + tokens


def test_item2_guest_cookie_is_httponly_lax_and_only_its_hash_is_stored(make_lobby, tmp_path) -> None:
    c, lob = make_lobby()
    r = c.get("/")
    cookie = r.headers["set-cookie"]
    assert cookie.startswith("gwc_guest=") and "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert "Secure" not in cookie
    value = c.cookies.get("gwc_guest")
    assert len(value) >= 43
    raw = (tmp_path / "selfhost" / "lobby.sqlite3").read_bytes()
    assert value.encode() not in raw
    assert lob.store.guest(hashlib.sha256(value.encode()).hexdigest()) is not None
    fresh = TestClient(c.app)
    assert "Secure" in fresh.get("/", headers={"x-forwarded-proto": "https"}).headers["set-cookie"]


def test_item2_seat_token_is_handed_over_once_and_only_hashed(make_lobby, tmp_path) -> None:
    c, lob = make_lobby()
    _accept(c)
    g = _game(c, humans=1)
    r = c.post(f"/api/games/{g['id']}/join", json={})
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    url = r.json()["claim_url"]
    assert url.startswith(f"/g/{g['id']}/bot/claim?seat=P1&token=")
    token = url.split("token=")[1]
    assert lob.calls[-1] == ("/control/seat-token", {"seat": "P1", "token": token})
    seat = lob.store.seats(g["id"])[0]
    assert seat["token_hash"] == hashlib.sha256(token.encode()).hexdigest()
    lob.store.close()
    for f in (tmp_path / "selfhost").glob("lobby.sqlite3*"):
        assert token.encode() not in f.read_bytes()
    lob.store.__init__(lob.cfg.db_path)
    r2 = c.post(f"/api/games/{g['id']}/resume", json={})
    token2 = r2.json()["claim_url"].split("token=")[1]
    assert token2 == token
    assert lob.seat_links[g["id"]]["P1"] == token
    assert lob.store.seats(g["id"])[0]["token_hash"] == hashlib.sha256(token2.encode()).hexdigest()
    other = TestClient(c.app)
    _accept(other)
    assert other.post(f"/api/games/{g['id']}/join", json={}).status_code == 409


def test_tokens_from_both_old_paths_still_authenticate(make_lobby, tmp_path) -> None:
    """A printed #70 link and a saved #73 file token both still open the seat.

    The worker learns the raw token. Authentication is the harness compare
    against that token. The sqlite row keeps only the sha256.
    """
    from tw2k.public.security import new_seat_token, sha256_hex
    from tw2k.server.harness_tokens import verify

    c, lob = make_lobby()
    _accept(c)
    published = new_seat_token()
    g = _game(c, humans=1)
    gid = g["id"]
    lob.seat_links[gid] = {"P1": published}
    lob.store.set_seat_hash(gid, "P1", sha256_hex(published))
    path = lob._seat_token_path(gid)
    if path.exists():
        path.unlink()
    joined = c.post(f"/api/games/{gid}/join", json={})
    assert joined.status_code == 200, joined.text
    handed = joined.json()["claim_url"].split("token=", 1)[1]
    worker = lob.calls[-1][1]["token"]
    assert handed == published == worker
    assert verify(published, worker)
    assert not verify(new_seat_token(), worker)
    assert lob.store.seats(gid)[0]["token_hash"] == sha256_hex(published)
    assert published.encode() not in (tmp_path / "selfhost" / "lobby.sqlite3").read_bytes()
    lob.seat_links.clear()
    again = c.post(f"/api/games/{gid}/resume", json={})
    assert again.json()["claim_url"].split("token=", 1)[1] == published
    assert verify(published, lob.calls[-1][1]["token"])

    filed = new_seat_token()
    g2 = _game(c, humans=1)
    gid2 = g2["id"]
    lob.seat_links.pop(gid2, None)
    lob.store.set_seat_hash(gid2, "P1", None)
    lob._store_seat_tokens(gid2, {"P1": filed})
    mode = lob._seat_token_path(gid2).stat().st_mode & 0o777
    assert mode == 0o600
    lob.seat_links.clear()
    joined2 = c.post(f"/api/games/{gid2}/join", json={})
    assert joined2.status_code == 200, joined2.text
    handed2 = joined2.json()["claim_url"].split("token=", 1)[1]
    worker2 = lob.calls[-1][1]["token"]
    assert handed2 == filed == worker2
    assert verify(filed, worker2)
    assert not verify(published, worker2)
    assert lob.store.seats(gid2)[0]["token_hash"] == sha256_hex(filed)
    assert filed.encode() not in (tmp_path / "selfhost" / "lobby.sqlite3").read_bytes()


def test_item2_one_join_link_per_open_seat(make_lobby) -> None:
    c, lob = make_lobby()
    _accept(c)
    g = _game(c, humans=3, visibility="link")
    links = g["join_links"]
    assert sorted(links) == ["P1", "P2", "P3"]
    friend = TestClient(c.app)
    _accept(friend)
    assert friend.post(f"/api/games/{g['id']}/join", json={}).status_code == 403
    k = links["P2"].split("k=")[1]
    page = friend.get(f"/join/{g['id']}/P2?k={k}")
    assert "Take this seat" in page.text and lob.store.seats(g["id"])[1]["guest_id"] is None
    assert friend.get(f"/join/{g['id']}/P2?k=wrong").status_code == 404
    r = friend.post(f"/api/games/{g['id']}/join", json={"seat": "P2", "k": k})
    assert r.status_code == 200 and r.json()["seat"] == "P2"


def test_created_page_prints_one_copyable_cockpit_link_per_seat(make_lobby) -> None:
    """Each human seat gets an https cockpit link when the request is forwarded."""
    from tw2k.public.workers import seat_ids

    c, lob = make_lobby(client=("127.0.0.1", 5000))
    real = lob.start_game

    async def start(gid, *, resume):
        ok = await real(gid, resume=resume)
        game = lob.store.game(gid) or {}
        humans = int((game.get("settings") or {}).get("humans") or 1)
        lob.seat_links[gid] = {seat: f"tok{seat}" for seat in seat_ids(humans)}
        return ok

    lob.start_game = start
    _accept(c)
    headers = {
        "host": "127.0.0.1:8020",
        "x-forwarded-host": "blue-pond.trycloudflare.com",
        "x-forwarded-proto": "https",
    }
    r = c.post("/api/games", json={"name": "Links", "humans": 2}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    gid = body["id"]
    links = body["cockpit_links"]
    assert sorted(links) == ["P1", "P2"]
    for seat in ("P1", "P2"):
        assert links[seat] == (
            f"https://blue-pond.trycloudflare.com/g/{gid}/bot?seat={seat}&token=tok{seat}&layout=redesign"
        )
    page = c.post("/new", data={"name": "Page", "humans": "2"}, headers=headers)
    assert page.status_code == 200, page.text
    assert "user-select:all" in page.text
    assert page.text.count('data-testid="seat-link"') == 2
    assert "layout=redesign" in page.text
    assert "Send each player their cockpit link" in page.text
    assert "Lobby invite P1" in page.text
    opened = c.get(f"/g/{gid}/bot?seat=P1&token=tokP1", headers={"accept": "text/html"})
    assert opened.status_code == 200
    guest = lob.store.guest(hashlib.sha256(c.cookies.get("gwc_guest").encode()).hexdigest())
    assert lob.store.guest_seat(gid, guest["id"]) == "P1"
    c.get(f"/g/{gid}/bot?seat=P2&token=not-the-token", headers={"accept": "text/html"})
    assert lob.store.seats(gid)[1]["guest_id"] is None


def _lock_app() -> Starlette:
    async def ok(request):
        return PlainTextResponse("ok")

    async def ws(websocket):
        await websocket.accept()
        await websocket.send_text("hi")
        await websocket.close()

    routes = [Route(p, ok, methods=["GET", "POST"]) for p in
              ("/control/pause", "/api/human/action", "/bot", "/harness/v1/P1/observation", "/state", "/admin/x")]
    routes.append(WebSocketRoute("/ws", ws))
    routes.append(WebSocketRoute("/control/ws", ws))
    return Starlette(routes=routes)


def test_item2_public_mode_answers_only_the_lobby(monkeypatch) -> None:
    monkeypatch.setenv(W.ENV_LOBBY_SECRET, "s" * 64)
    app = W.PublicLock(_lock_app())
    outside = TestClient(app)
    for path in ("/control/pause", "/api/human/action", "/admin/x"):
        r = outside.post(path, headers={W.LOBBY_HEADER: "s" * 64})
        assert r.status_code == 404 and r.json() == {"detail": "not available in this game"}
    for path in ("/bot", "/harness/v1/P1/observation", "/state"):
        assert outside.get(path).status_code == 200
    with outside.websocket_connect("/ws") as s:
        assert s.receive_text() == "hi"
    with pytest.raises(Exception), outside.websocket_connect("/control/ws"):
        pass
    lobby = TestClient(app, client=("127.0.0.1", 5000))
    assert lobby.post("/control/pause", headers={W.LOBBY_HEADER: "s" * 64}).status_code == 200
    assert lobby.post("/control/pause", headers={W.LOBBY_HEADER: "wrong"}).status_code == 404
    assert lobby.post("/control/pause").status_code == 404


def test_direct_cockpit_loads_manual_and_static_under_the_base_path(monkeypatch) -> None:
    """The scripted seat opens the worker's own /bot page. That page points at
    /g/<id>/static and /g/<id>/manual. Those land on the real routes. /control stays closed."""
    monkeypatch.setenv(W.ENV_LOBBY_SECRET, "s" * 64)
    seen: list[str] = []

    async def ok(request):
        seen.append(request.scope["path"])
        return PlainTextResponse("manual page" if request.scope["path"] == "/manual" else "ok")

    routes = [
        Route("/manual", ok),
        Route("/static/{rest:path}", ok),
        Route("/control/end", ok, methods=["POST"]),
    ]
    inner = Starlette(routes=routes)
    inner.add_middleware(W.PublicLock)
    inner.add_middleware(W.PageRewrite, base="/g/abc", brand_name="")
    inner.add_middleware(W.AcceptBasePath, base="/g/abc")
    outside = TestClient(inner)
    manual = outside.get("/g/abc/manual")
    assert manual.status_code == 200 and "manual page" in manual.text
    static = outside.get("/g/abc/static/redesign.js")
    assert static.status_code == 200
    assert seen == ["/manual", "/static/redesign.js"]
    direct = outside.get("/manual")
    assert direct.status_code == 200
    blocked = outside.post("/g/abc/control/end")
    assert blocked.status_code == 404 and blocked.json() == {"detail": "not available in this game"}
    lobby = TestClient(inner, client=("127.0.0.1", 5000))
    assert lobby.post("/g/abc/control/end", headers={W.LOBBY_HEADER: "s" * 64}).status_code == 200


def test_item2_public_worker_refuses_to_start_without_its_secrets(monkeypatch) -> None:
    from fastapi import FastAPI

    monkeypatch.setenv(W.ENV_PUBLIC_MODE, "1")
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    monkeypatch.setenv(W.ENV_LOBBY_SECRET, "s" * 64)
    with pytest.raises(RuntimeError, match="TW2K_SPECTATOR_TOKEN"):
        W.install(FastAPI(), SimpleNamespace())


def test_item2_rate_limits_answer_429_with_a_readable_message(make_lobby) -> None:
    c, lob = make_lobby()
    _accept(c)
    for i in range(3):
        _game(c, name=f"R{i}")
    r = c.post("/api/games", json={"name": "R4"})
    assert r.status_code == 429 and "most games allowed for one hour" in r.json()["detail"]
    r = c.post("/new", data={"name": "R4"})
    assert r.status_code == 429 and "Slow down" in r.text
    lob.cfg.joins_per_10min = 2
    gid = lob.store.games()[0]["id"]
    assert c.post(f"/api/games/{gid}/join", json={}).status_code == 200
    assert c.post(f"/api/games/{gid}/resume", json={}).status_code == 200
    r = c.post(f"/api/games/{gid}/resume", json={})
    assert r.status_code == 429 and "Too many joins" in r.json()["detail"]
    lob.cfg.actions_per_s = 3
    codes = [c.post(f"/g/{gid}/harness/v1/P1/action", json={}).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429
    log = (lob.cfg.logs_dir / "lobby.log").read_text(encoding="utf-8")
    for bucket in ("rate-limit new-game", "rate-limit resume", "rate-limit action"):
        assert bucket in log


def test_item2_body_cap_and_field_validation(make_lobby) -> None:
    c, _ = make_lobby()
    _accept(c)
    r = c.post("/api/games", content=b"x" * (70 * 1024), headers={"content-type": "application/json"})
    assert r.status_code == 413
    bad = [({"name": ""}, "game name"), ({"name": "<script>"}, "game name"), ({"name": "A", "bots": 6}, "bots"),
           ({"name": "A", "humans": 0}, "humans"), ({"name": "A", "universe_size": 1234}, "universe size"),
           ({"name": "A", "day": "5m"}, "day length"), ({"name": "A", "rules": "x"}, "rules"),
           ({"name": "A", "rules": "v311", "starting_package": "classic"}, "v3.11 starting package"),
           ({"name": "A", "max_days": 0}, "max_days"), ({"name": "A", "evil": 1}, "unknown field"),
           ({"name": "A", "bots": True}, "bots")]
    for body, msg in bad:
        r = c.post("/api/games", json=body)
        assert r.status_code == 400 and msg in r.json()["detail"], (body, r.text)
    r = c.post("/new", data={"name": "A", "bots": "9"})
    assert r.status_code == 400 and "bots must be between 0 and 5" in r.text
    r = c.post("/api/games", json={"name": "A"}, headers={"origin": "https://evil.example"})
    assert r.status_code == 403


def test_item2_proxy_keeps_lobby_secrets_and_cookies_away_from_games() -> None:
    hdrs = {"x-tw2k-lobby": "forged", "cf-connecting-ip": "8.8.8.8", "host": "x", "accept": "a",
            "cookie": "gwc_guest=abc; tw2k_seat_P1=tok; gwc_w_ab12=def"}
    out = dict(upstream_headers(hdrs, {"authorization": "Bearer spec"}, drop={"x-tw2k-lobby", "cf-connecting-ip",
                                                                              "host"}))
    assert out == {"accept": "a", "cookie": "tw2k_seat_P1=tok", "authorization": "Bearer spec"}
    assert strip_lobby_cookies("gwc_guest=1") == ""
    assert S.client_ip({"cf-connecting-ip": "203.0.113.9"}, "127.0.0.1") == "203.0.113.9"
    assert S.client_ip({"cf-connecting-ip": "203.0.113.9"}, "198.51.100.4") == "198.51.100.4"
    assert not S.is_local_admin({"cf-connecting-ip": "203.0.113.9"}, "127.0.0.1")
    assert S.is_local_admin({}, "127.0.0.1") and not S.is_local_admin({}, "10.0.0.2")


# ------------------------------------------------------------------ item 3: Cloudflare Tunnel plan


def test_item3_tunnel_plan_and_scripts_cover_every_step() -> None:
    plan = (REPO / "docs" / "plans" / "selfhost-beta-v1.md").read_text(encoding="utf-8")
    for needle in ("winget install --id Cloudflare.cloudflared", "cloudflared tunnel --url http://127.0.0.1:8099",
                   "cloudflared tunnel login", "cloudflared tunnel create", "cloudflared tunnel route dns",
                   "service: http_status:404", "cloudflared service install", "websocket", "thesingularity.netlify.app",
                   "powercfg", "does not expose", "Stop"):
        assert needle in plan, needle
    for name in ("start.ps1", "stop.ps1", "status.ps1"):
        text = (REPO / "scripts" / "selfhost" / name).read_text(encoding="utf-8")
        assert "0.0.0.0" not in text
    assert "8099" in (REPO / "scripts" / "selfhost" / "start.ps1").read_text(encoding="utf-8")
    assert "lobby.shutdown.key" in (REPO / "scripts" / "selfhost" / "stop.ps1").read_text(encoding="utf-8")


# ------------------------------------------------------------------ item 4: disclaimer + brand


def test_item4_disclaimer_must_be_accepted_once_and_is_linked_in_the_footer(make_lobby) -> None:
    c, _ = make_lobby()
    first = c.get("/")
    assert "I understand" in first.text and "New game" not in first.text
    for point in pages.DISCLAIMER_POINTS:
        assert point in first.text
    assert 'href="/about"' in first.text
    assert c.get("/new").text.count("I understand") == 1
    assert c.post("/api/games", json={"name": "A"}).status_code == 403
    r = c.post("/accept", data={"next": "/new"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/new"
    lobby = c.get("/").text
    assert "I understand" not in lobby and "New game" in lobby and 'href="/about"' in lobby
    assert "AI players are not available yet" in c.get("/about").text
    assert c.post("/accept", data={"next": "//evil.example"}, follow_redirects=False).headers["location"] == "/"


SERVED = ("index.html", "redesign.html", "bot.html", "app.js", "redesign.js", "media-player.js", "style.css",
          "redesign.css")


def test_item4_unset_brand_and_base_leave_every_page_byte_for_byte(monkeypatch) -> None:
    for name in SERVED:
        text = (WEB / name).read_text(encoding="utf-8")
        path = {"index.html": "/", "redesign.html": "/bot"}.get(name, f"/static/{name}")
        assert W.rewrite_text(path, text, base="", brand_name="") == text, name
    for name in (W.ENV_PUBLIC_MODE, W.ENV_BASE_PATH, W.ENV_BRAND, W.ENV_SNAPSHOT_DIR):
        monkeypatch.delenv(name, raising=False)
    from tw2k.server.app import create_app

    app = create_app(seed=7, universe_size=60, num_agents=2, agent_kind="heuristic", auto_start=False)
    kinds = {m.cls.__name__ for m in app.user_middleware}
    assert "PublicLock" not in kinds and "PageRewrite" not in kinds
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/control/seat-token" not in paths and "/healthz" not in paths


def test_item4_brand_replaces_only_player_facing_names() -> None:
    brand = "Galaxy War Command"
    red = (WEB / "redesign.html").read_text(encoding="utf-8")
    out = W.rewrite_text("/bot", red, base="", brand_name=brand)
    assert "<title>Galaxy War Command</title>" in out and "TRADE WARS 2002" not in out
    assert W._frame(brand) == "  GALAXY WAR COMMAND  " and len(W._frame(brand)) == len(W.TITLE_FRAME_OLD)
    idx = W.rewrite_text("/", (WEB / "index.html").read_text(encoding="utf-8"), base="", brand_name=brand)
    assert "<title>Galaxy War Command - Spectator</title>" in idx and "<h1>Galaxy War Command</h1>" in idx
    assert "AI Exhibition Match" not in idx and W.BRAND_LINE in idx
    app_js = (WEB / "app.js").read_text(encoding="utf-8")
    out_js = W.rewrite_text("/static/app.js", app_js, base="", brand_name=brand)
    assert "`Galaxy War Command - Day " in out_js and "`TW2K - Day " not in out_js
    assert out_js.count("tw2k") == app_js.count("tw2k")
    based = W.rewrite_text("/static/redesign.js", (WEB / "redesign.js").read_text(encoding="utf-8"),
                           base="/g/ab12cd34", brand_name="")
    assert '"/g/ab12cd34/harness/v1"' in based and '"/harness/v1"' not in based
    assert W.rewrite_location("/bot?seat=P1", "/g/ab12cd34") == "/g/ab12cd34/bot?seat=P1"
    assert W.rewrite_cookie("tw2k_seat_P1=x; Path=/harness/; HttpOnly", "/g/ab12cd34").endswith(
        "Path=/g/ab12cd34/harness/; HttpOnly")


# ------------------------------------------------------------------ item 5: snapshots + lifecycle


def _fake_runner(universe, day_mark=123.0):
    return SimpleNamespace(state=SimpleNamespace(universe=universe, status="running"), _live_day_mark=day_mark)


def test_item5_snapshots_are_atomic_keep_three_and_round_trip(tmp_path) -> None:
    from tw2k.engine import GameConfig, generate_universe

    u = generate_universe(GameConfig(seed=11, universe_size=60))
    runner = _fake_runner(u)
    paths = []
    for i in range(5):
        paths.append(W.write_snapshot(runner, f"r{i}", tmp_path))
        time.sleep(0.002)
    files = sorted(p.name for p in tmp_path.iterdir())
    assert files == sorted(p.name for p in paths[-3:]) and not any(f.endswith(".tmp") for f in files)
    meta, u2 = W.load_snapshot(W.latest_snapshot(tmp_path))
    assert meta["reason"] == "r4" and meta["day_started_at"] == 123.0
    assert u2.model_dump_json() == u.model_dump_json()
    runner._last_snapshot_at = time.time()
    runner._snapshot_dir = tmp_path
    before = W.latest_snapshot(tmp_path)
    W.maybe_snapshot(runner)
    assert W.latest_snapshot(tmp_path) == before
    W.maybe_snapshot(runner, rolled=True)
    assert W.latest_snapshot(tmp_path) != before


def test_item5_a_resumed_game_continues_from_its_snapshot(tmp_path, monkeypatch) -> None:
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.server.broadcaster import Broadcaster
    from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec

    cfg = GameConfig(seed=31, universe_size=80, max_days=3, enable_ferrengi=False, action_delay_s=0.0)
    u = generate_universe(cfg)
    from tw2k.engine.models import Player

    u.players["P1"] = Player(id="P1", name="Saved", credits=777_777, sector_id=1)
    u.day = 2
    snap = W.write_snapshot(_fake_runner(u, 1000.0), "test", tmp_path / "snaps")
    spec = MatchSpec(config=cfg, agents=[AgentSpec(player_id="P1", name="Saved", kind="heuristic")],
                     action_delay_s=0.0, paused=True, resume_from=str(snap))
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")

    async def go():
        await runner.start(spec)
        for _ in range(400):
            if runner.state.universe is not None and runner.state.agents:
                break
            await asyncio.sleep(0.01)
        got = runner.state.universe
        await runner.stop()
        return got

    got = asyncio.run(go())
    assert got.players["P1"].credits == 777_777 and got.day == 2
    assert not any(getattr(e, "kind", None) == "game_start" for e in got.events[-5:])


def test_item5_idle_games_sleep_and_wake_on_the_next_visit(make_lobby) -> None:
    c, lob = make_lobby()
    _accept(c)
    g = _game(c)
    lob.cfg.idle_s = 60.0
    lob.activity[g["id"]] = time.time() - 120
    lob.store._x("UPDATE games SET last_activity=? WHERE id=?", (time.time() - 120, g["id"]))
    asyncio.run(lob.tick())
    assert lob.store.game(g["id"])["status"] == "sleeping"
    r = c.get(f"/g/{g['id']}/bot", headers={"accept": "text/html"})
    assert r.status_code == 503 and "Waking up" in r.text
    time.sleep(0.2)
    assert lob.started[-1] == (g["id"], True)


def test_item5_a_crashed_worker_restarts_once_then_is_marked_failed(make_lobby) -> None:
    c, lob = make_lobby()
    _accept(c)
    g = _game(c)
    lob.workers.workers[g["id"]].up = False
    asyncio.run(lob.tick())
    assert lob.started[-1] == (g["id"], True) and lob.store.game(g["id"])["restarts"] == 1
    lob.workers.workers[g["id"]].up = False
    asyncio.run(lob.tick())
    row = lob.store.game(g["id"])
    assert row["status"] == "failed" and "second crash" in row["note"]
    assert "stopped working" in c.get(f"/g/{g['id']}/bot", headers={"accept": "text/html"}).text


def test_item5_old_games_are_archived_not_deleted(make_lobby) -> None:
    c, lob = make_lobby()
    _accept(c)
    g = _game(c)
    gdir = lob.workers.game_dir(g["id"])
    (gdir / "snapshots").mkdir(parents=True)
    (gdir / "snapshots" / "snap-1.jsonl").write_text("{}\n", encoding="utf-8")
    lob.store.set_game(g["id"], status="finished")
    lob.cfg.archive_s = 3600.0
    asyncio.run(lob.tick())
    assert lob.store.game(g["id"])["status"] == "finished"
    lob.store._x("UPDATE games SET updated_at=? WHERE id=?", (time.time() - 7200, g["id"]))
    asyncio.run(lob.tick())
    assert lob.store.game(g["id"])["status"] == "archived"
    assert (lob.cfg.archive_dir / g["id"] / "snapshots" / "snap-1.jsonl").exists() and not gdir.exists()


def test_item5_a_lobby_restart_brings_running_games_back(make_lobby, tmp_path) -> None:
    c, lob = make_lobby()
    _accept(c)
    g = _game(c)
    lob.store.set_game(g["id"], status="running")
    c2, lob2 = make_lobby()
    assert (g["id"], True) in lob2.started


def test_item5_logs_hold_no_tokens_cookies_or_ips(make_lobby, tmp_path) -> None:
    c, lob = make_lobby()
    _accept(c)
    g = _game(c)
    tok = c.post(f"/api/games/{g['id']}/join", json={}).json()["claim_url"].split("token=")[1]
    c.get(f"/g/{g['id']}/watch")
    log = "".join(p.read_text(encoding="utf-8") for p in (tmp_path / "selfhost" / "logs").glob("*.log*"))
    assert "join game=" in log and "create game=" in log
    assert tok not in log and c.cookies.get("gwc_guest") not in log and "testclient" not in log
    assert lob.secrets.spectator_token(g["id"]) not in log


def test_item5_admin_page_is_this_pc_only_with_a_kill_switch(make_lobby) -> None:
    c, lob = make_lobby()
    _accept(c)
    g = _game(c)
    assert c.get("/admin").status_code == 404
    local, _ = make_lobby(client=("127.0.0.1", 5000))
    local_lob = local.app.state.lobby
    assert local.get("/admin", headers={"cf-connecting-ip": "203.0.113.9"}).status_code == 404
    page = local.get("/admin")
    assert page.status_code == 200 and "Kill switch" in page.text
    csrf = re.search(r'name="csrf" value="([0-9a-f]+)"', page.text).group(1)
    assert local.post("/admin/kill", data={"csrf": "nope"}).status_code == 404
    _accept(local)
    lg = _game(local)
    r = local.post("/admin/kill", data={"csrf": csrf}, follow_redirects=False)
    assert r.status_code == 303 and local_lob.closed
    assert local_lob.store.game(lg["id"])["status"] == "stopped"
    assert local.post("/api/games", json={"name": "After"}).status_code == 503
    assert local.post("/admin/open", data={"csrf": csrf}).status_code == 200 and not local_lob.closed


# ------------------------------------------------------------------ item 6: spectator watch


def test_item6_spectator_routes_need_the_watch_cookie(make_lobby) -> None:
    c, lob = make_lobby()
    _accept(c)
    g = _game(c)
    gid = g["id"]
    viewer = TestClient(c.app)
    _accept(viewer)
    assert viewer.get(f"/g/{gid}/state").status_code == 403
    assert viewer.get(f"/g/{gid}/", headers={"accept": "text/html"}).status_code == 403
    assert viewer.get(f"/g/{gid}/spectate?token=guess").status_code == 403
    assert lob.proxied == []
    r = viewer.get(f"/g/{gid}/watch", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == f"/g/{gid}/"
    assert f"Path=/g/{gid}/" in r.headers["set-cookie"] and "HttpOnly" in r.headers["set-cookie"]
    assert viewer.cookies.get(f"gwc_w_{gid}") == lob.secrets.watch_cookie(gid)
    assert viewer.get(f"/g/{gid}/state").status_code == 200
    rest, extra = lob.proxied[-1]
    assert rest == "state" and extra == {"authorization": f"Bearer {lob.secrets.spectator_token(gid)}"}
    viewer.get(f"/g/{gid}/harness/v1/P1/observation")
    assert lob.proxied[-1] == ("harness/v1/P1/observation", {})
    forged = f"gwc_guest={viewer.cookies.get('gwc_guest')}; gwc_w_{gid}=forged"
    assert viewer.get(f"/g/{gid}/state", headers={"cookie": forged}).status_code == 403


def test_item6_link_only_watch_and_seated_players_cannot_watch(make_lobby) -> None:
    c, lob = make_lobby()
    _accept(c)
    g = _game(c, visibility="link")
    gid = g["id"]
    assert "?k=" in g["watch_link"]
    viewer = TestClient(c.app)
    _accept(viewer)
    assert viewer.get(f"/g/{gid}/watch").status_code == 403
    path = "/" + g["watch_link"].split("/", 3)[3]
    assert viewer.get(path, follow_redirects=False).status_code == 303
    c.post(f"/api/games/{gid}/join", json={})
    r = c.get(f"/g/{gid}/watch")
    assert r.status_code == 403 and "cannot watch" in r.text
    listed = _game(c, name="Listed")
    page = viewer.get("/").text
    assert f'href="/g/{listed["id"]}/watch"' in page and gid not in page
    c.post(f"/api/games/{listed['id']}/join", json={})
    assert f'href="/g/{listed["id"]}/watch"' not in c.get("/").text


# ------------------------------------------------------------------ item 7: Netlify plan


def test_item7_netlify_plan_and_status_cors(make_lobby) -> None:
    plan = (REPO / "docs" / "plans" / "selfhost-beta-v1.md").read_text(encoding="utf-8")
    sec = plan[plan.index("## Netlify play link"):]
    for needle in ("Play Galaxy War Command (beta)", "iframe", "frame-ancestors", "Access-Control-Allow-Origin",
                   "/status", "files to change", "index.html", "galaxy-war-command.html", "netlify.toml",
                   "offline"):
        assert needle in sec, needle
    c, _ = make_lobby()
    r = c.get("/status", headers={"origin": "https://thesingularity.netlify.app"})
    assert r.json()["online"] is True and r.headers["access-control-allow-origin"] == \
        "https://thesingularity.netlify.app"
    assert "access-control-allow-origin" not in c.get("/status", headers={"origin": "https://evil.example"}).headers
    home = c.get("/").headers
    assert home["x-frame-options"] == "DENY" and home["referrer-policy"] == "same-origin"
