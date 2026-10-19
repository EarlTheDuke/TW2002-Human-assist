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


def _stored_mcic(port: Port, commodity: Commodity) -> int:
    stored = port.mcic.get(commodity)
    if stored is not None:
        return int(stored)
    if port.buys(commodity):
        return K.PORT_MCIC_DEFAULT_BUY
    return K.PORT_MCIC_DEFAULT_SELL


def _experience_span(experience: int) -> float:
    if experience <= 0:
        return 0.0
    return min(1.0, experience / K.PORT_PRICE_EXPERIENCE_CAP)


def _unit_price(base: int, raw: float) -> int:
    cap = base * K.PORT_UNIT_PRICE_MAX_MULT
    price = round(raw)
    if price < 1:
        return 1
    if price > cap:
        return cap
    return price


def port_sell_price(port: Port, commodity: Commodity, experience: int = 0) -> int:
    """Price when the PORT sells this commodity TO the player.

    Full stock is cheaper, empty stock is dearer (0.60x to 1.25x base).
    A higher MCIC charges more. Experience up to the cap makes it cheaper.
    A federal port stays at the base price.
    """
    base = K.COMMODITY_BASE_PRICE[commodity.value]
    if port.class_id == PortClass.FEDERAL:
        return base
    frac = _stock_fraction(port, commodity)
    stock_mult = 1.25 - 0.65 * frac
    mcic_mult = max(
        0.05,
        1.0 + (_stored_mcic(port, commodity) - K.PORT_MCIC_DEFAULT_SELL) * K.PORT_MCIC_POINT,
    )
    exp_mult = 1.0 - K.PORT_EXPERIENCE_BUY_DISCOUNT * _experience_span(experience)
    if K.price_scale_live():
        # Chart point: a full selling port at MCIC 50. The slope is the same
        # stock, MCIC, and experience curve, measured from that point.
        anchor = K.price_scale_unit(K.PRICE_SCALE_SELL_250[commodity.value])
        chart_stock = 1.25 - 0.65 * 1.0
        chart_mcic = max(
            0.05,
            1.0 + (K.PRICE_SCALE_SELL_MCIC - K.PORT_MCIC_DEFAULT_SELL) * K.PORT_MCIC_POINT,
        )
        raw = anchor * (stock_mult / chart_stock) * (mcic_mult / chart_mcic) * exp_mult
        return _unit_price(anchor, raw)
    if K.port_price_live():
        anchor = K.PORT_PRICE_LIVE_SELL_FULL[commodity.value]
        raw = anchor * (stock_mult / K.PORT_PRICE_SELL_FULL_MULT) * mcic_mult * exp_mult
        return _unit_price(anchor, raw)
    return _unit_price(base, base * stock_mult * mcic_mult * exp_mult)


def port_buy_price(port: Port, commodity: Commodity, experience: int = 0) -> int:
    """Price when the PORT buys this commodity FROM the player.

    Low stock pays more, a full port pays less (0.75x to 1.45x base).
    A more negative MCIC pays more. Experience up to the cap pays more.
    A federal port stays at the base price. With the buy-price anchor on, a
    hungry port pays the live anchor and the quote eases as it fills.
    """
    base = K.COMMODITY_BASE_PRICE[commodity.value]
    if port.class_id == PortClass.FEDERAL:
        return base
    frac = _stock_fraction(port, commodity)
    stock_mult = 1.45 - 0.70 * frac
    mcic_mult = max(
        0.05,
        1.0 + (K.PORT_MCIC_DEFAULT_BUY - _stored_mcic(port, commodity)) * K.PORT_MCIC_POINT,
    )
    exp_mult = 1.0 + K.PORT_EXPERIENCE_SELL_BONUS * _experience_span(experience)
    if K.price_scale_live():
        # Chart point: an empty buying port at MCIC -50. economy2 calls that
        # 100 percent, because a buying port with nothing left is ready to buy.
        anchor = K.price_scale_unit(K.PRICE_SCALE_BUY_250[commodity.value])
        chart_stock = 1.45 - 0.70 * 0.0
        chart_mcic = max(
            0.05,
            1.0 + (K.PORT_MCIC_DEFAULT_BUY - K.PRICE_SCALE_BUY_MCIC) * K.PORT_MCIC_POINT,
        )
        raw = anchor * (stock_mult / chart_stock) * (mcic_mult / chart_mcic) * exp_mult
        return _unit_price(anchor, raw)
    if K.port_price_live():
        anchor = K.PORT_PRICE_LIVE_BUY_FULL[commodity.value]
        if K.port_buy_price_anchor_on():
            # Remaining demand is 1 when the port is hungry (current 0). That
            # point pays the anchor. Filling the hold eases the quote.
            ease = 1.0 - K.PORT_BUY_FILL_EASE * frac
            raw = anchor * ease * mcic_mult * exp_mult
        else:
            raw = anchor * (stock_mult / K.PORT_PRICE_BUY_FULL_MULT) * mcic_mult * exp_mult
        return _unit_price(anchor, raw)
    return _unit_price(base, base * stock_mult * mcic_mult * exp_mult)


