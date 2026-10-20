"""COMMANDER NOTE 68: say how long the day is, and report the turn a warp actually charged."""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

import httpx
import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.models import Player
from tw2k.public.pages import day_length_hint, new_game
from tw2k.public.security import DAY_PRESETS, parse_game_form
from tw2k.server.runner import reported_turns_used

REPO = Path(__file__).resolve().parents[1]
SHOTS = REPO / "docs" / "playtests" / "beta-day-length-and-turns-v1"
TOK = "d" * 40


def test_the_day_length_hint_uses_the_preset_numbers() -> None:
    assert day_length_hint(600, 250, 10) == (
        "10 min days: 10 days take about 1 h 40 min; a turn comes back every 2.4 s, so turns rarely run out"
    )
    assert day_length_hint(86400, 250, 10) == (
        "24 h days: a turn comes back every 5.8 min, like the original; 10 days take 10 real days"
    )
    page = new_game("Galaxy War Command")
    assert "Real time, 24 h (original)" in page
    assert day_length_hint(1800, 250, 30) in page


def test_every_preset_is_the_day_seconds_the_worker_passes() -> None:
    for key, seconds in DAY_PRESETS.items():
        form = parse_game_form({"name": "Alpha", "day": key})
        assert form.day_seconds == seconds
        assert f"{float(seconds):g}" == f"{float(form.day_seconds):g}"


def test_a_warp_reports_its_charge_when_a_turn_comes_back(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    universe = generate_universe(GameConfig(
        seed=7, universe_size=80, max_days=2, turns_per_day=250,
        enable_ferrengi=False, enable_planets=False,
    ))
    sector = next(s for s in universe.sectors.values() if s.warps and s.id > 10)
    player = Player(id="P1", name="A", sector_id=sector.id, turns_per_day=250, turns_today=10)
    universe.players["P1"] = player
    sector.occupant_ids.append("P1")
    assert sector.warps
    before = int(player.turns_today)

    def give_one_back(who, now=None):
        who.turns_today = max(0, int(who.turns_today) - 1)

    monkeypatch.setattr("tw2k.engine.runner.refresh_offline_turns", give_one_back)
    result = apply_action(universe, player.id, Action(kind=ActionKind.WARP, args={"target": sector.warps[0]}))
    assert result.ok, result.error
    net = int(player.turns_today) - before
    assert result.turns_spent == 3
    assert net == 2
    assert reported_turns_used(result) == 3
    assert reported_turns_used(result) != net


def test_the_day_clock_counts_down_and_resets(monkeypatch, tmp_path) -> None:
    from fastapi.testclient import TestClient

    from tw2k.server.app import create_app
    from tw2k.server.runner import AgentSpec, MatchSpec

    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"

    async def _start() -> None:
        await runner.start(MatchSpec(
            config=GameConfig(seed=7, universe_size=80, max_days=3, turns_per_day=250,
                              enable_ferrengi=False, enable_planets=False, action_delay_s=0.0,
                              turn_regen_day_seconds=10),
            agents=[AgentSpec(player_id="P1", name="A", kind="heuristic"),
                    AgentSpec(player_id="P2", name="B", kind="external", external_token="t" * 40)],
            action_delay_s=0.05, external_timeout_s=30.0,
        ))

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        client.portal.call(_start)
        deadline = time.time() + 8
        while time.time() < deadline and runner.day_clock() is None:
            time.sleep(0.05)
        assert runner.day_clock() is not None
        runner._live_day_mark = time.time() - 4
        first = client.get("/harness/v1/P2/observation?peek=1", headers={"Authorization": "Bearer " + "t" * 40})
        assert first.status_code == 200
        clock = first.json()["turn_clock"]
        assert 5 <= clock["next_day_in_s"] <= 7
        later = clock["next_day_in_s"]
        deadline = time.time() + 3
        while time.time() < deadline:
            second = client.get("/harness/v1/P2/observation?peek=1", headers={"Authorization": "Bearer " + "t" * 40})
            later = second.json()["turn_clock"]["next_day_in_s"]
            if later < clock["next_day_in_s"]:
                break
            time.sleep(0.05)
        assert later < clock["next_day_in_s"]
        runner._live_day_mark = time.time()
        rolled = client.get("/harness/v1/P2/observation?peek=1", headers={"Authorization": "Bearer " + "t" * 40})
        assert rolled.json()["turn_clock"]["next_day_in_s"] > 8


def test_the_cockpit_shows_the_day_clock_and_the_refill(monkeypatch, tmp_path) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    import uvicorn

    from tw2k.server.app import create_app
    from tw2k.server.runner import AgentSpec, MatchSpec

    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    # The match copies this game's 600s day onto the process-wide clock and the
    # server thread outlives the test. Put the saved value back with the test.
    monkeypatch.setattr(K, "TURN_REGEN_DAY_SECONDS", K.TURN_REGEN_DAY_SECONDS)
    from tests._cu_host import free_port

    port = free_port()
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"

    server_box: dict = {}

    async def _main() -> None:
        await runner.start(MatchSpec(
            config=GameConfig(seed=7, universe_size=80, max_days=3, turns_per_day=250,
                              enable_ferrengi=False, enable_planets=False, action_delay_s=0.0,
                              turn_regen_day_seconds=600),
            agents=[AgentSpec(player_id="P1", name="A", kind="heuristic"),
                    AgentSpec(player_id="P2", name="B", kind="external", external_token=TOK)],
            action_delay_s=0.05, external_timeout_s=30.0,
        ))
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        server_box["server"] = server
        await server.serve()

    thread = threading.Thread(target=lambda: asyncio.run(_main()), daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(80):
            try:
                if httpx.get(base + "/bot?layout=redesign", timeout=0.5).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
        else:
            raise RuntimeError("cockpit did not start")
        SHOTS.mkdir(parents=True, exist_ok=True)
        with sync() as pw:
            browser = pw.chromium.launch()
            for width, tag in ((1280, "1280"), (390, "390")):
                page = browser.new_page(viewport={"width": width, "height": 800})
                page.goto(f"{base}/bot?layout=redesign&seat=P2&token={TOK}")
                page.wait_for_function("document.querySelector('#dayClock').textContent.includes('next day in')", timeout=15000)
                text = page.locator("#turns").inner_text()
                assert "(full)" in text or "+1 every" in text
                page.screenshot(path=str(SHOTS / f"{tag}-clock.png"))
                page.close()
            browser.close()
    finally:
        server = server_box.get("server")
        if server is not None:
            server.should_exit = True
        thread.join(timeout=15)
        from tests._port_lock import release_ports

        release_ports(port)
