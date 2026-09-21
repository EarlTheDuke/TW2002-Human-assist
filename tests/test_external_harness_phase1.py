"""Phase 1 tests — external (Grok Bot) seats.

Plan: docs/plans/2026-09-20-external-harness.md §5. Numbering below follows
the plan so Commander can tick acceptance criteria against it.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from tw2k.agents.external import (
    ExternalAgent,
    NotYourTurnError,
    QueueFullError,
    StaleTurnError,
)
from tw2k.engine import ActionKind, GameConfig, PlayerKind, generate_universe
from tw2k.engine.actions import Action
from tw2k.engine.models import EventKind as EK
from tw2k.engine.models import Player
from tw2k.server import harness_tokens as ht
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec


def _fake_obs():
    """Minimal duck-typed observation; ExternalAgent only stores it."""

    class _Obs:
        seq = 0

    return _Obs()


# ---------------------------------------------------------------------------
# 1. PlayerKind + actor_kind
# ---------------------------------------------------------------------------


def test_01_player_kind_external_round_trips_and_tags_events() -> None:
    assert PlayerKind("external") is PlayerKind.EXTERNAL
    cfg = GameConfig(seed=1, universe_size=40, max_days=2, turns_per_day=10)
    u = generate_universe(cfg)
    u.players["P3"] = Player(id="P3", name="GrokBot", agent_kind="external")
    ev = u.emit(EK.AGENT_THOUGHT, actor_id="P3", payload={"thought": "hi"})
    assert ev.actor_kind == "external"


# ---------------------------------------------------------------------------
# 2–5. ExternalAgent turn protocol
# ---------------------------------------------------------------------------


def test_02_act_blocks_until_submit_and_turn_seq_increments() -> None:
    async def _go() -> None:
        agent = ExternalAgent("P3", "GrokBot", token="t")
        assert agent.turn_seq == 0 and not agent.awaiting_input

        task = asyncio.create_task(agent.act(_fake_obs()))
        await asyncio.sleep(0.02)
        assert not task.done()
        assert agent.awaiting_input and agent.turn_seq == 1

        bound = await agent.submit_action(Action(kind=ActionKind.SCAN), turn_seq=1)
        assert bound == 1
        got = await asyncio.wait_for(task, timeout=1.0)
        assert got.kind == ActionKind.SCAN
        assert not agent.awaiting_input

        task2 = asyncio.create_task(agent.act(_fake_obs()))
        await asyncio.sleep(0.02)
        assert agent.turn_seq == 2
        await agent.submit_action(Action(kind=ActionKind.WAIT))  # turn_seq omitted is OK
        await asyncio.wait_for(task2, timeout=1.0)

    asyncio.run(_go())


def test_03_stale_not_your_turn_and_queue_full() -> None:
    async def _go() -> None:
        agent = ExternalAgent("P3", "GrokBot")
        with pytest.raises(NotYourTurnError):
            await agent.submit_action(Action(kind=ActionKind.WAIT))

        task = asyncio.create_task(agent.act(_fake_obs()))
        await asyncio.sleep(0.02)
        with pytest.raises(StaleTurnError) as ei:
            await agent.submit_action(Action(kind=ActionKind.WAIT), turn_seq=0)
        assert ei.value.current == 1 and ei.value.submitted == 0

        # First accepted, second for the same turn is rejected. Hold the
        # scheduler side so the queue stays full.
        agent._queue = asyncio.Queue(maxsize=1)  # fresh queue not yet awaited
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        # Re-enter a turn, then fill it without draining.
        agent.awaiting_input = True
        agent.turn_seq = 5
        await agent.submit_action(Action(kind=ActionKind.WAIT), turn_seq=5)
        with pytest.raises(QueueFullError):
            await agent.submit_action(Action(kind=ActionKind.WAIT), turn_seq=5)

    asyncio.run(_go())


def test_04_wait_for_turn_long_poll() -> None:
    async def _go() -> None:
        agent = ExternalAgent("P3", "GrokBot")
        assert await agent.wait_for_turn(0.05) is False

        waiter = asyncio.create_task(agent.wait_for_turn(2.0))
        await asyncio.sleep(0.02)
        act_task = asyncio.create_task(agent.act(_fake_obs()))
        assert await asyncio.wait_for(waiter, timeout=1.0) is True
        await agent.submit_action(Action(kind=ActionKind.WAIT))
        await act_task

    asyncio.run(_go())


def test_05_record_result_and_actor_kind_stripped() -> None:
    async def _go() -> None:
        agent = ExternalAgent("P3", "GrokBot")
        task = asyncio.create_task(agent.act(_fake_obs()))
        await asyncio.sleep(0.02)
        a = Action(kind=ActionKind.WAIT, actor_kind="copilot")
        await agent.submit_action(a)
        got = await task
        assert got.actor_kind is None
        agent.record_result(False, "out of turns", [7, 8])
        st = agent.status()
        assert st["last_result"]["ok"] is False
        assert st["last_result"]["error"] == "out of turns"
        assert st["last_result"]["event_seqs"] == [7, 8]
        assert st["last_result"]["turn_seq"] == 1

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# 6. Token resolution
# ---------------------------------------------------------------------------


def test_06_token_resolution_order_and_persistence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tokens_file = tmp_path / "tok.json"
    tokens_file.write_text(json.dumps({"P4": "file-token-4444444444"}), encoding="utf-8")
    monkeypatch.setenv("TW2K_EXTERNAL_TOKEN_P5", "env-token-5555555555")
    monkeypatch.delenv("TW2K_EXTERNAL_TOKEN_P3", raising=False)

    out = ht.resolve_seat_tokens(
        {"P3": "explicit-333333333333", "P4": None, "P5": None, "P6": None},
        tokens_file=tokens_file,
    )
    assert out["P3"] == "explicit-333333333333"
    assert out["P4"] == "file-token-4444444444"
    assert out["P5"] == "env-token-5555555555"
    assert len(out["P6"]) >= 32  # generated

    on_disk = json.loads(tokens_file.read_text(encoding="utf-8"))
    # Only the generated one is persisted; explicit/env never leak into the file.
    assert set(on_disk) == {"P4", "P6"}
    assert on_disk["P6"] == out["P6"]

    # Second resolve reuses the persisted token (stable across restarts).
    again = ht.resolve_seat_tokens({"P6": None}, tokens_file=tokens_file)
    assert again["P6"] == out["P6"]

    m = ht.mask(out["P6"])
    assert "…" in m and len(m) == 9
    assert ht.verify(out["P6"], out["P6"]) and not ht.verify("x", out["P6"]) and not ht.verify("", "")


def test_06b_gitignore_covers_tokens() -> None:
    gi = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert ".tw2k/" in gi
    assert "*external_tokens*.json" in gi


# ---------------------------------------------------------------------------
# 7–9. Runner integration
# ---------------------------------------------------------------------------


def _tiny_spec(*, external_timeout_s: float = 30.0, seed: int = 42) -> MatchSpec:
    cfg = GameConfig(
        seed=seed,
        universe_size=60,
        max_days=2,
        turns_per_day=12,
        starting_credits=25_000,
        enable_ferrengi=False,
        enable_planets=False,
        action_delay_s=0.0,
    )
    return MatchSpec(
        config=cfg,
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(
                player_id="P2", name="GrokBot", kind="external", external_token="secret-token-2222222222"
            ),
        ],
        action_delay_s=0.0,
        external_timeout_s=external_timeout_s,
    )


async def _wait_until(pred, *, tries: int = 150, dt: float = 0.02) -> bool:
    for _ in range(tries):
        if pred():
            return True
        await asyncio.sleep(dt)
    return pred()


def test_07_scheduler_blocks_on_external_seat_and_applies_submitted_warp(tmp_path: Path) -> None:
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")

    async def _go() -> None:
        await runner.start(_tiny_spec())
        ext = None

        def _ready() -> bool:
            nonlocal ext
            if not runner.state.agents:
                return False
            ext = next(a for a in runner.state.agents if a.player_id == "P2")
            return bool(getattr(ext, "awaiting_input", False))

        assert await _wait_until(_ready), "scheduler never reached the external seat"
        assert isinstance(ext, ExternalAgent)
        assert ext.token == "secret-token-2222222222"
        u = runner.state.universe
        assert u is not None
        p2 = u.players["P2"]
        assert p2.agent_kind == "external"
        start_sector = p2.sector_id
        obs = ext.current_observation
        assert obs is not None and obs.self_id == "P2"
        target = obs.sector["warps_out"][0]

        await ext.submit_action(Action(kind=ActionKind.WARP, args={"target": target}), turn_seq=ext.turn_seq)
        assert await _wait_until(lambda: p2.sector_id == target), "warp not applied"
        assert p2.sector_id != start_sector
        assert await _wait_until(lambda: ext.last_result is not None and ext.last_result["ok"])
        warp_events = [e for e in u.events if e.kind == EK.WARP and e.actor_id == "P2"]
        assert warp_events and warp_events[0].actor_kind == "external"
        await runner.stop()

    asyncio.run(_go())


def test_08_timeout_applies_wait_emits_agent_error_and_streak_ends_day(tmp_path: Path) -> None:
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")

    async def _go() -> None:
        await runner.start(_tiny_spec(external_timeout_s=0.15))
        u = None

        def _errors() -> list:
            nonlocal u
            u = runner.state.universe
            if u is None:
                return []
            return [
                e
                for e in u.events
                if e.kind == EK.AGENT_ERROR and e.actor_id == "P2" and e.payload.get("external_timeout")
            ]

        assert await _wait_until(lambda: len(_errors()) >= 4, tries=400, dt=0.03)
        assert u is not None

        # Four consecutive timeout-WAITs trip the streak guard -> "ends the
        # day early" thought with turns_skipped. (turns_today itself resets
        # as soon as the day ticks, so assert on the event, not the counter.)
        def _day_ended() -> bool:
            return any(
                e.kind == EK.AGENT_THOUGHT
                and e.actor_id == "P2"
                and e.payload.get("turns_skipped") is not None
                for e in u.events
            )

        assert await _wait_until(_day_ended, tries=300, dt=0.03)
        ext = next(a for a in runner.state.agents if a.player_id == "P2")
        assert isinstance(ext, ExternalAgent)
        assert ext.last_result is not None and ext.last_result["ok"] is True  # WAIT applied fine
        await runner.stop()

    asyncio.run(_go())


def test_09_meta_json_records_kind_but_never_token(tmp_path: Path) -> None:
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")

    async def _go() -> None:
        await runner.start(_tiny_spec())
        assert await _wait_until(lambda: runner.state.save_dir is not None and runner.state.universe is not None)
        await runner.stop()

    asyncio.run(_go())
    save_dir = runner.state.save_dir
    assert save_dir is not None
    meta_text = (save_dir / "meta.json").read_text(encoding="utf-8")
    meta = json.loads(meta_text)
    kinds = {a["player_id"]: a["kind"] for a in meta["agents"]}
    assert kinds["P2"] == "external"
    assert "secret-token-2222222222" not in meta_text
    assert not any("token" in k.lower() for a in meta["agents"] for k in a)
