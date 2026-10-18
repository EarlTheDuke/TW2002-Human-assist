"""NOTE 64 class-m-production-units-v1: under the class M switch, production, fighters and growth count people in thousands.

Source: S1_planet_handbook_v1.01.html (production section and the class M table) and Ben's NOTE 19
ruling, "production is colonists(1000s)/ratio". Profile off stays the old game.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests.test_citadel_class_tables_v1 import _plant
from tests.test_phase_abc import _make_universe
from tw2k.engine.models import Commodity, Planet, PlanetClass
from tw2k.engine.observation import build_observation
from tw2k.engine.planets import (
    _accrue_planet,
    _apply_one_day,
    colonist_trend,
    fighters_from_colonists,
    planet_growth_status,
)

SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "class-m-production-units-v1"
TOK = "note64-classm-token-p2-00000000000"


@pytest.fixture
def v311():
    old = K.V311_PROFILE
    K.V311_PROFILE = "v311"
    try:
        yield
    finally:
        K.V311_PROFILE = old


def _world(class_id: PlanetClass = PlanetClass.M, **pools: int) -> Planet:
    planet = Planet(id=1, sector_id=20, name="Phoenix", class_id=class_id, owner_id="P1", origin="genesis")
    for name, qty in pools.items():
        planet.colonists[Commodity(name)] = qty
    return planet


def _made(planet: Planet) -> tuple[int, int, int, int]:
    return (
        int(planet.stockpile.get(Commodity.FUEL_ORE, 0)),
        int(planet.stockpile.get(Commodity.ORGANICS, 0)),
        int(planet.stockpile.get(Commodity.EQUIPMENT, 0)),
        int(planet.fighters),
    )


def test_the_s1_example_makes_500_fuel_100_organics_and_60_fighters(v311):
    """S1: "if you placed 1,500 colonists under Fuel Ore on a Class M planet (FOE= 3/7/13, n/10), the colonists
    would produce 500 units of fuel and 50 fighters per day. If you added another 700 colonists to produce
    Organics, you would get 500 Fuel, 100 Organics, and 60 fighters per day." NOTE 19: those are thousands."""
    assert K.class_m_fidelity_live()
    fuel = _world(fuel_ore=1_500_000)
    _apply_one_day(fuel)
    assert _made(fuel) == (500, 0, 0, 50)
    both = _world(fuel_ore=1_500_000, organics=700_000)
    _apply_one_day(both)
    assert _made(both) == (500, 100, 0, 60)
    assert fighters_from_colonists(PlanetClass.M, {"fuel_ore": 1_500_000, "organics": 700_000}) == 60


def test_the_191000_start_on_fuel_makes_63_fuel_and_6_fighters(v311):
    """S1 ratio 3 and fighters n/10 (30 per fighter on fuel), NOTE 19 thousands: 191,000 people are 191 thousand,
    191 // 3 = 63 fuel and 191 // 30 = 6 fighters a day (D16 saw 63,666 and 6,366)."""
    planet = _world(fuel_ore=K.LIVE_STARTING_COLONISTS)
    _apply_one_day(planet)
    assert _made(planet) == (63, 0, 0, 6)
    assert planet_growth_status(planet.class_id, {"fuel_ore": 191_000}, 0)["production"] == {
        "fuel_ore": 63, "organics": 0, "equipment": 0,
    }


def test_class_m_output_stops_at_the_s1_max_per_day(v311):
    """S1 class M table: Max Prod/Day at 15,000 colonists, Max/Day 5,000 / 2,142 / 1,153 and fighters 829 a day;
    "The daily production of FOE products is based on a bell curve, so the maximum production occurs at 50% of
    the maximum population." No curve shape is published, so above 15,000k a pool stays at the peak."""
    for people in (15_000_000, 25_000_000):
        planet = _world(fuel_ore=people, organics=people, equipment=people)
        _apply_one_day(planet)
        assert _made(planet) == (5_000, 2_142, 1_153, 829), people
    assert fighters_from_colonists(PlanetClass.M, {"fuel_ore": 29_000_000, "organics": 29_000_000, "equipment": 29_000_000}) == 829


def test_class_m_below_half_the_pool_cap_grows(v311):
    """S1: "Colonists below the 50% mark tend to multiply and increase." Each class M product pool holds
    30,000 thousand (NOTE 19 (b)); the rate is not published, so the engine's 5% stays. Above half a pool does
    not shrink; only the extra above the pool cap dies back (NOTE 19 (c))."""
    planet = _world(fuel_ore=1_500_000, organics=700_000)
    assert planet_growth_status(planet.class_id, planet.colonists, 0)["growth_active"] is True
    _apply_one_day(planet)
    assert planet.colonists[Commodity.FUEL_ORE] == 1_575_000
    assert planet.colonists[Commodity.ORGANICS] == 735_000
    start = _world(colonists=K.LIVE_STARTING_COLONISTS)
    _apply_one_day(start)
    assert start.colonists[Commodity.COLONISTS] == 200_550
    full = _world(fuel_ore=20_000_000)
    assert planet_growth_status(full.class_id, full.colonists, 0)["growth_active"] is False
    _apply_one_day(full)
    assert full.colonists[Commodity.FUEL_ORE] == 20_000_000
    over = _world(fuel_ore=K.CLASS_M_CATEGORY_CAP + 10_000_000)
    _apply_one_day(over)
    assert over.colonists[Commodity.FUEL_ORE] == K.CLASS_M_CATEGORY_CAP + 9_500_000
    assert "grows about 5% a day" in colonist_trend(PlanetClass.M, 191_000)


