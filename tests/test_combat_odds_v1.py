"""Per-ship attack odds. The switch stays off."""

from __future__ import annotations

import tw2k.engine.constants as K


def test_chart_odds_are_the_same_with_the_switch_off_or_on():
    _prior_combat_odds_mode = K.COMBAT_ODDS_MODE
    try:
        for mode in ("legacy", "live"):
            K.COMBAT_ODDS_MODE = mode
            assert K.combat_hull("merchant_cruiser") == (1.0, 750)
            assert K.combat_hull("scout_marauder") == (2.0, 250)
        K.COMBAT_ODDS_MODE = "legacy"
    finally:
        K.COMBAT_ODDS_MODE = _prior_combat_odds_mode
