"""Grokbot-player G6 - the four CU pilot fixes.

1. One status line: `Day X of Y - N turns left today - Rank R of S` (harness fields + CU bar + Turn card).
2. Game over: 200 + game_over/winner/standings/your_rank after the match; POST 409 `game_over`; /bot panel.
3. Route macro (`run_route`) + auto-accept + result digest; report gains turns per click / wall s per turn.
4. Wake-up ping: Authorization header from env / .tw2k file, never logged; status_line in the brief;
   no ping on held turns; a final `game_over` ping.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from tests._cu_host import CuHost
from tw2k.agents import external as external_mod
from tw2k.agents import route_macro
from tw2k.engine import GameConfig
from tw2k.engine.observation import build_observation, status_fields
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "web" / "bot-parity.js"
NODE = shutil.which("node")
TOK = "g6-token-p1-0000000000000000000"
TOK2 = "g6-token-p2-0000000000000000000"
A, B = 29, 35  # seed 1 / 200 sectors: 29 sells fuel + buys equipment, 35 the reverse; adjacent both ways


def _node(expr: str, data: object) -> object:
    script = (f"const P = require({json.dumps(str(PARITY))});"
              "const d = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
              f"process.stdout.write(JSON.stringify({expr}));")
    out = subprocess.run([NODE, "-e", script], input=json.dumps(data), capture_output=True, text=True,
                         encoding="utf-8", check=True, timeout=30)
    return json.loads(out.stdout)


needs_node = pytest.mark.skipif(NODE is None, reason="node not installed")


def _run(tmp_path: Path, spec: MatchSpec, body, *, park_at: int | None = None) -> None:
    """Start `spec` paused, optionally park P1 at `park_at` with empty holds, resume, run body."""
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"
    spec.paused = True

    async def go() -> None:
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5555)), base_url="http://g6.test")
        await runner.start(spec)
        for _ in range(300):
            if runner.state.agents and runner.state.universe is not None:
                break
            await asyncio.sleep(0.02)
        u = runner.state.universe
        if park_at is not None:
            me = u.players["P1"]
            u.sectors[me.sector_id].occupant_ids.remove("P1")
            me.sector_id = park_at
            u.sectors[park_at].occupant_ids.append("P1")
            me.known_sectors.update({A, B})
            me.ship.cargo = {c: 0 for c in me.ship.cargo}
        runner.resume()
        try:
            await body(client, runner)
        finally:
            await runner.stop()
            await client.aclose()

    asyncio.run(go())


async def _until(pred, tries: int = 500, dt: float = 0.02) -> bool:
    for _ in range(tries):
        if await pred():
            return True
        await asyncio.sleep(dt)
    return await pred()


def _h(tok: str = TOK) -> dict[str, str]:
    return {"authorization": f"Bearer {tok}"}


def _solo(days: int = 2, tpd: int = 200, seed: int = 1, hold_max: int = 10) -> MatchSpec:
    return MatchSpec(
        config=GameConfig(seed=seed, universe_size=200, max_days=days, turns_per_day=tpd, starting_credits=50_000,
                          enable_ferrengi=False, enable_planets=False, action_delay_s=0.0),
        agents=[AgentSpec(player_id="P1", name="Commander", kind="external", external_token=TOK)],
        action_delay_s=0.0, external_timeout_s=30.0, external_hold_max_actions=hold_max,
    )


# ------------------------------------------------------------------ 1. status line
def test_status_fields_are_one_line_from_the_seats_own_observation() -> None:
    from tw2k.engine import generate_universe
    from tw2k.engine.models import Player

    u = generate_universe(GameConfig(seed=3, universe_size=60, max_days=4, turns_per_day=50, enable_ferrengi=False))
    for pid, credits in (("P1", 10_000), ("P2", 90_000), ("P3", 50_000)):
        u.players[pid] = Player(id=pid, name=pid, agent_kind="external", sector_id=1, credits=credits, turns_per_day=50)
        u.sectors[1].occupant_ids.append(pid)
    u.players["P1"].turns_today = 18
    f = status_fields(build_observation(u, "P1"))
    assert f == {"status_line": "Day 1 of 4 - 32 turns left today - Rank 3 of 3", "day": 1, "max_days": 4,
                 "turns_left_today": 32, "turns_per_day": 50, "rank": 3, "seats": 3}


def test_harness_status_and_observation_carry_the_status_line(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)

    async def body(client, runner) -> None:
        for path in ("/harness/v1/P1/status", "/harness/v1/P1/observation?peek=1"):
            r = (await client.get(path, headers=_h())).json()
            assert re.fullmatch(r"Day 1 of 2 - \d+ turns left today - Rank 1 of 1", r["status_line"]), r["status_line"]
            assert {r["max_days"], r["turns_per_day"], r["rank"], r["seats"]} >= {2, 200, 1}
            assert r["game_over"] is False and "standings" not in r

    _run(tmp_path, _solo(), body)


@needs_node
def test_cu_banner_and_turn_card_never_show_seq_or_tick() -> None:
    cases = [["turn", "YOUR TURN  seq=17  day=2", "respond within 580s", {"hold": {"on": True, "used": 3, "max": 10}}],
             ["idle", "WAITING  day=2 tick=88", "x", {"current": {"player_id": "P1", "name": "QwenA", "kind": "llm",
                                                                  "started_at": 100, "deadline_at": 160}, "seat": "P3", "now": 134}],
             ["busy", "SUBMITTING seq=4", "", {}]]
    out = _node("d.map(([m, t, s, c]) => P.cuBanner(m, t, s, c))", cases)
    assert out[0]["main"] == "YOUR TURN · HOLDING 3/10"
    assert out[1]["main"] == "WAITING · QwenA (LLM) is thinking · 34s" and out[1]["sub"] == "their limit 26s"
    for b in out:
        assert not re.search(r"seq|tick|\bt\d+\b|day=", b["main"] + b["sub"]), b
    card = _node("P.turnCard({day:2,max_days:2,tick:88,turns_remaining:5,turns_per_day:60,sector:{id:3,warps_out:[1]},ship:{}},"
                 "{statusLine: 'Day 2 of 2 - 5 turns left today - Rank 1 of 3', turn: 'YOUR TURN'})", {})
    assert card.splitlines()[0] == "Day 2 of 2 - 5 turns left today - Rank 1 of 3"
    assert "tick" not in card and "88" not in card


# ------------------------------------------------------------------ 2. game over
def test_game_over_is_200_with_standings_and_actions_are_409(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)
    spec = MatchSpec(
        config=GameConfig(seed=9, universe_size=60, max_days=1, turns_per_day=4, starting_credits=25_000,
                          enable_ferrengi=False, enable_planets=False, action_delay_s=0.0),
        agents=[AgentSpec(player_id="P1", name="Commander", kind="external", external_token=TOK),
                AgentSpec(player_id="P2", name="HBot", kind="heuristic")],
        action_delay_s=0.0, external_timeout_s=30.0,
    )

    async def body(client, runner) -> None:
        async def finished():
            st = (await client.get("/harness/v1/P1/status", headers=_h())).json()
            if st.get("game_over"):
                return True
            if st.get("awaiting_input"):
                await client.post("/harness/v1/P1/action", headers=_h(), json={"turn_seq": st["turn_seq"], "action": {"kind": "wait", "args": {}}})
            return False
        assert await _until(finished, tries=600)
        for path in ("/harness/v1/P1/status", "/harness/v1/P1/observation?peek=1&format=both"):
            r = await client.get(path, headers=_h())
            assert r.status_code == 200, (path, r.text)
            body_ = r.json()
            assert body_["game_over"] is True and body_["winner"]["seat"] in ("P1", "P2")
            assert [s["rank"] for s in body_["standings"]] == [1, 2]
            assert set(body_["standings"][0]) >= {"seat", "name", "net_worth", "rank"}
            assert body_["your_rank"] in (1, 2) and body_["status_line"].startswith("Day ")
        post = await client.post("/harness/v1/P1/action", headers=_h(), json={"action": {"kind": "wait", "args": {}}})
        assert post.status_code == 409 and post.json()["detail"] == "game_over"

    _run(tmp_path, spec, body)


# ------------------------------------------------------------------ 3. route macro
def _obs(**over) -> dict:
    o = {"self_id": "P1", "turns_remaining": 50, "other_players": [],
         "sector": {"id": A, "warps_out": [B, 7], "occupants": ["P1"]}, "ship": {"cargo": {}},
         "legal_actions": [
             {"kind": "trade", "legal": True, "turn_cost": 1, "params": {
                 "commodity": {"buy_choices": ["fuel_ore"], "sell_choices": ["equipment"]},
                 "qty": {"max_by": {"fuel_ore": {"buy": 20}, "equipment": {"sell": 20}}}}},
             {"kind": "warp", "legal": True, "turn_cost": 2}, {"kind": "plot_course", "legal": True, "turn_cost": 0}]}
    o.update(over)
    return o


def test_route_planner_steps_and_every_stop_condition() -> None:
    plan = route_macro.new_plan(A, B, "fuel_ore", "equipment", 2)
    assert route_macro.next_step(_obs(), plan) == ({"kind": "trade", "args": {"commodity": "fuel_ore", "qty": 20, "side": "buy"}}, None)
    plan["steps"] = 1
    assert route_macro.next_step(_obs(), plan) == ({"kind": "warp", "args": {"target": B}}, None)
    far = route_macro.new_plan(A, 99, "fuel_ore", "equipment", 1)
    far["bought_here"] = A
    assert route_macro.next_step(_obs(), far)[0] == {"kind": "plot_course", "args": {"target": 99, "execute": True}}
    stops = {
        "enemy": _obs(sector={"id": A, "warps_out": [B], "occupants": ["P1", "P9"]}),
        "ferrengi": _obs(sector={"id": A, "warps_out": [B], "occupants": ["P1"], "ferrengi": [{"id": "F1"}]}),
        "out_of_stock": _obs(legal_actions=[{"kind": "trade", "legal": True, "turn_cost": 1, "params": {
            "commodity": {"buy_choices": ["fuel_ore"], "sell_choices": []}, "qty": {"max_by": {"fuel_ore": {"buy": 0}}}}}]),
        "low_turns": _obs(turns_remaining=0),
        "off_route": _obs(sector={"id": 7, "warps_out": [A], "occupants": ["P1"]}),
    }
    reasons = {}
    for name, o in stops.items():
        p = route_macro.new_plan(A, B, "fuel_ore", "equipment", 2)
        p["steps"] = 3
        step, why = route_macro.next_step(o, p)
        assert step is None, name
        reasons[name] = why
    assert "another commander" in reasons["enemy"] and "Ferrengi" in reasons["ferrengi"]
    assert "out of stock" in reasons["out_of_stock"] and "low turns" in reasons["low_turns"]
    assert "left the route" in reasons["off_route"]
    # corpmates are not enemies
    mate = _obs(sector={"id": A, "warps_out": [B], "occupants": ["P1", "P2"]}, other_players=[{"id": "P2", "is_corpmate": True}])
    assert route_macro.next_step(mate, route_macro.new_plan(A, B, "fuel_ore", "equipment", 1))[0] is not None
    with pytest.raises(ValueError):
        route_macro.new_plan(A, B, "fuel_ore", "fuel_ore", 1)
    # Fog: the planner reads a plain observation dict only, never the engine / universe.
    src = (ROOT / "src" / "tw2k" / "agents" / "route_macro.py").read_text(encoding="utf-8")
    assert "import" not in src.split('"""', 2)[2].replace("from __future__ import annotations", "").replace("from typing import Any", "")


