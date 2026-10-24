"""GAP 4.10. A photon wave and the level 6 interdictor.

HardwareMenu disables the interdictor for the wave. S1 does not list it, so
the stored path still holds. Row 234 stays off until the switch or the v3.11
profile is on. Mines, sector fighters, and the quasar shot stay on their own
rules. The ship Interdictor Cruiser is a different well.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.combat import hull_interdict_reason, interdictor_planet
from tw2k.engine.models import (
    Commodity,
    EventKind,
    FighterDeployment,
    FighterMode,
    GameConfig,
    MineDeployment,
    MineType,
    Planet,
    PlanetClass,
    Player,
    Sector,
    Ship,
    ShipClass,
    Universe,
)
from tw2k.engine.runner import apply_action


def _world(*, wave: int, level: int = 6, shields: int = 0, fuel: int = 10_000):
    sectors = {
        11: Sector(id=11, warps=[12], nav_hazard=0),
        12: Sector(
            id=12, warps=[11], nav_hazard=0, photon_wave_remaining=wave,
            mines=[MineDeployment(owner_id="O", kind=MineType.ARMID, count=4)],
            fighters=FighterDeployment(owner_id="O", count=30, mode=FighterMode.OFFENSIVE),
        ),
    }
    universe = Universe(
        config=GameConfig(seed=22901, universe_size=12, enable_ferrengi=False, enable_planets=False),
        sectors=sectors,
    )
    pilot = Player(
        id="A", name="Ada", sector_id=11, credits=0,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=2_000, shields=500),
        turns_per_day=40,
    )
    universe.players["A"] = pilot
    universe.sectors[11].occupant_ids.append("A")
    planet = Planet(
        id=2291, sector_id=12, name="Hold", class_id=PlanetClass.M,
        owner_id="O", citadel_level=level, citadel_target=level,
        shields=shields, quasar_sector_pct=10,
    )
    planet.stockpile[Commodity.FUEL_ORE] = fuel
    universe.planets[planet.id] = planet
    universe.sectors[12].planet_ids.append(planet.id)
    return universe, pilot, planet


def _warp(universe, pilot, dest: int):
    return apply_action(universe, pilot.id, Action(kind=ActionKind.WARP, args={"target": dest}))


def _shots(universe):
    return [ev for ev in universe.events if ev.kind is EventKind.QUASAR_FIRE]


def _holds(universe):
    return [ev for ev in universe.events if ev.kind is EventKind.INTERDICT]


def test_legacy_interdictor_still_holds_during_the_wave(monkeypatch) -> None:
    """Off, including profile "1" and the older live profile, the hold still burns fuel."""
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.photon_interdict_damp_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    assert K.photon_interdict_damp_live() is False
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.photon_interdict_damp_live() is False
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    assert K.PHOTON_WAVE_DURATION == 1

    universe, pilot, planet = _world(wave=1)
    entered = _warp(universe, pilot, 12)
    assert entered.ok, entered.error
    assert pilot.sector_id == 12
    assert pilot.ship.shields == 500 - (1_000 // 3)
    assert pilot.ship.fighters == 2_000
    assert universe.sectors[12].mines[0].count == 4
    assert universe.sectors[12].fighters.count == 30
    assert planet.stockpile[Commodity.FUEL_ORE] == 9_000
    assert len(_shots(universe)) == 1
    assert interdictor_planet(universe, "A", universe.sectors[12]) is planet

    universe.events.clear()
    held = _warp(universe, pilot, 11)
    assert held.ok is False
    assert held.error == "interdicted by a planet"
    assert pilot.sector_id == 12
    assert planet.stockpile[Commodity.FUEL_ORE] == 7_650
    assert pilot.ship.shields == 0
    assert pilot.ship.fighters == 1_884
    assert universe.sectors[12].mines[0].count == 4
    assert universe.sectors[12].fighters.count == 30
    assert universe.sectors[12].photon_wave_remaining == 1
    assert len(_holds(universe)) == 1
    assert len(_shots(universe)) == 1


def test_live_wave_lets_the_ship_leave_and_keeps_the_entry_shot(monkeypatch) -> None:
    """On, the hold fails open. The entry quasar, the mines, and the fighters do not move."""
    monkeypatch.setattr(K, "PHOTON_INTERDICT_DAMP_MODE", "live")
    universe, pilot, planet = _world(wave=1)
    entered = _warp(universe, pilot, 12)
    assert entered.ok, entered.error
    assert pilot.ship.shields == 500 - (1_000 // 3)
    assert pilot.ship.fighters == 2_000
    assert universe.sectors[12].mines[0].count == 4
    assert universe.sectors[12].fighters.count == 30
    assert planet.stockpile[Commodity.FUEL_ORE] == 9_000
    assert interdictor_planet(universe, "A", universe.sectors[12]) is None

    universe.events.clear()
    left = _warp(universe, pilot, 11)
    assert left.ok, left.error
    assert pilot.sector_id == 11
    assert planet.stockpile[Commodity.FUEL_ORE] == 9_000
    assert pilot.ship.shields == 500 - (1_000 // 3)
    assert pilot.ship.fighters == 2_000
    assert _holds(universe) == []
    assert _shots(universe) == []
    assert universe.sectors[12].photon_wave_remaining == 1

    universe.sectors[12].photon_wave_remaining = 0
    _stand_back(universe, pilot, 12)
    held = _warp(universe, pilot, 11)
    assert held.ok is False
    assert held.error == "interdicted by a planet"
    assert pilot.sector_id == 12
    assert planet.stockpile[Commodity.FUEL_ORE] == 7_650


def test_profile_damps_the_interdictor_and_leaves_the_stored_flag(monkeypatch) -> None:
    """The profile also damps a follower's quasar. The mines and fighters stay quiet."""
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.PHOTON_INTERDICT_DAMP_MODE == "legacy"
    assert K.PHOTON_FOLLOW_DAMP_MODE == "legacy"
    assert K.photon_interdict_damp_live() is True
    assert K.photon_follow_damp_live() is True
    universe, pilot, planet = _world(wave=1)
    entered = _warp(universe, pilot, 12)
    assert entered.ok, entered.error
    assert pilot.ship.shields == 500
    assert pilot.ship.fighters == 2_000
    assert planet.stockpile[Commodity.FUEL_ORE] == 10_000
    assert universe.sectors[12].mines[0].count == 4
    assert universe.sectors[12].fighters.count == 30
    assert _shots(universe) == []
    left = _warp(universe, pilot, 11)
    assert left.ok, left.error
    assert pilot.sector_id == 11
    assert planet.stockpile[Commodity.FUEL_ORE] == 10_000
    assert _holds(universe) == []


