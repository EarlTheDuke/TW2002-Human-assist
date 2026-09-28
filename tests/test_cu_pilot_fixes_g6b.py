"""Grokbot-player G6b — five CU pilot-2 fixes.

(a) REPEAT ROUTE dialog RUN ROUTE is enabled on your turn (macro is not an
    engine verb, so legal_actions must not gate it); Playwright clicks it.
(b) Status clamps day to max_days and says GAME OVER after the match.
(c) One-click auto-accept buttons for every commodity the port trades.
(d) `cu_pilot_report.py --latest` picks a real pilot run, not a test save.
(e) Reconnect banner on 401/403 or host drop, pointing at the seat link file.
"""

from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import httpx

from tests._cu_host import CuHost
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.models import Player
from tw2k.engine.observation import build_observation, status_fields
from tw2k.engine.runner import _record_port_intel
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

ROOT = Path(__file__).resolve().parents[1]
TOK = "g6b-token-p2-00000000000000000"
A, B = 29, 35  # seed 1 / 200 sectors: adjacent fuel/equipment pair (same as G6)


def _remember_pair(host) -> None:
    """This seat has seen both ports, so the route check can read its own intel."""
    u = host.runner.state.universe
    me = u.players["P2"]
    for sid in (A, B):
        _record_port_intel(me, sid, u.sectors[sid].port, universe=u)


def _trade_log() -> list[dict]:
    return [
        {"sector_id": A, "side": "buy", "commodity": "fuel_ore"},
        {"sector_id": B, "side": "sell", "commodity": "fuel_ore"},
        {"sector_id": B, "side": "buy", "commodity": "equipment"},
    ]


def _report():
    spec = importlib.util.spec_from_file_location("cu_pilot_report", ROOT / "scripts" / "cu_pilot_report.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _write_run(path: Path, names: list[str], *, actions: bool, seed: int = 42) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "meta.json").write_text(json.dumps({
        "seed": seed, "agents": [{"name": n} for n in names],
    }), encoding="utf-8")
    if actions:
        (path / "external_actions.jsonl").write_text(
            json.dumps({"event": "result", "seat": "P3", "ok": True, "kind": "trade"}) + "\n",
            encoding="utf-8")
    return path


# ------------------------------------------------------------------ static contract
def test_g6b_markup_and_gates() -> None:
    html = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")
    js = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")
    css = (ROOT / "web" / "bot.css").read_text(encoding="utf-8")
    ps1 = (ROOT / "scripts" / "run_cu_pilot.ps1").read_text(encoding="utf-8")
    assert 'data-testid="reconnect-banner"' in html and 'id="reconnect"' in html
    assert 'data-testid="cu-quick-trades"' in html
    assert "canUseForm" in js and 'kind === "run_route"' in js
    assert "go.disabled = !canUseForm(state.openVerb)" in js
    assert "cu-quick-${it.side}-${it.c}" in js
    assert "seat_links/${state.seat}.txt" in js
    assert "Math.min(obs.day, obs.max_days)" in js
    assert "GAME OVER" in (ROOT / "src" / "tw2k" / "engine" / "observation.py").read_text(encoding="utf-8")
    assert ".reconnect[hidden]" in css and ".cu-quick" in css
    assert "pilot_run.txt" in ps1 and "$Go" in ps1


# ------------------------------------------------------------------ (b) day clamp / GAME OVER
def test_status_fields_clamp_past_last_day_and_say_game_over() -> None:
    u = generate_universe(GameConfig(seed=3, universe_size=60, max_days=2, turns_per_day=50, enable_ferrengi=False))
    u.players["P1"] = Player(id="P1", name="Commander", agent_kind="external", sector_id=1, credits=10_000, turns_per_day=50)
    u.sectors[1].occupant_ids.append("P1")
    u.day = 3
    u.finished = True
    obs = build_observation(u, "P1")
    assert obs.day == 3 and obs.max_days == 2 and obs.finished is True
    f = status_fields(obs)
    assert f["day"] == 2 and f["turns_left_today"] == 0
    assert f["status_line"] == "Day 2 of 2 - GAME OVER - Rank 1 of 1"


