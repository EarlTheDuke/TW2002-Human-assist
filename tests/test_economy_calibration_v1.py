"""Economy calibration bands (economy-calibration-v1).

Every number here goes through the real engine: ``apply_action`` trades on a
generated universe, ``tick_day`` for the daily refill, and the fogged N3
replay for the ten-day growth band. See
docs/playtests/ports/ECONOMY_CALIBRATION.md for the sources and the table.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe, tick_day
from tw2k.engine import constants as K
from tw2k.engine.economy import haggle_bound
from tw2k.engine.models import Commodity, Player, Port, PortClass, PortStock, Ship

ROOT = Path(__file__).resolve().parents[1]
COMMODITIES = ("fuel_ore", "organics", "equipment")

# economy2.html, 250-hold totals divided by 250. Experience 0, no haggle,
# both ports at 100 percent: the selling port full, the buying port empty
# (economy2: a buying port with 0 product is at 100 percent).
CHART_SELL = {"fuel_ore": 3675 / 250, "organics": 6964 / 250, "equipment": 12190 / 250}  # MCIC 50
CHART_BUY = {"fuel_ore": 8791 / 250, "organics": 17712 / 250, "equipment": 31910 / 250}  # MCIC -50
CHART_SPREAD = {c: CHART_BUY[c] - CHART_SELL[c] for c in COMMODITIES}

# Best original trade per hold: experience 1000 (11,760 -> 9,097 sell side,
# 32,405 -> 34,646 buy side), cheapest published sell column and best
# published buy column (fuel 90 / -90, organics 75 / -75, equipment 65 / -65).
_EXP_SELL = 9097 / 11760
_EXP_BUY = 34646 / 32405
ORIGINAL_BEST = {
    "fuel_ore": 10678 / 250 * _EXP_BUY - 1092 / 250 * _EXP_SELL,
    "organics": 20144 / 250 * _EXP_BUY - 3768 / 250 * _EXP_SELL,
    "equipment": 34647 / 250 * _EXP_BUY - 8787 / 250 * _EXP_SELL,
}
# Our MCIC roll reaches 1 and -100; the published ranges stop at 65 / 75 / 90.
# That wider roll is the documented allowance on the best-trade ceiling.
BEST_CEILING = 1.35
BEST_FLOOR = 0.80

# The one-trade table in ECONOMY_CALIBRATION.md (port sells at, port buys at).
DOC_TABLE = {"fuel_ore": (16, 36), "organics": (34, 77), "equipment": (61, 140)}

# Port classes: class 3 sells fuel and buys the other two; class 1 is the mirror.
_SELLER = {"fuel_ore": 3, "organics": 1, "equipment": 1}
_BUYER = {"fuel_ore": 1, "organics": 3, "equipment": 3}


def _pair_universe():
    u = generate_universe(GameConfig(seed=4242, universe_size=40, enable_planets=False, enable_ferrengi=False))
    for sid in sorted(u.sectors):
        if sid in K.FEDSPACE_SECTORS:
            continue
        for w in u.sectors[sid].warps:
            if w not in K.FEDSPACE_SECTORS and w != sid:
                return u, sid, w
    raise AssertionError("no adjacent pair outside FedSpace")


def _one_trade(commodity: str, holds: int, *, sell_mcic: int = 50, buy_mcic: int = -50,
               experience: int = 0, counter: int | None = None) -> dict:
    """Buy a full hold at a full selling port, warp one hop, sell at an empty buying port."""
    c = Commodity(commodity)
    u, a, b = _pair_universe()
    u.sectors[a].port = Port(class_id=PortClass(_SELLER[commodity]), name="Seller",
                             stock={c: PortStock(current=3000, maximum=3000)},
                             mcic={c: sell_mcic}, productivity={c: 0})
    u.sectors[b].port = Port(class_id=PortClass(_BUYER[commodity]), name="Buyer",
                             stock={c: PortStock(current=0, maximum=3000)},
                             mcic={c: buy_mcic}, productivity={c: 0})
    p = Player(id="P1", name="Trader", agent_kind="external", sector_id=a, credits=50_000_000,
               ship=Ship(holds=holds))
    p.experience = experience
    u.players["P1"] = p
    u.sectors[a].occupant_ids.append("P1")
    buy = apply_action(u, "P1", Action(kind=ActionKind.TRADE, args={"commodity": commodity, "qty": holds, "side": "buy"}))
    assert buy.ok, buy.error
    bought = dict(p.trade_log[-1])
    moved = apply_action(u, "P1", Action(kind=ActionKind.WARP, args={"target": b}))
    assert moved.ok, moved.error
    args = {"commodity": commodity, "qty": holds, "side": "sell"}
    if counter is not None:
        args["unit_price"] = counter
    sell = apply_action(u, "P1", Action(kind=ActionKind.TRADE, args=args))
    out = {"buy": bought["unit"], "units": holds, "ok": sell.ok, "error": sell.error, "credits": p.credits}
    if sell.ok:
        sold = p.trade_log[-1]
        out.update(sell=sold["unit"], realized=sold["realized_profit"],
                   per_unit=sold["realized_profit"] / holds)
    return out


@pytest.mark.parametrize("commodity", COMMODITIES)
@pytest.mark.parametrize("holds", (20, 75, 250))
def test_one_trade_profit_sits_on_the_original_spread(commodity: str, holds: int) -> None:
    assert K.ECONOMY_SCALE_MODE == "tw2002"
    r = _one_trade(commodity, holds)
    assert r["ok"] and r["units"] == holds
    # Profit per hold: within 5 percent of the economy2 spread.
    assert abs(r["per_unit"] - CHART_SPREAD[commodity]) <= 0.05 * CHART_SPREAD[commodity], r
    # Each quote is on the original scale too (one base cannot hit both sides).
    assert 0.80 <= r["buy"] / CHART_SELL[commodity] <= 1.30, r
    assert 0.80 <= r["sell"] / CHART_BUY[commodity] <= 1.30, r
    assert r["realized"] == (r["sell"] - r["buy"]) * holds


def test_doc_table_matches_the_engine() -> None:
    for commodity, (sell_at, buy_at) in DOC_TABLE.items():
        r = _one_trade(commodity, 75)
        assert (r["buy"], r["sell"]) == (sell_at, buy_at), (commodity, r)


@pytest.mark.parametrize("commodity", COMMODITIES)
def test_best_trade_stays_inside_the_original_best_band(commodity: str) -> None:
    r = _one_trade(commodity, 75, sell_mcic=1, buy_mcic=K.PORT_MCIC_MIN, experience=K.PORT_PRICE_EXPERIENCE_CAP)
    assert r["ok"]
    best = ORIGINAL_BEST[commodity]
    assert BEST_FLOOR * best <= r["per_unit"] <= BEST_CEILING * best, (r, best)


def test_haggle_closes_at_the_limit_and_not_one_credit_past() -> None:
    listed = _one_trade("equipment", 75)["sell"]
    bound = haggle_bound(listed, -50, "sell")
    assert bound > listed
    won = _one_trade("equipment", 75, counter=bound)
    assert won["ok"] and won["sell"] == bound
    assert won["per_unit"] == bound - won["buy"]
    # Ceiling: the best published counter (149 percent) on the chart quote.
    assert won["per_unit"] <= CHART_BUY["equipment"] * 1.49 - CHART_SELL["equipment"]
    lost = _one_trade("equipment", 75, counter=bound + 1)
    assert not lost["ok"] and lost["error"] == "the port lost patience"
    assert lost["credits"] == 50_000_000 - lost["buy"] * 75


def test_daily_refill_is_five_percent_of_productivity_and_one_day_of_turns() -> None:
    u, a, _b = _pair_universe()
    c = Commodity.EQUIPMENT
    u.sectors[a].port = Port(class_id=PortClass(1), name="Refill",
                             stock={c: PortStock(current=0, maximum=4000)},
                             mcic={c: 50}, productivity={c: 3000})
    p = Player(id="P1", name="Trader", agent_kind="external", sector_id=a, credits=1000)
    u.players["P1"] = p
    u.sectors[a].occupant_ids.append("P1")
    p.turns_today = 400
    tick_day(u)
    gain = u.sectors[a].port.stock[c].current
    assert gain == round(3000 * K.PORT_REGEN_PER_DAY) == 150
    assert K.PORT_REGEN_PER_DAY == 0.05
    assert p.turns_per_day == K.STARTING_TURNS_PER_DAY == 1000
    assert p.turns_per_day - p.turns_today == 1000
    spent = 0
    while apply_action(u, "P1", Action(kind=ActionKind.WAIT, args={})).ok:
        spent += 1
        assert spent <= 2000
    assert spent == 1000 // K.TURN_COST["wait"]


def test_legacy_switch_keeps_the_old_one_trade() -> None:
    saved = K.ECONOMY_SCALE_MODE
    K.ECONOMY_SCALE_MODE = "legacy"
    try:
        r = _one_trade("equipment", 75)
        assert (r["buy"], r["sell"]) == (22, 49)
    finally:
        K.ECONOMY_SCALE_MODE = saved


def _acceptance():
    spec = importlib.util.spec_from_file_location("seat_brain_acceptance", ROOT / "scripts" / "seat_brain_acceptance.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_n3_ten_day_growth_sits_inside_the_band() -> None:
    """Seed 250925, solo N3, 1000 turns a day, 20k start: the measured day-10 band."""
    from tw2k.agents.seat_brain import SeatBrain

    mod = _acceptance()
    r = mod.prove_growth_replay(seed=mod.N3_BENCH_SEED, brain=SeatBrain())
    assert r["rejected"] == 0
    assert mod.N3_NET_WORTH_FLOOR <= r["net_worth"] <= mod.N3_NET_WORTH_CEILING, r["net_worth"]
    assert r["units_sold"] > 0
    per_unit = r["realized_profit"] / r["units_sold"]
    assert mod.N3_PROFIT_PER_UNIT_FLOOR <= per_unit <= mod.N3_PROFIT_PER_UNIT_CEILING, per_unit
