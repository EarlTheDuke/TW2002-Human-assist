"""NOTE 44. One page, in this order. Switches are turned on only inside a test and put back."""

from __future__ import annotations

from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine.models import FighterDeployment, FighterMode, MineDeployment, MineType

from tests._cu_host import CuHost

TOK = "n42-polish-token-p2-00000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "note42-polish-v1"


def _page(pw, host):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    return browser, page


def _shoot(page, stem: str, selector: str = "") -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, height, name in ((1920, 1080, "1920"), (390, 844, "390")):
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(120)
        page.evaluate(
            "(sel) => { const el = (sel && document.querySelector(sel)) || document.querySelector('#lastResult'); if (el) el.scrollIntoView({ block: 'center' }); }",
            selector,
        )
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _back(page, needle: str) -> None:
    page.wait_for_function(
        "() => (document.querySelector('#lastResult').textContent || '').includes(" + repr(needle) + ")",
        timeout=20_000,
    )
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)


def _next(page, host, mutate=None) -> None:
    host.runner._wait_streak = {"P2": 0}
    page.keyboard.press("Escape")
    page.evaluate("() => { if (window.__tw2kTest) window.__tw2kTest.resetWaits(); const el = document.querySelector('#lastResult'); if (el) el.textContent = ''; }")
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


def _install():
    import pytest

    @pytest.fixture(scope="module")
    def world(tmp_path_factory):
        sync = pytest.importorskip("playwright.sync_api").sync_playwright
        pw = sync().start()
        host = CuHost(tmp_path_factory.mktemp("n42"), TOK)
        host.__enter__()
        browser, page = _page(pw, host)
        try:
            yield {"page": page, "universe": host.runner.state.universe, "host": host}
        finally:
            K.SIEGE_REPORT_MODE = "legacy"
            K.PLANET_LANDING_COMBAT_MODE = "legacy"
            browser.close()
            host.__exit__(None, None, None)
            pw.stop()

    return world


world = _install()


def test_a_mine_hit_says_the_avoid_line_once(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    target = int(universe.sectors[me.sector_id].warps[0])
    universe.sectors[target].mines.append(MineDeployment(owner_id="P1", kind=MineType.ARMID, count=10))
    universe.sectors[target].fighters = FighterDeployment(owner_id="P1", count=60, mode=FighterMode.DEFENSIVE)
    me.ship.shields = 200
    me.ship.fighters = 400
    page.locator("#warps button", has_text=str(target)).first.click()
    _back(page, "mines hit")
    text = page.locator("#lastResult").inner_text()
    assert text.lower().count("adds it to the avoid list") == 1
    assert text.index("mines hit") < text.lower().index("adds it to the avoid list")
    assert "Answer the fighters first" in text
    log = page.locator("#log").inner_text()
    assert "avoid this sector?" not in log
    assert log.lower().count("adds it to the avoid list") == 1
    _shoot(page, "avoid", "#lastResult")


def test_a_landing_that_destroys_the_ship_names_the_losses(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    sector = universe.sectors[me.sector_id]
    sector.fighters = None
    sector.mines = [row for row in sector.mines if row.owner_id == "P2"]
    me.fighter_challenge = None
    planet = next(iter(universe.planets.values()))
    old = universe.sectors.get(planet.sector_id)
    if old is not None and planet.id in getattr(old, "planet_ids", []):
        old.planet_ids.remove(planet.id)
    planet.sector_id = int(me.sector_id)
    planet.owner_id = "P1"
    planet.citadel_level = 0
    planet.fighters = 400
    planet.shields = 0
    planet.military_reaction_pct = 100
    planet.name = "Phoenix"
    if planet.id not in sector.planet_ids:
        sector.planet_ids.append(planet.id)
    me.ship.fighters = 30
    me.ship.shields = 0
    K.PLANET_LANDING_COMBAT_MODE = "tw2002"
    K.SIEGE_REPORT_MODE = "tw2002"
    try:
        _next(page, world["host"])
        page.locator("#here button", has_text="Phoenix").click()
        page.locator("#dangerOk").click()
        page.wait_for_function(
            "() => { const t = document.querySelector('#lastResult').textContent || '';"
            " if (t.includes('ship destroyed') && t.includes('fighters killed')) { window.__hit = t; return true; } return false; }",
            timeout=20_000,
        )
        text = page.evaluate("() => window.__hit")
        assert "of the planet's fighters" in text
        assert "of your fighters" in text
        assert "Credits on board lost" in text
        _shoot(page, "siege", "#lastResult")
    finally:
        K.PLANET_LANDING_COMBAT_MODE = "legacy"
        K.SIEGE_REPORT_MODE = "legacy"
