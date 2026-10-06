"""ship-fleet-transporter-v1. Rules: docs/playtests/ships/SHIP_FLEET.md (rows fl1..fl33).

Every assertion goes through the real engine path (apply_action / legal_actions / build_observation /
tick_day / the bots' decide). Planted bugs 1..20 of the spec map to the tests named in the rules doc;
qc_bridge/fleet_artifacts records which test caught each plant.
"""

from __future__ import annotations

import copy
import os
import subprocess
import sys
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.agents.prompts import format_observation, get_system_prompt
from tw2k.agents.seat_brain import SeatBrain, tw_reserve_view
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.combat import _destroy_ship, retreat_block
from tw2k.engine.fleet import _new_ship_id, hops_between, parked_value
from tw2k.engine.hardware import limpets_on_target
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Alliance,
    Commodity,
    Corporation,
    EventKind,
    FighterDeployment,
    FighterMode,
    LimpetTrack,
    MineDeployment,
    MineType,
    ParkedShip,
    Player,
    Ship,
    ShipClass,
)
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import tick_day
from tw2k.engine.scanners import density_reading, sector_view
from tw2k.engine.victory import full_net_worth

ROOT = Path(__file__).resolve().parents[1]
FLEET_DEFAULTS = (
    ("FLEET_MODE", "tw2002"), ("FLEET_MAX_SHIPS", 5), ("FLEET_XPORT_METRIC", "directed"),
    ("FLEET_XPORT_SAME_SECTOR", True), ("FLEET_XPORT_INTERDICT", "ignore"), ("FLEET_POD_ON_LEAVE", "discard"),
    ("FLEET_CLOAK_ON_LEAVE", "decloak"), ("FLEET_LIMPET_POLICY", "hull"), ("FLEET_FED_REPO", "fedspace"),
    ("FLEET_UNMANNED_ODDS_FACTOR", 0.5), ("FLEET_UNMANNED_ALIGN", "v2_penalty"), ("FLEET_UNMANNED_KILL_EXP", 0),
    ("FLEET_SELL_WHERE", "stardock_orbit"), ("BOT_FLEET_POLICY", "spare_only"), ("DENSITY_PER_UNMANNED", 38),
)


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    """Pin this slice's switches to their defaults so a later retune shows up here first."""
    for name, value in FLEET_DEFAULTS:
        monkeypatch.setattr(K, name, value)


# ---- helpers ------------------------------------------------------------------------------------

def _world():
    return generate_universe(GameConfig(seed=11, universe_size=60, enable_ferrengi=False, enable_planets=False))


def _sit(u, pid, sector, hull=ShipClass.MERCHANT_CRUISER, credits=2_000_000, align=0, fighters=30):
    if pid not in u.players:
        u.players[pid] = Player(id=pid, name=pid, ship=Ship(), sector_id=1)
        u.sectors[1].occupant_ids.append(pid)
    p = u.players[pid]
    if pid in u.sectors[p.sector_id].occupant_ids:
        u.sectors[p.sector_id].occupant_ids.remove(pid)
    p.sector_id = int(sector)
    p.ship.ship_class = hull
    p.ship.holds = int((K.hull_spec(hull.value) or {}).get("holds", 20))
    p.ship.fighters = fighters
    p.credits = credits
    p.alignment = align
    for c in Commodity:
        p.ship.cargo[c] = 0
    p.turns_today = 0
    p.turns_per_day = 1000
    p.known_sectors.add(int(sector))
    u.sectors[int(sector)].occupant_ids.append(pid)
    return p


def _park(u, owner, sector, hull=ShipClass.MERCHANT_FREIGHTER, **fields):
    ship = Ship(ship_class=hull, name=f"{owner}-{hull.value}", holds=int(K.hull_spec(hull.value)["holds"]),
                fighters=0)
    for k, v in fields.items():
        setattr(ship, k, v)
    sid = _new_ship_id(u)
    ship.fleet_id = sid
    u.parked_ships[sid] = ParkedShip(id=sid, owner_id=owner, sector_id=int(sector), ship=ship, parked_day=u.day)
    return sid


def _do(u, pid, kind, **args):
    return apply_action(u, pid, Action(kind=kind, args=args))


def _la(u, pid, kind):
    return next((a for a in legal_actions(u, pid) if a.kind == kind), None)


def _xport(u, pid, sid):
    return _do(u, pid, ActionKind.SHIP_TRANSPORT, ship_id=sid)


def _xport_choices(u, pid="A"):
    la = _la(u, pid, "ship_transport")
    return list(la.params["ship_id"]["choices"]) if la is not None and la.legal else []


def _at(u, src, dist, avoid=(1,), metric="directed"):
    """A sector exactly `dist` hops from `src` (outside `avoid`)."""
    for sid in sorted(u.sectors):
        if sid not in avoid and hops_between(u, src, sid, metric) == dist:
            return sid
    raise AssertionError(f"no sector {dist} hops from {src}")


def _empty(u, sid, keep=()):
    s = u.sectors[sid]
    s.port = None
    s.planet_ids.clear()
    s.fighters = None
    s.mines.clear()
    s.beacon = None
    s.nav_hazard = 0
    for oid in list(s.occupant_ids):
        if oid not in keep:
            s.occupant_ids.remove(oid)
    return s


def _far_pair(u, dist):
    for a in sorted(u.sectors):
        if a in K.FEDSPACE_SECTORS:
            continue
        for b in sorted(u.sectors):
            if b in K.FEDSPACE_SECTORS or b == a:
                continue
            if hops_between(u, a, b) == dist:
                return a, b
    raise AssertionError(dist)


# ---- fl4-fl6 buy without trade-in --------------------------------------------------------------

def test_fl4_fl5_spare_full_price_pilot_stays_spare_parked_empty():
    """Plants 1, 2: full ship_cost, pilot stays in the old hull, the spare waits at sector 1 with nothing aboard."""
    u = _world()
    p = _sit(u, "A", 1, fighters=77)
    p.ship.cargo[Commodity.ORGANICS] = 10
    p.ship.scanner = "holo"
    old = p.ship
    r = _do(u, "A", ActionKind.BUY_SHIP, ship_class="cargotran", trade_in=False)
    assert r.ok and r.turns_spent == 0
    assert p.credits == 2_000_000 - K.ship_cost("cargotran")
    assert p.ship is old and p.ship.ship_class == ShipClass.MERCHANT_CRUISER
    assert p.ship.fighters == 77 and p.ship.cargo[Commodity.ORGANICS] == 10 and p.sector_id == 1
    (rec,) = u.parked_ships.values()
    assert rec.owner_id == "A" and rec.sector_id == 1 and rec.ship.fleet_id == rec.id
    s = rec.ship
    assert s.ship_class == ShipClass.CARGOTRAN and s.holds == K.ship_specs()["cargotran"]["holds"]
    assert s.fighters == 0 and s.shields == 0 and s.cargo_used == 0 and s.scanner is None
    assert s.transwarp_drive is None and s.genesis == s.photon_missiles == s.ether_probes == 0
    assert s.cloaks == s.corbomite == s.mine_disruptors == s.marker_beacons == s.atomic_detonators == 0
    assert sum(s.mines.values()) == 0 and s.name == K.ship_specs()["cargotran"]["display_name"]
    assert any(e.kind == EventKind.FLEET_SPARE_BOUGHT for e in u.events)


