"""NOTE 177, then R10 A.

6.10 gains PLANET_BLOW_ALIGN_MODE, row 214: blowing a planet costs 50 alignment (Bible).
That switch is legacy by default and turns on under V311_PROFILE=v311, not "1".
8.1 is NOTE 164's FERRENGI_ODDS_MODE (row 200, the Bible chart); the stored FERRSPEC
table stays the legacy value.
10.1 keeps CFS_CEO_USE_MODE for Gypsy's use-rule. R10 A does not select it:
only the C.E.O. buys a FlagShip, and a member may board. The profile leaves it off.
"""
from __future__ import annotations

from types import SimpleNamespace

import tw2k.engine.constants as K
from tests.test_fedspace_police_v1 import _world
from tw2k.engine.corpships import board_block
from tw2k.engine.models import Planet, PlanetClass, ShipClass
from tw2k.engine.runner import _remove_planet


def _flagship_world(monkeypatch):
    monkeypatch.setattr(K, "CORPSHIP_BOARD_CAP", False)
    mate = SimpleNamespace(corp_ticker="ABC")
    ceo = SimpleNamespace(corp_ticker="ABC")
    universe = SimpleNamespace(
        players={"M": mate, "C": ceo},
        corporations={"ABC": SimpleNamespace(ceo_id="C")},
    )
    rec = SimpleNamespace(
        owner_id="C",
        ship=SimpleNamespace(corp_ticker="ABC", ship_class=ShipClass.CORPORATE_FLAGSHIP),
    )
    return universe, rec


def test_switches_default_legacy_and_only_v311_turns_the_blow_on(monkeypatch):
    assert K.CFS_CEO_USE_MODE == "legacy"
    assert K.PLANET_BLOW_ALIGN_MODE == "legacy"
    assert K.cfs_ceo_use_live() is False
    assert K.planet_blow_align_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.cfs_ceo_use_live() is False
    assert K.planet_blow_align_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.cfs_ceo_use_live() is False
    assert K.planet_blow_align_live() is True
    assert "cfs_ceo_use_live" not in K.V311_PROFILE_HELPERS
    assert K.V311_PROFILE_HELPERS["planet_blow_align_live"][0] == "PLANET_BLOW_ALIGN_MODE"


def test_flagship_boarding_off_then_on(monkeypatch):
    universe, rec = _flagship_world(monkeypatch)
    assert board_block(universe, "M", rec) is None  # legacy: a corp mate may board
    monkeypatch.setattr(K, "CFS_CEO_USE_MODE", "v311")
    assert board_block(universe, "M", rec) == "only a C.E.O. may fly a Corporate FlagShip"
    assert board_block(universe, "C", rec) is None


def test_flagship_rule_leaves_other_corp_hulls_alone(monkeypatch):
    universe, rec = _flagship_world(monkeypatch)
    rec.ship.ship_class = ShipClass.MERCHANT_CRUISER
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert board_block(universe, "M", rec) is None


def _blow(monkeypatch, mode: str) -> int:
    monkeypatch.setattr(K, "PLANET_BLOW_ALIGN_MODE", mode)
    universe = _world(players={"A": dict(alignment=200, sector_id=20)})
    sector = universe.sectors[20]
    planet = Planet(id=900, sector_id=20, name="Target", class_id=PlanetClass("M"), owner_id=None)
    universe.planets[900] = planet
    sector.planet_ids.append(900)
    before = int(universe.players["A"].alignment)
    _remove_planet(universe, "A", planet)
    assert 900 not in universe.planets
    return before - int(universe.players["A"].alignment)


def test_planet_blow_alignment_off_then_on(monkeypatch):
    monkeypatch.setattr(K, "RANK_MODE", "tw2002")
    assert _blow(monkeypatch, "legacy") == int(K.PLANET_DESTROY_ALIGNMENT_TW2002) == 1
    assert _blow(monkeypatch, "v311") == 50


def test_legacy_constants_unchanged():
    assert K.CFS_CEO_RULE == "purchase"
    assert K.PLANET_DESTROY_ALIGNMENT_TW2002 == 1
    assert K.FERRENGI_ODDS_BY_HULL == {"assault_trader": 1.0, "battle_cruiser": 1.2, "dreadnought": 1.4}
    assert K.planet_blow_alignment_loss() == 1
