"""ship-transwarp-v1. Rules: docs/playtests/ships/SHIP_TRANSWARP.md (rows tw1..tw22).

Every assertion is the original rule through the real engine path (apply_action / legal_actions /
build_observation / the bots' decide). Planted bugs P1..P16 in the spec map to the tests named in the
rules doc; qc_bridge/transwarp_artifacts records which test caught each plant.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests._pin_env import pin_env
from tw2k.agents.heuristic import HeuristicAgent
from tw2k.agents.prompts import format_observation, get_system_prompt
from tw2k.agents.seat_brain import SeatBrain
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Alliance,
    Commodity,
    EventKind,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Player,
    Ship,
    ShipClass,
)
from tw2k.engine.observation import build_observation
from tw2k.engine.scanners import density_reading
from tw2k.engine.ship_transwarp import hop_count

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    """Pin this slice's switches to their defaults so a later slice retune shows up here first."""
    for name, value in (("SHIP_TW_MODE", "tw2002"), ("SHIP_TW_BLIND", "density0"),
                        ("SHIP_TW_FED_LOCK", "commissioned"), ("SHIP_TW_TURN_COST", "tpw"),
                        ("SHIP_TW_FRIENDLY", "own_corp_ally"), ("SHIP_TW_CLOAK_POLICY", "allow_decloak"),
                        ("SHIP_TW_FUSE_REFUNDS", False)):
        monkeypatch.setattr(K, name, value)


def _world():
    return generate_universe(GameConfig(seed=11, universe_size=60, enable_ferrengi=False, enable_planets=False))


def _sit(u, pid, sector, hull=ShipClass.IMPERIAL_STARSHIP, credits=200_000, align=0, ore=60):
    if pid not in u.players:
        u.players[pid] = Player(id=pid, name=pid, ship=Ship(), sector_id=1)
        u.sectors[1].occupant_ids.append(pid)
    p = u.players[pid]
    if pid in u.sectors[p.sector_id].occupant_ids:
        u.sectors[p.sector_id].occupant_ids.remove(pid)
    p.sector_id = int(sector)
    p.ship.ship_class = hull
    p.ship.holds = 80
    p.credits = credits
    p.alignment = align
    for c in Commodity:
        p.ship.cargo[c] = 0
    p.ship.cargo[Commodity.FUEL_ORE] = int(ore)
    p.turns_today = 0
    p.turns_per_day = 1000
    p.known_sectors.add(int(sector))
    u.sectors[int(sector)].occupant_ids.append(pid)
    return p


def _empty(u, sid, keep=()):
    """Density 0: no port, planet, fighters, mines, beacon, NavHaz or other ships."""
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


def _away(u, dist, avoid=(1,)):
    """A pair of sectors `dist` hops apart (outside `avoid`)."""
    for here in sorted(u.sectors):
        if here in avoid:
            continue
        for sid in sorted(u.sectors):
            if sid in avoid or sid == here:
                continue
            if hop_count(u, here, sid) == dist:
                return here, sid
    raise AssertionError(f"no sector at distance {dist}")


def _lock(u, sid, owner="A", count=1):
    u.sectors[sid].fighters = FighterDeployment(owner_id=owner, count=count, mode=FighterMode.DEFENSIVE)


def _ore(u, pid="A"):
    return int(u.players[pid].ship.cargo.get(Commodity.FUEL_ORE, 0))


def _buy(u, pid="A"):
    return apply_action(u, pid, Action(kind=ActionKind.BUY_EQUIP, args={"item": "transwarp_drive", "qty": 1}))


def _jump(u, pid, dest):
    return apply_action(u, pid, Action(kind=ActionKind.SHIP_TRANSWARP, args={"sector_id": dest}))


def _la(u, pid, kind):
    return next((a for a in legal_actions(u, pid) if a.kind == kind), None)


def _tw_choices(u, pid="A"):
    la = _la(u, pid, "ship_transwarp")
    if la is None or not la.legal:
        return []
    return list(la.params["sector_id"]["choices"])


def _equip_choices(u, pid="A"):
    la = _la(u, pid, "buy_equip")
    return list(la.params["item"]["choices"]) if la is not None and la.params else []


def _fitted(u, here, dest, ore=60, **kw):
    p = _sit(u, "A", here, ore=ore, **kw)
    p.ship.transwarp_drive = "type1"
    p.known_sectors.add(dest)
    return p


# ---- tw1-tw5 buy ---------------------------------------------------------------

