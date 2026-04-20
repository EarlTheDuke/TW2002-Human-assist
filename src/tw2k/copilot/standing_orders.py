"""Standing orders — user-defined guardrails that gate copilot actions.

A standing order is a *predicate* the human sets once ("never go below
5000 credits", "never warp into a sector containing ferrengi", "haggle
ceiling 15%"). Before every copilot-dispatched action, we evaluate
every active order. Any that reject the action cause it to be blocked
with a structured reason the chat panel renders back to the human.

Engine stays pure: orders live on `CopilotSession`, not `Universe`.
Blocking happens before `HumanAgent.submit_action` is called, so the
scheduler never sees the rejected call.

Currently supports three rule kinds — enough for H2's exit criteria
and the advisory guardrails §10 describes. New kinds can be added
without breaking the JSON shape by extending the `StandingOrderKind`
enum + `evaluate` dispatch.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..engine import ActionKind, Universe
from .tools import ToolCall


class StandingOrderKind(str, Enum):
    MIN_CREDIT_RESERVE = "min_credit_reserve"   # block spending if creds would drop below
    NO_WARP_TO_SECTORS = "no_warp_to_sectors"   # block warp/plot_course into forbidden list
    MAX_HAGGLE_DELTA_PCT = "max_haggle_delta_pct"  # block trade if counter-offer exceeds ±N% of port price


class StandingOrder(BaseModel):
    id: str
    kind: StandingOrderKind
    params: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    active: bool = True

    def summary(self) -> str:
        if self.description:
            return self.description
        if self.kind == StandingOrderKind.MIN_CREDIT_RESERVE:
            return f"Keep at least {self.params.get('credits', 0)} credits in the bank."
        if self.kind == StandingOrderKind.NO_WARP_TO_SECTORS:
            s = self.params.get("sectors", [])
            return f"Never warp into sectors: {', '.join(map(str, s))}"
        if self.kind == StandingOrderKind.MAX_HAGGLE_DELTA_PCT:
            return f"Haggle within ±{self.params.get('pct', 0)}% of port's quoted price."
        return f"{self.kind.value}({self.params})"


class OrderEvaluation(BaseModel):
    """Outcome of running every active order against a single tool call."""

    allowed: bool
    blocked_by: list[str] = Field(default_factory=list)  # order ids
    reasons: list[str] = Field(default_factory=list)     # human-readable


def evaluate(
    orders: list[StandingOrder],
    universe: Universe,
    player_id: str,
    call: ToolCall,
) -> OrderEvaluation:
    """Check `call` against every active `orders` entry.

    Non-action calls (planning/dialog/orchestration) always pass —
    orders only constrain side-effectful engine actions.
    """
    spec = call.spec()
    if spec is None or spec.group != "action":
        return OrderEvaluation(allowed=True)

    blocked_by: list[str] = []
    reasons: list[str] = []

    for order in orders:
        if not order.active:
            continue
        reason = _check_one(order, universe, player_id, call)
        if reason is not None:
            blocked_by.append(order.id)
            reasons.append(f"{order.id}: {reason}")

    return OrderEvaluation(
        allowed=not blocked_by, blocked_by=blocked_by, reasons=reasons
    )


def _check_one(
    order: StandingOrder,
    universe: Universe,
    player_id: str,
    call: ToolCall,
) -> str | None:
    """Return None to allow, str reason to block."""
    player = universe.players.get(player_id)
    if player is None:
        return None  # unknown player — let engine reject

    if order.kind == StandingOrderKind.MIN_CREDIT_RESERVE:
        reserve = int(order.params.get("credits", 0))
        # Buying could eat into our reserve. We can't perfectly predict the
        # final bill without touching the port's haggle RNG, so we use the
        # conservative "qty × offered_price (or player's credits snapshot)".
        if call.name == "buy":
            qty = int(call.arguments.get("qty", 0))
            unit = call.arguments.get("unit_price")
            # Fall back to the port's ask if the copilot didn't pick a price.
            if unit is None:
                port = _port_in_sector(universe, player.sector_id)
                if port is not None:
                    c = call.arguments.get("commodity")
                    unit = int(port.prices.get(c, 0)) if c else 0
            unit = int(unit or 0)
            projected = player.credits - unit * qty
            if projected < reserve:
                return (
                    f"would drop credits to {projected:,} (< reserve "
                    f"{reserve:,})"
                )
        if call.name == "buy_equip":
            # Generic equipment upgrades — block anything if we're already at
            # or near reserve. This is a soft guard; engine will reject if
            # we truly can't pay.
            if player.credits <= reserve:
                return (
                    f"already at/below reserve {reserve:,}, blocking equipment"
                    f" upgrades until sold goods"
                )
        return None

    if order.kind == StandingOrderKind.NO_WARP_TO_SECTORS:
        forbidden = {int(s) for s in order.params.get("sectors", [])}
        if call.name in ("warp", "plot_course"):
            tgt = call.arguments.get("target")
            if tgt is not None and int(tgt) in forbidden:
                return f"sector {tgt} is on the no-fly list"
        return None

    if order.kind == StandingOrderKind.MAX_HAGGLE_DELTA_PCT:
        pct = float(order.params.get("pct", 0))
        if call.name not in ("buy", "sell"):
            return None
        offered = call.arguments.get("unit_price")
        if offered is None:
            return None  # accepting port price, can't breach the order
        port = _port_in_sector(universe, player.sector_id)
        if port is None:
            return None
        c = call.arguments.get("commodity")
        if c is None:
            return None
        base = float(port.prices.get(c, 0) or 0)
        if base <= 0:
            return None
        delta_pct = abs(float(offered) - base) / base * 100.0
        if delta_pct > pct:
            return (
                f"counter-offer {int(offered)} is "
                f"{delta_pct:.1f}% off port price {int(base)} (> cap {pct}%)"
            )
        return None

    return None


def _port_in_sector(universe: Universe, sector_id: int):  # type: ignore[no-untyped-def]
    sec = universe.sectors.get(sector_id)
    return sec.port if sec is not None else None


__all__ = [
    "OrderEvaluation",
    "StandingOrder",
    "StandingOrderKind",
    "evaluate",
]


# Avoid "ActionKind imported but unused" — the enum import keeps this module
# self-documenting (orders apply at the ActionKind level even though we
# currently gate by tool name).
_ = ActionKind
