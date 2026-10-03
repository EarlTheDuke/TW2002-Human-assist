"""Planet TransWarp moves a citadel once a day along the warp graph."""

from __future__ import annotations

from tests.test_phase_abc import _make_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import Commodity, EventKind, FighterDeployment, FighterMode, Planet, PlanetClass
from tw2k.engine.observation import event_facts
from tw2k.engine.runner import apply_action


def _chain(u):
    ids = [sid for sid in u.sectors if sid > 10]
    a, b, c = ids[:3]
    far = ids[3]
    u.sectors[a].warps = [b]
    u.sectors[b].warps = [a, c]
    u.sectors[c].warps = [b]
    return a, b, c, far


def _stand(u, player, sid: int) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = sid
    player.planet_landed = None
    player.turns_today = 0
    if player.id not in u.sectors[sid].occupant_ids:
        u.sectors[sid].occupant_ids.append(player.id)


def _plant(u, sid: int, planet_id: int, owner: str, *, level: int, fuel: int) -> Planet:
    sector = u.sectors[sid]
    planet = Planet(
        id=planet_id, sector_id=sid, name=f"T{planet_id}", class_id=PlanetClass.M,
        owner_id=owner, citadel_level=level, citadel_target=level,
    )
    planet.stockpile[Commodity.FUEL_ORE] = fuel
    u.planets[planet.id] = planet
    if planet.id not in sector.planet_ids:
        sector.planet_ids.append(planet.id)
    return planet


def _fighters(u, sid: int, owner: str) -> None:
    u.sectors[sid].fighters = FighterDeployment(owner_id=owner, count=5, mode=FighterMode.DEFENSIVE)


def _go(u, player, planet_id: int, dest: int):
    return apply_action(
        u, player.id,
        Action(kind=ActionKind.PLANET_TRANSWARP, args={"planet_id": planet_id, "dest_sector": dest}),
    )


def test_two_hops_cost_800_and_move_everyone_on_the_planet() -> None:
    u, (owner, mate, *_) = _make_universe(seed=16001)
    a, _b, c, _far = _chain(u)
    planet = _plant(u, a, 88201, owner.id, level=4, fuel=800)
    _fighters(u, c, owner.id)
    _stand(u, owner, a)
    _stand(u, mate, a)
    owner.planet_landed = planet.id
    mate.planet_landed = planet.id
    owner.photon_damped_sector_id = a
    u.events.clear()
    res = _go(u, owner, planet.id, c)
    assert res.ok, res.error
    assert res.turns_spent == 1
    assert planet.sector_id == c
    assert planet.stockpile[Commodity.FUEL_ORE] == 0
    assert planet.last_transwarp_day == u.day
    assert planet.id not in u.sectors[a].planet_ids
    assert planet.id in u.sectors[c].planet_ids
    assert owner.sector_id == c and mate.sector_id == c
    assert owner.planet_landed == planet.id and mate.planet_landed == planet.id
    assert owner.photon_damped_sector_id is None
    ev = [item for item in u.events if item.kind is EventKind.PLANET_TRANSWARP][-1]
    assert ev.payload["planet_id"] == 88201
    assert ev.payload["from_sector"] == a
    assert ev.payload["to_sector"] == c
    assert "fuel" not in ev.payload
    assert set(event_facts(ev)) == {"planet_id", "from_sector", "to_sector"}
    assert "800" not in ev.summary and "400" not in ev.summary
    assert owner.id in ev.payload["_witnesses"]
    again = _go(u, owner, planet.id, a)
    assert again.ok is False
    assert again.error == "planet already moved today"
    assert planet.sector_id == c


def test_short_fuel_no_fighters_low_level_and_no_route_change_nothing() -> None:
    u, (owner, *_) = _make_universe(seed=16002)
    a, _b, c, far = _chain(u)
    planet = _plant(u, a, 88202, owner.id, level=4, fuel=799)
    _fighters(u, c, owner.id)
    _stand(u, owner, a)
    owner.planet_landed = planet.id
    res = _go(u, owner, planet.id, c)
    assert res.ok is False
    assert res.error == "not enough planet fuel"
    assert planet.sector_id == a
    assert planet.stockpile[Commodity.FUEL_ORE] == 799
    assert planet.last_transwarp_day is None
    assert planet.id in u.sectors[a].planet_ids

    planet.stockpile[Commodity.FUEL_ORE] = 800
    u.sectors[c].fighters = None
    res = _go(u, owner, planet.id, c)
    assert res.error == "destination needs a fighter of the planet owner"
    assert planet.sector_id == a

    _fighters(u, c, owner.id)
    planet.citadel_level = 3
    res = _go(u, owner, planet.id, c)
    assert res.error == "transwarp requires citadel level 4"
    assert planet.sector_id == a

    planet.citadel_level = 4
    res = _go(u, owner, planet.id, far)
    assert res.error == "no route to destination"
    assert planet.sector_id == a
    assert planet.stockpile[Commodity.FUEL_ORE] == 800


def test_corp_mate_may_move_the_planet() -> None:
    u, (owner, mate, *_) = _make_universe(seed=16003)
    a, _b, c, _far = _chain(u)
    planet = _plant(u, a, 88203, owner.id, level=4, fuel=1_000)
    planet.corp_ticker = "TT"
    owner.corp_ticker = "TT"
    mate.corp_ticker = "TT"
    _fighters(u, c, owner.id)
    _stand(u, mate, a)
    mate.planet_landed = planet.id
    res = _go(u, mate, planet.id, c)
    assert res.ok, res.error
    assert planet.sector_id == c
    assert mate.sector_id == c
    assert planet.stockpile[Commodity.FUEL_ORE] == 200
