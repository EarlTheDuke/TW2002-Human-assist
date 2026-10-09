#!/usr/bin/env python3
"""cProfile one scripted day window for slice 68.

    python scripts/long_game_pace_profile.py --seed 250925 --warmup 18 --profile-days 2
"""

from __future__ import annotations

import argparse
import cProfile
import importlib.util
import io
import os
import pstats
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


def _load_rsm():
    spec = importlib.util.spec_from_file_location(
        "run_scripted_match_prof", ROOT / "scripts" / "run_scripted_match.py"
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

    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=250925)
    ap.add_argument("--warmup", type=int, default=18, help="days to run before profiling")
    ap.add_argument("--profile-days", type=int, default=2)
    ap.add_argument("--seats", default="N3,N3,N2,N2,N1,H")
    ap.add_argument("--out", default="artifacts/pace68/cprofile.txt")
    args = ap.parse_args()

    total_days = args.warmup + args.profile_days
    rsm = _load_rsm()
    seats = rsm.parse_seats(args.seats)

    # Warmup without profiler.
    t0 = time.perf_counter()
    print(f"warmup {args.warmup} days...", flush=True)
    rsm.run_match(seats=seats, seed=args.seed, days=args.warmup, ferrengi=True)
    print(f"warmup done in {time.perf_counter()-t0:.1f}s; profiling next {args.profile_days} days", flush=True)

    # Fresh match for the profile window (deterministic from seed, just longer).
    pr = cProfile.Profile()
    pr.enable()
    rsm.run_match(seats=seats, seed=args.seed, days=total_days, ferrengi=True)
    pr.disable()

    buf = io.StringIO()
    stats = pstats.Stats(pr, stream=buf).sort_stats("cumulative")
    stats.print_stats(60)
    text = buf.getvalue()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
