"""ship-hardware-v2: corbomite, beacons, psychic probe, atomic detonator, NavHaz, entry order.

Rules table: docs/playtests/ships/SHIP_HARDWARE_V2.md. Tests named test_plant_* are the
planted-bug checks listed in that doc (each was run against a planted bug and failed).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.combat import _attach_limpet, _destroy_ship
from tw2k.engine.hardware import navhaz_pct, psychic_reading, tick_navhaz
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Commodity,
    EventKind,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Planet,
    PlanetClass,
    Player,
    Ship,
    ShipClass,
)
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import tick_day
from tw2k.engine.scanners import density_reading

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "playtests" / "ships" / "SHIP_HARDWARE_V2.md"
V2_ITEMS = ("corbomite", "marker_beacon", "psychic_probe", "atomic_detonator")


@pytest.fixture
def legacy(monkeypatch):
    monkeypatch.setattr(K, "HARDWARE_MODE", "legacy")


@pytest.fixture
def tw(monkeypatch):
    monkeypatch.setattr(K, "HARDWARE_MODE", "tw2002")


def _world(seed: int = 5202):
    u = generate_universe(GameConfig(seed=seed, universe_size=80, enable_ferrengi=False, enable_planets=True))
    sid = next(s for s in sorted(u.sectors) if s > 10 and len(u.sectors[s].warps) >= 1
               and all(w > 10 for w in u.sectors[s].warps))
    adj = u.sectors[sid].warps[0]
    for s in (sid, adj):
        sec = u.sectors[s]
        sec.mines, sec.fighters, sec.planet_ids = [], None, []
        sec.nav_hazard = 0.0
    u.players["A"] = Player(id="A", name="Alpha", ship=Ship(holds=40, fighters=200, shields=100),
                            sector_id=sid, credits=500_000)
    u.players["B"] = Player(id="B", name="Bravo", ship=Ship(holds=40, fighters=50, shields=20),
                            sector_id=adj, credits=50_000)
    u.sectors[sid].occupant_ids.append("A")
    u.sectors[adj].occupant_ids.append("B")
    for p in ("A", "B"):
        u.players[p].known_sectors.update([sid, adj])
    return u, sid, adj


def _move(u, pid: str, dest: int) -> None:
    p = u.players[pid]
    if pid in u.sectors[p.sector_id].occupant_ids:
        u.sectors[p.sector_id].occupant_ids.remove(pid)
    p.sector_id = dest
    u.sectors[dest].occupant_ids.append(pid)


def _planet(u, sector_id: int, pid: int = 901, owner: str | None = "B", colonists: int = 0, **kw) -> Planet:
    pl = Planet(id=pid, sector_id=sector_id, name=f"P{pid}", class_id=PlanetClass.M, owner_id=owner, **kw)
    pl.colonists[Commodity.FUEL_ORE] = colonists
    u.planets[pid] = pl
    u.sectors[sector_id].planet_ids.append(pid)
    return pl


def _las(u, pid: str) -> dict:
    return {a.kind: a for a in legal_actions(u, pid)}


def _act(u, pid: str, verb: ActionKind, **args):
    return apply_action(u, pid, Action(kind=verb, args=args))


def _rival_payload(u, pid: str) -> str:
    return json.dumps(build_observation(u, pid).model_dump(mode="json"), default=str)


# --- doc + switch ---------------------------------------------------------------

def test_rules_doc_rows_and_marks() -> None:
    text = DOC.read_text(encoding="utf-8")
    for n in range(1, 31):
        assert f"| v{n} |" in text, f"row v{n} missing"
    for word in ("CONFIRMED", "SOURCE-CONFLICT", "UNVERIFIED", "Deliberate differences", "HARDWARE_MODE",
                 "ATOMIC_MINES_PORT_NUKE", "Planted bugs", "Delivered", "entry order"):
        assert word.lower() in text.lower(), word


def test_switch_defaults() -> None:
    assert K.HARDWARE_MODE == "tw2002"
    assert K.CORBOMITE_COST == 1_000 and K.CORBOMITE_MAX == 1_500 and K.CORBOMITE_DAMAGE_PER_UNIT == 20
    assert K.BEACON_COST == 100 and K.BEACON_MESSAGE_MAX == 41 and K.DENSITY_PER_BEACON == 1
    assert K.PSYCHIC_PROBE_COST == 2_500 and K.PSYCHIC_PROBE_MAX == 1
    assert K.ATOMIC_DETONATOR_COST == 60_000 and K.ATOMIC_DETONATOR_MAX == 5
    assert K.ATOMIC_MINES_PORT_NUKE is True
    assert K.NAVHAZ_DAMAGE_PER_PCT == 10 and K.NAVHAZ_PER_PLANET_DESTROYED == 10
    assert K.DENSITY_PER_NAVHAZ_PCT == 21
    assert K.BEACON_MAX_BY_HULL["merchant_cruiser"] == 50 and K.BEACON_MAX_BY_HULL["imperial_starship"] == 150


# --- legacy pin -----------------------------------------------------------------

def test_plant_legacy_hides_v2(legacy) -> None:
    """Plant: legacy still sells / offers the v2 items and verbs."""
    u, sid, adj = _world()
    las = _las(u, "A")
    assert "launch_beacon" not in las
    assert las["deploy_atomic"].legal is False and "not a dispatched verb" in las["deploy_atomic"].reason
    _move(u, "A", K.STARDOCK_SECTOR)
    buy = _las(u, "A")["buy_equip"]
    for item in V2_ITEMS:
        assert item not in buy.params["item"]["choices"]
        assert item not in buy.params["item"]["unit_price_by"]
        assert _act(u, "A", ActionKind.BUY_EQUIP, item=item, qty=1).ok is False
    ship = build_observation(u, "A").ship
    for key in ("corbomite", "marker_beacons", "psychic_probe", "atomic_detonators"):
        assert key not in ship
    u.players["A"].ship.marker_beacons = 1
    assert _act(u, "A", ActionKind.LAUNCH_BEACON, message="hi").ok is False
    r = _act(u, "A", ActionKind.DEPLOY_ATOMIC, planet_id=1)
    assert r.ok is False and "unsupported action" in r.error
    # Legacy reads no NavHaz and keeps the density reading's navhaz 0.
    u.sectors[adj].nav_hazard = 100.0
    assert density_reading(u, adj)["navhaz"] == 0
    _move(u, "A", sid)
    shields = u.players["A"].ship.shields
    assert _act(u, "A", ActionKind.WARP, target=adj).ok
    assert u.players["A"].ship.shields == shields


def test_legacy_dead_list_and_harness_verbs(legacy) -> None:
    u, sid, adj = _world()
    u.players["A"].alive = False
    assert "launch_beacon" not in {a.kind for a in legal_actions(u, "A")}
    from pathlib import Path

    text = Path(__file__).resolve().parents[1].joinpath("src/tw2k/server/harness.py").read_text(encoding="utf-8")
    hide = text[text.index("if not K.hardware_tw2002():"):]
    assert "launch_beacon" in hide[:600]


# --- corbomite ------------------------------------------------------------------

def test_plant_corbomite_cap_1500(tw) -> None:
    """Plant: corbomite cap missing (buy 1,501)."""
    u, sid, adj = _world()
    _move(u, "A", K.STARDOCK_SECTOR)
    u.players["A"].credits = 10_000_000
    buy = _las(u, "A")["buy_equip"]
    assert buy.params["qty"]["max_by"]["corbomite"] == 1_500
    assert _act(u, "A", ActionKind.BUY_EQUIP, item="corbomite", qty=1_501).ok is False
    assert _act(u, "A", ActionKind.BUY_EQUIP, item="corbomite", qty=1_500).ok
    assert u.players["A"].credits == 10_000_000 - 1_500 * K.CORBOMITE_COST
    assert "corbomite" not in _las(u, "A")["buy_equip"].params["item"]["choices"]


def test_plant_corbomite_hits_killer(tw) -> None:
    """Plant: corbomite does nothing to the ship that destroyed you."""
    u, sid, adj = _world()
    u.players["B"].ship.corbomite = 10  # 200 damage
    a = u.players["A"].ship
    a.shields, a.fighters = 50, 1_000
    _destroy_ship(u, "B", reason="combat", killer_id="A", by_other=True)
    assert a.shields == 0 and a.fighters == 1_000 - 150
    ev = [e for e in u.events if e.kind == EventKind.CORBOMITE_BLAST]
    assert ev and ev[-1].payload["damage"] == 200 and ev[-1].payload["victim"] == "A"
    assert u.players["B"].ship.corbomite == 0  # gone with the hull


def test_corbomite_can_kill_killer_and_ignores_mines(tw) -> None:
    u, sid, adj = _world()
    u.players["B"].ship.corbomite = 1_500  # 30,000 damage
    deaths = u.players["A"].deaths
    _destroy_ship(u, "B", reason="combat", killer_id="A", by_other=True)
    assert u.players["A"].deaths == deaths + 1
    reasons = [e.payload.get("reason") for e in u.events if e.kind == EventKind.SHIP_DESTROYED]
    assert "corbomite" in reasons
    # A mine / quasar / NavHaz death is not a ship kill: no blast.
    u2, sid2, adj2 = _world()
    u2.players["B"].ship.corbomite = 1_500
    _destroy_ship(u2, "B", reason="mines", killer_id="A")
    assert not [e for e in u2.events if e.kind == EventKind.CORBOMITE_BLAST]


def test_corbomite_via_attack(tw) -> None:
    u, sid, adj = _world()
    _move(u, "B", sid)
    u.players["B"].ship.fighters, u.players["B"].ship.shields = 1, 0
    u.players["B"].ship.corbomite = 5
    u.players["A"].ship.fighters, u.players["A"].ship.shields = 2_000, 0
    r = _act(u, "A", ActionKind.ATTACK, target="B", qty=500)
    assert r.ok, r.error
    blast = [e for e in u.events if e.kind == EventKind.CORBOMITE_BLAST]
    assert blast and blast[-1].payload["damage"] == 100


def test_plant_corbomite_never_in_rival_view(tw) -> None:
    """Plant: corbomite count leaks into a rival's or corp mate's observation."""
    u, sid, adj = _world()
    _move(u, "B", sid)
    u.players["B"].ship.corbomite = 777
    u.players["A"].corp_ticker = u.players["B"].corp_ticker = "ZZZ"
    obs = build_observation(u, "A")
    assert "777" not in _rival_payload(u, "A")
    rivals = json.dumps([obs.other_players, obs.sector], default=str)
    assert "corbomite" not in rivals
    assert build_observation(u, "B").ship["corbomite"] == 777


# --- marker beacons -------------------------------------------------------------

def test_plant_two_beacons_both_explode(tw) -> None:
    """Plant: a second beacon overwrites the first instead of both exploding."""
    u, sid, adj = _world()
    u.players["A"].ship.marker_beacons = 2
    assert _act(u, "A", ActionKind.LAUNCH_BEACON, message="Alpha was here").ok
    assert u.sectors[sid].beacon == "Alpha was here"
    assert density_reading(u, sid)["density"] >= 1
    assert _act(u, "A", ActionKind.LAUNCH_BEACON, message="second").ok
    assert u.sectors[sid].beacon is None
    assert u.players["A"].ship.marker_beacons == 0
    assert _las(u, "A")["launch_beacon"].legal is False


def test_plant_beacon_message_limit_and_density(tw) -> None:
    """Plant: beacon message has no 41-char limit / beacon not on density."""
    u, sid, adj = _world()
    u.players["A"].ship.marker_beacons = 1
    la = _las(u, "A")["launch_beacon"]
    assert la.legal and la.params["message"]["max_len"] == 41
    assert _act(u, "A", ActionKind.LAUNCH_BEACON, message="x" * 42).ok is False
    assert u.players["A"].ship.marker_beacons == 1
    empty = density_reading(u, sid)["density"]
    assert _act(u, "A", ActionKind.LAUNCH_BEACON, message="x" * 41).ok
    assert density_reading(u, sid)["density"] == empty + 1


def test_plant_beacon_owner_hidden(tw) -> None:
    """Plant: the beacon launch event / owner reaches a rival."""
    u, sid, adj = _world()
    _move(u, "B", sid)
    u.players["A"].ship.marker_beacons = 1
    assert _act(u, "A", ActionKind.LAUNCH_BEACON, message="keep out").ok
    obs_b = build_observation(u, "B")
    assert obs_b.sector["beacon"] == "keep out"
    assert not [e for e in obs_b.recent_events if e["kind"] == "beacon_launched"]
    assert "beacon_owner" not in json.dumps(obs_b.sector)


def test_beacon_cap_by_hull(tw) -> None:
    u, sid, adj = _world()
    _move(u, "A", K.STARDOCK_SECTOR)
    u.players["A"].ship.ship_class = ShipClass.SCOUT_MARAUDER
    buy = _las(u, "A")["buy_equip"]
    assert buy.params["qty"]["max_by"]["marker_beacon"] == K.BEACON_MAX_BY_HULL["scout_marauder"]
    assert _act(u, "A", ActionKind.BUY_EQUIP, item="marker_beacon", qty=11).ok is False


# --- psychic probe --------------------------------------------------------------

def _port_world():
    u, sid, adj = _world()
    psid = next(s for s in sorted(u.sectors) if s > 10 and u.sectors[s].port is not None
                and int(u.sectors[s].port.class_id) in range(1, 9))
    _move(u, "A", psid)
    port = u.sectors[psid].port
    sold = next(c for c in (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT) if port.buys(c))
    u.players["A"].ship.cargo[sold] = 10
    return u, psid, port, sold


def test_plant_psychic_probe_reading(tw) -> None:
    """Plant: psychic probe reports nothing / the wrong side's limit."""
    from tw2k.engine.economy import _stored_mcic, haggle_bound, port_buy_price

    u, psid, port, sold = _port_world()
    u.players["A"].ship.psychic_probe = 1
    listed = port_buy_price(port, sold, int(u.players["A"].experience))
    best = haggle_bound(listed, _stored_mcic(port, sold), "sell")
    r = _act(u, "A", ActionKind.TRADE, commodity=sold.value, qty=5, side="sell", unit_price=best)
    assert r.ok, r.error
    ev = [e for e in u.events if e.kind == EventKind.PSYCHIC_PROBE]
    assert ev and ev[-1].payload["pct"] == 100.0
    assert psychic_reading(100, 100, 50, "sell") < 100.0
    assert psychic_reading(100, 100, 50, "buy") < 100.0
    assert psychic_reading(100, 80, 0, "buy") <= 100.0


