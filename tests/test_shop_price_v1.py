"""StarDock hold price can use the screen formula. The switch stays off."""

from __future__ import annotations

import tw2k.engine.constants as K


def test_legacy_day1_hold_at_20_uses_the_daily_base():
    K.SHOP_PRICE_MODE = "legacy"
    assert K.hold_next_price("merchant_cruiser", 20, 1) == 562


def test_live_hold_at_20_is_550():
    K.SHOP_PRICE_MODE = "live"
    try:
        assert K.hold_next_price("merchant_cruiser", 20, 1) == 550
        assert K.hold_next_price("merchant_cruiser", 19, 1) == 530
    finally:
        K.SHOP_PRICE_MODE = "legacy"


def test_live_two_holds_from_20_cost_1120():
    K.SHOP_PRICE_MODE = "live"
    try:
        assert K.hold_total_price("merchant_cruiser", 20, 2, 1) == 1120
    finally:
        K.SHOP_PRICE_MODE = "legacy"


def test_live_does_not_replace_the_fighter_wave():
    K.SHOP_PRICE_MODE = "legacy"
    legacy = K.fighter_unit_price(1)
    K.SHOP_PRICE_MODE = "live"
    try:
        assert K.fighter_unit_price(1) == legacy
    finally:
        K.SHOP_PRICE_MODE = "legacy"
