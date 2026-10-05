"""The tw2002 money scale, and the legacy switch that puts the old numbers back."""

from __future__ import annotations

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.economy import port_buy_price, port_sell_price
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, Player, Port, PortClass, PortStock, Ship

FUEL = Commodity.FUEL_ORE
ORG = Commodity.ORGANICS
EQ = Commodity.EQUIPMENT

# economy2.html, 250 holds, 100 percent stock, MCIC 50 / -50, experience 0.
CHART_250 = {"fuel_ore": 5116, "organics": 10748, "equipment": 19720}
CHART_TRIP = 121.872


def _full(class_num: int, commodity: Commodity, mcic: int) -> Port:
    return Port(
        class_id=PortClass(class_num),
        stock={commodity: PortStock(current=2500, maximum=2500)},
        mcic={commodity: mcic},
    )


def _empty(class_num: int, commodity: Commodity, mcic: int) -> Port:
    return Port(
        class_id=PortClass(class_num),
        stock={commodity: PortStock(current=0, maximum=2500)},
        mcic={commodity: mcic},
    )


def _spread(commodity: Commodity) -> int:
    # Class 3 sells fuel and buys the other two. Class 1 does the opposite.
    # Both ports at the chart's 100 percent: the seller full, the buyer empty
    # (economy2: a buying port with 0 product is at 100 percent).
    # ECONOMY_CALIBRATION.md.
    if commodity is FUEL:
        seller_class, buyer_class = 3, 1
    else:
        seller_class, buyer_class = 1, 3
    seller = _full(seller_class, commodity, 50)
    buyer = _empty(buyer_class, commodity, -50)
    return port_buy_price(buyer, commodity) - port_sell_price(seller, commodity)


def test_legacy_quotes_and_ship_costs_match_ae1d5c4() -> None:
    saved = K.ECONOMY_SCALE_MODE
    K.ECONOMY_SCALE_MODE = "legacy"
    try:
        assert port_sell_price(_full(3, FUEL, 50), FUEL) == 11
        assert port_buy_price(_full(1, FUEL, -50), FUEL) == 13
        assert port_sell_price(_full(1, ORG, 50), ORG) == 15
        assert port_buy_price(_full(3, ORG, -50), ORG) == 18
        assert port_sell_price(_full(1, EQ, 50), EQ) == 22
        assert port_buy_price(_full(3, EQ, -50), EQ) == 26
        for key, spec in K.SHIP_SPECS.items():
            assert K.ship_cost(key) == int(spec["cost"])
        assert K.fighter_unit_price(4) == K.FIGHTER_COST == 50
        assert K.hold_total_price("scout_marauder", 10, 3, 4) == 800 * 3
    finally:
        K.ECONOMY_SCALE_MODE = saved


def test_chart_spreads_and_the_fuel_integer_gap() -> None:
    assert K.ECONOMY_SCALE_MODE == "tw2002"
    got = {
        "fuel_ore": _spread(FUEL) * 250,
        "organics": _spread(ORG) * 250,
        "equipment": _spread(EQ) * 250,
    }
    assert got["organics"] == 10750
    assert got["equipment"] == 19750
    assert abs(got["organics"] - CHART_250["organics"]) / CHART_250["organics"] < 0.02
    assert abs(got["equipment"] - CHART_250["equipment"]) / CHART_250["equipment"] < 0.02
    # One credit of spread is 250 on the 250-hold chart. 5000 (base 26) is
    # closer than 5250 (base 27).
    fuel_err = abs(got["fuel_ore"] - CHART_250["fuel_ore"]) / CHART_250["fuel_ore"]
    assert got["fuel_ore"] == 5000
    assert fuel_err < 0.023
    assert fuel_err > 0.02
    for commodity, base in K.COMMODITY_BASE_PRICE.items():
        assert _spread(Commodity(commodity)) < base * K.PORT_UNIT_PRICE_MAX_MULT


