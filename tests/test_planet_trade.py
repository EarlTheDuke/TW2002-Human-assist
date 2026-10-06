"""planetary-trading-v1 (slice 54): Negotiate Planetary Trade Agreement (port menu <N>, PLANET_TRADE_MODE).

docs/playtests/planets/PLANETARY_TRADING.md rows pt1..pt26. Every rule runs through the real engine path
(apply_action / legal_actions / build_observation).
"""

from __future__ import annotations

import copy
import json

import pytest

import tw2k.engine.constants as K
from tw2k.agents.prompts import get_system_prompt
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.economy import _stored_mcic, can_trade, haggle_bound, port_buy_price
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Commodity,
    EventKind,
    Planet,
    PlanetClass,
    Player,
    Port,
    PortClass,
    PortStock,
    Ship,
    ShipClass,
)
from tw2k.engine.observation import build_observation
from tw2k.engine.planet_trade import BUSTED, LANDED, NO_AGREEMENT_PORT, NO_PLANET, NOT_INTERESTED, lot_price

ORE, ORG, EQ = Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT
PT_DEFAULTS = (
    ("PLANET_TRADE_MODE", "tw2002"), ("PLANET_TRADE_PRICING", "curve"), ("PLANET_TRADE_CURVE_STEP", 100),
    ("PLANET_TRADE_WHO", "owner_or_corp"), ("PLANET_TRADE_HAGGLE", "as_ship_sell"), ("PLANET_TRADE_PAYEE", "trader"),
    ("PLANET_TRADE_EXP", "as_trade"), ("PLANET_TRADE_TWARP_COOLDOWN", 0), ("PLANET_TRADE_FEED", "public_summary"),
    ("BOT_PLANET_TRADE_POLICY", "sell_surplus"), ("BOT_PLANET_TRADE_MIN_LOT", 500), ("BOT_PLANET_TRADE_KEEP_ORE", True),
    ("ROB_MODE", "tw2002"),
)


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    for name, value in PT_DEFAULTS:
        monkeypatch.setattr(K, name, value)


# ---- helpers ------------------------------------------------------------------------------------------

def _world():
    return generate_universe(GameConfig(seed=11, universe_size=60, enable_ferrengi=False, enable_planets=False))


def _sit(u, pid, sector, hull=ShipClass.MERCHANT_CRUISER, credits=10_000):
    if pid not in u.players:
        u.players[pid] = Player(id=pid, name=pid, ship=Ship(), sector_id=1)
        u.sectors[1].occupant_ids.append(pid)
    p = u.players[pid]
    if pid in u.sectors[p.sector_id].occupant_ids:
        u.sectors[p.sector_id].occupant_ids.remove(pid)
    p.sector_id = int(sector)
    p.ship.ship_class = hull
    for c in Commodity:
        p.ship.cargo[c] = 0
    p.credits = credits
    p.turns_today = 0
    p.turns_per_day = 1000
    p.planet_landed = None
    p.port_visit_sector_id = None
    p.known_sectors.add(int(sector))
    u.sectors[int(sector)].occupant_ids.append(pid)
    return p


def _lab_sector(u, skip=()):
    return next(s for s in sorted(u.sectors) if s not in K.FEDSPACE_SECTORS and s != K.STARDOCK_SECTOR
                and s not in skip and u.sectors[s].warps)


def _port(cls=PortClass.CLASS_7_BBB, cur=1_000, mx=10_000):
    stock = {c: PortStock(current=cur, maximum=mx) for c in (ORE, ORG, EQ)}
    return Port(class_id=cls, name="Lab", stock=stock)


def _planet(u, pid_, sector, owner="A", stock=(3_000, 3_000, 3_000), corp=None, name=None):
    pl = Planet(id=pid_, sector_id=sector, name=name or f"World{pid_}", class_id=PlanetClass.M, owner_id=owner,
                corp_ticker=corp)
    pl.stockpile = {ORE: stock[0], ORG: stock[1], EQ: stock[2]}
    u.planets[pid_] = pl
    u.sectors[sector].planet_ids.append(pid_)
    return pl


def _lab(cls=PortClass.CLASS_7_BBB, cur=1_000, mx=10_000, stock=(3_000, 3_000, 3_000)):
    u = _world()
    sid = _lab_sector(u)
    s = u.sectors[sid]
    s.port = _port(cls, cur, mx)
    s.planet_ids.clear()
    s.fighters = None
    s.mines.clear()
    a = _sit(u, "A", sid)
    pl = _planet(u, 900, sid, "A", stock, name="Oceanworld")
    return u, sid, a, pl


def _do(u, pid, kind, **args):
    return apply_action(u, pid, Action(kind=kind, args=args))


