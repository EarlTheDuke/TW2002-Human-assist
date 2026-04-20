"""What-if preview — cheap predicted outcomes for pending plans.

Given a list of ``ToolCall``s (a copilot-proposed plan), produce a
structured summary of what will happen if the human confirms it:
credit delta, turn cost, cargo flow, risk flags. **No engine fork** —
we just read the current ``Universe`` and apply per-tool heuristics.
Exact values depend on the engine's haggle RNG, so the preview is
labelled as an *estimate* everywhere.

Why this exists: in H2 the human gets a "plan preview" card listing
the tool names but nothing about cost. That makes Confirm a leap of
faith. The what-if preview turns that card into actual numbers the
human can veto against.

The preview is also exposed via ``GET /api/copilot/whatif?player_id=``
so the cockpit can poll it live.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..engine import Universe
from ..engine.economy import port_buy_price, port_sell_price
from ..engine.models import Commodity
from .tools import ToolCall


class StepPrediction(BaseModel):
    """What we expect to happen if this one step lands."""

    tool: str
    label: str  # one-line human-readable summary
    credit_delta: int = 0  # signed; + = we gain, - = we spend
    turn_cost: int = 0
    cargo_delta: dict[str, int] = Field(default_factory=dict)
    risk: str | None = None  # "warp_blocked" / "stock_out" / "haggle_variance" / ...
    note: str = ""  # optional freeform colour


class WhatIfSummary(BaseModel):
    """Aggregate prediction for a plan."""

    steps: list[StepPrediction] = Field(default_factory=list)
    credit_delta: int = 0
    turn_cost: int = 0
    cargo_delta: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    def one_liner(self) -> str:
        parts: list[str] = []
        if self.credit_delta > 0:
            parts.append(f"+{self.credit_delta:,} cr")
        elif self.credit_delta < 0:
            parts.append(f"{self.credit_delta:,} cr")
        if self.turn_cost:
            parts.append(f"-{self.turn_cost} turns")
        if self.cargo_delta:
            deltas = ", ".join(
                (f"+{v} {k}" if v >= 0 else f"{v} {k}")
                for k, v in sorted(self.cargo_delta.items())
                if v
            )
            if deltas:
                parts.append(deltas)
        if not parts:
            return "≈ no visible change"
        return " · ".join(parts)


# ---------------------------------------------------------------------------
# Preview builder
# ---------------------------------------------------------------------------


def _commodity_or_none(name: str | None) -> Commodity | None:
    if not name:
        return None
    try:
        return Commodity(name)
    except (ValueError, KeyError):
        return None


def preview_plan(
    universe: Universe, player_id: str, plan: list[ToolCall]
) -> WhatIfSummary:
    """Compute a WhatIfSummary over a plan without touching the engine state.

    Unknown/unhandled tools produce a neutral StepPrediction so the UI
    still sees them in the list.
    """
    summary = WhatIfSummary()
    player = universe.players.get(player_id)
    if player is None:
        summary.warnings.append(f"no player {player_id}")
        return summary

    # Track a shadow sector for step-by-step turn cost estimation, so
    # `plot_course A -> buy -> plot_course B` charges turns for both
    # hops and doesn't assume we've teleported.
    shadow_sector = player.sector_id
    for call in plan:
        step = _preview_one(
            universe, player, shadow_sector, call
        )
        summary.steps.append(step)
        summary.credit_delta += step.credit_delta
        summary.turn_cost += step.turn_cost
        for k, v in step.cargo_delta.items():
            summary.cargo_delta[k] = summary.cargo_delta.get(k, 0) + v
        if step.risk:
            summary.warnings.append(f"{call.name}: {step.risk}")

        # Advance shadow sector for warp/plot_course.
        if call.name == "warp" or call.name == "plot_course":
            tgt = call.arguments.get("target")
            if isinstance(tgt, int) and tgt in universe.sectors:
                shadow_sector = tgt

    return summary


def _preview_one(
    universe: Universe,
    player,
    shadow_sector: int,
    call: ToolCall,
) -> StepPrediction:
    name = call.name
    args = call.arguments

    if name == "warp":
        tgt = args.get("target")
        sec = universe.sectors.get(shadow_sector)
        warps = set(sec.warps) if sec else set()
        risk = None
        if not isinstance(tgt, int):
            risk = "missing target"
        elif tgt not in warps:
            risk = f"target {tgt} not in current warps"
        return StepPrediction(
            tool=name,
            label=f"warp to {tgt}",
            turn_cost=1,
            risk=risk,
        )

    if name == "plot_course":
        tgt = args.get("target")
        # Without running a real BFS here we stick to a cheap known-warps
        # lookup: if the target is directly adjacent in the shadow, it's
        # 1 turn; otherwise we flag it as "multi-hop (exact count at run
        # time)" so the UI shows uncertainty.
        sec = universe.sectors.get(shadow_sector)
        warps = set(sec.warps) if sec else set()
        if isinstance(tgt, int) and tgt in warps:
            return StepPrediction(
                tool=name, label=f"plot to {tgt} (1 hop)", turn_cost=1
            )
        return StepPrediction(
            tool=name,
            label=f"plot to {tgt}",
            turn_cost=2,  # conservative multi-hop estimate
            note="multi-hop estimate; exact cost computed at run time",
        )

    if name == "scan":
        return StepPrediction(tool=name, label="long-range scan", turn_cost=1)

    if name == "probe":
        tgt = args.get("target")
        return StepPrediction(
            tool=name,
            label=f"probe {tgt}",
            turn_cost=1,
            credit_delta=-1_000,  # probes cost ~1k base (heuristic)
            note="probe cost is an estimate; exact varies with class",
        )

    if name == "pass_turn":
        return StepPrediction(tool=name, label="pass turn", turn_cost=1)

    if name in ("buy", "sell"):
        commodity = _commodity_or_none(args.get("commodity"))
        qty = int(args.get("qty") or 0)
        sector = universe.sectors.get(shadow_sector)
        port = sector.port if sector else None
        if port is None or commodity is None or qty <= 0:
            return StepPrediction(
                tool=name,
                label=f"{name} {qty} {args.get('commodity') or '?'}",
                risk="no port / unknown commodity / zero qty",
            )
        if name == "buy":
            unit = args.get("unit_price")
            est_unit = int(unit) if isinstance(unit, int) else port_sell_price(
                port, commodity
            )
            if not port.sells(commodity):
                return StepPrediction(
                    tool=name,
                    label=f"buy {qty} {commodity.value}",
                    risk="port does not sell that commodity",
                )
            stock = port.stock.get(commodity)
            risk = None
            if stock is not None and stock.current < qty:
                risk = f"port has only {stock.current} in stock"
            total = est_unit * qty
            return StepPrediction(
                tool=name,
                label=f"buy {qty} {commodity.value} @ ~{est_unit}cr",
                credit_delta=-total,
                turn_cost=1,
                cargo_delta={commodity.value: qty},
                risk=risk,
                note="haggle variance ±10-15%",
            )
        if name == "sell":
            unit = args.get("unit_price")
            est_unit = int(unit) if isinstance(unit, int) else port_buy_price(
                port, commodity
            )
            if not port.buys(commodity):
                return StepPrediction(
                    tool=name,
                    label=f"sell {qty} {commodity.value}",
                    risk="port does not buy that commodity",
                )
            held = int(player.ship.cargo.get(commodity, 0))
            risk = None
            if held < qty:
                risk = f"only {held} on board"
            total = est_unit * qty
            return StepPrediction(
                tool=name,
                label=f"sell {qty} {commodity.value} @ ~{est_unit}cr",
                credit_delta=total,
                turn_cost=1,
                cargo_delta={commodity.value: -qty},
                risk=risk,
                note="haggle variance ±10-15%",
            )

    if name == "attack":
        return StepPrediction(
            tool=name,
            label=f"attack {args.get('target_id')}",
            turn_cost=1,
            risk="combat outcome uncertain",
        )

    if name == "deploy_fighters":
        qty = int(args.get("qty") or 0)
        return StepPrediction(
            tool=name,
            label=f"deploy {qty} fighters",
            turn_cost=1,
            note="reduces onboard fighter count",
        )

    if name == "land_planet":
        return StepPrediction(
            tool=name,
            label=f"land on planet {args.get('planet_id')}",
            turn_cost=1,
        )

    if name == "liftoff":
        return StepPrediction(tool=name, label="liftoff", turn_cost=1)

    # Planning/dialog/orchestration tools are zero-cost (no engine hit).
    return StepPrediction(
        tool=name,
        label=f"{name} (internal)",
        note="planning/dialog tool — no engine cost",
    )


__all__ = ["StepPrediction", "WhatIfSummary", "preview_plan"]
