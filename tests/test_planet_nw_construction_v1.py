"""planet-nw-construction-v1. Goods in a citadel build stay in the score only when live."""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine.models import Commodity, Planet, PlanetClass
from tw2k.engine.victory import _planet_asset_value, planet_tax_value

pytestmark = pytest.mark.legacy_profile


def _goods() -> tuple[int, int, int]:
    _colonists, fuel, organics, equipment, _days = K.citadel_class_cost("U", 1)
    return fuel, organics, equipment


def _planet(*, building: bool, done: bool, extra_fuel: int = 0) -> Planet:
    fuel, organics, equipment = _goods()
    stock_fuel = 0 if building or done else fuel
    stock_org = 0 if building or done else organics
    stock_eq = 0 if building or done else equipment
    return Planet(
        id=1,
        sector_id=50,
        name="Spam",
        class_id=PlanetClass.U,
        owner_id="P1",
        origin="genesis",
        citadel_level=1 if done else 0,
        citadel_target=1 if building or done else 0,
        colonists={
            Commodity.FUEL_ORE: 2500,
            Commodity.ORGANICS: 0,
            Commodity.EQUIPMENT: 0,
            Commodity.COLONISTS: 0,
        },
        stockpile={
            Commodity.FUEL_ORE: stock_fuel + extra_fuel,
            Commodity.ORGANICS: stock_org,
            Commodity.EQUIPMENT: stock_eq,
        },
    )


def test_default_stays_legacy() -> None:
    assert K.PLANET_NW_MODE == "legacy"
    before = _planet_asset_value(_planet(building=False, done=False))
    during = _planet_asset_value(_planet(building=True, done=False))
    assert before - during == 308_600


def test_live_keeps_the_goods_while_the_level_builds() -> None:
    _prior_planet_nw_mode = K.PLANET_NW_MODE
    try:
        prior = K.PLANET_NW_MODE
        try:
            K.PLANET_NW_MODE = "live"
            before = _planet_asset_value(_planet(building=False, done=False))
            during = _planet_asset_value(_planet(building=True, done=False))
            done = _planet_asset_value(_planet(building=False, done=True))
            extra = _planet_asset_value(_planet(building=True, done=False, extra_fuel=10))
        finally:
            K.PLANET_NW_MODE = prior
        assert during == before
        assert done == before
        assert extra - during == 10 * K.COMMODITY_BASE_PRICE["fuel_ore"]
    finally:
        K.PLANET_NW_MODE = _prior_planet_nw_mode


def test_a_genesis_seed_counts_only_once_level_1_is_built(monkeypatch) -> None:
    """The seed is the level-1 goods: hidden while idle (GENESIS_SCORE fair) and while building."""
    monkeypatch.setattr(K, "GENESIS_SCORE_MODE", "fair")
    monkeypatch.setattr(K, "PLANET_NW_MODE", "live")
    before = _planet_asset_value(_planet(building=False, done=False))
    during = _planet_asset_value(_planet(building=True, done=False))
    done = _planet_asset_value(_planet(building=False, done=True))
    assert during == before
    assert done - during == 308_600


def test_live_does_not_change_the_growth_tax() -> None:
    _prior_planet_nw_mode = K.PLANET_NW_MODE
    try:
        prior = K.PLANET_NW_MODE
        try:
            K.PLANET_NW_MODE = "live"
            legacy_basis = planet_tax_value(_planet(building=True, done=False))
        finally:
            K.PLANET_NW_MODE = prior
        assert planet_tax_value(_planet(building=True, done=False)) == legacy_basis
    finally:
        K.PLANET_NW_MODE = _prior_planet_nw_mode
