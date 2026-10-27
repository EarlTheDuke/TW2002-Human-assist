"""The opening pocket can match the live TWGS game without moving today's games.

Live Big Bang: 300 credits, 30 fighters, 250 turns, a free class M planet
with 191,000 colonists and empty stock. Turns come back at 250 per day of
wall-clock time, and a new day does not refill them to full.

STARTING_PACKAGE_MODE defaults to legacy, so the 20,000 / 20 / 1,000 pocket
and the midnight refill stay.

Plants:
  pb1 — live opening still pays 20,000 credits.
  pb2 — live recovery still gives nothing back for an hour away.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe, tick_day
from tw2k.engine.models import Commodity, Player
from tw2k.engine.runner import grant_starting_planet, recover_turns

pytestmark = pytest.mark.legacy_profile


def _universe():
    cfg = GameConfig(
        seed=21, universe_size=40, max_days=3, turns_per_day=1000,
        starting_credits=20_000, enable_ferrengi=False, enable_planets=False,
    )
    u = generate_universe(cfg)
    p = Player(id="P1", name="Seat", sector_id=1, credits=20_000, turns_per_day=1000)
    u.players["P1"] = p
    u.sectors[1].occupant_ids.append("P1")
    return u, p


def test_default_stays_legacy():
    assert K.STARTING_PACKAGE_MODE == "legacy"
    assert K.starting_package_live() is False
    credits, turns, fighters = K.opening_loadout(20_000, 1000, 1)
    assert credits == 20_000 + ((1 * 317) % 2001 - 1000)
    assert turns == 1000
    assert fighters == 20


def test_live_pocket_is_the_measured_opening(monkeypatch):
    monkeypatch.setattr(K, "STARTING_PACKAGE_MODE", "live")
    credits, turns, fighters = K.opening_loadout(20_000, 1000, 1)
    assert credits == 300
    assert turns == 250
    assert fighters == 30
    u, p = _universe()
    grant_starting_planet(u, p)
    owned = [pl for pl in u.planets.values() if pl.owner_id == "P1"]
    assert len(owned) == 1
    planet = owned[0]
    assert planet.class_id.value == "M"
    assert planet.sector_id == p.sector_id
    assert planet.colonists[Commodity.COLONISTS] == 191_000
    assert sum(planet.stockpile.values()) == 0


def test_legacy_day_tick_refills_and_live_day_tick_does_not(monkeypatch):
    u, p = _universe()
    p.turns_today = 40
    tick_day(u)
    assert p.turns_today == 0

    monkeypatch.setattr(K, "STARTING_PACKAGE_MODE", "live")
    u2, p2 = _universe()
    p2.turns_today = 40
    tick_day(u2)
    assert p2.turns_today == 40


def test_live_hour_gives_back_ten_turns_and_stops_at_full(monkeypatch):
    monkeypatch.setattr(K, "STARTING_PACKAGE_MODE", "live")
    _u, p = _universe()
    p.turns_today = 100
    assert recover_turns(p, 3600) == 10
    assert p.turns_today == 90
    assert recover_turns(p, 24 * 3600) == 90
    assert p.turns_today == 0


def test_legacy_recovery_changes_nothing():
    _u, p = _universe()
    p.turns_today = 100
    assert recover_turns(p, 3600) == 0
    assert p.turns_today == 100
