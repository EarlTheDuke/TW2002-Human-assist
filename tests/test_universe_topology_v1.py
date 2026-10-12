"""Dead ends, traps, tunnels, and one bubble, only when that switch is on.

Off, every sector still has a way out and a way back to sector 1.
On, a ship can be stuck, a plotted course says there is no route, and
Ferrengal prefers a real dead end.

Plants:
  pb1 — live generation still refuses a sector with no way out.
  pb2 — a plotted course from that sector still invents a route.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import GameConfig, Player, Ship, ShipClass
from tw2k.engine.observation import _action_hint
from tw2k.engine.runner import _handle_plot_course
from tw2k.engine.universe import generate_universe


def _adj(universe):
    return {sid: set(s.warps) for sid, s in universe.sectors.items()}


def _reaches_all_from_one(adj) -> bool:
    stack = [1]
    seen = {1}
    while stack:
        cur = stack.pop()
        for nxt in adj[cur]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return len(seen) == len(adj)


def _cannot_reach_one(adj) -> list[int]:
    rev = {i: [] for i in adj}
    for a, neigh in adj.items():
        for b in neigh:
            rev[b].append(a)
    stack = [1]
    seen = {1}
    while stack:
        cur = stack.pop()
        for nxt in rev[cur]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return sorted(set(adj) - seen)


def _long_one_ways(adj) -> list[tuple[int, int]]:
    n = len(adj)
    span = max(20, n // 10)
    found = []
    for a, neigh in adj.items():
        for b in neigh:
            if abs(a - b) >= span and a not in adj[b]:
                found.append((a, b))
    return found


def test_default_still_has_a_way_out_and_a_way_back():
    assert K.UNIVERSE_TOPOLOGY_MODE == "legacy"
    assert K.universe_topology_live() is False
    universe = generate_universe(GameConfig(seed=42, universe_size=200))
    adj = _adj(universe)
    assert all(adj[sid] for sid in adj)
    assert _reaches_all_from_one(adj)
    assert _cannot_reach_one(adj) == []
    player = Player(
        id="P1",
        name="P1",
        sector_id=1,
        credits=1000,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER),
    )
    player.known_warps = {1: [2]}
    universe.players["P1"] = player
    hint = _action_hint({"id": 1, "warps_out": [2]}, player, [], universe)
    assert "The universe is fully connected" in hint


def test_live_map_has_a_dead_end_a_trap_a_tunnel_and_a_bubble():
    K.UNIVERSE_TOPOLOGY_MODE = "live"
    try:
        universe = generate_universe(
            GameConfig(seed=42, universe_size=200, enable_ferrengi=True)
        )
        adj = _adj(universe)
        dead = sorted(sid for sid, neigh in adj.items() if not neigh)
        assert dead
        assert all(sid > 10 for sid in dead)
        assert _reaches_all_from_one(adj)
        trapped = _cannot_reach_one(adj)
        assert trapped
        assert _long_one_ways(adj)
        closed = [
            sid
            for sid, neigh in adj.items()
            if sid > 10 and not neigh and any(sid in adj[other] for other in adj)
        ]
        assert closed
        home = universe.ferrengal_sector
        assert home in dead
        player = Player(
            id="P1",
            name="P1",
            sector_id=dead[0],
            credits=1000,
            ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER),
        )
        universe.players["P1"] = player
        result = _handle_plot_course(
            universe,
            "P1",
            Action(kind=ActionKind.PLOT_COURSE, args={"target": 1}),
        )
        assert result.ok is False
        assert result.error == "no route to target"
        player.known_warps = {1: [2]}
        hint = _action_hint({"id": dead[0], "warps_out": []}, player, [], universe)
        assert "DEAD END" in hint
        assert "fully connected" not in hint
    finally:
        K.UNIVERSE_TOPOLOGY_MODE = "legacy"
