"""COMMANDER NOTE 65 item 0: a starting-credits choice on the lobby new-game form.

Original (no override) stays today's opening: 300 under v3.11, 20,000 with the
legacy skew. A preset or a custom amount, 0 to 10,000,000, is the opening
credits for every human and every bot.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

import tw2k.engine.constants as K
from tw2k.engine import GameConfig
from tw2k.public import config as C
from tw2k.public import security as S
from tw2k.public import worker as W
from tw2k.public import workers as WM
from tw2k.public.lobby import create_lobby_app
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec

pytestmark = pytest.mark.legacy_profile

REPO = Path(__file__).resolve().parents[1]
SHOTS = REPO / "docs" / "playtests" / "cockpit-nav-and-map-v1"


def test_item0_validation_accepts_original_presets_and_custom_and_rejects_the_rest() -> None:
    """Original, each preset, custom 0 and 10,000,000. Missing stays Original."""
    assert S.parse_game_form({"name": "Alpha"}).starting_credits_override is None
    assert S.parse_game_form({"name": "Alpha", "starting_credits": "original"}).starting_credits_override is None
    for preset in ("10000", "100000", "1000000", 10_000, 100_000, 1_000_000):
        assert S.parse_game_form({"name": "Alpha", "starting_credits": preset}).starting_credits_override == int(preset)
    assert S.parse_game_form(
        {"name": "Alpha", "starting_credits": "custom", "starting_credits_custom": "0"}
    ).starting_credits_override == 0
    assert S.parse_game_form(
        {"name": "Alpha", "starting_credits": "custom", "starting_credits_custom": "10000000"}
    ).starting_credits_override == 10_000_000
    for bad in ("abc", "-1", "10000001", "10.5"):
        with pytest.raises(S.FormError):
            S.parse_game_form({"name": "Alpha", "starting_credits": bad})
    with pytest.raises(S.FormError, match="Type a starting credit amount"):
        S.parse_game_form({"name": "Alpha", "starting_credits": "custom", "starting_credits_custom": ""})
    plain = S.parse_game_form({"name": "Alpha"}).settings()
    assert "starting_credits_override" not in plain
    chosen = S.parse_game_form({"name": "Alpha", "starting_credits": "1000000"}).settings()
    assert chosen["starting_credits_override"] == 1_000_000
    assert "--starting-credits-override" not in WM.serve_command(plain, 8101, REPO)
    cockpit = (REPO / "web" / "redesign.js").read_text(encoding="utf-8")
    assert "starting_credits_line" in cockpit and 'data-game-info="credits"' in cockpit
    cmd = WM.serve_command(chosen, 8101, REPO)
    assert cmd[cmd.index("--starting-credits-override") + 1] == "1000000"


def test_item0_no_override_is_todays_opening_and_an_override_hits_every_seat(monkeypatch) -> None:
    """Legacy keeps the skew. v3.11 keeps 300. An override replaces credits only."""
    assert "starting_credits_override" not in GameConfig().model_dump()
    assert GameConfig(starting_credits_override=1_000_000).model_dump()["starting_credits_override"] == 1_000_000
    with pytest.raises(ValidationError):
        GameConfig(starting_credits_override=10_000_001)
    left = K.opening_loadout(20_000, 1000, 0)
    right = K.opening_loadout(20_000, 1000, 1)
    assert left[0] != right[0] and left[1:] == (1000, 20) and right[1:] == (1000, 20)
    assert K.opening_loadout(20_000, 1000, 0, 1_000_000) == (1_000_000, 1000, 20)
    assert K.opening_loadout(20_000, 1000, 1, 1_000_000) == (1_000_000, 1000, 20)
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.opening_loadout(20_000, 1000, 0) == (300, 250, 30)
    assert K.opening_loadout(20_000, 80, 1, 1_000_000) == (1_000_000, 80, 30)
    assert K.starting_credits_line(None, 300) == "Starting credits: 300 (original)"
    assert K.starting_credits_line(1_000_000, 300) == "Starting credits: 1,000,000 (test setting)"


def _runner(tmp_path: Path, override: int | None, *, live: bool):
    _prior_v311_profile = K.V311_PROFILE
    try:
        if live:
            K.V311_PROFILE = "v311"
        cfg = GameConfig(
            seed=21, universe_size=40, max_days=2, turns_per_day=80,
            starting_credits=20_000, enable_ferrengi=False, enable_planets=True,
            action_delay_s=0.0, starting_credits_override=override,
        )
        spec = MatchSpec(
            config=cfg,
            agents=[
                AgentSpec(player_id="P1", name="Human", kind="external", external_token="t" * 40),
                AgentSpec(player_id="P2", name="Bot", kind="heuristic"),
            ],
            action_delay_s=0.0,
            paused=True,
            external_idle_wait_s=0.0,
        )
        runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")

        async def go():
            await runner.start(spec)
            for _ in range(400):
                if runner.state.universe is not None and runner.state.universe.players:
                    break
                await asyncio.sleep(0.01)
            got = runner.state.universe
            snap = W.write_snapshot(runner, "test", tmp_path / "snaps")
            await runner.stop()
            return got, snap

        try:
            return asyncio.run(go())
        finally:
            K.V311_PROFILE = "legacy"
    finally:
        K.V311_PROFILE = _prior_v311_profile


def test_item0_the_runner_pays_the_override_to_the_human_and_the_bot(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    universe, snap = _runner(tmp_path, 1_000_000, live=True)
    assert universe.players["P1"].credits == 1_000_000
    assert universe.players["P2"].credits == 1_000_000
    assert universe.players["P1"].ship.fighters == 30
    assert universe.players["P1"].turns_per_day == 80
    assert universe.players["P2"].turns_per_day == 80
    metas = list((tmp_path / "saves").rglob("meta.json"))
    assert metas and json.loads(metas[0].read_text(encoding="utf-8"))["config"]["starting_credits_override"] == 1_000_000
    assert snap is not None
    assert json.loads(snap.read_text(encoding="utf-8").splitlines()[0])["starting_credits_override"] == 1_000_000


def test_item0_a_snapshot_records_the_override_and_a_resume_keeps_the_credits(tmp_path) -> None:
    cfg = GameConfig(seed=31, universe_size=40, max_days=2, enable_ferrengi=False, action_delay_s=0.0,
                     starting_credits_override=1_000_000)
    from tw2k.engine import generate_universe
    from tw2k.engine.models import Player

    universe = generate_universe(cfg)
    universe.players["P1"] = Player(id="P1", name="Human", credits=1_000_000, sector_id=1)
    universe.players["P2"] = Player(id="P2", name="Bot", credits=1_000_000, sector_id=1)
    runner = type("R", (), {})()
    runner.state = type("S", (), {"universe": universe, "status": "running"})()
    runner._live_day_mark = 50.0
    runner._spec = MatchSpec(config=cfg, agents=[])
    snap = W.write_snapshot(runner, "stop", tmp_path)
    meta, loaded = W.load_snapshot(snap)
    assert meta["starting_credits_override"] == 1_000_000
    assert loaded.players["P1"].credits == loaded.players["P2"].credits == 1_000_000
    bare = type("R", (), {})()
    bare.state = runner.state
    bare._live_day_mark = 50.0
    bare_snap = W.write_snapshot(bare, "plain", tmp_path / "plain")
    assert "starting_credits_override" not in json.loads(bare_snap.read_text(encoding="utf-8").splitlines()[0])


class _FakeWorker:
    def __init__(self, port: int) -> None:
        self.port = port
        self.pid = 4242
        self.stopping = False

    def alive(self) -> bool:
        return True


def _lobby(tmp_path: Path):
    from tests._cu_host import LOBBY_FREE_START, free_port

    lobby_port = free_port(LOBBY_FREE_START)
    game_base = free_port(LOBBY_FREE_START, count=10)
    cfg = C.LobbyConfig(
        root=tmp_path / "selfhost", port=lobby_port,
        game_ports=range(game_base, game_base + 10), tick_s=3600.0,
    )
    app = create_lobby_app(cfg, port_probe=lambda _p: True)
    lob = app.state.lobby
    lob._held_ports = [lobby_port, *range(game_base, game_base + 10)]

    async def fake_start(gid, *, resume):
        lob.workers.workers[gid] = _FakeWorker(game_base)
        lob.store.set_game(gid, status="running", port=game_base)
        return True

    async def fake_stop(gid, *, lobby_secret, spectator_token, graceful=True):
        lob.workers.workers.pop(gid, None)

    lob.start_game = fake_start
    lob.workers.stop = fake_stop
    client = TestClient(app)
    client.__enter__()
    return client, lob


def test_item0_the_form_shows_the_choice_and_the_card_shows_the_line(tmp_path) -> None:
    client, lob = _lobby(tmp_path)
    try:
        assert client.post("/api/accept", json={}).status_code == 200
        html = client.get("/new").text
        assert 'name="starting_credits"' in html
        assert "Original (v3.11 default, 300 cr)" in html and "selected" in html
        for label in ("10,000", "100,000", "1,000,000", "Custom"):
            assert label in html
        assert 'name="starting_credits_custom"' in html
        bad = client.post("/new", data={"name": "Try", "starting_credits": "custom", "starting_credits_custom": ""})
        assert bad.status_code == 400 and "Type a starting credit amount." in bad.text
        assert 'value="custom" selected' in bad.text
        high = client.post("/new", data={"name": "Try", "starting_credits": "custom", "starting_credits_custom": "10000001"})
        assert high.status_code == 400 and "between 0 and 10000000" in high.text
        made = client.post("/api/games", json={"name": "Rich", "starting_credits": 1_000_000, "bots": 1})
        assert made.status_code == 200, made.text
        gid = made.json()["id"]
        home = client.get("/").text
        assert "Starting credits: 1,000,000 (test setting)" in home
        info = client.get(f"/api/games/{gid}").json()
        assert info["starting_credits"] == "Starting credits: 1,000,000 (test setting)"
        original = client.post("/api/games", json={"name": "Plain", "bots": 0})
        assert "Starting credits: 300 (original)" in client.get("/").text
        assert client.get(f"/api/games/{original.json()['id']}").json()["starting_credits"].endswith("(original)")
    finally:
        client.__exit__(None, None, None)
        from tests._port_lock import release_ports

        release_ports(*lob._held_ports)


def _free_block(n: int) -> int:
    from tests._cu_host import LOBBY_FREE_START, free_port

    return free_port(LOBBY_FREE_START, count=n)


@pytest.mark.skipif(os.name != "nt", reason="Windows host")
def test_item0_a_lobby_game_starts_every_seat_at_the_chosen_credits(tmp_path) -> None:
    """Real worker. Seat credits, healthz, the harness line, and a resume."""
    base = _free_block(3)
    root = tmp_path / "selfhost"
    root.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("TW2K_", "TW2002_")) and k != "COCKPIT_LAYOUT"}
    env.update(TW2K_LOBBY_ROOT=str(root), TW2K_LOBBY_PORT=str(base), TW2K_GAME_PORTS=f"{base + 1}-{base + 2}",
               PYTHONPATH=str(REPO / "src"), PYTHONHASHSEED="0")
    url = f"http://127.0.0.1:{base}"
    lob = subprocess.Popen([sys.executable, "-m", "tw2k.cli", "lobby"], env=env, cwd=str(REPO),
                           stdout=open(root / "lobby.out", "ab"), stderr=subprocess.STDOUT)  # noqa: SIM115
    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            assert lob.poll() is None, (root / "lobby.out").read_text(errors="replace")[-2000:]
            try:
                if httpx.get(url + "/healthz", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.3)
        else:
            raise AssertionError("lobby did not come up")
        client = httpx.Client(base_url=url, timeout=90)
        assert client.post("/api/accept", json={}).status_code == 200
        game = client.post("/api/games", json={
            "name": "Credits", "starting_credits": 1_000_000, "bots": 1, "universe_size": 200, "day": "30m",
        }).json()
        assert game["status"] == "running", game
        gid = game["id"]
        assert client.get("/").text.count("Starting credits: 1,000,000 (test setting)") >= 1
        claim = client.post(f"/api/games/{gid}/join", json={}).json()["claim_url"]
        jumped = client.get(claim, follow_redirects=False)
        assert jumped.status_code == 303
        client.get(jumped.headers["location"])
        obs = client.get(f"/g/{gid}/harness/v1/P1/observation?peek=1", headers={"X-TW2K-Seat": "P1"})
        assert obs.status_code == 200, obs.text
        body = obs.json()
        assert body["starting_credits_line"] == "Starting credits: 1,000,000 (test setting)"
        assert body["observation"]["credits"] == 1_000_000
        proxied = client.get(f"/g/{gid}/healthz")
        assert proxied.status_code == 200
        assert proxied.json()["starting_credits"] == "Starting credits: 1,000,000 (test setting)"
        key = (root / "lobby.shutdown.key").read_text().strip()
        assert client.post("/admin/shutdown", headers={"x-lobby-shutdown": key}).status_code == 200
        lob.wait(60)
        lob = subprocess.Popen([sys.executable, "-m", "tw2k.cli", "lobby"], env=env, cwd=str(REPO),
                               stdout=open(root / "lobby.out", "ab"), stderr=subprocess.STDOUT)  # noqa: SIM115
        deadline = time.time() + 60
        while time.time() < deadline:
            assert lob.poll() is None
            try:
                if httpx.get(url + "/healthz", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.3)
        else:
            raise AssertionError("lobby did not resume")
        client = httpx.Client(base_url=url, timeout=90)
        assert client.get(f"/api/games/{gid}").json()["status"] == "running"
        again = client.post("/api/accept", json={})
        assert again.status_code == 200
        # a fresh guest cannot see the seat; the line is on the public card and the worker health
        assert "Starting credits: 1,000,000 (test setting)" in client.get("/").text
        assert client.get(f"/g/{gid}/healthz").json()["starting_credits"].endswith("(test setting)")
        snaps = list((root / "games" / gid / "snapshots").glob("snap-*.jsonl"))
        assert snaps
        saved = json.loads(snaps[-1].read_text(encoding="utf-8").splitlines()[0])
        assert saved["starting_credits_override"] == 1_000_000
    finally:
        if lob.poll() is None:
            lob.kill()
            lob.wait(10)
        from tests._port_lock import release_ports

        release_ports(base, base + 1, base + 2)


@pytest.mark.skipif(os.name != "nt", reason="Windows host")
def test_item0_browser_form_and_game_info_line(tmp_path) -> None:
    """The select, the custom box, the error line, and the lobby card, at 1280 and 390."""
    from playwright.sync_api import sync_playwright

    base = _free_block(3)
    root = tmp_path / "selfhost"
    root.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("TW2K_", "TW2002_")) and k != "COCKPIT_LAYOUT"}
    env.update(TW2K_LOBBY_ROOT=str(root), TW2K_LOBBY_PORT=str(base), TW2K_GAME_PORTS=f"{base + 1}-{base + 2}",
               PYTHONPATH=str(REPO / "src"), PYTHONHASHSEED="0")
    url = f"http://127.0.0.1:{base}"
    lob = subprocess.Popen([sys.executable, "-m", "tw2k.cli", "lobby"], env=env, cwd=str(REPO),
                           stdout=open(root / "lobby.out", "ab"), stderr=subprocess.STDOUT)  # noqa: SIM115
    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            assert lob.poll() is None, (root / "lobby.out").read_text(errors="replace")[-2000:]
            try:
                if httpx.get(url + "/healthz", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.3)
        else:
            raise AssertionError("lobby did not come up")
        SHOTS.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(url + "/")
            page.get_by_role("button", name="I understand").click()
            page.wait_for_selector("text=New game")
            page.get_by_role("link", name="New game").click()
            page.wait_for_selector("#starting_credits")
            assert page.locator("#starting_credits").input_value() == "original"
            page.fill("#name", "Screen")
            page.select_option("#starting_credits", "custom")
            page.fill("#starting_credits_custom", "")
            page.get_by_role("button", name="Create game").click()
            page.wait_for_selector("text=Type a starting credit amount.")
            assert page.locator("#starting_credits").input_value() == "custom"
            for width, height, name in ((1280, 800, "1280"), (390, 844, "390")):
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_timeout(150)
                page.screenshot(path=str(SHOTS / f"{name}-starting-credits-form.png"), full_page=True)
            page.set_viewport_size({"width": 1280, "height": 800})
            page.select_option("#starting_credits", "1000000")
            page.get_by_role("button", name="Create game").click()
            page.wait_for_selector("text=Game created")
            page.goto(url + "/")
            page.wait_for_selector("text=Starting credits: 1,000,000 (test setting)")
            for width, height, name in ((1280, 800, "1280"), (390, 844, "390")):
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_timeout(150)
                page.screenshot(path=str(SHOTS / f"{name}-starting-credits-info.png"), full_page=True)
            browser.close()
    finally:
        if lob.poll() is None:
            lob.kill()
            lob.wait(10)
        from tests._port_lock import release_ports

        release_ports(base, base + 1, base + 2)
