"""COMMANDER NOTE 65 items 1-6: a free course, one warp clip, and a map you can read.

Plotting does not spend a turn. The warp clip plays only after the ship moves.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, build_observation, generate_universe
from tw2k.engine.models import Player
from tw2k.engine.runner import query_route
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

pytestmark = pytest.mark.legacy_profile

REPO = Path(__file__).resolve().parents[1]
SHOTS = REPO / "docs" / "playtests" / "cockpit-nav-and-map-v1"
TOK = "n" * 40
PATH = [173, 975, 948, 445, 739, 1]


def _free_block(n: int) -> int:
    from tests._cu_host import LOBBY_FREE_START, free_port

    return free_port(LOBBY_FREE_START, count=n)


def test_item2_route_query_does_not_spend_a_turn_and_names_the_one_way(monkeypatch) -> None:
    """Ben's seed: 524 to 1 is 6 hops, 18 turns. Avoids skip a sector. The target does not."""
    cfg = GameConfig(seed=1044995408, universe_size=1000, one_way_fraction=0.15, max_days=3, turns_per_day=100)
    universe = generate_universe(cfg)
    me = Player(id="P1", name="Ben", sector_id=524, turns_per_day=100)
    universe.players["P1"] = me
    seq, events, turns = universe.seq, len(universe.events), me.turns_today
    row = query_route(universe, "P1", 1)
    assert universe.seq == seq and len(universe.events) == events and me.turns_today == turns
    assert me.sector_id == 524
    assert row["ok"] is True
    assert row["path"] == PATH
    assert row["hops"] == 6 and row["turns_per_hop"] == 3 and row["total_turns"] == 18
    assert {"from": 424, "to": 524} in row["one_way"]
    monkeypatch.setattr(K, "avoid_live", lambda: True)
    me.avoided_sectors = [975]
    around = query_route(universe, "P1", 1)
    assert around["avoiding"] == [975]
    assert around["ok"] is True and 975 not in around["path"] and around["path"] != PATH
    assert universe.seq == seq and len(universe.events) == events
    me.avoided_sectors = [1]
    home = query_route(universe, "P1", 1)
    assert home["ok"] is True and home["path"][-1] == 1
    missing = query_route(universe, "P1", "nope")
    assert missing["ok"] is False and universe.seq == seq


class NavHost:
    def __init__(self, tmp: Path) -> None:
        import uvicorn

        self.token = TOK
        self.port = 0
        self.app = create_app(auto_start=False)
        self.runner = self.app.state.runner
        self.runner._saves_root = tmp / "saves"
        self.server = None
        self.thread = None
        self._uvicorn = uvicorn
        self.ready = False
        self._info = K.INFO_MODE

    async def _start(self) -> None:
        while not self.server.started:
            await asyncio.sleep(0.05)
        await self.runner.start(MatchSpec(
            config=GameConfig(
                seed=1044995408, universe_size=1000, one_way_fraction=0.15, max_days=3,
                turns_per_day=100, starting_credits=20_000, enable_ferrengi=False, enable_planets=True,
                action_delay_s=0.0,
            ),
            agents=[AgentSpec(player_id="P1", name="Ben", kind="external", external_token=TOK)],
            action_delay_s=0.05,
            external_timeout_s=600.0,
        ))
        for _ in range(400):
            agent = self._agent()
            if agent is not None and agent.awaiting_input and self.runner.state.universe is not None:
                break
            await asyncio.sleep(0.05)
        self.place()
        self.ready = True

    def _agent(self):
        return next((a for a in self.runner.state.agents if getattr(a, "player_id", None) == "P1"), None)

    def place(self, *, turns_left: int = 100, landed: bool = False) -> None:
        universe = self.runner.state.universe
        me = universe.players["P1"]
        if me.sector_id != 524:
            try:
                universe.sectors[me.sector_id].occupant_ids.remove("P1")
            except ValueError:
                pass
            me.sector_id = 524
            if "P1" not in universe.sectors[524].occupant_ids:
                universe.sectors[524].occupant_ids.append("P1")
        me.known_sectors.update([524, 424, *PATH])
        for sid in [524, 424, *PATH]:
            me.known_warps[sid] = list(universe.sectors[sid].warps)
        me.turns_today = max(0, int(me.turns_per_day) - int(turns_left))
        me.planet_landed = 1 if landed else None
        agent = self._agent()
        if agent is not None:
            agent.current_observation = build_observation(universe, "P1")

    async def _main(self) -> None:
        task = asyncio.create_task(self._start())
        await self.server.serve()
        task.cancel()
        await self.runner.stop()

    def __enter__(self) -> NavHost:
        from tests._cu_host import acquire_info_mode, release_info_mode

        self._info_pushed = False
        try:
            acquire_info_mode(self)
            self._info_pushed = True
            # _free_block reserves the port across processes before uvicorn binds it.
            self.port = _free_block(1)
            self.server = self._uvicorn.Server(
                self._uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="warning")
            )
            self.thread = threading.Thread(target=lambda: asyncio.run(self._main()), daemon=True)
            self.thread.start()
            deadline = time.time() + 40
            while time.time() < deadline and not (self.server and self.server.started):
                time.sleep(0.05)
            if not (self.server and self.server.started):
                raise AssertionError("nav host did not bind")
            deadline = time.time() + 40
            while time.time() < deadline and not self.ready:
                time.sleep(0.1)
            if not self.ready:
                raise AssertionError("nav host did not start")
            return self
        except BaseException:
            if self.server is not None:
                self.server.should_exit = True
            if self.thread is not None and self.thread.is_alive():
                self.thread.join(timeout=15)
            if self.port:
                from tests._port_lock import release_ports

                release_ports(self.port)
                self.port = 0
            if self._info_pushed:
                release_info_mode(self)
                self._info_pushed = False
            raise

    def __exit__(self, *exc) -> None:
        from tests._cu_host import release_info_mode

        try:
            if self.server is not None:
                self.server.should_exit = True
            if self.thread is not None:
                self.thread.join(timeout=15)
            if self.port:
                from tests._port_lock import release_ports

                release_ports(self.port)
        finally:
            if getattr(self, "_info_pushed", False):
                release_info_mode(self)
                self._info_pushed = False

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"


