"""A fresh genesis planet should not score the goods the torpedo just invented.

Game 5 valued a class U genesis planet at about 308,000. That number is the
level-1 citadel goods at the tw2002 bases: 1,200*26 + 400*56 + 2,500*102.

GENESIS_SCORE_MODE defaults to legacy, so today's scores stay put.
fair hides those seeded goods until the citadel reaches level 1. Goods the
planet makes on top of the seed still count. Colonists still count.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine.models import Commodity, Planet, PlanetClass
from tw2k.engine.victory import _planet_asset_value

pytestmark = pytest.mark.legacy_profile


def _class_u(*, extra_fuel: int = 0, level: int = 0) -> Planet:
    _colonists, fuel, organics, equipment, _days = K.citadel_class_cost("U", 1)
    return Planet(
        id=1,
        sector_id=50,
        name="Spam",
        class_id=PlanetClass.U,
        owner_id="P1",
        origin="genesis",
        citadel_level=level,
        colonists={
            Commodity.FUEL_ORE: 2500,
            Commodity.ORGANICS: 0,
            Commodity.EQUIPMENT: 0,
            Commodity.COLONISTS: 0,
        },
        stockpile={
            Commodity.FUEL_ORE: fuel + extra_fuel,
            Commodity.ORGANICS: organics,
            Commodity.EQUIPMENT: equipment,
        },
    )


def _seed_goods_value() -> int:
    _colonists, fuel, organics, equipment, _days = K.citadel_class_cost("U", 1)
    return (
        fuel * K.COMMODITY_BASE_PRICE["fuel_ore"]
        + organics * K.COMMODITY_BASE_PRICE["organics"]
        + equipment * K.COMMODITY_BASE_PRICE["equipment"]
    )


def test_default_stays_legacy():
    assert K.GENESIS_SCORE_MODE == "legacy"
    assert K.genesis_score_fair() is False


def test_class_u_seed_is_the_game5_number():
    assert _seed_goods_value() == 308_600


def test_legacy_scores_the_seeded_goods():
    value = _planet_asset_value(_class_u())
    assert value >= 308_600


def test_fair_hides_the_seed_and_keeps_extra_goods(monkeypatch):
    legacy = _planet_asset_value(_class_u())
    monkeypatch.setattr(K, "GENESIS_SCORE_MODE", "fair")
    fair = _planet_asset_value(_class_u())
    assert legacy - fair == 308_600
    extra = _planet_asset_value(_class_u(extra_fuel=10))
    assert extra - fair == 10 * K.COMMODITY_BASE_PRICE["fuel_ore"]
    assert fair >= 2500 * K.COLONIST_PRICE


def test_fair_counts_goods_again_once_the_citadel_is_level_1(monkeypatch):
    monkeypatch.setattr(K, "GENESIS_SCORE_MODE", "fair")
    fresh = _planet_asset_value(_class_u())
    built = _planet_asset_value(_class_u(level=1))
    assert built > fresh
    assert built - fresh >= 308_600
