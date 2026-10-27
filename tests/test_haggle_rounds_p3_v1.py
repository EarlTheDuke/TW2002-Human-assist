"""Playtest 3. Under the v3.11 profile a +22% ask or a -23% bid is no longer taken in one shot.

Cabal haggling.html: the table percent is the most a port will consider "reasonable enough
to continue haggling"; past it the port says get lost and the turn is used. The measured
TWGS rounds (HAGGLE_LIVE_MODE) close the deal inside that line. Legacy is unchanged.
"""
import pytest

import tw2k.engine.constants as K
from tests.test_ports_haggle_v1 import _port, _seat, _trade
from tw2k.engine.economy import port_buy_price, port_sell_price
from tw2k.engine.models import Commodity, PortClass
from tw2k.public.manual import render

pytestmark = pytest.mark.legacy_profile

FUEL = Commodity.FUEL_ORE


def _sell_list(universe) -> int:
    return port_buy_price(_port(universe, PortClass.CLASS_1_BSS, FUEL, -100, 0), FUEL, 0)


def _buy_list(universe) -> int:
    return port_sell_price(_port(universe, PortClass.CLASS_4_SSB, FUEL, 50, 100), FUEL, 0)


def test_switch_is_legacy_and_v311_profile_turns_it_on(monkeypatch) -> None:
    assert K.HAGGLE_ROUNDS_MODE == "legacy"
    assert K.haggle_rounds_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.haggle_rounds_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.haggle_rounds_live() is True
    assert K.V311_PROFILE_HELPERS["haggle_rounds_live"][0] == "HAGGLE_ROUNDS_MODE"


def test_table_alone_still_takes_a_big_ask(monkeypatch) -> None:
    """The NOTE 150 table path without this switch: the playtest's +22% is accepted."""
    monkeypatch.setattr(K, "HAGGLE_TABLE_MODE", "v311")
    universe, _player = _seat()
    listed = _sell_list(universe)
    assert _trade(universe, "sell", "fuel_ore", unit_price=(listed * 122) // 100).ok


def test_v311_rounds_refuse_the_playtest_asks(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    universe, player = _seat()
    listed = _sell_list(universe)
    big = _trade(universe, "sell", "fuel_ore", unit_price=(listed * 122) // 100)
    assert big.ok is False
    assert big.turns_spent == 1, "a refused haggle wastes a turn (haggling.html)"

    universe, _player = _seat()
    listed = _sell_list(universe)
    small = _trade(universe, "sell", "fuel_ore", unit_price=(listed * 103) // 100)
    assert small.ok, small.error

    universe, _player = _seat()
    listed = _sell_list(universe)
    asked = _trade(universe, "sell", "fuel_ore", unit_price=(listed * 110) // 100)
    assert asked.ok is False and str(asked.error).startswith("counter ")
    counter = int(str(asked.error).split()[-1])
    assert listed < counter <= max(listed + 1, (listed * 102) // 100)
    pushed = _trade(universe, "sell", "fuel_ore", unit_price=(listed * 108) // 100)
    assert pushed.ok is False and pushed.error == "the port lost patience"

    universe, _player = _seat()
    listed = _sell_list(universe)
    _trade(universe, "sell", "fuel_ore", unit_price=(listed * 110) // 100)
    met = _trade(universe, "sell", "fuel_ore", unit_price=counter)
    assert met.ok, met.error


def test_v311_rounds_refuse_a_deep_bid(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    universe, _player = _seat()
    listed = _buy_list(universe)
    deep = _trade(universe, "buy", "fuel_ore", unit_price=(listed * 77) // 100)
    assert deep.ok is False


def test_manual_has_the_line(monkeypatch) -> None:
    assert "Haggle rounds: The v3.11 profile turns this on. In this process it is off." in render("Galaxy War Command")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert "Haggle rounds: The v3.11 profile turns this on. In this process it is on." in render("Galaxy War Command")
