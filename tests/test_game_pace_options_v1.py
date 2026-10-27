"""COMMANDER NOTE 93: turns per day as a game setting, hold the clock, seat timer, waiting game.

These are lobby and cockpit settings. No stored switch moves, and an omitted
field leaves today's command and today's opening pocket alone.
"""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

import tw2k.engine.constants as K
from tw2k.engine import GameConfig
from tw2k.public import config as C
from tw2k.public import pages
from tw2k.public import security as S
from tw2k.public import workers as WM
from tw2k.public.lobby import create_lobby_app
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

pytestmark = pytest.mark.legacy_profile

REPO = Path(__file__).resolve().parents[1]
TOK = "p" * 40


def test_turns_choice_keeps_original_and_accepts_presets_and_custom() -> None:
    assert S.parse_game_form({"name": "Alpha"}).turns_per_day_override is None
    assert S.parse_game_form({"name": "Alpha"}).turns_per_day == 250
    assert S.parse_game_form({"name": "Alpha", "turns_per_day": "original"}).turns_per_day_override is None
    assert S.parse_game_form({"name": "Alpha", "turns_per_day": "250"}).turns_per_day_override is None
    assert S.parse_game_form({"name": "Alpha", "turns_per_day": 250}).turns_per_day_override is None
    for preset in ("500", "1000", 500, 1000):
        form = S.parse_game_form({"name": "Alpha", "turns_per_day": preset})
        assert form.turns_per_day_override == int(preset)
        assert form.turns_per_day == int(preset)
    assert S.parse_game_form(
        {"name": "Alpha", "turns_per_day": "custom", "turns_per_day_custom": "50"}
    ).turns_per_day_override == 50
    assert S.parse_game_form(
        {"name": "Alpha", "turns_per_day": "custom", "turns_per_day_custom": "5000"}
    ).turns_per_day_override == 5000
    for bad in ("abc", "49", "5001", "10.5", "-1"):
        with pytest.raises(S.FormError):
            S.parse_game_form({"name": "Alpha", "turns_per_day": bad})
    with pytest.raises(S.FormError, match="Type a turns-per-day amount"):
        S.parse_game_form({"name": "Alpha", "turns_per_day": "custom", "turns_per_day_custom": ""})
    plain = S.parse_game_form({"name": "Alpha"}).settings()
    assert "turns_per_day_override" not in plain and plain["turns_per_day"] == 250
    assert "--turns-per-day-override" not in WM.serve_command(plain, 8101, REPO)
    chosen = S.parse_game_form({"name": "Alpha", "turns_per_day": "1000"}).settings()
    cmd = WM.serve_command(chosen, 8101, REPO)
    assert cmd[cmd.index("--turns-per-day-override") + 1] == "1000"
    assert cmd[cmd.index("--turns-per-day") + 1] == "1000"
    html = pages.new_game("Galaxy War Command")
    assert 'name="turns_per_day"' in html
    assert "Original (250)" in html and '<option value="original" selected>' in html
    assert ">500<" in html and ">1,000<" in html
    assert 'name="turns_per_day_custom"' in html and 'min="50"' in html and 'max="5000"' in html