def test_route_macro_runs_cycles_legally_with_one_click_and_a_digest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)

    async def body(client, runner) -> None:
        u = runner.state.universe
        me = u.players["P1"]
        async def my_turn():
            return (await client.get("/harness/v1/P1/status", headers=_h())).json().get("awaiting_input")
        assert await _until(my_turn)
        st = (await client.get("/harness/v1/P1/status", headers=_h())).json()
        credits0, turns0 = me.credits, me.turns_today
        r = await client.post("/harness/v1/P1/macro", headers=_h(), json={
            "a": A, "b": B, "buy_at_a": "fuel_ore", "buy_at_b": "equipment", "cycles": 2, "turn_seq": st["turn_seq"]})
        assert r.status_code == 200 and r.json()["started"] is True, r.text
        async def digest():
            d = (await client.get("/harness/v1/P1/status", headers=_h())).json().get("digest")
            return bool(d)
        assert await _until(digest, tries=800)
        d = (await client.get("/harness/v1/P1/status", headers=_h())).json()["digest"]
        assert d["kind"] == "route" and d["cycles_done"] == 2 and "route complete" in d["stopped"]
        assert d["turns_used"] == me.turns_today - turns0 > 0 and d["credits_before"] == credits0 and d["credits_after"] == me.credits
        rows = [json.loads(x) for x in (runner.state.save_dir / "external_actions.jsonl").read_text(encoding="utf-8").splitlines()]
        results = [x for x in rows if x["event"] == "result"]
        assert results and all(x["ok"] for x in results), [x for x in results if not x["ok"]]
        kinds = [x["kind"] for x in results]
        # per cycle: buy@A, warp, sell+buy@B, warp back, sell@A -> 2 cycles = 8 trades + 4 warps
        assert kinds.count("trade") == 8 and kinds.count("warp") == 4 and len(kinds) == 12
        assert sum(1 for x in rows if x["event"] == "post" and x["status"] == 200) == 1, "one click"
        assert any(x["event"] == "macro_end" for x in rows) and any(x["event"] == "digest" for x in rows)
        rep = json.loads(subprocess.run([sys.executable, str(ROOT / "scripts" / "cu_pilot_report.py"), str(runner.state.save_dir), "--json"],
                                        capture_output=True, text=True, check=True, timeout=60).stdout)["P1"]
        assert rep["clicks"] == 1 and rep["turns_per_click"] == d["turns_used"] and rep["macro_steps"] == 11

    _run(tmp_path, _solo(), body, park_at=A)


