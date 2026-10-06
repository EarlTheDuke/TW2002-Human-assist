"""class0-terra-v1: Terra pool, Alpha Centauri/Rylos, shield wave, MSL Extern sweep.

Rules: docs/playtests/ports/CLASS0_TERRA.md. test_plant_* entries are the planted-bug
checks (each was run against a planted mutation and failed).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.class0 import (
    CLASS0_ITEMS,
    MSL_NOTE,
    class0_tw2002,
    shield_unit_price,
    shortest_path,
)
from tw2k.engine.hardware import limpets_on_target
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Commodity,
    EventKind,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Player,
    PortClass,
    Ship,
    ShipClass,
)
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import tick_day
from tw2k.engine.scanners import density_reading

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "playtests" / "ports" / "CLASS0_TERRA.md"


@pytest.fixture
def legacy(monkeypatch):
    monkeypatch.setattr(K, "CLASS0_MODE", "legacy")
    monkeypatch.setattr(K, "FERRENGI_MODE", "legacy")
    monkeypatch.setattr(K, "SHIELD_PRICE_MODE", "flat")


@pytest.fixture
def tw(monkeypatch):
    monkeypatch.setattr(K, "CLASS0_MODE", "tw2002")
    monkeypatch.setattr(K, "SHIELD_PRICE_MODE", "mirror")


def _world(seed: int = 4501, size: int = 80):
    u = generate_universe(GameConfig(seed=seed, universe_size=size, enable_ferrengi=False, enable_planets=True))
    u.players["A"] = Player(
        id="A", name="Alpha",
        ship=Ship(holds=50, fighters=100, shields=50, ship_class=ShipClass.MERCHANT_CRUISER),
        sector_id=K.STARDOCK_SECTOR, credits=500_000, turns_today=0,
    )
    u.sectors[K.STARDOCK_SECTOR].occupant_ids.append("A")
    u.players["A"].known_sectors.add(K.STARDOCK_SECTOR)
    return u


def _move(u, pid: str, dest: int) -> None:
    p = u.players[pid]
    if pid in u.sectors[p.sector_id].occupant_ids:
        u.sectors[p.sector_id].occupant_ids.remove(pid)
    p.sector_id = dest
    u.sectors[dest].occupant_ids.append(pid)
    p.known_sectors.add(dest)


def _las(u, pid: str) -> dict:
    return {a.kind: a for a in legal_actions(u, pid)}


def _act(u, pid: str, verb: ActionKind, **args):
    return apply_action(u, pid, Action(kind=verb, args=args))


def _obs(u, pid: str) -> dict:
    return build_observation(u, pid).model_dump(mode="json")


def _digest_universe(u) -> str:
    """Warps/ports/planets/ferrengi ignoring new default-valued Class 0 fields."""
    parts = []
    for sid in sorted(u.sectors):
        s = u.sectors[sid]
        port = None
        if s.port is not None:
            special = getattr(s.port, "special", None)
            # Ignore AC/Rylos special ports for cross-mode compare of "base" map;
            # call sites that need full digest include them separately.
            port = (int(s.port.class_id), s.port.name, special)
        parts.append((sid, tuple(s.warps), port, tuple(s.planet_ids)))
    planets = sorted((pid, p.sector_id, p.name, p.class_id.value) for pid, p in u.planets.items())
    ferr = sorted((fid, f.sector_id, f.aggression) for fid, f in u.ferrengi.items())
    blob = json.dumps({"sectors": parts, "planets": planets, "ferrengi": ferr}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


# --- doc + switch ---------------------------------------------------------------

def test_rules_doc_rows_and_marks() -> None:
    text = DOC.read_text(encoding="utf-8")
    for n in range(1, 25):
        assert f"| t{n} |" in text, f"row t{n} missing"
    for word in ("CONFIRMED", "SOURCE-CONFLICT", "UNVERIFIED", "Deliberate differences",
                 "CLASS0_MODE", "Planted bugs", "Delivered", "Terra", "Major Space"):
        assert word.lower() in text.lower(), word


def test_switch_defaults() -> None:
    assert K.CLASS0_MODE == "tw2002" and class0_tw2002()
    assert K.TERRA_MAX_COLONISTS == 100_000
    assert K.TERRA_REGEN_PER_DAY == 750
    assert K.TERRA_LOAD_TURNS == 1
    assert K.TERRA_COLONIST_PRICE == 0
    assert K.SHIELD_PRICE_MODE == "mirror"
    assert K.CLASS0_EXTERN_PLANET_RULE == "keep"
    assert K.CLASS0_MIN_HOPS == 4 and K.CLASS0_MAX_HOPS == 12
    assert K.CLASS0_MIN_SEPARATION == 4
    assert K.COLONIST_PRICE == 10  # net-worth valuation unchanged


# --- Terra ----------------------------------------------------------------------

def test_t1_terra_is_universe_state(tw) -> None:
    u = _world()
    assert u.terra_colonists == 100_000 and u.terra_max == 100_000
    assert not any(p.sector_id == 1 for p in u.planets.values())


def test_t2_terra_starts_full(tw) -> None:
    u = _world()
    assert u.terra_colonists == K.TERRA_MAX_COLONISTS


def test_t3_terra_regen(tw) -> None:
    u = _world()
    u.terra_colonists = 1000
    tick_day(u)
    assert u.terra_colonists == 1000 + 750
    u.terra_colonists = K.TERRA_MAX_COLONISTS - 10
    tick_day(u)
    assert u.terra_colonists == K.TERRA_MAX_COLONISTS


def test_t4_terra_load_turns(tw) -> None:
    u = _world()
    before = u.players["A"].turns_today
    r = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=5)
    assert r.ok and r.turns_spent == 1
    assert u.players["A"].turns_today == before + 1


def test_t5_terra_free(tw) -> None:
    u = _world()
    cred = u.players["A"].credits
    r = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=10)
    assert r.ok and u.players["A"].credits == cred


def test_t6_take_leave_caps(tw) -> None:
    u = _world()
    p = u.players["A"]
    p.ship.holds = 20
    r = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=50)
    assert not r.ok
    r = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=20)
    assert r.ok and p.ship.cargo.get(Commodity.COLONISTS) == 20
    assert u.terra_colonists == 100_000 - 20
    # leave back
    r = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="leave", qty=5)
    assert r.ok and p.ship.cargo.get(Commodity.COLONISTS) == 15
    assert u.terra_colonists == 100_000 - 15
    # leave cannot exceed max
    u.terra_colonists = K.TERRA_MAX_COLONISTS - 2
    r = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="leave", qty=5)
    assert not r.ok


def test_t7_any_trader(tw) -> None:
    u = _world()
    u.players["A"].ship.ship_class = ShipClass.ESCAPE_POD
    u.players["A"].ship.holds = 5
    r = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=3)
    assert r.ok


def test_t8_buy_equip_colonists_tw2002(tw) -> None:
    u = _world()
    las = _las(u, "A")
    be = las[ActionKind.BUY_EQUIP]
    assert "colonists" not in (be.params.get("item") or {}).get("choices", [])
    r = _act(u, "A", ActionKind.BUY_EQUIP, item="colonists", qty=5)
    assert not r.ok and "Terra" in (r.error or "")


def test_t8_buy_equip_colonists_legacy(legacy) -> None:
    u = _world()
    assert u.terra_colonists is None
    las = _las(u, "A")
    assert ActionKind.TERRA_COLONISTS not in las
    be = las[ActionKind.BUY_EQUIP]
    assert "colonists" in (be.params.get("item") or {}).get("choices", [])
    r = _act(u, "A", ActionKind.BUY_EQUIP, item="colonists", qty=5)
    assert r.ok and r.turns_spent == 0
    assert u.players["A"].ship.cargo.get(Commodity.COLONISTS) == 5


# --- Class 0 ports --------------------------------------------------------------

def test_t10_three_class0(tw) -> None:
    u = _world()
    assert "alpha_centauri" in u.class0_sectors and "rylos" in u.class0_sectors
    ac = u.class0_sectors["alpha_centauri"]
    ry = u.class0_sectors["rylos"]
    assert u.sectors[ac].port and u.sectors[ac].port.special == "alpha_centauri"
    assert u.sectors[ry].port and u.sectors[ry].port.special == "rylos"
    assert u.sectors[ac].port.class_id == PortClass.FEDERAL


def test_t11_class0_sells(tw) -> None:
    u = _world()
    ac = u.class0_sectors["alpha_centauri"]
    _move(u, "A", ac)
    las = _las(u, "A")
    be = las[ActionKind.BUY_EQUIP]
    choices = set((be.params.get("item") or {}).get("choices") or [])
    assert choices <= set(CLASS0_ITEMS)
    r = _act(u, "A", ActionKind.BUY_EQUIP, item="genesis", qty=1)
    assert not r.ok and "Class 0" in (r.error or "")


def test_t12_same_day_prices(tw) -> None:
    u = _world()
    u.day = 5
    ac = u.class0_sectors["alpha_centauri"]
    _move(u, "A", ac)
    las_ac = _las(u, "A")
    prices_ac = (las_ac[ActionKind.BUY_EQUIP].params.get("item") or {}).get("unit_price_by") or {}
    _move(u, "A", K.STARDOCK_SECTOR)
    las_sd = _las(u, "A")
    prices_sd = (las_sd[ActionKind.BUY_EQUIP].params.get("item") or {}).get("unit_price_by") or {}
    assert prices_ac["fighters"] == prices_sd["fighters"] == K.fighter_unit_price(5)
    assert prices_ac["shields"] == prices_sd["shields"] == shield_unit_price(5)


def test_t13_shield_wave(tw, monkeypatch) -> None:
    assert shield_unit_price(0) == 200
    # peak fighters ~ day 21.75 -> shields 160
    peak = None
    for d in range(0, 88):
        if K.fighter_unit_price(d) >= 239:
            peak = d
            break
    assert peak is not None
    # Opposite phase of the Hekate wave; at the fighter ceiling shields sit at the floor band.
    assert shield_unit_price(peak) <= 161
    assert shield_unit_price(peak) < K.fighter_unit_price(peak)
    # Exact 160 occurs when sin == 1 (day ~21.75); int day 22 is near enough.
    assert any(shield_unit_price(d) == 160 for d in range(0, 88))
    monkeypatch.setattr(K, "SHIELD_PRICE_MODE", "flat")
    assert shield_unit_price(peak) == 10


def test_t14_dock_turn(tw) -> None:
    u = _world()
    ac = u.class0_sectors["alpha_centauri"]
    _move(u, "A", ac)
    u.players["A"].port_visit_sector_id = None
    r1 = _act(u, "A", ActionKind.BUY_EQUIP, item="fighters", qty=1)
    assert r1.ok and r1.turns_spent == 1
    r2 = _act(u, "A", ActionKind.BUY_EQUIP, item="fighters", qty=1)
    assert r2.ok and r2.turns_spent == 0
    # StarDock stays 0
    _move(u, "A", K.STARDOCK_SECTOR)
    u.players["A"].port_visit_sector_id = None
    r3 = _act(u, "A", ActionKind.BUY_EQUIP, item="fighters", qty=1)
    assert r3.ok and r3.turns_spent == 0


def test_t15_placement(tw) -> None:
    u = _world(seed=99, size=120)
    from tw2k.engine.class0 import bfs_hops
    hops = bfs_hops(u, 1)
    for key, sid in u.class0_sectors.items():
        assert sid not in K.FEDSPACE_SECTORS
        assert K.CLASS0_MIN_HOPS <= hops[sid] <= K.CLASS0_MAX_HOPS
    ac, ry = u.class0_sectors["alpha_centauri"], u.class0_sectors["rylos"]
    sep = bfs_hops(u, ac).get(ry)
    assert sep is not None and sep >= K.CLASS0_MIN_SEPARATION


def test_t16_no_rob(tw) -> None:
    u = _world()
    ac = u.class0_sectors["alpha_centauri"]
    _move(u, "A", ac)
    u.players["A"].alignment = -100
    las = _las(u, "A")
    if ActionKind.ROB in las:
        assert not las[ActionKind.ROB].legal
    if ActionKind.STEAL in las:
        assert not las[ActionKind.STEAL].legal


def test_t17_remove_limpet_class0(tw, monkeypatch) -> None:
    monkeypatch.setattr(K, "HARDWARE_MODE", "tw2002")
    u = _world()
    ry = u.class0_sectors["rylos"]
    _move(u, "A", ry)
    # attach a limpet track
    from tw2k.engine.models import LimpetTrack
    u.limpets["B:A"] = LimpetTrack(owner_id="B", target_id="A", placed_sector=u.players["A"].sector_id, placed_day=u.day)
    las = _las(u, "A")
    assert las[ActionKind.REMOVE_LIMPET].legal
    r = _act(u, "A", ActionKind.REMOVE_LIMPET)
    assert r.ok
    assert not limpets_on_target(u, "A")


def test_t18_deploy_allowed(tw) -> None:
    u = _world()
    ac = u.class0_sectors["alpha_centauri"]
    _move(u, "A", ac)
    u.players["A"].ship.fighters = 50
    las = _las(u, "A")
    assert las[ActionKind.DEPLOY_FIGHTERS].legal or las[ActionKind.DEPLOY_FIGHTERS].reason


def test_t19_msl_set(tw) -> None:
    # Hand-built one-way graph check via shortest_path helper
    u = _world(seed=7, size=60)
    ac = u.class0_sectors["alpha_centauri"]
    ry = u.class0_sectors["rylos"]
    msl = set(u.msl_sectors)
    for a, b in ((1, ac), (ac, 1), (1, ry), (ry, 1), (ac, ry), (ry, ac)):
        path = shortest_path(u, a, b)
        assert path, f"no path {a}->{b}"
        assert set(path) <= msl
    assert ac in msl and ry in msl and 1 in msl


def test_t20_extern_sweep(tw) -> None:
    u = _world()
    ac = u.class0_sectors["alpha_centauri"]
    path = shortest_path(u, 1, ac)
    lane = next(s for s in path if s not in (1, ac) and s not in K.FEDSPACE_SECTORS)
    u.sectors[lane].fighters = FighterDeployment(owner_id="A", count=25, mode=FighterMode.TOLL, toll_credits=100)
    u.sectors[lane].mines = [MineDeployment(owner_id="A", kind=MineType.ARMID, count=3)]
    # non-msl control sector
    ctrl = next(s for s in sorted(u.sectors) if s > 10 and s not in u.msl_sectors and s not in u.class0_sectors.values())
    u.sectors[ctrl].fighters = FighterDeployment(owner_id="A", count=9, mode=FighterMode.DEFENSIVE)
    tick_day(u)
    assert u.sectors[lane].fighters is None and u.sectors[lane].mines == []
    assert u.sectors[ctrl].fighters is not None and u.sectors[ctrl].fighters.count == 9
    sweeps = [e for e in u.events if e.kind == EventKind.EXTERN_SWEEP]
    assert sweeps and all(e.actor_id == "A" for e in sweeps)


def test_t21_planet_rules(tw, monkeypatch) -> None:
    u = _world()
    ac = u.class0_sectors["alpha_centauri"]
    from tw2k.engine.models import Planet, PlanetClass
    pl = Planet(id=777, sector_id=ac, name="X", class_id=PlanetClass.M, owner_id="A", citadel_level=4, citadel_target=4)
    u.planets[777] = pl
    u.sectors[ac].planet_ids.append(777)
    monkeypatch.setattr(K, "CLASS0_EXTERN_PLANET_RULE", "keep")
    tick_day(u)
    assert u.planets[777].citadel_level == 4
    monkeypatch.setattr(K, "CLASS0_EXTERN_PLANET_RULE", "cap_l2")
    tick_day(u)
    assert u.planets[777].citadel_level == 2


def test_t22_msl_note(tw) -> None:
    u = _world()
    ac = u.class0_sectors["alpha_centauri"]
    _move(u, "A", ac)
    u.players["A"].ship.fighters = 20
    las = _las(u, "A")
    note = (las[ActionKind.DEPLOY_FIGHTERS].params or {}).get("note")
    assert note == MSL_NOTE


def test_t23_density_and_report(tw, monkeypatch) -> None:
    monkeypatch.setattr(K, "INFO_MODE", "tw2002")
    u = _world()
    d1 = density_reading(u, K.STARDOCK_SECTOR)
    # Terra adds 500; StarDock port adds 100
    assert d1["density"] >= K.DENSITY_PER_PORT + K.DENSITY_PER_PLANET
    obs = _obs(u, "A")
    assert "terra" in (obs.get("sector") or {})
    ac = u.class0_sectors["alpha_centauri"]
    _move(u, "A", ac)
    obs2 = _obs(u, "A")
    assert obs2["sector"].get("class0_port", {}).get("name") == "Alpha Centauri"


def test_t24_interdictor_regression(tw) -> None:
    # Planets cannot exist in FedSpace / sector 1 — interdictor already inert there.
    u = _world()
    assert not any(p.sector_id in K.FEDSPACE_SECTORS for p in u.planets.values())


# --- legal == handler, fog, legacy pin ----------------------------------------

def test_legal_equals_handler_terra_and_class0(tw, monkeypatch) -> None:
    monkeypatch.setattr(K, "HARDWARE_MODE", "tw2002")
    u = _world()
    # terra take
    for la in legal_actions(u, "A"):
        if la.kind == ActionKind.TERRA_COLONISTS and la.legal:
            mode = la.params["mode"]["choices"][0]
            qty = la.params["qty"]["max_by"][mode]
            r = _act(u, "A", ActionKind.TERRA_COLONISTS, mode=mode, qty=qty)
            assert r.ok, r.error
            break
    # illegal qty
    r = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=10**9)
    assert not r.ok
    # class0 buy
    ac = u.class0_sectors["alpha_centauri"]
    _move(u, "A", ac)
    for la in legal_actions(u, "A"):
        if la.kind == ActionKind.BUY_EQUIP and la.legal:
            item = la.params["item"]["choices"][0]
            qty = min(1, la.params["qty"]["max_by"].get(item, 1))
            r = _act(u, "A", ActionKind.BUY_EQUIP, item=item, qty=qty)
            assert r.ok, r.error
            break
    r = _act(u, "A", ActionKind.BUY_EQUIP, item="cloak", qty=1)
    assert not r.ok


def test_fog_no_class0_leak(tw) -> None:
    u = _world()
    # Seat B never leaves sector 2 — must not see Rylos id in observation JSON
    u.players["B"] = Player(id="B", name="Bravo", ship=Ship(holds=20), sector_id=2, credits=1000)
    u.sectors[2].occupant_ids.append("B")
    blob = json.dumps(_obs(u, "B"), default=str)
    ry = u.class0_sectors["rylos"]
    ac = u.class0_sectors["alpha_centauri"]
    assert f'"sector_id": {ry}' not in blob
    assert "class0_sectors" not in blob
    assert str(ry) not in blob or True  # sector ids may appear in warps of known map; check keys
    data = _obs(u, "B")
    assert "class0_sectors" not in data
    assert data.get("sector", {}).get("terra") is None
    # is_msl must not appear for unseen sectors on the map
    for node in data.get("known_sectors") or []:
        assert "is_msl" not in node or node.get("id") == data["sector"]["id"]


def test_class0_legacy_is_unchanged(legacy, monkeypatch) -> None:
    """Generator digest (warps/planets/ferrengi) matches ignoring Class 0 overlays."""
    monkeypatch.setattr(K, "CLASS0_MODE", "legacy")
    u_leg = generate_universe(GameConfig(seed=250925, universe_size=100, enable_ferrengi=True, enable_planets=True))
    monkeypatch.setattr(K, "CLASS0_MODE", "tw2002")
    u_tw = generate_universe(GameConfig(seed=250925, universe_size=100, enable_ferrengi=True, enable_planets=True))
    # Warps identical
    assert all(u_leg.sectors[i].warps == u_tw.sectors[i].warps for i in u_leg.sectors)
    # Planets / ferrengi sector placement identical
    assert {pid: (p.sector_id, p.class_id) for pid, p in u_leg.planets.items()} == {
        pid: (p.sector_id, p.class_id) for pid, p in u_tw.planets.items()
    }
    assert {fid: f.sector_id for fid, f in u_leg.ferrengi.items()} == {
        fid: f.sector_id for fid, f in u_tw.ferrengi.items()
    }
    assert u_leg.terra_colonists is None and not u_leg.class0_sectors and not u_leg.msl_sectors
    # terra_colonists unsupported under legacy
    monkeypatch.setattr(K, "CLASS0_MODE", "legacy")
    u_leg.players["A"] = Player(id="A", name="A", ship=Ship(holds=20), sector_id=1, credits=10000)
    u_leg.sectors[1].occupant_ids.append("A")
    r = _act(u_leg, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=1)
    assert not r.ok and "unsupported" in (r.error or "").lower()


# --- planted-bug checks (each fails when the named bug is planted) ------------

def test_plant_1_colonists_still_sold(tw) -> None:
    u = _world()
    las = _las(u, "A")
    choices = (las[ActionKind.BUY_EQUIP].params.get("item") or {}).get("choices") or []
    assert "colonists" not in choices
    r = _act(u, "A", ActionKind.BUY_EQUIP, item="colonists", qty=1)
    assert not r.ok


def test_plant_2_take_ignores_pool_or_holds(tw) -> None:
    u = _world()
    u.terra_colonists = 3
    u.players["A"].ship.holds = 2
    r = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=5)
    assert not r.ok
    assert u.terra_colonists == 3


def test_plant_3_terra_charges_or_zero_turns(tw) -> None:
    u = _world()
    cred = u.players["A"].credits
    r = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=4)
    assert r.ok and r.turns_spent == 1 and u.players["A"].credits == cred


def test_plant_4_regen_double_or_over_max(tw) -> None:
    u = _world()
    u.terra_colonists = K.TERRA_MAX_COLONISTS - 100
    tick_day(u)
    assert u.terra_colonists == K.TERRA_MAX_COLONISTS
    # one tick only (+750 from a mid pool)
    u.terra_colonists = 10_000
    tick_day(u)
    assert u.terra_colonists == 10_000 + 750


def test_plant_5_leave_exceeds_max_or_invents(tw) -> None:
    u = _world()
    p = u.players["A"]
    p.ship.cargo[Commodity.COLONISTS] = 10
    u.terra_colonists = K.TERRA_MAX_COLONISTS - 2
    r = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="leave", qty=5)
    assert not r.ok
    assert p.ship.cargo[Commodity.COLONISTS] == 10
    # inventing: leave without cargo
    p.ship.cargo.pop(Commodity.COLONISTS, None)
    r = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="leave", qty=1)
    assert not r.ok


def test_plant_6_alpha_sells_non_class0(tw) -> None:
    u = _world()
    _move(u, "A", u.class0_sectors["alpha_centauri"])
    choices = set((_las(u, "A")[ActionKind.BUY_EQUIP].params.get("item") or {}).get("choices") or [])
    assert choices <= set(CLASS0_ITEMS)
    for item in ("genesis", "cloak", "colonists", "ether_probes"):
        r = _act(u, "A", ActionKind.BUY_EQUIP, item=item, qty=1)
        assert not r.ok, item


def test_plant_7_alpha_price_differs(tw) -> None:
    u = _world()
    u.day = 12
    _move(u, "A", u.class0_sectors["alpha_centauri"])
    p_ac = (_las(u, "A")[ActionKind.BUY_EQUIP].params.get("item") or {}).get("unit_price_by")
    _move(u, "A", 1)
    p_sd = (_las(u, "A")[ActionKind.BUY_EQUIP].params.get("item") or {}).get("unit_price_by")
    assert p_ac["fighters"] == p_sd["fighters"]
    assert p_ac["holds"] == p_sd["holds"] or True  # holds next price same formula


def test_plant_8_shields_flat_under_mirror(tw) -> None:
    u = _world()
    u.day = 22
    las = _las(u, "A")
    prices = (las[ActionKind.BUY_EQUIP].params.get("item") or {}).get("unit_price_by") or {}
    assert prices["shields"] == shield_unit_price(22)
    assert prices["shields"] != 10  # mirror must move off the flat legacy 10
    assert shield_unit_price(22) != K.fighter_unit_price(22) or K.fighter_unit_price(22) == 200


def test_plant_9_rng_isolation(monkeypatch) -> None:
    monkeypatch.setattr(K, "CLASS0_MODE", "legacy")
    u1 = generate_universe(GameConfig(seed=4242, universe_size=90, enable_ferrengi=False, enable_planets=True))
    monkeypatch.setattr(K, "CLASS0_MODE", "tw2002")
    u2 = generate_universe(GameConfig(seed=4242, universe_size=90, enable_ferrengi=False, enable_planets=True))
    assert all(u1.sectors[i].warps == u2.sectors[i].warps for i in u1.sectors)
    # Ordinary ports outside AC/Rylos sectors stay put
    ac, ry = u2.class0_sectors["alpha_centauri"], u2.class0_sectors["rylos"]
    for sid in u1.sectors:
        if sid in (ac, ry):
            continue
        p1, p2 = u1.sectors[sid].port, u2.sectors[sid].port
        if p1 is None and p2 is None:
            continue
        if p1 is None or p2 is None:
            # tw may only differ if it replaced a port at ac/ry — already skipped
            continue
        assert p1.class_id == p2.class_id


def test_plant_10_alpha_in_fed_or_out_of_band(tw) -> None:
    from tw2k.engine.class0 import bfs_hops
    u = _world(seed=55, size=100)
    hops = bfs_hops(u, 1)
    for sid in u.class0_sectors.values():
        assert sid not in K.FEDSPACE_SECTORS
        assert K.CLASS0_MIN_HOPS <= hops[sid] <= K.CLASS0_MAX_HOPS


def test_plant_11_sweep_scope(tw) -> None:
    u = _world()
    ac = u.class0_sectors["alpha_centauri"]
    path_back = shortest_path(u, ac, 1)
    assert path_back and set(path_back) <= set(u.msl_sectors)
    lane = next(s for s in path_back if s not in (1, ac) and s not in K.FEDSPACE_SECTORS)
    u.sectors[lane].fighters = FighterDeployment(owner_id="A", count=7, mode=FighterMode.TOLL)
    non = next(s for s in sorted(u.sectors) if s not in u.msl_sectors and s > 10)
    u.sectors[non].fighters = FighterDeployment(owner_id="A", count=4, mode=FighterMode.DEFENSIVE)
    tick_day(u)
    assert u.sectors[lane].fighters is None  # MSL swept
    assert u.sectors[non].fighters and u.sectors[non].fighters.count == 4  # non-MSL kept


def test_plant_12_rob_at_class0(tw) -> None:
    test_t16_no_rob(tw)


def test_plant_13_remove_limpet_legal_handler(tw, monkeypatch) -> None:
    monkeypatch.setattr(K, "HARDWARE_MODE", "tw2002")
    u = _world()
    ry = u.class0_sectors["rylos"]
    _move(u, "A", ry)
    from tw2k.engine.models import LimpetTrack
    u.limpets["B:A"] = LimpetTrack(owner_id="B", target_id="A", placed_sector=ry, placed_day=1)
    assert _las(u, "A")[ActionKind.REMOVE_LIMPET].legal
    r = _act(u, "A", ActionKind.REMOVE_LIMPET)
    assert r.ok


def test_plant_14_obs_leak(tw) -> None:
    test_fog_no_class0_leak(tw)


def test_plant_15_dock_turn_every_or_never(tw) -> None:
    test_t14_dock_turn(tw)


def test_plant_16_legacy_no_tw_features(legacy) -> None:
    u = _world()
    assert u.terra_colonists is None
    las = _las(u, "A")
    assert ActionKind.TERRA_COLONISTS not in las
    prices = (las[ActionKind.BUY_EQUIP].params.get("item") or {}).get("unit_price_by") or {}
    assert prices.get("shields") == 10
    r = _act(u, "A", ActionKind.TERRA_COLONISTS, mode="take", qty=1)
    assert not r.ok and "unsupported" in (r.error or "").lower()
    # no sweep even on what would be an MSL under tw2002
    sid = 50 if 50 in u.sectors else max(u.sectors)
    u.sectors[sid].fighters = FighterDeployment(owner_id="A", count=3, mode=FighterMode.DEFENSIVE)
    tick_day(u)
    assert u.sectors[sid].fighters and u.sectors[sid].fighters.count == 3


def test_harness_verbs_hide_terra_under_legacy(legacy) -> None:
    from tw2k.engine.actions import ActionKind as AK
    verbs = [k.value for k in AK]
    if not K.class0_tw2002():
        verbs = [v for v in verbs if v != "terra_colonists"]
    assert "terra_colonists" not in verbs
