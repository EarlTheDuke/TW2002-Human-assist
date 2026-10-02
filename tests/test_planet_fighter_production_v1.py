"""Owned planets mint fighters from product-pool colonists on the day tick."""

from __future__ import annotations

from tests.test_phase_abc import _make_universe
from tests.test_siege_path_v1 import _place, _planet
from tw2k.engine.constants import PLANET_FIGHTER_CAP
from tw2k.engine.models import Commodity, PlanetClass
from tw2k.engine.planets import K, fighters_from_colonists
from tw2k.engine.runner import tick_day

SECTOR = 120


def _world(seed: int, class_id: PlanetClass, pools: dict, *, owner: str | None = "B", fighters: int = 0):
    u, (owner_player, *_) = _make_universe(seed=seed)
    planet = _planet(92000 + seed, fighters=fighters, shields=0, level=0, treasury=0)
    planet.class_id = class_id
    planet.owner_id = owner
    planet.colonists = {
        Commodity.FUEL_ORE: 0,
        Commodity.ORGANICS: 0,
        Commodity.EQUIPMENT: 0,
        Commodity.COLONISTS: 0,
    }
    planet.colonists.update(pools)
    _place(u, planet, owner_player)
    return u, planet


def test_original_examples_and_several_pools() -> None:
    u, planet = _world(9201, PlanetClass.M, {Commodity.FUEL_ORE: 1500})
    tick_day(u)
    assert planet.fighters == 50

    u, planet = _world(9202, PlanetClass.M, {
        Commodity.FUEL_ORE: 1500,
        Commodity.ORGANICS: 700,
        Commodity.EQUIPMENT: 260,
    })
    tick_day(u)
    assert planet.fighters == 62
    assert planet.colonists[Commodity.FUEL_ORE] > 1500


def test_each_class_once_and_class_u_still_makes_stock() -> None:
    samples = (
        (PlanetClass.M, Commodity.FUEL_ORE, 30, 1),
        (PlanetClass.K, Commodity.ORGANICS, 1500, 1),
        (PlanetClass.O, Commodity.EQUIPMENT, 1500, 1),
        (PlanetClass.L, Commodity.FUEL_ORE, 24, 1),
        (PlanetClass.C, Commodity.FUEL_ORE, 1250, 1),
        (PlanetClass.H, Commodity.FUEL_ORE, 50, 1),
        (PlanetClass.H, Commodity.ORGANICS, 10_000, 0),
        (PlanetClass.U, Commodity.FUEL_ORE, 10_000, 0),
    )
    for index, (class_id, pool, count, expected) in enumerate(samples):
        u, planet = _world(9300 + index, class_id, {pool: count})
        before = planet.stockpile.get(pool, 0)
        tick_day(u)
        assert planet.fighters == expected
        if class_id is PlanetClass.U and pool is not Commodity.ORGANICS:
            assert planet.stockpile.get(pool, 0) > before


def test_rounding_unowned_idle_pool_and_cap() -> None:
    u, planet = _world(9401, PlanetClass.M, {Commodity.FUEL_ORE: 29})
    tick_day(u)
    assert planet.fighters == 0

    u, planet = _world(9402, PlanetClass.M, {Commodity.FUEL_ORE: 1500}, owner=None)
    tick_day(u)
    assert planet.fighters == 0
    assert planet.stockpile[Commodity.FUEL_ORE] > 0

    u, planet = _world(9403, PlanetClass.M, {Commodity.COLONISTS: 10_000})
    tick_day(u)
    assert planet.fighters == 0

    u, planet = _world(9404, PlanetClass.M, {Commodity.FUEL_ORE: 1500}, fighters=PLANET_FIGHTER_CAP - 2)
    tick_day(u)
    assert planet.fighters == PLANET_FIGHTER_CAP
    assert all("fighters_made" not in ev.kind.value for ev in u.events)


def test_rate_scales_the_day() -> None:
    assert fighters_from_colonists(PlanetClass.M, {"fuel_ore": 1500}) == 50
    old = K.PLANET_FIGHTER_RATE_PCT
    K.PLANET_FIGHTER_RATE_PCT = 50
    try:
        assert fighters_from_colonists(PlanetClass.M, {"fuel_ore": 1500}) == 25
    finally:
        K.PLANET_FIGHTER_RATE_PCT = old
