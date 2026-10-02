"""Sector quasar: hostile warp, owner setting, and fog."""

from __future__ import annotations

from pathlib import Path

from tests.test_phase_abc import _make_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import Alliance, Commodity, EventKind, Planet, PlanetClass
from tw2k.engine.observation import build_observation, event_facts
from tw2k.engine.runner import apply_action

ROOT = Path(__file__).resolve().parents[1]


def _lane(u):
    for sid, sector in u.sectors.items():
        if sid <= 10:
            continue
        for dest in sector.warps:
            if dest > 10:
                return sid, dest
    raise AssertionError("no warp lane")


def _stand(u, player, sid: int) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = sid
    player.planet_landed = None
    player.turns_today = 0
    if player.id not in u.sectors[sid].occupant_ids:
        u.sectors[sid].occupant_ids.append(player.id)


def _plant(u, sid: int, planet_id: int, owner: str, *, level: int, pct: int, fuel: int) -> Planet:
    planet = Planet(
        id=planet_id, sector_id=sid, name=f"Q{planet_id}", class_id=PlanetClass.M,
        owner_id=owner, citadel_level=level, citadel_target=level,
        quasar_sector_pct=pct,
    )
    planet.stockpile[Commodity.FUEL_ORE] = fuel
    u.planets[planet.id] = planet
    u.sectors[sid].planet_ids.append(planet.id)
    return planet


def _clear(u, dest: int) -> None:
    sector = u.sectors[dest]
    sector.mines.clear()
    sector.fighters = None


def _warp(u, player, dest: int):
    _clear(u, dest)
    _stand(u, player, next(sid for sid, sector in u.sectors.items() if dest in sector.warps and sid != dest))
    return apply_action(u, player.id, Action(kind=ActionKind.WARP, args={"target": dest}))


def _shots(u):
    return [ev for ev in u.events if ev.kind is EventKind.QUASAR_FIRE]


def test_report_examples_burn_fuel_and_damage_shields_then_fighters() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=12001)
    origin, dest = _lane(u)
    planet = _plant(u, dest, 88031, owner.id, level=3, pct=10, fuel=10_000)
    attacker.ship.fighters = 5000
    attacker.ship.shields = 0
    _clear(u, dest)
    _stand(u, attacker, origin)

    res = apply_action(u, attacker.id, Action(kind=ActionKind.WARP, args={"target": dest}))
    assert res.ok, res.error
    assert planet.stockpile[Commodity.FUEL_ORE] == 9000
    assert attacker.ship.fighters == 4667
    assert attacker.ship.shields == 0
    shot = _shots(u)[-1]
    assert shot.payload["planet_id"] == 88031
    assert shot.payload["mode"] == "sector"
    assert shot.payload["damage"] == 333
    assert "fuel" not in shot.payload
    assert set(event_facts(shot)) == {"planet_id", "mode", "damage"}
    assert "1000" not in shot.summary and "9000" not in shot.summary

    _clear(u, dest)
    _stand(u, attacker, origin)
    res = apply_action(u, attacker.id, Action(kind=ActionKind.WARP, args={"target": dest}))
    assert res.ok, res.error
    assert planet.stockpile[Commodity.FUEL_ORE] == 8100
    assert attacker.ship.fighters == 4367
    assert _shots(u)[-1].payload["damage"] == 300

    attacker.ship.shields = 400
    attacker.ship.fighters = 10
    planet.stockpile[Commodity.FUEL_ORE] = 10_000
    _clear(u, dest)
    _stand(u, attacker, origin)
    apply_action(u, attacker.id, Action(kind=ActionKind.WARP, args={"target": dest}))
    assert attacker.ship.shields == 67
    assert attacker.ship.fighters == 10
    assert attacker.deaths == 0


def test_level_pct_and_fuel_gates_skip_the_shot() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=12002)
    _, dest = _lane(u)
    planet = _plant(u, dest, 88032, owner.id, level=2, pct=10, fuel=10_000)
    attacker.ship.fighters = 1000
    attacker.ship.shields = 0
    _warp(u, attacker, dest)
    assert not _shots(u)
    assert planet.stockpile[Commodity.FUEL_ORE] == 10_000

    planet.citadel_level = 3
    planet.quasar_sector_pct = 0
    _warp(u, attacker, dest)
    assert not _shots(u)

    planet.quasar_sector_pct = 10
    planet.stockpile[Commodity.FUEL_ORE] = 0
    _warp(u, attacker, dest)
    assert not _shots(u)
    assert attacker.ship.fighters == 1000


