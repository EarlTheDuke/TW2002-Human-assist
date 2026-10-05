"""ship-hardware-v1: mines, photons, cloaks, disruptors (docs/playtests/ships/SHIP_HARDWARE.md)."""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.hardware import armid_detonation_hits
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Player,
    Ship,
    ShipClass,
)
from tw2k.engine.scanners import density_reading

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "playtests" / "ships" / "SHIP_HARDWARE.md"


@pytest.fixture
def legacy(monkeypatch):
    monkeypatch.setattr(K, "HARDWARE_MODE", "legacy")


@pytest.fixture
def tw(monkeypatch):
    monkeypatch.setattr(K, "HARDWARE_MODE", "tw2002")


def test_rules_doc_lists_rows_and_marks() -> None:
    text = DOC.read_text(encoding="utf-8")
    for row in [f"h{n}" for n in range(1, 27)]:
        assert f"| {row} |" in text, f"row {row} missing"
    for word in ("CONFIRMED", "SOURCE-CONFLICT", "UNVERIFIED", "Deliberate differences",
                 "HARDWARE_MODE", "ARMID_DAMAGE_TW2002", "ship-hardware-v2", "Delivered"):
        assert word.lower() in text.lower(), word


def test_switch_defaults() -> None:
    assert K.HARDWARE_MODE == "tw2002" and K.hardware_tw2002()
    assert K.ARMID_DAMAGE_TW2002 == 20
    assert K.ARMID_DAMAGE == 100
    assert K.CLOAK_COST == 25_000 and K.CLOAK_MAX == 5 and K.CLOAK_FAIL_RATE == 0.03
    assert K.DISRUPTOR_COST == 40_000 and K.DISRUPTOR_MAX == 10 and K.DISRUPTOR_CLEAR_MAX == 12
    assert K.LIMPET_REMOVAL_COST == 1_250
    assert K.PHOTON_WAVE_DURATION == 1


def _world(seed: int = 5101):
    u = generate_universe(GameConfig(seed=seed, universe_size=80, enable_ferrengi=False, enable_planets=True))
    # Place two players in a linked pair of non-Fed sectors
    sid = next(s for s in sorted(u.sectors) if s > 10 and len(u.sectors[s].warps) >= 1)
    adj = u.sectors[sid].warps[0]
    u.players["A"] = Player(
        id="A", name="Alpha", ship=Ship(holds=40, fighters=200, shields=100),
        sector_id=sid, credits=500_000,
    )
    u.players["B"] = Player(
        id="B", name="Bravo", ship=Ship(holds=40, fighters=50, shields=20),
        sector_id=adj, credits=50_000,
    )
    u.sectors[sid].occupant_ids.append("A")
    u.sectors[adj].occupant_ids.append("B")
    u.players["A"].known_sectors.update([sid, adj])
    u.players["B"].known_sectors.update([sid, adj])
    return u, sid, adj


# --- planted bugs (legal list + handler) --------------------------------------

def test_plant_cloak_without_owning(tw) -> None:
    """Plant: cloak without owning one."""
    u, sid, adj = _world()
    u.players["A"].ship.cloaks = 0
    las = {a.kind: a for a in legal_actions(u, "A")}
    assert las["cloak"].legal is False
    r = apply_action(u, "A", Action(kind=ActionKind.CLOAK, args={}))
    assert r.ok is False


def test_plant_cloak_still_attackable(tw) -> None:
    """Plant: cloak still attackable."""
    u, sid, adj = _world()
    # Move B into A's sector and cloak B
    u.sectors[adj].occupant_ids.remove("B")
    u.players["B"].sector_id = sid
    u.sectors[sid].occupant_ids.append("B")
    u.players["B"].ship.cloaks = 1
    assert apply_action(u, "B", Action(kind=ActionKind.CLOAK, args={})).ok
    assert u.players["B"].ship.cloaked is True
    las = {a.kind: a for a in legal_actions(u, "A")}
    assert "B" not in (las["attack"].params.get("target") or {}).get("choices", [])
    r = apply_action(u, "A", Action(kind=ActionKind.ATTACK, args={"target": "B", "qty": 10}))
    assert r.ok is False and "cloak" in (r.error or "").lower()


def test_plant_cloaked_density_not_forty(tw) -> None:
    """Plant: density shows cloaked ship as 40."""
    u, sid, adj = _world()
    # Empty-ish sector: only B, cloaked
    u.sectors[sid].occupant_ids.remove("A")
    u.players["A"].sector_id = adj
    u.sectors[adj].occupant_ids.append("A")
    # B alone in sid
    u.sectors[adj].occupant_ids = [x for x in u.sectors[adj].occupant_ids if x != "B"]
    u.players["B"].sector_id = sid
    if "B" not in u.sectors[sid].occupant_ids:
        u.sectors[sid].occupant_ids.append("B")
    u.sectors[sid].fighters = None
    u.sectors[sid].mines = []
    u.sectors[sid].port = None
    u.sectors[sid].planet_ids = []
    u.players["B"].ship.cloaks = 1
    apply_action(u, "B", Action(kind=ActionKind.CLOAK, args={}))
    reading = density_reading(u, sid)
    assert reading["density"] == 0
    assert reading["anomaly"] is True