def test_two_hundred_shields_still_fire_the_quasar(monkeypatch) -> None:
    """The 200-shield quasar exception stays. The interdictor damp does not borrow it."""
    monkeypatch.setattr(K, "PHOTON_FOLLOW_DAMP_MODE", "live")
    monkeypatch.setattr(K, "PHOTON_INTERDICT_DAMP_MODE", "live")
    universe, pilot, planet = _world(wave=1, level=6, shields=K.QUASAR_PHOTON_SHIELD_MIN)
    entered = _warp(universe, pilot, 12)
    assert entered.ok, entered.error
    assert pilot.photon_damped_sector_id == 12
    assert pilot.ship.shields == 500 - (1_000 // 3)
    assert len(_shots(universe)) == 1
    assert universe.sectors[12].mines[0].count == 4
    assert universe.sectors[12].fighters.count == 30
    left = _warp(universe, pilot, 11)
    assert left.ok, left.error
    assert pilot.sector_id == 11
    assert planet.stockpile[Commodity.FUEL_ORE] == 9_000
    assert len(_shots(universe)) == 1


def test_a_ship_interdictor_still_holds_during_the_wave(monkeypatch) -> None:
    """The cruiser well is not the citadel generator HardwareMenu names."""
    monkeypatch.setattr(K, "PHOTON_INTERDICT_DAMP_MODE", "live")
    monkeypatch.setattr(K, "SPECIAL_HULL_RULES_MODE", "live")
    monkeypatch.setattr(K, "SHIP_ROSTER_MODE", "live")
    universe, pilot, _planet = _world(wave=1, level=1, fuel=0)
    cruiser = Player(
        id="C", name="Cruiser", sector_id=12,
        ship=Ship(ship_class=ShipClass.INTERDICTOR_CRUISER, fighters=20, shields=10),
    )
    universe.players["C"] = cruiser
    universe.sectors[12].occupant_ids.append("C")
    assert _warp(universe, pilot, 12).ok
    assert hull_interdict_reason(universe, "A") == "an Interdictor Cruiser holds this sector"
    blocked = _warp(universe, pilot, 11)
    assert blocked.ok is False
    assert blocked.error == "an Interdictor Cruiser holds this sector"
    assert pilot.sector_id == 12


def _stand_back(universe, pilot, sid: int) -> None:
    here = universe.sectors[pilot.sector_id]
    if pilot.id in here.occupant_ids:
        here.occupant_ids.remove(pilot.id)
    pilot.sector_id = sid
    pilot.turns_today = 0
    if pilot.id not in universe.sectors[sid].occupant_ids:
        universe.sectors[sid].occupant_ids.append(pilot.id)
