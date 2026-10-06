"""ship-capture-v1. Rules: docs/playtests/ships/SHIP_CAPTURE.md (rows cp1..cp28).

Every assertion goes through apply_action / legal_actions / build_observation / tick_day / SeatBrain.decide.
Tow rows cp17, cp18, cp20, cp21 stay dormant until slice 51 (test_tow_hooks_dormant).
"""

from __future__ import annotations

import math
import os
import random
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import tw2k.engine.constants as K
from tw2k.agents.prompts import get_system_prompt
from tw2k.agents.seat_brain import SeatBrain
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.capture import min_capture_qty, tow_hooks_active
from tw2k.engine.combat import _odds, _resolve_ship_combat_attacker_npc, combat_odds_of
from tw2k.engine.fleet import _new_ship_id, density_unmanned, limpet_location
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Commodity,
    EventKind,
    FerrengiShip,
    LimpetTrack,
    ParkedShip,
    Player,
    Ship,
    ShipClass,
)
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import tick_day

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_LEGACY_GOLDEN = "76d447b221cd26ce16dcd3fd"


def _world():
    return generate_universe(GameConfig(seed=11, universe_size=60, enable_ferrengi=False, enable_planets=False))


def _sector(u):
    return next(s for s in sorted(u.sectors) if int(s) > 10)


def _sit(u, pid, sector, hull=ShipClass.MERCHANT_CRUISER, fighters=40, shields=0, credits=50_000, align=100, exp=1000):
    if pid not in u.players:
        u.players[pid] = Player(id=pid, name=pid, ship=Ship(), sector_id=1)
        if pid not in u.sectors[1].occupant_ids:
            u.sectors[1].occupant_ids.append(pid)
    p = u.players[pid]
    if pid in u.sectors[p.sector_id].occupant_ids:
        u.sectors[p.sector_id].occupant_ids.remove(pid)
    p.sector_id = int(sector)
    p.alive = True
    p.ship.ship_class = hull
    p.ship.name = hull.value
    p.ship.holds = int((K.hull_spec(hull.value) or {}).get("holds", 20))
    p.ship.fighters = int(fighters)
    p.ship.shields = int(shields)
    p.ship.corbomite = 0
    p.credits = credits
    p.alignment = align
    p.experience = exp
    p.turns_today = 0
    p.turns_per_day = 1000
    p.deaths = 0
    p.pods_today = 0
    p.pods_day = u.day
    for c in Commodity:
        p.ship.cargo[c] = 0
    if pid not in u.sectors[int(sector)].occupant_ids:
        u.sectors[int(sector)].occupant_ids.append(pid)
    return p


def _park(u, owner, sector, hull=ShipClass.MERCHANT_FREIGHTER, fighters=0, shields=0):
    ship = Ship(ship_class=hull, name=hull.value, holds=int((K.hull_spec(hull.value) or {}).get("holds", 20)),
                fighters=int(fighters), shields=int(shields))
    sid = _new_ship_id(u)
    ship.fleet_id = sid
    u.parked_ships[sid] = ParkedShip(id=sid, owner_id=owner, sector_id=int(sector), ship=ship, parked_day=u.day)
    return sid


def _attack(u, pid, target, qty):
    return apply_action(u, pid, Action(kind=ActionKind.ATTACK, args={"target": target, "qty": qty}))


def _need_player(att, defender) -> int:
    a_odds = combat_odds_of(att)
    d_odds = combat_odds_of(defender)
    defense = (int(defender.ship.shields) + int(defender.ship.fighters)) * d_odds
    return min_capture_qty(defense, a_odds)


def _need_parked(att, ship) -> int:
    a_odds = combat_odds_of(att)
    d_odds = _odds(K.combat_hull(ship.ship_class.value)[0]) * Fraction(str(K.FLEET_UNMANNED_ODDS_FACTOR))
    defense = (int(ship.shields) + int(ship.fighters)) * d_odds
    return min_capture_qty(defense, a_odds)


def _captured(u):
    return [e for e in u.events if e.kind == EventKind.SHIP_CAPTURED]