def test_tw1_buy_only_on_tw_hulls_at_stardock():
    """P1: a non-TW hull (CargoTran, Merchant Cruiser, Scout, Interdictor, pod) cannot buy or see the drive."""
    for hull in (ShipClass.IMPERIAL_STARSHIP, ShipClass.CORPORATE_FLAGSHIP, ShipClass.HAVOC_GUNSTAR):
        u = _world()
        _sit(u, "A", 1, hull)
        assert "transwarp_drive" in _equip_choices(u)
        assert _buy(u).ok
        assert u.players["A"].ship.transwarp_drive == "type1"
    for hull in (ShipClass.CARGOTRAN, ShipClass.MERCHANT_CRUISER, ShipClass.SCOUT_MARAUDER,
                 ShipClass.INTERDICTOR_CRUISER, ShipClass.ESCAPE_POD):
        u = _world()
        _sit(u, "A", 1, hull)
        assert "transwarp_drive" not in _equip_choices(u), hull
        assert not _buy(u).ok, hull
        assert u.players["A"].ship.transwarp_drive is None
        assert u.players["A"].credits == 200_000


def test_tw2_buy_at_stardock_only_and_never_under_legacy(monkeypatch):
    """P2: Alpha Centauri / Rylos / any other sector refuses; SHIP_TW_MODE legacy refuses at StarDock."""
    u = _world()
    _sit(u, "A", 12)
    assert not _buy(u).ok and u.players["A"].credits == 200_000
    specials = [sid for sid, s in u.sectors.items() if s.port is not None and getattr(s.port, "special", None)]
    for sid in specials:
        _sit(u, "A", sid)
        assert "transwarp_drive" not in _equip_choices(u)
        assert not _buy(u).ok
        assert u.players["A"].ship.transwarp_drive is None
    monkeypatch.setattr(K, "SHIP_TW_MODE", "legacy")
    u = _world()
    _sit(u, "A", 1)
    assert "transwarp_drive" not in _equip_choices(u)
    assert not _buy(u).ok
    assert u.players["A"].ship.transwarp_drive is None and u.players["A"].credits == 200_000


def test_tw3_type1_price_is_12500():
    """P3: Type 1 costs exactly 12,500 (not the 20,000 Type II price, not free)."""
    assert K.SHIP_TW_TYPE1_COST == 12_500
    u = _world()
    _sit(u, "A", 1, credits=12_499)
    assert "transwarp_drive" not in _equip_choices(u)
    assert not _buy(u).ok and u.players["A"].credits == 12_499
    u.players["A"].credits = 50_000
    la = _la(u, "A", "buy_equip")
    assert la.params["item"]["unit_price_by"]["transwarp_drive"] == 12_500
    assert la.params["qty"]["max_by"]["transwarp_drive"] == 1
    assert _buy(u).ok
    assert u.players["A"].credits == 50_000 - 12_500


def test_tw4_one_drive_per_ship_and_no_type2(monkeypatch):
    monkeypatch.setattr(K, "TOW_MODE", "legacy")  # Type 2 / upgrade arrive with slice 51 (SHIP_TOW.md tt16)
    u = _world()
    _sit(u, "A", 1)
    assert _buy(u).ok
    assert "transwarp_drive" not in _equip_choices(u)
    again = _buy(u)
    assert not again.ok and "already fitted" in again.error
    assert u.players["A"].credits == 200_000 - 12_500
    for item in ("transwarp_type2", "transwarp_upgrade"):
        assert not apply_action(u, "A", Action(kind=ActionKind.BUY_EQUIP, args={"item": item, "qty": 1})).ok
        assert item not in _equip_choices(u)


def test_tw5_drive_lost_on_pod_and_trade_in():
    """P11: the escape pod has no drive and a traded-in hull takes its drive with it."""
    u = _world()
    here, dest = _away(u, 2)
    _fitted(u, here, dest, ore=20)
    assert int(density_reading(u, dest)["density"]) > 0
    _jump(u, "A", dest)  # blind into density > 0: fuse
    assert u.players["A"].ship.ship_class.value == "escape_pod"
    assert u.players["A"].ship.transwarp_drive is None
    assert "transwarp" not in (build_observation(u, "A").ship.get("transwarp") or {}) or \
        build_observation(u, "A").ship["transwarp"]["fitted"] is None

    u = _world()
    p = _sit(u, "A", 1, align=3000, credits=900_000)
    assert _buy(u).ok
    bought = apply_action(u, "A", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "havoc_gunstar"}))
    assert bought.ok
    assert p.ship.ship_class.value == "havoc_gunstar"
    assert u.players["A"].ship.transwarp_drive is None
    assert "transwarp_drive" in _equip_choices(u)  # the new hull may buy its own


# ---- tw6-tw12 locked jump ------------------------------------------------------

