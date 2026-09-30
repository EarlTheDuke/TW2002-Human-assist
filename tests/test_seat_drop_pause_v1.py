"""Opt-in pause when an external seat stops polling. Off by default."""

from __future__ import annotations

import asyncio
from pathlib import Path

from tw2k.engine import GameConfig
from tw2k.server.runner import AgentSpec, MatchSpec

TOK2 = "seat-drop-token-p2-000000000000"
TOK3 = "seat-drop-token-p3-000000000000"
WINDOW = 0.45


def _spec(*seats: tuple[str, str], pause: bool) -> MatchSpec:
    cfg = GameConfig(
        seed=42,
        universe_size=60,
        max_days=2,
        turns_per_day=12,
        starting_credits=25_000,
        enable_ferrengi=False,
        enable_planets=False,
        action_delay_s=0.0,
    )
    agents = [AgentSpec(player_id="P1", name="HBot", kind="heuristic")]
    for pid, tok in seats:
        agents.append(AgentSpec(player_id=pid, name=pid, kind="external", external_token=tok))
    return MatchSpec(
        config=cfg,
        agents=agents,
        action_delay_s=0.0,
        external_timeout_s=30.0,
        pause_on_seat_drop=pause,
        seat_drop_after_s=WINDOW,
    )


async def _wait_until(pred, *, tries: int = 60, dt: float = 0.05) -> bool:
    for _ in range(tries):
        if pred():
            return True
        await asyncio.sleep(dt)
    return pred()


def _client(tmp_path: Path):
    import httpx

    from tw2k.server.app import create_app

    app = create_app(auto_start=False)
    app.state.runner._saves_root = tmp_path / "saves"
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 5555))
    client = httpx.AsyncClient(transport=transport, base_url="http://harness.test")
    return app, client


def _auth(tok: str) -> dict[str, str]:
    return {"authorization": f"Bearer {tok}"}


def _drops(runner) -> list[str]:
    universe = runner.state.universe
    assert universe is not None
    return [e.summary for e in universe.events if "disconnected - match paused" in e.summary]


def test_flag_off_does_not_pause_when_a_seat_stops_polling(tmp_path: Path) -> None:
    app, client = _client(tmp_path)
    runner = app.state.runner

    async def _go() -> None:
        await runner.start(_spec(("P2", TOK2), pause=False))
        assert runner._drop_task is None
        assert await _wait_until(lambda: runner.state.status == "running")
        status = await client.get("/harness/v1/P2/status", headers=_auth(TOK2))
        assert status.status_code == 200
        await asyncio.sleep(WINDOW * 3)
        assert runner.state.status == "running"
        assert _drops(runner) == []
        await runner.stop()
        await client.aclose()

    asyncio.run(_go())


def test_one_seat_pauses_once_and_a_manual_pause_stays(tmp_path: Path) -> None:
    app, client = _client(tmp_path)
    runner = app.state.runner

    async def _go() -> None:
        await runner.start(_spec(("P2", TOK2), pause=True))
        assert await _wait_until(lambda: runner.state.status == "running")
        status = await client.get("/harness/v1/P2/status", headers=_auth(TOK2))
        assert status.status_code == 200
        assert runner.state.status == "running"
        assert await _wait_until(lambda: runner.state.status == "paused")
        assert _drops(runner) == ["seat P2 disconnected - match paused"]
        await asyncio.sleep(WINDOW)
        assert _drops(runner) == ["seat P2 disconnected - match paused"]
        assert runner.state.status == "paused"

        obs = await client.get("/harness/v1/P2/observation?peek=1", headers=_auth(TOK2))
        assert obs.status_code == 200
        assert await _wait_until(lambda: runner.state.status == "running")

        paused = await client.post("/control/pause")
        assert paused.status_code == 200 and runner.state.status == "paused"
        again = await client.get("/harness/v1/P2/status", headers=_auth(TOK2))
        assert again.status_code == 200
        await asyncio.sleep(0.15)
        assert runner.state.status == "paused"
        await runner.stop()
        await client.aclose()

    asyncio.run(_go())


def test_two_seats_resume_only_when_both_are_back(tmp_path: Path) -> None:
    app, client = _client(tmp_path)
    runner = app.state.runner

    async def _go() -> None:
        await runner.start(_spec(("P2", TOK2), ("P3", TOK3), pause=True))
        assert await _wait_until(lambda: runner.state.status == "running")
        assert (await client.get("/harness/v1/P2/status", headers=_auth(TOK2))).status_code == 200
        assert (await client.get("/harness/v1/P3/status", headers=_auth(TOK3))).status_code == 200
        assert await _wait_until(lambda: runner.state.status == "paused")
        assert sorted(_drops(runner)) == [
            "seat P2 disconnected - match paused",
            "seat P3 disconnected - match paused",
        ]
        await asyncio.sleep(WINDOW)
        assert len(_drops(runner)) == 2
        assert (await client.get("/harness/v1/P2/status", headers=_auth(TOK2))).status_code == 200
        await asyncio.sleep(0.15)
        assert runner.state.status == "paused"
        assert (await client.get("/harness/v1/P3/observation?peek=1", headers=_auth(TOK3))).status_code == 200
        assert await _wait_until(lambda: runner.state.status == "running")
        await runner.stop()
        await client.aclose()

    asyncio.run(_go())
