"""Planet siege, including the shield gate."""

from __future__ import annotations

from tests.test_phase_abc import _make_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.constants import STARTING_FIGHTERS, TURN_COST
from tw2k.engine.models import EventKind, Planet, PlanetClass
from tw2k.engine.runner import apply_action

LAND_COST = TURN_COST["land_planet"]
SECTOR = 120


def _place(u, planet: Planet, attacker) -> None:
    u.planets[planet.id] = planet
    u.sectors[SECTOR].planet_ids.append(planet.id)
    here = u.sectors[attacker.sector_id]
    if attacker.id in here.occupant_ids:
        here.occupant_ids.remove(attacker.id)
    attacker.sector_id = SECTOR
    attacker.planet_landed = None
    u.sectors[SECTOR].occupant_ids.append(attacker.id)


def _planet(pid: int, *, fighters: int, shields: int, level: int = 2, treasury: int = 100) -> Planet:
    planet = Planet(
        id=pid, sector_id=SECTOR, name=f"Siege{pid}",
        class_id=PlanetClass.M, owner_id="B", corp_ticker="QQ",
        fighters=fighters, shields=shields,
        citadel_level=level, citadel_target=level, treasury=treasury,
    )
    return planet


def _land(u, pid: int, planet_id: int):
    return apply_action(u, pid, Action(kind=ActionKind.LAND_PLANET, args={"planet_id": planet_id}))


def test_attacker_captures_a_defended_planet() -> None:
    u, (attacker, *_) = _make_universe(seed=8801)
    attacker.corp_ticker = "ACE"
    attacker.ship.fighters = 1_000
    attacker.ship.shields = 0
    planet = _planet(8801, fighters=10, shields=0, level=2, treasury=100)
    _place(u, planet, attacker)

    res = _land(u, attacker.id, planet.id)

    assert res.ok, res.error
    assert planet.owner_id == attacker.id
    assert planet.corp_ticker == "ACE"
    assert planet.citadel_level == 1
    assert planet.treasury == 50
    landed = next(ev for ev in u.events if ev.kind is EventKind.LAND_PLANET)
    assert landed.payload["seized"] is True
    assert attacker.planet_landed == planet.id
    combat = next(ev for ev in u.events if ev.kind is EventKind.COMBAT)
    assert combat.payload["rounds"]
    assert [row["phase"] for row in combat.payload["rounds"]] == ["defense"]
    assert attacker.ship.fighters == 970


def test_attacker_loses_and_the_ship_is_destroyed() -> None:
    u, (attacker, *_) = _make_universe(seed=8802)
    attacker.ship.fighters = 300
    attacker.ship.shields = 0
    deaths = attacker.deaths
    planet = _planet(8802, fighters=5_000, shields=0)
    owner = planet.owner_id
    _place(u, planet, attacker)

    res = _land(u, attacker.id, planet.id)

    assert res.ok, res.error
    assert attacker.deaths == deaths + 1
    assert attacker.sector_id == 1
    assert attacker.ship.fighters == STARTING_FIGHTERS
    assert attacker.planet_landed is None
    assert planet.owner_id == owner
    destroyed = next(ev for ev in u.events if ev.kind is EventKind.SHIP_DESTROYED)
    assert destroyed.payload["reason"] == "planet_defense"
    assert destroyed.payload["victim"] == attacker.id


def test_repelled_landing_charges_the_landing_turn() -> None:
    u, (attacker, *_) = _make_universe(seed=8803)
    attacker.ship.fighters = 20
    attacker.ship.shields = 100_000
    planet = _planet(8803, fighters=20, shields=100_000)
    _place(u, planet, attacker)
    before = attacker.turns_today

    res = _land(u, attacker.id, planet.id)

    # The landing failed, so ok stays False, and this one failure still
    # spends the landing turn.
    assert res.ok is False
    assert res.turns_spent == LAND_COST
    assert res.error == "planetary defenses repelled landing"
    assert attacker.turns_today == before + LAND_COST
    assert planet.owner_id == "B"
    assert attacker.planet_landed is None