def test_tw9_locked_jump_burns_three_ore_per_hop():
    """P4: 4 hops costs 12 ore; 11 ore refuses and consumes nothing."""
    u = _world()
    here, dest = _away(u, 4)
    _fitted(u, here, dest, ore=13)
    _lock(u, dest)
    result = _jump(u, "A", dest)
    assert result.ok, result.error
    assert u.players["A"].sector_id == dest
    assert _ore(u) == 1
    assert u.players["A"].arrived_by_transwarp
    ev = [e for e in u.events if e.kind == EventKind.SHIP_TRANSWARP and e.actor_id == "A"][-1]
    assert ev.payload["hops"] == 4 and ev.payload["ore"] == 12 and ev.payload["locked"] and not ev.payload["blind"]

    u = _world()
    here, dest = _away(u, 4)
    _fitted(u, here, dest, ore=11)
    _lock(u, dest)
    turns = u.players["A"].turns_today
    refused = _jump(u, "A", dest)
    assert not refused.ok and "ore" in refused.error
    assert _ore(u) == 11 and u.players["A"].sector_id == here and u.players["A"].turns_today == turns


def test_tw9_hop_metric_is_shortest_path_along_warps_out():
    """P5: hop count is the BFS warp-path length (not warps-out degree, not counting reverse one-ways)."""
    u = _world()
    here, dest = _away(u, 3)
    # A one-way link dest -> here must not shorten here -> dest.
    if here not in u.sectors[dest].warps:
        u.sectors[dest].warps.append(here)
    assert hop_count(u, here, dest) == 3
    assert hop_count(u, here, here) == 0
    _fitted(u, here, dest, ore=9)
    _lock(u, dest)
    assert _jump(u, "A", dest).ok
    assert _ore(u) == 0
    # A new forward one-way here2 -> dest makes it one hop.
    u = _world()
    here, dest = _away(u, 3)
    u.sectors[here].warps.append(dest)
    assert hop_count(u, here, dest) == 1
    # Degree of the origin is not the metric.
    u = _world()
    here, dest = _away(u, 2)
    assert hop_count(u, here, dest) == 2 != len(u.sectors[here].warps) or len(u.sectors[here].warps) == 2


def test_tw10_max_hops_is_ore_over_three():
    u = _world()
    p = _sit(u, "A", 1, hull=ShipClass.HAVOC_GUNSTAR, ore=50)
    p.ship.transwarp_drive = "type1"
    tw = build_observation(u, "A").ship["transwarp"]
    assert tw == {"fitted": "type1", "ore_per_hop": 3, "max_hops_now": 16, "fed_lock": False}


def test_tw11_turn_cost_is_one_ship_tpw_and_hops_switch(monkeypatch):
    """P10: default spends one ship TPW (not zero, not TPW * hops); "hops" spends TPW * hops."""
    tpw = int(K.hull_spec("imperial_starship")["turns_per_warp"])
    u = _world()
    here, dest = _away(u, 4)
    _fitted(u, here, dest, ore=40)
    _lock(u, dest)
    res = _jump(u, "A", dest)
    assert res.ok and res.turns_spent == tpw > 0
    assert u.players["A"].turns_today == tpw
    monkeypatch.setattr(K, "SHIP_TW_TURN_COST", "hops")
    u = _world()
    here, dest = _away(u, 4)
    _fitted(u, here, dest, ore=40)
    _lock(u, dest)
    assert _jump(u, "A", dest).turns_spent == tpw * 4


def test_tw6_no_drive_refused_and_challenge_refused():
    u = _world()
    here, dest = _away(u, 2)
    p = _sit(u, "A", here, ore=40)
    p.known_sectors.add(dest)
    _lock(u, dest)
    assert not _jump(u, "A", dest).ok and u.players["A"].sector_id == here and _ore(u) == 40
    p.ship.transwarp_drive = "type1"
    _sit(u, "E", 1, hull=ShipClass.MERCHANT_CRUISER, align=-400)
    _lock(u, here, owner="E", count=50)
    p.fighter_challenge = {"sector_id": here, "from_sector": dest, "mode": "defensive"}
    assert not _la(u, "A", "ship_transwarp").legal
    assert not _jump(u, "A", dest).ok and _ore(u) == 40 and u.players["A"].sector_id == here


def test_tw6_cloak_drops_on_arrival():
    u = _world()
    here, dest = _away(u, 2)
    p = _fitted(u, here, dest, ore=40)
    p.ship.cloaked = True
    _lock(u, dest)
    assert _jump(u, "A", dest).ok
    assert u.players["A"].ship.cloaked is False


