"""Split the suite so each browser file keeps its own process.

Unit files share a pytest-xdist run. A file that launches Chromium, or asks
for the browser fixture, runs as its own pytest process. free_port inside
those tests keeps the listeners apart. Failures stay in the log and in the
process exit code.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_BROWSER = re.compile(
    r"playwright|sync_playwright|chromium\.launch|"
    r"def test_\w+\([^)]*\bbrowser\b",
    re.S,
)


def is_browser_file(path: Path) -> bool:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return _BROWSER.search(text) is not None


def split_files(tests_dir: Path) -> tuple[list[Path], list[Path]]:
    files = sorted(Path(tests_dir).glob("test_*.py"))
    browser = [path for path in files if is_browser_file(path)]
    unit = [path for path in files if path not in set(browser)]
    return browser, unit


def _env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    previous = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src if not previous else src + os.pathsep + previous
    env.setdefault("TW2K_LEAK_GUARD", "fail")
    env["PYTHONUNBUFFERED"] = "1"
    # The runner chooses workers itself. An ambient -n would nest another xdist.
    env.pop("PYTEST_ADDOPTS", None)
    return env


def run_pytest(args: list[str], *, log: Path, junit: Path) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    junit.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "pytest", "-q", "--tb=line",
        f"--junitxml={junit}",
        *args,
    ]
    with log.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(cmd, cwd=str(ROOT), env=_env(), stdout=handle, stderr=subprocess.STDOUT)
    return int(proc.returncode)


def read_junit(path: Path) -> dict[str, int]:
    if not path.is_file():
        return {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in totals:
            totals[key] += int(suite.attrib.get(key, 0))
    return totals


def add_counts(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    return {key: int(left.get(key, 0)) + int(right.get(key, 0)) for key in ("tests", "failures", "errors", "skipped")}


def failed_names(path: Path) -> list[str]:
    if not path.is_file():
        return []
    root = ET.parse(path).getroot()
    names = []
    for case in root.iter("testcase"):
        if case.find("failure") is not None or case.find("error") is not None:
            names.append(f"{case.attrib.get('classname', '')}::{case.attrib.get('name', '')}")
    return names


def _cpus() -> int:
    return max(1, os.cpu_count() or 1)


def execute(tests_dir: Path, work: Path, *, unit_workers: int | None = None, browser_workers: int | None = None) -> dict:
    """Run the suite. Browser files are one pytest process each."""
    browser, unit = split_files(tests_dir)
    work.mkdir(parents=True, exist_ok=True)
    cpus = _cpus()
    unit_workers = unit_workers if unit_workers is not None else max(1, cpus // 2)
    browser_workers = browser_workers if browser_workers is not None else max(1, cpus - 1)
    started = time.time()
    rows: list[tuple[str, float, int]] = []

    def unit_job() -> int:
        if not unit:
            return 0
        t0 = time.time()
        code = run_pytest(
            ["-n", str(unit_workers), "--dist", "loadscope", "--durations=30",
             *[str(path) for path in unit]],
            log=work / "unit.log",
            junit=work / "unit.xml",
        )
        rows.append(("unit", time.time() - t0, code))
        print(f"slice unit {time.time() - t0:.1f}s exit {code}", flush=True)
        return code

    def browser_job(path: Path) -> int:
        t0 = time.time()
        code = run_pytest(
            ["--durations=5", str(path)],
            log=work / f"{path.stem}.log",
            junit=work / f"{path.stem}.xml",
        )
        elapsed = time.time() - t0
        rows.append((path.name, elapsed, code))
        if code != 0 or elapsed >= 30:
            print(f"slice {path.name} {elapsed:.1f}s exit {code}", flush=True)
        return code

    unit_code = 0
    browser_codes: list[int] = []
    with ThreadPoolExecutor(max_workers=browser_workers + 1) as pool:
        unit_future = pool.submit(unit_job)
        browser_futures = [pool.submit(browser_job, path) for path in browser]
        unit_code = unit_future.result()
        for future in as_completed(browser_futures):
            browser_codes.append(future.result())

    counts = read_junit(work / "unit.xml")
    names = failed_names(work / "unit.xml")
    for path in browser:
        junit = work / f"{path.stem}.xml"
        counts = add_counts(counts, read_junit(junit))
        names.extend(failed_names(junit))
    passed = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    return {
        "seconds": time.time() - started,
        "browser_files": len(browser),
        "unit_files": len(unit),
        "unit_workers": unit_workers,
        "browser_workers": browser_workers,
        "returncode": 0 if unit_code == 0 and all(code == 0 for code in browser_codes) else 1,
        "counts": counts,
        "passed": passed,
        "failed_names": names,
        "rows": sorted(rows, key=lambda row: row[1], reverse=True),
    }