def _pt(u, pid="A", **args):
    return _do(u, pid, ActionKind.PLANET_TRADE, **args)


def _la(u, pid="A"):
    return next((a for a in legal_actions(u, pid) if a.kind == "planet_trade"), None)


def _quote(u, sid, c, qty, xp=0, pricing=None):
    return lot_price(u.sectors[sid].port, c, qty, xp, pricing)


# ---- pt1 - pt3: where the menu exists ----------------------------------------------------------------

def test_pt1_verb_sells_planet_stock_at_a_port_in_the_same_sector():
    u, sid, a, pl = _lab()
    q = _quote(u, sid, ORG, 1_000)
    res = _pt(u, planet_id=900, commodity="organics", qty=1_000)
    assert res.ok, res.error
    assert a.credits == 10_000 + q and pl.stockpile[ORG] == 2_000
    u.sectors[sid].port = None
    res = _pt(u, planet_id=900, commodity="organics", qty=10)
    assert not res.ok and "no trading port" in res.error


def test_pt2_stardock_and_class0_have_no_agreement():
    u, sid, a, pl = _lab()
    u.sectors[sid].port.class_id = PortClass.FEDERAL
    res = _pt(u, planet_id=900, commodity="organics", qty=10)
    assert not res.ok and res.error == NO_AGREEMENT_PORT and a.turns_today == 0
    assert not _la(u).legal and _la(u).params["planets"] == []
    u.sectors[sid].port.class_id = PortClass.STARDOCK
    assert _pt(u, planet_id=900, commodity="organics", qty=10).error == NO_AGREEMENT_PORT
    for cls in range(1, 8):
        u.sectors[sid].port.class_id = PortClass(cls)
        assert _pt(u, planet_id=900, commodity="organics", qty=1).error != NO_AGREEMENT_PORT


def test_pt3_landed_trader_refused_and_pod_trades_like_a_ship():
    u, sid, a, pl = _lab()
    a.planet_landed = 900
    res = _pt(u, planet_id=900, commodity="organics", qty=10)
    assert not res.ok and res.error == LANDED and pl.stockpile[ORG] == 3_000
    assert not _la(u).legal and _la(u).reason == LANDED
    a.planet_landed = None
    a.ship.ship_class = ShipClass.ESCAPE_POD  # the ship-trade guards allow a pod to trade; so does <N>
    assert _pt(u, planet_id=900, commodity="organics", qty=10).ok
    a.port_visit_sector_id = None
    a.turns_today = a.turns_per_day  # Ship Destroyed / day over: nothing that costs a turn
    res = _pt(u, planet_id=900, commodity="organics", qty=10)
    assert not res.ok and "out of turns" in res.error


# ---- pt4: who may negotiate --------------------------------------------------------------------------

def test_pt4_eligibility_matrix():
    u, sid, a, pl = _lab()
    _sit(u, "B", _lab_sector(u, skip=(sid,)))
    corp_pl = _planet(u, 901, sid, owner="B", corp="ZZZ")
    rival = _planet(u, 902, sid, owner="B", stock=(0, 987_654, 0))
    a.corp_ticker = "ZZZ"
    assert _pt(u, planet_id=901, commodity="equipment", qty=100).ok  # corp-mate's corp planet
    assert corp_pl.stockpile[EQ] == 2_900
    res_rival = _pt(u, planet_id=902, commodity="organics", qty=100)
    res_none = _pt(u, planet_id=4242, commodity="organics", qty=100)
    assert not res_rival.ok and res_rival.error == res_none.error == NO_PLANET
    assert rival.stockpile[ORG] == 987_654
    a.corp_ticker = None  # left the corp
    assert _pt(u, planet_id=901, commodity="equipment", qty=100).error == NO_PLANET
    pl.corp_ticker = "ZZZ"  # own planet still tagged with the old corp: still his
    assert _pt(u, planet_id=900, commodity="equipment", qty=100).ok


def test_pt4_who_owner_switch():
    u, sid, a, pl = _lab()
    _planet(u, 901, sid, owner="B", corp="ZZZ")
    a.corp_ticker = "ZZZ"
    assert 901 in _la(u).params["planet_id"]["choices"]
    K.PLANET_TRADE_WHO = "owner"
    assert 901 not in _la(u).params["planet_id"]["choices"]
    assert _pt(u, planet_id=901, commodity="organics", qty=1).error == NO_PLANET
    assert _pt(u, planet_id=900, commodity="organics", qty=1).ok


