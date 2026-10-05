"""Ship combat follow-ups from the ship-combat QC (combat challenge follow-ups).

(a) Waiting never keeps a challenged ship in a held sector past the day: an open challenge at
    the day tick ends in a free retreat to the sector the ship came from (SHIP_COMBAT.md).
(b) The flee penalty in the legal list matches what apply_action charges.
"""

from __future__ import annotations

import asyncio

import pytest

import tw2k.engine.constants as K
from tests.test_ship_combat_core_v1 import _act, _challenge, _duel, _la, _last
from tw2k.agents import HeuristicAgent
from tw2k.agents.seat_acceptance import validate_action
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import EventKind, Planet, PlanetClass
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action, tick_day

# ---------------------------------------------------------------------------
# (a) no staying in a held sector past the day
# ---------------------------------------------------------------------------


def test_waiting_out_the_day_ends_in_a_free_retreat_at_the_tick() -> None:
    u, owner, ship, home, there = _challenge(36301)
    assert ship.fighter_challenge
    while ship.turns_today < ship.turns_per_day:
        assert _la(u, ship.id, "wait").legal
        assert _act(u, ship.id, ActionKind.WAIT).ok
    assert ship.sector_id == there and ship.fighter_challenge
    ship.port_visit_sector_id = there  # the move ends any visit, as a retreat does
    day = u.day
    tick_day(u)
    assert ship.sector_id == home and ship.fighter_challenge is None and ship.port_visit_sector_id is None
    assert ship.id in u.sectors[home].occupant_ids and ship.id not in u.sectors[there].occupant_ids
    assert ship.turns_today == 0 and ship.prev_sector_id == there
    ev = _last(u, EventKind.RETREAT)
    assert ev.day == day and {k: ev.payload[k] for k in ("from", "to", "overnight")} == {"from": there, "to": home, "overnight": True}
    assert u.sectors[there].fighters is not None and u.sectors[there].fighters.count == 10  # fighters unchanged


def test_a_stale_challenge_at_the_tick_moves_nobody() -> None:
    u, owner, ship, home, there = _challenge(36302)
    u.sectors[there].fighters = None
    tick_day(u)
    assert ship.sector_id == there and ship.fighter_challenge is None
    assert not [e for e in u.events if e.kind is EventKind.RETREAT]


def test_a_ship_that_may_not_retreat_stays_held_and_must_answer() -> None:
    u, owner, ship, home, there = _challenge(36303, one_way=True)
    tick_day(u)
    assert ship.sector_id == there and ship.fighter_challenge  # one-way lane: no way back
    assert not _la(u, ship.id, "retreat").legal and _la(u, ship.id, "surrender").legal


def test_a_paid_or_answered_challenge_is_not_touched_at_the_tick() -> None:
    u, owner, ship, home, there = _challenge(36304, mode="toll", credits=5000)
    assert _act(u, ship.id, ActionKind.PAY_TOLL).ok
    tick_day(u)
    assert ship.sector_id == there and ship.fighter_challenge is None


def _brains():
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("sba", root / "scripts" / "seat_brain_acceptance.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from tw2k.agents.seat_brain import SeatBrain

    return {"N1": mod.n1_brain, "N2": mod.n2_brain, "N3": SeatBrain, "H": None}


def _decide(name, seat, u, pid):
    if seat is None or name == "H":
        act = asyncio.run(seat.act(build_observation(u, pid)))
        return {"kind": getattr(act.kind, "value", str(act.kind)), "args": dict(act.args or {})}, None
    obs = build_observation(u, pid).model_dump(mode="json")
    return seat.decide(obs), obs


@pytest.mark.parametrize("name", ["N1", "N2", "N3", "H"])
def test_seats_held_at_the_end_of_the_day_fall_back_and_play_on(name: str) -> None:
    u, owner, ship, home, there = _challenge(36305, count=5000)
    ship.ship.fighters = 10
    ship.turns_today = ship.turns_per_day - 1  # short of turns for the retreat and the attack
    make = _brains()[name]
    seat = HeuristicAgent(ship.id, name, seed=5) if make is None else make()
    for _ in range(6):
        if ship.turns_today >= ship.turns_per_day:
            break
        act, obs = _decide(name, seat, u, ship.id)
        assert act["kind"] == "wait", (name, act)
        assert apply_action(u, ship.id, Action(kind=act["kind"], args=act.get("args") or {})).ok
    assert ship.sector_id == there and ship.deaths == 0
    tick_day(u)
    assert ship.sector_id == home and ship.fighter_challenge is None
    spent = 0
    for _ in range(25):
        act, obs = _decide(name, seat, u, ship.id)
        legal = {la.kind: la.legal for la in legal_actions(u, ship.id)}
        assert legal.get(act["kind"]), (name, act)
        if obs is not None:
            assert validate_action(obs, act) == [], (name, act)
        before = ship.turns_today
        assert apply_action(u, ship.id, Action(kind=act["kind"], args=act.get("args") or {})).ok, (name, act)
        spent += ship.turns_today - before
    assert spent > 0 and ship.deaths == 0, name


# ---------------------------------------------------------------------------
# (b) the flee penalty: the list shows what the handler charges
# ---------------------------------------------------------------------------


def _fled(seed: int):
    u, a, d, _c, sid = _duel(seed)
    a.ship.fighters, d.ship.fighters, d.ship.shields = 1000, 50, 0
    assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=1).ok
    assert d.flee_penalty
    here = u.sectors[d.sector_id]
    pl = Planet(id=97101, sector_id=d.sector_id, name="Haven", class_id=PlanetClass.M, owner_id=d.id)
    u.planets[pl.id] = pl
    here.planet_ids = [*here.planet_ids, pl.id]
    return u, d, pl


@pytest.mark.parametrize("left_after", [0, 1, 5])
def test_flee_penalty_in_the_list_matches_the_handler(left_after: int) -> None:
    u, d, pl = _fled(36310)
    land = K.TURN_COST["land_planet"]
    d.turns_today = d.turns_per_day - land - left_after
    listed = _la(u, d.id, "land_planet")
    want_extra = min(1, left_after)
    assert listed.legal and listed.turn_cost == land + want_extra
    assert listed.params["flee_penalty_turns"] == want_extra
    before = d.turns_today
    res = _act(u, d.id, ActionKind.LAND_PLANET, planet_id=pl.id)
    assert res.ok, res.error
    assert d.turns_today - before == listed.turn_cost == res.turns_spent
    assert not d.flee_penalty


def test_a_free_second_trade_shows_no_flee_penalty() -> None:
    u, d, _pl = _fled(36311)
    d.port_visit_sector_id = d.sector_id  # an open visit: the next trade costs no turn
    listed = _la(u, d.id, "trade")
    assert listed.turn_cost == 0 and not listed.params.get("flee_penalty_turns")
