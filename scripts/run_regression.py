#!/usr/bin/env python3
"""Run the regression suite with browser files in their own processes.

Unit tests share one pytest-xdist run. Each file that launches Chromium runs
as its own pytest process, so two browsers never share an interpreter. Those
tests take ports from free_port. A failure in any slice fails this command
and the failed names are printed.

    PYTHONPATH=src python scripts/run_regression.py
    PYTHONPATH=src python scripts/run_regression.py --list
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests._regression import execute, split_files  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="print the split and exit")
    parser.add_argument("--work", default="/tmp/tw2k-regression", help="logs and junit xml")
    args = parser.parse_args()
    tests = ROOT / "tests"
    browser, unit = split_files(tests)
    if args.list:
        print(f"browser files {len(browser)} (one process each)")
        print(f"unit files {len(unit)} (pytest-xdist)")
        return 0
    report = execute(tests, Path(args.work))
    print(
        f"files browser={report['browser_files']} unit={report['unit_files']} "
        f"workers browser={report['browser_workers']} unit={report['unit_workers']}"
    )
    counts = report["counts"]
    print(
        f"passed {report['passed']} failed {counts['failures']} "
        f"errors {counts['errors']} skipped {counts['skipped']} "
        f"tests {counts['tests']} in {report['seconds']:.1f}s"
    )
    print("slowest slices:")
    for name, seconds, code in report["rows"][:25]:
        mark = "ok" if code == 0 else "FAIL"
        print(f"  {seconds:7.1f}s {mark} {name}")
    if report["failed_names"]:
        print("failures:")
        for name in report["failed_names"]:
            print(f"  {name}")
    return int(report["returncode"])


if __name__ == "__main__":
    raise SystemExit(main())
