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


def _la(obs, kind, legal=True, **params):
    obs["legal_actions"] = [row for row in obs["legal_actions"] if row["kind"] != kind]
    obs["legal_actions"].append({
        "kind": kind, "legal": legal, "reason": None, "detail": "precise", "params": params,
    })
    return obs


def test_bb4_reserve_deposits_above_the_away_reserve_not_the_old_float(monkeypatch):
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain
    from tw2k.engine import constants as engine_k

    brain = SeatBrain()
    obs = synthetic_obs(sector=1, credits=80_000, ship_class="cargotran", day=3)
    obs["bank_balance"] = 0
    obs["net_worth"] = 80_000
    _la(obs, "buy_equip", item={"choices": [], "unit_price_by": {}})
    _la(obs, "bank_deposit", max_amount=80_000, balance=0, room=500_000)
    first = brain.decide(obs)
    # 75 holds * 250 = 18,750 trade capital, plus the 2,000 toll because no fighters are aboard.
    assert first["kind"] == "bank_deposit"
    assert first["args"]["amount"] == 80_000 - (18_750 + 2_000)
    assert brain.decide(obs)["kind"] != "bank_deposit"

    monkeypatch.setattr(engine_k, "BOTS_BANK_MODE", "legacy")
    legacy = SeatBrain().decide(obs)
    assert legacy["kind"] == "bank_deposit"
    assert legacy["args"]["amount"] == 80_000 - int(engine_k.BOT_BANK_FLOAT)


def test_bb8_day1_seat_deposits_the_cap():
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain

    brain = SeatBrain()
    obs = synthetic_obs(sector=1, credits=80_000, ship_class="cargotran", day=1)
    obs["bank_balance"] = 0
    obs["net_worth"] = 80_000
    _la(obs, "buy_equip", item={"choices": [], "unit_price_by": {}})
    _la(obs, "bank_deposit", max_amount=80_000, balance=0, room=500_000)
    first = brain.decide(obs)
    assert first["kind"] == "bank_deposit" and first["args"]["amount"] == 10_000


def test_bb13_a_pod_withdraws_before_it_buys_the_scout():
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain

    pod = synthetic_obs(sector=1, credits=0, ship_class="escape_pod", holds=5)
    pod["bank_balance"] = 80_000
    pod["net_worth"] = 80_000
    _la(pod, "buy_ship", ship_class={
        "choices": ["cargotran", "scout_marauder"],
        "net_cost_by": {"cargotran": 40_000, "scout_marauder": 5_000},
    })
    _la(pod, "bank_withdraw", max_amount=80_000, balance=80_000)
    withdrawn = SeatBrain().decide(pod)
    assert withdrawn["kind"] == "bank_withdraw"
    assert withdrawn["args"]["amount"] == 40_000 + 2_000


def test_bb8_day1_cap():
    assert deposit_amount(40_000, 10_000, 500_000, day1=False) == 30_000
    assert deposit_amount(20_000, 8_000, 500_000, day1=True) == 10_000
    assert deposit_amount(15_000, 8_000, 500_000, day1=True) == 0
    assert deposit_amount(40_000, 10_000, 5_000, day1=False) == 5_000
