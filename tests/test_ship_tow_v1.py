"""ship-tow-transwarp2-v1: tractor tow + Type 2 TransWarp + Extern tow-lock hold (TOW_MODE).

docs/playtests/ships/SHIP_TOW.md rows tt1..tt32. Every rule runs through the real engine path
(apply_action / legal_actions / build_observation / tick_day).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.agents.prompts import get_system_prompt
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.fleet import _new_ship_id
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Commodity,
    EventKind,
    FighterDeployment,
    FighterMode,
    LimpetTrack,
    MineDeployment,
    MineType,
    ParkedShip,
    Planet,
    PlanetClass,
    Player,
    Ship,
    ShipClass,
)
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import tick_day
from tw2k.engine.ship_transwarp import hop_count

ROOT = Path(__file__).resolve().parents[1]
TOW_DEFAULTS = (
    ("TOW_MODE", "tw2002"), ("TOW_MANNED", "any"), ("TOW_MANNED_MAX_FIGHTERS", 0), ("TOW_UNMANNED_FIGHTERS", "allow"),
    ("TOW_TOWEE_TPW_MULT", 2), ("TOW_CHAIN", False), ("TOW_ON_ATTACK", "release"), ("TOW_ON_RETREAT", "drop"),
    ("TOW_ON_FED_TOW", "release"), ("TOW_LOCK_ON_XPORT", "keep_hull"), ("TOW_FUSE_TOWEE", "stays"),
    ("TOW_EXTERN_LOCK", "hold"), ("TOW_EXTERN_REQUIRE_GOOD", False), ("SHIP_TW_TYPE2_COST", 20_000),
    ("SHIP_TW_UPGRADE_COST", 9_000), ("SHIP_TW_TOW_ORE_PER_HOP", 6), ("BOT_TOW_POLICY", "extern_hold_only"),
    ("SHIP_TW_TURN_COST", "tpw"), ("FLEET_MODE", "tw2002"), ("SHIP_TW_MODE", "tw2002"),
)


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    for name, value in TOW_DEFAULTS:
        monkeypatch.setattr(K, name, value)


# ---- helpers ------------------------------------------------------------------------------------

def _world():
    return generate_universe(GameConfig(seed=11, universe_size=60, enable_ferrengi=False, enable_planets=False))


def _sit(u, pid, sector, hull=ShipClass.IMPERIAL_STARSHIP, credits=2_000_000, align=0, fighters=0):
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
    p.ship.shields = 0
    p.credits = credits
    p.alignment = align
    for c in Commodity:
        p.ship.cargo[c] = 0
    p.turns_today = 0
    p.turns_per_day = 1000
    p.known_sectors.add(int(sector))
    u.sectors[int(sector)].occupant_ids.append(pid)
    return p


def _park(u, owner, sector, hull=ShipClass.COLONIAL_TRANSPORT, **fields):
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


def _engage(u, pid, target):
    return _do(u, pid, ActionKind.TOW_ENGAGE, target=target)


def _choices(u, pid="A"):
    la = _la(u, pid, "tow_engage")
    return list(la.params["target"]["choices"]) if la is not None and la.legal else []


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


def _space(u, avoid=tuple(K.FEDSPACE_SECTORS)):
    """A non-FedSpace sector with an empty non-FedSpace neighbour (both cleared)."""
    for sid in sorted(u.sectors):
        if sid in avoid:
            continue
        for w in u.sectors[sid].warps:
            if int(w) not in avoid:
                _empty(u, sid)
                _empty(u, int(w))
                return sid, int(w)
    raise AssertionError("no space pair")


def _away(u, dist, avoid=tuple(K.FEDSPACE_SECTORS)):
    for here in sorted(u.sectors):
        if here in avoid:
            continue
        for sid in sorted(u.sectors):
            if sid not in avoid and sid != here and hop_count(u, here, sid) == dist:
                return here, sid
    raise AssertionError("no pair")


def _rel_events(u, reason=None):
    return [e for e in u.events if e.kind == EventKind.TOW_RELEASED and (reason is None or e.payload["reason"] == reason)]


def _lock(u, pid="A"):
    return u.players[pid].ship.tow_lock


def _towing_ct(u, hull=ShipClass.IMPERIAL_STARSHIP, towee=ShipClass.COLONIAL_TRANSPORT, **park):
    """A towing an own unmanned Colonial Transport in open space; returns (here, nxt, ship id)."""
    here, nxt = _space(u)
    _sit(u, "A", here, hull)
    sid = _park(u, "A", here, towee, **park)
    assert _engage(u, "A", f"ship:{sid}").ok
    return here, nxt, sid


# ---- tt1-tt5 engage ---------------------------------------------------------------------------------

def test_tt3_tow_own_parked_hull_for_zero_turns():
    u = _world()
    here, _nxt = _space(u)
    p = _sit(u, "A", here)
    sid = _park(u, "A", here)
    la = _la(u, "A", "tow_engage")
    assert la.legal and la.params["target"]["choices"] == [f"ship:{sid}"]
    assert la.params["target"]["cost_by"] == {f"ship:{sid}": 16} and la.params["target"]["kind_by"][f"ship:{sid}"] == "ship"
    res = _engage(u, "A", f"ship:{sid}")
    assert res.ok and res.turns_spent == 0 and p.turns_today == 0
    assert _lock(u).kind == "ship" and _lock(u).ship_id == sid
    assert any(e.kind == EventKind.TOW_ENGAGED and e.payload["cost"] == 16 for e in u.events)
    assert _la(u, "A", "tow_release").legal and not _la(u, "A", "tow_engage").legal  # one lock per hull (tt1)
    assert _do(u, "A", ActionKind.TOW_RELEASE).ok and _lock(u) is None
    assert _rel_events(u, "manual")


def test_tt3_refusals_other_sector_rival_corp_ally_pod_landed_legacy(monkeypatch):
    u = _world()
    here, nxt = _space(u)
    _sit(u, "A", here)
    _sit(u, "B", here, ShipClass.MERCHANT_CRUISER, fighters=5)
    far = _park(u, "A", nxt)
    rival = _park(u, "B", here)
    assert _choices(u) == []
    assert "not in your sector" in _engage(u, "A", f"ship:{far}").error
    assert "own ships only" in _engage(u, "A", f"ship:{rival}").error
    assert not _engage(u, "A", "ship:999").ok
    assert not _engage(u, "A", "ferrengi:1").ok
    mine = _park(u, "A", here)
    u.players["A"].ship.ship_class = ShipClass.ESCAPE_POD
    assert "escape pod" in _engage(u, "A", f"ship:{mine}").error and _choices(u) == []
    u.players["A"].ship.ship_class = ShipClass.IMPERIAL_STARSHIP
    u.players["A"].planet_landed = 1
    assert _engage(u, "A", f"ship:{mine}").error == "must be in space"
    u.players["A"].planet_landed = None
    monkeypatch.setattr(K, "TOW_MODE", "legacy")
    assert _la(u, "A", "tow_engage") is None and _la(u, "A", "tow_release") is None
    assert _engage(u, "A", f"ship:{mine}").error == "unsupported action"
    assert _do(u, "A", ActionKind.TOW_RELEASE).error == "unsupported action"


def test_tt3_cfs_after_corp_leave_refused():
    u = _world()
    here, _nxt = _space(u)
    _sit(u, "A", here)
    cfs = _park(u, "A", here, ShipClass.CORPORATE_FLAGSHIP)
    assert u.players["A"].corp_ticker is None
    assert "corporation hull" in _engage(u, "A", f"ship:{cfs}").error


def test_tt1_one_lock_per_target_and_no_chains():
    u = _world()
    here, _nxt = _space(u)
    _sit(u, "A", here)
    _sit(u, "B", here)
    sid = _park(u, "A", here)
    assert _engage(u, "A", f"ship:{sid}").ok
    assert not _engage(u, "A", f"ship:{_park(u, 'A', here)}").ok  # already locked
    assert _engage(u, "B", "player:A").error == "that trader is towing a ship"  # TOW_CHAIN False
    assert _do(u, "A", ActionKind.TOW_RELEASE).ok
    _sit(u, "C", here)
    assert _engage(u, "B", "player:A").ok
    assert _engage(u, "C", "player:A").error == "that trader is already in tow"
    assert _engage(u, "A", "player:C").error == "you are in tow yourself"


def test_tt4_manned_trader_fighters_fedspace_cloak_switches(monkeypatch):
    u = _world()
    here, _nxt = _space(u)
    _sit(u, "A", here)
    b = _sit(u, "B", here, ShipClass.MERCHANT_CRUISER, fighters=1)
    assert "fighters aboard" in _engage(u, "A", "player:B").error and _choices(u) == []
    b.ship.fighters = 0
    assert _choices(u) == ["player:B"]
    b.ship.cloaked = True
    assert _choices(u) == [] and not _engage(u, "A", "player:B").ok
    b.ship.cloaked = False
    monkeypatch.setattr(K, "TOW_MANNED", "off")
    assert not _engage(u, "A", "player:B").ok
    monkeypatch.setattr(K, "TOW_MANNED", "corp_ally")
    assert "corp mates" in _engage(u, "A", "player:B").error
    monkeypatch.setattr(K, "TOW_MANNED", "any")
    assert _engage(u, "A", "player:B").ok and _lock(u).kind == "player"
    for fed in (1, 10):
        u2 = _world()
        _sit(u2, "A", fed)
        _sit(u2, "B", fed, ShipClass.MERCHANT_CRUISER)
        assert _engage(u2, "A", "player:B").error == "you cannot tow a trader in FedSpace"


def test_tt3_unmanned_with_fighters_allow_and_refuse(monkeypatch):
    u = _world()
    here, _nxt = _space(u)
    _sit(u, "A", here)
    sid = _park(u, "A", here, fighters=200)
    assert f"ship:{sid}" in _choices(u)
    monkeypatch.setattr(K, "TOW_UNMANNED_FIGHTERS", "refuse")
    assert _choices(u) == [] and "carries fighters" in _engage(u, "A", f"ship:{sid}").error


def test_tt5_fighter_challenge_blocks_engage():
    u = _world()
    here, nxt = _space(u)
    a = _sit(u, "A", here, fighters=100)
    sid = _park(u, "A", nxt)
    _sit(u, "E", 1, ShipClass.MERCHANT_CRUISER)
    u.sectors[nxt].fighters = FighterDeployment(owner_id="E", count=50, mode=FighterMode.DEFENSIVE)
    assert _do(u, "A", ActionKind.WARP, target=nxt).ok and a.fighter_challenge
    la = _la(u, "A", "tow_engage")
    assert not la.legal
    assert not _engage(u, "A", f"ship:{sid}").ok and _lock(u) is None


# ---- tt6-tt10 moving ---------------------------------------------------------------------------------

@pytest.mark.parametrize("tower,towee,cost", [
    (ShipClass.IMPERIAL_STARSHIP, ShipClass.COLONIAL_TRANSPORT, 16),
    (ShipClass.IMPERIAL_STARSHIP, ShipClass.MERCHANT_FREIGHTER, 8),
    (ShipClass.STAR_MASTER, ShipClass.IMPERIAL_STARSHIP, 11),
    (ShipClass.IMPERIAL_STARSHIP, ShipClass.INTERDICTOR_CRUISER, 34),
])
def test_tt6_tow_cost_table_charged_to_the_tower_only(tower, towee, cost):
    u = _world()
    here, nxt = _space(u)
    a = _sit(u, "A", here, tower)
    sid = _park(u, "A", here, towee)
    assert _engage(u, "A", f"ship:{sid}").ok
    la = _la(u, "A", "warp")
    assert la.turn_cost == cost and la.params["tow_cost"] == cost
    res = _do(u, "A", ActionKind.WARP, target=nxt)
    assert res.ok and res.turns_spent == cost and a.turns_today == cost
    assert a.sector_id == nxt and u.parked_ships[sid].sector_id == nxt
    ev = [e for e in u.events if e.kind == EventKind.TOWED][-1]
    assert (ev.payload["from"], ev.payload["to"], ev.payload["via"]) == (here, nxt, "warp")


def test_tt6_manned_towee_turns_unchanged_and_arrives_with_the_tower():
    u = _world()
    here, nxt = _space(u)
    a = _sit(u, "A", here)
    b = _sit(u, "B", here, ShipClass.MERCHANT_FREIGHTER)
    b.turns_today = 7
    assert _engage(u, "A", "player:B").ok
    assert _do(u, "A", ActionKind.WARP, target=nxt).ok
    assert a.turns_today == 8 and b.turns_today == 7
    assert b.sector_id == nxt and "B" in u.sectors[nxt].occupant_ids and "B" not in u.sectors[here].occupant_ids
    assert b.prev_sector_id == here and nxt in b.known_sectors
    obs_b = build_observation(u, "B").model_dump(mode="json")
    assert obs_b["in_tow_by"] == {"name": "A", "hull": "imperial_starship"}
    assert "in_tow_by" not in build_observation(u, "A").model_dump(mode="json")


def test_tt6_out_of_turns_refused_and_hidden():
    u = _world()
    here, nxt, sid = _towing_ct(u)
    a = u.players["A"]
    a.turns_today = a.turns_per_day - 15
    la = _la(u, "A", "warp")
    assert not la.legal and la.params["target"]["choices"] == []
    res = _do(u, "A", ActionKind.WARP, target=nxt)
    assert not res.ok and a.sector_id == here and u.parked_ships[sid].sector_id == here
    assert a.turns_today == a.turns_per_day - 15
    plot = _do(u, "A", ActionKind.PLOT_COURSE, target=nxt, execute=True)
    assert not plot.ok and "16" in plot.error


def test_tt9_tower_destroyed_on_entry_leaves_the_towee():
    u = _world()
    here, nxt, sid = _towing_ct(u)
    _sit(u, "E", 1, ShipClass.MERCHANT_CRUISER)
    u.sectors[nxt].mines.append(MineDeployment(owner_id="E", kind=MineType.ARMID, count=500))
    a = u.players["A"]
    _do(u, "A", ActionKind.WARP, target=nxt)
    assert a.deaths == 1
    assert u.parked_ships[sid].sector_id == here
    assert a.ship.tow_lock is None and _rel_events(u, "tower_destroyed")
    assert not any(e.kind == EventKind.TOWED for e in u.events)


def test_tt8_towee_takes_no_entry_hazard():
    u = _world()
    here, nxt, sid = _towing_ct(u, fighters=40, shields=20, photon_missiles=1)
    a = u.players["A"]
    a.ship.fighters, a.ship.shields = 5000, 5000
    _sit(u, "E", 1, ShipClass.MERCHANT_CRUISER)
    u.sectors[nxt].mines.append(MineDeployment(owner_id="E", kind=MineType.ARMID, count=20))
    u.sectors[nxt].mines.append(MineDeployment(owner_id="E", kind=MineType.LIMPET, count=5))
    u.sectors[nxt].nav_hazard = 50
    before = (a.ship.fighters, a.ship.shields)
    assert _do(u, "A", ActionKind.WARP, target=nxt).ok
    rec = u.parked_ships[sid]
    assert rec.sector_id == nxt and (rec.ship.fighters, rec.ship.shields, rec.ship.photon_missiles) == (40, 20, 1)
    assert (a.ship.fighters, a.ship.shields) != before  # the tower took the hits
    assert not any(isinstance(lt, LimpetTrack) and lt.target_ship_id == sid for lt in u.limpets.values())


def test_tt10_interdictor_hold_charges_the_tow_cost_and_keeps_the_lock():
    u = _world()
    here, nxt, sid = _towing_ct(u, towee=ShipClass.INTERDICTOR_CRUISER)
    _sit(u, "E", 1, ShipClass.MERCHANT_CRUISER)
    planet = Planet(id=999, sector_id=here, name="Hold", class_id=next(iter(PlanetClass)), owner_id="E",
                    citadel_level=K.INTERDICTOR_MIN_LEVEL)
    planet.stockpile[Commodity.FUEL_ORE] = K.INTERDICTOR_FUEL
    u.planets[999] = planet
    u.sectors[here].planet_ids.append(999)
    a = u.players["A"]
    res = _do(u, "A", ActionKind.WARP, target=nxt)
    assert not res.ok and "interdict" in res.error and res.turns_spent == 34 and a.turns_today == 34
    assert _lock(u) is not None and u.parked_ships[sid].sector_id == here


# ---- tt11 break conditions ---------------------------------------------------------------------------

def test_tt11_attack_and_photon_release_unless_prelock(monkeypatch):
    u = _world()
    here, _nxt, sid = _towing_ct(u)
    u.players["A"].ship.fighters = 500
    b = _sit(u, "B", here, ShipClass.MERCHANT_CRUISER, fighters=1)
    b.ship.shields = 0
    assert _do(u, "A", ActionKind.ATTACK, target="B", fighters=10).ok
    assert _lock(u) is None and _rel_events(u, "attack")
    monkeypatch.setattr(K, "TOW_ON_ATTACK", "keep")
    assert _engage(u, "A", f"ship:{sid}").ok
    if u.players["B"].alive:
        _do(u, "A", ActionKind.ATTACK, target="B", fighters=1)
    assert _lock(u) is not None


def test_tt11_dock_verb_and_land_release():
    u = _world()
    _sit(u, "A", 1)
    sid = _park(u, "A", 1)
    assert _engage(u, "A", f"ship:{sid}").ok
    assert _do(u, "A", ActionKind.BUY_EQUIP, item="fighters", qty=1).ok
    assert _lock(u) is None and _rel_events(u, "dock")


def test_tt11_port_trade_releases():
    u = _world()
    for port in sorted(u.sectors):
        if u.sectors[port].port is None or port in K.FEDSPACE_SECTORS:
            continue
        for st in u.sectors[port].port.stock.values():
            st.current = st.maximum
        _sit(u, "A", port)
        la = _la(u, "A", "trade")
        if la.legal and la.params["commodity"]["buy_choices"]:
            break
    sid = _park(u, "A", port)
    assert _engage(u, "A", f"ship:{sid}").ok
    comm = (la.params["commodity"]["buy_choices"] or la.params["commodity"]["sell_choices"])[0]
    side = "buy" if comm in la.params["commodity"]["buy_choices"] else "sell"
    _do(u, "A", ActionKind.TRADE, commodity=comm, qty=1, side=side)
    assert _lock(u) is None and _rel_events(u, "port")


def test_tt11_manned_towee_self_warp_releases():
    u = _world()
    here, nxt = _space(u)
    _sit(u, "A", here)
    _sit(u, "B", here, ShipClass.MERCHANT_CRUISER)
    assert _engage(u, "A", "player:B").ok
    assert _do(u, "B", ActionKind.WARP, target=nxt).ok
    assert _lock(u) is None and _rel_events(u, "towee_moved")


def test_tt11h_manned_towee_in_fedspace_released_tower_moves_alone():
    u = _world()
    here, nxt = _space(u)
    _sit(u, "A", here)
    b = _sit(u, "B", here, ShipClass.MERCHANT_CRUISER)
    assert _engage(u, "A", "player:B").ok
    # B is (somehow) in FedSpace with A now: move both into sector 10's neighbourhood by hand
    fed = 10
    for pid in ("A", "B"):
        u.sectors[u.players[pid].sector_id].occupant_ids.remove(pid)
        u.players[pid].sector_id = fed
        u.sectors[fed].occupant_ids.append(pid)
    out = next(int(w) for w in u.sectors[fed].warps)
    assert _la(u, "A", "warp").turn_cost == 4  # no tow cost: the towee would be released
    assert _do(u, "A", ActionKind.WARP, target=out).ok
    assert u.players["A"].sector_id == out and b.sector_id == fed and _rel_events(u, "fedspace")


def test_tt14_towee_cloaking_after_lock_stays_in_tow_and_cloaked():
    u = _world()
    here, nxt = _space(u)
    _sit(u, "A", here)
    b = _sit(u, "B", here, ShipClass.MERCHANT_CRUISER)
    assert _engage(u, "A", "player:B").ok
    b.ship.cloaked = True
    assert _do(u, "A", ActionKind.WARP, target=nxt).ok
    assert b.sector_id == nxt and b.ship.cloaked and _lock(u) is not None


def test_tt11j_retreat_drop_vs_drag(monkeypatch):
    for mode, follows in (("drop", False), ("drag", True)):
        monkeypatch.setattr(K, "TOW_ON_RETREAT", mode)
        u = _world()
        here, nxt, sid = _towing_ct(u)
        a = u.players["A"]
        a.ship.fighters = 100
        _sit(u, "E", 1, ShipClass.MERCHANT_CRUISER)
        u.sectors[nxt].fighters = FighterDeployment(owner_id="E", count=50, mode=FighterMode.DEFENSIVE)
        assert _do(u, "A", ActionKind.WARP, target=nxt).ok
        assert a.fighter_challenge and u.parked_ships[sid].sector_id == nxt
        res = _do(u, "A", ActionKind.RETREAT)
        assert res.ok and a.sector_id == here
        assert (u.parked_ships[sid].sector_id == here) is follows
        assert (_lock(u) is not None) is follows
        if not follows:
            assert _rel_events(u, "retreat")


# ---- tt12 / tt13 transporters --------------------------------------------------------------------------

def test_tt12_ship_transport_out_leaves_a_dormant_lock_that_resumes(monkeypatch):
    u = _world()
    here, nxt, sid = _towing_ct(u)
    a = u.players["A"]
    tower_ship = a.ship
    spare = _park(u, "A", nxt, ShipClass.MERCHANT_FREIGHTER)
    assert _do(u, "A", ActionKind.SHIP_TRANSPORT, ship_id=spare).ok
    assert tower_ship.tow_lock is not None and a.ship.tow_lock is None
    assert not any(e.kind == EventKind.TOW_RELEASED for e in u.events)
    obs = build_observation(u, "A").model_dump(mode="json")
    assert obs["ship"]["tow"]["engaged"] is False and obs["ship"]["tow"]["target"] is None
    rec = next(r for r in u.parked_ships.values() if r.ship is tower_ship)
    assert _do(u, "A", ActionKind.SHIP_TRANSPORT, ship_id=rec.id).ok
    assert a.ship is tower_ship and _la(u, "A", "warp").turn_cost == 16
    monkeypatch.setattr(K, "TOW_LOCK_ON_XPORT", "release")
    assert _do(u, "A", ActionKind.SHIP_TRANSPORT, ship_id=next(r.id for r in u.parked_ships.values()
                                                            if r.ship.ship_class == ShipClass.MERCHANT_FREIGHTER)).ok
    assert tower_ship.tow_lock is None and _rel_events(u, "xport")


def test_tt12_dormant_lock_released_when_apart():
    u = _world()
    here, nxt, sid = _towing_ct(u)
    a = u.players["A"]
    tower_ship = a.ship
    spare = _park(u, "A", here, ShipClass.MERCHANT_FREIGHTER)
    assert _do(u, "A", ActionKind.SHIP_TRANSPORT, ship_id=spare).ok
    u.parked_ships[sid].sector_id = nxt  # the towee is moved away (any means)
    tick_day(u)
    assert tower_ship.tow_lock is None and _rel_events(u, "towee_gone")


def test_tt15_limpet_on_towee_follows_it():
    u = _world()
    here, nxt, sid = _towing_ct(u)
    _sit(u, "E", 1, ShipClass.MERCHANT_CRUISER)
    u.limpets["E:A"] = LimpetTrack(owner_id="E", target_id="A", placed_sector=here, placed_day=1, target_ship_id=sid)
    assert _do(u, "A", ActionKind.WARP, target=nxt).ok
    from tw2k.engine.fleet import limpet_location
    assert limpet_location(u, u.limpets["E:A"])[0] == nxt


# ---- tt16-tt21 Type 2 ----------------------------------------------------------------------------------

def test_tt16_type2_buy_upgrade_and_refusals():
    u = _world()
    a = _sit(u, "A", 1, credits=100_000)
    la = _la(u, "A", "buy_equip")
    prices = la.params["item"]["unit_price_by"]
    assert prices["transwarp_type2"] == 20_000 and "transwarp_upgrade" not in prices
    assert _do(u, "A", ActionKind.BUY_EQUIP, item="transwarp_type2", qty=1).ok
    assert a.ship.transwarp_drive == "type2" and a.credits == 80_000
    assert _do(u, "A", ActionKind.BUY_EQUIP, item="transwarp_drive", qty=1).error == "already fitted"
    assert _do(u, "A", ActionKind.BUY_EQUIP, item="transwarp_upgrade", qty=1).error == "already fitted"
    a.ship.transwarp_drive = None
    assert "Type 1" in _do(u, "A", ActionKind.BUY_EQUIP, item="transwarp_upgrade", qty=1).error
    a.ship.transwarp_drive = "type1"
    prices = _la(u, "A", "buy_equip").params["item"]["unit_price_by"]
    assert prices.get("transwarp_upgrade") == 9_000 and "transwarp_type2" not in prices
    assert _do(u, "A", ActionKind.BUY_EQUIP, item="transwarp_upgrade", qty=1).ok
    assert a.ship.transwarp_drive == "type2" and a.credits == 71_000
    for hull in (ShipClass.CORPORATE_FLAGSHIP, ShipClass.HAVOC_GUNSTAR):
        b = _sit(u, "B", 1, hull)
        b.ship.transwarp_drive = None
        assert _do(u, "B", ActionKind.BUY_EQUIP, item="transwarp_type2", qty=1).ok
    c = _sit(u, "C", 1, ShipClass.CARGOTRAN)
    assert "transwarp_type2" not in (_la(u, "C", "buy_equip").params["item"].get("unit_price_by") or {})
    assert not _do(u, "C", ActionKind.BUY_EQUIP, item="transwarp_type2", qty=1).ok and c.ship.transwarp_drive is None
    here, _n = _space(u)
    _sit(u, "D", here, credits=100_000)
    assert not _do(u, "D", ActionKind.BUY_EQUIP, item="transwarp_type2", qty=1).ok
    from tw2k.engine.class0 import special_port_at
    c0 = next((sid for sid in sorted(u.sectors) if sid != 1 and special_port_at(u, sid) is not None), None)
    if c0 is not None:  # a Class 0 port sells hardware, but the Type 2 shelf is StarDock only
        d = _sit(u, "D", c0, credits=100_000)
        assert "transwarp_type2" not in (_la(u, "D", "buy_equip").params["item"].get("unit_price_by") or {})
        assert not _do(u, "D", ActionKind.BUY_EQUIP, item="transwarp_type2", qty=1).ok and d.ship.transwarp_drive is None


def _tow_jump_world(dist=4, ore=60, towee=ShipClass.COLONIAL_TRANSPORT, drive="type2"):
    u = _world()
    here, dest = _away(u, dist)
    _empty(u, here)
    a = _sit(u, "A", here)
    a.ship.transwarp_drive = drive
    a.ship.cargo[Commodity.FUEL_ORE] = ore
    a.known_sectors.add(dest)
    u.sectors[dest].fighters = FighterDeployment(owner_id="A", count=1, mode=FighterMode.DEFENSIVE)
    sid = _park(u, "A", here, towee)
    u.parked_ships[sid].ship.cargo[Commodity.FUEL_ORE] = 50
    assert _engage(u, "A", f"ship:{sid}").ok
    return u, a, here, dest, sid


def test_tt19_type2_tow_jump_costs_and_carries_the_towee(monkeypatch):
    u, a, here, dest, sid = _tow_jump_world()
    _sit(u, "E", 1, ShipClass.MERCHANT_CRUISER)
    u.sectors[dest].mines.append(MineDeployment(owner_id="E", kind=MineType.ARMID, count=5))
    a.ship.fighters, a.ship.shields = 5000, 5000
    spec = _la(u, "A", "ship_transwarp").params["sector_id"]
    assert spec["tow_ore_by"][str(dest)] == 24 and spec["tow_turns_by"][str(dest)] == 16
    res = _do(u, "A", ActionKind.SHIP_TRANSWARP, sector_id=dest)
    assert res.ok and res.turns_spent == 16
    assert a.ship.cargo[Commodity.FUEL_ORE] == 36 and u.parked_ships[sid].ship.cargo[Commodity.FUEL_ORE] == 50
    assert u.parked_ships[sid].sector_id == dest and u.parked_ships[sid].ship.fighters == 0
    ev = [e for e in u.events if e.kind == EventKind.SHIP_TRANSWARP][-1]
    assert ev.payload["tow"] == {"hull": "colonial_transport", "ore": 24}
    monkeypatch.setattr(K, "SHIP_TW_TURN_COST", "hops")
    u, a, here, dest, sid = _tow_jump_world()
    assert _do(u, "A", ActionKind.SHIP_TRANSWARP, sector_id=dest).turns_spent == 64


def test_tt19_short_ore_refuses_the_whole_tow_jump():
    u, a, here, dest, sid = _tow_jump_world(ore=23)
    la = _la(u, "A", "ship_transwarp")
    assert la is None or not la.legal or dest not in la.params["sector_id"]["choices"]
    res = _do(u, "A", ActionKind.SHIP_TRANSWARP, sector_id=dest)
    assert not res.ok and "need 24" in res.error
    assert a.sector_id == here and _lock(u) is not None and a.ship.cargo[Commodity.FUEL_ORE] == 23


def test_tt18_type2_without_lock_is_type1():
    u, a, here, dest, sid = _tow_jump_world()
    assert _do(u, "A", ActionKind.TOW_RELEASE).ok
    res = _do(u, "A", ActionKind.SHIP_TRANSWARP, sector_id=dest)
    assert res.ok and res.turns_spent == 4 and a.ship.cargo[Commodity.FUEL_ORE] == 48
    assert u.parked_ships[sid].sector_id == here
    ev = [e for e in u.events if e.kind == EventKind.SHIP_TRANSWARP][-1]
    assert "tow" not in ev.payload


def test_tt17_type1_with_lock_drops_the_tow_and_jumps_alone():
    u, a, here, dest, sid = _tow_jump_world(drive="type1")
    spec = _la(u, "A", "ship_transwarp").params["sector_id"]
    assert spec.get("drops_tow") is True and "tow_ore_by" not in spec
    res = _do(u, "A", ActionKind.SHIP_TRANSWARP, sector_id=dest)
    assert res.ok and res.turns_spent == 4 and a.ship.cargo[Commodity.FUEL_ORE] == 48
    assert a.sector_id == dest and u.parked_ships[sid].sector_id == here
    assert _lock(u) is None and _rel_events(u, "type1_transwarp")


def test_tt19_commission_lock_tows_an_unmanned_ship_into_sector_1():
    u = _world()
    here = next(s for s in sorted(u.sectors) if s not in K.FEDSPACE_SECTORS and 2 <= (hop_count(u, s, 1) or 0) <= 6)
    a = _sit(u, "A", here, align=1000)
    a.commission_used = True
    a.ship.transwarp_drive = "type2"
    a.ship.cargo[Commodity.FUEL_ORE] = 100
    sid = _park(u, "A", here, ShipClass.MERCHANT_FREIGHTER)
    assert _engage(u, "A", f"ship:{sid}").ok
    assert 1 in _la(u, "A", "ship_transwarp").params["sector_id"]["choices"]
    assert _do(u, "A", ActionKind.SHIP_TRANSWARP, sector_id=1).ok
    assert a.sector_id == 1 and u.parked_ships[sid].sector_id == 1


def test_tt20_blind_tow_density0_and_fuse_stays_or_destroyed(monkeypatch):
    u, a, here, dest, sid = _tow_jump_world()
    u.sectors[dest].fighters = None
    _empty(u, dest)
    assert dest not in (_la(u, "A", "ship_transwarp").params.get("sector_id") or {}).get("choices", [])
    assert _do(u, "A", ActionKind.SHIP_TRANSWARP, sector_id=dest).ok
    assert a.sector_id == dest and u.parked_ships[sid].sector_id == dest
    for mode, survives in (("stays", True), ("destroyed", False)):
        monkeypatch.setattr(K, "TOW_FUSE_TOWEE", mode)
        u, a, here, dest, sid = _tow_jump_world()
        u.sectors[dest].fighters = None
        _sit(u, "E", dest, ShipClass.MERCHANT_CRUISER)  # density > 0
        assert _do(u, "A", ActionKind.SHIP_TRANSWARP, sector_id=dest).ok
        assert a.deaths == 1
        assert (sid in u.parked_ships) is survives
        if survives:
            assert u.parked_ships[sid].sector_id == here
        assert _rel_events(u, "tower_destroyed")


def test_tt19_manned_towee_gets_arrived_by_transwarp():
    u = _world()
    here, dest = _away(u, 3)
    _empty(u, here)
    a = _sit(u, "A", here)
    a.ship.transwarp_drive = "type2"
    a.ship.cargo[Commodity.FUEL_ORE] = 60
    a.known_sectors.add(dest)
    u.sectors[dest].fighters = FighterDeployment(owner_id="A", count=1, mode=FighterMode.DEFENSIVE)
    b = _sit(u, "B", here, ShipClass.MERCHANT_CRUISER)
    assert _engage(u, "A", "player:B").ok
    res = _do(u, "A", ActionKind.SHIP_TRANSWARP, sector_id=dest)
    assert res.ok and res.turns_spent == 4 + 2 * 3
    assert b.sector_id == dest and b.arrived_by_transwarp


def test_tt21_observation_type2_block_and_rival_sees_nothing():
    u, a, here, dest, sid = _tow_jump_world()
    _sit(u, "B", here, ShipClass.MERCHANT_CRUISER, fighters=5)
    obs = build_observation(u, "A").model_dump(mode="json")
    tw = obs["ship"]["transwarp"]
    assert tw["fitted"] == "type2" and tw["tow_capable"] and tw["tow_ore_per_hop"] == 6 and tw["max_tow_hops_now"] == 10
    tow = obs["ship"]["tow"]
    assert tow["engaged"] and tow["target"] == {"kind": "ship", "hull": "colonial_transport", "ship_id": sid}
    assert tow["turns_per_tow_warp"] == 16
    fleet = {s["ship_id"]: s for s in obs["fleet"]["ships"]}
    assert fleet[sid]["in_tow"] is True and fleet[sid]["extern_hold"] is False
    rival = build_observation(u, "B").model_dump(mode="json")
    text = str(rival)
    assert "tow_capable" not in text and "type2" not in text and "in_tow" not in text
    assert rival["ship"]["tow"]["target"] is None and "in_tow_by" not in rival


# ---- tt22-tt24 Extern ---------------------------------------------------------------------------------

def _spare_at_dock(u, fighters=0):
    a = _sit(u, "A", 1, fighters=fighters)
    sid = _park(u, "A", 1, ShipClass.MERCHANT_FREIGHTER)
    return a, sid


def test_tt22_extern_hold_keeps_a_locked_spare_overnight():
    u = _world()
    a, sid = _spare_at_dock(u)
    assert _engage(u, "A", f"ship:{sid}").ok
    obs = build_observation(u, "A").model_dump(mode="json")
    entry = next(s for s in obs["fleet"]["ships"] if s["ship_id"] == sid)
    assert entry["extern_hold"] is True and entry["repo_at_extern"] is False
    assert obs["ship"]["tow"]["extern_hold_ok"] is True
    for _day in range(3):
        tick_day(u)
        assert sid in u.parked_ships and _lock(u) is not None  # the lock persists into the next day
    assert sum(1 for e in u.events if e.kind == EventKind.EXTERN_TOW_HOLD) == 3
    # control seat without a lock loses its spare on night 1
    b = _sit(u, "B", 1)
    other = _park(u, "B", 1, ShipClass.MERCHANT_FREIGHTER)
    tick_day(u)
    assert other not in u.parked_ships and sid in u.parked_ships
    del b


@pytest.mark.parametrize("breaker", ["fighters", "dormant", "away", "landed", "off"])
def test_tt22_extern_hold_fails_without_every_condition(breaker, monkeypatch):
    u = _world()
    a, sid = _spare_at_dock(u)
    assert _engage(u, "A", f"ship:{sid}").ok
    if breaker == "fighters":
        a.ship.fighters = K.FED_TOW_FIGHTER_LIMIT + 1
        why = build_observation(u, "A").model_dump(mode="json")["ship"]["tow"]["why_not"]
        assert why == "tower_has_too_many_fighters"
    elif breaker == "dormant":
        spare2 = _park(u, "A", 1, ShipClass.MERCHANT_CRUISER)
        assert _do(u, "A", ActionKind.SHIP_TRANSPORT, ship_id=spare2).ok
    elif breaker == "away":
        u.sectors[1].occupant_ids.remove("A")
        a.sector_id = 2
        u.sectors[2].occupant_ids.append("A")
        why = build_observation(u, "A").model_dump(mode="json")["ship"]["tow"]["why_not"]
        assert why == "not_same_sector"
    elif breaker == "landed":
        a.planet_landed = 4242
        why = build_observation(u, "A").model_dump(mode="json")["ship"]["tow"]["why_not"]
        assert why == "landed"
    else:
        monkeypatch.setattr(K, "TOW_EXTERN_LOCK", "off")
    tick_day(u)
    assert sid not in u.parked_ships
    assert not any(e.kind == EventKind.EXTERN_TOW_HOLD for e in u.events)


def test_tt23_fed_tow_of_the_tower_releases_but_the_ship_survived():
    u = _world()
    a, sid = _spare_at_dock(u, fighters=0)
    assert _engage(u, "A", f"ship:{sid}").ok
    import tw2k.engine.fed as fed
    from tw2k.engine.fed import run_tows as real_run_tows

    def fake_run_tows(universe):
        n = real_run_tows(universe)
        p = universe.players["A"]  # the Feds tow the tower out of FedSpace after the hold
        universe.sectors[p.sector_id].occupant_ids.remove("A")
        p.sector_id = 11 if 11 in universe.sectors else max(universe.sectors)
        universe.sectors[p.sector_id].occupant_ids.append("A")
        return n + 1
    fed.run_tows = fake_run_tows
    try:
        tick_day(u)
    finally:
        fed.run_tows = real_run_tows
    assert sid in u.parked_ships and _lock(u) is None and _rel_events(u, "fed_tow")


# ---- tt25 Ferrengi / tt28 net worth / tt27 rng ------------------------------------------------------

def test_tt25_ferrengi_tribute_from_the_tower_then_release():
    from tw2k.engine.models import FerrengiShip
    u = _world()
    here, nxt, sid = _towing_ct(u)
    a = u.players["A"]
    a.credits = 50_000
    rec = u.parked_ships[sid]
    rec.ship.cargo[Commodity.EQUIPMENT] = 30
    f = FerrengiShip(id="F1", name="Grabby", sector_id=here, aggression=3, fighters=10, shields=10)
    u.ferrengi["F1"] = f
    a.ferrengi_encounter = {"ferr_id": "F1", "sector_id": here, "day": u.day, "demand": 1000}
    res = _do(u, "A", ActionKind.TOW_RELEASE)
    assert rec.ship.cargo[Commodity.EQUIPMENT] == 30
    assert res.ok and _lock(u) is None


def test_tt28_net_worth_counts_type2_like_type1_and_the_towed_hull_once():
    from tw2k.engine.victory import full_net_worth
    u, a, here, dest, sid = _tow_jump_world()
    nw_locked = full_net_worth(u, a)
    assert _do(u, "A", ActionKind.TOW_RELEASE).ok
    assert full_net_worth(u, a) == nw_locked
    a.ship.transwarp_drive = "type1"
    nw1 = full_net_worth(u, a)
    a.ship.transwarp_drive = "type2"
    assert full_net_worth(u, a) == nw1  # slice 48 does not value the drive; Type 2 follows it


def test_tt27_tow_draws_no_rng():
    u = _world()
    here, nxt, sid = _towing_ct(u)
    state = u.rng.getstate() if hasattr(u, "rng") and hasattr(u.rng, "getstate") else None
    assert _do(u, "A", ActionKind.WARP, target=nxt).ok
    assert _do(u, "A", ActionKind.TOW_RELEASE).ok
    if state is not None:
        assert u.rng.getstate() == state


# ---- tt5 legal == handler sweep / tt29 events / tt30 prompt --------------------------------------------

def test_legal_list_matches_handler_for_every_advertised_tow_target():
    u = _world()
    here, _nxt = _space(u)
    _sit(u, "A", here)
    _sit(u, "B", here, ShipClass.MERCHANT_CRUISER)
    _sit(u, "C", here, ShipClass.MERCHANT_CRUISER, fighters=3)
    _park(u, "A", here)
    _park(u, "A", here, ShipClass.MERCHANT_FREIGHTER)
    _park(u, "C", here)
    adv = _choices(u)
    assert len(adv) == 3 and "player:C" not in adv
    for t in adv:
        assert _engage(u, "A", t).ok, t
        assert _do(u, "A", ActionKind.TOW_RELEASE).ok
    for t in ("player:C", "ship:3", "ship:77", "player:Z", "bogus"):
        if t not in adv:
            assert not _engage(u, "A", t).ok


def test_tt29_events_visible_to_tower_towee_and_witnesses_only():
    u = _world()
    here, nxt = _space(u)
    _sit(u, "A", here)
    _sit(u, "B", here, ShipClass.MERCHANT_CRUISER)
    _sit(u, "W", nxt, ShipClass.MERCHANT_CRUISER, fighters=5)
    far = next(s for s in sorted(u.sectors) if s not in (here, nxt) and s not in K.FEDSPACE_SECTORS)
    _sit(u, "R", far, ShipClass.MERCHANT_CRUISER, fighters=5)
    assert _engage(u, "A", "player:B").ok
    assert _do(u, "A", ActionKind.WARP, target=nxt).ok

    def kinds(pid):
        return {e["kind"] for e in build_observation(u, pid).model_dump(mode="json")["recent_events"]}
    assert {"tow_engaged", "towed"} <= kinds("A") and {"tow_engaged", "towed"} <= kinds("B")
    assert "towed" in kinds("W") and "tow_engaged" not in kinds("W")
    assert not ({"tow_engaged", "towed"} & kinds("R"))


def test_tt30_prompt_paragraph_only_under_tw2002(monkeypatch):
    assert "TOWING (docs/playtests/ships/SHIP_TOW.md)" in get_system_prompt()
    monkeypatch.setattr(K, "TOW_MODE", "legacy")
    assert "TOWING" not in get_system_prompt()


# ---- bots (step 6) -------------------------------------------------------------------------------------

def test_bot_locks_its_spare_at_day_end_and_releases_next_morning():
    from tw2k.agents.seat_brain import SeatBrain
    u = _world()
    a, sid = _spare_at_dock(u)
    a.turns_today = a.turns_per_day - 1
    brain = SeatBrain()
    act = brain.decide(build_observation(u, "A").model_dump(mode="json"))
    assert act["kind"] == "tow_engage" and act["args"] == {"target": f"ship:{sid}"}
    assert apply_action(u, "A", Action(kind=ActionKind.TOW_ENGAGE, args=act["args"])).ok
    act = brain.decide(build_observation(u, "A").model_dump(mode="json"))
    assert act["kind"] == "query_limpets"  # sits still, nothing that would dock
    tick_day(u)
    assert sid in u.parked_ships
    act = brain.decide(build_observation(u, "A").model_dump(mode="json"))
    assert act["kind"] == "tow_release"


def test_bot_tow_policy_off_and_legacy_no_op(monkeypatch):
    from tw2k.agents.seat_brain import SeatBrain
    for name, value in (("BOT_TOW_POLICY", "off"), ("TOW_MODE", "legacy")):
        monkeypatch.setattr(K, name, value)
        u = _world()
        a, sid = _spare_at_dock(u)
        a.turns_today = a.turns_per_day - 1
        act = SeatBrain().decide(build_observation(u, "A").model_dump(mode="json"))
        assert act["kind"] != "tow_engage"
        monkeypatch.setattr(K, name, dict(TOW_DEFAULTS)[name])


# ---- legacy pin ---------------------------------------------------------------------------------------

# Recorded with tests/fed_legacy_digest.py on the commit before this slice (slice 50 + its follow-up): scripted
# match N3,N2,N1,H, seed 250925, 3 days, every switch at its default (= this slice with only TOW_MODE flipped).
# CAPTURE_MODE, CORPSHIP_MODE and the fullgame-fixes-v2 switches are also flipped: they did not exist
# on that parent, and leaving them tw2002 changes the match.
TOW_LEGACY_GOLDEN = "5032bedfb3722133d47b18eb"  # recorded on 5968646 + slice-47 QC brain fixes (79acd71; TOW_MODE absent)


# Later slices that add a tw2002 mode flip it here too (planetary-trading-v1: PLANET_TRADE_MODE).
FULLGAME_V2_SWITCHES = ("PLANET_DIVIDEND_MODE", "HUNT_MODE", "COMBAT_FRAMING_MODE", "SLOW_HULL_HINT_MODE",
                        "COMBAT_SCANNER_MODE", "GENESIS_HULL_MODE", "MINE_OVERFLOW_MODE")
TOW_PIN_FLIPS = ("TOW_MODE", "CAPTURE_MODE", "PLANET_TRADE_MODE", "CORPSHIP_MODE") + FULLGAME_V2_SWITCHES


def test_tow_legacy_is_unchanged():
    code = (
        "import sys; sys.path.insert(0, 'tests'); sys.path.insert(0, 'src');"
        "from pathlib import Path; from fed_legacy_digest import legacy_run_digest;"
        f"print(legacy_run_digest(Path('.'), 'N3,N2,N1,H', 3, 250925, flip={TOW_PIN_FLIPS!r}))"
    )
    env = dict(os.environ, PYTHONHASHSEED="0")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True,
                         timeout=900, check=True)
    assert out.stdout.strip().splitlines()[-1] == TOW_LEGACY_GOLDEN


def test_tt11a_tt13_landing_releases_so_planet_transport_never_carries_a_towee():
    u = _world()
    here, nxt, sid = _towing_ct(u)
    planet = Planet(id=777, sector_id=here, name="Home", class_id=next(iter(PlanetClass)), owner_id="A")
    u.planets[777] = planet
    u.sectors[here].planet_ids.append(777)
    res = _do(u, "A", ActionKind.LAND_PLANET, planet_id=777)
    assert res.ok and u.players["A"].planet_landed == 777
    assert _lock(u) is None and _rel_events(u, "land")
    assert u.parked_ships[sid].sector_id == here


def test_tt11g_towee_sold_or_destroyed_releases():
    u = _world()
    a = _sit(u, "A", 1)
    sid = _park(u, "A", 1, ShipClass.MERCHANT_FREIGHTER)
    assert _engage(u, "A", f"ship:{sid}").ok
    res = _do(u, "A", ActionKind.SELL_SHIP, ship_id=sid)
    assert res.ok and sid not in u.parked_ships
    assert a.ship.tow_lock is None and (_rel_events(u, "dock") or _rel_events(u, "towee_gone"))


def test_tt8_manned_towee_takes_no_entry_hazard():
    u = _world()
    here, nxt = _space(u)
    a = _sit(u, "A", here)
    a.ship.fighters, a.ship.shields = 5000, 5000
    b = _sit(u, "B", here, ShipClass.MERCHANT_CRUISER)
    b.ship.shields = 30
    assert _engage(u, "A", "player:B").ok
    _sit(u, "E", 1, ShipClass.MERCHANT_CRUISER)
    u.sectors[nxt].mines.append(MineDeployment(owner_id="E", kind=MineType.ARMID, count=20))
    u.sectors[nxt].mines.append(MineDeployment(owner_id="E", kind=MineType.LIMPET, count=5))
    u.sectors[nxt].nav_hazard = 50
    assert _do(u, "A", ActionKind.WARP, target=nxt).ok
    assert b.sector_id == nxt and b.alive and b.ship.shields == 30
    assert not any(lt.target_id == "B" for lt in u.limpets.values())


def test_tt1_dormant_lock_still_blocks_a_second_lock_on_the_same_ship():
    u = _world()
    here, _nxt = _space(u)
    _sit(u, "A", here)
    sid = _park(u, "A", here, ShipClass.MERCHANT_FREIGHTER)
    other = _park(u, "A", here, ShipClass.MERCHANT_CRUISER)
    assert _engage(u, "A", f"ship:{sid}").ok
    assert _do(u, "A", ActionKind.SHIP_TRANSPORT, ship_id=other).ok  # the ISS keeps a dormant lock
    assert f"ship:{sid}" not in _la(u, "A", "tow_engage").params["target"]["choices"]
    res = _engage(u, "A", f"ship:{sid}")
    assert not res.ok and "already locked" in res.error