def haggle_room_pct(mcic: int) -> float:
    """Percent of the first offer a counter may reach. Hidden. See HAGGLE.md."""
    if K.haggle_window_live():
        return float(K.PORT_HAGGLE_LIVE_ROOM_PCT)
    span = min(K.PORT_HAGGLE_MCIC_SPAN, max(0, abs(int(mcic))))
    extra = K.PORT_HAGGLE_MAX_PCT - K.PORT_HAGGLE_MIN_PCT
    return K.PORT_HAGGLE_MIN_PCT + extra * span / K.PORT_HAGGLE_MCIC_SPAN


def haggle_experience(bargain: int, span: int) -> int:
    """Experience for one accepted counter that beat the list price.

    Legacy is the credit gap, stopped at PORT_HAGGLE_XP_CAP.
    Live (NOTE 87, HAGGLE_EXP_MODE) is +1 for a good haggle and +2 for a
    great one. UNVERIFIED, searched: HardwareMenu.html lines 240-241 (better
    deal, more points, no amounts), S2_cabal_formulas.html (no split),
    S7_softdocs_slice-10.txt ("haggle for 2 points"), and Eugene Hung's
    player tips (exact best price pays 5, not adopted). A great haggle is
    an accepted price at least as far from the list as the hidden bound.
    A smaller improvement is a good haggle.
    """
    gap = int(bargain)
    if gap <= 0:
        return 0
    if not K.haggle_exp_live():
        return min(int(K.PORT_HAGGLE_XP_CAP), gap)
    if int(span) > 0 and gap >= int(span):
        return int(K.HAGGLE_EXP_GREAT)
    return int(K.HAGGLE_EXP_GOOD)


def haggle_bound(listed: int, mcic: int, side: str) -> int:
    """Farthest counter the port will take, in credits.

    Sell side: the highest price the player may ask.
    Buy side: the lowest price the player may bid.
    """
    pct = haggle_room_pct(mcic)
    if side == "sell":
        return max(listed, round(listed * pct / 100.0))
    floor = round(listed * (200.0 - pct) / 100.0)
    return min(listed, max(1, floor))


