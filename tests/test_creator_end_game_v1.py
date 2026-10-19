"""creator-end-game-v1 (COMMANDER NOTE 76).

The creator can end a running game from the lobby or the redesign cockpit.
The match stops, the lobby marks it finished with ended_by=creator, and the
redesign end screen names the creator and the rankings. No rule switch: a
profile-off game that nobody ends stays the old game.

Plants:
  p1 — a non-creator can end the game.
  p2 — ending twice changes the row again.
  p3 — a missing confirm still stops the worker.
  p4 — a finished game stays on the open list.
  p5 — the cockpit paints End game for everyone with no creator check.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

from tw2k.engine.models import GameConfig, Player
from tw2k.engine.observation import build_observation
from tw2k.engine.universe import generate_universe
from tw2k.engine.victory import end_match_by_creator, game_over_panel
from tw2k.public.config import LobbyConfig
from tw2k.public.lobby import create_lobby_app
from tw2k.public.security import new_guest_cookie, sha256_hex
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

ROOT = Path(__file__).resolve().parents[1]
REDESIGN = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")
BOT_HTML = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")
BOT_JS = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")
BOT_PARITY = (ROOT / "web" / "bot-parity.js").read_text(encoding="utf-8")
SHOTS = ROOT / "docs" / "playtests" / "creator-end-game-v1"
BLOCKED = set(range(8031, 8120))


class _FakeWorker:
    def __init__(self, port: int) -> None:
        self.port = port
        self.pid = 4242
        self.stopping = False
        self.up = True

    def alive(self) -> bool:
        return self.up


def _cfg(tmp_path: Path) -> LobbyConfig:
    return LobbyConfig(root=tmp_path / "selfhost", port=47350, game_ports=range(47351, 47360), tick_s=3600.0)


@pytest.fixture
def lobby(tmp_path, monkeypatch):
    for name in ("TW2K_PUBLIC_MODE", "TW2K_BRAND", "TW2K_BASE_PATH", "TW2K_SPECTATOR_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    app = create_lobby_app(_cfg(tmp_path), port_probe=lambda _p: True)
    lob = app.state.lobby

    async def fake_start(gid, *, resume):
        lob.workers.workers[gid] = _FakeWorker(47351)
        lob.store.set_game(gid, status="running", port=47351)
        return True

    async def fake_call(gid, method, path, body=None):
        lob.calls.append((gid, method, path, body))
        return SimpleNamespace(status_code=200, json=lambda: {"ok": True, "ended": True, "finished": True})

    async def fake_stop(gid, *, lobby_secret, spectator_token, graceful=True):
        lob.workers.workers.pop(gid, None)

    lob.calls = []
    lob.start_game = fake_start
    lob.worker_call = fake_call
    lob.workers.stop = fake_stop
    with TestClient(app) as client:
        yield client, lob


def _accept(client) -> None:
    assert client.post("/api/accept", json={}).status_code == 200


def _game(client, **kw) -> dict:
    body = {"name": "Alpha", "humans": 1, "bots": 0}
    body.update(kw)
    response = client.post("/api/games", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _ends(lob) -> list:
    return [row for row in lob.calls if row[2] == "/control/end"]


def test_creator_ends_and_the_lobby_moves_the_game_to_finished(lobby) -> None:
    client, lob = lobby
    _accept(client)
    created = _game(client, name="Alpha", bots=2)
    gid = created["id"]
    page = client.get("/").text
    assert f'data-end-game="{gid}"' in page
    assert "End Alpha for everyone?" in page
    assert "<h2>Finished</h2>" not in page
    denied = client.post(f"/api/games/{gid}/end", json={})
    assert denied.status_code == 400
    assert lob.store.game(gid)["status"] == "running"
    assert _ends(lob) == []
    done = client.post(f"/api/games/{gid}/end", json={"confirm": True})
    assert done.status_code == 200, done.text
    body = done.json()
    assert body["status"] == "finished" and body["ended_by"] == "creator" and body["already"] is False
    row = lob.store.game(gid)
    assert row["status"] == "finished" and row["ended_by"] == "creator"
    assert len(_ends(lob)) == 1
    again = client.post(f"/api/games/{gid}/end", json={"confirm": True})
    assert again.status_code == 200 and again.json()["already"] is True
    assert len(_ends(lob)) == 1
    stamped = lob.store.game(gid)
    assert stamped["status"] == "finished" and stamped["ended_by"] == "creator"
    assert stamped["updated_at"] == row["updated_at"]
    home = client.get("/").text
    open_list, _, finished = home.partition("<h2>Finished</h2>")
    assert f'data-finished="{gid}"' in finished
    assert "Alpha" in finished
    assert "Alpha" not in open_list.split("<h2>Games</h2>", 1)[1]
    assert "data-end-game" not in home


def test_non_creator_gets_403_and_nothing_changes(lobby) -> None:
    client, lob = lobby
    _accept(client)
    gid = _game(client, name="Alpha")["id"]
    before = lob.store.game(gid)
    other = new_guest_cookie()
    lob.store.accept(sha256_hex(other))
    saved = client.cookies.get("gwc_guest")
    client.cookies.set("gwc_guest", other)
    denied = client.post(f"/api/games/{gid}/end", json={"confirm": True})
    assert denied.status_code == 403
    stranger = client.get("/").text
    assert "data-end-game" not in stranger
    assert client.get(f"/api/games/{gid}/creator").json() == {"creator": False}
    client.cookies.set("gwc_guest", saved)
    after = lob.store.game(gid)
    assert after["status"] == before["status"] == "running"
    assert after.get("ended_by") in (None, "")
    assert after["updated_at"] == before["updated_at"]
    assert _ends(lob) == []
    mine = client.get(f"/api/games/{gid}/creator").json()
    assert mine["creator"] is True and mine["name"] == "Alpha" and mine["status"] == "running"


def test_a_dead_worker_does_not_mark_the_game_finished(lobby) -> None:
    client, lob = lobby
    _accept(client)
    gid = _game(client)["id"]

    async def down(gid, method, path, body=None):
        lob.calls.append((gid, method, path, body))
        return None

    lob.worker_call = down
    response = client.post(f"/games/{gid}/end", data={"confirm": "true"}, follow_redirects=False)
    assert response.status_code == 503
    assert lob.store.game(gid)["status"] == "running"
    assert lob.store.game(gid).get("ended_by") in (None, "")


def test_form_confirm_names_the_game_and_a_seated_creator_keeps_one_button(lobby) -> None:
    client, lob = lobby
    _accept(client)
    gid = _game(client, name="Beta Run", visibility="link")["id"]
    quiet = client.get("/").text
    assert f'data-end-game="{gid}"' in quiet
    assert "End Beta Run for everyone?" in quiet
    assert "link only" in quiet
    client.post(f"/api/games/{gid}/join", json={})
    seated = client.get("/").text
    assert seated.count(f'data-end-game="{gid}"') == 1
    assert "Resume my seat" in seated
    response = client.post(f"/games/{gid}/end", data={"confirm": "true"}, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/"
    assert lob.store.game(gid)["ended_by"] == "creator"


def _seat(world, pid: str, name: str, *, experience: int = 0) -> Player:
    player = Player(id=pid, name=name, sector_id=1, credits=300, turns_per_day=250, experience=experience)
    world.players[pid] = player
    return player


def test_solo_and_code_bots_get_the_creator_line_and_rankings(monkeypatch) -> None:
    solo = generate_universe(GameConfig(seed=76, universe_size=40, enable_ferrengi=False, enable_planets=False))
    _seat(solo, "P1", "Guest 1", experience=40)
    assert "game_over_panel" not in build_observation(solo, "P1").model_dump()
    assert end_match_by_creator(solo) is True
    assert end_match_by_creator(solo) is False
    panel = game_over_panel(solo, solo.players["P1"])
    assert panel is not None
    assert "Ended by the game's creator." in panel
    assert "1st Guest 1" in panel and "You finished 1st of 1." in panel
    dumped = build_observation(solo, "P1").model_dump()
    assert dumped["game_over_panel"] == panel
    assert "can_end" not in dumped

    bots = generate_universe(GameConfig(seed=77, universe_size=40, enable_ferrengi=False, enable_planets=False))
    _seat(bots, "P1", "Guest 1", experience=10)
    vega = _seat(bots, "P2", "Vega", experience=80)
    vega.agent_kind = "heuristic"
    orion = _seat(bots, "P3", "Orion", experience=25)
    orion.agent_kind = "heuristic"
    monkeypatch.setattr("tw2k.engine.constants.PLANET_VALUE_SCORE_MODE", "experience")
    assert end_match_by_creator(bots) is True
    ranked = game_over_panel(bots, bots.players["P1"])
    assert ranked is not None and "Ended by the game's creator." in ranked
    assert "Decided by experience:" in ranked
    assert "1st Vega 80" in ranked and "2nd Orion 25" in ranked and "3rd Guest 1 10" in ranked
    assert "You finished 3rd of 3." in ranked
    assert sum(1 for ev in bots.events if ev.kind.value == "game_over") == 1


def test_a_waiting_seat_stops_and_a_second_end_is_a_no_op(tmp_path) -> None:
    async def _go() -> None:
        app = create_app(auto_start=False)
        runner = app.state.runner
        runner._saves_root = tmp_path / "saves"
        await runner.start(MatchSpec(
            config=GameConfig(seed=76, universe_size=40, max_days=30, turns_per_day=250,
                              enable_ferrengi=False, enable_planets=False, action_delay_s=0.0),
            agents=[
                AgentSpec(player_id="P1", name="Guest 1", kind="external", external_token="t" * 40),
                AgentSpec(player_id="P2", name="Vega", kind="heuristic"),
            ],
            action_delay_s=0.0,
            external_timeout_s=30.0,
        ))
        try:
            for _ in range(200):
                universe = runner.state.universe
                if universe is not None and {"P1", "P2"} <= set(universe.players):
                    break
                await asyncio.sleep(0.02)
            universe = runner.state.universe
            assert universe is not None and "P2" in universe.players
            assert runner.end_by_creator() is True
            for _ in range(200):
                if runner.state.status == "finished":
                    break
                await asyncio.sleep(0.02)
            assert runner.state.status == "finished"
            assert universe.win_reason == "creator" and universe.finished is True
            panel = build_observation(universe, "P1").game_over_panel or ""
            assert "Ended by the game's creator." in panel
            assert "Guest 1" in panel and "Vega" in panel
            assert runner.end_by_creator() is False
            assert sum(1 for ev in universe.events if ev.kind.value == "game_over") == 1
        finally:
            await runner.stop()

    asyncio.run(_go())


def test_redesign_hides_the_item_unless_this_seat_is_the_creator_and_bot_is_untouched() -> None:
    end_row = REDESIGN[REDESIGN.index("const endRow"):REDESIGN.index("const endRow") + 280]
    assert "state.canEnd" in end_row
    assert "End game for everyone" in end_row
    assert 'id="endForEveryone"' in end_row
    assert "Ended by the game's creator." not in BOT_HTML
    assert "endForEveryone" not in BOT_JS and "End game for everyone" not in BOT_JS
    assert "endForEveryone" not in BOT_PARITY and "End game for everyone" not in BOT_PARITY


def _free_port(start: int = 8210) -> int:
    from tests._port_lock import claim_ports

    return claim_ports(1, low=start, high=start + 80, avoid=set(BLOCKED), sequential=True)


def test_screenshots_at_1280_and_390(tmp_path, monkeypatch) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    import threading
    import time

    import uvicorn

    from tests._cu_host import CuHost

    monkeypatch.setattr("tests._cu_host.free_port", _free_port)
    for name in ("TW2K_PUBLIC_MODE", "TW2K_BRAND", "TW2K_BASE_PATH", "TW2K_SPECTATOR_TOKEN", "COCKPIT_LAYOUT"):
        monkeypatch.delenv(name, raising=False)

    port = _free_port(8210)
    app = create_lobby_app(
        LobbyConfig(root=tmp_path / "shots", port=port, game_ports=range(port + 1, port + 4), tick_s=3600.0),
        port_probe=lambda _p: True,
    )
    lob = app.state.lobby

    async def fake_start(gid, *, resume):
        lob.workers.workers[gid] = _FakeWorker(port + 1)
        lob.store.set_game(gid, status="running", port=port + 1)
        return True

    async def fake_call(gid, method, path, body=None):
        return SimpleNamespace(status_code=200, json=lambda: {"ok": True, "ended": True, "finished": True})

    async def fake_stop(gid, *, lobby_secret, spectator_token, graceful=True):
        lob.workers.workers.pop(gid, None)

    lob.start_game = fake_start
    lob.worker_call = fake_call
    lob.workers.stop = fake_stop
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while time.time() < deadline and not server.started:
        time.sleep(0.05)
    assert server.started
    SHOTS.mkdir(parents=True, exist_ok=True)
    pw = sync_api.sync_playwright().start()
    try:
        browser = pw.chromium.launch()
    except Exception as exc:
        server.should_exit = True
        thread.join(timeout=5)
        pytest.skip(f"chromium not available: {exc}")
    try:
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"http://127.0.0.1:{port}/")
        page.get_by_role("button", name="I understand").click()
        page.wait_for_url(f"http://127.0.0.1:{port}/")
        page.goto(f"http://127.0.0.1:{port}/new")
        page.fill("#name", "Alpha")
        page.get_by_role("button", name="Create game").click()
        page.get_by_role("link", name="Back to the lobby").click()
        button = page.locator("[data-end-game]")
        button.wait_for()
        assert button.count() == 1
        page.screenshot(path=str(SHOTS / "1280-lobby-end.png"))
        page.set_viewport_size({"width": 390, "height": 844})
        button.scroll_into_view_if_needed()
        page.screenshot(path=str(SHOTS / "390-lobby-end.png"))
        messages = []
        page.once("dialog", lambda dialog: (messages.append(dialog.message), dialog.accept()))
        button.click()
        page.wait_for_selector("#finished")
        assert messages == ["End Alpha for everyone?"]
        assert page.locator("[data-end-game]").count() == 0
        assert "Alpha" in page.locator("#finished").inner_text()
        page.set_viewport_size({"width": 1280, "height": 800})
        page.screenshot(path=str(SHOTS / "1280-lobby-finished.png"))
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#finished").scroll_into_view_if_needed()
        page.screenshot(path=str(SHOTS / "390-lobby-finished.png"))

        token = "c" * 40
        with CuHost(tmp_path / "cu", token, max_days=3, turns_per_day=40, seed=76) as host:
            assert host.port >= 8210 and host.port not in BLOCKED

            def install(route):
                url = route.request.url
                if "/api/games/shot1/creator" in url:
                    seat = route.request.headers.get("x-test-seat", "")
                    body = {"creator": True, "seat": "P2", "name": "Alpha", "status": "running"}
                    if seat == "other":
                        body = {"creator": False}
                    if seat == "p1":
                        body = {"creator": True, "seat": "P1", "name": "Alpha", "status": "running"}
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
                    return
                route.continue_(url=url.replace("/g/shot1", ""))

            cock = browser.new_page(viewport={"width": 1280, "height": 800})
            cock.route("**/*", install)
            cock.goto(f"http://127.0.0.1:{host.port}/g/shot1/bot?layout=redesign&seat=P2#token={token}")
            cock.wait_for_selector("#waitchip", timeout=20_000)
            cock.wait_for_function(
                "() => document.querySelector('#waitchip') && document.querySelector('#waitchip').textContent === 'YOUR MOVE'",
                timeout=30_000,
            )
            cock.keyboard.press("?")
            cock.locator("[data-testid=end-for-everyone]").wait_for()
            cock.screenshot(path=str(SHOTS / "1280-menu-end.png"))
            cock.set_viewport_size({"width": 390, "height": 844})
            cock.locator("[data-testid=end-for-everyone]").scroll_into_view_if_needed()
            cock.screenshot(path=str(SHOTS / "390-menu-end.png"))
            cock.keyboard.press("Escape")

            hidden = browser.new_page(viewport={"width": 1280, "height": 800})
            hidden.set_extra_http_headers({"x-test-seat": "p1"})
            hidden.route("**/*", install)
            hidden.goto(f"http://127.0.0.1:{host.port}/g/shot1/bot?layout=redesign&seat=P2#token={token}")
            hidden.wait_for_selector("#waitchip", timeout=20_000)
            hidden.keyboard.press("?")
            hidden.wait_for_timeout(400)
            assert hidden.locator("[data-testid=end-for-everyone]").count() == 0
            hidden.close()

            stranger = browser.new_page(viewport={"width": 390, "height": 844})
            stranger.set_extra_http_headers({"x-test-seat": "other"})
            stranger.route("**/*", install)
            stranger.goto(f"http://127.0.0.1:{host.port}/g/shot1/bot?layout=redesign&seat=P2#token={token}")
            stranger.wait_for_selector("#waitchip", timeout=20_000)
            stranger.keyboard.press("?")
            stranger.wait_for_timeout(400)
            assert stranger.locator("[data-testid=end-for-everyone]").count() == 0
            stranger.screenshot(path=str(SHOTS / "390-menu-hidden.png"))
            stranger.close()

            async def _end() -> None:
                host.runner.end_by_creator()

            asyncio.run_coroutine_threadsafe(_end(), host.runner._loop).result(timeout=10)
            cock.set_viewport_size({"width": 1280, "height": 800})
            cock.wait_for_function(
                "() => { const p = document.querySelector('[data-game-over=panel]'); return p && p.textContent.indexOf(\"Ended by the game's creator.\") >= 0; }",
                timeout=20_000,
            )
            text = cock.locator("[data-game-over=panel]").inner_text()
            assert "Ended by the game's creator." in text
            assert "Guest" in text or "Commander" in text or "HBot" in text
            cock.screenshot(path=str(SHOTS / "1280-game-over.png"))
            cock.set_viewport_size({"width": 390, "height": 844})
            cock.locator("[data-game-over=panel]").scroll_into_view_if_needed()
            cock.screenshot(path=str(SHOTS / "390-game-over.png"))
    finally:
        browser.close()
        pw.stop()
        server.should_exit = True
        thread.join(timeout=10)
