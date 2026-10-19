"""assign_colonists to=colonists. Legacy drops them in fuel. Live keeps the pool."""

from __future__ import annotations

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.models import Commodity, Player


def _seat():
    universe = generate_universe(GameConfig(seed=123, universe_size=40, max_days=2))
    planet = next(iter(universe.planets.values()))
    planet.owner_id = "P1"
    planet.fighters = 0
    planet.shields = 0
    for key in list(planet.colonists):
        planet.colonists[key] = 0
    sector = universe.sectors[planet.sector_id]
    sector.fighters = None
    player = Player(id="P1", name="Tester")
    player.sector_id = planet.sector_id
    player.planet_landed = planet.id
    player.ship.cargo[Commodity.COLONISTS] = 40
    universe.players["P1"] = player
    sector.occupant_ids.append("P1")
    return universe, player, planet


def _move(universe, planet_id: int, dest: str, qty: int = 10):
    return apply_action(
        universe,
        "P1",
        Action(
            kind=ActionKind.ASSIGN_COLONISTS,
            args={"planet_id": planet_id, "from": "ship", "to": dest, "qty": qty},
        ),
    )


def test_legacy_sends_the_colonist_pool_into_fuel():
    assert K.ASSIGN_POOL_FIX_MODE == "legacy"
    universe, _player, planet = _seat()
    result = _move(universe, planet.id, "colonists")
    assert result.ok is True
    assert planet.colonists[Commodity.FUEL_ORE] == 10
    assert planet.colonists[Commodity.COLONISTS] == 0


def test_live_keeps_the_colonist_pool():
    _prior_assign_pool_fix_mode = K.ASSIGN_POOL_FIX_MODE
    try:
        universe, _player, planet = _seat()
        try:
            K.ASSIGN_POOL_FIX_MODE = "live"
            result = _move(universe, planet.id, "colonists")
            assert result.ok is True
            assert planet.colonists[Commodity.COLONISTS] == 10
            assert planet.colonists[Commodity.FUEL_ORE] == 0
        finally:
            K.ASSIGN_POOL_FIX_MODE = "legacy"
    finally:
        K.ASSIGN_POOL_FIX_MODE = _prior_assign_pool_fix_mode


def test_named_goods_pools_stay_named():
    _prior_assign_pool_fix_mode = K.ASSIGN_POOL_FIX_MODE
    try:
        universe, _player, planet = _seat()
        try:
            K.ASSIGN_POOL_FIX_MODE = "live"
            assert _move(universe, planet.id, "organics").ok is True
            assert planet.colonists[Commodity.ORGANICS] == 10
            assert _move(universe, planet.id, "equipment").ok is True
            assert planet.colonists[Commodity.EQUIPMENT] == 10
            assert _move(universe, planet.id, "fuel_ore").ok is True
            assert planet.colonists[Commodity.FUEL_ORE] == 10
        finally:
            K.ASSIGN_POOL_FIX_MODE = "legacy"
    finally:
        K.ASSIGN_POOL_FIX_MODE = _prior_assign_pool_fix_mode