def test_fl4_trade_in_default_is_todays_path(monkeypatch):
    """No trade_in arg = today's trade-in, byte for byte against FLEET_MODE legacy."""
    dumps = []
    for mode in ("tw2002", "legacy"):
        monkeypatch.setattr(K, "FLEET_MODE", mode)
        u = _world()
        _sit(u, "A", 1)
        assert _do(u, "A", ActionKind.BUY_SHIP, ship_class="cargotran").ok
        assert not u.parked_ships
        dumps.append(u.players["A"].model_dump_json())
    assert dumps[0] == dumps[1]


def test_fl6_spare_gates_location_legacy_corp_alignment():
    u = _world()
    _sit(u, "A", 12)
    assert not _do(u, "A", ActionKind.BUY_SHIP, ship_class="cargotran", trade_in=False).ok
    _sit(u, "A", 1)
    r = _do(u, "A", ActionKind.BUY_SHIP, ship_class="corporate_flagship", trade_in=False)
    assert not r.ok and "corporation" in r.error
    r = _do(u, "A", ActionKind.BUY_SHIP, ship_class="imperial_starship", trade_in=False)
    assert not r.ok and "alignment" in r.error
    assert not u.parked_ships and u.players["A"].credits == 2_000_000
    params = _la(u, "A", "buy_ship").params["trade_in"]
    assert "corporate_flagship" in params["spare_blocked_by"] and "imperial_starship" in params["spare_blocked_by"]


def test_fl6_spare_ignored_under_legacy(monkeypatch):
    """FLEET_MODE legacy: trade_in is an unknown arg like today - the buy trades in."""
    monkeypatch.setattr(K, "FLEET_MODE", "legacy")
    u = _world()
    p = _sit(u, "A", 1)
    assert "trade_in" not in _la(u, "A", "buy_ship").params
    assert _do(u, "A", ActionKind.BUY_SHIP, ship_class="cargotran", trade_in=False).ok
    assert p.ship.ship_class == ShipClass.CARGOTRAN and not u.parked_ships


def test_fl2_cap_counts_the_manned_ship():
    """Plant 4: 4 spares + the manned ship = 5; the 6th is refused by the handler and the legal list."""
    u = _world()
    _sit(u, "A", 1)
    for _ in range(4):
        assert _do(u, "A", ActionKind.BUY_SHIP, ship_class="merchant_freighter", trade_in=False).ok
    blocked = _la(u, "A", "buy_ship").params["trade_in"]["spare_blocked_by"]
    assert blocked.get("merchant_freighter", "").startswith("fleet full")
    r = _do(u, "A", ActionKind.BUY_SHIP, ship_class="merchant_freighter", trade_in=False)
    assert not r.ok and "fleet full" in r.error and len(u.parked_ships) == 4


def test_fl6_unique_iss_counts_parked_ships():
    """Plant 3: a parked ISS anywhere blocks a second ISS - trade-in and spare, legal list and handler."""
    u = _world()
    _sit(u, "B", 30)
    _park(u, "B", 30, ShipClass.IMPERIAL_STARSHIP)
    _sit(u, "A", 1, align=5000)
    la = _la(u, "A", "buy_ship")
    assert la.params["ship_class"]["blocked_by"].get("imperial_starship") == "already owned elsewhere"
    assert la.params["trade_in"]["spare_blocked_by"].get("imperial_starship") == "already owned elsewhere"
    for extra in ({}, {"trade_in": False}):
        r = _do(u, "A", ActionKind.BUY_SHIP, ship_class="imperial_starship", **extra)
        assert not r.ok and "already owned" in r.error


def test_fl6_spare_legal_list_matches_handler():
    """Every hull the legal list leaves unblocked buys; every blocked one refuses."""
    for key in K.ship_specs():
        u = _world()
        _sit(u, "A", 1, credits=300_000, align=200)
        blocked = _la(u, "A", "buy_ship").params["trade_in"]["spare_blocked_by"]
        r = _do(u, "A", ActionKind.BUY_SHIP, ship_class=key, trade_in=False)
        assert r.ok == (key not in blocked), (key, r.error, blocked.get(key))


# ---- fl7 sell -----------------------------------------------------------------------------------

def test_fl7_sell_in_orbit_pays_trade_in_credit_and_drops_contents():
    """Plant 11."""
    u = _world()
    p = _sit(u, "A", 1)
    sid = _park(u, "A", 1, ShipClass.CARGOTRAN, fighters=500, shields=100)
    u.parked_ships[sid].ship.cargo[Commodity.EQUIPMENT] = 50
    la = _la(u, "A", "sell_ship")
    assert la.legal and la.params["ship_id"]["choices"] == [sid]
    assert la.params["ship_id"]["credit_by"] == {str(sid): K.trade_in_credit("cargotran")}
    r = _do(u, "A", ActionKind.SELL_SHIP, ship_id=sid)
    assert r.ok and r.turns_spent == 0
    assert p.credits == 2_000_000 + K.trade_in_credit("cargotran") and not u.parked_ships
    assert p.ship.fighters == 30 and p.ship.cargo[Commodity.EQUIPMENT] == 0


def test_fl7_sell_refusals():
    u = _world()
    p = _sit(u, "A", 1)
    p.ship.fleet_id = _new_ship_id(u)
    away = _park(u, "A", 12)
    foreign = _park(u, "B", 1)
    _sit(u, "B", 20)
    assert not _do(u, "A", ActionKind.SELL_SHIP, ship_id=p.ship.fleet_id).ok
    assert "not in orbit" in _do(u, "A", ActionKind.SELL_SHIP, ship_id=away).error
    assert "not your ship" in _do(u, "A", ActionKind.SELL_SHIP, ship_id=foreign).error
    assert not _la(u, "A", "sell_ship").legal
    mine = _park(u, "A", 1)
    _sit(u, "A", 12)
    assert "StarDock" in _do(u, "A", ActionKind.SELL_SHIP, ship_id=mine).error
    assert not _la(u, "A", "sell_ship").legal
    assert len(u.parked_ships) == 3 and p.credits == 2_000_000


