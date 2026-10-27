"""The V-screen counts appear only when that switch is on.

Off, the observation does not carry them. On, it counts ports,
planets, traders, aliens, and fighters and mines in use.

Plants:
  pb1 — the live screen still leaves the counts off the observation.
  pb2 — the switch off still publishes the counts.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine.models import GameConfig, Player, Ship
from tw2k.engine.observation import build_observation, game_status
from tw2k.engine.universe import generate_universe

pytestmark = pytest.mark.legacy_profile


def _world():
    u = generate_universe(GameConfig(seed=3, universe_size=40, enable_ferrengi=False, enable_planets=True))
    u.players["A"] = Player(id="A", name="Alpha", ship=Ship(fighters=10), sector_id=1, credits=1000)
    u.sectors[1].occupant_ids.append("A")
    return u


def test_switch_stays_off() -> None:
    assert K.DAILY_STATS_MODE == "legacy"
    assert K.daily_stats_live() is False


def test_off_omits_the_screen() -> None:
    u = _world()
    dumped = build_observation(u, "A").model_dump()
    assert "daily_stats" not in dumped


def test_on_counts_the_universe() -> None:
    _prior_daily_stats_mode = K.DAILY_STATS_MODE
    try:
        u = _world()
        try:
            K.DAILY_STATS_MODE = "live"
            stats = game_status(u)
            assert stats["ports"] > 0
            assert stats["planets"] == len(u.planets)
            assert stats["traders"] == 1
            assert stats["aliens"] >= 0
            assert stats["fighters_in_use"] >= 10
            assert stats["mines_in_use"] >= 0
            dumped = build_observation(u, "A").model_dump()
            assert dumped["daily_stats"] == stats
        finally:
            K.DAILY_STATS_MODE = "legacy"
    finally:
        K.DAILY_STATS_MODE = _prior_daily_stats_mode
