"""Phase 6 smoke test: 5-day heuristic-only match must stay healthy.

This is the load-bearing regression guard for the core economic loop. It
drives the HeuristicAgent against a trade-only universe (no Ferrengi, no
planets, no PvP) for five in-game days and asserts the invariants that
every sane TW2002 match MUST satisfy:

    1. `player.credits` never dips below zero at any point in the sim
       — no action should ever commit a player to spending cash they
       don't have. An engine bug that double-charges a trade, or
       misses an affordability check, shows up here as a negative
       balance immediately.

    2. No player's `full_net_worth` craters below a loose floor
       (starting credits x 0.75). Heuristic trades aren't always
       profitable (a haggle rejected at a bad spread can book a small
       paper loss), so day-over-day monotonicity is NOT a real engine
       invariant — but a 25 % drawdown in a trade-only world over
       five days would indicate a genuine accounting bug (e.g. cargo
       that gets debited without credit back, or double-booked
       warp-fuel costs).

    3. Aggregate net worth across all players at end of day 5 is at
       least the aggregate starting credits. The economy is supposed
       to grow (port regen + price spreads). A drop in the AGGREGATE
       is the smoking gun of a true leakage bug.

Heuristic (not LLM) so the test stays cheap and crash-free on every CI
push. Note: Python's per-process hash seed makes `HeuristicAgent` not
bit-for-bit deterministic across runs (agent trade-choice RNG depends
on `hash(player_id)`), which is why we assert bounds rather than
monotonicity.
"""

from __future__ import annotations

import asyncio

import pytest

from tw2k.agents import HeuristicAgent
from tw2k.engine import (
    GameConfig,
    apply_action,
    build_observation,
    generate_universe,
    is_finished,
    tick_day,
)
from tw2k.engine.models import Player, Ship
from tw2k.engine.victory import full_net_worth


@pytest.mark.parametrize("seed", [17, 42, 123])
def test_heuristic_5day_economy_stays_healthy(seed: int) -> None:
    cfg = GameConfig(
        seed=seed,
        universe_size=150,
        max_days=6,  # 1 extra so we can tick through 5 without triggering victory
        turns_per_day=40,
        starting_credits=25_000,
        enable_ferrengi=False,
        enable_planets=False,
        action_delay_s=0.0,
    )
    universe = generate_universe(cfg)

    players = [
        Player(
            id=f"P{i}",
            name=f"HBot-{i}",
            ship=Ship(),
            credits=cfg.starting_credits,
            turns_per_day=cfg.turns_per_day,
            sector_id=1,
            agent_kind="heuristic",
        )
        for i in range(1, 3)
    ]
    for p in players:
        universe.players[p.id] = p
        universe.sectors[1].occupant_ids.append(p.id)
        p.known_sectors.add(1)
        for wid in universe.sectors[1].warps:
            p.known_sectors.add(wid)
    agents = [HeuristicAgent(p.id, p.name) for p in players]

    day_boundaries: list[int] = []

    async def loop() -> None:
        idx = 0
        safety = 0
        # A single in-game day is capped by turns_per_day actions per
        # player, so 5 days × 2 players × 40 turns = 400 actions worst
        # case. 5× that as a safety cap to catch any infinite-loop bug.
        action_cap = 3000
        # Per-player failure streak counter. When the heuristic has
        # too few turns left for its preferred trade (e.g. 1 turn vs. a
        # 2-turn BUY), apply_action returns ok=False with turns_spent=0
        # and we'd loop forever. Three consecutive failures force the
        # player's day closed so the simulation makes progress.
        fail_streak = {p.id: 0 for p in players}
        max_fail_streak = 3

        while not is_finished(universe) and universe.day <= 5:
            safety += 1
            if safety > action_cap:
                pytest.fail(
                    f"action cap ({action_cap}) exceeded; likely a day-done "
                    f"detection regression — day={universe.day}, "
                    f"turns={[f'{p.id}:{p.turns_today}/{p.turns_per_day}' for p in players]}"
                )
            agent = agents[idx]
            player = universe.players[agent.player_id]

            assert player.credits >= 0, (
                f"{player.id} credits negative: {player.credits} "
                f"(day {universe.day}, turn {player.turns_today})"
            )

            if player.turns_today >= player.turns_per_day:
                all_done = all(
                    universe.players[a.player_id].turns_today
                    >= universe.players[a.player_id].turns_per_day
                    for a in agents
                )
                if all_done:
                    day_boundaries.append(universe.day)
                    tick_day(universe)
                    for k in fail_streak:
                        fail_streak[k] = 0
                idx = (idx + 1) % len(agents)
                continue

            obs = build_observation(universe, agent.player_id)
            action = await agent.act(obs)
            result = apply_action(universe, agent.player_id, action)
            if result.ok and result.turns_spent > 0:
                fail_streak[player.id] = 0
            else:
                fail_streak[player.id] += 1
                if fail_streak[player.id] >= max_fail_streak:
                    # Force-end the day for this player so the test makes
                    # progress — simulates a human "passing" when they can't
                    # afford or can't productively spend their last turns.
                    player.turns_today = player.turns_per_day
                    fail_streak[player.id] = 0
            idx = (idx + 1) % len(agents)

    asyncio.run(loop())

    # We should have observed at least the first few day rollovers.
    assert len(day_boundaries) >= 1, (
        f"no day boundaries observed (day={universe.day})"
    )

    # Invariant #1 (end-of-day sample): credits still non-negative.
    for p in players:
        assert p.credits >= 0, f"{p.id} ended with {p.credits} credits"

    # Invariant #2: no player's net worth craters below a loose floor.
    # A 25 % drawdown in a trade-only world over 5 days indicates an
    # accounting bug, not strategy. The per-player floor catches
    # individual blow-ups (e.g. bug that blanks one player's cargo).
    floor = int(cfg.starting_credits * 0.75)
    for p in players:
        final = full_net_worth(universe, p)
        assert final >= floor, (
            f"{p.id} net worth collapsed: final={final} < floor={floor} "
            f"(started {cfg.starting_credits}, day {universe.day})"
        )

    # Invariant #3: aggregate wealth conserves-or-grows. Port
    # regeneration + price spreads mean the universe-as-economy should
    # at worst tread water over 5 days. An aggregate shortfall is the
    # smoking gun for a leakage bug (e.g. credits silently zeroed on
    # an error path, cargo cost that never refunds).
    total_final = sum(full_net_worth(universe, p) for p in players)
    total_start = cfg.starting_credits * len(players)
    assert total_final >= total_start, (
        f"aggregate net worth shrank: start={total_start}, final={total_final} "
        f"— indicates economic leakage in engine"
    )
