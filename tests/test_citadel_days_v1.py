"""Live citadel build days, without guessing the colonist count.

A TWGS v3.34b screen said a class M level 1 takes 4 days. This copy
scales that table by 0.25, so 4 becomes 1. The same screen said
1,000,000 colonists. The S1 table says 1,000. That number is not changed.

CITADEL_DAYS_MODE defaults to legacy, so today's digests stay put.

Plants:
  pb1 — live days stay on the 0.25 scale.
  pb2 — live mode swaps the class M colonist count to 1,000,000.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K

pytestmark = pytest.mark.legacy_profile


def test_default_keeps_the_scaled_days_and_the_s1_colonists():
    assert K.CITADEL_DAYS_MODE == "legacy"
    assert K.citadel_build_days(4) == 1
    assert K.citadel_build_days(2) == 1
    colonists, fuel, organics, equipment, days = K.citadel_class_cost("M", 1)
    assert colonists == 1_000
    assert (fuel, organics, equipment) == (300, 200, 250)
    assert days == 1


def test_live_uses_the_screen_days_and_keeps_one_thousand_colonists():
    _prior_citadel_days_mode = K.CITADEL_DAYS_MODE
    try:
        try:
            K.CITADEL_DAYS_MODE = "live"
            assert K.citadel_build_days(4) == 4
            assert K.citadel_build_days(2) == 2
            assert K.citadel_build_days(8) == 8
            assert K.citadel_build_days(18) == 18
            colonists, fuel, organics, equipment, days = K.citadel_class_cost("M", 1)
            assert colonists == 1_000
            assert (fuel, organics, equipment) == (300, 200, 250)
            assert days == 4
            assert K.citadel_class_cost("L", 1)[-1] == 2
            assert K.citadel_class_cost("U", 1)[-1] == 8
            assert K.citadel_class_cost("H", 6)[-1] == 18
        finally:
            K.CITADEL_DAYS_MODE = "legacy"
    finally:
        K.CITADEL_DAYS_MODE = _prior_citadel_days_mode
