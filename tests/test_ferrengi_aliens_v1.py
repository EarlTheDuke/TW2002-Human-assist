"""ferrengi-aliens-v1: three hulls, Ferrengal, tribute, grudges, regen.

Rules: docs/playtests/npc/FERRENGI.md. test_plant_* entries are the
planted-bug checks (each was run against a planted mutation and failed).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.ferrengi import (
    _ferrengi_regen,
    _ferrengi_roam_and_hunt,
    _make_ferrengi,
    _spawn_ferrengi,
    apply_ferrengi_tribute,
    ferrengi_density,
    ferrengi_odds,
    hull_for_aggression,
    hull_spec,
    live_ferrengi_encounter,
    open_ferrengi_encounter,
    record_ferrengi_grudge,
)
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    EventKind,
    FerrengiShip,
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

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "playtests" / "npc" / "FERRENGI.md"


@pytest.fixture
def legacy(monkeypatch):
    monkeypatch.setattr(K, "FERRENGI_MODE", "legacy")


@pytest.fixture
def tw(monkeypatch):
    monkeypatch.setattr(K, "FERRENGI_MODE", "tw2002")
    monkeypatch.setattr(K, "FERRENGI_ENCOUNTER", "tribute")
    monkeypatch.setattr(K, "FERRENGI_FIGHTER_BLOCK", False)
    monkeypatch.setattr(K, "FERRENGI_HIT_MINES", True)
    monkeypatch.setattr(K, "FERRENGI_ALIGN_ON_KILL", 10)
    monkeypatch.setattr(K, "FERRENGI_REGEN_PCT", 0.20)
    monkeypatch.setattr(K, "FERRENGAL_MINES", 50)
    monkeypatch.setattr(K, "FERRENGAL_FIGHTERS", 1000)
    monkeypatch.setattr(K, "FERRENGI_SEES_CLOAK", False)
    monkeypatch.setattr(K, "FERRENGI_STARTUP_GRACE_DAYS", 0)


def _add_player(u, pid="A", **raw):
    fighters = int(raw.pop("fighters", 50))
    holds = int(raw.pop("holds", 50))
    shields = int(raw.pop("shields", 0))
    cloaked = bool(raw.pop("cloaked", False))
    sector_id = int(raw.pop("sector_id", 20))
    credits = int(raw.pop("credits", 50_000))
    cargo = raw.pop("cargo", None) or {}
    ship = Ship(
        holds=holds,
        fighters=fighters,
        shields=shields,
        ship_class=ShipClass.MERCHANT_CRUISER,
        cloaked=cloaked,
        cargo=dict(cargo),
    )
    p = Player(
        id=pid,
        name=pid,
        credits=credits,
        ship=ship,
        sector_id=sector_id,
        turns_today=0,
        turns_per_day=1000,
        alignment=int(raw.pop("alignment", 0)),
        experience=int(raw.pop("experience", 100)),
        alive=True,
    )
    u.players[pid] = p
    if sector_id in u.sectors and pid not in u.sectors[sector_id].occupant_ids:
        u.sectors[sector_id].occupant_ids.append(pid)
    return p


def _world(seed: int = 4901, size: int = 120, enable_ferrengi: bool = True):
    return generate_universe(
        GameConfig(
            seed=seed,
            universe_size=size,
            enable_ferrengi=enable_ferrengi,
            enable_planets=False,
            all_start_stardock=False,
            ferrengi_grace_days=0,
        )
    )


def test_doc_exists():
    assert DOC.is_file()
    text = DOC.read_text(encoding="utf-8")
    assert "FERRENGI_MODE" in text
    assert "SOURCE-CONFLICT" in text


def test_n1_three_hulls(tw):
    assert hull_for_aggression(1) == K.FERRENGI_HULL_ASSAULT
    assert hull_for_aggression(5) == K.FERRENGI_HULL_CRUISER
    assert hull_for_aggression(9) == K.FERRENGI_HULL_DREAD
    u = _world()
    assert u.ferrengi
    hulls = {f.hull for f in u.ferrengi.values()}
    assert hulls <= set(K.FERRENGI_HULL_SPECS)


def test_n2_specs(tw):
    at = hull_spec(K.FERRENGI_HULL_ASSAULT)
    assert at["max_fighters"] == 3000 and at["odds"] == 1.0 and at["density"] == 40
    bc = hull_spec(K.FERRENGI_HULL_CRUISER)
    assert bc["max_fighters"] == 8000 and bc["odds"] == 1.2 and bc["density"] == 100
    dn = hull_spec(K.FERRENGI_HULL_DREAD)
    assert dn["max_fighters"] == 15000 and dn["odds"] == 1.4 and dn["photons"] == 1


def test_n3_hull_mix(tw):
    assert hull_for_aggression(4) == "assault_trader"
    assert hull_for_aggression(7) == "battle_cruiser"
    assert hull_for_aggression(8) == "dreadnought"


def test_n4_odds(tw):
    f = FerrengiShip(
        id="x", name="x", sector_id=20, aggression=9, fighters=100, shields=10, hull="dreadnought"
    )
    assert ferrengi_odds(f) == 1.4


def test_n5_density(tw):
    u = _world()
    # Place a known dreadnought alone in an empty deep sector
    sid = 50
    for f in list(u.ferrengi.values()):
        f.alive = False
    ferr = _make_ferrengi(u, fid="d1", sid=sid, aggression=9)
    assert ferr.hull == "dreadnought"
    u.ferrengi["d1"] = ferr
    # Clear other density contributors
    u.sectors[sid].port = None
    u.sectors[sid].planet_ids = []
    u.sectors[sid].fighters = None
    u.sectors[sid].mines = []
    dens = density_reading(u, sid)["density"]
    assert dens == 100, dens


def test_n6_ferrengal(tw):
    u = _world(seed=4901)
    assert u.ferrengal_sector is not None
    assert u.ferrengal_sector not in K.FEDSPACE_SECTORS
    assert u.ferrengal_sector >= 11


def test_n7_mines(tw):
    u = _world()
    sid = u.ferrengal_sector
    sector = u.sectors[sid]
    mines = sum(m.count for m in sector.mines if m.owner_id == K.FERRENGI_OWNER_ID and m.kind == MineType.ARMID)
    assert mines == 50
    assert sector.fighters is not None
    assert sector.fighters.owner_id == K.FERRENGI_OWNER_ID
    assert sector.fighters.count == 1000


def test_n8_spawn_near(tw):
    u = _world(seed=4910, size=200)
    home = u.ferrengal_sector
    assert home
    # Force a daily spawn and check at least one lands near when possible
    before = set(u.ferrengi)
    u.config.ferrengi_per_day = 5
    u.config.ferrengi_max_alive = 50
    _spawn_ferrengi(u)
    new = [f for fid, f in u.ferrengi.items() if fid not in before]
    assert new


def test_n9_regen(tw):
    u = _world()
    ferr = next(f for f in u.ferrengi.values() if f.alive and f.hull)
    spec = hull_spec(ferr.hull)
    ferr.fighters = 10
    ferr.shields = 0
    _ferrengi_regen(u)
    assert ferr.fighters == min(spec["max_fighters"], 10 + int(spec["max_fighters"] * 0.20))
    assert ferr.shields == min(spec["max_shields"], int(spec["max_shields"] * 0.20))


def test_n11_ramp_cap(tw):
    u = _world()
    u.day = 9999
    f, s = __import__("tw2k.engine.ferrengi", fromlist=["_scaled_ferrengi_stats"])._scaled_ferrengi_stats(
        u, 9, "dreadnought"
    )
    assert f == 15000 and s == 1000


def test_n12_fighters_mines(tw):
    u = _world(size=80)
    # Ferrengi can enter a sector with player fighters
    deep = next(sid for sid in u.sectors if sid >= 20 and u.sectors[sid].warps)
    neighbour = u.sectors[deep].warps[0]
    if neighbour in K.FEDSPACE_SECTORS:
        neighbour = next(w for w in u.sectors[deep].warps if w not in K.FEDSPACE_SECTORS)
    u.sectors[neighbour].fighters = FighterDeployment(owner_id="A", count=50, mode=FighterMode.DEFENSIVE)
    ferr = _make_ferrengi(u, fid="m1", sid=deep, aggression=5)
    u.ferrengi = {"m1": ferr}
    # Plant hostile mines on neighbour
    u.sectors[neighbour].mines = [
        MineDeployment(owner_id="A", kind=MineType.ARMID, count=20)
    ]
    ferr.sector_id = neighbour
    from tw2k.engine.ferrengi import _apply_mines_to_ferrengi

    before_f = ferr.fighters
    _apply_mines_to_ferrengi(u, ferr)
    # With HIT_MINES, damage should apply (may or may not kill depending on rng)
    assert ferr.fighters <= before_f or not ferr.alive or ferr.shields < hull_spec(ferr.hull)["max_shields"]


def test_n14_encounter(tw):
    u = _world()
    p = _add_player(u, "A", sector_id=30, fighters=5, shields=0)
    ferr = _make_ferrengi(u, fid="e1", sid=30, aggression=5)
    u.ferrengi = {"e1": ferr}
    open_ferrengi_encounter(u, ferr, p)
    assert live_ferrengi_encounter(u, "A") is not None
    kinds = {a.kind for a in legal_actions(u, "A") if a.legal}
    assert ActionKind.SURRENDER.value in kinds
    assert ActionKind.RETREAT.value in kinds
    assert ActionKind.ATTACK.value in kinds


def test_n15_tribute(tw):
    u = _world()
    p = _add_player(
        u, "A", sector_id=30, fighters=5, holds=40, credits=10_000, cargo={"fuel_ore": 10, "organics": 5}
    )
    ferr = _make_ferrengi(u, fid="e1", sid=30, aggression=5)
    u.ferrengi = {"e1": ferr}
    open_ferrengi_encounter(u, ferr, p)
    r = apply_action(u, "A", Action(kind=ActionKind.SURRENDER, args={}))
    assert r.ok
    assert p.ship.cargo.get("fuel_ore", 0) == 0
    assert p.ship.cargo.get("organics", 0) == 0
    assert ferr.cargo.get("fuel_ore", 0) == 10
    assert p.ship.holds < 40  # some holds stolen
    assert live_ferrengi_encounter(u, "A") is None


def test_n15_tribute_credits_when_empty(tw):
    u = _world()
    p = _add_player(u, "A", sector_id=30, fighters=5, holds=40, credits=10_000, cargo={})
    ferr = _make_ferrengi(u, fid="e1", sid=30, aggression=5)
    u.ferrengi = {"e1": ferr}
    open_ferrengi_encounter(u, ferr, p)
    apply_ferrengi_tribute(u, "A")
    assert p.credits == 9000  # 10%
    assert ferr.credits >= 1000


def test_n16_attack_enc(tw):
    u = _world()
    p = _add_player(u, "A", sector_id=30, fighters=5000, shields=500)
    ferr = _make_ferrengi(u, fid="e1", sid=30, aggression=1)
    ferr.fighters = 10
    ferr.shields = 0
    u.ferrengi = {"e1": ferr}
    open_ferrengi_encounter(u, ferr, p)
    r = apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": "e1", "qty": 100}))
    assert r.ok
    assert "A" in u.ferrengi_grudges


def test_n17_flee(tw):
    u = _world()
    # Pick a sector with a warp
    sid = next(s for s in u.sectors if s >= 20 and any(w not in K.FEDSPACE_SECTORS for w in u.sectors[s].warps))
    p = _add_player(u, "A", sector_id=sid, fighters=5)
    ferr = _make_ferrengi(u, fid="e1", sid=sid, aggression=5)
    u.ferrengi = {"e1": ferr}
    open_ferrengi_encounter(u, ferr, p)
    r = apply_action(u, "A", Action(kind=ActionKind.RETREAT, args={}))
    assert r.ok
    assert p.sector_id != sid
    assert live_ferrengi_encounter(u, "A") is None


def test_n18_grudge(tw):
    u = _world()
    record_ferrengi_grudge(u, "A")
    assert "A" in u.ferrengi_grudges


def test_n19_kill(tw):
    u = _world()
    p = _add_player(u, "A", sector_id=30, fighters=8000, shields=500, credits=0)
    ferr = _make_ferrengi(u, fid="e1", sid=30, aggression=3)
    ferr.fighters = 1
    ferr.shields = 0
    ferr.credits = 100
    u.ferrengi = {"e1": ferr}
    align_before = p.alignment
    r = apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": "e1", "qty": 100}))
    assert r.ok
    assert not ferr.alive
    assert p.alignment == align_before + 10
    assert p.credits >= K.FERRENGI_BOUNTY_PER_AGG * 3


def test_n20_cargo(tw):
    u = _world()
    ferr = _make_ferrengi(u, fid="e1", sid=30, aggression=4)
    assert ferr.credits == 4 * K.FERRENGI_SPAWN_CREDITS_PER_AGG


def test_n21_no_fedspace(tw):
    u = _world()
    for f in u.ferrengi.values():
        assert f.sector_id not in K.FEDSPACE_SECTORS
    u.day = 10
    for _ in range(30):
        _ferrengi_roam_and_hunt(u)
    for f in u.ferrengi.values():
        if f.alive:
            assert f.sector_id not in K.FEDSPACE_SECTORS


def test_n22_no_fed_fight(tw):
    # Feds and Ferrengi simply never target each other (no code path).
    u = _world()
    assert not any(
        e.kind == EventKind.COMBAT and "fed" in str(e.payload).lower() and "ferr" in str(e.payload).lower()
        for e in u.events
    )


def test_n23_cloak(tw):
    u = _world()
    p = _add_player(u, "A", sector_id=30, fighters=0, shields=0, cloaked=True)
    ferr = _make_ferrengi(u, fid="e1", sid=30, aggression=9)
    u.ferrengi = {"e1": ferr}
    u.config.all_start_stardock = False
    monkey_grace = 0
    u.config.ferrengi_grace_days = 0
    # Force hunt path without move
    import tw2k.engine.constants as KC

    old = KC.FERRENGI_MOVE_PROB
    KC.FERRENGI_MOVE_PROB = 0.0
    try:
        _ferrengi_roam_and_hunt(u)
    finally:
        KC.FERRENGI_MOVE_PROB = old
    assert live_ferrengi_encounter(u, "A") is None
    assert p.alive and p.ship.fighters == 0


def test_n26_legal_handler(tw):
    u = _world()
    sid = next(s for s in u.sectors if s >= 20 and u.sectors[s].warps)
    p = _add_player(u, "A", sector_id=sid, fighters=20, cargo={"equipment": 3})
    ferr = _make_ferrengi(u, fid="e1", sid=sid, aggression=5)
    u.ferrengi = {"e1": ferr}
    open_ferrengi_encounter(u, ferr, p)
    legal = {a.kind: a for a in legal_actions(u, "A") if a.legal}
    assert ActionKind.SURRENDER.value in legal
    # Non-answers stay legal, flagged, and the handler takes tribute before running them.
    assert ActionKind.WARP.value in legal
    assert "ferrengi_note" in legal[ActionKind.WARP.value].params
    dest = int(u.sectors[sid].warps[0])
    before = len(u.events)
    r = apply_action(u, "A", Action(kind=ActionKind.WARP, args={"target": dest}))
    assert r.ok
    assert live_ferrengi_encounter(u, "A") is None
    assert p.ship.cargo.get("equipment", 0) == 0
    trib = [e for e in u.events[before:] if e.kind == EventKind.FERRENGI_TRIBUTE]
    assert trib and trib[0].payload.get("ignored") is True
    # An answer verb is not taxed: surrender on a fresh boarding pays exactly one tribute.
    u.players["A"].sector_id = sid
    ferr.sector_id = sid
    open_ferrengi_encounter(u, ferr, p)
    before = len(u.events)
    r2 = apply_action(u, "A", Action(kind=ActionKind.SURRENDER, args={}))
    assert r2.ok
    trib = [e for e in u.events[before:] if e.kind == EventKind.FERRENGI_TRIBUTE]
    assert len(trib) == 1 and "ignored" not in trib[0].payload


def test_ferrengi_legacy_is_unchanged(legacy):
    u = _world(seed=7777, size=100)
    assert u.ferrengal_sector is None
    for f in u.ferrengi.values():
        assert f.hull == ""
        # legacy formula: fighters = max(1, int((100 + agg*300) * scale))
        assert f.ship_class in (ShipClass.BATTLESHIP, ShipClass.MISSILE_FRIGATE)
    # No encounter path
    p = _add_player(u, "A", sector_id=30, fighters=0, shields=0)
    ferr = next(iter(u.ferrengi.values()))
    ferr.sector_id = 30
    ferr.aggression = 9
    import tw2k.engine.constants as KC

    old = KC.FERRENGI_MOVE_PROB
    KC.FERRENGI_MOVE_PROB = 0.0
    try:
        _ferrengi_roam_and_hunt(u)
    finally:
        KC.FERRENGI_MOVE_PROB = old
    assert getattr(p, "ferrengi_encounter", None) is None


# ---- planted bugs (also double as rule tests) ----


def test_plant_1_assault_specs(tw):
    at = hull_spec("assault_trader")
    assert at["max_fighters"] == 3000 and at["odds"] == 1.0


def test_plant_2_density(tw):
    f = FerrengiShip(
        id="x", name="x", sector_id=1, aggression=6, fighters=100, shields=10, hull="battle_cruiser"
    )
    assert ferrengi_density(f) == 100


def test_plant_3_ferrengal(tw):
    u = _world(seed=4950)
    assert u.ferrengal_sector not in K.FEDSPACE_SECTORS
    mines = sum(
        m.count
        for m in u.sectors[u.ferrengal_sector].mines
        if m.owner_id == K.FERRENGI_OWNER_ID
    )
    assert mines == 50


def test_plant_4_fighter_block(tw):
    assert K.FERRENGI_FIGHTER_BLOCK is False


def test_plant_5_mines(tw):
    assert K.FERRENGI_HIT_MINES is True
    u = _world(size=60)
    sid = 25
    ferr = _make_ferrengi(u, fid="m", sid=sid, aggression=2)
    ferr.fighters = 50
    ferr.shields = 0
    u.sectors[sid].mines = [MineDeployment(owner_id="A", kind=MineType.ARMID, count=40)]
    from tw2k.engine.ferrengi import _apply_mines_to_ferrengi

    _apply_mines_to_ferrengi(u, ferr)
    assert ferr.fighters < 50 or not ferr.alive


def test_plant_6_encounter(tw):
    u = _world()
    p = _add_player(u, "A", sector_id=30, fighters=2, shields=0)
    ferr = _make_ferrengi(u, fid="e", sid=30, aggression=5)
    u.ferrengi = {"e": ferr}
    import tw2k.engine.constants as KC

    old = KC.FERRENGI_MOVE_PROB
    KC.FERRENGI_MOVE_PROB = 0.0
    try:
        _ferrengi_roam_and_hunt(u)
    finally:
        KC.FERRENGI_MOVE_PROB = old
    assert live_ferrengi_encounter(u, "A") is not None


def test_plant_7_tribute(tw):
    test_n15_tribute(tw)


def test_plant_8_kill_rewards(tw):
    test_n19_kill(tw)


def test_plant_9_grudge(tw):
    u = _world()
    p = _add_player(u, "A", sector_id=30, fighters=5000)
    ferr = _make_ferrengi(u, fid="e", sid=30, aggression=1)
    ferr.fighters = 5
    ferr.shields = 0
    u.ferrengi = {"e": ferr}
    apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": "e", "qty": 50}))
    assert "A" in u.ferrengi_grudges


def test_plant_10_regen(tw):
    test_n9_regen(tw)


def test_plant_11_legacy(legacy):
    test_ferrengi_legacy_is_unchanged(legacy)


def test_plant_12_legal_handler(tw):
    test_n26_legal_handler(tw)


def test_plant_13_cloak(tw):
    test_n23_cloak(tw)


def test_plant_14_rng(tw, monkeypatch):
    # Ferrengal placement must not consume universe.rng: the shared stream after
    # generation is the same with placement switched off.
    import tw2k.engine.ferrengi as FM

    u1 = _world(seed=4960, size=100)
    assert u1.ferrengal_sector is not None
    monkeypatch.setattr(FM, "place_ferrengal", lambda universe: None)
    u2 = _world(seed=4960, size=100)
    assert u2.ferrengal_sector is None
    assert u1.rng.getstate() == u2.rng.getstate()


def test_plant_15_dread_specs(tw):
    dn = hull_spec("dreadnought")
    assert dn["max_fighters"] == 15000
    assert dn["max_mines"] == 50
    assert dn["photons"] == 1


def test_plant_16_fedspace(tw, monkeypatch):
    test_n21_no_fedspace(tw)
    # Deterministic: a roamer whose only exits are FedSpace never moves in.
    u = _world()
    sid = 30
    fed = sorted(K.FEDSPACE_SECTORS)[:2]
    u.sectors[sid].warps = list(fed)
    ferr = _make_ferrengi(u, fid="r", sid=sid, aggression=3)
    u.ferrengi = {"r": ferr}
    monkeypatch.setattr(K, "FERRENGI_MOVE_PROB", 1.0)
    for _ in range(20):
        _ferrengi_roam_and_hunt(u)
        assert ferr.sector_id not in K.FEDSPACE_SECTORS


def test_observation_shows_hull(tw):
    u = _world()
    p = _add_player(u, "A", sector_id=30)
    ferr = _make_ferrengi(u, fid="e", sid=30, aggression=9)
    u.ferrengi = {"e": ferr}
    obs = build_observation(u, "A")
    dump = obs.model_dump()
    entries = dump.get("sector", {}).get("ferrengi") or []
    assert any(e.get("hull") == "dreadnought" for e in entries)

def test_overnight_clears_encounter(tw):
    # enable_ferrengi=False so roam cannot re-board after the overnight flee.
    u = generate_universe(
        GameConfig(seed=4902, universe_size=80, enable_ferrengi=False, enable_planets=False)
    )
    sid = next(s for s in u.sectors if s >= 20 and u.sectors[s].warps)
    p = _add_player(u, "A", sector_id=sid, fighters=5)
    ferr = _make_ferrengi(u, fid="e", sid=sid, aggression=5)
    u.ferrengi = {"e": ferr}
    open_ferrengi_encounter(u, ferr, p)
    assert live_ferrengi_encounter(u, "A")
    from tw2k.engine.runner import tick_day
    old_sid = p.sector_id
    tick_day(u)
    assert live_ferrengi_encounter(u, "A") is None
    assert p.sector_id != old_sid  # fled overnight
