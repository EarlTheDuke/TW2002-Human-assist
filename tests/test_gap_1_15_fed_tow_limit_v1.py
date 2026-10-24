"""GAP 1.15: FedSpace fighter tow is Match-behind-flag on profile row 168.

Stored legacy tows above FED_TOW_FIGHTER_LIMIT 98 (Gypsy 99 or more).
V311_PROFILE "v311" uses the Bible line of 50 through fed_tow_fighter_limit.
The stored flag and both limit numbers stay put.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_fedspace_police_v1 import _world
from tw2k.engine.fed import run_tows


def _pure_legacy(monkeypatch) -> None:
    monkeypatch.setattr(K, "FED_MODE", "tw2002")
    monkeypatch.setattr(K, "FED_TOW_LIMIT_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")


def test_legacy_limit_is_98(monkeypatch) -> None:
    _pure_legacy(monkeypatch)
    assert K.fed_tow_limit_live() is False
    assert K.fed_tow_fighter_limit() == 98
    assert K.FED_TOW_FIGHTER_LIMIT == 98
    assert K.FED_TOW_LIVE_LIMIT == 50
    assert K.FED_TOW_LIMIT_MODE == "legacy"
    assert K.V311_PROFILE_HELPERS["fed_tow_limit_live"][0] == "FED_TOW_LIMIT_MODE"


def test_v311_profile_limit_is_50_and_the_stored_flag_stays(monkeypatch) -> None:
    _pure_legacy(monkeypatch)
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.v311_profile() is True
    assert K.fed_tow_limit_live() is True
    assert K.fed_tow_fighter_limit() == 50
    assert K.FED_TOW_LIMIT_MODE == "legacy"
    assert K.FED_TOW_FIGHTER_LIMIT == 98
    assert K.FED_TOW_LIVE_LIMIT == 50


def test_fifty_one_fighters_tow_only_under_the_profile(monkeypatch) -> None:
    _pure_legacy(monkeypatch)
    legacy = _world(
        players={
            "LOW": dict(fighters=51, sector_id=3),
            "EDGE": dict(fighters=98, sector_id=4),
            "OVER": dict(fighters=99, sector_id=5),
        }
    )
    assert run_tows(legacy) == 1
    assert legacy.players["LOW"].sector_id == 3
    assert legacy.players["EDGE"].sector_id == 4
    assert legacy.players["OVER"].sector_id not in K.FEDSPACE_SECTORS

    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.fed_tow_limit_live() is True
    live = _world(
        seed=4615,
        players={
            "AT": dict(fighters=50, sector_id=3),
            "OVER": dict(fighters=51, sector_id=4),
        },
    )
    assert run_tows(live) == 1
    assert live.players["AT"].sector_id == 3
    assert live.players["OVER"].sector_id not in K.FEDSPACE_SECTORS
    assert K.FED_TOW_FIGHTER_LIMIT == 98
    assert K.FED_TOW_LIVE_LIMIT == 50
