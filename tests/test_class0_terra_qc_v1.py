"""Independent QC plants for class0-terra-v1 (legacy byte-identity, legal == handler, fog, hints)."""

from __future__ import annotations

import hashlib

import pytest

import tw2k.engine.constants as K
from tw2k.agents.prompts import get_system_prompt
from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View
from tw2k.engine import Action, GameConfig, apply_action, generate_universe
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
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import tick_day

# sha256[:16] of get_system_prompt() on eb19593 (pre-slice), full and minimal hint levels.
LEGACY_PROMPT_FULL = "f6129281ab710c02"
LEGACY_PROMPT_MINIMAL = "c2258c3b76a09d73"
# buy_equip item choices at StarDock on eb19593 for a 200k MerchantCruiser (HARDWARE/INFO tw2002).
LEGACY_STARDOCK_CHOICES = [
    "fighters",
    "shields",
    "armid_mines",
    "limpet_mines",
    "atomic_mines",
    "ether_probes",
    "genesis",
    "holds",
    "colonists",
    "cloak",
    "mine_disruptor",
    "corbomite",
    "marker_beacon",
    "psychic_probe",
    "atomic_detonator",
    "density_scanner",
    "holo_scanner",
]


@pytest.fixture
def legacy(monkeypatch):
    monkeypatch.setattr(K, "CLASS0_MODE", "legacy")
    monkeypatch.setattr(K, "FERRENGI_MODE", "legacy")
    monkeypatch.setattr(K, "FED_MODE", "legacy")  # pins predate fedspace-police-v1
    monkeypatch.setattr(K, "SHIP_TW_MODE", "legacy")  # pins predate ship TransWarp
    monkeypatch.setattr(K, "FLEET_MODE", "legacy")  # pins predate the ship fleet
    monkeypatch.setattr(K, "BUY_RESERVE_MODE", "legacy")  # pins predate fullgame-fixes-v1 price sheet


@pytest.fixture
def tw(monkeypatch):
    monkeypatch.setattr(K, "CLASS0_MODE", "tw2002")
    monkeypatch.setattr(K, "SHIELD_PRICE_MODE", "mirror")


def _world(seed: int = 250925, size: int = 1000):
    u = generate_universe(
        GameConfig(seed=seed, universe_size=size, enable_ferrengi=False, enable_planets=True)
    )
    u.players["A"] = Player(
        id="A",
        name="Alpha",
        ship=Ship(holds=40, fighters=100, shields=10, ship_class=ShipClass.MERCHANT_CRUISER),
        sector_id=1,
        credits=200_000,
    )
    u.sectors[1].occupant_ids.append("A")
    return u


def _move(u, pid, dest):
    p = u.players[pid]
    if pid in u.sectors[p.sector_id].occupant_ids:
        u.sectors[p.sector_id].occupant_ids.remove(pid)
    p.sector_id = dest
    u.sectors[dest].occupant_ids.append(pid)