def test_tw7_corp_and_ally_fighters_lock_enemy_does_not(monkeypatch):
    """P8: corp-mate and ally fighters lock under own_corp_ally; an enemy fighter never locks; own_only switch."""
    u = _world()
    here, dest = _away(u, 2)
    a = _fitted(u, here, dest, ore=40)
    b = _sit(u, "B", here, hull=ShipClass.MERCHANT_CRUISER, ore=0)
    a.corp_ticker = b.corp_ticker = "ZZ"
    _lock(u, dest, owner="B")
    assert dest in _tw_choices(u)
    assert _jump(u, "A", dest).ok and u.players["A"].sector_id == dest and u.players["A"].alive

    u = _world()
    here, dest = _away(u, 2)
    a = _fitted(u, here, dest, ore=40)
    _sit(u, "B", here, hull=ShipClass.MERCHANT_CRUISER, ore=0)
    u.alliances["X1"] = Alliance(id="X1", member_ids=["A", "B"], proposed_by="A", formed_day=1, active=True)
    a.alliances.append("X1")
    u.players["B"].alliances.append("X1")
    _lock(u, dest, owner="B")
    assert dest in _tw_choices(u)
    assert _jump(u, "A", dest).ok and u.players["A"].alive

    u = _world()
    here, dest = _away(u, 2)
    _fitted(u, here, dest, ore=40)
    _sit(u, "E", here, hull=ShipClass.MERCHANT_CRUISER, ore=0)
    _lock(u, dest, owner="E")
    assert dest not in _tw_choices(u)
    deaths = u.players["A"].deaths
    _jump(u, "A", dest)  # enemy fighters: blind into density > 0
    assert u.players["A"].deaths == deaths + 1

    monkeypatch.setattr(K, "SHIP_TW_FRIENDLY", "own_only")
    u = _world()
    here, dest = _away(u, 2)
    a = _fitted(u, here, dest, ore=40)
    b = _sit(u, "B", here, hull=ShipClass.MERCHANT_CRUISER, ore=0)
    a.corp_ticker = b.corp_ticker = "ZZ"
    _lock(u, dest, owner="B")
    assert dest not in _tw_choices(u)
    _jump(u, "A", dest)
    assert u.players["A"].deaths == 1


def test_tw8_commission_fedspace_lock(monkeypatch):
    """P7: alignment 1000 jumps into FedSpace without a fighter; 999 is a blind jump; fighter_only switch."""
    u = _world()
    here, _d = _away(u, 3, avoid=tuple(K.FEDSPACE_SECTORS))
    p = _fitted(u, here, 1, align=1000, ore=80)
    assert u.sectors[1].fighters is None or u.sectors[1].fighters.owner_id != "A"
    assert set(int(s) for s in K.FEDSPACE_SECTORS if hop_count(u, here, int(s)) and
               3 * hop_count(u, here, int(s)) <= 80) <= set(_tw_choices(u))
    assert build_observation(u, "A").ship["transwarp"]["fed_lock"] is True
    result = _jump(u, "A", 1)
    assert result.ok and u.players["A"].sector_id == 1 and u.players["A"].alive
    assert p.deaths == 0

    u = _world()
    here, _d = _away(u, 3, avoid=tuple(K.FEDSPACE_SECTORS))
    _fitted(u, here, 1, align=999, ore=80)
    assert 1 not in _tw_choices(u)
    assert build_observation(u, "A").ship["transwarp"]["fed_lock"] is False
    assert int(density_reading(u, 1)["density"]) > 0
    _jump(u, "A", 1)
    assert u.players["A"].deaths == 1

    monkeypatch.setattr(K, "SHIP_TW_FED_LOCK", "fighter_only")
    u = _world()
    here, _d = _away(u, 3, avoid=tuple(K.FEDSPACE_SECTORS))
    _fitted(u, here, 1, align=1500, ore=80)
    assert 1 not in _tw_choices(u)
    _jump(u, "A", 1)
    assert u.players["A"].deaths == 1


def test_tw12_retreat_blocked_until_a_normal_warp():
    """P9: no retreat right after a TransWarp arrival; a normal warp clears the flag."""
    u = _world()
    here, dest = _away(u, 2)
    _fitted(u, here, dest, ore=40)
    _lock(u, dest)
    _sit(u, "B", 1, hull=ShipClass.MERCHANT_CRUISER, align=-400)
    assert _jump(u, "A", dest).ok
    assert u.players["A"].arrived_by_transwarp
    _lock(u, dest, owner="B", count=5)
    u.players["A"].fighter_challenge = {"sector_id": dest, "from_sector": here, "mode": "defensive"}
    la = _la(u, "A", "retreat")
    assert la is None or not la.legal
    retreat = apply_action(u, "A", Action(kind=ActionKind.RETREAT, args={}))
    assert not retreat.ok and "TransWarp" in (retreat.error or "")
    u.players["A"].fighter_challenge = None
    u.sectors[dest].fighters = None
    neighbour = next(int(w) for w in u.sectors[dest].warps if int(w) != here)
    _empty(u, neighbour)
    assert apply_action(u, "A", Action(kind=ActionKind.WARP, args={"target": neighbour})).ok
    assert not u.players["A"].arrived_by_transwarp
    landed = u.players["A"].sector_id
    _lock(u, landed, owner="B", count=5)
    u.players["A"].fighter_challenge = {"sector_id": landed, "from_sector": dest, "mode": "defensive"}
    assert apply_action(u, "A", Action(kind=ActionKind.RETREAT, args={})).ok


