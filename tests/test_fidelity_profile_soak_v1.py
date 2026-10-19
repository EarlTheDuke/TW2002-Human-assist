"""Headless days still play when the live profile is on.

The server gives turns back by the hour. A scripted day is that hour.
With the profile on, a 10-day match throws nothing and every seat warps.
The stored profile stays legacy.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import tw2k.engine.constants as K

ROOT = Path(__file__).resolve().parents[1]


def _runner():
    spec = importlib.util.spec_from_file_location(
        "run_scripted_match_soak", ROOT / "scripts" / "run_scripted_match.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_profile_on_ten_days_every_seat_moves() -> None:
    _prior_tw2002_live_profile = K.TW2002_LIVE_PROFILE
    try:
        assert K.TW2002_LIVE_PROFILE == "legacy"
        mod = _runner()
        try:
            K.TW2002_LIVE_PROFILE = "live"
            result = mod.run_match(["N3", "N2", "N1", "H"], seed=250925, days=10)
        finally:
            K.TW2002_LIVE_PROFILE = "legacy"
        assert K.TW2002_LIVE_PROFILE == "legacy"
        assert result["days_played"] == 10
        assert len(result["players"]) == 4
        for row in result["players"].values():
            assert row["exceptions"] == 0
            assert len(row["daily"]) == 10
            assert row["kinds"].get("warp", 0) >= 1
            assert row["actions"] > 2000
    finally:
        K.TW2002_LIVE_PROFILE = _prior_tw2002_live_profile
