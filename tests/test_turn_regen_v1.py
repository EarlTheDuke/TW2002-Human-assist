"""offline-turn-regen-v1. Off, a new day still refills the turns."""
import tw2k.engine.constants as K
from tests.test_ports_haggle_v1 import _seat
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.runner import apply_action, tick_day


def test_flag_stays_legacy() -> None:
    assert K.TURN_REGEN_MODE == "legacy"
    assert K.turn_regen_live() is False


def test_off_a_day_still_refills(monkeypatch) -> None:
    monkeypatch.setattr("time.time", lambda: 10_000.0)
    universe, player = _seat()
    player.turns_today = 40
    player.turn_regen_at = 0.0
    tick_day(universe)
    assert player.turns_today == 0


def test_on_an_hour_returns_about_ten_and_stops_at_the_cap(monkeypatch) -> None:
    monkeypatch.setattr(K, "TURN_REGEN_MODE", "live")
    monkeypatch.setattr("time.time", lambda: 4_600.0)
    universe, player = _seat()
    player.turns_per_day = 240
    player.turns_today = 100
    player.turn_regen_at = 1_000.0
    res = apply_action(universe, player.id, Action(kind=ActionKind.WAIT, args={}))
    assert res.ok
    assert player.turns_today == 91

    player.turns_today = 0
    player.turn_regen_at = 1_000.0
    apply_action(universe, player.id, Action(kind=ActionKind.WAIT, args={}))
    assert player.turns_today == 1


def test_on_a_new_day_does_not_refill(monkeypatch) -> None:
    monkeypatch.setattr(K, "TURN_REGEN_MODE", "live")
    universe, player = _seat()
    player.turns_today = 5
    tick_day(universe)
    assert player.turns_today == 5


def test_half_an_hour_at_fifty_thousand_is_not_194() -> None:
    assert int(1800 * 50_000 / K.TURN_REGEN_DAY_SECONDS) == 1041
