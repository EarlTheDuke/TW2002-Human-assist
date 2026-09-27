"""Grokbot-player G4 - reach + turn cadence for a human-speed player.

docs/plans/2026-09-26-grokbot-plays-by-screen.md (G4):
* per-seat external deadlines (600 s computer-use seat next to fast bots), LLM seats unaffected;
* turn_due webhook: seat, turn_seq, deadline_at, public /bot URL; no observation dump, no token;
  retry with backoff; deliveries logged;
* hold-my-slot: chain several actions in one scheduler slot, end it explicitly;
* -Tunnel host switch + watchdog health lines + seat-link refresh.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from tw2k.agents import external as external_mod
from tw2k.engine import GameConfig
from tw2k.engine.models import EventKind
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

ROOT = Path(__file__).resolve().parents[1]
TOK2 = "g4-token-p2-0000000000000000000"
TOK3 = "g4-token-p3-0000000000000000000"


def _spec(p2_timeout: float | None = None, hold_max: int = 10, third: bool = False) -> MatchSpec:
    agents = [AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
              AgentSpec(player_id="P2", name="Seat2", kind="external", external_token=TOK2, external_timeout_s=p2_timeout)]
    if third:
        agents.append(AgentSpec(player_id="P3", name="Seat3", kind="external", external_token=TOK3))
    return MatchSpec(
        config=GameConfig(seed=9, universe_size=60, max_days=2, turns_per_day=30, starting_credits=25_000,
                          enable_ferrengi=False, enable_planets=False, action_delay_s=0.0),
        agents=agents, action_delay_s=0.0, external_timeout_s=30.0, external_hold_max_actions=hold_max,
    )


def _run(tmp_path: Path, spec: MatchSpec, body) -> None:
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"

    async def go() -> None:
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5555)), base_url="http://g4.test")
        await runner.start(spec)
        for _ in range(300):
            if runner.state.agents and runner.state.universe is not None:
                break
            await asyncio.sleep(0.02)
        try:
            await body(client, runner)
        finally:
            await runner.stop()
            await client.aclose()

    asyncio.run(go())


async def _until(pred, tries: int = 400, dt: float = 0.02) -> bool:
    for _ in range(tries):
        if await pred():
            return True
        await asyncio.sleep(dt)
    return await pred()


def _auth(tok: str = TOK2) -> dict[str, str]:
    return {"authorization": f"Bearer {tok}"}


async def _status(client, seat: str = "P2", tok: str = TOK2) -> dict:
    return (await client.get(f"/harness/v1/{seat}/status", headers=_auth(tok))).json()


# ------------------------------------------------------------------ per-seat timeouts
def test_per_seat_external_deadline_is_honoured_and_reported(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)

    async def body(client, runner) -> None:
        u = runner.state.universe
        # P2 has a 0.4 s override and nobody answers: it times out fast (AGENT_ERROR) ...
        async def p2_timed_out():
            return any(e.kind is EventKind.AGENT_ERROR and e.actor_id == "P2" and e.payload.get("external_timeout")
                       for e in u.events)
        assert await _until(p2_timed_out, tries=300)
        # ... while P3 (no override) gets the match default of 30 s, reported in its status.
        async def p3_turn():
            return (await _status(client, "P3", TOK3)).get("awaiting_input")
        assert await _until(p3_turn, tries=300)
        st = await _status(client, "P3", TOK3)
        assert st["timeout_s"] == 30.0 and abs((st["deadline_at"] - st["turn_started_at"]) - 30.0) < 0.5
        assert not any(e.kind is EventKind.AGENT_ERROR and e.actor_id == "P3" for e in u.events)
        # The heuristic seat is untouched by external deadlines.
        assert not any(e.kind is EventKind.AGENT_ERROR and e.actor_id == "P1" for e in u.events)

    _run(tmp_path, _spec(p2_timeout=0.4, third=True), body)


def test_restart_body_and_cli_carry_per_seat_timeouts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    app = create_app(auto_start=False)
    app.state.runner._saves_root = tmp_path / "saves"
    body = {"num_agents": 2, "agent_kind": "heuristic", "universe_size": 60, "max_days": 1, "turns_per_day": 5,
            "external_timeout_s": 120, "external_hold_max_actions": 3,
            "agents": [{"kind": "heuristic"}, {"kind": "external", "token": TOK2, "timeout_s": 600}]}

    async def go() -> None:
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5555)), base_url="http://g4.test")
        assert (await client.post("/control/restart", json=body)).status_code == 200
        spec = app.state.runner._spec
        assert spec.external_timeout_s == 120 and spec.external_hold_max_actions == 3
        assert [a.external_timeout_s for a in spec.agents] == [None, 600.0]
        for _ in range(200):
            if app.state.runner.state.agents:
                break
            await asyncio.sleep(0.02)
        ext = next(a for a in app.state.runner.state.agents if a.player_id == "P2")
        assert ext.timeout_s == 600.0 and ext.hold_max == 3
        await app.state.runner.stop()
        await client.aclose()

    asyncio.run(go())
    import inspect

    from tw2k import cli

    opt = inspect.signature(cli.serve).parameters["external_seat_timeouts"].default
    assert "--external-seat-timeouts" in opt.param_decls


# ------------------------------------------------------------------ webhook
def test_turn_due_webhook_payload_retry_and_delivery_log(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TW2K_GROKBOT_WEBHOOK_URL", "https://hook.test/turn?key=SECRET-IN-QUERY")
    monkeypatch.setenv("TW2K_PUBLIC_BASE_URL", "https://public.example/")
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_FULL_OBS", raising=False)
    monkeypatch.setattr(external_mod, "WEBHOOK_RETRY_DELAYS_S", (0.01, 0.01, 0.01))
    calls: list[dict] = []
    real_client = httpx.AsyncClient

    class FlakyClient:
        def __new__(cls, *a, **k):
            if "transport" in k:  # the test's own ASGI client
                return real_client(*a, **k)
            return super().__new__(cls)

        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json=None, **k):
            calls.append(json)
            return httpx.Response(503 if len(calls) <= 2 else 200)

    monkeypatch.setattr(httpx, "AsyncClient", FlakyClient)

    async def body(client, runner) -> None:
        agent = next(a for a in runner.state.agents if a.player_id == "P2")
        async def delivered():
            return any(e["ok"] for e in agent.webhook_log)
        assert await _until(delivered, tries=300)
        p = calls[0]
        assert p["seat"] == "P2" and p["turn_seq"] >= 1 and p["deadline_at"] > p["started_at"]
        assert p["bot_url"] == "https://public.example/bot?seat=P2&mode=cu"
        assert "observation" not in p and TOK2 not in json.dumps(p) and "token" not in p
        attempts = [(e["attempt"], e["status"]) for e in agent.webhook_log if e["turn_seq"] == p["turn_seq"]]
        assert attempts[:3] == [(1, 503), (2, 503), (3, 200)]
        assert all(e["target"] == "https://hook.test" for e in agent.webhook_log), "path/query secrets never logged"
        log_file = runner.state.save_dir / "webhook_deliveries.jsonl"
        rows = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
        assert rows and rows[0]["seat"] == "P2" and "SECRET" not in log_file.read_text(encoding="utf-8")
        # The seat can see its own recent deliveries in status.
        st = await _status(client)
        assert st["webhook"] and st["webhook"][-1]["ok"] is True

    _run(tmp_path, _spec(), body)


def test_webhook_retry_stops_when_the_turn_moves_on(monkeypatch) -> None:
    monkeypatch.setattr(external_mod, "WEBHOOK_RETRY_DELAYS_S", (0.01, 0.01, 0.01))
    agent = external_mod.ExternalAgent("P2", "Seat2", token=TOK2)
    agent.turn_seq, agent.awaiting_input = 5, True

    class Down:
        async def post(self, url, json=None, **k):
            agent.turn_seq = 6  # the seat acted (or timed out) meanwhile
            raise httpx.ConnectError("down")

    asyncio.run(agent._deliver(Down(), "http://hook.test/x", {"turn_seq": 5}, 5))
    assert [(e["attempt"], e["error"]) for e in agent.webhook_log] == [(1, "ConnectError")]


# ------------------------------------------------------------------ hold my slot
def test_hold_slot_chains_actions_then_ends_without_spending_a_turn(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)

    async def body(client, runner) -> None:
        u = runner.state.universe
        p1, p2 = u.players["P1"], u.players["P2"]

        async def my_turn():
            return (await _status(client)).get("awaiting_input")
        assert await _until(my_turn)
        r = await client.post("/harness/v1/P2/hold", json={"hold": True}, headers=_auth())
        assert r.status_code == 200 and r.json()["hold"] is True and r.json()["max"] == 10
        p1_before = p1.turns_today
        for _ in range(3):
            st = await _status(client)
            post = await client.post("/harness/v1/P2/action", headers=_auth(),
                                     json={"turn_seq": st["turn_seq"], "action": {"kind": "scan", "args": {}}})
            assert post.status_code == 200
            async def next_held_turn(seq=st["turn_seq"]):
                s = await _status(client)
                return s.get("awaiting_input") and s["turn_seq"] == seq + 1
            assert await _until(next_held_turn), "held seat did not get the next action immediately"
        assert p1.turns_today == p1_before, "another seat acted inside the held slot"
        assert (await _status(client))["hold"] == {"on": True, "used": 3, "max": 10}
        p2_turns = p2.turns_today
        r = await client.post("/harness/v1/P2/hold", json={"hold": False}, headers=_auth())
        assert r.json()["released"] is True
        async def moved_on():
            return p1.turns_today > p1_before
        assert await _until(moved_on), "slot did not end"
        assert p2.turns_today == p2_turns, "ending the slot must not spend a turn"
        assert not any(e.kind is EventKind.AGENT_ERROR and e.actor_id == "P2" for e in u.events)

    _run(tmp_path, _spec(), body)


def test_hold_slot_cap_and_idle_release(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)

    async def body(client, runner) -> None:
        u = runner.state.universe
        p1, p2 = u.players["P1"], u.players["P2"]
        async def my_turn():
            return (await _status(client)).get("awaiting_input")
        assert await _until(my_turn)
        p1_before = p1.turns_today
        st = await _status(client)
        # hold can ride along with an action
        assert (await client.post("/harness/v1/P2/action", headers=_auth(), json={
            "turn_seq": st["turn_seq"], "action": {"kind": "scan", "args": {}}, "hold": True})).status_code == 200
        async def held():
            s = await _status(client)
            return s.get("awaiting_input") and s["hold"]["used"] == 1
        assert await _until(held)
        # cap = 1 extra action: after this one the slot ends even though hold is on.
        st = await _status(client)
        await client.post("/harness/v1/P2/action", headers=_auth(), json={"turn_seq": st["turn_seq"], "action": {"kind": "scan", "args": {}}})
        async def p1_moved():
            return p1.turns_today > p1_before
        assert await _until(p1_moved), "hold cap not enforced"
        # Next P2 turn: hold still on -> act once, then leave the held turn idle past the 1 s deadline.
        assert await _until(my_turn)
        st = await _status(client)
        await client.post("/harness/v1/P2/action", headers=_auth(), json={"turn_seq": st["turn_seq"], "action": {"kind": "scan", "args": {}}})
        assert await _until(held)
        turns = p2.turns_today
        async def released():
            s = await _status(client)
            return s["hold"]["on"] is False and not (s.get("awaiting_input") and s["hold"]["used"])
        assert await _until(released, tries=200, dt=0.05)
        assert p2.turns_today == turns, "idle held turn must not auto-WAIT"
        assert not any(e.kind is EventKind.AGENT_ERROR and e.actor_id == "P2" for e in u.events)

    _run(tmp_path, _spec(p2_timeout=1.0, hold_max=1), body)


def test_hold_disabled_is_409(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)

    async def body(client, runner) -> None:
        r = await client.post("/harness/v1/P2/hold", json={"hold": True}, headers=_auth())
        assert r.status_code == 409 and r.json()["detail"] == "hold_disabled"

    _run(tmp_path, _spec(hold_max=0), body)


# ------------------------------------------------------------------ cockpit + host scripts
def test_cu_hold_control_and_host_scripts() -> None:
    js = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")
    html = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")
    parity = (ROOT / "web" / "bot-parity.js").read_text(encoding="utf-8")
    assert 'data-testid="cu-hold"' in html and '{ key: "H"' in parity
    assert "/hold`" in js and "h: () => toggleHold()" in js
    ps1 = (ROOT / "scripts" / "run_hosted_grokbot.ps1").read_text(encoding="utf-8")
    assert "[switch]$Tunnel" in ps1 and "scripts/tunnel_watchdog.ps1" in ps1
    assert "[int]$ExternalTimeoutS = 600" in ps1 and "--external-seat-timeouts" in ps1
    wd = (ROOT / "scripts" / "tunnel_watchdog.ps1").read_text(encoding="utf-8")
    assert "health ok" in wd and "scripts/write_seat_links.py" in wd


@pytest.mark.parametrize("seat", ["P2"])
def test_status_lobby_stays_fog_safe_with_new_fields(tmp_path: Path, seat: str, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)

    async def body(client, runner) -> None:
        lobby = (await client.get("/harness/v1/seats", headers=_auth())).json()
        for s in lobby["seats"]:
            assert "hold" not in s and "webhook" not in s  # siblings never see these
        assert (await client.get("/harness/v1/P3/status", headers=_auth())).status_code == 403

    _run(tmp_path, _spec(third=True), body)
