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
# Protected live bands. free_port may still hand out an OS ephemeral port above them.
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


def test_the_scripted_trader_keeps_a_port_pair_and_declines_a_bad_counter() -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.trader import ScriptedTrader

    trader = ScriptedTrader()
    # A neighbour pays more for the fuel, and the hop still leaves a turn to sell.
    held = trader.decide(_view({
        "sector": "16", "day": "1", "turns": "9", "credits": "49,317 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 10 Organics 0 Equipment 0",
        "ship": "Holds 10/20",
        "port": "Port Hydra Class 6 BBS",
        "rows": [{
            "cells": ["Fuel Ore", "Buying, room 1000", "1000", "33", "10"],
            "button": "SELL 10",
        }],
        "labels": ["SELL 10", "1:35 (3t)"],
        "warps": ["1:35 (3t)"],
    }))
    assert held.label == "SELL 10"
    trader.ports[35] = {"Fuel Ore": {"bid": 39}}
    trader.links[16] = {35: 3}
    trader.warp_labels[(16, 35)] = "1:35 (3t)"
    moved = trader.decide(_view({
        "sector": "16", "day": "1", "turns": "9", "credits": "49,317 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 10 Organics 0 Equipment 0",
        "ship": "Holds 10/20",
        "port": "Port Hydra Class 6 BBS",
        "rows": [{
            "cells": ["Fuel Ore", "Buying, room 1000", "1000", "33", "10"],
            "button": "SELL 10",
        }],
        "labels": ["SELL 10", "1:35 (3t)"],
        "warps": ["1:35 (3t)"],
    }))
    assert moved.label == "1:35 (3t)"
    # Empty holds, and the organics pair is already on the map. Don't wander.
    trader.ports[16]["Organics"] = {"bid": 96}
    trader.ports[35]["Organics"] = {"ask": 53}
    trader.links[35] = {16: 3}
    trader.warp_labels[(35, 16)] = "1:16 (3t)"
    paired = trader.decide(_view({
        "sector": "16", "day": "2", "turns": "24", "credits": "49,647 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "port": "Port Hydra Class 6 BBS",
        "rows": [{
            "cells": ["Organics", "Buying, room 1000", "1000", "96", "0"],
            "button": "",
        }],
        "labels": ["1:35 (3t)", "2:126 (3t)"],
        "warps": ["1:35 (3t)", "2:126 (3t)"],
    }))
    assert paired.label == "1:35 (3t)"
    # Three turns cannot finish another sale. Park on the seller, don't take the one-way.
    parked = trader.decide(_view({
        "sector": "16", "day": "2", "maxDay": "3", "turns": "3", "credits": "51,000 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "port": "Port Hydra Class 6 BBS",
        "labels": ["1:35 (3t)", "2:126 (3t)"],
        "warps": ["1:35 (3t)", "2:126 (3t)"],
    }))
    assert parked.label == "1:35 (3t)"
    # The last day has nowhere to deliver a parked ship, so the leftover turns are waits.
    last = trader.decide(_view({
        "sector": "16", "day": "3", "maxDay": "3", "turns": "3", "credits": "51,000 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "port": "Port Hydra Class 6 BBS",
        "labels": ["1:35 (3t)", "2:126 (3t)"],
        "warps": ["1:35 (3t)", "2:126 (3t)"],
    }))
    assert last.op == "press" and last.key == "."
    # Fuel at 39 is the best fuel bid. Organics paying 96 must not sink this sale.
    fuel_ok = trader.decide(_view({
        "sector": "35", "day": "2", "turns": "8", "credits": "49,000 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 10 Organics 0 Equipment 0",
        "formOpen": True,
        "formText": "TRADE",
        "haggle": "We'll buy them for 39 cr each.",
        "fields": {"unit_price": "39", "qty": "10"},
        "labels": ["CONFIRM", "ESC"],
        "warps": ["1:16 (3t)"],
    }))
    assert fuel_ok.label == "CONFIRM"
    low = trader.decide(_view({
        "sector": "35", "day": "2", "turns": "8", "credits": "49,000 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 20 Equipment 0",
        "formOpen": True,
        "formText": "TRADE",
        "haggle": "We'll buy them for 10 cr each.",
        "fields": {"unit_price": "10", "qty": "20"},
        "labels": ["CONFIRM", "ESC"],
        "warps": ["1:16 (3t)"],
    }))
    assert low.label == "ESC"


