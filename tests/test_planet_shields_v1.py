"""Planet shields fight only at citadel level 5 when the switch is on.

The manual says shields can be loaded before level 5 and only stop a
landing once level 5 is done. This copy lets any stocked shields fight.
The free gift stays 0. No new shield count is invented.

PLANET_SHIELD_ACTIVE_MODE defaults to legacy, so today's digests stay put.

Plants:
  pb1 — a live level-3 stock still soaks in the fight.
  pb2 — the live helper still counts shields before level 5.
"""

from __future__ import annotations

from types import SimpleNamespace

import tw2k.engine.constants as K
from tw2k.engine.runner import _planet_odds_fight


def _player() -> SimpleNamespace:
    return SimpleNamespace(
        ship=SimpleNamespace(fighters=100, ship_class=SimpleNamespace(value="scout_marauder")),
        deaths=0,
        photon_damped_sector_id=None,
    )


def _planet(level: int) -> SimpleNamespace:
    return SimpleNamespace(
        fighters=0, shields=10, military_reaction_pct=0,
        citadel_level=level, sector_id=1,
    )


def test_default_shields_fight_before_level_five():
    assert K.PLANET_SHIELD_ACTIVE_MODE == "legacy"
    assert K.CITADEL_GIFT_SHIELDS_PER_LEVEL == 0
    planet = _planet(3)
    assert K.fighting_planet_shields(planet) == 10
    _a, _d, left, rounds = _planet_odds_fight(_player(), planet)
    assert left == 5
    assert rounds[0]["phase"] == "shields"
    assert planet.shields == 10


def test_live_shields_wait_for_level_five_and_keep_the_stock():
    _prior_planet_shield_active_mode = K.PLANET_SHIELD_ACTIVE_MODE
    try:
        try:
            K.PLANET_SHIELD_ACTIVE_MODE = "live"
            early = _planet(3)
            assert K.fighting_planet_shields(early) == 0
            _a, _d, left, rounds = _planet_odds_fight(_player(), early)
            assert left == 0
            assert rounds == []
            assert early.shields == 10
            ready = _planet(5)
            assert K.fighting_planet_shields(ready) == 10
            _a, _d, left, rounds = _planet_odds_fight(_player(), ready)
            assert left == 5
            assert rounds[0]["phase"] == "shields"
        finally:
            K.PLANET_SHIELD_ACTIVE_MODE = "legacy"
    finally:
        K.PLANET_SHIELD_ACTIVE_MODE = _prior_planet_shield_active_mode