def test_no_class_pair_prints_more_than_the_chart_trip() -> None:
    names = (FUEL, ORG, EQ)
    best = 0
    for left in range(1, 8):
        for right in range(1, 8):
            profit = 0
            for index, commodity in enumerate(names):
                if K.PORT_CLASS_TRADES[left][index] is False and K.PORT_CLASS_TRADES[right][index] is True:
                    profit += _spread(commodity)
            best = max(best, profit)
    assert best <= CHART_TRIP * 1.02
    assert best == _spread(ORG) + _spread(EQ)


def test_mode_switch_changes_the_next_quote() -> None:
    saved = K.ECONOMY_SCALE_MODE
    try:
        K.ECONOMY_SCALE_MODE = "tw2002"
        assert K.COMMODITY_BASE_PRICE["equipment"] == 102
        assert dict(K.COMMODITY_BASE_PRICE.items())["fuel_ore"] == 26
        K.ECONOMY_SCALE_MODE = "legacy"
        assert K.COMMODITY_BASE_PRICE["equipment"] == 36
        assert K.COMMODITY_BASE_PRICE.get("organics") == 25
    finally:
        K.ECONOMY_SCALE_MODE = saved


def test_fighter_wave_stays_inside_160_to_239() -> None:
    prices = [K.fighter_unit_price(day) for day in range(87)]
    assert min(prices) >= 160
    assert max(prices) <= 239
    assert K.fighter_unit_price(0) == 200
    assert max(prices) >= 230
    assert K.FIGHTER_COST == 50


def test_hold_formula_matches_the_page_shape() -> None:
    def page(base: int, holds: int) -> int:
        return base * holds + 20 * holds * (holds - 1) // 2

    assert page(200, 100) == 119_000
    assert K.hold_day_base(0) == 151
    assert K.hold_day_base(9) == 249
    assert K.hold_day_base(18) == 151
    day = 0
    base = K.hold_day_base(day)
    assert K.hold_total_price("merchant_cruiser", 0, 100, day) == page(base, 100)
    running = 0
    for held in range(20):
        step = K.hold_next_price("cargotran", held, day)
        assert step == base + 20 * held
        running += step
    assert running == K.hold_total_price("cargotran", 0, 20, day)
    assert K.SHIP_SPECS["battleship"]["holds"] == 80
    assert K.SHIP_SPECS["battleship"]["cost"] == 880_000
    assert K.ship_cost("battleship") == 88_500
    assert K.PORT_SPAWN_PROBABILITY == 0.65


def test_stardock_shows_the_wave_and_charges_the_hold_formula() -> None:
    universe = generate_universe(
        GameConfig(seed=11, universe_size=25, enable_planets=False, enable_ferrengi=False)
    )
    player = Player(id="P9", name="Trader", ship=Ship(), credits=500_000)
    player.sector_id = 1
    universe.players["P9"] = player
    universe.sectors[1].occupant_ids.append("P9")
    day = int(universe.day)
    rows = legal_actions(universe, "P9")
    blob = " ".join(str(row.model_dump()) for row in rows).lower()
    assert "mcic" not in blob
    assert "productivity" not in blob
    equip = next(row for row in rows if row.kind == "buy_equip")
    prices = equip.params["item"]["unit_price_by"]
    class_key = player.ship.ship_class.value
    assert prices["fighters"] == K.fighter_unit_price(day)
    assert prices["shields"] == 10
    assert prices["holds"] == K.hold_next_price(class_key, player.ship.holds, day)
    ships = next(row for row in rows if row.kind == "buy_ship")
    trade_in = int(K.ship_cost(class_key) * 0.25)
    assert ships.params["ship_class"]["trade_in"] == trade_in
    assert ships.params["ship_class"]["net_cost_by"]["scout_marauder"] == (
        K.ship_cost("scout_marauder") - trade_in
    )
    before = player.credits
    held = player.ship.holds
    result = apply_action(
        universe, "P9", Action(kind=ActionKind.BUY_EQUIP, args={"item": "holds", "qty": 2})
    )
    assert result.ok
    assert player.ship.holds == held + 2
    assert before - player.credits == K.hold_total_price(class_key, held, 2, day)
