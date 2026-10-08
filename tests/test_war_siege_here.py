"""A seat lands a siege in its own sector only when the gates clear."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View


def _obs(*, owner_alignment: int = -100, day: int = 6, fedspace: bool = False,
         orphan: bool = False, ticker: str = "", turns_left: int = 40,
         citadel: int = 2, fuel: int = 0) -> dict:
    planet = {
        "id": 9, "owner_id": "P2", "owner_alignment": owner_alignment,
        "citadel_level": citadel, "fighters": 0, "shields": 0,
        "corp_ticker": ticker, "stockpile": {"fuel_ore": fuel},
    }
    obs = {
        "self_id": "P1",
        "alignment": 100,
        "credits": 100_000,
        "day": day,
        "turns_left": turns_left,
        "corp_ticker": ticker,
        "sector": {"id": 50, "is_fedspace": fedspace, "planets": [planet], "occupants": ["P1"]},
        "ship": {"fighters": 500, "class": "merchant_cruiser"},
        "legal_actions": [{
            "kind": "land_planet",
            "legal": True,
            "params": {"planet_id": {"choices": [9]}},
        }],
    }
    if orphan:
        obs["orphaned_planets"] = [dict(planet)]
    return obs


def _brain(**kw) -> SeatBrain:
    brain = SeatBrain(**kw)
    brain.mem = SeatMemory()
    return brain


def test_n3_lands_on_an_evil_planet_in_this_sector(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    brain = _brain()
    action = brain._siege_here(View(_obs()))
    assert action is not None and action["kind"] == "land_planet"
    assert action["args"]["planet_id"] == 9
    assert brain.mem is not None and brain.mem.war_land_tries == 1


def test_n3_reads_evil_from_the_rival_side(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    obs = _obs()
    del obs["sector"]["planets"][0]["owner_alignment"]
    obs["rivals"] = [{"id": "P2", "side": "evil"}]
    action = _brain()._siege_here(View(obs))
    assert action is not None and action["args"]["planet_id"] == 9


def test_one_siege_target_a_day(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    brain = _brain()
    assert brain._siege_here(View(_obs())) is not None
    other = _obs()
    other["sector"]["planets"][0]["id"] = 10
    other["legal_actions"][0]["params"]["planet_id"]["choices"] = [10]
    assert brain._siege_here(View(other)) is None


def test_legacy_n1_good_fedspace_orphan_early_and_low_turns_do_not_land(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    assert _brain(value_allocator=False, feed_organics=False)._siege_here(View(_obs())) is None
    assert _brain()._siege_here(View(_obs(owner_alignment=50))) is None
    assert _brain()._siege_here(View(_obs(fedspace=True))) is None
    assert _brain()._siege_here(View(_obs(orphan=True))) is None
    assert _brain()._siege_here(View(_obs(day=4))) is None
    assert _brain()._siege_here(View(_obs(turns_left=10))) is None
    assert _brain()._siege_here(View(_obs(citadel=6, fuel=800))) is None
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "legacy")
    assert _brain()._siege_here(View(_obs())) is None
