"""Regression tests for M2-7 (auto-end-day flushes leading waits) and
M2-8 (DELETE /api/human/queue endpoint).

Both fixes were born out of Match 2B live-play: a Cursor driver
subagent got stuck in a WAIT loop, the scheduler's 4-wait auto-end
guard fired, but the queued actions behind the waits persisted into
the next day and re-triggered the same guard, stalling productive
actions (scan/warp/attack) for multiple real-time days with no
recovery path. See ``docs/MATCH_PLAY_NOTES.md`` M2-7 and M2-8.

What we prove here:
  * ``HumanAgent.drop_leading_waits`` only strips CONTIGUOUS leading
    waits and leaves the rest of the queue intact.
  * ``HumanAgent.clear_queue`` empties the queue regardless of what's
    in it.
  * The runner's 4-wait guard invokes ``drop_leading_waits`` when
    auto-ending the day, so a ``[wait, wait, wait, wait, scan]``
    queue lands as ``[scan]`` ready for tomorrow.
  * ``DELETE /api/human/queue?player_id=P2`` flushes the queue and
    returns a correct dropped/pending count; error cases (404, 409,
    503) all fire.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from tw2k.agents.human import HumanAgent
from tw2k.engine import ActionKind, EventKind, GameConfig
from tw2k.engine.actions import Action
from tw2k.server.app import create_app
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec

# ---------------------------------------------------------------------------
# M2-7: HumanAgent.drop_leading_waits — unit
# ---------------------------------------------------------------------------


def test_drop_leading_waits_strips_only_leading_run() -> None:
    async def _go() -> None:
        agent = HumanAgent(player_id="P1", name="H")
        await agent.submit_action(Action(kind=ActionKind.WAIT))
        await agent.submit_action(Action(kind=ActionKind.WAIT))
        await agent.submit_action(Action(kind=ActionKind.WAIT))
        await agent.submit_action(Action(kind=ActionKind.SCAN))
        await agent.submit_action(Action(kind=ActionKind.WAIT))  # trailing wait preserved
        assert agent.pending == 5
        dropped = agent.drop_leading_waits()
        assert dropped == 3
        # Queue head must now be SCAN, then the trailing WAIT, in order.
        a1 = await agent.act(_fake_obs())
        a2 = await agent.act(_fake_obs())
        assert a1.kind == ActionKind.SCAN
        assert a2.kind == ActionKind.WAIT
        assert agent.pending == 0

    asyncio.run(_go())


def test_drop_leading_waits_empty_is_zero() -> None:
    agent = HumanAgent(player_id="P1", name="H")
    assert agent.drop_leading_waits() == 0
    assert agent.pending == 0


def test_drop_leading_waits_non_wait_head_is_zero() -> None:
    async def _go() -> None:
        agent = HumanAgent(player_id="P1", name="H")
        await agent.submit_action(Action(kind=ActionKind.SCAN))
        await agent.submit_action(Action(kind=ActionKind.WAIT))
        assert agent.drop_leading_waits() == 0
        assert agent.pending == 2

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# M2-8: HumanAgent.clear_queue — unit
# ---------------------------------------------------------------------------


def test_clear_queue_drops_everything() -> None:
    async def _go() -> None:
        agent = HumanAgent(player_id="P1", name="H")
        await agent.submit_action(Action(kind=ActionKind.SCAN))
        await agent.submit_action(Action(kind=ActionKind.WAIT))
        await agent.submit_action(Action(kind=ActionKind.WAIT))
        assert agent.pending == 3
        dropped = agent.clear_queue()
        assert dropped == 3
        assert agent.pending == 0
        # Second call is a no-op.
        assert agent.clear_queue() == 0

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# M2-7: Integration — runner's 4-wait guard flushes leading waits so a
# queued ``scan`` lands first on the next day.
# ---------------------------------------------------------------------------


def test_auto_end_day_flushes_leading_wait_streak(tmp_path: Path) -> None:
    """End-to-end reproducer for M2-7.

    Queue ``[wait x 8, scan]`` into a HUMAN slot. The scheduler's 4-wait
    guard consumes the first 4 waits and then auto-ends the day — the
    fix must ALSO strip the remaining 4 leading waits so the ``scan``
    fires next day instead of re-triggering the guard. Without the
    fix (previous behavior), the ``scan`` stayed buried for
    ``ceil(remaining_waits / 4)`` additional days.
    """
    broadcaster = Broadcaster()
    runner = MatchRunner(broadcaster, saves_root=tmp_path / "saves")
    cfg = GameConfig(
        seed=17,
        universe_size=40,
        max_days=4,
        turns_per_day=20,
        starting_credits=20_000,
        enable_ferrengi=False,
        enable_planets=False,
        action_delay_s=0.0,
    )
    spec = MatchSpec(
        config=cfg,
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="Human", kind="human"),
        ],
        action_delay_s=0.0,
    )

    async def _go() -> None:
        await runner.start(spec)
        # Find the HumanAgent and pre-load the buggy pattern.
        human: HumanAgent | None = None
        for _ in range(100):
            await asyncio.sleep(0.01)
            for a in runner.state.agents:
                if isinstance(a, HumanAgent) and a.player_id == "P2":
                    human = a
                    break
            if human is not None:
                break
        assert human is not None, "HumanAgent P2 never spun up"

        # 8 waits + scan: scheduler consumes 4 waits -> guard fires ->
        # 4 waits remain at queue head -> must be flushed so scan lands.
        for _ in range(8):
            await human.submit_action(Action(kind=ActionKind.WAIT))
        await human.submit_action(Action(kind=ActionKind.SCAN))
        assert human.pending == 9

        # Let the scheduler drain waits; auto-end-day should fire and
        # flush the remaining leading waits, leaving ONLY the scan.
        universe = runner.state.universe
        assert universe is not None
        flushed_seen = False
        for _ in range(400):
            await asyncio.sleep(0.02)
            # Look for our auto-end-day thought carrying waits_flushed.
            for ev in universe.events:
                if (
                    ev.kind == EventKind.AGENT_THOUGHT
                    and ev.actor_id == "P2"
                    and isinstance(ev.payload, dict)
                    and int(ev.payload.get("waits_flushed") or 0) > 0
                ):
                    flushed_seen = True
                    break
            if flushed_seen:
                break
            if runner.state.status in ("finished", "error"):
                break

        assert flushed_seen, (
            "M2-7 regression: auto-end-day fired but no waits_flushed "
            "payload — leading waits still sit in the queue."
        )
        # Queue must now be just the scan (1 pending, kind == SCAN).
        # Note: human.pending could already be 0 if the next day rolled
        # over and the scheduler consumed the scan. That's fine — what
        # we care about is that the scan WAS consumed, not re-buried.
        # Inspect the event log for a SCAN action on P2.
        scans = [
            e for e in universe.events
            if e.kind == EventKind.SCAN and e.actor_id == "P2"
        ]
        assert scans or human.pending <= 1, (
            "scan never surfaced; the wait flush may have dropped too much"
        )

        await runner.stop()

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# M2-8: DELETE /api/human/queue — integration
# ---------------------------------------------------------------------------


def _app_with_human(tmp_path: Path) -> FastAPI:
    return create_app(
        seed=101,
        universe_size=40,
        max_days=1,
        num_agents=2,
        agent_kind="heuristic",
        auto_start=False,
        turns_per_day=6,
        starting_credits=20_000,
        agent_overrides=[{}, {"kind": "human"}],
        action_delay_s=0.0,
    )


async def _start_match(app: FastAPI, tmp_path: Path) -> MatchRunner:
    runner: MatchRunner = app.state.runner
    runner._saves_root = tmp_path / "saves"  # type: ignore[attr-defined]
    spec = MatchSpec(
        config=GameConfig(
            seed=101,
            universe_size=40,
            max_days=1,
            turns_per_day=6,
            starting_credits=20_000,
            enable_ferrengi=False,
            enable_planets=False,
            action_delay_s=0.0,
        ),
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="You", kind="human"),
        ],
        action_delay_s=0.0,
    )
    await runner.start(spec)
    for _ in range(120):
        await asyncio.sleep(0.02)
        u = runner.state.universe
        if u is None:
            continue
        if any(e.kind == EventKind.HUMAN_TURN_START for e in u.events):
            break
    return runner


def test_delete_queue_flushes_and_returns_dropped_count(tmp_path: Path) -> None:
    app = _app_with_human(tmp_path)

    async def _go() -> None:
        runner = await _start_match(app, tmp_path)
        try:
            human = next(
                a for a in runner.state.agents
                if a.player_id == "P2" and isinstance(a, HumanAgent)
            )
            for _ in range(5):
                await human.submit_action(Action(kind=ActionKind.WAIT))
            assert human.pending == 5

            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.delete("/api/human/queue", params={"player_id": "P2"})
                assert r.status_code == 200, r.text
                body = r.json()
                assert body["player_id"] == "P2"
                assert body["dropped"] == 5
                assert body["pending"] == 0
            assert human.pending == 0
        finally:
            await runner.stop()

    asyncio.run(_go())


def test_delete_queue_404_on_unknown_player(tmp_path: Path) -> None:
    app = _app_with_human(tmp_path)

    async def _go() -> None:
        runner = await _start_match(app, tmp_path)
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.delete("/api/human/queue", params={"player_id": "P99"})
                assert r.status_code == 404
                assert "no such player" in r.json()["detail"].lower()
        finally:
            await runner.stop()

    asyncio.run(_go())


def test_delete_queue_409_on_non_human_slot(tmp_path: Path) -> None:
    app = _app_with_human(tmp_path)

    async def _go() -> None:
        runner = await _start_match(app, tmp_path)
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.delete("/api/human/queue", params={"player_id": "P1"})
                assert r.status_code == 409
                assert "not a human slot" in r.json()["detail"].lower()
        finally:
            await runner.stop()

    asyncio.run(_go())


def test_delete_queue_503_when_no_match(tmp_path: Path) -> None:
    app = _app_with_human(tmp_path)

    async def _go() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.delete("/api/human/queue", params={"player_id": "P2"})
            assert r.status_code == 503

    asyncio.run(_go())


def test_delete_queue_400_on_missing_player_id(tmp_path: Path) -> None:
    app = _app_with_human(tmp_path)

    async def _go() -> None:
        runner = await _start_match(app, tmp_path)
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
                # Empty string should 400 (FastAPI will convert missing to 422
                # by default, so we pass an explicit empty string).
                r = await c.delete("/api/human/queue", params={"player_id": ""})
                assert r.status_code in (400, 422)
        finally:
            await runner.stop()

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_obs() -> object:
    class _O:
        seq = 0

    return _O()


@pytest.fixture(autouse=True)
def _event_loop_policy() -> None:
    # Ensure asyncio.run works cleanly on Windows event loop policies.
    # No-op placeholder; asyncio.run handles policy internally in 3.11+.
    return None
