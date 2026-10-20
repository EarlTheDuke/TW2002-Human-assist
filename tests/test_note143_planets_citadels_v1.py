"""NOTE 143. Three planet and citadel rows whose v3.11 numbers are known.

Each row stays on the legacy rule while its switch is off, including when
V311_PROFILE is "1". The switch, or V311_PROFILE "v311" alone, uses the
handbook or cabal number.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import (
    Commodity,
    GameConfig,
    Planet,
    PlanetClass,
    Player,
    Sector,
    Ship,
    ShipClass,
    Universe,
)
from tw2k.engine.runner import apply_action


def _pair(seed: int) -> tuple[Universe, Player, Player]:
    sectors = {
        1: Sector(id=1, warps=[2]),
        2: Sector(id=2, warps=[1]),
    }
    universe = Universe(
        config=GameConfig(seed=seed, universe_size=2, enable_ferrengi=False, enable_planets=False),
        sectors=sectors,
    )
    killer = Player(
        id="A", name="Alpha", sector_id=2, credits=0,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=20, shields=5_000),
        turns_per_day=100, experience=1_000, alignment=1_000,
    )
    victim = Player(
        id="B", name="Bravo", sector_id=2, credits=0,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=10, shields=10),
        turns_per_day=100, experience=10_000, alignment=-10_000,
    )
    universe.players["A"] = killer
    universe.players["B"] = victim
    universe.sectors[2].occupant_ids.extend(["A", "B"])
    return universe, killer, victim


def _hostile_planet(universe: Universe, sector_id: int, **kw) -> Planet:
    planet = Planet(
        id=7, sector_id=sector_id, name="Haven", class_id=PlanetClass.M, owner_id="B", **kw,
    )
    universe.planets[7] = planet
    universe.sectors[sector_id].planet_ids.append(7)
    return planet


def test_zdy_awards_fail_off_and_pass_on(monkeypatch) -> None:
    """GAP 6.10. 10,000 experience becomes 1,666. Alignment -10,000 becomes +3,333, then the blow's -1."""
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.planet_zdy_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    assert K.zdy_kill_experience(10_000) == 1_666
    assert K.zdy_kill_alignment(-10_000) == 3_333
    assert K.zdy_kill_alignment(1_000) == -333

    def scene():
        universe, killer, victim = _pair(14301)
        planet = _hostile_planet(universe, 2, citadel_level=0, citadel_target=0)
        killer.planet_landed = planet.id
        victim.planet_landed = planet.id
        killer.ship.atomic_detonators = 1
        apply_action(universe, "A", Action(kind=ActionKind.PLANET_DESTROY, args={"planet_id": planet.id}))
        return universe, killer, victim

    universe, killer, victim = scene()
    assert 7 not in universe.planets
    assert victim.deaths == 0
    assert victim.ship.ship_class is ShipClass.MERCHANT_CRUISER
    assert killer.experience == 1_050
    assert killer.alignment == 999

    monkeypatch.setattr(K, "PLANET_ZDY_MODE", "v311")
    _universe, killer, victim = scene()
    assert victim.deaths == 1
    assert victim.ship.ship_class is ShipClass.ESCAPE_POD
    assert killer.experience == 2_716
    assert killer.alignment == 4_332

    monkeypatch.setattr(K, "PLANET_ZDY_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.PLANET_ZDY_MODE == "legacy"
    _universe, killer, victim = scene()
    assert victim.deaths == 1
    assert killer.experience == 2_716
    assert killer.alignment == 4_332


def test_shieldless_atmosphere_shot_fails_off_and_passes_on(monkeypatch) -> None:
    """S1: one atmosphere shot when no shields are fighting. 10,000 fuel at 10% burns 1,000 and deals 2,000."""
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.quasar_atm_order_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")

    def scene():
        universe, killer, _victim = _pair(14302)
        planet = _hostile_planet(
            universe, 2, citadel_level=3, citadel_target=3, quasar_atm_pct=10, shields=0, fighters=0,
        )
        planet.stockpile[Commodity.FUEL_ORE] = 10_000
        apply_action(universe, "A", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": planet.id}))
        return planet, killer

    planet, killer = scene()
    assert planet.stockpile[Commodity.FUEL_ORE] == 8_100
    assert killer.ship.shields == 1_200

    monkeypatch.setattr(K, "QUASAR_ATM_ORDER_MODE", "v311")
    planet, killer = scene()
    assert planet.stockpile[Commodity.FUEL_ORE] == 9_000
    assert killer.ship.shields == 3_000

    monkeypatch.setattr(K, "QUASAR_ATM_ORDER_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.QUASAR_ATM_ORDER_MODE == "legacy"
    planet, killer = scene()
    assert planet.stockpile[Commodity.FUEL_ORE] == 9_000
    assert killer.ship.shields == 3_000


def test_stardock_interdictor_fails_off_and_passes_on(monkeypatch) -> None:
    """v3.11: an interdictor does not hold at StarDock. Terra is that sector. Sector 2 still burns 500."""
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.planet_interdict_safe_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")

    def leave(sector_id: int):
        universe, killer, _victim = _pair(14303)
        planet = _hostile_planet(universe, sector_id, citadel_level=6, citadel_target=6, quasar_sector_pct=0)
        planet.stockpile[Commodity.FUEL_ORE] = 500
        killer.sector_id = sector_id
        universe.sectors[2].occupant_ids = [pid for pid in universe.sectors[2].occupant_ids if pid != "A"]
        universe.sectors[sector_id].occupant_ids.append("A")
        dest = 2 if sector_id == 1 else 1
        result = apply_action(universe, "A", Action(kind=ActionKind.WARP, args={"target": dest}))
        return universe, killer, planet, result

    _universe, killer, planet, result = leave(1)
    assert result.ok is False
    assert result.error == "interdicted by a planet"
    assert killer.sector_id == 1
    assert planet.stockpile[Commodity.FUEL_ORE] == 0

    monkeypatch.setattr(K, "PLANET_INTERDICT_SAFE_MODE", "v311")
    _universe, killer, planet, result = leave(1)
    assert result.ok is True
    assert killer.sector_id == 2
    assert planet.stockpile[Commodity.FUEL_ORE] == 500
    _universe, killer, planet, result = leave(2)
    assert result.ok is False
    assert result.error == "interdicted by a planet"
    assert planet.stockpile[Commodity.FUEL_ORE] == 0

    monkeypatch.setattr(K, "PLANET_INTERDICT_SAFE_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.PLANET_INTERDICT_SAFE_MODE == "legacy"
    _universe, killer, planet, result = leave(1)
    assert result.ok is True
    assert killer.sector_id == 2
    assert planet.stockpile[Commodity.FUEL_ORE] == 500
