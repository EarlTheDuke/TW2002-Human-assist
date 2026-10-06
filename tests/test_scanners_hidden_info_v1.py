"""scanners-hidden-info-v1: density / holo scanners, ether probes, port reports and the fog.

Rules: docs/playtests/scanners/SCANNERS_HIDDEN_INFO.md. INFO_MODE "tw2002" is the default;
"legacy" must reproduce today's fog exactly (golden digests recorded on origin 4b8fd31, identical on 73971b3).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.agents.prompts import format_observation
from tw2k.agents.seat_acceptance import validate_action
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, build_observation, generate_universe
from tw2k.engine.models import (
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

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "playtests" / "scanners" / "SCANNERS_HIDDEN_INFO.md"
BIG = 98765  # sentinel fighter count in the busy neighbour


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_world(seed: int = 3901, big: int = 4321):
    u = generate_universe(GameConfig(seed=seed, universe_size=200, max_days=10, planet_spawn_probability=0.06))
    for pid, name in (("A", "Alice"), ("B", "Bob"), ("C", "Carol")):
        u.players[pid] = Player(id=pid, name=name, ship=Ship(holds=40, fighters=200, shields=100), sector_id=1)
        u.sectors[1].occupant_ids.append(pid)
        u.players[pid].known_sectors.add(1)
    home = next(s for s in sorted(u.sectors) if s >= 40 and s not in K.FEDSPACE_SECTORS and len(u.sectors[s].warps) >= 3)
    nb = [int(w) for w in u.sectors[home].warps]
    busy, quiet = nb[0], nb[1]
    for pid, sid in (("A", home), ("B", busy), ("C", home)):
        p = u.players[pid]
        u.sectors[p.sector_id].occupant_ids.remove(pid)
        p.sector_id = sid
        u.sectors[sid].occupant_ids.append(pid)
    u.sectors[busy].fighters = FighterDeployment(owner_id="B", count=big, mode=FighterMode.DEFENSIVE)
    u.sectors[busy].mines = [MineDeployment(owner_id="B", kind=MineType.ARMID, count=7),
                             MineDeployment(owner_id="B", kind=MineType.LIMPET, count=3)]
    u.sectors[home].mines = [MineDeployment(owner_id="C", kind=MineType.LIMPET, count=5)]
    u.players["A"].ship.ether_probes = 2
    u.players["A"].credits = 100_000
    return u, home, busy, quiet


def act(u, pid, kind, **args):
    return apply_action(u, pid, Action(kind=kind, args=args))


def legal(u, pid, kind):
    obs = build_observation(u, pid)
    return next(x for x in obs.legal_actions if x["kind"] == kind)


@pytest.fixture
def legacy(monkeypatch):
    monkeypatch.setattr(K, "INFO_MODE", "legacy")
    monkeypatch.setattr(K, "RANK_MODE", "legacy")  # the goldens predate rank titles (experience-alignment-v1)
    monkeypatch.setattr(K, "ROB_MODE", "legacy")  # goldens predate rob/steal
    monkeypatch.setattr(K, "CLASS0_MODE", "legacy")  # goldens predate Terra / Class 0 observation keys
    monkeypatch.setattr(K, "FED_MODE", "legacy")  # goldens predate FedSpace police observation keys
    monkeypatch.setattr(K, "FERRENGI_MODE", "legacy")  # goldens predate ferrengi-aliens-v1 (Ferrengal, hulls)
    monkeypatch.setattr(K, "SHIP_TW_MODE", "legacy")  # goldens predate ship-transwarp-v1 (ship.transwarp block)
    monkeypatch.setattr(K, "FLEET_MODE", "legacy")  # goldens predate ship-fleet-transporter-v1 (unmanned_ships, fleet)
    monkeypatch.setattr(K, "TOW_MODE", "legacy")  # goldens predate ship-tow-transwarp2-v1 (ship.tow, in_tow_by)
    monkeypatch.setattr(K, "PLANET_TRADE_MODE", "legacy")  # pins predate planetary-trading-v1
    monkeypatch.setattr(K, "NET_WORTH_MODE", "legacy")  # goldens predate fullgame-fixes-v1 (net worth)
    monkeypatch.setattr(K, "BUY_RESERVE_MODE", "legacy")  # goldens predate fullgame-fixes-v1 (hints)
    monkeypatch.setattr(K, "PORT_UPGRADE_MODE", "legacy")  # goldens predate port-upgrade-build-v1
    monkeypatch.setattr(K, "FED_OUTPOST_MODE", "legacy")  # goldens predate class0-outpost-label (QC 55)
    monkeypatch.setattr(K, "BANK_MODE", "legacy")  # goldens predate galactic-bank-tax-v1
    monkeypatch.setattr(K, "CORP_MODE", "legacy")  # goldens predate corp-rules-v1


@pytest.fixture
def tw(monkeypatch):
    monkeypatch.setattr(K, "INFO_MODE", "tw2002")


# --- doc first -----------------------------------------------------------------------------

def test_rules_doc_lists_every_row_with_a_mark() -> None:
    text = DOC.read_text(encoding="utf-8")
    for n in range(1, 21):
        assert f"| s{n} |" in text, f"row s{n} missing"
    for word in ("CONFIRMED", "SOURCE-CONFLICT", "UNVERIFIED", "Deliberate differences", "INFO_MODE",
                 "density", "holo", "ether probe", "port report", "limpet"):
        assert word.lower() in text.lower(), word


def test_switch_defaults() -> None:
    assert K.INFO_MODE == "tw2002"
    assert K.info_tw2002()
    assert (K.DENSITY_SCANNER_COST, K.HOLO_SCANNER_COST) == (2_000, 25_000)
    assert K.SCAN_TURNS_TW2002 == {"density": 0, "holo": 1}
    assert K.scan_tiers("holo") == ["density", "holo"] and K.scan_tiers("density") == ["density"]
    assert K.scan_tiers(None) == []
    assert set(K.SCANNER_BY_HULL) >= {c.value for c in ShipClass}


# --- legacy is today's fog, byte for byte ---------------------------------------------------

LEGACY_GOLDEN = [('start', 'A', 'eb0b1ccc22aaa91b', '3a264254ba796f53'),
 ('start', 'B', 'cf487452e3100f1f', '0b45a9fd9de11d4f'),
 ('start', 'C', '89809492e9c70f60', '0207d562a3fc5213'),
 ('scan_basic', True, 1, ''),
 ('scan_basic', 'A', 'b2c373c1dcebca21', 'a651cd06e0e3414f'),
 ('scan_basic', 'B', '4f7f1e5007c09167', '850c0b42b97e0925'),
 ('scan_basic', 'C', '4c373b205979ef1e', '398b9b92a34a58e9'),
 ('scan_density', True, 1, ''),
 ('scan_density', 'A', '7f595aec4c3e59af', '312415a8a11231ef'),
 ('scan_density', 'B', '68b39b74cb5769ef', '88b503814b6d213e'),
 ('scan_density', 'C', '84f3a0d8dc5a9210', '80c9b7f36c20fa94'),
 ('scan_holo', True, 1, ''),
 ('scan_holo', 'A', '4ae93eafee1ae609', '22cf75d736388e30'),
 ('scan_holo', 'B', 'c469897663d56716', '26d99cc94f9a5569'),
 ('scan_holo', 'C', '4d9c25c674bd3409', '4d6c837efe148b0d'),
 ('probe', True, 1, ''),
 ('probe', 'A', 'ed8649f8af323b63', '260bd367faec9da4'),
 ('probe', 'B', 'a077ba20ca31c6f2', '79ec9a190786ba51'),
 ('probe', 'C', 'a95bbcb75bf9176a', '9a495815a2bc5212'),
 ('warp_quiet', True, 3, ''),
 ('warp_quiet', 'A', '7cf74f4be8244be8', '055f924d616e8255'),
 ('warp_quiet', 'B', 'e2c62bec053e9328', 'ee89a20ab337ac61'),
 ('warp_quiet', 'C', 'fc50a8b0b74e65bf', 'f3a088c272b4c935')]


def test_legacy_fog_is_unchanged(legacy) -> None:
    u, home, busy, quiet = build_world()
    out = []

    def snap(tag):
        for pid in ("A", "B", "C"):
            obs = build_observation(u, pid)
            out.append((tag, pid, _digest(obs.model_dump(mode="json")), _digest(format_observation(obs))))

    snap("start")
    far = max(u.sectors)
    for tag, kind, args in (
        ("scan_basic", ActionKind.SCAN, {}),
        ("scan_density", ActionKind.SCAN, {"tier": "density"}),
        ("scan_holo", ActionKind.SCAN, {"tier": "holo"}),
        ("probe", ActionKind.PROBE, {"target": far}),
        ("warp_quiet", ActionKind.WARP, {"target": quiet}),
    ):
        r = apply_action(u, "A", Action(kind=kind, args=args))
        out.append((tag, bool(r.ok), int(r.turns_spent or 0), str(r.error or "")))
        snap(tag)
    assert out == LEGACY_GOLDEN


# --- density scanner -------------------------------------------------------------------------

def _fit(u, pid, scanner):
    u.players[pid].ship.scanner = scanner


def test_density_numbers_follow_the_chart(tw) -> None:
    from tw2k.engine.scanners import density_reading

    u, home, busy, quiet = build_world()
    s = u.sectors[busy]
    port = 100 if s.port is not None else 0
    planets = 500 * len(s.planet_ids)
    r = density_reading(u, busy)
    # 4321 fighters x5, 7 armids x10, 3 limpets x2, Bob's ship 40, plus port and planets
    assert r["density"] == 4321 * 5 + 70 + 6 + 40 + port + planets
    assert r["anomaly"] is True  # limpets read as an anomaly
    assert r["warps"] == len(s.warps) and r["navhaz"] == 0
    q = u.sectors[quiet]
    q.fighters = None
    q.mines = []
    q.occupant_ids = []
    q.planet_ids = []
    q.port = None
    assert density_reading(u, quiet) == {"density": 0, "warps": len(q.warps), "navhaz": 0, "anomaly": False}
    pl = Planet(id=9901, sector_id=quiet, name="Zyzzyx", class_id=PlanetClass.M)
    u.planets[pl.id] = pl
    q.planet_ids.append(pl.id)
    q.mines = [MineDeployment(owner_id="B", kind=MineType.ARMID, count=2)]
    assert density_reading(u, quiet)["density"] == 500 + 20
    u.players["C"].alive = False
    assert density_reading(u, home)["density"] == density_reading(u, home)["density"]  # deterministic


def test_density_scan_costs_no_turn_and_needs_a_scanner(tw) -> None:
    u, home, busy, quiet = build_world()
    la = legal(u, "A", "scan")
    assert la["legal"] is False and "scanner" in la["reason"]
    r = act(u, "A", ActionKind.SCAN)
    assert not r.ok and "scanner" in r.error
    assert u.players["A"].scan_memory == {}
    _fit(u, "A", "density")
    la = legal(u, "A", "scan")
    assert la["legal"] is True and la["turn_cost"] == 0
    assert la["params"]["tier"]["choices"] == ["density"]
    before = u.players["A"].turns_today
    r = act(u, "A", ActionKind.SCAN)
    assert r.ok and r.turns_spent == 0 and u.players["A"].turns_today == before
    mem = u.players["A"].scan_memory[busy]
    assert mem["tier"] == "density" and mem["density"] >= 4321 * 5
    assert "traders" not in mem and "fighters" not in mem
    assert not act(u, "A", ActionKind.SCAN, tier="holo").ok  # density hull fit: no holo mode


def test_holo_scan_costs_a_turn_and_shows_who_is_there(tw) -> None:
    u, home, busy, quiet = build_world()
    _fit(u, "A", "holo")
    la = legal(u, "A", "scan")
    assert la["params"]["tier"]["choices"] == ["density", "holo"]
    assert la["params"]["tier"]["turn_cost_by"] == {"density": 0, "holo": 1}
    before = u.players["A"].turns_today
    r = act(u, "A", ActionKind.SCAN, tier="holo")
    assert r.ok and r.turns_spent == 1
    assert u.players["A"].turns_today == before + 1
    mem = u.players["A"].scan_memory[busy]
    assert mem["fighters"] == {"owner_id": "B", "count": 4321, "mode": "defensive"}
    assert [t["id"] for t in mem["traders"]] == ["B"]
    assert all(m["kind"] != "limpet" for m in mem["mines"])  # Bob's limpets stay invisible
    assert {"kind": "armid", "owner": "personal", "count": 7} in mem["mines"]
    assert "stock" not in json.dumps(mem)
    adj = {a["id"]: a for a in build_observation(u, "A").adjacent}
    assert adj[busy]["fighter_count"] == 4321 and adj[busy]["occupants"] == ["B"]
    assert adj[busy]["mines"] == 7 and adj[busy]["scan_tier"] == "holo"
    assert busy not in u.players["A"].known_warps  # a holo scan does not explore (s10)


def test_hull_caps_and_scanner_shop(tw) -> None:
    assert K.scanner_room("missile_frigate") is None and K.scanner_room("colonial_transport") is None
    assert K.scanner_room("scout_marauder") == "density" and K.scanner_room("merchant_cruiser") == "holo"
    assert K.scanner_offer("scout_marauder", None) == {"density_scanner": 2_000}
    assert K.scanner_offer("merchant_cruiser", None) == {"density_scanner": 2_000, "holo_scanner": 25_000}
    assert K.scanner_offer("merchant_cruiser", "density") == {"holo_scanner": 25_000}
    assert K.scanner_offer("merchant_cruiser", "holo") == {}
    assert K.scanner_offer("missile_frigate", None) == {}
    u, home, busy, quiet = build_world()
    a = u.players["A"]
    u.sectors[a.sector_id].occupant_ids.remove("A")
    a.sector_id = K.STARDOCK_SECTOR
    u.sectors[K.STARDOCK_SECTOR].occupant_ids.append("A")
    eq = legal(u, "A", "buy_equip")
    assert eq["params"]["item"]["unit_price_by"]["holo_scanner"] == 25_000
    assert not act(u, "A", ActionKind.BUY_EQUIP, item="holo_scanner", qty=2).ok
    r = act(u, "A", ActionKind.BUY_EQUIP, item="density_scanner", qty=1)
    assert r.ok and a.ship.scanner == "density" and a.credits == 98_000
    assert not act(u, "A", ActionKind.BUY_EQUIP, item="density_scanner", qty=1).ok
    r = act(u, "A", ActionKind.BUY_EQUIP, item="holo_scanner", qty=1)
    assert r.ok and a.ship.scanner == "holo" and a.credits == 73_000
    assert "holo_scanner" not in legal(u, "A", "buy_equip")["params"]["item"]["unit_price_by"]
    a.ship.ship_class = ShipClass.MISSILE_FRIGATE
    a.ship.scanner = None
    r = act(u, "A", ActionKind.BUY_EQUIP, item="density_scanner", qty=1)
    assert not r.ok and "cannot carry" in r.error


def test_scanner_goes_with_the_ship(tw) -> None:
    from tw2k.engine.combat import _destroy_ship

    u, home, busy, quiet = build_world()
    a = u.players["A"]
    u.sectors[a.sector_id].occupant_ids.remove("A")
    a.sector_id = K.STARDOCK_SECTOR
    u.sectors[K.STARDOCK_SECTOR].occupant_ids.append("A")
    a.ship.scanner = "holo"
    a.credits = 10_000_000
    r = act(u, "A", ActionKind.BUY_SHIP, ship_class="cargotran")
    assert r.ok and a.ship.scanner is None
    a.ship.scanner = "density"
    _destroy_ship(u, "A", "test", None)
    assert a.ship.scanner is None


def test_no_experience_for_scans_or_probes(tw) -> None:
    u, home, busy, quiet = build_world()
    a = u.players["A"]
    _fit(u, "A", "holo")
    xp = a.experience
    assert act(u, "A", ActionKind.SCAN, tier="density").ok
    assert act(u, "A", ActionKind.SCAN, tier="holo").ok
    assert act(u, "A", ActionKind.PROBE, target=quiet).ok
    assert a.experience == xp


# --- ether probe ------------------------------------------------------------------------------

def test_probe_explores_its_route(tw) -> None:
    u, home, busy, quiet = build_world()
    a = u.players["A"]
    la = legal(u, "A", "probe")
    assert la["params"]["target"]["max_hops"] == 45
    u.sectors[busy].fighters = None
    far = max(u.sectors)
    r = act(u, "A", ActionKind.PROBE, target=far)
    assert r.ok and r.turns_spent == 1 and a.ship.ether_probes == 1
    assert far in a.known_warps and a.probe_log[far]["intel"]["warps_out"]
    ev = [e for e in u.events if e.kind.value == "probe"][-1]
    assert ev.payload["destroyed_at"] is None and ev.payload["route"][-1] == far
    # only the firer witnesses the probe event
    assert all(e.get("kind") != "probe" for e in build_observation(u, "C").recent_events)


def test_hostile_fighters_destroy_a_probe_friendly_ones_do_not(tw) -> None:
    u, home, busy, quiet = build_world()
    a = u.players["A"]
    r = act(u, "A", ActionKind.PROBE, target=busy)
    assert r.ok
    assert a.probe_log[busy]["intel"] == {"sector_id": busy, "probe_destroyed": True}
    assert busy not in a.known_warps
    ev = [e for e in u.events if e.kind.value == "probe"][-1]
    assert ev.payload["destroyed_at"] == busy and "destroyed" in ev.summary
    assert all(e.get("kind") != "probe" for e in build_observation(u, "B").recent_events)
    # Corporate fighters and mines let a corp mate's probe through. Personal ones do not.
    u.players["A"].corp_ticker = "XYZ"
    u.players["B"].corp_ticker = "XYZ"
    u.sectors[busy].fighters.corp_ticker = "XYZ"
    for md in u.sectors[busy].mines:
        md.corp_ticker = "XYZ"
    r = act(u, "A", ActionKind.PROBE, target=busy)
    assert r.ok and busy in a.known_warps and "warps_out" in a.probe_log[busy]["intel"]
    assert not act(u, "A", ActionKind.PROBE, target=busy).ok  # out of probes


def test_a_destroyed_probe_reports_nothing_beyond(tw) -> None:
    from tw2k.engine.scanners import probe_route

    u, home, busy, quiet = build_world()
    a = u.players["A"]
    beyond = next(t for t in sorted(u.sectors) if t not in (home, busy)
                  and probe_route(u, home, t)[:1] == [busy] and len(probe_route(u, home, t)) >= 2)
    route = probe_route(u, home, beyond)
    assert act(u, "A", ActionKind.PROBE, target=beyond).ok
    assert a.probe_log[busy]["intel"].get("probe_destroyed") is True
    assert not any(s in a.probe_log for s in route[1:])
    assert not any(s in a.known_warps for s in route[1:] if s != home)


# --- port reports -----------------------------------------------------------------------------

def _report(u, pid, sid):
    return next(k for k in build_observation(u, pid).known_ports if k["sector_id"] == sid)


def test_port_report_live_blocked_remembered(tw) -> None:
    u, home, busy, quiet = build_world()
    a = u.players["A"]
    port_sid = next(s for s in sorted(u.sectors) if u.sectors[s].port is not None and s not in K.FEDSPACE_SECTORS
                    and s != K.STARDOCK_SECTOR and s not in (home, busy))
    port = u.sectors[port_sid].port
    u.sectors[port_sid].fighters = None
    r = act(u, "A", ActionKind.PROBE, target=port_sid)
    assert r.ok and port_sid in a.known_warps
    rep = _report(u, "A", port_sid)
    assert rep["report"] == "live"
    c = next(iter(port.stock))
    port.stock[c].current = max(0, port.stock[c].current - 17)
    u.day += 1
    rep = _report(u, "A", port_sid)
    assert rep["report"] == "live" and rep["last_seen_day"] == u.day
    assert rep["stock"][c.value if hasattr(c, "value") else c]["current"] == port.stock[c].current
    u.sectors[port_sid].fighters = FighterDeployment(owner_id="B", count=1, mode=FighterMode.TOLL)
    assert _report(u, "A", port_sid)["report"] == "blocked"
    u.sectors[port_sid].fighters = FighterDeployment(owner_id="A", count=1, mode=FighterMode.TOLL)
    assert _report(u, "A", port_sid)["report"] == "live"
    del a.known_warps[port_sid]
    assert _report(u, "A", port_sid)["report"] == "remembered"


# --- the fog: diff observations with and without each device ---------------------------------

def _sentinel_world():
    u, home, busy, quiet = build_world(big=BIG)
    pl = Planet(id=9901, sector_id=quiet, name="Zyzzyxplanet", class_id=PlanetClass.M)
    u.planets[pl.id] = pl
    u.sectors[quiet].planet_ids.append(pl.id)
    names = {}
    for wid in u.sectors[home].warps:
        if u.sectors[wid].port is not None:
            u.sectors[wid].port.name = f"Qxport{wid}"
            names[wid] = u.sectors[wid].port.name
    u.players["B"].ship.name = "Shipsentinel"
    return u, home, busy, quiet, names


def _views(u, pid):
    obs = build_observation(u, pid)
    return json.dumps(obs.model_dump(mode="json"), default=str), format_observation(obs)


def _hits(u, pid, words):
    blob, text = _views(u, pid)
    return {w for w in words if w in blob or w in text}


@pytest.mark.parametrize("device", ["none", "density", "holo", "probe"])
def test_observation_only_carries_what_the_device_reveals(tw, device: str) -> None:
    u, home, busy, quiet, names = _sentinel_world()
    words = {str(BIG), "Zyzzyxplanet", "Shipsentinel", *names.values()}
    baseline = _hits(u, "A", words)
    assert baseline == set(), f"leak before any device: {baseline}"
    base_blob, _ = _views(u, "A")
    others = {pid: _views(u, pid) for pid in ("B", "C")}
    if device == "none":
        assert not act(u, "A", ActionKind.SCAN).ok
        assert not act(u, "A", ActionKind.SCAN, tier="holo").ok
        expect: set[str] = set()
    elif device == "density":
        _fit(u, "A", "density")
        assert act(u, "A", ActionKind.SCAN).ok
        expect = set()
        assert "density" in _views(u, "A")[0] and _views(u, "A")[0] != base_blob
    elif device == "holo":
        _fit(u, "A", "holo")
        assert act(u, "A", ActionKind.SCAN, tier="holo").ok
        expect = {str(BIG), "Zyzzyxplanet", "Shipsentinel", *names.values()}
    else:
        assert act(u, "A", ActionKind.PROBE, target=quiet).ok
        expect = {"Zyzzyxplanet"} | ({names[quiet]} if quiet in names else set())
    got = _hits(u, "A", words)
    assert got == expect, f"{device}: saw {got}, expected {expect}"
    assert "limpet" not in json.dumps([a for a in build_observation(u, "A").adjacent])
    # nobody else learns anything from A's device
    if device == "density":
        keys = {"id", "port", "known", "density", "warps", "navhaz", "anomaly", "scan_tier", "scan_day", "scan_tick"}
        assert all(set(a) <= keys for a in build_observation(u, "A").adjacent)
    for pid in ("B", "C"):
        assert _hits(u, pid, words) == _hits_from(others[pid], words), pid


def _hits_from(views, words):
    blob, text = views
    return {w for w in words if w in blob or w in text}


def test_a_pod_landing_reaches_only_the_pilot(tw) -> None:
    """1fe17f2: the pod's sector is on the pilot's map and nowhere in anyone else's observation."""
    from tw2k.engine.combat import _destroy_ship

    u, home, busy, quiet = build_world()
    _fit(u, "A", "holo")
    assert act(u, "A", ActionKind.SCAN, tier="holo").ok
    before = {a["id"]: a for a in build_observation(u, "A").adjacent}
    _destroy_ship(u, "B", "combat", killer_id="A", by_other=True)
    b = u.players["B"]
    assert b.ship.ship_class is ShipClass.ESCAPE_POD
    dest = b.sector_id
    assert dest != busy and dest in b.known_warps  # the pilot's map has it
    for pid in ("A", "C"):
        obs = build_observation(u, pid)
        for e in obs.recent_events:
            assert "pod_sector" not in (e.get("facts") or {}), e
            assert f"sector {dest}" not in (e.get("summary") or ""), e
        adj = {a["id"]: a for a in obs.adjacent}
        if dest in adj:
            assert "B" not in (adj[dest].get("occupants") or []), pid
    # A's holo reading of the busy sector is a memory, not a live view: Bob still shows there.
    after = {a["id"]: a for a in build_observation(u, "A").adjacent}
    assert after[busy]["occupants"] == before[busy]["occupants"] == ["B"]
    assert after[busy]["seen_tick"] == before[busy]["seen_tick"]


