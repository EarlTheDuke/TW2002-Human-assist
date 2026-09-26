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
                   max_actions: int = 4000, seat: str = "P1", universe_size: int = 150,
                   turns_per_day: int | None = None, spawn: int = 1) -> dict:
    """Offline engine run. The brain only sees build_observation(u, seat); every payload is recorded."""
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.actions import Action
    from tw2k.engine.models import Player
    from tw2k.engine.observation import build_observation
    from tw2k.engine.runner import apply_action, tick_day

    u = generate_universe(GameConfig(seed=seed, universe_size=universe_size, max_days=days + 2,
                                     turns_per_day=turns_per_day or 250, starting_credits=credits,
                                     enable_ferrengi=False, enable_planets=True))
    for pid, name, sid in ((seat, "Seat", spawn), ("P9", "Idle", 1)):
        extra = {"turns_per_day": turns_per_day} if turns_per_day else {}
        p = Player(id=pid, name=name, agent_kind="external", sector_id=sid, credits=credits, **extra)
        u.players[pid] = p
        u.sectors[sid].occupant_ids.append(pid)
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


N1_SCENARIOS = (
    # qwen2-kimi3-grok live settings: seed 250925, 1000 sectors, 120 turns/day, P6 spawned in sector 6.
    {"name": "250925-100k", "seed": 250925, "credits": 100_000, "spawn": 6},
    {"name": "250925-20k", "seed": 250925, "credits": 20_000, "spawn": 6},
)


def run_n1(tmp_dir: Path, *, days: int = 1) -> tuple[int, list[dict]]:
    """N1 'route instead of search' proof on the live seed; metrics from the seat's own observations."""
    from tw2k.agents.seat_acceptance import route_metrics

    tmp_dir.mkdir(parents=True, exist_ok=True)
    results = []
    failures = 0
    for sc in N1_SCENARIOS:
        trace = tmp_dir / f"n1_{sc['name']}.jsonl"
        rec = record_offline(trace, seed=sc["seed"], credits=sc["credits"], days=days, universe_size=1000,
                             turns_per_day=120, spawn=sc["spawn"])
        m = route_metrics(load_jsonl(trace))
        m.update(name=sc["name"], engine_rejections=rec["rejected"], validation_errors=len(rec["report"].errors))
        ok = (m["stardock_day"] == 1 and m["aba_per_100_turns"] <= 2 and m["engine_rejections"] == 0
              and m["validation_errors"] == 0 and (sc["credits"] > 20_000 or m["day1_trade_profit"] > 0))
        m["pass"] = ok
        failures += not ok
        results.append(m)
        print(("PASS " if ok else "FAIL ") + json.dumps(m))
    return (0 if failures == 0 else 1), results


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
    n1 = sub.add_parser("n1", help="N1 route-instead-of-search proof on seed 250925 (spawn 6, 100k and 20k)")
    n1.add_argument("--out-dir", default=str(Path.cwd() / ".n1_traces"))
    n1.add_argument("--days", type=int, default=1)
    args = ap.parse_args()
    if args.cmd == "synthetic":
        return run_synthetic()
    if args.cmd == "n1":
        return run_n1(Path(args.out_dir), days=args.days)[0]
    if args.cmd == "record":
        res = record_offline(Path(args.out), seed=args.seed, credits=args.credits, days=args.days)
        print(res["report"].summary(), f"engine_rejections={res['rejected']}")
        print(f"wrote {args.out}")
        return 0 if res["rejected"] == 0 and res["report"].empire_loop_ok else 1
    return run_replay(Path(args.trace))


if __name__ == "__main__":
    raise SystemExit(main())