def test_the_scripted_trader_keeps_the_best_pair_and_banks_the_surplus() -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.trader import ScriptedTrader

    trader = ScriptedTrader()
    trader.ports[16] = {"Organics": {"bid": 96}, "Fuel Ore": {"bid": 33}}
    trader.ports[35] = {"Organics": {"ask": 53}, "Fuel Ore": {"bid": 39}}
    trader.ports[85] = {"Organics": {"ask": 79}}
    trader.links = {16: {35: 3, 126: 3}, 35: {16: 3}}
    trader.warp_labels = {(16, 35): "1:35 (3t)", (16, 126): "2:126 (3t)", (35, 16): "1:16 (3t)"}
    trader.day = 2
    trader.max_day = 10
    trader.day_turns = 40
    paired = trader.decide(_view({
        "sector": "16", "day": "2", "maxDay": "10", "turns": "40", "credits": "49,000 cr",
        "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "port": "Port Hydra Class 6 BBS",
        "labels": ["1:35 (3t)", "2:126 (3t)"],
        "warps": ["1:35 (3t)", "2:126 (3t)"],
    }))
    assert paired.label == "1:35 (3t)"
    parked = trader.decide(_view({
        "sector": "16", "day": "2", "maxDay": "10", "turns": "3", "credits": "49,000 cr",
        "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "labels": ["1:35 (3t)", "2:126 (3t)"],
        "warps": ["1:35 (3t)", "2:126 (3t)"],
    }))
    assert parked.label == "1:35 (3t)"
    trader.day = 3
    trader.bought.update({"holds", "fighters", "shields", "ship"})
    bank = trader.decide(_view({
        "sector": "1", "day": "3", "maxDay": "10", "turns": "20", "credits": "80,000 cr",
        "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "port": "StarDock",
        "labels": ["Bank", "Shipyards"],
        "warps": [],
    }))
    assert bank.label == "Bank"
    filled = trader.decide(_view({
        "sector": "1", "day": "3", "turns": "20", "credits": "80,000 cr", "chip": "YOUR MOVE",
        "formOpen": True, "formText": "BANK Balance 0 cr.",
        "fields": {"side": "deposit", "amount": "80000"},
        "labels": ["CONFIRM", "ESC"],
    }))
    assert filled.op == "type" and filled.text == "60000"
    weak = trader.decide(_view({
        "sector": "8", "day": "4", "maxDay": "10", "turns": "20", "credits": "40,000 cr",
        "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "here": "Class M Unclaimed Organics 2 per day",
        "labels": ["QLift off", "Claim planet"],
    }))
    assert "lift off" in weak.label.lower()
    rich = ScriptedTrader()
    rich.day = 4
    rich.max_day = 10
    rich.day_turns = 40
    claimed = rich.decide(_view({
        "sector": "8", "day": "4", "maxDay": "10", "turns": "20", "credits": "40,000 cr",
        "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "here": "Class M Unclaimed Organics 400 per day",
        "labels": ["QLift off", "Claim planet"],
    }))
    assert claimed.label == "Claim planet"


def test_the_scripted_trader_will_not_take_a_one_way_warp_without_a_return() -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.trader import ScriptedTrader

    trader = ScriptedTrader()
    trader.ports[20] = {"Organics": {"bid": 80}}
    trader.ports[10] = {"Organics": {"ask": 40}}
    trader.links = {10: {11: 3, 12: 3}, 11: {20: 3}, 12: {10: 3, 20: 3}, 20: {12: 3}}
    trader.warp_labels = {
        (10, 11): "1:11 (3t) one-way",
        (10, 12): "2:12 (3t)",
        (11, 20): "1:20 (3t)",
        (12, 10): "1:10 (3t)",
        (12, 20): "2:20 (3t)",
        (20, 12): "1:12 (3t)",
    }
    action = trader.decide(_view({
        "sector": "10", "day": "2", "maxDay": "10", "turns": "40", "credits": "49,000 cr",
        "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 20 Equipment 0",
        "ship": "Holds 20/20",
        "labels": ["1:11 (3t) one-way", "2:12 (3t)"],
        "warps": ["1:11 (3t) one-way", "2:12 (3t)"],
    }))
    assert action.label == "2:12 (3t)"


