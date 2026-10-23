"""v311-port-buy-price-v1 (NOTE 69) and the chart that wins under the profile (NOTE 112).

Live v3.34b day 1 (REPORT.md row 94, REPORT2.md:24/32): fuel 34.9-40.65,
organics 62-75, equipment 100.7-105. StarDock equipment was 105 at 51%
remaining demand and about 100.8 at 37%. Those figures are the hungry screen
anchors when the buy-price anchor is on and the economy2 chart is off.

PORT_BUY_PRICE_ANCHOR_MODE stays legacy. V311_PROFILE turns that anchor on and
also turns the price-scale helper on. The chart is checked first, so a
profile-on quote is the economy2 unit plus the same stock and MCIC slope.
An empty buyer at the default MCIC (-60) is fuel 37, organics 75, equipment
135. The chart point itself is MCIC -50: fuel 35, organics 71, equipment 128.
Seed 41 StarDock equipment is 127 on that slope. The screen band stopped at 124
because it was round(102 * 1.22), the equipment screen anchor at MCIC -100.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.economy import haggle_bound, haggle_room_pct, port_buy_price, port_sell_price
from tw2k.engine.models import Commodity, Port, PortClass, PortStock

ROOT = Path(__file__).resolve().parents[1]
FUEL = Commodity.FUEL_ORE
ORG = Commodity.ORGANICS
EQ = Commodity.EQUIPMENT
# Screen anchor times buy MCIC -1 .. -100 (about 0.676x .. 1.22x) at experience 0.
# Live sample sits inside this: fuel 34.9-40.65, organics 62-75, equipment 100.7-105.
SCREEN_ANCHOR = {FUEL: 38, ORG: 73, EQ: 102}
MCIC_BAND = {
    FUEL: (26, 46),
    ORG: (49, 89),
    EQ: (69, 124),
}
# Chart slope at an empty buyer. Chart MCIC is -50, so default MCIC -60 is
# unit / 0.945. Band ends are that same slope at MCIC -1 and MCIC -100.
CHART_HUNGRY = {FUEL: 37, ORG: 75, EQ: 135}
CHART_BAND = {
    FUEL: (25, 45),
    ORG: (51, 92),
    EQ: (91, 165),
}
# generate_universe seed 41, 40 sectors. StarDock buys all three, stock empty.
STARDOCK_SEED41 = {FUEL: 43, ORG: 66, EQ: 127}
LIVE_SAMPLE = {
    FUEL: (34.9, 40.65),
    ORG: (62.0, 75.0),
    EQ: (100.7, 105.0),
}


def _buyer(current: int, *, maximum: int = 1000, mcic: int = -60, class_id: PortClass = PortClass.CLASS_7_BBB) -> Port:
    stock = {c: PortStock(current=current, maximum=maximum) for c in (FUEL, ORG, EQ)}
    return Port(class_id=class_id, stock=stock, mcic={c: mcic for c in stock})


def _mcic_mult(mcic: int) -> float:
    return max(0.05, 1.0 + (K.PORT_MCIC_DEFAULT_BUY - mcic) * K.PORT_MCIC_POINT)


def _chart_mcic() -> float:
    return max(
        0.05,
        1.0 + (K.PORT_MCIC_DEFAULT_BUY - K.PRICE_SCALE_BUY_MCIC) * K.PORT_MCIC_POINT,
    )


def _chart_hungry(commodity: Commodity, mcic: int) -> int:
    unit = K.price_scale_unit(K.PRICE_SCALE_BUY_250[commodity.value])
    return round(unit * _mcic_mult(mcic) / _chart_mcic())


def _chart_off(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    monkeypatch.setattr(K, "PRICE_SCALE_MODE", "legacy")


def _full_seller() -> Port:
    return Port(
        class_id=PortClass.CLASS_9_SSS,
        stock={c: PortStock(current=1000, maximum=1000) for c in (FUEL, ORG, EQ)},
        mcic={c: K.PORT_MCIC_DEFAULT_SELL for c in (FUEL, ORG, EQ)},
    )


def _assert_hungry_universe_in_band(band: dict) -> None:
    universe = generate_universe(
        GameConfig(seed=41, universe_size=200, enable_ferrengi=False, enable_planets=False)
    )
    seen = {c: [] for c in (FUEL, ORG, EQ)}
    for sector in universe.sectors.values():
        port = sector.port
        if port is None or port.class_id == PortClass.FEDERAL:
            continue
        for commodity, stock in port.stock.items():
            if not port.buys(commodity):
                continue
            assert int(stock.current) == 0
            price = port_buy_price(port, commodity, 0)
            lo, hi = band[commodity]
            assert lo <= price <= hi, (commodity, price, port.mcic.get(commodity))
            seen[commodity].append(price)
    assert all(seen.values())


def test_switch_stays_legacy_until_the_profile(monkeypatch) -> None:
    assert K.PORT_BUY_PRICE_ANCHOR_MODE == "legacy"
    assert K.port_buy_price_anchor_on() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.PORT_BUY_PRICE_ANCHOR_MODE == "legacy"
    assert K.port_buy_price_anchor_on() is True


def test_legacy_hungry_quote_stays_on_the_193x_curve() -> None:
    """Switch off: an empty buyer still pays the full-hold anchor times 1.45/0.75."""
    _prior_port_price_mode = K.PORT_PRICE_MODE
    try:
        assert K.PORT_BUY_PRICE_ANCHOR_MODE == "legacy"
        prior = K.PORT_PRICE_MODE
        try:
            K.PORT_PRICE_MODE = "live"
            full = _buyer(1000)
            empty = _buyer(0)
            assert port_buy_price(full, FUEL) == 38
            assert port_buy_price(full, ORG) == 73
            assert port_buy_price(full, EQ) == 102
            assert port_buy_price(empty, EQ) == round(102 * 1.45 / 0.75)
            assert port_buy_price(empty, EQ) == 197
        finally:
            K.PORT_PRICE_MODE = prior
    finally:
        K.PORT_PRICE_MODE = _prior_port_price_mode


def test_screen_anchors_hold_when_the_chart_is_off(monkeypatch) -> None:
    """NOTE 69, chart off: a hungry default-MCIC quote is the screen anchor.

    Live v3.34b day 1 sits on that anchor: fuel 34.9-40.65, organics 62-75,
    equipment 100.7-105. The MCIC band is the anchor times buy MCIC -1..-100:
    fuel 26-46, organics 49-89, equipment 69-124.
    """
    _chart_off(monkeypatch)
    monkeypatch.setattr(K, "PORT_PRICE_MODE", "live")
    monkeypatch.setattr(K, "PORT_BUY_PRICE_ANCHOR_MODE", "live")
    assert K.price_scale_live() is False
    assert K.port_buy_price_anchor_on() is True
    for commodity, anchor in SCREEN_ANCHOR.items():
        lo = round(anchor * _mcic_mult(-1))
        hi = round(anchor * _mcic_mult(K.PORT_MCIC_MIN))
        assert (lo, hi) == MCIC_BAND[commodity]
        assert port_buy_price(_buyer(0), commodity, 0) == anchor
        assert port_buy_price(_buyer(0), commodity, 1000) > anchor
        low, high = LIVE_SAMPLE[commodity]
        assert low <= anchor <= high
        assert port_buy_price(_buyer(0, mcic=-1), commodity, 0) == lo
        assert port_buy_price(_buyer(0, mcic=K.PORT_MCIC_MIN), commodity, 0) == hi
    _assert_hungry_universe_in_band(MCIC_BAND)


def test_day1_hungry_buy_quotes_sit_in_the_mcic_band(monkeypatch) -> None:
    """Profile on: the chart slope, not the screen anchor.

    Empty buyer, experience 0, default MCIC -60: fuel 37, organics 75,
    equipment 135. MCIC -1 and MCIC -100 are the band ends: fuel 25-45,
    organics 51-92, equipment 91-165. Equipment 135 is the chart at MCIC -60.
    The v3.34b sample 100.7-105 is the screen anchor, covered above.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.price_scale_live() is True
    for commodity, quote in CHART_HUNGRY.items():
        assert _chart_hungry(commodity, -60) == quote
        assert _chart_hungry(commodity, -1) == CHART_BAND[commodity][0]
        assert _chart_hungry(commodity, K.PORT_MCIC_MIN) == CHART_BAND[commodity][1]
        assert port_buy_price(_buyer(0), commodity, 0) == quote
        assert port_buy_price(_buyer(0), commodity, 1000) > quote
        assert quote != SCREEN_ANCHOR[commodity]
        assert port_buy_price(_buyer(0, mcic=-1), commodity, 0) == CHART_BAND[commodity][0]
        assert port_buy_price(_buyer(0, mcic=K.PORT_MCIC_MIN), commodity, 0) == CHART_BAND[commodity][1]
    _assert_hungry_universe_in_band(CHART_BAND)