def test_plant_psychic_probe_private(tw) -> None:
    """Plant: psychic reading visible to a rival in the port sector / works without a probe."""
    u, psid, port, sold = _port_world()
    _move(u, "B", psid)
    assert _act(u, "A", ActionKind.TRADE, commodity=sold.value, qty=2, side="sell").ok
    assert not [e for e in u.events if e.kind == EventKind.PSYCHIC_PROBE]
    u.players["A"].ship.psychic_probe = 1
    assert _act(u, "A", ActionKind.TRADE, commodity=sold.value, qty=2, side="sell").ok
    assert [e for e in u.events if e.kind == EventKind.PSYCHIC_PROBE]
    obs_b = build_observation(u, "B")
    assert not [e for e in obs_b.recent_events if e["kind"] == "psychic_probe"]
    assert "pct" not in json.dumps(obs_b.recent_events)
    mine = [e for e in build_observation(u, "A").recent_events if e["kind"] == "psychic_probe"]
    assert mine and "pct" in mine[-1]["facts"]


def test_psychic_probe_cap_one(tw) -> None:
    u, sid, adj = _world()
    _move(u, "A", K.STARDOCK_SECTOR)
    assert _act(u, "A", ActionKind.BUY_EQUIP, item="psychic_probe", qty=1).ok
    assert _act(u, "A", ActionKind.BUY_EQUIP, item="psychic_probe", qty=1).ok is False