def test_own_corp_and_ally_are_not_shot() -> None:
    u, (attacker, owner, ally) = _make_universe(seed=12003)
    _, dest = _lane(u)
    planet = _plant(u, dest, 88033, attacker.id, level=3, pct=10, fuel=10_000)
    attacker.ship.fighters = 800
    _warp(u, attacker, dest)
    assert not _shots(u)

    planet.owner_id = owner.id
    planet.corp_ticker = "QQ"
    attacker.corp_ticker = "QQ"
    owner.corp_ticker = "QQ"
    _warp(u, attacker, dest)
    assert not _shots(u)

    attacker.corp_ticker = None
    owner.corp_ticker = "OTHER"
    planet.corp_ticker = "OTHER"
    planet.owner_id = ally.id
    ally.corp_ticker = "OTHER"
    u.alliances["A1"] = Alliance(
        id="A1", member_ids=[attacker.id, ally.id], proposed_by=attacker.id, formed_day=0, active=True,
    )
    attacker.alliances.append("A1")
    _warp(u, attacker, dest)
    assert not _shots(u)
    assert planet.stockpile[Commodity.FUEL_ORE] == 10_000


def test_planets_fire_in_id_order_and_stop_when_the_ship_dies() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=12004)
    _, dest = _lane(u)
    first = _plant(u, dest, 88041, owner.id, level=3, pct=10, fuel=10_000)
    second = _plant(u, dest, 88042, owner.id, level=3, pct=50, fuel=5_000)
    attacker.ship.fighters = 50
    attacker.ship.shields = 0
    deaths = attacker.deaths
    _warp(u, attacker, dest)
    shots = _shots(u)
    assert [ev.payload["planet_id"] for ev in shots] == [first.id]
    assert shots[0].payload["damage"] == 333
    assert second.stockpile[Commodity.FUEL_ORE] == 5_000
    assert attacker.deaths == deaths + 1


def test_set_quasar_sector_refusals_and_fog() -> None:
    u, (owner, outsider, mate) = _make_universe(seed=12005)
    _, dest = _lane(u)
    planet = _plant(u, dest, 88051, owner.id, level=2, pct=0, fuel=4_321)
    planet.corp_ticker = "QQ"
    owner.corp_ticker = "QQ"
    _stand(u, owner, dest)
    refused = apply_action(u, owner.id, Action(
        kind=ActionKind.SET_QUASAR_SECTOR, args={"planet_id": planet.id, "pct": 10},
    ))
    assert refused.ok is False
    assert refused.error == "must be landed on the planet first"

    owner.planet_landed = planet.id
    low = apply_action(u, owner.id, Action(
        kind=ActionKind.SET_QUASAR_SECTOR, args={"planet_id": planet.id, "pct": 10},
    ))
    assert low.error == "quasar requires citadel level 3"

    planet.citadel_level = 3
    bad = apply_action(u, owner.id, Action(
        kind=ActionKind.SET_QUASAR_SECTOR, args={"planet_id": planet.id, "pct": 101},
    ))
    assert bad.error == "pct must be from 0 to 100"

    _stand(u, outsider, dest)
    other = apply_action(u, outsider.id, Action(
        kind=ActionKind.SET_QUASAR_SECTOR, args={"planet_id": planet.id, "pct": 10},
    ))
    assert other.error == "planet not owned by you or your corp"

    ok = apply_action(u, owner.id, Action(
        kind=ActionKind.SET_QUASAR_SECTOR, args={"planet_id": planet.id, "pct": 10},
    ))
    assert ok.ok, ok.error
    assert planet.quasar_sector_pct == 10
    assert owner.turns_today == 1

    hidden = next(p for p in build_observation(u, outsider.id).sector["planets"] if p["id"] == planet.id)
    assert "quasar_sector_pct" not in hidden
    assert "stockpile" not in hidden
    assert "4321" not in str(hidden)

    owned = next(p for p in build_observation(u, owner.id).owned_planets if p["id"] == planet.id)
    assert owned["quasar_sector_pct"] == 10
    assert owned["stockpile"]["fuel_ore"] == 4321

    mate.corp_ticker = "QQ"
    _stand(u, mate, dest)
    shared = next(p for p in build_observation(u, mate.id).sector["planets"] if p["id"] == planet.id)
    assert shared["quasar_sector_pct"] == 10
    assert shared["stockpile"]["fuel_ore"] == 4321

    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert 'quasar_fire:       { cat: "combat"' in js
