"""Sector mines and fighters resolve before a planet landing."""

from __future__ import annotations

import pytest

import tw2k.engine.constants as _HWK
from tests.test_phase_abc import _make_universe
from tests.test_siege_path_v1 import SECTOR, _place, _planet
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.constants import TURN_COST
from tw2k.engine.models import (
    Alliance,
    EventKind,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
)
from tw2k.engine.observation import build_observation, event_facts
from tw2k.engine.runner import apply_action

COST = TURN_COST["land_planet"]



@pytest.fixture(autouse=True)
def _pin_hardware_legacy(monkeypatch):
    """Pin HARDWARE_MODE legacy so old photon/armid bars do not drift."""
    monkeypatch.setattr(_HWK, "HARDWARE_MODE", "legacy")

def _armids(u, owner_id: str, count: int) -> None:
    u.sectors[SECTOR].mines.append(MineDeployment(owner_id=owner_id, kind=MineType.ARMID, count=count))


def _sector_fighters(u, owner_id: str, count: int, mode: FighterMode) -> None:
    u.sectors[SECTOR].fighters = FighterDeployment(owner_id=owner_id, count=count, mode=mode)


def _land(u, pid: str, planet_id: int):
    return apply_action(u, pid, Action(kind=ActionKind.LAND_PLANET, args={"planet_id": planet_id}))


def test_mines_kill_a_weak_ship_before_the_planet_fight() -> None:
    u, (attacker, *_, outsider) = _make_universe(seed=9601)
    attacker.ship.fighters = 50
    attacker.ship.shields = 0
    planet = _planet(9601, fighters=500, shields=0)
    _place(u, planet, attacker)
    _armids(u, planet.owner_id, 1)
    outsider.sector_id = SECTOR
    u.sectors[SECTOR].occupant_ids.append(outsider.id)
    deaths = attacker.deaths

    res = _land(u, attacker.id, planet.id)

    assert res.ok and res.turns_spent == COST
    assert attacker.turns_today == COST
    assert attacker.deaths == deaths + 1
    assert attacker.planet_landed is None
    assert planet.owner_id == "B"
    assert planet.fighters == 500
    assert not any(
        ev.kind is EventKind.COMBAT and ev.payload.get("exchange_kind") == "planet_siege"
        for ev in u.events
    )
    mine = next(ev for ev in u.events if ev.kind is EventKind.MINE_DETONATED)
    assert event_facts(mine) == {"hits": 1, "damage": 100, "victim": attacker.id}
    assert mine.summary == f"1 armid mines hit {attacker.name} landing {SECTOR} (100 dmg)"
    assert "planet_id" not in mine.payload
    hidden = next(p for p in build_observation(u, outsider.id).sector["planets"] if p["id"] == planet.id)
    assert "fighters" not in hidden


def test_mines_weaken_a_ship_and_the_planet_fight_changes() -> None:
    u, (attacker, *_) = _make_universe(seed=9602)
    attacker.ship.fighters = 200
    attacker.ship.shields = 0
    planet = _planet(9602, fighters=40, shields=0)
    _place(u, planet, attacker)
    _armids(u, planet.owner_id, 1)

    res = _land(u, attacker.id, planet.id)

    assert res.ok is False
    assert res.error == "planetary defenses repelled landing"
    assert planet.owner_id == "B"
    assert attacker.ship.fighters == 1
    assert planet.fighters == 7
    siege = next(ev for ev in u.events if ev.payload.get("exchange_kind") == "planet_siege")
    assert "sector" not in [row.get("phase") for row in siege.payload["rounds"]]


def test_same_landing_captures_when_the_sector_is_clear() -> None:
    u, (attacker, *_) = _make_universe(seed=9603)
    attacker.ship.fighters = 200
    attacker.ship.shields = 0
    planet = _planet(9603, fighters=40, shields=0)
    _place(u, planet, attacker)

    res = _land(u, attacker.id, planet.id)

    assert res.ok, res.error
    assert planet.owner_id == attacker.id
    assert attacker.ship.fighters == 80


def test_planet_owner_sector_fighters_engage_before_the_landing() -> None:
    u, (attacker, *_) = _make_universe(seed=9604)
    attacker.ship.fighters = 50
    attacker.ship.shields = 0
    planet = _planet(9604, fighters=400, shields=20)
    _place(u, planet, attacker)
    _sector_fighters(u, planet.owner_id, 100, FighterMode.OFFENSIVE)
    deaths = attacker.deaths

    res = _land(u, attacker.id, planet.id)

    assert res.ok and attacker.deaths == deaths + 1
    assert planet.owner_id == "B"
    assert planet.fighters == 400
    assert planet.shields == 20
    clash = next(ev for ev in u.events if ev.payload.get("vs") == "fighter_sector")
    assert event_facts(clash)["vs"] == "fighter_sector"
    assert "defender_f" not in clash.payload
    destroyed = next(ev for ev in u.events if ev.kind is EventKind.SHIP_DESTROYED)
    assert destroyed.payload["reason"] == "sector_fighters"
    assert not any(ev.payload.get("exchange_kind") == "planet_siege" for ev in u.events)


