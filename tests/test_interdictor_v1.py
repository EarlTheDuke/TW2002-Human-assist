"""Citadel L6 holds one hostile warp, burns 500 fuel, then fires the sector cannon."""

from __future__ import annotations

from tests.test_phase_abc import _make_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import Alliance, Commodity, EventKind, Planet, PlanetClass
from tw2k.engine.observation import event_facts
from tw2k.engine.runner import apply_action


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


def _plant(u, sid: int, planet_id: int, owner: str, *, level: int, fuel: int, pct: int = 10) -> Planet:
    sector = u.sectors[sid]
    planet = Planet(
        id=planet_id, sector_id=sid, name=f"I{planet_id}", class_id=PlanetClass.M,
        owner_id=owner, citadel_level=level, citadel_target=level,
        quasar_sector_pct=pct,
    )
    planet.stockpile[Commodity.FUEL_ORE] = fuel
    u.planets[planet.id] = planet
    if planet.id not in sector.planet_ids:
        sector.planet_ids.append(planet.id)
    return planet


def _clear(u, sid: int) -> None:
    sector = u.sectors[sid]
    sector.mines.clear()
    sector.fighters = None
    sector.planet_ids.clear()


def _link(u, src: int, dest: int) -> None:
    if dest not in u.sectors[src].warps:
        u.sectors[src].warps.append(dest)


def _warp(u, player, dest: int):
    _link(u, player.sector_id, dest)
    return apply_action(u, player.id, Action(kind=ActionKind.WARP, args={"target": dest}))


def _holds(u):
    return [ev for ev in u.events if ev.kind is EventKind.INTERDICT]


def test_five_hundred_fuel_holds_and_the_cannon_uses_what_remains() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=15001)
    origin, here = _lane(u)
    planet = _plant(u, here, 88101, owner.id, level=6, fuel=10_000)
    attacker.ship.fighters = 2000
    attacker.ship.shields = 0
    attacker.photon_damped_sector_id = here
    _clear(u, here)
    _clear(u, origin)
    sector = u.sectors[here]
    sector.planet_ids.append(planet.id)
    _stand(u, attacker, here)
    u.events.clear()
    res = _warp(u, attacker, origin)
    assert res.ok is False
    assert res.error == "interdicted by a planet"
    assert attacker.sector_id == here
    assert attacker.turns_today == res.turns_spent
    assert res.turns_spent > 0
    assert planet.stockpile[Commodity.FUEL_ORE] == 8550
    shot = [ev for ev in u.events if ev.kind is EventKind.QUASAR_FIRE][-1]
    assert shot.payload["damage"] == 316
    assert shot.payload["mode"] == "sector"
    held = _holds(u)[-1]
    assert held.payload["planet_id"] == 88101
    assert held.payload["ship_name"] == attacker.name
    assert "fuel" not in held.payload
    assert set(event_facts(held)) == {"planet_id", "ship_name"}
    assert "500" not in held.summary and "8550" not in held.summary
    assert not [ev for ev in u.events if ev.kind is EventKind.WARP]


