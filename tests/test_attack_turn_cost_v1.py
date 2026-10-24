"""NOTE 112. A ship attack spends 0 turns on the v3.11 card and 5 in a stored game.

Capture: docs/playtests/twgs-live/attack-turn-cost-ven.txt
Only a Merchant Cruiser was measured. This is not a per-hull table.
Port attacks, photons, and disruptors stay on TURN_COST["attack"].
"""

from __future__ import annotations

from pathlib import Path

import tw2k.engine.constants as K
from tests.test_ship_combat_core_v1 import _act, _challenge, _duel, _la
from tw2k.engine.actions import ActionKind
from tw2k.engine.models import ShipClass

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "docs" / "playtests" / "twgs-live" / "attack-turn-cost-ven.txt"
PROFILE = ROOT / "docs" / "plans" / "v311-profile-v1.md"
VALUE = 'VALUE: 0 turns per ship attack (engine TURN_COST["attack"]=5 is wrong; should be 0)'


def test_capture_value_line() -> None:
    lines = CAPTURE.read_text(encoding="utf-8").splitlines()
    assert VALUE in lines
    assert K.TURN_COST["attack"] == 5
    assert K.ATTACK_TURN_MODE == "legacy"
    assert K.attack_turn_live() is False
    assert K.attack_turn_cost() == 5


def test_profile_row_is_228() -> None:
    assert K.V311_PROFILE_HELPERS["attack_turn_live"][0] == "ATTACK_TURN_MODE"
    text = PROFILE.read_text(encoding="utf-8")
    assert "| 228 | `ATTACK_TURN_MODE` | `attack_turn_live` |" in text
    assert "docs/playtests/twgs-live/attack-turn-cost-ven.txt" in text
    assert "## The switch set (156 helpers)" in text


def _ship_attack(seed: int):
    universe, attacker, defender, _c, _sid = _duel(seed, ShipClass.MERCHANT_CRUISER)
    attacker.ship.fighters = 400
    defender.ship.fighters = 400
    defender.ship.shields = 0
    return universe, attacker, defender


def test_stored_game_spends_5(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    monkeypatch.setattr(K, "ATTACK_TURN_MODE", "1")
    assert K.attack_turn_live() is False
    universe, attacker, defender = _ship_attack(11201)
    listed = _la(universe, attacker.id, "attack")
    assert listed.turn_cost == 5
    before = attacker.turns_today
    res = _act(universe, attacker.id, ActionKind.ATTACK, target=defender.id, qty=10)
    assert res.ok and res.turns_spent == 5
    assert attacker.turns_today == before + 5
    assert K.TURN_COST["attack"] == 5

    short, a2, d2 = _ship_attack(11202)
    a2.turns_today = a2.turns_per_day - 4
    refused = _act(short, a2.id, ActionKind.ATTACK, target=d2.id, qty=10)
    assert not refused.ok and "out of turns" in (refused.error or "")
    assert a2.turns_today == a2.turns_per_day - 4
    assert a2.ship.fighters == 400


def test_live_card_spends_0_and_the_profile_does_the_same(monkeypatch) -> None:
    monkeypatch.setattr(K, "ATTACK_TURN_MODE", "live")
    assert K.V311_PROFILE == "legacy"
    assert K.attack_turn_live() is True
    assert K.attack_turn_cost() == 0
    assert K.TURN_COST["attack"] == 5
    universe, attacker, defender = _ship_attack(11203)
    attacker.ship.ship_class = ShipClass.MISSILE_FRIGATE
    attacker.ship.photon_missiles = 1
    listed = _la(universe, attacker.id, "attack")
    photon = _la(universe, attacker.id, "photon_missile")
    assert listed.turn_cost == 0
    assert photon.turn_cost == 5
    attacker.turns_today = attacker.turns_per_day
    before_fighters = attacker.ship.fighters
    res = _act(universe, attacker.id, ActionKind.ATTACK, target=defender.id, qty=10)
    assert res.ok and res.turns_spent == 0
    assert attacker.turns_today == attacker.turns_per_day
    assert attacker.ship.fighters == before_fighters - 10

    monkeypatch.setattr(K, "ATTACK_TURN_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.ATTACK_TURN_MODE == "legacy"
    assert K.attack_turn_cost() == 0
    again, a2, d2 = _ship_attack(11204)
    a2.turns_today = 229
    spent = _act(again, a2.id, ActionKind.ATTACK, target=d2.id, qty=10)
    assert spent.ok and spent.turns_spent == 0
    assert a2.turns_today == 229


def test_fighter_attack_is_0_on_and_5_off(monkeypatch) -> None:
    universe, _owner, ship, _home, _there = _challenge(11205, count=10)
    before = ship.turns_today
    res = _act(universe, ship.id, ActionKind.ATTACK, target="fighters", qty=10)
    assert res.ok and res.turns_spent == 5
    assert ship.turns_today == before + 5

    monkeypatch.setattr(K, "ATTACK_TURN_MODE", "live")
    live, _owner2, ship2, _home2, there2 = _challenge(11206, count=10)
    start = ship2.turns_today
    fighters = ship2.ship.fighters
    hit = _act(live, ship2.id, ActionKind.ATTACK, target="fighters", qty=10)
    assert hit.ok and hit.turns_spent == 0
    assert ship2.turns_today == start
    assert ship2.ship.fighters < fighters
    assert live.sectors[there2].fighters is None or live.sectors[there2].fighters.count < 10


def test_live_profile_does_not_turn_attack_turns_on(monkeypatch) -> None:
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.v311_profile() is False
    assert K.attack_turn_live() is False
    assert K.attack_turn_cost() == 5