@pytest.fixture(scope="module")
def nav(tmp_path_factory):
    with NavHost(tmp_path_factory.mktemp("nav65")) as host:
        yield host


def _open(page, nav: NavHost, *, turns_left: int = 100, landed: bool = False) -> None:
    nav.place(turns_left=turns_left, landed=landed)
    page.goto(f"{nav.base}/bot?layout=redesign&seat=P1&token={TOK}")
    page.wait_for_selector("#map .node.here", timeout=20_000)
    page.wait_for_selector("#map .node[data-id='1']", timeout=10_000)
    page.evaluate(
        """() => {
          window.__warpBatches = 0;
          const orig = window.TW2KMedia.onEvents.bind(window.TW2KMedia);
          window.TW2KMedia.onEvents = (list, obs, opts) => {
            if ((list || []).some((ev) => ev && (ev.kind === "warp" || ev.kind === "autopilot"))) window.__warpBatches += 1;
            return orig(list, obs, opts);
          };
        }"""
    )


def _seat(page) -> dict:
    return page.evaluate(
        """async (token) => {
          const headers = {Authorization: "Bearer " + token, "X-TW2K-Seat": "P1"};
          const body = await fetch("/harness/v1/P1/observation?peek=1", {headers}).then((r) => r.json());
          const ev = await fetch("/harness/v1/P1/events?since=0&limit=500", {headers}).then((r) => r.json());
          return {
            turn: body.turn_seq,
            sector: body.observation.sector.id,
            turns: body.observation.turns_remaining,
            latest: ev.latest_seq,
          };
        }""",
        TOK,
    )


def _batches(page) -> int:
    return page.evaluate("() => window.__warpBatches")


def _wait_batches(page, n: int) -> None:
    """The result line can land before the media callback under load. The count stays exact."""
    page.wait_for_function(f"() => (window.__warpBatches || 0) >= {n}", timeout=20_000)
    assert _batches(page) == n


@pytest.mark.skipif(os.name != "nt", reason="Windows host")
def test_item6a_click_or_type_a_far_sector_opens_a_free_course(nav, tmp_path) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    with sync() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            _open(page, nav)
            before = _seat(page)
            page.locator("#map .node[data-id='1'] circle.hit").click()
            page.wait_for_selector("[data-testid=course-line]", timeout=10_000)
            line = page.locator("[data-testid=course-line]").inner_text()
            assert "Course to 1: 524 > 173 > 975 > 948 > 445 > 739 > 1." in line
            assert "6 hops, 18 turns." in line
            note = page.locator("[data-testid=one-way-note]").inner_text()
            assert "524 -> 424 is one-way (424 -> 524 only), so the shortest way back is 6 hops." in note
            assert _batches(page) == 0
            after = _seat(page)
            assert after["turn"] == before["turn"] and after["latest"] == before["latest"]
            assert after["sector"] == 524 and after["turns"] == before["turns"]
            SHOTS.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(SHOTS / "1280-course.png"))
            page.locator("[data-testid=course-cancel]").click()
            page.wait_for_selector("[data-testid=course]", state="hidden")
            page.keyboard.press("c")
            page.keyboard.press("f")
            page.fill("#sectorAsk", "1")
            page.locator("#sectorGo").click()
            page.wait_for_selector("[data-testid=course-line]")
            assert "6 hops, 18 turns." in page.locator("[data-testid=course-line]").inner_text()
            assert _seat(page)["latest"] == before["latest"]
            assert _batches(page) == 0
        finally:
            browser.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows host")
