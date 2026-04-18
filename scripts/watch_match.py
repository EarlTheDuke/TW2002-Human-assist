"""Poll the running TW2K-AI server and write a human-readable log.

Usage:  python scripts/watch_match.py [--url http://127.0.0.1:8000] [--out match.log]

Streams every event as it arrives (via /events with ?since=<seq>), appends
periodic summary snapshots of player state, and — at each day transition —
emits a per-player "healthy game" SCORECARD evaluated against the rubric in
docs/HEALTHY_GAME_PLAYBOOK.md §8.

The scorecard is the quick-glance answer to "is this agent playing well?"
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

# ---------------------------------------------------------------------------
# Rubric (kept in lockstep with docs/HEALTHY_GAME_PLAYBOOK.md §8)
# ---------------------------------------------------------------------------

RUBRIC: dict[int, list[dict]] = {
    1: [
        {"id": "net_worth_gain_pct", "label": "net worth +20%",          "threshold": 20},
        {"id": "distinct_trades",    "label": "≥3 trades",               "threshold": 3},
        {"id": "distinct_sectors",   "label": "≥4 sectors visited",      "threshold": 4},
    ],
    2: [
        {"id": "distinct_port_pairs","label": "≥2 port pairs",           "threshold": 2},
        {"id": "net_worth",          "label": "net worth ≥150k",         "threshold": 150_000},
        {"id": "bought_upgrade",     "label": "density scanner or ship", "one_of": ["density_scanner", "ship_upgrade"]},
    ],
    3: [
        {"id": "event_seen",         "label": "Genesis deployed",         "kind": "genesis_deployed"},
        {"id": "event_seen",         "label": "Citadel build started",    "kind": "build_citadel"},
    ],
    4: [
        {"id": "event_seen",         "label": "Citadel L1 complete",      "kind": "citadel_complete"},
        {"id": "net_worth",          "label": "net worth ≥500k",          "threshold": 500_000},
    ],
    5: [
        {"id": "citadel_level_min",  "label": "Citadel ≥ L2",             "threshold": 2},
        {"id": "any_event_seen",     "label": "corp / alliance / probe",  "kinds": ["corp_create", "alliance_formed", "probe"]},
        {"id": "net_worth",          "label": "net worth ≥1M",            "threshold": 1_000_000},
    ],
}

EQUIP_UPGRADES = {"density_scanner", "holo_scanner", "ether_probe"}
SHIP_UPGRADES_FROM_STARTER = {
    "scout_marauder", "missile_frigate", "battleship", "corporate_flagship",
    "merchant_freighter", "havoc_gunstar", "imperial_starship",
}


# ---------------------------------------------------------------------------
# Per-player per-day accumulators
# ---------------------------------------------------------------------------


@dataclass
class DayStats:
    nw_start: int = 0
    nw_end: int = 0
    trades: int = 0
    trade_sectors: list[int] = field(default_factory=list)  # in-order
    port_pairs: set[frozenset[int]] = field(default_factory=set)
    sectors_visited: set[int] = field(default_factory=set)
    bought_density: bool = False
    bought_ship: bool = False
    events_seen: set[str] = field(default_factory=set)
    citadel_level_reached: int = 0  # highest we've seen in day-end snapshots

    def note_trade(self, sector_id: int) -> None:
        self.trades += 1
        if self.trade_sectors and self.trade_sectors[-1] != sector_id:
            self.port_pairs.add(frozenset({self.trade_sectors[-1], sector_id}))
        self.trade_sectors.append(sector_id)


@dataclass
class PlayerArc:
    name: str = "?"
    days: dict[int, DayStats] = field(default_factory=dict)
    days_on_arc: int = 0  # count of days with ≥ (N-1)/N checks passed
    days_scored: int = 0

    def stats_for(self, day: int) -> DayStats:
        if day not in self.days:
            self.days[day] = DayStats()
        return self.days[day]


# ---------------------------------------------------------------------------
# Rubric evaluation
# ---------------------------------------------------------------------------


def _pct(start: int, end: int) -> float:
    if start <= 0:
        return 0.0
    return (end - start) / start * 100.0


def evaluate(stats: DayStats, day: int) -> list[tuple[str, bool, str]]:
    """Returns list of (label, ok, measured_text)."""
    checks = RUBRIC.get(day)
    if not checks:
        return []
    out: list[tuple[str, bool, str]] = []
    for c in checks:
        cid = c["id"]
        label = c["label"]
        ok = False
        measured = "?"
        if cid == "net_worth_gain_pct":
            pct = _pct(stats.nw_start, stats.nw_end)
            ok = pct >= c["threshold"]
            measured = f"+{pct:.0f}%" if pct >= 0 else f"{pct:.0f}%"
        elif cid == "distinct_trades":
            ok = stats.trades >= c["threshold"]
            measured = str(stats.trades)
        elif cid == "distinct_sectors":
            ok = len(stats.sectors_visited) >= c["threshold"]
            measured = str(len(stats.sectors_visited))
        elif cid == "distinct_port_pairs":
            ok = len(stats.port_pairs) >= c["threshold"]
            measured = str(len(stats.port_pairs))
        elif cid == "net_worth":
            ok = stats.nw_end >= c["threshold"]
            measured = f"${stats.nw_end:,}"
        elif cid == "bought_upgrade":
            ok = stats.bought_density or stats.bought_ship
            measured = ("density " if stats.bought_density else "") + ("ship" if stats.bought_ship else "")
            measured = measured.strip() or "—"
        elif cid == "event_seen":
            kind = c["kind"]
            ok = kind in stats.events_seen
            measured = "yes" if ok else "—"
        elif cid == "any_event_seen":
            seen = [k for k in c["kinds"] if k in stats.events_seen]
            ok = bool(seen)
            measured = ",".join(seen) if seen else "—"
        elif cid == "citadel_level_min":
            ok = stats.citadel_level_reached >= c["threshold"]
            measured = f"L{stats.citadel_level_reached}"
        out.append((label, ok, measured))
    return out


def render_scorecard(player_name: str, day: int, checks: list[tuple[str, bool, str]]) -> list[str]:
    if not checks:
        return []
    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)
    if passed == total:
        marker = "OK "
    elif passed >= total - 1:
        marker = "WRN"
    else:
        marker = "MIS"
    lines = [f"  [{marker}] {player_name:<22s} {passed}/{total}"]
    for label, ok, measured in checks:
        tick = "[+]" if ok else "[x]"
        lines.append(f"         {tick} {label:<28s} ({measured})")
    return lines


def render_arc_report(arcs: dict[str, PlayerArc], max_day: int) -> list[str]:
    lines = ["", "=" * 66, "  ARC REPORT — days-on-arc per player", "=" * 66]
    for _pid, arc in sorted(arcs.items(), key=lambda kv: -kv[1].days_on_arc):
        lines.append(f"  {arc.name:<22s} on-arc {arc.days_on_arc}/{arc.days_scored} days")
        for d in range(1, max_day + 1):
            st = arc.days.get(d)
            if st is None:
                continue
            checks = evaluate(st, d)
            if not checks:
                continue
            passed = sum(1 for _, ok, _ in checks if ok)
            tag = "OK " if passed == len(checks) else ("WRN" if passed >= len(checks) - 1 else "MIS")
            trades = st.trades
            nw = st.nw_end
            lines.append(f"     Day {d}  [{tag}] {passed}/{len(checks)}   trades={trades:>3}  nw=${nw:,}")
    lines.append("=" * 66)
    return lines


# ---------------------------------------------------------------------------
# HTTP / polling
# ---------------------------------------------------------------------------


def jget(url: str, timeout: float = 5.0):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def fmt_player(p: dict) -> str:
    cargo = p.get("cargo") or {}
    holds = p.get("holds") or 0
    used = sum(int(v) for v in cargo.values())
    return (
        f"{p['name']:<22s} "
        f"sec={p.get('sector_id','?'):>4} "
        f"cr={p.get('credits',0):>7}  "
        f"nw={p.get('net_worth',0):>7}  "
        f"fig={p.get('fighters',0):>4}  "
        f"cargo={used}/{holds}  "
        f"turns_day={p.get('turns_today','?')}/{p.get('turns_per_day','?')}  "
        f"ship={p.get('ship','?')}"
    )


# ---------------------------------------------------------------------------
# Event → stats update
# ---------------------------------------------------------------------------


def resolve_actor(ev: dict, state_players: dict[str, dict]) -> str | None:
    """Some events don't carry actor_id; try to infer from payload."""
    aid = ev.get("actor_id")
    if aid:
        return aid
    kind = ev.get("kind")
    payload = ev.get("payload") or {}
    if kind == "citadel_complete":
        planet_id = payload.get("planet_id")
        if planet_id is None:
            return None
        for pid, pl in state_players.items():
            for planet in pl.get("planets", []) or []:
                if planet.get("id") == planet_id:
                    return pid
    return None