def test_pt4_planet_in_another_sector_refused():
    u, sid, a, pl = _lab()
    other = _lab_sector(u, skip=(sid,))
    u.sectors[sid].planet_ids.remove(900)
    pl.sector_id = other
    u.sectors[other].planet_ids.append(900)
    res = _pt(u, planet_id=900, commodity="organics", qty=10)
    assert not res.ok and res.error == NO_PLANET and pl.stockpile[ORG] == 3_000
    assert not _la(u).legal


# ---- pt5 - pt8: what and how much ---------------------------------------------------------------------

def test_pt5_sell_only_and_only_what_the_port_buys():
    u, sid, a, pl = _lab(cls=PortClass.CLASS_3_SBB)  # sells ore, buys organics and equipment
    la = _la(u)
    assert la.legal and la.params["commodity"]["choices"] == ["equipment", "organics"]
    assert "fuel_ore" not in la.params["planets"][0]["sellable"]
    res = _pt(u, planet_id=900, commodity="fuel_ore", qty=10)
    assert not res.ok and "not buying" in res.error and pl.stockpile[ORE] == 3_000 and a.turns_today == 0


def test_pt6_qty_matrix():
    u, sid, a, pl = _lab(cur=8_000, mx=10_000, stock=(3_000, 3_000, 1_500))  # room 2,000
    for bad in (0, -5):
        res = _pt(u, planet_id=900, commodity="organics", qty=bad)
        assert not res.ok and a.turns_today == 0
    res = _pt(u, planet_id=900, commodity="organics", qty=2_001)  # more than the port is buying
    assert not res.ok and res.error.startswith("We are buying up to 2000") and a.turns_today == 0
    res = _pt(u, planet_id=900, commodity="equipment", qty=1_501)  # more than the planet holds
    assert not res.ok and "You have 1500 equipment on planet Oceanworld" in res.error
    mb = _la(u).params["qty"]["max_by"]["900"]
    assert mb == {"fuel_ore": 2_000, "organics": 2_000, "equipment": 1_500}
    assert not _pt(u, planet_id=900, commodity="equipment", qty=mb["equipment"] + 1).ok
    assert _pt(u, planet_id=900, commodity="equipment", qty=mb["equipment"]).ok
    assert pl.stockpile[EQ] == 0 and a.turns_today == 1


def test_pt6_default_qty_is_the_offered_max():
    u, sid, a, pl = _lab(cur=9_000, mx=10_000)
    assert _pt(u, planet_id=900, commodity="organics").ok
    assert pl.stockpile[ORG] == 2_000 and u.sectors[sid].port.stock[ORG].current == 10_000


def test_pt7_port_room_is_can_trade_capacity():
    u, sid, a, pl = _lab(cur=7_654, mx=10_000)
    port = u.sectors[sid].port
    room = _la(u).params["planets"][0]["sellable"]["organics"]
    assert room == 2_346
    assert can_trade(port, ORG, room, "sell")[0] and not can_trade(port, ORG, room + 1, "sell")[0]


def test_pt8_one_commodity_per_action():
    u, sid, a, pl = _lab()
    assert _pt(u, planet_id=900, commodity="equipment", qty=700).ok
    assert pl.stockpile == {ORE: 3_000, ORG: 3_000, EQ: 2_300}
    port = u.sectors[sid].port
    assert port.stock[ORE].current == 1_000 and port.stock[ORG].current == 1_000 and port.stock[EQ].current == 1_700


# ---- pt9: turns ---------------------------------------------------------------------------------------

def test_pt9_turn_matrix():
    u, sid, a, pl = _lab()
    assert _pt(u, planet_id=900, commodity="organics", qty=100).ok and a.turns_today == 1  # first of the visit
    assert _pt(u, planet_id=900, commodity="equipment", qty=100).ok and a.turns_today == 1  # second commodity
    assert _pt(u, planet_id=900, commodity="organics", qty=100).ok and a.turns_today == 1
    a.ship.cargo[ORG] = 10
    assert _do(u, "A", ActionKind.TRADE, commodity="organics", qty=5, side="sell").ok and a.turns_today == 1
    a.end_port_visit()  # new visit
    assert _la(u).turn_cost == 1
    assert _pt(u, planet_id=900, commodity="organics", qty=100).ok and a.turns_today == 2
    a.end_port_visit()
    assert _do(u, "A", ActionKind.TRADE, commodity="organics", qty=5, side="sell").ok and a.turns_today == 3
    assert _la(u).turn_cost == 0
    assert _pt(u, planet_id=900, commodity="organics", qty=100).ok and a.turns_today == 3  # after a ship trade


# ---- pt10 / pt11: lot price and quote -----------------------------------------------------------------