def test_item6b_engage_flies_the_course_and_plays_one_clip(nav) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    with sync() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            _open(page, nav)
            page.locator("#map .node[data-id='1'] circle.hit").click()
            page.wait_for_selector("[data-testid=engage]")
            page.locator("[data-testid=engage]").click()
            page.wait_for_function(
                "() => (document.querySelector('#lastResult').textContent || '').includes('arrived at 1')",
                timeout=20_000,
            )
            assert "Autopilot: arrived at 1 (6 hops, 18 turns)." in page.locator("#lastResult").inner_text()
            page.wait_for_function("() => document.querySelector('#pSector').textContent.trim() === '1'", timeout=10_000)
            _wait_batches(page, 1)
            assert _seat(page)["sector"] == 1
        finally:
            browser.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows host")
def test_item6c_refused_engage_plays_nothing(nav) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    with sync() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            _open(page, nav, turns_left=1)
            before = _seat(page)
            page.locator("#map .node[data-id='1'] circle.hit").click()
            page.wait_for_selector("[data-testid=engage]")
            page.locator("[data-testid=engage]").click()
            page.wait_for_function(
                "() => (document.querySelector('#lastResult').textContent || '').includes('REFUSED')",
                timeout=10_000,
            )
            assert "unaffordable" in page.locator("#lastResult").inner_text()
            assert _batches(page) == 0
            assert _seat(page)["sector"] == 524 and _seat(page)["turns"] == before["turns"]
            _open(page, nav, landed=True)
            page.locator("#map .node[data-id='1'] circle.hit").click()
            page.wait_for_selector("[data-testid=engage]")
            page.locator("[data-testid=engage]").click()
            page.wait_for_function(
                "() => (document.querySelector('#lastResult').textContent || '').includes('REFUSED')",
                timeout=10_000,
            )
            assert "Lift off first" in page.locator("#lastResult").inner_text()
            assert _batches(page) == 0
            assert _seat(page)["sector"] == 524
        finally:
            browser.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows host")
def test_item6d_engage_off_turn_queues_then_flies(nav) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    with sync() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            _open(page, nav)
            page.evaluate("() => window.__tw2kTest.setAwaiting(false)")
            page.locator("#map .node[data-id='1'] circle.hit").click()
            page.wait_for_selector("[data-testid=course-line]")
            assert "will run" not in page.locator("#lastResult").inner_text()
            assert _batches(page) == 0
            page.locator("[data-testid=engage]").click()
            page.wait_for_function(
                "() => (document.querySelector('#lastResult').textContent || '').includes('will run when your turn comes')",
                timeout=10_000,
            )
            assert _batches(page) == 0
            page.evaluate("() => window.__tw2kTest.release()")
            page.wait_for_function(
                "() => (document.querySelector('#lastResult').textContent || '').includes('arrived at 1')",
                timeout=20_000,
            )
            _wait_batches(page, 1)
            assert _seat(page)["sector"] == 1
        finally:
            browser.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows host")
def test_item6e_a_single_warp_plays_one_clip(nav) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    with sync() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            _open(page, nav)
            page.locator("#warps button", has_text="173").click()
            page.wait_for_function("() => document.querySelector('#pSector').textContent.trim() === '173'", timeout=15_000)
            _wait_batches(page, 1)
        finally:
            browser.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows host")
def test_item6f_leaving_the_course_offers_a_free_replot(nav) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    with sync() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            _open(page, nav)
            page.locator("#map .node[data-id='1'] circle.hit").click()
            page.wait_for_selector("[data-testid=course-line]")
            page.locator("#warps button", has_text="797").click()
            page.wait_for_selector("[data-testid=off-course]", timeout=15_000)
            assert "Off course - re-plot to 1?" in page.locator("[data-testid=off-course]").inner_text()
            parked = _seat(page)
            assert parked["sector"] == 797
            page.locator("[data-testid=replot]").click()
            page.wait_for_selector("[data-testid=course-line]")
            assert "Course to 1:" in page.locator("[data-testid=course-line]").inner_text()
            again = _seat(page)
            assert again["turns"] == parked["turns"] and again["latest"] == parked["latest"]
            assert again["sector"] == 797
        finally:
            browser.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows host")
