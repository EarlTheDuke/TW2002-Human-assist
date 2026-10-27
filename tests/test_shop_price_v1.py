"""StarDock hold price can use the screen formula. The switch stays off."""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K

pytestmark = pytest.mark.legacy_profile


def test_legacy_day1_hold_at_20_uses_the_daily_base():
    _prior_shop_price_mode = K.SHOP_PRICE_MODE
    try:
        K.SHOP_PRICE_MODE = "legacy"
        assert K.hold_next_price("merchant_cruiser", 20, 1) == 562
    finally:
        K.SHOP_PRICE_MODE = _prior_shop_price_mode


def test_live_hold_at_20_is_550():
    _prior_shop_price_mode = K.SHOP_PRICE_MODE
    try:
        try:
            K.SHOP_PRICE_MODE = "live"
            assert K.hold_next_price("merchant_cruiser", 20, 1) == 550
            assert K.hold_next_price("merchant_cruiser", 19, 1) == 530
        finally:
            K.SHOP_PRICE_MODE = "legacy"
    finally:
        K.SHOP_PRICE_MODE = _prior_shop_price_mode


def test_live_two_holds_from_20_cost_1120():
    _prior_shop_price_mode = K.SHOP_PRICE_MODE
    try:
        try:
            K.SHOP_PRICE_MODE = "live"
            assert K.hold_total_price("merchant_cruiser", 20, 2, 1) == 1120
        finally:
            K.SHOP_PRICE_MODE = "legacy"
    finally:
        K.SHOP_PRICE_MODE = _prior_shop_price_mode


def test_live_does_not_replace_the_fighter_wave():
    _prior_shop_price_mode = K.SHOP_PRICE_MODE
    try:
        K.SHOP_PRICE_MODE = "legacy"
        legacy = K.fighter_unit_price(1)
        try:
            K.SHOP_PRICE_MODE = "live"
            assert K.fighter_unit_price(1) == legacy
        finally:
            K.SHOP_PRICE_MODE = "legacy"
    finally:
        K.SHOP_PRICE_MODE = _prior_shop_price_mode