def test_override_hits_every_seat_and_none_stays_out_of_the_dump(monkeypatch) -> None:
    assert "turns_per_day_override" not in GameConfig().model_dump()
    assert GameConfig(turns_per_day_override=500).model_dump()["turns_per_day_override"] == 500
    with pytest.raises(ValidationError):
        GameConfig(turns_per_day_override=49)
    with pytest.raises(ValidationError):
        GameConfig(turns_per_day_override=5001)
    assert K.turns_per_day_line(None, 250) == "Turns per day: 250 (original)"
    assert K.turns_per_day_line(1000, 250) == "Turns per day: 1,000 (game setting)"
    left = K.opening_loadout(20_000, 1000, 0)
    right = K.opening_loadout(20_000, 1000, 1)
    assert left[1] == right[1] == 1000
    assert K.opening_loadout(20_000, 1000, 0, None, 500) == (left[0], 500, left[2])
    assert K.opening_loadout(20_000, 1000, 1, None, 500)[1] == 500
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.opening_loadout(20_000, 1000, 0)[1] == 250
    assert K.opening_loadout(20_000, 1000, 0, None, 1000)[1] == 1000
    assert K.opening_loadout(20_000, 250, 1, None, 75)[1] == 75
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "STARTING_PACKAGE_MODE", "live")
    monkeypatch.setattr(K, "LIVE_PACE_MODE", "legacy")
    # Live package without live pace rewrites a bare 500 back to 250. The override sticks.
    assert K.opening_loadout(20_000, 500, 0)[1] == 250
    assert K.opening_loadout(20_000, 500, 0, None, 500)[1] == 500
    assert K.opening_loadout(20_000, 500, 3, None, 500)[1] == 500


def test_hold_box_defaults_on_and_a_missing_field_stays_off() -> None:
    html = pages.new_game("Galaxy War Command")
    assert 'id="hold_until_human"' in html and "checked" in html
    assert "Hold the clock until the first player opens a seat" in html
    missing = S.parse_game_form({"name": "Alpha"})
    assert missing.hold_until_human is False
    assert "hold_until_human" not in missing.settings()
    assert "--hold-until-human" not in WM.serve_command(missing.settings(), 8101, REPO)
    held = S.parse_game_form({"name": "Alpha", "hold_until_human": "on"})
    assert held.hold_until_human is True
    assert "--hold-until-human" in WM.serve_command(held.settings(), 8101, REPO)
    off = S.parse_game_form({"name": "Alpha", "hold_until_human": "off"})
    assert off.hold_until_human is False
    assert "--hold-until-human" not in WM.serve_command(off.settings(), 8101, REPO)
    # The form sends a hidden "off" and then the checkbox. The last value wins.
    both = S.parse_game_form({"name": "Alpha", "hold_until_human": "on"})
    assert both.hold_until_human is True
    from urllib.parse import parse_qs
    raw = "name=Alpha&hold_until_human=off&hold_until_human=on"
    folded = {k: v[-1] for k, v in parse_qs(raw, keep_blank_values=True).items()}
    assert S.parse_game_form(folded).hold_until_human is True
    raw_off = "name=Alpha&hold_until_human=off"
    folded_off = {k: v[-1] for k, v in parse_qs(raw_off, keep_blank_values=True).items()}
    assert S.parse_game_form(folded_off).hold_until_human is False