def test_tw12_locked_arrival_still_runs_sector_hazards():
    """A lock does not skip the mines: hostile armids in the lock sector still hit."""
    u = _world()
    here, dest = _away(u, 2)
    p = _fitted(u, here, dest, ore=40)
    p.ship.fighters = 50
    p.ship.shields = 0
    _sit(u, "E", 1, hull=ShipClass.MERCHANT_CRUISER)
    _lock(u, dest)
    u.sectors[dest].mines.append(MineDeployment(owner_id="E", kind=MineType.ARMID, count=5))
    before = (p.ship.fighters, p.ship.shields, p.deaths)
    assert _jump(u, "A", dest).ok
    after = (u.players["A"].ship.fighters, u.players["A"].ship.shields, u.players["A"].deaths)
    assert after != before
    assert any(e.kind == EventKind.MINE_DETONATED for e in u.events)


def test_tw12_planet_interdictor_holds_a_transwarp_out():
    """cabal planets.html: backing out or TransWarping out of an Interdictor sector is held (500 ore)."""
    from tw2k.engine.models import Planet, PlanetClass
    u = _world()
    here, dest = _away(u, 2)
    _fitted(u, here, dest, ore=40)
    _sit(u, "E", 1, hull=ShipClass.MERCHANT_CRUISER)
    _lock(u, dest)
    planet = Planet(id=999, sector_id=here, name="Hold", class_id=next(iter(PlanetClass)), owner_id="E",
                    citadel_level=K.INTERDICTOR_MIN_LEVEL)
    planet.stockpile[Commodity.FUEL_ORE] = K.INTERDICTOR_FUEL
    u.planets[999] = planet
    u.sectors[here].planet_ids.append(999)
    held = _jump(u, "A", dest)
    assert not held.ok and "interdict" in held.error
    assert u.players["A"].sector_id == here and _ore(u) == 40


# ---- tw13-tw16 blind -----------------------------------------------------------

def test_tw14_blind_density0_succeeds_and_dense_fuses():
    """P6: blind into density 0 lands; blind into density > 0 pods the ship (DEATH_MODE path)."""
    u = _world()
    here, dest = _away(u, 2)
    _fitted(u, here, dest, ore=40)
    _empty(u, dest)
    assert int(density_reading(u, dest)["density"]) == 0
    assert dest not in _tw_choices(u)
    res = _jump(u, "A", dest)
    assert res.ok and u.players["A"].sector_id == dest and u.players["A"].alive and u.players["A"].deaths == 0
    assert _ore(u) == 34
    ev = [e for e in u.events if e.kind == EventKind.SHIP_TRANSWARP][-1]
    assert ev.payload["blind"] and not ev.payload["locked"]

    u = _world()
    here, dest = _away(u, 2)
    p = _fitted(u, here, dest, ore=40)
    assert int(density_reading(u, dest)["density"]) > 0
    fused = _jump(u, "A", dest)
    assert fused.ok  # the jump was committed
    assert p.deaths == 1 and u.players["A"].ship.ship_class.value == "escape_pod"
    assert any(e.kind == EventKind.SHIP_TRANSWARP_FUSE and e.actor_id == "A" for e in u.events)
    assert not any(e.kind == EventKind.SHIP_TRANSWARP and e.actor_id == "A" for e in u.events)


def test_tw14_limpet_alone_fuses():
    u = _world()
    here, dest = _away(u, 2)
    p = _fitted(u, here, dest, ore=40)
    _empty(u, dest)
    _sit(u, "E", 1, hull=ShipClass.MERCHANT_CRUISER)
    u.sectors[dest].mines.append(MineDeployment(owner_id="E", kind=MineType.LIMPET, count=1))
    assert int(density_reading(u, dest)["density"]) > 0
    _jump(u, "A", dest)
    assert p.deaths == 1


def test_tw14_refuse_switch_hides_and_refuses_blind(monkeypatch):
    monkeypatch.setattr(K, "SHIP_TW_BLIND", "refuse")
    u = _world()
    here, dest = _away(u, 2)
    _fitted(u, here, dest, ore=40)
    _empty(u, dest)
    res = _jump(u, "A", dest)
    assert not res.ok and u.players["A"].sector_id == here and _ore(u) == 40


