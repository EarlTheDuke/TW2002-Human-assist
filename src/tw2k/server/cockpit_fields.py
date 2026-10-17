"""cockpit-gaps-v1 (NOTE 56). One cockpit block on the seat's own observation.

Only used when K.cockpit_fields_on(). Legacy observations carry no block,
and the runner records nothing extra. Each part closes one row of
docs/playtests/cockpit-ai-seat-v2/gaps.md and follows an original TW2002
screen (C:\\Users\\sugar\\tw2002_reference\\live_twgs\\transcript.txt):

* verdict: the outcome right after the command ("Docking... One turn
  deducted, 237 turns left." 2432-2433, "Agreed, 9 units." 2454, "Very
  well, we'll take that offer." 2470, "We're not interested." 9241).
* haggle: the port's quote and counter for the amount ("We'll sell them for
  317 credits." then 309, 306, 2456-2470). No accept band is shown, because
  the original never prints one.
* port_notes: this seat's own last-seen price per product at ports it has
  docked at, with the day. The original player keeps these in notes (S3
  bible around lines 3186-3188). Never a live price of another port.
* hold_quote: the StarDock hold price, how many you can afford, and the
  total for each amount ("550 credits / next hold 14" 4174, "The cost for
  10 more holds is 6,410 credits." 4186), from the engine's own hold rule.
"""

from __future__ import annotations

import time
from typing import Any

from tw2k.engine import constants as K

COMMODITIES = ("fuel_ore", "organics", "equipment")
ENDED = ("the port lost patience", "Swine, go peddle your wares", "Get lost creep")


def _port_here(universe: Any, player: Any) -> Any:
    sector = universe.sectors.get(player.sector_id) if universe is not None else None
    return getattr(sector, "port", None)


def _commodity(name: Any) -> Any:
    from tw2k.engine.models import Commodity

    try:
        return Commodity(str(name))
    except ValueError:
        return None


def _listed(port: Any, commodity: Any, side: str, xp: int) -> int:
    from tw2k.engine.economy import port_buy_price, port_sell_price

    if side == "buy":
        return int(port_sell_price(port, commodity, xp))
    return int(port_buy_price(port, commodity, xp))


def before_action(universe: Any, player: Any, action: Any) -> dict[str, Any]:
    """What the cockpit needs to explain the verdict, read before the action runs."""
    pre: dict[str, Any] = {
        "credits": int(player.credits),
        "turns_today": int(player.turns_today),
        "sector_id": int(player.sector_id),
    }
    kind = getattr(action.kind, "value", str(action.kind))
    if kind != "trade":
        return pre
    args = dict(action.args or {})
    port = _port_here(universe, player)
    commodity = _commodity(args.get("commodity"))
    side = str(args.get("side") or "").lower()
    try:
        qty = int(args.get("qty") or 0)
    except (TypeError, ValueError):
        qty = 0
    if port is None or commodity is None or side not in ("buy", "sell") or qty <= 0:
        return pre
    pending = player.haggle_counter if isinstance(player.haggle_counter, dict) else None
    if (pending and pending.get("sector_id") == player.sector_id
            and pending.get("commodity") == commodity.value and pending.get("side") == side):
        listed = int(pending.get("listed") or 0)
    else:
        try:
            listed = _listed(port, commodity, side, int(player.experience))
        except Exception:
            return pre
    offer = args.get("unit_price")
    try:
        offer = int(offer) if offer is not None else listed
    except (TypeError, ValueError):
        offer = listed
    pre["trade"] = {
        "commodity": commodity.value, "side": side, "qty": qty,
        "listed": listed, "quote": listed * qty, "offer": offer, "offer_total": offer * qty,
    }
    return pre


def _haggle(pre: dict[str, Any], player: Any, ok: bool, error: str | None, credits_change: int) -> dict[str, Any]:
    trade = dict(pre["trade"])
    if ok:
        trade["outcome"] = "taken"
        qty = max(1, int(trade["qty"]))
        trade["paid_total"] = abs(int(credits_change))
        trade["paid"] = abs(int(credits_change)) // qty
        return trade
    text = str(error or "")
    if text.startswith("counter "):
        try:
            counter = int(text.split()[1])
        except (IndexError, ValueError):
            counter = int(trade["listed"])
        trade["outcome"] = "countered"
        trade["counter"] = counter
        trade["counter_total"] = counter * int(trade["qty"])
        trade["next_offer"] = counter
        return trade
    trade["outcome"] = "ended" if text in ENDED else "refused"
    return trade


