"""NOTE 100. Lobby AI seats. The switch stays off unless a test turns it on.

No API key is written in this file. A test builds one at runtime and points
the seat at a local fake endpoint.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
from starlette.testclient import TestClient

import tw2k.agents.cockpit_seat as seat
import tw2k.engine.constants as K
import tw2k.public.pages as pages
import tw2k.public.security as S
import tw2k.public.workers as WM
from tests.test_external_harness_phase1 import TOK2, _wait_until
from tw2k.engine import GameConfig
from tw2k.public.ai_seat import FALLBACK_LINE, LlmBudget, mask_key
from tw2k.public.config import LobbyConfig
from tw2k.public.lobby import create_lobby_app
from tw2k.public.manual import render
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

_SETTINGS_KEYS = {
    "rules", "universe_size", "max_days", "turns_per_day", "starting_package",
    "bots", "ferrengi", "day", "day_seconds", "humans", "seed",
}


def _runtime_key() -> str:
    return "local" + secrets.token_hex(8)


def _walk_text(root: Path) -> str:
    chunks: list[str] = []
    if not root.exists():
        return ""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            chunks.append(path.read_bytes().decode("utf-8", errors="replace"))
    return "\n".join(chunks)


def test_switch_off_leaves_the_form_the_parser_and_the_command(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(K, "LOBBY_AI_SEAT_MODE", "off")
    assert K.lobby_ai_seat_on() is False
    html = pages.new_game("Galaxy War Command")
    assert 'name="ai_opponents"' not in html
    assert 'name="ai_key"' not in html
    assert 'name="ai_endpoint"' not in html
    assert "AI opponents" not in html
    assert "Heuristic (free)" not in html
    bots = html.index('name="bots"')
    ferr = html.index('name="ferrengi"')
    assert "ai_" not in html[bots:ferr]
    plain = S.parse_game_form({"name": "Alpha", "humans": 2, "bots": 3, "ferrengi": "off", "day": "1h"})
    assert set(plain.settings()) == _SETTINGS_KEYS
    with pytest.raises(S.FormError, match="unknown field: ai_opponents"):
        S.parse_game_form({"name": "Alpha", "ai_opponents": "1"})
    stored = dict(plain.settings())
    stored["ai_opponents"] = 2
    stored["ai_brain"] = "llm"
    cmd = " ".join(WM.serve_command(stored, 47301, tmp_path))
    assert "--external P1,P2" in cmd
    assert "--num-agents 5" in cmd
    assert "AI (" not in cmd


def test_switch_on_form_parses_the_brain_and_keeps_the_key_out_of_settings(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(K, "LOBBY_AI_SEAT_MODE", "on")
    secret = _runtime_key()
    endpoint = "http://127.0.0.1:9/note100-endpoint"
    html = pages.new_game("Galaxy War Command")
    assert 'name="ai_opponents"' in html
    assert "Heuristic (free)" in html and "LLM (your key)" in html
    assert 'id="ai_key" name="ai_key" type="password"' in html
    assert 'id="ai_endpoint"' in html and 'value=""' in html
    assert secret not in html and endpoint not in html
    assert "Estimate: 0 model calls per game day with the heuristic brain." in html
    echoed = pages.new_game("Galaxy War Command", values={"ai_key": secret, "ai_endpoint": endpoint, "name": "A"})
    assert secret not in echoed and endpoint not in echoed
    form = S.parse_game_form({
        "name": "Alpha", "humans": 1, "bots": 0, "ai_opponents": 1, "ai_brain": "llm",
        "ai_key": secret, "ai_endpoint": endpoint,
    })
    settings = form.settings()
    assert settings["ai_opponents"] == 1 and settings["ai_brain"] == "llm"
    assert "ai_key" not in settings and "ai_endpoint" not in settings
    assert secret not in repr(form) and secret not in json.dumps(settings)
    assert endpoint not in json.dumps(settings)
    cmd = WM.serve_command(settings, 47302, tmp_path)
    joined = " ".join(cmd)
    assert "--external P1,P2" in joined
    assert "--num-agents 2" in joined
    assert "AI (LLM)" in joined
    assert secret not in joined and endpoint not in joined
    env = WM.worker_env(
        gid="ab12cd34", settings=settings, game_dir=tmp_path, brand="Galaxy War Command",
        lobby_secret="L" * 64, spectator_token="T" * 64, seat_tokens={"P1": "a" * 43, "P2": "b" * 43},
        resume=None, base={"PATH": "p"},
    )
    blob = json.dumps(env)
    assert secret not in blob and endpoint not in blob
    assert mask_key(secret) == "key ****" + secret[-4:]
    assert secret not in mask_key(secret)


def test_a_posted_key_stays_out_of_files_logs_and_responses(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(K, "LOBBY_AI_SEAT_MODE", "on")
    secret = _runtime_key()
    endpoint = "http://127.0.0.1:9/note100-endpoint"
    cfg = LobbyConfig(root=tmp_path / "selfhost", port=47299, game_ports=range(47300, 47310), tick_s=3600.0)
    app = create_lobby_app(cfg, port_probe=lambda _p: True)
    lob = app.state.lobby
    lob.cfg.new_games_per_hour = 100

    async def fake_start(gid, *, resume):
        lob.store.set_game(gid, status="running", port=47300)
        return True

    lob.start_game = fake_start
    with TestClient(app) as c:
        assert c.post("/api/accept", json={}).status_code == 200
        bad = c.post("/new", data={"name": "", "ai_opponents": "1", "ai_brain": "llm", "ai_key": secret,
                                   "ai_endpoint": endpoint})
        assert bad.status_code == 400
        assert secret not in bad.text and endpoint not in bad.text
        created = c.post("/api/games", json={
            "name": "With AI", "humans": 1, "bots": 0, "ai_opponents": 1, "ai_brain": "llm",
            "ai_key": secret, "ai_endpoint": endpoint,
        })
        assert created.status_code == 200, created.text
        body = created.json()
        assert list(body["join_links"]) == ["P1"]
        gid = body["id"]
        pages_text = "\n".join([
            bad.text, created.text, c.get("/").text, c.get("/new").text, c.get("/about").text,
            c.get("/manual").text, c.get("/admin").text, c.get(f"/api/games/{gid}").text,
        ])
        assert secret not in pages_text and endpoint not in pages_text
        row = lob.ai_memory.row(gid)
        assert row is not None and row.key == secret and row.url == endpoint
        assert secret not in repr(row)
        on_disk = _walk_text(lob.cfg.root)
        assert secret not in on_disk and endpoint not in on_disk
        assert ("key ****" + secret[-4:]) in on_disk
        lob._drop_ai(gid)
        assert lob.ai_memory.row(gid) is None
        assert secret not in _walk_text(lob.cfg.root)


def test_profile_does_not_turn_lobby_ai_on(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    monkeypatch.setattr(K, "LOBBY_AI_SEAT_MODE", "off")
    assert K.v311_profile() is True
    assert K.lobby_ai_seat_on() is False
    assert "lobby_ai_seat_on" not in K.V311_PROFILE_HELPERS
    html = render("Galaxy War Command")
    assert 'id="ai-opponents"' in html
    assert "Bring your own key" in html or "bring your own key" in html
    assert "not written to disk" in html


def test_budget_caps_and_endpoint_errors_fall_back(monkeypatch) -> None:
    monkeypatch.setattr(seat, "_llm_http_choose", lambda *_a, **_k: ("wait", {}, "hold"))
    capped = LlmBudget(url="http://127.0.0.1:9/v1", cap=1, per_minute=10)
    assert capped("abc", {}, None) == ("wait", {}, "hold")
    assert capped("abc", {}, None) is None and capped.lasting_fallback is True
    paced = LlmBudget(url="http://127.0.0.1:9/v1", cap=10, per_minute=1)
    assert paced("abc", {}, None)[0] == "wait"
    assert paced("abc", {}, None) is None and paced.lasting_fallback is False

    def _down(*_a, **_k):
        raise OSError("endpoint down")

    monkeypatch.setattr(seat, "_llm_http_choose", _down)
    failed = LlmBudget(url="http://127.0.0.1:9/v1", cap=5, per_minute=5)
    assert failed("abc", {}, None) is None and failed.lasting_fallback is True


def test_lobby_off_refuses_the_seat() -> None:
    async def _go() -> None:
        await seat.CockpitSeat("P2", None, None).run(1, lobby=True)

    try:
        asyncio.run(_go())
    except seat.CockpitSeatOff as exc:
        assert "LOBBY_AI_SEAT_MODE" in str(exc)
    else:
        raise AssertionError("the seat ran while the switch was off")


def _spec(name: str) -> MatchSpec:
    cfg = GameConfig(
        seed=250925, universe_size=200, max_days=2, turns_per_day=100,
        starting_credits=20_000, enable_ferrengi=True, enable_planets=True,
        action_delay_s=0.0, all_start_stardock=True, turn_regen_day_seconds=12,
    )
    return MatchSpec(
        config=cfg,
        agents=[
            AgentSpec(player_id="P1", name="Vega", kind="heuristic"),
            AgentSpec(player_id="P2", name=name, kind="external", external_token=TOK2),
        ],
        action_delay_s=0.0,
        external_timeout_s=180.0,
    )


def test_two_day_heuristic_ai_seat_finishes(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    monkeypatch.setattr(K, "LOBBY_AI_SEAT_MODE", "on")
    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "legacy")
    assert K.ai_cockpit_seat_on() is False
    monkeypatch.delenv(seat.LLM_KEY_ENV, raising=False)
    monkeypatch.delenv(seat.LLM_URL_ENV, raising=False)

    def _refuse(*_a, **_k):
        raise AssertionError("heuristic seat opened a socket")

    monkeypatch.setattr(urllib.request, "urlopen", _refuse)
    app = create_app(auto_start=False)
    app.state.runner._saves_root = tmp_path / "saves"
    runner = app.state.runner
    seen: list[tuple[str, str]] = []
    bodies: list[str] = []

    async def _record(request: httpx.Request) -> None:
        seen.append((request.method, request.url.path))

    async def _body(response: httpx.Response) -> None:
        await response.aread()
        bodies.append(response.text)

    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 5555))
    http = httpx.AsyncClient(
        transport=transport, base_url="http://harness.test", timeout=60.0,
        event_hooks={"request": [_record], "response": [_body]},
    )

    async def _go() -> dict:
        await runner.start(_spec("AI (heuristic)"))
        assert await _wait_until(lambda: runner.state.universe is not None, tries=500, dt=0.05)
        try:
            report = await seat.run_http(http, "P2", TOK2, 2, lobby=True, idle_s=90)
            obs = await http.get("/harness/v1/P2/observation", params={"peek": 1},
                                 headers={"authorization": f"Bearer {TOK2}"})
            report["names"] = [row.get("name") for row in (obs.json().get("observation") or {}).get("trader_rankings") or []]
            return report
        finally:
            await runner.stop()
            await http.aclose()

    report = asyncio.run(_go())
    assert report["died"] is False
    assert [row["day"] for row in report["days"]] == [1, 2]
    assert "AI (heuristic)" in report["names"]
    assert report["kinds"].get("liftoff", 0) >= 1
    for method, path in seen:
        assert path.startswith("/harness/v1/P2/"), path
        assert path.removeprefix("/harness/v1/P2/") in {"observation", "reference", "events", "status", "action"}
        assert (method == "POST") == path.endswith("/action")
    assert "AI (heuristic)" in " ".join(bodies)


class _FakeLLM(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        server = self.server
        auth = self.headers.get("authorization") or ""
        server.auths.append(auth)  # type: ignore[attr-defined]
        length = int(self.headers.get("content-length") or 0)
        self.rfile.read(length)
        n = server.calls  # type: ignore[attr-defined]
        server.calls = n + 1  # type: ignore[attr-defined]
        if n == 0:
            payload = {"choices": [{"message": {"content": '{"kind": "wait", "args": {}, "why": "hold"}'}}]}
            raw = json.dumps(payload).encode()
            self.send_response(200)
        else:
            raw = b"no"
            self.send_response(500)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args) -> None:
        return


def test_fake_endpoint_calls_then_falls_back(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    monkeypatch.setattr(K, "LOBBY_AI_SEAT_MODE", "on")
    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "legacy")
    monkeypatch.delenv(seat.LLM_KEY_ENV, raising=False)
    monkeypatch.delenv(seat.LLM_URL_ENV, raising=False)
    secret = _runtime_key()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeLLM)
    server.calls = 0  # type: ignore[attr-defined]
    server.auths = []  # type: ignore[attr-defined]
    port = server.server_address[1]
    import threading
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    app = create_app(auto_start=False)
    app.state.runner._saves_root = tmp_path / "saves"
    runner = app.state.runner
    responses: list[str] = []

    async def _body(response: httpx.Response) -> None:
        await response.aread()
        responses.append(response.text)

    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 5556))
    http = httpx.AsyncClient(
        transport=transport, base_url="http://harness.test", timeout=60.0,
        event_hooks={"response": [_body]},
    )
    budget = LlmBudget(url=f"http://127.0.0.1:{port}/v1/chat/completions", cap=8, per_minute=30)

    async def _events() -> list[str]:
        since = 0
        lines: list[str] = []
        for _ in range(30):
            reply = await http.get(
                "/harness/v1/P2/events", params={"since": since, "limit": 500},
                headers={"authorization": f"Bearer {TOK2}"},
            )
            payload = reply.json()
            for ev in payload.get("events") or []:
                lines.append(str(ev.get("summary") or ""))
            if not payload.get("has_more"):
                break
            since = int(payload.get("next_since") or since)
        return lines

    async def _go() -> tuple[dict, list[str]]:
        await runner.start(_spec("AI (LLM)"))
        assert await _wait_until(lambda: runner.state.universe is not None, tries=500, dt=0.05)
        try:
            report = await seat.run_http(
                http, "P2", TOK2, 2, lobby=True, idle_s=90, llm_key=secret, llm_ask=budget,
                fallback_line=FALLBACK_LINE,
            )
            lines = await _events()
            return report, lines
        finally:
            await runner.stop()
            await http.aclose()

    try:
        report, lines = asyncio.run(_go())
    finally:
        server.shutdown()
        thread.join(2)
    assert server.calls >= 1  # type: ignore[attr-defined]
    assert f"Bearer {secret}" in server.auths  # type: ignore[attr-defined]
    assert budget.lasting_fallback is True
    assert report["died"] is False
    assert [row["day"] for row in report["days"]] == [1, 2]
    assert any(FALLBACK_LINE in line for line in lines)
    blob = "\n".join(responses) + _walk_text(tmp_path)
    assert secret not in blob
    assert secret not in "\n".join(lines)
