"""N2, N3, and H use the tavern. N1 and a legacy game do not."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View
from tw2k.agents.tavern_brain import join_underground, seat_may_use, trace_due


def _obs(*, credits: int = 80_000, alignment: int = 100, day: int = 8) -> dict:
    return {
        "self_id": "P1",
        "credits": credits,
        "net_worth": 200_000,
        "alignment": alignment,
        "day": day,
        "sector": {"id": 1, "planets": [], "occupants": ["P1"]},
        "ship": {"class": "merchant_cruiser", "fighters": 100},
        "rivals": [{"id": "P2", "alignment": -50}],
        "legal_actions": [{
            "kind": "grimy_ask",
            "legal": True,
            "params": {"topic": {"choices": ["trader", "underground"]}},
        }],
        "known_warps": {},
        "tavern": {},
        "trade_summary": {"total_profit_cr": 500_000},
    }


def test_bt1_mode(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_TAVERN_MODE", "legacy")
    brain = SeatBrain()
    brain.mem = SeatMemory()
    assert brain._maybe_tavern(View(_obs())) is None


def test_bt2_skill() -> None:
    assert seat_may_use("N1") is False
    assert seat_may_use("N2") and seat_may_use("N3") and seat_may_use("H")
    brain = SeatBrain(feed_organics=False, value_allocator=False)
    brain.mem = SeatMemory()
    assert brain._maybe_tavern(View(_obs())) is None


def test_bt3_reason() -> None:
    assert trace_due(hunting=False, picking_lane=False, credits=80_000, cost=3_000,
                     reserve=20_000, last_day=-1, day=8, gap_days=10) is False


def test_bt4_broke() -> None:
    assert trace_due(hunting=True, picking_lane=False, credits=22_000, cost=3_000,
                     reserve=20_000, last_day=-1, day=8, gap_days=10) is False


def test_bt5_once() -> None:
    assert trace_due(hunting=True, picking_lane=False, credits=80_000, cost=3_000,
                     reserve=20_000, last_day=8, day=8, gap_days=10) is False


def test_bt6_gap() -> None:
    assert trace_due(hunting=True, picking_lane=False, credits=80_000, cost=3_000,
                     reserve=20_000, last_day=4, day=8, gap_days=10) is False
    assert trace_due(hunting=True, picking_lane=False, credits=80_000, cost=3_000,
                     reserve=20_000, last_day=4, day=14, gap_days=10) is True


def test_bt7_alignment() -> None:
    assert join_underground(alignment=100, credits=80_000, password_price=2_000, already=False) is False


def test_bt8_cash() -> None:
    assert join_underground(alignment=-20, credits=4_000, password_price=2_000, already=False) is False
    assert join_underground(alignment=-20, credits=4_001, password_price=2_000, already=False) is True


def test_bt9_thought(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_TAVERN_MODE", "tw2002")
    brain = SeatBrain(feed_organics=False, value_allocator=False)
    brain.mem = SeatMemory()
    obs = _obs(alignment=-50, credits=80_000)
    obs["tavern"] = {"password_known": False}
    # N1 does not ask. An evil N3 does, and the thought does not carry the word.
    assert brain._maybe_tavern(View(obs)) is None
    brain = SeatBrain()
    brain.mem = SeatMemory()
    action = brain._maybe_tavern(View(obs))
    assert action is not None and action["kind"] == "grimy_ask"
    assert "password" not in action["thought"]
    assert "word" not in action["args"]


def test_bt10_n3_traces(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_TAVERN_MODE", "tw2002")
    brain = SeatBrain()
    brain.mem = SeatMemory()
    action = brain._maybe_tavern(View(_obs()))
    assert action is not None and action["args"]["topic"] == "trader"
    assert action["args"]["target"] == "P2"
    assert brain._maybe_tavern(View(_obs())) is None


def test_bt17_early_day_still_says_a_word(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_TAVERN_MODE", "tw2002")
    brain = SeatBrain()
    brain.mem = SeatMemory()
    obs = _obs(day=2, credits=40_000)
    obs["trade_summary"] = {"total_profit_cr": 1_000}
    obs["legal_actions"].append({"kind": "tavern_talk", "legal": True, "params": {}})
    action = brain._maybe_tavern(View(obs))
    assert action is not None and action["kind"] == "tavern_talk"


def test_bt16_trace_fits_income() -> None:
    from tw2k.agents.tavern_brain import trace_fits_income
    assert trace_fits_income(cost=3_000, spent=0, profit=150_000) is False
    assert trace_fits_income(cost=3_000, spent=0, profit=150_001) is True
    assert trace_fits_income(cost=3_000, spent=6_000, profit=200_000) is False


def test_bt11_reserve() -> None:
    assert trace_due(hunting=True, picking_lane=True, credits=20_000, cost=3_000,
                     reserve=20_000, last_day=-1, day=8, gap_days=10) is False


def test_bt12_n2_picks_a_lane(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_TAVERN_MODE", "tw2002")
    brain = SeatBrain(value_allocator=False)
    brain.mem = SeatMemory()
    # No trade quote in this bare view, so a lane-only seat does not ask.
    assert brain._maybe_tavern(View(_obs())) is None


def test_bt13_known_password() -> None:
    assert join_underground(alignment=-20, credits=80_000, password_price=2_000, already=True) is False


def test_bt14_enter_hides_the_word(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_TAVERN_MODE", "tw2002")
    brain = SeatBrain()
    brain.mem = SeatMemory()
    obs = _obs(alignment=-40, credits=80_000)
    obs["tavern"] = {"password_known": True, "ug_password": "seedword"}
    obs["legal_actions"].append({"kind": "underground_enter", "legal": True, "params": {}})
    action = brain._maybe_tavern(View(obs))
    assert action is not None and action["kind"] == "underground_enter"
    assert action["args"]["password"] == "seedword"
    assert "seedword" not in action["thought"]


def test_bt15_docs() -> None:
    from pathlib import Path
    text = Path("docs/playtests/bots/BOTS_USE_TAVERN.md").read_text(encoding="utf-8")
    assert "BOTS_TAVERN_MODE" in text and "2%" in text


def test_bt18_withdraws_for_a_trace(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_TAVERN_MODE", "tw2002")
    brain = SeatBrain()
    brain.mem = SeatMemory()
    obs = _obs(credits=10_000)
    obs["bank_balance"] = 100_000
    obs["legal_actions"].append({
        "kind": "bank_withdraw", "legal": True,
        "params": {"max_amount": 100_000},
    })
    action = brain._maybe_tavern(View(obs))
    assert action is not None and action["kind"] == "bank_withdraw"
    assert int(action["args"]["amount"]) == 13_000
    assert brain.mem.tavern_day < 0


def test_bt19_waits_when_the_bank_is_empty(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_TAVERN_MODE", "tw2002")
    brain = SeatBrain()
    brain.mem = SeatMemory()
    obs = _obs(credits=10_000)
    obs["bank_balance"] = 0
    obs["legal_actions"].append({"kind": "tavern_talk", "legal": True, "params": {}})
    assert brain._maybe_tavern(View(obs)) is None


def test_bt20_free_word_does_not_block_a_trace(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_TAVERN_MODE", "tw2002")
    brain = SeatBrain()
    brain.mem = SeatMemory()
    poor = _obs(day=2, credits=40_000)
    poor["trade_summary"] = {"total_profit_cr": 1_000}
    poor["legal_actions"].append({"kind": "tavern_talk", "legal": True, "params": {}})
    word = brain._maybe_tavern(View(poor))
    assert word is not None and word["kind"] == "tavern_talk"
    rich = _obs(day=3, credits=80_000)
    rich["trade_summary"] = {"total_profit_cr": 500_000}
    paid = brain._maybe_tavern(View(rich))
    assert paid is not None and paid["args"]["topic"] == "trader"