def test_the_scripted_trader_keeps_exploring_until_a_short_pair_pays() -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.trader import ScriptedTrader

    trader = ScriptedTrader()
    trader.day = 2
    trader.max_day = 10
    trader.day_turns = 40
    trader.ports[10] = {"Equipment": {"ask": 100, "avail": 14}}
    trader.ports[80] = {"Equipment": {"bid": 140, "avail": 14}}
    trader.links = {10: {11: 3, 12: 3}, 12: {13: 3}, 13: {14: 3}, 14: {80: 3}, 80: {14: 3}}
    trader.warp_labels = {(10, 11): "1:11 (3t)", (10, 12): "2:12 (3t)"}
    trader.visited.update({10, 12, 13, 14, 80})
    looking = trader.decide(_view({
        "sector": "10", "day": "2", "maxDay": "10", "turns": "40", "credits": "49,000 cr",
        "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "rows": [{
            "cells": ["Equipment", "Selling 14/4000", "14", "100", "0"],
            "button": "BUY 14",
        }],
        "labels": ["BUY 14", "1:11 (3t)", "2:12 (3t)"],
        "warps": ["1:11 (3t)", "2:12 (3t)"],
    }))
    assert looking.label == "1:11 (3t)"
    rich = ScriptedTrader()
    rich.day = 2
    rich.max_day = 10
    rich.day_turns = 40
    rich.hold_cap = 20
    rich.ports[10] = {"Equipment": {"ask": 40, "avail": 90}}
    rich.ports[11] = {"Equipment": {"bid": 100, "avail": 90}}
    rich.links = {10: {11: 3, 12: 3}, 11: {10: 3}, 12: {10: 3}}
    rich.warp_labels = {
        (10, 11): "1:11 (3t)",
        (10, 12): "2:12 (3t)",
        (11, 10): "1:10 (3t)",
        (12, 10): "1:10 (3t)",
    }
    running = rich.decide(_view({
        "sector": "12", "day": "2", "maxDay": "10", "turns": "40", "credits": "49,000 cr",
        "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "labels": ["1:10 (3t)"],
        "warps": ["1:10 (3t)"],
    }))
    assert running.label == "1:10 (3t)"


def test_a_mock_provider_replies_are_validated_like_a_live_model(tmp_path: Path) -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.providers import MockMind, build_provider, system_prompt

    script = tmp_path / "replies.json"
    script.write_text(
        json.dumps([
            json.dumps({"op": "click", "label": "Not on screen"}),
            "not json at all",
            json.dumps({"op": "click", "label": "Manual"}),
        ]),
        encoding="utf-8",
    )
    mind = build_provider("mock", mock_script=str(script))
    assert isinstance(mind, MockMind)
    view = _view({"labels": ["Manual"]}, manual=True, labels=["Manual"])
    view.manual_excerpt = "Getting started\nTrade at ports."
    action = mind.decide(view)
    assert action.label == "Manual"
    assert len(mind.prompts) == 3
    assert "that control is not on screen" in mind.prompts[1]
    assert "the reply had no action object" in mind.prompts[2]
    assert "StarDock" in mind.systems[0]
    assert "Getting started" in system_prompt(view.manual_excerpt)
    assert mind.last_usage is not None and mind.last_usage.provider == "mock"
    assert "xai-" not in script.read_text(encoding="utf-8")


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


def test_easy_wanders_and_buys_a_weak_local_trade() -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.trader import ScriptedTrader

    easy = ScriptedTrader(level="easy")
    bought = easy.decide(_view({
        "sector": "8", "day": "1", "turns": "20", "credits": "50,000 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "rows": [{"cells": ["Organics", "Selling 40/100", "40", "90", "0"], "button": "BUY 10"}],
        "labels": ["BUY 10", "1:9 (3t) one-way", "StarDock: buy gear"],
        "warps": ["1:9 (3t) one-way"],
    }))
    assert bought.label == "BUY 10"
    wandered = easy.decide(_view({
        "sector": "8", "day": "1", "turns": "19", "credits": "49,000 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "labels": ["1:9 (3t) one-way", "StarDock: buy gear"],
        "warps": ["1:9 (3t) one-way"],
    }))
    assert wandered.label == "1:9 (3t) one-way"
    fled = ScriptedTrader(level="easy").decide(_view({
        "sector": "4", "day": "1", "turns": "10", "credits": "50,000 cr", "chip": "YOUR MOVE",
        "here": "Ferrengi Marauder, 40 fighters",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "warps": ["1:4 (3t)", "2:12 (3t)"],
        "labels": ["1:4 (3t)", "2:12 (3t)"],
    }))
    assert fled.label.endswith("12 (3t)")
    # After a short look, easy keeps the thinner pair and does not outfit.
    stuck = ScriptedTrader(level="easy")
    stuck.visited.update({2, 3, 4})
    stuck.day = 2
    stuck.ports[8] = {"Organics": {"ask": 10, "avail": 40}}
    stuck.ports[9] = {"Organics": {"bid": 80, "avail": 40}, "Equipment": {"bid": 30, "avail": 40}}
    stuck.ports[12] = {"Equipment": {"ask": 20, "avail": 40}}
    stuck.links = {8: {9: 3}, 9: {8: 3, 12: 3}, 12: {9: 3}}
    stuck.warp_labels = {
        (8, 9): "1:9 (3t)",
        (9, 8): "1:8 (3t)",
        (9, 12): "2:12 (3t)",
        (12, 9): "1:9 (3t)",
    }
    weak = stuck.decide(_view({
        "sector": "9", "day": "2", "turns": "30", "credits": "40,000 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "labels": ["1:8 (3t)", "2:12 (3t)", "StarDock: buy gear"],
        "warps": ["1:8 (3t)", "2:12 (3t)"],
    }))
    assert weak.label == "2:12 (3t)"
    assert "stardock" not in weak.label.lower()


