"""NOTE 110: queue constants are real, and the proposal script is a dry run."""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "docs/plans/live-twgs-test-queue-v1.md"
SHEET = ROOT / "docs/plans/live-twgs-run-sheet-v1.md"
TEMPLATE = ROOT / "docs/plans/live-twgs-results-template-v1.csv"
SCRIPT = ROOT / "scripts/live_queue_proposals.py"
CONSTANTS_PY = ROOT / "src/tw2k/engine/constants.py"

# GameConfig fields and doc paths. Not symbols on tw2k.engine.constants.
ALLOW = {
    "GameConfig.death_delay": (
        "Yes/No on tw2k.engine.models.GameConfig. TWGS v3 has no numeric maximum."
    ),
    "GameConfig.deaths_per_day": (
        "Whole-number allowance on tw2k.engine.models.GameConfig. The TEDIT maximum is unmeasured."
    ),
    "GameConfig.max_course_length": (
        "Field on tw2k.engine.models.GameConfig. A game's BIGBANG/TEDIT Maximum Course Length. Unset keeps the published sample."
    ),
    "docs/plans/ship-odds-exchange-v1.md": (
        "The ship-odds ruling is this doc. No engine constant and no new switch."
    ),
    "RULINGS_v311.md": "Cited only to say the file is not in the repo.",
    "docs/plans/live-twgs-run-sheet-v1.md": (
        "Pointer to the ordered run. Not a settled constant."
    ),
    "docs/plans/live-twgs-test-queue-v1.md": (
        "Pointer back to the queue this sheet orders. Not a settled constant."
    ),
    "docs/playtests/ports/ECONOMY_SCALE.md": (
        "NOTE 112 searched this playtest for a shield unit price. Not a constant."
    ),
    "docs/reference/tw2002/GAP_MAP.md": (
        "NOTE 112 cites gap rows 5.7 and 12.3. Not a constant."
    ),
    "docs/playtests/fedspace/STARDOCK_TAVERN.md": (
        "NOTE 115 cites the tavern playtest. Not a constant."
    ),
    "docs/playtests/ports/ROB_STEAL.md": (
        "NOTE 115 cites the rob and steal playtest. Not a constant."
    ),
    "docs/plans/gap-map-refresh-v6.md": (
        "NOTE 117 cites the still-open gap ranks. Not a constant."
    ),
}

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


def _queue_items(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        if re.match(r"^\|\s*-+", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0].lower() == "item":
            continue
        items.append(cells[0])
    return items


def _ticked(text: str) -> list[str]:
    return [tick.strip() for tick in re.findall(r"`([^`]+)`", text)]


def test_proposal_script_is_a_dry_run(tmp_path: Path) -> None:
    watched = (QUEUE, SHEET, TEMPLATE, SCRIPT, CONSTANTS_PY)
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