def test_harness_finished_status_never_says_day_past_max(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)
    spec = MatchSpec(
        config=GameConfig(seed=9, universe_size=60, max_days=1, turns_per_day=4, starting_credits=25_000,
                          enable_ferrengi=False, enable_planets=False, action_delay_s=0.0),
        agents=[AgentSpec(player_id="P1", name="Commander", kind="external", external_token=TOK)],
        action_delay_s=0.0, external_timeout_s=30.0,
    )
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"

    async def go() -> None:
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5555)),
                                   base_url="http://g6b.test")
        await runner.start(spec)
        for _ in range(300):
            if runner.state.universe is not None:
                break
            await asyncio.sleep(0.02)
        h = {"authorization": f"Bearer {TOK}"}
        for _ in range(400):
            st = (await client.get("/harness/v1/P1/status", headers=h)).json()
            if st.get("game_over"):
                break
            if st.get("awaiting_input"):
                await client.post("/harness/v1/P1/action", headers=h,
                                  json={"turn_seq": st["turn_seq"], "action": {"kind": "wait", "args": {}}})
            await asyncio.sleep(0.02)
        assert st.get("game_over")
        assert st["day"] <= st["max_days"] == 1
        assert st["status_line"].startswith("Day 1 of 1 - GAME OVER -")
        assert "turns left" not in st["status_line"]
        await runner.stop()
        await client.aclose()

    asyncio.run(go())


# ------------------------------------------------------------------ (d) --latest picks a real pilot
def test_latest_pilot_run_skips_test_saves_and_dry_runs(tmp_path: Path, monkeypatch) -> None:
    report = _report()
    saves = tmp_path / "saves"
    logs = tmp_path / ".tw2k" / "cu_pilot"
    older = _write_run(saves / "20260926-190000-seed250925",
                       ["QwenA", "SeatBrain", "Commander"], actions=True, seed=250925)
    _write_run(saves / "20260926-220000-seed42",
               ["HBot", "Commander"], actions=True, seed=42)
    dry = _write_run(saves / "20260926-230000-dry",
                     ["QwenA", "SeatBrain", "Commander"], actions=False, seed=250925)
    os.utime(saves / "20260926-220000-seed42", (9_999_999_999, 9_999_999_999))
    os.utime(dry, (9_999_999_998, 9_999_999_998))
    assert report.latest_pilot_run(saves, logs) == older

    marker = logs / "20260926-194114"
    marker.mkdir(parents=True)
    (marker / "pilot_run.txt").write_text(str(older), encoding="utf-8")
    assert report.latest_pilot_run(saves, logs) == older

    monkeypatch.setattr(report, "ROOT", tmp_path)
    monkeypatch.setenv("TW2K_SAVES_DIR", str(saves))
    buf, err = io.StringIO(), io.StringIO()
    with redirect_stdout(buf), redirect_stderr(err):
        rc = report.main(["--latest", "--json"])
    assert rc == 0 and older.name in err.getvalue()
    assert json.loads(buf.getvalue())["P3"]["ok"] == 1

    bare = tmp_path / "bare"
    (bare / "saves").mkdir(parents=True)
    monkeypatch.setattr(report, "ROOT", bare)
    monkeypatch.setenv("TW2K_SAVES_DIR", str(bare / "saves"))
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        assert report.main(["--latest"]) == 1


# ------------------------------------------------------------------ browser: (a) (c) (e)
def test_browser_run_route_button_is_enabled_and_clicks(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)
    with CuHost(tmp_path, TOK, seed=1, park_at=A, fuel=0, max_days=2, turns_per_day=80) as host:
        me = host.runner.state.universe.players["P2"]
        me.trade_log = _trade_log()
        _remember_pair(host)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK}")
        page.wait_for_selector("#cuTurn.turn", timeout=20_000)
        page.locator("[data-testid=cu-route]").click()
        go = page.locator("[data-testid=route-go]")
        go.wait_for(timeout=5_000)
        assert go.is_enabled(), "RUN ROUTE stayed disabled with valid cycles and a known pair"
        why = page.locator("[data-testid=route-why]")
        assert why.count() == 0 or why.inner_text().strip() == ""
        go.click()
        page.wait_for_function(
            "(() => { const t = document.querySelector('#cuToast');"
            " return t && /ROUTE/.test(t.textContent) && !/rejected|did not start/i.test(t.textContent); })()",
            timeout=20_000,
        )