def test_a_day_paid_in_slices_matches_the_daily_number(v311):
    """The day-slice split (_split_units, prod_remain) pays the corrected daily number once a day."""
    planet = _world(fuel_ore=20_000_000)
    day = int(K.TURN_REGEN_DAY_SECONDS)
    for _ in range(4):
        _accrue_planet(planet, day // 4)
    assert _made(planet) == (5_000, 0, 0, 500)


def test_profile_off_and_other_classes_are_unchanged():
    """Profile off is the old game: class M keeps the handbook unit as stored and the legacy table."""
    assert not K.class_m_fidelity_live()
    planet = _world(fuel_ore=1_500, organics=700)
    assert planet_growth_status(planet.class_id, planet.colonists, 0)["production"] == {
        "fuel_ore": 45, "organics": 35, "equipment": 0,
    }
    _apply_one_day(planet)
    assert _made(planet) == (45, 13, 0, 60)
    assert fighters_from_colonists(PlanetClass.M, {"fuel_ore": 1_500_000}) == 50_000
    old = K.V311_PROFILE
    K.V311_PROFILE = "v311"
    try:
        class_l = _world(PlanetClass.L, fuel_ore=1_500, organics=700)
        _apply_one_day(class_l)
        assert _made(class_l) == (750, 140, 0, 73)
    finally:
        K.V311_PROFILE = old


def test_the_owner_sees_the_server_daily_numbers(v311):
    """The owned-planet row carries the day tick's numbers, so the cockpit does no math."""
    u, _players = _make_universe(seed=64001)
    owner = next(iter(u.players.values()))
    planet = _plant(u, owner.id, class_id=PlanetClass.M, level=0)
    planet.colonists = {Commodity.FUEL_ORE: 1_500_000, Commodity.ORGANICS: 700_000, Commodity.EQUIPMENT: 0, Commodity.COLONISTS: 0}
    row = next(p for p in build_observation(u, owner.id).owned_planets if p["id"] == planet.id)
    assert row["production"] == {"fuel_ore": 500, "organics": 100, "equipment": 0}
    assert row["fighters_per_day"] == 60
    assert "(i.e. 2,200 thousands)" in row["colonists_text"]


def test_the_planet_card_shows_the_class_m_day(tmp_path):
    """Redesign planet card: per-day lines and fighters per day come from the server row."""
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    from tests._cu_host import CuHost

    flags = {"CLASS_M_FIDELITY_MODE": "live", "PLANET_PROD_MODE": "live", "PLANET_GROWTH_MODE": "tw2002"}
    saved = {name: getattr(K, name) for name in flags}
    pw = sync().start()
    host = CuHost(tmp_path, TOK)
    host.__enter__()
    browser = pw.chromium.launch()
    try:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
        page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=25_000)
        universe = host.runner.state.universe
        me = universe.players["P2"]
        planet = next(iter(universe.planets.values()))
        old = universe.sectors.get(planet.sector_id)
        if old is not None and planet.id in old.planet_ids:
            old.planet_ids.remove(planet.id)
        planet.sector_id = int(me.sector_id)
        planet.owner_id = "P2"
        planet.class_id = PlanetClass.M
        planet.name = "Phoenix"
        planet.fighters = 0
        planet.shields = 0
        planet.colonists = {Commodity.FUEL_ORE: 1_500_000, Commodity.ORGANICS: 700_000, Commodity.EQUIPMENT: 0, Commodity.COLONISTS: 0}
        if planet.id not in universe.sectors[me.sector_id].planet_ids:
            universe.sectors[me.sector_id].planet_ids.append(planet.id)
        for name, value in flags.items():
            setattr(K, name, value)
        host.runner._wait_streak = {"P2": 0}
        page.keyboard.press("Escape")
        page.keyboard.press(".")
        page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
        page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=25_000)
        page.locator("#here button", has_text="Phoenix").click()
        page.locator("#dangerOk").click()
        page.wait_for_selector(".planet [data-day=fighters]", timeout=20_000)
        page.wait_for_function(
            "() => /\\(i\\.e\\. 2,2\\d\\d thousands\\)/.test((document.querySelector('[data-colonists=trend]') || {}).textContent || '')",
            timeout=10_000,
        )
        rows = page.evaluate(
            """() => Object.fromEntries([...document.querySelectorAll('.planet [data-day]')].map(
                 (el) => [el.dataset.day, (el.nextElementSibling || {}).textContent || '']))"""
        )
        assert rows["fuel_ore"].endswith(" per day")
        made = {name: int(rows[name].rsplit("  ", 1)[-1].split()[0].replace(",", "")) for name in ("fuel_ore", "organics")}
        fighters = int(rows["fighters"].split()[0].replace(",", ""))
        assert made["fuel_ore"] in range(500, 526) and made["organics"] in range(100, 106), rows
        assert fighters in range(60, 64), rows
        SHOTS.mkdir(parents=True, exist_ok=True)
        for width, name in ((1920, "1920"), (390, "390")):
            page.set_viewport_size({"width": width, "height": 844 if width == 390 else 1080})
            page.wait_for_timeout(80)
            page.evaluate("() => { const el = document.querySelector('.planet'); if (el) el.scrollIntoView({ block: 'center' }); }")
            page.screenshot(path=str(SHOTS / f"{name}-planet.png"))
    finally:
        for name, value in saved.items():
            setattr(K, name, value)
        browser.close()
        host.__exit__(None, None, None)
        pw.stop()
