"""The leak guard flags a CAPTURE_SLACK change and stays quiet when it is put back."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

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
            "-q", "--tb=line",
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

