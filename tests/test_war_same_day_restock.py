"""Stocking fighters onto a planet does not buy that stack back the same day."""

from __future__ import annotations

from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View


def _obs() -> dict:
    return {
        "self_id": "P1",
        "day": 30,
        "credits": 150_000,
        "sector": {"id": 1},
        "ship": {"class": "battleship", "fighters": 0, "shields": 200},
        "legal_actions": [{
            "kind": "buy_equip",
            "legal": True,
            "params": {
                "item": {
                    "choices": ["fighters", "shields"],
                    "unit_price_by": {"fighters": 233, "shields": 167},
                },
                "qty": {"max_by": {"fighters": 400, "shields": 200}},
            },
        }],
    }


def _brain() -> SeatBrain:
    brain = SeatBrain()
    brain.mem = SeatMemory()
    brain.mem.hot_sectors.add(9)
    return brain


def test_a_same_day_stock_does_not_rebuy_fighters() -> None:
    brain = _brain()
    brain._war_stocked_day = 30
    action = brain._buy_defense(View(_obs()))
    assert action is None or action["args"].get("item") != "fighters"


def test_a_fresh_day_still_buys_the_fighter_floor() -> None:
    action = _brain()._buy_defense(View(_obs()))
    assert action is not None and action["args"]["item"] == "fighters"
    assert action["args"]["qty"] == 200
