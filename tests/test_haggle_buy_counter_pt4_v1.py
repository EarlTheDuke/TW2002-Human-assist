"""Playtest 4: under v3.11 rounds, bidding the port's own BUY counter closes the deal.

Game 668cbeaf: bid 11 on a list of 13, port countered 12, bid 12 -> "lost patience" at
three ports. TWGS accepts its own counter; the sell side already did.
"""
import tw2k.engine.constants as K
from tests.test_haggle_rounds_p3_v1 import _buy_list
from tests.test_ports_haggle_v1 import _seat, _trade


def _counter_then(monkeypatch, step):
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    universe, player = _seat()
    player.ship.cargo.clear()
    listed = _buy_list(universe)
    low = _trade(universe, "buy", "fuel_ore", unit_price=(listed * 85) // 100)
    assert low.ok is False and str(low.error).startswith("counter "), low.error
    counter = int(str(low.error).split()[-1])
    assert counter <= listed
    return _trade(universe, "buy", "fuel_ore", unit_price=step(counter)), counter


def test_v311_buy_counter_is_accepted(monkeypatch) -> None:
    met, _ = _counter_then(monkeypatch, lambda c: c)
    assert met.ok, met.error


def test_v311_buy_under_counter_still_ends(monkeypatch) -> None:
    under, _ = _counter_then(monkeypatch, lambda c: c - 1)
    assert under.ok is False and under.error == "the port lost patience"
