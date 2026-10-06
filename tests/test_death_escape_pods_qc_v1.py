"""Independent QC of death-escape-pods-v1 (4b8fd31): the fixes in "escape pods QC fixes".

Each test failed on 4b8fd31. Real engine path; numbers hardcoded on purpose.
"""

from __future__ import annotations

import asyncio
import json

import tw2k.engine.constants as K
from tests.test_death_escape_pods_v1 import (
    _act,
    _brains,
    _challenge,
    _clear,
    _la,
    _make_universe,
    _park,
    _pod_at,
)
from tests.test_phase_abc import _first_non_fed_sector
from tw2k.agents import HeuristicAgent
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.combat import _destroy_ship
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import ShipClass
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action, tick_day

PODDED = [c.value for c in ShipClass if c.value not in ("scout_marauder", "escape_pod")]


def _far_sector(u, hops: int = 5) -> int:
    """A non-FedSpace sector at least `hops` warps from StarDock, the lowest id that qualifies."""
    depth = {K.STARDOCK_SECTOR: 0}
    order = [K.STARDOCK_SECTOR]
    for cur in order:
        for w in u.sectors[cur].warps:
            if w not in depth:
                depth[w] = depth[cur] + 1
                order.append(w)
    return min(s for s, d in depth.items() if d >= hops and s not in K.FEDSPACE_SECTORS)


def _h_run(u, pid: str, steps: int, stop=None) -> list:
    """Drive the heuristic seat through the legal list. Returns (kind, ok, error) per step."""
    agent = HeuristicAgent(pid, "H", seed=3)
    out = []
    p = u.players[pid]
    for _ in range(steps):
        if p.turns_today >= p.turns_per_day or (stop and stop()):
            break
        obs = build_observation(u, pid)
        act = asyncio.run(agent.act(obs))
        kind = getattr(act.kind, "value", str(act.kind))
        legal = {la.kind: la.legal for la in legal_actions(u, pid)}
        res = apply_action(u, pid, act)
        out.append((kind, legal.get(kind, False), res.ok, res.error))
    return out


# ---------------------------------------------------------------------------
# fog: the killer and the witnesses do not learn where the pod went
# ---------------------------------------------------------------------------


def test_no_rival_reads_the_pod_sector_in_any_event_text() -> None:
    u, (a, b, c) = _make_universe(seed=36190)
    start = _first_non_fed_sector(u, 40)
    _park(u, a, start)
    _park(u, b, start)
    _park(u, c, start)
    a.ship.ship_class = ShipClass.BATTLESHIP
    _destroy_ship(u, a.id, reason="combat", killer_id=b.id, by_other=True)
    assert a.ship.ship_class is ShipClass.ESCAPE_POD and a.sector_id != start
    pod = str(a.sector_id)
    for rival in (b, c):
        events = build_observation(u, rival.id).model_dump(mode="json")["recent_events"]
        mine = [e for e in events if e["kind"] == "ship_destroyed"]
        assert mine, rival.id  # the loss itself is public to the sector
        assert all(f"sector {pod}" not in json.dumps(e) and pod not in json.dumps(e.get("facts")) for e in mine), mine
        assert "escaped in a pod" in mine[0]["summary"]
    # The pilot knows where it is.
    assert build_observation(u, a.id).sector["id"] == a.sector_id


def test_the_pod_and_the_free_scout_land_on_the_pilot_map() -> None:
    u, (a, b, c) = _make_universe(seed=36191)
    start = _first_non_fed_sector(u, 40)
    _park(u, a, start)
    a.ship.ship_class = ShipClass.CARGOTRAN
    a.known_sectors = {start}
    a.known_warps = {}
    _destroy_ship(u, a.id, reason="combat", killer_id=b.id, by_other=True)
    assert a.sector_id in a.known_sectors and a.known_warps[a.sector_id] == list(u.sectors[a.sector_id].warps)
    a.known_sectors = set()
    a.known_warps = {}
    _destroy_ship(u, a.id, reason="mines")  # the pod is lost: Ship Destroyed, free Scout at StarDock
    assert a.ship.ship_class is ShipClass.SCOUT_MARAUDER
    assert K.STARDOCK_SECTOR in a.known_sectors and K.STARDOCK_SECTOR in a.known_warps


# ---------------------------------------------------------------------------
# nothing from nothing: losing a ship never beats trading it in
# ---------------------------------------------------------------------------


