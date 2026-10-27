"""A live game keeps the turn count it was given, and does not race the day.

An idle external seat is not skipped when the short idle wait is off.
A day that just ended waits for the hourly turn recovery instead of
rolling again on the next pass.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from tw2k.engine import GameConfig
from tw2k.engine import constants as K
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec

pytestmark = pytest.mark.legacy_profile


def test_requested_turns_are_kept_and_the_switches_can_stay_off(monkeypatch) -> None:
    monkeypatch.setattr(K, "STARTING_PACKAGE_MODE", "live")
    assert K.opening_loadout(20_000, 50, 0)[1] == 250
    monkeypatch.setattr(K, "LIVE_PACE_MODE", "live")
    assert K.opening_loadout(20_000, 50, 0)[1] == 50
    assert K.opening_loadout(20_000, 1000, 0)[1] == 250
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    monkeypatch.setattr(K, "SEAT_DEADLINE_MODE", "off")
    monkeypatch.setattr(K, "ASYNC_DAY_MODE", "off")
    assert K.seat_deadline_live() is False
    assert K.async_day_live() is False
    monkeypatch.setenv("TW2K_SEAT_DEADLINE_MODE", "live")
    assert K.seat_deadline_live() is True


def _spec(turns: int, kinds: list[str]) -> MatchSpec:
    cfg = GameConfig(
        seed=11,
        universe_size=40,
        max_days=30,
        turns_per_day=turns,
        starting_credits=20_000,
        enable_ferrengi=False,
        action_delay_s=0.0,
    )
    return MatchSpec(
        config=cfg,
        agents=[
            AgentSpec(player_id=f"P{i + 1}", name=f"S{i + 1}", kind=kind,
                      external_token=f"pace-token-p{i + 1}-000000000000")
            for i, kind in enumerate(kinds)
        ],
        action_delay_s=0.0,
        external_timeout_s=30.0,
        external_idle_wait_s=0.0,
    )


async def _until(pred, *, tries: int = 200, dt: float = 0.02) -> bool:
    for _ in range(tries):
        if pred():
            return True
        await asyncio.sleep(dt)
    return pred()


def test_a_spent_day_does_not_roll_again_immediately(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(K, "STARTING_PACKAGE_MODE", "live")
    monkeypatch.setattr(K, "LIVE_PACE_MODE", "live")
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")

    async def _go() -> None:
        await runner.start(_spec(12, ["heuristic", "heuristic"]))
        assert await _until(lambda: runner.state.universe is not None and runner.state.universe.day >= 2)
        await asyncio.sleep(1.0)
        assert runner.state.universe is not None
        assert runner.state.universe.day == 2
        await runner.stop()

    asyncio.run(_go())


def test_an_idle_external_seat_is_not_skipped(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(K, "STARTING_PACKAGE_MODE", "live")
    monkeypatch.setattr(K, "LIVE_PACE_MODE", "live")
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")

    async def _go() -> None:
        await runner.start(_spec(40, ["heuristic", "external"]))
        assert await _until(lambda: runner.state.universe is not None)

        def _busy() -> bool:
            u = runner.state.universe
            return u is not None and u.players["P1"].turns_today > 0

        assert await _until(_busy)
        await asyncio.sleep(0.3)
        u = runner.state.universe
        assert u is not None
        assert u.day == 1
        assert u.players["P2"].turns_today == 0
        assert u.players["P2"].turns_per_day == 40
        await runner.stop()

    asyncio.run(_go())
