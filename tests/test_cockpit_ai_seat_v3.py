"""NOTE 95. The cockpit seat on V311_PROFILE, still test-only.

The 2-day run stays inside CI time by using a 12-second day (the clock's
minimum is 10). The heuristic brain stays the default. The LLM hook reads
TW2K_COCKPIT_LLM_KEY and does not open a socket when that variable is empty.
"""

from __future__ import annotations

import asyncio
import socket
import urllib.request

import httpx

import tw2k.agents.cockpit_seat as seat
import tw2k.engine.constants as K
from scripts import cockpit_seat_v311 as v311
from tests.test_external_harness_phase1 import TOK2, _wait_until
from tw2k.engine import GameConfig
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

ROUTE_PREFIX = "/harness/v1/P2/"


def _two_day_spec() -> MatchSpec:
    cfg = GameConfig(
        seed=250925,
        universe_size=200,
        max_days=2,
        turns_per_day=100,
        starting_credits=20_000,
        enable_ferrengi=True,
        enable_planets=True,
        action_delay_s=0.0,
        all_start_stardock=True,
        turn_regen_day_seconds=12,
    )
    return MatchSpec(
        config=cfg,
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="CockpitSeat", kind="external", external_token=TOK2),
        ],
        action_delay_s=0.0,
        external_timeout_s=180.0,
    )


def test_v311_two_days_trades_and_lifts_off(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "tw2002")
    monkeypatch.delenv(seat.LLM_KEY_ENV, raising=False)
    monkeypatch.delenv(seat.LLM_URL_ENV, raising=False)
    assert K.v311_profile() is True
    assert K.ai_cockpit_seat_on() is True

    app = create_app(auto_start=False)
    app.state.runner._saves_root = tmp_path / "saves"
    runner = app.state.runner
    seen: list[tuple[str, str]] = []

    async def _record(request: httpx.Request) -> None:
        seen.append((request.method, request.url.path))

    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 5555))
    http = httpx.AsyncClient(
        transport=transport, base_url="http://harness.test", timeout=60.0,
        event_hooks={"request": [_record]},
    )

    async def _go() -> dict:
        await runner.start(_two_day_spec())
        assert await _wait_until(lambda: runner.state.universe is not None, tries=500, dt=0.05)
        try:
            return await seat.run_http(http, "P2", TOK2, 2, idle_s=90)
        finally:
            await runner.stop()
            await http.aclose()

    report = asyncio.run(_go())
    assert report["refused"] == []
    assert report["died"] is False
    assert [row["day"] for row in report["days"]] == [1, 2]
    assert report["kinds"].get("liftoff", 0) >= 1
    assert report["kinds"].get("trade", 0) > 0
    assert report["days"][-1]["credits_end"] > report["days"][0]["credits_start"]
    assert {row["id"] for row in report["gaps"]} <= set(seat.GAP_TEXT)
    for method, path in seen:
        assert path.startswith(ROUTE_PREFIX), path
        assert path.removeprefix(ROUTE_PREFIX) in {"observation", "reference", "events", "status", "action"}
        assert (method == "POST") == path.endswith("/action")


def test_llm_hook_does_not_open_a_socket_without_a_key(monkeypatch) -> None:
    monkeypatch.delenv(seat.LLM_KEY_ENV, raising=False)
    monkeypatch.delenv(seat.LLM_URL_ENV, raising=False)

    def _refuse(*_a, **_k):
        raise AssertionError("the hook ran with no key")

    monkeypatch.setattr(seat, "_llm_http_choose", _refuse)
    monkeypatch.setattr(socket, "create_connection", _refuse)
    assert seat.cockpit_llm_key() == ""
    assert seat.llm_choose({"legal_actions": []}) is None


def test_llm_hook_uses_the_caller_and_skips_a_missing_url(monkeypatch) -> None:
    monkeypatch.setenv(seat.LLM_KEY_ENV, "test-only-not-a-real-key")
    monkeypatch.delenv(seat.LLM_URL_ENV, raising=False)

    def _no_urlopen(*_a, **_k):
        raise AssertionError("urlopen")

    monkeypatch.setattr(urllib.request, "urlopen", _no_urlopen)
    assert seat.llm_choose({"legal_actions": []}) is None

    def _ask(key, _obs, _cockpit):
        assert key == "test-only-not-a-real-key"
        return ("wait", {}, "hold")

    assert seat.llm_choose({"legal_actions": []}, ask=_ask) == ("wait", {}, "hold")
    assert seat.llm_choose({"legal_actions": []}, ask=lambda *_a: ("not-a-kind", {}, "no")) is None


def test_scripted_challenge_and_terra(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "tw2002")
    monkeypatch.delenv(seat.LLM_KEY_ENV, raising=False)

    challenge = asyncio.run(v311.challenge_exchange())
    assert challenge["seat_deploy_qty"] > 0
    assert challenge["bot_deploy_qty"] > 0
    assert challenge["answered"] is not None
    assert challenge["answered"]["ok"] is not False

    terra = asyncio.run(v311.terra_citadel())
    assert terra["terra_holds_taken"] > 0
    after = terra.get("planet_after") or {}
    after_col = int(after.get("colonists_total") or 0)
    assert after_col > terra["colonists_before"]
    assert any(terra["goods_dumped"][name] > 0 for name in ("fuel_ore", "organics", "equipment"))
    build = terra["build"]
    # The build either starts, or the form names the colonist gap the routes cannot close.
    assert build["ok"] is True or (build["error"] and "colonists" in str(build["error"]))
