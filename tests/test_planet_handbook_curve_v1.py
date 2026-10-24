"""GAP 6.3. Printed S1 maximums, stock caps, and the half-population curve.

The curve stays off on a stored game. V311_PROFILE, PLANET_PROD_MODE live,
and PLANET_GROWTH_MODE tw2002 turn it on. PLANET_ECONOMY_MODE tw2002 is
already the stored default for stock caps and the total colonist ceiling;
it does not by itself change the day tick.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine.models import Commodity, Planet, PlanetClass
from tw2k.engine.planets import _apply_one_day, daily_production, fighters_from_colonists


def _world(class_id: PlanetClass, **pools: int) -> Planet:
    planet = Planet(id=1, sector_id=20, name="Lab", class_id=class_id, owner_id="P1")
    for name, qty in pools.items():
        planet.colonists[Commodity(name)] = qty
    return planet


def _goods(planet: Planet) -> tuple[int, int, int]:
    return (
        int(planet.stockpile.get(Commodity.FUEL_ORE, 0)),
        int(planet.stockpile.get(Commodity.ORGANICS, 0)),
        int(planet.stockpile.get(Commodity.EQUIPMENT, 0)),
    )


def test_stored_defaults_keep_todays_day_tick() -> None:
    assert K.PLANET_PROD_MODE == "legacy"
    assert K.PLANET_GROWTH_MODE == "legacy"
    assert K.V311_PROFILE == "legacy"
    assert K.PLANET_ECONOMY_MODE == "tw2002"
    assert K.planet_handbook_on() is False
    planet = _world(PlanetClass.M, fuel_ore=100)
    planet.stockpile[Commodity.ORGANICS] = 0
    _apply_one_day(planet)
    assert _goods(planet) == (3, 0, 0)
    assert planet.colonists[Commodity.FUEL_ORE] == 100
    crowded = _world(PlanetClass.M, fuel_ore=20_000)
    _apply_one_day(crowded)
    assert crowded.colonists[Commodity.FUEL_ORE] == 20_000
    assert K.colonist_drop_error("M", 0, 30_000, 1) == "planet colonist cap is 30000"


def test_legacy_economy_still_has_no_cap_and_no_curve(monkeypatch) -> None:
    monkeypatch.setattr(K, "PLANET_ECONOMY_MODE", "legacy")
    assert K.planet_handbook_on() is False
    planet = _world(PlanetClass.M, fuel_ore=10_000)
    planet.stockpile[Commodity.FUEL_ORE] = K.PLANET_MAX_STOCK["M"]["fuel_ore"]
    planet.stockpile[Commodity.ORGANICS] = 100
    _apply_one_day(planet)
    assert int(planet.stockpile[Commodity.FUEL_ORE]) > K.PLANET_MAX_STOCK["M"]["fuel_ore"]
    assert planet.colonists[Commodity.FUEL_ORE] > 10_000
    assert K.planet_stock_room("M", "fuel_ore", 100_000) is None


def test_s1_curve_peaks_at_half_and_is_zero_at_the_maximum(monkeypatch) -> None:
    monkeypatch.setattr(K, "PLANET_PROD_MODE", "live")
    monkeypatch.setattr(K, "PLANET_ECONOMY_MODE", "legacy")
    assert K.planet_handbook_on() is True
    fuel = _world(PlanetClass.M, fuel_ore=1_500)
    _apply_one_day(fuel)
    assert _goods(fuel) == (500, 0, 0)
    assert fuel.fighters == 50
    both = _world(PlanetClass.M, fuel_ore=1_500, organics=700)
    _apply_one_day(both)
    assert daily_production(PlanetClass.M, {"fuel_ore": 1_500, "organics": 700}) == {
        "fuel_ore": 500, "organics": 100, "equipment": 0,
    }
    # 100 organics were made, then the under-half colony ate 2,200 // 100.
    assert _goods(both) == (500, 78, 0)
    assert both.fighters == 60
    peak = _world(PlanetClass.M, fuel_ore=15_000, organics=15_000, equipment=15_000)
    _apply_one_day(peak)
    assert _goods(peak) == (5_000, 2_142, 1_153)
    assert peak.fighters == 829
    assert peak.colonists[Commodity.FUEL_ORE] == 15_000
    high = _world(PlanetClass.M, fuel_ore=20_000)
    _apply_one_day(high)
    assert int(high.stockpile[Commodity.FUEL_ORE]) == 3_333
    assert high.colonists[Commodity.FUEL_ORE] == 19_000
    full = _world(PlanetClass.M, fuel_ore=30_000)
    _apply_one_day(full)
    assert int(full.stockpile[Commodity.FUEL_ORE]) == 0
    assert full.colonists[Commodity.FUEL_ORE] == 28_500


def test_each_class_matches_the_printed_max_day(monkeypatch) -> None:
    """S1 Max/Day is (maximum colonists / 2) / ratio, and fighters are that day's products / n."""
    monkeypatch.setattr(K, "PLANET_PROD_MODE", "live")
    printed = {
        "M": ((3, 7, 13), (5_000, 2_142, 1_153), 10, 829),
        "K": ((2, 100, 500), (10_000, 200, 40), 15, 682),
        "L": ((2, 5, 20), (10_000, 4_000, 1_000), 12, 1_250),
        "O": ((20, 2, 100), (5_000, 50_000, 1_000), 15, 3_733),
        "C": ((50, 100, 500), (1_000, 500, 100), 25, 64),
        "H": ((1, 0, 500), (50_000, 0, 100), 50, 1_002),
        "U": ((0, 0, 0), (0, 0, 0), 0, 0),
    }
    for class_id, (ratios, max_day, per, fighters) in printed.items():
        cap = K.PLANET_MAX_COLONISTS[class_id]
        half = cap // 2
        assert K.PLANET_PROD_PER_UNIT[class_id] == ratios
        pools = {
            "fuel_ore": half,
            "organics": half,
            "equipment": half,
        }
        made = daily_production(class_id, pools)
        assert (made["fuel_ore"], made["organics"], made["equipment"]) == max_day, class_id
        assert fighters_from_colonists(class_id, pools) == fighters, class_id
        if per:
            assert sum(max_day) // per == fighters
        full = {name: cap for name in pools}
        stopped = daily_production(class_id, full)
        assert stopped == {"fuel_ore": 0, "organics": 0, "equipment": 0}, class_id


