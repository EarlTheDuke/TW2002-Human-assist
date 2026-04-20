"""Economy dashboards for the /play cockpit (Phase H6.4).

Two pure functions + a pair of FastAPI endpoints wire them:

* ``build_price_table(universe, player_id)`` — per known-port snapshot of
  live buy/sell prices + stock %, plus staleness from the player's
  last-seen-day.
* ``build_route_table(universe, player_id, *, max_routes=10)`` — top-N
  trade routes across the player's discovered port graph, ranked by
  estimated credits-per-turn using current prices, cargo capacity, and
  warp distance.

Both are **read-only** and use the universe + player state that already
exists in the runner. No per-match state is cached. That keeps the
endpoints idempotent and avoids any cross-session invalidation hazards.

Design notes
------------

* **Known-port fog-of-war respected.** Only ports in
  ``player.known_ports`` appear. Unknown ports shouldn't leak through
  the dashboard even though they leak less-strictly through spectator
  endpoints.
* **Live prices, not last-seen intel.** The player's ``known_ports``
  dict stores a snapshot at last-visit time. For the dashboard we
  recompute prices from the current universe so the UI reflects what a
  trade would *actually* execute at. ``last_seen_day`` / ``age_days``
  are still reported so the UI can show "stale" warnings if the port
  was last scanned >3 days ago.
* **Route cost = round-trip.** Trade loops in TW2002 are bidirectional
  (buy at A → sell at B → deadhead back to A for next load), so
  ``turns_per_trip`` = warp(A→B) + warp(B→A) + 2 (one turn docking at
  each end). If either direction has no BFS path, the route is skipped.
* **Commodity pairing.** A route is valid only when port A SELLS
  commodity X and port B BUYS commodity X. The profit per unit is then
  ``B.buy_price(X) - A.sell_price(X)``. Negative-profit pairs are
  filtered out.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from ..engine.economy import port_buy_price, port_sell_price
from ..engine.models import Commodity, Universe

COMMODITIES: tuple[Commodity, ...] = (
    Commodity.FUEL_ORE,
    Commodity.ORGANICS,
    Commodity.EQUIPMENT,
)


# ---------------------------------------------------------------------------
# Price table
# ---------------------------------------------------------------------------


def build_price_table(universe: Universe, player_id: str) -> dict[str, Any]:
    """Return a serialisable price snapshot for every known port.

    Raises ``KeyError`` if ``player_id`` is absent from the universe.
    """
    player = universe.players[player_id]
    known_ids = sorted(player.known_ports.keys())
    rows: list[dict[str, Any]] = []
    for sid in known_ids:
        sector = universe.sectors.get(sid)
        if sector is None or sector.port is None:
            continue
        port = sector.port
        buys: list[str] = []
        sells: list[str] = []
        prices: dict[str, dict[str, Any]] = {}
        for c in COMMODITIES:
            s = port.stock.get(c)
            stock_current = s.current if s is not None else 0
            stock_max = s.maximum if s is not None else 0
            pct = (stock_current / stock_max) if stock_max else 0.0
            if port.buys(c):
                buys.append(c.value)
                prices[c.value] = {
                    "side": "buy",  # port buys FROM player
                    "price": port_buy_price(port, c),
                    "stock": stock_current,
                    "max": stock_max,
                    "pct": round(pct, 3),
                }
            elif port.sells(c):
                sells.append(c.value)
                prices[c.value] = {
                    "side": "sell",  # port sells TO player
                    "price": port_sell_price(port, c),
                    "stock": stock_current,
                    "max": stock_max,
                    "pct": round(pct, 3),
                }
        last_seen = player.known_ports[sid].get("last_seen_day")
        age_days = (
            max(0, universe.day - last_seen) if isinstance(last_seen, int) else None
        )
        rows.append(
            {
                "sector_id": sid,
                "class": port.code,
                "buys": buys,
                "sells": sells,
                "prices": prices,
                "last_seen_day": last_seen,
                "age_days": age_days,
            }
        )
    return {
        "player_id": player_id,
        "day": universe.day,
        "commodities": [c.value for c in COMMODITIES],
        "ports": rows,
    }


# ---------------------------------------------------------------------------
# Trade-route ranking
# ---------------------------------------------------------------------------


def _bfs_hops(universe: Universe, src: int, dst: int, *, cap: int = 40) -> int | None:
    """Return shortest warp distance src→dst, or ``None`` if unreachable.

    Duplicates the hop count from ``runner._bfs_path`` but returns the
    integer directly and bails at ``cap`` hops — the dashboard only
    cares about short round-trips (long routes are low profit-per-turn).
    """
    if src == dst:
        return 0
    visited = {src}
    q: deque[tuple[int, int]] = deque([(src, 0)])
    while q:
        cur, d = q.popleft()
        if d >= cap:
            continue
        for nxt in universe.sectors[cur].warps:
            if nxt in visited:
                continue
            if nxt == dst:
                return d + 1
            visited.add(nxt)
            q.append((nxt, d + 1))
    return None


def build_route_table(
    universe: Universe,
    player_id: str,
    *,
    max_routes: int = 10,
    hop_cap: int = 25,
) -> dict[str, Any]:
    """Return up to ``max_routes`` best trade routes between known ports."""
    player = universe.players[player_id]
    holds = max(1, player.ship.holds)
    known_ids = sorted(player.known_ports.keys())

    # Cache (port, commodity) → (price, stock) pairs to avoid recomputing
    # inside the O(n^2) loop.
    sell_side: dict[tuple[int, Commodity], tuple[int, int]] = {}
    buy_side: dict[tuple[int, Commodity], tuple[int, int]] = {}
    for sid in known_ids:
        sector = universe.sectors.get(sid)
        if sector is None or sector.port is None:
            continue
        port = sector.port
        for c in COMMODITIES:
            s = port.stock.get(c)
            stock = s.current if s is not None else 0
            if port.sells(c):
                sell_side[(sid, c)] = (port_sell_price(port, c), stock)
            elif port.buys(c):
                # For BUY-side, stock is "capacity remaining" since the
                # port's stock counter is units already bought from
                # incoming sellers. Effective qty the port can absorb
                # from us is ``maximum - current``.
                capacity = (s.maximum - s.current) if s is not None else 0
                buy_side[(sid, c)] = (port_buy_price(port, c), max(0, capacity))

    candidates: list[dict[str, Any]] = []
    distance_cache: dict[tuple[int, int], int | None] = {}

    def _dist(a: int, b: int) -> int | None:
        key = (a, b)
        if key not in distance_cache:
            distance_cache[key] = _bfs_hops(universe, a, b, cap=hop_cap)
        return distance_cache[key]

    for (src, commodity), (sell_price, src_stock) in sell_side.items():
        if src_stock <= 0:
            continue
        for (dst, dst_commodity), (buy_price, dst_capacity) in buy_side.items():
            if dst_commodity is not commodity:
                continue
            if src == dst:
                continue
            profit_per_unit = buy_price - sell_price
            if profit_per_unit <= 0:
                continue
            qty = min(holds, src_stock, dst_capacity)
            if qty <= 0:
                continue
            fwd = _dist(src, dst)
            if fwd is None:
                continue
            back = _dist(dst, src)
            if back is None:
                continue
            turns = fwd + back + 2  # docking at each end
            profit_trip = profit_per_unit * qty
            profit_per_turn = profit_trip / turns
            candidates.append(
                {
                    "from_sector": src,
                    "to_sector": dst,
                    "commodity": commodity.value,
                    "buy_price": sell_price,
                    "sell_price": buy_price,
                    "profit_per_unit": profit_per_unit,
                    "qty": qty,
                    "profit_per_trip": profit_trip,
                    "turns": turns,
                    "profit_per_turn": round(profit_per_turn, 2),
                }
            )

    candidates.sort(key=lambda r: r["profit_per_turn"], reverse=True)
    return {
        "player_id": player_id,
        "day": universe.day,
        "holds": holds,
        "routes": candidates[:max_routes],
        "known_ports": len(known_ids),
    }


__all__ = ["COMMODITIES", "build_price_table", "build_route_table"]
