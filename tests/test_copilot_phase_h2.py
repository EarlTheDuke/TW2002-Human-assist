"""Phase H2 tests — text copilot (advisory + delegated + autopilot).

Exercises the pieces promised by docs/HUMAN_COPILOT_PLAN.md §12:
  1. Tool catalog + cross-provider schema adapters.
  2. Standing-order evaluator (min credit, no-warp, max haggle).
  3. ChatAgent envelope parsing for every envelope shape.
  4. CopilotSession mode toggle, plan confirm/cancel, actor_kind tagging.
  5. TaskAgent end-to-end trade loop against a scripted mock provider
     (the H2 exit-criterion demo: "run my trade loop until 30k cr").
  6. Esc / cancel_active_task halts a running TaskAgent mid-flight.
  7. Pure AI-only matches don't create copilot sessions and their
     action events never leak an `actor_kind="copilot"` tag.

Every test drives the FastAPI app through httpx.ASGITransport so nothing
binds a real port, and uses the `mock:` provider tag so zero API keys
are needed.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tw2k.copilot import (
    TOOL_CATALOG,
    CopilotMode,
    CopilotSession,
    StandingOrder,
    StandingOrderKind,
    ToolCall,
)
from tw2k.copilot import standing_orders as so
from tw2k.copilot.chat_agent import ChatAgent
from tw2k.copilot.provider import (
    clear_mock_responders,
    parse_tool_response,
    register_mock_responder,
)
from tw2k.copilot.task_agent import TaskAgent, TaskContext, TaskStatus
from tw2k.copilot.tools import tool_schema_for_provider
from tw2k.engine import ActionKind, EventKind, GameConfig
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec

# ---------------------------------------------------------------------------
# Tool catalog + adapter tests
# ---------------------------------------------------------------------------


def test_tool_catalog_every_entry_has_required_fields() -> None:
    for name, spec in TOOL_CATALOG.items():
        assert spec.name == name
        assert spec.group in {
            "action",
            "planning",
            "dialog",
            "orchestration",
            "observability",
        }
        assert isinstance(spec.description, str) and spec.description
        assert spec.parameters["type"] == "object"
        if spec.group == "action":
            assert spec.engine_action, f"action tool {name} missing engine_action"


def test_tool_schema_openai_shape() -> None:
    openai_tools = tool_schema_for_provider("openai")
    # OpenAI-compatible shape nests function under "function".
    assert all(t["type"] == "function" for t in openai_tools)
    by_name = {t["function"]["name"]: t for t in openai_tools}
    assert "warp" in by_name
    assert "parameters" in by_name["warp"]["function"]


def test_tool_schema_anthropic_shape() -> None:
    anth_tools = tool_schema_for_provider("anthropic")
    # Anthropic uses input_schema at the top level (no "function" wrapper).
    assert all("input_schema" in t for t in anth_tools)
    assert all("name" in t and "description" in t for t in anth_tools)
    names = {t["name"] for t in anth_tools}
    assert {"warp", "buy", "sell", "start_task", "speak"} <= names


def test_toolcall_validation_catches_unknown_tool_and_missing_args() -> None:
    tc = ToolCall(name="does_not_exist", arguments={})
    assert tc.validate_against_catalog() is not None

    # warp requires `target`.
    tc2 = ToolCall(name="warp", arguments={})
    err = tc2.validate_against_catalog()
    assert err is not None and "target" in err

    # unknown arg.
    tc3 = ToolCall(name="warp", arguments={"target": 1, "bogus": 2})
    err = tc3.validate_against_catalog()
    assert err is not None and "bogus" in err


# ---------------------------------------------------------------------------
# Provider: JSON envelope parsing
# ---------------------------------------------------------------------------


def test_parse_tool_response_accepts_single_action_envelope() -> None:
    raw = '{"tool": "warp", "arguments": {"target": 874}, "thought": "go east"}'
    out = parse_tool_response(raw)
    assert len(out) == 1
    assert out[0].name == "warp"
    assert out[0].arguments == {"target": 874}
    assert out[0].thought == "go east"


def test_parse_tool_response_accepts_multi_step_plan() -> None:
    raw = (
        '{"plan": ['
        '{"tool": "warp", "arguments": {"target": 3}},'
        '{"tool": "sell", "arguments": {"commodity": "fuel_ore", "qty": 10}}'
        '], "thought": "round trip"}'
    )
    out = parse_tool_response(raw)
    assert [c.name for c in out] == ["warp", "sell"]
    # Outer thought fans down when no per-call thought given.
    assert all("round trip" in c.thought for c in out)


def test_parse_tool_response_strips_markdown_fences_and_prose() -> None:
    raw = (
        "Here's what I'd do:\n"
        "```json\n"
        '{"tool": "scan", "arguments": {}}\n'
        "```"
    )
    out = parse_tool_response(raw)
    assert len(out) == 1 and out[0].name == "scan"


def test_parse_tool_response_empty_on_garbage() -> None:
    assert parse_tool_response("") == []
    assert parse_tool_response("not json at all") == []


# ---------------------------------------------------------------------------
# Standing orders
# ---------------------------------------------------------------------------


def _tiny_universe_with_port(credits: int = 10_000):
    """Spin up a minimal Universe with a port in sector 1 so standing-order
    checks can look up port prices without spinning up the full match."""
    from tw2k.engine import generate_universe
    from tw2k.engine.models import Player, Ship, ShipClass

    u = generate_universe(GameConfig(seed=7, universe_size=20, max_days=1))
    p = Player(
        id="P1",
        name="Test",
        credits=credits,
        sector_id=next(iter(u.sectors.keys())),
        ship=Ship(class_id=ShipClass.MERCHANT_CRUISER),
        agent_kind="human",
        color="#fff",
    )
    u.players[p.id] = p
    return u, p


def test_standing_order_min_credit_reserve_blocks_buy_that_would_dip() -> None:
    u, p = _tiny_universe_with_port(credits=1_000)
    order = StandingOrder(
        id="r1",
        kind=StandingOrderKind.MIN_CREDIT_RESERVE,
        params={"credits": 500},
    )
    # Would spend 600 cr (3 × 200) and only has 1000 → projected 400 < 500.
    call = ToolCall(
        name="buy",
        arguments={"commodity": "fuel_ore", "qty": 3, "unit_price": 200},
    )
    verdict = so.evaluate([order], u, p.id, call)
    assert verdict.allowed is False
    assert verdict.blocked_by == ["r1"]


def test_standing_order_min_credit_reserve_passes_within_budget() -> None:
    u, p = _tiny_universe_with_port(credits=5_000)
    order = StandingOrder(
        id="r1",
        kind=StandingOrderKind.MIN_CREDIT_RESERVE,
        params={"credits": 500},
    )
    call = ToolCall(
        name="buy",
        arguments={"commodity": "fuel_ore", "qty": 3, "unit_price": 200},
    )
    verdict = so.evaluate([order], u, p.id, call)
    assert verdict.allowed is True


def test_standing_order_no_warp_to_sectors_blocks_warp_into_forbidden() -> None:
    u, p = _tiny_universe_with_port()
    order = StandingOrder(
        id="nofly",
        kind=StandingOrderKind.NO_WARP_TO_SECTORS,
        params={"sectors": [42]},
    )
    verdict = so.evaluate(
        [order],
        u,
        p.id,
        ToolCall(name="warp", arguments={"target": 42}),
    )
    assert verdict.allowed is False
    verdict2 = so.evaluate(
        [order],
        u,
        p.id,
        ToolCall(name="warp", arguments={"target": 43}),
    )
    assert verdict2.allowed is True


def test_standing_order_ignores_non_action_calls() -> None:
    u, p = _tiny_universe_with_port()
    order = StandingOrder(
        id="cr",
        kind=StandingOrderKind.MIN_CREDIT_RESERVE,
        params={"credits": 50_000},  # nobody has this many creds
    )
    # `speak` is a dialog tool — should never trip an order.
    call = ToolCall(name="speak", arguments={"message": "hi"})
    assert so.evaluate([order], u, p.id, call).allowed is True


# ---------------------------------------------------------------------------
# ChatAgent classification via mock provider
# ---------------------------------------------------------------------------


def _use_scripted_provider(tag: str, script: list[str]):
    """Install a mock that returns `script[i]` on the i-th call."""
    idx = {"n": 0}

    async def fn(system: str, user: str, ctx: dict[str, Any]) -> str:
        i = idx["n"]
        idx["n"] = min(i + 1, len(script) - 1)
        return script[i]

    register_mock_responder(tag, fn)


def _fake_observation():
    from tw2k.engine import Observation

    return Observation(
        day=1,
        tick=1,
        max_days=1,
        finished=False,
        self_id="P1",
        self_name="Test",
        credits=1000,
        alignment=0,
        turns_remaining=100,
        turns_per_day=300,
        ship={"class": "cc", "hull": 10, "max_hull": 10, "cargo": {}, "cargo_max": 75},
        corp_ticker=None,
        planet_landed=None,
        scratchpad="",
        sector={"id": 1, "warps": [2, 3]},
        adjacent=[],
        known_ports=[],
        other_players=[],
        inbox=[],
        recent_events=[],
    )


@pytest.mark.asyncio
async def test_chat_agent_classifies_single_action_as_action_kind() -> None:
    clear_mock_responders()
    _use_scripted_provider("ca1", ['{"tool":"warp","arguments":{"target":2}}'])
    agent = ChatAgent(provider="mock:ca1")
    resp = await agent.respond("go to 2", _fake_observation(), mode="delegated")
    assert resp.kind == "action"
    assert len(resp.plan) == 1
    assert resp.plan[0].name == "warp"


@pytest.mark.asyncio
async def test_chat_agent_classifies_multi_step_plan() -> None:
    clear_mock_responders()
    _use_scripted_provider(
        "ca2",
        [
            '{"plan":[{"tool":"warp","arguments":{"target":2}},'
            '{"tool":"scan","arguments":{}}],"thought":"explore"}'
        ],
    )
    agent = ChatAgent(provider="mock:ca2")
    resp = await agent.respond("explore", _fake_observation(), mode="autopilot")
    assert resp.kind == "plan"
    assert resp.needs_confirm is True
    assert [c.name for c in resp.plan] == ["warp", "scan"]


@pytest.mark.asyncio
async def test_chat_agent_classifies_start_task() -> None:
    clear_mock_responders()
    _use_scripted_provider(
        "ca3",
        [
            '{"tool":"start_task","arguments":{"kind":"profit_loop",'
            '"params":{"target_cr":30000}},"thought":"loop"}'
        ],
    )
    agent = ChatAgent(provider="mock:ca3")
    resp = await agent.respond("run a trade loop", _fake_observation(), mode="autopilot")
    assert resp.kind == "start_task"
    assert resp.task_kind == "profit_loop"
    assert resp.task_params == {"target_cr": 30000}
    assert resp.needs_confirm is True


@pytest.mark.asyncio
async def test_chat_agent_recognises_cancel_tool() -> None:
    clear_mock_responders()
    _use_scripted_provider(
        "ca4", ['{"tool":"cancel_task","arguments":{"reason":"ok"}}']
    )
    agent = ChatAgent(provider="mock:ca4")
    resp = await agent.respond("stop", _fake_observation(), mode="autopilot")
    assert resp.kind == "cancel"


# ---------------------------------------------------------------------------
# End-to-end: app with a human slot + copilot wiring
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
    # Scheduler populates runner.state.agents asynchronously inside _run;
    # wait until it's ready before rebuilding the registry.
    for _ in range(120):
        await asyncio.sleep(0.02)
        if runner.state.agents and runner.state.universe is not None:
            break
    # Rebuild registry — production code does this in the lifespan, but
    # auto_start=False skips that path so the test fixture rebuilds by hand.
    app.state.copilot_registry.rebuild(
        runner=runner, broadcaster=app.state.broadcaster
    )
    for _ in range(120):
        await asyncio.sleep(0.02)
        u = runner.state.universe
        if u is not None and any(
            e.kind == EventKind.HUMAN_TURN_START for e in u.events
        ):
            break
    return runner


@pytest.fixture
def app_with_human(tmp_path: Path) -> FastAPI:
    return _app_with_human(tmp_path)


def test_copilot_registry_creates_sessions_for_humans_only(
    app_with_human: FastAPI, tmp_path: Path
) -> None:
    async def _go() -> None:
        await _start_match(app_with_human, tmp_path)
        reg = app_with_human.state.copilot_registry
        assert reg.get("P2") is not None  # human
        assert reg.get("P1") is None      # heuristic
        # P2's session is pre-populated with the right player_id.
        sess = reg.get("P2")
        assert isinstance(sess, CopilotSession)
        assert sess.player_id == "P2"
        assert sess.mode == CopilotMode.ADVISORY
        await app_with_human.state.runner.stop()

    asyncio.run(_go())


def test_copilot_state_endpoint_returns_mode_and_empty_chat(
    app_with_human: FastAPI, tmp_path: Path
) -> None:
    async def _go() -> None:
        await _start_match(app_with_human, tmp_path)
        transport = httpx.ASGITransport(app=app_with_human)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/copilot/state", params={"player_id": "P2"})
            assert r.status_code == 200
            data = r.json()
            assert data["mode"] == "advisory"
            assert data["chat"] == []
            assert data["pending_plan"] is None
            assert data["active_task"] is None
            assert "tool_catalog" in data
            assert "warp" in data["tool_catalog"]
        await app_with_human.state.runner.stop()

    asyncio.run(_go())


def test_copilot_state_endpoint_404_409_503(
    app_with_human: FastAPI, tmp_path: Path
) -> None:
    """Mirror the /api/human/action error contract so the UI can
    surface errors uniformly regardless of endpoint."""

    async def _go() -> None:
        transport = httpx.ASGITransport(app=app_with_human)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            # Before match starts -> 503
            r = await c.get("/api/copilot/state", params={"player_id": "P2"})
            assert r.status_code == 503
            await _start_match(app_with_human, tmp_path)
            # Now P1 is heuristic -> 409
            r = await c.get("/api/copilot/state", params={"player_id": "P1"})
            assert r.status_code == 409
            # Unknown player -> 404
            r = await c.get("/api/copilot/state", params={"player_id": "P99"})
            assert r.status_code == 404
        await app_with_human.state.runner.stop()

    asyncio.run(_go())


def test_copilot_mode_endpoint_switches_session_mode(
    app_with_human: FastAPI, tmp_path: Path
) -> None:
    async def _go() -> None:
        await _start_match(app_with_human, tmp_path)
        transport = httpx.ASGITransport(app=app_with_human)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/copilot/mode",
                json={"player_id": "P2", "mode": "autopilot"},
            )
            assert r.status_code == 200
            assert r.json()["mode"] == "autopilot"
            sess = app_with_human.state.copilot_registry.get("P2")
            assert sess.mode == CopilotMode.AUTOPILOT

            # Unknown mode -> 422
            r = await c.post(
                "/api/copilot/mode", json={"player_id": "P2", "mode": "nope"}
            )
            assert r.status_code == 422
        await app_with_human.state.runner.stop()

    asyncio.run(_go())


def test_copilot_chat_delegated_mode_dispatches_action_and_tags_copilot(
    app_with_human: FastAPI, tmp_path: Path
) -> None:
    """Exit-criterion microcosm: delegated mode, one utterance → one
    engine action submitted on the human's behalf with actor_kind=copilot."""

    clear_mock_responders()
    _use_scripted_provider(
        "e2e1", ['{"tool":"pass_turn","arguments":{},"thought":"just wait"}']
    )

    async def _go() -> None:
        runner = await _start_match(app_with_human, tmp_path)
        sess = app_with_human.state.copilot_registry.get("P2")
        # Force the session's ChatAgent to use our mock.
        sess.chat_agent = ChatAgent(provider="mock:e2e1")
        await sess.set_mode(CopilotMode.DELEGATED)

        u = runner.state.universe
        pre_seq = u.seq

        transport = httpx.ASGITransport(app=app_with_human)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/copilot/chat",
                json={"player_id": "P2", "message": "just pass this turn"},
            )
            assert r.status_code == 200
            data = r.json()
            assert data["response"]["kind"] == "action"

        # Wait a tick for the scheduler to consume the queued action.
        for _ in range(60):
            await asyncio.sleep(0.03)
            if u.seq > pre_seq:
                break

        # Find any event emitted for P2 after pre_seq — it must be
        # tagged actor_kind=copilot (not "human") since the copilot
        # submitted it.
        copilot_events = [
            e
            for e in u.events
            if e.seq > pre_seq
            and e.actor_id == "P2"
            and e.actor_kind == "copilot"
        ]
        assert copilot_events, "no copilot-tagged events found for P2"

        await runner.stop()

    asyncio.run(_go())