def test_normal_settles_sooner_and_skips_shields() -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.trader import ScriptedTrader

    def arm(trader: ScriptedTrader) -> None:
        trader.ports[10] = {"Equipment": {"ask": 10, "avail": 100}}
        trader.ports[11] = {"Equipment": {"bid": 18, "avail": 100}}
        trader.links[10] = {11: 3}
        trader.links[11] = {10: 3}
        trader.day_turns = 40
        trader.hold_cap = 20

    normal = ScriptedTrader(level="normal")
    hard = ScriptedTrader(level="hard")
    arm(normal)
    arm(hard)
    assert normal._settled(10) is True
    assert hard._settled(10) is True
    normal.bought.update({"holds", "fighters"})
    normal.day = 2
    normal.links[1] = {10: 3}
    normal.warp_labels[(1, 10)] = "1:10 (3t)"
    dock = normal.decide(_view({
        "sector": "1", "day": "2", "turns": "30", "credits": "10,000 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/40",
        "port": "StarDock",
        "labels": ["StarDock: buy gear", "Shipyards", "1:10 (3t)"],
        "warps": ["1:10 (3t)"],
    }))
    assert dock.label == "StarDock: buy gear"
    assert normal.gear is not None and normal.gear["item"] == "density_scanner"
    assert dock.label != "Shipyards"
    assert "shields" not in normal.plan_note


def test_hard_plots_a_course_when_stardock_was_never_linked() -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.trader import ScriptedTrader

    trader = ScriptedTrader(level="hard")
    trader.ports[35] = {"Organics": {"ask": 20, "avail": 90}}
    trader.ports[16] = {"Organics": {"bid": 96, "avail": 90}}
    trader.links[35] = {16: 3}
    trader.links[16] = {35: 3}
    trader.warp_labels[(35, 16)] = "1:16 (3t)"
    trader.warp_labels[(16, 35)] = "1:35 (3t)"
    trader.day = 2
    trader.settled_day = 1
    trader.day_turns = 40
    trader.visited = {16, 35}
    trader.hold_cap = 20
    assert trader._hops(35, 1) is None
    assert trader._wants_dock(35) is True
    base = {
        "sector": "35", "day": "2", "turns": "30", "credits": "40,000 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "labels": ["C Computer", "1:16 (3t)"],
        "warps": ["1:16 (3t)"],
    }
    opened = trader.decide(_view(base))
    assert opened.label == "C Computer"
    menu = dict(base, menuOpen=True, menuText="Computer command <F> Course Plotter")
    plotted = trader.decide(_view(menu))
    assert plotted.op == "press" and plotted.key == "F"
    asking = dict(menu, menuText="What is the destination sector? ENTER Esc to close", sectorAsk="")
    named = trader.decide(_view(asking))
    assert named.op == "type" and named.selector == "#sectorAsk" and named.text == "1"
    asking["sectorAsk"] = "1"
    asking["labels"] = ["ENTER", "C Computer"]
    entered = trader.decide(_view(asking))
    assert entered.label == "ENTER"
    course = dict(base)
    course["course"] = "Course to 1: 35 > 9 > 1. 2 hops, 6 turns."
    course["warps"] = ["1:9 (3t) one-way"]
    course["labels"] = ["1:9 (3t) one-way", "Engage Express", "Cancel"]
    hopped = trader.decide(_view(course))
    assert hopped.label == "1:9 (3t) one-way"
    stalled = dict(course)
    stalled["turns"] = "2"
    stalled["warps"] = []
    stalled["labels"] = ["Engage Express", "Cancel"]
    stalled["course"] = "Course to 1: 35 > 9 > 1. 2 hops, 6 turns."
    skipped = trader.decide(_view(stalled))
    assert skipped.op != "wait"
    pocket = ScriptedTrader(level="hard")
    for sector in range(20, 26):
        pocket.ports[sector] = {"Equipment": {"ask": 50, "avail": 10}}
    pocket.ports[20] = {"Equipment": {"ask": 40, "avail": 20}}
    pocket.ports[21] = {"Equipment": {"bid": 48, "avail": 20}}
    pocket.links[20] = {21: 3}
    pocket.links[21] = {20: 3}
    pocket.day_turns = 40
    pocket.hold_cap = 20
    pocket.day = 2
    assert pocket._settled(20) is False
    assert pocket._wants_dock(20) is False
    pocket.day = 3
    assert pocket._wants_dock(20) is True
    opened_late = pocket.decide(_view({
        "sector": "20", "day": "3", "turns": "40", "credits": "40,000 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "labels": ["C Computer", "1:21 (3t)"],
        "warps": ["1:21 (3t)"],
    }))
    assert opened_late.label == "C Computer"