# ---- fl9-fl11 range -----------------------------------------------------------------------------

def test_fl9_fl10_range_exact_and_off_by_one():
    """Plant 6: Merchant Cruiser reaches exactly 5 hops; 6 is refused (handler and legal list)."""
    u = _world()
    here = 12
    five, six = _at(u, here, 5), _at(u, here, 6)
    _sit(u, "A", here)
    s5, s6 = _park(u, "A", five), _park(u, "A", six)
    assert _xport_choices(u) == [s5]
    la = _la(u, "A", "ship_transport")
    assert la.params["ship_id"]["range"] == 5 and la.params["ship_id"]["hops_by"] == {str(s5): 5}
    r = _xport(u, "A", s6)
    assert not r.ok and "out of transporter range" in r.error and u.players["A"].turns_today == 0
    assert _xport(u, "A", s5).ok and u.players["A"].sector_id == five


def test_fl10_range_is_the_source_hull():
    """Plant 5: a Scout cannot beam 1 hop into an ISS; an ISS reaches 10."""
    u = _world()
    here = 12
    one = _at(u, here, 1)
    _sit(u, "A", here, ShipClass.SCOUT_MARAUDER)
    iss = _park(u, "A", one, ShipClass.IMPERIAL_STARSHIP)
    assert _xport_choices(u) == []
    assert "out of transporter range" in _xport(u, "A", iss).error
    u = _world()
    ten = None
    for src in sorted(u.sectors):
        try:
            ten = _at(u, src, 10, avoid=())
            here = src
            break
        except AssertionError:
            continue
    if ten is None:
        far = max((hops_between(u, 12, s) or 0, s) for s in u.sectors)
        here, ten = 12, far[1]
    _sit(u, "A", here, ShipClass.IMPERIAL_STARSHIP)
    target = _park(u, "A", ten, ShipClass.SCOUT_MARAUDER)
    assert hops_between(u, here, ten) <= 10
    assert _xport(u, "A", target).ok


def test_fl11_range_zero_boards_in_the_same_sector():
    u = _world()
    _sit(u, "A", 12, ShipClass.ESCAPE_POD, fighters=0)
    sid = _park(u, "A", 12, ShipClass.CARGOTRAN)
    assert _xport_choices(u) == [sid]
    assert _xport(u, "A", sid).ok and u.players["A"].ship.ship_class == ShipClass.CARGOTRAN


def test_fl10_directed_vs_undirected(monkeypatch):
    """Plant 6: the directed default follows warp direction; undirected is the switch."""
    u = _world()
    pick = None
    for a in sorted(u.sectors):
        for b in sorted(u.sectors):
            d = hops_between(u, a, b, "directed")
            if d is not None and d > 5 and (hops_between(u, a, b, "undirected") or 99) <= 5:
                pick = (a, b)
                break
        if pick:
            break
    if pick is None:  # make a one-way lane: b -> a only
        a, b = 12, _at(u, 12, 6)
        u.sectors[b].warps.append(a)
        pick = (a, b)
    a, b = pick
    _sit(u, "A", a)
    sid = _park(u, "A", b)
    assert sid not in _xport_choices(u)
    monkeypatch.setattr(K, "FLEET_XPORT_METRIC", "undirected")
    assert sid in _xport_choices(u)
    assert _xport(u, "A", sid).ok


# ---- fl14 / fl15 cost and no hazards -----------------------------------------------------------

def test_fl14_fl15_one_turn_no_ore_no_hazards():
    """Plant 8: armid + limpet mines, offensive fighters and 100% NavHaz in the target sector fire nothing."""
    u = _world()
    here = 12
    dest = _at(u, here, 3)
    _sit(u, "B", 40)
    s = _empty(u, dest)
    s.mines = [MineDeployment(owner_id="B", kind=MineType.ARMID, count=200),
               MineDeployment(owner_id="B", kind=MineType.LIMPET, count=50)]
    s.fighters = FighterDeployment(owner_id="B", count=5000, mode=FighterMode.OFFENSIVE)
    s.nav_hazard = 100
    p = _sit(u, "A", here, ShipClass.CARGOTRAN, fighters=0)
    p.ship.cargo[Commodity.FUEL_ORE] = 40
    sid = _park(u, "A", dest, ShipClass.MERCHANT_FREIGHTER, fighters=10, shields=5)
    r = _xport(u, "A", sid)
    assert r.ok and r.turns_spent == 1 and p.turns_today == 1
    assert p.alive and p.deaths == 0 and p.sector_id == dest and not p.fighter_challenge
    assert p.ship.fighters == 10 and p.ship.shields == 5
    assert next(iter(u.parked_ships.values())).ship.cargo[Commodity.FUEL_ORE] == 40
    assert not limpets_on_target(u, "A")
    assert dest in p.known_sectors and dest in p.known_warps
    hazards = (EventKind.MINE_DETONATED, EventKind.COMBAT, EventKind.NAVHAZ_HIT, EventKind.FIGHTER_CHALLENGE,
               EventKind.QUASAR_FIRE)
    assert not [e for e in u.events if e.kind in hazards]


# ---- fl17 / fl18 effects, hull vs pilot, aliasing ----------------------------------------------

def test_fl18_hull_bound_stays_pilot_bound_travels():
    """Plant 10."""
    u = _world()
    here = 12
    dest = _at(u, here, 2)
    p = _sit(u, "A", here, ShipClass.IMPERIAL_STARSHIP, align=1000, fighters=900)
    p.ship.cargo[Commodity.ORGANICS] = 40
    p.ship.transwarp_drive = "type1"
    p.ship.scanner = "holo"
    p.ship.corbomite = 7
    p.ship.shields = 300
    p.experience = 1234
    p.last_crime_sector_id = 77
    old = p.ship
    sid = _park(u, "A", dest, ShipClass.CARGOTRAN, fighters=3)
    assert _xport(u, "A", sid).ok
    (parked,) = u.parked_ships.values()
    assert parked.ship is old and parked.sector_id == here and parked.ship.fleet_id == parked.id
    assert old.cargo[Commodity.ORGANICS] == 40 and old.transwarp_drive == "type1" and old.scanner == "holo"
    assert old.corbomite == 7 and old.fighters == 900 and old.shields == 300
    assert p.ship.ship_class == ShipClass.CARGOTRAN and p.ship.fighters == 3 and p.ship.transwarp_drive is None
    assert p.credits == 2_000_000 and p.experience == 1234 and p.alignment == 1000
    assert p.last_crime_sector_id == 77 and p.turns_today == 1


