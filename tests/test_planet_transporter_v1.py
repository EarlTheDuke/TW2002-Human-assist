"""A bought transporter moves the player. The planet stays."""

from __future__ import annotations

from tests.test_phase_abc import _make_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import Commodity, EventKind, FighterDeployment, FighterMode, Planet, PlanetClass
from tw2k.engine.observation import build_observation, event_facts
from tw2k.engine.runner import apply_action


def _chain(u):
    ids = [sid for sid in u.sectors if sid > 10]
    a, b, c = ids[:3]
    u.sectors[a].warps = [b]
    u.sectors[b].warps = [a, c]
    u.sectors[c].warps = [b]
    return a, b, c


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
    planet = Planet(
        id=planet_id, sector_id=sid, name=f"R{planet_id}", class_id=PlanetClass.M,
        owner_id=owner, citadel_level=level, citadel_target=level,
    )
    planet.stockpile[Commodity.FUEL_ORE] = fuel
    u.planets[planet.id] = planet
    if planet.id not in u.sectors[sid].planet_ids:
        u.sectors[sid].planet_ids.append(planet.id)
    return planet


def _fighters(u, sid: int, owner: str) -> None:
    u.sectors[sid].fighters = FighterDeployment(owner_id=owner, count=4, mode=FighterMode.DEFENSIVE)


def _buy(u, player, planet_id: int):
    return apply_action(
        u, player.id, Action(kind=ActionKind.PLANET_BUY_TRANSPORTER, args={"planet_id": planet_id}),
    )


def _hop(u, player, planet_id: int, dest: int):
    return apply_action(
        u, player.id,
        Action(kind=ActionKind.PLANET_TRANSPORT, args={"planet_id": planet_id, "dest_sector": dest}),
    )


def test_buy_is_once_and_round_trips_through_a_snapshot() -> None:
    u, (owner, outsider, *_) = _make_universe(seed=17001)
    a, b, _c = _chain(u)
    planet = _plant(u, a, 88301, owner.id, level=1, fuel=100)
    owner.credits = 60_000
    _stand(u, owner, a)
    owner.planet_landed = planet.id
    u.events.clear()
    res = _buy(u, owner, planet.id)
    assert res.ok, res.error
    assert res.turns_spent == 0
    assert owner.credits == 10_000
    assert planet.has_transporter is True
    bought = [ev for ev in u.events if ev.kind is EventKind.PLANET_TRANSPORTER_BOUGHT][-1]
    assert bought.payload["planet_id"] == 88301
    assert set(event_facts(bought)) == {"planet_id"}
    assert "50000" not in bought.summary
    again = _buy(u, owner, planet.id)
    assert again.ok is False
    assert again.error == "transporter already bought"
    assert owner.credits == 10_000

    raw = planet.model_dump()
    assert raw["has_transporter"] is True
    assert Planet.model_validate(raw).has_transporter is True
    raw.pop("has_transporter")
    assert Planet.model_validate(raw).has_transporter is False

    owner_view = build_observation(u, owner.id)
    shown = next(item for item in owner_view.owned_planets if item["id"] == planet.id)
    assert shown["has_transporter"] is True
    _stand(u, outsider, a)
    hidden = next(item for item in build_observation(u, outsider.id).sector["planets"] if item["id"] == planet.id)
    assert "has_transporter" not in hidden


def test_one_hop_and_two_hops_move_the_player_only() -> None:
    u, (owner, *_) = _make_universe(seed=17002)
    a, b, c = _chain(u)
    planet = _plant(u, a, 88302, owner.id, level=1, fuel=100)
    planet.has_transporter = True
    owner.credits = 200_000
    _fighters(u, b, owner.id)
    _fighters(u, c, owner.id)
    _stand(u, owner, a)
    owner.planet_landed = planet.id
    u.events.clear()
    res = _hop(u, owner, planet.id, b)
    assert res.ok, res.error
    assert res.turns_spent == 1
    assert owner.sector_id == b
    assert owner.planet_landed is None
    assert owner.credits == 150_000
    assert planet.sector_id == a
    assert planet.stockpile[Commodity.FUEL_ORE] == 90
    ev = [item for item in u.events if item.kind is EventKind.PLANET_TRANSPORT][-1]
    assert ev.payload["from_sector"] == a
    assert ev.payload["to_sector"] == b
    assert set(event_facts(ev)) == {"planet_id", "from_sector", "to_sector"}
    assert "fuel" not in ev.payload
    assert "50000" not in ev.summary

    _stand(u, owner, a)
    owner.planet_landed = planet.id
    owner.credits = 200_000
    planet.stockpile[Commodity.FUEL_ORE] = 100
    res = _hop(u, owner, planet.id, c)
    assert res.ok, res.error
    assert owner.sector_id == c
    assert planet.sector_id == a
    assert owner.credits == 125_000
    assert planet.stockpile[Commodity.FUEL_ORE] == 80


def test_short_credits_fuel_fighters_and_no_flag_spend_nothing() -> None:
    u, (owner, mate, *_) = _make_universe(seed=17003)
    a, b, _c = _chain(u)
    planet = _plant(u, a, 88303, owner.id, level=1, fuel=9)
    planet.has_transporter = True
    planet.corp_ticker = "RR"
    owner.corp_ticker = "RR"
    mate.corp_ticker = "RR"
    owner.credits = 40_000
    _fighters(u, b, owner.id)
    _stand(u, owner, a)
    owner.planet_landed = planet.id
    res = _hop(u, owner, planet.id, b)
    assert res.error == "not enough credits"
    assert owner.credits == 40_000
    assert owner.sector_id == a
    assert owner.planet_landed == planet.id
    assert planet.stockpile[Commodity.FUEL_ORE] == 9

    owner.credits = 80_000
    res = _hop(u, owner, planet.id, b)
    assert res.error == "not enough planet fuel"
    assert owner.credits == 80_000
    assert planet.stockpile[Commodity.FUEL_ORE] == 9
    assert owner.sector_id == a

    planet.stockpile[Commodity.FUEL_ORE] = 100
    planet.citadel_level = 0
    planet.has_transporter = False
    res = _buy(u, owner, planet.id)
    assert res.error == "transporter requires citadel level 1"
    assert owner.credits == 80_000
    assert planet.has_transporter is False
    planet.citadel_level = 1
    planet.has_transporter = True
    u.sectors[b].fighters = None
    res = _hop(u, owner, planet.id, b)
    assert res.error == "destination needs a fighter of the planet owner"
    assert owner.credits == 80_000
    assert planet.stockpile[Commodity.FUEL_ORE] == 100

    planet.has_transporter = False
    _fighters(u, b, mate.id)
    res = _hop(u, owner, planet.id, b)
    assert res.error == "planet has no transporter"
    assert owner.credits == 80_000

    planet.has_transporter = True
    res = _hop(u, owner, planet.id, b)
    assert res.ok, res.error
    assert owner.sector_id == b
    assert planet.sector_id == a
    assert owner.credits == 30_000
    assert planet.stockpile[Commodity.FUEL_ORE] == 90
