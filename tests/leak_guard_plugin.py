"""Leak guard.

tests/conftest.py loads this plugin and sets TW2K_LEAK_GUARD=fail when that
variable is unset, so a test that leaves a watched global changed fails with
its node id.

While later tests in the same module are still going to run, the comparison is
the value before this test's function fixtures. A module fixture may hold a
different value for the whole module, and a function fixture such as
monkeypatch may change a value and put it back. When the module is finished,
the comparison is the session start.

    pytest -p tests.leak_guard_plugin

pytest -p imports a module name. A filesystem path
(`-p tests/leak_guard_plugin.py`) raises ImportError.

Without conftest (`--noconftest`) and without TW2K_LEAK_GUARD, the plugin
reports and does not fail. TW2K_LEAK_GUARD=warn prints the line and lets the
test pass. TW2K_LEAK_GUARD=off skips the check. TW2K_LEAK_GUARD_LOG, when set,
is a file that receives the same lines.

Watched values: every UPPER_CASE global in the engine modules below, and every
CAPTURE_, COMBAT_, SHIP_, FLEET_, or V311_ environment variable. Comparison is
repr, so a dict or list mutated in place counts.
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
_before_function: dict[str, dict[str, str]] = {}


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
    """Keys whose repr differs from baseline, including new and missing keys."""
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


def leak_message(nodeid: str, baseline: dict[str, str] | None = None, *, module_done: bool = False) -> str | None:
    rows = drifts(baseline)
    if not rows:
        return None
    lines = [f"LEAK {nodeid}"]
    if module_done:
        lines.append("  still different after the module finished")
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


def _module_done(item, nextitem) -> bool:
    if nextitem is None:
        return True
    return getattr(nextitem, "module", None) is not getattr(item, "module", None)


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    """Remember the globals before the first function fixture changes them."""
    node = getattr(request, "node", None)
    nodeid = getattr(node, "nodeid", None)
    if nodeid and fixturedef.scope == "function" and nodeid not in _before_function:
        _before_function[nodeid] = snapshot()
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    yield
    # No function fixture: the module fixtures have already run and the body has not.
    _before_function.setdefault(item.nodeid, snapshot())


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item, nextitem):
    yield
    mode = os.environ.get("TW2K_LEAK_GUARD", "report")
    module_done = _module_done(item, nextitem)
    baseline = None if module_done else _before_function.get(item.nodeid)
    _before_function.pop(item.nodeid, None)
    if mode == "off" or (not module_done and baseline is None):
        return
    message = leak_message(item.nodeid, baseline, module_done=module_done)
    if not message:
        return
    _emit(item, message)
    if mode == "fail":
        pytest.fail(message, pytrace=False)