# --- atomic detonator -----------------------------------------------------------

def _landed(u, sid, colonists=0, owner="B", **kw):
    pl = _planet(u, sid, colonists=colonists, owner=owner, **kw)
    u.players["A"].planet_landed = pl.id
    return pl


def test_plant_detonator_with_colonists_kills_you(tw) -> None:
    """Plant: detonator with colonists alive destroys the planet instead of you."""
    u, sid, adj = _world()
    pl = _landed(u, sid, colonists=500)
    u.players["A"].ship.atomic_detonators = 2
    deaths = u.players["A"].deaths
    las = _las(u, "A")["deploy_atomic"]
    assert las.legal and las.params["colonists_alive"] is True
    r = _act(u, "A", ActionKind.DEPLOY_ATOMIC, planet_id=pl.id)
    assert r.ok
    assert u.players["A"].deaths == deaths + 1
    assert pl.id in u.planets
    assert navhaz_pct(u.sectors[sid]) == 0


def test_plant_detonator_destroys_empty_planet(tw) -> None:
    """Plant: detonator on an empty planet leaves it / no NavHaz / not consumed."""
    u, sid, adj = _world()
    pl = _landed(u, sid, colonists=0)
    u.players["A"].ship.atomic_detonators = 2
    r = _act(u, "A", ActionKind.DEPLOY_ATOMIC, planet_id=pl.id)
    assert r.ok, r.error
    assert pl.id not in u.planets and pl.id not in u.sectors[sid].planet_ids
    assert u.players["A"].ship.atomic_detonators == 1
    assert navhaz_pct(u.sectors[sid]) == K.NAVHAZ_PER_PLANET_DESTROYED
    assert density_reading(u, sid)["navhaz"] == 10


