"""Coverage gate for the planet invariant fuzz."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "planet_invariants_fuzz.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_planet_invariants_fuzz_coverage_passes() -> None:
    proc = _run("--seeds", "3")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "planet_invariants_fuzz: PASS" in proc.stdout
    assert "coverage:" not in proc.stdout
    assert proc.stdout.count("| pass |") == 3


def test_planet_invariants_fuzz_coverage_fails_when_a_kind_is_zero() -> None:
    proc = _run("--seeds", "1", "--force-zero", "attack")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "coverage: attack never succeeded" in proc.stdout
    assert "planet_invariants_fuzz: FAIL" in proc.stdout
