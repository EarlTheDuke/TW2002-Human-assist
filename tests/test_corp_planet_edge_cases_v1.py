"""Planets when a corp member leaves, and when the last member disbands it."""

from __future__ import annotations

from tests.test_phase_abc import _make_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.combat import _are_allied
from tw2k.engine.models import Alliance, Commodity, Corporation, EventKind, Planet, PlanetClass, Universe
from tw2k.engine.observation import build_observation, event_facts
from tw2k.engine.runner import apply_action

ORPHAN_KEYS = {"planet_id", "planet_name", "former_owner", "citadel_level", "fighters"}


def _corp(u, *players, ticker: str = "ZZ") -> None:
    u.corporations[ticker] = Corporation(
        ticker=ticker, name=ticker, ceo_id=players[0].id,
        member_ids=[player.id for player in players], formed_day=u.day,
    )
    for player in players:
        player.corp_ticker = ticker


def _plant(u, sid: int, owner: str | None, planet_id: int, *, ticker: str | None = "ZZ") -> Planet:
    planet = Planet(
        id=planet_id, sector_id=sid, name=f"Hold{planet_id}", class_id=PlanetClass.M,
        owner_id=owner, corp_ticker=ticker, citadel_level=4, citadel_target=4,
        fighters=0, shields=0, treasury=900, has_transporter=True,
    )
    planet.stockpile[Commodity.FUEL_ORE] = 8000
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


def _leave(u, player):
    return apply_action(u, player.id, Action(kind=ActionKind.CORP_LEAVE, args={}))


def test_disband_keeps_live_owners_and_round_trips() -> None:
    u, (ceo, mate, *_) = _make_universe(seed=21001)
    sid = next(sector_id for sector_id in u.sectors if sector_id > 10)
    _corp(u, ceo, mate)
    mine = _plant(u, sid, ceo.id, 88611)
    theirs = _plant(u, sid, mate.id, 88612)
    first = _leave(u, mate)
    assert first.ok, first.error
    assert "ZZ" in u.corporations
    assert mate.corp_ticker is None
    assert ceo.corp_ticker == "ZZ"
    assert mine.owner_id == ceo.id and mine.corp_ticker == "ZZ"
    assert theirs.owner_id == mate.id and theirs.corp_ticker is None
    assert not any(ev.kind is EventKind.PLANET_ORPHANED for ev in u.events)
    second = _leave(u, ceo)
    assert second.ok, second.error
    assert "ZZ" not in u.corporations
    assert mine.owner_id == ceo.id and mine.corp_ticker is None
    assert theirs.owner_id == mate.id and theirs.corp_ticker is None
    assert mine.treasury == 900
    assert not any(ev.kind is EventKind.PLANET_ORPHANED for ev in u.events)
    leave = [ev for ev in u.events if ev.kind is EventKind.CORP_LEAVE]
    assert leave[-1].payload == {"ticker": "ZZ"}
    restored = Universe.model_validate(u.model_dump())
    assert restored.planets[88611].owner_id == ceo.id
    assert restored.planets[88611].corp_ticker is None
    assert restored.planets[88612].owner_id == mate.id
    assert "ZZ" not in restored.corporations


def test_disband_orphans_a_planet_with_no_live_owner() -> None:
    u, (ceo, dead, *_) = _make_universe(seed=21002)
    sid = next(sector_id for sector_id in u.sectors if sector_id > 10)
    _corp(u, ceo)
    dead.alive = False
    kept = _plant(u, sid, ceo.id, 88621)
    gone = _plant(u, sid, dead.id, 88622)
    empty = _plant(u, sid, None, 88623)
    u.events.clear()
    res = _leave(u, ceo)
    assert res.ok, res.error
    assert "ZZ" not in u.corporations
    assert kept.owner_id == ceo.id and kept.corp_ticker is None
    assert gone.owner_id is None and gone.corp_ticker is None
    assert empty.owner_id is None and empty.corp_ticker is None
    assert gone.fighters == 0 and gone.treasury == 900
    orphans = [ev for ev in u.events if ev.kind is EventKind.PLANET_ORPHANED]
    assert {ev.payload["planet_id"] for ev in orphans} == {88622, 88623}
    for ev in orphans:
        public = {key for key in ev.payload if not str(key).startswith("_")}
        assert public <= ORPHAN_KEYS | {"is_first"}
        assert public >= ORPHAN_KEYS
        assert set(event_facts(ev)) == {"planet_id", "planet_name", "former_owner"}
    assert next(ev for ev in orphans if ev.payload["planet_id"] == 88622).payload["former_owner"] == dead.id
    restored = Universe.model_validate(u.model_dump())
    assert restored.planets[88622].owner_id is None
    assert restored.planets[88622].corp_ticker is None
    assert restored.planets[88621].owner_id == ceo.id