def test_a_pool_below_half_grows_and_a_pool_above_half_dies(monkeypatch) -> None:
    monkeypatch.setattr(K, "PLANET_PROD_MODE", "live")
    growing = _world(PlanetClass.M, fuel_ore=1_000, organics=20_000)
    growing.stockpile[Commodity.ORGANICS] = 40
    _apply_one_day(growing)
    assert growing.colonists[Commodity.FUEL_ORE] == 1_050
    assert growing.colonists[Commodity.ORGANICS] == 19_000
    # Fuel 1,000/3 = 333. Organics mirror of 20,000 is 10,000/7 = 1,428.
    # The colony as a whole is over half, so the day does not eat organics.
    assert int(growing.stockpile[Commodity.FUEL_ORE]) == 333
    assert int(growing.stockpile[Commodity.ORGANICS]) == 40 + 1_428
    dry = _world(PlanetClass.K, fuel_ore=1_000)
    _apply_one_day(dry)
    assert dry.colonists[Commodity.FUEL_ORE] == 1_000


def test_stock_and_per_product_colonist_caps_follow_the_switch(monkeypatch) -> None:
    monkeypatch.setattr(K, "PLANET_PROD_MODE", "live")
    monkeypatch.setattr(K, "PLANET_ECONOMY_MODE", "legacy")
    capped = _world(PlanetClass.M, fuel_ore=1_500)
    capped.stockpile[Commodity.FUEL_ORE] = K.PLANET_MAX_STOCK["M"]["fuel_ore"]
    _apply_one_day(capped)
    assert int(capped.stockpile[Commodity.FUEL_ORE]) == 100_000
    assert K.colonist_drop_error("M", 30_000, 30_000, 1) == "planet colonist cap is 30000"
    assert K.colonist_drop_error("M", 0, 30_000, 100) is None
    assert K.colonist_drop_error("O", 200_000, 200_000, 1) == "planet colonist cap is 200000"
    assert K.PLANET_MAX_STOCK["H"]["fuel_ore"] == 1_000_000
    assert K.PLANET_MAX_STOCK["O"]["organics"] == 1_000_000
    assert K.PLANET_MAX_STOCK["U"]["equipment"] == 10_000


def test_v311_uses_the_printed_table_and_class_m_thousands(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.PLANET_PROD_MODE == "legacy"
    assert K.planet_handbook_on() is True
    people = _world(PlanetClass.M, fuel_ore=1_500_000)
    _apply_one_day(people)
    assert int(people.stockpile[Commodity.FUEL_ORE]) == 500
    assert people.fighters == 50
    maxed = _world(PlanetClass.M, fuel_ore=30_000_000)
    _apply_one_day(maxed)
    assert int(maxed.stockpile[Commodity.FUEL_ORE]) == 0
    assert maxed.colonists[Commodity.FUEL_ORE] == 28_500_000
    desert = _world(PlanetClass.K, fuel_ore=20_000)
    _apply_one_day(desert)
    assert int(desert.stockpile[Commodity.FUEL_ORE]) == 10_000
    assert desert.colonists[Commodity.FUEL_ORE] == 20_000