def test_own_and_corp_hazards_do_not_fire() -> None:
    u, (attacker, owner, mate) = _make_universe(seed=9605)
    attacker.corp_ticker = "ACE"
    mate.corp_ticker = "ACE"
    attacker.ship.fighters = 200
    attacker.ship.shields = 0
    planet = _planet(9605, fighters=40, shields=0)
    planet.owner_id = owner.id
    _place(u, planet, attacker)
    _armids(u, attacker.id, 5)
    _armids(u, mate.id, 5)
    _sector_fighters(u, mate.id, 100, FighterMode.OFFENSIVE)

    res = _land(u, attacker.id, planet.id)

    assert res.ok, res.error
    assert planet.owner_id == attacker.id
    assert attacker.ship.fighters == 80
    assert not any(ev.kind is EventKind.MINE_DETONATED for ev in u.events)
    assert not any(ev.payload.get("vs") == "fighter_sector" for ev in u.events)


def _quiet(u, attacker, planet) -> None:
    assert attacker.ship.fighters == 80
    assert attacker.ship.shields == 0
    assert attacker.credits == 5_000
    assert attacker.deaths == 0
    assert attacker.planet_landed == planet.id
    assert not any(ev.kind is EventKind.MINE_DETONATED for ev in u.events)
    assert not any(ev.payload.get("vs") == "fighter_sector" for ev in u.events)
    assert not any(ev.payload.get("toll_to") for ev in u.events)
    assert u.sectors[SECTOR].mines[0].count == 1


def test_friendly_landings_do_not_touch_sector_hazards() -> None:
    u, (attacker, owner, outsider) = _make_universe(seed=9611)
    attacker.ship.fighters = 80
    attacker.ship.shields = 0
    attacker.credits = 5_000
    planet = _planet(9611, fighters=30, shields=10)
    planet.owner_id = attacker.id
    _place(u, planet, attacker)
    _armids(u, outsider.id, 1)
    _sector_fighters(u, outsider.id, 100, FighterMode.OFFENSIVE)
    res = _land(u, attacker.id, planet.id)
    assert res.ok, res.error
    assert planet.owner_id == attacker.id
    _quiet(u, attacker, planet)

    u, (attacker, mate, outsider) = _make_universe(seed=9612)
    attacker.corp_ticker = mate.corp_ticker = "ACE"
    attacker.ship.fighters = 80
    attacker.ship.shields = 0
    attacker.credits = 5_000
    planet = _planet(9612, fighters=30, shields=10)
    planet.owner_id = mate.id
    planet.corp_ticker = "ACE"
    _place(u, planet, attacker)
    _armids(u, outsider.id, 1)
    _sector_fighters(u, outsider.id, 40, FighterMode.TOLL)
    res = _land(u, attacker.id, planet.id)
    assert res.ok, res.error
    assert planet.owner_id == mate.id
    _quiet(u, attacker, planet)

    u, (attacker, owner, outsider) = _make_universe(seed=9613)
    attacker.ship.fighters = 80
    attacker.ship.shields = 0
    attacker.credits = 5_000
    planet = _planet(9613, fighters=0, shields=0)
    planet.owner_id = None
    planet.corp_ticker = None
    _place(u, planet, attacker)
    _armids(u, outsider.id, 1)
    _sector_fighters(u, outsider.id, 100, FighterMode.OFFENSIVE)
    res = _land(u, attacker.id, planet.id)
    assert res.ok, res.error
    assert planet.owner_id == attacker.id
    _quiet(u, attacker, planet)


def test_allied_owner_still_fights() -> None:
    u, (attacker, ally, _) = _make_universe(seed=9614)
    attacker.ship.fighters = 1000
    attacker.ship.shields = 0
    planet = _planet(9614, fighters=10, shields=0)
    planet.owner_id = ally.id
    planet.corp_ticker = "OTHER"
    u.alliances["A1"] = Alliance(
        id="A1", member_ids=[attacker.id, ally.id], proposed_by=attacker.id, formed_day=0, active=True,
    )
    attacker.alliances.append("A1")
    _place(u, planet, attacker)
    _armids(u, ally.id, 3)

    res = _land(u, attacker.id, planet.id)

    assert res.ok, res.error
    assert planet.owner_id == attacker.id
    assert attacker.ship.fighters == 970
    assert not any(ev.kind is EventKind.MINE_DETONATED for ev in u.events)
    assert any(ev.payload.get("exchange_kind") == "planet_siege" for ev in u.events)
