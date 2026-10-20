"""NOTE 128. A cockpit player that only sees the rendered seat page.

The scripted provider reads the player manual and sells once. The runner
process does not import the engine. Keys and the seat token stay out of the
run log. The lobby hook stays idle while AI_COCKPIT_SEAT_MODE is legacy.
"""

from __future__ import annotations

import ast
import json
import os
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
KEYS = {
    "XAI_API_KEY": "xai-testsecretkey1234567890",
    "OPENAI_API_KEY": "sk-testsecretkey1234567890",
    "ANTHROPIC_API_KEY": "sk-ant-testsecretkey1234567890",
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

    for value in KEYS.values():
        assert redact(f"authorization {value} token=seat-secret") == "authorization [redacted] token=[redacted]"
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
        assert host.port < 8060
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
    assert "SELL" in labels
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