def update_from_event(
    arc: PlayerArc,
    day: int,
    ev: dict,
) -> None:
    stats = arc.stats_for(day)
    kind = ev.get("kind")
    payload = ev.get("payload") or {}
    sector_id = ev.get("sector_id")

    if kind == "warp":
        to = payload.get("to")
        if isinstance(to, int):
            stats.sectors_visited.add(to)
    elif kind == "trade":
        # Only count successful side actions — skip tolls (which also emit TRADE)
        if "commodity" in payload and isinstance(sector_id, int):
            stats.note_trade(sector_id)
            stats.sectors_visited.add(sector_id)
    elif kind == "buy_equip":
        item = payload.get("item") or ""
        if item in EQUIP_UPGRADES:
            stats.bought_density = True
        stats.events_seen.add(kind)
    elif kind == "buy_ship":
        sc = payload.get("ship_class") or ""
        if sc in SHIP_UPGRADES_FROM_STARTER:
            stats.bought_ship = True
        stats.events_seen.add(kind)
    else:
        stats.events_seen.add(kind or "?")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--out", default="match.log")
    ap.add_argument("--poll-ms", type=int, default=1500)
    ap.add_argument("--summary-every", type=int, default=20,
                    help="Print a player-state summary every N event-polls.")
    ap.add_argument("--no-scorecards", action="store_true",
                    help="Disable rubric scorecards (events + summary only).")
    args = ap.parse_args()

    logfile = open(args.out, "a", encoding="utf-8", buffering=1)

    def log(line: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {line}")
        logfile.write(f"[{ts}] {line}\n")

    def logn(lines: list[str]) -> None:
        for line in lines:
            log(line)

    log(f"=== watcher starting · target={args.url} · log={args.out} ===")
    if not args.no_scorecards:
        log("=== scorecard rubric loaded from docs/HEALTHY_GAME_PLAYBOOK.md §8 ===")
        for d, checks in RUBRIC.items():
            labels = ", ".join(c["label"] for c in checks)
            log(f"    Day {d}: {labels}")

    since = 0
    loops = 0
    last_player_summary_ts = 0.0
    last_status = ""
    arcs: dict[str, PlayerArc] = defaultdict(PlayerArc)
    current_day = 0         # the day the latest events belong to
    nw_start_seeded = False  # seed nw_start from first snapshot
    max_day_seen = 0

    def seed_day_nw(day_no: int, state: dict) -> None:
        for p in state.get("players", []):
            pid = p["id"]
            if pid not in arcs:
                arcs[pid] = PlayerArc(name=p.get("name", pid))
            else:
                arcs[pid].name = p.get("name", arcs[pid].name)
            st = arcs[pid].stats_for(day_no)
            if st.nw_start == 0:
                st.nw_start = int(p.get("net_worth") or p.get("credits") or 0)

    def close_day(day_no: int, state: dict) -> None:
        """Finalise Day N: record nw_end, citadel levels, emit scorecards."""
        if args.no_scorecards:
            return
        player_dicts = {p["id"]: p for p in state.get("players", [])}
        planets = state.get("planets") or state.get("universe", {}).get("planets", []) or []
        planet_level_by_owner: dict[str, int] = {}
        for pl in planets:
            owner = pl.get("owner_id")
            lvl = int(pl.get("citadel_level") or 0)
            if owner is not None and lvl > planet_level_by_owner.get(owner, 0):
                planet_level_by_owner[owner] = lvl

        log("")
        log(f"========== Day {day_no} Scorecard ==========")
        for pid, arc in arcs.items():
            st = arc.stats_for(day_no)
            p = player_dicts.get(pid, {})
            st.nw_end = int(p.get("net_worth") or st.nw_end or st.nw_start)
            st.citadel_level_reached = max(st.citadel_level_reached, planet_level_by_owner.get(pid, 0))
            # also mirror flags derived from cumulative events — carry milestones forward
            for prior_day in range(1, day_no):
                prior = arc.days.get(prior_day)
                if prior is None:
                    continue
                st.events_seen.update(prior.events_seen)
                st.bought_density = st.bought_density or prior.bought_density
                st.bought_ship = st.bought_ship or prior.bought_ship
            checks = evaluate(st, day_no)
            if not checks:
                continue
            logn(render_scorecard(arc.name, day_no, checks))
            passed = sum(1 for _, ok, _ in checks if ok)
            arc.days_scored += 1
            if passed >= len(checks) - 1:
                arc.days_on_arc += 1
        log("=" * 40)
        log("")

    while True:
        loops += 1
        try:
            evs = jget(f"{args.url}/events?since={since}&limit=200")
            new_events = evs.get("events", [])

            # Ingest events
            for ev in new_events:
                since = max(since, int(ev["seq"]))
                kind = ev.get("kind", "?")
                day = int(ev.get("day") or current_day or 1)
                max_day_seen = max(max_day_seen, day)
                tag = f"D{day}·{ev.get('tick',0)}"
                actor = ev.get("actor_id") or "-"
                summary = ev.get("summary", "") or json.dumps(ev.get("payload", {}), default=str)
                log(f"{tag:>7s}  {kind:<18s} {actor:<6s}  {summary}")

                # Route to accumulators
                pid = resolve_actor(ev, {})  # actor lookup from payload if missing
                if pid:
                    if pid not in arcs:
                        arcs[pid] = PlayerArc(name=pid)
                    update_from_event(arcs[pid], day, ev)

            # Periodic snapshot + day-transition scorecard
            if loops % args.summary_every == 0 or (time.time() - last_player_summary_ts) > 30 or new_events:
                state = jget(f"{args.url}/state")
                status = state.get("status", "?")
                state_day = int(state.get("day") or 0)
                if status != last_status:
                    log(f"-- STATUS: {status} (day {state_day}, tick {state.get('tick','?')}) --")
                    last_status = status

                # Seed nw_start on first snapshot for whatever day we're in
                if not nw_start_seeded and state_day > 0:
                    current_day = state_day
                    seed_day_nw(current_day, state)
                    nw_start_seeded = True

                # Player name sync + day-transition emission
                for p in state.get("players", []):
                    pid = p["id"]
                    if pid not in arcs:
                        arcs[pid] = PlayerArc(name=p.get("name", pid))
                    else:
                        arcs[pid].name = p.get("name", arcs[pid].name)

                if state_day > current_day and current_day > 0:
                    # Close prior days we never finalised (rare, in case we missed a tick)
                    for d in range(current_day, state_day):
                        close_day(d, state)
                        seed_day_nw(d + 1, state)
                    current_day = state_day
                    max_day_seen = max(max_day_seen, state_day)

                # Every summary pass, only print summary in non-day-boundary case
                if loops % args.summary_every == 0 or (time.time() - last_player_summary_ts) > 30:
                    log("-- player summary --")
                    for p in state.get("players", []):
                        log("    " + fmt_player(p))
                    last_player_summary_ts = time.time()

                if state.get("finished"):
                    # Final day: finalise its scorecard too
                    if current_day > 0:
                        close_day(current_day, state)
                    log(f"=== GAME OVER · winner={state.get('winner_id')} reason={state.get('win_reason')} ===")
                    for p in state.get("players", []):
                        log("final  " + fmt_player(p))
                    logn(render_arc_report(arcs, max_day_seen))
                    break

        except urllib.error.URLError as e:
            log(f"!! server unreachable: {e}")
        except Exception as e:
            log(f"!! watcher error: {type(e).__name__}: {e}")

        time.sleep(args.poll_ms / 1000.0)

    logfile.close()


if __name__ == "__main__":
    main()