def test_a_pod_is_worth_no_more_than_any_hull_it_came_from() -> None:
    assert K.trade_in_credit("escape_pod") == 3987  # 25 percent of the 15,950 Scout
    assert K.net_hull_cost("escape_pod", "scout_marauder") == 0  # d17: the pod buys a Scout outright
    for lost in PODDED:
        assert K.trade_in_credit("escape_pod") <= K.trade_in_credit(lost), lost
        for new in K.ship_specs():
            if new == "scout_marauder":
                continue
            assert K.net_hull_cost("escape_pod", new) >= K.net_hull_cost(lost, new), (lost, new)


def test_surrendering_a_cruiser_does_not_buy_a_cheaper_cargotran() -> None:
    # Trade the live Merchant Cruiser in.
    u, owner, ship, home, there = _challenge(36192)
    _park(u, ship, K.STARDOCK_SECTOR)
    ship.credits = 100_000
    assert _act(u, ship.id, ActionKind.BUY_SHIP, ship_class="cargotran").ok
    traded = ship.credits
    # Surrender it, fly the pod in, buy the same Cargotran.
    u, owner, ship, home, there = _challenge(36192)
    ship.credits = 100_000
    assert _act(u, ship.id, ActionKind.SURRENDER).ok
    assert ship.ship.ship_class is ShipClass.ESCAPE_POD
    assert ship.credits == 0  # gb13: surrender sinks the cash; put it back so the hull trade-in is the comparison
    ship.credits = 100_000
    _park(u, ship, K.STARDOCK_SECTOR)
    net = _la(u, ship.id, "buy_ship").params["ship_class"]["net_cost_by"]["cargotran"]
    assert net == 51_950 - 3_987
    assert _act(u, ship.id, ActionKind.BUY_SHIP, ship_class="cargotran").ok
    assert ship.credits < traded, (ship.credits, traded)


def test_surrender_after_surrender_mints_nothing() -> None:
    u, owner, ship, home, there = _challenge(36193)
    ship.credits = 0
    worth = []
    for _ in range(3):
        _park(u, ship, home)
        ship.fighter_challenge = None
        ship.turns_today = 0
        assert _act(u, ship.id, ActionKind.WARP, target=there).ok and ship.fighter_challenge
        assert _act(u, ship.id, ActionKind.SURRENDER).ok
        worth.append((ship.ship.ship_class.value, K.trade_in_credit(ship.ship.ship_class.value), ship.credits))
    assert [w[0] for w in worth] == ["escape_pod", "scout_marauder", "scout_marauder"]
    assert all(w[2] == 0 for w in worth) and max(w[1] for w in worth) <= K.trade_in_credit("merchant_cruiser")


# ---------------------------------------------------------------------------
# the heuristic (H) seat in a pod and after Ship Destroyed
# ---------------------------------------------------------------------------


def test_heuristic_seat_flies_its_pod_to_stardock_and_trades_it() -> None:
    u, (a, b, c) = _make_universe(seed=36194)
    far = _far_sector(u)
    _pod_at(u, a, far)
    for sid in list(u.sectors):
        if sid != far:
            _clear(u, sid)
    a.credits = 5_000
    steps = _h_run(u, a.id, 40, stop=lambda: a.ship.ship_class is not ShipClass.ESCAPE_POD)
    assert a.ship.ship_class is ShipClass.SCOUT_MARAUDER and a.sector_id == K.STARDOCK_SECTOR, steps
    assert all(legal and ok for _k, legal, ok, _e in steps), steps
    assert [k for k, *_ in steps] == ["plot_course", "buy_ship"]


def test_heuristic_seat_in_a_pod_short_of_turns_waits_not_warps() -> None:
    u, (a, b, c) = _make_universe(seed=36195)
    _pod_at(u, a, _far_sector(u))
    a.turns_today = a.turns_per_day - 4  # a pod warp costs 6
    steps = _h_run(u, a.id, 10)
    assert steps and all(legal and ok for _k, legal, ok, _e in steps), steps
    assert {k for k, *_ in steps} == {"wait"}


def test_heuristic_seat_after_ship_destroyed_plays_the_next_day_legally() -> None:
    u, (a, b, c) = _make_universe(seed=36196)
    _park(u, a, _first_non_fed_sector(u, 40))
    a.credits = 90_000
    a.ship.ship_class = ShipClass.SCOUT_MARAUDER
    _destroy_ship(u, a.id, reason="mines")
    assert a.sector_id == K.STARDOCK_SECTOR and a.turns_today == a.turns_per_day
    tick_day(u)
    steps = _h_run(u, a.id, 60)
    bad = [s for s in steps if not (s[1] and s[2])]
    assert not bad, bad[:5]
    assert a.ship.fighters <= K.hull_spec("scout_marauder")["max_fighters"]


