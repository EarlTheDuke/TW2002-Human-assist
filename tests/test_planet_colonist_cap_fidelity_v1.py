"""A class U planet can hold the colonists a level 3 citadel asks for.

The handbook cap is 3,000. Level 3 asks for 5,000. Legacy keeps 3,000.
Live raises class U to 8,000, the most any class U citadel level asks for.
Class M stays 30,000.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_citadel_class_tables_v1 import _build, _fill, _land, _plant
from tests.test_phase_abc import _make_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import Commodity, PlanetClass
from tw2k.engine.runner import apply_action


def test_legacy_keeps_the_handbook_cap() -> None:
    assert K.PLANET_COLONIST_CAP_MODE == "legacy"
    assert K.planet_colonist_cap_live() is False
    assert K.planet_colonist_cap("U") == 3_000
    assert K.planet_colonist_cap("M") == 30_000
    u, _players = _make_universe(seed=81301)
    owner, planet = _u_planet(u, colonists=3_000)
    owner.ship.cargo[Commodity.COLONISTS] = 20
    res = _assign(u, owner, planet.id, 20)
    assert res.ok is False
    assert res.error == "planet colonist cap is 3000"
    assert sum(planet.colonists.values()) == 3_000


def test_live_class_u_reaches_level_3(monkeypatch) -> None:
    monkeypatch.setattr(K, "PLANET_COLONIST_CAP_MODE", "live")
    assert K.planet_colonist_cap("U") == 8_000
    assert K.planet_colonist_cap("M") == 30_000
    u, _players = _make_universe(seed=81302)
    owner, planet = _u_planet(u, colonists=3_000)
    owner.ship.cargo[Commodity.COLONISTS] = 2_000
    res = _assign(u, owner, planet.id, 2_000)
    assert res.ok, res.error
    assert sum(planet.colonists.values()) == 5_000
    _stock_level_3(planet)
    built = _build(u, owner, planet.id)
    assert built.ok, built.error
    assert planet.citadel_target == 3


def _u_planet(u, *, colonists: int):
    owner = next(iter(u.players.values()))
    planet = _plant(u, owner.id, class_id=PlanetClass.U, level=2)
    _fill(planet, colonists, 0, 0, 0)
    _land(u, owner, planet)
    return owner, planet


def _assign(u, owner, planet_id: int, qty: int):
    return apply_action(u, owner.id, Action(
        kind=ActionKind.ASSIGN_COLONISTS,
        args={"planet_id": planet_id, "from": "ship", "to": "colonists", "qty": qty},
    ))


def _stock_level_3(planet) -> None:
    _col, fuel, organics, equipment, _days = K.citadel_class_cost("U", 3)
    planet.stockpile[Commodity.FUEL_ORE] = fuel
    planet.stockpile[Commodity.ORGANICS] = organics
    planet.stockpile[Commodity.EQUIPMENT] = equipment
