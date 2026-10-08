"""Bots lay the armids they bought, except in a legacy game."""

from __future__ import annotations

from pathlib import Path

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


def test_bw4_armids(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    obs = _obs(here=14, adjacent=[{"id": 40, "warps": 1}])
    action = _brain()._maybe_lay_armids(View(obs))
    assert action is not None and action["kind"] == "deploy_mines"
    assert action["args"]["kind"] == "armid" and action["args"]["qty"] == 5


def test_bw6_ownership(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    solo = _brain()._maybe_lay_armids(View(_obs(here=14, adjacent=[{"id": 40, "warps": 1}])))
    assert solo is not None and "ownership" not in solo["args"]
    monkeypatch.setattr(K, "bot_corp_policy", lambda: "pair")
    obs = _obs(here=14, adjacent=[{"id": 40, "warps": 1}])
    obs["legal_actions"][0]["params"]["ownership"] = {"choices": ["personal", "corporate"]}
    corp = _brain()._maybe_lay_armids(View(obs))
    assert corp is not None and corp["args"]["ownership"] == "corporate"


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


def test_bw5_pickets(monkeypatch) -> None:
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


def _landed_obs(planet: dict, legal: list[dict]) -> dict:
    return {
        "self_id": "P1",
        "credits": 100_000,
        "net_worth": 100_000,
        "day": 6,
        "planet_landed": planet["id"],
        "sector": {"id": 40, "planets": [], "occupants": ["P1"]},
        "ship": {"fighters": 10_000, "shields": 500, "class": "merchant_cruiser"},
        "legal_actions": legal,
        "owned_planets": [planet],
        "known_warps": {},
    }


def _planet(**over: object) -> dict:
    row = {
        "id": 1,
        "sector_id": 40,
        "citadel_level": 3,
        "fighters": 0,
        "shields": 0,
        "military_reaction_pct": 0,
        "quasar_sector_pct": 0,
        "quasar_atm_pct": 0,
        "stockpile": {"fuel_ore": 5_000},
        "origin": "genesis",
    }
    row.update(over)
    return row


def test_bw8_reaction(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    legal = [{"kind": "set_military_reaction", "legal": True, "params": {"planet_id": {"choices": [1]}, "pct": {}}}]
    first = _brain()._war_while_landed(View(_landed_obs(_planet(citadel_level=2), legal)), _planet(citadel_level=2))
    assert first is not None and first["args"] == {"planet_id": 1, "pct": 20}
    again = _brain()._war_while_landed(
        View(_landed_obs(_planet(citadel_level=2, military_reaction_pct=20), legal)),
        _planet(citadel_level=2, military_reaction_pct=20),
    )
    assert again is None or again["kind"] != "set_military_reaction"


def test_bw9_quasar(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    legal = [
        {"kind": "set_quasar_sector", "legal": True, "params": {}},
        {"kind": "set_quasar_atm", "legal": True, "params": {}},
    ]
    ready = _planet(military_reaction_pct=20)
    sector = _brain()._war_while_landed(View(_landed_obs(ready, legal)), ready)
    assert sector is not None and sector["kind"] == "set_quasar_sector"
    assert sector["args"]["pct"] == 30
    planet = _planet(military_reaction_pct=20, quasar_sector_pct=30)
    atm = _brain()._war_while_landed(View(_landed_obs(planet, legal)), planet)
    assert atm is not None and atm["kind"] == "set_quasar_atm" and atm["args"]["pct"] == 60


def test_bw7_stock(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    planet = _planet(military_reaction_pct=20, quasar_sector_pct=30, quasar_atm_pct=60)
    legal = [{
        "kind": "deposit_planet_defense",
        "legal": True,
        "params": {"kind": {"choices": ["fighters", "shields"]}, "qty": {"max_by": {"fighters": 10_000, "shields": 50}}},
    }]
    action = _brain()._war_while_landed(View(_landed_obs(planet, legal)), planet)
    assert action is not None and action["kind"] == "deposit_planet_defense"
    assert action["args"]["kind"] == "fighters" and action["args"]["qty"] > 0


def test_bw7_legacy_does_not_stock(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "legacy")
    planet = _planet()
    legal = [{"kind": "set_military_reaction", "legal": True, "params": {}}]
    assert _brain()._war_while_landed(View(_landed_obs(planet, legal)), planet) is None


def test_bw4_does_not_mine_a_rival_dead_end_gate(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_WAR_MODE", "tw2002")
    monkeypatch.setattr(K, "BOT_WAR_POLICY", "full")
    obs = _obs(here=14, adjacent=[{"id": 428, "warps": 1, "seen": {"planets": [{"owner_id": "P3"}]}}])
    assert _brain()._maybe_lay_armids(View(obs)) is None


def test_bw30_docs() -> None:
    root = Path(__file__).resolve().parents[1]
    needle = "docs/playtests/bots/BOTS_USE_PLANET_WARFARE.md"
    gap = (root / "docs/reference/tw2002/GAP_MAP.md").read_text(encoding="utf-8")
    growth = (root / "docs/playtests/bots/BOT_GROWTH.md").read_text(encoding="utf-8")
    assert needle in gap and needle in growth