def test_route_macro_stops_on_hold_release_and_on_a_failed_step(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)
    agent = external_mod.ExternalAgent("P1", "x", token=TOK)
    agent.macro = route_macro.new_plan(A, B, "fuel_ore", "equipment", 3)
    agent.hold_slot = True
    agent.record_result(False, "not enough credits", [])
    assert agent.macro_stop == "step failed: not enough credits" and agent.hold_slot is False

    async def body(client, runner) -> None:
        async def my_turn():
            return (await client.get("/harness/v1/P1/status", headers=_h())).json().get("awaiting_input")
        assert await _until(my_turn)
        ag = runner.state.agents[0]
        st = (await client.get("/harness/v1/P1/status", headers=_h())).json()
        ag.hold_max = 10
        orig = ag._macro_step
        def slow_step(obs):  # release the hold right after the second step
            step = orig(obs)
            if ag.macro and ag.macro["steps"] >= 2:
                ag.set_hold(False)
            return step
        ag._macro_step = slow_step
        await client.post("/harness/v1/P1/macro", headers=_h(), json={
            "a": A, "b": B, "buy_at_a": "fuel_ore", "buy_at_b": "equipment", "cycles": 5, "turn_seq": st["turn_seq"]})
        async def digest():
            return bool((await client.get("/harness/v1/P1/status", headers=_h())).json().get("digest"))
        assert await _until(digest, tries=800)
        d = (await client.get("/harness/v1/P1/status", headers=_h())).json()["digest"]
        assert d["stopped"] == "hold released" and d["cycles_done"] < 5

    _run(tmp_path, _solo(), body, park_at=A)


