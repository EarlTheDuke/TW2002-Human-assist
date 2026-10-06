"""Planetary Trade Agreement (port menu <N>) - planetary-trading-v1, slice 54.

docs/playtests/planets/PLANETARY_TRADING.md rows pt1..pt26. A trader at a commodity port sells one commodity
of a same-sector own / own-corp planet's stockpile straight to that port in one action. The legal list
(`legal_spec`) and the handler (`handle_planet_trade`) share `port_reason`, `eligible_planets`, `max_qty`
and `lot_price`, so what is listed is what the handler accepts (pt / step 4).

Nothing here draws from universe.rng (pt22: the ship-sale path draws none either). Ship-trade prices and
haggling are untouched: economy.py is only read. Behind K.PLANET_TRADE_MODE ("legacy" = verb absent).
"""

from __future__ import annotations

from typing import Any

from . import constants as K
from .actions import Action, ActionResult
from .economy import _stored_mcic, begin_port_visit, haggle_bound, port_buy_price, trade_turn_cost
from .models import (
    TRADE_COMMODITIES,
    Commodity,
    EventKind,
    Planet,
    Player,
    Port,
    PortClass,
    PortStock,
    Universe,
)

# pt5 / fog step 5: a rival's planet and a missing id read exactly the same.
NO_PLANET = "no such planet in this sector you can trade from"
# pt12: a counter past the port's patience. apply_action charges the visit turn for this refusal.
NOT_INTERESTED = "We're not interested."
NO_AGREEMENT_PORT = "this port offers no planetary trade agreement (commodity ports, classes 1-8, only)"
LANDED = "lift off first: the agreement is negotiated with the port, not from the planet"
BUSTED = "you are busted at this port until it clears"
NOTHING_TO_SELL = "no planet of yours (or your corporation's) here holds a commodity this port is buying"


def on() -> bool:
    return K.planet_trade_on()


# ---- shared checks (legal list == handler) ---------------------------------------------------------------

def port_reason(universe: Universe, player: Player) -> str | None:
    """pt1-pt3, pt17: None when this trader may open the <N> menu here."""
    port = universe.sectors[player.sector_id].port
    if port is None:
        return "no trading port in this sector"
    if getattr(port, "construction", None):
        return "that port is under construction"
    if port.class_id in (PortClass.FEDERAL, PortClass.STARDOCK):  # pt2: no agreement at Class 0 / StarDock
        return NO_AGREEMENT_PORT
    if player.planet_landed is not None:  # pt3
        return LANDED
    if K.rob_tw2002() and getattr(port, "bust_player_id", None) == player.id:  # pt17 (same guard as trade)
        return BUSTED
    if K.port_upgrade_on():  # pu23: docks stay shut while the port is being built
        from .port_build import docks_closed
        if docks_closed(port):
            return "this port is under construction"
    return None


def _may_trade_from(universe: Universe, player: Player, planet: Planet) -> bool:
    """pt4 (+ pt20 cooldown): own planet, or (owner_or_corp) a planet of the trader's current corporation."""
    if int(planet.sector_id) != int(player.sector_id):
        return False
    cool = int(K.PLANET_TRADE_TWARP_COOLDOWN)
    if cool > 0 and planet.last_transwarp_day is not None and int(universe.day) - int(planet.last_transwarp_day) < cool:
        return False
    if planet.owner_id is not None and planet.owner_id == player.id:
        return True
    if K.PLANET_TRADE_WHO == "owner_or_corp":
        return bool(planet.corp_ticker and player.corp_ticker and planet.corp_ticker == player.corp_ticker)
    return False


def eligible_planets(universe: Universe, player: Player) -> list[Planet]:
    """pt4 / pt21: planets in the trader's sector he may negotiate for, by planet id."""
    sector = universe.sectors[player.sector_id]
    out = [universe.planets[pid] for pid in sector.planet_ids if pid in universe.planets]
    return sorted((pl for pl in out if _may_trade_from(universe, player, pl)), key=lambda pl: int(pl.id))


def port_room(port: Port, commodity: Commodity) -> int:
    """pt5 / pt7: "We are buying up to N" - exactly can_trade's sell capacity (maximum - current)."""
    if commodity not in TRADE_COMMODITIES or not port.buys(commodity):
        return 0
    s = port.stock.get(commodity)
    if s is None:
        return 0
    return max(0, int(s.maximum) - int(s.current))


def max_qty(port: Port, planet: Planet, commodity: Commodity) -> int:
    """pt6: offered max = min(port buying room, planet stockpile). Colonists are never offered (pt19)."""
    if commodity not in TRADE_COMMODITIES:
        return 0
    return max(0, min(port_room(port, commodity), int(planet.stockpile.get(commodity, 0) or 0)))


