"""Parity S6 - multi-bot ops + Path-B reference client.

* Two Path-B SeatClients (one brain each, scripted heuristic) + one unattended
  external seat + one heuristic engine seat in one match: attended seats take
  many turns with zero external timeouts / zero stale submits; the unattended
  seat idle-WAITs instead of stalling the round-robin.
* turn_due webhook fires with the lean payload (deadline from the runner,
  base_url, no full Observation) - captured by monkeypatching httpx.
* /seats is a lobby view: no sibling sector / last_result / observation.
* MailboxPolicy: decision file -> action; late brain -> safe wait.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from tw2k.agents import external as external_mod
from tw2k.agents.pathb_client import MailboxPolicy, SeatClient, TurnContext, legal_heuristic_policy, run_seats
from tw2k.engine import GameConfig
from tw2k.engine.models import EventKind
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

ROOT = Path(__file__).resolve().parents[1]
TOK = {"P2": "s6-token-p2-000000000000000", "P3": "s6-token-p3-000000000000000", "P4": "s6-token-p4-000000000000000"}


def _spec(*, idle: float = 0.4, timeout: float = 20.0) -> MatchSpec:
    cfg = GameConfig(seed=8, universe_size=70, max_days=3, turns_per_day=40, starting_credits=30_000,
                     enable_ferrengi=False, enable_planets=False, action_delay_s=0.0)
    return MatchSpec(
        config=cfg,
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="BotA", kind="external", external_token=TOK["P2"]),
            AgentSpec(player_id="P3", name="BotB", kind="external", external_token=TOK["P3"]),
            AgentSpec(player_id="P4", name="Empty", kind="external", external_token=TOK["P4"]),
        ],
        action_delay_s=0.0,
        external_timeout_s=timeout,
        external_idle_wait_s=idle,
        external_attend_window_s=3.0,
    )


async def _until(pred, *, tries: int = 400, dt: float = 0.02) -> bool:
    for _ in range(tries):
        if pred():
            return True
        await asyncio.sleep(dt)
    return pred()


def test_two_pathb_brains_plus_unattended_seat_no_stalls(tmp_path: Path) -> None:
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"

    async def _go() -> None:
        http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5555)), base_url="http://s6.test")
        await runner.start(_spec())
        assert await _until(lambda: bool(runner.state.agents) and runner.state.universe is not None)
        u = runner.state.universe
        a = SeatClient(http, "P2", TOK["P2"], legal_heuristic_policy, wait_s=5.0, safety_margin_s=1.0)
        b = SeatClient(http, "P3", TOK["P3"], legal_heuristic_policy, wait_s=5.0, safety_margin_s=1.0)
        stats = await asyncio.wait_for(run_seats([a, b], max_turns=8), timeout=120)
        assert stats["P2"].turns >= 8 and stats["P3"].turns >= 8
        assert stats["P2"].stale == 0 and stats["P3"].stale == 0
        assert stats["P2"].fallback_waits == 0 and stats["P3"].fallback_waits == 0
        # Same fogged observation the LLM seats get: rules fetched once, llm message present in the poll body.
        assert a.rules.get("system_prompt") and "warp" in (a.rules.get("verbs") or []) and len(a.rules["verbs"]) == 34
        # No external timeout errors for the attended seats; idle auto-waits only for P4.
        errs = [e for e in u.events if e.kind is EventKind.AGENT_ERROR and e.actor_id in ("P2", "P3")
                and (e.payload or {}).get("external_timeout")]
        assert not errs, [e.summary for e in errs]
        idle_waits = [e for e in u.events if e.kind is EventKind.AGENT_THOUGHT and (e.payload or {}).get("external_idle")]
        assert idle_waits and {e.actor_id for e in idle_waits} == {"P4"}
        # Attended seats spent the vast majority of their turns doing something other than wait.
        acted = sum(v for k, v in stats["P2"].kinds.items() if k != "wait") + sum(v for k, v in stats["P3"].kinds.items() if k != "wait")
        assert acted >= 10, stats
        await runner.stop()
        await http.aclose()

    asyncio.run(_go())


def test_webhook_fires_lean_payload_with_runner_deadline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TW2K_GROKBOT_WEBHOOK_URL", "http://hook.test/turn")
    monkeypatch.setenv("TW2K_PUBLIC_BASE_URL", "https://public.example/")
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_FULL_OBS", raising=False)
    captured: list[dict] = []

    class FakeClient:
        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json=None, **k):
            captured.append({"url": url, "json": json})

    # external.py imports httpx lazily inside the webhook coroutine -> patch the library symbol.
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    assert external_mod.ExternalAgent  # module under test is loaded
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"

    async def _go() -> None:
        await runner.start(_spec(idle=0.3))
        assert await _until(lambda: bool(runner.state.agents) and runner.state.universe is not None)
        assert await _until(lambda: len(captured) >= 1, tries=300)
        hook = captured[0]
        assert hook["url"] == "http://hook.test/turn"
        p = hook["json"]
        assert p["event"] == "turn_due" and p["player_id"] in ("P2", "P3", "P4") and p["turn_seq"] >= 1
        assert p["base_url"] == "https://public.example"
        assert p["observation_url"].endswith(f"/harness/v1/{p['player_id']}/observation")
        assert "observation" not in p and set(p["brief"]) >= {"day", "sector_id", "credits"}
        # Unattended seat: the deadline reflects the idle window, not the 20 s nominal timeout.
        assert 0 < p["deadline_at"] - p["started_at"] <= 0.3 + 0.2
        await runner.stop()

    asyncio.run(_go())


def test_seats_lobby_is_fog_safe(tmp_path: Path) -> None:
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"

    async def _go() -> None:
        http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5555)), base_url="http://s6.test")
        await runner.start(_spec())
        assert await _until(lambda: bool(runner.state.agents) and runner.state.universe is not None)
        r = await http.get("/harness/v1/seats", headers={"authorization": f"Bearer {TOK['P4']}"})
        assert r.status_code == 200
        body = r.json()
        assert {s["player_id"] for s in body["seats"]} == {"P2", "P3", "P4"}
        for s in body["seats"]:
            assert set(s) == {"player_id", "name", "kind", "alive", "awaiting_input", "attended", "turn_seq"}, s
        assert "current_turn" in body and "server_time" in body
        await runner.stop()
        await http.aclose()

    asyncio.run(_go())


def test_mailbox_policy_roundtrip_and_deadline_fallback(tmp_path: Path) -> None:
    pol = MailboxPolicy(tmp_path / "mb", poll_s=0.05, margin_s=0.5)

    async def _go() -> None:
        ctx = TurnContext(seat="P3", turn_seq=4, observation={"day": 1}, llm_user_message="{}", rules={"system_prompt": "x"},
                          status={}, deadline_at=time.time() + 5.0, server_skew=0.0)

        async def brain() -> None:
            pend = pol.pending_path("P3")
            for _ in range(100):
                if pend.exists():
                    break
                await asyncio.sleep(0.02)
            data = json.loads(pend.read_text(encoding="utf-8"))
            assert data["turn_seq"] == 4 and data["rules"]["system_prompt"] == "x" and data["observation"] == {"day": 1}
            pol.decision_path("P3").write_text(json.dumps({"turn_seq": 4, "action": {"kind": "scan", "args": {}}}), encoding="utf-8")

        action, _ = await asyncio.gather(pol(ctx), brain())
        assert action == {"kind": "scan", "args": {}}
        assert not pol.pending_path("P3").exists() and not pol.decision_path("P3").exists()
        # Late brain: no decision before the margin -> safe wait.
        ctx2 = TurnContext(seat="P3", turn_seq=5, observation={}, llm_user_message=None, rules={}, status={},
                           deadline_at=time.time() + 0.8, server_skew=0.0)
        action2 = await pol(ctx2)
        assert action2["kind"] == "wait"

    asyncio.run(_go())


def test_seat_client_script_has_no_xai_and_runs_help() -> None:
    src = (ROOT / "scripts" / "grokbot_seat_client.py").read_text(encoding="utf-8")
    mod = (ROOT / "src" / "tw2k" / "agents" / "pathb_client.py").read_text(encoding="utf-8")
    for bad in ("api.x.ai", "XAI_API_KEY", "openai"):
        assert bad not in src and bad not in mod, bad
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "grokbot_seat_client.py"), "--help"],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0 and "--policy" in proc.stdout and "mailbox" in proc.stdout