def _live_haggle(player: Player, commodity: Commodity, side: str, listed: int, offered: int) -> tuple[str, int | str]:
    """Measured bands from REPORT2. Returns accept+price, or counter/end+message."""
    pending = player.haggle_counter if isinstance(player.haggle_counter, dict) else None
    base = listed
    if (
        pending is not None
        and pending.get("sector_id") == player.sector_id
        and pending.get("commodity") == commodity.value
        and pending.get("side") == side
    ):
        counter = int(pending["counter"])
        base = int(pending["listed"])
        if side == "sell" and offered <= counter:
            player.haggle_counter = None
            return "accept", offered
        if side == "sell" and offered * 100 <= base * 112:
            player.haggle_counter = None
            return "accept", offered
        if side == "buy" and offered >= counter:
            player.haggle_counter = None
            return "accept", offered
        listed = base
    if side == "sell":
        if offered * 100 <= listed * 103:
            player.haggle_counter = None
            return "accept", offered
        if offered * 100 <= listed * 112:
            counter = (listed * 101 + 50) // 100
            if counter <= listed:
                counter = listed + 1
            player.haggle_counter = {
                "sector_id": player.sector_id,
                "commodity": commodity.value,
                "side": side,
                "listed": listed,
                "counter": counter,
            }
            return "counter", f"counter {counter}"
        player.haggle_counter = None
        if offered * 100 >= listed * 137:
            return "end", "Get lost creep"
        return "end", "Swine, go peddle your wares"
    if offered * 100 >= listed * 88:
        player.haggle_counter = None
        return "accept", offered
    if offered * 100 >= listed * 77:
        counter = min(listed, (listed * 96 + 50) // 100)
        player.haggle_counter = {
            "sector_id": player.sector_id,
            "commodity": commodity.value,
            "side": side,
            "listed": listed,
            "counter": counter,
        }
        return "counter", f"counter {counter}"
    player.haggle_counter = None
    return "end", "the port lost patience"


def trade_turn_cost(player: Player) -> int:
    """Turns a successful trade spends right now.

    The first trade of a visit costs the dock turn. Further trades in that
    sector cost none. The visit ends when the player leaves the sector.
    legacy and live both use that rule, so the pin stays put.
    """
    if player.port_visit_sector_id == player.sector_id and K.trade_visit_free():
        return 0
    return K.PORT_DOCK_TURN_COST


def begin_port_visit(player: Player) -> None:
    player.port_visit_sector_id = player.sector_id


def can_trade(port: Port, commodity: Commodity, qty: int, side: str) -> tuple[bool, str]:
    """side = 'buy' means player is buying from port; 'sell' means player is selling to port."""
    if side == "buy":
        if not port.sells(commodity):
            return False, f"Port does not sell {commodity.value}"
        s = port.stock.get(commodity)
        if s is not None and (K.port_regen_live() or K.port_stock_fidelity_live()) and qty > int(s.maximum):
            return False, "a visit can move at most 100% of this port's max"
        if s is None or s.current < qty:
            return False, "Port does not have enough stock"
        return True, ""
    elif side == "sell":
        if not port.buys(commodity):
            return False, f"Port does not buy {commodity.value}"
        s = port.stock.get(commodity)
        if s is None:
            return False, "Port has no capacity for this commodity"
        if (K.port_regen_live() or K.port_stock_fidelity_live()) and qty > int(s.maximum):
            return False, "a visit can move at most 100% of this port's max"
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
) -> tuple[bool, int, int, str, int | None]:
    """Run a haggle + settle.

    Returns (success, total_price, per_unit_price, message, realized_profit).
    `realized_profit` is None for buys (you haven't realized anything yet,
    just shifted cost basis) and is (unit - basis_avg_at_sale) * qty for
    sells, rounded to int. It CAN be negative if the agent dumped cargo
    below its cost — that's a valuable signal we want in the trade_log.
    Does not modify state if unsuccessful.
    """
    if qty <= 0:
        return False, 0, 0, "Quantity must be positive", None

    # NOTE 71. Holds and cargo on board are checked before credits and before
    # the port's "100% of this port's max" cap, so a too-big order says what
    # the ship can carry.
    if K.haggle_counter_live():
        if side == "buy" and int(player.ship.cargo_free) < qty:
            free = int(player.ship.cargo_free)
            return False, 0, 0, f"You only have {free} empty holds.", None
        if side == "sell":
            have = int(player.ship.cargo.get(commodity, 0) or 0)
            if have < qty:
                label = {
                    Commodity.FUEL_ORE: "Fuel Ore",
                    Commodity.ORGANICS: "Organics",
                    Commodity.EQUIPMENT: "Equipment",
                }.get(commodity, str(getattr(commodity, "value", commodity)))
                return False, 0, 0, f"You only have {have} {label} in your holds.", None

    ok, err = can_trade(port, commodity, qty, side)
    if not ok:
        return False, 0, 0, err, None

    xp = int(player.experience)
    listed = (
        port_sell_price(port, commodity, xp) if side == "buy" else port_buy_price(port, commodity, xp)
    )
    offered = offered_unit_price if offered_unit_price is not None else listed
    # The roll is gone. A counter past the hidden limit does not trade.
    # rng stays in the signature so existing callers do not change.
    del rng

    if K.haggle_live():
        kind, value = _live_haggle(player, commodity, side, listed, offered)
        if kind != "accept":
            return False, 0, 0, str(value), None
        final_unit = int(value)
        haggled = final_unit != listed
    else:
        # No counter, or a price that is not better for the player than the
        # first offer, trades at that offer.
        better = (side == "buy" and offered < listed) or (side == "sell" and offered > listed)
        if not better:
            final_unit = listed
            haggled = False
        else:
            bound = haggle_bound(listed, _stored_mcic(port, commodity), side)
            within = offered >= bound if side == "buy" else offered <= bound
            # A sell past the live wild-bid line ends the trade even if a later
            # edit widens the accept band. Buy-side instant-end percent was not
            # measured, so a low buy fails only by missing the band above.
            wild = (
                K.haggle_window_live()
                and side == "sell"
                and listed > 0
                and offered * 100 > listed * K.PORT_HAGGLE_LIVE_END_PCT
            )
            if not within or wild:
                return False, 0, 0, "the port lost patience", None
            final_unit = offered
            haggled = True

    total = final_unit * qty
    realized_profit: int | None = None

    # Apply state changes
    if side == "buy":
        if player.credits < total:
            return False, 0, 0, f"Insufficient credits ({player.credits} < {total})", None
        if player.ship.cargo_free < qty:
            return False, 0, 0, f"Not enough free holds ({player.ship.cargo_free} < {qty})", None
        player.credits -= total
        port.credits = int(getattr(port, "credits", 0) or 0) + total
        # Weighted-average cost basis update: (old_qty*old_avg + buy_qty*unit) / new_qty.
        # This is the standard inventory-accounting approach — it means buying
        # the same commodity at two different ports blends the basis so the
        # agent's "profit at next sell" reflects the full round trip, not just
        # the final leg. Uses the post-haggle unit price (what we actually paid).
        old_qty = player.ship.cargo.get(commodity, 0)
        old_avg = player.ship.cargo_cost.get(commodity, 0.0) if old_qty > 0 else 0.0
        new_qty = old_qty + qty
        new_avg = ((old_qty * old_avg) + (qty * final_unit)) / new_qty if new_qty > 0 else 0.0
        player.ship.cargo[commodity] = new_qty
        player.ship.cargo_cost[commodity] = new_avg
        port.stock[commodity].current -= qty
    else:  # sell
        have = player.ship.cargo.get(commodity, 0)
        if have < qty:
            return False, 0, 0, f"Not enough cargo ({have} < {qty})", None
        basis_avg = player.ship.cargo_cost.get(commodity, 0.0)
        realized_profit = round((final_unit - basis_avg) * qty)
        player.credits += total
        port.credits = max(0, int(getattr(port, "credits", 0) or 0) - total)
        remaining = have - qty
        player.ship.cargo[commodity] = remaining
        # If the last holds of this commodity are sold out, clear the basis so
        # future buys start fresh instead of blending into stale average.
        if remaining <= 0:
            player.ship.cargo_cost[commodity] = 0.0
        port.stock[commodity].current += qty

    # Build experience
    port.experience[player.id] = min(1.0, port.experience.get(player.id, 0.0) + 0.05)

    if haggled:
        bargain = abs(final_unit - listed)
        if bargain:
            bound = haggle_bound(listed, _stored_mcic(port, commodity), side)
            span = abs(int(bound) - int(listed))
            player.experience = int(player.experience) + haggle_experience(bargain, span)
        msg = f"haggle won at {final_unit}cr (list {listed})"
    else:
        msg = "ok"
    return True, total, final_unit, msg, realized_profit


def regenerate_ports(universe: Universe) -> None:
    """Add each commodity's daily productivity, scaled by the regen setting."""
    for sector in universe.sectors.values():
        port = sector.port
        if port is None or getattr(port, "construction", None):
            continue
        for commodity, stock in port.stock.items():
            prod = int(port.productivity.get(commodity, 0) or 0)
            if K.port_stock_fidelity_live() and port.buys(commodity):
                give_back = round(int(stock.maximum) * K.PORT_REGEN_PER_DAY)
                stock.current = max(0, int(stock.current) - give_back)
                continue
            if K.port_regen_live() or K.port_open_full() or K.port_stock_fidelity_live():
                gain = round(int(stock.maximum) * K.PORT_REGEN_PER_DAY)
            else:
                gain = round(prod * K.PORT_REGEN_PER_DAY)
            stock.current = max(0, min(stock.maximum, stock.current + gain))