def _ref_curve(port, c, qty, step=100):
    total, done = 0, 0
    while done < qty:
        n = min(step, qty - done)
        p2 = port.model_copy(deep=True)
        p2.stock[c].current = port.stock[c].current + done
        total += port_buy_price(p2, c, 0) * n
        done += n
    return total


def test_pt10_lot_price_table_curve_end_mbbs100():
    u, sid, a, pl = _lab(cur=1_000, mx=10_000)
    port = u.sectors[sid].port
    bid = port_buy_price(port, ORG, 0)
    for qty in (100, 1_000, 3_000, 250):
        curve = _quote(u, sid, ORG, qty)
        assert curve == _ref_curve(port, ORG, qty)
        end_p = port.model_copy(deep=True)
        end_p.stock[ORG].current += qty
        assert _quote(u, sid, ORG, qty, pricing="end") == port_buy_price(end_p, ORG, 0) * qty
        assert _quote(u, sid, ORG, qty, pricing="mbbs100") == bid * qty
        assert _quote(u, sid, ORG, qty, pricing="end") <= curve <= bid * qty
    assert _quote(u, sid, ORG, 100) == bid * 100  # one step = the opening bid
    assert _quote(u, sid, ORG, 1_000) < bid * 1_000  # the bid falls as the port fills
    assert _quote(u, sid, ORG, 3_000) < bid * 3_000
    assert _quote(u, sid, ORG, 3_000) > _quote(u, sid, ORG, 3_000, pricing="end")
    assert port.stock[ORG].current == 1_000  # quoting never touches the port


def test_pt10_curve_step_and_pricing_switch_reach_the_handler():
    u, sid, a, pl = _lab()
    bid = port_buy_price(u.sectors[sid].port, ORG, 0)
    K.PLANET_TRADE_PRICING = "mbbs100"
    assert _pt(u, planet_id=900, commodity="organics", qty=1_000).ok and a.credits == 10_000 + bid * 1_000
    u, sid, a, pl = _lab()
    K.PLANET_TRADE_PRICING = "curve"
    K.PLANET_TRADE_CURVE_STEP = 1_000
    assert _quote(u, sid, ORG, 1_000) == bid * 1_000


def test_pt11_quote_is_what_an_accepted_lot_pays():
    u, sid, a, pl = _lab()
    row = _la(u).params["planets"][0]
    assert row["quote"]["organics"] == _quote(u, sid, ORG, 3_000)
    assert row["unit_bid"]["organics"] == port_buy_price(u.sectors[sid].port, ORG, 0)
    assert _pt(u, planet_id=900, commodity="organics", qty=3_000).ok
    assert a.credits == 10_000 + row["quote"]["organics"]
    ev = [e for e in u.events if e.kind == EventKind.PLANET_TRADE][-1]
    assert ev.payload["quote"] == ev.payload["price"] == row["quote"]["organics"] and "We'll buy" not in ev.summary


# ---- pt12: one counter --------------------------------------------------------------------------------

def test_pt12_haggle_matrix():
    u, sid, a, pl = _lab()
    q = _quote(u, sid, ORG, 1_000)
    bound = haggle_bound(q, _stored_mcic(u.sectors[sid].port, ORG), "sell")
    assert bound > q
    snap = copy.deepcopy(u)
    # counter past the bound: no sale, the visit turn is spent
    res = _pt(u, planet_id=900, commodity="organics", qty=1_000, offer=bound + 1)
    assert not res.ok and res.error == NOT_INTERESTED and a.turns_today == 1
    assert a.credits == 10_000 and pl.stockpile[ORG] == 3_000 and u.sectors[sid].port.stock[ORG].current == 1_000
    # good counter at the bound: paid the offer + good-counter experience
    u = copy.deepcopy(snap)
    a, pl = u.players["A"], u.planets[900]
    xp0 = a.experience
    assert _pt(u, planet_id=900, commodity="organics", qty=1_000, offer=bound).ok
    assert a.credits == 10_000 + bound and pl.stockpile[ORG] == 2_000
    bargain = (bound - q + 500) // 1_000
    assert a.experience - xp0 == K.xp_award("trade") + K.xp_award("first_dock") + min(K.PORT_HAGGLE_XP_CAP, bargain)
    ev = [e for e in u.events if e.kind == EventKind.PLANET_TRADE][-1]
    assert ev.payload["countered"] is True and ev.payload["quote"] == q
    # low offer accepted at the offer
    u = copy.deepcopy(snap)
    assert _pt(u, planet_id=900, commodity="organics", qty=1_000, offer=q - 500).ok
    assert u.players["A"].credits == 10_000 + q - 500
    # at the quote
    u = copy.deepcopy(snap)
    assert _pt(u, planet_id=900, commodity="organics", qty=1_000, offer=q).ok and u.players["A"].credits == 10_000 + q