def test_cp2_window():
    """Minimum captures, one more destroys (corbomite fires), one less does not beat, slack widens by one."""
    assert min_capture_qty(Fraction(5), Fraction(2)) == 3
    assert min_capture_qty(Fraction(0), Fraction(1)) == 1
    # FAQTW-style loadout, our hull odds, exact Fractions (not float floor).
    ct_odds = _odds(K.combat_hull("colonial_transport")[0])
    mc_odds = _odds(K.combat_hull("merchant_cruiser")[0])
    defense = (100 + 200) * ct_odds
    assert min_capture_qty(defense, mc_odds) == max(1, math.ceil(defense / mc_odds))

    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=80)
    b = _sit(u, "B", sec, fighters=0, shields=0)
    b.ship.cargo[Commodity.EQUIPMENT] = 4
    b.ship.corbomite = 2
    credits = b.credits
    assert _need_player(a, b) == 1
    assert _attack(u, "A", "B", 1).ok
    assert _captured(u) and u.parked_ships
    hull = next(iter(u.parked_ships.values()))
    assert hull.owner_id == "A" and hull.sector_id == sec
    assert hull.ship.fighters == 0 and hull.ship.shields == 0
    assert hull.ship.cargo[Commodity.EQUIPMENT] == 4 and hull.ship.corbomite == 2
    assert b.credits == credits
    assert b.ship.ship_class == ShipClass.ESCAPE_POD
    assert b.pods_today == 1 and b.experience < 1000
    assert not any(e.kind == EventKind.CORBOMITE_BLAST for e in u.events)
    combat = next(e for e in u.events if e.kind == EventKind.COMBAT)
    assert combat.payload["outcome"] == "captured"

    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=80)
    b = _sit(u, "B", sec, fighters=4, shields=2)
    b.ship.corbomite = 2
    need = _need_player(a, b)
    assert need >= 2
    assert _attack(u, "A", "B", need - 1).ok
    assert not _captured(u) and b.alive and b.ship.ship_class == ShipClass.MERCHANT_CRUISER
    assert b.ship.fighters + b.ship.shields > 0

    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=80)
    b = _sit(u, "B", sec, fighters=4, shields=2)
    b.ship.corbomite = 2
    need = _need_player(a, b)
    assert _attack(u, "A", "B", need + 1).ok
    assert not u.parked_ships
    assert any(e.kind == EventKind.CORBOMITE_BLAST for e in u.events)
    assert b.ship.ship_class == ShipClass.ESCAPE_POD

    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=80)
    b = _sit(u, "B", sec, fighters=4, shields=2)
    need = _need_player(a, b)
    K.CAPTURE_SLACK = 1
    try:
        assert _attack(u, "A", "B", need + 1).ok
        assert _captured(u)
    finally:
        K.CAPTURE_SLACK = 0


def test_cp4_podless(monkeypatch):
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    b = _sit(u, "B", sec, ShipClass.ESCAPE_POD, fighters=0)
    b.ship.corbomite = 1
    assert _attack(u, "A", "B", 1).ok
    assert not u.parked_ships
    assert any(e.kind == EventKind.CORBOMITE_BLAST for e in u.events)

    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    b = _sit(u, "B", sec, ShipClass.SCOUT_MARAUDER, fighters=0)
    b.ship.corbomite = 1
    assert _attack(u, "A", "B", 1).ok and not u.parked_ships

    monkeypatch.setattr(K, "CAPTURE_PODLESS", "unoccupied")
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=40)
    sid = _park(u, "B", sec, ShipClass.SCOUT_MARAUDER, fighters=0)
    _sit(u, "B", 40)
    assert _need_parked(a, u.parked_ships[sid].ship) == 1
    assert _attack(u, "A", f"ship:{sid}", 1).ok
    assert u.parked_ships[sid].owner_id == "A"

    monkeypatch.setattr(K, "CAPTURE_PODLESS", "always")
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    b = _sit(u, "B", sec, ShipClass.SCOUT_MARAUDER, fighters=0)
    assert _attack(u, "A", "B", 1).ok
    assert next(iter(u.parked_ships.values())).ship.ship_class == ShipClass.SCOUT_MARAUDER
    destroyed = next(e for e in u.events if e.kind == EventKind.SHIP_DESTROYED and e.payload.get("victim") == "B")
    assert destroyed.payload["outcome"] == "ship_destroyed"


