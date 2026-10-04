"""The money-scale report prints and leaves the spawn rate alone."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tw2k.engine import constants as K

ROOT = Path(__file__).resolve().parents[1]


def test_economy_scale_report_prints_and_changes_nothing() -> None:
    before = K.PORT_SPAWN_PROBABILITY
    script = ROOT / "scripts" / "economy_scale_report.py"
    text = script.read_text(encoding="utf-8")
    assert "open(" not in text
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    out = proc.stdout
    assert "economy_scale_report" in out
    assert "| Commodity |" in out
    assert "| Pair |" in out
    assert "| Ship |" in out
    assert "| Density |" in out
    assert "spawn probability left at 0.65" in out
    assert K.PORT_SPAWN_PROBABILITY == before == 0.65
    assert K.FIGHTER_COST == 50
    assert K.COMMODITY_BASE_PRICE["equipment"] == 719
