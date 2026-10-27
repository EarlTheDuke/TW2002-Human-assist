"""Class L citadel level 1 is 400 handbook thousands, not 400 people.

S1 section VII, class L: Colo 400. Under the v3.11 profile that figure is
the same unit as a non-M planet pool. One Terra hold is 1,000 people, and
a dump divides by 1,000. 31,000 people land as 31 thousands, short of 400.
The build dialog says "400 (thousands)=400,000 people".

Class M is not part of that conversion. Level 1 stays 1,000,000 people
while class_m_fidelity_live is on. No new profile switch.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tests.test_colonist_units_v1 import _act, _land, _take, _world
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, PlanetClass
from tw2k.engine.observation import build_observation

pytestmark = pytest.mark.legacy_profile

_PHRASE = "400 (thousands)=400,000 people"


def _stock_l1(planet) -> None:
    planet.stockpile[Commodity.FUEL_ORE] = 150
    planet.stockpile[Commodity.ORGANICS] = 100
    planet.stockpile[Commodity.EQUIPMENT] = 150


def test_no_new_switch_and_class_m_cost_stays_a_million(monkeypatch) -> None:
    assert "citadel_colonists_are_handbook" not in K.V311_PROFILE_HELPERS
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.class_m_fidelity_live() is True
    assert K.colonist_units_live() is True
    assert K.citadel_class_cost("M", 1)[0] == 1_000_000
    assert K.citadel_class_cost("L", 1)[0] == 400
    assert K.citadel_colonists_are_handbook("L") is True
    assert K.citadel_colonists_are_handbook("M") is False


def test_terra_dump_of_31k_is_31_thousands_toward_400(monkeypatch) -> None:
    """Mid Eden: 31,000 Terra people become 31 thousands, not 31,000."""
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _world()
    # Live Terra opens at 30,000 people. Top it up so one take is 31 holds.
    u.terra_colonists = 40_000
    _take(u, 31)
    ship = u.players["P1"].ship
    assert ship.cargo[Commodity.COLONISTS] == 31_000
    planet = _land(u, PlanetClass.L)
    planet.name = "Mid Eden"
    _stock_l1(planet)
    dropped = _act(
        u, "assign_colonists", planet_id=planet.id,
        **{"from": "ship", "to": "fuel_ore", "qty": 31_000},
    )
    assert dropped.ok, dropped.error
    assert planet.colonists[Commodity.FUEL_ORE] == 31
    assert ship.cargo.get(Commodity.COLONISTS, 0) == 0

    refused = _act(u, "build_citadel", planet_id=planet.id)
    assert refused.ok is False
    assert _PHRASE in (refused.error or "")
    assert "31 (thousands)=31,000 people" in (refused.error or "")
    assert planet.citadel_target == 0

    obs = build_observation(u, "P1")
    quote = obs.citadel_next_build
    assert quote["need"] == 400
    assert quote["have"] == 31
    assert quote["need_people"] == 400_000
    assert quote["have_people"] == 31_000
    assert _PHRASE in quote["plain"]
    listed = {la.kind: la for la in legal_actions(u, "P1")}
    nxt = listed["build_citadel"].params["next"]
    assert listed["build_citadel"].legal is False
    assert _PHRASE in nxt["plain"]
    assert _PHRASE in (listed["build_citadel"].reason or "")


def test_level_1_opens_at_400_thousands_and_399_does_not(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _world()
    planet = _land(u, PlanetClass.L)
    _stock_l1(planet)
    planet.colonists[Commodity.FUEL_ORE] = 399
    short = _act(u, "build_citadel", planet_id=planet.id)
    assert short.ok is False
    assert _PHRASE in (short.error or "")
    assert planet.citadel_target == 0
    planet.colonists[Commodity.FUEL_ORE] = 400
    started = _act(u, "build_citadel", planet_id=planet.id)
    assert started.ok, started.error
    assert planet.citadel_target == 1
    summaries = [ev.summary for ev in u.events if "Citadel" in (ev.summary or "")]
    assert summaries
    assert "400 (thousands)=400,000 people" in summaries[-1]


def test_class_m_still_needs_a_million_people(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _world()
    planet = _land(u, PlanetClass.M)
    planet.stockpile[Commodity.FUEL_ORE] = 300
    planet.stockpile[Commodity.ORGANICS] = 200
    planet.stockpile[Commodity.EQUIPMENT] = 250
    planet.colonists[Commodity.FUEL_ORE] = 999_999
    short = _act(u, "build_citadel", planet_id=planet.id)
    assert short.ok is False
    assert "1000000" in (short.error or "")
    assert _PHRASE not in (short.error or "")
    planet.colonists[Commodity.FUEL_ORE] = 1_000_000
    started = _act(u, "build_citadel", planet_id=planet.id)
    assert started.ok, started.error
    assert planet.citadel_target == 1
    quote = build_observation(u, "P1").citadel_next_build
    assert quote is None or quote.get("level") != 1


def test_profile_off_keeps_the_raw_colonist_sentence() -> None:
    assert K.v311_profile() is False
    assert K.citadel_colonists_are_handbook("L") is False
    u = _world()
    planet = _land(u, PlanetClass.L)
    _stock_l1(planet)
    planet.colonists[Commodity.FUEL_ORE] = 31
    refused = _act(u, "build_citadel", planet_id=planet.id)
    assert refused.ok is False
    assert refused.error == "need 400 colonists on planet (have 31)"
    assert _PHRASE not in (refused.error or "")