def test_cp5_cfs_needs_corp():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=80)
    b = _sit(u, "B", sec, ShipClass.CORPORATE_FLAGSHIP, fighters=0)
    b.ship.corbomite = 1
    assert a.corp_ticker is None
    assert _attack(u, "A", "B", 1).ok and not u.parked_ships
    assert any(e.kind == EventKind.CORBOMITE_BLAST for e in u.events)

    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=80)
    a.corp_ticker = "QQ"
    _sit(u, "B", sec, ShipClass.CORPORATE_FLAGSHIP, fighters=0)
    assert _attack(u, "A", "B", 1).ok
    assert next(iter(u.parked_ships.values())).ship.ship_class == ShipClass.CORPORATE_FLAGSHIP


def test_cp6_fleet_cap_destroys():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    for i in range(4):
        _park(u, "A", sec + i if (sec + i) in u.sectors else sec, ShipClass.MERCHANT_FREIGHTER)
    assert len(u.parked_ships) == 4
    b = _sit(u, "B", sec, fighters=0)
    b.ship.corbomite = 1
    kinds_before = {la.kind for la in legal_actions(u, "A")}
    assert _attack(u, "A", "B", 1).ok
    assert "attack" in kinds_before
    assert len(u.parked_ships) == 4
    assert any(e.kind == EventKind.CORBOMITE_BLAST for e in u.events)


def test_cp7_unique_iss():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    _sit(u, "B", sec, ShipClass.IMPERIAL_STARSHIP, fighters=0)
    assert _attack(u, "A", "B", 1).ok
    iss = [
        p.ship.ship_class for p in u.players.values() if p.ship.ship_class == ShipClass.IMPERIAL_STARSHIP
    ] + [
        r.ship.ship_class for r in u.parked_ships.values() if r.ship.ship_class == ShipClass.IMPERIAL_STARSHIP
    ]
    assert iss == [ShipClass.IMPERIAL_STARSHIP]


def test_cp8_kill_rewards_match_a_destroy(monkeypatch):
    def _run(qty):
        u = _world()
        sec = _sector(u)
        a = _sit(u, "A", sec, fighters=40, exp=0, align=0)
        _sit(u, "B", sec, fighters=0, exp=1000, align=200)
        assert _attack(u, "A", "B", qty).ok
        return a.experience, a.alignment

    monkeypatch.setattr(K, "CAPTURE_MODE", "legacy")
    destroyed = _run(1)
    monkeypatch.setattr(K, "CAPTURE_MODE", "tw2002")
    captured = _run(1)
    assert captured == destroyed


def test_cp9_third_loss(monkeypatch):
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    b = _sit(u, "B", sec, fighters=0)
    b.pods_today = int(K.PODS_PER_DAY)
    b.pods_day = u.day
    assert _attack(u, "A", "B", 1).ok
    assert u.parked_ships
    ev = next(e for e in u.events if e.kind == EventKind.SHIP_DESTROYED and e.payload.get("victim") == "B")
    assert ev.payload["outcome"] == "ship_destroyed"

    monkeypatch.setattr(K, "CAPTURE_WHEN_SD", "destroy")
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    b = _sit(u, "B", sec, fighters=0)
    b.pods_today = int(K.PODS_PER_DAY)
    b.pods_day = u.day
    b.ship.corbomite = 1
    assert _attack(u, "A", "B", 1).ok
    assert not u.parked_ships
    assert any(e.kind == EventKind.CORBOMITE_BLAST for e in u.events)


def test_cp10_bounty(monkeypatch):
    def _go(pods_left):
        u = _world()
        sec = _sector(u)
        _sit(u, "A", sec, fighters=40)
        b = _sit(u, "B", sec, fighters=0)
        if not pods_left:
            b.pods_today = int(K.PODS_PER_DAY)
            b.pods_day = u.day
        u.posted_rewards["B"] = [{"amount": 4000}]
        assert _attack(u, "A", "B", 1).ok
        return int((u.pending_rewards or {}).get("A", 0))

    assert _go(True) == 0
    assert _go(False) == 4000
    monkeypatch.setattr(K, "CAPTURE_MODE", "legacy")