def test_filling_from_51_to_37_eases_under_ten_percent(monkeypatch) -> None:
    """Live v3.34b StarDock equipment: 105 at 51% remaining, about 100.8 at 37%.

    A port filled from 51% remaining demand to 37% eases by under 10%.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    maximum = 10_000
    at_51 = _buyer(4_900, maximum=maximum)  # 5,100 of 10,000 still wanted
    at_37 = _buyer(6_300, maximum=maximum)  # 3,700 of 10,000 still wanted
    before = port_buy_price(at_51, EQ, 0)
    after = port_buy_price(at_37, EQ, 0)
    assert after < before
    assert (before - after) / before < 0.10


def test_plant_restoring_the_193x_curve_fails(monkeypatch) -> None:
    """Profile on, an empty equipment buyer is the chart slope at MCIC -60 (135).

    A plant that quotes the screen anchor * 1.45/0.75 on an empty buyer
    (equipment 197) still fails. 135 is the chart unit 128 divided by the
    MCIC distance from -50 to -60.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    hungry = _buyer(0)
    assert port_buy_price(hungry, EQ, 0) == 135
    assert port_buy_price(hungry, FUEL, 0) == 37
    assert port_buy_price(hungry, ORG, 0) == 75
    assert round(102 * 1.45 / 0.75) == 197
    assert port_buy_price(hungry, EQ, 0) != 197