def test_low_fuel_low_level_and_friends_warp_free() -> None:
    u, (attacker, owner, ally) = _make_universe(seed=15002)
    origin, here = _lane(u)
    planet = _plant(u, here, 88102, owner.id, level=6, fuel=499)
    attacker.ship.fighters = 500
    _clear(u, here)
    _clear(u, origin)
    u.sectors[here].planet_ids.append(planet.id)
    _stand(u, attacker, here)
    res = _warp(u, attacker, origin)
    assert res.ok, res.error
    assert attacker.sector_id == origin
    assert planet.stockpile[Commodity.FUEL_ORE] == 499
    assert not _holds(u)

    planet.stockpile[Commodity.FUEL_ORE] = 10_000
    planet.citadel_level = 5
    _stand(u, attacker, here)
    res = _warp(u, attacker, origin)
    assert res.ok, res.error
    assert planet.stockpile[Commodity.FUEL_ORE] == 10_000

    planet.citadel_level = 6
    planet.owner_id = attacker.id
    _stand(u, attacker, here)
    res = _warp(u, attacker, origin)
    assert res.ok, res.error
    assert planet.stockpile[Commodity.FUEL_ORE] == 10_000

    planet.owner_id = owner.id
    planet.corp_ticker = "QQ"
    attacker.corp_ticker = "QQ"
    owner.corp_ticker = "QQ"
    _stand(u, attacker, here)
    res = _warp(u, attacker, origin)
    assert res.ok, res.error

    attacker.corp_ticker = None
    owner.corp_ticker = "OTHER"
    planet.corp_ticker = "OTHER"
    planet.owner_id = ally.id
    ally.corp_ticker = "OTHER"
    u.alliances["A1"] = Alliance(
        id="A1", member_ids=[attacker.id, ally.id], proposed_by=attacker.id, formed_day=0, active=True,
    )
    attacker.alliances.append("A1")
    _stand(u, attacker, here)
    res = _warp(u, attacker, origin)
    assert res.ok, res.error
    assert planet.stockpile[Commodity.FUEL_ORE] == 10_000
    assert not _holds(u)


def test_only_the_lowest_id_planet_holds() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=15003)
    origin, here = _lane(u)
    _clear(u, here)
    _clear(u, origin)
    first = _plant(u, here, 88111, owner.id, level=6, fuel=10_000)
    second = _plant(u, here, 88112, owner.id, level=6, fuel=10_000)
    attacker.ship.fighters = 2000
    attacker.ship.shields = 0
    _stand(u, attacker, here)
    u.events.clear()
    res = _warp(u, attacker, origin)
    assert res.ok is False
    assert first.stockpile[Commodity.FUEL_ORE] == 8550
    assert second.stockpile[Commodity.FUEL_ORE] == 10_000
    assert [ev.payload["planet_id"] for ev in _holds(u)] == [88111]


def test_the_quasar_can_destroy_the_held_ship(monkeypatch) -> None:
    monkeypatch.setattr("tw2k.engine.constants.DEATH_MODE", "legacy")  # the old death: StarDock, x0.75, 3 lives
    u, (attacker, owner, *_) = _make_universe(seed=15004)
    origin, here = _lane(u)
    _clear(u, here)
    planet = _plant(u, here, 88121, owner.id, level=6, fuel=10_000)
    attacker.ship.fighters = 10
    attacker.ship.shields = 0
    _stand(u, attacker, here)
    u.events.clear()
    res = _warp(u, attacker, origin)
    assert res.ok is False
    assert res.error == "interdicted by a planet"
    assert attacker.turns_today == res.turns_spent
    assert attacker.deaths == 1
    assert attacker.sector_id != here
    assert planet.stockpile[Commodity.FUEL_ORE] == 8550
    assert [ev for ev in u.events if ev.kind is EventKind.QUASAR_FIRE]


def test_plot_course_stops_at_the_interdict() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=15005)
    origin, mid = _lane(u)
    beyond = next(sid for sid in u.sectors if sid not in (origin, mid) and sid > 10)
    u.sectors[origin].warps = [mid]
    if beyond not in u.sectors[mid].warps:
        u.sectors[mid].warps.append(beyond)
    _clear(u, origin)
    _clear(u, mid)
    _clear(u, beyond)
    planet = _plant(u, mid, 88131, owner.id, level=6, fuel=10_000, pct=0)
    attacker.ship.fighters = 2000
    attacker.ship.shields = 0
    _stand(u, attacker, origin)
    u.events.clear()
    res = apply_action(
        u, attacker.id,
        Action(kind=ActionKind.PLOT_COURSE, args={"target": beyond, "execute": True}),
    )
    assert res.ok is False
    assert res.error == "interdicted by a planet"
    assert attacker.sector_id == mid
    assert planet.stockpile[Commodity.FUEL_ORE] == 9500
    stopped = [ev for ev in u.events if ev.kind is EventKind.AUTOPILOT][-1]
    assert stopped.payload["stopped"] == "interdict"
    assert "interdict" in stopped.summary
    assert _holds(u)