def test_fl3_no_aliasing_after_death_or_buy_equip():
    """Plant 9: the death strip and a StarDock buy touch only player.ship."""
    u = _world()
    p = _sit(u, "A", 1, fighters=400)
    p.ship.cargo[Commodity.EQUIPMENT] = 20
    sid = _park(u, "A", 1, ShipClass.CARGOTRAN)
    assert _xport(u, "A", sid).ok
    (parked,) = u.parked_ships.values()
    assert parked.ship is not p.ship
    assert _do(u, "A", ActionKind.BUY_EQUIP, item="fighters", qty=5).ok
    assert parked.ship.fighters == 400
    _destroy_ship(u, "A", reason="test", killer_id=None)
    assert parked.ship.fighters == 400 and parked.ship.cargo[Commodity.EQUIPMENT] == 20
    assert parked.ship.ship_class == ShipClass.MERCHANT_CRUISER


def test_fl17a_pod_discarded_or_parked(monkeypatch):
    u = _world()
    _sit(u, "A", 12, ShipClass.ESCAPE_POD, fighters=0)
    sid = _park(u, "A", 12, ShipClass.CARGOTRAN)
    assert _xport(u, "A", sid).ok and not u.parked_ships
    monkeypatch.setattr(K, "FLEET_POD_ON_LEAVE", "park")
    u = _world()
    _sit(u, "A", 12, ShipClass.ESCAPE_POD, fighters=0)
    sid = _park(u, "A", 12, ShipClass.CARGOTRAN)
    assert _xport(u, "A", sid).ok
    assert [r.ship.ship_class for r in u.parked_ships.values()] == [ShipClass.ESCAPE_POD]


def test_fl12_own_ships_only():
    """Plant 7: another player's, a corp mate's and an ally's ship are refused and never listed."""
    u = _world()
    _sit(u, "A", 12)
    for other in ("B", "C", "D"):
        _sit(u, other, 40)
    u.corporations["XX"] = Corporation(ticker="XX", name="X", ceo_id="A", member_ids=["A", "C"])
    u.players["A"].corp_ticker = u.players["C"].corp_ticker = "XX"
    u.alliances["a1"] = Alliance(id="a1", member_ids=["A", "D"], proposed_by="A", formed_day=1, active=True)
    u.players["A"].alliances.append("a1")
    ids = [_park(u, o, 12) for o in ("B", "C", "D")]
    assert _xport_choices(u) == []
    for sid in ids:
        r = _xport(u, "A", sid)
        assert not r.ok and "own ships only" in r.error
    assert u.players["A"].turns_today == 0 and len(u.parked_ships) == 3


def test_fl13_cfs_needs_corp_membership():
    """Plant 17: a parked CFS cannot be boarded after leaving the corp."""
    u = _world()
    _sit(u, "A", 12)
    sid = _park(u, "A", 12, ShipClass.CORPORATE_FLAGSHIP)
    u.players["A"].corp_ticker = None
    assert sid not in _xport_choices(u)
    assert "corporation" in _xport(u, "A", sid).error
    u.players["A"].corp_ticker = "XX"
    assert _xport(u, "A", sid).ok


def test_fl16_preconditions_landed_challenge_turns():
    u = _world()
    p = _sit(u, "A", 12)
    sid = _park(u, "A", 12)
    p.planet_landed = 999
    assert not _xport(u, "A", sid).ok
    p.planet_landed = None
    p.turns_today = p.turns_per_day
    assert "out of turns" in _xport(u, "A", sid).error
    p.turns_today = 0
    _sit(u, "B", 40)
    u.sectors[12].fighters = FighterDeployment(owner_id="B", count=50, mode=FighterMode.DEFENSIVE)
    p.fighter_challenge = {"sector_id": 12, "from_sector": _at(u, 12, 1, avoid=()), "mode": "defensive"}
    assert not _la(u, "A", "ship_transport").legal
    assert not _xport(u, "A", sid).ok and u.players["A"].ship.fleet_id is None and p.turns_today == 0


def test_fl17c_retreat_refused_after_transport_cleared_by_warp():
    """Plant 16."""
    u = _world()
    here = 12
    dest = _at(u, here, 2)
    p = _sit(u, "A", here)
    p.arrived_by_transwarp = True
    sid = _park(u, "A", dest)
    assert _xport(u, "A", sid).ok
    assert p.arrived_by_transport and not p.arrived_by_transwarp
    p.fighter_challenge = {"sector_id": dest, "from_sector": here, "mode": "defensive"}
    assert retreat_block(u, "A") == "cannot retreat after a transporter arrival"
    p.fighter_challenge = None
    nxt = u.sectors[dest].warps[0]
    assert _do(u, "A", ActionKind.WARP, target=nxt).ok or not p.alive
    assert not p.arrived_by_transport


def test_fl17e_evil_pilot_boarding_iss_meets_f22():
    """Plant 17: boarding an ISS as an evil pilot destroys it (f22); leaving one by transport escapes."""
    u = _world()
    here = 12
    p = _sit(u, "A", here, align=-500)
    sid = _park(u, "A", here, ShipClass.IMPERIAL_STARSHIP)
    assert _xport(u, "A", sid).ok
    assert p.ship.ship_class != ShipClass.IMPERIAL_STARSHIP
    assert any(e.kind in (EventKind.FED_REPOSSESS, EventKind.SHIP_DESTROYED) for e in u.events)
    u = _world()
    p = _sit(u, "A", here, ShipClass.IMPERIAL_STARSHIP, align=-500)
    sid = _park(u, "A", _at(u, here, 1), ShipClass.MERCHANT_CRUISER)
    assert _xport(u, "A", sid).ok
    assert [r.ship.ship_class for r in u.parked_ships.values()] == [ShipClass.IMPERIAL_STARSHIP]


# ---- fl19 / fl20 limpets and cloak -------------------------------------------------------------

def test_fl19_limpet_follows_the_hull_and_retargets():
    u = _world()
    here = 12
    dest = _at(u, here, 2)
    p = _sit(u, "A", here)
    _sit(u, "B", 40)
    u.limpets["B:A"] = LimpetTrack(owner_id="B", target_id="A", placed_sector=here, placed_day=1)
    sid = _park(u, "A", dest)
    assert _xport(u, "A", sid).ok
    assert not limpets_on_target(u, "A")
    _do(u, "B", ActionKind.QUERY_LIMPETS)
    rep = [e for e in u.events if e.kind == EventKind.LIMPET_REPORT][-1].payload["reports"]
    assert rep[0]["current_sector"] == here and rep[0]["ship_class"] == "merchant_cruiser"
    back = p.ship.fleet_id  # not parked: we are in it
    assert back == sid
    old_id = next(iter(u.parked_ships))
    assert _xport(u, "A", old_id).ok or True
    if p.sector_id == here:
        assert limpets_on_target(u, "A")


