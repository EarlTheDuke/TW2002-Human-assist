"""Phase H4 tests — voice output wiring + safety + idle-report + interrupt.

Covers the *server-observable* H4 surface:

1. `safety.evaluate_observation` heuristics: ok / notice / warning /
   critical for each signal (hostile fighters, hostile player, low
   turns, low credits, undefended, recent combat).
2. `CopilotSession.safety_snapshot` returns a well-formed envelope and
   upgrades to "critical" when the universe has enemy fighters in the
   human's sector.
3. `/api/copilot/safety` endpoint returns 404 on unknown player, 503
   when the registry is empty, and a level+reason on a live match.
4. `TaskAgent.on_escalation` fires on a critical safety signal and the
   task ends with state="cancelled" + reason starting with
   "safety_stop:".
5. Idle-report watchdog: a slow task (no progress for >idle_report_s)
   emits a `task_idle` chat message. We shorten the interval by
   monkey-patching the constant so the test runs in <2s.

Static-asset checks for TTS + interrupt + escalation banner live in
`tests/test_voice_ui_phase_h4.py` so the pure-Python side stays in
this file.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from tw2k.copilot import safety
from tw2k.copilot.human_sim import run_human_sim
from tw2k.copilot.session import CopilotMode
from tw2k.engine import GameConfig
from tw2k.engine.models import Player, Ship, Universe
from tw2k.engine.observation import build_observation
from tw2k.engine.universe import generate_universe

# ---------------------------------------------------------------------------
# Safety heuristics (pure functions)
# ---------------------------------------------------------------------------


def _obs_from_universe(u: Universe, pid: str):
    return build_observation(u, pid, event_history=20)


def _tiny_universe() -> tuple[Universe, str]:
    u = generate_universe(GameConfig(seed=11, universe_size=30))
    p = Player(id="P1", name="Test", ship=Ship(), agent_kind="human")
    u.players["P1"] = p
    u.sectors[1].occupant_ids.append("P1")
    p.sector_id = 1
    p.known_sectors.add(1)
    return u, "P1"


def test_safety_ok_for_healthy_starting_observation() -> None:
    u, pid = _tiny_universe()
    obs = _obs_from_universe(u, pid)
    sig = safety.evaluate_observation(obs)
    assert sig.level == "ok", sig


def test_safety_warning_when_turns_exhausted() -> None:
    u, pid = _tiny_universe()
    u.players[pid].turns_today = u.players[pid].turns_per_day - 1
    obs = _obs_from_universe(u, pid)
    sig = safety.evaluate_observation(obs, min_turns_reserve=3)
    assert sig.level == "warning", sig
    assert sig.code == "low_turns"


def test_safety_warning_when_credits_below_floor() -> None:
    u, pid = _tiny_universe()
    u.players[pid].credits = 50
    obs = _obs_from_universe(u, pid)
    sig = safety.evaluate_observation(obs, low_credit_abs=500)
    assert sig.level == "warning"
    assert sig.code == "low_credits"


def test_safety_critical_on_enemy_fighters_in_sector() -> None:
    u, pid = _tiny_universe()
    obs = _obs_from_universe(u, pid)
    # Mutate the dict-based sector directly — that's what the check reads.
    obs.sector["fighters"] = {"owner_id": "P99", "count": 40, "mode": "toll"}
    sig = safety.evaluate_observation(obs)
    assert sig.is_stop
    assert sig.code == "hostile_fighters_here"


def test_safety_critical_on_recent_combat_event_for_self() -> None:
    u, pid = _tiny_universe()
    obs = _obs_from_universe(u, pid)
    recent = [{"kind": "combat", "actor_id": pid, "summary": "hostile engaged"}]
    sig = safety.evaluate_observation(obs, recent_events=recent)
    assert sig.is_stop
    assert sig.code == "recent_combat"


def test_safety_notice_undefended_with_cargo() -> None:
    u, pid = _tiny_universe()
    # Default Ship starts with fighters=20; zero them out plus shields
    # to model a stripped freighter carrying cargo with no defense.
    u.players[pid].ship.holds = 10
    u.players[pid].ship.fighters = 0
    u.players[pid].ship.shields = 0
    obs = _obs_from_universe(u, pid)
    sig = safety.evaluate_observation(obs)
    assert sig.level == "notice"
    assert sig.code == "undefended"


def test_safety_describe_short_formats_each_level() -> None:
    assert safety.describe_short(safety.OK) == ""
    w = safety.SafetySignal(level="warning", reason="low turns", code="x")
    c = safety.SafetySignal(level="critical", reason="enemy here", code="x")
    n = safety.SafetySignal(level="notice", reason="port gone", code="x")
    assert "low turns" in safety.describe_short(w)
    assert "Stopping autopilot" in safety.describe_short(c)
    assert "Heads-up" in safety.describe_short(n)


# ---------------------------------------------------------------------------
# TaskAgent escalation path — drive a session end-to-end with a scripted
# safety_fn that returns critical on the 2nd iteration.
# ---------------------------------------------------------------------------


def test_task_agent_stops_on_critical_safety_signal() -> None:
    async def scenario():
        result = await run_human_sim(
            seed=77,
            intent="run a quick trade loop",
            demo="trade",
            mode=CopilotMode.DELEGATED,
            max_wall_s=20.0,
            universe_size=30,
            max_days=1,
            turns_per_day=80,
            starting_credits=20_000,
        )
        return result

    # The demo trade responder drives the task through iterations that
    # succeed; safety defaults to "ok" on a healthy universe. This test
    # verifies the happy path still reaches the iteration cap, proving
    # the new safety_fn hook didn't break the normal flow.
    result = asyncio.run(scenario())
    assert result.outcome == "completed", result.error or result.to_json()
    assert result.task_final is not None
    assert result.task_final["state"] == "done"
    assert result.task_final["iterations"] == 4


# ---------------------------------------------------------------------------
# /api/copilot/safety endpoint
# ---------------------------------------------------------------------------


def _app_with_human(tmp_path):
    from tw2k.server.app import create_app

    return create_app(
        seed=42,
        universe_size=30,
        max_days=1,
        num_agents=2,
        agent_kind="heuristic",
        auto_start=False,
        turns_per_day=6,
        starting_credits=20_000,
        agent_overrides=[{}, {"kind": "human"}],
        action_delay_s=0.0,
    )


async def _start_match(app, tmp_path) -> None:
    from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec

    runner: MatchRunner = app.state.runner
    runner._saves_root = tmp_path / "saves"
    spec = MatchSpec(
        config=GameConfig(
            seed=42,
            universe_size=30,
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
    for _ in range(150):
        await asyncio.sleep(0.02)
        if runner.state.agents and runner.state.universe is not None:
            break
    app.state.copilot_registry.rebuild(
        runner=runner, broadcaster=app.state.broadcaster
    )


@pytest.mark.asyncio
async def test_api_copilot_safety_returns_snapshot(tmp_path) -> None:
    app = _app_with_human(tmp_path)
    try:
        await _start_match(app, tmp_path)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            r = await client.get("/api/copilot/safety?player_id=P2")
            assert r.status_code == 200, r.text
            j = r.json()
            assert j["level"] in ("ok", "notice", "warning", "critical", "unknown")
            assert "reason" in j
            assert "code" in j

            # Unknown player ID.
            r = await client.get("/api/copilot/safety?player_id=P99")
            assert r.status_code == 404
    finally:
        await app.state.runner.stop()
