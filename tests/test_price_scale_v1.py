"""NOTE 112 GAP 2.5. Chart quotes on, and the stored curve off."""

from __future__ import annotations

from tw2k.engine import constants as K
from tw2k.engine.economy import port_buy_price, port_sell_price
from tw2k.engine.models import Commodity, Port, PortClass, PortStock

EQ = Commodity.EQUIPMENT
FUEL = Commodity.FUEL_ORE
ORG = Commodity.ORGANICS


def _port(class_num: int, commodity: Commodity, current: int, mcic: int) -> Port:
    return Port(
        class_id=PortClass(class_num),
        stock={commodity: PortStock(current=current, maximum=2500)},
        mcic={commodity: mcic},
    )


def test_chart_units_are_the_nearest_credit_of_the_250_hold_total() -> None:
    assert K.price_scale_unit(3_675) == 15
    assert K.price_scale_unit(8_791) == 35
    assert K.price_scale_unit(6_964) == 28
    assert K.price_scale_unit(17_712) == 71
    assert K.price_scale_unit(12_190) == 49
    assert K.price_scale_unit(31_910) == 128


def test_legacy_keeps_the_calibrated_curve(monkeypatch) -> None:
    monkeypatch.setattr(K, "PRICE_SCALE_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    assert K.price_scale_live() is False
    assert port_sell_price(_port(1, EQ, 2500, 50), EQ) == 61
    assert port_buy_price(_port(3, EQ, 0, -50), EQ) == 140
    assert K.ship_cost("battleship") == 88_500


def test_live_quotes_the_chart_and_still_moves_with_the_slope(monkeypatch) -> None:
    monkeypatch.setattr(K, "PRICE_SCALE_MODE", "live")
    assert port_sell_price(_port(1, FUEL, 2500, 50), FUEL) == 15
    assert port_sell_price(_port(1, ORG, 2500, 50), ORG) == 28
    assert port_sell_price(_port(1, EQ, 2500, 50), EQ) == 49
    assert port_buy_price(_port(3, FUEL, 0, -50), FUEL) == 35
    assert port_buy_price(_port(3, ORG, 0, -50), ORG) == 71
    assert port_buy_price(_port(3, EQ, 0, -50), EQ) == 128
    # MCIC 1 on a full seller is the existing MCIC slope, measured from 49.
    assert port_sell_price(_port(1, EQ, 2500, 1), EQ) == 36
    # An empty seller is dearer than the full-port chart point.
    assert port_sell_price(_port(1, EQ, 0, 50), EQ) > 49
    assert K.ship_cost("battleship") == 88_500
    assert K.ship_cost("merchant_cruiser") == 41_300


def test_chart_wins_over_the_screen_anchors(monkeypatch) -> None:
    monkeypatch.setattr(K, "PRICE_SCALE_MODE", "live")
    monkeypatch.setattr(K, "PORT_PRICE_MODE", "live")
    assert port_sell_price(_port(1, EQ, 2500, 50), EQ) == 49
    monkeypatch.setattr(K, "PRICE_SCALE_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    assert port_sell_price(_port(1, EQ, 2500, 50), EQ) == 36


def test_v311_turns_the_helper_on_and_leaves_the_stored_flag(monkeypatch) -> None:
    monkeypatch.setattr(K, "PRICE_SCALE_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.price_scale_live() is True
    assert K.PRICE_SCALE_MODE == "legacy"
    assert port_sell_price(_port(1, EQ, 2500, 50), EQ) == 49
