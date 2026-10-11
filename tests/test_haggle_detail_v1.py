"""haggle-detail-v1. Off, the older window stays. On, the measured bands apply."""
import tw2k.engine.constants as K
from tests.test_ports_haggle_v1 import _port, _seat, _trade
from tw2k.engine.economy import port_buy_price, port_sell_price
from tw2k.engine.models import Commodity, PortClass

FUEL = Commodity.FUEL_ORE


def _listed_sell(universe) -> int:
    port = _port(universe, PortClass.CLASS_1_BSS, FUEL, -100, 0)
    return port_buy_price(port, FUEL, 0)


def _listed_buy(universe) -> int:
    port = _port(universe, PortClass.CLASS_4_SSB, FUEL, 50, 100)
    return port_sell_price(port, FUEL, 0)


def test_flag_stays_legacy() -> None:
    assert K.HAGGLE_LIVE_MODE == "legacy"
    assert K.haggle_live() is False


def test_off_a_high_sale_does_not_say_swine() -> None:
    universe, _player = _seat()
    listed = _listed_sell(universe)
    lost = _trade(universe, "sell", "fuel_ore", unit_price=listed * 2)
    assert lost.ok is False
    assert lost.error == "the port lost patience"


def test_on_sale_bands(monkeypatch) -> None:
    monkeypatch.setattr(K, "HAGGLE_LIVE_MODE", "live")
    universe, player = _seat()
    listed = _listed_sell(universe)
    taken = _trade(universe, "sell", "fuel_ore", unit_price=(listed * 103) // 100)
    assert taken.ok, taken.error
    assert player.port_visit_sector_id == 11

    universe, player = _seat()
    listed = _listed_sell(universe)
    asked = _trade(universe, "sell", "fuel_ore", unit_price=(listed * 112) // 100)
    assert asked.ok is False and str(asked.error).startswith("counter ")
    counter = int(str(asked.error).split()[-1])
    assert counter > listed
    met = _trade(universe, "sell", "fuel_ore", unit_price=counter - 1)
    assert met.ok, met.error

    universe, player = _seat()
    listed = _listed_sell(universe)
    _trade(universe, "sell", "fuel_ore", unit_price=(listed * 112) // 100)
    again = _trade(universe, "sell", "fuel_ore", unit_price=(listed * 104) // 100)
    assert again.ok, again.error

    universe, _player = _seat()
    listed = _listed_sell(universe)
    swine = _trade(universe, "sell", "fuel_ore", unit_price=(listed * 117) // 100)
    assert swine.ok is False and swine.error == "Swine, go peddle your wares"
    rude = _trade(universe, "sell", "fuel_ore", unit_price=_reaches(listed, 137))
    assert rude.ok is False and rude.error == "Get lost creep"


def test_on_a_refused_sale_makes_the_next_trade_cost_a_turn(monkeypatch) -> None:
    monkeypatch.setattr(K, "HAGGLE_LIVE_MODE", "live")
    universe, player = _seat()
    listed = _listed_sell(universe)
    first = _trade(universe, "sell", "fuel_ore", unit_price=listed)
    assert first.ok and first.turns_spent == 1 and player.port_visit_sector_id == 11
    swine = _trade(universe, "sell", "fuel_ore", unit_price=(listed * 117) // 100)
    assert swine.turns_spent == 1 and player.port_visit_sector_id is None
    player.ship.cargo[FUEL] = 20
    again = _trade(universe, "sell", "fuel_ore", unit_price=listed)
    assert again.ok and again.turns_spent == 1


def _reaches(listed: int, pct: int) -> int:
    px = (listed * pct) // 100
    while px * 100 < listed * pct:
        px += 1
    return px


def test_on_buy_bands(monkeypatch) -> None:
    monkeypatch.setattr(K, "HAGGLE_LIVE_MODE", "live")
    universe, player = _seat()
    listed = _listed_buy(universe)
    player.ship.cargo[FUEL] = 0
    taken = _trade(universe, "buy", "fuel_ore", unit_price=_reaches(listed, 88))
    assert taken.ok, taken.error

    universe, player = _seat()
    listed = _listed_buy(universe)
    player.ship.cargo[FUEL] = 0
    asked = _trade(universe, "buy", "fuel_ore", unit_price=_reaches(listed, 88) - 1)
    assert asked.ok is False and str(asked.error).startswith("counter ")
    low = _trade(universe, "buy", "fuel_ore", unit_price=_reaches(listed, 77) - 1)
    assert low.ok is False and low.error == "the port lost patience"