def test_macro_endpoint_guards(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)

    async def body(client, runner) -> None:
        async def my_turn():
            return (await client.get("/harness/v1/P1/status", headers=_h())).json().get("awaiting_input")
        assert await _until(my_turn)
        bad = {"a": A, "b": B, "buy_at_a": "fuel_ore", "buy_at_b": "fuel_ore", "cycles": 2}
        assert (await client.post("/harness/v1/P1/macro", headers=_h(), json=bad)).status_code == 422
        assert (await client.post("/harness/v1/P1/macro", headers=_h(), json={**bad, "buy_at_b": "equipment", "cycles": 99})).status_code == 422
        assert (await client.post("/harness/v1/P1/macro", headers=_h(), json={**bad, "buy_at_b": "equipment", "kind": "teleport"})).status_code == 422
        assert (await client.post("/harness/v1/P1/macro", json={**bad, "buy_at_b": "equipment"})).status_code == 401

    _run(tmp_path, _solo(hold_max=10), body, park_at=A)


@needs_node
def test_route_prefill_and_digest_text() -> None:
    log = [{"sector_id": 408, "side": "buy", "commodity": "fuel_ore"}, {"sector_id": 410, "side": "sell", "commodity": "fuel_ore"},
           {"sector_id": 410, "side": "buy", "commodity": "equipment"}]
    ports = [
        {"sector_id": 408, "stock": {"fuel_ore": {"side": "sells_to_player"}, "equipment": {"side": "buys_from_player"}}},
        {"sector_id": 410, "stock": {"equipment": {"side": "sells_to_player"}, "fuel_ore": {"side": "buys_from_player"}}},
    ]
    assert _node("P.routeFromTradeLog(d.log, 410, d.ports)", {"log": log, "ports": ports}) == {
        "a": 410, "b": 408, "buy_at_a": "equipment", "buy_at_b": "fuel_ore"}
    assert _node("P.routeFromTradeLog(d.log, 3, d.ports)", {"log": log, "ports": ports}) == {
        "a": 408, "b": 410, "buy_at_a": "fuel_ore", "buy_at_b": "equipment"}
    assert _node("P.routeFromTradeLog(d.log, 3, d.ports)", {"log": log[:1], "ports": ports}) is None
    mismatch = [
        ports[0],
        {"sector_id": 410, "stock": {"equipment": {"side": "sells_to_player"}, "fuel_ore": {"side": "sells_to_player"}}},
    ]
    bad = _node("P.routeFromTradeLog(d.log, 410, d.ports)", {"log": log, "ports": mismatch})
    assert "a" not in bad and "do not buy" in bad["reason"]
    thin = [ports[0], {"sector_id": 410, "stock": {}}]
    intel = _node("P.routeFromTradeLog(d.log, 410, d.ports)", {"log": log, "ports": thin})
    assert "a" not in intel and "there isn't enough port intel" in intel["reason"]
    assert "do not buy" not in intel["reason"]
    dg = {"kind": "route", "actions": 11, "turns_used": 30, "credits_before": 49317, "credits_after": 52117,
          "stopped": "route complete (2 cycles)", "cycles_done": 2, "cycles": 2, "last_turn_seq": 16}
    t = _node("[P.digestText(d, 16), P.digestText(d, 15)]", dg)
    assert t[0] == "ROUTE 2/2 cycles: 11 actions · 30 turns · credits 49,317 -> 52,117 (+2,800) · stopped: route complete (2 cycles)"
    assert t[1] == ""