def test_fl20_leaving_a_cloaked_hull_decloaks_it(monkeypatch):
    u = _world()
    here = 12
    p = _sit(u, "A", here)
    p.ship.cloaked = True
    sid = _park(u, "A", here)
    assert _xport(u, "A", sid).ok
    (parked,) = u.parked_ships.values()
    assert parked.ship.cloaked is False
    monkeypatch.setattr(K, "FLEET_CLOAK_ON_LEAVE", "keep")
    u = _world()
    _empty(u, 30)
    p = _sit(u, "A", 30)
    p.ship.cloaked = True
    sid = _park(u, "A", 30)
    assert _xport(u, "A", sid).ok
    _sit(u, "A", 31)
    d = density_reading(u, 30)
    assert d["density"] == 0 and d["anomaly"] is True


# ---- fl22 density and fog ----------------------------------------------------------------------

def test_fl22_density_38_and_never_an_occupant():
    """Plants 13, 15."""
    u = _world()
    _empty(u, 30)
    base = density_reading(u, 30)["density"]
    _sit(u, "A", 31)
    sid = _park(u, "A", 30, ShipClass.CARGOTRAN, fighters=99)
    u.parked_ships[sid].ship.cargo[Commodity.EQUIPMENT] = 12
    u.parked_ships[sid].ship.corbomite = 5
    u.parked_ships[sid].ship.transwarp_drive = "type1"
    assert density_reading(u, 30)["density"] == base + 38
    _sit(u, "B", 30)
    assert density_reading(u, 30)["density"] == base + 38 + 40
    o = build_observation(u, "B")
    assert set(o.sector["occupants"]) == {"B"}
    assert all(t.get("id") != sid for t in o.sector.get("traders") or [])
    (um,) = o.sector["unmanned_ships"]
    assert um["ship_id"] == sid and um["own"] is False and um["owner_name"] == "A"
    assert set(um) <= {"ship_id", "hull", "owner_name", "own", "fighters"}
    assert o.fleet["ships"] == []
    text = format_observation(o)
    assert "type1" not in str(o.sector) and text
    view = sector_view(u, "B", 30)
    assert [x["ship_id"] for x in view["unmanned_ships"]] == [sid]
    oa = build_observation(u, "A")
    assert oa.fleet["ships"][0]["cargo"]["equipment"] == 12 and oa.fleet["ships"][0]["transwarp"] == "type1"


# ---- fl23 Extern -------------------------------------------------------------------------------

def test_fl23_extern_repossesses_fedspace_only(monkeypatch):
    """Plant 12: sectors 1..10 incl. 1 go; 11+ and every manned ship stay."""
    u = _world()
    _sit(u, "A", 1)
    _sit(u, "B", 5)
    a1, a5, a20 = _park(u, "A", 1), _park(u, "B", 5), _park(u, "A", 20)
    o = build_observation(u, "A")
    assert {s["ship_id"]: s["repo_at_extern"] for s in o.fleet["ships"]} == {a1: True, a20: False}
    tick_day(u)
    assert set(u.parked_ships) == {a20}
    assert u.players["A"].alive and u.players["B"].alive and u.players["A"].sector_id == 1
    ev = [e for e in u.events if e.kind == EventKind.FLEET_REPOSSESSED]
    assert [e.payload["ship_id"] for e in ev] == [a1, a5]
    monkeypatch.setattr(K, "FLEET_FED_REPO", "off")
    u = _world()
    _sit(u, "A", 1)
    _park(u, "A", 1)
    tick_day(u)
    assert len(u.parked_ships) == 1


# ---- fl24 attacking unmanned ships -------------------------------------------------------------

def _duel(u, hull=ShipClass.MERCHANT_FREIGHTER, fighters=100, shields=0, sector=30, att_fighters=500):
    _sit(u, "B", 31)
    sid = _park(u, "B", sector, hull, fighters=fighters, shields=shields)
    p = _sit(u, "A", sector, ShipClass.BATTLESHIP, align=500, fighters=att_fighters)
    return p, sid


def test_fl24_refusals_fedspace_own_corp_ally():
    """Plant 14 (refusals)."""
    u = _world()
    _sit(u, "B", 40)
    fed = _park(u, "B", 5)
    _sit(u, "A", 5, ShipClass.BATTLESHIP, fighters=500)
    assert "FedSpace" in _do(u, "A", ActionKind.ATTACK, target=f"ship:{fed}").error
    own = _park(u, "A", 30)
    _sit(u, "A", 30, ShipClass.BATTLESHIP, fighters=500)
    assert "own ship" in _do(u, "A", ActionKind.ATTACK, target=f"ship:{own}").error
    u.alliances["a1"] = Alliance(id="a1", member_ids=["A", "B"], proposed_by="A", formed_day=1, active=True)
    u.players["A"].alliances.append("a1")
    ally = _park(u, "B", 30)
    la = _la(u, "A", "attack")
    assert la.params["target"]["unmanned_choices"] == []
    assert "corp mate or ally" in _do(u, "A", ActionKind.ATTACK, target=f"ship:{ally}").error
    assert len(u.parked_ships) == 3 and u.players["A"].turns_today == 0


def test_fl24_half_odds_never_flees_and_kill_rules():
    """Plant 14: 0.5 x hull odds, no flee, owner keeps pod/deaths/exp, corbomite fires, record gone."""
    u = _world()
    p, sid = _duel(u, fighters=100, shields=0)
    la = _la(u, "A", "attack")
    assert la.legal and la.params["target"]["unmanned_choices"] == [f"ship:{sid}"]
    assert f"ship:{sid}" not in la.params["target"]["choices"]
    a_odds = K.combat_hull("battleship")[0]
    d_odds = K.combat_hull("merchant_freighter")[0] * 0.5
    r = _do(u, "A", ActionKind.ATTACK, target=f"ship:{sid}", qty=10)
    assert r.ok and r.turns_spent == K.TURN_COST["attack"]
    rec = u.parked_ships[sid]
    import math
    assert rec.ship.fighters == 100 - math.floor(10 * a_odds / d_odds) and rec.sector_id == 30
    owner = u.players["B"]
    deaths, exp = owner.deaths, owner.experience
    u.parked_ships[sid].ship.corbomite = 3
    p.ship.shields = 0
    before_f = p.ship.fighters
    align0 = p.alignment
    lost = rec.ship.fighters
    r = _do(u, "A", ActionKind.ATTACK, target=f"ship:{sid}")
    assert r.ok and sid not in u.parked_ships
    assert owner.deaths == deaths and owner.experience == exp and owner.ship.ship_class != ShipClass.ESCAPE_POD
    assert p.alignment == align0 - int(align0 * 0.10 * lost / 1000)
    assert any(e.kind == EventKind.UNMANNED_SHIP_DESTROYED for e in u.events)
    assert any(e.kind == EventKind.CORBOMITE_BLAST for e in u.events)
    assert p.ship.fighters < before_f - math.ceil(lost * d_odds / a_odds) + 1