def test_capture_lowers_citadel_target_with_the_level() -> None:
    u, (attacker, *_) = _make_universe(seed=8804)
    attacker.ship.fighters = 1_000
    attacker.ship.shields = 0
    attacker.credits = 100_000
    planet = _planet(8804, fighters=10, shields=0, level=2, treasury=80)
    _place(u, planet, attacker)

    landed = _land(u, attacker.id, planet.id)
    assert landed.ok, landed.error
    assert planet.citadel_level == 1
    assert planet.citadel_target == 1
    assert planet.citadel_complete_day is None

    built = apply_action(u, attacker.id, Action(
        kind=ActionKind.BUILD_CITADEL, args={"planet_id": planet.id},
    ))
    assert "already under construction" not in (built.error or "")


def _phases(u) -> list[str]:
    combat = next(ev for ev in u.events if ev.kind is EventKind.COMBAT)
    return [row["phase"] for row in combat.payload["rounds"]]


def test_shields_only_strong_attacker_captures() -> None:
    u, (attacker, *_) = _make_universe(seed=8805)
    attacker.corp_ticker = "ACE"
    attacker.ship.fighters = 20_000
    attacker.ship.shields = 0
    planet = _planet(8805, fighters=0, shields=15, level=3, treasury=90)
    _place(u, planet, attacker)

    res = _land(u, attacker.id, planet.id)

    assert res.ok, res.error
    assert planet.owner_id == attacker.id
    assert planet.corp_ticker == "ACE"
    assert planet.shields == 0
    assert planet.fighters == 0
    assert planet.citadel_level == 2
    assert planet.treasury == 45
    assert _phases(u) == ["shields"]


def test_shields_only_weak_attacker_is_repelled() -> None:
    u, (attacker, *_) = _make_universe(seed=8806)
    attacker.ship.fighters = 40
    attacker.ship.shields = 0
    planet = _planet(8806, fighters=0, shields=100, level=3, treasury=90)
    _place(u, planet, attacker)
    before = attacker.turns_today

    res = _land(u, attacker.id, planet.id)

    assert res.ok is False
    assert res.error == "planetary defenses repelled landing"
    assert attacker.turns_today == before + LAND_COST
    assert planet.owner_id == "B"
    assert planet.fighters == 0
    assert planet.shields > 90
    assert attacker.ship.fighters == 40
    assert attacker.planet_landed is None
    assert _phases(u) == ["shields"]
    assert not any(ev.kind is EventKind.LAND_PLANET for ev in u.events)


def test_shields_and_fighters_need_both_phases() -> None:
    u, (attacker, *_) = _make_universe(seed=8807)
    attacker.ship.fighters = 8_000
    attacker.ship.shields = 0
    planet = _planet(8807, fighters=30, shields=4, level=2, treasury=80)
    _place(u, planet, attacker)

    res = _land(u, attacker.id, planet.id)

    assert res.ok, res.error
    assert planet.owner_id == attacker.id
    assert planet.fighters == 0
    assert planet.shields == 0
    phases = _phases(u)
    assert phases == ["shields", "defense"]
    combat = next(ev for ev in u.events if ev.kind is EventKind.COMBAT)
    shield_row = combat.payload["rounds"][0]
    defense_row = combat.payload["rounds"][1]
    assert shield_row["attacker_fighters_lost"] == 0 and shield_row["defender_fighters_lost"] == 0
    assert defense_row["defender_fighters_lost"] == 30
    assert attacker.ship.fighters == 7910


def test_planet_fighters_do_not_fire_while_shields_remain() -> None:
    u, (attacker, *_) = _make_universe(seed=8808)
    attacker.ship.fighters = 25
    attacker.ship.shields = 0
    planet = _planet(8808, fighters=400, shields=80)
    _place(u, planet, attacker)

    res = _land(u, attacker.id, planet.id)

    assert res.ok is False
    assert res.error == "planetary defenses repelled landing"
    assert attacker.ship.fighters == 25
    assert planet.fighters == 400
    assert planet.shields < 80
    assert planet.owner_id == "B"
    assert _phases(u) == ["shields"]
