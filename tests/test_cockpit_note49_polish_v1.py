"""NOTE 50. The growth switch is on only inside a test and put back."""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.agents.seat_brain import _organics_burn
from tw2k.engine.models import Commodity, Planet, PlanetClass
from tw2k.engine.planets import _apply_one_day, planet_growth_status

from tests._cu_host import CuHost

TOK = "note49-polish-token-p2-00000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "note49-polish-v1"


def _total(planet: Planet) -> int:
    return sum(int(n) for n in planet.colonists.values())


def _world(count: int) -> Planet:
    planet = Planet(id=1, sector_id=20, name="Phoenix", class_id=PlanetClass.M, owner_id="P1", origin="genesis")
    planet.colonists[Commodity.ORGANICS] = count
    planet.stockpile[Commodity.ORGANICS] = 0
    return planet


def test_tw2002_growth_keeps_the_organics_and_follows_the_half_cap():
    before = _world(2500)
    assert planet_growth_status(before.class_id, before.colonists, 0)["organics_consumption_per_day"] == 25
    assert _organics_burn({"organics_consumption_per_day": 0}) == 1
    _apply_one_day(before)
    assert int(before.stockpile[Commodity.ORGANICS]) == 100
    K.PLANET_GROWTH_MODE = "tw2002"
    try:
        assert _organics_burn({"organics_consumption_per_day": 0}) == 0
        growing = _world(2500)
        status = planet_growth_status(growing.class_id, growing.colonists, 0)
        assert status["organics_consumption_per_day"] == 0
        made = int(status["production"]["organics"])
        _apply_one_day(growing)
        assert int(growing.stockpile[Commodity.ORGANICS]) == made
        assert _total(growing) > 2500
        crowded = _world(20_000)
        _apply_one_day(crowded)
        assert _total(crowded) < 20_000
        assert int(crowded.stockpile[Commodity.ORGANICS]) == int(
            planet_growth_status(crowded.class_id, {Commodity.ORGANICS: 20_000}, 0)["production"]["organics"]
        )
    finally:
        K.PLANET_GROWTH_MODE = "legacy"


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


def _sit(universe, sector_id: int) -> None:
    player = universe.players["P2"]
    origin = universe.sectors[player.sector_id]
    if "P2" in origin.occupant_ids:
        origin.occupant_ids.remove("P2")
    player.sector_id = int(sector_id)
    player.planet_landed = None
    dest = universe.sectors[player.sector_id]
    if "P2" not in dest.occupant_ids:
        dest.occupant_ids.append("P2")


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
        browser.close()
        host.__exit__(None, None, None)
        pw.stop()


def test_the_citadel_form_capitalizes_the_shortfall(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    planet = next(iter(universe.planets.values()))
    old = universe.sectors.get(planet.sector_id)
    if old is not None and planet.id in getattr(old, "planet_ids", []):
        old.planet_ids.remove(planet.id)
    planet.sector_id = int(me.sector_id)
    planet.owner_id = "P2"
    planet.citadel_level = 1
    planet.fighters = 0
    planet.shields = 0
    planet.name = "Phoenix"
    for good in (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT):
        planet.stockpile[good] = 0
    if planet.id not in universe.sectors[me.sector_id].planet_ids:
        universe.sectors[me.sector_id].planet_ids.append(planet.id)
    _next(page, world["host"])
    page.locator("#here button", has_text="Phoenix").click()
    page.locator("#dangerOk").click()
    page.wait_for_function(
        "() => (document.querySelector('#lastResult').textContent || '').toLowerCase().includes('land')",
        timeout=20_000,
    )
    page.locator("#here button", has_text="Build citadel").click()
    page.wait_for_selector("#menu", timeout=10_000)
    text = page.locator("#menu").inner_text()
    assert "Short: fuel ore" in text
    assert " short" not in text
    _shoot(page, "short", "#menu")
    page.keyboard.press("Escape")


def test_one_cargo_hold_is_singular(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    _sit(universe, 1)
    me.credits = 5_000_000
    _next(page, world["host"])
    page.locator("#here button", has_text="StarDock: buy gear").click()
    page.wait_for_selector(".frm", timeout=10_000)
    page.locator(".frm select").evaluate(
        """el => {
          const hit = [...el.options].find(o => o.value === 'holds');
          if (hit) el.value = hit.value;
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }"""
    )
    page.locator(".frm input").fill("1")
    page.locator(".frm button", has_text="CONFIRM").click()
    page.wait_for_function(
        "() => (document.querySelector('#lastResult').textContent || '').includes('1 cargo hold')",
        timeout=20_000,
    )
    text = page.locator("#lastResult").inner_text()
    assert "1 holds" not in text
    log = page.locator("#log").inner_text()
    assert "1 cargo hold" in log
    assert "1 holds" not in log
    _shoot(page, "hold", "#lastResult")
    page.locator("#here button", has_text="StarDock: buy gear").click()
    page.wait_for_selector(".frm", timeout=10_000)
    page.locator(".frm select").evaluate(
        """el => {
          const hit = [...el.options].find(o => o.value === 'holds');
          if (hit) el.value = hit.value;
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }"""
    )
    page.locator(".frm input").fill("2")
    page.locator(".frm button", has_text="CONFIRM").click()
    page.wait_for_function(
        "() => (document.querySelector('#lastResult').textContent || '').includes('2 cargo holds')",
        timeout=20_000,
    )
    again = page.locator("#lastResult").inner_text()
    assert "2 holds" not in again