def test_hard_skips_a_dock_trip_and_a_ship_that_cannot_pay_back() -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.trader import ScriptedTrader

    trader = ScriptedTrader(level="hard")
    trader.ports[20] = {"Equipment": {"ask": 40, "avail": 20}}
    trader.ports[21] = {"Equipment": {"bid": 48, "avail": 20}}
    trader.links[20] = {21: 3}
    trader.links[21] = {20: 3}
    trader.day = 9
    trader.max_day = 10
    trader.day_turns = 40
    trader.hold_cap = 20
    trader.settled_day = 7
    trader.plot_to = 1
    trader.dock_go = False
    late = trader.decide(_view({
        "sector": "20", "day": "9", "maxDay": "10", "turns": "30", "credits": "40,000 cr",
        "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "course": "Course to 1: 20 > 3 > 4 > 5 > 6 > 7 > 8 > 9 > 14 > 15 > 16 > 17 > 1. 12 hops, 36 turns.",
        "labels": ["Cancel", "1:3 (3t)"],
        "warps": ["1:3 (3t)"],
    }))
    assert late.label == "Cancel"
    assert trader.plot_to == 0
    quote = (
        "CargoTran: 41,625 cr. Holds 75, fighters 400, shields 1,000, 4 turns per warp, "
        "no photons, no TransWarp."
    )
    assert trader._yard_pays({"ship": "Holds 0/20"}, quote) is False
    freighter = (
        "Merchant Freighter: 23,075 cr. Holds 65, fighters 150, shields 200, 2 turns per warp."
    )
    assert trader._yard_pays({"ship": "Holds 0/20"}, freighter) is False
    rich = ScriptedTrader(level="hard")
    rich.ports[10] = {"Equipment": {"ask": 20, "avail": 400}}
    rich.ports[11] = {"Equipment": {"bid": 120, "avail": 400}}
    rich.links[10] = {11: 3}
    rich.links[11] = {10: 3}
    rich.day = 2
    rich.max_day = 10
    rich.day_turns = 40
    rich.hold_cap = 20
    cheap = "Merchant Freighter: 2,000 cr. Holds 40, fighters 50, shields 50, 3 turns per warp."
    assert rich._yard_pays({"ship": "Holds 0/20"}, cheap) is True
    # After the yard is declined, a thin pair is still the route. Hard stays on it.
    trader.bought.update({"holds", "fighters", "shields"})
    trader.ship_skip_profit = 500
    trader.day = 4
    trader.warp_labels[(21, 20)] = "1:20 (3t)"
    assert trader._settled(21) is False
    assert trader._gear_done() is True
    stayed = trader.decide(_view({
        "sector": "21", "day": "4", "maxDay": "10", "turns": "30", "credits": "40,000 cr",
        "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "labels": ["1:20 (3t)", "2:30 (3t)"],
        "warps": ["1:20 (3t)", "2:30 (3t)"],
    }))
    assert stayed.label == "1:20 (3t)"
    medium = ScriptedTrader(level="hard")
    medium.ports[10] = {"Equipment": {"ask": 40, "avail": 200}}
    medium.ports[11] = {"Equipment": {"bid": 70, "avail": 200}}
    medium.links[1] = {10: 3}
    medium.links[10] = {1: 3, 11: 3}
    medium.links[11] = {10: 3}
    medium.day = 3
    medium.max_day = 10
    medium.day_turns = 40
    medium.hold_cap = 20
    scout = (
        "Scout Marauder: 5,625 cr. Holds 25, fighters 150, shields 100, 2 turns per warp, "
        "no photons, no TransWarp. Trade-in sells your ship for 10,325 cr and you fly the new one."
    )
    assert medium._yard_pays({"ship": "Holds 0/20"}, scout) is False


