"""Three fixed fuzz seeds keep the planet rules intact."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_planet_invariants_fuzz_three_seeds() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "planet_invariants_fuzz.py"), "--seeds", "3"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "planet_invariants_fuzz: PASS" in proc.stdout
    assert "| xfail |" not in proc.stdout
    assert proc.stdout.count("| pass |") == 3
