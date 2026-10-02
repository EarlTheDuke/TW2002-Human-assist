"""Keep the scenario lab importable. Two cells, three seeds, not the full grid."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _lab():
    path = ROOT / "scripts" / "planetary_scenario_lab.py"
    spec = importlib.util.spec_from_file_location("planetary_scenario_lab", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_two_cells_three_seeds_cover_a_free_capture_and_a_loss() -> None:
    lab = _lab()
    cells = lab.run_grid(
        planet_fighters=(0, 10000),
        planet_shields=(200,),
        attacker_fighters=(100,),
        seeds=3,
    )
    assert len(cells) == 2
    assert all(cell.n == 3 and cell.other == 0 for cell in cells)
    free, hopeless = cells
    assert free.planet_fighters == 0 and free.planet_shields == 200
    assert free.capture_rate == 1.0
    assert free.repelled_rate == 0.0
    assert free.attacker_destroyed_rate == 0.0
    assert hopeless.planet_fighters == 10000
    assert hopeless.attacker_destroyed_rate == 1.0
    assert hopeless.capture_rate == 0.0
    assert hopeless.mean_fighters_left == 0