def test_a_known_pair_is_not_left_for_an_unseen_sector() -> None:
    """Seed 7: the organics pair is on screen and the ask has no stock. Stay put."""
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.trader import ScriptedTrader

    trader = ScriptedTrader(level="normal")
    trader.day = 1
    trader.max_day = 10
    trader.day_turns = 40
    trader.hold_cap = 20
    trader.visited = {4, 117}
    trader.previous = 117
    rows = [
        {"cells": ["Fuel Ore", "Buying, room 2,928", "2,928", "33", "0"], "button": ""},
        {"cells": ["Organics", "Selling 0/2,629", "0", "73", "0"], "button": ""},
        {"cells": ["Equipment", "Buying, room 2,744", "2,744", "172", "0"], "button": ""},
    ]
    trader.ports[117] = {"Organics": {"bid": 99, "avail": 2987, "now": 2987}}
    trader.links[117] = {32: 3, 4: 3}
    trader.links[32] = {117: 3, 101: 3}
    trader.warp_labels[(32, 117)] = "2:117 (3t)"
    trader.warp_labels[(32, 101)] = "1:101 (3t)"
    stayed = trader.decide(_view({
        "sector": "32", "day": "1", "maxDay": "10", "turns": "34", "credits": "49,951 cr",
        "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "port": "Class 2 BSB",
        "rows": rows,
        "labels": ["1:101 (3t)", "2:117 (3t)"],
        "warps": ["1:101 (3t)", "2:117 (3t)"],
    }))
    assert stayed.label != "1:101 (3t)"
    assert 101 not in trader.visited
    alien = ScriptedTrader(level="hard")
    fled = alien.decide(_view({
        "sector": "8", "day": "1", "turns": "20", "credits": "40,000 cr", "chip": "YOUR MOVE",
        "here": "Alien trader, 12 fighters",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "warps": ["1:2 (3t)", "2:9 (3t)"],
        "labels": ["1:2 (3t)", "2:9 (3t)"],
    }))
    assert fled.label == "1:2 (3t)" or fled.label == "2:9 (3t)"
    assert 8 in alien.danger
    remembered = alien.decide(_view({
        "sector": "2", "day": "1", "turns": "17", "credits": "40,000 cr", "chip": "YOUR MOVE",
        "here": "clear",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "warps": ["1:8 (3t)", "2:9 (3t)"],
        "labels": ["1:8 (3t)", "2:9 (3t)"],
    }))
    assert remembered.label == "2:9 (3t)"
    warned = ScriptedTrader(level="hard")
    warned.decide(_view({
        "sector": "9", "day": "1", "turns": "19", "credits": "0 cr", "chip": "YOUR MOVE",
        "last": "25 armid mines hit Commander entering 48 (500 dmg)",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "warps": ["1:48 (6t)", "2:120 (6t)"],
        "labels": ["1:48 (6t)", "2:120 (6t)"],
    }))
    assert 48 in warned.danger
    dense = ScriptedTrader(level="hard")
    dense.scanner = True
    dense.scan_pending = 9
    dense.decide(_view({
        "sector": "9", "day": "2", "turns": "30", "credits": "40,000 cr", "chip": "YOUR MOVE",
        "last": "Sector 48 ==> 5,500 Warps : 1 NavHaz : 0% Anom : No",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "warps": ["1:48 (3t)", "2:120 (3t)"],
        "labels": ["1:48 (3t)", "2:120 (3t)"],
    }))
    assert 48 in dense.danger
    assert 9 in dense.scanned


