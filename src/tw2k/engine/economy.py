"""Port pricing, trade execution, and haggling."""

from __future__ import annotations

import random

from . import constants as K
from .models import Commodity, Player, Port, PortClass, Universe


def _stock_fraction(port: Port, commodity: Commodity) -> float:
    s = port.stock.get(commodity)
    if not s or s.maximum == 0:
        return 0.0
    return max(0.0, min(1.0, s.current / s.maximum))


def port_sell_price(port: Port, commodity: Commodity) -> int:
    """Price when the PORT sells this commodity TO the player."""
    base = K.COMMODITY_BASE_PRICE[commodity.value]
    if port.class_id == PortClass.FEDERAL:
        return base  # fixed, no discount
    # Well stocked port sells at near base, empty port discounts because it can't move product
    frac = _stock_fraction(port, commodity)
    mult = 0.90 + 0.20 * frac
    return max(1, round(base * mult))


def port_buy_price(port: Port, commodity: Commodity) -> int:
    """Price when the PORT buys this commodity FROM the player."""
    base = K.COMMODITY_BASE_PRICE[commodity.value]
    if port.class_id == PortClass.FEDERAL:
        return base
    # Empty port (low stock of what it buys? Actually port stock of a BUYS commodity =
    # how much it has already purchased; we treat low stock as high demand -> pays more.)
    frac = _stock_fraction(port, commodity)
    mult = 1.20 - 0.30 * frac
    return max(1, round(base * mult))


def can_trade(port: Port, commodity: Commodity, qty: int, side: str) -> tuple[bool, str]:
    """side = 'buy' means player is buying from port; 'sell' means player is selling to port."""
    if side == "buy":
        if not port.sells(commodity):
            return False, f"Port does not sell {commodity.value}"
        s = port.stock.get(commodity)
        if s is None or s.current < qty:
            return False, "Port does not have enough stock"
        return True, ""
    elif side == "sell":
        if not port.buys(commodity):
            return False, f"Port does not buy {commodity.value}"
        s = port.stock.get(commodity)
        if s is None:
            return False, "Port has no capacity for this commodity"
        # Capacity to buy more from player = maximum - current (how much more it can stockpile)
        capacity = s.maximum - s.current
        if capacity < qty:
            return False, "Port already full for this commodity"
        return True, ""
    return False, f"Unknown side {side!r}"


def execute_trade(
    universe: Universe,
    player: Player,
    port: Port,
    commodity: Commodity,
    qty: int,
    side: str,
    offered_unit_price: int | None,
    rng: random.Random,
) -> tuple[bool, int, int, str]:
    """Run a haggle + settle.

    Returns (success, total_price, per_unit_price, message).
    Does not modify state if unsuccessful.
    """
    if qty <= 0:
        return False, 0, 0, "Quantity must be positive"

    ok, err = can_trade(port, commodity, qty, side)
    if not ok:
        return False, 0, 0, err

    listed = port_sell_price(port, commodity) if side == "buy" else port_buy_price(port, commodity)
    offered = offered_unit_price if offered_unit_price is not None else listed

    # Haggle success probability: closer to fair => higher chance.
    # For the player: "buying" wants offered <= listed; "selling" wants offered >= listed.
    # Classic TW2002 behaviour: a rejected haggle DOESN'T forfeit the trade — the
    # port counter-offers at list price and the player still gets the deal. This
    # prevents agents from learning "never haggle" and keeps the feed clean of
    # thrashing red events while still rewarding accurate haggling with a better
    # unit price.
    haggled = False
    if side == "buy":
        diff_ratio = (listed - offered) / max(1, listed)  # positive if player bids low
        if diff_ratio <= 0:
            accepted = True
            final_unit = listed
        else:
            success_prob = max(0.0, 1.0 - 4.0 * diff_ratio)
            accepted = rng.random() < success_prob
            final_unit = offered if accepted else listed
            haggled = True
    else:  # sell
        diff_ratio = (offered - listed) / max(1, listed)  # positive if player asks high
        if diff_ratio <= 0:
            accepted = True
            final_unit = listed
        else:
            success_prob = max(0.0, 1.0 - 4.0 * diff_ratio)
            accepted = rng.random() < success_prob
            final_unit = offered if accepted else listed
            haggled = True

    total = final_unit * qty

    # Apply state changes
    if side == "buy":
        if player.credits < total:
            return False, 0, 0, f"Insufficient credits ({player.credits} < {total})"
        if player.ship.cargo_free < qty:
            return False, 0, 0, f"Not enough free holds ({player.ship.cargo_free} < {qty})"
        player.credits -= total
        player.ship.cargo[commodity] = player.ship.cargo.get(commodity, 0) + qty
        port.stock[commodity].current -= qty
    else:  # sell
        have = player.ship.cargo.get(commodity, 0)
        if have < qty:
            return False, 0, 0, f"Not enough cargo ({have} < {qty})"
        player.credits += total
        player.ship.cargo[commodity] = have - qty
        port.stock[commodity].current += qty

    # Build experience
    port.experience[player.id] = min(1.0, port.experience.get(player.id, 0.0) + 0.05)

    if haggled and not accepted:
        msg = f"haggle countered; settled at list {listed}cr"
    elif haggled and accepted:
        msg = f"haggle won at {final_unit}cr (list {listed})"
    else:
        msg = "ok"
    return True, total, final_unit, msg


def regenerate_ports(universe: Universe) -> None:
    """Called on day tick. Move each port's stock toward its max by regen %."""
    for sector in universe.sectors.values():
        port = sector.port
        if port is None:
            continue
        for _commodity, stock in port.stock.items():
            if port.buys(_commodity):
                # Buying ports "consume" their purchases (representing onward sale).
                # They drift back toward a moderate level.
                target = int(stock.maximum * 0.3)
                delta = int((target - stock.current) * K.PORT_REGEN_PER_DAY * 2)
                stock.current = max(0, min(stock.maximum, stock.current + delta))
            else:
                # Selling ports regenerate stock toward max.
                delta = int((stock.maximum - stock.current) * K.PORT_REGEN_PER_DAY * 2)
                stock.current = min(stock.maximum, stock.current + delta)
