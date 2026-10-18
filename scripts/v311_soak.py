"""NOTE 57 v311-rulings-v1 item 9. A 10-day soak with V311_PROFILE on.

Test use only. The real app runs in this process on a free port in 8020-8030
and plays one match with four code bots (the server's heuristic seats).
V311_PROFILE is set only inside this process; the stored default stays legacy.

Clock: RULINGS s5 gives back turns_per_day over 24 hours. A real-time game
day would take a day, so --day-seconds compresses TURN_REGEN_DAY_SECONDS
(default 60 s for one game day, so one "hour" is 2.5 s). The live-pace day
roll follows that clock. Everything else runs at its normal speed.

Writes docs/playtests/v311-profile-v1/soak_<seed>.json and .md.

    python scripts/v311_soak.py --seed 250925 --days 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import socket
import sys
import tempfile
import threading
import time
import traceback
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "playtests" / "v311-profile-v1"
PORTS = range(8020, 8031)
SEATS = ("P1", "P2", "P3", "P4")


def free_port() -> int:
    for port in PORTS:
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit("no free port in 8020-8030")


class Tally(logging.Handler):
    """Every log record that carries an exception."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.rows: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.exc_info:
            self.rows.append(f"{record.name}: {record.getMessage()} | "
                             + "".join(traceback.format_exception(*record.exc_info))[-600:])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=250925)
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--size", type=int, default=1000)
    ap.add_argument("--day-seconds", type=float, default=60.0)
    a = ap.parse_args(argv)

    import uvicorn

    import tw2k.engine.constants as K
    import tw2k.engine.runner as ER
    import tw2k.server.runner as SR
    from tw2k.engine import GameConfig
    from tw2k.engine.models import EventKind
    from tw2k.engine.planets import daily_production
    from tw2k.engine.victory import full_net_worth
    from tw2k.server.app import create_app
    from tw2k.server.runner import AgentSpec, MatchSpec

    K.V311_PROFILE = "v311"
    K.TURN_REGEN_DAY_SECONDS = float(a.day_seconds)
    assert K.TW2002_LIVE_PROFILE == "legacy"

    regen: dict[str, int] = defaultdict(int)
    regen_by_day: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    acts: dict[str, dict[str, int]] = {pid: {"ok": 0, "rejected": 0} for pid in SEATS}
    reject_samples: dict[str, list[str]] = defaultdict(list)
    kinds: dict[str, dict[str, int]] = {pid: defaultdict(int) for pid in SEATS}
    day_kinds: dict[int, dict[str, dict[str, int]]] = defaultdict(lambda: {pid: defaultdict(int) for pid in SEATS})
    wait_reasons: dict[str, dict[str, int]] = {pid: defaultdict(int) for pid in SEATS}
    exceptions: list[str] = []
    holder: dict = {}

    real_refresh = ER.refresh_offline_turns

    def counted_refresh(player, now=None):
        before = int(player.turns_today)
        real_refresh(player, now)
        gain = before - int(player.turns_today)
        if gain > 0:
            regen[player.id] += gain
            u = holder.get("u")
            regen_by_day[int(getattr(u, "day", 0) or 0)][player.id] += gain

    ER.refresh_offline_turns = counted_refresh

    real_apply = SR.apply_action

    def counted_apply(universe, pid, action):
        holder["u"] = universe
        try:
            res = real_apply(universe, pid, action)
        except Exception:
            exceptions.append(f"apply_action {pid} {action.kind}: " + traceback.format_exc()[-800:])
            raise
        kind = getattr(action.kind, "value", str(action.kind))
        if pid in acts:
            acts[pid]["ok" if res.ok else "rejected"] += 1
            kinds[pid][kind] += 1
            day_kinds[int(universe.day)][pid][kind] += 1
            if kind == "wait":
                why = str(getattr(action, "thought", "") or "")[:90]
                wait_reasons[pid][why] += 1
            if not res.ok and len(reject_samples[pid]) < 8:
                reject_samples[pid].append(f"d{universe.day} {kind}: {res.error}")
        return res

    SR.apply_action = counted_apply

    tally = Tally()
    logging.getLogger().addHandler(tally)

    tmp = Path(tempfile.mkdtemp(prefix="v311_soak_"))
    port = free_port()
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp / "saves"
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))

    async def _main() -> None:
        async def start() -> None:
            while not server.started:
                await asyncio.sleep(0.05)
            await runner.start(MatchSpec(
                config=GameConfig(seed=a.seed, universe_size=a.size, max_days=a.days,
                                  turns_per_day=K.STARTING_TURNS_PER_DAY, starting_credits=20_000,
                                  enable_ferrengi=True, enable_planets=True, action_delay_s=0.0),
                agents=[AgentSpec(player_id=pid, name=f"Bot{pid}", kind="heuristic") for pid in SEATS],
                action_delay_s=0.0,
            ))

        task = asyncio.create_task(start())
        await server.serve()
        task.cancel()
        await runner.stop()

    thread = threading.Thread(target=lambda: asyncio.run(_main()), daemon=True)
    t0 = time.time()
    thread.start()
    while time.time() - t0 < 60 and runner.state.universe is None:
        time.sleep(0.1)
    if runner.state.universe is None:
        raise SystemExit("the local server did not start")

    u = runner.state.universe
    holder["u"] = u
    day_marks: list[dict] = []
    seen_day = 0
    last_sector: dict[str, int] = {}
    still: dict[str, int] = defaultdict(int)
    deadline = t0 + a.days * a.day_seconds * 4 + 300
    while time.time() < deadline:
        u = runner.state.universe
        over = bool(getattr(u, "game_over", False)) or runner.state.status in ("finished", "stopped", "error")
        if u is not None and int(u.day) != seen_day:
            seen_day = int(u.day)
            row = {"day": seen_day, "t": round(time.time() - t0, 1), "seats": {}}
            for pid in SEATS:
                p = u.players[pid]
                row["seats"][pid] = {"credits": int(p.credits), "net_worth": int(full_net_worth(u, p)),
                                     "sector": int(p.sector_id), "turns_used": int(p.turns_today),
                                     "ship": p.ship.ship_class.value, "alive": bool(p.alive)}
                if last_sector.get(pid) == int(p.sector_id):
                    still[pid] += 1
                else:
                    still[pid] = 0
                last_sector[pid] = int(p.sector_id)
            day_marks.append(row)
            print(f"day {seen_day} t={row['t']}s "
                  + " ".join(f"{pid}:{s['credits']}/{s['net_worth']}@{s['sector']}" for pid, s in row["seats"].items()),
                  flush=True)
        if over:
            break
        time.sleep(0.5)
    elapsed = round(time.time() - t0, 1)
    u = runner.state.universe
    server.should_exit = True
    thread.join(timeout=30)

    taxes: dict[str, int] = defaultdict(int)
    tax_rows: list[dict] = []
    citadel_starts: list[dict] = []
    deaths: dict[str, int] = defaultdict(int)
    clashes = 0
    for ev in u.events:
        if ev.kind is EventKind.TAX_COLLECTED:
            taxes[ev.actor_id] += int(ev.payload.get("tax") or 0)
            tax_rows.append({"day": ev.day if hasattr(ev, "day") else None, "pid": ev.actor_id,
                             "tax": int(ev.payload.get("tax") or 0)})
        elif ev.kind is EventKind.BUILD_CITADEL:
            citadel_starts.append({"pid": ev.actor_id, "planet": ev.payload.get("planet_id"),
                                   "level": ev.payload.get("level")})
        elif ev.kind is EventKind.SHIP_DESTROYED:
            deaths[str(ev.payload.get("victim") or ev.actor_id)] += 1
        elif ev.kind is EventKind.COMBAT and ev.payload.get("wave") is not None:
            clashes += 1
    seats = {}
    for pid in SEATS:
        p = u.players[pid]
        planets = [pl for pl in u.planets.values() if pl.owner_id == pid]
        home = next((pl for pl in planets if pl.origin == "other"), None)
        home_row = None
        if home is not None:
            made = daily_production(home.class_id, home.colonists)
            fuel = 0
            for key, value in home.colonists.items():
                token = key.value if hasattr(key, "value") else str(key)
                if token == "fuel_ore":
                    fuel = int(value or 0)
            home_row = {
                "id": int(home.id), "sector": int(home.sector_id),
                "fedspace": int(home.sector_id) in K.FEDSPACE_SECTORS,
                "fuel": fuel,
                "production": made,
            }
        seats[pid] = {
            "credits": int(p.credits), "net_worth": int(full_net_worth(u, p)), "alive": bool(p.alive),
            "ship": p.ship.ship_class.value, "alignment": int(p.alignment), "experience": int(p.experience),
            "actions_ok": acts[pid]["ok"], "rejected": acts[pid]["rejected"],
            "reject_samples": reject_samples[pid], "turn_regen_total": int(regen[pid]),
            "taxes_paid": int(taxes[pid]), "deaths": int(deaths[pid]),
            "citadels": {str(pl.id): {"class": pl.class_id.value, "level": int(pl.citadel_level),
                                      "target": int(getattr(pl, "citadel_target", 0) or 0)} for pl in planets},
            "kinds": dict(kinds[pid]), "days_in_same_sector_at_end": int(still[pid]),
            "wait_reasons": dict(sorted(wait_reasons[pid].items(), key=lambda kv: -kv[1])[:6]),
            "home": home_row,
        }
    result = {
        "seed": a.seed, "days_asked": a.days, "day_reached": int(u.day), "size": a.size,
        "day_seconds": a.day_seconds, "elapsed_s": elapsed, "port_range": "8020-8030",
        "status": runner.state.status, "game_over": bool(getattr(u, "game_over", False)),
        "exceptions": exceptions + tally.rows, "offensive_waves": clashes,
        "citadel_starts": citadel_starts, "taxes": tax_rows, "seats": seats, "days": day_marks,
        "regen_by_day": {d: dict(v) for d, v in sorted(regen_by_day.items())},
        "kinds_by_day": {d: {pid: dict(k) for pid, k in v.items()} for d, v in sorted(day_kinds.items())},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"soak_{a.seed}.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    lines = [f"# v311 soak, seed {a.seed}", "",
             f"V311_PROFILE on in this process only. {a.days} days asked, day {u.day} reached, "
             f"status {runner.state.status}, {elapsed} s wall clock, one game day = {a.day_seconds:g} s of "
             f"the turn clock. Exceptions: {len(result['exceptions'])}. Offensive waves: {clashes}.", "",
             "| seat | credits | net worth | ship | ok | rejected | regen turns | taxes | deaths | citadels | home |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for pid, s in seats.items():
        cit = ", ".join(f"{c['class']} L{c['level']}" for c in s["citadels"].values()) or "-"
        home = s.get("home") or {}
        where = "-" if not home else f"#{home['id']} s{home['sector']}" + (" FED" if home["fedspace"] else "")
        made = (home.get("production") or {}) if home else {}
        prod = "" if not made else f" {made.get('fuel_ore', 0)}/{made.get('organics', 0)}/{made.get('equipment', 0)}"
        lines.append(f"| {pid} | {s['credits']:,} | {s['net_worth']:,} | {s['ship']} | {s['actions_ok']} | "
                     f"{s['rejected']} | {s['turn_regen_total']} | {s['taxes_paid']:,} | {s['deaths']} | {cit} | {where}{prod} |")
    (OUT / f"soak_{a.seed}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
