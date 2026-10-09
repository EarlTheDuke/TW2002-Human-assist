#!/usr/bin/env python3
"""Wall-clock per day for a scripted match (slice 68 long-game-pace-v1).

    python scripts/long_game_pace_lab.py --seed 250925 --days 60 --json pace.json

Uses the same seats and engine path as run_scripted_match. Prints day, wall_s,
events, planets, and a running ratio vs day 5.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


def _load_run_match():
    spec = importlib.util.spec_from_file_location(
        "run_scripted_match_pace", ROOT / "scripts" / "run_scripted_match.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    if os.environ.get("PYTHONHASHSEED") != "0":
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = "0"
        return subprocess.call([sys.executable, *sys.argv], env=env)

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=250925)
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--seats", default="N3,N3,N2,N2,N1,H")
    ap.add_argument("--size", type=int, default=1000)
    ap.add_argument("--turns-per-day", type=int, default=1000)
    ap.add_argument("--credits", type=int, default=20_000)
    ap.add_argument("--json", dest="json_out", help="write day timings here")
    args = ap.parse_args()

    import tw2k.engine as eng
    import tw2k.engine.runner as runner_mod

    real_tick = runner_mod.tick_day
    timings: list[dict] = []
    day_started = time.perf_counter()
    current_day = {"n": 1}

    def timed_tick(u, *a, **kw):
        nonlocal day_started
        now = time.perf_counter()
        row = {
            "day": int(current_day["n"]),
            "wall_s": round(now - day_started, 3),
            "events": len(getattr(u, "events", []) or []),
            "planets": len(getattr(u, "planets", {}) or {}),
        }
        timings.append(row)
        print(
            f"day {row['day']:3d}  wall_s={row['wall_s']:7.2f}  "
            f"events={row['events']:7d}  planets={row['planets']:4d}",
            flush=True,
        )
        day_started = time.perf_counter()
        out = real_tick(u, *a, **kw)
        current_day["n"] = int(getattr(u, "day", current_day["n"]))
        return out

    runner_mod.tick_day = timed_tick  # type: ignore[assignment]
    eng.tick_day = timed_tick  # type: ignore[assignment]

    rsm = _load_run_match()
    seats = rsm.parse_seats(args.seats)
    t0 = time.perf_counter()
    result = rsm.run_match(
        seats=seats,
        seed=args.seed,
        days=args.days,
        universe_size=args.size,
        turns_per_day=args.turns_per_day,
        credits=args.credits,
        ferrengi=True,
    )
    total = time.perf_counter() - t0

    day5 = next((row["wall_s"] for row in timings if row["day"] == 5), None)
    print(f"seed={args.seed} days={args.days} total_s={total:.1f} rows={len(timings)}")
    print("day wall_s events planets vs_d5")
    for row in timings:
        ratio = (row["wall_s"] / day5) if day5 and day5 > 0 else None
        vs = f"{ratio:.2f}x" if ratio is not None else "-"
        print(f"{row['day']:3d} {row['wall_s']:7.2f} {row['events']:7d} {row['planets']:7d} {vs}")
    late_day = min(60, args.days)
    late = next((row for row in timings if row["day"] == late_day), timings[-1] if timings else None)
    if day5 and late:
        print(
            f"bar_check day5={day5:.2f}s day{late['day']}={late['wall_s']:.2f}s "
            f"ratio={late['wall_s']/day5:.2f}x limit=1.50x "
            f"{'PASS' if late['wall_s'] <= day5 * 1.5 else 'FAIL'}"
        )

    payload = {
        "seed": args.seed,
        "days": args.days,
        "seats": args.seats,
        "total_s": round(total, 3),
        "day5_s": day5,
        "timings": timings,
        "digest": result.get("digest") if isinstance(result, dict) else None,
        "ranking": result.get("ranking") if isinstance(result, dict) else None,
    }
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