def _price_at(port: Port, commodity: Commodity, current: int, xp: int) -> int:
    """port_buy_price for the port's stock as it would stand at `current` (the port object is not touched)."""
    s = port.stock[commodity]
    stock = dict(port.stock)
    stock[commodity] = PortStock(current=int(current), maximum=int(s.maximum))
    return port_buy_price(port.model_copy(update={"stock": stock}), commodity, xp)


def lot_price(port: Port, commodity: Commodity, qty: int, xp: int, pricing: str | None = None) -> int:
    """pt10 lot price (SOURCE-CONFLICT, K.PLANET_TRADE_PRICING).

    "curve" (TWGS model, default): steps of K.PLANET_TRADE_CURVE_STEP units (last one partial), each at the
    port's buy price for its stock after the previous steps. "end": the whole lot at the post-sale price.
    "mbbs100": the whole lot at the opening unit bid (MBBS "100% Planetary Trading").
    """
    qty = int(qty)
    if qty <= 0:
        return 0
    mode = pricing or K.PLANET_TRADE_PRICING
    start = int(port.stock[commodity].current)
    if mode == "mbbs100":
        return int(port_buy_price(port, commodity, xp)) * qty
    if mode == "end":
        return int(_price_at(port, commodity, start + qty, xp)) * qty
    step = max(1, int(K.PLANET_TRADE_CURVE_STEP))
    total = 0
    done = 0
    while done < qty:
        n = min(step, qty - done)
        total += int(_price_at(port, commodity, start + done, xp)) * n
        done += n
    return int(total)


# ---- legal list ------------------------------------------------------------------------------------------

def _planet_entries(universe: Universe, player: Player, port: Port) -> list[dict[str, Any]]:
    xp = int(player.experience)
    rows: list[dict[str, Any]] = []
    for pl in eligible_planets(universe, player):
        sellable: dict[str, int] = {}
        quote: dict[str, int] = {}
        bid: dict[str, int] = {}
        for c in TRADE_COMMODITIES:
            mx = max_qty(port, pl, c)
            if mx <= 0:
                continue
            sellable[c.value] = mx
            quote[c.value] = lot_price(port, c, mx, xp)
            bid[c.value] = int(port_buy_price(port, c, xp))
        if sellable:
            rows.append({"planet_id": int(pl.id), "name": pl.name,
                         "owner": "self" if pl.owner_id == player.id else "corp",
                         "sellable": sellable, "quote": quote, "unit_bid": bid})
    return rows


def legal_spec(universe: Universe, pid: str) -> tuple[bool, str | None, int, dict[str, Any]]:
    """(legal, reason, turn_cost, params) for planet_trade. Planets are listed only when the verb is legal
    (fog: only the trader's own / own-corp planets ever appear)."""
    player = universe.players[pid]
    cost = trade_turn_cost(player)
    why = port_reason(universe, player)
    rows: list[dict[str, Any]] = []
    if why is None:
        rows = _planet_entries(universe, player, universe.sectors[player.sector_id].port)
        if not rows:
            why = NOTHING_TO_SELL
    if why is None and player.turns_per_day - player.turns_today < cost:
        why = f"out of turns ({player.turns_per_day - player.turns_today} left, needs {cost})"
    if why is not None:
        rows = []
    commodities = sorted({c for r in rows for c in r["sellable"]})
    params: dict[str, Any] = {
        "planet_id": {"type": "int", "required": True, "choices": [r["planet_id"] for r in rows]},
        "commodity": {"type": "str", "required": True, "choices": commodities},
        "qty": {"type": "int", "required": True, "min": 1,
                "max_by": {str(r["planet_id"]): dict(r["sellable"]) for r in rows}},
        "offer": {"type": "int", "required": False,
                  "note": "total credits; default = the quote; one counter, a greedy one is refused"},
        "planets": rows,
        "turn_cost": cost,
    }
    if why is None and getattr(player, "flee_penalty", False) and cost > 0:  # same rule as a ship trade
        extra = min(int(K.FLEE_PENALTY_TURNS), max(0, player.turns_per_day - player.turns_today - cost))
        params["flee_penalty_turns"] = extra
        cost += extra
    return why is None, why, cost, params


def available(universe: Universe, pid: str) -> bool:
    """Observation port block `planet_trade_available` (same answer as the legal list)."""
    if pid not in universe.players or not universe.players[pid].alive:
        return False
    return legal_spec(universe, pid)[0]


# ---- handler ---------------------------------------------------------------------------------------------

