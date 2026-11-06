"""NOTE 110: queue constants are real, and the proposal script is a dry run."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/live_queue_proposals.py"
CONSTANTS_PY = ROOT / "src/tw2k/engine/constants.py"

COLUMNS = (
    "item_id",
    "constant",
    "current_value",
    "observed_text",
    "observed_value",
    "date",
    "tester",
    "notes",
)


def test_proposal_script_is_a_dry_run(tmp_path: Path) -> None:
    watched = (SCRIPT, CONSTANTS_PY)
    before = {path: path.read_bytes() for path in watched}
    sample = tmp_path / "sample.csv"
    with sample.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "item_id": "n97-haggle-good",
                "constant": "HAGGLE_EXP_GOOD",
                "current_value": "+1",
                "observed_text": "experience rose by 3",
                "observed_value": "3",
                "date": "2026-10-19",
                "tester": "sample",
                "notes": "Good haggle experience",
            }
        )
        writer.writerow(
            {
                "item_id": "n98-port-capture",
                "constant": "none until a screen shows a capture",
                "current_value": "not implemented",
                "observed_text": "",
                "observed_value": "",
                "date": "",
                "tester": "",
                "notes": "Port capture",
            }
        )
    sample_bytes = sample.read_bytes()
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(sample)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "n98-port-capture" not in proc.stdout
    assert "HAGGLE_EXP_GOOD" in proc.stdout
    assert "current value: 1" in proc.stdout
    assert "proposed value: 3" in proc.stdout
    assert "UNVERIFIED" in proc.stdout
    assert "writes nothing" in proc.stdout.lower()
    assert list(tmp_path.iterdir()) == [sample]
    assert sample.read_bytes() == sample_bytes
    for path, data in before.items():
        assert path.read_bytes() == data

    help_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert help_proc.returncode == 0, help_proc.stderr
    lowered = help_proc.stdout.lower()
    assert "dry run" in lowered
    assert "writes nothing" in lowered
