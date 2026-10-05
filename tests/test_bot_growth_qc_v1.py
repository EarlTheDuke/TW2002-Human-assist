"""QC follow-ups for bot-growth-and-fixes-v1."""

from __future__ import annotations

from tw2k.agents.seat_acceptance import SYN_WARPS, synthetic_obs, validate_action
from tw2k.agents.seat_brain import (
    DEFENSE_FIGHTERS_FLOOR,
    DEFENSE_SHIELDS_FLOOR,
    RICH_CREDITS,
    STARDOCK,
    SeatBrain,
    SeatMemory,
    View,
)


def test_opt_defense_does_not_divert_when_already_at_floor() -> None:
    """Rich + hot + already at the defence floor must not plot to StarDock.

    A prior RICH-only branch kept offering plot_course for a 20k \"top-up\"
    value even when fighters/shields were already past the floor; at the dock
    `_buy_defense` often no-oped (have >= floor*2), burning a trade day.
    """
    brain = SeatBrain(value_allocator=True)
    brain.mem = SeatMemory()
    brain.mem.hot_sectors.add(187)
    sid = next(s for s in SYN_WARPS if s != STARDOCK)
    obs = synthetic_obs(sector=sid, credits=RICH_CREDITS + 50_000, ship_class="cargotran")
    obs["ship"]["fighters"] = DEFENSE_FIGHTERS_FLOOR + 50
    obs["ship"]["shields"] = DEFENSE_SHIELDS_FLOOR + 50
    obs["known_warps"] = dict(SYN_WARPS)
    assert brain._opt_defense(View(obs)) is None


def test_opt_defense_still_plots_when_under_defended() -> None:
    brain = SeatBrain(value_allocator=True)
    brain.mem = SeatMemory()
    brain.mem.hot_sectors.add(187)
    sid = next(s for s in SYN_WARPS if s != STARDOCK)
    obs = synthetic_obs(sector=sid, credits=RICH_CREDITS + 50_000, ship_class="cargotran")
    obs["ship"]["fighters"] = 10
    obs["ship"]["shields"] = 0
    obs["known_warps"] = dict(SYN_WARPS)
    out = brain._opt_defense(View(obs))
    assert out is not None
    _value, action, _intent = out
    assert action["kind"] == "plot_course"
    assert validate_action(obs, action) == []
