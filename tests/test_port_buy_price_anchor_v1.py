"""v311-port-buy-price-v1 (NOTE 69). A hungry buying port pays the live anchor.

Live v3.34b day 1 (REPORT.md row 94, REPORT2.md:24/32): fuel 34.9-40.65,
organics 62-75, equipment 100.7-105. StarDock equipment was 105 at 51%
remaining demand and about 100.8 at 37%. MCIC still spreads a quote, so the
day-1 band below is the anchor times the buy-MCIC span, not only that sample.

PORT_BUY_PRICE_ANCHOR_MODE stays legacy. V311_PROFILE turns it on. The sell
side is unchanged.
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
# Anchor times buy MCIC -1 .. -100 (about 0.676x .. 1.22x) at experience 0.
# Live sample sits inside this: fuel 34.9-40.65, organics 62-75, equipment 100.7-105.
MCIC_BAND = {
    FUEL: (26, 46),
    ORG: (49, 89),
    EQ: (69, 124),
}
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


def test_day1_hungry_buy_quotes_sit_in_the_mcic_band(monkeypatch) -> None:
    """Live v3.34b day 1: fuel 34.9-40.65, organics 62-75, equipment 100.7-105.

    MCIC band used here (experience 0, hungry, buy MCIC -100..-1): fuel 26-46,
    organics 49-89, equipment 69-124. A default MCIC (-60) hungry quote is the
    anchor itself, inside the live sample.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    for commodity, anchor in ((FUEL, 38), (ORG, 73), (EQ, 102)):
        lo = round(anchor * _mcic_mult(-1))
        hi = round(anchor * _mcic_mult(K.PORT_MCIC_MIN))
        assert (lo, hi) == MCIC_BAND[commodity]
        assert port_buy_price(_buyer(0), commodity, 0) == anchor
        assert port_buy_price(_buyer(0), commodity, 1000) > anchor
        low, high = LIVE_SAMPLE[commodity]
        assert low <= anchor <= high
        assert lo <= port_buy_price(_buyer(0, mcic=-1), commodity, 0) <= hi
        assert lo <= port_buy_price(_buyer(0, mcic=K.PORT_MCIC_MIN), commodity, 0) <= hi

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
            lo, hi = MCIC_BAND[commodity]
            assert lo <= price <= hi, (commodity, price, port.mcic.get(commodity))
            seen[commodity].append(price)
    assert all(seen.values())


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
    """Live v3.34b day-1 equipment is 100.7-105, not about 1.93x the anchor.

    A plant that quotes anchor * 1.45/0.75 on an empty buyer (equipment 197) fails.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    hungry = _buyer(0)
    assert port_buy_price(hungry, EQ, 0) == 102
    assert port_buy_price(hungry, FUEL, 0) == 38
    assert port_buy_price(hungry, ORG, 0) == 73
    assert round(102 * 1.45 / 0.75) == 197
    assert port_buy_price(hungry, EQ, 0) != 197


def test_sell_side_keeps_the_full_port_screen_anchors(monkeypatch) -> None:
    """Sell quotes were checked and left alone.

    The recorded full-port sell screen is fuel 16, organics 35, equipment 36.
    A full seller at MCIC 50 still quotes those under the profile.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    seller = Port(
        class_id=PortClass.CLASS_9_SSS,
        stock={c: PortStock(current=1000, maximum=1000) for c in (FUEL, ORG, EQ)},
        mcic={c: K.PORT_MCIC_DEFAULT_SELL for c in (FUEL, ORG, EQ)},
    )
    assert port_sell_price(seller, FUEL, 0) == 16
    assert port_sell_price(seller, ORG, 0) == 35
    assert port_sell_price(seller, EQ, 0) == 36


def test_haggle_window_still_tracks_the_listed_quote(monkeypatch) -> None:
    """MCIC and the haggle window stay on top of the new anchor."""
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    port = _buyer(0, mcic=-90)
    listed = port_buy_price(port, EQ, 0)
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
    bought = False
    for commodity, stock in dock.stock.items():
        if not dock.buys(commodity):
            continue
        bought = True
        twin = Port(
            class_id=PortClass.CLASS_7_BBB,
            stock={commodity: stock},
            mcic={commodity: dock.mcic[commodity]},
        )
        assert port_buy_price(dock, commodity, 0) == port_buy_price(twin, commodity, 0)
        lo, hi = MCIC_BAND[commodity]
        assert lo <= port_buy_price(dock, commodity, 0) <= hi
    assert bought


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

    With V311_PROFILE on (the anchor switch on) every seat finishes with 0
    refused and the seats still sell at a profit. Day-10 net worth is reported
    next to the same run with the profile, and the switch, off.
    """
    assert K.V311_PROFILE == "legacy"
    off = _ten_day("legacy")
    on = _ten_day("v311")
    assert K.V311_PROFILE == "legacy"
    report = {"on": on, "off": off}
    assert all(_refused(row) == 0 for row in on.values()), report
    assert sum(row["realized_profit"] for row in on.values()) > 0, report
    assert sum(row["sells"] for row in on.values()) > 0, report
    print("NOTE69 day-10 net worth", report)
