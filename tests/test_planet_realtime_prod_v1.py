"""Planet goods accrue during the day only when that switch is on.

The live server showed fuel, organics, and equipment higher after 7.3 hours,
not only at the day tick. Off, the day tick is still the only time they move.
On, 7.3 hours pays that fraction, and the day tick pays the rest once.

Plants:
  pb1 — a live clock adds no goods.
  pb2 — the day tick pays the accrued fraction a second time.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine.models import Commodity, Planet, PlanetClass
from tw2k.engine.planets import _advance_planets, _close_realtime_production, refresh_planet_production

pytestmark = pytest.mark.legacy_profile

# 7.3 hours. 1,000 fuel colonists on class M make 30 fuel a day, so this
# slice is 9 and the day tick owes the other 21.
SLICE_S = 7.3 * 3600


class _Bag:
    def __init__(self, planet: Planet) -> None:
        self.planets = {planet.id: planet}


def _home() -> Planet:
    return Planet(
        id=1,
        sector_id=2,
        name="Home",
        class_id=PlanetClass.M,
        colonists={
            Commodity.FUEL_ORE: 1000,
            Commodity.ORGANICS: 0,
            Commodity.EQUIPMENT: 0,
            Commodity.COLONISTS: 0,
        },
        stockpile={
            Commodity.FUEL_ORE: 0,
            Commodity.ORGANICS: 0,
            Commodity.EQUIPMENT: 0,
        },
    )


def _fuel(planet: Planet) -> int:
    return int(planet.stockpile[Commodity.FUEL_ORE])


def test_default_is_midnight_only_and_the_clock_is_not_saved():
    assert K.PLANET_REALTIME_PROD_MODE == "legacy"
    assert K.planet_realtime_prod() is False
    planet = _home()
    assert "prod_clock_at" not in planet.model_dump()
    assert "prod_paid_s" not in planet.model_dump()
    assert "prod_remain" not in planet.model_dump()
    planet.prod_clock_at = 0.0
    refresh_planet_production(_Bag(planet), now=SLICE_S)
    assert _fuel(planet) == 0
    _advance_planets(_Bag(planet))
    assert _fuel(planet) == 30
    assert planet.prod_clock_at == 0.0


def test_live_slice_pays_nine_and_the_day_tick_pays_the_rest_once():
    _prior_planet_realtime_prod_mode = K.PLANET_REALTIME_PROD_MODE
    try:
        try:
            K.PLANET_REALTIME_PROD_MODE = "live"
            planet = _home()
            planet.prod_clock_at = 0.0
            refresh_planet_production(_Bag(planet), now=SLICE_S)
            assert _fuel(planet) == 9
            _close_realtime_production(_Bag(planet), now=SLICE_S)
            assert _fuel(planet) == 30
            assert planet.prod_clock_at is None
            assert planet.prod_paid_s == 0
            assert planet.prod_remain == {}
            assert "prod_clock_at" not in planet.model_dump()
        finally:
            K.PLANET_REALTIME_PROD_MODE = "legacy"
    finally:
        K.PLANET_REALTIME_PROD_MODE = _prior_planet_realtime_prod_mode