def _la(u, pid, kind):
    return next(a for a in legal_actions(u, pid) if a.kind == kind)


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def test_plant_legacy_prompt_byte_identical(legacy, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_HINT_LEVEL", raising=False)
    full = get_system_prompt()
    assert "terra_colonists" not in full
    assert _h(full) == LEGACY_PROMPT_FULL
    monkeypatch.setenv("TW2K_HINT_LEVEL", "minimal")
    assert _h(get_system_prompt()) == LEGACY_PROMPT_MINIMAL


def test_tw2002_prompt_teaches_terra(tw, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_HINT_LEVEL", raising=False)
    text = get_system_prompt()
    assert "terra_colonists" in text and "Major Space Lanes" in text
    assert 'buy_equip {"item":"colonists"' not in text


def test_plant_legacy_buy_equip_choice_order(legacy) -> None:
    u = _world()
    assert _la(u, "A", "buy_equip").params["item"]["choices"] == LEGACY_STARDOCK_CHOICES


def test_plant_tw2002_stardock_hint_uses_terra(tw) -> None:
    u = _world()
    hint = build_observation(u, "A").action_hint
    assert "terra_colonists mode=take" in hint
    assert "buy_equip item=colonists" not in hint


def test_legacy_stardock_hint_unchanged(legacy) -> None:
    u = _world()
    hint = build_observation(u, "A").action_hint
    assert "buy_equip item=colonists qty=40" in hint and "terra_colonists" not in hint


def test_plant_class0_buy_out_of_turns_refused(tw) -> None:
    u = _world()
    ac = u.class0_sectors["alpha_centauri"]
    _move(u, "A", ac)
    p = u.players["A"]
    p.turns_today = p.turns_per_day
    la = _la(u, "A", "buy_equip")
    assert la.legal is False and "out of turns" in (la.reason or "")
    before = (p.ship.fighters, p.credits)
    r = apply_action(u, "A", Action(kind="buy_equip", args={"item": "fighters", "qty": 1}))
    assert r.ok is False and "out of turns" in (r.error or "")
    assert (p.ship.fighters, p.credits) == before


def test_class0_dock_turn_charged_once(tw) -> None:
    u = _world()
    _move(u, "A", u.class0_sectors["rylos"])
    assert (
        apply_action(u, "A", Action(kind="buy_equip", args={"item": "fighters", "qty": 1})).turns_spent == 1
    )
    assert (
        apply_action(u, "A", Action(kind="buy_equip", args={"item": "fighters", "qty": 1})).turns_spent == 0
    )


def test_plant_terra_bad_qty_is_an_error_not_a_crash(tw) -> None:
    u = _world()
    r = apply_action(u, "A", Action(kind="terra_colonists", args={"mode": "take", "qty": "lots"}))
    assert r.ok is False and "whole number" in (r.error or "")


def test_plant_terra_load_is_actor_only(tw) -> None:
    u = _world()
    u.players["B"] = Player(id="B", name="Bravo", ship=Ship(holds=40), sector_id=1, credits=10)
    u.sectors[1].occupant_ids.append("B")
    assert apply_action(u, "A", Action(kind="terra_colonists", args={"mode": "take", "qty": 5})).ok
    assert [e for e in build_observation(u, "A").recent_events if e["kind"] == "terra_colonists"]
    assert not [e for e in build_observation(u, "B").recent_events if e["kind"] == "terra_colonists"]


def test_plant_extern_sweep_does_not_leak_rival_counts(tw) -> None:
    u = _world()
    lane = next(
        s for s in u.msl_sectors if s not in K.FEDSPACE_SECTORS and s not in u.class0_sectors.values()
    )
    u.players["B"] = Player(id="B", name="Bravo", ship=Ship(holds=40), sector_id=lane, credits=10)
    u.sectors[lane].occupant_ids.append("B")
    u.sectors[lane].fighters = FighterDeployment(owner_id="B", count=777, mode=FighterMode.DEFENSIVE)
    u.sectors[lane].mines = [MineDeployment(owner_id="A", kind=MineType.LIMPET, count=3)]
    tick_day(u)
    a = [e for e in build_observation(u, "A").recent_events if e["kind"] == "extern_sweep"]
    b = [e for e in build_observation(u, "B").recent_events if e["kind"] == "extern_sweep"]
    assert a and b
    assert "777" not in a[0]["summary"]  # A must not learn B's fighter count
    assert "3 mines" not in b[0]["summary"]  # B must not learn A's hidden limpets
    assert "your 777 fighters, 0 mines" in b[0]["summary"]
    assert "your 0 fighters, 3 mines" in a[0]["summary"]


def test_extern_sweep_event_order_is_deterministic(tw) -> None:
    u = _world()
    lane = next(
        s for s in u.msl_sectors if s not in K.FEDSPACE_SECTORS and s not in u.class0_sectors.values()
    )
    u.players["B"] = Player(id="B", name="Bravo", ship=Ship(holds=40), sector_id=lane, credits=10)
    u.sectors[lane].mines = [
        MineDeployment(owner_id="Z", kind=MineType.ARMID, count=1),
        MineDeployment(owner_id="B", kind=MineType.ARMID, count=1),
        MineDeployment(owner_id="M", kind=MineType.ARMID, count=1),
    ]
    tick_day(u)
    owners = [e.actor_id for e in u.events if e.kind.value == "extern_sweep"]
    assert owners == sorted(owners)


def test_legacy_universe_matches_class0_free_generation(legacy) -> None:
    """Legacy generation: no AC/Rylos, no MSL, no Terra; tw2002 moves only the two special sectors."""
    u_leg = generate_universe(GameConfig(seed=4242, universe_size=400, enable_planets=True))
    assert u_leg.class0_sectors == {} and u_leg.msl_sectors == [] and u_leg.terra_colonists is None
    K.CLASS0_MODE = "tw2002"
    try:
        u_tw = generate_universe(GameConfig(seed=4242, universe_size=400, enable_planets=True))
    finally:
        K.CLASS0_MODE = "legacy"
    specials = set(u_tw.class0_sectors.values())
    assert len(specials) == 2
    for sid, s in u_leg.sectors.items():
        t = u_tw.sectors[sid]
        assert s.warps == t.warps
        assert s.planet_ids == t.planet_ids
        if sid not in specials:
            assert (s.port.model_dump() if s.port else None) == (t.port.model_dump() if t.port else None), sid
    assert u_leg.rng.random() == u_tw.rng.random()


def test_plant_seat_brain_buys_defence_at_class0(tw) -> None:
    """N2 defence trip routed to Alpha Centauri must buy there (was a 308<->719 ping-pong, seed 250925)."""
    u = _world()
    ac = u.class0_sectors["alpha_centauri"]
    _move(u, "A", ac)
    p = u.players["A"]
    p.credits, p.ship.shields, p.ship.fighters = 150_000, 0, 20
    p.known_sectors.add(ac)
    brain = SeatBrain(feed_organics=True, value_allocator=False)
    brain.mem = SeatMemory()
    brain.mem.hot_sectors = {999}
    out = brain._travel(View(build_observation(u, "A").model_dump(mode="json")))
    assert out is not None and out[0]["kind"] == "buy_equip", out
    assert out[0]["args"]["item"] == "shields"


def test_plant_n2_defence_trip_keeps_stardock_business(tw) -> None:
    """A 20-hold N2 seat that can afford CargoTran keeps flying to StarDock (hull + colonists there)."""
    u = _world()
    ac = u.class0_sectors["alpha_centauri"]
    _move(u, "A", ac)
    p = u.players["A"]
    p.credits, p.ship.shields, p.ship.fighters, p.ship.holds = 150_000, 0, 20, 20
    p.known_sectors.add(ac)
    brain = SeatBrain(feed_organics=True, value_allocator=False)
    brain.mem = SeatMemory()
    brain.mem.hot_sectors = {999}
    v = View(build_observation(u, "A").model_dump(mode="json"))
    assert brain._nearest_equip_port(v) == ac  # Class 0 is right here...
    assert brain._defence_dock(v) == 1  # ...but CargoTran is affordable, so StarDock wins


def _stuck_seat(u):
    from tw2k.engine.models import Commodity

    p = u.players["A"]
    p.ship.cargo[Commodity.COLONISTS] = 30
    brain = SeatBrain(feed_organics=True, value_allocator=False)
    brain.mem = SeatMemory()
    brain.mem.home_planet = 77
    brain.mem.no_colonist_room = {77}
    return brain


def test_plant_seat_returns_refused_colonists_to_terra(tw) -> None:
    """Full home world: the seat hands its colonists back instead of trading with full holds."""
    u = _world()
    u.terra_colonists = int(u.terra_max) - 1_000
    brain = _stuck_seat(u)
    out = brain._at_stardock(View(build_observation(u, "A").model_dump(mode="json")))
    assert out is not None and out[0]["kind"] == "terra_colonists", out
    assert out[0]["args"] == {"mode": "leave", "qty": 30}
    assert apply_action(u, "A", Action(kind="terra_colonists", args=out[0]["args"])).ok


def test_full_terra_does_not_ping_pong(tw) -> None:
    u = _world()  # pool starts full: nothing can be left today
    brain = _stuck_seat(u)
    v = View(build_observation(u, "A").model_dump(mode="json"))
    assert brain._return_colonists_to_terra(v) is None
    _move(u, "A", next(iter(u.sectors[1].warps)))
    out = brain._travel(View(build_observation(u, "A").model_dump(mode="json")))
    assert not (out and out[0]["kind"] == "plot_course" and out[0]["args"].get("target") == 1), out


def test_n2_solo_tw2002_keeps_colonising(tw) -> None:
    """Builder pinned the N2 day-10 bar to legacy. Under tw2002, seed 250925 N2 stranded a 75-colonist
    load at a full home world and traded with full holds (NW 174k, one world). Keep it growing."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "seat_brain_acceptance.py"
    spec = importlib.util.spec_from_file_location("seat_brain_acceptance_qc", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    r = mod.prove_growth_replay(seed=250925, brain=mod.n2_brain())
    assert r["rejected"] == 0
    assert r["genesis_worlds"] == 2, r
    assert r["net_worth"] > 300_000, r