def test_tw15_fuse_spends_ore_and_turns(monkeypatch):
    u = _world()
    here, dest = _away(u, 2)
    _fitted(u, here, dest, ore=20)
    res = _jump(u, "A", dest)
    assert res.turns_spent == int(K.hull_spec("imperial_starship")["turns_per_warp"])
    assert _ore(u) == 0  # the pod has no ore; the 6 went with the jump and the rest with the hull
    monkeypatch.setattr(K, "SHIP_TW_FUSE_REFUNDS", True)
    u = _world()
    here, dest = _away(u, 2)
    _fitted(u, here, dest, ore=20)
    assert _jump(u, "A", dest).turns_spent == 0


# ---- tw16 / tw20 legal list == handler ----------------------------------------

def test_tw16_legal_list_matches_handler_and_never_lists_blind():
    """P12 + P13: every listed target lands; no blind target is listed; off when no drive / ore / turns."""
    u = _world()
    here, _d = _away(u, 2)
    p = _sit(u, "A", here, ore=60)
    p.ship.transwarp_drive = "type1"
    from tw2k.engine.ship_transwarp import has_lock
    for sid in sorted(u.sectors):
        p.known_sectors.add(sid)
        if sid % 3 == 0 and sid != here:
            _lock(u, sid)
    choices = _tw_choices(u)
    assert choices
    for sid in u.sectors:
        if sid in choices:
            assert has_lock(u, "A", sid)
        elif sid != here and not has_lock(u, "A", sid):
            assert sid not in choices
    spec = _la(u, "A", "ship_transwarp").params["sector_id"]
    for sid in choices:
        v = _world()
        _sit(v, "A", here, ore=60).ship.transwarp_drive = "type1"
        v.players["A"].known_sectors.update(u.sectors)
        _lock(v, sid)
        assert spec["hops_by"][str(sid)] == hop_count(v, here, sid)
        assert spec["ore_by"][str(sid)] == 3 * hop_count(v, here, sid)
        res = _jump(v, "A", sid)
        assert res.ok and v.players["A"].sector_id == sid and v.players["A"].alive, (sid, res.error)


def test_tw16_legal_list_off_when_drive_ore_or_turns_short():
    u = _world()
    here, dest = _away(u, 4)
    p = _sit(u, "A", here, ore=60)
    p.known_sectors.add(dest)
    _lock(u, dest)
    assert not _tw_choices(u) and not _jump(u, "A", dest).ok  # no drive
    p.ship.transwarp_drive = "type1"
    p.ship.cargo[Commodity.FUEL_ORE] = 11
    assert dest not in _tw_choices(u) and not _jump(u, "A", dest).ok  # 4 hops needs 12
    p.ship.cargo[Commodity.FUEL_ORE] = 60
    p.turns_today = p.turns_per_day - int(K.hull_spec("imperial_starship")["turns_per_warp"]) + 1
    la = _la(u, "A", "ship_transwarp")
    assert not la.legal and not _jump(u, "A", dest).ok  # short of one TPW
    p.turns_today = 0
    assert dest in _tw_choices(u) and _jump(u, "A", dest).ok


# ---- tw17 rng ----------------------------------------------------------------------

def test_tw17_hop_search_and_locked_jump_do_not_draw_rng():
    """P14: the hop BFS, the legal list and a quiet locked jump never touch universe.rng."""
    u = _world()
    here, dest = _away(u, 3)
    _fitted(u, here, dest, ore=40)
    _lock(u, dest)
    _empty(u, dest)
    _lock(u, dest)
    state = u.rng.getstate()
    assert hop_count(u, here, dest) == 3
    legal_actions(u, "A")
    build_observation(u, "A")
    assert _jump(u, "A", dest).ok
    assert u.rng.getstate() == state


# ---- tw19 planet TransWarp -------------------------------------------------------

def test_tw19_planet_transwarp_is_a_different_handler():
    """P15: planet_transwarp keeps its own handler (the planet TransWarp tests also run in the suite)."""
    from tw2k.engine import runner
    from tw2k.engine.ship_transwarp import handle_ship_transwarp
    assert ActionKind.PLANET_TRANSWARP.value == "planet_transwarp" != ActionKind.SHIP_TRANSWARP.value
    assert runner._DISPATCH[ActionKind.PLANET_TRANSWARP] is not handle_ship_transwarp
    assert runner._DISPATCH[ActionKind.SHIP_TRANSWARP] is handle_ship_transwarp


# ---- tw20 observation / fog ------------------------------------------------------

