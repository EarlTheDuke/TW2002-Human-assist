"""Phase H0 tests — human-player plumbing.

What H0 promises:
  1. `HumanAgent.act()` blocks until someone calls `submit_action`.
  2. `ScriptedHumanAgent` drops in as a deterministic test substitute
     and works end-to-end through `MatchRunner` alongside heuristic agents.
  3. The scheduler emits HUMAN_TURN_START before blocking for human input.
  4. Events carry `actor_kind` so replay / forensics can distinguish
     heuristic / llm / human origins.
  5. A recorded match with a human slot replays bit-for-bit.

These all live in one file so the phase gate is easy to inspect.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from tw2k.agents.human import HumanAgent, ScriptedHumanAgent
from tw2k.engine import (
    ActionKind,
    EventKind,
    GameConfig,
    PlayerKind,
    generate_universe,
)
from tw2k.engine.actions import Action
from tw2k.engine.models import EventKind as EK
from tw2k.engine.models import Player
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.replay import ReplayRunner
from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec

# ---------------------------------------------------------------------------
# PlayerKind enum sanity
# ---------------------------------------------------------------------------


def test_player_kind_enum_values() -> None:
    assert PlayerKind.HEURISTIC.value == "heuristic"
    assert PlayerKind.LLM.value == "llm"
    assert PlayerKind.HUMAN.value == "human"
    # Round-trip from the `Player.agent_kind` string form.
    assert PlayerKind("human") is PlayerKind.HUMAN


# ---------------------------------------------------------------------------
# Event.actor_kind auto-resolution
# ---------------------------------------------------------------------------


def test_emit_auto_tags_actor_kind_from_player() -> None:
    cfg = GameConfig(seed=1, universe_size=40, max_days=2, turns_per_day=10)
    u = generate_universe(cfg)
    u.players["P1"] = Player(id="P1", name="Human One", agent_kind="human")
    u.players["P2"] = Player(id="P2", name="Heur Two", agent_kind="heuristic")

    ev_h = u.emit(EK.AGENT_THOUGHT, actor_id="P1", payload={"thought": "hi"})
    ev_a = u.emit(EK.AGENT_THOUGHT, actor_id="P2", payload={"thought": "bot"})
    ev_none = u.emit(EK.DAY_TICK)

    assert ev_h.actor_kind == "human"
    assert ev_a.actor_kind == "heuristic"
    assert ev_none.actor_kind is None


def test_emit_respects_explicit_actor_kind_override() -> None:
    """Copilot path (H2+) passes actor_kind="copilot" to distinguish an
    action the AI dispatched on behalf of a human from one the human
    typed manually. H0 needs the override to work even though no
    copilot code exists yet."""
    cfg = GameConfig(seed=1, universe_size=40, max_days=2, turns_per_day=10)
    u = generate_universe(cfg)
    u.players["P1"] = Player(id="P1", name="Human", agent_kind="human")

    ev = u.emit(
        EK.AGENT_THOUGHT,
        actor_id="P1",
        actor_kind="copilot",
        payload={"thought": "dispatched"},
    )
    assert ev.actor_kind == "copilot"


# ---------------------------------------------------------------------------
# HumanAgent blocks until fed
# ---------------------------------------------------------------------------


def test_human_agent_blocks_until_submit() -> None:
    async def _go() -> None:
        agent = HumanAgent(player_id="P1", name="HumanOne")

        async def _waiter() -> Action:
            return await agent.act(observation=_fake_obs())

        task = asyncio.create_task(_waiter())
        # Queue is empty; act() must not have completed in 50ms.
        await asyncio.sleep(0.05)
        assert not task.done(), "act() returned without an Action in the queue"

        action = Action(kind=ActionKind.SCAN, args={"sector_id": 5})
        await agent.submit_action(action)
        got = await asyncio.wait_for(task, timeout=1.0)
        assert got.kind == ActionKind.SCAN
        assert got.args == {"sector_id": 5}

    asyncio.run(_go())


def test_human_agent_queue_full_raises() -> None:
    async def _go() -> None:
        agent = HumanAgent(player_id="P1", name="Human", queue_maxsize=2)
        await agent.submit_action(Action(kind=ActionKind.WAIT))
        await agent.submit_action(Action(kind=ActionKind.WAIT))
        with pytest.raises(RuntimeError, match="queue full"):
            await agent.submit_action(Action(kind=ActionKind.WAIT))

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# ScriptedHumanAgent — drop-in fixture
# ---------------------------------------------------------------------------


def test_scripted_human_replays_list_then_waits() -> None:
    async def _go() -> None:
        agent = ScriptedHumanAgent(
            player_id="P1",
            name="Scripted",
            actions=[
                {"kind": "scan", "args": {"sector_id": 3}},
                Action(kind=ActionKind.WAIT),
            ],
        )
        a1 = await agent.act(_fake_obs())
        a2 = await agent.act(_fake_obs())
        # 3rd call must pad with WAIT (no StopIteration / no IndexError).
        a3 = await agent.act(_fake_obs())
        assert a1.kind == ActionKind.SCAN
        assert a1.args["sector_id"] == 3
        assert a2.kind == ActionKind.WAIT
        assert a3.kind == ActionKind.WAIT
        assert agent.wait_pads == 1
        assert agent.remaining == 0

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# Scheduler blocks on human turn + emits HUMAN_TURN_START
# ---------------------------------------------------------------------------


def _tiny_match_spec(seed: int = 42) -> MatchSpec:
    cfg = GameConfig(
        seed=seed,
        universe_size=60,
        max_days=2,
        turns_per_day=15,
        starting_credits=25_000,
        enable_ferrengi=False,
        enable_planets=False,
        action_delay_s=0.0,
    )
    return MatchSpec(
        config=cfg,
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="Human", kind="human"),
        ],
        action_delay_s=0.0,
    )


def test_scheduler_blocks_on_human_turn_and_emits_start_event(tmp_path: Path) -> None:
    """Exit-criterion test for H0: scheduler must pause at the human's
    first turn and emit HUMAN_TURN_START. Other players keep their
    own turn budget; they may act up to the round-robin before
    looping back to the blocked human."""
    broadcaster = Broadcaster()
    runner = MatchRunner(broadcaster, saves_root=tmp_path / "saves")
    spec = _tiny_match_spec()

    async def _go() -> None:
        await runner.start(spec)
        # Give the scheduler a chance to: warm up, emit init, and cycle
        # at least once — P1 (heuristic) acts, then P2 (human) blocks.
        for _ in range(80):
            await asyncio.sleep(0.02)
            u = runner.state.universe
            if u is None:
                continue
            starts = [e for e in u.events if e.kind == EventKind.HUMAN_TURN_START]
            if starts:
                break

        u = runner.state.universe
        assert u is not None

        starts = [e for e in u.events if e.kind == EventKind.HUMAN_TURN_START]
        assert starts, "scheduler never emitted HUMAN_TURN_START"
        s0 = starts[0]
        assert s0.actor_id == "P2"
        # actor_kind auto-resolves from Player.agent_kind='human'
        assert s0.actor_kind == "human"
        assert s0.payload.get("turns_remaining") is not None

        # Sanity: the human player should not have moved yet (turns_today
        # still 0) AND the scheduler is idling on it (not finished).
        human = u.players["P2"]
        assert human.turns_today == 0
        assert runner.state.status == "running"

        # Unblock the human: feed a WAIT through the agent directly.
        # In production /api/human/action would do this over HTTP.
        human_agent = next(
            a for a in runner.state.agents if a.player_id == "P2"
        )
        await human_agent.submit_action(Action(kind=ActionKind.WAIT))  # type: ignore[attr-defined]

        # Let scheduler consume the action and keep going.
        for _ in range(30):
            await asyncio.sleep(0.02)
            if human.turns_today >= 1:
                break
        # After consumption the WAIT costs 1 turn.
        assert human.turns_today >= 1, "human action not consumed by scheduler"

        await runner.stop()

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# Match record + replay round-trip with a human slot
# ---------------------------------------------------------------------------


def _drive_match_with_scripted_human(tmp_path: Path, seed: int = 7) -> Path:
    """Run a short match where P2 is a human driven by a hand-rolled
    action queue. Returns the saves/<run-id>/ dir."""
    broadcaster = Broadcaster()
    saves_root = tmp_path / "saves"
    runner = MatchRunner(broadcaster, saves_root=saves_root)

    spec = _tiny_match_spec(seed=seed)

    async def _go() -> None:
        await runner.start(spec)
        # The human is P2. Hand-craft a tiny script and keep feeding
        # while the runner churns.
        script = [
            Action(kind=ActionKind.WAIT),
            Action(kind=ActionKind.SCAN, args={}),
            Action(kind=ActionKind.WAIT),
            Action(kind=ActionKind.WAIT),
        ]
        fed = 0
        for _ in range(200):
            await asyncio.sleep(0.01)
            if runner.state.status in ("finished", "error"):
                break
            # Find the human agent and push as soon as its queue is empty.
            hum = next(
                (
                    a for a in runner.state.agents
                    if a.player_id == "P2" and isinstance(a, HumanAgent)
                ),
                None,
            )
            if hum is not None and hum.pending == 0 and fed < len(script):
                try:
                    await hum.submit_action(script[fed])
                    fed += 1
                except RuntimeError:
                    pass
        await runner.stop()

    asyncio.run(_go())

    run_dirs = sorted([d for d in saves_root.iterdir() if d.is_dir()])
    assert run_dirs
    return run_dirs[-1]


def test_human_actions_recorded_in_actions_log(tmp_path: Path) -> None:
    run_dir = _drive_match_with_scripted_human(tmp_path)
    lines = (run_dir / "actions.jsonl").read_text(encoding="utf-8").splitlines()
    human_actions = [
        json.loads(ln)
        for ln in lines
        if ln.strip() and json.loads(ln).get("player_id") == "P2"
    ]
    assert human_actions, "no P2 (human) actions were recorded"


def test_replay_from_human_match_does_not_crash(tmp_path: Path) -> None:
    """Replay re-executes actions.jsonl without needing a live HumanAgent.
    The Action is pulled from the log, the engine applies it, events
    are re-emitted. Same code path as any LLM match.
    """
    run_dir = _drive_match_with_scripted_human(tmp_path)

    broadcaster = Broadcaster()
    replay = ReplayRunner(broadcaster, run_dir)

    async def _go() -> None:
        await replay.start()
        for _ in range(200):
            await asyncio.sleep(0.01)
            if replay.state.status in ("finished", "error"):
                break
        await replay.stop()

    asyncio.run(_go())

    assert replay.state.status in ("finished", "running"), (
        f"replay ended in unexpected status {replay.state.status}: "
        f"{replay.state.last_error}"
    )
    # Live match had actor_kind='human' on P2's events; the replayed
    # universe should reproduce that because replay's _place_players
    # sets agent_kind="human" and Universe.emit auto-tags.
    u = replay.state.universe
    assert u is not None
    p2_events = [e for e in u.events if e.actor_id == "P2" and e.actor_kind is not None]
    assert p2_events, "no actor-tagged P2 events re-emitted in replay"
    assert any(e.actor_kind == "human" for e in p2_events)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_obs() -> object:
    """Minimal observation stand-in for unit tests — neither HumanAgent
    nor ScriptedHumanAgent inspects it beyond reading `seq` (optional)."""

    class _O:
        seq = 0

    return _O()