def test_sell_side_screen_anchors_when_the_chart_is_off(monkeypatch) -> None:
    """Chart off: a full seller at MCIC 50 quotes the recorded screen.

    Fuel 16, organics 35, equipment 36.
    """
    _chart_off(monkeypatch)
    monkeypatch.setattr(K, "PORT_PRICE_MODE", "live")
    seller = _full_seller()
    assert port_sell_price(seller, FUEL, 0) == 16
    assert port_sell_price(seller, ORG, 0) == 35
    assert port_sell_price(seller, EQ, 0) == 36


def test_profile_sell_side_quotes_the_chart(monkeypatch) -> None:
    """Profile on: a full seller at MCIC 50 quotes the economy2 chart point.

    Fuel 15, organics 28, equipment 49. The screen anchors stay 16, 35, and 36
    on the stored table, and this quote does not use them.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    seller = _full_seller()
    assert K.PORT_PRICE_LIVE_SELL_FULL == {"fuel_ore": 16, "organics": 35, "equipment": 36}
    assert port_sell_price(seller, FUEL, 0) == 15
    assert port_sell_price(seller, ORG, 0) == 28
    assert port_sell_price(seller, EQ, 0) == 49


def test_haggle_window_still_tracks_the_listed_quote(monkeypatch) -> None:
    """MCIC and the haggle window stay on top of the new anchor."""
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    port = _buyer(0, mcic=-90)
    listed = port_buy_price(port, EQ, 0)
    assert listed == 158
    assert listed != 102
    room = haggle_bound(listed, -90, "sell")
    assert room == max(listed, round(listed * haggle_room_pct(-90) / 100.0))
    assert room > listed


def test_stardock_buy_rows_follow_the_same_curve(monkeypatch) -> None:
    """StarDock's buy rows use the same remaining-demand curve as any other buyer."""
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    universe = generate_universe(
        GameConfig(seed=41, universe_size=40, enable_ferrengi=False, enable_planets=False)
    )
    dock = universe.sectors[K.STARDOCK_SECTOR].port
    assert dock is not None and dock.class_id == PortClass.STARDOCK
    bought: list[Commodity] = []
    for commodity, stock in dock.stock.items():
        if not dock.buys(commodity):
            continue
        bought.append(commodity)
        twin = Port(
            class_id=PortClass.CLASS_7_BBB,
            stock={commodity: stock},
            mcic={commodity: dock.mcic[commodity]},
        )
        price = port_buy_price(dock, commodity, 0)
        assert price == port_buy_price(twin, commodity, 0)
        assert price == STARDOCK_SEED41[commodity]
        lo, hi = CHART_BAND[commodity]
        assert lo <= price <= hi
    assert set(bought) == {FUEL, ORG, EQ}