def test_item6g_a_known_one_way_lane_has_an_arrowhead(nav) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    with sync() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            _open(page, nav)
            arrow = page.locator("#map .arrowhead[data-from='424'][data-to='524']")
            assert arrow.count() >= 1
            assert page.locator("#map .lane.oneway").count() >= 1
        finally:
            browser.close()


def _labels_and_hits(page) -> dict:
    return page.evaluate(
        """() => {
          const texts = [...document.querySelectorAll("#map text")].map((t) => t.getBoundingClientRect().height);
          const hits = [...document.querySelectorAll("#map circle.hit")].map((c) => c.getBoundingClientRect().width);
          const world = document.getElementById("mapWorld");
          return {texts, hits, transform: world ? world.getAttribute("transform") : ""};
        }"""
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows host")
def test_item6h_zoom_pan_center_enlarge_and_labels(nav) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    with sync() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            _open(page, nav)
            SHOTS.mkdir(parents=True, exist_ok=True)
            sized = _labels_and_hits(page)
            assert sized["texts"] and min(sized["texts"]) >= 12
            assert sized["hits"] and min(sized["hits"]) >= 24
            page.screenshot(path=str(SHOTS / "1280-map.png"))
            here = _seat(page)["sector"]
            node = page.locator("#map .node[data-id='1'] circle.hit").bounding_box()
            page.mouse.move(node["x"] + 4, node["y"] + 4)
            page.mouse.down()
            page.mouse.move(node["x"] + 80, node["y"] + 40)
            page.mouse.up()
            page.wait_for_timeout(200)
            assert page.locator("[data-testid=course]").is_hidden()
            assert _seat(page)["sector"] == here
            page.locator("#map").dispatch_event("wheel", {"deltaY": -100, "clientX": 640, "clientY": 400})
            zoomed = _labels_and_hits(page)["transform"]
            assert "scale(" in zoomed and "scale(1)" not in zoomed
            page.mouse.move(200, 200)
            page.mouse.down()
            page.mouse.move(280, 240)
            page.mouse.up()
            panned = _labels_and_hits(page)["transform"]
            assert not panned.startswith("translate(0 0)")
            page.locator("[data-testid=map-center]").click()
            centered = _labels_and_hits(page)["transform"]
            assert centered.startswith("translate(0 0)")
            page.evaluate(
                """() => {
                  const svg = document.querySelector("#map");
                  const r = svg.getBoundingClientRect();
                  const fire = (type, id, x, y) => svg.dispatchEvent(new PointerEvent(type, {
                    pointerId: id, clientX: x, clientY: y, bubbles: true, pointerType: "touch", isPrimary: id === 1,
                  }));
                  fire("pointerdown", 1, r.left + 80, r.top + 80);
                  fire("pointerdown", 2, r.left + 140, r.top + 80);
                  fire("pointermove", 2, r.left + 200, r.top + 80);
                  fire("pointerup", 2, r.left + 200, r.top + 80);
                  fire("pointerup", 1, r.left + 80, r.top + 80);
                }"""
            )
            pinched = _labels_and_hits(page)["transform"]
            assert "scale(" in pinched
            page.locator("[data-testid=map-zoom-in]").click()
            kept = _labels_and_hits(page)["transform"]
            page.wait_for_timeout(2500)
            assert _labels_and_hits(page)["transform"] == kept
            page.locator("[data-testid=map-enlarge]").click()
            page.wait_for_function("() => document.querySelector('#nav').classList.contains('enlarged')")
            wide = page.locator("#nav").bounding_box()
            assert wide["width"] >= 1270
            page.screenshot(path=str(SHOTS / "1280-map-enlarged.png"))
            page.keyboard.press("Escape")
            page.wait_for_function("() => !document.querySelector('#nav').classList.contains('enlarged')")
            page.set_viewport_size({"width": 1920, "height": 1080})
            page.wait_for_timeout(300)
            big = _labels_and_hits(page)
            assert min(big["texts"]) >= 12 and min(big["hits"]) >= 24
            page.locator("[data-testid=map-enlarge]").click()
            page.wait_for_timeout(200)
            assert page.locator("#nav").bounding_box()["width"] >= 1900
            page.screenshot(path=str(SHOTS / "1920-map-enlarged.png"))
            page.keyboard.press("Escape")
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(300)
            phone = _labels_and_hits(page)
            assert min(phone["texts"]) >= 12 and min(phone["hits"]) >= 24
            page.screenshot(path=str(SHOTS / "390-map.png"))
        finally:
            browser.close()


def test_item6j_bot_and_the_shared_resolver_stay_untouched() -> None:
    diff = subprocess.check_output(
        ["git", "diff", "--", "web/bot.js", "web/bot.html", "web/bot-parity.js", "web/media-resolver.js"],
        cwd=str(REPO),
    )
    assert diff == b""


@pytest.mark.skipif(os.name != "nt", reason="Windows host")
def test_item6i_a_lobby_game_serves_the_same_redesign(tmp_path) -> None:
    """Own ports, never 8099-8119. The proxied cockpit is the redesign, and a route read spends nothing."""
    lob = None
    base = None
    try:
        # _free_block reserves the three ports across processes before the lobby binds them.
        base = _free_block(3)
        root = tmp_path / "selfhost"
        root.mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith(("TW2K_", "TW2002_")) and k != "COCKPIT_LAYOUT"}
        env.update(
            TW2K_LOBBY_ROOT=str(root), TW2K_LOBBY_PORT=str(base), TW2K_GAME_PORTS=f"{base + 1}-{base + 2}",
            PYTHONPATH=str(REPO / "src"), PYTHONHASHSEED="0",
        )
        url = f"http://127.0.0.1:{base}"
        lob = subprocess.Popen(
            [sys.executable, "-m", "tw2k.cli", "lobby"], env=env, cwd=str(REPO),
            stdout=open(root / "lobby.out", "ab"), stderr=subprocess.STDOUT,  # noqa: SIM115
        )
        deadline = time.time() + 60
        while time.time() < deadline:
            assert lob.poll() is None, (root / "lobby.out").read_text(errors="replace")[-2000:]
            try:
                if httpx.get(url + "/healthz", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.3)
        else:
            raise AssertionError("lobby did not come up")
        client = httpx.Client(base_url=url, timeout=90)
        assert client.post("/api/accept", json={}).status_code == 200
        game = client.post("/api/games", json={"name": "Nav", "bots": 0, "universe_size": 200, "day": "30m"}).json()
        assert game["status"] == "running", game
        gid = game["id"]
        claim = client.post(f"/api/games/{gid}/join", json={}).json()["claim_url"]
        jumped = client.get(claim, follow_redirects=False)
        assert jumped.status_code == 303
        client.get(jumped.headers["location"])
        page = client.get(f"/g/{gid}/bot")
        assert page.status_code == 200
        assert 'data-testid="map-zoom-in"' in page.text
        script = client.get(f"/g/{gid}/static/redesign.js")
        assert script.status_code == 200
        assert "clipEvents" in script.text and "Engage Express" in script.text and "loadCourse" in script.text
        bot = client.get(f"/g/{gid}/static/bot.js")
        assert "loadCourse" not in bot.text
        obs = client.get(f"/g/{gid}/harness/v1/P1/observation?peek=1", headers={"X-TW2K-Seat": "P1"})
        assert obs.status_code == 200, obs.text
        body = obs.json()
        sector = body["observation"]["sector"]["id"]
        target = 1 if sector != 1 else 2
        before_events = client.get(
            f"/g/{gid}/harness/v1/P1/events?since=0&limit=20", headers={"X-TW2K-Seat": "P1"}
        ).json()["latest_seq"]
        route = client.get(
            f"/g/{gid}/harness/v1/P1/route?target={target}", headers={"X-TW2K-Seat": "P1"}
        )
        assert route.status_code == 200, route.text
        assert "path" in route.json() and "turns_per_hop" in route.json()
        again = client.get(f"/g/{gid}/harness/v1/P1/observation?peek=1", headers={"X-TW2K-Seat": "P1"}).json()
        assert again["observation"]["sector"]["id"] == sector
        assert again["observation"]["turns_remaining"] == body["observation"]["turns_remaining"]
        assert again["turn_seq"] == body["turn_seq"]
        latest = client.get(
            f"/g/{gid}/harness/v1/P1/events?since=0&limit=20", headers={"X-TW2K-Seat": "P1"}
        ).json()["latest_seq"]
        assert latest == before_events
    finally:
        if lob is not None and lob.poll() is None:
            lob.kill()
            lob.wait(10)
        if base is not None:
            from tests._port_lock import release_ports

            release_ports(base, base + 1, base + 2)
