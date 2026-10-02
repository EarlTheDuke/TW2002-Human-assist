"""Planet landings use 2:1 reaction and 3:1 defense, not dice."""

from __future__ import annotations

from tests.test_phase_abc import _make_universe
from tests.test_siege_path_v1 import _land, _place, _planet
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.constants import PLANET_DEFENSE_ODDS, PLANET_OFFENSE_ODDS, TURN_COST
from tw2k.engine.models import EventKind
from tw2k.engine.observation import build_observation, event_facts
from tw2k.engine.runner import apply_action


def test_odds_constants() -> None:
    assert PLANET_OFFENSE_ODDS == 2
    assert PLANET_DEFENSE_ODDS == 3


def test_reaction_zero_repels_and_reaction_100_destroys() -> None:
    def fight(pct: int, seed: int):
        u, (attacker, *_) = _make_universe(seed=seed)
        attacker.ship.fighters = 100
        attacker.ship.shields = 40
        planet = _planet(8810 + pct, fighters=60, shields=0)
        planet.military_reaction_pct = pct
        _place(u, planet, attacker)
        res = _land(u, attacker.id, planet.id)
        return res, attacker, planet, u

    held, attacker, planet, _u = fight(0, 8810)
    assert held.ok is False
    assert held.error == "planetary defenses repelled landing"
    assert attacker.ship.fighters == 1
    assert attacker.ship.shields == 40
    assert planet.fighters == 27
    assert planet.owner_id == "B"

    lost, attacker, planet, u = fight(100, 8811)
    assert lost.ok is True
    assert attacker.deaths == 1
    assert planet.owner_id == "B"
    assert planet.fighters == 10
    combat = next(ev for ev in u.events if ev.kind is EventKind.COMBAT)
    assert [row["phase"] for row in combat.payload["rounds"]] == ["offense"]


def test_shields_up_skip_fighters_and_shields_down_reach_them() -> None:
    u, (attacker, *_) = _make_universe(seed=8820)
    attacker.ship.fighters = 100
    planet = _planet(8820, fighters=10, shields=50)
    _place(u, planet, attacker)
    blocked = _land(u, attacker.id, planet.id)
    assert blocked.ok is False
    assert planet.fighters == 10
    assert planet.shields == 45
    assert attacker.ship.fighters == 100

    u, (attacker, *_) = _make_universe(seed=8821)
    attacker.ship.fighters = 2000
    planet = _planet(8821, fighters=10, shields=10)
    _place(u, planet, attacker)
    taken = _land(u, attacker.id, planet.id)
    assert taken.ok, taken.error
    assert planet.owner_id == attacker.id
    assert planet.shields == 0
    assert planet.fighters == 0
    assert attacker.ship.fighters == 1970


def test_corp_mate_can_set_reaction_and_an_outsider_cannot() -> None:
    u, (owner, mate, outsider) = _make_universe(seed=8830)
    planet = _planet(8830, fighters=12, shields=0)
    planet.owner_id = owner.id
    planet.corp_ticker = "QQ"
    mate.corp_ticker = "QQ"
    _place(u, planet, owner)
    for player in (mate, outsider):
        if player.id not in u.sectors[120].occupant_ids:
            u.sectors[120].occupant_ids.append(player.id)
        player.sector_id = 120
    mate.planet_landed = planet.id
    outsider.planet_landed = planet.id
    before = mate.turns_today
    res = apply_action(u, mate.id, Action(
        kind=ActionKind.SET_MILITARY_REACTION, args={"planet_id": planet.id, "pct": 40},
    ))
    assert res.ok, res.error
    assert res.turns_spent == TURN_COST["set_military_reaction"]
    assert mate.turns_today == before + res.turns_spent
    assert planet.military_reaction_pct == 40
    ev = next(e for e in u.events if e.kind is EventKind.PLANET_MILITARY_REACTION)
    assert event_facts(ev) == {"planet_id": planet.id, "pct": 40}
    denied = apply_action(u, outsider.id, Action(
        kind=ActionKind.SET_MILITARY_REACTION, args={"planet_id": planet.id, "pct": 90},
    ))
    assert denied.ok is False
    assert planet.military_reaction_pct == 40
    owner_brief = next(p for p in build_observation(u, owner.id).sector["planets"] if p["id"] == planet.id)
    outsider_brief = next(p for p in build_observation(u, outsider.id).sector["planets"] if p["id"] == planet.id)
    assert owner_brief["military_reaction_pct"] == 40
    assert "military_reaction_pct" not in outsider_brief
