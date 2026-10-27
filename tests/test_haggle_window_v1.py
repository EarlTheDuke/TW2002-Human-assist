"""The live haggle band is about +8% on a sell and -8% on a buy.

A TWGS v3.34b session took first bids in that band and ended a sell past
about 130%. This copy's chart pays 110% to 149% and scales with MCIC.
Counter rounds between the band and the wild bid were not built. A failed
haggle still costs one turn.

HAGGLE_WINDOW_MODE defaults to legacy, so today's digests stay put.

Plants:
  pb1 — live room still follows the 110 to 149 chart.
  pb2 — a live offer past the band still trades, at the band edge.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.economy import haggle_bound, haggle_room_pct, port_buy_price, port_sell_price
from tw2k.engine.models import Commodity, GameConfig, Player, Port, PortClass, PortStock, Ship
from tw2k.engine.runner import apply_action
from tw2k.engine.universe import generate_universe

pytestmark = pytest.mark.legacy_profile

FUEL = Commodity.FUEL_ORE
EQ = Commodity.EQUIPMENT


def _seat() -> tuple:
    universe = generate_universe(
        GameConfig(seed=4, universe_size=20, max_days=5, enable_planets=False, enable_ferrengi=False)
    )
    player = Player(id="P1", name="Trader", ship=Ship(), credits=500_000, experience=0)
    player.sector_id = 11
    player.ship.cargo[FUEL] = 20
    universe.players["P1"] = player
    universe.sectors[11].occupant_ids.append("P1")
    return universe, player


def _port(universe, class_id: PortClass, commodity: Commodity, mcic: int, current: int) -> Port:
    port = Port(
        class_id=class_id,
        stock={commodity: PortStock(current=current, maximum=3000)},
        mcic={commodity: mcic},
    )
    universe.sectors[11].port = port
    return port


def _trade(universe, side: str, commodity: str, unit_price: int):
    return apply_action(
        universe,
        "P1",
        Action(
            kind=ActionKind.TRADE,
            args={"side": side, "commodity": commodity, "qty": 1, "unit_price": unit_price},
        ),
    )


def test_default_keeps_the_old_chart_and_the_failed_turn():
    assert K.HAGGLE_WINDOW_MODE == "legacy"
    assert K.PORT_HAGGLE_FAIL_TURNS == 1
    assert haggle_room_pct(0) == K.PORT_HAGGLE_MIN_PCT
    assert haggle_room_pct(-100) == K.PORT_HAGGLE_MAX_PCT


def test_live_band_is_flat_and_a_wild_sell_still_costs_a_turn():
    _prior_haggle_window_mode = K.HAGGLE_WINDOW_MODE
    try:
        try:
            K.HAGGLE_WINDOW_MODE = "live"
            assert haggle_room_pct(0) == K.PORT_HAGGLE_LIVE_ROOM_PCT
            assert haggle_room_pct(-800) == K.PORT_HAGGLE_LIVE_ROOM_PCT

            universe, player = _seat()
            port = _port(universe, PortClass.CLASS_1_BSS, FUEL, -100, 0)
            listed = port_buy_price(port, FUEL, 0)
            ask = round(listed * 104 / 100)
            assert ask <= haggle_bound(listed, -100, "sell")
            won = _trade(universe, "sell", "fuel_ore", ask)
            assert won.ok, won.error
            assert player.credits == 500_000 + ask

            universe, player = _seat()
            port = _port(universe, PortClass.CLASS_1_BSS, FUEL, -100, 0)
            listed = port_buy_price(port, FUEL, 0)
            wild = round(listed * 137 / 100)
            assert wild <= round(listed * K.PORT_HAGGLE_MAX_PCT / 100)
            credits = player.credits
            held = player.ship.cargo[FUEL]
            lost = _trade(universe, "sell", "fuel_ore", wild)
            assert lost.ok is False
            assert lost.error == "the port lost patience"
            assert player.credits == credits
            assert player.ship.cargo[FUEL] == held
            assert player.turns_today == K.PORT_HAGGLE_FAIL_TURNS

            universe, player = _seat()
            player.ship.cargo[FUEL] = 0
            port = _port(universe, PortClass.CLASS_5_SBS, EQ, 100, 3000)
            listed = port_sell_price(port, EQ, 0)
            bid = round(listed * 95 / 100)
            assert bid >= haggle_bound(listed, 100, "buy")
            bought = _trade(universe, "buy", "equipment", bid)
            assert bought.ok, bought.error
            assert player.credits == 500_000 - bid
        finally:
            K.HAGGLE_WINDOW_MODE = "legacy"
    finally:
        K.HAGGLE_WINDOW_MODE = _prior_haggle_window_mode
