"""Ports open full, and regen is 5% of max, only when the flag says so.

Live TWGS Big Bang opens every port at 100% and puts about 5% of max back
each day. The clone opens at 0% and regens 5% of productivity. Game 5 saw
3-500 units against a 3,000-4,000 max.

PORT_OPEN_STOCK_MODE defaults to "legacy" so today's digests stay put.
"full" is the live rule. The unused 35-95% random draw stays in the stream
either way, so sector layout does not move.

Plants these tests re-break:
- pb1 full mode still opens at 0
- pb2 full regen follows productivity instead of max
- pb3 dropping the leftover random draw moves later port sizes
- pb4 regen climbs past the maximum
- pb5 legacy regen follows max, so an empty productivity port still fills
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine.economy import regenerate_ports
from tw2k.engine.models import GameConfig
from tw2k.engine.universe import generate_universe

pytestmark = pytest.mark.legacy_profile


def _shape(universe):
    rows = []
    for sid in sorted(universe.sectors):
        sector = universe.sectors[sid]
        warps = tuple(sorted(int(w) for w in sector.warps))
        port = sector.port
        if port is None:
            rows.append((sid, warps, None))
            continue
        caps = tuple(
            sorted((str(commodity), int(stock.maximum)) for commodity, stock in port.stock.items())
        )
        rows.append((sid, warps, str(port.class_id), str(port.name), caps))
    return rows


def _currents(universe):
    found = []
    for sid in sorted(universe.sectors):
        port = universe.sectors[sid].port
        if port is None:
            continue
        for commodity, stock in sorted(port.stock.items(), key=lambda item: str(item[0])):
            found.append((sid, str(commodity), int(stock.current), int(stock.maximum)))
    return found


def _first_stock(universe):
    for sector in universe.sectors.values():
        port = sector.port
        if port is None or not port.stock:
            continue
        commodity, stock = next(iter(port.stock.items()))
        return port, commodity, stock
    raise AssertionError("expected a port with stock")


def _world(seed: int = 250925):
    return generate_universe(
        GameConfig(seed=seed, universe_size=40, enable_ferrengi=False, enable_planets=False)
    )


def test_default_stays_legacy():
    assert K.PORT_OPEN_STOCK_MODE == "legacy"
    assert K.port_open_full() is False


def test_legacy_ports_open_empty():
    currents = _currents(_world())
    assert currents, "expected ports"
    assert all(current == int(maximum * K.PORT_START_STOCK_PERCENT) for _s, _c, current, maximum in currents)


def test_full_ports_open_at_max(monkeypatch):
    monkeypatch.setattr(K, "PORT_OPEN_STOCK_MODE", "full")
    currents = _currents(_world())
    assert currents
    assert all(current == maximum and maximum > 0 for _s, _c, current, maximum in currents)


def test_full_does_not_move_layout_or_maximums(monkeypatch):
    legacy = _shape(_world())
    monkeypatch.setattr(K, "PORT_OPEN_STOCK_MODE", "full")
    assert _shape(_world()) == legacy


def test_legacy_regen_follows_productivity_and_stays_capped():
    universe = _world(seed=3)
    port, commodity, stock = _first_stock(universe)
    stock.maximum = 3000
    stock.current = 100
    port.productivity[commodity] = 0
    regenerate_ports(universe)
    assert stock.current == 100
    port.productivity[commodity] = 400
    regenerate_ports(universe)
    assert stock.current == 100 + round(400 * K.PORT_REGEN_PER_DAY)
    stock.current = stock.maximum - 1
    port.productivity[commodity] = 10_000
    regenerate_ports(universe)
    assert stock.current == stock.maximum


def test_full_regen_is_five_percent_of_max_and_caps(monkeypatch):
    monkeypatch.setattr(K, "PORT_OPEN_STOCK_MODE", "full")
    universe = _world(seed=3)
    port, commodity, stock = _first_stock(universe)
    stock.maximum = 3000
    stock.current = 0
    port.productivity[commodity] = 80_000
    regenerate_ports(universe)
    assert stock.current == round(3000 * K.PORT_REGEN_PER_DAY)
    stock.current = 2990
    regenerate_ports(universe)
    assert stock.current == 3000