# ------------------------------------------------------------------ 4. wake-up ping
def test_webhook_auth_header_status_line_no_held_ping_and_game_over_ping(tmp_path: Path, monkeypatch) -> None:
    secret = "Bearer grokbot-routine-SECRET-123"
    monkeypatch.setenv("TW2K_GROKBOT_WEBHOOK_URL", "https://routine.test/hook?k=QUERYSECRET")
    monkeypatch.setenv("TW2K_GROKBOT_WEBHOOK_AUTH_P1", secret)
    monkeypatch.setattr(external_mod, "WEBHOOK_RETRY_DELAYS_S", (0.01, 0.01, 0.01))
    sent: list[tuple[dict, dict]] = []
    real = httpx.AsyncClient

    class Hook:
        def __new__(cls, *a, **k):
            return real(*a, **k) if "transport" in k else super().__new__(cls)
        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json=None, headers=None, **k):
            sent.append((json, dict(headers or {})))
            return httpx.Response(200)

    monkeypatch.setattr(httpx, "AsyncClient", Hook)
    spec = _solo(days=1, tpd=12)

    async def body(client, runner) -> None:
        async def my_turn():
            return (await client.get("/harness/v1/P1/status", headers=_h())).json().get("awaiting_input")
        assert await _until(my_turn)
        assert await _until(lambda: _true(len(sent) >= 1))
        first, hdr = sent[0]
        assert hdr.get("Authorization") == secret and first["event"] == "turn_due"
        assert first["brief"]["status_line"].startswith("Day 1 of 1 - ")
        # held chain: 3 actions, only the slot's first turn was pinged
        await client.post("/harness/v1/P1/hold", headers=_h(), json={"hold": True})
        for _ in range(3):
            st = (await client.get("/harness/v1/P1/status", headers=_h())).json()
            await client.post("/harness/v1/P1/action", headers=_h(), json={"turn_seq": st["turn_seq"], "action": {"kind": "scan", "args": {}}})
            await _until(my_turn)
        turn_pings = [p for p, _ in sent if p["event"] == "turn_due"]
        assert len(turn_pings) == 1, [p["turn_seq"] for p in turn_pings]
        await client.post("/harness/v1/P1/hold", headers=_h(), json={"hold": False})
        # play out the day -> game over ping with standings
        async def over():
            st = (await client.get("/harness/v1/P1/status", headers=_h())).json()
            if st.get("game_over"):
                return True
            if st.get("awaiting_input"):
                await client.post("/harness/v1/P1/action", headers=_h(), json={"turn_seq": st["turn_seq"], "action": {"kind": "wait", "args": {}}})
            return False
        assert await _until(over, tries=600)
        assert await _until(lambda: _true(any(p["event"] == "game_over" for p, _ in sent)))
        go, go_hdr = next((p, h) for p, h in sent if p["event"] == "game_over")
        assert go_hdr.get("Authorization") == secret and go["your_rank"] == 1 and go["standings"][0]["seat"] == "P1"
        assert "observation" not in go and TOK not in json.dumps(go)
        log_text = (runner.state.save_dir / "webhook_deliveries.jsonl").read_text(encoding="utf-8")
        assert "SECRET" not in log_text and "QUERYSECRET" not in log_text

    _run(tmp_path, spec, body)