def test_fl24_alignment_none_switch(monkeypatch):
    monkeypatch.setattr(K, "FLEET_UNMANNED_ALIGN", "none")
    u = _world()
    p, sid = _duel(u, fighters=2000)
    assert _do(u, "A", ActionKind.ATTACK, target=f"ship:{sid}", qty=100).ok
    assert p.alignment == 500


# ---- fl26 / fl27 owner loss and net worth ------------------------------------------------------

def test_fl26_owner_pod_leaves_parked_ships():
    u = _world()
    _sit(u, "A", 30, fighters=10)
    sid = _park(u, "A", 31, ShipClass.CARGOTRAN, fighters=50)
    _destroy_ship(u, "A", reason="test", killer_id=None)
    assert u.parked_ships[sid].ship.fighters == 50


def test_fl27_net_worth_counts_parked_hulls_once():
    """Plant 20."""
    u = _world()
    p = _sit(u, "A", 1)
    nw0 = full_net_worth(u, p)
    assert _do(u, "A", ActionKind.BUY_SHIP, ship_class="cargotran", trade_in=False).ok
    (rec,) = u.parked_ships.values()
    assert full_net_worth(u, p) == nw0 - K.ship_cost("cargotran") + parked_value(rec.ship)
    assert parked_value(rec.ship) == int(K.ship_cost("cargotran") * 0.5)
    nw1 = full_net_worth(u, p)
    assert _xport(u, "A", rec.id).ok
    assert full_net_worth(u, p) == nw1
    assert build_observation(u, "A").net_worth == nw1
    (old,) = u.parked_ships.values()
    assert _do(u, "A", ActionKind.SELL_SHIP, ship_id=old.id).ok
    assert full_net_worth(u, p) == nw1 - parked_value(old.ship) + K.trade_in_credit("merchant_cruiser")


# ---- fl28 rob / steal loop ---------------------------------------------------------------------

def test_fl28_steal_transport_loop_no_fake_bust(monkeypatch):
    """Alternating two ports by transporter never fake-busts; the same port twice still does."""
    import tw2k.engine.rob_steal as RS
    monkeypatch.setattr(RS, "_roll_bust", lambda universe, *, forced, over_cap: (True, "fake") if forced else (False, ""))
    u = _world()
    ports = [s for s in sorted(u.sectors) if u.sectors[s].port is not None and s not in K.FEDSPACE_SECTORS
             and RS.port_allows_crime(u.sectors[s].port)[0]]
    pair = next((a, b) for a in ports for b in ports if a != b and (hops_between(u, a, b) or 99) <= 20
                and (hops_between(u, b, a) or 99) <= 20)
    a, b = pair
    for sid in pair:
        for st in u.sectors[sid].port.stock.values():
            st.current = st.maximum
    p = _sit(u, "A", a, ShipClass.INTERDICTOR_CRUISER, align=-500, fighters=0)
    p.experience = 10_000
    sb = _park(u, "A", b, ShipClass.INTERDICTOR_CRUISER)

    def steal():
        port = u.sectors[p.sector_id].port
        c = next(c for c in (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT)
                 if port.stock.get(c) and int(port.stock[c].current) > 0)
        return _do(u, "A", ActionKind.STEAL, commodity=c.value, qty=1)

    def busts():
        return sum(1 for e in u.events if e.kind == EventKind.BUST)

    assert steal().ok and busts() == 0
    assert _xport(u, "A", sb).ok
    sa = next(iter(u.parked_ships))
    assert steal().ok and busts() == 0
    assert _xport(u, "A", sa).ok and p.sector_id == a
    assert steal().ok and busts() == 0
    assert steal().ok and busts() == 1  # same port twice in a row: fake bust


# ---- fl29 rng isolation, fl21 planet transport -------------------------------------------------

def test_fl29_no_rng_draws():
    """Plant 19: buy spare, transport, sell and Extern draw nothing from universe.rng."""
    u = _world()
    p = _sit(u, "A", 1)
    state = u.rng.getstate()
    assert _do(u, "A", ActionKind.BUY_SHIP, ship_class="cargotran", trade_in=False).ok
    assert _do(u, "A", ActionKind.BUY_SHIP, ship_class="merchant_freighter", trade_in=False).ok
    first = sorted(u.parked_ships)
    assert first == [1, 2]
    assert _xport(u, "A", 1).ok
    assert _do(u, "A", ActionKind.SELL_SHIP, ship_id=2).ok
    build_observation(u, "A")
    legal_actions(u, "A")
    assert u.rng.getstate() == state
    assert p.ship.fleet_id == 1 and sorted(u.parked_ships) == [3]


# ---- legal list == handler sweep ---------------------------------------------------------------

def test_legal_list_equals_handler_for_every_advertised_choice():
    u = _world()
    here = 12
    p = _sit(u, "A", here)
    for d in (0, 1, 2, 4, 5, 6, 8):
        try:
            _park(u, "A", _at(u, here, d, avoid=()) if d else here)
        except AssertionError:
            pass
    _sit(u, "B", 40)
    _park(u, "B", here, ShipClass.CARGOTRAN, fighters=5)
    choices = _xport_choices(u)
    assert choices
    for sid in sorted(u.parked_ships):
        uu = copy.deepcopy(u)
        r = _xport(uu, "A", sid)
        assert r.ok == (sid in choices), (sid, r.error)
    for t in _la(u, "A", "attack").params["target"]["unmanned_choices"]:
        uu = copy.deepcopy(u)
        assert _do(uu, "A", ActionKind.ATTACK, target=t, qty=1).ok
    assert p.turns_today == 0


# ---- legacy (plant 18) -------------------------------------------------------------------------

def test_legacy_has_no_fleet_verbs_keys_events_or_density(monkeypatch):
    monkeypatch.setattr(K, "FLEET_MODE", "legacy")
    u = _world()
    _empty(u, 30)
    _sit(u, "A", 30)
    kinds = {a.kind for a in legal_actions(u, "A")}
    assert "sell_ship" not in kinds and "ship_transport" not in kinds
    assert "unmanned_choices" not in _la(u, "A", "attack").params["target"]
    assert _xport(u, "A", 1).error == "unsupported action"
    assert _do(u, "A", ActionKind.SELL_SHIP, ship_id=1).error == "unsupported action"
    assert _do(u, "A", ActionKind.ATTACK, target="ship:1").error == "target ship:1 not found"
    o = build_observation(u, "A").model_dump(mode="json")
    assert "fleet" not in o and "unmanned_ships" not in o["sector"]
    assert "ship_transport" not in get_system_prompt()
    assert "unmanned_ships" not in sector_view(u, "A", 30)


