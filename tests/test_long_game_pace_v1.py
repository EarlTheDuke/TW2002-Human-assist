"""Slice 68: nav graph is built once per decide, not once per BFS."""

from __future__ import annotations

from tw2k.agents.seat_brain import SeatBrain, View


def _obs() -> dict:
    return {
        "self_id": "P1",
        "day": 3,
        "credits": 50_000,
        "sector": {"id": 1, "warps_out": [2, 3]},
        "ship": {"class": "merchant_cruiser", "holds": 20, "fighters": 0},
        "known_warps": {"1": [2, 3], "2": [1, 4], "3": [1], "4": [2]},
        "legal_actions": [{"kind": "warp", "legal": True, "params": {"target": {"choices": [2, 3]}}}],
        "scratchpad": {},
    }


def test_lp1_nav_graph_cached_per_view() -> None:
    brain = SeatBrain(feed_organics=False, value_allocator=False)
    v = View(_obs())
    g1 = brain._nav_graph(v)
    g2 = brain._nav_graph(v)
    assert g1 is g2
    assert g1[1] == (2, 3)


def test_lp2_bfs_reuses_nav() -> None:
    brain = SeatBrain(feed_organics=False, value_allocator=False)
    v = View(_obs())
    d1 = brain._distances_from(v, 1)
    d2 = brain._distances_from(v, 4)
    assert d1[4] == 2 and d2[1] == 2
    assert brain._path_cache(v)["nav"] is brain._nav_graph(v)
