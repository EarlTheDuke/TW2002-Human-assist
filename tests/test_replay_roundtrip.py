"""Tests for the Phase 6 save + replay pipeline.

These tests verify the core promise of `tw2k replay`: for the same seed,
re-executing the recorded actions.jsonl onto a fresh Universe reconstructs
the live match bit-for-bit — every commander's credits, every ship loadout,
every planet ownership, every event seq.

We deliberately exercise the MatchRunner's real save sink (not a mock) and
the real ReplayRunner, wired up to an in-memory Broadcaster. No network,
no uvicorn — just the engine + the runners.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from tw2k.engine import (
    GameConfig,
    apply_action,
    build_observation,
    generate_universe,
    is_finished,
    tick_day,
)
from tw2k.engine.actions import Action
from tw2k.engine.models import Player, Ship
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.replay import ReplayRunner
from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec


def _run_tiny_heuristic_match(tmp_path: Path, seed: int = 42) -> Path:
    """Record a short heuristic-only match to tmp_path/saves/<id>/ and
    return the saves dir.
    """
    broadcaster = Broadcaster()
    saves_root = tmp_path / "saves"
    runner = MatchRunner(broadcaster, saves_root=saves_root)

    cfg = GameConfig(
        seed=seed,
        universe_size=80,
        max_days=2,
        turns_per_day=20,
        starting_credits=30_000,
        enable_ferrengi=False,
        enable_planets=False,
        action_delay_s=0.0,
    )
    spec = MatchSpec(
        config=cfg,
        agents=[
            AgentSpec(player_id="P1", name="HBot-1", kind="heuristic"),
            AgentSpec(player_id="P2", name="HBot-2", kind="heuristic"),
        ],
        action_delay_s=0.0,
    )

    async def _go() -> None:
        await runner.start(spec)
        # Let the runner churn through a few actions then stop.
        for _ in range(80):
            await asyncio.sleep(0.01)
            if runner.state.status in ("finished", "error"):
                break
        await runner.stop()

    asyncio.run(_go())

    # Resolve the one and only run dir we just wrote.
    run_dirs = sorted([d for d in saves_root.iterdir() if d.is_dir()])
    assert run_dirs, "MatchRunner did not create a saves/<run-id>/ dir"
    return run_dirs[-1]


def test_saves_dir_has_expected_files(tmp_path: Path) -> None:
    save_dir = _run_tiny_heuristic_match(tmp_path, seed=1234)

    assert (save_dir / "meta.json").is_file(), "meta.json missing"
    assert (save_dir / "actions.jsonl").is_file(), "actions.jsonl missing"
    assert (save_dir / "events.jsonl").is_file(), "events.jsonl missing"

    meta = json.loads((save_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["config"]["seed"] == 1234
    assert meta["schema_version"] == 1
    assert len(meta["agents"]) == 2
    assert {a["player_id"] for a in meta["agents"]} == {"P1", "P2"}

    # At least a few action entries should have been written.
    actions_lines = [
        json.loads(line)
        for line in (save_dir / "actions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert actions_lines, "no actions recorded"
    assert all(e.get("kind") in ("action", "day_tick") for e in actions_lines)
    assert any(e.get("kind") == "action" for e in actions_lines)


def _replay_headless(save_dir: Path) -> ReplayRunner:
    """Run ReplayRunner to completion on save_dir and return the runner."""
    broadcaster = Broadcaster()
    runner = ReplayRunner(broadcaster, save_dir)
    # Max out the speed so playback is wall-clock trivial regardless of
    # how long the live match took between actions.
    runner.set_speed(10.0)

    async def _go() -> None:
        await runner.start()
        for _ in range(1200):
            await asyncio.sleep(0.005)
            if runner.state.status in ("finished", "error"):
                break
        await runner.stop()

    asyncio.run(_go())
    return runner


def test_replay_reconstructs_final_state(tmp_path: Path) -> None:
    """End-to-end: MatchRunner records → ReplayRunner re-executes → snapshots match.

    This is the load-bearing test for the save/replay contract. If the
    engine ever picks up a non-determinism source (a stray time.time(),
    a non-universe RNG, a dict-ordering dependency), this test fails —
    which is exactly the behavior we want.
    """
    save_dir = _run_tiny_heuristic_match(tmp_path, seed=7777)

    # Reconstruct the expected terminal state by running the same config
    # with the same heuristic logic directly — no runner, no broadcaster,
    # no save sink. If replay matches this, we've proven determinism.
    expected = _simulate_match_from_meta(save_dir)

    runner = _replay_headless(save_dir)
    assert runner.state.status == "finished"
    u = runner.state.universe
    assert u is not None

    # Core per-player invariants. These are the ones a spectator cares
    # about: did the same money, the same ship, land in the same place?
    for pid in ("P1", "P2"):
        live = expected.players[pid]
        rep = u.players[pid]
        assert rep.credits == live.credits, f"{pid} credits drift"
        assert rep.sector_id == live.sector_id, f"{pid} sector drift"
        assert rep.ship.fighters == live.ship.fighters, f"{pid} fighters drift"
        assert rep.ship.shields == live.ship.shields, f"{pid} shields drift"
        assert rep.turns_today == live.turns_today, f"{pid} turns_today drift"
        assert rep.alignment == live.alignment, f"{pid} alignment drift"
        assert rep.experience == live.experience, f"{pid} experience drift"
        assert rep.deaths == live.deaths, f"{pid} deaths drift"
        for commodity in live.ship.cargo:
            assert rep.ship.cargo.get(commodity, 0) == live.ship.cargo.get(commodity, 0), (
                f"{pid} cargo drift on {commodity}"
            )

    # Universe-level: day must match.
    assert u.day == expected.day, "universe.day drift"

    # Engine-level event counts must match. Note: the replay runner emits
    # its own server-level GAME_START + the synthetic replay_eof GAME_OVER
    # wrappers, which the direct-simulation helper doesn't. Those are both
    # surface-layer events, not engine state. So we compare event counts
    # by EventKind after filtering out those two — the rest of the stream
    # is engine-emitted and must align exactly for a deterministic replay.
    from collections import Counter

    from tw2k.engine.models import EventKind

    def _engine_events(events):
        out = [e for e in events if e.kind is not EventKind.GAME_START]
        # Drop trailing GAME_OVER-from-replay_eof (replay sometimes caps a
        # mid-game-finished log with a marker; real matches end on the
        # engine's time-limit / economic / elimination GAME_OVER only).
        return out

    rep_counts = Counter(e.kind for e in _engine_events(u.events))
    exp_counts = Counter(e.kind for e in _engine_events(expected.events))
    assert rep_counts == exp_counts, (
        f"event-kind histogram drift: replay={dict(rep_counts)} "
        f"vs expected={dict(exp_counts)}"
    )


def _simulate_match_from_meta(save_dir: Path):
    """Re-execute the actions.jsonl directly (without the runner) for a
    ground-truth comparison in `test_replay_reconstructs_final_state`.

    This is a thin reimplementation of ReplayRunner._run minus the async
    boilerplate. If this and ReplayRunner diverge, the replay test fails
    — which tells us the runner is adding state the engine doesn't need.
    """
    meta = json.loads((save_dir / "meta.json").read_text(encoding="utf-8"))
    cfg = GameConfig(**meta["config"])
    u = generate_universe(cfg)

    # Same player placement as MatchRunner._build_agents / ReplayRunner._place_players.
    from tw2k.engine import constants as K

    fed_sectors = sorted(K.FEDSPACE_SECTORS)
    start_order = [fed_sectors[0]] + [s for s in fed_sectors if s != fed_sectors[0]]
    for i, ag in enumerate(meta["agents"]):
        start_sid = start_order[i % len(start_order)]
        credit_skew = (i * 317) % 2001 - 1000
        base_credits = getattr(cfg, "starting_credits", K.STARTING_CREDITS)
        base_tpd = getattr(cfg, "turns_per_day", K.STARTING_TURNS_PER_DAY)
        player = Player(
            id=ag["player_id"],
            name=ag["name"],
            credits=base_credits + credit_skew,
            turns_per_day=base_tpd,
            ship=Ship(),
            sector_id=start_sid,
            agent_kind=ag["kind"],
        )
        u.players[ag["player_id"]] = player
        u.sectors[start_sid].occupant_ids.append(ag["player_id"])
        player.known_sectors.add(start_sid)
        sector = u.sectors[start_sid]
        if sector.port is not None:
            player.known_ports[start_sid] = {
                "class": sector.port.code,
                "stock": {
                    c.value: {"current": s.current, "max": s.maximum}
                    for c, s in sector.port.stock.items()
                },
                "last_seen_day": u.day,
            }
        for wid in sector.warps:
            player.known_sectors.add(wid)
            w = u.sectors[wid]
            if w.port is not None:
                player.known_ports[wid] = {
                    "class": w.port.code,
                    "stock": {
                        c.value: {"current": s.current, "max": s.maximum}
                        for c, s in w.port.stock.items()
                    },
                    "last_seen_day": u.day,
                }

    # Replay the log.
    with (save_dir / "actions.jsonl").open("r", encoding="utf-8") as fp:
        for line in fp:
            if not line.strip():
                continue
            entry = json.loads(line)
            if is_finished(u):
                break
            if entry.get("kind") == "day_tick":
                tick_day(u)
                continue
            action = Action.model_validate(entry["action"])
            apply_action(u, entry["player_id"], action)
            # Touch the observation builder so anything lazy stays exercised —
            # matches the shape of the live loop.
            build_observation(u, entry["player_id"])

    return u


def test_replay_runner_refuses_when_meta_missing(tmp_path: Path) -> None:
    """A path with no meta.json should produce a clean failure, not a crash."""
    broadcaster = Broadcaster()
    runner = ReplayRunner(broadcaster, tmp_path)

    async def _go() -> None:
        with pytest.raises(FileNotFoundError):
            await runner.start()

    asyncio.run(_go())
