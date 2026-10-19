"""NOTE 48. Each test has its own game. The avoid switch is on only inside a test and put back."""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K

from tests._cu_host import CuHost

TOK = "note47-polish-token-p2-00000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "note47-polish-v1"


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


@pytest.fixture
def world(tmp_path):
    _prior_avoid_mode = K.AVOID_MODE
    _prior_siege_report_mode = K.SIEGE_REPORT_MODE
    _prior_planet_landing_combat_mode = K.PLANET_LANDING_COMBAT_MODE
    try:
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
    finally:
        K.AVOID_MODE = _prior_avoid_mode
        K.SIEGE_REPORT_MODE = _prior_siege_report_mode
        K.PLANET_LANDING_COMBAT_MODE = _prior_planet_landing_combat_mode


def test_typing_zero_clears_the_avoid_list(world):
    _prior_avoid_mode = K.AVOID_MODE
    try:
        page = world["page"]
        universe = world["universe"]
        universe.players["P2"].avoided_sectors = [12, 40]
        K.AVOID_MODE = "live"
        _next(page, world["host"])
        _open_avoid(page)
        assert "12" in page.locator(".frm").inner_text()
        page.locator(".frm input").fill("0")
        page.locator(".frm button", has_text="CONFIRM").click()
        page.wait_for_function(
            "() => (document.querySelector('#lastResult').textContent || '').includes('Avoid list cleared')",
            timeout=20_000,
        )
        text = page.locator("#lastResult").inner_text()
        assert "Avoided sectors: none" in text
        _shoot(page, "clear", "#lastResult")
        _open_avoid(page)
        form = page.locator(".frm").inner_text()
        assert "Avoided sectors: none" in form
        assert "12" not in form and "40" not in form
        page.keyboard.press("Escape")
    finally:
        K.AVOID_MODE = _prior_avoid_mode


def test_adding_a_sector_names_it_on_the_result_and_in_the_log(world):
    _prior_avoid_mode = K.AVOID_MODE
    try:
        page = world["page"]
        universe = world["universe"]
        universe.players["P2"].avoided_sectors = [12]
        K.AVOID_MODE = "live"
        _next(page, world["host"])
        page.evaluate("() => { const el = document.querySelector('#lastResult'); if (el) el.textContent = 'ok — bought 200 shields for 39,400 cr. Turns spent 0. Credits +0.'; }")
        _open_avoid(page)
        page.locator(".frm input").fill("40")
        page.locator(".frm button", has_text="CONFIRM").click()
        page.wait_for_function(
            "() => (document.querySelector('#lastResult').textContent || '').includes('Sector 40 added to the avoid list')",
            timeout=20_000,
        )
        text = page.locator("#lastResult").inner_text()
        assert "avoided: 12, 40" in text
        assert "bought 200 shields" not in text
        log = page.locator("#log").inner_text()
        assert "Sector 40 added to the avoid list" in log
        assert "avoided: 12, 40" in log
        _shoot(page, "add", "#lastResult")
        page.keyboard.press("Escape")
    finally:
        K.AVOID_MODE = _prior_avoid_mode


def test_a_landing_siege_names_whose_fighters_died(world):
    _prior_planet_landing_combat_mode = K.PLANET_LANDING_COMBAT_MODE
    _prior_siege_report_mode = K.SIEGE_REPORT_MODE
    try:
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
        _next(page, world["host"])
        page.locator("#here button", has_text="Phoenix").click()
        page.locator("#dangerOk").click()
        page.wait_for_function(
            "() => { const t = document.querySelector('#lastResult').textContent || '';"
            " if (t.includes('ship destroyed') && t.includes('of your fighters')) { window.__hit = t; return true; } return false; }",
            timeout=20_000,
        )
        text = page.evaluate("() => window.__hit")
        assert "You killed" in text
        assert "of the planet's fighters" in text
        assert "of your fighters" in text
        assert "Credits on board lost" in text
        _shoot(page, "siege", "#lastResult")
    finally:
        K.PLANET_LANDING_COMBAT_MODE = _prior_planet_landing_combat_mode
        K.SIEGE_REPORT_MODE = _prior_siege_report_mode