def _runner():
    spec = importlib.util.spec_from_file_location(
        "run_scripted_match_note69", ROOT / "scripts" / "run_scripted_match.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ten_day(profile: str) -> dict:
    _prior_v311_profile = K.V311_PROFILE
    try:
        prior = K.V311_PROFILE
        try:
            K.V311_PROFILE = profile
            result = _runner().run_match(
                ["N3", "N2", "N1", "H"], seed=250925, days=10, reject_report=100)
        finally:
            K.V311_PROFILE = prior
        seats = {}
        for row in result["players"].values():
            seats[row["name"]] = {
                "net_worth": int(row["net_worth"]),
                "realized_profit": int(row["realized_profit"]),
                "rejected_validate": int(row["rejected_validate"]),
                "rejected_engine": int(row["rejected_engine"]),
                "rejected_top": list(row["rejected_top"]),
                "sells": int(row["sells"]),
                "exceptions": int(row["exceptions"]),
            }
        return seats
    finally:
        K.V311_PROFILE = _prior_v311_profile


def _refused(row: dict) -> int:
    """Engine and validator refusals. A haggle counter is the port's next offer, not a refusal."""
    refused = int(row["rejected_validate"]) + int(row["exceptions"])
    listed = 0
    for reason, count in row["rejected_top"]:
        listed += int(count)
        if not str(reason).startswith("trade: counter "):
            refused += int(count)
    hidden = int(row["rejected_engine"]) - listed
    return refused + max(0, hidden)


def test_ten_day_bots_still_profit_with_the_anchor_on() -> None:
    """10-day code-only run, seed 250925, seats N3 N2 N1 H.

    With V311_PROFILE on, the buy-price anchor and the economy2 chart are both
    on. A haggle counter is the port's next offer, not a refusal. NOTE 157's
    extra two-way lanes move this map, so the old no-route plot is gone. N3's
    four refusals are buys that ask for more empty holds than the ship has
    (5, 10, 25 and 30). None of them is a quote from the anchor. Every seat
    still sells at a profit. Day-10 net worth is reported next to the same run
    with the profile off.
    """
    assert K.V311_PROFILE == "legacy"
    off = _ten_day("legacy")
    on = _ten_day("v311")
    assert K.V311_PROFILE == "legacy"
    report = {"on": on, "off": off}
    # Playtest 3 (HAGGLE_ROUNDS_MODE, on under the profile): the cockpit seat
    # sells at the quote, so this map's run no longer meets the four short-hold
    # buys it used to. Row 221 (BIG_BANG_BUILT_MODE) builds more ports, which
    # moves the bots' trades: the refusals left are N3's three sells of an
    # empty Equipment/Organics hold (seed 250925), a holds slip by the planner,
    # never a haggle or a quote from the anchor.
    for seat, row in on.items():
        for reason, _count in row["rejected_top"]:
            assert "in your holds" in str(reason) or str(reason).startswith("trade: counter "), (seat, report)
    assert sum(_refused(row) for row in on.values()) <= 3, report
    assert sum(row["realized_profit"] for row in on.values()) > 0, report
    assert sum(row["sells"] for row in on.values()) > 0, report
    print("NOTE69 day-10 net worth", report)