def test_copilot_manual_action_still_tagged_human(
    app_with_human: FastAPI, tmp_path: Path
) -> None:
    """A direct /api/human/action submit (no copilot) must retain the
    "human" actor_kind. Otherwise our forensic / replay audit trail
    can't distinguish clicks from autopilot."""

    async def _go() -> None:
        runner = await _start_match(app_with_human, tmp_path)
        u = runner.state.universe
        pre_seq = u.seq

        transport = httpx.ASGITransport(app=app_with_human)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/human/action",
                json={
                    "player_id": "P2",
                    "action": {"kind": "wait", "args": {}, "thought": "manual"},
                },
            )
            assert r.status_code == 200

        for _ in range(60):
            await asyncio.sleep(0.03)
            if u.seq > pre_seq:
                break
        human_events = [
            e for e in u.events if e.seq > pre_seq and e.actor_id == "P2"
        ]
        assert human_events, "P2 produced no events"
        assert all(e.actor_kind == "human" for e in human_events), (
            f"manual action leaked non-human actor_kind: "
            f"{[e.actor_kind for e in human_events]}"
        )
        await runner.stop()

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# TaskAgent loop + cancellation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task_agent_runs_until_target_credits_reached() -> None:
    """Scripted next_step_fn mimics the trade-loop exit criterion: every
    iteration submits `pass_turn`, but we mutate credits between calls
    via a fake dispatch_fn so the terminal condition fires on schedule."""

    status = TaskStatus(
        id="t1", kind="profit_loop", params={"target_cr": 30_000, "max_iterations": 10}
    )

    credits = {"n": 10_000}

    async def next_step(ctx: TaskContext):
        return ToolCall(name="pass_turn", arguments={})

    async def dispatch(call: ToolCall):
        # Pretend the copilot sold something for a 5000 cr profit.
        credits["n"] += 5_000
        return (True, "")

    def obs():
        from tw2k.engine import Observation

        return Observation(
            day=1,
            tick=credits["n"],
            max_days=1,
            finished=False,
            self_id="P1",
            self_name="Test",
            credits=credits["n"],
            alignment=0,
            turns_remaining=100,
            turns_per_day=300,
            ship={"class": "cc", "hull": 1, "max_hull": 1, "cargo": {}, "cargo_max": 75},
            corp_ticker=None,
            planet_landed=None,
            scratchpad="",
            sector={"id": 1, "warps": []},
            adjacent=[],
            known_ports=[],
            other_players=[],
            inbox=[],
            recent_events=[],
        )

    reports: list[tuple[str, dict]] = []

    async def report(kind: str, payload: dict):
        reports.append((kind, payload))

    task = TaskAgent(
        status,
        obs_fn=obs,
        dispatch_fn=dispatch,
        next_step_fn=next_step,
        report_fn=report,
        iter_delay_s=0,
    )
    await task.run()
    assert status.state == "done"
    assert "reached target" in (status.reason_finished or "")
    # Should have hit exactly (30000-10000)/5000 = 4 iterations BEFORE
    # the terminal-condition loop-top check passes. But the task checks
    # terminal BEFORE asking next_step, so it does 4 dispatch cycles
    # then one no-op loop that ends.
    assert 3 <= status.iterations <= 6