def test_plant_detonator_legal_equals_handler(tw) -> None:
    """Plant: legal list offers deploy_atomic with no detonator / on a defended or corp planet."""
    u, sid, adj = _world()
    pl = _landed(u, sid, colonists=0, fighters=10)
    for ships_dets, fighters, corp in ((0, 0, None), (1, 10, None), (1, 0, "ZZZ")):
        u.players["A"].ship.atomic_detonators = ships_dets
        pl.fighters = fighters
        pl.corp_ticker = corp
        u.players["A"].corp_ticker = corp
        la = _las(u, "A")["deploy_atomic"]
        r = _act(u, "A", ActionKind.DEPLOY_ATOMIC, planet_id=pl.id)
        assert la.legal is False and r.ok is False and pl.id in u.planets


def test_detonator_cap_five_and_own_planet(tw) -> None:
    u, sid, adj = _world()
    _move(u, "A", K.STARDOCK_SECTOR)
    assert _act(u, "A", ActionKind.BUY_EQUIP, item="atomic_detonator", qty=6).ok is False
    assert _act(u, "A", ActionKind.BUY_EQUIP, item="atomic_detonator", qty=5).ok
    _move(u, "A", sid)
    pl = _landed(u, sid, colonists=0, owner="A", fighters=999)  # P-busting your own empty planet
    assert _act(u, "A", ActionKind.DEPLOY_ATOMIC, planet_id=pl.id).ok
    assert pl.id not in u.planets


