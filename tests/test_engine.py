"""Smoke tests for the TW2K-AI engine.

These verify the core invariants: universe generation is deterministic and
connected; trading and movement apply correctly; agents can play a short
match without raising.
"""

from __future__ import annotations

import asyncio

from tw2k.agents import HeuristicAgent
from tw2k.engine import (
    Action,
    ActionKind,
    GameConfig,
    apply_action,
    build_observation,
    generate_universe,
    is_finished,
    tick_day,
)
from tw2k.engine.models import Player, Ship


def _build_universe_with_agent():
    config = GameConfig(seed=123, universe_size=300, max_days=2)
    u = generate_universe(config)
    p = Player(id="P1", name="Test", ship=Ship())
    u.players["P1"] = p
    u.sectors[1].occupant_ids.append("P1")
    p.known_sectors.add(1)
    return u, p


def test_universe_generation_is_deterministic():
    a = generate_universe(GameConfig(seed=42, universe_size=200))
    b = generate_universe(GameConfig(seed=42, universe_size=200))
    assert [s.warps for s in a.sectors.values()] == [s.warps for s in b.sectors.values()]


def test_universe_is_fully_reachable_from_sector_1():
    u = generate_universe(GameConfig(seed=7, universe_size=500))
    visited = {1}
    stack = [1]
    while stack:
        cur = stack.pop()
        for w in u.sectors[cur].warps:
            if w not in visited:
                visited.add(w)
                stack.append(w)
    assert len(visited) == 500


def test_stardock_is_in_sector_one():
    u = generate_universe(GameConfig(seed=1, universe_size=100))
    assert u.sectors[1].port is not None
    assert u.sectors[1].port.class_id.name == "STARDOCK"


def test_warp_costs_turns_and_updates_position():
    u, p = _build_universe_with_agent()
    target = u.sectors[1].warps[0]
    result = apply_action(u, "P1", Action(kind=ActionKind.WARP, args={"target": target}))
    assert result.ok is True
    assert p.sector_id == target
    # Merchant Cruiser's per-ship turns_per_warp is 3 (per K.SHIP_SPECS)
    assert p.turns_today == 3


def test_warp_to_non_adjacent_fails():
    u, p = _build_universe_with_agent()
    bad = 999 if 999 not in u.sectors[1].warps else 888
    result = apply_action(u, "P1", Action(kind=ActionKind.WARP, args={"target": bad}))
    assert result.ok is False
    assert p.sector_id == 1


def test_fedspace_disallows_attack():
    u, _ = _build_universe_with_agent()
    u.players["P2"] = Player(id="P2", name="Other", ship=Ship(), sector_id=1)
    u.sectors[1].occupant_ids.append("P2")
    result = apply_action(u, "P1", Action(kind=ActionKind.ATTACK, args={"target": "P2"}))
    assert result.ok is False


def test_corp_create_requires_funds_and_stardock():
    u, p = _build_universe_with_agent()
    p.credits = 499_000
    result = apply_action(u, "P1", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "ABC"}))
    assert result.ok is False


def test_day_tick_resets_turns_and_advances_day():
    u, p = _build_universe_with_agent()
    p.turns_today = 500
    prev_day = u.day
    tick_day(u)
    assert u.day == prev_day + 1
    assert p.turns_today == 0


def test_heuristic_agent_plays_short_match_without_error():
    config = GameConfig(seed=99, universe_size=200, max_days=1)
    u = generate_universe(config)
    a = Player(id="A", name="Alice", ship=Ship())
    b = Player(id="B", name="Bob", ship=Ship())
    u.players["A"] = a
    u.players["B"] = b
    u.sectors[1].occupant_ids.extend(["A", "B"])
    a.known_sectors.add(1)
    b.known_sectors.add(1)
    agents = [HeuristicAgent("A", "Alice"), HeuristicAgent("B", "Bob")]

    async def run():
        idx = 0
        steps = 0
        while not is_finished(u) and steps < 1000:
            agent = agents[idx]
            player = u.players[agent.player_id]
            if player.turns_today >= player.turns_per_day:
                if all(u.players[a.player_id].turns_today >= u.players[a.player_id].turns_per_day for a in agents):
                    tick_day(u)
                idx = (idx + 1) % len(agents)
                continue
            obs = build_observation(u, agent.player_id)
            action = await agent.act(obs)
            apply_action(u, agent.player_id, action)
            idx = (idx + 1) % len(agents)
            steps += 1

    asyncio.run(run())
    # If we got here without exceptions, the match is sane
    assert u.day >= 1


def test_observation_respects_visibility():
    config = GameConfig(seed=5, universe_size=100)
    u = generate_universe(config)
    a = Player(id="A", name="A", ship=Ship(), sector_id=1)
    b = Player(id="B", name="B", ship=Ship(), sector_id=50)
    u.players["A"] = a
    u.players["B"] = b
    obs = build_observation(u, "A")
    # B should appear but without sector info unless visible
    other = next(o for o in obs.other_players if o["id"] == "B")
    assert other["is_corpmate"] is False
    # B is in a different sector — no sector_id leaked unless in corp
    assert "sector_id" not in other
