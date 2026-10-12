"""seat-deadline-autopass-v1. The clock changes only when the switch is on."""
from tw2k.engine.models import GameConfig, Player
from tw2k.engine.runner import tick_day
from tw2k.engine.universe import generate_universe
import tw2k.engine.constants as K


def test_flag_stays_legacy() -> None:
    assert K.SEAT_DEADLINE_MODE == "legacy"
    assert K.seat_deadline_live() is False
    assert K.SEAT_DEADLINE_S == 75
    assert K.SEAT_DEADLINE_STREAK == 3


def test_off_a_new_day_does_not_touch_the_count() -> None:
    universe = generate_universe(GameConfig(seed=7, universe_size=20, max_days=3, enable_ferrengi=False))
    player = Player(id="P1", name="Tester")
    player.seat_timeout_streak = 2
    player.seat_timeouts_today = 4
    universe.players["P1"] = player
    tick_day(universe)
    assert player.seat_timeout_streak == 2
    assert player.seat_timeouts_today == 4
    fresh = Player(id="P2", name="Other")
    assert "seat_timeout_streak" not in fresh.model_dump()


def test_on_a_new_day_clears_the_count(monkeypatch) -> None:
    monkeypatch.setattr(K, "SEAT_DEADLINE_MODE", "live")
    universe = generate_universe(GameConfig(seed=7, universe_size=20, max_days=3, enable_ferrengi=False))
    player = Player(id="P1", name="Tester")
    player.seat_timeout_streak = 3
    player.seat_timeouts_today = 5
    universe.players["P1"] = player
    tick_day(universe)
    assert player.seat_timeout_streak == 0
    assert player.seat_timeouts_today == 0