@pytest.mark.asyncio
async def test_task_agent_cancel_halts_mid_loop() -> None:
    status = TaskStatus(
        id="t2", kind="profit_loop", params={"target_cr": 99_999_999}
    )

    async def dispatch(call: ToolCall):
        return (True, "")

    async def next_step(ctx: TaskContext):
        return ToolCall(name="pass_turn", arguments={})

    def obs():
        from tw2k.engine import Observation

        return Observation(
            day=1,
            tick=0,
            max_days=1,
            finished=False,
            self_id="P1",
            self_name="Test",
            credits=0,
            alignment=0,
            turns_remaining=100,
            turns_per_day=300,
            ship={"class": "cc", "hull": 1, "max_hull": 1, "cargo": {}, "cargo_max": 75},
            corp_ticker=None,
            planet_landed=None,
            scratchpad="",
            sector={"id": 1, "warps": []},
            adjacent=[],
            known_ports=[],
            other_players=[],
            inbox=[],
            recent_events=[],
        )

    async def report(kind: str, payload: dict):
        pass

    task = TaskAgent(
        status,
        obs_fn=obs,
        dispatch_fn=dispatch,
        next_step_fn=next_step,
        report_fn=report,
        iter_delay_s=0.02,
    )

    async def cancel_soon():
        await asyncio.sleep(0.08)
        task.cancel(reason="test_cancel")

    await asyncio.gather(task.run(), cancel_soon())
    assert status.state == "cancelled"
    assert status.iterations >= 1
    # Iterations should stop well before the target (which is never reached).
    assert status.iterations < 1000


