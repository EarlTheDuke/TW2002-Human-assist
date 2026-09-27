"""Grokbot-player G5 - computer-use pilot prep (no live pilot in tests).

* paused start: the dry-run host builds seats but nobody acts until resume;
* per-action log for external seats (wall time, illegal attempts, rejected posts, retries);
* webhook test ping endpoint; access logs never keep `?token=`;
* run_cu_pilot.ps1 guard rails + report / check scripts.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path

import httpx

from tw2k.agents import external as external_mod
from tw2k.engine import GameConfig
from tw2k.server.app import _RedactTokenQuery, create_app
from tw2k.server.runner import AgentSpec, MatchSpec

ROOT = Path(__file__).resolve().parents[1]
TOK2 = "g5-token-p2-0000000000000000000"


def _spec(paused: bool = False) -> MatchSpec:
    return MatchSpec(
        config=GameConfig(seed=9, universe_size=60, max_days=2, turns_per_day=30, starting_credits=25_000,
                          enable_ferrengi=False, enable_planets=False, action_delay_s=0.0),
        agents=[AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
                AgentSpec(player_id="P2", name="Seat2", kind="external", external_token=TOK2, external_timeout_s=2.0)],
        action_delay_s=0.0, external_timeout_s=30.0, paused=paused,
    )


def _run(tmp_path: Path, spec: MatchSpec, body) -> None:
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"

    async def go() -> None:
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5555)), base_url="http://g5.test")
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


H = {"authorization": f"Bearer {TOK2}"}


def test_paused_start_builds_seats_but_nobody_acts_until_resume(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)

    async def body(client, runner) -> None:
        await asyncio.sleep(0.5)
        u = runner.state.universe
        assert runner.state.status == "paused" and set(u.players) == {"P1", "P2"}
        assert all(p.turns_today == 0 for p in u.players.values())
        assert (await client.get("/harness/v1/P2/status", headers=H)).json()["awaiting_input"] is False
        assert (await client.post("/control/resume")).status_code == 200
        async def p1_acted():
            return u.players["P1"].turns_today > 0
        assert await _until(p1_acted)

    _run(tmp_path, _spec(paused=True), body)


def test_per_action_log_records_wall_time_rejections_retries_and_auto_waits(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)

    async def body(client, runner) -> None:
        async def my_turn():
            return (await client.get("/harness/v1/P2/status", headers=H)).json().get("awaiting_input")
        assert await _until(my_turn)
        st = (await client.get("/harness/v1/P2/status", headers=H)).json()
        await asyncio.sleep(0.3)  # "think"
        bad = await client.post("/harness/v1/P2/action", headers=H, json={"turn_seq": st["turn_seq"] + 7, "action": {"kind": "scan", "args": {}}})
        assert bad.status_code == 409
        ok = await client.post("/harness/v1/P2/action", headers=H, json={"turn_seq": st["turn_seq"], "action": {"kind": "warp", "args": {"target": 99999}}})
        assert ok.status_code == 200  # accepted by the harness, rejected by the engine (illegal)
        # next turn: say nothing -> 2 s per-seat deadline -> auto-WAIT
        async def auto_waited():
            log = runner.state.save_dir / "external_actions.jsonl"
            return log.is_file() and any(json.loads(line).get("auto") for line in log.read_text(encoding="utf-8").splitlines())
        assert await _until(auto_waited, tries=300, dt=0.05)
        rows = [json.loads(line) for line in (runner.state.save_dir / "external_actions.jsonl").read_text(encoding="utf-8").splitlines()]
        posts = [r for r in rows if r["event"] == "post" and r["turn_seq"] == st["turn_seq"]]
        assert [p["status"] for p in posts] == [409, 200] and posts[0]["detail"] == "stale_turn"
        res = next(r for r in rows if r["event"] == "result" and r["turn_seq"] == st["turn_seq"])
        assert res["ok"] is False and res["kind"] == "warp" and res["posts"] == 2 and res["think_s"] >= 0.3 and res["auto"] is False
        assert any(r["event"] == "result" and r["auto"] and r["think_s"] is None for r in rows)
        assert TOK2 not in json.dumps(rows)
        # the report script turns it into the pilot table
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "cu_pilot_report.py"), str(runner.state.save_dir), "--json"],
                             capture_output=True, text=True, check=True, timeout=60).stdout
        s = json.loads(out)["P2"]
        assert s["illegal"] >= 1 and s["auto_waits"] >= 1 and s["retries"] >= 1 and s["rejected_posts"].get("409") == 1
        assert s["think_median_s"] is not None

    _run(tmp_path, _spec(), body)


def test_webhook_test_ping_endpoint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_P2", raising=False)
    sent: list[dict] = []
    real = httpx.AsyncClient

    class Hook:
        def __new__(cls, *a, **k):
            return real(*a, **k) if "transport" in k else super().__new__(cls)
        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json=None, **k):
            sent.append(json)
            return httpx.Response(200)

    async def body(client, runner) -> None:
        assert (await client.post("/harness/v1/P2/webhook_test", headers=H)).status_code == 409
        monkeypatch.setenv("TW2K_GROKBOT_WEBHOOK_P2", "https://hook.test/p2")
        monkeypatch.setattr(httpx, "AsyncClient", Hook)
        r = await client.post("/harness/v1/P2/webhook_test", headers=H)
        assert r.status_code == 200 and r.json()["delivered"] is True
        assert sent[-1]["event"] == "turn_due_test" and sent[-1]["seat"] == "P2" and "observation" not in sent[-1]
        assert TOK2 not in json.dumps(sent[-1])

    monkeypatch.setattr(external_mod, "WEBHOOK_RETRY_DELAYS_S", (0.01, 0.01, 0.01))
    _run(tmp_path, _spec(paused=True), body)


def test_access_log_redacts_token_query() -> None:
    rec = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d', (
        "127.0.0.1:1", "GET", "/bot/claim?seat=P3&token=SUPERSECRETVALUE123&mode=cu", "1.1", 303), None)
    assert _RedactTokenQuery().filter(rec)
    msg = rec.getMessage()
    assert "SUPERSECRETVALUE123" not in msg and "token=<redacted>&mode=cu" in msg
    create_app(auto_start=False)
    assert any(isinstance(f, _RedactTokenQuery) for f in logging.getLogger("uvicorn.access").filters)


def test_pilot_script_guard_rails() -> None:
    ps1 = (ROOT / "scripts" / "run_cu_pilot.ps1").read_text(encoding="utf-8")
    assert "if ($DryRun -eq $Go)" in ps1 and "exit 2" in ps1, "must pick -DryRun or -Go explicitly"
    assert 'if ($Port -eq 8031)' in ps1 and "[int]$Port = 8032" in ps1
    assert "[int]$Seed = 250925" in ps1 and "[int]$MaxDays = 2" in ps1 and "[int]$TurnsPerDay = 60" in ps1
    assert '"QwenA,SeatBrain,Commander"' in ps1 and '"--external", "P2,P3"' in ps1 and '"--provider", "custom"' in ps1
    assert '"P2=$BotTimeoutS"' in ps1 and "[int]$CuTimeoutS = 600" in ps1
    assert 'if ($DryRun) { $serveArgs += "--start-paused" }' in ps1
    assert "TW2K_GROKBOT_WEBHOOK_P3" in ps1 and "Remove-Item Env:TW2K_GROKBOT_WEBHOOK_URL" in ps1, "only P3 is pinged"
    assert "TW2K_SPECTATOR_TOKEN" in ps1 and "tunnel_watchdog.ps1" in ps1
    assert '"scripts/seat_brain_v2.py", "--seat", "P2", "--harness"' in ps1
    for script in ("cu_pilot_check.py", "cu_pilot_report.py"):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / script), "--help"], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, script
