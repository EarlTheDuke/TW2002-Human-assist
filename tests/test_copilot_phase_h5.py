"""Phase H5 backend tests — memory, tracer, what-if, API endpoints.

These tests cover the polish-and-power-features pack shipped in H5:

* **H5.1 — Memory**: ``CopilotMemory`` CRUD + parsing, ``MemoryStore``
  on-disk round-trip, CopilotSession wiring of ``remember`` / ``forget``
  auto-learning on plan confirm, favourite-sector capture on warp, the
  new ``/api/copilot/memory`` + ``/api/copilot/memory/remember`` +
  ``/api/copilot/memory/forget`` endpoints, and the ``memory`` block in
  ``state_snapshot()``.

* **H5.2 — Tracer**: ``CopilotTracer`` JSONL writes (no-op when disabled,
  append semantics + ring buffer when enabled), session integration on
  utterance / chat-response / mode-change / memory-update /
  standing-order-block / action-dispatched / escalation.

* **H5.4 — What-if**: ``preview_plan`` credit / turn / cargo math,
  risk detection, ``/api/copilot/whatif`` endpoint, and whatif embedded
  in ``state_snapshot()`` when a plan is pending.

H5.3 (multi-language voice + mobile layout) is a pure UI change
covered by the H5 static-asset tests in ``test_voice_ui_phase_h5.py``.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from tw2k.copilot import memory as mem_mod
from tw2k.copilot import whatif as wi
from tw2k.copilot.memory import CopilotMemory, MemoryStore
from tw2k.copilot.tools import ToolCall
from tw2k.copilot.trace import CopilotTracer
from tw2k.engine import GameConfig
from tw2k.engine.models import Player, PortClass, Ship, Universe
from tw2k.engine.universe import generate_universe

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _tiny_universe() -> tuple[Universe, str]:
    """Build a minimal universe with one port + one human player.

    Kept deterministic (seed=5) so the ports/warps layout is stable
    across runs — the what-if math is very sensitive to stock levels
    + adjacency so we don't want RNG drift.
    """
    cfg = GameConfig(
        seed=5,
        universe_size=12,
        max_days=1,
        turns_per_day=6,
        starting_credits=20_000,
        enable_ferrengi=False,
        enable_planets=False,
        action_delay_s=0.0,
    )
    u = generate_universe(cfg)
    pid = "P1"
    u.players[pid] = Player(id=pid, name="You", ship=Ship(), credits=20_000)
    # Drop the player into a sector that has a port (generate_universe
    # doesn't put the player in one by default).
    for sid, sec in u.sectors.items():
        if sec.port is not None and sec.port.class_id != PortClass.FEDERAL:
            u.players[pid].sector_id = sid
            break
    return u, pid


# ===========================================================================
# H5.1 — Memory
# ===========================================================================


class TestCopilotMemory:
    def test_remember_recall_forget_roundtrip(self) -> None:
        m = CopilotMemory(player_id="P1")
        m.remember("min_reserve", "5000")
        m.remember("preferred_port_class", "7")
        assert m.recall("min_reserve") == "5000"
        assert m.recall("preferred_port_class") == "7"
        assert m.forget("min_reserve") is True
        assert m.recall("min_reserve") is None
        # Idempotent forget.
        assert m.forget("min_reserve") is False

    def test_remember_empty_is_noop(self) -> None:
        m = CopilotMemory(player_id="P1")
        m.remember("", "x")
        m.remember("k", "")
        assert m.preferences == {}

    def test_learned_rules_dedupe_and_cap(self) -> None:
        m = CopilotMemory(player_id="P1")
        for i in range(mem_mod.MAX_LEARNED_RULES + 5):
            m.add_learned_rule(f"rule {i}")
        # Cap enforced.
        assert len(m.learned_rules) == mem_mod.MAX_LEARNED_RULES
        # Case-insensitive dedupe + reinforcement: re-adding moves to tail.
        m.add_learned_rule("RULE 4")
        assert "RULE 4" in m.learned_rules
        assert m.learned_rules.count("RULE 4") == 1
        # Ensure the reinforced rule is at the end.
        assert m.learned_rules[-1] == "RULE 4"

    def test_favorite_sectors_ordered_mru(self) -> None:
        m = CopilotMemory(player_id="P1")
        for sid in [1, 2, 3, 2, 4]:
            m.mark_favorite_sector(sid)
        # 2 should appear only once, most-recent at end.
        assert m.favorite_sectors == [1, 3, 2, 4]

    def test_summary_and_prompt_block(self) -> None:
        m = CopilotMemory(player_id="P1")
        assert m.summary_line() == "memory: empty"
        assert m.prompt_block() == ""
        m.remember("x", "y")
        m.add_learned_rule("stay in fedspace near dock")
        m.mark_favorite_sector(7)
        m.bump_stat("session_count", 3)
        s = m.summary_line()
        assert "1 prefs" in s
        assert "1 rules" in s
        assert "1 favs" in s
        assert "3 sessions" in s
        block = m.prompt_block()
        assert "[memory]" in block
        assert "pref: x = y" in block
        assert "learned: stay in fedspace near dock" in block

    def test_bump_stat_counts_up(self) -> None:
        m = CopilotMemory(player_id="P1")
        assert m.bump_stat("session_count") == 1
        assert m.bump_stat("session_count") == 2
        assert m.bump_stat("session_count", 3) == 5

    def test_parse_remember_directive(self) -> None:
        assert mem_mod.parse_remember_directive(
            "remember my preferred port class is 7"
        ) == ("my preferred port class", "7")
        assert mem_mod.parse_remember_directive(
            "remember min_reserve = 5000"
        ) == ("min_reserve", "5000")
        assert mem_mod.parse_remember_directive("note: theme = dark") == (
            "theme",
            "dark",
        )
        assert mem_mod.parse_remember_directive("tell me a joke") is None

    def test_parse_forget_directive(self) -> None:
        assert mem_mod.parse_forget_directive("forget min_reserve") == "min_reserve"
        assert mem_mod.parse_forget_directive("forget that my preferred port class") == (
            "preferred port class"
        )
        assert mem_mod.parse_forget_directive("tell me more") is None


class TestMemoryStore:
    def test_in_memory_store_has_no_root(self) -> None:
        s = MemoryStore()
        assert s.root is None
        m = s.load("P1")
        assert m.player_id == "P1"
        # Load is cached.
        m.remember("x", "y")
        s.save(m)
        again = s.load("P1")
        assert again.recall("x") == "y"

    def test_on_disk_roundtrip(self, tmp_path: Path) -> None:
        s = MemoryStore(tmp_path)
        m = s.load("P1")
        m.remember("k", "v")
        s.save(m)
        assert (tmp_path / "copilot_memory_P1.json").exists()
        # Fresh store reads from disk.
        s2 = MemoryStore(tmp_path)
        m2 = s2.load("P1")
        assert m2.recall("k") == "v"

    def test_corrupt_file_falls_back_to_empty(self, tmp_path: Path) -> None:
        (tmp_path / "copilot_memory_P1.json").write_text("{bad json", encoding="utf-8")
        s = MemoryStore(tmp_path)
        m = s.load("P1")
        assert m.player_id == "P1"
        assert m.preferences == {}


# ===========================================================================
# H5.2 — Tracer
# ===========================================================================


class TestCopilotTracer:
    @pytest.mark.asyncio
    async def test_disabled_tracer_is_noop(self, tmp_path: Path) -> None:
        t = CopilotTracer(player_id="P1", root_dir=None, enable=False)
        assert t.enabled is False
        await t.emit("chat_utterance", {"text": "hi"})
        assert t.ring() == []
        # No file should have been written.
        assert not any((tmp_path).iterdir())

    @pytest.mark.asyncio
    async def test_enabled_tracer_writes_jsonl(self, tmp_path: Path) -> None:
        t = CopilotTracer(player_id="P1", root_dir=tmp_path, enable=True)
        await t.emit("chat_utterance", {"text": "hello"})
        await t.emit("action_dispatched", {"tool": "warp", "ok": True})
        path = t.path
        assert path is not None
        lines = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()]
        assert len(lines) == 2
        assert lines[0]["event"] == "chat_utterance"
        assert lines[0]["payload"]["text"] == "hello"
        assert lines[1]["event"] == "action_dispatched"
        # Ring mirror is populated too.
        assert len(t.ring()) == 2

    @pytest.mark.asyncio
    async def test_convenience_helpers_set_levels(self, tmp_path: Path) -> None:
        t = CopilotTracer(player_id="P1", root_dir=tmp_path, enable=True)
        await t.trace_standing_order_block("buy", ["o1"], ["over reserve"])
        await t.trace_safety_signal("critical", "COMBAT", "hostile fighters")
        ring = t.ring()
        assert ring[0]["level"] == "warn"
        assert ring[1]["level"] == "warn"
        assert ring[1]["payload"]["signal_level"] == "critical"

    @pytest.mark.asyncio
    async def test_env_toggle_respected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TW2K_COPILOT_TRACE", "1")
        t = CopilotTracer(player_id="P1", root_dir=tmp_path)
        assert t.enabled is True
        monkeypatch.delenv("TW2K_COPILOT_TRACE", raising=False)
        t2 = CopilotTracer(player_id="P1", root_dir=tmp_path)
        assert t2.enabled is False


# ===========================================================================
# H5.4 — What-if preview
# ===========================================================================


class TestWhatIfPreview:
    def test_empty_plan_returns_zero_summary(self) -> None:
        u, pid = _tiny_universe()
        s = wi.preview_plan(u, pid, [])
        assert s.steps == []
        assert s.credit_delta == 0
        assert s.turn_cost == 0
        assert s.one_liner() == "≈ no visible change"

    def test_warp_step_costs_one_turn_and_flags_bad_target(self) -> None:
        u, pid = _tiny_universe()
        player = u.players[pid]
        sec = u.sectors[player.sector_id]
        good = sec.warps[0] if sec.warps else next(iter(u.sectors.keys()))
        bad = 9999
        plan = [
            ToolCall(name="warp", arguments={"target": good}),
            ToolCall(name="warp", arguments={"target": bad}),
        ]
        s = wi.preview_plan(u, pid, plan)
        assert s.turn_cost == 2
        assert s.steps[0].risk is None
        assert s.steps[1].risk is not None
        assert any("9999" in w for w in s.warnings)

    def test_buy_sell_cycle_estimates_credit_delta_and_cargo(self) -> None:
        u, pid = _tiny_universe()
        # Find a sector with a port that sells fuel_ore.
        from tw2k.engine.models import Commodity

        origin = None
        for sid, sec in u.sectors.items():
            if sec.port is not None and sec.port.sells(Commodity.FUEL_ORE):
                origin = sid
                break
        if origin is None:
            pytest.skip("no fuel_ore-selling port in generated universe")
        u.players[pid].sector_id = origin
        plan = [
            ToolCall(name="buy", arguments={"commodity": "fuel_ore", "qty": 10}),
        ]
        s = wi.preview_plan(u, pid, plan)
        step = s.steps[0]
        # Buying fuel_ore should produce a negative credit delta and
        # positive cargo delta.
        assert step.credit_delta < 0
        assert step.cargo_delta == {"fuel_ore": 10}
        assert s.turn_cost == 1
        assert s.cargo_delta == {"fuel_ore": 10}

    def test_one_liner_renders_credits_and_turns(self) -> None:
        summary = wi.WhatIfSummary(
            credit_delta=2500, turn_cost=3, cargo_delta={"fuel_ore": 10}
        )
        out = summary.one_liner()
        assert "+2,500 cr" in out
        assert "-3 turns" in out
        assert "+10 fuel_ore" in out

    def test_planning_tools_are_zero_cost(self) -> None:
        u, pid = _tiny_universe()
        plan = [ToolCall(name="speak", arguments={"message": "hi"})]
        s = wi.preview_plan(u, pid, plan)
        assert s.credit_delta == 0
        assert s.turn_cost == 0
        assert s.steps[0].tool == "speak"


# ===========================================================================
# CopilotSession integration
# ===========================================================================


def _session_fixture(tmp_path: Path):
    """Build a CopilotSession without a running scheduler for unit tests.

    We stub ``human_agent`` + ``universe_fn`` with minimal shims so the
    session can run ``remember`` / ``forget`` / ``state_snapshot`` /
    ``whatif_snapshot`` without booting a MatchRunner.
    """
    from tw2k.agents.human import HumanAgent
    from tw2k.copilot.session import CopilotSession

    u, pid = _tiny_universe()

    class _StubAgent(HumanAgent):
        def __init__(self, player_id):
            super().__init__(player_id, "Stub")
            self.submitted: list = []

        async def submit_action(self, action):
            self.submitted.append(action)

    agent = _StubAgent(pid)

    async def broadcast_fn(msg):
        return None

    tracer = CopilotTracer(player_id=pid, root_dir=tmp_path, enable=True)
    store = MemoryStore(tmp_path)
    sess = CopilotSession(
        player_id=pid,
        human_agent=agent,
        universe_fn=lambda: u,
        broadcast_fn=broadcast_fn,
        memory_store=store,
        tracer=tracer,
    )
    return sess, u, pid, tracer, store


@pytest.mark.asyncio
async def test_session_remember_forget_persists(tmp_path: Path) -> None:
    sess, _u, pid, tracer, store = _session_fixture(tmp_path)
    ok = await sess.remember("min_reserve", "5000")
    assert ok is True
    # On-disk state.
    m = store.load(pid)
    assert m.recall("min_reserve") == "5000"
    # Tracer captured it.
    events = [e for e in tracer.ring() if e["event"] == "memory_update"]
    assert any(e["payload"]["op"] == "remember" for e in events)

    had = await sess.forget("min_reserve")
    assert had is True
    m2 = store.load(pid)
    assert m2.recall("min_reserve") is None


@pytest.mark.asyncio
async def test_session_chat_remember_directive_shortcircuits_llm(
    tmp_path: Path,
) -> None:
    """`remember X = Y` must not require the LLM — the session parses it
    directly and logs a memory_update."""
    sess, _u, _pid, _tracer, _store = _session_fixture(tmp_path)
    resp = await sess.handle_chat("remember min_reserve = 5000")
    assert resp.kind == "speak"
    assert "5000" in resp.message
    assert sess.memory.recall("min_reserve") == "5000"


@pytest.mark.asyncio
async def test_state_snapshot_includes_memory_block(tmp_path: Path) -> None:
    sess, _u, _pid, _tracer, _store = _session_fixture(tmp_path)
    await sess.remember("pref", "value")
    snap = sess.state_snapshot()
    assert "memory" in snap
    assert snap["memory"]["preferences"]["pref"] == "value"
    assert snap["memory"]["summary"].startswith("memory:")


@pytest.mark.asyncio
async def test_whatif_snapshot_returns_preview_for_pending_plan(
    tmp_path: Path,
) -> None:
    from tw2k.copilot.session import PendingPlan

    sess, u, pid, _tracer, _store = _session_fixture(tmp_path)
    sec = u.sectors[u.players[pid].sector_id]
    if not sec.warps:
        pytest.skip("no warps from player's sector in generated universe")
    target = sec.warps[0]
    sess.pending_plan = PendingPlan(
        id="abc",
        plan=[ToolCall(name="warp", arguments={"target": target})],
        thought="probe ahead",
    )
    snap = sess.whatif_snapshot()
    assert snap is not None
    assert snap["plan_id"] == "abc"
    assert snap["turn_cost"] == 1
    assert "warp" in snap["steps"][0]["tool"]


@pytest.mark.asyncio
async def test_session_bumps_session_count_on_init(tmp_path: Path) -> None:
    sess, _u, pid, _tracer, store = _session_fixture(tmp_path)
    assert sess.memory.stats.get("session_count", 0) == 1
    # Rebuilding the session loads the prior file and bumps again.
    from tw2k.copilot.session import CopilotSession

    async def broadcast_fn(msg):
        return None

    sess2 = CopilotSession(
        player_id=pid,
        human_agent=sess.human_agent,
        universe_fn=sess._universe_fn,
        broadcast_fn=broadcast_fn,
        memory_store=store,
        tracer=CopilotTracer(player_id=pid, root_dir=tmp_path, enable=True),
    )
    assert sess2.memory.stats["session_count"] >= 2


@pytest.mark.asyncio
async def test_session_confirm_pending_auto_learns_rule(tmp_path: Path) -> None:
    from tw2k.copilot.session import PendingPlan

    sess, u, pid, _tracer, _store = _session_fixture(tmp_path)
    sec = u.sectors[u.players[pid].sector_id]
    if not sec.warps:
        pytest.skip("no warps")
    target = sec.warps[0]
    sess.pending_plan = PendingPlan(
        id="plan-1",
        plan=[ToolCall(name="warp", arguments={"target": target})],
        thought="scout the northern chain",
    )
    ok = await sess.confirm_pending("plan-1")
    assert ok is True
    assert any(
        "scout the northern chain" in r for r in sess.memory.learned_rules
    )
    # Stats bumped.
    assert sess.memory.stats.get("plans_confirmed", 0) >= 1


# ===========================================================================
# API endpoints
# ===========================================================================


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


async def _start_match(app: FastAPI, tmp_path: Path) -> None:
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
async def test_api_memory_roundtrip(tmp_path: Path) -> None:
    app = _app_with_human(tmp_path)
    try:
        await _start_match(app, tmp_path)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            # Initial memory is empty (or session_count=1 only).
            r = await client.get("/api/copilot/memory?player_id=P2")
            assert r.status_code == 200
            j = r.json()
            assert j["player_id"] == "P2"
            assert "preferences" in j

            # Remember.
            r = await client.post(
                "/api/copilot/memory/remember",
                json={
                    "player_id": "P2",
                    "key": "min_reserve",
                    "value": "5000",
                },
            )
            assert r.status_code == 200
            assert r.json()["memory"]["preferences"]["min_reserve"] == "5000"

            # Forget.
            r = await client.post(
                "/api/copilot/memory/forget",
                json={"player_id": "P2", "key": "min_reserve"},
            )
            assert r.status_code == 200
            assert r.json()["existed"] is True
            assert "min_reserve" not in r.json()["memory"]["preferences"]

            # 400 on malformed body.
            r = await client.post(
                "/api/copilot/memory/remember",
                json={"player_id": "P2", "key": "x"},
            )
            assert r.status_code == 400

            # 404 on unknown player.
            r = await client.get("/api/copilot/memory?player_id=P99")
            assert r.status_code == 404
    finally:
        await app.state.runner.stop()


@pytest.mark.asyncio
async def test_api_whatif_pending_false_when_no_plan(tmp_path: Path) -> None:
    app = _app_with_human(tmp_path)
    try:
        await _start_match(app, tmp_path)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            r = await client.get("/api/copilot/whatif?player_id=P2")
            assert r.status_code == 200
            assert r.json() == {"pending": False}
    finally:
        await app.state.runner.stop()


@pytest.mark.asyncio
async def test_api_whatif_returns_preview_with_pending_plan(
    tmp_path: Path,
) -> None:
    from tw2k.copilot.session import PendingPlan

    app = _app_with_human(tmp_path)
    try:
        await _start_match(app, tmp_path)
        sess = app.state.copilot_registry.get("P2")
        assert sess is not None
        u = app.state.runner.state.universe
        sec = u.sectors[u.players["P2"].sector_id]
        target = sec.warps[0] if sec.warps else next(iter(u.sectors.keys()))
        sess.pending_plan = PendingPlan(
            id="p1",
            plan=[ToolCall(name="warp", arguments={"target": target})],
            thought="scout",
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            r = await client.get("/api/copilot/whatif?player_id=P2")
            assert r.status_code == 200
            j = r.json()
            assert j["pending"] is True
            assert j["plan_id"] == "p1"
            assert j["turn_cost"] == 1
            assert "warp" in [s["tool"] for s in j["steps"]]
    finally:
        await app.state.runner.stop()
