#!/usr/bin/env python3
"""Run the quick test set: unit files minus the slow ones, pins included.

Meant for every change; target is a few minutes. The full suite stays
scripts/run_regression.py. A quick file that took SLOW_SECONDS or more is
printed so it can move to SLOW_UNIT_FILES in tests/_tiers.py.

    PYTHONPATH=src python scripts/run_quick.py
    PYTHONPATH=src python scripts/run_quick.py --list
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests._regression import failed_names, read_junit, run_pytest  # noqa: E402
from tests._tiers import SLOW_SECONDS, is_pin_file, quick_files  # noqa: E402


def file_seconds(junit: Path) -> Counter[str]:
    seconds: Counter[str] = Counter()
    if not junit.is_file():
        return seconds
    for case in ET.parse(junit).getroot().iter("testcase"):
        module = case.attrib.get("classname", "").split(".")
        name = next((part for part in module if part.startswith("test_")), "?")
        seconds[name + ".py"] += float(case.attrib.get("time", 0) or 0)
    return seconds


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="print the quick files and exit")
    parser.add_argument("--work", default="/tmp/tw2k-quick", help="log and junit xml")
    parser.add_argument("--workers", type=int, default=min(12, os.cpu_count() or 1))
    args = parser.parse_args()
    files = quick_files(ROOT / "tests")
    if args.list:
        pins = [path for path in files if is_pin_file(path)]
        print(f"quick files {len(files)} (pins {len(pins)})")
        for path in files:
            print(f"  {path.relative_to(ROOT).as_posix()}")
        return 0
    work = Path(args.work)
    junit = work / "quick.xml"
    started = time.monotonic()
    code = run_pytest(
        ["-n", str(args.workers), "-p", "no:cacheprovider", *(path.relative_to(ROOT).as_posix() for path in files)],
        log=work / "quick.log",
        junit=junit,
    )
    seconds = time.monotonic() - started
    counts = read_junit(junit)
    print(
        f"quick files {len(files)} passed {counts['tests'] - counts['failures'] - counts['errors'] - counts['skipped']} "
        f"failed {counts['failures']} errors {counts['errors']} skipped {counts['skipped']} in {seconds:.1f}s"
    )
    slow = [(name, s) for name, s in file_seconds(junit).most_common() if s >= SLOW_SECONDS]
    slow = [(name, s) for name, s in slow if not is_pin_file(Path(name))]
    if slow:
        print(f"quick files at {SLOW_SECONDS:.0f}s or more (move to SLOW_UNIT_FILES in tests/_tiers.py):")
        for name, s in slow:
            print(f"  {s:7.1f}s {name}")
    failed = failed_names(junit)
    if failed:
        print("failed:")
        for name in failed:
            print(f"  {name}")
    print(f"log {work / 'quick.log'}")
    return 1 if code != 0 or failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
