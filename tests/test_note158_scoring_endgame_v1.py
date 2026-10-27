"""NOTE 158. The free Scout's fighters, the one printed re-entry number still off.

The switch stays legacy while it is off, including when V311_PROFILE is "1".
The switch, or V311_PROFILE "v311" alone, uses the printed cap.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tests.test_death_escape_pods_v1 import _make_universe, _park
from tests.test_phase_abc import _first_non_fed_sector
from tw2k.engine.combat import _destroy_ship
from tw2k.engine.models import ShipClass
from tw2k.public.manual import render

pytestmark = pytest.mark.legacy_profile


def _scout_loss(seed: int) -> int:
    universe, (pilot, _other, _third) = _make_universe(seed=seed)
    sector = _first_non_fed_sector(universe)
    _park(universe, pilot, sector)
    pilot.ship.ship_class = ShipClass.SCOUT_MARAUDER
    _destroy_ship(universe, pilot.id, reason="combat")
    return int(pilot.ship.fighters)


def _pod_loss(seed: int) -> int:
    universe, (pilot, _other, _third) = _make_universe(seed=seed)
    sector = _first_non_fed_sector(universe)
    _park(universe, pilot, sector)
    pilot.ship.ship_class = ShipClass.MERCHANT_CRUISER
    _destroy_ship(universe, pilot.id, reason="mines")
    assert pilot.ship.ship_class is ShipClass.ESCAPE_POD
    return int(pilot.ship.fighters)


def test_reentry_fighters_fails_off_and_passes_on(monkeypatch) -> None:
    """The revision grants min(250, Initial Fighters), not an empty Scout and not 2,500.

    The stored scout holds 150. The v3.11 roster holds 250, so 2,500 becomes 250.
    A pod is not restocked.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.reentry_fighters_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")

    assert K.reentry_fighter_grant(2_500) == 0
    assert K.reentry_fighter_grant(20) == 0
    assert _scout_loss(15801) == 0
    assert _pod_loss(15802) == 0

    monkeypatch.setattr(K, "REENTRY_FIGHTERS_MODE", "v311")
    assert K.reentry_fighter_grant(20) == 20
    assert K.reentry_fighter_grant(2_500) == 150
    assert _scout_loss(15803) == 20
    assert _pod_loss(15804) == 0

    monkeypatch.setattr(K, "SHIP_ROSTER_MODE", "live")
    assert K.ship_roster_live() is True
    assert K.reentry_fighter_grant(2_500) == 250
    assert K.reentry_fighter_grant(30) == 30

    monkeypatch.setattr(K, "REENTRY_FIGHTERS_MODE", "legacy")
    monkeypatch.setattr(K, "SHIP_ROSTER_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.REENTRY_FIGHTERS_MODE == "legacy"
    assert K.reentry_fighters_live() is True
    assert K.starting_package_live() is True
    assert K.ship_roster_live() is True
    assert K.reentry_fighter_grant() == 30
    assert K.reentry_fighter_grant(2_500) == 250
    assert _scout_loss(15805) == 30


def test_manual_names_the_empty_scout() -> None:
    page = render("Galaxy War Command")
    assert "the free Scout at StarDock has no fighters." in page
    assert "The next loss that day is Ship Destroyed" in page
    assert "v3.11 ranks traders by experience." in page
