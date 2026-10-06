"""bots-use-planet-trade-v1: N-bots keep a world's goods for planet_trade when a port above it buys them, fly
there to sell kept lots, and steer a genesis torpedo a few known hops to land under such a port.
docs/playtests/planets/PLANETARY_TRADING.md "Bots"."""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tests import test_planet_trade as T
from tw2k.agents.prompts import get_system_prompt
from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View
from tw2k.engine import Action, ActionKind, apply_action
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, PortClass
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import _record_port_intel

ORE, ORG, EQ = Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT
NEW_DEFAULTS = (("BOT_PLANET_TRADE_HOLD", True), ("BOT_PLANET_TRADE_GENESIS_HOPS", 2),
                ("BOT_PLANET_TRADE_QUOTE_PCT", 90), ("BOT_PLANET_TRADE_FREE_LOT", 10))


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    for name, value in T.PT_DEFAULTS + NEW_DEFAULTS:
        monkeypatch.setattr(K, name, value)


def _obs(u, pid="A", mem=None):
    o = build_observation(u, pid).model_dump(mode="json")
    if mem is not None:
        o["scratchpad"] = mem.dump()
    return o


def _brain_view(u, pid="A"):
    b = SeatBrain()
    b.mem = SeatMemory()
    return b, View(_obs(u, pid))


def _know(u, pid, *sids):
    p = u.players[pid]
    for s in sids:
        p.known_sectors.add(int(s))
        p.known_warps[int(s)] = list(u.sectors[int(s)].warps)
        if u.sectors[int(s)].port is not None:
            _record_port_intel(p, int(s), u.sectors[int(s)].port, universe=u)


def _away_lab(cls=PortClass.CLASS_7_BBB, stock=(3_000, 3_000, 3_000)):
    """World 900 (genesis) under a port in sector Y; trader A one hop away in sector Z with no port."""
    u, y, a, pl = T._lab(cls, stock=stock)
    pl.origin = "genesis"
    z = next(int(w) for w in u.sectors[y].warps if int(w) not in K.FEDSPACE_SECTORS and int(w) != K.STARDOCK_SECTOR)
    u.sectors[z].port = None
    T._sit(u, "A", z)
    _know(u, "A", z, y)
    return u, y, z, a, pl


def test_kept_stock_is_held_for_planet_trade_not_ferried():
    u, y, z, a, pl = _away_lab()
    b, v = _brain_view(u)
    planet = v.planet(900)
    assert b._pt_held(v, planet, "organics") and b._pt_held(v, planet, "equipment")
    assert not b._pt_held(v, planet, "fuel_ore")  # BOT_PLANET_TRADE_KEEP_ORE
    opt = b._opt_stockpile(v)
    assert opt is None or opt[3]["stock_load"][1] not in ("organics", "equipment")


def test_hold_only_where_the_port_buys_the_good():
    u, y, z, a, pl = _away_lab(cls=PortClass.CLASS_1_BSS)  # buys ore only
    b, v = _brain_view(u)
    planet = v.planet(900)
    assert not b._pt_held(v, planet, "organics") and not b._pt_held(v, planet, "equipment")


@pytest.mark.parametrize("name,value", [("BOT_PLANET_TRADE_HOLD", False), ("BOT_PLANET_TRADE_POLICY", "off"),
                                        ("PLANET_TRADE_MODE", "legacy")])
def test_switches_turn_the_hold_off(monkeypatch, name, value):
    monkeypatch.setattr(K, name, value)
    u, y, z, a, pl = _away_lab()
    b, v = _brain_view(u)
    assert not b._pt_held(v, v.planet(900), "organics")
    assert b._opt_planet_sell(v) is None


def test_bot_flies_to_a_world_with_a_kept_lot():
    u, y, z, a, pl = _away_lab()
    b, v = _brain_view(u)
    opt = b._opt_planet_sell(v)
    assert opt is not None and opt[0] > 0
    assert y in [int(x) for x in opt[1]["args"].values() if isinstance(x, int)]


def test_lot_under_the_min_is_left_to_grow(monkeypatch):
    monkeypatch.setattr(K, "BOT_PLANET_TRADE_MIN_LOT", 200)
    u, y, z, a, pl = _away_lab(stock=(0, 0, 199))
    b, v = _brain_view(u)
    assert b._opt_planet_sell(v) is None
    pl.stockpile[EQ] = 200
    b, v = _brain_view(u)
    assert b._opt_planet_sell(v) is not None


