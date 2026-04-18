"""Offline smoke test for watch_match scorecards.

Simulates a day-1 and day-2 event stream for 3 agents and prints what the
watcher would log. Lets us eyeball the format without spinning up a server.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys


def _load():
    path = pathlib.Path(__file__).resolve().parent / "watch_match.py"
    spec = importlib.util.spec_from_file_location("watch_match", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["watch_match"] = module
    spec.loader.exec_module(module)
    return module


wm = _load()


def emit(lines):
    for line in lines:
        print(line)


def main() -> None:
    # Three agents: Blake (on-arc), Reyes (warning), Vex (stalled).
    arcs = {
        "p1": wm.PlayerArc(name="Commodore Blake"),
        "p2": wm.PlayerArc(name="Captain Reyes"),
        "p3": wm.PlayerArc(name="Admiral Vex"),
    }

    # Seed day 1 starting net worth
    for arc in arcs.values():
        arc.stats_for(1).nw_start = 40_000

    # ---------- Day 1 ----------
    def ev(kind, actor, sector=None, payload=None):
        return {"kind": kind, "actor_id": actor, "sector_id": sector, "payload": payload or {}}

    # Blake: perfect — 5 trades across 3 sectors, multiple warps
    for k in [
        ev("warp", "p1", 7, {"from": 1, "to": 7}),
        ev("warp", "p1", 11, {"from": 7, "to": 11}),
        ev("trade", "p1", 11, {"commodity": "fuel_ore", "qty": 20, "side": "sell"}),
        ev("warp", "p1", 12, {"from": 11, "to": 12}),
        ev("trade", "p1", 12, {"commodity": "organics", "qty": 20, "side": "buy"}),
        ev("warp", "p1", 11, {"from": 12, "to": 11}),
        ev("trade", "p1", 11, {"commodity": "organics", "qty": 20, "side": "sell"}),
        ev("trade", "p1", 12, {"commodity": "equipment", "qty": 20, "side": "buy"}),
        ev("warp", "p1", 15, {"from": 12, "to": 15}),
        ev("trade", "p1", 15, {"commodity": "fuel_ore", "qty": 10, "side": "sell"}),
    ]:
        wm.update_from_event(arcs["p1"], 1, k)

    # Reyes: only 2 trades (below threshold)
    for k in [
        ev("warp", "p2", 7, {"from": 2, "to": 7}),
        ev("warp", "p2", 8, {"from": 7, "to": 8}),
        ev("trade", "p2", 8, {"commodity": "fuel_ore", "qty": 20, "side": "buy"}),
        ev("trade", "p2", 8, {"commodity": "fuel_ore", "qty": 20, "side": "sell"}),
    ]:
        wm.update_from_event(arcs["p2"], 1, k)

    # Vex: no trades at all, 1 sector visited
    wm.update_from_event(arcs["p3"], 1, ev("warp", "p3", 4, {"from": 3, "to": 4}))

    # Simulate end-of-day state snapshot
    state_d1_end = {
        "players": [
            {"id": "p1", "name": "Commodore Blake", "net_worth": 55_000, "planets": []},
            {"id": "p2", "name": "Captain Reyes",   "net_worth": 42_500, "planets": []},
            {"id": "p3", "name": "Admiral Vex",     "net_worth": 39_000, "planets": []},
        ],
        "planets": [],
    }

    print("=" * 40)
    print("  Day 1 Scorecard (synthetic)")
    print("=" * 40)
    for pid, arc in arcs.items():
        st = arc.stats_for(1)
        p = next(p for p in state_d1_end["players"] if p["id"] == pid)
        st.nw_end = p["net_worth"]
        checks = wm.evaluate(st, 1)
        emit(wm.render_scorecard(arc.name, 1, checks))
        if sum(1 for _, ok, _ in checks if ok) >= len(checks) - 1:
            arc.days_on_arc += 1
        arc.days_scored += 1
    print()

    # ---------- Day 2 ----------
    # Seed nw_start for day 2 from day 1 end
    for pid, arc in arcs.items():
        arc.stats_for(2).nw_start = arc.stats_for(1).nw_end

    # Blake: buys density, 3 port pairs, ends at 280k
    for k in [
        ev("buy_equip", "p1", payload={"item": "density_scanner", "qty": 1, "total": 5000}),
        ev("trade", "p1", 11, {"commodity": "fuel_ore", "qty": 30, "side": "sell"}),
        ev("trade", "p1", 12, {"commodity": "organics", "qty": 30, "side": "buy"}),
        ev("trade", "p1", 14, {"commodity": "equipment", "qty": 30, "side": "sell"}),
        ev("trade", "p1", 15, {"commodity": "organics", "qty": 30, "side": "buy"}),
        ev("trade", "p1", 21, {"commodity": "fuel_ore", "qty": 30, "side": "buy"}),
        ev("trade", "p1", 22, {"commodity": "equipment", "qty": 30, "side": "sell"}),
    ]:
        wm.update_from_event(arcs["p1"], 2, k)

    # Reyes: same 1 port pair as day 1 (stuck)
    for k in [
        ev("trade", "p2", 8, {"commodity": "fuel_ore", "qty": 20, "side": "buy"}),
        ev("trade", "p2", 9, {"commodity": "fuel_ore", "qty": 20, "side": "sell"}),
        ev("trade", "p2", 8, {"commodity": "fuel_ore", "qty": 20, "side": "buy"}),
    ]:
        wm.update_from_event(arcs["p2"], 2, k)

    # Vex: flat
    wm.update_from_event(arcs["p3"], 2, ev("wait", "p3"))

    state_d2_end = {
        "players": [
            {"id": "p1", "name": "Commodore Blake", "net_worth": 280_000, "planets": []},
            {"id": "p2", "name": "Captain Reyes",   "net_worth":  60_000, "planets": []},
            {"id": "p3", "name": "Admiral Vex",     "net_worth":  39_000, "planets": []},
        ],
        "planets": [],
    }

    print("=" * 40)
    print("  Day 2 Scorecard (synthetic)")
    print("=" * 40)
    for pid, arc in arcs.items():
        st = arc.stats_for(2)
        p = next(p for p in state_d2_end["players"] if p["id"] == pid)
        st.nw_end = p["net_worth"]
        checks = wm.evaluate(st, 2)
        emit(wm.render_scorecard(arc.name, 2, checks))
        if sum(1 for _, ok, _ in checks if ok) >= len(checks) - 1:
            arc.days_on_arc += 1
        arc.days_scored += 1
    print()

    # Arc report
    emit(wm.render_arc_report(arcs, 2))


if __name__ == "__main__":
    main()
