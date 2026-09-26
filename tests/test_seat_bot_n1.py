"""Seat-bot N1 - route to StarDock instead of searching for it.

Done-when (docs prompt / 2026-09-26 plan):
* plot_course execute target 1 when CargoTran or genesis is affordable, mapped or not
* a poor seat earns on known ports before that trip
* exploration plots through known warps to the nearest frontier (not ABA local warps)
* seed 250925, spawn sector 6: StarDock on day 1 at 100k and 20k; 20k shows trade profit;
  ABA bounces <= 2 per 100 turns

Offline only. The brain is fed build_observation for its own seat.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from tw2k.agents.seat_acceptance import aba_bounces, synthetic_obs, validate_action
from tw2k.agents.seat_brain import SeatBrain

ROOT = Path(__file__).resolve().parents[1]


def _load_acceptance():
    path = ROOT / "scripts" / "seat_brain_acceptance.py"
    spec = importlib.util.spec_from_file_location("seat_brain_acceptance_n1", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _frontier_obs(*, credits: int, here: int = 11) -> dict:
    """Dead-end 11. The unvisited neighbour (13) hangs off sector 12, two known hops away."""
    obs = synthetic_obs(sector=4, credits=credits, ship_class="cargotran")
    obs["sector"] = {"id": here, "warps_out": [10], "port": None, "is_fedspace": False}
    obs["known_warps"] = {"10": [11, 12], "11": [10], "12": [10, 13]}
    obs["known_sectors"] = [{"id": s} for s in (10, 11, 12)]
    obs["known_ports"] = []
    las = []
    for la in obs["legal_actions"]:
        if la["kind"] == "warp":
            la = {**la, "params": {"target": {"type": "int", "required": True, "choices": [10]}}}
        las.append(la)
    obs["legal_actions"] = las
    return obs


def test_affordable_stardock_plots_target_1_even_when_unmapped() -> None:
    obs = _frontier_obs(credits=100_000)
    a = SeatBrain().decide(obs)
    assert validate_action(obs, a) == []
    assert a["kind"] == "plot_course" and a["args"] == {"target": 1, "execute": True}
    assert "1" in a["thought"]


def test_poor_seat_does_not_hunt_stardock_before_it_can_pay() -> None:
    obs = _frontier_obs(credits=20_000)
    a = SeatBrain().decide(obs)
    assert validate_action(obs, a) == []
    assert not (a["kind"] == "plot_course" and a["args"].get("target") == 1)
    # Frontier is sector 12 (unvisited neighbour 13), not the greedy bounce back to 10.
    assert a["kind"] == "plot_course" and a["args"] == {"target": 12, "execute": True}


def test_rejected_stardock_plot_falls_through_to_frontier() -> None:
    brain = SeatBrain()
    first = _frontier_obs(credits=100_000)
    assert brain.decide(first)["args"].get("target") == 1
    brain.mem.banned["plot_course:1"] = brain.mem.decisions + 5
    obs = _frontier_obs(credits=100_000)
    a = brain.decide(obs)
    assert validate_action(obs, a) == []
    assert a["args"].get("target") != 1
    assert a["kind"] == "plot_course" and a["args"]["target"] == 12
    assert "rejected" in a["thought"]


def test_aba_counter_ignores_trade_plots_and_counts_warp_reversals() -> None:
    rows = [
        (6, "warp", 132),
        (132, "trade", None),
        (132, "plot_course", 264),  # autopilot breaks the chain
        (264, "warp", 132),
        (132, "warp", 264),  # reversal of the previous warp
        (264, "warp", 110),
    ]
    assert aba_bounces(rows) == 1


def test_n1_day1_stardock_on_playtest_seed() -> None:
    """Seed 250925 spawn 6, plus a second map the same rules clear offline."""
    mod = _load_acceptance()
    for seed in (250925, 20260925):
        for credits in (100_000, 20_000):
            row = mod.prove_n1_day(seed=seed, credits=credits)
            assert row["rejected"] == 0, row
            assert row["reached_stardock_day"] == 1, row
            assert row["aba_per_100"] <= 2.0, row
            if credits == 20_000:
                assert row["trade_profit"] > 0, row
                assert row["peak_credits"] > credits, row