def test_entering_a_sector_shows_traders_and_hides_foreign_limpets(tw) -> None:
    u, home, busy, quiet = build_world()
    sec = build_observation(u, "A").sector
    assert [t["id"] for t in sec["traders"]] == ["C"]
    assert sec["mines"] == []  # Carol's limpets are not visible to Alice
    assert build_observation(u, "C").sector["mines"] == [{"owner": "personal", "kind": "limpet", "count": 5}]
    u.players["A"].corp_ticker = u.players["C"].corp_ticker = "QQQ"
    assert build_observation(u, "A").sector["mines"] == [{"owner": "personal", "kind": "limpet", "count": 5}]


def test_unscanned_adjacent_carries_no_live_contents(tw) -> None:
    u, home, busy, quiet = build_world()
    for a in build_observation(u, "A").adjacent:
        assert set(a) <= {"id", "port", "known"}, a


def test_warp_toll_not_shown_before_arrival(tw, monkeypatch) -> None:
    monkeypatch.setattr(K, "COMBAT_MODE", "tw2002", raising=False)
    u, home, busy, quiet = build_world()
    u.sectors[quiet].fighters = FighterDeployment(owner_id="B", count=50, mode=FighterMode.TOLL)
    warp = legal(u, "A", "warp")
    assert warp["params"].get("toll_due_by") == {}
    monkeypatch.setattr(K, "INFO_MODE", "legacy")
    assert legal(u, "A", "warp")["params"]["toll_due_by"] == {str(quiet): 250}  # today's build shows it


# --- seat brains ------------------------------------------------------------------------------

def _brains():
    spec = importlib.util.spec_from_file_location("sba", ROOT / "scripts" / "seat_brain_acceptance.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from tw2k.agents.seat_brain import SeatBrain

    return {"N1": mod.n1_brain, "N2": mod.n2_brain, "N3": SeatBrain}


@pytest.mark.parametrize("scanner", [None, "density", "holo"])
def test_seat_brains_stay_legal_with_and_without_scanners(tw, scanner) -> None:
    for name, make in _brains().items():
        u, home, busy, quiet = build_world()
        a = u.players["A"]
        a.ship.scanner = scanner
        brain = make()
        for _ in range(25):
            obs = build_observation(u, "A").model_dump(mode="json")
            choice = brain.decide(obs)
            assert validate_action(obs, choice) == [], (name, scanner, choice)
            res = apply_action(u, "A", Action(kind=choice["kind"], args=choice.get("args") or {}))
            assert res.ok, (name, scanner, choice, res.error)
            if a.turns_today >= a.turns_per_day:
                break

