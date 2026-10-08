"""Bots lay the armids they bought, except in a legacy game."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View


def _obs(*, here: int, adjacent: list[dict], mines: int = 5) -> dict:
    return {
        "self_id": "P1",
        "credits": 100_000,
        "day": 6,
        "sector": {"id": here, "planets": [], "occupants": ["P1"]},
        "ship": {"mines": {"armid": mines}, "class": "merchant_cruiser"},
        "legal_actions": [{
            "kind": "deploy_mines",
            "legal": True,
            "params": {
                "kind": {"choices": ["armid"]},
                "qty": {"max_by": {"armid": mines}},
            },
        }],
        "adjacent": adjacent,
        "owned_planets": [{"id": 1, "sector_id": 40, "citadel_level": 1}],
        "known_warps": {40: [here], here: [40]},
    }


def _brain() -> SeatBrain:
    brain = SeatBrain()
    brain.mem = SeatMemory(home_sector=14)
    return brain


def test_bw4_lays_at_the_gate_of_our_own_dead_end(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    obs = _obs(here=14, adjacent=[{"id": 40, "warps": 1}])
    action = _brain()._maybe_lay_armids(View(obs))
    assert action is not None and action["kind"] == "deploy_mines"
    assert action["args"]["kind"] == "armid" and action["args"]["qty"] == 5


def test_bw4_legacy_still_refuses_a_dead_end_gate(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "legacy")
    obs = _obs(here=14, adjacent=[{"id": 40, "warps": 1}])
    assert _brain()._maybe_lay_armids(View(obs)) is None


def _fighter_obs(*, here: int, adjacent: list[dict], fighters: int = 1000, already: int = 0) -> dict:
    sector: dict = {"id": here, "planets": [], "occupants": ["P1"]}
    if already:
        sector["fighter_group"] = {"owner_id": "P1", "count": already, "mode": "offensive"}
    return {
        "self_id": "P1",
        "credits": 100_000,
        "day": 6,
        "sector": sector,
        "ship": {"fighters": fighters, "class": "merchant_cruiser"},
        "legal_actions": [{
            "kind": "deploy_fighters",
            "legal": True,
            "params": {"qty": {"max": fighters}, "mode": {"choices": ["defensive", "offensive"]}},
        }],
        "adjacent": adjacent,
        "owned_planets": [{"id": 1, "sector_id": 40, "citadel_level": 1}],
        "known_warps": {40: [here], here: [40]},
    }


def test_bw5_parks_an_offensive_picket_at_our_dead_end_gate(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    obs = _fighter_obs(here=14, adjacent=[{"id": 40, "warps": 1}])
    action = _brain()._maybe_lay_pickets(View(obs))
    assert action is not None and action["kind"] == "deploy_fighters"
    assert action["args"]["mode"] == "offensive" and action["args"]["qty"] == 120
    assert "toll" not in action["args"]


def test_bw5_stops_once_the_picket_is_already_there(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    obs = _fighter_obs(here=14, adjacent=[{"id": 40, "warps": 1}], already=120)
    assert _brain()._maybe_lay_pickets(View(obs)) is None


def test_bw5_legacy_does_not_park_a_picket(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "legacy")
    obs = _fighter_obs(here=14, adjacent=[{"id": 40, "warps": 1}])
    assert _brain()._maybe_lay_pickets(View(obs)) is None


def test_bw4_does_not_mine_a_rival_dead_end_gate(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    obs = _obs(here=14, adjacent=[{"id": 428, "warps": 1, "seen": {"planets": [{"owner_id": "P3"}]}}])
    assert _brain()._maybe_lay_armids(View(obs)) is None
