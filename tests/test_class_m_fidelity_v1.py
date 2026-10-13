"""Class M uses people only when that switch is on.

Off, level 1 still asks for 1,000. On, 999,000 is refused and
1,000,000 with the materials is allowed. Each product pool holds
30,000 thousand. A pool under that cap does not shrink.

Plants:
  pb1 — the live build still accepts 999,000.
  pb2 — the switch off still asks for a million.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_citadel_class_tables_v1 import _build, _fill, _land, _plant
from tests.test_phase_abc import _make_universe
from tw2k.engine.models import Commodity, PlanetClass
from tw2k.engine.observation import build_observation
from tw2k.engine.planets import _apply_one_day


def test_switch_stays_off() -> None:
    assert K.CLASS_M_FIDELITY_MODE == "legacy"
    assert K.class_m_fidelity_live() is False
    assert K.citadel_class_cost("M", 1)[0] == 1_000


def test_off_keeps_the_handbook_unit() -> None:
    u, _players = _make_universe(seed=91001)
    owner = next(iter(u.players.values()))
    planet = _plant(u, owner.id, class_id=PlanetClass.M, level=0)
    _fill(planet, 1_000, 300, 200, 250)
    _land(u, owner, planet)
    res = _build(u, owner, planet.id)
    assert res.ok, res.error
    assert "colonists_text" not in build_observation(u, owner.id).owned_planets[0]


def test_on_uses_people_and_the_category_cap() -> None:
    u, _players = _make_universe(seed=91002)
    owner = next(iter(u.players.values()))
    planet = _plant(u, owner.id, class_id=PlanetClass.M, level=0)
    _fill(planet, 999_000, 300, 200, 250)
    _land(u, owner, planet)
    K.CLASS_M_FIDELITY_MODE = "live"
    K.PLANET_PROD_MODE = "live"
    try:
        refused = _build(u, owner, planet.id)
        assert refused.ok is False
        assert "1000000" in refused.error
        planet.colonists[Commodity.COLONISTS] = 1_000_000
        planet.stockpile[Commodity.FUEL_ORE] = 300
        planet.stockpile[Commodity.ORGANICS] = 200
        planet.stockpile[Commodity.EQUIPMENT] = 250
        allowed = _build(u, owner, planet.id)
        assert allowed.ok, allowed.error
        assert planet.citadel_complete_day == u.day + 4
        blocked = K.colonist_drop_error("M", K.CLASS_M_CATEGORY_CAP, 0, 1)
        assert blocked == f"planet colonist cap is {K.CLASS_M_CATEGORY_CAP}"
        assert K.colonist_drop_error("M", K.CLASS_M_CATEGORY_CAP - 1, 0, 1) is None
        planet.colonists[Commodity.FUEL_ORE] = 20_000
        _apply_one_day(planet)
        assert planet.colonists[Commodity.FUEL_ORE] == 20_000
        planet.colonists[Commodity.FUEL_ORE] = K.CLASS_M_CATEGORY_CAP + 10_000
        _apply_one_day(planet)
        assert planet.colonists[Commodity.FUEL_ORE] == K.CLASS_M_CATEGORY_CAP + 9_500
        text = build_observation(u, owner.id).owned_planets[0]["colonists_text"]
        assert "thousands" in text
    finally:
        K.CLASS_M_FIDELITY_MODE = "legacy"
        K.PLANET_PROD_MODE = "legacy"
