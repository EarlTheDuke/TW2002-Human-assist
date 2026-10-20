#!/usr/bin/env python3
"""Run the regression suite with browser files in their own processes.

Unit tests share one pytest-xdist run. Each file that launches Chromium runs
as its own pytest process, so two browsers never share an interpreter. Those
tests take ports from free_port. A failure in any slice fails this command
and the failed names are printed.

``--repeat N`` reruns only those failures, up to N times. A failure that
passes on a rerun is printed as flaky. It is not added to the passed count,
and the command still exits 1 so the flake is not a green run.

    PYTHONPATH=src python scripts/run_regression.py
    PYTHONPATH=src python scripts/run_regression.py --list
    PYTHONPATH=src python scripts/run_regression.py --repeat 1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests._regression import execute, rerun_nodeids, split_files  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="print the split and exit")
    parser.add_argument("--work", default="/tmp/tw2k-regression", help="logs and junit xml")
    parser.add_argument(
        "--repeat",
        type=int,
        default=0,
        help="rerun only the failures this many times; a pass on rerun is flaky, not passed",
    )
    args = parser.parse_args()
    if args.repeat < 0:
        parser.error("--repeat must be >= 0")
    tests = ROOT / "tests"
    browser, unit = split_files(tests)
    if args.list:
        print(f"browser files {len(browser)} (one process each)")
        print(f"unit files {len(unit)} (pytest-xdist)")
        return 0
    report = execute(tests, Path(args.work))
    failed = list(report["failed_names"])
    flaky: list[str] = []
    seconds = float(report["seconds"])
    if args.repeat and failed:
        flaky, failed, rerun_seconds = rerun_nodeids(failed, Path(args.work) / "rerun", args.repeat)
        seconds += rerun_seconds
    print(
        f"files browser={report['browser_files']} unit={report['unit_files']} "
        f"workers browser={report['browser_workers']} unit={report['unit_workers']}"
    )
    counts = report["counts"]
    # A rerun pass stays out of `passed`. With --repeat, `failed` is what is still failing
    # (the first-run failures and errors, minus the ones that passed a rerun).
    if args.repeat:
        print(
            f"passed {report['passed']} failed {len(failed)} flaky {len(flaky)} "
            f"skipped {counts['skipped']} tests {counts['tests']} in {seconds:.1f}s"
        )
    else:
        print(
            f"passed {report['passed']} failed {counts['failures']} "
            f"errors {counts['errors']} skipped {counts['skipped']} "
            f"tests {counts['tests']} in {seconds:.1f}s"
        )
    print("slowest slices:")
    for name, row_seconds, code in report["rows"][:25]:
        mark = "ok" if code == 0 else "FAIL"
        print(f"  {row_seconds:7.1f}s {mark} {name}")
    if flaky:
        print("flaky:")
        for name in flaky:
            print(f"  {name}")
    if failed:
        print("failures:")
        for name in failed:
            print(f"  {name}")
    if args.repeat:
        return 1 if failed or flaky else 0
    return int(report["returncode"])


if __name__ == "__main__":
    raise SystemExit(main())
