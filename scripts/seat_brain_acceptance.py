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
    args = ap.parse_args()
    if args.cmd == "synthetic":
        return run_synthetic()
    if args.cmd == "record":
        res = record_offline(Path(args.out), seed=args.seed, credits=args.credits, days=args.days)
        print(res["report"].summary(), f"engine_rejections={res['rejected']}")
        print(f"wrote {args.out}")
        return 0 if res["rejected"] == 0 and res["report"].empire_loop_ok else 1
    return run_replay(Path(args.trace))


if __name__ == "__main__":
    raise SystemExit(main())