def test_plant_photon_from_wrong_hull(tw) -> None:
    """Plant: photon from wrong hull."""
    u, sid, adj = _world()
    u.players["A"].ship.ship_class = ShipClass.MERCHANT_CRUISER
    u.players["A"].ship.photon_missiles = 2
    las = {a.kind: a for a in legal_actions(u, "A")}
    assert las["photon_missile"].legal is False
    r = apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": adj}))
    assert r.ok is False


def test_plant_photon_same_sector_player_refused(tw) -> None:
    """Plant: photon same-sector player target still works under tw2002."""
    u, sid, adj = _world()
    u.players["A"].ship.ship_class = ShipClass.MISSILE_FRIGATE
    u.players["A"].ship.photon_missiles = 2
    # B same sector
    u.sectors[adj].occupant_ids.remove("B")
    u.players["B"].sector_id = sid
    u.sectors[sid].occupant_ids.append("B")
    r = apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": "B"}))
    assert r.ok is False
    # Adjacent sector works
    r2 = apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": adj}))
    assert r2.ok is True
    assert u.sectors[adj].photon_wave_remaining == K.PHOTON_WAVE_DURATION


def test_plant_photon_clears_mines_fighters(tw) -> None:
    """Plant: photon does not clear/neutralize mines/fighters."""
    u, sid, adj = _world()
    u.players["A"].ship.ship_class = ShipClass.MISSILE_FRIGATE
    u.players["A"].ship.photon_missiles = 1
    u.sectors[adj].mines = [MineDeployment(owner_id="B", kind=MineType.ARMID, count=20)]
    u.sectors[adj].fighters = FighterDeployment(owner_id="B", count=100, mode=FighterMode.OFFENSIVE)
    assert apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": adj})).ok
    assert u.sectors[adj].photon_wave_remaining > 0
    # Warp A into adj — mines/fighters must not bite during the wave
    shields_before = u.players["A"].ship.shields
    fighters_before = u.players["A"].ship.fighters
    # Move A next to adj if needed — A is in sid which warps to adj
    r = apply_action(u, "A", Action(kind=ActionKind.WARP, args={"target": adj}))
    assert r.ok
    assert u.players["A"].ship.shields == shields_before
    assert u.players["A"].ship.fighters == fighters_before
    # Mines still sitting (neutralized, not destroyed)
    assert sum(m.count for m in u.sectors[adj].mines if m.kind == MineType.ARMID) == 20


def test_plant_disruptor_non_adjacent(tw) -> None:
    """Plant: disruptor from non-adjacent."""
    u, sid, adj = _world()
    u.players["A"].ship.mine_disruptors = 2
    far = next(s for s in sorted(u.sectors) if s not in (sid, adj) and s not in u.sectors[sid].warps)
    las = {a.kind: a for a in legal_actions(u, "A")}
    assert far not in (las["fire_disruptor"].params.get("target") or {}).get("choices", [])
    r = apply_action(u, "A", Action(kind=ActionKind.FIRE_DISRUPTOR, args={"target": far}))
    assert r.ok is False


def test_plant_disruptor_clears_at_most_12(tw) -> None:
    """Plant: disruptor clears >12."""
    u, sid, adj = _world()
    u.players["A"].ship.mine_disruptors = 3
    u.sectors[adj].mines = [MineDeployment(owner_id="B", kind=MineType.ARMID, count=40)]
    before = 40
    assert apply_action(u, "A", Action(kind=ActionKind.FIRE_DISRUPTOR, args={"target": adj})).ok
    after = sum(m.count for m in u.sectors[adj].mines if m.kind == MineType.ARMID)
    cleared = before - after
    assert 1 <= cleared <= 12


def test_plant_armid_not_100_under_tw2002(tw) -> None:
    """Plant: armid still deals 100 dmg under tw2002."""
    hits, dmg = armid_detonation_hits(10, __import__("random").Random(0))
    assert hits == 5 and dmg == 20
    u, sid, adj = _world()
    u.sectors[adj].mines = [MineDeployment(owner_id="B", kind=MineType.ARMID, count=10)]
    u.sectors[adj].fighters = None
    u.players["A"].ship.shields = 500
    u.players["A"].ship.fighters = 500
    u.players["A"].ship.photon_missiles = 0
    before = u.players["A"].ship.shields
    apply_action(u, "A", Action(kind=ActionKind.WARP, args={"target": adj}))
    # 5 hits * 20 = 100 damage to shields
    assert before - u.players["A"].ship.shields == 100


