"""NOTE 55. The cockpit seat plays whole days, and stays off by default.

Flag off: the seat posts nothing, and a default match keeps its seats.
The runner script refuses to start without the switch in its own process.
Flag on: a 2-day run on an in-process app finishes with no refused posts,
and every request the seat sends is one of this seat's five cockpit routes.
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path

import httpx

import tw2k.agents.cockpit_seat as seat
import tw2k.engine.constants as K
from tests.test_external_harness_phase1 import TOK2, _app_and_client, _http_spec, _wait_until
from tw2k.engine import GameConfig
from tw2k.server.runner import AgentSpec, MatchSpec

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_cockpit_seat.py"
ROUTE = re.compile(r"^/harness/v1/P2/(observation|reference|events|status|action)$")


def seat_spec(days: int = 2) -> MatchSpec:
    """P1 heuristic and P2 external, both starting at StarDock."""
    cfg = GameConfig(
        seed=250925,
        universe_size=200,
        max_days=days,
        turns_per_day=100,
        starting_credits=20_000,
        enable_ferrengi=True,
        enable_planets=True,
        action_delay_s=0.0,
        all_start_stardock=True,
    )
    return MatchSpec(
        config=cfg,
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="CockpitSeat", kind="external", external_token=TOK2),
        ],
        action_delay_s=0.0,
        external_timeout_s=120.0,
    )


def test_flag_off_posts_nothing_and_keeps_default_seats(tmp_path) -> None:
    assert K.AI_COCKPIT_SEAT_MODE == "legacy"
    assert K.ai_cockpit_seat_on() is False
    called = {"n": 0}

    async def _refuse(*_a, **_k):
        called["n"] += 1
        raise AssertionError("flag off must not touch the harness")

    async def _off() -> None:
        for attempt in (
            seat.CockpitSeat("P2", _refuse, _refuse).run(2),
            seat.run_http(object(), "P2", "unused", 2),
        ):
            try:
                await attempt
            except seat.CockpitSeatOff:
                continue
            raise AssertionError("legacy mode ran the seat")

    asyncio.run(_off())
    assert called["n"] == 0

    app, http = _app_and_client(tmp_path)
    runner = app.state.runner

    async def _match() -> None:
        await runner.start(_http_spec())
        assert await _wait_until(lambda: runner.state.universe is not None)
        assert [spec.kind for spec in runner._spec.agents] == ["heuristic", "external", "external"]
        assert len(runner.state.agents) == 3
        await runner.stop()
        await http.aclose()

    asyncio.run(_match())


def test_leave_stardock_prefers_a_port_that_can_trade() -> None:
    """v1 fix 6a: tradeable port first, then any port, then the first warp."""

    def obs(reports):
        return {
            "credits": 20_000,
            "ship": {"cargo_free": 20},
            "sector": {"id": 1, "warps_out": [13, 18, 20]},
            "adjacent": [{"id": 13, "port": None}, {"id": 18, "port": "BBS"}, {"id": 20, "port": "SBB"}],
            "known_ports": reports,
            "legal_actions": [{"kind": "warp", "legal": True, "params": {"target": {"choices": [13, 18, 20]}}}],
        }

    full = {"current": 900, "max": 1000}
    empty = {"current": 0, "max": 1000}
    sold_out = {"sector_id": 18, "class": "BBS", "stock": {"fuel_ore": full, "organics": full, "equipment": empty}}
    selling = {"sector_id": 20, "class": "SBB", "stock": {"fuel_ore": full, "organics": full, "equipment": full}}
    assert seat.leave_stardock(obs([sold_out, selling])) == ("warp", {"target": 20})
    assert seat.leave_stardock(obs([sold_out])) == ("warp", {"target": 18})
    bare = obs([])
    bare["adjacent"] = [{"id": 13, "port": None}]
    assert seat.leave_stardock(bare) == ("warp", {"target": 13})


def test_runner_script_refuses_without_the_switch(tmp_path) -> None:
    env = {k: v for k, v in os.environ.items() if k != "AI_COCKPIT_SEAT_MODE"}
    env["PYTHONPATH"] = str(ROOT / "src")
    missing = tmp_path / "no-such-tokens.json"
    for extra in ({}, {"AI_COCKPIT_SEAT_MODE": "legacy"}):
        got = subprocess.run(
            [sys.executable, str(SCRIPT), "--base-url", "http://127.0.0.1:9", "--seat", "P2",
             "--tokens-file", str(missing), "--days", "1"],
            env={**env, **extra}, capture_output=True, text=True, timeout=120,
        )
        assert got.returncode == 2, got.stderr
        assert "refusing to start" in got.stderr
        assert "tokens file" not in got.stderr


def test_switch_on_two_days_no_refused_posts(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "tw2002")
    monkeypatch.setattr(K, "PORT_STOCK_FIDELITY_MODE", "live")
    monkeypatch.setattr(K, "HAGGLE_LIVE_MODE", "live")
    assert K.ai_cockpit_seat_on() is True

    from tw2k.server.app import create_app

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
        await runner.start(seat_spec(2))
        assert await _wait_until(lambda: runner.state.universe is not None)
        try:
            return await seat.run_http(http, "P2", TOK2, 2, idle_s=120)
        finally:
            await runner.stop()
            await http.aclose()

    report = asyncio.run(_go())
    assert report["refused"] == []
    assert [row["day"] for row in report["days"]] == [1, 2]
    assert report["posts"] > 20
    assert report["kinds"].get("trade", 0) > 0
    assert set(report["kinds"]) <= set(seat.COCKPIT_KINDS)
    first, last = report["days"][0], report["days"][-1]
    assert last["credits_end"] > first["credits_start"]
    assert last["net_worth_end"] > first["net_worth_start"]
    assert seen
    for method, path in seen:
        assert ROUTE.match(path), path
        assert (method == "POST") == path.endswith("/action"), (method, path)
    gaps = {row["id"] for row in report["gaps"]}
    assert gaps <= set(seat.GAP_TEXT)
