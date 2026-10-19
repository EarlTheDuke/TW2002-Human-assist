"""COMMANDER NOTE 75 item 2: two fresh v3.11 runs of the same seed agree."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_scripted_match.py"


def _run(hashseed: str, dest: Path) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT)
    env["PYTHONHASHSEED"] = hashseed
    env["V311_PROFILE"] = "v311"
    env.pop("TW2002_HAGGLE_LIVE", None)
    env.pop("COCKPIT_LAYOUT", None)
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--seats", "N3,N2,N1,H", "--seed", "250925",
         "--days", "3", "--action-digest", "--json", str(dest)],
        cwd=str(ROOT), env=env, check=True, capture_output=True, text=True,
    )
    # The script applies V311_PROFILE from the environment. Without that line the run is the profile-off game.
    assert "V311_PROFILE v311" in done.stdout
    return json.loads(dest.read_text(encoding="utf-8"))


def test_two_fresh_v311_runs_match(tmp_path: Path) -> None:
    """Seed 250925 for 3 days. Different hash seeds still give the same digest and net worth."""
    first = _run("1", tmp_path / "a.json")
    second = _run("2", tmp_path / "b.json")
    assert first["action_digest"] == second["action_digest"]
    for pid, row in first["players"].items():
        assert row["net_worth"] == second["players"][pid]["net_worth"]
        assert row["rejected_engine"] == second["players"][pid]["rejected_engine"]
        assert row["rejected_validate"] == second["players"][pid]["rejected_validate"]
