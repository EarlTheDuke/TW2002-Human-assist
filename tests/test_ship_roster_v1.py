"""The live ship screen can differ from the Bible chart. The switch stays off."""

from __future__ import annotations

import tw2k.engine.constants as K


def test_legacy_iss_and_scout_stay_on_the_bible_chart():
    K.SHIP_ROSTER_MODE = "legacy"
    assert K.ship_cost("imperial_starship") == 339_000
    assert K.ship_specs()["scout_marauder"]["max_fighters"] == 150


def test_live_iss_is_329000_and_does_not_edit_the_chart():
    K.SHIP_ROSTER_MODE = "live"
    try:
        assert K.ship_cost("imperial_starship") == 329_000
        assert K.ship_specs()["imperial_starship"]["cost"] == 329_000
        assert K.SHIP_SPECS_TW2002["imperial_starship"]["cost"] == 339_000
    finally:
        K.SHIP_ROSTER_MODE = "legacy"


def test_live_scout_carries_250_fighters():
    K.SHIP_ROSTER_MODE = "live"
    try:
        assert K.ship_specs()["scout_marauder"]["max_fighters"] == 250
        assert K.SHIP_SPECS_TW2002["scout_marauder"]["max_fighters"] == 150
    finally:
        K.SHIP_ROSTER_MODE = "legacy"


def test_named_hulls_already_match_the_screen():
    freighter = K.SHIP_SPECS_TW2002["merchant_freighter"]
    assert freighter["cost"] == 33_400
    assert freighter["holds"] == 65
    assert freighter["max_fighters"] == 300
    assert freighter["max_shields"] == 500
    assert freighter["turns_per_warp"] == 2
    assert K.SHIP_SPECS_TW2002["scout_marauder"]["cost"] == 15_950
    assert K.SHIP_SPECS_TW2002["battleship"]["cost"] == 88_500
    assert K.SHIP_SPECS_TW2002["corporate_flagship"]["cost"] == 163_500
    assert K.SHIP_SPECS_TW2002["colonial_transport"]["max_holds"] == 250
    assert K.SHIP_SPECS_TW2002["havoc_gunstar"]["cost"] == 79_000
    assert K.SHIP_SPECS_TW2002["havoc_gunstar"]["holds"] == 50
