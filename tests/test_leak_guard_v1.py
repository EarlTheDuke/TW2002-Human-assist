"""The leak guard names a test that leaves CAPTURE_SLACK changed."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import tw2k.engine.constants as K

from tests._cu_host import acquire_info_mode, release_info_mode

ROOT = Path(__file__).resolve().parents[1]

_LEAK = """
import tw2k.engine.constants as K

def test_leaks():
    K.CAPTURE_SLACK = int(K.CAPTURE_SLACK) + 1
"""

_RESTORE = """
import tw2k.engine.constants as K

def test_restores():
    old = K.CAPTURE_SLACK
    K.CAPTURE_SLACK = int(old) + 1
    K.CAPTURE_SLACK = old
"""

_MODULE_HOLDS = """
import pytest
import tw2k.engine.constants as K

@pytest.fixture(scope="module")
def held():
    old = K.CAPTURE_SLACK
    K.CAPTURE_SLACK = int(old) + 1
    try:
        yield
    finally:
        K.CAPTURE_SLACK = old

def test_during(held):
    assert int(K.CAPTURE_SLACK) == 1

def test_during_too(held):
    assert int(K.CAPTURE_SLACK) == 1
"""

_MODULE_LEAKS = """
import pytest
import tw2k.engine.constants as K

@pytest.fixture(scope="module")
def held():
    K.CAPTURE_SLACK = int(K.CAPTURE_SLACK) + 1
    yield

def test_first(held):
    assert int(K.CAPTURE_SLACK) == 1

def test_last(held):
    assert int(K.CAPTURE_SLACK) == 1
"""


def _run(tmp_path: Path, body: str, *, fail: bool = False, plugin: str = "tests.leak_guard_plugin"):
    path = tmp_path / "test_sample_leak.py"
    path.write_text(body, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src"), str(ROOT), env.get("PYTHONPATH", "")]
    )
    env.pop("TW2K_LEAK_GUARD_LOG", None)
    if fail:
        env["TW2K_LEAK_GUARD"] = "fail"
    else:
        env.pop("TW2K_LEAK_GUARD", None)
    return subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "-p", plugin,
            "-p", "no:cacheprovider",
            "--noconftest",
            # The report line is written in teardown. Captured stdout drops it,
            # so the parent would not see LEAK.
            "-q", "-s", "--tb=line",
            str(path),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_unrestored_capture_slack_is_reported(tmp_path):
    done = _run(tmp_path, _LEAK)
    out = done.stdout + done.stderr
    assert done.returncode == 0, out
    assert "LEAK" in out
    assert "test_leaks" in out
    assert "tw2k.engine.constants.CAPTURE_SLACK: 0 -> 1" in out


def test_unrestored_capture_slack_fails_when_asked(tmp_path):
    done = _run(tmp_path, _LEAK, fail=True)
    out = done.stdout + done.stderr
    assert done.returncode != 0, out
    assert "LEAK" in out
    assert "CAPTURE_SLACK" in out


def test_restored_capture_slack_stays_quiet(tmp_path):
    done = _run(tmp_path, _RESTORE)
    out = done.stdout + done.stderr
    assert done.returncode == 0, out
    assert "LEAK" not in out
    assert "CAPTURE_SLACK" not in out


_MONKEY = """
import pytest
import tw2k.engine.constants as K

def test_patched(monkeypatch):
    monkeypatch.setattr(K, "CAPTURE_SLACK", int(K.CAPTURE_SLACK) + 1)
    assert int(K.CAPTURE_SLACK) == 1

def test_after(monkeypatch):
    assert int(K.CAPTURE_SLACK) == 0
"""

_BODY_BESIDE_MONKEY = """
import pytest
import tw2k.engine.constants as K

def test_body(monkeypatch):
    monkeypatch.setattr(K, "INFO_MODE", "legacy")
    K.CAPTURE_SLACK = int(K.CAPTURE_SLACK) + 1

def test_after():
    assert True
"""


def test_monkeypatch_restore_stays_quiet(tmp_path):
    done = _run(tmp_path, _MONKEY, fail=True)
    out = done.stdout + done.stderr
    assert done.returncode == 0, out
    assert "LEAK" not in out


def test_body_change_beside_monkeypatch_is_reported(tmp_path):
    done = _run(tmp_path, _BODY_BESIDE_MONKEY, fail=True)
    out = done.stdout + done.stderr
    assert done.returncode != 0, out
    assert "LEAK" in out
    assert "test_body" in out
    assert "CAPTURE_SLACK" in out


def test_module_fixture_that_restores_stays_quiet(tmp_path):
    done = _run(tmp_path, _MODULE_HOLDS, fail=True)
    out = done.stdout + done.stderr
    assert done.returncode == 0, out
    assert "LEAK" not in out


def test_module_fixture_that_does_not_restore_fails_the_last_test(tmp_path):
    done = _run(tmp_path, _MODULE_LEAKS, fail=True)
    out = done.stdout + done.stderr
    assert done.returncode != 0, out
    assert "LEAK" in out
    assert "test_last" in out
    assert "still different after the module finished" in out
    assert "CAPTURE_SLACK" in out


def test_nested_hosts_restore_the_outer_info_mode():
    old = K.INFO_MODE
    outer = type("Hold", (), {})()
    inner = type("Hold", (), {})()
    try:
        K.INFO_MODE = "tw2002"
        acquire_info_mode(outer)
        assert K.INFO_MODE == "legacy"
        acquire_info_mode(inner)
        assert K.INFO_MODE == "legacy"
        release_info_mode(outer)
        assert K.INFO_MODE == "legacy"
        release_info_mode(inner)
        assert K.INFO_MODE == "tw2002"
    finally:
        release_info_mode(inner)
        release_info_mode(outer)
        K.INFO_MODE = old
