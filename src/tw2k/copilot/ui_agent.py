"""UIAgent — fast, rule-based annotations for the cockpit UI.

No LLM calls. Pure functions over `Observation`. H2 only needs button
tooltips + a suggested-next-move hint; richer UIAgent features
(structured "explain last decision" answers, etc.) can arrive later.
"""

from __future__ import annotations

from typing import Any

from ..engine import Observation


def _warps(sector: dict[str, Any]) -> list[int]:
    """Extract adjacent sector IDs from a sector dict.

    The engine's observation builder emits ``warps_out`` (current schema);
    some older test fixtures still use ``warps``. Accept both so the hint
    surface stays correct against real game state and legacy test data.
    """
    raw = sector.get("warps_out")
    if not raw:
        raw = sector.get("warps")
    return [int(w) for w in (raw or [])]


def _port_buys(port: dict[str, Any]) -> list[str]:
    raw = port.get("buys")
    if raw is None:
        raw = port.get("buying")
    return list(raw or [])


def _port_sells(port: dict[str, Any]) -> list[str]:
    raw = port.get("sells")
    if raw is None:
        raw = port.get("selling")
    return list(raw or [])


def _stock_qty(port: dict[str, Any], commodity: str) -> int:
    """Return current stock for a commodity regardless of schema shape.

    Real engine stock is ``{commodity: {"current": int, "max": int,
    "price": int, "side": "…"}}``. Legacy/test fixtures may emit a flat
    ``{commodity: int}`` map. Handle both.
    """
    stock = port.get("stock") or {}
    v = stock.get(commodity)
    if isinstance(v, dict):
        return int(v.get("current", 0) or 0)
    if isinstance(v, (int, float)):
        return int(v)
    return 0


def _stock_price(port: dict[str, Any], commodity: str) -> int | None:
    """Return best-known price for a commodity, checking both schemas."""
    stock = port.get("stock") or {}
    v = stock.get(commodity)
    if isinstance(v, dict):
        p = v.get("price")
        if p is not None:
            return int(p)
    prices = port.get("prices") or {}
    p = prices.get(commodity)
    if p is not None:
        return int(p)
    return None


def summarize_status(obs: Observation) -> str:
    """One-line status string for the chat panel header."""
    s = obs.ship or {}
    holds = int(s.get("holds") or s.get("cargo_max") or 0)
    used = _holds_used(s)
    sec = obs.sector or {}
    port = sec.get("port") if isinstance(sec, dict) else None
    port_text = ""
    if port:
        code = port.get("code") or port.get("class_id")
        port_text = f", port {code}"
    return (
        f"Day {obs.day} tick {obs.tick} — {obs.credits:,} cr, "
        f"fighters {int(s.get('fighters', 0))}, "
        f"holds {used}/{holds}{port_text}"
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
    warps = _warps(sec)
    port = sec.get("port") if isinstance(sec, dict) else None

    if warps:
        preview = ", ".join(map(str, warps[:8]))
        more = "" if len(warps) <= 8 else f" (+{len(warps) - 8} more)"
        hints["warp"] = f"Adjacent sectors: {preview}{more}"
    else:
        hints["warp"] = "No visible warps — try scanning first."

    if port is not None:
        bits: list[str] = []
        for c in ("fuel_ore", "organics", "equipment"):
            p = _stock_price(port, c)
            if p is not None:
                bits.append(f"{c}={p}")
        hints["trade"] = "Port prices: " + ", ".join(bits) if bits else "Port here."
    else:
        hints["trade"] = "No trading port in this sector."

    hints["scan"] = "Reveals port class + commodities in current sector."

    hints["wait"] = "Skip this tick."

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
    port = sec.get("port") if isinstance(sec, dict) else None
    ship_cargo = (obs.ship or {}).get("cargo", {}) or {}

    if port is not None:
        for c in _port_buys(port):
            if int(ship_cargo.get(c, 0)) > 0:
                return f"Port here buys {c} — consider SELL {c}."
        sells = _port_sells(port)
        if sells and obs.credits >= 1000:
            for c in sells:
                if _stock_qty(port, c) > 0:
                    return f"Port here sells {c} — consider BUY {c}."

    warps = _warps(sec)
    if warps:
        return f"No local action — WARP {warps[0]} to keep moving."

    return "Consider SCAN to reveal neighbours."
