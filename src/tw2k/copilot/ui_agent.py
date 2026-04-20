"""UIAgent — fast, rule-based annotations for the cockpit UI.

No LLM calls. Pure functions over `Observation`. H2 only needs button
tooltips + a suggested-next-move hint; richer UIAgent features
(structured "explain last decision" answers, etc.) can arrive later.
"""

from __future__ import annotations

from typing import Any

from ..engine import Observation


def summarize_status(obs: Observation) -> str:
    """One-line status string for the chat panel header."""
    s = obs.ship
    port_text = ""
    sec = obs.sector or {}
    port = sec.get("port") if isinstance(sec, dict) else None
    if port:
        port_text = f", port class {port.get('class_id')}"
    return (
        f"Day {obs.day} tick {obs.tick} — {obs.credits:,} cr, "
        f"hull {s.get('hull', 0)}/{s.get('max_hull', 0)}, "
        f"holds {_holds_used(s)}/{s.get('cargo_max', 0)}{port_text}"
    )


def _holds_used(ship: dict[str, Any]) -> int:
    cargo = ship.get("cargo", {}) or {}
    return sum(int(v) for v in cargo.values())


def button_hints(obs: Observation) -> dict[str, str]:
    """Return a mapping of action-kind → one-line hint.

    Shown as tooltips on the cockpit action buttons (Advisory mode).
    Empty string means "no annotation".
    """
    hints: dict[str, str] = {}

    sec = obs.sector or {}
    warps = sec.get("warps") or []
    port = sec.get("port")

    # Warp / plot_course
    if warps:
        hints["warp"] = f"Adjacent sectors: {', '.join(map(str, warps[:8]))}"
    else:
        hints["warp"] = "No visible warps — try scanning first."

    # Trade
    if port is not None:
        prices = port.get("prices") or {}
        bits = []
        for k in ("fuel_ore", "organics", "equipment"):
            p = prices.get(k)
            if p:
                bits.append(f"{k}={p}")
        hints["trade"] = "Port prices: " + ", ".join(bits) if bits else "Port here."
    else:
        hints["trade"] = "No trading port in this sector."

    # Scan is always useful
    hints["scan"] = "Reveals port class + commodities in current sector."

    # Pass turn
    hints["wait"] = "Skip this tick."

    # Suggested move
    suggest = suggest_next_move(obs)
    if suggest:
        hints["_suggest"] = suggest

    return hints


def suggest_next_move(obs: Observation) -> str:
    """Very small heuristic — a hint, not a decision.

    - If the current sector has a port and we have cargo worth selling
      there, suggest SELL.
    - Else if current sector has a port and we have credits and a
      commodity it's buying, suggest BUY.
    - Else if we can scan (haven't yet this sector), suggest SCAN.
    - Else suggest WARP to a known warp.
    """
    sec = obs.sector or {}
    port = sec.get("port")
    ship_cargo = obs.ship.get("cargo", {}) or {}

    if port is not None:
        # Sell side — if we have any of the port's buy commodities
        buying = port.get("buying") or []
        for c in buying:
            if int(ship_cargo.get(c, 0)) > 0:
                return f"Port here buys {c} — consider SELL {c}."
        # Buy side — if we have credits and the port is selling something
        selling = port.get("selling") or []
        if selling and obs.credits >= 1000:
            stock = port.get("stock") or {}
            best = None
            for c in selling:
                q = int(stock.get(c, 0))
                if q > 0:
                    best = c
                    break
            if best:
                return f"Port here sells {best} — consider BUY {best}."

    if sec.get("warps"):
        first = sec["warps"][0]
        return f"No local action — WARP {first} to keep moving."

    return "Consider SCAN to reveal neighbours."
