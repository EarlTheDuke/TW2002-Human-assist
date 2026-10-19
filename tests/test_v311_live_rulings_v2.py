"""NOTE 90 v311-live-rulings-v2. Switches stay legacy until the profile is on.

Ship odds and alien FedSpace are written up in RULINGS_v311.md and left in
the code they already have. Autopilot port stops and Genesis names are new.
"""
from pathlib import Path

from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.combat import _resolve_ship_attack_tw2002
from tw2k.engine.models import Player, Port, PortClass, ShipClass
from tw2k.engine.runner import _bfs_path, apply_action

ROOT = Path(__file__).resolve().parents[1]


def _seat(u, pid, sid):
    p = Player(id=pid, name=pid, agent_kind="external", sector_id=sid, credits=50_000,
               turns_per_day=200, turns_today=0)
    p.ship.fighters = 50
    u.players[pid] = p
    u.sectors[sid].occupant_ids.append(pid)
    return p


def _course(u):
    start = 11 if 11 in u.sectors else sorted(u.sectors)[0]
    for target in sorted(u.sectors):
        if target == start:
            continue
        path = _bfs_path(u, start, target)
        if path and len(path) >= 2:
            mid = int(path[0])
            if u.sectors[mid].port is None:
                u.sectors[mid].port = Port(class_id=PortClass.CLASS_3_SBB, name="Waystation")
            return start, target, mid
    raise AssertionError("no two-hop course")


def test_the_tax_file_uses_the_helper_reserved_ports() -> None:
    text = (ROOT / "tests" / "test_cockpit_tax_wording_v1.py").read_text(encoding="utf-8")
    assert "range(8031, 8120)" not in text
    assert "RESERVED_TEST_PORTS" in text


def test_two_cruisers_trade_one_for_one_and_a_scout_does_not() -> None:
    """Bible chart already drives the exchange. A Merchant Cruiser is 1.0, so
    cruiser versus cruiser is 1:1. A Scout Marauder is 2.0 and is not."""
    assert K.combat_hull("merchant_cruiser") == (1.0, 750)
    assert K.combat_hull("scout_marauder")[0] == 2.0
    cfg = GameConfig(seed=90, universe_size=30, max_days=2, turns_per_day=20,
                     enable_ferrengi=False, enable_planets=False)
    u = generate_universe(cfg)
    a = _seat(u, "P1", 1)
    b = _seat(u, "P2", 1)
    a.ship.ship_class = ShipClass.SCOUT_MARAUDER
    a.ship.fighters = 30
    b.ship.fighters = 40
    b.ship.shields = 0
    _resolve_ship_attack_tw2002(u, "P1", b, 20)
    assert b.ship.fighters == 0  # 20 sent at 2:1 clears 40
    assert a.ship.fighters == 10


def test_express_stops_at_a_port_only_when_the_cockpit_asks() -> None:
    cfg = GameConfig(seed=91, universe_size=60, max_days=2, turns_per_day=200,
                     enable_ferrengi=False, enable_planets=False)
    u = generate_universe(cfg)
    start, target, mid = _course(u)
    p = _seat(u, "P1", start)
    saved = K.V311_PROFILE
    try:
        def _back() -> None:
            if p.sector_id != start:
                u.sectors[p.sector_id].occupant_ids.remove(p.id)
                p.sector_id = start
                u.sectors[start].occupant_ids.append(p.id)
            p.turns_today = 0

        off = apply_action(u, "P1", Action(kind=ActionKind.PLOT_COURSE, args={
            "target": target, "execute": True, "stop_at_ports": True}))
        assert off.ok and p.sector_id == target
        _back()
        K.V311_PROFILE = "v311"
        flown = apply_action(u, "P1", Action(kind=ActionKind.PLOT_COURSE, args={
            "target": target, "execute": True}))
        assert flown.ok and p.sector_id == target
        _back()
        paused = apply_action(u, "P1", Action(kind=ActionKind.PLOT_COURSE, args={
            "target": target, "execute": True, "stop_at_ports": True}))
        assert paused.ok and p.sector_id == mid
        ev = next(e for e in reversed(u.events) if e.kind.value == "autopilot" and (e.payload or {}).get("stopped") == "port")
        assert ev.payload["hops_done"] >= 1
    finally:
        K.V311_PROFILE = saved


def _genesis_sector(u):
    for sid in sorted(u.sectors):
        if sid in K.FEDSPACE_SECTORS:
            continue
        if len(_bfs_path(u, K.STARDOCK_SECTOR, sid)) >= K.GENESIS_MIN_HOPS_FROM_STARDOCK:
            if u.sectors[sid].planet_ids:
                continue
            return sid
    raise AssertionError("no genesis sector")


def test_a_typed_genesis_name_is_kept_only_under_the_profile() -> None:
    cfg = GameConfig(seed=92, universe_size=80, max_days=2, turns_per_day=50,
                     enable_ferrengi=False, enable_planets=True)
    u = generate_universe(cfg)
    sid = _genesis_sector(u)
    p = _seat(u, "P1", sid)
    p.ship.genesis = 1
    saved = K.V311_PROFILE
    try:
        off = apply_action(u, "P1", Action(kind=ActionKind.DEPLOY_GENESIS, args={"name": "Genesis One"}))
        assert off.ok
        named = [pl for pl in u.planets.values() if pl.sector_id == sid]
        assert named and named[-1].name != "Genesis One"
        named[-1].sector_id = -1
        u.sectors[sid].planet_ids.clear()
        p.ship.genesis = 1
        K.V311_PROFILE = "v311"
        on = apply_action(u, "P1", Action(kind=ActionKind.DEPLOY_GENESIS, args={"name": "Genesis One"}))
        assert on.ok
        again = [pl for pl in u.planets.values() if pl.sector_id == sid]
        assert again[-1].name == "Genesis One"
    finally:
        K.V311_PROFILE = saved
