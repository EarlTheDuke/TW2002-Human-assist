"""NOTE 64 class-m-production-units-v1: under the class M switch, production, fighters and growth count people in thousands.

Source: S1_planet_handbook_v1.01.html (production section and the class M table) and Ben's NOTE 19
ruling, "production is colonists(1000s)/ratio". Profile off stays the old game.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests.test_citadel_class_tables_v1 import _build, _fill, _land, _plant
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
# S1_planet_handbook_v1.01.html section VII, CITADEL ADVANCEMENT TABLES, rows L1..L6 as printed.
S1_SECTION_VII = """
M Colo 1000 2000 4000 6000 6000 6000 | F/O 300 200 500 1000 300 1000 | Org 200 50 250 1200 400 1200 | Equ 250 250 500 1000 1000 2000 | Days 4 4 5 10 5 15
K Colo 1000 2400 4400 7000 8000 7000 | F/O 400 300 600 700 800 700 | Org 300 80 400 900 400 900 | Equ 600 400 650 800 1000 1600 | Days 6 5 8 5 4 8
O Colo 1400 2400 4400 7000 8000 7000 | F/O 500 200 600 700 300 700 | Org 200 50 400 900 400 900 | Equ 400 300 650 800 1000 1600 | Days 6 5 8 5 4 8
L Colo 400 1400 3600 5600 7000 5600 | F/O 150 200 600 1000 300 1000 | Org 100 50 250 1200 400 1200 | Equ 150 250 700 1000 1000 2000 | Days 2 5 5 8 5 12
C Colo 1000 2400 4400 6600 9000 6600 | F/O 400 300 600 700 300 700 | Org 300 80 400 900 400 900 | Equ 600 400 650 700 1000 1400 | Days 5 5 7 5 4 8
H Colo 800 1600 4400 7000 10000 7000 | F/O 500 300 1200 2000 3000 2000 | Org 300 100 400 2000 1200 2000 | Equ 600 400 1500 2500 2000 5000 | Days 4 5 8 12 5 18
U Colo 3000 3000 8000 6000 8000 6000 | F/O 1200 300 500 500 200 500 | Org 400 100 500 200 200 200 | Equ 2500 400 2000 600 600 1200 | Days 8 4 5 5 4 8
"""


def _s1_rows() -> dict[str, list[tuple[int, int, int, int, int]]]:
    rows = {}
    for line in S1_SECTION_VII.strip().splitlines():
        cls, rest = line.split(" ", 1)
        cols = [[int(n) for n in part.split()[1:]] for part in rest.split("|")]
        rows[cls] = list(zip(*cols))
    return rows
TOK = "note64-classm-token-p2-00000000000"


@pytest.fixture
def v311():
    _prior_v311_profile = K.V311_PROFILE
    try:
        old = K.V311_PROFILE
        try:
            K.V311_PROFILE = "v311"
            yield
        finally:
            K.V311_PROFILE = old
    finally:
        K.V311_PROFILE = _prior_v311_profile


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
    """S1 prints 1,500 colonists, not 1,500 thousand. NOTE 167 keeps that count."""
    assert K.class_m_fidelity_live() is False
    fuel = _world(fuel_ore=1_500)
    _apply_one_day(fuel)
    assert _made(fuel) == (500, 0, 0, 50)
    both = _world(fuel_ore=1_500, organics=700)
    _apply_one_day(both)
    assert _made(both) == (500, 100, 0, 60)
    assert fighters_from_colonists(PlanetClass.M, {"fuel_ore": 1_500, "organics": 700}) == 60


def test_the_191000_start_on_fuel_makes_63_fuel_and_6_fighters(v311):
    """S1 ratio 3. 191 printed colonists are 191 // 3 = 63 fuel and 191 // 30 = 6 fighters."""
    planet = _world(fuel_ore=191)
    _apply_one_day(planet)
    assert _made(planet) == (63, 0, 0, 6)
    assert planet_growth_status(planet.class_id, {"fuel_ore": 191}, 0)["production"] == {
        "fuel_ore": 63, "organics": 0, "equipment": 0,
    }


def test_class_m_output_stops_at_the_s1_max_per_day(v311):
    """S1 class M peaks at 15,000 colonists: 5,000 / 2,142 / 1,153 and 829 fighters."""
    for people in (15_000, 25_000):
        planet = _world(fuel_ore=people, organics=people, equipment=people)
        _apply_one_day(planet)
        assert _made(planet) == (5_000, 2_142, 1_153, 829), people
    assert fighters_from_colonists(PlanetClass.M, {"fuel_ore": 29_000, "organics": 29_000, "equipment": 29_000}) == 829


def test_class_m_below_half_the_pool_cap_grows(v311):
    """Below half of 30,000 the colony grows about 5%. Above that half it dies off about 5%."""
    planet = _world(fuel_ore=1_500, organics=700)
    assert planet_growth_status(planet.class_id, planet.colonists, 0)["growth_active"] is True
    _apply_one_day(planet)
    assert planet.colonists[Commodity.FUEL_ORE] == 1_575
    assert planet.colonists[Commodity.ORGANICS] == 735
    full = _world(fuel_ore=20_000)
    _apply_one_day(full)
    assert full.colonists[Commodity.FUEL_ORE] == 19_000
    assert "die off" in colonist_trend(PlanetClass.M, 20_000)


