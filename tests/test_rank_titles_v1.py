"""The 22 good titles and 22 evil titles. The switch stays off."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine.victory import rank_for


def test_good_ladder_doubles_from_private_to_fleet_admiral():
    for mode in ("legacy", "live"):
        K.RANK_TITLES_MODE = mode
        assert rank_for(1, 0) == "Civilian"
        assert rank_for(2, 0) == "Private"
        assert rank_for(4, 0) == "Private 1st Class"
        assert rank_for(32, 0) == "Sergeant"
        assert rank_for(4_194_304, 0) == "Fleet Admiral"
    K.RANK_TITLES_MODE = "legacy"


def test_evil_ladder_uses_the_same_thresholds():
    K.RANK_TITLES_MODE = "live"
    try:
        assert rank_for(2, -1) == "Nuisance 3rd Class"
        assert rank_for(4, -5) == "Nuisance 2nd Class"
        assert rank_for(4_194_304, -1) == "Prime Evil"
        assert len(K.GOOD_RANKS) == 23
        assert len(K.EVIL_RANKS) == 23
    finally:
        K.RANK_TITLES_MODE = "legacy"
