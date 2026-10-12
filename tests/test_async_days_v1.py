"""async-days-v1. Seats share a day clock only when the switch is on."""
import asyncio

from tw2k.engine.models import GameConfig, Player
from tw2k.engine.universe import generate_universe
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.runner import MatchRunner, MatchSpec, collect_in_seat_order
import tw2k.engine.constants as K


def test_flag_stays_legacy() -> None:
    assert K.ASYNC_DAY_MODE == "legacy"
    assert K.async_day_live() is False
    assert K.ASYNC_DAY_CAP_S == 20 * 60
    assert K.async_day_should_roll(True, 99999) is False


def test_on_the_day_rolls_when_everyone_is_done_or_the_clock_hits(monkeypatch) -> None:
    monkeypatch.setattr(K, "ASYNC_DAY_MODE", "live")
    assert K.async_day_should_roll(True, 0) is True
    assert K.async_day_should_roll(False, K.ASYNC_DAY_CAP_S) is True
    assert K.async_day_should_roll(False, 1) is False


def test_answers_start_together_and_come_back_in_seat_order() -> None:
    started: list[str] = []

    async def first():
        started.append("a-start")
        await asyncio.sleep(0.05)
        started.append("a-end")
        return "a"

    async def second():
        started.append("b-start")
        return "b"

    result = asyncio.run(collect_in_seat_order([first(), second()]))
    assert result == ["a", "b"]
    assert started.index("b-start") < started.index("a-end")


def _runner(universe):
    runner = MatchRunner(Broadcaster())
    runner.state.universe = universe
    runner._spec = MatchSpec(
        config=universe.config,
        agents=[],
        action_delay_s=0.0,
        external_timeout_s=2.0,
    )
    return runner


def test_on_a_round_applies_both_seats_before_the_day_rolls(monkeypatch) -> None:
    monkeypatch.setattr(K, "ASYNC_DAY_MODE", "live")
    universe = generate_universe(GameConfig(seed=7, universe_size=20, max_days=3, enable_ferrengi=False))
    asked: list[str] = []

    class Seat:
        def __init__(self, pid: str) -> None:
            self.player_id = pid
            self.name = pid

        async def act(self, obs):
            asked.append(self.player_id)
            from tw2k.engine import Action, ActionKind
            return Action(kind=ActionKind.WAIT, thought="ok")

    for pid in ("P1", "P2"):
        player = Player(id=pid, name=pid, sector_id=1)
        universe.players[pid] = player
        universe.sectors[1].occupant_ids.append(pid)
    day = universe.day
    runner = _runner(universe)

    async def _go():
        await runner._async_day_round([Seat("P1"), Seat("P2")], universe)

    asyncio.run(_go())
    assert asked == ["P1", "P2"]
    assert universe.day == day
