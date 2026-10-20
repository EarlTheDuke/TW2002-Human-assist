"""NOTE 128. A cockpit player that only sees the rendered seat page.

The scripted provider reads the player manual, trades port pairs from the
screen, and spends the day. The runner process does not import the engine.
Keys and the seat token stay out of the run log. The new-game AI cockpit
seat is absent while AI_COCKPIT_SEAT_MODE is legacy.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests._cu_host import RESERVED_TEST_PORTS, CuHost, allowed_test_port

REPO = Path(__file__).resolve().parents[1]
PLAYER = REPO / "scripts" / "ai_cockpit_player.py"
PACKAGE = REPO / "scripts" / "ai_cockpit"
TOKEN = "ai-cockpit-p2-token-000000000001"
# Joined at runtime. A single literal would match the source secret scan
# (xai- or sk- plus 16 alphanumeric characters).
_SOURCE_SECRET = re.compile(r"xai-[A-Za-z0-9]{16,}|sk-[A-Za-z0-9]{16,}")


def _key(*parts: str) -> str:
    return "".join(parts)


KEYS = {
    "XAI_API_KEY": _key("xai-", "testsecretkey", "1234567890"),
    "OPENAI_API_KEY": _key("sk-", "testsecretkey", "1234567890"),
    "ANTHROPIC_API_KEY": _key("sk-", "ant-", "testsecretkey", "1234567890"),
}
# Open pockets only. 8060 and the live bands stay unused.
FORBIDDEN = set(range(8031, 8038)) | {8041, 8042} | set(range(8045, 8050)) | set(range(8055, 8120))


def _sources() -> list[Path]:
    return [PLAYER, *sorted(PACKAGE.glob("*.py"))]


def test_the_player_sources_do_not_import_the_engine() -> None:
    for path in _sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                assert not name.startswith("tw2k"), f"{path.name} imports {name}"


def test_the_player_process_does_not_load_the_engine() -> None:
    proc = subprocess.run(
        [sys.executable, str(PLAYER), "--check-imports"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "engine import check: clean"
    assert proc.stderr.strip() == ""


def test_keys_are_redacted_and_a_missing_key_is_not_echoed(monkeypatch) -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.actions import parse_action
    from ai_cockpit.providers import ProviderError, ScriptedTrader, TurnView, build_provider
    from ai_cockpit.redact import redact

    source = Path(__file__).read_text(encoding="utf-8")
    assert _SOURCE_SECRET.search(source) is None
    for value in KEYS.values():
        assert len(value) > 16
        assert value not in source
        assert redact(f"authorization {value} token=seat-secret") == "authorization [redacted] token=[redacted]"
        assert value not in redact(value)
    action = parse_action('sure {"op":"press","key":"."}')
    assert action.op == "press" and action.key == "."
    view = TurnView("YOUR MOVE", ["Manual"], b"", False, "", 1)
    assert ScriptedTrader().decide(view).label == "Manual"
    read = TurnView("YOUR MOVE SELL 10", ["SELL 10"], b"", True, "Getting started", 2)
    assert ScriptedTrader().decide(read).label == "SELL"
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    with pytest.raises(ProviderError) as caught:
        build_provider("grok").decide(view)
    message = str(caught.value)
    assert "XAI_API_KEY" in message
    assert "sk-" not in message
    assert "xai-" not in message


def test_a_stop_file_ends_the_run_before_the_browser(tmp_path: Path) -> None:
    stop = tmp_path / "STOP"
    stop.write_text("stop", encoding="utf-8")
    run = tmp_path / "run"
    proc = subprocess.run(
        [sys.executable, str(PLAYER), "--url", "http://127.0.0.1:9/bot?token=secret",
         "--provider", "scripted", "--run-dir", str(run), "--stop-file", str(stop)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **KEYS},
    )
    assert proc.returncode == 0, proc.stderr
    blob = (run / "player.log").read_text(encoding="utf-8") + proc.stdout + proc.stderr
    assert "stop file" in blob
    assert (run / "modules.txt").read_text(encoding="utf-8") == ""
    for secret in (*KEYS.values(), "secret"):
        assert secret not in blob


def test_the_lobby_hook_stays_idle_until_the_switch_is_on(tmp_path: Path, monkeypatch, caplog) -> None:
    from tw2k.public.ai_cockpit_launch import cockpit_seat_url, launch_player
    from tw2k.public.lobby import Lobby

    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "legacy")
    assert K.ai_cockpit_seat_on() is False
    spawned: list = []
    assert launch_player(
        base_url="http://127.0.0.1:9", gid="game", seat="P2", token=TOKEN,
        run_dir=tmp_path / "off", popen=lambda *args, **kwargs: spawned.append(args),
    ) is None
    assert spawned == []
    lobby = Lobby.__new__(Lobby)
    assert lobby.launch_browser_seat(
        "game", "P2", TOKEN, run_dir=tmp_path / "off2", base_url="http://127.0.0.1:9",
    ) is None

    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "tw2002")
    seen: dict = {}

    class _Proc:
        def __init__(self, cmd, **kwargs):
            seen["cmd"] = cmd

    with caplog.at_level("INFO"):
        proc = launch_player(
            base_url="http://127.0.0.1:9", gid="game", seat="P2", token=TOKEN,
            run_dir=tmp_path / "on", provider="scripted", popen=_Proc,
        )
    assert isinstance(proc, _Proc)
    url = seen["cmd"][seen["cmd"].index("--url") + 1]
    assert url.endswith(cockpit_seat_url("game", "P2", TOKEN))
    assert "mode=cu" in url and "layout=redesign" in url and "seat=P2" in url
    assert TOKEN not in caplog.text
    for value in KEYS.values():
        assert value not in caplog.text


def test_scripted_player_reads_the_manual_and_sells(tmp_path: Path) -> None:
    pytest.importorskip("playwright.sync_api")
    run = tmp_path / "run"
    with CuHost(tmp_path / "host", TOKEN) as host:
        assert host.port not in RESERVED_TEST_PORTS
        assert host.port not in FORBIDDEN
        assert allowed_test_port(host.port)
        url = f"{host.base}/bot?seat=P2&mode=cu&token={TOKEN}&layout=redesign"
        proc = subprocess.run(
            [sys.executable, str(PLAYER), "--url", url, "--provider", "scripted",
             "--max-turns", "12", "--min-interval", "0", "--run-dir", str(run)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
            timeout=90,
            env={**os.environ, **KEYS, "PYTHONPATH": str(REPO / "src")},
        )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    actions = [json.loads(line) for line in (run / "actions.jsonl").read_text(encoding="utf-8").splitlines()]
    labels = [row["label"] for row in actions]
    assert "Manual" in labels
    assert any(row == "SELL" or str(row).upper().startswith("SELL") for row in labels)
    manual = (run / "text-manual.txt").read_text(encoding="utf-8")
    assert "Getting started" in manual
    blob = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in run.iterdir()
        if path.suffix in {".txt", ".jsonl", ".log"}
    )
    blob += proc.stdout + proc.stderr
    for secret in (*KEYS.values(), TOKEN):
        assert secret not in blob
    modules = (run / "modules.txt").read_text(encoding="utf-8")
    assert modules.strip() == ""
    assert any(path.name.startswith("screen-") and path.stat().st_size > 0 for path in run.iterdir())


def _view(screen: dict, *, manual: bool = True, labels: list[str] | None = None):
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.providers import TurnView

    shown = labels if labels is not None else list(screen.get("labels") or [])
    return TurnView("screen", shown, b"", manual, "Getting started", 1, screen=screen)


def test_the_scripted_trader_pairs_ports_haggles_and_avoids_danger() -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.trader import ScriptedTrader

    trader = ScriptedTrader()
    sold = trader.decide(_view({
        "sector": "12", "day": "1", "turns": "9", "credits": "50,000 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 10 Organics 0 Equipment 0",
        "ship": "Holds 10/20",
        "port": "Port Example Class 2 BSS",
        "here": "Port Example Class 2 BSS",
        "rows": [{
            "cells": ["Fuel Ore", "Buying, room 1000", "1000", "40", "10"],
            "button": "SELL 10",
        }],
        "labels": ["SELL 10", "1:20 (3t)"],
        "warps": ["1:20 (3t)"],
    }))
    assert sold.label == "SELL 10"
    # The port at 20 pays less than this one asks, so the pair is worth buying.
    trader.ports[20] = {"Organics": {"bid": 30}}
    bought = trader.decide(_view({
        "sector": "12", "day": "1", "turns": "8", "credits": "50,400 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "port": "Port Example Class 2 BSS",
        "rows": [{
            "cells": ["Organics", "Selling 500/2000", "500", "12", "0"],
            "button": "BUY 8",
        }],
        "labels": ["BUY 8"],
        "warps": ["1:20 (3t)"],
    }))
    assert bought.label == "BUY 8"
    confirmed = trader.decide(_view({
        "sector": "12", "day": "1", "turns": "8", "credits": "50,000 cr", "chip": "YOUR MOVE",
        "formOpen": True, "formText": "TRADE Port counters: We'll buy them",
        "haggle": "Port counters: We'll buy them for 40 cr each.",
        "fields": {"unit_price": "40", "qty": "10"},
        "labels": ["CONFIRM", "ESC"],
    }))
    assert confirmed.label == "CONFIRM"
    fled = trader.decide(_view({
        "sector": "4", "day": "1", "turns": "6", "credits": "50,000 cr", "chip": "YOUR MOVE",
        "here": "Ferrengi Marauder, 40 fighters",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "warps": ["1:4 (3t)", "2:9 (3t)"],
        "labels": ["1:4 (3t)", "2:9 (3t)"],
    }))
    assert fled.op == "click" and fled.label.endswith("9 (3t)")
    avoided = trader.decide(_view({
        "sector": "9", "day": "1", "turns": "3", "credits": "50,000 cr", "chip": "YOUR MOVE",
        "here": "clear",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "warps": ["1:4 (3t)", "2:15 (3t)"],
        "labels": ["1:4 (3t)", "2:15 (3t)"],
    }))
    assert avoided.label.startswith("2:15")
    dock = trader.decide(_view({
        "sector": "1", "day": "1", "turns": "9", "credits": "50,000 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "labels": ["StarDock: buy gear"],
        "warps": [],
    }))
    assert dock.label == "StarDock: buy gear"
    picked = trader.decide(_view({
        "sector": "1", "day": "1", "turns": "9", "credits": "50,000 cr", "chip": "YOUR MOVE",
        "formOpen": True, "formText": "BUY EQUIP",
        "fields": {"item": "armid_mines", "qty": ""},
        "gearNote": "Holds: 200 cr each, up to 10",
        "labels": ["CONFIRM", "ESC"],
    }))
    assert picked.op == "type" and picked.text == "holds"
    trader.decide(_view({
        "sector": "1", "day": "1", "turns": "9", "credits": "50,000 cr", "chip": "YOUR MOVE",
        "formOpen": True, "formText": "BUY EQUIP",
        "fields": {"item": "holds", "qty": ""},
        "gearNote": "Holds: 200 cr each, up to 10",
        "labels": ["CONFIRM"],
    }))
    assert trader.decide(_view({
        "sector": "1", "day": "1", "turns": "9", "credits": "50,000 cr", "chip": "YOUR MOVE",
        "formOpen": True, "formText": "BUY EQUIP",
        "fields": {"item": "holds", "qty": "1"},
        "labels": ["CONFIRM"],
    })).label == "CONFIRM"
    again = trader.decide(_view({
        "sector": "1", "day": "1", "turns": "8", "credits": "49,000 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "labels": ["StarDock: buy gear"],
        "warps": [],
    }))
    assert again.label == "StarDock: buy gear"
    assert trader.gear is not None and trader.gear["item"] == "fighters"
    # The buy-gear list names Armid, Limpet and Atomic mines. That is a catalog.
    catalog = trader.decide(_view({
        "sector": "1", "day": "1", "turns": "8", "credits": "49,000 cr", "chip": "YOUR MOVE",
        "here": "StarDock: buy gear Armid Mines Limpet Mines Atomic Mines",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "labels": ["StarDock: buy gear", "1:25 (3t)"],
        "warps": ["1:25 (3t)"],
    }))
    assert catalog.label == "StarDock: buy gear"
    assert 1 not in trader.danger


def test_a_live_reply_is_checked_priced_and_retried(monkeypatch) -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit import providers as minds
    from ai_cockpit.cost import price_usage
    from ai_cockpit.providers import TurnView, system_prompt

    prompt = system_prompt("Getting started\nTrade at ports.")
    assert "Getting started" in prompt and "StarDock" in prompt
    priced = price_usage("grok", "grok-4", input_tokens=1_000_000, output_tokens=1_000_000)
    assert priced.usd == 18.0
    monkeypatch.setenv("XAI_API_KEY", KEYS["XAI_API_KEY"])
    calls = {"n": 0}

    def fake_post(url, body, headers):
        calls["n"] += 1
        assert KEYS["XAI_API_KEY"] not in json.dumps(body)
        label = "Not on screen" if calls["n"] == 1 else "Manual"
        return {
            "choices": [{"message": {"content": json.dumps({"op": "click", "label": label})}}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 10},
        }

    monkeypatch.setattr(minds, "_post_json", fake_post)
    view = TurnView("YOUR MOVE", ["Manual"], b"\x89PNG", True, "Getting started", 2, history=["step 1 click Manual"])
    mind = minds.build_provider("grok", "grok-4")
    action = mind.decide(view)
    assert action.label == "Manual"
    assert calls["n"] == 2
    assert mind.last_usage.input_tokens == 2000
    assert mind.last_usage.output_tokens == 20
    assert mind.last_usage.usd > 0
    assert KEYS["XAI_API_KEY"] not in mind.last_usage.line()


def test_the_lobby_option_is_hidden_until_the_switch_is_on(monkeypatch, tmp_path: Path) -> None:
    from tw2k.public import pages
    from tw2k.public import security as S
    from tw2k.public import workers as WM
    from tw2k.public.ai_cockpit_launch import direct_seat_url, status_line
    from tw2k.public.lobby import Lobby

    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "legacy")
    hidden = pages.new_game("Galaxy War Command")
    assert "AI cockpit seat" not in hidden
    assert 'name="ai_cockpit"' not in hidden
    with pytest.raises(S.FormError, match="unknown field: ai_cockpit"):
        S.parse_game_form({"name": "Alpha", "ai_cockpit": "on"})
    stored = S.parse_game_form({"name": "Alpha", "humans": 1, "bots": 2}).settings()
    stored["ai_cockpit"] = True
    cmd = " ".join(WM.serve_command(stored, 47310, tmp_path))
    assert "--external P1" in cmd
    assert "AI cockpit" not in cmd

    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "tw2002")
    shown = pages.new_game("Galaxy War Command")
    assert "AI cockpit seat" in shown
    assert 'name="ai_cockpit_provider"' in shown
    assert 'name="ai_cockpit_model"' in shown
    form = S.parse_game_form({
        "name": "Alpha", "humans": 1, "bots": 2, "ai_cockpit": "on",
        "ai_cockpit_provider": "grok", "ai_cockpit_model": "grok-4",
    })
    settings = form.settings()
    assert settings["ai_cockpit"] is True
    assert settings["ai_cockpit_provider"] == "grok"
    assert settings["ai_cockpit_model"] == "grok-4"
    assert "ai_key" not in settings
    joined = " ".join(WM.serve_command(settings, 47311, tmp_path))
    assert "--external P1,P2" in joined
    assert "--num-agents 4" in joined
    assert "AI cockpit" in joined
    both = dict(settings)
    both["ai_opponents"] = 1
    both["ai_brain"] = "heuristic"
    monkeypatch.setattr(K, "LOBBY_AI_SEAT_MODE", "on")
    mixed = " ".join(WM.serve_command(both, 47312, tmp_path))
    assert "--external P1,P2,P3" in mixed
    assert "AI (heuristic)" in mixed and "AI cockpit" in mixed

    lobby = Lobby.__new__(Lobby)
    lobby.cockpit_rows = {
        "game": {"seat": "P2", "token": TOKEN, "provider": "scripted", "model": "", "proc": None},
    }
    lobby.workers = type("W", (), {
        "workers": {"game": type("P", (), {"port": 8043})()},
        "game_dir": lambda self, gid: tmp_path / gid,
    })()
    lobby.store = type("S", (), {"game": lambda self, gid: {"settings": settings}})()
    captured: dict = {}

    def fake_launch(*args, **kwargs):
        captured["args"] = args
        captured.update(kwargs)
        return type("Proc", (), {"poll": lambda self: None})()

    monkeypatch.setattr(lobby, "launch_browser_seat", fake_launch)
    lobby._launch_cockpit("game")
    assert captured["base_url"] == "http://127.0.0.1:8043"
    assert captured["path"] == direct_seat_url("P2", TOKEN)
    assert TOKEN not in status_line("scripted", "", True)
    card = pages.created(
        "Galaxy War Command",
        game={"id": "game", "name": "Alpha", "settings": {**settings, "day_seconds": 1800}},
        join_links=[], watch_link="http://127.0.0.1/g/game/watch",
        cockpit={"status": status_line("scripted", "", True), "seat": "P2", "href": "/games/game/ai-seat"},
    )
    assert "AI cockpit seat: scripted, running" in card
    assert 'data-cockpit="seat"' in card
    assert TOKEN not in card
    assert "/g/game/watch" in card


def _numbers(log: str, key: str) -> list[int]:
    import re

    found = []
    for match in re.finditer(rf"{key}=([\d,]+)", log):
        found.append(int(match.group(1).replace(",", "")))
    return found


def test_scripted_player_gains_net_worth_over_three_days(tmp_path: Path) -> None:
    pytest.importorskip("playwright.sync_api")
    run = tmp_path / "run"
    with CuHost(tmp_path / "host", TOKEN, max_days=3, turns_per_day=9) as host:
        assert host.port not in RESERVED_TEST_PORTS
        assert host.port not in FORBIDDEN
        assert allowed_test_port(host.port)
        url = f"{host.base}/bot?seat=P2&mode=cu&token={TOKEN}&layout=redesign"
        proc = subprocess.run(
            [sys.executable, str(PLAYER), "--url", url, "--provider", "scripted",
             "--max-turns", "60", "--min-interval", "0", "--run-dir", str(run)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
            timeout=240,
            env={**os.environ, **KEYS, "PYTHONPATH": str(REPO / "src")},
        )
    log = (run / "player.log").read_text(encoding="utf-8") if (run / "player.log").is_file() else ""
    assert proc.returncode == 0, proc.stderr + proc.stdout + "\n" + log[-4000:]
    days = set(_numbers(log, "day"))
    assert {1, 2, 3} <= days, log[-4000:]
    worth = _numbers(log, "nw")
    assert worth and worth[-1] > worth[0], log[-4000:]
    assert "game over" in log
    blob = log + proc.stdout + proc.stderr
    for path in run.iterdir():
        if path.suffix in {".txt", ".jsonl"}:
            blob += path.read_text(encoding="utf-8", errors="replace")
    for secret in (*KEYS.values(), TOKEN):
        assert secret not in blob
    assert (run / "modules.txt").read_text(encoding="utf-8").strip() == ""


def test_scripted_player_buys_holds_and_fighters_at_stardock(tmp_path: Path) -> None:
    pytest.importorskip("playwright.sync_api")
    run = tmp_path / "yard"
    with CuHost(tmp_path / "host", TOKEN, max_days=1, turns_per_day=12, park_at=1) as host:
        assert host.port not in RESERVED_TEST_PORTS
        assert host.port not in FORBIDDEN
        assert allowed_test_port(host.port)
        url = f"{host.base}/bot?seat=P2&mode=cu&token={TOKEN}&layout=redesign"
        proc = subprocess.run(
            [sys.executable, str(PLAYER), "--url", url, "--provider", "scripted",
             "--max-turns", "18", "--min-interval", "0", "--run-dir", str(run)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
            timeout=150,
            env={**os.environ, **KEYS, "PYTHONPATH": str(REPO / "src")},
        )
    log = (run / "player.log").read_text(encoding="utf-8") if (run / "player.log").is_file() else ""
    assert proc.returncode == 0, proc.stderr + proc.stdout + "\n" + log[-3000:]
    actions = [json.loads(line) for line in (run / "actions.jsonl").read_text(encoding="utf-8").splitlines()]
    labels = [str(row["label"]) for row in actions]
    texts = [str(row["text"]) for row in actions]
    assert any(label.startswith("StarDock") for label in labels), labels
    assert "holds" in texts and "fighters" in texts, texts
