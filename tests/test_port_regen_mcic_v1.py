"""Port regen uses each port's own numbers. The switch stays off."""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine.economy import can_trade, regenerate_ports
from tw2k.engine.models import Commodity, GameConfig, Port, PortClass, PortStock, Sector, Universe

pytestmark = pytest.mark.legacy_profile


def _universe(productivity: int, maximum: int, current: int) -> Universe:
    port = Port(
        class_id=PortClass.CLASS_9_SSS,
        stock={
            Commodity.FUEL_ORE: PortStock(current=current, maximum=maximum),
        },
        productivity={Commodity.FUEL_ORE: productivity},
        mcic={Commodity.FUEL_ORE: 40},
    )
    return Universe(
        config=GameConfig(seed=1),
        sectors={1: Sector(id=1, port=port)},
    )


def test_legacy_regen_uses_productivity_not_max():
    _prior_port_regen_mode = K.PORT_REGEN_MODE
    try:
        try:
            K.PORT_REGEN_MODE = "legacy"
            universe = _universe(productivity=100, maximum=1000, current=0)
            regenerate_ports(universe)
            assert universe.sectors[1].port.stock[Commodity.FUEL_ORE].current == 5
        finally:
            K.PORT_REGEN_MODE = "legacy"
    finally:
        K.PORT_REGEN_MODE = _prior_port_regen_mode


def test_live_regen_is_five_percent_of_max():
    _prior_port_regen_mode = K.PORT_REGEN_MODE
    try:
        try:
            K.PORT_REGEN_MODE = "live"
            universe = _universe(productivity=100, maximum=1000, current=0)
            regenerate_ports(universe)
            assert universe.sectors[1].port.stock[Commodity.FUEL_ORE].current == 50
        finally:
            K.PORT_REGEN_MODE = "legacy"
    finally:
        K.PORT_REGEN_MODE = _prior_port_regen_mode


def test_live_visit_stops_at_the_max():
    _prior_port_regen_mode = K.PORT_REGEN_MODE
    try:
        try:
            K.PORT_REGEN_MODE = "live"
            port = _universe(100, 1000, 1000).sectors[1].port
            ok, msg = can_trade(port, Commodity.FUEL_ORE, 1001, "buy")
            assert ok is False
            assert "100%" in msg
        finally:
            K.PORT_REGEN_MODE = "legacy"
    finally:
        K.PORT_REGEN_MODE = _prior_port_regen_mode


def test_legacy_visit_keeps_the_stock_message():
    _prior_port_regen_mode = K.PORT_REGEN_MODE
    try:
        K.PORT_REGEN_MODE = "legacy"
        port = _universe(100, 1000, 1000).sectors[1].port
        ok, msg = can_trade(port, Commodity.FUEL_ORE, 1001, "buy")
        assert ok is False
        assert "enough stock" in msg
    finally:
        K.PORT_REGEN_MODE = _prior_port_regen_mode
