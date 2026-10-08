"""A hit at home sends the seat back, inside eight hops."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View


def _chain(length: int) -> dict[int, list[int]]:
    warps: dict[int, list[int]] = {}
    for n in range(1, length + 1):
        nxt = n + 1
        warps[n] = [nxt]
        warps[nxt] = [n]
    return warps


def _obs(*, hops: int, hit: bool) -> dict:
    home = hops + 1
    return {
        "self_id": "P1",
        "day": 6,
        "sector": {"id": 1, "warps_out": [2]},
        "ship": {"class": "merchant_cruiser", "fighters": 1000},
        "known_warps": _chain(hops),
        "owned_planets": [{"id": 4, "sector_id": home, "citadel_level": 2}],
        "recent_events": (
            [{"kind": "land_planet", "actor_id": "P2", "sector_id": home, "payload": {"planet_id": 4}}]
            if hit else []
        ),
        "legal_actions": [{
            "kind": "warp",
            "legal": True,
            "params": {"target": {"choices": [2]}},
        }],
    }


def _brain(home: int) -> SeatBrain:
    brain = SeatBrain()
    brain.mem = SeatMemory(home_sector=home)
    return brain


def test_a_hit_within_eight_hops_warps_toward_home(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    action = _brain(4)._defend_home(View(_obs(hops=3, hit=True)))
    assert action is not None and action["kind"] == "warp"
    assert action["args"]["target"] == 2


def test_a_far_home_a_quiet_day_and_legacy_stay_put(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    assert _brain(11)._defend_home(View(_obs(hops=10, hit=True))) is None
    assert _brain(4)._defend_home(View(_obs(hops=3, hit=False))) is None
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "legacy")
    assert _brain(4)._defend_home(View(_obs(hops=3, hit=True))) is None


def test_arriving_home_acks_the_hit(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    brain = _brain(4)
    away = _obs(hops=3, hit=True)
    away["recent_events"][0]["seq"] = 4
    assert brain._defend_home(View(away)) is not None
    home = _obs(hops=3, hit=True)
    home["recent_events"][0]["seq"] = 4
    home["sector"]["id"] = 4
    assert brain._defend_home(View(home)) is None
    assert brain.mem is not None and brain.mem.war_home_seq == 4
    assert brain._defend_home(View(away)) is None
    again = _obs(hops=3, hit=True)
    again["recent_events"][0]["seq"] = 9
    assert brain._defend_home(View(again)) is not None