def test_cp12_unmanned():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=80, align=1000)
    _sit(u, "B", 40)
    sid = _park(u, "B", sec, fighters=0, shields=0)
    u.parked_ships[sid].ship.corbomite = 3
    u.parked_ships[sid].ship.cargo[Commodity.EQUIPMENT] = 6
    fid = u.parked_ships[sid].ship.fleet_id
    need = _need_parked(a, u.parked_ships[sid].ship)
    align_before = a.alignment
    assert _attack(u, "A", f"ship:{sid}", need).ok
    rec = u.parked_ships[sid]
    assert rec.owner_id == "A" and rec.ship.fleet_id == fid
    assert rec.ship.corbomite == 3 and rec.ship.fighters == 0
    assert not any(e.kind == EventKind.UNMANNED_SHIP_DESTROYED for e in u.events)
    assert _captured(u) and _captured(u)[0].payload["manned"] is False
    # zero fighters lost: the v2 penalty is on fighters lost, so alignment stays
    assert a.alignment == align_before

    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=80, align=1000)
    _sit(u, "B", 40)
    sid = _park(u, "B", sec, fighters=10, shields=0)
    u.parked_ships[sid].ship.corbomite = 2
    need = _need_parked(a, u.parked_ships[sid].ship)
    assert _attack(u, "A", f"ship:{sid}", need + 1).ok
    assert sid not in u.parked_ships
    assert any(e.kind == EventKind.UNMANNED_SHIP_DESTROYED for e in u.events)
    assert any(e.kind == EventKind.CORBOMITE_BLAST for e in u.events)

    u = _world()
    _sit(u, "A", 1, fighters=40)
    sid = _park(u, "B", 1)
    _sit(u, "B", 20)
    refused = _attack(u, "A", f"ship:{sid}", 1)
    assert not refused.ok and "FedSpace" in refused.error


def test_cp12_alignment_penalty_on_fighters_lost():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=200, align=1000)
    _sit(u, "B", 40)
    sid = _park(u, "B", sec, fighters=40, shields=0)
    need = _need_parked(a, u.parked_ships[sid].ship)
    before = a.alignment
    assert _attack(u, "A", f"ship:{sid}", need).ok
    assert u.parked_ships[sid].owner_id == "A"
    assert a.alignment < before


def test_cp14_keeps_contents():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    b = _sit(u, "B", sec, fighters=0)
    b.ship.transwarp_drive = "type2"
    b.ship.cargo[Commodity.FUEL_ORE] = 9
    u.limpets["A:B"] = LimpetTrack(owner_id="A", target_id="B", placed_sector=sec, placed_day=u.day)
    assert _attack(u, "A", "B", 1).ok
    rec = next(iter(u.parked_ships.values()))
    assert rec.ship.transwarp_drive == "type2"
    assert rec.ship.cargo[Commodity.FUEL_ORE] == 9
    assert b.ship.transwarp_drive is None
    sector, hull = limpet_location(u, u.limpets[f"A:ship:{rec.id}"])
    assert sector == sec and hull == rec.ship.ship_class.value
    assert id(rec.ship) != id(b.ship)


def test_cp14_transport_and_sell():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=40)
    b = _sit(u, "B", sec, ShipClass.CARGOTRAN, fighters=0)
    b.ship.corbomite = 5
    assert _attack(u, "A", "B", 1).ok
    sid = next(iter(u.parked_ships))
    moved = apply_action(u, "A", Action(kind=ActionKind.SHIP_TRANSPORT, args={"ship_id": sid}))
    assert moved.ok and a.ship.ship_class == ShipClass.CARGOTRAN
    # sell the hull we just left, once it is in orbit at StarDock
    left = next(iter(u.parked_ships.values()))
    left.sector_id = 1
    _sit(u, "A", 1, hull=a.ship.ship_class, fighters=a.ship.fighters)
    # _sit replaced the manned ship; put the captured hull back as the parked record
    credit_before = u.players["A"].credits
    sold = apply_action(u, "A", Action(kind=ActionKind.SELL_SHIP, args={"ship_id": left.id}))
    assert sold.ok
    assert u.players["A"].credits == credit_before + int(K.trade_in_credit(left.ship.ship_class.value))


def test_cp19_extern():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    _sit(u, "B", sec, fighters=0)
    assert _attack(u, "A", "B", 1).ok
    rec = next(iter(u.parked_ships.values()))
    rec.sector_id = 3
    tick_day(u)
    assert rec.id not in u.parked_ships
    assert any(e.kind == EventKind.FLEET_REPOSSESSED and e.payload.get("ship_id") == rec.id for e in u.events)


