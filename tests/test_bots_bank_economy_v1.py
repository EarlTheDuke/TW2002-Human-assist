"""Purse math for bots-bank-death-economy-v1. The seat brain does not call it yet."""

from __future__ import annotations

from tw2k.agents.bank_brain import (
    away_reserve,
    deposit_amount,
    nest_egg,
    purse,
    trade_capital,
    withdraw_amount,
)


def test_bb6_nest_egg():
    assert nest_egg(0) == 10_000
    assert nest_egg(149_999) == 10_000
    assert nest_egg(150_000) == 50_000
    assert nest_egg(500_000) == 100_000


def test_bb2_purse():
    assert purse(20_000, 0, 10_000, 0) == 10_000
    assert purse(5_000, 80_000, 10_000, 40_000) == 45_000
    assert purse(1_000, 0, 10_000, 0) == 0


def test_bb5_away_reserve():
    assert trade_capital(10) == 5_000
    assert trade_capital(40) == 10_000
    assert away_reserve(20, [], 0, owns_fighters=True) == 5_000
    assert away_reserve(20, [], 0, owns_fighters=False) == 7_000
    assert away_reserve(40, [40_000], 0, owns_fighters=True) == 50_000
    assert away_reserve(40, [200_000], 0, owns_fighters=True) == 210_000
    assert away_reserve(20, [20_000, 20_000, 20_000], 0, owns_fighters=True) == 65_000
    # A pile of small buys still stops at the cap. One risk flag halves that cap.
    assert away_reserve(20, [20_000] * 10, 0, owns_fighters=True) == 150_000
    assert away_reserve(20, [20_000] * 10, 1, owns_fighters=True) == 75_000
    # The floor is the trade capital plus the largest single buy.
    assert away_reserve(40, [40_000], 5, owns_fighters=True) == 50_000


def test_bb3_withdraw_the_shortfall():
    assert withdraw_amount(25_000, 2_000, 5_000, 80_000, 10_000, 70_000, recovery=False) == 22_000
    assert withdraw_amount(25_000, 2_000, 5_000, 10_000, 10_000, 70_000, recovery=False) == 0
    assert withdraw_amount(25_000, 2_000, 5_000, 10_000, 10_000, 70_000, recovery=True) == 10_000


def test_bb8_day1_cap():
    assert deposit_amount(40_000, 10_000, 500_000, day1=False) == 30_000
    assert deposit_amount(20_000, 8_000, 500_000, day1=True) == 10_000
    assert deposit_amount(15_000, 8_000, 500_000, day1=True) == 0
    assert deposit_amount(40_000, 10_000, 5_000, day1=False) == 5_000