def test_a_day_paid_in_slices_matches_the_daily_number(v311):
    """The day-slice split (_split_units, prod_remain) pays the corrected daily number once a day."""
    planet = _world(fuel_ore=15_000)
    day = int(K.TURN_REGEN_DAY_SECONDS)
    for _ in range(4):
        _accrue_planet(planet, day // 4)
    assert _made(planet) == (5_000, 0, 0, 500)


def test_profile_off_and_other_classes_are_unchanged():
    """Profile off is the old game: class M keeps the handbook unit as stored and the legacy table."""
    _prior_v311_profile = K.V311_PROFILE
    try:
        assert not K.class_m_fidelity_live()
        planet = _world(fuel_ore=1_500, organics=700)
        assert planet_growth_status(planet.class_id, planet.colonists, 0)["production"] == {
            "fuel_ore": 45, "organics": 35, "equipment": 0,
        }
        _apply_one_day(planet)
        assert _made(planet) == (45, 13, 0, 60)
        assert fighters_from_colonists(PlanetClass.M, {"fuel_ore": 1_500_000}) == 50_000
        old = K.V311_PROFILE
        try:
            K.V311_PROFILE = "v311"
            class_l = _world(PlanetClass.L, fuel_ore=1_500, organics=700)
            _apply_one_day(class_l)
            assert _made(class_l) == (750, 140, 0, 73)
        finally:
            K.V311_PROFILE = old
    finally:
        K.V311_PROFILE = _prior_v311_profile


def test_the_owner_sees_the_server_daily_numbers(v311):
    """The owned-planet row carries the day tick's numbers, so the cockpit does no math."""
    u, _players = _make_universe(seed=64001)
    owner = next(iter(u.players.values()))
    planet = _plant(u, owner.id, class_id=PlanetClass.M, level=0)
    planet.colonists = {Commodity.FUEL_ORE: 1_500, Commodity.ORGANICS: 700, Commodity.EQUIPMENT: 0, Commodity.COLONISTS: 0}
    row = next(p for p in build_observation(u, owner.id).owned_planets if p["id"] == planet.id)
    assert row["production"] == {"fuel_ore": 500, "organics": 100, "equipment": 0}
    assert row["fighters_per_day"] == 60
    assert "below half the class cap (30,000)" in row["colonists_text"]


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


def test_every_citadel_row_matches_s1_under_the_profile(v311):
    """S1 section VII, all 42 class/level rows. NOTE 167 reads class M as printed, so level 1 is 1,000."""
    rows = _s1_rows()
    assert sum(len(levels) for levels in rows.values()) == 42
    assert K.class_m_fidelity_live() is False
    for cls, levels in rows.items():
        for level, (colonists, fuel, organics, equipment, days) in enumerate(levels, start=1):
            assert K.citadel_class_cost(cls, level) == (colonists, fuel, organics, equipment, days), (cls, level)
    assert K.citadel_class_cost("M", 1)[0] == 1_000
    assert K.planet_colonist_cap("M") == 30_000
    assert K.planet_colonist_cap("U") == 8_000
    assert K.citadel_class_cost("K", 5)[1] == 800


def test_explicit_fidelity_still_asks_for_a_million():
    """NOTE 19 stays available on its own switch. The profile does not select it."""
    prior = K.CLASS_M_FIDELITY_MODE
    try:
        K.CLASS_M_FIDELITY_MODE = "live"
        assert K.V311_PROFILE != "v311"
        assert K.citadel_class_cost("M", 1)[0] == 1_000_000
    finally:
        K.CLASS_M_FIDELITY_MODE = prior


def test_class_u_level_3_asks_for_8000_only_with_the_switch():
    """Legacy keeps the stored 5,000; the new switch alone asks for the S1 8,000 and a build at 7,999 is refused."""
    assert K.CITADEL_TABLE_FIX_MODE == "legacy" and not K.citadel_table_fix_live()
    assert K.citadel_class_cost("U", 3)[0] == 5_000
    assert K.CITADEL_CLASS_COSTS["U"][2][0] == 5_000
    saved = (K.CITADEL_TABLE_FIX_MODE, K.PLANET_COLONIST_CAP_MODE)
    K.CITADEL_TABLE_FIX_MODE, K.PLANET_COLONIST_CAP_MODE = "live", "live"
    try:
        assert K.citadel_class_cost("U", 3)[0] == 8_000
        u, _players = _make_universe(seed=64018)
        owner = next(iter(u.players.values()))
        planet = _plant(u, owner.id, class_id=PlanetClass.U, level=2)
        _fill(planet, 7_999, 500, 500, 2_000)
        _land(u, owner, planet)
        refused = _build(u, owner, planet.id)
        assert refused.ok is False and "8000" in refused.error, refused.error
        planet.colonists[Commodity.COLONISTS] = 8_000
        allowed = _build(u, owner, planet.id)
        assert allowed.ok, allowed.error
        assert planet.citadel_target == 3
    finally:
        K.CITADEL_TABLE_FIX_MODE, K.PLANET_COLONIST_CAP_MODE = saved
