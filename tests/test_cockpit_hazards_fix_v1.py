"""The NOTE 39 leftovers: one arrival line, names, and the reload warnings.

The browser tests share one page and run in this order. No stored flag moves.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._cu_host import CuHost
from tw2k.engine.models import EventKind, FighterDeployment, FighterMode, MineDeployment, MineType

pytestmark = pytest.mark.legacy_profile

TOK = "hazard-fix-token-p2-00000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-hazards-fix-v1"


def _page(pw, host):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    return browser, page


def _shoot(page, stem: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, height, name in ((1920, 1080, "1920"), (390, 844, "390")):
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(120)
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _back(page, needle: str) -> None:
    page.wait_for_function(
        "() => (document.querySelector('#lastResult').textContent || '').includes(" + repr(needle) + ")",
        timeout=20_000,
    )
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)


def _next(page, host, mutate=None) -> None:
    """Post one Wait. A day-ending confirm is dismissed, never accepted."""
    host.runner._wait_streak = {"P2": 0}
    page.keyboard.press("Escape")
    page.evaluate(
        "() => { if (window.__tw2kTest) window.__tw2kTest.resetWaits();"
        " const el = document.querySelector('#lastResult'); if (el) el.textContent = ''; }"
    )
    page.keyboard.press(".")
    menu = page.locator("#menu")
    if menu.count() and menu.is_visible() and "ends your day" in (menu.inner_text() or ""):
        page.keyboard.press("Escape")
        host.runner._wait_streak = {"P2": 0}
        page.evaluate("() => window.__tw2kTest.resetWaits()")
        page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    if mutate:
        mutate()
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=30_000)


def _signed_in(page, host) -> None:
    """Open the cockpit again. A reload drops the token the page takes off the address."""
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_function("() => document.querySelector('#sbDay').textContent !== '-'", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)


def _sit(universe, pid: str, sector_id: int) -> None:
    player = universe.players[pid]
    origin = universe.sectors[player.sector_id]
    if pid in origin.occupant_ids:
        origin.occupant_ids.remove(pid)
    player.sector_id = int(sector_id)
    player.planet_landed = None
    dest = universe.sectors[player.sector_id]
    if pid not in dest.occupant_ids:
        dest.occupant_ids.append(pid)
    if pid != "P2":
        player.turns_today = int(player.turns_per_day)


def _install():
    import pytest

    @pytest.fixture(scope="module")
    def world(tmp_path_factory):
        sync = pytest.importorskip("playwright.sync_api").sync_playwright
        pw = sync().start()
        host = CuHost(tmp_path_factory.mktemp("hazfix"), TOK)
        host.__enter__()
        browser, page = _page(pw, host)
        try:
            yield {"page": page, "universe": host.runner.state.universe, "host": host}
        finally:
            browser.close()
            host.__exit__(None, None, None)
            pw.stop()

    return world


world = _install()


def test_arrival_counts_each_hit_once(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    target = int(universe.sectors[me.sector_id].warps[0])

    def lay():
        universe.sectors[target].mines.append(MineDeployment(owner_id="P1", kind=MineType.ARMID, count=2))
        me.ship.shields = 400

    _next(page, world["host"], lay)
    page.evaluate("() => { const el = document.querySelector('#lastResult'); if (el) el.textContent = ''; }")
    page.locator("#warps button", has_text=str(target)).first.click()
    page.wait_for_function(
        "() => { const t = document.querySelector('#lastResult').textContent || '';"
        " return t.includes('mines hit') && t.includes('Computer, then O'); }",
        timeout=40_000,
    )
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    text = page.locator("#lastResult").inner_text()
    assert text.count("mines hit") == 1
    assert "avoid this sector" not in text
    assert "Computer, then O" in text
    _shoot(page, "arrival")


def test_mines_name_the_trader(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    sector = universe.sectors[me.sector_id]

    def plant():
        sector.mines.append(MineDeployment(owner_id="P1", kind=MineType.ARMID, count=4))
        _sit(universe, "P1", me.sector_id)

    _next(page, world["host"], plant)
    text = page.locator("#sectorText").inner_text()
    assert "(belong to HBot)" in text
    assert "personal" not in text
    _shoot(page, "mines")
    sector.mines = [row for row in sector.mines if row.owner_id != "P1"]


def test_owner_notice_names_the_trader_and_does_not_repeat(world):
    page = world["page"]
    universe = world["universe"]

    def hit():
        universe.emit(
            EventKind.MINE_DETONATED,
            actor_id="P2",
            sector_id=90,
            payload={"hits": 1, "damage": 200, "victim": "P1"},
            summary="1 armid mines hit HBot",
        )

    _next(page, world["host"], hit)
    text = page.locator("#lastResult").inner_text()
    assert "Your mines hit HBot in sector 90 for 200 damage." in text
    stored = page.evaluate("() => localStorage.getItem('tw2k-alert-P2')")
    assert stored and int(stored) > 0
    _signed_in(page, world["host"])
    assert "Your mines hit" not in page.locator("#lastResult").inner_text()
    _shoot(page, "notice")


def test_end_of_day_warning_uses_the_server_count(world):
    page = world["page"]
    host = world["host"]
    host.runner._wait_streak = {"P2": 3}
    page.wait_for_function("() => window.__tw2kTest.serverWaits() >= 3", timeout=10_000)
    page.keyboard.press("Escape")
    page.keyboard.press(".")
    page.wait_for_selector("#menu:not([hidden])", timeout=10_000)
    assert "One more Wait ends your day" in page.locator("#menu").inner_text()
    _shoot(page, "wait")
    page.keyboard.press("Escape")
    host.runner._wait_streak = {"P2": 0}
    page.evaluate("() => window.__tw2kTest.resetWaits()")
    page.wait_for_function("() => window.__tw2kTest.serverWaits() === 0", timeout=10_000)


def test_port_report_marks_a_holo_port_and_the_buying_room(world):
    page = world["page"]
    me = world["universe"].players["P2"]
    me.known_ports[8801] = {
        "class": "BSS",
        "last_seen_day": 1,
        "stock": {"fuel_ore": {"current": 0, "max": 100, "price": 0}},
    }
    me.known_ports[8802] = {
        "class": "SBB",
        "last_seen_day": 1,
        "stock": {"fuel_ore": {"current": 0, "max": 100, "price": 27, "side": "buys_from_player"}},
    }
    _next(page, world["host"])
    page.keyboard.press("C")
    page.keyboard.press("R")
    page.wait_for_selector("[data-port=report]", timeout=10_000)
    text = page.locator("#menu").inner_text()
    assert "not docked" in text
    assert "Buying 100 (100%)" in text
    _shoot(page, "ports")
    page.keyboard.press("Escape")


def test_citadel_form_says_what_is_being_built(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    planet = next(iter(universe.planets.values()))
    origin = universe.sectors[planet.sector_id]
    if planet.id in origin.planet_ids:
        origin.planet_ids.remove(planet.id)
    planet.sector_id = me.sector_id
    dest = universe.sectors[me.sector_id]
    if planet.id not in dest.planet_ids:
        dest.planet_ids.append(planet.id)
    planet.owner_id = "P2"
    planet.citadel_level = 0
    planet.citadel_target = 1
    planet.citadel_complete_day = 2
    planet.name = "Home Rock"
    _next(page, world["host"])
    page.locator("#here button", has_text="Land on").click()
    assert "Your planet." in page.locator("#menu").inner_text()
    _shoot(page, "own")
    page.locator("#dangerOk").click()
    _back(page, "ok")
    page.keyboard.press("B")
    page.wait_for_selector("#menu", timeout=10_000)
    text = page.locator("#menu").inner_text()
    assert "Citadel L1 is being built, ready day 2." in text
    assert "Fuel ore 0" not in text
    _shoot(page, "citadel")
    page.keyboard.press("Escape")
    page.keyboard.press("Q")
    _back(page, "ok")


def test_held_command_says_it_will_run(world):
    page = world["page"]
    page.evaluate("() => window.__tw2kTest.setAwaiting(false)")
    page.locator("#warps button").first.click()
    text = page.locator("#lastResult").inner_text()
    assert "will run when your turn comes" in text
    page.locator("#warps button").first.click()
    assert page.locator("#lastResult").inner_text().count("will run when your turn comes") == 1
    _shoot(page, "held")
    page.evaluate("() => window.__tw2kTest.setAwaiting(true)")


def test_small_words_use_the_singular(world):
    page = world["page"]
    me = world["universe"].players["P2"]
    me.known_warps = {int(me.sector_id): []}
    me.known_sectors = {int(me.sector_id)}
    _next(page, world["host"])
    # Under load the page can still hold the observation from before the known map was cut to one
    # sector (peek reads are cached for half a second), so open the panel again until it reads that map.
    text = ""
    for _ in range(40):
        page.keyboard.press("Escape")
        page.keyboard.press("C")
        page.keyboard.press("K")
        page.wait_for_function(
            "() => { const m = document.querySelector('#menu');"
            " return !!m && !m.hidden && (m.textContent || '').includes('You have explored'); }",
            timeout=10_000,
        )
        text = page.locator("#menu").inner_text()
        if text.count("warps") == 1:
            break
        page.wait_for_timeout(500)
    assert text.count("warps") == 1, text
    assert "1 sector" in text
    assert "1 sectors" not in text
    _shoot(page, "known")
    page.keyboard.press("Escape")


def test_defensive_challenge_names_only_the_real_options(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]

    def plant():
        sector = universe.sectors[me.sector_id]
        sector.fighters = FighterDeployment(owner_id="P1", count=10, mode=FighterMode.DEFENSIVE)
        _sit(universe, "P1", me.sector_id)
        back = int(sector.warps[0]) if sector.warps else int(me.sector_id)
        me.fighter_challenge = {"sector_id": int(me.sector_id), "from_sector": back, "mode": "defensive"}

    _next(page, world["host"], plant)
    page.keyboard.press("L")
    page.wait_for_function(
        "() => (document.querySelector('#lastResult').textContent || '').includes('Answer the fighters first')",
        timeout=10_000,
    )
    text = page.locator("#lastResult").inner_text()
    assert "pay the toll" not in text
    assert "attack" in text
    _shoot(page, "challenge")
    page.keyboard.press("Escape")
    me.fighter_challenge = None
    universe.sectors[me.sector_id].fighters = None
