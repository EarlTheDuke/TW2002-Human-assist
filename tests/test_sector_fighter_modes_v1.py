"""Defensive, toll, and offensive fighters are already on. Do not flip the switch."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine.models import FighterMode
from tw2k.engine.runner import _handle_surrender


def test_the_three_modes_stay_on():
    assert K.SECTOR_FIGHTER_MODE == "tw2002"
    assert {m.value for m in FighterMode} == {"defensive", "offensive", "toll"}
    assert _handle_surrender is not None
