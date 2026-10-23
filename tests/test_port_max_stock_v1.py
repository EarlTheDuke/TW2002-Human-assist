"""GAP 2.5 and the playtest 3 note: 1-hop port pairs barely deplete.

Bible (S3), an unused Tarsus: Fuel Ore 2720, Organics 2020, Equipment 1470 at
100%. Cabal economy2: SBB 2610, 950, 2100. Cabal economy3: "1,500 units of each
product ... roughly average amounts for ports", drained about 4 percent a trip
by a 65-hold Merf, and "The profit from the first 50% of the product is more
than twice that of the final 50%".
"""

from __future__ import annotations

import random
import statistics

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import economy as E
from tw2k.engine.models import Commodity, Player, Ship, ShipClass


def _maxima(u):
    return [st.maximum for s in u.sectors.values() if s.port and s.port.class_id.value not in (0, 9)
            for st in s.port.stock.values()]


def _gen(monkeypatch, profile, seed=5):
    monkeypatch.setattr(K, "V311_PROFILE", profile)
    return generate_universe(GameConfig(seed=seed, universe_size=1000))


def test_legacy_keeps_big_ports(monkeypatch):
    m = _maxima(_gen(monkeypatch, "legacy"))
    assert min(m) >= 2500 and statistics.mean(m) > 3000


def test_v311_uses_printed_span(monkeypatch):
    m = [x for x in _maxima(_gen(monkeypatch, "v311")) if x != 0]
    assert min(m) >= 950 and max(m) <= 2720
    assert 1500 <= statistics.mean(m) <= 2100


def test_draw_maps_ends():
    assert K.port_max_stock(-500) in (K.PORT_DEFAULT_MAX_STOCK - 500, 950)


def test_switch_alone(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    monkeypatch.setattr(K, "PORT_MAX_STOCK_MODE", "live")
    assert K.port_max_stock(-500) == 950 and K.port_max_stock(1500) == 2720
    monkeypatch.setattr(K, "PORT_MAX_STOCK_MODE", "legacy")
    assert K.port_max_stock(-500) == 2500


def _pair(u):
    for s in u.sectors.values():
        if not s.port or int(s.id) in K.FEDSPACE_SECTORS:
            continue
        for w in s.warps:
            t = u.sectors[w]
            if t.port and s.id in t.warps and int(t.id) not in K.FEDSPACE_SECTORS:
                for c in (Commodity.ORGANICS, Commodity.EQUIPMENT, Commodity.FUEL_ORE):
                    if s.port.sells(c) and t.port.buys(c):
                        return s, t, c
    raise AssertionError("no 1-hop pair")


def _margins(u, trips=10, holds=65):
    s, t, c = _pair(u)
    p = Player(id="P", name="P", ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, holds=holds),
               sector_id=s.id, credits=10**9, experience=0, turns_per_day=9999)
    u.players["P"] = p
    rng = random.Random(1)
    out = []
    for _ in range(trips):
        E.begin_port_visit(p)
        ok, _t, buy, _m, _r = E.execute_trade(u, p, s.port, c, holds, "buy", None, rng)
        E.begin_port_visit(p)
        ok2, _t2, sell, _m2, _r2 = E.execute_trade(u, p, t.port, c, holds, "sell", None, rng)
        assert ok and ok2, (_m, _m2, s.port.stock[c], t.port.stock[c])
        out.append(sell - buy)
    return out, s.port.stock[c]


def test_v311_pair_drains_like_economy3(monkeypatch):
    m, stock = _margins(_gen(monkeypatch, "v311"))
    drained = 1 - stock.current / stock.maximum
    assert drained >= 0.24  # economy3: 10 Merf trips take a 1,500 port to 61%
    assert m[-1] < m[0] * 0.7
    monkeypatch.setattr(K, "PORT_STOCK_FIDELITY_MODE", "live")  # same opening stock, legacy size
    legacy, lstock = _margins(_gen(monkeypatch, "legacy"))
    assert 1 - lstock.current / lstock.maximum < drained


def test_manual_line():
    from tw2k.public import manual
    assert "PORT_MAX_STOCK_MODE" in manual._SWITCH_PLAIN
    assert "takes a few percent off a port pair each trip" in open(manual.__file__).read()
