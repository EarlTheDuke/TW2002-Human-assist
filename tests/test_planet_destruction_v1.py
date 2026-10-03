"""A hostile planet loses its colonists, then the planet itself."""

from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_phase_abc import _make_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import Alliance, Commodity, EventKind, Planet, PlanetClass, Universe
from tw2k.engine.observation import build_observation, event_facts
from tw2k.engine.runner import apply_action


def _plant(u, sid: int, owner: str, *, fighters: int = 0, shields: int = 0) -> Planet:
    planet = Planet(
        id=88601, sector_id=sid, name="Hold", class_id=PlanetClass.M,
        owner_id=owner, citadel_level=1, citadel_target=1,
        fighters=fighters, shields=shields, treasury=900,
    )
    planet.colonists[Commodity.FUEL_ORE] = 3
    planet.colonists[Commodity.ORGANICS] = 4
    planet.colonists[Commodity.EQUIPMENT] = 5
    planet.colonists[Commodity.COLONISTS] = 6
    planet.stockpile[Commodity.FUEL_ORE] = 80
    u.planets[planet.id] = planet
    u.sectors[sid].planet_ids.append(planet.id)
    return planet


def _stand(u, player, sid: int, planet_id: int | None) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = sid
    player.planet_landed = planet_id
    player.turns_today = 0
    if player.id not in u.sectors[sid].occupant_ids:
        u.sectors[sid].occupant_ids.append(player.id)


def _destroy(u, player, planet_id: int):
    return apply_action(
        u, player.id, Action(kind=ActionKind.PLANET_DESTROY, args={"planet_id": planet_id}),
    )


def test_two_steps_remove_the_planet_and_round_trip() -> None:
    assert K.PLANET_DESTROY_COLONISTS_TO_ZERO is True
    assert K.PLANET_DESTROY_ALIGNMENT == 50
    u, (attacker, owner, bystander, *_) = _make_universe(seed=20001)
    sid = next(sector_id for sector_id in u.sectors if sector_id > 10)
    planet = _plant(u, sid, owner.id)
    _stand(u, attacker, sid, planet.id)
    _stand(u, owner, sid, None)
    bystander.planet_landed = planet.id
    bystander_sector = bystander.sector_id
    u.events.clear()
    first = _destroy(u, attacker, planet.id)
    assert first.ok, first.error
    assert first.turns_spent == 1
    assert attacker.alignment == -50
    assert attacker.planet_landed == planet.id
    assert sum(planet.colonists.values()) == 0
    assert planet.treasury == 900
    assert planet.stockpile[Commodity.FUEL_ORE] == 80
    assert planet.fighters == 0
    killed = next(ev for ev in u.events if ev.kind is EventKind.PLANET_COLONISTS_KILLED)
    assert set(event_facts(killed)) == {"planet_id"}
    assert "900" not in killed.summary
    second = _destroy(u, attacker, planet.id)
    assert second.ok, second.error
    assert second.turns_spent == 1
    assert attacker.alignment == -100
    assert attacker.planet_landed is None
    assert attacker.sector_id == sid
    assert bystander.planet_landed is None
    assert bystander.sector_id == bystander_sector
    assert planet.id not in u.planets
    assert planet.id not in u.sectors[sid].planet_ids
    destroyed = next(ev for ev in u.events if ev.kind is EventKind.PLANET_DESTROYED)
    assert set(event_facts(destroyed)) == {"planet_id", "sector_id"}
    assert "treasury" not in destroyed.payload
    obs = build_observation(u, attacker.id)
    assert all(row["id"] != 88601 for row in obs.sector["planets"])
    restored = Universe.model_validate(u.model_dump())
    assert 88601 not in restored.planets
    assert 88601 not in restored.sectors[sid].planet_ids


def test_failures_change_nothing() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=20002)
    sid = next(sector_id for sector_id in u.sectors if sector_id > 10)
    planet = _plant(u, sid, owner.id, fighters=4, shields=0)
    _stand(u, attacker, sid, planet.id)
    res = _destroy(u, attacker, planet.id)
    assert res.ok is False
    assert res.error == "planet still has defenders"
    assert res.turns_spent == 0
    assert attacker.alignment == 0
    assert planet.colonists[Commodity.FUEL_ORE] == 3
    planet.fighters = 0
    planet.shields = 7
    shielded = _destroy(u, attacker, planet.id)
    assert shielded.error == "planet still has defenders"
    assert planet.shields == 7
    planet.shields = 0
    _stand(u, attacker, sid, None)
    away = _destroy(u, attacker, planet.id)
    assert away.error == "must be landed on the planet first"
    assert sum(planet.colonists.values()) == 18
    _stand(u, attacker, sid, planet.id)
    attacker.turns_today = attacker.turns_per_day
    tired = _destroy(u, attacker, planet.id)
    assert tired.error == "out of turns"
    assert attacker.alignment == 0
    assert sum(planet.colonists.values()) == 18


def test_friendly_planets_are_refused() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=20003)
    sid = next(sector_id for sector_id in u.sectors if sector_id > 10)
    own = _plant(u, sid, attacker.id)
    _stand(u, attacker, sid, own.id)
    assert _destroy(u, attacker, own.id).error == "planet is friendly"
    own.owner_id = owner.id
    own.corp_ticker = "ZZ"
    attacker.corp_ticker = "ZZ"
    owner.corp_ticker = "ZZ"
    assert _destroy(u, attacker, own.id).error == "planet is friendly"
    own.corp_ticker = None
    attacker.corp_ticker = None
    owner.corp_ticker = None
    attacker.alliances.append("A1")
    u.alliances["A1"] = Alliance(
        id="A1", member_ids=[attacker.id, owner.id], proposed_by=attacker.id, formed_day=1, active=True,
    )
    refused = _destroy(u, attacker, own.id)
    assert refused.error == "planet is friendly"
    assert refused.turns_spent == 0
    assert sum(own.colonists.values()) == 18


def test_switch_off_spends_nothing(monkeypatch) -> None:
    monkeypatch.setattr(K, "PLANET_DESTROY_COLONISTS_TO_ZERO", False)
    u, (attacker, owner, *_) = _make_universe(seed=20004)
    sid = next(sector_id for sector_id in u.sectors if sector_id > 10)
    planet = _plant(u, sid, owner.id)
    _stand(u, attacker, sid, planet.id)
    res = _destroy(u, attacker, planet.id)
    assert res.ok is False
    assert res.error == "planet destruction is off"
    assert attacker.alignment == 0
    assert sum(planet.colonists.values()) == 18


def test_shielded_landing_still_repels() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=20005)
    sid = next(sector_id for sector_id in u.sectors if sector_id > 10)
    planet = _plant(u, sid, owner.id, fighters=0, shields=10)
    u.sectors[sid].fighters = None
    u.sectors[sid].mines.clear()
    attacker.ship.fighters = 0
    attacker.ship.shields = 0
    _stand(u, attacker, sid, None)
    res = apply_action(
        u, attacker.id, Action(kind=ActionKind.LAND_PLANET, args={"planet_id": planet.id}),
    )
    assert res.error == "planetary defenses repelled landing"
    assert planet.id in u.planets