def test_plant_planet_destroy_last_step_needs_detonator(tw) -> None:
    """Plant: planet_destroy removes the planet without an atomic detonator under tw2002."""
    u, sid, adj = _world()
    pl = _landed(u, sid, colonists=300)
    assert _act(u, "A", ActionKind.PLANET_DESTROY, planet_id=pl.id).ok  # kills colonists, no detonator
    assert sum(pl.colonists.values()) == 0
    la = _las(u, "A")["planet_destroy"]
    assert la.legal is False and "atomic detonator" in la.reason
    assert _act(u, "A", ActionKind.PLANET_DESTROY, planet_id=pl.id).ok is False
    u.players["A"].ship.atomic_detonators = 1
    assert _act(u, "A", ActionKind.PLANET_DESTROY, planet_id=pl.id).ok
    assert pl.id not in u.planets and u.players["A"].ship.atomic_detonators == 0


def test_legacy_planet_destroy_unchanged(legacy) -> None:
    u, sid, adj = _world()
    pl = _landed(u, sid, colonists=0)
    assert _act(u, "A", ActionKind.PLANET_DESTROY, planet_id=pl.id).ok
    assert pl.id not in u.planets and navhaz_pct(u.sectors[sid]) == 0


def test_atomic_mines_switch(tw, monkeypatch) -> None:
    u, sid, adj = _world()
    _move(u, "A", K.STARDOCK_SECTOR)
    assert "atomic_mines" in _las(u, "A")["buy_equip"].params["item"]["choices"]
    monkeypatch.setattr(K, "ATOMIC_MINES_PORT_NUKE", False)
    assert "atomic_mines" not in _las(u, "A")["buy_equip"].params["item"]["choices"]
    assert _act(u, "A", ActionKind.BUY_EQUIP, item="atomic_mines", qty=1).ok is False
    _move(u, "A", sid)
    u.players["A"].ship.mines[MineType.ATOMIC] = 2
    assert "atomic" not in _las(u, "A")["deploy_mines"].params["kind"]["choices"]
    assert _act(u, "A", ActionKind.DEPLOY_MINES, kind="atomic", qty=1).ok is False