def after_action(agent: Any, universe: Any, player: Any, action: Any, result: Any, pre: dict[str, Any]) -> None:
    """Store the verdict on the seat and note the port it now sits at."""
    kind = getattr(action.kind, "value", str(action.kind))
    ok = bool(result.ok)
    credits_change = int(player.credits) - int(pre.get("credits", player.credits))
    same_day = int(player.turns_today) >= int(pre.get("turns_today", 0))
    verdict: dict[str, Any] = {
        "turn_seq": int(getattr(agent, "turn_seq", 0) or 0),
        "day": int(getattr(universe, "day", 0) or 0),
        "kind": kind,
        "args": dict(action.args or {}),
        "ok": ok,
        "outcome": "OK" if ok else "REFUSED",
        "reason": None if ok else (result.error or "refused"),
        "turns_spent": max(0, int(player.turns_today) - int(pre.get("turns_today", 0))) if same_day else None,
        "turns_left": max(0, int(player.turns_per_day) - int(player.turns_today)),
        "credits_change": credits_change,
        "credits": int(player.credits),
        "net_worth": _net_worth(universe, player),
        "sector_id": int(player.sector_id),
        "recorded_at": time.time(),
    }
    if "trade" in pre:
        verdict["haggle"] = _haggle(pre, player, ok, result.error, credits_change)
    agent.cockpit_verdict = verdict
    note_port(agent, universe, player)


def _net_worth(universe: Any, player: Any) -> int | None:
    from tw2k.engine.runner import full_net_worth

    try:
        return int(full_net_worth(universe, player))
    except Exception:
        return None


def note_port(agent: Any, universe: Any, player: Any) -> None:
    """Remember this seat's prices at the port it is docked at, with the day."""
    port = _port_here(universe, player)
    if port is None or not getattr(port, "stock", None):
        return
    notes = getattr(agent, "cockpit_port_notes", None)
    if notes is None:
        notes = {}
        agent.cockpit_port_notes = notes
    xp = int(player.experience)
    row: dict[str, Any] = {}
    for commodity in port.stock:
        if port.buys(commodity):
            side = "buys"
            price = _listed(port, commodity, "sell", xp)
        elif port.sells(commodity):
            side = "sells"
            price = _listed(port, commodity, "buy", xp)
        else:
            continue
        stock = port.stock[commodity]
        row[commodity.value] = {
            "price": int(price), "side": side, "day": int(universe.day),
            "pct_of_max": _pct(stock, side),
        }
    if row:
        notes[int(player.sector_id)] = row


def _pct(stock: Any, side: str) -> int:
    top = int(getattr(stock, "maximum", 0) or 0)
    if top <= 0:
        return 0
    current = int(getattr(stock, "current", 0) or 0)
    amount = top - current if side == "buys" else current
    return max(0, min(100, round(100 * amount / top)))


def _haggle_pending(player: Any) -> dict[str, Any] | None:
    pending = player.haggle_counter if isinstance(player.haggle_counter, dict) else None
    if not pending or pending.get("sector_id") != player.sector_id:
        return None
    counter = int(pending.get("counter") or 0)
    return {
        "commodity": pending.get("commodity"), "side": pending.get("side"),
        "listed": int(pending.get("listed") or 0), "counter": counter, "next_offer": counter,
    }


def hold_quote(universe: Any, player: Any) -> dict[str, Any] | None:
    """StarDock holds: next price, how many you can afford, and the total per amount."""
    from tw2k.engine.models import PortClass

    sector = universe.sectors.get(player.sector_id)
    port = getattr(sector, "port", None)
    if port is None or getattr(port, "class_id", None) != PortClass.STARDOCK:
        return None
    ship = player.ship
    class_key = getattr(ship.ship_class, "value", str(ship.ship_class))
    holds = int(ship.holds)
    spec = K.hull_spec(class_key) or {}
    cap = int(spec["max_holds"]) if "max_holds" in spec else 150
    room = max(0, cap - holds)
    day = int(universe.day)
    top = int(K.holds_affordable(class_key, holds, int(player.credits), day, room))
    totals = {str(q): int(K.hold_total_price(class_key, holds, q, day)) for q in range(1, top + 1)}
    return {
        "holds": holds, "max_holds": cap, "next_price": int(K.hold_next_price(class_key, holds, day)),
        "afford": top, "totals": totals,
    }


def cockpit_block(universe: Any, agent: Any) -> dict[str, Any]:
    player = universe.players.get(agent.player_id)
    if player is None:
        return {}
    note_port(agent, universe, player)
    notes = getattr(agent, "cockpit_port_notes", None) or {}
    return {
        "verdict": getattr(agent, "cockpit_verdict", None),
        "haggle": _haggle_pending(player),
        "port_notes": {str(sid): dict(row) for sid, row in sorted(notes.items())},
        "hold_quote": hold_quote(universe, player),
    }