async def _true(v: bool) -> bool:
    return v


def test_webhook_auth_from_gitignored_file(tmp_path: Path, monkeypatch) -> None:
    for k in ("TW2K_GROKBOT_WEBHOOK_AUTH", "TW2K_GROKBOT_WEBHOOK_AUTH_P3"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr("tw2k.server.harness_tokens._repo_root", lambda: tmp_path)
    (tmp_path / ".tw2k").mkdir()
    agent = external_mod.ExternalAgent("P3", "Commander", token=TOK)
    assert agent._webhook_auth() == ""
    (tmp_path / ".tw2k" / "grokbot_webhook_auth.txt").write_text("Bearer from-file\n", encoding="utf-8")
    assert agent._webhook_auth() == "Bearer from-file"
    monkeypatch.setenv("TW2K_GROKBOT_WEBHOOK_AUTH_P3", "Bearer env-wins")
    assert agent._webhook_auth() == "Bearer env-wins"
    r = subprocess.run(["git", "check-ignore", "-q", ".tw2k/grokbot_webhook_auth.txt"], cwd=ROOT, check=False)
    assert r.returncode == 0
    ps1 = (ROOT / "scripts" / "run_cu_pilot.ps1").read_text(encoding="utf-8")
    assert "grokbot_webhook_url.txt" in ps1 and "grokbot_webhook_auth.txt" in ps1


# ------------------------------------------------------------------ browser: status line + game over panel
def test_browser_status_line_and_game_over_panel(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)
    with CuHost(tmp_path, TOK2, max_days=1, turns_per_day=6) as host:
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK2}")
        page.wait_for_selector("#cuTurn.turn", timeout=20_000)
        page.wait_for_function("/^Day 1 of 1 - \\d+ turns left today - Rank \\d of 2$/.test(document.querySelector('#cuStatusLine').textContent)",
                               timeout=10_000)
        top = page.locator(".cu-top").inner_text()
        assert top.count("turns left today") == 1 and not re.search(r"seq|tick|\bt\d{2,}\b|day=", top), top
        card = page.locator("#cuTurnCard").inner_text().splitlines()
        assert card[0] == page.locator("#cuStatusLine").inner_text()
        # play the seat out via the harness; the page must switch to GAME OVER
        c = httpx.Client(base_url=host.base, headers={"authorization": f"Bearer {TOK2}"}, timeout=30)
        for _ in range(400):
            st = c.get("/harness/v1/P2/status").json()
            if st.get("game_over"):
                break
            if st.get("awaiting_input"):
                c.post("/harness/v1/P2/action", json={"turn_seq": st["turn_seq"], "action": {"kind": "wait", "args": {}}})
            page.wait_for_timeout(50)
        assert st.get("game_over")
        page.reload()
        page.wait_for_selector("[data-testid=game-over]:not([hidden])", timeout=15_000)
        title = page.locator("#gameOverTitle").inner_text()
        assert re.fullmatch(r"GAME OVER - You finished (1st|2nd) of 2 - winner .+", title), title
        assert page.locator("[data-testid=final-P2]").is_visible()
        assert not page.locator("#verbPad").is_visible() and not page.locator("[data-testid=cu-actions]").is_visible()
        page2 = browser.new_page()
        page2.goto(f"{host.base}/bot?seat=P2&token={TOK2}")
        page2.wait_for_selector("[data-testid=game-over]:not([hidden])", timeout=15_000)
        assert not page2.locator("#verbPad").is_visible() and page2.locator("[data-testid=final-standings]").is_visible()
