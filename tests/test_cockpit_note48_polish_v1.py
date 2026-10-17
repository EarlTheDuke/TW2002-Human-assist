"""NOTE 49. Each test has its own game. The avoid switch is on only inside a test and put back."""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine.models import Commodity
from tw2k.engine.planets import planet_growth_status

from tests._cu_host import CuHost

TOK = "note48-polish-token-p2-00000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "note48-polish-v1"


def _page(pw, host):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    return browser, page


def _shoot(page, stem: str, selector: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, name in ((1920, "1920"), (390, "390")):
        page.set_viewport_size({"width": width, "height": 844 if width == 390 else 1080})
        page.wait_for_timeout(80)
        page.evaluate(
            "(sel) => { const el = document.querySelector(sel); if (el) el.scrollIntoView({ block: 'center' }); }",
            selector,
        )
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _next(page, host) -> None:
    host.runner._wait_streak = {"P2": 0}
    page.evaluate("() => { if (window.__tw2kTest) window.__tw2kTest.resetWaits(); }")
    page.keyboard.press("Escape")
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)


def _open_avoid(page) -> None:
    page.keyboard.press("Escape")
    page.keyboard.press("C")
    page.keyboard.press("O")
    page.wait_for_selector(".frm", timeout=10_000)


def _confirm(page, needle: str) -> str:
    page.locator(".frm button", has_text="CONFIRM").click()
    page.wait_for_function(
        "() => (document.querySelector('#lastResult').textContent || '').includes(" + repr(needle) + ")",
        timeout=20_000,
    )
    return page.locator("#lastResult").inner_text()


@pytest.fixture
def world(tmp_path):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    host = CuHost(tmp_path, TOK)
    host.__enter__()
    browser, page = _page(pw, host)
    try:
        yield {"page": page, "universe": host.runner.state.universe, "host": host}
    finally:
        K.AVOID_MODE = "legacy"
        K.SIEGE_REPORT_MODE = "legacy"
        K.PLANET_LANDING_COMBAT_MODE = "legacy"
        browser.close()
        host.__exit__(None, None, None)
        pw.stop()


