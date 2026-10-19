"""A fresh escape pod. The switch stays off."""

from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_phase_abc import _make_universe
from tw2k.engine.combat import _destroy_ship
from tw2k.engine.models import ShipClass


def _pod(mode: str):
    _prior_death_pod_mode = K.DEATH_POD_MODE
    try:
        K.DEATH_POD_MODE = mode
        u, (player, *_) = _make_universe(seed=8870)
        player.ship.ship_class = ShipClass.MERCHANT_CRUISER
        player.experience = 1000
        _destroy_ship(u, player.id, "test", None)
        return player
    finally:
        K.DEATH_POD_MODE = _prior_death_pod_mode


def test_legacy_pod_keeps_the_chart_and_loses_ten_percent():
    _prior_death_pod_mode = K.DEATH_POD_MODE
    try:
        K.DEATH_POD_MODE = "legacy"
        player = _pod("legacy")
        assert player.ship.ship_class is ShipClass.ESCAPE_POD
        assert player.ship.holds == 5
        assert player.ship.fighters == 0
        assert player.ship.shields == 0
        assert player.experience == 900
    finally:
        K.DEATH_POD_MODE = _prior_death_pod_mode


def test_live_pod_matches_the_clean_game_loadout():
    _prior_death_pod_mode = K.DEATH_POD_MODE
    try:
        try:
            K.DEATH_POD_MODE = "live"
            player = _pod("live")
            assert player.ship.holds == 1
            assert player.ship.fighters == 1
            assert player.ship.shields == 30
            assert player.ship.scanner == "density"
            assert player.experience == 900
        finally:
            K.DEATH_POD_MODE = "legacy"
    finally:
        K.DEATH_POD_MODE = _prior_death_pod_mode
