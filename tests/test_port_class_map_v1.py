"""Class 1 and class 6 can use the live letters, and StarDock can buy goods.

v3.34b: class 1 is BBS, class 6 is BSS, and the StarDock port buys fuel,
organics, and equipment. This copy has those two letters swapped, and the
sector-1 StarDock trades nothing. Class 7 stays BBB. Live class 7 is SSS
and live class 8 is a normal buy-all port, but class 8 is the StarDock id
until Ben moves StarDock off sector 1. Class 0 still trades no commodities.
Sol does not either.

PORT_CLASS_MAP_MODE defaults to legacy, so today's digests stay put.

Plants:
  pb1 — live class 1 is still BSS.
  pb2 — live StarDock still has no stock.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import Commodity, GameConfig, Player
from tw2k.engine.port_build import build_class
from tw2k.engine.runner import apply_action
from tw2k.engine.universe import generate_universe


def _world():
    return generate_universe(
        GameConfig(seed=250925, universe_size=80, enable_ferrengi=False, enable_planets=False)
    )


def _ports(universe, class_id: int):
    found = []
    for sector in universe.sectors.values():
        port = sector.port
        if port is not None and int(port.class_id) == class_id and int(sector.id) != K.STARDOCK_SECTOR:
            found.append(port)
    return found


def _shape(universe):
    rows = []
    for sid in sorted(universe.sectors):
        sector = universe.sectors[sid]
        warps = tuple(sorted(int(w) for w in sector.warps))
        port = sector.port
        if port is None:
            rows.append((sid, warps, None))
            continue
        caps = tuple(sorted((str(c), int(s.maximum)) for c, s in port.stock.items()))
        rows.append((sid, warps, int(port.class_id), caps))
    return rows


def test_default_stays_legacy():
    assert K.PORT_CLASS_MAP_MODE == "legacy"
    assert K.port_class_live() is False
    world = _world()
    dock = world.sectors[K.STARDOCK_SECTOR].port
    assert int(dock.class_id) == 8
    assert dock.stock == {}
    assert dock.code == "STARDOCK"
    one = _ports(world, 1)[0]
    six = _ports(world, 6)[0]
    assert one.code == "BSS"
    assert one.buys(Commodity.FUEL_ORE) and not one.buys(Commodity.ORGANICS)
    assert six.code == "BBS"
    assert six.buys(Commodity.FUEL_ORE) and six.buys(Commodity.ORGANICS)


def test_live_swaps_class_1_and_6_and_stardock_buys(monkeypatch):
    monkeypatch.setattr(K, "PORT_CLASS_MAP_MODE", "live")
    world = _world()
    one = _ports(world, 1)[0]
    six = _ports(world, 6)[0]
    assert one.code == "BBS"
    assert one.buys(Commodity.FUEL_ORE) and one.buys(Commodity.ORGANICS)
    assert one.sells(Commodity.EQUIPMENT)
    assert six.code == "BSS"
    assert six.buys(Commodity.FUEL_ORE) and six.sells(Commodity.ORGANICS)
    dock = world.sectors[K.STARDOCK_SECTOR].port
    assert int(dock.class_id) == 8
    assert dock.name == "Sol-1 StarDock"
    assert dock.buys(Commodity.FUEL_ORE)
    assert dock.buys(Commodity.ORGANICS)
    assert dock.buys(Commodity.EQUIPMENT)
    assert len(dock.stock) == 3
    assert build_class("BBS") == type(one.class_id)(1)
    assert int(build_class("BSS")) == 6


def test_live_does_not_move_class_ids_or_later_port_sizes(monkeypatch):
    legacy = _shape(_world())
    monkeypatch.setattr(K, "PORT_CLASS_MAP_MODE", "live")
    live = _shape(_world())
    assert len(legacy) == len(live)
    for left, right in zip(legacy, live, strict=True):
        assert left[0] == right[0]
        assert left[1] == right[1]
        assert left[2] == right[2]
        if left[2] is None:
            continue
        if left[0] == K.STARDOCK_SECTOR:
            assert left[3] == ()
            assert len(right[3]) == 3
        else:
            assert left[3] == right[3]


def test_legacy_refuses_stardock_trade_and_live_pays_for_equipment(monkeypatch):
    world = _world()
    player = Player(id="P1", name="Seat", sector_id=K.STARDOCK_SECTOR, credits=300, turns_per_day=250)
    player.ship.cargo[Commodity.EQUIPMENT] = 5
    world.players["P1"] = player
    world.sectors[K.STARDOCK_SECTOR].occupant_ids.append("P1")
    refused = apply_action(
        world, "P1",
        Action(kind=ActionKind.TRADE, args={"commodity": "equipment", "qty": 5, "side": "sell"}),
    )
    assert refused.ok is False

    monkeypatch.setattr(K, "PORT_CLASS_MAP_MODE", "live")
    live = _world()
    seller = Player(id="P1", name="Seat", sector_id=K.STARDOCK_SECTOR, credits=300, turns_per_day=250)
    seller.ship.cargo[Commodity.EQUIPMENT] = 5
    live.players["P1"] = seller
    live.sectors[K.STARDOCK_SECTOR].occupant_ids.append("P1")
    before = seller.credits
    sold = apply_action(
        live, "P1",
        Action(kind=ActionKind.TRADE, args={"commodity": "equipment", "qty": 5, "side": "sell"}),
    )
    assert sold.ok is True
    assert seller.ship.cargo[Commodity.EQUIPMENT] == 0
    assert seller.credits > before