def test_later_actions_keep_their_own_result_lines(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    K.AVOID_MODE = "live"
    _next(page, world["host"])
    _open_avoid(page)
    page.locator(".frm input").fill("12")
    added = _confirm(page, "Sector 12 added")
    assert "avoided: 12" in added
    _open_avoid(page)
    page.locator(".frm input").fill("0")
    cleared = _confirm(page, "Avoid list cleared")
    assert ".." not in cleared
    target = int(universe.sectors[me.sector_id].warps[0])
    page.locator("#warps button", has_text=str(target)).first.click()
    page.wait_for_function(
        "() => /warped/i.test(document.querySelector('#lastResult').textContent || '')",
        timeout=20_000,
    )
    warp = page.locator("#lastResult").inner_text()
    assert "Avoid list cleared" not in warp
    assert str(target) in warp
    here = int(me.sector_id)
    hops = {int(sid) for sid in universe.sectors[here].warps}
    far = next(int(sid) for sid in universe.sectors if int(sid) not in hops and int(sid) != here and int(sid) > 1)
    page.keyboard.press("Escape")
    page.keyboard.press("C")
    page.keyboard.press("F")
    page.wait_for_selector("#sectorAsk", timeout=10_000)
    page.locator("#sectorAsk").fill(str(far))
    page.locator("#sectorGo").click()
    page.wait_for_function(
        "() => /plotted course/i.test(document.querySelector('#lastResult').textContent || '')",
        timeout=20_000,
    )
    plot = page.locator("#lastResult").inner_text()
    assert "Avoid list cleared" not in plot
    log = page.locator("#log").inner_text()
    assert log.find("plotted course") < log.find("Avoid list cleared")
    died = int(me.sector_id)
    sector = universe.sectors[died]
    sector.fighters = None
    sector.mines = [row for row in sector.mines if row.owner_id == "P2"]
    me.fighter_challenge = None
    planet = next(iter(universe.planets.values()))
    old = universe.sectors.get(planet.sector_id)
    if old is not None and planet.id in getattr(old, "planet_ids", []):
        old.planet_ids.remove(planet.id)
    planet.sector_id = died
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
    _next(page, world["host"])
    page.locator("#here button", has_text="Phoenix").click()
    page.locator("#dangerOk").click()
    page.wait_for_function(
        "() => { const t = document.querySelector('#lastResult').textContent || '';"
        " if (t.includes('ship destroyed') && !t.includes('Avoid list cleared')) { window.__hit = t; return true; } return false; }",
        timeout=20_000,
    )
    lost = page.evaluate("() => window.__hit")
    assert "ship destroyed" in lost
    assert "Credits on board lost" in lost
    later = page.locator("#log").inner_text()
    assert later.find("ship destroyed") < later.find("Avoid list cleared")
    _shoot(page, "later", "#lastResult")


def test_an_unknown_sector_is_refused(world):
    page = world["page"]
    universe = world["universe"]
    universe.players["P2"].avoided_sectors = [12, 40]
    K.AVOID_MODE = "live"
    _next(page, world["host"])
    _open_avoid(page)
    size = int(universe.config.universe_size)
    assert page.locator(".frm input").get_attribute("max") == str(size)
    page.locator(".frm input").fill("99999")
    text = _confirm(page, "REFUSED")
    assert "99,999" in text
    assert "added to the avoid list" not in text
    _shoot(page, "invalid", "#lastResult")
    _open_avoid(page)
    form = page.locator(".frm").inner_text()
    assert "12" in form and "40" in form
    page.keyboard.press("Escape")


def test_the_clear_line_has_one_period(world):
    page = world["page"]
    universe = world["universe"]
    universe.players["P2"].avoided_sectors = [12]
    K.AVOID_MODE = "live"
    _next(page, world["host"])
    _open_avoid(page)
    page.locator(".frm input").fill("0")
    text = _confirm(page, "Avoid list cleared")
    assert "none.." not in text
    assert "Avoided sectors: none. Turns spent" in text
    _shoot(page, "period", "#lastResult")


def test_a_sector_already_listed_says_so(world):
    page = world["page"]
    universe = world["universe"]
    universe.players["P2"].avoided_sectors = [12, 40]
    K.AVOID_MODE = "live"
    _next(page, world["host"])
    _open_avoid(page)
    page.locator(".frm input").fill("12")
    text = _confirm(page, "already on the avoid list")
    assert "avoided: 12, 40" in text
    assert "added to the avoid list" not in text
    _shoot(page, "already", "#lastResult")


def test_a_death_sector_is_named_on_the_result(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    sector = universe.sectors[me.sector_id]
    died = int(me.sector_id)
    sector.fighters = None
    sector.mines = [row for row in sector.mines if row.owner_id == "P2"]
    me.fighter_challenge = None
    planet = next(iter(universe.planets.values()))
    old = universe.sectors.get(planet.sector_id)
    if old is not None and planet.id in getattr(old, "planet_ids", []):
        old.planet_ids.remove(planet.id)
    planet.sector_id = died
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
    K.AVOID_MODE = "live"
    K.PLANET_LANDING_COMBAT_MODE = "tw2002"
    K.SIEGE_REPORT_MODE = "tw2002"
    _next(page, world["host"])
    page.locator("#here button", has_text="Phoenix").click()
    page.locator("#dangerOk").click()
    page.wait_for_function(
        "() => { const t = document.querySelector('#lastResult').textContent || '';"
        " if (t.includes('ship destroyed') && t.includes('is now on your avoid list')) { window.__hit = t; return true; } return false; }",
        timeout=20_000,
    )
    text = page.evaluate("() => window.__hit")
    assert f"Sector {died} is now on your avoid list" in text
    assert "Credits on board lost" in text
    log = page.locator("#log").inner_text()
    assert f"Sector {died} is now on your avoid list" in log
    _shoot(page, "death", "#lastResult")


def test_the_planet_card_shows_the_organics_that_arrive(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    planet = next(iter(universe.planets.values()))
    old = universe.sectors.get(planet.sector_id)
    if old is not None and planet.id in getattr(old, "planet_ids", []):
        old.planet_ids.remove(planet.id)
    planet.sector_id = int(me.sector_id)
    planet.owner_id = "P2"
    planet.fighters = 0
    planet.shields = 0
    planet.name = "Harvest"
    planet.colonists[Commodity.FUEL_ORE] = 1000
    planet.colonists[Commodity.ORGANICS] = 2500
    planet.colonists[Commodity.EQUIPMENT] = 0
    planet.stockpile[Commodity.ORGANICS] = 0
    if planet.id not in universe.sectors[me.sector_id].planet_ids:
        universe.sectors[me.sector_id].planet_ids.append(planet.id)
    growth = planet_growth_status(planet.class_id, planet.colonists, 0)
    made = int(growth["production"]["organics"])
    eat = int(growth["organics_consumption_per_day"])
    arrives = max(0, made - eat)
    fuel = int(growth["production"]["fuel_ore"])
    _next(page, world["host"])
    page.locator("#here button", has_text="Harvest").click()
    page.locator("#dangerOk").click()
    page.wait_for_function(
        "() => (document.querySelector('#lastResult').textContent || '').toLowerCase().includes('land')",
        timeout=20_000,
    )
    page.wait_for_selector("[data-day=organics]", timeout=10_000)
    organic = page.locator("[data-day=organics] + div").inner_text()
    assert f"{arrives:,} per day" in organic
    assert f"colonists eat {eat:,}" in organic
    assert f"{made:,} per day" not in organic or arrives == made
    fuel_line = page.locator("[data-day=fuel_ore] + div").inner_text()
    assert f"{fuel:,} per day" in fuel_line
    assert "colonists eat" not in fuel_line
    _shoot(page, "organics", "[data-day=organics]")