# --- NavHaz ---------------------------------------------------------------------

def test_plant_navhaz_damage(tw) -> None:
    """Plant: NavHaz never read on entry / wrong damage."""
    u, sid, adj = _world()
    u.sectors[adj].nav_hazard = 100.0  # chance 100%: 1,000 damage
    a = u.players["A"].ship
    a.shields, a.fighters = 300, 2_000
    assert _act(u, "A", ActionKind.WARP, target=adj).ok
    assert a.shields == 0 and a.fighters == 2_000 - 700
    ev = [e for e in u.events if e.kind == EventKind.NAVHAZ_HIT]
    assert ev and ev[-1].payload["damage"] == 1_000


def test_plant_navhaz_zero_rolls_no_dice(tw) -> None:
    """Plant: NavHaz rolls the RNG in a clean sector (drifts every match)."""
    u, sid, adj = _world()
    state = u.rng.getstate()
    from tw2k.engine.hardware import apply_navhaz
    assert apply_navhaz(u, "A", u.sectors[adj], u.rng) == 0
    assert u.rng.getstate() == state


def test_navhaz_chance_and_death(tw) -> None:
    u, sid, adj = _world()
    from tw2k.engine.hardware import apply_navhaz
    u.sectors[adj].nav_hazard = 30.0
    hits = sum(1 for _ in range(400) if apply_navhaz(u, "B", u.sectors[adj], random.Random(_)) > 0)
    assert 60 < hits < 180  # about 30%
    u.sectors[adj].nav_hazard = 100.0
    u.players["A"].ship.shields, u.players["A"].ship.fighters = 0, 5
    deaths = u.players["A"].deaths
    _act(u, "A", ActionKind.WARP, target=adj)
    assert u.players["A"].deaths == deaths + 1


def test_plant_navhaz_tick(tw) -> None:
    """Plant: FedSpace keeps NavHaz overnight / NavHaz never disperses / StarDock takes NavHaz."""
    u, sid, adj = _world()
    fed = sorted(K.FEDSPACE_SECTORS - {K.STARDOCK_SECTOR})[1]
    u.sectors[fed].nav_hazard = 40.0
    u.sectors[sid].nav_hazard = 40.0
    tick_navhaz(u)
    assert navhaz_pct(u.sectors[fed]) == 0
    assert navhaz_pct(u.sectors[sid]) == 40 - K.NAVHAZ_DISPERSION_PER_DAY
    from tw2k.engine.hardware import add_navhaz
    assert add_navhaz(u.sectors[K.STARDOCK_SECTOR], 10) == 0
    assert add_navhaz(u.sectors[sid], 500) == 100
    tick_day(u)
    assert navhaz_pct(u.sectors[sid]) == 100 - K.NAVHAZ_DISPERSION_PER_DAY


