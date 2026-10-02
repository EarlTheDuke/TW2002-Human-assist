"""Pin today's planet-siege behaviour. These tests do not change the rules."""

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


def test_attacker_loses_and_the_ship_is_destroyed() -> None:
    u, (attacker, *_) = _make_universe(seed=8802)
    attacker.ship.fighters = 5
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


def test_repelled_landing_does_not_charge_turns() -> None:
    u, (attacker, *_) = _make_universe(seed=8803)
    attacker.ship.fighters = 20
    attacker.ship.shields = 100_000
    planet = _planet(8803, fighters=20, shields=100_000)
    _place(u, planet, attacker)
    before = attacker.turns_today

    res = _land(u, attacker.id, planet.id)

    # The handler returns ok=False with turns_spent set to the landing cost.
    # apply_action only adds turns when ok is True, so the turn counter does
    # not move. KNOWN GAP: a three-round siege that fails still reports a
    # turn cost the player is never charged.
    assert res.ok is False
    assert res.turns_spent == LAND_COST
    assert "repelled" in (res.error or "")
    assert attacker.turns_today == before
    assert planet.owner_id == "B"
    assert attacker.planet_landed is None


def test_capture_leaves_citadel_target_above_the_damaged_level() -> None:
    u, (attacker, *_) = _make_universe(seed=8804)
    attacker.ship.fighters = 1_000
    attacker.ship.shields = 0
    attacker.credits = 100_000
    planet = _planet(8804, fighters=10, shields=0, level=2, treasury=80)
    _place(u, planet, attacker)

    landed = _land(u, attacker.id, planet.id)
    assert landed.ok, landed.error
    assert planet.citadel_level == 1
    assert planet.citadel_target == 2

    built = apply_action(u, attacker.id, Action(
        kind=ActionKind.BUILD_CITADEL, args={"planet_id": planet.id},
    ))
    # KNOWN GAP: the siege lowers citadel_level and leaves citadel_target
    # where it was, so a finished citadel looks like it is still under
    # construction and build_citadel is refused.
    assert built.ok is False
    assert "already under construction" in (built.error or "")
    assert planet.citadel_level == 1
    assert planet.citadel_target == 2


def test_undefended_planet_with_shields_is_captured_without_a_fight() -> None:
    u, (attacker, *_) = _make_universe(seed=8805)
    attacker.corp_ticker = "ACE"
    planet = _planet(8805, fighters=0, shields=40, level=3, treasury=90)
    _place(u, planet, attacker)

    res = _land(u, attacker.id, planet.id)

    assert res.ok, res.error
    assert planet.owner_id == attacker.id
    assert planet.corp_ticker == "ACE"
    assert planet.shields == 40
    assert planet.fighters == 0
    assert planet.citadel_level == 3
    assert planet.treasury == 90
    assert not any(ev.kind is EventKind.COMBAT for ev in u.events)
    landed = next(ev for ev in u.events if ev.kind is EventKind.LAND_PLANET)
    assert landed.payload["seized"] is True
