"""Planet days can use the S1 colonist ratios. The switch stays off."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine.models import Commodity, GameConfig, Planet, PlanetClass, Universe
from tw2k.engine.planets import _advance_planets


def _world(fuel: int, organics: int = 0, stock_org: int = 0) -> Universe:
    planet = Planet(
        id=1,
        sector_id=20,
        name="M",
        class_id=PlanetClass.M,
        owner_id="A",
        colonists={
            Commodity.FUEL_ORE: fuel,
            Commodity.ORGANICS: organics,
            Commodity.EQUIPMENT: 0,
            Commodity.COLONISTS: 0,
        },
        stockpile={
            Commodity.FUEL_ORE: 0,
            Commodity.ORGANICS: stock_org,
            Commodity.EQUIPMENT: 0,
        },
    )
    return Universe(config=GameConfig(seed=1), sectors={}, planets={1: planet})


def test_legacy_hundred_fuel_colonists_make_three():
    _prior_planet_prod_mode = K.PLANET_PROD_MODE
    try:
        K.PLANET_PROD_MODE = "legacy"
        universe = _world(100)
        _advance_planets(universe)
        assert universe.planets[1].stockpile[Commodity.FUEL_ORE] == 3
    finally:
        K.PLANET_PROD_MODE = _prior_planet_prod_mode


def test_live_1500_fuel_colonists_make_500():
    _prior_planet_prod_mode = K.PLANET_PROD_MODE
    try:
        try:
            K.PLANET_PROD_MODE = "live"
            universe = _world(1500)
            _advance_planets(universe)
            assert universe.planets[1].stockpile[Commodity.FUEL_ORE] == 500
            crowded = _world(20_000, organics=700)
            _advance_planets(crowded)
            assert crowded.planets[1].stockpile[Commodity.ORGANICS] == 100
        finally:
            K.PLANET_PROD_MODE = "legacy"
    finally:
        K.PLANET_PROD_MODE = _prior_planet_prod_mode


def test_live_population_above_half_shrinks():
    _prior_planet_prod_mode = K.PLANET_PROD_MODE
    try:
        try:
            K.PLANET_PROD_MODE = "live"
            universe = _world(20_000)
            _advance_planets(universe)
            assert sum(universe.planets[1].colonists.values()) == 19_000
        finally:
            K.PLANET_PROD_MODE = "legacy"
    finally:
        K.PLANET_PROD_MODE = _prior_planet_prod_mode


def test_legacy_population_above_half_does_not_shrink():
    _prior_planet_prod_mode = K.PLANET_PROD_MODE
    try:
        K.PLANET_PROD_MODE = "legacy"
        universe = _world(20_000)
        _advance_planets(universe)
        assert sum(universe.planets[1].colonists.values()) == 20_000
    finally:
        K.PLANET_PROD_MODE = _prior_planet_prod_mode