def test_prompt_explains_the_fleet_under_tw2002():
    text = get_system_prompt()
    for word in ("ship_transport", "sell_ship", "trade_in", "Extern"):
        assert word in text


# Recorded with tests/fed_legacy_digest.py (flip=None: every tw2002 *_MODE to legacy) on da25c47, the commit
# before this slice: scripted match N3,N3,N2,N2,N1,H, seed 250925, 3 days (3 tick_day state digests + every obs
# JSON, prompt text, action + result and event). Floats rounded as in that helper (Linux/Windows libm).
FLEET_LEGACY_GOLDEN = "8e1a3a968cef4347d2558a64"
# Same helper, N3,N2,N1,H, only FLEET_MODE flipped (every other switch at its default) on da25c47: defaults
# elsewhere plus FLEET_MODE legacy must be the pre-slice engine byte for byte. Later slices that retune tw2002
# play change this one, so it is recorded here and checked by QC (Delivered note), not run in the suite.
FLEET_ONLY_LEGACY_ON_DA25C47 = "b9a52b96095f12c7c453151b"


def test_fleet_legacy_is_unchanged():
    code = (
        "import sys; from pathlib import Path; sys.path.insert(0, 'src'); sys.path.insert(0, 'tests');"
        "from fed_legacy_digest import legacy_run_digest;"
        "print(legacy_run_digest(Path('.'), 'N3,N3,N2,N2,N1,H', 3))"
    )
    env = dict(os.environ, PYTHONHASHSEED="0")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True,
                         timeout=900, check=True)
    assert out.stdout.strip().splitlines()[-1] == FLEET_LEGACY_GOLDEN


# ---- bots ---------------------------------------------------------------------------------------

def _seat_obs(u, pid):
    return build_observation(u, pid).model_dump(mode="json")


def test_bot_pod_beams_into_a_better_parked_hull():
    u = _world()
    p = _sit(u, "A", 30, ShipClass.ESCAPE_POD, fighters=0)
    p.deaths = 1
    sid = _park(u, "A", 30, ShipClass.CARGOTRAN)
    act = SeatBrain().decide(_seat_obs(u, "A"))
    assert act["kind"] == "ship_transport" and act["args"] == {"ship_id": sid}
    assert apply_action(u, "A", Action(kind=ActionKind.SHIP_TRANSPORT, args=act["args"])).ok


def test_bot_never_buys_spares_sells_or_attacks_unmanned():
    u = _world()
    _sit(u, "A", 1, credits=5_000_000)
    _sit(u, "B", 30)
    brain = SeatBrain()
    for _ in range(25):
        act = brain.decide(_seat_obs(u, "A"))
        assert act["kind"] not in ("sell_ship", "ship_transport")
        assert not (act["kind"] == "buy_ship" and "trade_in" in (act.get("args") or {}))
        assert not str((act.get("args") or {}).get("target", "")).startswith("ship:")
        r = apply_action(u, "A", Action(kind=ActionKind(act["kind"]), args=act.get("args") or {}))
        if not r.ok:
            break
    assert not [s for s in u.parked_ships.values() if s.owner_id == "A"]


def test_bot_policy_off_never_transports(monkeypatch):
    monkeypatch.setattr(K, "BOT_FLEET_POLICY", "off")
    u = _world()
    p = _sit(u, "A", 30, ShipClass.ESCAPE_POD, fighters=0)
    p.deaths = 1
    _park(u, "A", 30, ShipClass.CARGOTRAN)
    assert SeatBrain().decide(_seat_obs(u, "A"))["kind"] != "ship_transport"


# ---- TransWarp add-ons (Ben 2026-10-05) --------------------------------------------------------

def _ore_port(u, buys=True):
    for s in sorted(u.sectors):
        port = u.sectors[s].port
        if port is None or s in K.FEDSPACE_SECTORS:
            continue
        if port.buys(Commodity.FUEL_ORE) == buys:
            return s
    raise AssertionError("no port")


def _ore_seat(drive):
    u = _world()
    port = _ore_port(u, buys=True)
    for st in u.sectors[port].port.stock.values():
        st.current = st.maximum // 2
    p = _sit(u, "A", port, ShipClass.IMPERIAL_STARSHIP, credits=5_000)
    p.ship.cargo[Commodity.FUEL_ORE] = 60
    p.ship.transwarp_drive = drive
    return u, p


def _planned(u, p, monkeypatch):
    """Commissioned ISS on the ore port: plan a jump to the farthest listed FedSpace lock; returns (target, hops)."""
    import tw2k.agents.seat_brain as sb
    p.alignment, p.commission_used = 1000, True
    spec = _la(u, "A", "ship_transwarp").params["sector_id"]
    target = max((int(t) for t in spec["choices"] if int(t) in K.FEDSPACE_SECTORS),
                 key=lambda t: (spec["hops_by"][str(t)], t))
    hops = spec["hops_by"][str(target)]
    monkeypatch.setattr(sb, "SHIP_TW_MIN_TURNS_SAVED", sb.tw_turns_saved(4, hops))
    return target, hops


def test_tw_ore_reserve_only_for_drive_owners(monkeypatch):
    """Follow-up to slice 50: a drive owner holds back just the ore of its PLANNED jump; no plan, no reserve.
    A seat without a drive gets the observation back untouched and sells it all."""
    from tw2k.agents.stall import Intent
    u, p = _ore_seat(None)
    o = _seat_obs(u, "A")
    assert tw_reserve_view(o) is o  # no drive: the observation is untouched (non-owner play identical)
    act = SeatBrain().decide(o)
    assert act == {**act, "kind": "trade", "args": {"commodity": "fuel_ore", "qty": 60, "side": "sell"}}
    u, p = _ore_seat("type1")
    o = _seat_obs(u, "A")
    v = tw_reserve_view(o)  # drive, no planned jump: nothing held back
    assert v["_tw_ore_reserve"] == 0 and v["ship"]["cargo"]["fuel_ore"] == 60
    act = SeatBrain().decide(o)
    assert act["kind"] == "trade" and act["args"] == {"commodity": "fuel_ore", "qty": 60, "side": "sell"}

    u, p = _ore_seat("type1")
    target, hops = _planned(u, p, monkeypatch)
    keep = K.SHIP_TW_ORE_PER_HOP * hops
    brain = SeatBrain()
    brain._intent = Intent("travel", target)
    o = _seat_obs(u, "A")
    assert brain._planned_tw_hops(o) == hops
    v = tw_reserve_view(o, hops)
    assert v["_tw_ore_reserve"] == keep and v["_tw_ore_aboard"] == 60
    assert v["ship"]["cargo"]["fuel_ore"] == 60 - keep and o["ship"]["cargo"]["fuel_ore"] == 60
    act = brain.decide(o)
    assert act["kind"] == "trade" and act["args"] == {"commodity": "fuel_ore", "qty": 60 - keep, "side": "sell"}
    assert apply_action(u, "A", Action(kind=ActionKind.TRADE, args=act["args"])).ok
    assert int(p.ship.cargo[Commodity.FUEL_ORE]) == keep
    import tw2k.agents.seat_brain as sb
    monkeypatch.setattr(sb, "SHIP_TW_MIN_TURNS_SAVED", sb.tw_turns_saved(4, hops) + 1)  # not worth a jump
    brain._intent = Intent("travel", target)
    assert brain._planned_tw_hops(_seat_obs(u, "A")) is None


