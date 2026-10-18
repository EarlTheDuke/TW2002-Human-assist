"""COMMANDER NOTE 74: the day rolls on the clock while a seat holds its turn."""

from __future__ import annotations

import asyncio
import socket
import threading
import time
from pathlib import Path

import uvicorn

import tw2k.engine.constants as K
from tw2k.engine import GameConfig
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec


def _port() -> int:
    for port in range(42000, 42100):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("no free port in 42000-42099")


def test_a_held_turn_reaches_day_3_on_a_10_second_clock(tmp_path: Path, monkeypatch) -> None:
    """A seat that never moves still reaches day 3 in about 30 seconds."""
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    port = _port()
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    started = threading.Event()
    errors: list[BaseException] = []

    async def _main() -> None:
        async def kick() -> None:
            try:
                while not server.started:
                    await asyncio.sleep(0.05)
                match = asyncio.create_task(runner.start(MatchSpec(
                    config=GameConfig(
                        seed=74, universe_size=80, max_days=6, turns_per_day=250,
                        starting_credits=20_000, enable_ferrengi=False, enable_planets=True,
                        action_delay_s=0.0, turn_regen_day_seconds=10,
                    ),
                    agents=[AgentSpec(player_id="P1", name="Holder", kind="external", external_token="h" * 40)],
                    action_delay_s=0.0,
                    external_timeout_s=90.0,
                )))
                while runner.state.universe is None and not match.done():
                    await asyncio.sleep(0.05)
                started.set()
                await match
            except Exception as exc:
                errors.append(exc)
            finally:
                started.set()

        task = asyncio.create_task(kick())
        await server.serve()
        task.cancel()

    thread = threading.Thread(target=lambda: asyncio.run(_main()), daemon=True)
    thread.start()
    try:
        assert started.wait(30), "match did not start"
        if errors:
            raise errors[0]
        deadline = time.time() + 32
        day = 1
        while time.time() < deadline:
            universe = runner.state.universe
            day = int(universe.day) if universe is not None else 1
            if day >= 3:
                break
            time.sleep(0.5)
        assert day >= 3, day
        clock = runner.day_clock()
        assert clock is not None
        assert abs(clock["next_day_at"] - clock["day_started_at"] - 10) < 0.2
    finally:
        server.should_exit = True
        thread.join(timeout=15)
