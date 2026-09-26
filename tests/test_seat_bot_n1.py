"""Seat-bot N1 - route instead of search (docs/plans/2026-09-26-seat-bot-next.md).

Done-when (offline, seat-only observations):
* seed 250925 from sector 6 reaches StarDock on day 1 at 100k AND 20k starts;
* the 20k seat makes trade profit on day 1;
* ABA bounces <= 2 per 100 game turns.
Plus unit cases: StarDock plotted whether or not sector 1 is mapped, poor seats earn first,
plot rejection falls back to exploration, frontier-directed exploration, metric definitions.
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

from tw2k.agents.seat_acceptance import count_aba, route_metrics, synthetic_obs, validate_action
from tw2k.agents.seat_brain import SeatBrain

ROOT = Path(__file__).resolve().parents[1]


def _script():
    spec = importlib.util.spec_from_file_location("seat_brain_acceptance", ROOT / "scripts" / "seat_brain_acceptance.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Acceptance on the live seed
# ---------------------------------------------------------------------------


def test_n1_acceptance_seed_250925_both_starts(tmp_path: Path) -> None:
    code, results = _script().run_n1(tmp_path, days=1)
    by = {r["name"]: r for r in results}
    for name in ("250925-100k", "250925-20k"):
        r = by[name]
        assert r["stardock_day"] == 1, r
        assert r["aba_per_100_turns"] <= 2, r
        assert r["engine_rejections"] == 0 and r["validation_errors"] == 0, r
    assert by["250925-20k"]["day1_trade_profit"] > 0, by["250925-20k"]
    assert code == 0


# ---------------------------------------------------------------------------
# Route, don't search
# ---------------------------------------------------------------------------


def _unmapped(credits: int, ship_class: str = "cargotran", holds: int = 75, **extra):
    """Sector 4 of a small known pocket that does NOT include sector 1."""
    obs = synthetic_obs(sector=4, credits=credits, ship_class=ship_class, holds=holds)
    obs["known_warps"] = {"4": [3, 5], "3": [4, 30], "5": [4]}
    obs["known_sectors"] = [{"id": s} for s in (3, 4, 5)]
    obs["self_id"], obs["net_worth"] = "P1", credits
    obs.update(extra)
    return obs


def test_plots_stardock_when_unmapped_and_a_purchase_is_affordable() -> None:
    rich = SeatBrain().decide(_unmapped(40_000))
    assert rich["kind"] == "plot_course" and rich["args"] == {"target": 1, "execute": True}
    # A merchant cruiser that can afford the CargoTran goes for the hull, sector 1 unseen.
    hull = _unmapped(36_000, ship_class="merchant_cruiser", holds=20)
    a = SeatBrain().decide(hull)
    assert a["args"] == {"target": 1, "execute": True} and "CargoTran" in a["thought"]


def test_poor_seat_earns_before_stardock() -> None:
    poor = _unmapped(20_000, ship_class="merchant_cruiser", holds=20)
    a = SeatBrain().decide(poor)
    assert not (a["kind"] == "plot_course" and a["args"].get("target") == 1), a
    assert "earn" in a["thought"]
    # Once it has banked real trade profit, a hold expansion justifies the StarDock trip.
    earned = _unmapped(20_000, ship_class="merchant_cruiser", holds=20,
                       trade_summary={"total_trades": 2, "sells": 1, "total_profit_cr": 720})
    b = SeatBrain().decide(earned)
    assert b["args"] == {"target": 1, "execute": True} and "holds" in b["thought"]


def test_holds_bought_at_stardock_within_envelope_and_never_when_hull_affordable() -> None:
    obs = synthetic_obs(sector=1, credits=20_000, ship_class="merchant_cruiser", holds=20)
    obs["trade_summary"] = {"sells": 1, "total_profit_cr": 720}
    obs["legal_actions"] = [la for la in obs["legal_actions"] if la["kind"] != "buy_equip"]
    obs["legal_actions"].append({"kind": "buy_equip", "legal": True, "reason": None, "detail": "precise", "params": {
        "item": {"choices": ["holds", "fighters"], "unit_price_by": {"holds": 500, "fighters": 50}},
        "qty": {"min": 1, "max_by": {"holds": 40, "fighters": 400}}}})
    a = SeatBrain().decide(obs)
    assert a["kind"] == "buy_equip" and a["args"]["item"] == "holds" and 10 <= a["args"]["qty"] <= 40
    assert validate_action(obs, a) == []
    assert 20 + a["args"]["qty"] <= 60 and 20_000 - 500 * a["args"]["qty"] >= 6_000  # target + trade capital
    rich = copy.deepcopy(obs)
    rich["credits"] = 60_000
    assert SeatBrain().decide(rich)["args"].get("item") != "holds"  # buy the CargoTran path instead


def test_stardock_trip_implies_a_purchase_there_under_pressure() -> None:
    """Regression (seed 99): pressure lowered the trip threshold but not the purchase threshold,
    so a 30-32k seat shuttled StarDock <-> trade port forever buying nothing."""
    credits = 31_000  # between the pressured (30k) and calm (32k) first-genesis thresholds
    away = _unmapped(credits, rivals=[{"id": "P2", "name": "R", "alive": True, "net_worth": 90_000}])
    brain = SeatBrain()
    trip = brain.decide(away)
    assert trip["args"] == {"target": 1, "execute": True}
    dock = synthetic_obs(sector=1, credits=credits)
    dock["self_id"], dock["net_worth"] = "P1", credits
    dock["rivals"] = away["rivals"]
    buy = brain.decide(dock)
    assert buy["kind"] == "buy_equip" and buy["args"]["item"] == "genesis", buy
    # Without pressure neither threshold is met: no trip at all.
    calm = SeatBrain().decide(_unmapped(credits))
    assert calm["args"].get("target") != 1


def test_rejected_stardock_plot_falls_back_to_exploration() -> None:
    brain = SeatBrain()
    first = brain.decide(_unmapped(40_000))
    assert first["args"].get("target") == 1
    again = _unmapped(40_000, recent_events=[{"seq": 9, "kind": "warp_blocked", "actor_id": "P1",
                                              "summary": "no route", "facts": {"target": 1}}])
    second = brain.decide(again)
    assert second["args"].get("target") != 1 and second["kind"] in ("warp", "plot_course", "scan")


# ---------------------------------------------------------------------------
# Frontier-directed exploration
# ---------------------------------------------------------------------------


def _pocket(sector: int, known: dict[int, list[int]], warps: list[int]):
    obs = synthetic_obs(sector=5, credits=5_000)  # poor + no route: exploration rung
    obs["sector"] = {"id": sector, "warps_out": warps}
    obs["known_warps"] = {str(k): v for k, v in known.items()}
    obs["known_sectors"] = [{"id": k} for k in known]
    obs["legal_actions"] = [la for la in obs["legal_actions"] if la["kind"] != "warp"]
    obs["legal_actions"].append({"kind": "warp", "legal": True, "reason": None, "detail": "precise",
                                 "params": {"target": {"choices": warps}}})
    obs["self_id"] = "P1"
    return obs


def test_unvisited_neighbour_is_warped_to_directly() -> None:
    obs = _pocket(10, {10: [11, 12], 11: [10]}, [11, 12])
    a = SeatBrain().decide(obs)
    assert a["kind"] == "warp" and a["args"]["target"] == 12


def test_dead_end_plots_to_nearest_frontier_instead_of_bouncing() -> None:
    # 13 is a dead end; everything adjacent is visited; 12 has an unvisited neighbour 14.
    known = {13: [11], 11: [13, 12], 12: [11, 14]}
    a = SeatBrain().decide(_pocket(13, known, [11]))
    assert a["kind"] == "plot_course" and a["args"] == {"target": 14, "execute": True}, a


def test_explored_pocket_without_frontier_falls_back_to_least_visited() -> None:
    known = {20: [21], 21: [20]}
    a = SeatBrain().decide(_pocket(20, known, [21]))
    assert a["kind"] == "warp" and a["args"]["target"] == 21


# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------


def _o(sector, *, day=1, turns=100, credits=1000, cargo=None):
    return {"observation": {"sector": {"id": sector}, "day": day, "turns_remaining": turns, "credits": credits,
                            "ship": {"cargo": cargo or {}}, "trade_log": []}}


def test_aba_counts_and_idle_vs_trade_bounces() -> None:
    assert count_aba([1, 2, 1, 2, 3, 3, 4]) == 2
    wander = [_o(5, turns=100), _o(6, turns=97), _o(5, turns=94)]
    trade = [_o(5, turns=100), _o(6, turns=97, credits=500, cargo={"fuel_ore": 20}), _o(5, turns=94, credits=900)]
    mw, mt = route_metrics(wander), route_metrics(trade)
    assert mw["aba"] == 1 and mw["idle_aba"] == 1 and mw["game_turns"] == 6
    assert mt["aba"] == 1 and mt["idle_aba"] == 0
    assert mw["aba_per_100_turns"] == round(100 / 6, 2)
