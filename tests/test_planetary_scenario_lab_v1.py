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


def test_two_cells_three_seeds_cover_a_shield_repel_and_a_fighter_loss() -> None:
    lab = _lab()
    repelled = lab.run_grid(
        planet_fighters=(0,),
        planet_shields=(200,),
        attacker_fighters=(100,),
        seeds=3,
    )[0]
    destroyed = lab.run_grid(
        planet_fighters=(10000,),
        planet_shields=(0,),
        attacker_fighters=(99,),
        seeds=3,
    )[0]
    assert repelled.n == 3 and repelled.other == 0
    assert repelled.repelled_rate == 1.0
    assert repelled.capture_rate == 0.0
    assert destroyed.n == 3 and destroyed.other == 0
    assert destroyed.attacker_destroyed_rate == 1.0
    assert destroyed.capture_rate == 0.0
    assert destroyed.mean_fighters_left == 0