def test_plant_limpet_removal_needs_fee_and_stardock(tw) -> None:
    """Plant: limpet removal free / without StarDock."""
    u, sid, adj = _world()
    from tw2k.engine.combat import _attach_limpet
    _attach_limpet(u, "B", "A")
    # Not at StarDock
    las = {a.kind: a for a in legal_actions(u, "A")}
    assert las["remove_limpet"].legal is False
    r = apply_action(u, "A", Action(kind=ActionKind.REMOVE_LIMPET, args={}))
    assert r.ok is False
    # Move to StarDock
    for s in list(u.sectors[u.players["A"].sector_id].occupant_ids):
        pass
    try:
        u.sectors[u.players["A"].sector_id].occupant_ids.remove("A")
    except ValueError:
        pass
    u.players["A"].sector_id = K.STARDOCK_SECTOR
    u.sectors[K.STARDOCK_SECTOR].occupant_ids.append("A")
    u.players["A"].credits = 0
    las = {a.kind: a for a in legal_actions(u, "A")}
    assert las["remove_limpet"].legal is False
    u.players["A"].credits = 50_000
    r = apply_action(u, "A", Action(kind=ActionKind.REMOVE_LIMPET, args={}))
    assert r.ok is True
    assert u.players["A"].credits == 50_000 - K.LIMPET_REMOVAL_COST
    assert not any(lt.target_id == "A" for lt in u.limpets.values())


def test_plant_legal_photon_with_zero_missiles(tw) -> None:
    """Plant: legal list offers photon with 0 missiles."""
    u, sid, adj = _world()
    u.players["A"].ship.ship_class = ShipClass.MISSILE_FRIGATE
    u.players["A"].ship.photon_missiles = 0
    las = {a.kind: a for a in legal_actions(u, "A")}
    assert las["photon_missile"].legal is False


def test_plant_carried_photon_blast(tw) -> None:
    """Plant: carried photon does not risk blast into offensive figs."""
    u, sid, adj = _world()
    u.players["A"].ship.ship_class = ShipClass.MISSILE_FRIGATE
    u.players["A"].ship.photon_missiles = 3
    u.sectors[adj].mines = []
    u.sectors[adj].fighters = FighterDeployment(owner_id="B", count=50, mode=FighterMode.OFFENSIVE)
    u.players["A"].turns_today = 10
    u.players["A"].turns_per_day = 100
    apply_action(u, "A", Action(kind=ActionKind.WARP, args={"target": adj}))
    assert u.players["A"].ship.photon_missiles == 0
    assert u.players["A"].turns_today == u.players["A"].turns_per_day


def test_plant_legacy_keeps_old_armid_and_hides_gadgets(legacy) -> None:
    """Plant: HARDWARE_MODE legacy still offers working cloak / half-armid."""
    u, sid, adj = _world()
    kinds = {a.kind: a for a in legal_actions(u, "A")}
    # Legacy does not offer the new gadgets at all (same as rob/steal under ROB_MODE legacy) ...
    for k in ("cloak", "fire_disruptor", "remove_limpet"):
        assert k not in kinds, k
    # ... and the handler refuses them even with a cloak aboard.
    u.players["A"].ship.cloaks = 1
    r = apply_action(u, "A", Action(kind=ActionKind.CLOAK, args={}))
    assert r.ok is False and not u.players["A"].ship.cloaked
    u.players["A"].ship.cloaks = 0
    hits, dmg = armid_detonation_hits(10, __import__("random").Random(1))
    assert dmg == 100
    assert 1 <= hits <= 10
    # Legacy photon: same-sector player still works
    u.players["A"].ship.photon_missiles = 1
    u.sectors[adj].occupant_ids.remove("B")
    u.players["B"].sector_id = sid
    u.sectors[sid].occupant_ids.append("B")
    r = apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": "B"}))
    assert r.ok is True
    assert u.players["B"].ship.photon_disabled_ticks > 0


def test_buy_cloak_and_disruptor_caps(tw) -> None:
    u, sid, adj = _world()
    try:
        u.sectors[sid].occupant_ids.remove("A")
    except ValueError:
        pass
    u.players["A"].sector_id = K.STARDOCK_SECTOR
    u.sectors[K.STARDOCK_SECTOR].occupant_ids.append("A")
    u.players["A"].credits = 10_000_000
    r = apply_action(u, "A", Action(kind=ActionKind.BUY_EQUIP, args={"item": "cloak", "qty": 5}))
    assert r.ok
    assert u.players["A"].ship.cloaks == 5
    r = apply_action(u, "A", Action(kind=ActionKind.BUY_EQUIP, args={"item": "cloak", "qty": 1}))
    assert r.ok is False
    r = apply_action(u, "A", Action(kind=ActionKind.BUY_EQUIP, args={"item": "mine_disruptor", "qty": 10}))
    assert r.ok
    assert u.players["A"].ship.mine_disruptors == 10
    r = apply_action(u, "A", Action(kind=ActionKind.BUY_EQUIP, args={"item": "mine_disruptor", "qty": 1}))
    assert r.ok is False


def test_photon_decloaks(tw) -> None:
    u, sid, adj = _world()
    u.players["A"].ship.ship_class = ShipClass.IMPERIAL_STARSHIP
    u.players["A"].ship.photon_missiles = 1
    u.players["B"].ship.cloaks = 1
    apply_action(u, "B", Action(kind=ActionKind.CLOAK, args={}))
    assert u.players["B"].ship.cloaked
    assert apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": adj})).ok
    assert u.players["B"].ship.cloaked is False
