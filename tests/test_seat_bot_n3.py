"""Seat-bot N3 — value per turn after the first world.

Done-when (offline, fogged observation only):
* ferry turns under 40% of turns spent in a 10-day replay
* day-10 net worth at least 145k on seed 250925
* rejected stays 0
* seeds 230923, 99, and 31 stay within 85% of the fixed ladder and keep organics
* seeds 250925 and 20260925 are held at the measured starve (planet 32 and
  planet 30) and the measured net worth. The price scale did that. The brain
  was not retuned. See ECONOMY_SCALE_APPLY.md.

The brain is fed build_observation for its own seat. No /state.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_acceptance():
    path = ROOT / "scripts" / "seat_brain_acceptance.py"
    spec = importlib.util.spec_from_file_location("seat_brain_acceptance_n3", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_ferry_turn_counts_the_empty_stardock_leg_and_a_colonist_move() -> None:
    mod = _load_acceptance()
    assert mod._is_ferry_action({"kind": "plot_course", "args": {"target": 1}, "thought": "ferry: StarDock"}, 0)
    assert mod._is_ferry_action({"kind": "buy_equip", "args": {"item": "colonists", "qty": 75}, "thought": "load"}, 0)
    assert mod._is_ferry_action({"kind": "plot_course", "args": {"target": 32}, "thought": "haul home"}, 40)
    assert not mod._is_ferry_action({"kind": "plot_course", "args": {"target": 12}, "thought": "trade pair"}, 0)
    assert not mod._is_ferry_action({"kind": "trade", "args": {"side": "sell"}, "thought": "sell equipment"}, 0)


def test_n3_day10_ferry_and_net_worth() -> None:
    """Five seeds, ten days. Seed 250925 must clear 145k with ferry under 40%."""
    mod = _load_acceptance()
    assert mod.run_n3(list(mod.N2_SEEDS)) == 0