def test_pt12_refused_counter_inside_a_visit_costs_nothing_more():
    u, sid, a, pl = _lab()
    assert _pt(u, planet_id=900, commodity="equipment", qty=100).ok and a.turns_today == 1
    q = _quote(u, sid, ORG, 1_000)
    res = _pt(u, planet_id=900, commodity="organics", qty=1_000, offer=q * 3)
    assert res.error == NOT_INTERESTED and a.turns_today == 1


def test_pt12_no_counter_switch():
    u, sid, a, pl = _lab()
    K.PLANET_TRADE_HAGGLE = "no_counter"
    q = _quote(u, sid, ORG, 1_000)
    assert _pt(u, planet_id=900, commodity="organics", qty=1_000, offer=q + 1).error == NOT_INTERESTED
    assert _pt(u, planet_id=900, commodity="organics", qty=1_000, offer=q).ok


# ---- pt13 - pt16: settlement --------------------------------------------------------------------------

def test_pt13_pt14_payee_and_conservation():
    u, sid, a, pl = _lab()
    port = u.sectors[sid].port
    port.credits = 1_000_000
    pl.treasury = 55
    q = _quote(u, sid, EQ, 1_234)
    assert _pt(u, planet_id=900, commodity="equipment", qty=1_234).ok
    assert a.credits - 10_000 == q and pl.treasury == 55
    assert port.stock[EQ].current - 1_000 == 1_234 and 3_000 - pl.stockpile[EQ] == 1_234
    assert port.credits == 1_000_000 - q


def test_pt13_payee_planet_switch():
    u, sid, a, pl = _lab()
    K.PLANET_TRADE_PAYEE = "planet"
    q = _quote(u, sid, EQ, 100)
    assert _pt(u, planet_id=900, commodity="equipment", qty=100).ok
    assert a.credits == 10_000 and pl.treasury == q


def test_pt14_port_stock_updated_once_and_matches_a_ship_sale():
    u, sid, a, pl = _lab()
    ship_u = copy.deepcopy(u)
    sa = ship_u.players["A"]
    sa.ship.holds = 5_000
    sa.ship.cargo[ORG] = 1_000
    assert _do(ship_u, "A", ActionKind.TRADE, commodity="organics", qty=1_000, side="sell").ok
    assert _pt(u, planet_id=900, commodity="organics", qty=1_000).ok
    assert u.sectors[sid].port.stock[ORG].current == ship_u.sectors[sid].port.stock[ORG].current == 2_000


def test_pt15_experience_as_one_ship_sale():
    u, sid, a, pl = _lab()
    ship_u = copy.deepcopy(u)
    sa = ship_u.players["A"]
    sa.ship.holds = 5_000
    sa.ship.cargo[ORG] = 1_000
    assert _do(ship_u, "A", ActionKind.TRADE, commodity="organics", qty=1_000, side="sell").ok
    assert _pt(u, planet_id=900, commodity="organics", qty=1_000).ok
    assert a.experience == sa.experience > 0
    assert u.sectors[sid].port.experience == ship_u.sectors[sid].port.experience
    u2, sid2, a2, _ = _lab()
    K.PLANET_TRADE_EXP = "none"
    assert _pt(u2, planet_id=900, commodity="organics", qty=1_000).ok and a2.experience == 0


def test_pt16_alignment_unchanged():
    u, sid, a, pl = _lab()
    a.alignment = 37
    assert _pt(u, planet_id=900, commodity="organics", qty=1_000).ok and a.alignment == 37


# ---- pt17 - pt21 --------------------------------------------------------------------------------------

def test_pt17_busted_trader_refused_but_a_blue_corp_mate_may_sell():
    u, sid, a, pl = _lab()
    u.sectors[sid].port.bust_player_id = "A"
    res = _pt(u, planet_id=900, commodity="equipment", qty=100)
    assert not res.ok and res.error == BUSTED and a.turns_today == 0
    assert not _la(u).legal and _la(u).reason == BUSTED
    b = _sit(u, "B", sid)
    a.corp_ticker = b.corp_ticker = "ZZZ"
    pl.corp_ticker = "ZZZ"
    assert _pt(u, "B", planet_id=900, commodity="equipment", qty=100).ok  # CABAL: "have a blue sell the eq"
    assert b.credits > 10_000


def test_pt18_fuel_ore_may_be_sold():
    u, sid, a, pl = _lab(cls=PortClass.CLASS_1_BSS)
    assert _pt(u, planet_id=900, commodity="fuel_ore", qty=500).ok and pl.stockpile[ORE] == 2_500


