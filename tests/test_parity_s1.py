"""Parity S1 - server data + fog fixes (docs/plans/2026-09-21-bot-human-parity.md).

1. Observation peek between turns (fog-safe: own seat only).
2. Fogged event stream with seq cursor + per-kind `facts` whitelist.
3. Spectator gate (TW2K_SPECTATOR_TOKEN) on whole-galaxy routes; /bot + harness stay open.
4. xAI seat script refuses to run without --allow-xai-fallback.
5. Webhook turn_due payload: effective deadline from the runner, base_url, no fat Observation.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from tw2k.agents.external import ExternalAgent
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import EventKind as EK
from tw2k.engine.models import Player
from tw2k.engine.observation import (
    EVENT_FACTS,
    _event_visible_to,
    build_observation,
    event_facts,
    event_view,
)
from tw2k.server.app import create_app
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec
from tw2k.server.spectator_gate import is_gated_path

ROOT = Path(__file__).resolve().parents[1]
TOK2 = "s1-token-p2-00000000000000"
TOK3 = "s1-token-p3-00000000000000"


def _spec(**cfg_over) -> MatchSpec:
    cfg = GameConfig(
        seed=5,
        universe_size=60,
        max_days=2,
        turns_per_day=12,
        starting_credits=25_000,
        enable_ferrengi=False,
        enable_planets=False,
        action_delay_s=0.0,
        **cfg_over,
    )
    return MatchSpec(
        config=cfg,
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="SeatTwo", kind="external", external_token=TOK2),
            AgentSpec(player_id="P3", name="SeatThree", kind="external", external_token=TOK3),
        ],
        action_delay_s=0.0,
        external_timeout_s=30.0,
        external_idle_wait_s=0.0,
    )


async def _until(pred, *, tries: int = 300, dt: float = 0.02) -> bool:
    for _ in range(tries):
        if pred():
            return True
        await asyncio.sleep(dt)
    return pred()


def _client(app, host: str = "127.0.0.1") -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=(host, 5555)), base_url="http://s1.test"
    )


def _auth(tok: str) -> dict[str, str]:
    return {"authorization": f"Bearer {tok}"}


# ---------------------------------------------------------------------------
# 2. Event view / facts whitelist (engine level)
# ---------------------------------------------------------------------------


def test_event_view_whitelists_facts_and_never_leaks_private_keys() -> None:
    cfg = GameConfig(seed=1, universe_size=40, max_days=2, turns_per_day=10)
    u = generate_universe(cfg)
    u.players["P1"] = Player(id="P1", name="A", agent_kind="external")
    ev = u.emit(
        EK.TRADE,
        actor_id="P1",
        sector_id=1,
        payload={
            "commodity": "fuel_ore", "qty": 5, "side": "sell", "unit": 20, "total": 100,
            "realized_profit": 15, "note": "internal", "_witnesses": ["P1", "P2"],
        },
        summary="A sold 5 fuel_ore",
    )
    view = event_view(ev)
    assert view["summary"] == "A sold 5 fuel_ore"
    assert view["kind"] == "trade" and view["actor_kind"] == "external"
    assert view["facts"] == {
        "commodity": "fuel_ore", "qty": 5, "side": "sell", "unit": 20, "total": 100, "realized_profit": 15
    }
    assert "note" not in view["facts"] and "_witnesses" not in view["facts"]

    # Scan carries bulky neighbour intel in the payload; only the tier ships.
    ev2 = u.emit(EK.SCAN, actor_id="P1", sector_id=1, payload={"tier": "basic", "neighbors": [{"id": 2}]}, summary="scan")
    assert event_facts(ev2) == {"tier": "basic"}

    # Kinds with no whitelist entry ship summary only.
    ev3 = u.emit(EK.LLM_USAGE, actor_id="P1", payload={"input_tokens": 999}, summary="usage")
    assert event_facts(ev3) == {}
    # Every whitelist key is a plain string and never underscore-prefixed.
    for kind, keys in EVENT_FACTS.items():
        assert isinstance(kind, EK)
        assert all(isinstance(k, str) and not k.startswith("_") for k in keys), kind


def test_recent_events_in_observation_carry_facts() -> None:
    cfg = GameConfig(seed=1, universe_size=40, max_days=2, turns_per_day=10)
    u = generate_universe(cfg)
    u.players["P1"] = Player(id="P1", name="A", agent_kind="external", sector_id=1)
    u.sectors[1].occupant_ids.append("P1")
    u.emit(EK.WARP, actor_id="P1", sector_id=1, payload={"from": 3, "to": 1, "_witnesses": ["P1"]}, summary="w")
    obs = build_observation(u, "P1")
    warp = next(e for e in obs.recent_events if e["kind"] == "warp")
    assert warp["facts"] == {"from": 3, "to": 1}
    assert "actor_kind" not in warp  # LLM shape stays lean


# ---------------------------------------------------------------------------
# 1 + 2. Peek and event stream over HTTP
# ---------------------------------------------------------------------------


def test_peek_returns_own_observation_between_turns_and_events_stream_is_fogged(tmp_path: Path) -> None:
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"
    client = _client(app)

    async def _go() -> None:
        await runner.start(_spec())
        assert await _until(lambda: bool(runner.state.agents) and runner.state.universe is not None)
        u = runner.state.universe
        assert u is not None
        p2 = next(a for a in runner.state.agents if a.player_id == "P2")
        p3 = next(a for a in runner.state.agents if a.player_id == "P3")
        assert isinstance(p2, ExternalAgent) and isinstance(p3, ExternalAgent)
        # Scheduler order P1 -> P2 -> P3: P2 blocks first, so P3 is NOT awaiting.
        assert await _until(lambda: p2.awaiting_input, tries=200)
        assert not p3.awaiting_input

        # Without peek: null observation for the non-awaiting seat (legacy).
        r = await client.get("/harness/v1/P3/observation", headers=_auth(TOK3))
        assert r.status_code == 200 and r.json()["observation"] is None and r.json()["peek"] is False

        # With peek: a full fogged Observation for P3, awaiting still false.
        r = await client.get("/harness/v1/P3/observation", params={"peek": 1, "format": "both"}, headers=_auth(TOK3))
        body = r.json()
        assert body["peek"] is True and body["awaiting_input"] is False
        obs = body["observation"]
        assert obs["self_id"] == "P3" and "sector" in obs and "known_ports" in obs
        assert isinstance(body["llm_user_message"], str)
        assert p3.awaiting_input is False and p3.turn_seq == 0  # peek did not touch turn state

        # Peek for the awaiting seat returns its bound observation (peek flag false).
        r = await client.get("/harness/v1/P2/observation", params={"peek": 1}, headers=_auth(TOK2))
        assert r.json()["peek"] is False and r.json()["observation"]["self_id"] == "P2"

        # Drive a couple of turns so there are events to stream.
        target = obs_target = None
        obs2 = p2.current_observation
        assert obs2 is not None
        target = obs2.sector["warps_out"][0]
        await p2.submit_action(Action(kind=ActionKind.WARP, args={"target": target}), turn_seq=p2.turn_seq)
        assert await _until(lambda: p3.awaiting_input, tries=200)
        obs_target = p3.current_observation.sector["warps_out"][0]  # type: ignore[union-attr]
        await p3.submit_action(Action(kind=ActionKind.WARP, args={"target": obs_target}), turn_seq=p3.turn_seq)
        assert await _until(lambda: p2.awaiting_input and p2.turn_seq >= 2, tries=200)

        # Event stream for P2: every event must pass the fog rule for P2,
        # carry a summary, and have only whitelisted facts keys.
        r = await client.get("/harness/v1/P2/events", params={"since": 0, "limit": 500}, headers=_auth(TOK2))
        assert r.status_code == 200
        stream = r.json()
        assert stream["player_id"] == "P2" and stream["events"]
        seqs = [e["seq"] for e in stream["events"]]
        assert seqs == sorted(seqs)
        by_seq = {e.seq: e for e in u.events}
        for ev in stream["events"]:
            real = by_seq[ev["seq"]]
            assert _event_visible_to(real, "P2", u), f"leaked seq {ev['seq']} kind {ev['kind']}"
            assert isinstance(ev["summary"], str) and ev["summary"]
            allowed = set(EVENT_FACTS.get(real.kind, ()))
            assert set(ev["facts"]) <= allowed, (ev["kind"], ev["facts"])
            assert not any(k.startswith("_") for k in ev["facts"])
        # P2 must see its own warp but never P3's (P3 warped from a sector P2 was not in).
        kinds_actors = {(e["kind"], e["actor_id"]) for e in stream["events"]}
        assert ("warp", "P2") in kinds_actors
        p3_warps_visible = [e for e in stream["events"] if e["kind"] == "warp" and e["actor_id"] == "P3"]
        for e in p3_warps_visible:
            assert _event_visible_to(by_seq[e["seq"]], "P2", u)
        # Cursor semantics: page forward from the first visible seq.
        assert len(seqs) >= 2, seqs
        first = seqs[0]
        r2 = await client.get("/harness/v1/P2/events", params={"since": first, "limit": 2}, headers=_auth(TOK2))
        page = r2.json()
        assert page["events"] and all(e["seq"] > first for e in page["events"]) and len(page["events"]) <= 2
        assert page["next_since"] == page["events"][-1]["seq"]
        assert page["latest_seq"] == u.events[-1].seq
        # Past the end: empty page, cursor unchanged.
        r3 = await client.get("/harness/v1/P2/events", params={"since": u.events[-1].seq}, headers=_auth(TOK2))
        assert r3.json()["events"] == [] and r3.json()["next_since"] == u.events[-1].seq
        # Cross-seat token still refused on the new routes.
        r = await client.get("/harness/v1/P3/events", headers=_auth(TOK2))
        assert r.status_code == 403
        r = await client.get("/harness/v1/P3/observation", params={"peek": 1}, headers=_auth(TOK2))
        assert r.status_code == 403

        await runner.stop()
        await client.aclose()

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# 3. Spectator gate
# ---------------------------------------------------------------------------


def test_gated_path_table() -> None:
    for p in ("/", "/state", "/events", "/history", "/highlights", "/ws", "/play", "/control/restart", "/api/cost", "/api/human/observation"):
        assert is_gated_path(p), p
    for p in ("/bot", "/static/bot.js", "/harness/v1/P3/status", "/harness/v1/rules", "/spectate"):
        assert not is_gated_path(p), p


def test_spectator_gate_blocks_without_token_and_accepts_header_query_cookie(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TW2K_SPECTATOR_TOKEN", "spec-secret-123456789")
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"
    client = _client(app)

    async def _go() -> None:
        await runner.start(_spec())
        assert await _until(lambda: bool(runner.state.agents) and runner.state.universe is not None)

        for p in ("/", "/state", "/events", "/history", "/highlights", "/api/cost", "/play"):
            r = await client.get(p)
            assert r.status_code == 401, p
        r = await client.post("/control/pause")
        assert r.status_code == 401
        # Open surfaces unaffected.
        assert (await client.get("/bot")).status_code == 200
        assert (await client.get("/static/bot.js")).status_code == 200
        r = await client.get("/harness/v1/P2/status", headers=_auth(TOK2))
        assert r.status_code == 200

        # Header, query, cookie all work.
        assert (await client.get("/state", headers={"authorization": "Bearer spec-secret-123456789"})).status_code == 200
        assert (await client.get("/state", params={"token": "spec-secret-123456789"})).status_code == 200
        assert (await client.get("/state", params={"token": "wrong"})).status_code == 401
        r = await client.get("/spectate", params={"token": "spec-secret-123456789"}, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/"
        assert "tw2k_spectator=spec-secret-123456789" in r.headers.get("set-cookie", "")
        cookie_client = _client(app)
        cookie_client.cookies.set("tw2k_spectator", "spec-secret-123456789")
        assert (await cookie_client.get("/state")).status_code == 200
        await cookie_client.aclose()
        assert (await client.get("/spectate", params={"token": "nope"})).status_code == 401

        await runner.stop()
        await client.aclose()

    asyncio.run(_go())


def test_spectator_gate_disabled_when_env_unset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"
    client = _client(app)

    async def _go() -> None:
        await runner.start(_spec())
        assert await _until(lambda: bool(runner.state.agents) and runner.state.universe is not None)
        assert (await client.get("/state")).status_code == 200
        r = await client.get("/spectate", follow_redirects=False)
        assert r.status_code == 303
        await runner.stop()
        await client.aclose()

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# 4. xAI seat script is gated
# ---------------------------------------------------------------------------


def test_xai_seat_script_refuses_without_explicit_flag() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "play_grok_external_seats.py"), "--seats", "P3"],
        capture_output=True,
        text=True,
        timeout=60,
        env={**__import__("os").environ, "XAI_API_KEY": "", "GROK_API_KEY": ""},
    )
    assert proc.returncode == 2
    assert "NOT a Grok Bot brain" in proc.stderr
    assert "--allow-xai-fallback" in proc.stderr


# ---------------------------------------------------------------------------
# 5. Webhook payload
# ---------------------------------------------------------------------------


def test_turn_due_payload_uses_runner_deadline_and_omits_full_observation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_FULL_OBS", raising=False)
    monkeypatch.setenv("TW2K_PUBLIC_BASE_URL", "https://example-tunnel.test/")
    cfg = GameConfig(seed=1, universe_size=40, max_days=2, turns_per_day=10)
    u = generate_universe(cfg)
    u.players["P3"] = Player(id="P3", name="Bot", agent_kind="external", sector_id=1)
    u.sectors[1].occupant_ids.append("P3")
    obs = build_observation(u, "P3")

    agent = ExternalAgent("P3", "Bot", token="t")
    agent.turn_seq = 7
    agent.turn_started_at = 1000.0
    agent.turn_deadline_at = 1008.0  # runner-effective (idle rule), not the 180s env default
    payload = agent.turn_due_payload(obs)
    assert payload["event"] == "turn_due" and payload["player_id"] == "P3" and payload["turn_seq"] == 7
    assert payload["deadline_at"] == 1008.0 and payload["started_at"] == 1000.0
    assert payload["base_url"] == "https://example-tunnel.test"
    assert payload["observation_url"].endswith("/harness/v1/P3/observation")
    assert payload["action_url"].endswith("/harness/v1/P3/action")
    assert payload["brief"]["sector_id"] == 1 and "credits" in payload["brief"]
    assert "observation" not in payload

    monkeypatch.setenv("TW2K_GROKBOT_WEBHOOK_FULL_OBS", "1")
    assert "observation" in agent.turn_due_payload(obs)

    # Fallback when the runner never set a deadline: env timeout from started_at.
    agent.turn_deadline_at = None
    monkeypatch.setenv("TW2K_EXTERNAL_TIMEOUT_S", "42")
    assert agent.turn_due_payload(obs)["deadline_at"] == 1042.0


def test_runner_sets_effective_deadline_before_act(tmp_path: Path) -> None:
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")

    async def _go() -> None:
        spec = _spec()
        spec.external_idle_wait_s = 0.3  # unattended -> short effective deadline
        await runner.start(spec)
        assert await _until(lambda: bool(runner.state.agents) and runner.state.universe is not None)
        p2 = next(a for a in runner.state.agents if a.player_id == "P2")
        assert isinstance(p2, ExternalAgent)
        assert await _until(lambda: p2.turn_deadline_at is not None, tries=200)
        assert p2.turn_started_at is not None and p2.turn_deadline_at is not None
        eff = p2.turn_deadline_at - p2.turn_started_at
        assert 0.0 < eff <= 0.3 + 0.2, eff  # idle rule, not the 30s nominal timeout
        # A client showing up inside the idle window extends THIS turn to the
        # full budget (runner re-checks attendance) and the deadline moves out.
        p2.touch_client()
        await asyncio.sleep(0.6)  # idle window elapses; runner re-checks attendance
        assert p2.awaiting_input and p2.turn_seq == 1
        assert await _until(lambda: (p2.turn_deadline_at or 0) - time.time() > 20.0, tries=100)
        await runner.stop()

    asyncio.run(_go())