def test_tw20_other_seats_never_see_the_drive_ore_or_fuse():
    """P16: B shares a sector with A and sees neither A's drive, ore holds, buy, nor a fuse event."""
    u = _world()
    a = _sit(u, "A", 1, ore=77)
    _sit(u, "B", 1, hull=ShipClass.MERCHANT_CRUISER, ore=0)
    a.ship.cargo[Commodity.FUEL_ORE] = 0
    assert _buy(u).ok
    a.ship.cargo[Commodity.FUEL_ORE] = 77
    own = build_observation(u, "A")
    assert own.ship["transwarp"]["fitted"] == "type1"
    other = build_observation(u, "B")
    dumped = other.model_dump(mode="json")
    assert dumped["ship"]["transwarp"]["fitted"] is None
    for occ in (dumped.get("sector") or {}).get("occupants") or []:
        text = str(occ)
        assert "transwarp" not in text and "fuel_ore" not in text and "77" not in text
    assert "transwarp_drive" not in format_observation(other)
    assert not any("transwarp" in str(e).lower() for e in dumped.get("recent_events") or [])

    u = _world()
    here, dest = _away(u, 2)
    _fitted(u, here, dest, ore=40)
    _sit(u, "W", here, hull=ShipClass.MERCHANT_CRUISER, ore=0)
    _jump(u, "A", dest)  # fuse in front of W
    seen = [e["kind"] for e in build_observation(u, "W").model_dump(mode="json")["recent_events"]]
    assert "ship_transwarp_fuse" not in seen
    mine = [e["kind"] for e in build_observation(u, "A").model_dump(mode="json")["recent_events"]]
    assert "ship_transwarp_fuse" in mine


def test_tw20_arrival_is_seen_by_destination_occupants():
    u = _world()
    here, dest = _away(u, 2)
    _fitted(u, here, dest, ore=40)
    _lock(u, dest)
    _sit(u, "W", dest, hull=ShipClass.MERCHANT_CRUISER, ore=0)
    assert _jump(u, "A", dest).ok
    seen = build_observation(u, "W").model_dump(mode="json")["recent_events"]
    tw = [e for e in seen if e["kind"] == "ship_transwarp"]
    assert tw and tw[-1]["facts"]["to"] == dest
    assert "fuel_ore" not in str(tw[-1])


# ---- tw21 prompts / legacy -------------------------------------------------------

def test_tw21_prompt_names_the_drive(monkeypatch):
    monkeypatch.delenv("TW2K_HINT_LEVEL", raising=False)
    text = get_system_prompt()
    for needle in ("transwarp_drive", "3 fuel ore", "Never blind-jump", "planet_transwarp", "FedSpace", "12,500"):
        assert needle in text
    monkeypatch.setattr(K, "SHIP_TW_MODE", "legacy")
    assert "Never blind-jump" not in get_system_prompt()


def test_legacy_has_no_drive_verb_keys_or_events(monkeypatch):
    monkeypatch.setattr(K, "SHIP_TW_MODE", "legacy")
    u = _world()
    here, dest = _away(u, 2)
    p = _fitted(u, here, dest, ore=40)
    _lock(u, dest)
    assert _la(u, "A", "ship_transwarp") is None
    res = _jump(u, "A", dest)
    assert not res.ok and res.error == "unsupported action"
    assert u.players["A"].sector_id == here and _ore(u) == 40
    assert "transwarp" not in build_observation(u, "A").ship
    assert not any(e.kind in (EventKind.SHIP_TRANSWARP, EventKind.SHIP_TRANSWARP_FUSE) for e in u.events)
    del p
    fresh = _world().model_dump_json()  # resume fields are saved once set, omitted while empty (legacy dumps)
    assert "transwarp_drive" not in fresh and "arrived_by_transwarp" not in fresh


# Recorded with tests/fed_legacy_digest.py (flip=None: every tw2002 *_MODE to legacy) on 9dbe56b, the commit
# before this slice: scripted match N3,N2,N1,H, seed 250925, 3 days (3 tick_day state digests + every obs JSON,
# prompt text, action + result and event). Floats rounded as in that helper (Linux/Windows libm).
SHIP_TW_LEGACY_GOLDEN = "00135a9202e44a0e085ce978"
# Same run with only SHIP_TW_MODE flipped (every other switch at its default) on 9dbe56b: defaults elsewhere
# plus SHIP_TW_MODE legacy must be the pre-slice engine byte for byte. Later slices that retune tw2002 play
# change this one, so it is recorded here and checked by QC (see the Delivered note), not run in the suite.
SHIP_TW_ONLY_LEGACY_ON_9DBE56B = "85fb398575b2a69e92e0bc17"


def test_ship_tw_legacy_is_unchanged():
    code = (
        "import sys; from pathlib import Path; sys.path.insert(0, 'src'); sys.path.insert(0, 'tests');"
        "from fed_legacy_digest import legacy_run_digest; print(legacy_run_digest(Path('.'), 'N3,N2,N1,H', 3))"
    )
    env = pin_env()
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True,
                         timeout=900, check=True)
    assert out.stdout.strip().splitlines()[-1] == SHIP_TW_LEGACY_GOLDEN


