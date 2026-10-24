"""TinyBox (server key) brain for lobby AI seats. Only a local fake endpoint is used."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

import tw2k.agents.cockpit_seat as seat
import tw2k.engine.constants as K
import tw2k.public.pages as pages
import tw2k.public.security as S
import tw2k.public.tinybox as TB
import tw2k.public.workers as WM
from tests.test_external_harness_phase1 import TOK2, _wait_until
from tests.test_lobby_ai_opponents_v1 import _SeatIdleClock, _spec, _walk_text
from tw2k.server.app import create_app

_ENV = ("TW2K_CUSTOM_BASE_URL", "TW2K_CUSTOM_API_KEY", "TW2K_TINYBOX_API_KEY", "TW2K_CUSTOM_MAX_TOKENS",
        "TW2K_CUSTOM_THINK_CAP_S", "TW2K_TINYBOX_MODELS", "TW2K_TINYBOX_CALL_CAP", "TW2K_TINYBOX_CALLS_PER_MIN")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in _ENV:
        monkeypatch.delenv(name, raising=False)


def _key() -> str:
    return "tbk" + secrets.token_hex(10)


class _Fake(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        srv = self.server
        body = json.loads(self.rfile.read(int(self.headers.get("content-length") or 0)) or b"{}")
        srv.seen.append({"path": self.path, "auth": self.headers.get("authorization"), "body": body})  # type: ignore[attr-defined]
        mode = srv.mode  # type: ignore[attr-defined]
        if mode == "down":
            raw, code = b"busy", 503
        else:
            user = json.loads(body["messages"][-1]["content"])
            kinds = [row["kind"] for row in user.get("legal_actions") or []]
            kind = "wait" if "wait" in kinds else (kinds[0] if kinds else "wait")
            text = json.dumps({"kind": kind, "args": {}, "why": "fake " + body["model"]})
            msg = {"content": "", "reasoning": "<think>hmm</think>" + text} if mode == "reasoning" else {"content": text}
            raw, code = json.dumps({"choices": [{"message": msg}]}).encode(), 200
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_a) -> None:
        return


@pytest.fixture
def fake():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Fake)
    srv.seen = []  # type: ignore[attr-defined]
    srv.mode = "ok"  # type: ignore[attr-defined]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv
    srv.shutdown()
    t.join(2)


def _point(monkeypatch, srv, key: str) -> None:
    monkeypatch.setenv("TW2K_CUSTOM_BASE_URL", f"http://127.0.0.1:{srv.server_address[1]}/api")
    monkeypatch.setenv("TW2K_TINYBOX_API_KEY", key)
    monkeypatch.setenv("TW2K_CUSTOM_THINK_CAP_S", "20")


_OBS = {
    "day": 3, "credits": 5000, "turns_remaining": 90, "self_id": "P3",
    "sector": {"id": 12, "warps": [4, 9], "port": {"class": "BBS", "prices": {"ore": 30}}},
    "ship": {"holds": 40, "cargo": {"ore": 10}},
    "recent_events": [{"summary": "sold 10 ore"}],
    "legal_actions": [
        {"kind": "warp", "legal": True, "turn_cost": 3, "params": {"target": {"choices": [4, 9]}}},
        {"kind": "wait", "legal": True, "params": {}},
        {"kind": "attack", "legal": False, "reason": "no target"},
    ],
}


def test_parse_models_per_seat() -> None:
    assert TB.parse_models("qwen3.8:latest x2, kimi-k2.6 x2", 4) == [
        "qwen3.8:latest", "qwen3.8:latest", "kimi-k2.6", "kimi-k2.6"]
    assert TB.parse_models("kimi-k2.6", 3) == ["kimi-k2.6"] * 3
    assert TB.parse_models("a, b", 4) == ["a", "b", "a", "b"]
    with pytest.raises(ValueError):
        TB.parse_models("a x3, b", 2)
    with pytest.raises(ValueError):
        TB.parse_models("bad\x01", 1)


def test_env_file_loads_without_overriding(tmp_path, monkeypatch) -> None:
    key = _key()
    env = tmp_path / ".env"
    env.write_text(f'# c\nTW2K_CUSTOM_BASE_URL=https://tb.example/api\nTW2K_CUSTOM_API_KEY="{key}"\n'
                   "TW2K_CUSTOM_THINK_CAP_S=240\n", encoding="utf-8")
    monkeypatch.setenv("TW2K_CUSTOM_THINK_CAP_S", "99")
    names = TB.load_env_file(env)
    for n in ("TW2K_CUSTOM_BASE_URL", "TW2K_CUSTOM_API_KEY"):
        monkeypatch.setenv(n, __import__("os").environ[n])  # let monkeypatch undo it
    assert "TW2K_CUSTOM_THINK_CAP_S" not in names
    cfg = TB.config()
    assert cfg.ready and cfg.key == key and cfg.think_cap_s == 99.0
    assert cfg.endpoint == "https://tb.example/api/chat/completions"
    assert key not in repr(cfg) and key not in "".join(names)


def test_form_needs_server_config_and_keeps_key_out(monkeypatch, tmp_path, fake) -> None:
    monkeypatch.setattr(K, "LOBBY_AI_SEAT_MODE", "on")
    data = {"name": "Six", "humans": 1, "bots": 2, "ai_opponents": 4, "ai_brain": "tinybox",
            "ai_models": "qwen3.8:latest x2, kimi-k2.6 x2"}
    with pytest.raises(S.FormError):
        S.parse_game_form(dict(data))
    key = _key()
    _point(monkeypatch, fake, key)
    html = pages.new_game("Galaxy War Command")
    assert "TinyBox (server key)" in html and 'name="ai_models"' in html and key not in html
    settings = S.parse_game_form(dict(data)).settings()
    assert settings["ai_brain"] == "tinybox"
    assert settings["ai_models"] == ["qwen3.8:latest", "qwen3.8:latest", "kimi-k2.6", "kimi-k2.6"]
    cmd = " ".join(WM.serve_command(settings, 47302, tmp_path))
    assert cmd.count("AI (qwen3.8)") == 2 and cmd.count("AI (kimi-k2.6)") == 2
    assert key not in json.dumps(settings) and key not in cmd
    legacy = S.parse_game_form({"name": "L", "humans": 1, "bots": 0, "ai_opponents": 1}).settings()
    assert "ai_models" not in legacy and legacy["ai_brain"] == "heuristic"


def test_budget_sends_cockpit_state_and_model(monkeypatch, fake, caplog) -> None:
    key = _key()
    _point(monkeypatch, fake, key)
    fake.mode = "reasoning"
    b = TB.TinyboxSeatBudget(TB.config(), "kimi-k2.6", gid="g1", seat="P3")
    picked = b("server", _OBS, {"hold_quote": {"next": 762}})
    assert picked == ("wait", {}, "fake kimi-k2.6")
    hit = fake.seen[-1]
    assert hit["path"] == "/api/chat/completions"
    assert hit["auth"] == f"Bearer {key}"
    assert hit["body"]["model"] == "kimi-k2.6" and hit["body"]["max_tokens"] == 4000
    user = json.loads(hit["body"]["messages"][-1]["content"])
    assert user["sector"]["port"]["class"] == "BBS" and user["sector"]["warps"] == [4, 9]
    assert user["ship"]["cargo"] == {"ore": 10}
    assert user["legal_actions"][0]["params"]["target"]["choices"] == [4, 9]
    assert user["blocked_actions"] == {"attack": "no target"}
    assert user["recent_events"] and user["cockpit"]["hold_quote"] == {"next": 762}
    b("server", _OBS, None)
    assert json.loads(fake.seen[-1]["body"]["messages"][-1]["content"])["my_last_moves"][0]["kind"] == "wait"
    fake.mode = "down"
    with caplog.at_level(logging.INFO, logger="tw2k.lobby.tinybox"):
        for _ in range(3):
            assert b("server", _OBS, None) is None
    assert b.lasting_fallback and "HTTP 503" in b.reason
    assert any("FALLBACK to heuristic" in r.getMessage() and "P3" in r.getMessage() for r in caplog.records)
    assert key not in caplog.text


def test_unconfigured_budget_falls_back_and_logs(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="tw2k.lobby.tinybox"):
        b = TB.TinyboxSeatBudget(TB.config(), "qwen3.8:latest", gid="g", seat="P2")
    assert b.lasting_fallback and b("x", _OBS, None) is None
    assert "not configured" in caplog.text


def test_caps_default_long_and_configurable(monkeypatch) -> None:
    cfg = TB.config()
    assert cfg.call_cap == 20_000 and cfg.per_minute == 60 and cfg.think_cap_s == 180.0
    monkeypatch.setenv("TW2K_TINYBOX_CALL_CAP", "5")
    monkeypatch.setenv("TW2K_CUSTOM_THINK_CAP_S", "600")
    cfg = TB.config()
    assert cfg.call_cap == 5 and cfg.think_cap_s == 600.0
    assert K.LOBBY_AI_CALL_CAP == 400 and K.LOBBY_AI_CALLS_PER_MINUTE == 6  # legacy unchanged


def test_two_day_seat_plays_through_fake_tinybox(tmp_path, monkeypatch, fake) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    monkeypatch.setattr(K, "LOBBY_AI_SEAT_MODE", "on")
    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "legacy")
    key = _key()
    _point(monkeypatch, fake, key)
    monkeypatch.setenv("TW2K_TINYBOX_CALL_CAP", "40")
    app = create_app(auto_start=False)
    app.state.runner._saves_root = tmp_path / "saves"
    runner = app.state.runner
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5557)),
                             base_url="http://harness.test", timeout=60.0)
    budget = TB.TinyboxSeatBudget(TB.config(), "qwen3.8:latest", gid="t", seat="P2")

    async def _go() -> dict:
        await runner.start(_spec("AI (qwen3.8)"))
        assert await _wait_until(lambda: runner.state.universe is not None, tries=500, dt=0.05)
        monkeypatch.setattr(seat, "time", _SeatIdleClock(runner, 90))
        try:
            return await seat.run_http(http, "P2", TOK2, 2, lobby=True, idle_s=90, llm_key="server",
                                       llm_ask=budget, fallback_line="x")
        finally:
            await runner.stop()
            await http.aclose()

    report = asyncio.run(_go())
    assert len(fake.seen) >= 1 and all(s["body"]["model"] == "qwen3.8:latest" for s in fake.seen)
    assert report["died"] is False and [r["day"] for r in report["days"]] == [1, 2]
    assert key not in _walk_text(tmp_path)
