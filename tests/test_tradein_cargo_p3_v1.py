"""Playtest 3 leftovers (e): say whether cargo transfers on a ship trade-in.

The engine (runner._handle_buy_ship) moves cargo to the new hull in both
profiles and drops what does not fit, equipment kept first. These tests pin
that rule and the words that now tell the player.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.models import Commodity, Player, Ship, ShipClass

ROOT = Path(__file__).resolve().parents[1]


def _buy(monkeypatch, profile, cargo, new="scout_marauder"):
    monkeypatch.setattr(K, "V311_PROFILE", profile)
    u = generate_universe(GameConfig(seed=11, universe_size=80, max_days=3, turns_per_day=500, enable_ferrengi=False))
    ship = Ship(ship_class=ShipClass("merchant_cruiser"), holds=80, fighters=0)
    for c, n in cargo.items():
        ship.cargo[c] = n
    p = Player(id="P9", name="P9", ship=ship, credits=2_000_000)
    p.sector_id = 1
    p.turns_per_day = 1000
    p.turns_today = 0
    u.players["P9"] = p
    u.sectors[1].occupant_ids.append("P9")
    r = apply_action(u, "P9", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": new}))
    assert r.ok, r.error
    return p.ship


@pytest.mark.parametrize("profile", ["legacy", "v311"])
def test_cargo_moves_to_the_new_ship(monkeypatch, profile):
    ship = _buy(monkeypatch, profile, {Commodity.FUEL_ORE: 5, Commodity.EQUIPMENT: 3}, new="cargotran")
    assert ship.cargo[Commodity.FUEL_ORE] == 5
    assert ship.cargo[Commodity.EQUIPMENT] == 3


@pytest.mark.parametrize("profile", ["legacy", "v311"])
def test_cargo_past_the_new_holds_is_lost_equipment_first(monkeypatch, profile):
    ship = _buy(monkeypatch, profile, {Commodity.EQUIPMENT: 70, Commodity.ORGANICS: 10})
    holds = int(ship.holds)
    assert holds < 70
    assert ship.cargo[Commodity.EQUIPMENT] == holds
    assert ship.cargo.get(Commodity.ORGANICS, 0) == 0


def test_yard_confirm_and_manual_say_so():
    js = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")
    assert "moves to the new ship" in js and "the rest is lost (equipment is kept first" in js
    from tw2k.public import manual

    src = Path(manual.__file__).read_text(encoding="utf-8")
    assert "Cargo moves to the new ship in both modes" in src