def test_browser_route_form_drops_a_stale_refusal_and_skips_a_bad_pair(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)
    with CuHost(tmp_path, TOK, seed=1, park_at=A, fuel=0, max_days=2, turns_per_day=80) as host:
        me = host.runner.state.universe.players["P2"]
        me.trade_log = _trade_log()
        _remember_pair(host)
        me.known_ports[B]["stock"]["fuel_ore"] = {"side": "sells_to_player", "price": 10, "current": 10, "max": 40}

        mismatch = browser.new_page(viewport={"width": 1280, "height": 800})
        mismatch.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK}")
        mismatch.wait_for_selector("#cuTurn.turn", timeout=20_000)
        mismatch.locator("[data-testid=cu-route]").click()
        mismatch.wait_for_function(
            "() => /do not buy/.test((document.querySelector('#cuToast') || {}).textContent || '')",
            timeout=5_000,
        )
        assert mismatch.locator("[data-testid=route-go]").count() == 0
        assert mismatch.locator("#verbForm").is_hidden()
        mismatch.close()

        me.known_ports[B]["stock"]["fuel_ore"] = {"side": "buys_from_player", "price": 20, "current": 20, "max": 40}
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK}")
        page.wait_for_selector("#cuTurn.turn", timeout=20_000)

        def refuse(route) -> None:
            path = route.request.url.split("?", 1)[0]
            if route.request.method == "POST" and path.endswith("/action"):
                route.fulfill(status=422, content_type="application/json", body=json.dumps({"detail": "cannot sell that here"}))
                return
            route.continue_()

        page.route("**/harness/v1/**", refuse)
        page.locator("[data-testid=action-scan]").click()
        page.wait_for_function(
            "() => /cannot sell that here/.test((document.querySelector('#cuToast') || {}).textContent || '')",
            timeout=10_000,
        )
        page.unroute("**/harness/v1/**", refuse)
        page.locator("[data-testid=cu-route]").click()
        page.locator("[data-testid=route-go]").wait_for(timeout=5_000)
        toast = page.locator("#cuToast")
        assert toast.is_hidden() or "cannot sell that here" not in toast.inner_text()
        assert "REJECTED" not in (toast.inner_text() or "")
        page.close()


def test_browser_one_click_trades_for_every_commodity(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)
    with CuHost(tmp_path, TOK, max_days=2, turns_per_day=40) as host:
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK}")
        page.wait_for_selector("#cuTurn.turn", timeout=20_000)
        page.wait_for_selector("[data-testid=cu-quick-sell-fuel_ore]", timeout=10_000)
        box = page.locator("[data-testid=cu-quick-trades]")
        labels = box.locator("button").all_inner_texts()
        assert any("SELL Fuel" in t for t in labels), labels
        assert any(t.startswith("BUY ") for t in labels), labels
        assert page.locator("[data-testid^=cu-quick-buy-]").count() >= 1
        page.locator("[data-testid=cu-quick-sell-fuel_ore]").click()
        page.wait_for_function(
            "(() => { const t = document.querySelector('#cuToast');"
            " return t && /trade|SELL|sold|ok/i.test(t.textContent); })()",
            timeout=15_000,
        )


def test_browser_reconnect_banner_on_host_drop_and_auth(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    monkeypatch.delenv("TW2K_GROKBOT_WEBHOOK_URL", raising=False)
    with CuHost(tmp_path, TOK, max_days=2, turns_per_day=40) as host:
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK}")
        page.wait_for_selector("#cuTurn.turn", timeout=20_000)
        banner = page.locator("[data-testid=reconnect-banner]")
        assert banner.is_hidden()

        def drop(route):
            route.fulfill(status=503, content_type="application/json", body='{"detail":"no tunnel here"}')

        page.route("**/harness/v1/**", drop)
        page.wait_for_selector("[data-testid=reconnect-banner]:not([hidden])", timeout=15_000)
        text = banner.inner_text()
        assert "seat_links/P2.txt" in text and "tunnel" in text.lower()
        assert page.locator("#reconnect").get_attribute("data-kind") == "host"

        def unauth(route):
            route.fulfill(status=401, content_type="application/json", body='{"detail":"unauthorized"}')

        page.unroute("**/harness/v1/**")
        page.route("**/harness/v1/**", unauth)
        page.wait_for_function(
            "document.querySelector('#reconnect').getAttribute('data-kind') === 'auth'",
            timeout=15_000,
        )
        assert "Signed out of P2" in page.locator("#reconnectTitle").inner_text()
        assert "seat_links/P2.txt" in banner.inner_text()
        assert "refreshed seat link" in banner.inner_text().lower()