def test_bot_sells_the_kept_lot_on_arrival(monkeypatch):
    monkeypatch.setattr(K, "BOT_PLANET_TRADE_MIN_LOT", 200)
    u, sid, a, pl = T._lab(stock=(0, 0, 250))
    pl.origin = "genesis"
    act = SeatBrain().decide(_obs(u))
    assert act["kind"] == "planet_trade" and act["args"] == {"planet_id": 900, "commodity": "equipment", "qty": 250}
    assert apply_action(u, "A", Action(kind=ActionKind.PLANET_TRADE, args=act["args"])).ok



def test_small_lot_sells_once_the_visit_is_paid(monkeypatch):
    """A lot under MIN_LOT is not worth the dock turn, but after a ship trade in the same visit (turn_cost 0,
    PLANETARY_TRADING.md pt9) anything from BOT_PLANET_TRADE_FREE_LOT up is free money."""
    monkeypatch.setattr(K, "BOT_PLANET_TRADE_MIN_LOT", 200)
    u, sid, a, pl = T._lab(stock=(0, 0, 30))
    pl.origin = "genesis"
    b, v = _brain_view(u)
    assert v.params("planet_trade")["turn_cost"] == 1 and b._planet_trade(v) is None
    u.players["A"].port_visit_sector_id = u.players["A"].sector_id
    b, v = _brain_view(u)
    act = b._planet_trade(v)
    assert v.params("planet_trade")["turn_cost"] == 0
    assert act["kind"] == "planet_trade" and act["args"] == {"planet_id": 900, "commodity": "equipment", "qty": 30}
    pl.stockpile[EQ] = 9
    b, v = _brain_view(u)
    assert b._planet_trade(v) is None

def _genesis_lab():
    """Trader A carries a genesis torpedo in sector X (no port, deploy legal); sector Y next door has a BBB port."""
    u = T._world()
    for x in sorted(u.sectors):
        if x in K.FEDSPACE_SECTORS or x == K.STARDOCK_SECTOR or not u.sectors[x].warps:
            continue
        ys = [int(w) for w in u.sectors[x].warps if int(w) not in K.FEDSPACE_SECTORS and int(w) != K.STARDOCK_SECTOR]
        if not ys:
            continue
        y = ys[0]
        u.sectors[x].port = None
        u.sectors[y].port = T._port(PortClass.CLASS_7_BBB)
        a = T._sit(u, "A", x)
        a.ship.genesis = 1
        if any(la.kind == "deploy_genesis" and la.legal for la in legal_actions(u, "A")):
            _know(u, "A", x, y)
            return u, x, y, a
    raise AssertionError("no lab sector")


def test_genesis_detours_to_a_known_buying_port():
    u, x, y, a = _genesis_lab()
    act = SeatBrain().decide(_obs(u))
    assert act["kind"] != "deploy_genesis"
    assert y in [int(v) for v in act["args"].values() if isinstance(v, int)]


def test_genesis_deploys_under_the_port_and_detour_is_bounded():
    u, x, y, a = _genesis_lab()
    act = SeatBrain().decide(_obs(u, mem=SeatMemory(pt_detour=K.BOT_PLANET_TRADE_GENESIS_HOPS + 1)))
    assert act["kind"] == "deploy_genesis"  # out of detour budget: deploy where it stands
    u.sectors[x].port = T._port(PortClass.CLASS_7_BBB)
    act = SeatBrain().decide(_obs(u))
    assert act["kind"] == "deploy_genesis"  # already under a buying port


@pytest.mark.parametrize("name,value", [("BOT_PLANET_TRADE_GENESIS_HOPS", 0), ("PLANET_TRADE_MODE", "legacy"),
                                        ("BOT_PLANET_TRADE_POLICY", "off")])
def test_genesis_detour_switches(monkeypatch, name, value):
    monkeypatch.setattr(K, name, value)
    u, x, y, a = _genesis_lab()
    assert SeatBrain().decide(_obs(u))["kind"] == "deploy_genesis"


def test_detour_memory_stays_off_the_scratchpad_by_default():
    assert "pt_detour" not in SeatMemory().dump()
    assert SeatMemory.load(SeatMemory(pt_detour=2).dump()).pt_detour == 2


def test_prompt_strategy_note_only_under_tw2002(monkeypatch):
    assert "Strategy note: a planet in the same sector as a port" in get_system_prompt()
    monkeypatch.setattr(K, "PLANET_TRADE_MODE", "legacy")
    assert "Strategy note: a planet in the same sector" not in get_system_prompt()
