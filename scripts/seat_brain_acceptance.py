#!/usr/bin/env python3
"""Seat-only acceptance harness for the S3 SeatBrain (seat-bot S4).

  # 1. engine-free: hand-built fogged observations for the empire loop
  python scripts/seat_brain_acceptance.py synthetic

  # 2. record a trace of the seat's OWN observations from an offline engine run
  #    (mailbox payload format - identical to what a live seat receives)
  python scripts/seat_brain_acceptance.py record --out docs/playtests/seat_trace.jsonl --days 4

  # 3. replay any trace (offline recording, or a live one from seat_brain_v2.py --record)
  #    through a FRESH brain; validate every action against that observation's legal_actions
  python scripts/seat_brain_acceptance.py replay docs/playtests/seat_trace.jsonl

  # 4. N1 offline proof (no live match): seed 250925, spawn sector 6, day-1 StarDock
  python scripts/seat_brain_acceptance.py n1

Exit code 0 = every action valid and the genesis -> land -> citadel -> ferry loop completed.
Replay and synthetic modes never touch the engine state, /state, or another seat.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tw2k.agents.seat_acceptance import (  # noqa: E402
    STORYBOARD,
    MilestoneTracker,
    aba_bounces,
    ferry_storyboard,
    load_jsonl,
    replay,
    validate_action,
)
from tw2k.agents.seat_brain import SeatBrain  # noqa: E402


def run_synthetic() -> int:
    failures = 0
    for board_name, board in (("genesis", STORYBOARD), ("citadel+ferry", ferry_storyboard())):
        brain = SeatBrain()
        for label, obs, kind, args in board:
            action = brain.decide(obs)
            problems = validate_action(obs, action)
            match = action["kind"] == kind and all(action["args"].get(k) == v for k, v in args.items())
            ok = match and not problems
            failures += not ok
            print(f"{'OK ' if ok else 'FAIL'} [{board_name}] {label}: {action['kind']} {action['args']}"
                  + ("" if match else f"  (expected {kind} {args})") + (f"  {problems}" if problems else ""))
    print(f"synthetic: {'PASS' if failures == 0 else f'{failures} FAIL'}")
    return 0 if failures == 0 else 1


def record_offline(out: Path, *, seed: int = 230923, credits: int = 120_000, days: int = 4,
                   max_actions: int = 4000, seat: str = "P1") -> dict:
    """Offline engine run. The brain only sees build_observation(u, seat); every payload is recorded."""
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.actions import Action
    from tw2k.engine.models import Player
    from tw2k.engine.observation import build_observation
    from tw2k.engine.runner import apply_action, tick_day

    u = generate_universe(GameConfig(seed=seed, universe_size=150, max_days=days + 2, turns_per_day=250,
                                     starting_credits=credits, enable_ferrengi=False, enable_planets=True))
    for pid, name in ((seat, "Seat"), ("P9", "Idle")):
        p = Player(id=pid, name=name, agent_kind="external", sector_id=1, credits=credits)
        u.players[pid] = p
        u.sectors[1].occupant_ids.append(pid)
    brain = SeatBrain()
    tracker = MilestoneTracker()
    out.parent.mkdir(parents=True, exist_ok=True)
    rejected = 0
    with out.open("w", encoding="utf-8") as f:
        for seq in range(max_actions):
            p = u.players[seat]
            if p.turns_today >= p.turns_per_day:
                if u.day >= days:
                    break
                tick_day(u)
                continue
            obs = build_observation(u, seat).model_dump(mode="json")
            f.write(json.dumps({"seat": seat, "turn_seq": seq, "observation": obs}) + "\n")
            action = brain.decide(obs)
            tracker.observe(seq, obs, action)
            rejected += not apply_action(u, seat, Action(**action)).ok
            if action["kind"] == "query_limpets":
                tick_day(u)
    return {"report": tracker.report, "rejected": rejected}


def _open_seat(u, seat: str, sector: int, credits: int):
    """Place a seat the way the live server does: FedSpace spawn knowledge, no god view.

    Neighbour ports are remembered as class + stock only (no prices) until visited.
    """
    from tw2k.engine.models import Player

    p = Player(id=seat, name="Seat", agent_kind="external", sector_id=sector, credits=credits,
               turns_per_day=u.config.turns_per_day)
    u.players[seat] = p
    u.sectors[sector].occupant_ids.append(seat)
    p.known_sectors.add(sector)
    sec = u.sectors[sector]
    p.known_warps[sector] = list(sec.warps)
    if sec.port is not None:
        p.known_ports[sector] = {
            "class": sec.port.code,
            "stock": {c.value: {"current": s.current, "max": s.maximum} for c, s in sec.port.stock.items()},
            "last_seen_day": u.day,
        }
    for wid in sec.warps:
        p.known_sectors.add(wid)
        w = u.sectors[wid]
        if w.port is not None:
            p.known_ports[wid] = {
                "class": w.port.code,
                "stock": {c.value: {"current": s.current, "max": s.maximum} for c, s in w.port.stock.items()},
                "last_seen_day": u.day,
            }
    return p


def prove_n1_day(*, seed: int = 250925, credits: int = 20_000, spawn: int = 6,
                 universe_size: int = 1000, turns_per_day: int = 1000) -> dict:
    """One fogged day from ``spawn``. The brain never sees ``/state``."""
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.actions import Action
    from tw2k.engine.observation import build_observation
    from tw2k.engine.runner import apply_action

    u = generate_universe(GameConfig(
        seed=seed, universe_size=universe_size, max_days=3, turns_per_day=turns_per_day,
        starting_credits=credits, enable_ferrengi=False, enable_planets=True,
    ))
    p = _open_seat(u, "P1", spawn, credits)
    brain = SeatBrain()
    rows: list[tuple] = []
    rejected = 0
    peak = credits
    trade_profit = 0
    reached_day = None
    reached_turns = None
    for _ in range(2500):
        if p.turns_today >= p.turns_per_day:
            break
        day = u.day
        sector = p.sector_id
        if sector == 1 and reached_day is None:
            reached_day, reached_turns = day, p.turns_today
        obs = build_observation(u, "P1").model_dump(mode="json")
        action = brain.decide(obs)
        problems = validate_action(obs, action)
        if problems:
            rejected += 1
        res = apply_action(u, "P1", Action(**action))
        if not res.ok:
            rejected += 1
        kind = action.get("kind")
        target = (action.get("args") or {}).get("target")
        rows.append((sector, kind, target))
        if kind == "trade" and (action.get("args") or {}).get("side") == "sell":
            # realized profit is on the player's own trade log (seat-visible ledger).
            entry = p.trade_log[-1] if p.trade_log else None
            if entry and entry.get("day") == day and isinstance(entry.get("realized_profit"), int):
                trade_profit += int(entry["realized_profit"])
        peak = max(peak, p.credits)
        if p.sector_id == 1 and reached_day is None:
            reached_day, reached_turns = u.day, p.turns_today
    bounces = aba_bounces(rows)
    per_100 = (100.0 * bounces / len(rows)) if rows else 0.0
    return {
        "seed": seed, "credits": credits, "spawn": spawn, "day_end_sector": p.sector_id,
        "end_credits": p.credits, "peak_credits": peak, "trade_profit": trade_profit,
        "reached_stardock_day": reached_day, "reached_turns": reached_turns,
        "decisions": len(rows), "aba_bounces": bounces, "aba_per_100": per_100,
        "rejected": rejected,
    }


def run_n1(seeds: list[int], credits_list: list[int]) -> int:
    """N1 done-when: StarDock on day 1 at 100k and 20k; 20k trades a profit; ABA <= 2/100."""
    failures = 0
    for seed in seeds:
        for credits in credits_list:
            row = prove_n1_day(seed=seed, credits=credits)
            ok_sd = row["reached_stardock_day"] == 1
            ok_aba = row["aba_per_100"] <= 2.0
            ok_rej = row["rejected"] == 0
            ok_profit = True if credits >= 50_000 else row["trade_profit"] > 0
            ok = ok_sd and ok_aba and ok_rej and ok_profit
            failures += not ok
            print(
                f"{'OK ' if ok else 'FAIL'} seed={seed} start={credits} "
                f"stardock_day={row['reached_stardock_day']} turns={row['reached_turns']} "
                f"peak={row['peak_credits']} trade_profit={row['trade_profit']} "
                f"aba={row['aba_bounces']}/{row['decisions']} ({row['aba_per_100']:.2f}/100) "
                f"rejected={row['rejected']} end_sector={row['day_end_sector']}"
            )
    print(f"n1: {'PASS' if failures == 0 else f'{failures} FAIL'}")
    return 0 if failures == 0 else 1


def run_replay(path: Path, *, show_errors: int = 10) -> int:
    payloads = load_jsonl(path)
    report, _ = replay(SeatBrain(), payloads)
    print(report.summary())
    for i, e in report.errors[:show_errors]:
        print(f"  #{i}: {e}")
    ok = not report.errors and report.empire_loop_ok
    print(f"replay: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("synthetic")
    rec = sub.add_parser("record")
    rec.add_argument("--out", required=True)
    rec.add_argument("--seed", type=int, default=230923)
    rec.add_argument("--credits", type=int, default=120_000)
    rec.add_argument("--days", type=int, default=4)
    rep = sub.add_parser("replay")
    rep.add_argument("trace")
    n1 = sub.add_parser("n1", help="offline N1 proof: route to StarDock, earn first, frontier explore")
    n1.add_argument("--seeds", default="250925,20260925", help="comma-separated universe seeds")
    n1.add_argument("--credits", default="100000,20000", help="comma-separated starting credits")
    args = ap.parse_args()
    if args.cmd == "synthetic":
        return run_synthetic()
    if args.cmd == "record":
        res = record_offline(Path(args.out), seed=args.seed, credits=args.credits, days=args.days)
        print(res["report"].summary(), f"engine_rejections={res['rejected']}")
        print(f"wrote {args.out}")
        return 0 if res["rejected"] == 0 and res["report"].empire_loop_ok else 1
    if args.cmd == "n1":
        seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
        credits = [int(s) for s in args.credits.split(",") if s.strip()]
        return run_n1(seeds, credits)
    return run_replay(Path(args.trace))


if __name__ == "__main__":
    raise SystemExit(main())
