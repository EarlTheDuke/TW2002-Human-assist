"""Opt-in leak guard. Not loaded unless pytest is given -p.

    pytest -p tests.leak_guard_plugin
    pytest -p tests/leak_guard_plugin.py

After each test, compare every UPPER_CASE global in the engine modules below,
and every CAPTURE_, COMBAT_, SHIP_, FLEET_, or V311_ environment variable, with
the session-start snapshot. Comparison is repr, so a dict or list mutated in
place counts. TW2K_LEAK_GUARD=fail turns a drift into a failure of that test.
TW2K_LEAK_GUARD_LOG, when set, is a file that receives the same lines.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

MODULES = (
    "tw2k.engine.constants",
    "tw2k.engine.combat",
    "tw2k.engine.capture",
    "tw2k.engine.runner",
)
ENV_PREFIXES = ("CAPTURE_", "COMBAT_", "SHIP_", "FLEET_", "V311_")

_baseline: dict[str, str] | None = None


def snapshot() -> dict[str, str]:
    """repr of the watched globals and environment keys."""
    found: dict[str, str] = {}
    for name in MODULES:
        module = importlib.import_module(name)
        for key, value in vars(module).items():
            if key.isupper():
                found[f"{name}.{key}"] = repr(value)
    for key, value in os.environ.items():
        if key.startswith(ENV_PREFIXES):
            found[f"env.{key}"] = repr(value)
    return found


def drifts(baseline: dict[str, str] | None = None) -> list[tuple[str, str | None, str | None]]:
    """Keys whose repr differs from the session start, including new and missing keys."""
    start = _baseline if baseline is None else baseline
    if start is None:
        return []
    current = snapshot()
    rows: list[tuple[str, str | None, str | None]] = []
    for key in sorted(set(start) | set(current)):
        before = start.get(key)
        after = current.get(key)
        if before != after:
            rows.append((key, before, after))
    return rows


def leak_message(nodeid: str, baseline: dict[str, str] | None = None) -> str | None:
    rows = drifts(baseline)
    if not rows:
        return None
    lines = [f"LEAK {nodeid}"]
    for key, before, after in rows:
        lines.append(f"  {key}: {before} -> {after}")
    return "\n".join(lines)


def pytest_sessionstart(session) -> None:
    global _baseline
    _baseline = snapshot()


def _emit(item, message: str) -> None:
    reporter = item.config.pluginmanager.getplugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(message)
    else:
        print(message, flush=True)
    path = os.environ.get("TW2K_LEAK_GUARD_LOG")
    if path:
        with Path(path).open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item, nextitem):
    yield
    message = leak_message(item.nodeid)
    if not message:
        return
    _emit(item, message)
    if os.environ.get("TW2K_LEAK_GUARD") == "fail":
        pytest.fail(message, pytrace=False)
