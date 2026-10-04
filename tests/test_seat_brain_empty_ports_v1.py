"""Empty shelves, and hull and fighter prices that match what StarDock charges."""

from __future__ import annotations

from pathlib import Path

from tw2k.agents.seat_acceptance import synthetic_obs, validate_action
from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View, _defense_value
from tw2k.engine.constants import fighter_unit_price, ship_cost

ROOT = Path(__file__).resolve().parents[1]
BRAIN = ROOT / "src" / "tw2k" / "agents" / "seat_brain.py"


def _trade(commodity: str, side: str, qty: int, price: int) -> dict:
    return {
        "kind": "trade", "legal": True, "reason": None, "detail": "precise",
        "params": {
            "commodity": {"buy_choices": [commodity] if side == "buy" else [],
                          "sell_choices": [commodity] if side == "sell" else [],
                          "choices": [commodity]},
            "qty": {"max_by": {commodity: {side: qty}}},
            "unit_price": {"listed_by": {commodity: {side: price}}},
        },
    }


def test_empty_shelf_is_not_bought_and_hides_port_math() -> None:
    obs = synthetic_obs(sector=4, credits=20_000, ship_class="merchant_cruiser", holds=20)
    obs["known_ports"] = [{
        "sector_id": 4,
        "class": "SSB",
        "stock": {"fuel_ore": {"side": "sells_to_player", "price": 107, "current": 0, "max": 2500}},
    }]
    obs["legal_actions"] = [la for la in obs["legal_actions"] if la["kind"] != "trade"]
    obs["legal_actions"].append(_trade("fuel_ore", "buy", 0, 107))
    action = SeatBrain().decide(obs)
    assert validate_action(obs, action) == []
    assert not (action["kind"] == "trade" and action.get("args", {}).get("side") == "buy")
    thought = action.get("thought", "").lower()
    assert "mcic" not in thought
    assert "productivity" not in thought
    assert "haggle" not in thought


def test_a_fresh_legal_qty_buys_even_if_memory_says_empty() -> None:
    obs = synthetic_obs(sector=4, credits=20_000, ship_class="merchant_cruiser", holds=20)
    obs["known_ports"] = [
        {"sector_id": 4, "class": "SSB", "stock": {
            "fuel_ore": {"side": "sells_to_player", "price": 107, "current": 0, "max": 2500},
        }},
        {"sector_id": 6, "class": "BSS", "stock": {
            "fuel_ore": {"side": "buys_from_player", "price": 200, "current": 10, "max": 2500},
        }},
    ]
    obs["legal_actions"] = [la for la in obs["legal_actions"] if la["kind"] != "trade"]
    obs["legal_actions"].append(_trade("fuel_ore", "buy", 10, 107))
    action = SeatBrain().decide(obs)
    assert action["kind"] == "trade"
    assert action["args"]["side"] == "buy"
    assert action["args"]["commodity"] == "fuel_ore"


def test_a_stocked_seller_is_the_route() -> None:
    obs = synthetic_obs(sector=4, credits=20_000, ship_class="merchant_cruiser", holds=20)
    obs["known_warps"] = {"4": [5, 6], "5": [4], "6": [4]}
    obs["known_ports"] = [
        {"sector_id": 5, "class": "SSB", "stock": {
            "fuel_ore": {"side": "sells_to_player", "price": 107, "current": 0, "max": 2500},
        }},
        {"sector_id": 6, "class": "SBB", "stock": {
            "fuel_ore": {"side": "sells_to_player", "price": 107, "current": 40, "max": 2500},
            "organics": {"side": "buys_from_player", "price": 276, "current": 10, "max": 2500},
        }},
        {"sector_id": 4, "class": "BSS", "stock": {
            "fuel_ore": {"side": "buys_from_player", "price": 127, "current": 10, "max": 2500},
        }},
    ]
    brain = SeatBrain()
    brain.mem = SeatMemory()
    pair = brain._best_buy_pair(View(obs))
    assert pair is not None
    assert pair[0] == 6
    assert pair[1] == 4


def test_cargotran_net_is_the_yard_price() -> None:
    obs = synthetic_obs(sector=4, credits=80_000, ship_class="merchant_cruiser", holds=20)
    net = SeatBrain()._cargotran_net(View(obs))
    expect = ship_cost("cargotran") - int(ship_cost("merchant_cruiser") * 0.25)
    assert net == expect == 41_625


def test_unaffordable_cargotran_is_not_sent() -> None:
    obs = synthetic_obs(sector=1, credits=10_000, ship_class="merchant_cruiser", holds=20)
    obs["legal_actions"] = [la for la in obs["legal_actions"] if la["kind"] != "buy_ship"]
    obs["legal_actions"].append({
        "kind": "buy_ship", "legal": True, "reason": None, "detail": "precise",
        "params": {"ship_class": {
            "type": "str", "required": True, "choices": ["cargotran"],
            "net_cost_by": {"cargotran": 41_625}, "trade_in": 10_325,
        }},
    })
    action = SeatBrain().decide(obs)
    assert action["kind"] != "buy_ship"
    assert validate_action(obs, action) == []


def test_gift_math_uses_the_fighter_wave_and_the_file_drops_the_flat_50() -> None:
    assert _defense_value(2, day=0) == 0
    assert fighter_unit_price(0) == 200
    text = BRAIN.read_text(encoding="utf-8")
    assert "FIGHTER_COST" not in text
    assert "fighter_unit_price" in text
    assert "ship_cost(" in text