def test_pt19_colonists_and_treasury_never_sellable():
    u, sid, a, pl = _lab()
    pl.colonists[ORE] = 5_000
    pl.treasury = 99_999
    res = _pt(u, planet_id=900, commodity="colonists", qty=100)
    assert not res.ok and "only fuel_ore, organics or equipment" in res.error
    assert pl.colonists[ORE] == 5_000 and pl.treasury == 99_999 and a.credits == 10_000
    assert "colonists" not in json.dumps(_la(u).params["planets"])
    assert not _pt(u, planet_id=900, commodity="treasury", qty=1).ok


def test_pt20_planet_twarped_in_today_trades_and_cooldown_switch():
    u, sid, a, pl = _lab()
    pl.last_transwarp_day = u.day
    assert _pt(u, planet_id=900, commodity="organics", qty=100).ok
    K.PLANET_TRADE_TWARP_COOLDOWN = 1
    assert _pt(u, planet_id=900, commodity="organics", qty=100).error == NO_PLANET


def test_pt21_several_planets_pick_by_id():
    u, sid, a, pl = _lab()
    second = _planet(u, 905, sid, owner="A", stock=(0, 0, 4_000))
    la = _la(u)
    assert la.params["planet_id"]["choices"] == [900, 905]
    assert [r["planet_id"] for r in la.params["planets"]] == [900, 905]
    assert _pt(u, planet_id=905, commodity="equipment", qty=400).ok
    assert second.stockpile[EQ] == 3_600 and pl.stockpile[EQ] == 3_000


# ---- pt22 - pt26 --------------------------------------------------------------------------------------

def test_pt22_no_rng_draws_like_a_ship_sale():
    u, sid, a, pl = _lab()
    a.ship.holds = 5_000
    a.ship.cargo[ORG] = 100
    s0 = u.rng.getstate()
    assert _do(u, "A", ActionKind.TRADE, commodity="organics", qty=100, side="sell").ok
    assert u.rng.getstate() == s0  # the ship sale draws none
    assert _pt(u, planet_id=900, commodity="organics", qty=1_000).ok
    q = _quote(u, sid, EQ, 500)
    assert _pt(u, planet_id=900, commodity="equipment", qty=500, offer=q * 5).error == NOT_INTERESTED
    assert _pt(u, planet_id=900, commodity="equipment", qty=500, offer=q + 1).ok
    legal_actions(u, "A")
    build_observation(u, "A")
    assert u.rng.getstate() == s0


def test_pt23_rest_of_the_visit_sees_the_new_stock():
    u, sid, a, pl = _lab()
    port = u.sectors[sid].port
    assert _pt(u, planet_id=900, commodity="organics", qty=3_000).ok
    trade = next(x for x in legal_actions(u, "A") if x.kind == "trade")
    assert trade.params["unit_price"]["listed_by"]["organics"]["sell"] == port_buy_price(port, ORG, a.experience)
    ref = _port()
    ref.stock[ORG].current = 4_000
    assert port_buy_price(port, ORG, a.experience) == port_buy_price(ref, ORG, a.experience)
    obs = build_observation(u, "A").model_dump(mode="json")
    assert obs["sector"]["port"]["stock"]["organics"]["current"] == 4_000


def test_pt24_event_visibility_and_payload():
    u, sid, a, pl = _lab()
    _sit(u, "B", sid)  # witness in the sector
    _sit(u, "C", _lab_sector(u, skip=(sid,)))
    assert _pt(u, planet_id=900, commodity="organics", qty=655).ok  # 2,345 left on the planet
    ev = [e for e in u.events if e.kind == EventKind.PLANET_TRADE][-1]
    assert {k for k in ev.payload if not k.startswith("_")} == {
        "trader", "planet_id", "port_sector", "commodity", "qty", "price", "quote", "countered"}
    assert ev.payload["trader"] == "A" and ev.payload["port_sector"] == sid and ev.payload["qty"] == 655

    def seen(pid):
        return [e for e in build_observation(u, pid).model_dump(mode="json")["recent_events"]
                if e["kind"] == "planet_trade"]
    assert seen("A") and seen("B") and not seen("C")
    for e in seen("B"):
        assert "2345" not in json.dumps(e) and "2,345" not in json.dumps(e)
    assert "2345" not in json.dumps(ev.payload) and "2,345" not in ev.summary
    K.PLANET_TRADE_FEED = "actor_only"
    assert seen("A") and not seen("B")


def test_pt25_victory_planet_stock_price_unchanged():
    from tw2k.engine.victory import planet_stock_unit_price
    for c in ("fuel_ore", "organics", "equipment"):
        assert planet_stock_unit_price(c) == int(K.COMMODITY_BASE_PRICE[c])