# ---------------------------------------------------------------------------
# Pure-AI regression: no copilot sessions and no copilot actor_kind leakage
# ---------------------------------------------------------------------------


def test_pure_ai_match_has_empty_copilot_registry(tmp_path: Path) -> None:
    app = create_app(
        seed=42,
        universe_size=40,
        max_days=1,
        num_agents=3,
        agent_kind="heuristic",
        auto_start=False,
        turns_per_day=6,
        action_delay_s=0.0,
    )

    async def _go() -> None:
        runner: MatchRunner = app.state.runner
        runner._saves_root = tmp_path / "saves"  # type: ignore[attr-defined]
        spec = MatchSpec(
            config=GameConfig(
                seed=42,
                universe_size=40,
                max_days=1,
                turns_per_day=6,
                enable_ferrengi=False,
                enable_planets=False,
                action_delay_s=0.0,
            ),
            agents=[
                AgentSpec(player_id=f"P{i+1}", name=f"B{i}", kind="heuristic")
                for i in range(3)
            ],
            action_delay_s=0.0,
        )
        await runner.start(spec)
        app.state.copilot_registry.rebuild(
            runner=runner, broadcaster=app.state.broadcaster
        )
        # No human slots = no sessions.
        assert app.state.copilot_registry.all() == []
        # Run a few ticks and confirm no event carries actor_kind=copilot.
        for _ in range(40):
            await asyncio.sleep(0.02)
        u = runner.state.universe
        assert u is not None
        leaks = [e for e in u.events if e.actor_kind == "copilot"]
        assert leaks == [], (
            f"pure-AI match leaked copilot actor_kind: {[e.summary for e in leaks[:5]]}"
        )
        await runner.stop()

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# UIAgent (rule-based, no LLM)
# ---------------------------------------------------------------------------


