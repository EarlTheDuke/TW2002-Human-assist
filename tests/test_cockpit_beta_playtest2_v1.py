"""NOTE 106. Playtest 2, redesign cockpit only.

The fighter and mine forms stay in the document across refreshes. M always
asks for a sector. A HERE form is the element under its own centre. A
turn_clock with a next dawn prints the day countdown beside the turns.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests._cu_host import CuHost
from tw2k.engine.models import MineType

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "beta-playtest2-v1"
TOK = "note106-playtest2-token-p2-00000000"
VIEWPORTS = ((1280, 720), (1600, 1000), (390, 844))
DAY_LINE = re.compile(r"Day \d+ ends in \d+:\d{2}(?::\d{2})?; turns refill at dawn")


def _your_move(page) -> None:
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function(
        "() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'",
        timeout=20_000,
    )


def _open(page, host, width: int, height: int) -> None:
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    _your_move(page)


def _publish(host) -> None:
    """The seat keeps the observation from the start of its turn."""
    from tw2k.engine.observation import build_observation

    universe = host.runner.state.universe
    obs = build_observation(universe, "P2")
    for agent in host.runner.state.agents:
        if getattr(agent, "player_id", None) == "P2":
            agent.current_observation = obs
            return
    raise AssertionError("P2 has no seat")


def _place(host, sector_id: int) -> None:
    universe = host.runner.state.universe
    me = universe.players["P2"]
    origin = universe.sectors[me.sector_id]
    if "P2" in origin.occupant_ids:
        origin.occupant_ids.remove("P2")
    me.sector_id = int(sector_id)
    me.planet_landed = None
    dest = universe.sectors[me.sector_id]
    if "P2" not in dest.occupant_ids:
        dest.occupant_ids.append("P2")
    me.known_sectors.add(me.sector_id)
    me.turns_per_day = 400
    me.turns_today = 0
    _publish(host)


def _sync(page, sector_id: int) -> None:
    page.evaluate("() => window.__tw2kTest.refreshNow()")
    page.wait_for_function(
        "(id) => document.querySelector('#pSector').textContent.trim() === String(id)",
        arg=str(sector_id),
        timeout=15_000,
    )
    _your_move(page)


def _arm(host) -> None:
    universe = host.runner.state.universe
    me = universe.players["P2"]
    me.ship.fighters = 100
    me.ship.mines[MineType.ARMID] = 5
    me.ship.mines[MineType.LIMPET] = 5
    me.turns_per_day = 400
    me.turns_today = 0
    sector = universe.sectors[me.sector_id]
    sector.fighters = None
    sector.mines = [row for row in sector.mines if getattr(row, "owner_id", None) != "P2"]
    _publish(host)


def _one_exit(universe):
    for sector in universe.sectors.values():
        if int(sector.id) > 10 and len(sector.warps) == 1:
            return sector
    raise AssertionError("no one-exit sector")


def _many_exit(universe):
    for sector in universe.sectors.values():
        if int(sector.id) > 10 and len(sector.warps) >= 3:
            return sector
    raise AssertionError("no many-exit sector")


def _far(universe, start: int, hops: int = 4) -> int:
    seen = {int(start)}
    layer = [int(start)]
    for _ in range(hops):
        nxt = []
        for sid in layer:
            for warp in universe.sectors[sid].warps:
                warp = int(warp)
                if warp not in seen:
                    seen.add(warp)
                    nxt.append(warp)
        if not nxt:
            break
        layer = nxt
    if not layer or layer[0] == int(start):
        raise AssertionError("no far sector")
    return layer[0]


def _shot(page, name: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / name))


def _refreshes(page, n: int = 5) -> None:
    page.evaluate(
        "(n) => { window.__note106 = (window.__tw2kTest.refreshCount() || 0) + n; }",
        n,
    )
    page.wait_for_function(
        "() => window.__tw2kTest.refreshCount() >= window.__note106",
        timeout=20_000,
    )


def _connected(handle) -> bool:
    return bool(handle.evaluate("el => !!(el && el.isConnected)"))


def test_fighter_and_mine_choices_survive_refresh(tmp_path, monkeypatch) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    with CuHost(tmp_path, TOK) as host, sync() as pw:
        universe = host.runner.state.universe
        assert int(universe.players["P2"].sector_id) not in K.FEDSPACE_SECTORS
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            for width, height in VIEWPORTS:
                _arm(host)
                _open(page, host, width, height)
                page.keyboard.press("f")
                page.wait_for_selector("#formSlot select[data-n=mode]", timeout=10_000)
                page.locator("#formSlot input[data-n=leave]").fill("70")
                page.locator("#formSlot select[data-n=mode]").select_option("offensive")
                handle = page.locator("#formSlot select[data-n=mode]").element_handle()
                button = page.locator("#formSlot button[data-role=confirm]")
                assert button.inner_text() == "Deploy 70 offensive"
                _refreshes(page)
                assert _connected(handle), "the fighter select was replaced by a refresh"
                assert button.inner_text() == "Deploy 70 offensive"
                if (width, height) == (1280, 720):
                    _shot(page, "1280-fighters.png")
                page.locator("#formSlot input[data-n=leave]").focus()
                page.keyboard.press("Enter")
                page.wait_for_function(
                    "() => /offensive/i.test(document.querySelector('#lastResult').textContent || '')",
                    timeout=20_000,
                )
                sector = universe.sectors[universe.players["P2"].sector_id]
                assert sector.fighters is not None
                assert sector.fighters.mode.value == "offensive"
                assert int(sector.fighters.count) == 70

                page.keyboard.press("h")
                page.wait_for_selector("#formSlot select[data-n=kind]", timeout=10_000)
                kind = page.locator("#formSlot select[data-n=kind] option").last.get_attribute("value")
                page.locator("#formSlot select[data-n=kind]").select_option(kind)
                mine_handle = page.locator("#formSlot select[data-n=kind]").element_handle()
                page.locator("#formSlot input[data-n=qty]").fill("2")
                _refreshes(page)
                assert _connected(mine_handle), "the mine select was replaced by a refresh"
                assert page.locator("#formSlot select[data-n=kind]").input_value() == kind
                page.locator("#formSlot input[data-n=qty]").focus()
                page.keyboard.press("Enter")
                page.wait_for_function(
                    "(word) => (document.querySelector('#lastResult').textContent || '').toLowerCase().includes(word)",
                    arg=kind,
                    timeout=20_000,
                )
                kinds = []
                for row in universe.sectors[universe.players["P2"].sector_id].mines:
                    value = row.kind.value if hasattr(row.kind, "value") else row.kind
                    if getattr(row, "owner_id", None) == "P2":
                        kinds.append(value)
                assert kind in kinds
        finally:
            browser.close()


def test_move_always_asks_and_one_exit_is_the_default(tmp_path, monkeypatch) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    with CuHost(tmp_path, TOK) as host, sync() as pw:
        universe = host.runner.state.universe
        many = _many_exit(universe)
        one = _one_exit(universe)
        exit_id = int(one.warps[0])
        far = _far(universe, int(one.id))
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            for width, height in VIEWPORTS:
                _place(host, int(many.id))
                _open(page, host, width, height)
                _sync(page, int(many.id))
                target = int(many.warps[0])
                page.locator("#warps button").first.click()
                page.wait_for_function(
                    "(id) => document.querySelector('#pSector').textContent.trim() === String(id)",
                    arg=str(target),
                    timeout=20_000,
                )
                assert page.locator("#menu[data-screen=ask-sector]:not([hidden])").count() == 0

                _place(host, int(one.id))
                _sync(page, int(one.id))
                page.keyboard.press("m")
                page.wait_for_selector("#sectorAsk", timeout=10_000)
                assert page.locator("#sectorAsk").input_value() == str(exit_id)
                page.keyboard.press("Enter")
                page.wait_for_function(
                    "(id) => document.querySelector('#pSector').textContent.trim() === String(id)",
                    arg=str(exit_id),
                    timeout=20_000,
                )

                _place(host, int(one.id))
                _sync(page, int(one.id))
                page.keyboard.press("m")
                page.wait_for_selector("#sectorAsk", timeout=10_000)
                page.locator("#sectorAsk").fill(str(far))
                page.keyboard.press("Enter")
                page.wait_for_selector("[data-testid=engage]", timeout=15_000)
                course = page.locator("[data-testid=course-line]").inner_text()
                assert str(far) in course and "hops" in course
                assert page.locator("#pSector").inner_text().strip() == str(one.id)
                if (width, height) == (1280, 720):
                    _shot(page, "1280-course.png")
                page.locator("[data-testid=engage]").click()
                page.wait_for_function(
                    "(id) => document.querySelector('#pSector').textContent.trim() !== String(id)",
                    arg=str(one.id),
                    timeout=30_000,
                )

                _place(host, int(many.id))
                _sync(page, int(many.id))
                page.keyboard.press("m")
                page.wait_for_selector("#sectorAsk", timeout=10_000)
                assert page.locator("#sectorAsk").input_value() == ""
                page.wait_for_timeout(400)
                assert page.locator("#pSector").inner_text().strip() == str(many.id)
                page.keyboard.press("Escape")
        finally:
            browser.close()


def _on_top(page, selector: str) -> dict:
    return page.evaluate(
        """(sel) => {
          const el = document.querySelector(sel);
          if (!el) return {ok: false, hit: "missing"};
          const r = el.getBoundingClientRect();
          const x = r.left + r.width / 2;
          const y = r.top + r.height / 2;
          if (x < 0 || y < 0 || x > window.innerWidth || y > window.innerHeight) {
            return {ok: false, hit: "offscreen", x, y};
          }
          const hit = document.elementFromPoint(x, y);
          const ok = !!(hit && (el === hit || el.contains(hit)));
          return {ok, hit: hit ? (hit.id || hit.className || hit.tagName) : "none"};
        }""",
        selector,
    )


def _forms_on_top(page) -> int:
    opened = 0
    count = page.locator("#here button").count()
    for index in range(count):
        button = page.locator("#here button").nth(index)
        if not button.is_enabled():
            continue
        cls = button.get_attribute("class") or ""
        if "dim" in cls.split() or "tbtn" in cls.split():
            continue
        label = " ".join(button.inner_text().split())
        button.click()
        page.wait_for_timeout(250)
        form = page.locator("#formSlot .frm")
        menu = page.locator("#menu:not([hidden])")
        if form.count() == 0 and menu.count() == 0:
            page.wait_for_function(
                "() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'",
                timeout=20_000,
            )
            continue
        selector = "#formSlot .frm" if form.count() else "#menu"
        seen = _on_top(page, selector)
        assert seen["ok"], f"{label} is under {seen.get('hit')}"
        opened += 1
        page.keyboard.press("Escape")
        page.wait_for_timeout(100)
    return opened


def test_here_forms_are_the_top_element_at_their_centre(tmp_path, monkeypatch) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    with CuHost(tmp_path, TOK) as host, sync() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            for profile in ("legacy", "v311"):
                K.V311_PROFILE = profile
                for width, height in ((1280, 720), (1600, 1000), (390, 844)):
                    _place(host, 1)
                    _open(page, host, width, height)
                    opened = _forms_on_top(page)
                    assert opened >= 1, profile
                    if profile == "legacy" and (width, height) == (1600, 1000):
                        _shot(page, "1600-here.png")
                    if profile == "v311" and (width, height) == (390, 844):
                        _shot(page, "390-here.png")
        finally:
            browser.close()


def test_day_countdown_uses_the_turn_clock(tmp_path, monkeypatch) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    with CuHost(tmp_path, TOK) as host, sync() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            for width, height in VIEWPORTS:
                _open(page, host, width, height)
                page.wait_for_timeout(300)
                assert page.locator("#dayEnds").is_hidden()
                page.evaluate(
                    """() => window.__tw2kTest.setTurnClock({
                      server_now: Date.now() / 1000,
                      day_seconds: 86400,
                      next_day_in_s: 125,
                      next_day_at: Date.now() / 1000 + 125
                    })"""
                )
                line = page.locator("#dayEnds").inner_text()
                assert DAY_LINE.fullmatch(line), line
                assert "02:05" in line
                assert page.evaluate("() => document.querySelector('#dayEnds').parentElement.id") == "turnsStat"
                if (width, height) == (1280, 720):
                    _shot(page, "1280-day.png")
                if (width, height) == (390, 844):
                    _shot(page, "390-day.png")
                page.evaluate(
                    "() => window.__tw2kTest.setTurnClock({server_now: 1, day_seconds: 86400})"
                )
                assert page.locator("#dayEnds").is_hidden()
                page.evaluate("() => window.__tw2kTest.setTurnClock(null)")
                assert page.locator("#dayEnds").is_hidden()
        finally:
            browser.close()
