"""A new planet can start empty, and a sector still holds five. The switch stays off."""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.models import Player, Ship, ShipClass

pytestmark = pytest.mark.legacy_profile


def _deploy(mode: str):
    _prior_genesis_start_mode = K.GENESIS_START_MODE
    _prior_genesis_min_hops_from_stardock = K.GENESIS_MIN_HOPS_FROM_STARDOCK
    try:
        prior_mode = K.GENESIS_START_MODE
        prior_hops = K.GENESIS_MIN_HOPS_FROM_STARDOCK
        K.GENESIS_START_MODE = mode
        K.GENESIS_MIN_HOPS_FROM_STARDOCK = 0
        try:
            universe = generate_universe(GameConfig(
                seed=7, universe_size=40, enable_ferrengi=False, enable_planets=False,
            ))
            universe.players["A"] = Player(
                id="A",
                name="Alpha",
                ship=Ship(holds=20, ship_class=ShipClass.MERCHANT_CRUISER, genesis=1),
                sector_id=20,
                credits=1_000,
                turns_today=0,
            )
            universe.sectors[20].occupant_ids.append("A")
            result = apply_action(universe, "A", Action(kind=ActionKind.DEPLOY_GENESIS, args={}))
            assert result.ok
            planet = next(iter(universe.planets.values()))
            return planet
        finally:
            K.GENESIS_START_MODE = prior_mode
            K.GENESIS_MIN_HOPS_FROM_STARDOCK = prior_hops
    finally:
        K.GENESIS_START_MODE = _prior_genesis_start_mode
        K.GENESIS_MIN_HOPS_FROM_STARDOCK = _prior_genesis_min_hops_from_stardock


def test_legacy_planet_keeps_the_seed():
    planet = _deploy("legacy")
    assert sum(planet.colonists.values()) == 2_500
    assert sum(planet.stockpile.values()) > 0


def test_live_planet_starts_empty():
    planet = _deploy("live")
    assert sum(planet.colonists.values()) == 0
    assert sum(planet.stockpile.values()) == 0


def test_live_sector_stops_at_five_even_without_the_economy_cap():
    _prior_planet_economy_mode = K.PLANET_ECONOMY_MODE
    _prior_genesis_start_mode = K.GENESIS_START_MODE
    try:
        prior_mode = K.GENESIS_START_MODE
        prior_econ = K.PLANET_ECONOMY_MODE
        try:
            K.PLANET_ECONOMY_MODE = "legacy"
            K.GENESIS_START_MODE = "legacy"
            assert K.sector_has_planet_room(5) is True
            K.GENESIS_START_MODE = "live"
            assert K.sector_has_planet_room(5) is False
            assert K.sector_has_planet_room(4) is True
        finally:
            K.GENESIS_START_MODE = prior_mode
            K.PLANET_ECONOMY_MODE = prior_econ
    finally:
        K.PLANET_ECONOMY_MODE = _prior_planet_economy_mode
        K.GENESIS_START_MODE = _prior_genesis_start_mode


def test_torpedo_price_stays_on_the_hardware_switch():
    _prior_genesis_start_mode = K.GENESIS_START_MODE
    try:
        prior = K.GENESIS_START_MODE
        try:
            K.GENESIS_START_MODE = "live"
            assert K.genesis_torpedo_cost() == K.genesis_torpedo_cost()
            live_cost = K.genesis_torpedo_cost()
        finally:
            K.GENESIS_START_MODE = "legacy"
        assert K.genesis_torpedo_cost() == live_cost
    finally:
        K.GENESIS_START_MODE = _prior_genesis_start_mode
