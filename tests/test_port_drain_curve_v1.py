"""Row 224: the economy3 drain table and the economy2 10 percent restock.

economy3 Merf run, equipment, two 1,500-unit ports, MCIC 50/-50, experience 0:
trip 1 buy 2,889 sell 8,813 profit 5,923 at 100%; trip 10 buy 3,957 sell 7,774
profit 3,818 at 61%; trip 23 buy 5,614 sell 6,193 at 5%.
economy2 T-Edit: maximum 2610/950/2100, productivity 261/95/210 a day.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import economy as E
from tw2k.engine.models import Commodity

ECON3 = [  # (stock fraction, EQ buy, EQ sell)
    (1.00, 2889, 8813), (0.87, 3224, 8498), (0.74, 3582, 8057), (0.61, 3957, 7774),
    (0.48, 4396, 7401), (0.35, 4690, 7007), (0.22, 5078, 6696), (0.05, 5614, 6193),
]


def _ports(monkeypatch, profile):
    monkeypatch.setattr(K, "V311_PROFILE", profile)
    u = generate_universe(GameConfig(seed=5, universe_size=1000))
    c = Commodity.EQUIPMENT
    sell = next(s.port for s in u.sectors.values() if s.port and s.port.class_id.value not in (0, 9)
                and s.port.sells(c) and s.port.stock[c].maximum > 0)
    buy = next(s.port for s in u.sectors.values() if s.port and s.port.class_id.value not in (0, 9)
               and s.port.buys(c) and s.port.stock[c].maximum > 0)
    for port, mcic in ((sell, 50), (buy, -50)):
        port.mcic[c] = mcic
        port.stock[c].maximum = 1500
    return sell, buy, c


def _curve(sell, buy, c):
    out = []
    for frac, _b, _s in ECON3:
        sell.stock[c].current = round(1500 * frac)
        buy.stock[c].current = round(1500 * (1 - frac))
        out.append((E.port_sell_price(sell, c, 0), E.port_buy_price(buy, c, 0)))
    return out


def test_v311_follows_economy3_shape(monkeypatch):
    got = _curve(*_ports(monkeypatch, "v311"))
    b0, s0 = got[0]
    for (frac, eb, es), (b, s) in zip(ECON3, got):
        assert b / b0 == pytest.approx(eb / ECON3[0][1], abs=0.20), frac
        assert s / s0 == pytest.approx(es / ECON3[0][2], abs=0.10), frac
    assert [b for b, _ in got] == sorted(b for b, _ in got)
    assert [s for _, s in got] == sorted((s for _, s in got), reverse=True)
    ratio = (got[3][1] - got[3][0]) / (s0 - b0)
    assert 0.60 <= ratio <= 0.68  # economy3: 3,818 / 5,923 = 0.64


@pytest.mark.parametrize("c", [Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT])
def test_profit_share_at_61_each_product(monkeypatch, c):
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = generate_universe(GameConfig(seed=5, universe_size=1000))
    ports = [s.port for s in u.sectors.values() if s.port and s.port.class_id.value not in (0, 9)]
    sell = next(p for p in ports if p.sells(c)); buy = next(p for p in ports if p.buys(c))
    sell.mcic[c], buy.mcic[c] = 50, -50
    for p in (sell, buy):
        p.stock[c].maximum = 1500
    def profit(frac):
        sell.stock[c].current = round(1500 * frac); buy.stock[c].current = round(1500 * (1 - frac))
        return E.port_buy_price(buy, c, 0) - E.port_sell_price(sell, c, 0)
    assert 0.55 <= profit(0.61) / profit(1.0) <= 0.70


def test_legacy_curve_unchanged(monkeypatch):
    monkeypatch.setattr(K, "PORT_DRAIN_CURVE_MODE", "legacy")
    sell, buy, c = _ports(monkeypatch, "legacy")
    sell.stock[c].current = 750
    frac = 0.5
    base = K.COMMODITY_BASE_PRICE[c.value]
    assert K.port_regen_per_day() == K.PORT_REGEN_PER_DAY == 0.05
    assert not K.port_drain_curve_live()
    assert E.port_sell_price(sell, c, 0) >= 1 and base > 0 and frac


def test_switch_alone(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    monkeypatch.setattr(K, "PORT_DRAIN_CURVE_MODE", "live")
    assert K.port_drain_curve_live() and K.port_regen_per_day() == 0.10


def test_v311_restock_is_ten_percent(monkeypatch):
    sell, _buy, c = _ports(monkeypatch, "v311")
    sell.stock[c].current = 0
    sell.productivity[c] = 150
    from types import SimpleNamespace
    E.regenerate_ports(SimpleNamespace(sectors={1: SimpleNamespace(port=sell)}))
    assert sell.stock[c].current == 150  # 10% of 1,500, economy2 261/2610


def test_manual_line():
    from tw2k.public import manual
    assert "PORT_DRAIN_CURVE_MODE" in manual._SWITCH_PLAIN
    assert "Drain curve and restock" in open(manual.__file__).read()
