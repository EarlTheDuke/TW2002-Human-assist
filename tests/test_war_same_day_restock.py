"""The last day does not buy back fighters that were just stocked on a planet."""

from __future__ import annotations

from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View


def _obs(*, day: int, max_days: int | None) -> dict:
    obs = {
        "self_id": "P1",
        "day": day,
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
    if max_days is not None:
        obs["max_days"] = max_days
    return obs


def _brain() -> SeatBrain:
    brain = SeatBrain()
    brain.mem = SeatMemory()
    brain.mem.hot_sectors.add(9)
    return brain


def test_the_last_day_does_not_rebuy_fighters_after_a_stock() -> None:
    brain = _brain()
    brain._war_stocked_day = 30
    action = brain._buy_defense(View(_obs(day=30, max_days=32)))
    assert action is None or action["args"].get("item") != "fighters"


def test_the_day_before_the_pad_still_rebuys() -> None:
    brain = _brain()
    brain._war_stocked_day = 29
    action = brain._buy_defense(View(_obs(day=29, max_days=32)))
    assert action is not None and action["args"]["item"] == "fighters"


def test_an_earlier_day_still_rebuys_the_floor_after_a_stock() -> None:
    brain = _brain()
    brain._war_stocked_day = 19
    action = brain._buy_defense(View(_obs(day=19, max_days=32)))
    assert action is not None and action["args"]["item"] == "fighters"
    assert action["args"]["qty"] == 200


def test_the_last_day_still_buys_fighters_when_nothing_was_stocked() -> None:
    action = _brain()._buy_defense(View(_obs(day=30, max_days=30)))
    assert action is not None and action["args"]["item"] == "fighters"
