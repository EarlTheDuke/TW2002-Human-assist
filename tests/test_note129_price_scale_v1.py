"""NOTE 129 GAP 2.5. Day-1 quotes differ from the economy2 chart anchors.

Capture: docs/playtests/twgs-live/price-scale.txt
TWGS v2.20b, Trade Wars 2002 3.34b, game TW Test Game 2, 19 Oct 2026.
Experience 0 or 1. The screen did not print MCIC.

PRICE_SCALE_MODE already quotes the economy2 100% chart: a full selling port
at MCIC 50, and an empty buying port at MCIC -50. Those 250-hold totals stay.
The day-1 screen is not a replacement chart. Organics buying was 94 percent,
equipment buying was not quoted, and MCIC was not printed. No new formula.
"""

from __future__ import annotations

from pathlib import Path

from tw2k.engine import constants as K
from tw2k.engine.economy import port_buy_price, port_sell_price
from tw2k.engine.models import Commodity, Port, PortClass, PortStock

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "docs/playtests/twgs-live/price-scale.txt"

# side, commodity, percent of max, screen credits, chart unit at the economy2 point.
QUOTES = (
    ("sell", Commodity.FUEL_ORE, 100, 11, 15),
    ("buy", Commodity.FUEL_ORE, 100, 27, 35),
    ("sell", Commodity.ORGANICS, 100, 31, 28),
    ("buy", Commodity.ORGANICS, 94, 66, 71),
    ("sell", Commodity.EQUIPMENT, 100, 56, 49),
)

# In file order, so a swapped quote fails this test.
CAPTURE_LINES = (
    "Experience 0 or 1. The screen never printed MCIC. The column is \"% of max\".",
    "Class 3 New Mytus, sector 2, Fuel Ore Selling 2710, 100%:",
    "We'll sell them for 11 credits.",
    "Class 1 Salayna Annex, sector 6, Fuel Ore Buying 1260, 100%, 1 on board:",
    "We'll buy them for 27 credits.",
    "Same port, Equipment Selling 1860, 100%, asked for 1:",
    "We'll sell them for 56 credits.",
    "Class 2 Klingenstjerna Primus, sector 157, Organics Selling 1540, 100%:",
    "We'll sell them for 31 credits.",
    "Class 9 Stargate Alpha I, sector 144, Organics Buying 2836, 94%, 1 on board:",
    "We'll buy them for 66 credits.",
    "Same screen: Fuel Ore Buying 2836 94%. Equipment Buying 2406 80%. Those two were not quoted.",
)


def _port(commodity: Commodity, current: int, maximum: int, mcic: int) -> Port:
    return Port(
        class_id=PortClass(1),
        stock={commodity: PortStock(current=current, maximum=maximum)},
        mcic={commodity: mcic},
    )


def _quoted(port: Port, commodity: Commodity, side: str, experience: int) -> int:
    if side == "sell":
        return port_sell_price(port, commodity, experience)
    return port_buy_price(port, commodity, experience)


def _holds(side: str, percent: int) -> tuple[int, ...]:
    """On-hand units, out of 100, for each reading of "% of max".

    Selling 100% is a full hold. Buying 100% is either a full hold or the
    economy2 point, where on-hand 0 means the port is at 100% and ready to buy.
    """
    if side == "sell":
        return (percent,)
    return (percent, 100 - percent)


def test_capture_file_holds_the_day1_quotes() -> None:
    text = CAPTURE.read_text(encoding="utf-8")
    cursor = 0
    for line in CAPTURE_LINES:
        found = text.find(line, cursor)
        assert found >= cursor, line
        cursor = found + len(line)


def test_chart_anchors_stay_and_the_screen_is_different() -> None:
    assert K.PRICE_SCALE_MODE == "legacy"
    assert K.PRICE_SCALE_SELL_250 == {"fuel_ore": 3_675, "organics": 6_964, "equipment": 12_190}
    assert K.PRICE_SCALE_BUY_250 == {"fuel_ore": 8_791, "organics": 17_712, "equipment": 31_910}
    sell = {key: K.price_scale_unit(total) for key, total in K.PRICE_SCALE_SELL_250.items()}
    buy = {key: K.price_scale_unit(total) for key, total in K.PRICE_SCALE_BUY_250.items()}
    assert sell == {"fuel_ore": 15, "organics": 28, "equipment": 49}
    assert buy == {"fuel_ore": 35, "organics": 71, "equipment": 128}
    for side, commodity, _percent, screen, chart in QUOTES:
        assert screen != chart
        table = sell if side == "sell" else buy
        assert table[commodity.value] == chart
    bought_at_100 = {
        commodity
        for side, commodity, percent, _screen, _chart in QUOTES
        if side == "buy" and percent == 100
    }
    assert Commodity.EQUIPMENT not in bought_at_100


def test_live_chart_point_is_not_the_day1_screen(monkeypatch) -> None:
    """A full seller at MCIC 50, and an empty buyer at MCIC -50, stay on the chart.

    The stored flag stays legacy. Live mode and the v3.11 profile both use it.
    Experience 0 and 1 are the capture's range. Neither matches the screen.
    """
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    for profile, mode in (("legacy", "live"), ("v311", "legacy")):
        monkeypatch.setattr(K, "V311_PROFILE", profile)
        monkeypatch.setattr(K, "PRICE_SCALE_MODE", mode)
        assert K.price_scale_live() is True
        assert K.PRICE_SCALE_SELL_250["fuel_ore"] == 3_675
        for side, commodity, percent, screen, chart in QUOTES:
            if side == "sell":
                if percent != 100:
                    continue
                port = _port(commodity, 100, 100, K.PRICE_SCALE_SELL_MCIC)
            else:
                # Chart buy is an empty port, not the capture's percent column.
                port = _port(commodity, 0, 100, K.PRICE_SCALE_BUY_MCIC)
            for experience in (0, 1):
                got = _quoted(port, commodity, side, experience)
                assert got == chart
                assert got != screen


def test_captured_percents_miss_the_screen_on_every_existing_slope(monkeypatch) -> None:
    """The existing slope, at the chart MCIC, does not land on the screen.

    Checked with the scale off, with the scale on, and with the v3.11 profile
    (that profile also turns the drain curve on). A hit would be a clean
    alignment. There is none, so the anchors stay.
    """
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    setups = (
        ("legacy", "legacy"),
        ("legacy", "live"),
        ("v311", "legacy"),
    )
    for profile, mode in setups:
        monkeypatch.setattr(K, "V311_PROFILE", profile)
        monkeypatch.setattr(K, "PRICE_SCALE_MODE", mode)
        for side, commodity, percent, screen, chart in QUOTES:
            mcic = K.PRICE_SCALE_SELL_MCIC if side == "sell" else K.PRICE_SCALE_BUY_MCIC
            for current in _holds(side, percent):
                port = _port(commodity, current, 100, mcic)
                for experience in (0, 1):
                    got = _quoted(port, commodity, side, experience)
                    assert got != screen
                    on_chart = (side == "sell" and current == 100) or (side == "buy" and current == 0)
                    if K.price_scale_live() and on_chart:
                        assert got == chart
