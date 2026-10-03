"""The planetary lab runner exits 0 when every scenario still matches."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_planetary_lab_all_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "planetary_lab_all.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "planetary_lab_all: PASS" in proc.stdout
    assert "| fail |" not in proc.stdout