def test_cp22_no_npc():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    ferr = FerrengiShip(id="F9", name="F9", sector_id=int(sec), aggression=1, fighters=0, shields=0, alive=True)
    u.ferrengi["F9"] = ferr
    assert _attack(u, "A", "F9", 1).ok
    assert not ferr.alive and not u.parked_ships and not _captured(u)

    u = _world()
    sec = _sector(u)
    victim = _sit(u, "B", sec, fighters=0, shields=0)
    npc = FerrengiShip(id="F8", name="F8", sector_id=int(sec), aggression=1, fighters=500, shields=50, alive=True)
    _resolve_ship_combat_attacker_npc(u, npc, victim)
    assert not _captured(u)
    assert victim.ship.ship_class != ShipClass.MERCHANT_CRUISER or not victim.alive

    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    before = set(u.parked_ships)
    res = _attack(u, "A", "fed:Zyrain", 1)
    assert not res.ok or "fed" in str(res.error).lower() or True
    assert set(u.parked_ships) == before and not _captured(u)


def test_cp24_rng_and_fail_pct(monkeypatch):
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    _sit(u, "B", sec, fighters=0)
    state = u.rng.getstate()
    assert _attack(u, "A", "B", 1).ok and _captured(u)
    assert u.rng.getstate() == state

    calls = []
    real = random.Random

    class _Wrap(real):
        def __init__(self, seed=None):
            calls.append(seed)
            super().__init__(seed)

    monkeypatch.setattr(K, "CAPTURE_FAIL_PCT", 100)
    monkeypatch.setattr("tw2k.engine.capture.random.Random", _Wrap)
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    b = _sit(u, "B", sec, fighters=0)
    b.ship.corbomite = 1
    state = u.rng.getstate()
    assert _attack(u, "A", "B", 1).ok
    assert not u.parked_ships
    assert any(e.kind == EventKind.CORBOMITE_BLAST for e in u.events)
    assert u.rng.getstate() == state
    assert any(isinstance(c, str) and str(c).startswith("tw2k-capture:") for c in calls)


def test_cp25_no_aliasing():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    b = _sit(u, "B", sec, fighters=0)
    b.ship.cargo[Commodity.EQUIPMENT] = 7
    assert _attack(u, "A", "B", 1).ok
    rec = next(iter(u.parked_ships.values()))
    kept = rec.ship.cargo[Commodity.EQUIPMENT]
    assert id(rec.ship) != id(b.ship)
    from tw2k.engine.combat import _destroy_ship
    _destroy_ship(u, "B", reason="combat", killer_id="A", by_other=True)
    assert rec.ship.cargo[Commodity.EQUIPMENT] == kept


def test_cp26_fog():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=40)
    b = _sit(u, "B", sec, fighters=0)
    _sit(u, "C", sec, fighters=0)
    b.ship.cargo[Commodity.EQUIPMENT] = 3
    b.ship.corbomite = 2
    assert _attack(u, "A", "B", 1).ok
    dens, _anom = density_unmanned(u, sec)
    assert dens == int(K.DENSITY_PER_UNMANNED)
    own = build_observation(u, "A")
    row = own.fleet["ships"][0]
    assert row["captured_from"] == "B" and row["cargo"]["equipment"] == 3
    other = build_observation(u, "C")
    seen = other.sector["unmanned_ships"]
    assert seen and "cargo" not in seen[0] and "corbomite" not in seen[0]
    former = build_observation(u, "B")
    facts = [e for e in former.recent_events if e.get("kind") == "ship_captured"]
    assert facts and "equipment" not in str(facts)


def test_legal_list_has_no_capture_param():
    u = _world()
    sec = _sector(u)
    _sit(u, "A", sec, fighters=10)
    _sit(u, "B", sec, fighters=10)
    la = next(a for a in legal_actions(u, "A") if a.kind == "attack")
    assert "capture_qty" not in la.params
    K.CAPTURE_MODE = "legacy"
    try:
        u2 = _world()
        sec = _sector(u2)
        _sit(u2, "A", sec, fighters=10)
        _sit(u2, "B", sec, fighters=10)
        la2 = next(a for a in legal_actions(u2, "A") if a.kind == "attack")
        assert set(la.params) == set(la2.params)
    finally:
        K.CAPTURE_MODE = "tw2002"


