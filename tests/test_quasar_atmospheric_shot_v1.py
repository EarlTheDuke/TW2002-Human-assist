"""Atmospheric quasar fires twice on a hostile landing."""

from __future__ import annotations

from tests.test_phase_abc import _make_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import Commodity, EventKind, Planet, PlanetClass
from tw2k.engine.observation import build_observation, event_facts
from tw2k.engine.runner import apply_action


def _sector(u):
    for sid, sector in u.sectors.items():
        if sid > 10:
            return sid
    raise AssertionError("no sector")


def _stand(u, player, sid: int) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = sid
    player.planet_landed = None
    player.turns_today = 0
    player.alive = True
    if player.id not in u.sectors[sid].occupant_ids:
        u.sectors[sid].occupant_ids.append(player.id)


def _plant(u, sid: int, planet_id: int, owner: str, *, level: int, pct: int, fuel: int,
           fighters: int = 0, shields: int = 0) -> Planet:
    planet = Planet(
        id=planet_id, sector_id=sid, name=f"A{planet_id}", class_id=PlanetClass.M,
        owner_id=owner, citadel_level=level, citadel_target=level,
        quasar_atm_pct=pct, fighters=fighters, shields=shields,
    )
    planet.stockpile[Commodity.FUEL_ORE] = fuel
    u.planets[planet.id] = planet
    u.sectors[sid].planet_ids.append(planet.id)
    return planet


def _clear(u, sid: int) -> None:
    sector = u.sectors[sid]
    sector.mines.clear()
    sector.fighters = None


def _land(u, player, planet):
    _clear(u, planet.sector_id)
    _stand(u, player, planet.sector_id)
    return apply_action(u, player.id, Action(kind=ActionKind.LAND_PLANET, args={"planet_id": planet.id}))


def _shots(u):
    return [ev for ev in u.events if ev.kind is EventKind.QUASAR_FIRE and ev.payload.get("mode") == "atmosphere"]


def test_two_shots_match_the_report_examples() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=13001)
    sid = _sector(u)
    planet = _plant(u, sid, 88101, owner.id, level=3, pct=10, fuel=10_000)
    attacker.ship.fighters = 20_000
    attacker.ship.shields = 0
    res = _land(u, attacker, planet)
    assert res.ok, res.error
    shots = _shots(u)
    assert [ev.payload["damage"] for ev in shots] == [2000, 1800]
    assert shots[0].payload["planet_id"] == planet.id
    assert set(event_facts(shots[0])) == {"planet_id", "mode", "damage"}
    assert "fuel" not in shots[0].payload
    assert planet.stockpile[Commodity.FUEL_ORE] == 8100
    assert attacker.ship.fighters == 16_200
    assert attacker.deaths == 0


def test_second_shot_waits_until_shields_fall_and_a_kill_ends_the_landing() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=13002)
    sid = _sector(u)
    held = _plant(u, sid, 88102, owner.id, level=3, pct=10, fuel=10_000, shields=500)
    attacker.ship.fighters = 10
    attacker.ship.shields = 8_000
    res = _land(u, attacker, held)
    assert res.ok is False and res.error == "planetary defenses repelled landing"
    assert [ev.payload["damage"] for ev in _shots(u)] == [2000]
    assert held.stockpile[Commodity.FUEL_ORE] == 9000
    assert held.shields == 500
    assert attacker.ship.shields == 6_000
    assert attacker.deaths == 0

    u.events.clear()
    falling = _plant(u, sid, 88103, owner.id, level=3, pct=10, fuel=10_000, shields=1)
    attacker.ship.fighters = 2_500
    attacker.ship.shields = 0
    deaths = attacker.deaths
    res = _land(u, attacker, falling)
    assert res.ok, res.error
    assert [ev.payload["damage"] for ev in _shots(u)] == [2000, 1800]
    assert falling.owner_id == owner.id
    assert falling.shields == 0
    assert attacker.deaths == deaths + 1
    assert falling.stockpile[Commodity.FUEL_ORE] == 8100


def test_level_and_pct_gates_and_own_corp_skip() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=13003)
    sid = _sector(u)
    planet = _plant(u, sid, 88104, owner.id, level=2, pct=10, fuel=10_000)
    attacker.ship.fighters = 5_000
    _land(u, attacker, planet)
    assert not _shots(u)
    assert planet.stockpile[Commodity.FUEL_ORE] == 10_000

    planet.citadel_level = 3
    planet.quasar_atm_pct = 0
    _land(u, attacker, planet)
    assert not _shots(u)

    planet.quasar_atm_pct = 10
    planet.owner_id = attacker.id
    _land(u, attacker, planet)
    assert not _shots(u)

    planet.owner_id = owner.id
    planet.corp_ticker = "QQ"
    attacker.corp_ticker = "QQ"
    owner.corp_ticker = "QQ"
    _land(u, attacker, planet)
    assert not _shots(u)
    assert planet.stockpile[Commodity.FUEL_ORE] == 10_000


def test_set_quasar_atm_refusals_and_fog() -> None:
    u, (owner, outsider, mate) = _make_universe(seed=13004)
    sid = _sector(u)
    planet = _plant(u, sid, 88105, owner.id, level=2, pct=0, fuel=4_321)
    planet.corp_ticker = "QQ"
    owner.corp_ticker = "QQ"
    _stand(u, owner, sid)
    refused = apply_action(u, owner.id, Action(
        kind=ActionKind.SET_QUASAR_ATM, args={"planet_id": planet.id, "pct": 10},
    ))
    assert refused.error == "must be landed on the planet first"
    owner.planet_landed = planet.id
    low = apply_action(u, owner.id, Action(
        kind=ActionKind.SET_QUASAR_ATM, args={"planet_id": planet.id, "pct": 10},
    ))
    assert low.error == "quasar requires citadel level 3"
    planet.citadel_level = 3
    bad = apply_action(u, owner.id, Action(
        kind=ActionKind.SET_QUASAR_ATM, args={"planet_id": planet.id, "pct": 101},
    ))
    assert bad.error == "pct must be from 0 to 100"
    _stand(u, outsider, sid)
    other = apply_action(u, outsider.id, Action(
        kind=ActionKind.SET_QUASAR_ATM, args={"planet_id": planet.id, "pct": 10},
    ))
    assert other.error == "planet not owned by you or your corp"
    ok = apply_action(u, owner.id, Action(
        kind=ActionKind.SET_QUASAR_ATM, args={"planet_id": planet.id, "pct": 10},
    ))
    assert ok.ok, ok.error
    assert planet.quasar_atm_pct == 10
    assert owner.turns_today == 1

    hidden = next(p for p in build_observation(u, outsider.id).sector["planets"] if p["id"] == planet.id)
    assert "quasar_atm_pct" not in hidden
    assert "stockpile" not in hidden
    assert "4321" not in str(hidden)
    owned = next(p for p in build_observation(u, owner.id).owned_planets if p["id"] == planet.id)
    assert owned["quasar_atm_pct"] == 10
    assert owned["stockpile"]["fuel_ore"] == 4321
    mate.corp_ticker = "QQ"
    _stand(u, mate, sid)
    shared = next(p for p in build_observation(u, mate.id).sector["planets"] if p["id"] == planet.id)
    assert shared["quasar_atm_pct"] == 10
    assert shared["stockpile"]["fuel_ore"] == 4321
