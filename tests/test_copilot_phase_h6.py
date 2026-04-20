"""Phase H6 backend tests.

Covers the three implementation-side features shipped in H6:

* **H6.1 — MCP server**: ``TwkHttpClient`` HTTP wrapper against an
  in-process ASGI app, tool registry shape, ``dispatch_tool`` smoke.
* **H6.3 — OTEL bridge**: ``CopilotOtelBridge`` spans + events via an
  in-memory exporter; tracer fan-out to the bridge.
* **H6.4 — Economy dashboards**: ``build_price_table`` +
  ``build_route_table`` pure functions plus the ``/api/economy/prices``
  and ``/api/economy/routes`` endpoints.

The two *plan-only* H6 deliverables (H6.2 local STT, H6.5 multi-human
multiplayer) are documentation-only and have no runtime surface to
test.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from tw2k.copilot.dashboards import build_price_table, build_route_table
from tw2k.copilot.trace import CopilotTracer
from tw2k.engine import GameConfig

# ===========================================================================
# Shared match fixtures (mirrors the H5 test helpers)
# ===========================================================================


def _app_with_human() -> FastAPI:
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


# ===========================================================================
# H6.1 — MCP server
# ===========================================================================


def test_mcp_module_imports_without_mcp_package() -> None:
    """Importing the module must not require the soft `mcp` dep."""
    # The test environment may or may not have `mcp` installed; either
    # way the module body itself must be importable (dispatch_tool, the
    # HTTP client, and the spec list are all SDK-free).
    from tw2k import mcp_server

    assert hasattr(mcp_server, "TwkHttpClient")
    assert hasattr(mcp_server, "MCP_TOOL_SPECS")
    assert callable(mcp_server.dispatch_tool)


def test_mcp_tool_registry_shape() -> None:
    from tw2k.mcp_server import MCP_TOOL_SPECS, tool_names

    names = tool_names()
    # 14 tools as documented in the module header.
    assert len(names) == 14
    # Each tool has the fields the FastMCP adapter and the unit tests
    # both depend on.
    for spec in MCP_TOOL_SPECS:
        assert set(spec).issuperset({"name", "description", "input_schema", "fn"})
        assert spec["name"].startswith("tw2k_")
        assert callable(spec["fn"])
        assert isinstance(spec["description"], str) and spec["description"]
        schema = spec["input_schema"]
        assert schema["type"] == "object"
    # Tool names must be unique.
    assert len(set(names)) == len(names)


@pytest.mark.asyncio
async def test_mcp_http_client_roundtrip_against_asgi(tmp_path: Path) -> None:
    """The HTTP client must drive the real /api/* surface end-to-end."""
    from tw2k.mcp_server import TwkHttpClient, dispatch_tool

    app = _app_with_human()
    try:
        await _start_match(app, tmp_path)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as raw:
            client = TwkHttpClient(base_url="http://test", client=raw)

            humans = await dispatch_tool("tw2k_list_humans", {}, client=client)
            assert isinstance(humans, dict)
            ids = {h["player_id"] for h in humans.get("humans", [])}
            assert "P2" in ids

            obs = await dispatch_tool(
                "tw2k_get_observation", {"player_id": "P2"}, client=client
            )
            assert isinstance(obs, dict)
            assert "sector" in obs or "self_id" in obs

            state = await dispatch_tool(
                "tw2k_get_copilot_state", {"player_id": "P2"}, client=client
            )
            assert state.get("mode") in (
                "manual",
                "advisory",
                "delegated",
                "autopilot",
            )

            # Memory remember/forget round-trip via MCP dispatch.
            r = await dispatch_tool(
                "tw2k_remember",
                {"player_id": "P2", "key": "prefers", "value": "organics"},
                client=client,
            )
            assert r["memory"]["preferences"]["prefers"] == "organics"

            r = await dispatch_tool(
                "tw2k_forget",
                {"player_id": "P2", "key": "prefers"},
                client=client,
            )
            assert r["existed"] is True

            mem = await dispatch_tool(
                "tw2k_get_memory", {"player_id": "P2"}, client=client
            )
            assert "preferences" in mem

            whatif = await dispatch_tool(
                "tw2k_get_whatif", {"player_id": "P2"}, client=client
            )
            assert whatif.get("pending") is False

            safety = await dispatch_tool(
                "tw2k_get_safety", {"player_id": "P2"}, client=client
            )
            assert isinstance(safety, dict)

            hints = await dispatch_tool(
                "tw2k_get_hints", {"player_id": "P2"}, client=client
            )
            assert "hints" in hints

            # set_mode should flip the session mode.
            await dispatch_tool(
                "tw2k_set_mode",
                {"player_id": "P2", "mode": "advisory"},
                client=client,
            )
            state2 = await dispatch_tool(
                "tw2k_get_copilot_state", {"player_id": "P2"}, client=client
            )
            assert state2["mode"] == "advisory"
    finally:
        await app.state.runner.stop()


@pytest.mark.asyncio
async def test_mcp_dispatch_tool_raises_on_unknown_name() -> None:
    from tw2k.mcp_server import TwkHttpClient, dispatch_tool

    client = TwkHttpClient(base_url="http://irrelevant")
    with pytest.raises(KeyError):
        await dispatch_tool("tw2k_nope", {}, client=client)


def test_mcp_client_bearer_header() -> None:
    from tw2k.mcp_server import TwkHttpClient

    c = TwkHttpClient(base_url="http://x", token="sekrit")
    headers = c._headers()
    assert headers["authorization"] == "Bearer sekrit"
    c2 = TwkHttpClient(base_url="http://x", token="")
    assert "authorization" not in c2._headers()


# ===========================================================================
# H6.3 — OTEL bridge
# ===========================================================================


@pytest.fixture
def otel_memory_exporter():
    """Install an in-memory OTEL span exporter scoped to the test.

    OTEL's ``set_tracer_provider`` can only fire once per process, so
    the fixture cooperates with that reality: on first use it installs
    a ``TracerProvider`` and attaches a ``SimpleSpanProcessor`` feeding
    an ``InMemorySpanExporter``. Subsequent tests reuse the same
    provider, clear the exporter, and mark the bridge module's "ready"
    flag so ``build_bridge`` doesn't try to re-install. Requires
    ``opentelemetry-sdk``; the test is skipped when that's missing.
    """
    otel_api = pytest.importorskip("opentelemetry")
    pytest.importorskip("opentelemetry.sdk")

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from tw2k.copilot import otel as otel_bridge_mod

    current = trace.get_tracer_provider()
    if not isinstance(current, TracerProvider):
        # Fresh process — install our own provider. Only happens once.
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    else:
        provider = current

    exporter = InMemorySpanExporter()
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)

    # Tell the bridge module that the provider is already wired so it
    # doesn't try to add its own OTLP exporter on top of ours.
    otel_bridge_mod._PROVIDER_READY = True

    yield exporter

    exporter.clear()
    _ = otel_api  # pin the skip check


@pytest.mark.asyncio
async def test_otel_bridge_emits_session_span_and_events(
    otel_memory_exporter,
) -> None:
    from tw2k.copilot.otel import build_bridge

    bridge = build_bridge(player_id="P1", force=True)
    assert bridge is not None and bridge.enabled

    bridge.emit_event("chat_utterance", {"text": "hello", "mode": "manual"})
    bridge.emit_event(
        "action_dispatched",
        {"tool": "warp", "args": {"target": 42}, "ok": True, "reason": ""},
    )
    bridge.emit_action_span(
        tool="warp", args={"target": 42}, ok=True, reason=""
    )
    bridge.shutdown()

    spans = otel_memory_exporter.get_finished_spans()
    names = [s.name for s in spans]
    assert "copilot.session" in names
    assert any(n.startswith("copilot.action.") for n in names)

    session_span = next(s for s in spans if s.name == "copilot.session")
    event_names = {ev.name for ev in session_span.events}
    assert {"chat_utterance", "action_dispatched"}.issubset(event_names)


@pytest.mark.asyncio
async def test_tracer_fans_out_to_otel_bridge(otel_memory_exporter) -> None:
    from tw2k.copilot.otel import build_bridge

    bridge = build_bridge(player_id="P1", force=True)
    assert bridge is not None
    tracer = CopilotTracer(player_id="P1", otel_bridge=bridge)
    # Root dir is None, so JSONL sink is disabled — but tracer should
    # still be "enabled" because the OTEL bridge is live.
    assert tracer._enabled is True

    await tracer.emit("chat_utterance", {"text": "hi"})
    await tracer.emit(
        "action_dispatched",
        {"tool": "scan", "args": {}, "ok": True, "reason": "ok"},
    )
    tracer.shutdown()

    spans = otel_memory_exporter.get_finished_spans()
    sess = next(s for s in spans if s.name == "copilot.session")
    events = {ev.name for ev in sess.events}
    assert "chat_utterance" in events
    assert "action_dispatched" in events
    # action_dispatched also yields a discrete child span.
    assert any(s.name == "copilot.action.scan" for s in spans)


def test_build_bridge_none_without_env_or_force(monkeypatch) -> None:
    from tw2k.copilot.otel import ENV_CONSOLE, ENV_ENDPOINT, build_bridge

    monkeypatch.delenv(ENV_ENDPOINT, raising=False)
    monkeypatch.delenv(ENV_CONSOLE, raising=False)
    assert build_bridge(player_id="P1") is None
    assert build_bridge(player_id="P1", force=False) is None


def test_tracer_without_bridge_or_root_is_noop() -> None:
    t = CopilotTracer(player_id="P1", root_dir=None, enable=False)
    assert t._enabled is False

    async def _run() -> None:
        await t.emit("anything", {"foo": "bar"})
        assert t.ring() == []

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_run())


# ===========================================================================
# H6.4 — Economy dashboards
# ===========================================================================


def _make_universe_with_known_ports():
    """Build a tiny universe where P1 has scouted two trading ports.

    ``generate_universe`` ships the empty universe; we add a single
    player manually (same pattern the engine tests use) and then seed
    their ``known_ports`` dict so the dashboard has data to work with.
    """
    from tw2k.engine import generate_universe
    from tw2k.engine.models import Player, Ship

    u = generate_universe(GameConfig(seed=42, universe_size=60))
    port_sids = [sid for sid, s in u.sectors.items() if s.port is not None][:4]
    assert len(port_sids) >= 2, "seed must have at least 2 ports in 60 sectors"
    player = Player(
        id="P1", name="Tester", ship=Ship(holds=40), sector_id=port_sids[0]
    )
    u.players["P1"] = player
    for sid in port_sids:
        port = u.sectors[sid].port
        player.known_ports[sid] = {
            "class": port.code,
            "stock": {
                c.value: {"current": s.current, "max": s.maximum}
                for c, s in port.stock.items()
            },
            "last_seen_day": u.day,
        }
    return u, player, port_sids


def test_dashboard_price_table_shape() -> None:
    u, player, port_sids = _make_universe_with_known_ports()
    table = build_price_table(u, player.id)
    assert table["player_id"] == player.id
    assert table["day"] == u.day
    assert set(table["commodities"]) == {"fuel_ore", "organics", "equipment"}
    sectors_in_table = {p["sector_id"] for p in table["ports"]}
    assert sectors_in_table == set(port_sids)
    # Each port row carries per-commodity prices when the port trades
    # that commodity, with valid side labels.
    for row in table["ports"]:
        for cname, entry in row["prices"].items():
            assert entry["side"] in ("buy", "sell")
            assert entry["price"] > 0
            assert 0.0 <= entry["pct"] <= 1.0


def test_dashboard_route_table_ranks_by_profit_per_turn() -> None:
    u, player, port_sids = _make_universe_with_known_ports()
    table = build_route_table(u, player.id, max_routes=10)
    assert table["player_id"] == player.id
    assert table["known_ports"] == len(port_sids)
    routes = table["routes"]
    # All route entries have positive profit + well-formed fields.
    for r in routes:
        assert r["profit_per_unit"] > 0
        assert r["qty"] > 0
        assert r["turns"] >= 2
        assert r["from_sector"] in port_sids
        assert r["to_sector"] in port_sids
        assert r["commodity"] in {"fuel_ore", "organics", "equipment"}
    # Results are sorted descending by profit_per_turn.
    ppt = [r["profit_per_turn"] for r in routes]
    assert ppt == sorted(ppt, reverse=True)


def test_dashboard_route_table_empty_with_one_port() -> None:
    from tw2k.engine import generate_universe
    from tw2k.engine.models import Player, Ship

    u = generate_universe(GameConfig(seed=42, universe_size=40))
    port_sid = next(sid for sid, s in u.sectors.items() if s.port is not None)
    player = Player(id="P1", name="Solo", ship=Ship(holds=40), sector_id=port_sid)
    u.players["P1"] = player
    player.known_ports[port_sid] = {
        "class": u.sectors[port_sid].port.code,
        "stock": {},
        "last_seen_day": u.day,
    }
    table = build_route_table(u, player.id)
    assert table["routes"] == []


@pytest.mark.asyncio
async def test_api_economy_prices_endpoint(tmp_path: Path) -> None:
    app = _app_with_human()
    try:
        await _start_match(app, tmp_path)
        # Seed known_ports on P2 so the dashboard has something to show.
        u = app.state.runner.state.universe
        player = u.players["P2"]
        sids = [sid for sid, s in u.sectors.items() if s.port is not None][:2]
        for sid in sids:
            port = u.sectors[sid].port
            player.known_ports[sid] = {
                "class": port.code,
                "stock": {
                    c.value: {"current": s.current, "max": s.maximum}
                    for c, s in port.stock.items()
                },
                "last_seen_day": u.day,
            }
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            r = await client.get("/api/economy/prices?player_id=P2")
            assert r.status_code == 200
            j = r.json()
            assert j["player_id"] == "P2"
            # The runner seeds the start sector + adjacents as
            # known_ports too, so the table should contain AT LEAST
            # the extra ports we added on top of that baseline.
            returned_sids = {p["sector_id"] for p in j["ports"]}
            for sid in sids:
                assert sid in returned_sids

            r = await client.get("/api/economy/prices?player_id=P99")
            assert r.status_code == 404
    finally:
        await app.state.runner.stop()


@pytest.mark.asyncio
async def test_api_economy_routes_endpoint(tmp_path: Path) -> None:
    app = _app_with_human()
    try:
        await _start_match(app, tmp_path)
        u = app.state.runner.state.universe
        player = u.players["P2"]
        sids = [sid for sid, s in u.sectors.items() if s.port is not None][:4]
        for sid in sids:
            port = u.sectors[sid].port
            player.known_ports[sid] = {
                "class": port.code,
                "stock": {},
                "last_seen_day": u.day,
            }
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            r = await client.get(
                "/api/economy/routes?player_id=P2&max_routes=3"
            )
            assert r.status_code == 200
            j = r.json()
            assert j["player_id"] == "P2"
            assert len(j["routes"]) <= 3
            # max_routes is clamped to [1, 50] even on malformed input.
            r = await client.get("/api/economy/routes?player_id=P2&max_routes=0")
            assert r.status_code == 200
    finally:
        await app.state.runner.stop()
