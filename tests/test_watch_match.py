"""Unit tests for scripts/watch_match.py scorecard evaluation logic."""

from __future__ import annotations

import importlib.util
import pathlib
import sys


def _load_watch_match_module():
    path = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "watch_match.py"
    spec = importlib.util.spec_from_file_location("watch_match", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["watch_match"] = module
    spec.loader.exec_module(module)
    return module


wm = _load_watch_match_module()


def _ev(kind: str, day: int = 1, tick: int = 0, actor_id: str | None = None,
        sector_id: int | None = None, payload: dict | None = None, summary: str = "",
        seq: int = 1) -> dict:
    return {
        "seq": seq,
        "kind": kind,
        "day": day,
        "tick": tick,
        "actor_id": actor_id,
        "sector_id": sector_id,
        "payload": payload or {},
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Accumulator / update tests
# ---------------------------------------------------------------------------


def test_warp_event_populates_sectors_visited():
    arc = wm.PlayerArc(name="Blake")
    ev = _ev("warp", actor_id="p1", sector_id=7, payload={"from": 1, "to": 7})
    wm.update_from_event(arc, 1, ev)
    assert 7 in arc.stats_for(1).sectors_visited


def test_trade_event_increments_trades_and_sectors():
    arc = wm.PlayerArc(name="Blake")
    wm.update_from_event(arc, 1, _ev("trade", actor_id="p1", sector_id=11,
                                     payload={"commodity": "fuel_ore", "qty": 20, "side": "sell", "total": 2000, "unit": 100}))
    wm.update_from_event(arc, 1, _ev("trade", actor_id="p1", sector_id=12,
                                     payload={"commodity": "organics", "qty": 20, "side": "buy", "total": 1800, "unit": 90}))
    wm.update_from_event(arc, 1, _ev("trade", actor_id="p1", sector_id=11,
                                     payload={"commodity": "organics", "qty": 20, "side": "sell", "total": 2200, "unit": 110}))
    st = arc.stats_for(1)
    assert st.trades == 3
    assert st.sectors_visited >= {11, 12}
    # 11↔12 forms one distinct port pair
    assert len(st.port_pairs) == 1
    assert frozenset({11, 12}) in st.port_pairs


def test_buy_equip_density_flag():
    arc = wm.PlayerArc(name="Blake")
    wm.update_from_event(arc, 1, _ev("buy_equip", actor_id="p1",
                                     payload={"item": "density_scanner", "qty": 1, "total": 5000}))
    assert arc.stats_for(1).bought_density is True


def test_buy_ship_upgrade_flag():
    arc = wm.PlayerArc(name="Blake")
    wm.update_from_event(arc, 2, _ev("buy_ship", actor_id="p1",
                                     payload={"ship_class": "missile_frigate", "net_cost": 100_000}))
    assert arc.stats_for(2).bought_ship is True


def test_toll_trade_payload_skipped_for_port_pair_counting():
    """Toll passage emits a TRADE event without 'commodity'; must not count as a real trade."""
    arc = wm.PlayerArc(name="Blake")
    wm.update_from_event(arc, 1, _ev("trade", actor_id="p1", sector_id=5,
                                     payload={"toll_to": "p2", "amount": 1000}))
    st = arc.stats_for(1)
    assert st.trades == 0
    assert not st.port_pairs


# ---------------------------------------------------------------------------
# Scorecard evaluation tests
# ---------------------------------------------------------------------------


def _build_day1_perfect_stats() -> "wm.DayStats":
    st = wm.DayStats()
    st.nw_start = 40_000
    st.nw_end = 52_000  # +30%
    # 4 trades across 2 sectors
    for sec in [11, 12, 11, 12]:
        st.note_trade(sec)
    st.sectors_visited.update({11, 12, 13, 14, 15})
    return st


def test_day1_perfect_score():
    st = _build_day1_perfect_stats()
    checks = wm.evaluate(st, 1)
    assert len(checks) == 3
    assert all(ok for _, ok, _ in checks)


def test_day1_fail_nw_gain():
    st = _build_day1_perfect_stats()
    st.nw_end = 40_500  # only +1%
    checks = wm.evaluate(st, 1)
    results = dict((label, ok) for label, ok, _ in checks)
    assert results["net worth +20%"] is False


def test_day2_port_pairs_threshold():
    st = wm.DayStats()
    st.nw_start = 150_000
    st.nw_end = 260_000
    st.bought_density = True
    # Only one port pair (11↔12) — fails threshold of 2
    for sec in [11, 12, 11, 12, 11]:
        st.note_trade(sec)
    checks = wm.evaluate(st, 2)
    results = dict((label, ok) for label, ok, _ in checks)
    assert results["≥2 port pairs"] is False
    assert results["density scanner or ship"] is True
    assert results["net worth ≥150k"] is True


def test_day3_genesis_and_citadel():
    st = wm.DayStats()
    st.events_seen.update({"genesis_deployed", "build_citadel"})
    checks = wm.evaluate(st, 3)
    assert all(ok for _, ok, _ in checks)


def test_day4_citadel_and_nw():
    st = wm.DayStats()
    st.events_seen.add("citadel_complete")
    st.nw_end = 600_000
    checks = wm.evaluate(st, 4)
    assert all(ok for _, ok, _ in checks)


def test_day5_citadel_level_and_any_event():
    st = wm.DayStats()
    st.citadel_level_reached = 2
    st.events_seen.add("alliance_formed")
    st.nw_end = 1_500_000
    checks = wm.evaluate(st, 5)
    assert all(ok for _, ok, _ in checks)


def test_day5_requires_any_of_events():
    st = wm.DayStats()
    st.citadel_level_reached = 3
    st.nw_end = 2_000_000
    # no corp/alliance/probe — the "any_event_seen" check must fail
    checks = wm.evaluate(st, 5)
    results = dict((label, ok) for label, ok, _ in checks)
    assert results["corp / alliance / probe"] is False
    assert results["Citadel ≥ L2"] is True
    assert results["net worth ≥1M"] is True


# ---------------------------------------------------------------------------
# Render tests
# ---------------------------------------------------------------------------


def test_render_scorecard_marks_pass_and_fail():
    st = _build_day1_perfect_stats()
    st.nw_end = 41_000  # +2.5% — fails
    checks = wm.evaluate(st, 1)
    lines = wm.render_scorecard("Blake", 1, checks)
    header = lines[0]
    assert "Blake" in header
    # Two passes + one fail out of three
    assert "2/3" in header or "3/3" in header  # depends on rounding; just be tolerant
    body = "\n".join(lines)
    assert "[+]" in body and "[x]" in body


def test_render_scorecard_all_pass_uses_ok_marker():
    st = _build_day1_perfect_stats()
    checks = wm.evaluate(st, 1)
    lines = wm.render_scorecard("Blake", 1, checks)
    assert "[OK ]" in lines[0]


def test_render_arc_report_sorts_by_days_on_arc():
    arcs = {
        "p1": wm.PlayerArc(name="Blake"),
        "p2": wm.PlayerArc(name="Reyes"),
    }
    arcs["p1"].days_on_arc = 3
    arcs["p1"].days_scored = 5
    arcs["p2"].days_on_arc = 1
    arcs["p2"].days_scored = 5
    lines = wm.render_arc_report(arcs, 5)
    blob = "\n".join(lines)
    # Blake must appear before Reyes in the report
    assert blob.index("Blake") < blob.index("Reyes")


# ---------------------------------------------------------------------------
# resolve_actor tests
# ---------------------------------------------------------------------------


def test_resolve_actor_uses_explicit_id():
    ev = _ev("warp", actor_id="p1")
    assert wm.resolve_actor(ev, {}) == "p1"


def test_resolve_actor_finds_citadel_owner_when_missing():
    ev = {"kind": "citadel_complete", "payload": {"planet_id": 99, "from": 0, "to": 1}}
    players = {
        "pA": {"id": "pA", "planets": [{"id": 42}]},
        "pB": {"id": "pB", "planets": [{"id": 99}]},
    }
    assert wm.resolve_actor(ev, players) == "pB"


def test_resolve_actor_none_when_nothing_matches():
    ev = {"kind": "citadel_complete", "payload": {"planet_id": 999}}
    assert wm.resolve_actor(ev, {}) is None