def test_pt26_ferrengi_never_negotiate():
    from tw2k.engine.runner import tick_day
    u = generate_universe(GameConfig(seed=5, universe_size=60, enable_ferrengi=True, enable_planets=True))
    for _ in range(3):
        tick_day(u)
    assert not [e for e in u.events if e.kind == EventKind.PLANET_TRADE]
    assert all(not str(fid).startswith("P") or fid in u.players for fid in u.ferrengi)


# ---- step 4: legal list == handler --------------------------------------------------------------------

def _all_offers(u, pid):
    la = _la(u, pid)
    if la is None or not la.legal:
        return []
    out = []
    for row in la.params["planets"]:
        for c, mx in row["sellable"].items():
            assert la.params["qty"]["max_by"][str(row["planet_id"])][c] == mx
            out.append((row["planet_id"], c, mx, row["quote"][c]))
    return out


@pytest.mark.parametrize("cur,stock", [(1_000, (3_000, 3_000, 3_000)), (9_500, (100, 7_000, 0)),
                                       (0, (12_000, 1, 250)), (9_999, (5, 5, 5))])
def test_legal_list_matches_handler(cur, stock):
    u, sid, a, pl = _lab(cur=cur, stock=stock)
    _planet(u, 903, sid, owner="A", stock=(stock[2], stock[0], stock[1]))
    _planet(u, 904, sid, owner="B", stock=(50_000, 50_000, 50_000))  # rival: never listed
    offers = _all_offers(u, "A")
    assert offers and all(p != 904 for p, *_ in offers)
    for planet_id, c, mx, quote in offers:
        for qty in sorted({1, max(1, mx // 2), mx}):
            uu = copy.deepcopy(u)
            before = uu.players["A"].credits
            res = _pt(uu, planet_id=planet_id, commodity=c, qty=qty)
            assert res.ok, (planet_id, c, qty, res.error)
            assert uu.players["A"].credits - before == lot_price(u.sectors[sid].port, Commodity(c), qty, 0)
            if qty == mx:
                assert uu.players["A"].credits - before == quote
        uu = copy.deepcopy(u)
        assert not _pt(uu, planet_id=planet_id, commodity=c, qty=mx + 1).ok and uu.players["A"].turns_today == 0
    listed = {(p, c) for p, c, *_ in offers}
    for pid_ in (900, 903, 904, 4242):
        for c in ("fuel_ore", "organics", "equipment", "colonists"):
            if (pid_, c) not in listed:
                uu = copy.deepcopy(u)
                assert not _pt(uu, planet_id=pid_, commodity=c, qty=1).ok


def test_legal_list_absent_reasons_and_flee_penalty():
    u, sid, a, pl = _lab(stock=(0, 0, 0))
    la = _la(u)
    assert not la.legal and "holds a commodity this port is buying" in la.reason and la.params["planets"] == []
    u, sid, a, pl = _lab()
    a.flee_penalty = True
    la = _la(u)
    assert la.legal and la.turn_cost == 1 + K.FLEE_PENALTY_TURNS
    assert _pt(u, planet_id=900, commodity="organics", qty=10).ok
    assert a.turns_today == 1 + K.FLEE_PENALTY_TURNS and not a.flee_penalty


# ---- step 5: fog --------------------------------------------------------------------------------------

def test_fog_rival_planet_never_shown_or_inferable():
    u, sid, a, pl = _lab()
    b = _sit(u, "B", sid)
    rival = _planet(u, 906, sid, owner="B", stock=(918_273, 827_364, 736_455))
    obs = build_observation(u, "A").model_dump_json()
    for n in ("918273", "827364", "736455"):
        assert n not in obs
    assert 906 not in _la(u).params["planet_id"]["choices"]
    errs = {_pt(u, planet_id=906, commodity=c, qty=q).error for c in ("fuel_ore", "organics", "equipment")
            for q in (1, 999_999_999)}
    assert errs == {NO_PLANET}
    assert a.turns_today == 0 and rival.stockpile[ORG] == 827_364
    # B (the rival) sees A's sale but never A's remaining stock or A's planet quote table
    assert _pt(u, planet_id=900, commodity="organics", qty=1_111).ok  # 1,889 left
    ob = build_observation(u, "B").model_dump(mode="json")
    blob = json.dumps(ob)
    assert "1889" not in blob and "1,889" not in blob
    assert not (next(x for x in ob["legal_actions"] if x["kind"] == "planet_trade")["legal"]) or \
        900 not in next(x for x in ob["legal_actions"] if x["kind"] == "planet_trade")["params"]["planet_id"]["choices"]
    assert b.credits == 10_000


def test_observation_port_flag():
    u, sid, a, pl = _lab()
    _sit(u, "B", sid)
    assert build_observation(u, "A").model_dump(mode="json")["sector"]["port"]["planet_trade_available"] is True
    assert build_observation(u, "B").model_dump(mode="json")["sector"]["port"]["planet_trade_available"] is False


# ---- tow (SHIP_TOW.md tt11 "port") ---------------------------------------------------------------------

def test_planet_trade_drops_a_tow_like_a_port_trade(monkeypatch):
    from tw2k.engine.fleet import _new_ship_id
    from tw2k.engine.models import ParkedShip
    monkeypatch.setattr(K, "TOW_MODE", "tw2002")
    monkeypatch.setattr(K, "FLEET_MODE", "tw2002")
    u, sid, a, pl = _lab()
    ship = Ship(ship_class=ShipClass.MERCHANT_FREIGHTER, name="spare", holds=65, fighters=0)
    fid = _new_ship_id(u)
    ship.fleet_id = fid
    u.parked_ships[fid] = ParkedShip(id=fid, owner_id="A", sector_id=sid, ship=ship, parked_day=u.day)
    assert _do(u, "A", ActionKind.TOW_ENGAGE, target=f"ship:{fid}").ok and a.ship.tow_lock is not None
    assert _pt(u, planet_id=900, commodity="organics", qty=100).ok
    assert a.ship.tow_lock is None


# ---- bots (step 6) -------------------------------------------------------------------------------------

def _bot_action(u, pid="A"):
    from tw2k.agents.seat_brain import SeatBrain
    return SeatBrain().decide(build_observation(u, pid).model_dump(mode="json"))


def test_bot_sells_organics_or_equipment_lot_at_the_quote_and_never_counters():
    u, sid, a, pl = _lab(stock=(3_000, 3_000, 3_000))
    act = _bot_action(u)
    assert act["kind"] == "planet_trade" and act["args"]["commodity"] in ("organics", "equipment")
    assert "offer" not in act["args"] and act["args"]["qty"] >= 500
    res = apply_action(u, "A", Action(kind=ActionKind.PLANET_TRADE, args=act["args"]))
    assert res.ok


def test_bot_never_sells_fuel_ore_and_respects_min_lot():
    u, sid, a, pl = _lab(stock=(9_000, 0, 499))
    act = _bot_action(u)
    assert act["kind"] != "planet_trade"
    pl.stockpile[EQ] = 500
    act = _bot_action(u)
    assert act["kind"] == "planet_trade" and act["args"] == {"planet_id": 900, "commodity": "equipment", "qty": 500}


def test_bot_policy_off_and_legacy_never_use_it():
    for name, value in (("BOT_PLANET_TRADE_POLICY", "off"), ("PLANET_TRADE_MODE", "legacy")):
        setattr(K, name, value)
        u, sid, a, pl = _lab()
        assert _bot_action(u)["kind"] != "planet_trade"
        setattr(K, name, dict(PT_DEFAULTS)[name])


def test_bot_action_passes_the_seat_validator():
    from tw2k.agents.seat_acceptance import validate_action
    u, sid, a, pl = _lab()
    obs = build_observation(u, "A").model_dump(mode="json")
    act = _bot_action(u)
    assert validate_action(obs, act) == []
    bad = dict(act, args=dict(act["args"], qty=act["args"]["qty"] + 10_000))
    assert any("exceeds envelope cap" in e for e in validate_action(obs, bad))


# ---- legacy ---------------------------------------------------------------------------------------------

def test_legacy_mode_has_no_verb_key_event_or_prompt():
    K.PLANET_TRADE_MODE = "legacy"
    u, sid, a, pl = _lab()
    assert "planet_trade" not in {x.kind for x in legal_actions(u, "A")}
    obs = build_observation(u, "A").model_dump(mode="json")
    assert "planet_trade_available" not in obs["sector"]["port"]
    assert "planet_trade" not in json.dumps(obs["legal_actions"])
    res = _pt(u, planet_id=900, commodity="organics", qty=100)
    assert not res.ok and "unsupported" in res.error and pl.stockpile[ORG] == 3_000 and a.credits == 10_000
    assert not [e for e in u.events if e.kind == EventKind.PLANET_TRADE]
    assert "PLANETARY TRADE" not in get_system_prompt()
    a.alive = False
    assert "planet_trade" not in {x.kind for x in legal_actions(u, "A")}


def test_prompt_paragraph_only_under_tw2002():
    assert "PLANETARY TRADE (docs/playtests/planets/PLANETARY_TRADING.md)" in get_system_prompt()
    assert "planet_trade {planet_id, commodity" in get_system_prompt()
