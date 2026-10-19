"""Alignment from lost fighters, and who FedSpace protects. The switch stays off."""

from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_phase_abc import _make_universe
from tw2k.engine.victory import combat_rewards, is_fedsafe


def _delta(mode: str) -> int:
    _prior_alignment_mode = K.ALIGNMENT_MODE
    try:
        K.ALIGNMENT_MODE = mode
        u, (attacker, *_) = _make_universe(seed=8860)
        attacker.alignment = 100
        _exp, align = combat_rewards(u, attacker.id, -100_000, 10_000)
        return align
    finally:
        K.ALIGNMENT_MODE = _prior_alignment_mode


def test_legacy_and_live_use_the_handbook_example():
    _prior_alignment_mode = K.ALIGNMENT_MODE
    try:
        try:
            assert _delta("legacy") == 200_000
            assert _delta("live") == 200_000
        finally:
            K.ALIGNMENT_MODE = "legacy"
    finally:
        K.ALIGNMENT_MODE = _prior_alignment_mode


def test_fedsafe_is_a_good_trader_under_1000_experience():
    _u, (trader, *_) = _make_universe(seed=8861)
    trader.alignment = 0
    trader.experience = 999
    assert is_fedsafe(trader) is True
    trader.experience = 1000
    assert is_fedsafe(trader) is False
    trader.experience = 0
    trader.alignment = -1
    assert is_fedsafe(trader) is False
