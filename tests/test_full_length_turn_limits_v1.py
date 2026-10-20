"""NOTE 131 full-length-turn-limits-v1.

Fast test days stay today's pocket and today's day length. A full-length game
uses the v3.11 sysop limit of 250 turns per day on a 24-hour day, and a longer
game lowers that limit so the whole game stays near 7,500 turns. The stored
flag default is legacy. "1" and V311_PROFILE do not turn it on.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if __name__ == "__main__":
    _root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(_root))
    sys.path.insert(0, str(_root / "src"))

import pytest
from pydantic import ValidationError

import tests._cu_host as cu
import tw2k.engine.constants as K
from tests._cu_host import CuHost
from tw2k.engine import GameConfig
from tw2k.public import pages
from tw2k.public import security as S
from tw2k.public import workers as WM
from tw2k.public.manual import render
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec

ROOT = Path(__file__).resolve().parents[1]
SHOTS = Path("/opt/cursor/artifacts/note131")
CASES = ("redesign", "bot")


def test_flag_off_is_legacy_and_dumps_omit_the_field() -> None:
    assert K.FULL_LENGTH_TURN_LIMITS_MODE == "legacy"
    assert K.full_length_turn_limits_on() is False
    assert "game_length" not in GameConfig().model_dump()
    assert "game_length" not in GameConfig(game_length="fast").model_dump()
    assert "game_length" not in GameConfig(game_length="legacy").model_dump()
    stored = GameConfig(game_length="full", max_days=60)
    assert stored.model_dump()["game_length"] == "full"
    assert K.full_length_turns_override(stored, None) is None
    assert K.full_length_turns_override(stored, 1000) == 1000
    with pytest.raises(ValidationError):
        GameConfig(game_length="1")
    with pytest.raises(ValueError):
        K.parse_game_length("v311")


def test_only_v311_turns_the_flag_on(monkeypatch) -> None:
    monkeypatch.setattr(K, "FULL_LENGTH_TURN_LIMITS_MODE", "1")
    assert K.full_length_turn_limits_on() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    monkeypatch.setattr(K, "FULL_LENGTH_TURN_LIMITS_MODE", "legacy")
    assert K.v311_profile() is True
    assert K.full_length_turn_limits_on() is False
    monkeypatch.setattr(K, "FULL_LENGTH_TURN_LIMITS_MODE", "v311")
    assert K.full_length_turn_limits_on() is True


def test_daily_cap_follows_the_v311_sysop_pocket() -> None:
    assert K.FULL_LENGTH_TURNS_PER_DAY == 250
    assert K.FULL_LENGTH_REFERENCE_DAYS == 30
    assert K.FULL_LENGTH_DAY_SECONDS == 86400
    assert K.full_length_daily_cap(7) == 250
    assert K.full_length_daily_cap(30) == 250
    assert K.full_length_daily_cap(31) == 7500 // 31
    assert K.full_length_daily_cap(60) == 125
    assert K.full_length_daily_cap(90) == 83
    assert K.full_length_daily_cap(365) == 50


def test_lobby_hides_the_choice_until_the_flag_is_on(monkeypatch) -> None:
    html = pages.new_game("Galaxy War Command")
    assert 'name="game_length"' not in html
    with pytest.raises(S.FormError, match="unknown field: game_length"):
        S.parse_game_form({"name": "Alpha", "game_length": "full"})
    plain = S.parse_game_form({"name": "Alpha"}).settings()
    assert "game_length" not in plain
    assert plain["day_seconds"] == 1800
    assert plain["turns_per_day"] == 250
    assert "--game-length" not in WM.serve_command(plain, 8101, ROOT)

    monkeypatch.setattr(K, "FULL_LENGTH_TURN_LIMITS_MODE", "v311")
    shown = pages.new_game("Galaxy War Command")
    assert 'name="game_length"' in shown
    assert "Fast test days" in shown and "Full-length" in shown
    assert 'value="fast" selected' in shown
    fast = S.parse_game_form({"name": "Alpha", "game_length": "fast"})
    assert fast.game_length is None
    assert "game_length" not in fast.settings()
    assert fast.day_seconds == 1800
    assert fast.turns_per_day_override is None
    missing = S.parse_game_form({"name": "Alpha"})
    assert missing.game_length is None and missing.day == "30m"
    with pytest.raises(S.FormError, match="game length must be fast or full"):
        S.parse_game_form({"name": "Alpha", "game_length": "1"})


def test_full_length_sets_the_day_and_the_daily_limit(monkeypatch) -> None:
    monkeypatch.setattr(K, "FULL_LENGTH_TURN_LIMITS_MODE", "v311")
    long = S.parse_game_form({"name": "Alpha", "game_length": "full", "max_days": "60", "day": "10m"})
    assert long.game_length == "full"
    assert long.max_days == 60
    assert long.day == "24h"
    assert long.day_seconds == 86400
    assert long.turns_per_day == 125
    assert long.turns_per_day_override == 125
    stored = long.settings()
    assert stored["game_length"] == "full"
    assert stored["turns_per_day_override"] == 125
    assert S.turns_phrase(stored) == "Turns per day: 125 (full-length)"
    cmd = WM.serve_command(stored, 8101, ROOT)
    assert cmd[cmd.index("--game-length") + 1] == "full"
    assert cmd[cmd.index("--turns-per-day-override") + 1] == "125"
    assert cmd[cmd.index("--day-seconds") + 1] == "86400"
    classic = S.parse_game_form({"name": "Alpha", "game_length": "full", "max_days": "30"})
    assert classic.turns_per_day_override == 250
    assert classic.day_seconds == 86400
    short = S.parse_game_form({"name": "Alpha", "game_length": "full", "max_days": "7"})
    assert short.turns_per_day == 250
    year = S.parse_game_form({"name": "Alpha", "game_length": "full", "max_days": "365"})
    assert year.turns_per_day == 50
    card = pages.created(
        "Galaxy War Command",
        game={"id": "g", "name": "Alpha", "settings": stored},
        join_links=[],
        watch_link="/w",
    )
    assert "Full-length game" in card


def test_the_manual_documents_the_defaults_for_a_full_length_game() -> None:
    quiet = render("Galaxy War Command")
    assert "Full-length games use" not in quiet
    cfg = GameConfig(
        game_length="full", max_days=60, turns_per_day=125,
        turns_per_day_override=125, turn_regen_day_seconds=86400,
    )
    html = render("Galaxy War Command", cfg, lobby=False)
    assert "Full-length games use" in html
    assert "250" in html and "7,500" in html and "30" in html
    assert "This game is full-length" in html
    assert "60 days" in html and "125 turns per day" in html
    assert "86,400 seconds" in html
    assert "750" in html and "sample game" in html
    assert "Fast test days" in html


def test_flag_off_keeps_todays_pocket_and_v311_applies_the_cap(monkeypatch, tmp_path) -> None:
    kept = asyncio.run(_seat_turns(tmp_path / "off", GameConfig(
        seed=7, universe_size=40, max_days=60, turns_per_day=1000,
        enable_ferrengi=False, action_delay_s=0.0, game_length="full",
    )))
    assert kept == 1000
    monkeypatch.setattr(K, "FULL_LENGTH_TURN_LIMITS_MODE", "v311")
    capped = asyncio.run(_seat_turns(tmp_path / "on", GameConfig(
        seed=7, universe_size=40, max_days=60, turns_per_day=1000,
        enable_ferrengi=False, action_delay_s=0.0, game_length="full",
    )))
    assert capped == 125
    fast = asyncio.run(_seat_turns(tmp_path / "fast", GameConfig(
        seed=7, universe_size=40, max_days=60, turns_per_day=1000,
        enable_ferrengi=False, action_delay_s=0.0,
    )))
    assert fast == 1000


async def _seat_turns(tmp: Path, cfg: GameConfig) -> int:
    runner = MatchRunner(Broadcaster(), saves_root=tmp / "saves")
    spec = MatchSpec(
        config=cfg,
        agents=[
            AgentSpec(player_id="P1", name="A", kind="heuristic"),
            AgentSpec(player_id="P2", name="B", kind="heuristic"),
        ],
        action_delay_s=0.0,
    )
    try:
        await runner.start(spec)
        for _ in range(200):
            universe = runner.state.universe
            if universe is not None and "P1" in universe.players:
                return int(universe.players["P1"].turns_per_day)
            await asyncio.sleep(0.05)
        raise AssertionError("players never appeared")
    finally:
        await runner.stop()


def test_bot_pages_do_not_carry_the_redesign_line() -> None:
    js = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")
    assert "turns-left-today" in js
    assert "paintFullLengthTurns" in js
    for name in ("bot.html", "bot.js", "bot-parity.js"):
        body = (ROOT / "web" / name).read_text(encoding="utf-8")
        assert "turns-left-today" not in body, name
        assert "turns_left_line" not in body, name
        assert "paintFullLengthTurns" not in body, name


def test_browsers_run_in_their_own_processes() -> None:
    script = str(Path(__file__).resolve())
    for spec in CASES:
        env = os.environ.copy()
        env.pop("COCKPIT_LAYOUT", None)
        env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT)
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, script, spec],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=180,
        )
        tail = (proc.stdout or "")[-2500:] + (proc.stderr or "")[-2500:]
        assert proc.returncode == 0, spec + "\n" + tail
        assert "BROWSER_OK " + spec in (proc.stdout or ""), tail


def _browser(kind: str) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    os.environ.pop("COCKPIT_LAYOUT", None)
    os.environ.pop("TW2K_SPECTATOR_TOKEN", None)
    SHOTS.mkdir(parents=True, exist_ok=True)
    tok = "full-length-turns-" + kind + "-p2-000000"
    tmp = Path(tempfile.mkdtemp(prefix="full-length-"))
    with CuHost(
        tmp, tok, max_days=60, turns_per_day=1000, game_length="full",
        turns_per_day_override=125, park_at=1, fuel=0,
    ) as host, sync_playwright() as pw:
        assert cu.allowed_test_port(host.port)
        from tw2k.engine.observation import build_observation

        me = host.runner.state.universe.players["P2"]
        assert me.turns_per_day == 125
        me.turns_today = 40
        fresh = build_observation(host.runner.state.universe, "P2")
        for agent in host.runner.state.agents:
            if getattr(agent, "player_id", None) == "P2":
                agent.current_observation = fresh
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            if kind == "redesign":
                page.goto(f"{host.base}/bot?layout=redesign&seat=P2#token={tok}")
                page.wait_for_function(
                    """() => {
                        const el = document.querySelector('[data-testid=turns-left-today]');
                        return el && el.textContent === 'Turns left today: 85 of 125';
                    }""",
                    timeout=20_000,
                )
                header = page.locator("#turns").inner_text()
                assert "85" in header
                page.screenshot(path=str(SHOTS / "redesign-turns-left.png"))
            else:
                page.goto(f"{host.base}/bot?seat=P2&token={tok}")
                page.wait_for_selector("[data-testid=turns-left]", timeout=20_000)
                page.wait_for_function(
                    "() => document.querySelector('[data-testid=turns-left]').textContent !== '-'",
                    timeout=20_000,
                )
                assert page.locator("[data-testid=turns-left-today]").count() == 0
                assert "turns-left-today" not in page.content()
                assert "Turns left today:" not in page.content()
        finally:
            browser.close()
    print("BROWSER_OK " + kind)


if __name__ == "__main__":
    _browser(sys.argv[1])