def test_one_probe_when_the_shelf_has_no_scanner() -> None:
    """The legacy gear list has probes. Buy one, then stop."""
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.trader import ScriptedTrader

    trader = ScriptedTrader(level="hard")
    trader.bought.update({"holds", "fighters"})
    trader.credits = 40_000
    trader.gear = {"item": "density_scanner", "phase": "select"}
    first = trader.decide(_view({
        "sector": "1", "day": "2", "turns": "28", "credits": "40,000 cr", "chip": "YOUR MOVE",
        "formOpen": True, "formText": "BUY EQUIP",
        "fields": {"item": "holds", "itemOptions": ["holds", "fighters", "ether_probes"]},
        "labels": ["CONFIRM", "ESC"],
    }))
    assert first.op == "type" and first.text == "ether_probes"
    trader.gear = {"item": "ether_probes", "phase": "confirm"}
    assert trader.decide(_view({
        "sector": "1", "day": "2", "turns": "28", "credits": "40,000 cr", "chip": "YOUR MOVE",
        "formOpen": True, "formText": "BUY EQUIP",
        "fields": {"item": "ether_probes", "qty": "1", "itemOptions": ["holds", "fighters", "ether_probes"]},
        "labels": ["CONFIRM"],
    })).label == "CONFIRM"
    assert "ether_probes" in trader.bought
    again = trader.decide(_view({
        "sector": "1", "day": "2", "turns": "28", "credits": "35,000 cr", "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "labels": ["StarDock: buy gear", "Bank"],
        "warps": [],
    }))
    assert again.label != "StarDock: buy gear"


def test_a_thin_restock_stays_on_the_known_pair() -> None:
    """Seed 7 day 2: the real quantity is small. Do not walk into an unseen sector."""
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.trader import ScriptedTrader

    trader = ScriptedTrader(level="normal")
    trader.settled_day = 1
    trader.visited = {4, 117, 32}
    trader.previous = 117
    trader.ports[32] = {"Organics": {"ask": 73, "avail": 4, "now": 0}}
    trader.ports[117] = {"Organics": {"bid": 99, "avail": 4, "now": 4}}
    trader.links[32] = {117: 3, 101: 3}
    trader.links[117] = {32: 3}
    trader.warp_labels[(32, 117)] = "2:117 (3t)"
    trader.warp_labels[(32, 101)] = "1:101 (3t)"
    stayed = trader.decide(_view({
        "sector": "32", "day": "2", "maxDay": "10", "turns": "31", "credits": "50,151 cr",
        "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "port": "Class 2 BSB",
        "rows": [{"cells": ["Organics", "Selling 0/2,629", "0", "73", "0"], "button": ""}],
        "labels": ["1:101 (3t)", "2:117 (3t)"],
        "warps": ["1:101 (3t)", "2:117 (3t)"],
    }))
    assert stayed.label != "1:101 (3t)"
    assert 101 not in trader.visited


def test_a_quiet_map_keeps_looking_and_a_threat_walks_back() -> None:
    """The paying pair is several new hops out. Back up only after a threat."""
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.trader import ScriptedTrader

    trader = ScriptedTrader(level="normal")
    trader.fresh_chain = 5
    trader.visited = {1, 2, 3}
    trader.previous = 2
    options = [(2, "1:2 (3t)", 3), (5, "2:5 (3t)", 3)]
    assert trader._explore_choice(4, options) == 5
    trader.danger.add(9)
    assert trader._explore_choice(4, options) == 2


def test_hard_trades_a_stocked_pair_when_the_best_ask_is_empty() -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    from ai_cockpit.trader import ScriptedTrader

    hard = ScriptedTrader(level="hard")
    hard.day = 4
    hard.max_day = 10
    hard.day_turns = 40
    hard.hold_cap = 20
    hard.visited = {10, 11, 12, 13}
    hard.ports[10] = {"Equipment": {"ask": 20, "avail": 400, "now": 0}}
    hard.ports[11] = {"Equipment": {"bid": 80, "avail": 400, "now": 400}}
    hard.ports[12] = {"Organics": {"ask": 30, "avail": 80, "now": 80}}
    hard.ports[13] = {"Organics": {"bid": 50, "avail": 80, "now": 80}}
    hard.links[10] = {11: 3, 12: 3}
    hard.links[11] = {10: 3}
    hard.links[12] = {10: 3, 13: 3}
    hard.links[13] = {12: 3}
    hard.warp_labels[(10, 12)] = "2:12 (3t)"
    hard.warp_labels[(10, 11)] = "1:11 (3t)"
    hard.pair_blocked = 4
    moved = hard.decide(_view({
        "sector": "10", "day": "4", "maxDay": "10", "turns": "30", "credits": "40,000 cr",
        "chip": "YOUR MOVE",
        "holds": "Fuel Ore 0 Organics 0 Equipment 0",
        "ship": "Holds 0/20",
        "rows": [{"cells": ["Equipment", "Selling 0/400", "0", "20", "0"], "button": ""}],
        "labels": ["1:11 (3t)", "2:12 (3t)"],
        "warps": ["1:11 (3t)", "2:12 (3t)"],
    }))
    assert moved.label == "2:12 (3t)"