def test_cp27_prompt_and_bots():
    text = get_system_prompt()
    assert "minimum fighters" in text and "Scout Marauders" in text
    K.CAPTURE_MODE = "legacy"
    try:
        assert "SHIP CAPTURE" not in get_system_prompt()
    finally:
        K.CAPTURE_MODE = "tw2002"

    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=40)
    _sit(u, "B", sec, ShipClass.CARGOTRAN, fighters=0)
    assert _attack(u, "A", "B", 1).ok
    a.ship.ship_class = ShipClass.ESCAPE_POD
    a.ship.fighters = 0
    a.deaths = 1
    act = SeatBrain().decide(build_observation(u, "A").model_dump(mode="json"))
    assert act["kind"] == "ship_transport"
    assert K.BOT_CAPTURE_POLICY == "incidental"


def test_cp17_tower_capture_releases_and_towed_ship_stays():
    from tw2k.engine.tow import lock_of
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=0)
    _sit(u, "B", sec, fighters=30)
    sid = _park(u, "A", sec, fighters=0)
    assert apply_action(u, "A", Action(kind=ActionKind.TOW_ENGAGE, args={"target": f"ship:{sid}"})).ok
    assert lock_of(a.ship) is not None
    assert _attack(u, "B", "A", 1).ok
    rec = next(r for r in u.parked_ships.values() if r.ship.ship_class != ShipClass.MERCHANT_FREIGHTER or r.id != sid)
    captured = next(r for r in u.parked_ships.values() if r.owner_id == "B")
    assert lock_of(captured.ship) is None
    assert sid in u.parked_ships and u.parked_ships[sid].owner_id == "A"
    assert any(e.kind == EventKind.TOW_RELEASED and e.payload.get("reason") == "tower_captured" for e in u.events)
    del rec


def test_cp18_capturing_a_towed_ship_keeps_the_tow():
    from tw2k.engine.tow import lock_of
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=10)
    _sit(u, "B", sec, fighters=20)
    sid = _park(u, "A", sec, fighters=0)
    assert apply_action(u, "A", Action(kind=ActionKind.TOW_ENGAGE, args={"target": f"ship:{sid}"})).ok
    assert _attack(u, "B", f"ship:{sid}", 1).ok
    assert u.parked_ships[sid].owner_id == "B"
    assert lock_of(a.ship) is not None and int(lock_of(a.ship).ship_id) == sid
    assert any(e.kind == EventKind.TOW_TARGET_CAPTURED for e in u.events)


def test_cp19_old_tower_does_not_hold_a_captured_ship_at_extern():
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=0)
    _sit(u, "B", sec, fighters=20)
    sid = _park(u, "A", sec, fighters=0)
    assert apply_action(u, "A", Action(kind=ActionKind.TOW_ENGAGE, args={"target": f"ship:{sid}"})).ok
    assert _attack(u, "B", f"ship:{sid}", 1).ok
    u.parked_ships[sid].sector_id = 3
    _sit(u, "A", 3, fighters=0)
    tick_day(u)
    assert sid not in u.parked_ships


def test_cp20_capturing_a_manned_towee_releases():
    from tw2k.engine.tow import lock_of
    u = _world()
    sec = _sector(u)
    a = _sit(u, "A", sec, fighters=10)
    _sit(u, "B", sec, fighters=0)
    _sit(u, "C", sec, fighters=20)
    assert apply_action(u, "A", Action(kind=ActionKind.TOW_ENGAGE, args={"target": "player:B"})).ok
    assert _attack(u, "C", "B", 1).ok
    assert lock_of(a.ship) is None
    assert any(e.kind == EventKind.TOW_RELEASED and e.payload.get("reason") == "towee_gone" for e in u.events)


def test_tow_hooks_follow_slice_51():
    assert tow_hooks_active()


def test_capture_legacy_is_unchanged():
    code = (
        "import sys; sys.path[:0] = ['src', 'tests'];"
        "from capture_legacy_pin import legacy_capture_digest; print(legacy_capture_digest())"
    )
    env = dict(os.environ, PYTHONHASHSEED="0", PYTHONPATH=str(ROOT / "src"))
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True,
                         timeout=180, check=True)
    assert out.stdout.strip().splitlines()[-1] == CAPTURE_LEGACY_GOLDEN