def test_ui_agent_hints_returns_tooltips_and_suggestion() -> None:
    from tw2k.copilot.ui_agent import button_hints, suggest_next_move

    obs = _fake_observation()
    h = button_hints(obs)
    assert "warp" in h
    # suggest_next_move should produce a non-empty string for any plausible state.
    assert isinstance(suggest_next_move(obs), str)


def test_hints_endpoint_reachable(app_with_human: FastAPI, tmp_path: Path) -> None:
    async def _go() -> None:
        await _start_match(app_with_human, tmp_path)
        transport = httpx.ASGITransport(app=app_with_human)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/copilot/hints", params={"player_id": "P2"})
            assert r.status_code == 200
            body = r.json()
            assert "hints" in body and "suggest" in body
            # Warp hint is always emitted, even when adjacent list is empty.
            assert "warp" in body["hints"]
        await app_with_human.state.runner.stop()

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# Standing-order integration: block a copilot-dispatched action through the
# full CopilotSession pipeline (§10 exit: "standing-order blocks").
# ---------------------------------------------------------------------------


def test_copilot_session_blocks_action_violating_standing_order(
    app_with_human: FastAPI, tmp_path: Path
) -> None:
    clear_mock_responders()
    _use_scripted_provider(
        "so1",
        [
            '{"tool":"warp","arguments":{"target":999},"thought":"forbidden warp"}'
        ],
    )

    async def _go() -> None:
        runner = await _start_match(app_with_human, tmp_path)
        sess = app_with_human.state.copilot_registry.get("P2")
        sess.chat_agent = ChatAgent(provider="mock:so1")
        await sess.set_mode(CopilotMode.DELEGATED)
        await sess.add_standing_order(
            StandingOrder(
                id="nofly999",
                kind=StandingOrderKind.NO_WARP_TO_SECTORS,
                params={"sectors": [999]},
            )
        )

        resp = await sess.handle_chat("warp to 999 please")
        assert resp.kind == "action"
        # Session logs a block notice — inspect chat history for the block.
        blocks = [
            m
            for m in sess.chat_history
            if m.kind == "standing_order_block"
        ]
        assert blocks, "expected standing_order_block log entry"
        await runner.stop()

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# Teardown: clear any mock responders so tests don't bleed into each other
# when run in a single session.
# ---------------------------------------------------------------------------


def teardown_function(_fn) -> None:
    clear_mock_responders()


# Keep ActionKind import alive so test file isn't flagged for "unused".
_ = ActionKind