def test_several_cockpit_seats_each_get_a_process_and_a_stop(monkeypatch, tmp_path: Path) -> None:
    from tw2k.public import pages
    from tw2k.public import security as S
    from tw2k.public import workers as WM
    from tw2k.public.lobby import Lobby

    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "legacy")
    with pytest.raises(S.FormError, match="unknown field: ai_cockpit_count"):
        S.parse_game_form({"name": "Alpha", "ai_cockpit_count": "2"})
    with pytest.raises(S.FormError, match="unknown field: ai_cockpit_level"):
        S.parse_game_form({"name": "Alpha", "ai_cockpit_level": "easy"})

    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "tw2002")
    shown = pages.new_game("Galaxy War Command")
    assert 'name="ai_cockpit_count"' in shown
    assert 'name="ai_cockpit_level"' in shown
    assert 'value="hard" selected' in shown
    form = S.parse_game_form({
        "name": "Alpha", "humans": 1, "bots": 2, "ai_cockpit": "on",
        "ai_cockpit_count": "2", "ai_cockpit_level": "normal",
    })
    settings = form.settings()
    assert settings["ai_cockpit_count"] == 2
    assert settings["ai_cockpit_level"] == "normal"
    assert "ai_key" not in settings
    off = S.parse_game_form({"name": "Alpha", "ai_cockpit": "off", "ai_cockpit_count": "4"}).settings()
    assert "ai_cockpit" not in off
    assert WM.cockpit_count(off) == 0
    assert WM.cockpit_count(settings) == 2
    joined = " ".join(WM.serve_command(settings, 47313, tmp_path))
    assert "--external P1,P2,P3" in joined
    assert "--num-agents 5" in joined
    assert "AI cockpit" in joined

    lobby = Lobby.__new__(Lobby)
    token_a = "seat-token-alpha"
    token_b = "seat-token-beta"
    lobby.cockpit_rows = {
        "game": [
            {"seat": "P2", "token": token_a, "provider": "scripted", "model": "", "level": "normal", "proc": None},
            {"seat": "P3", "token": token_b, "provider": "scripted", "model": "", "level": "hard", "proc": None},
        ],
    }
    lobby.workers = type("W", (), {
        "workers": {"game": type("P", (), {"port": 8050})()},
        "game_dir": lambda self, gid: tmp_path / gid,
    })()
    lobby.store = type("S", (), {"game": lambda self, gid: {"settings": settings}})()
    launched: list[dict] = []

    def fake_launch(*args, **kwargs):
        launched.append({"args": args, **kwargs})
        return type("Proc", (), {"poll": lambda self: None, "terminate": lambda self: None})()

    monkeypatch.setattr(lobby, "launch_browser_seat", fake_launch)
    lobby._launch_cockpit("game")
    assert [row["args"][1] for row in launched] == ["P2", "P3"]
    assert [row["level"] for row in launched] == ["normal", "hard"]
    assert token_a not in str(launched[0]["run_dir"])
    assert launched[0]["run_dir"] != launched[1]["run_dir"]
    card = pages.created(
        "Galaxy War Command",
        game={"id": "game", "name": "Alpha", "settings": {**settings, "day_seconds": 1800}},
        join_links=[], watch_link="http://127.0.0.1/g/game/watch",
        cockpit={"status": "two", "seat": "P2", "href": "/games/game/ai-seat",
                 "seats": lobby.cockpit_public("game")},
    )
    assert "AI cockpit seat P2: scripted normal, running" in card
    assert "AI cockpit seat P3: scripted hard, running" in card
    assert 'data-cockpit="stop"' in card
    assert "/games/game/ai-seat/P2/stop" in card
    assert "/games/game/ai-seat/P3/stop" in card
    assert token_a not in card and token_b not in card
    stopped = {"n": 0}

    class Proc:
        def poll(self):
            return None

        def terminate(self):
            stopped["n"] += 1

    lobby.cockpit_rows["game"][0]["proc"] = Proc()
    lobby.cockpit_rows["game"][1]["proc"] = Proc()
    assert lobby.stop_cockpit_seat("game", "P2") is True
    assert stopped["n"] == 1
    assert lobby.cockpit_rows["game"][1]["proc"].poll() is None


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