def test_navhaz_density_and_sector_view(tw) -> None:
    u, sid, adj = _world()
    base = density_reading(u, adj)["density"]
    u.sectors[adj].nav_hazard = 5.0
    reading = density_reading(u, adj)
    assert reading["navhaz"] == 5 and reading["density"] == base + 5 * 21
    _move(u, "A", adj)
    assert build_observation(u, "A").sector["nav_hazard_pct"] == 5


# --- entry order ----------------------------------------------------------------

def test_plant_entry_order(tw) -> None:
    """Plant: hostile entry order not NavHaz > limpet > armid > quasar > fighters."""
    u, sid, adj = _world()
    sec = u.sectors[adj]
    sec.nav_hazard = 1.0
    sec.mines = [MineDeployment(owner_id="B", kind=MineType.ARMID, count=4),
                 MineDeployment(owner_id="B", kind=MineType.LIMPET, count=3)]
    sec.fighters = FighterDeployment(owner_id="B", count=5, mode=FighterMode.OFFENSIVE)
    pl = _planet(u, adj, owner="B", citadel_level=max(3, K.QUASAR_MIN_LEVEL), quasar_sector_pct=10)
    pl.stockpile[Commodity.FUEL_ORE] = 3_000
    a = u.players["A"].ship
    a.shields, a.fighters, a.photon_missiles = 1_000, 5_000, 0
    # Force the 1% NavHaz roll to hit.
    u.rng.seed(0)
    while True:
        st = u.rng.getstate()
        if u.rng.random() * 100.0 < 1.0:
            u.rng.setstate(st)
            break
    seq0 = u.seq
    assert _act(u, "A", ActionKind.WARP, target=adj).ok
    kinds = [e.kind for e in u.events if e.seq > seq0]
    order = [EventKind.NAVHAZ_HIT, EventKind.MINE_DETONATED, EventKind.QUASAR_FIRE, EventKind.COMBAT]
    idx = [kinds.index(k) for k in order]
    assert idx == sorted(idx), kinds
    assert any(lt.target_id == "A" for lt in u.limpets.values())


def test_plant_legacy_entry_order_unchanged(legacy) -> None:
    """Plant: legacy entry order drifts (quasar before fighters, or fired twice)."""
    u, sid, adj = _world()
    sec = u.sectors[adj]
    sec.fighters = FighterDeployment(owner_id="B", count=5, mode=FighterMode.OFFENSIVE)
    pl = _planet(u, adj, owner="B", citadel_level=max(3, K.QUASAR_MIN_LEVEL), quasar_sector_pct=10)
    pl.stockpile[Commodity.FUEL_ORE] = 3_000
    a = u.players["A"].ship
    a.shields, a.fighters, a.photon_missiles = 1_000, 5_000, 0
    seq0 = u.seq
    assert _act(u, "A", ActionKind.WARP, target=adj).ok
    kinds = [e.kind for e in u.events if e.seq > seq0]
    assert kinds.count(EventKind.QUASAR_FIRE) == 1, kinds
    assert kinds.index(EventKind.COMBAT) < kinds.index(EventKind.QUASAR_FIRE), kinds


