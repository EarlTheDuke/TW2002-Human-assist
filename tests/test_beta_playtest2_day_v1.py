"""COMMANDER NOTE 104. A legacy day with its own length rolls on the clock.

The stored switch stays legacy. With no day length the day stays put, so a
scripted match does not move. A held seat still sees the dawn countdown.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn

import tw2k.engine.constants as K
from tw2k.engine import GameConfig
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

TOKEN = "h" * 40
# Shortest day the clock accepts. 20s made the same check wait a minute.
DAY_S = 10.0


def _port() -> int:
    from tests._cu_host import free_port

    return free_port()


@contextlib.contextmanager
def _held_game(tmp_path: Path, monkeypatch, *, day_seconds: float | None, mode: str):
    """One external seat that never answers. The day length is the game's, or unset."""
    monkeypatch.setattr(K, "LEGACY_DAY_CLOCK_MODE", mode)
    saved_day = K.TURN_REGEN_DAY_SECONDS
    port = _port()
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    started = threading.Event()
    errors: list[BaseException] = []

    async def _main() -> None:
        match: asyncio.Task | None = None

        async def kick() -> None:
            nonlocal match
            try:
                while not server.started:
                    await asyncio.sleep(0.05)
                config = dict(
                    seed=104, universe_size=80, max_days=30, turns_per_day=250,
                    starting_credits=20_000, enable_ferrengi=False, enable_planets=False,
                    action_delay_s=0.0,
                )
                if day_seconds is not None:
                    config["turn_regen_day_seconds"] = day_seconds
                match = asyncio.create_task(runner.start(MatchSpec(
                    config=GameConfig(**config),
                    agents=[AgentSpec(player_id="P1", name="Holder", kind="external", external_token=TOKEN)],
                    action_delay_s=0.0,
                    external_timeout_s=180.0,
                )))
                while runner.state.universe is None and not match.done():
                    await asyncio.sleep(0.05)
                started.set()
                await match
            except Exception as exc:
                errors.append(exc)
            finally:
                started.set()
                if match is not None and not match.done():
                    match.cancel()
                    with contextlib.suppress(asyncio.CancelledError, Exception):
                        await match

        task = asyncio.create_task(kick())
        await server.serve()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    thread = threading.Thread(target=lambda: asyncio.run(_main()), daemon=True)
    thread.start()
    try:
        assert started.wait(30), "match did not start"
        if errors:
            raise errors[0]
        yield runner, port
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        K.TURN_REGEN_DAY_SECONDS = saved_day
        from tests._port_lock import release_ports

        release_ports(port)


def _clock(port: int) -> dict | None:
    res = httpx.get(
        f"http://127.0.0.1:{port}/harness/v1/P1/observation",
        params={"peek": 1, "wait_s": 0},
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=5,
    )
    assert res.status_code == 200, res.text[:300]
    return res.json().get("turn_clock")


def test_a_held_legacy_turn_rolls_three_days_and_refills(tmp_path: Path, monkeypatch) -> None:
    """A short day length still rolls three dawns and puts the turns back."""
    with _held_game(tmp_path, monkeypatch, day_seconds=DAY_S, mode="live") as (runner, port):
        deadline = time.time() + 15
        while time.time() < deadline and runner.state.universe is None:
            time.sleep(0.05)
        universe = runner.state.universe
        assert universe is not None
        universe.players["P1"].turns_today = 40
        seen: list[int] = []
        last = 1
        deadline = time.time() + DAY_S * 4 + 8
        while time.time() < deadline:
            day = int(runner.state.universe.day)
            if day > last:
                settle = time.time() + 0.25
                turns = int(runner.state.universe.players["P1"].turns_today)
                while turns != 0 and time.time() < settle:
                    time.sleep(0.02)
                    turns = int(runner.state.universe.players["P1"].turns_today)
                seen.append(turns)
                runner.state.universe.players["P1"].turns_today = 40
                last = day
            if day >= 4:
                break
            time.sleep(0.05)
        assert int(runner.state.universe.day) >= 4, runner.state.universe.day
        assert seen[:3] == [0, 0, 0], seen
        clock = runner.day_clock()
        assert clock is not None
        assert abs(clock["next_day_at"] - clock["day_started_at"] - DAY_S) < 0.5
        payload = _clock(port)
        assert payload is not None
        assert payload["day_seconds"] == DAY_S
        assert payload["day_started_at"] == pytest.approx(clock["day_started_at"])
        assert payload["next_day_at"] == pytest.approx(clock["next_day_at"])


def test_without_a_day_length_the_held_turn_does_not_roll(tmp_path: Path, monkeypatch) -> None:
    """The same game with no --day-seconds stays on day 1 and sends no turn clock."""
    with _held_game(tmp_path, monkeypatch, day_seconds=None, mode="live") as (runner, port):
        deadline = time.time() + 15
        while time.time() < deadline and runner.state.universe is None:
            time.sleep(0.05)
        assert runner.state.universe is not None
        settled = time.time() + 0.4
        while time.time() < settled:
            assert int(runner.state.universe.day) == 1
            time.sleep(0.05)
        assert int(runner.state.universe.day) == 1
        assert runner.day_clock() is None
        assert _clock(port) is None


def test_the_switch_off_does_not_roll_a_short_day(tmp_path: Path, monkeypatch) -> None:
    """Stored legacy ignores --day-seconds. One day length passes and the day stays 1."""
    assert K.LEGACY_DAY_CLOCK_MODE == "legacy"
    with _held_game(tmp_path, monkeypatch, day_seconds=DAY_S, mode="legacy") as (runner, port):
        deadline = time.time() + 15
        while time.time() < deadline and runner.state.universe is None:
            time.sleep(0.05)
        assert runner.state.universe is not None
        deadline = time.time() + DAY_S + 0.4
        while time.time() < deadline:
            assert int(runner.state.universe.day) == 1
            time.sleep(0.05)
        assert int(runner.state.universe.day) == 1
        assert runner.day_clock() is None
        assert _clock(port) is None
