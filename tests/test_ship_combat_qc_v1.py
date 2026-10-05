"""ship-combat-core-v1 QC: seat brains answer a challenge sensibly, and coverage for gaps found by QC plants.

Real engine path. Numbers are hardcoded on purpose (warp 3 turns, attack 5, Merchant Cruiser odds 1.0
and 750 fighters per attack).
"""

from __future__ import annotations

import asyncio

from tests.test_phase_abc import _first_non_fed_sector
from tests.test_ship_combat_core_v1 import _act, _brains, _challenge, _duel, _la, _last, _link
from tw2k.agents import HeuristicAgent
from tw2k.agents.seat_acceptance import validate_action
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import EventKind, FighterDeployment, FighterMode, ShipClass
from tw2k.engine.observation import build_observation, event_facts
from tw2k.engine.runner import apply_action


def _brain_step(brain, u, pid):
    obs = build_observation(u, pid).model_dump(mode="json")
    act = brain.decide(obs)
    assert validate_action(obs, act) == [], act
    res = apply_action(u, pid, Action(kind=act["kind"], args=act.get("args") or {}))
    assert res.ok, (act, res.error)
    return act


def _heuristic_step(agent, u, pid):
    act = asyncio.run(agent.act(build_observation(u, pid)))
    res = apply_action(u, pid, act)
    assert res.ok, (act, res.error)
    return act


def _held_with_a_side_exit(seed: int):
    """Unbeatable defensive fighters in `there`; `home` keeps another exit so the seat has somewhere to go.

    The seat knows every sector except the far side of `there`, so `there` is its nearest frontier: the
    pull that walked the seat straight back in after each retreat. No port next door, so a drifting
    heuristic seat picks between `there` and the side exit only.
    """
    u, owner, ship, home, there = _challenge(seed, count=5000)
    side = next(s for s in sorted(u.sectors) if s > there and s not in u.sectors[there].warps
                and s not in u.sectors[home].warps and s not in (1, home, there) and s > 10)
    _link(u, home, side)
    u.sectors[side].fighters = None
    beyond = {w for w in u.sectors[there].warps if w != home}
    for sid, sector in u.sectors.items():
        if sid in beyond:
            continue
        ship.known_sectors.add(sid)
        ship.known_warps[sid] = list(sector.warps)
    for sid in (side, there):
        u.sectors[sid].port = None
    return u, owner, ship, home, there


# ---------------------------------------------------------------------------
# brains: no warp/retreat ping-pong, no surrender for want of turns, waves count
# ---------------------------------------------------------------------------


def test_seat_brains_do_not_walk_back_into_fighters_they_retreated_from() -> None:
    for name, make in _brains().items():
        u, owner, ship, home, there = _held_with_a_side_exit(35401)
        brain = make()
        assert _brain_step(brain, u, ship.id)["kind"] == "retreat", name
        assert ship.sector_id == home
        for _ in range(12):
            _brain_step(brain, u, ship.id)
            assert ship.sector_id != there, (name, "walked back into the fighters it fled")
        assert sum(1 for e in u.events if e.kind is EventKind.FIGHTER_CHALLENGE) == 1, name


def test_heuristic_seat_does_not_walk_back_into_fighters_it_retreated_from() -> None:
    for seed in range(8):
        u, owner, ship, home, there = _held_with_a_side_exit(35402)
        agent = HeuristicAgent(ship.id, ship.name, seed=seed)
        assert _heuristic_step(agent, u, ship.id).kind is ActionKind.RETREAT
        assert ship.sector_id == home
        _heuristic_step(agent, u, ship.id)
        assert ship.sector_id != there, seed


def test_seats_short_of_turns_wait_instead_of_surrendering() -> None:
    # 2 turns left: retreat (3) and attack (5) are out of reach, surrender (1) is not. Losing the ship
    # for want of turns is never the answer; waiting keeps it for tomorrow's turns.
    seats = [(name, make) for name, make in _brains().items()] + [("H", None)]
    for name, make in seats:
        u, owner, ship, home, there = _challenge(35403, count=50)
        ship.turns_today = ship.turns_per_day - 2
        assert _la(u, ship.id, "surrender").legal and not _la(u, ship.id, "retreat").legal
        if make is None:
            kind = _heuristic_step(HeuristicAgent(ship.id, ship.name, seed=1), u, ship.id).kind.value
        else:
            kind = _brain_step(make(), u, ship.id)["kind"]
        assert kind == "wait", (name, kind)
        assert ship.deaths == 0 and ship.fighter_challenge is not None