def test_plant_one_limpet_and_old_falls_off(tw) -> None:
    """Plant: every limpet field attaches / an older limpet stays on."""
    u, sid, adj = _world()
    u.players["C"] = Player(id="C", name="Charlie", ship=Ship(), sector_id=sid, credits=1)
    _attach_limpet(u, "C", "A")  # an old limpet from C
    u.sectors[adj].mines = [MineDeployment(owner_id="B", kind=MineType.LIMPET, count=2),
                            MineDeployment(owner_id="D", kind=MineType.LIMPET, count=2)]
    assert _act(u, "A", ActionKind.WARP, target=adj).ok
    owners = sorted(lt.owner_id for lt in u.limpets.values() if lt.target_id == "A")
    assert owners == ["B"]
    assert sum(m.count for m in u.sectors[adj].mines) == 3


def test_plant_avoid_prompt_stops_autopilot(tw) -> None:
    """Plant: mines do not stop autopilot (no avoid prompt)."""
    u, sid, adj = _world()
    nxt = next((w for w in u.sectors[adj].warps if w not in (sid, adj)), None)
    assert nxt is not None
    u.sectors[nxt].mines, u.sectors[nxt].fighters = [], None
    u.sectors[adj].mines = [MineDeployment(owner_id="B", kind=MineType.ARMID, count=1)]
    r = _act(u, "A", ActionKind.PLOT_COURSE, target=nxt, execute=True)
    assert r.ok
    assert u.players["A"].sector_id == adj
    prompts = [e for e in u.events if e.kind == EventKind.HAZARD_AVOID_PROMPT]
    assert prompts and prompts[-1].actor_id == "A"
    # The prompt is private.
    _move(u, "B", adj)
    assert not [e for e in build_observation(u, "B").recent_events if e["kind"] == "hazard_avoid_prompt"]


def test_plant_cloaked_navhaz_hit_hidden(tw) -> None:
    """Plant: a cloaked ship's NavHaz hit tells rivals in the sector it is there."""
    u, sid, adj = _world()
    u.players["A"].ship.cloaks = 1
    u.players["A"].ship.fighters = 5_000
    assert _act(u, "A", ActionKind.CLOAK).ok
    u.sectors[adj].nav_hazard = 100.0
    assert _act(u, "A", ActionKind.WARP, target=adj).ok
    seen = build_observation(u, "B").recent_events
    assert not [e for e in seen if e["kind"] == "navhaz_hit"]


def test_ship_view_and_strip_on_death(tw) -> None:
    u, sid, adj = _world()
    s = u.players["A"].ship
    s.corbomite, s.marker_beacons, s.psychic_probe, s.atomic_detonators, s.cloaks = 9, 3, 1, 2, 1
    view = build_observation(u, "A").ship
    assert (view["corbomite"], view["marker_beacons"], view["psychic_probe"], view["atomic_detonators"]) == (9, 3, 1, 2)
    _destroy_ship(u, "A", reason="mines")
    s = u.players["A"].ship
    assert (s.corbomite, s.marker_beacons, s.psychic_probe, s.atomic_detonators, s.cloaks) == (0, 0, 0, 0, 0)


def test_legal_matches_handler_v2_verbs(tw) -> None:
    """legal list == handler for launch_beacon / deploy_atomic over random states."""
    rng = random.Random(7)
    for i in range(40):
        u, sid, adj = _world(seed=5202)
        p = u.players["A"]
        p.ship.marker_beacons = rng.choice([0, 1, 2])
        p.ship.atomic_detonators = rng.choice([0, 1])
        p.turns_today = rng.choice([0, p.turns_per_day])
        if rng.random() < 0.6:
            _landed(u, sid, colonists=rng.choice([0, 10]), owner=rng.choice(["A", "B", None]),
                    fighters=rng.choice([0, 5]))
        las = _las(u, "A")
        snap = u.model_copy(deep=True)
        r = _act(snap, "A", ActionKind.LAUNCH_BEACON, message="m")
        assert las["launch_beacon"].legal == r.ok, (i, las["launch_beacon"].reason, r.error)
        snap = u.model_copy(deep=True)
        r = _act(snap, "A", ActionKind.DEPLOY_ATOMIC, planet_id=p.planet_landed if p.planet_landed else 0)
        assert las["deploy_atomic"].legal == r.ok, (i, las["deploy_atomic"].reason, r.error)