def test_new_game_screen_links_a_game_that_is_already_waiting(tmp_path, monkeypatch) -> None:
    for name in ("TW2K_PUBLIC_MODE", "TW2K_BRAND", "TW2K_BASE_PATH", "TW2K_SPECTATOR_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    from tests._cu_host import LOBBY_FREE_START, free_port
    from tests._port_lock import release_ports

    lobby_port = free_port(LOBBY_FREE_START)
    game_base = free_port(LOBBY_FREE_START, count=10)
    try:
        cfg = C.LobbyConfig(
            root=tmp_path / "selfhost", port=lobby_port,
            game_ports=range(game_base, game_base + 10), tick_s=3600.0,
        )
        app = create_lobby_app(cfg, port_probe=lambda _p: True)
        lob = app.state.lobby

        async def fake_start(gid, *, resume):
            lob.store.set_game(gid, status="running", port=game_base)
            return True

        lob.start_game = fake_start
        with TestClient(app) as client:
            assert client.post("/api/accept", json={}).status_code == 200
            made = client.post("/api/games", json={"name": "Waiting", "humans": 1, "bots": 0})
            assert made.status_code == 200, made.text
            gid = made.json()["id"]
            page = client.get("/new")
            assert page.status_code == 200
            assert 'data-waiting="game"' in page.text
            assert "You have a game waiting." in page.text
            assert f'href="/games/{gid}/join"' in page.text
            assert "Join it" in page.text
    finally:
        release_ports(lobby_port, *range(game_base, game_base + 10))


def test_the_clock_and_the_bots_wait_for_the_first_open_seat(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"

    async def _start() -> None:
        await runner.start(MatchSpec(
            config=GameConfig(seed=93, universe_size=80, max_days=3, turns_per_day=250,
                              enable_ferrengi=False, enable_planets=False, action_delay_s=0.0,
                              turn_regen_day_seconds=600),
            agents=[AgentSpec(player_id="P1", name="Bot", kind="heuristic"),
                    AgentSpec(player_id="P2", name="Human", kind="external", external_token=TOK)],
            action_delay_s=0.0, external_timeout_s=30.0, external_idle_wait_s=1.0,
            hold_until_human=True,
        ))

    try:
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            client.portal.call(_start)
            time.sleep(0.45)
            assert runner.day_clock() is None
            assert runner.state.universe is not None
            assert runner.state.universe.tick == 0
            opened = client.get(
                "/harness/v1/P2/observation?peek=1",
                headers={"Authorization": "Bearer " + TOK},
            )
            assert opened.status_code == 200
            assert opened.json()["turns_per_day_line"] == "Turns per day: 250 (original)"
            deadline = time.time() + 5
            while time.time() < deadline and runner.day_clock() is None:
                time.sleep(0.05)
            clock = runner.day_clock()
            assert clock is not None
            assert time.time() - float(clock["day_started_at"]) < 3
    finally:
        saved_day = getattr(runner, "_saved_day_seconds", None)
        if saved_day is not None:
            K.TURN_REGEN_DAY_SECONDS = saved_day
            runner._saved_day_seconds = None


def test_the_redesign_cockpit_counts_the_seat_timer(monkeypatch, tmp_path) -> None:
    bot = (REPO / "web" / "bot.html").read_text(encoding="utf-8")
    assert "seatTimer" not in bot and "seat-timer" not in bot
    assert "seatTimer" in (REPO / "web" / "redesign.html").read_text(encoding="utf-8")
    script = (REPO / "web" / "redesign.js").read_text(encoding="utf-8")
    assert "auto-WAIT" in script and "left < 30" in script
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    import uvicorn

    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    from tests._cu_host import free_port
    from tests._port_lock import release_ports

    port = free_port()
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"
    box: dict = {"server": None}

    async def _main() -> None:
        await runner.start(MatchSpec(
            config=GameConfig(seed=93, universe_size=40, max_days=2, turns_per_day=40,
                              enable_ferrengi=False, enable_planets=False, action_delay_s=0.0),
            agents=[AgentSpec(player_id="P1", name="Human", kind="external", external_token=TOK)],
            action_delay_s=0.0, external_timeout_s=20.0, external_idle_wait_s=0.0,
        ))
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        box["server"] = server
        try:
            await server.serve()
        finally:
            await runner.stop()

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
        with sync() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"{base}/bot?layout=redesign&seat=P1&token={TOK}")
            page.wait_for_selector("#seatTimer:not([hidden])", timeout=15000)
            text = page.locator("#seatTimer").inner_text()
            assert text.startswith("auto-WAIT ")
            left = int(text.removeprefix("auto-WAIT ").removesuffix("s"))
            assert 0 <= left < 30
            assert "amber" in (page.locator("#seatTimer").get_attribute("class") or "")
            page.screenshot(path="/tmp/note93-seat-timer.png")
            narrow = browser.new_page(viewport={"width": 390, "height": 844})
            narrow.goto(f"{base}/bot?layout=redesign&seat=P1&token={TOK}")
            narrow.wait_for_selector("#seatTimer:not([hidden])", timeout=15000)
            assert "amber" in (narrow.locator("#seatTimer").get_attribute("class") or "")
            narrow.screenshot(path="/tmp/note93-seat-timer-390.png")
            browser.close()
    finally:
        server = box["server"]
        if server is not None:
            server.should_exit = True
        thread.join(timeout=15)
        release_ports(port)