# ---- tw6 bots ----------------------------------------------------------------------

def _seat_obs(u, pid):
    return build_observation(u, pid).model_dump(mode="json")


def test_bots_swap_a_long_walk_for_a_listed_lock_only():
    """seat_brain: a plot to a listed lock becomes a jump when it saves SHIP_TW_MIN_TURNS_SAVED+ turns; else it walks."""
    from tw2k.agents.stall import Intent
    u = _world()
    here, dest = _away(u, 4)
    _fitted(u, here, dest, ore=24)
    _lock(u, dest)
    brain = SeatBrain()
    brain.decide(_seat_obs(u, "A"))
    from tw2k.agents.seat_brain import View
    v = View(_seat_obs(u, "A"))
    plot = {"kind": "plot_course", "args": {"target": dest, "execute": True}}
    swapped = brain._transwarp_instead(v, dict(plot), Intent("travel", dest))
    assert swapped["kind"] == "ship_transwarp" and swapped["args"] == {"sector_id": dest}
    assert apply_action(u, "A", Action(kind=ActionKind.SHIP_TRANSWARP, args=swapped["args"])).ok

    u = _world()
    here, dest = _away(u, 4)
    _fitted(u, here, dest, ore=12)  # just the jump's ore: no return reserve needed (follow-up to slice 50)
    _lock(u, dest)
    v = View(_seat_obs(u, "A"))
    assert brain._transwarp_instead(v, dict(plot, args={"target": dest}), Intent("travel", dest))["kind"] == "ship_transwarp"
    import tw2k.agents.seat_brain as sb
    saved = sb.tw_turns_saved(4, 4)  # ISS: 4 warps of 4 turns walked vs one 4-turn jump
    assert saved == 12
    old_min = sb.SHIP_TW_MIN_TURNS_SAVED
    try:
        sb.SHIP_TW_MIN_TURNS_SAVED = saved + 1  # not worth it: walk
        assert brain._transwarp_instead(v, dict(plot, args={"target": dest}), Intent("travel", dest))["kind"] == "plot_course"
    finally:
        sb.SHIP_TW_MIN_TURNS_SAVED = old_min

    u = _world()
    here, dest = _away(u, 4)
    _fitted(u, here, dest, ore=60)
    _empty(u, dest)  # density 0, but no lock: never blind
    v = View(_seat_obs(u, "A"))
    assert brain._transwarp_instead(v, dict(plot, args={"target": dest}), Intent("travel", dest))["kind"] == "plot_course"

    u = _world()
    here, dest = _away(u, 2)
    _fitted(u, here, dest, ore=60)
    _lock(u, dest)
    v = View(_seat_obs(u, "A"))  # 2 hops: walking is close enough
    assert brain._transwarp_instead(v, {"kind": "plot_course", "args": {"target": dest}}, Intent())["kind"] == "plot_course"


def test_bots_buy_the_drive_only_on_a_tw_hull_with_spare_cash(monkeypatch):
    from tw2k.agents.seat_brain import View
    brain = SeatBrain()
    u = _world()
    _sit(u, "A", 1, credits=400_000)
    brain.decide(_seat_obs(u, "A"))
    act = brain._buy_transwarp_drive(View(_seat_obs(u, "A")))
    assert act is not None and act["args"] == {"item": "transwarp_drive", "qty": 1}
    u.players["A"].credits = 100_000
    assert brain._buy_transwarp_drive(View(_seat_obs(u, "A"))) is None
    u = _world()
    _sit(u, "A", 1, hull=ShipClass.CARGOTRAN, credits=900_000)
    assert brain._buy_transwarp_drive(View(_seat_obs(u, "A"))) is None
    monkeypatch.setattr(K, "SHIP_TW_MODE", "legacy")
    u = _world()
    _sit(u, "A", 1, credits=900_000)
    assert brain._buy_transwarp_drive(View(_seat_obs(u, "A"))) is None


def test_heuristic_jumps_only_to_a_stardock_lock():
    import asyncio
    u = _world()
    here, _d = _away(u, 4, avoid=tuple(K.FEDSPACE_SECTORS))
    _fitted(u, here, 1, align=1200, ore=200, credits=80_000)
    agent = HeuristicAgent("A", "A")
    jump = agent._ship_transwarp(build_observation(u, "A"))
    assert jump is not None and jump.kind == ActionKind.SHIP_TRANSWARP and jump.args == {"sector_id": 1}
    u.players["A"].alignment = 999  # no commission lock: sector 1 would be blind
    assert agent._ship_transwarp(build_observation(u, "A")) is None
    act = asyncio.run(agent.act(build_observation(u, "A")))
    assert act.kind != ActionKind.SHIP_TRANSWARP