def test_leaver_cannot_manage_a_corp_mate_planet() -> None:
    u, (leaver, mate, *_) = _make_universe(seed=21003)
    sid = next(sector_id for sector_id in u.sectors if sector_id > 10)
    other = next(sector_id for sector_id in u.sectors if sector_id > 10 and sector_id != sid)
    _corp(u, leaver, mate)
    planet = _plant(u, sid, mate.id, 88631)
    own = _plant(u, sid, leaver.id, 88632)
    _stand(u, leaver, sid, planet.id)
    _stand(u, mate, other, None)
    u.sectors[other].fighters = None
    credits = leaver.credits
    fuel = planet.stockpile[Commodity.FUEL_ORE]
    left = _leave(u, leaver)
    assert left.ok, left.error
    assert planet.owner_id == mate.id and planet.corp_ticker == "ZZ"
    assert own.owner_id == leaver.id and own.corp_ticker is None
    assert "ZZ" in u.corporations
    tries = [
        Action(kind=ActionKind.PLANET_TRANSWARP, args={"planet_id": planet.id, "dest_sector": other}),
        Action(kind=ActionKind.PLANET_TRANSPORT, args={"planet_id": planet.id, "dest_sector": other}),
        Action(kind=ActionKind.DEPOSIT_TREASURY, args={"planet_id": planet.id, "amount": 100}),
    ]
    for action in tries:
        res = apply_action(u, leaver.id, action)
        assert res.ok is False
        assert res.error == "planet not owned by you or your corp"
        assert res.turns_spent == 0
    assert leaver.turns_today == 0
    assert leaver.credits == credits
    assert planet.stockpile[Commodity.FUEL_ORE] == fuel
    assert planet.treasury == 900
    assert planet.owner_id == mate.id
    assert leaver.planet_landed == planet.id


def test_partial_leave_drops_the_leavers_ticker() -> None:
    u, (leaver, mate, *_) = _make_universe(seed=21005)
    sid = next(sector_id for sector_id in u.sectors if sector_id > 10)
    _corp(u, leaver, mate)
    mine = _plant(u, sid, leaver.id, 88651)
    mine.fighters = 40
    mine.shields = 12
    theirs = _plant(u, sid, mate.id, 88652)
    fuel = mine.stockpile[Commodity.FUEL_ORE]
    _stand(u, mate, sid, mine.id)
    left = _leave(u, leaver)
    assert left.ok, left.error
    assert "ZZ" in u.corporations
    assert leaver.corp_ticker is None
    assert mate.corp_ticker == "ZZ"
    assert mine.owner_id == leaver.id and mine.corp_ticker is None
    assert mine.fighters == 40 and mine.shields == 12
    assert mine.treasury == 900
    assert mine.stockpile[Commodity.FUEL_ORE] == fuel
    assert theirs.owner_id == mate.id and theirs.corp_ticker == "ZZ"
    assert left.turns_spent == 0
    refused = apply_action(
        u, mate.id, Action(kind=ActionKind.DEPOSIT_TREASURY, args={"planet_id": mine.id, "amount": 100}),
    )
    assert refused.ok is False
    assert refused.error == "planet not owned by you or your corp"
    assert refused.turns_spent == 0
    assert mine.treasury == 900
    _stand(u, leaver, sid, theirs.id)
    back = apply_action(
        u, leaver.id, Action(kind=ActionKind.DEPOSIT_TREASURY, args={"planet_id": theirs.id, "amount": 100}),
    )
    assert back.ok is False
    assert back.error == "planet not owned by you or your corp"
    assert back.turns_spent == 0
    assert theirs.owner_id == mate.id and theirs.corp_ticker == "ZZ"
    for pid in u.players:
        obs = build_observation(u, pid)
        assert obs.self_id == pid
    seen = build_observation(u, leaver.id)
    assert any(row["id"] == mine.id for row in seen.owned_planets)
    assert not any(row["id"] == theirs.id for row in seen.owned_planets)


def test_allied_landing_is_still_a_siege() -> None:
    u, (attacker, owner, *_) = _make_universe(seed=21004)
    sid = next(sector_id for sector_id in u.sectors if sector_id > 10)
    planet = _plant(u, sid, owner.id, 88641, ticker=None)
    planet.shields = 8
    planet.citadel_level = 1
    ally = Alliance(
        id="A1", member_ids=[attacker.id, owner.id], proposed_by=owner.id,
        formed_day=u.day, active=True,
    )
    u.alliances["A1"] = ally
    attacker.alliances.append("A1")
    owner.alliances.append("A1")
    assert _are_allied(u, attacker.id, owner.id)
    sector = u.sectors[sid]
    sector.fighters = None
    sector.mines.clear()
    attacker.ship.fighters = 0
    attacker.ship.shields = 0
    _stand(u, attacker, sid, None)
    res = apply_action(
        u, attacker.id, Action(kind=ActionKind.LAND_PLANET, args={"planet_id": planet.id}),
    )
    assert res.ok is False
    assert res.error == "planetary defenses repelled landing"
    assert res.turns_spent == 3
    assert attacker.planet_landed is None
    assert planet.owner_id == owner.id
    assert planet.shields == 8
    assert not any(ev.kind is EventKind.LAND_PLANET for ev in u.events)