def test_every_seat_kind_leaves_a_far_pod_the_same_day() -> None:
    for name, make in {**_brains(), "H": None}.items():
        u, (a, b, c) = _make_universe(seed=36197)
        far = _far_sector(u)
        _pod_at(u, a, far)
        for sid in list(u.sectors):
            if sid != far:
                _clear(u, sid)
        if make is None:
            steps = _h_run(u, a.id, 40, stop=lambda p=a: p.ship.ship_class is not ShipClass.ESCAPE_POD)
            assert all(legal and ok for _k, legal, ok, _e in steps), (name, steps)
        else:
            brain = make()
            for _ in range(40):
                if a.ship.ship_class is not ShipClass.ESCAPE_POD:
                    break
                act = brain.decide(build_observation(u, a.id).model_dump(mode="json"))
                assert apply_action(u, a.id, Action(kind=act["kind"], args=act.get("args") or {})).ok, (name, act)
        assert a.ship.ship_class is not ShipClass.ESCAPE_POD, name


def test_heuristic_seat_short_of_turns_for_a_warp_waits_instead_of_a_rejected_warp() -> None:
    # Pre-existing: H sent a warp it could not pay for at the end of every day (one rejection a day,
    # 6-turn pod warps made it a loop). It now WAITs the last turns away.
    u, (a, b, c) = _make_universe(seed=36198)
    _park(u, a, _first_non_fed_sector(u, 40))
    a.ship.ship_class = ShipClass.MERCHANT_CRUISER
    a.turns_today = a.turns_per_day - (_la(u, a.id, "warp").turn_cost - 1)
    steps = _h_run(u, a.id, 10)
    assert steps and all(legal and ok for _k, legal, ok, _e in steps), steps
    assert a.turns_today == a.turns_per_day


def test_the_two_pods_warning_clears_at_the_day_tick() -> None:
    u, (a, b, c) = _make_universe(seed=36199)
    _park(u, a, _first_non_fed_sector(u, 40))
    for _ in range(2):
        a.ship.ship_class = ShipClass.BATTLESHIP
        _destroy_ship(u, a.id, reason="mines")
    assert "one more today is SHIP DESTROYED" in build_observation(u, a.id).action_hint
    tick_day(u)
    assert a.pods_today == 2  # the counter resets lazily on the next loss
    assert "one more today is SHIP DESTROYED" not in build_observation(u, a.id).action_hint
    a.ship.ship_class = ShipClass.BATTLESHIP
    _destroy_ship(u, a.id, reason="mines")
    assert a.ship.ship_class is ShipClass.ESCAPE_POD and a.pods_today == 1


def test_a_pod_that_stays_put_ends_the_port_visit() -> None:
    u, (a, b, c) = _make_universe(seed=36200)
    sid = next(s for s in sorted(u.sectors) if s not in K.FEDSPACE_SECTORS and u.sectors[s].port is not None
               and s != K.STARDOCK_SECTOR)
    _park(u, a, sid)
    a.prev_sector_id = None  # no previous sector: the pod stays where it died
    a.port_visit_sector_id = sid
    a.ship.ship_class = ShipClass.CARGOTRAN
    _destroy_ship(u, a.id, reason="mines")
    assert a.sector_id == sid and a.ship.ship_class is ShipClass.ESCAPE_POD
    assert a.port_visit_sector_id is None


def test_the_pod_and_the_free_scout_carry_nothing_over() -> None:
    from tw2k.engine.models import Commodity, MineType

    u, (a, b, c) = _make_universe(seed=36201)
    _park(u, a, _first_non_fed_sector(u, 40))
    for hull in (ShipClass.HAVOC_GUNSTAR, ShipClass.ESCAPE_POD):  # a pod, then Ship Destroyed
        if hull is not ShipClass.ESCAPE_POD:
            a.ship.ship_class = hull
        s = a.ship
        s.fighters, s.shields, s.genesis, s.photon_missiles, s.ether_probes, s.photon_disabled_ticks = 9, 9, 2, 3, 4, 1
        s.mines = {MineType.ARMID: 5, MineType.LIMPET: 6, MineType.ATOMIC: 1}
        s.cargo[Commodity.EQUIPMENT] = 3
        _destroy_ship(u, a.id, reason="mines")
        s = a.ship
        assert (s.fighters, s.shields, s.genesis, s.photon_missiles, s.ether_probes, s.photon_disabled_ticks) == (0,) * 6
        assert sum(s.mines.values()) == 0 and s.cargo_used == 0
