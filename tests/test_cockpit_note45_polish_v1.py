"""NOTE 47. Prices, NavHaz, the avoid list, Terra, ranks, and colonist moves."""

from __future__ import annotations

from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine.models import Commodity, PlanetClass

from tests._cu_host import CuHost

TOK = "note45-polish-token-p2-00000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "note45-polish-v1"


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


def _install():
    import pytest

    @pytest.fixture(scope="module")
    def world(tmp_path_factory):
        sync = pytest.importorskip("playwright.sync_api").sync_playwright
        pw = sync().start()
        host = CuHost(tmp_path_factory.mktemp("note45"), TOK)
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


def test_navhaz_shows_on_the_sector_line(world):
    page = world["page"]
    universe = world["universe"]
    sector = universe.sectors[universe.players["P2"].sector_id]
    sector.nav_hazard = 12
    try:
        _next(page, world["host"])
        text = page.locator("[data-navhaz=here]").inner_text()
        assert "12" in text
        _shoot(page, "navhaz", "#sectorText")
    finally:
        sector.nav_hazard = 0


def test_the_avoid_form_lists_the_saved_sectors(world):
    page = world["page"]
    universe = world["universe"]
    universe.players["P2"].avoided_sectors = [12, 40]
    K.AVOID_MODE = "live"
    try:
        _next(page, world["host"])
        page.keyboard.press("C")
        page.keyboard.press("O")
        page.wait_for_selector(".frm", timeout=10_000)
        text = page.locator(".frm").inner_text()
        assert "12" in text and "40" in text
        _shoot(page, "avoid", ".frm")
        page.keyboard.press("Escape")
    finally:
        K.AVOID_MODE = "legacy"
        universe.players["P2"].avoided_sectors = []


def test_terra_uses_the_original_planet_line(world):
    page = world["page"]
    universe = world["universe"]
    if universe.terra_colonists is None:
        universe.terra_colonists = 1000
    _sit(universe, 1)
    _next(page, world["host"])
    text = page.locator("[data-planet=class]", has_text="Terra").inner_text()
    assert text.startswith("(M)")
    assert "Terra" in text
    _shoot(page, "terra", "#sectorText")


def test_the_rank_ladder_is_on_the_reference(world):
    page = world["page"]
    page.keyboard.press("Z")
    page.wait_for_selector("[data-rank='0']", timeout=20_000)
    text = page.locator("#menu").inner_text()
    assert "Civilian" in text
    assert "experience" in text.lower()
    page.keyboard.press("Escape")


def test_the_same_product_is_not_a_colonist_move(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    planet = next(iter(universe.planets.values()))
    old = universe.sectors.get(planet.sector_id)
    if old is not None and planet.id in getattr(old, "planet_ids", []):
        old.planet_ids.remove(planet.id)
    planet.sector_id = int(me.sector_id)
    planet.owner_id = "P2"
    planet.name = "Haul Rock"
    planet.fighters = 0
    planet.shields = 0
    planet.colonists[Commodity.FUEL_ORE] = 15
    if planet.id not in universe.sectors[me.sector_id].planet_ids:
        universe.sectors[me.sector_id].planet_ids.append(planet.id)
    _next(page, world["host"])
    page.locator("#here button", has_text="Haul Rock").click()
    page.locator("#dangerOk").click()
    page.wait_for_function(
        "() => /landed|your planet/i.test(document.querySelector('#lastResult').textContent || '')"
        " || document.querySelector('.planet')",
        timeout=20_000,
    )
    page.keyboard.press("N")
    page.wait_for_selector(".frm [data-n=from]", timeout=10_000)
    state = page.evaluate(
        """() => {
          const from = document.querySelector('.frm [data-n=from]');
          const to = document.querySelector('.frm [data-n=to]');
          const qty = document.querySelector('.frm [data-n=qty]');
          const fuel = [...from.options].find(o => o.value === 'fuel_ore');
          if (fuel) from.value = 'fuel_ore';
          from.dispatchEvent(new Event('change'));
          const same = [...to.options].find(o => o.value === from.value);
          return { disabled: !!(same && same.disabled), qty: qty.value, to: to.value, from: from.value };
        }"""
    )
    assert state["disabled"]
    assert state["to"] != state["from"]
    assert int(state["qty"]) == 15
    _shoot(page, "colonists", ".frm")
    page.keyboard.press("Escape")


def test_a_class_m_card_shows_the_colonist_trend(world):
    page = world["page"]
    universe = world["universe"]
    planet = next(p for p in universe.planets.values() if p.name == "Haul Rock")
    planet.class_id = PlanetClass.M
    K.CLASS_M_FIDELITY_MODE = "live"
    try:
        _next(page, world["host"])
        page.wait_for_selector("[data-colonists=trend]", timeout=10_000)
        text = page.locator("[data-colonists=trend]").inner_text()
        assert text
        _shoot(page, "trend", ".planet")
    finally:
        K.CLASS_M_FIDELITY_MODE = "legacy"