def _int(v: Any) -> int | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def handle_planet_trade(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    why = port_reason(universe, player)
    if why is not None:
        return ActionResult(ok=False, error=why)
    sector = universe.sectors[player.sector_id]
    port = sector.port
    args = action.args or {}
    planet_id = _int(args.get("planet_id"))
    planet = next((pl for pl in eligible_planets(universe, player) if planet_id is not None and int(pl.id) == planet_id),
                  None)
    if planet is None:  # pt4 / pt20 / fog: a rival planet, a planet elsewhere and a bad id are one answer
        return ActionResult(ok=False, error=NO_PLANET)
    raw_c = str(args.get("commodity") or "").lower()
    try:
        commodity = Commodity(raw_c)
    except ValueError:
        return ActionResult(ok=False, error=f"invalid commodity {args.get('commodity')!r}")
    if commodity not in TRADE_COMMODITIES:  # pt19
        return ActionResult(ok=False, error="only fuel_ore, organics or equipment can be sold to a port")
    room = port_room(port, commodity)
    if not port.buys(commodity):  # pt5
        return ActionResult(ok=False, error=f"this port is not buying {commodity.value}")
    have = int(planet.stockpile.get(commodity, 0) or 0)
    mx = max_qty(port, planet, commodity)
    qty = _int(args.get("qty")) if args.get("qty") is not None else mx  # PTW "How many units ... [3000]?"
    if qty is None:
        return ActionResult(ok=False, error="qty must be a whole number")
    if qty < 1:  # pt6: no turn
        return ActionResult(ok=False, error="quantity must be at least 1")
    if qty > room:
        return ActionResult(ok=False, error=f"We are buying up to {room} {commodity.value}.")
    if qty > have:
        return ActionResult(ok=False, error=f"You have {have} {commodity.value} on planet {planet.name}.")
    offer = _int(args.get("offer")) if args.get("offer") is not None else None
    if args.get("offer") is not None and (offer is None or offer < 1):
        return ActionResult(ok=False, error="offer must be a positive whole number of credits")
    cost = trade_turn_cost(player)  # pt9: part of the port visit
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns for this day")

    xp = int(player.experience)
    quote = lot_price(port, commodity, qty, xp)  # pt10 / pt11
    paid = quote
    countered = False
    if offer is not None and offer != quote:
        if offer > quote:  # pt12: one counter on the total
            if K.PLANET_TRADE_HAGGLE == "no_counter":
                bound = quote
            else:  # "as_ship_sell": HAGGLE.md's ship-sale bound on the lot
                bound = haggle_bound(quote, _stored_mcic(port, commodity), "sell")
            if offer > bound:
                universe.emit(
                    EventKind.TRADE_FAILED, actor_id=pid, sector_id=sector.id,
                    payload={"commodity": commodity.value, "qty": qty, "side": "sell", "reason": NOT_INTERESTED,
                             "planet_id": int(planet.id), "planet_trade": True},
                    summary=f"{player.name} planetary trade refused: {NOT_INTERESTED}",
                )
                _drop_tow(universe, player)
                return ActionResult(ok=False, error=NOT_INTERESTED, turns_spent=cost)
        paid = int(offer)  # a good counter is paid; an offer under the quote is the trader's loss
        countered = True

    unused_port = not port.experience
    # pt14: one stock update each side; pt13: credits to the payee
    planet.stockpile[commodity] = have - qty
    port.stock[commodity].current += qty
    port.credits = max(0, int(getattr(port, "credits", 0) or 0) - paid)
    if K.PLANET_TRADE_PAYEE == "planet":
        planet.treasury = int(planet.treasury) + paid
    else:
        player.credits += paid
    if K.PLANET_TRADE_EXP == "as_trade":  # pt15: experience as one ship sale of qty
        from .victory import _award_xp
        port.experience[player.id] = min(1.0, port.experience.get(player.id, 0.0) + 0.05)
        if paid > quote:
            bargain = (paid - quote + qty // 2) // qty  # per-unit bargain, as a ship counter is judged
            if bargain > 0:
                player.experience = int(player.experience) + min(K.PORT_HAGGLE_XP_CAP, bargain)
        if unused_port:
            _award_xp(universe, pid, "first_dock")
    from .runner import _record_port_intel
    _record_port_intel(player, sector.id, port, universe=universe)
    begin_port_visit(player)
    # pt24: who sold what here; never the planet's remaining stock
    universe.emit(
        EventKind.PLANET_TRADE, actor_id=pid, sector_id=sector.id,
        payload={"trader": pid, "planet_id": int(planet.id), "port_sector": int(sector.id),
                 "commodity": commodity.value, "qty": int(qty), "price": int(paid), "quote": int(quote),
                 "countered": countered},
        summary=(f"{player.name} sold {qty} {commodity.value} from planet {planet.name} to the port for "
                 f"{paid:,}cr (Planetary Trade Agreement)"),
    )
    if K.PLANET_TRADE_EXP == "as_trade":
        from .victory import _award_xp
        _award_xp(universe, pid, "trade")
    _drop_tow(universe, player)
    return ActionResult(ok=True, turns_spent=cost)


def _drop_tow(universe: Universe, player: Player) -> None:
    """SHIP_TOW.md tt11: dealing with a port drops a tow (tow.py's PORT_VERBS cannot list this verb: the slice
    may not edit tow.py, so it calls the public release here)."""
    if not K.tow_on() or getattr(player.ship, "tow_lock", None) is None:
        return
    from .tow import release
    release(universe, player.ship, player.id, "port")