def test_seats_clear_a_group_bigger_than_one_wave() -> None:
    # One-way in, 900 defensive fighters, 2000 aboard a Merchant Cruiser (750 per attack): two waves win.
    seats = [(name, make) for name, make in _brains().items()] + [("H", None)]
    for name, make in seats:
        u, owner, ship, home, there = _challenge(35404, count=900, one_way=True)
        ship.ship.fighters = 2000
        seat = HeuristicAgent(ship.id, ship.name, seed=1) if make is None else make()
        kinds = []
        for _ in range(4):
            if ship.fighter_challenge is None:
                break
            if make is None:
                kinds.append(_heuristic_step(seat, u, ship.id).kind.value)
            else:
                kinds.append(_brain_step(seat, u, ship.id)["kind"])
        assert kinds == ["attack", "attack"], (name, kinds)
        assert u.sectors[there].fighters is None and ship.deaths == 0
        assert ship.ship.fighters == 2000 - 900


# ---------------------------------------------------------------------------
# coverage for QC plants the slice tests missed
# ---------------------------------------------------------------------------


def test_retreat_needs_the_warp_turns_in_the_list_and_the_handler() -> None:
    u, owner, ship, home, there = _challenge(35405)
    ship.turns_today = ship.turns_per_day - 2
    listed = _la(u, ship.id, "retreat")
    assert not listed.legal and "out of turns" in (listed.reason or "")
    res = _act(u, ship.id, ActionKind.RETREAT)
    assert not res.ok
    assert ship.sector_id == there and ship.turns_today == ship.turns_per_day - 2
    assert ship.fighter_challenge is not None


def test_attacking_the_fighters_needs_the_attack_turns() -> None:
    u, owner, ship, home, there = _challenge(35406, count=10)
    ship.turns_today = ship.turns_per_day - 4
    listed = _la(u, ship.id, "attack")
    assert not listed.legal and "out of turns" in (listed.reason or "")
    res = _act(u, ship.id, ActionKind.ATTACK, target="fighters", qty=10)
    assert not res.ok
    assert u.sectors[there].fighters.count == 10 and ship.ship.fighters == 200
    assert ship.turns_today == ship.turns_per_day - 4


def test_one_short_of_the_group_leaves_one_fighter() -> None:
    u, owner, ship, home, there = _challenge(35407, count=50)
    assert _act(u, ship.id, ActionKind.ATTACK, target="fighters", qty=49).ok
    assert u.sectors[there].fighters.count == 1 and ship.ship.fighters == 151
    assert ship.fighter_challenge is not None
    assert _act(u, ship.id, ActionKind.ATTACK, target="fighters", qty=1).ok
    assert u.sectors[there].fighters is None and ship.fighter_challenge is None


def test_photon_disabled_attacker_cannot_attack_in_the_list_or_the_handler() -> None:
    u, a, d, _c, _sid = _duel(35408)
    a.ship.fighters, d.ship.fighters = 500, 100
    a.ship.photon_disabled_ticks = 1
    listed = _la(u, a.id, "attack")
    assert not listed.legal and "photon" in (listed.reason or "")
    res = _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=10)
    assert not res.ok
    assert a.ship.fighters == 500 and d.ship.fighters == 100 and a.turns_today == 0


def test_a_flee_never_lands_in_hostile_fighters() -> None:
    for seed in range(35410, 35418):
        u, a, d, c, sid = _duel(seed)
        extra = _first_non_fed_sector(u, sid + 1)
        _link(u, sid, extra)
        warps = sorted(u.sectors[sid].warps)
        safe = warps[0]
        for w in warps[1:]:
            u.sectors[w].fighters = FighterDeployment(owner_id=c.id, count=1, mode=FighterMode.TOLL)
        a.ship.fighters, d.ship.fighters, d.ship.shields = 1000, 10, 0
        a.ship.ship_class = d.ship.ship_class = ShipClass.MERCHANT_CRUISER
        assert _act(u, a.id, ActionKind.ATTACK, target=d.id, qty=1).ok
        assert event_facts(_last(u, EventKind.COMBAT))["defender_fled"] is True
        assert d.sector_id == safe, (seed, d.sector_id, safe)