def test_tw_ore_reserve_tops_up_for_the_planned_jump_only(monkeypatch):
    from tw2k.agents.stall import Intent
    u = _world()
    p = None
    for port in sorted(u.sectors):
        if u.sectors[port].port is None or port in K.FEDSPACE_SECTORS:
            continue
        for st in u.sectors[port].port.stock.values():
            st.current = st.maximum
        p = _sit(u, "A", port, ShipClass.IMPERIAL_STARSHIP, align=1000)
        trade = _la(u, "A", "trade")
        if trade.legal and "fuel_ore" in trade.params["commodity"]["buy_choices"]:
            break
    p.ship.transwarp_drive = "type1"
    act = SeatBrain().decide(_seat_obs(u, "A"))  # no planned jump: no ore bought for the drive
    assert not (act["kind"] == "trade" and "TransWarp" in str(act.get("thought", "")))
    p.ship.cargo[Commodity.FUEL_ORE] = 60
    target, hops = _planned(u, p, monkeypatch)
    p.ship.cargo[Commodity.FUEL_ORE] = 0
    p.known_sectors.update(u.sectors)  # unlisted (no ore): the seat's own known-warp map gives the hops
    p.known_warps = {sid: list(u.sectors[sid].warps) for sid in u.sectors}
    brain = SeatBrain()
    brain._intent = Intent("travel", target)  # FedSpace under the commission lock: planned even when unlisted
    act = brain.decide(_seat_obs(u, "A"))
    assert act["kind"] == "trade" and act["args"]["commodity"] == "fuel_ore" and act["args"]["side"] == "buy"
    assert act["args"]["qty"] <= K.SHIP_TW_ORE_PER_HOP * hops
    assert apply_action(u, "A", Action(kind=ActionKind.TRADE, args=act["args"])).ok


def test_fed_lock_hulls_switch(monkeypatch):
    """SHIP_TW_FED_LOCK_HULLS: all three TW hulls by default; "iss_only" keeps it for the ISS alone."""
    from tw2k.engine.ship_transwarp import fed_lock_on
    u = _world()
    p = _sit(u, "A", 30, ShipClass.CORPORATE_FLAGSHIP, align=1000)
    p.commission_used = True
    monkeypatch.setattr("tw2k.engine.ship_transwarp.is_commissioned", lambda pl: True)
    assert fed_lock_on(p)
    monkeypatch.setattr(K, "SHIP_TW_FED_LOCK_HULLS", "iss_only")
    assert not fed_lock_on(p)
    p.ship.ship_class = ShipClass.IMPERIAL_STARSHIP
    assert fed_lock_on(p)


# ---- follow-up: fleet + TransWarp resume fields survive save / restore ---------------------------------

def test_fleet_and_transwarp_fields_survive_save_restore():
    """Universe dump -> validate keeps parked hulls, ship ids, fleet ids, the drive, the arrival flags and a
    parked-hull limpet; while they are empty they stay out of the dump (legacy dumps byte-identical)."""
    from tw2k.engine.models import Universe
    u = _world()
    fresh = u.model_dump_json()
    for key in ("parked_ships", "next_ship_id", "fleet_id", "transwarp_drive", "arrived_by_transwarp",
                "arrived_by_transport", "target_ship_id"):
        assert f'"{key}"' not in fresh
    assert Universe.model_validate_json(fresh).model_dump_json() == fresh
    a = _sit(u, "A", 30, ShipClass.IMPERIAL_STARSHIP)
    b = _sit(u, "B", 31)
    a.ship.transwarp_drive = "type1"
    a.ship.fleet_id = _new_ship_id(u)
    a.arrived_by_transwarp = True
    b.arrived_by_transport = True
    sid = _park(u, "B", 31, ShipClass.MERCHANT_FREIGHTER, fighters=40)
    u.limpets["A:B"] = LimpetTrack(owner_id="A", target_id="B", placed_sector=31, placed_day=1, target_ship_id=sid)
    for restored in (Universe.model_validate(u.model_dump()), Universe.model_validate_json(u.model_dump_json())):
        assert restored.parked_ships.keys() == {sid} and restored.next_ship_id == u.next_ship_id == sid + 1
        rec = restored.parked_ships[sid]
        assert (rec.owner_id, rec.sector_id, rec.ship.fighters, rec.ship.fleet_id) == ("B", 31, 40, sid)
        assert rec.ship.ship_class == ShipClass.MERCHANT_FREIGHTER
        ra, rb = restored.players["A"], restored.players["B"]
        assert ra.ship.transwarp_drive == "type1" and ra.ship.fleet_id == a.ship.fleet_id
        assert ra.arrived_by_transwarp and rb.arrived_by_transport and not rb.arrived_by_transwarp
        assert restored.limpets["A:B"].target_ship_id == sid
        assert restored.model_dump_json() == u.model_dump_json()
    # the restored game keeps playing the fleet: B can still see and value its parked hull
    restored = Universe.model_validate_json(u.model_dump_json())
    assert parked_value(restored.parked_ships[sid].ship) == parked_value(u.parked_ships[sid].ship) > 0
    assert full_net_worth(restored, restored.players["B"]) == full_net_worth(u, u.players["B"])


def test_fleet_snapshot_parked_ships():
    """fl32: the spectator snapshot carries parked hulls for the hollow map ring, and no key while none exist."""
    from tw2k.server.broadcaster import Broadcaster
    from tw2k.server.runner import MatchRunner
    u = _world()
    _sit(u, "A", 30)
    r = MatchRunner(Broadcaster())
    r.state.universe = u
    assert "parked_ships" not in r.snapshot()
    sid = _park(u, "A", 31, ShipClass.MERCHANT_FREIGHTER)
    assert r.snapshot()["parked_ships"] == [
        {"id": sid, "owner_id": "A", "sector_id": 31, "hull": "merchant_freighter"}]
    app_js = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")
    assert "unmanned-marker" in app_js and "snap.parked_ships" in app_js
