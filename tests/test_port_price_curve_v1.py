"""port-price-curve-v1. Live quotes use the screen's full-port anchors."""

from __future__ import annotations

from tw2k.engine import constants as K
from tw2k.engine.economy import port_buy_price, port_sell_price
from tw2k.engine.models import Commodity, Port, PortClass, PortStock


def _port(current: int, class_id: PortClass, maximum: int = 1000) -> Port:
    stock = {
        commodity: PortStock(current=current, maximum=maximum)
        for commodity in (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT)
    }
    return Port(class_id=class_id, stock=stock)


def test_default_keeps_todays_curve() -> None:
    assert K.PORT_PRICE_MODE == "legacy"
    full = _port(1000, PortClass.CLASS_9_SSS)
    assert port_sell_price(full, Commodity.EQUIPMENT) != 36
    buyer = _port(1000, PortClass.CLASS_7_BBB)
    assert port_buy_price(buyer, Commodity.FUEL_ORE) != 38


def test_live_full_port_hits_the_screen_anchors() -> None:
    _prior_port_price_mode = K.PORT_PRICE_MODE
    try:
        prior = K.PORT_PRICE_MODE
        try:
            K.PORT_PRICE_MODE = "live"
            seller = _port(1000, PortClass.CLASS_9_SSS)
            buyer = _port(1000, PortClass.CLASS_7_BBB)
            empty_seller = _port(0, PortClass.CLASS_9_SSS)
            empty_buyer = _port(0, PortClass.CLASS_7_BBB)
            assert port_sell_price(seller, Commodity.FUEL_ORE) == 16
            assert port_sell_price(seller, Commodity.ORGANICS) == 35
            assert port_sell_price(seller, Commodity.EQUIPMENT) == 36
            assert port_buy_price(buyer, Commodity.FUEL_ORE) == 38
            assert port_buy_price(buyer, Commodity.ORGANICS) == 73
            assert port_buy_price(buyer, Commodity.EQUIPMENT) == 102
            assert port_sell_price(empty_seller, Commodity.FUEL_ORE) > 16
            assert port_buy_price(empty_buyer, Commodity.EQUIPMENT) > 102
            cheap = port_sell_price(seller, Commodity.EQUIPMENT, experience=1000)
            capped = port_sell_price(seller, Commodity.EQUIPMENT, experience=2000)
            assert cheap < 36
            assert capped == cheap
            federal = Port(class_id=PortClass.FEDERAL, stock=seller.stock)
            assert port_sell_price(federal, Commodity.FUEL_ORE) == K.COMMODITY_BASE_PRICE["fuel_ore"]
        finally:
            K.PORT_PRICE_MODE = prior
    finally:
        K.PORT_PRICE_MODE = _prior_port_price_mode
