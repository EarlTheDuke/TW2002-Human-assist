"""QC slice 55 (port-upgrade-build-v1): rows the first pass did not pin."""

from __future__ import annotations

from tests.test_port_upgrade_build import EQ, _build, _kinds, _planet, _port, _up, _world
from tw2k.engine import Action, ActionKind, apply_action, tick_day
from tw2k.engine import constants as K
from tw2k.engine.models import EventKind, Player, Ship
from tw2k.engine.observation import build_observation, event_facts
from tw2k.engine.port_build import port_count


def _events(u, kind):
    return [e for e in u.events if e.kind == kind]


def _rival(u, pid="B", sector=3):
    rival = Player(id=pid, name="Bo", ship=Ship(), credits=1000)
    rival.sector_id = sector
    u.players[pid] = rival
    u.sectors[sector].occupant_ids.append(pid)
    return rival


def test_upgrade_facts_carry_cost_capacity_exp_and_align():
    u, _ = _world()
    _port(u)
    assert _up(u, "equipment", 10).ok
    ev = _events(u, EventKind.PORT_UPGRADED)[-1]
    assert event_facts(ev) == {"commodity": "equipment", "units": 10, "cost": 9000, "capacity": 3100,
                               "exp": 3, "align": 1}


def test_build_facts_match_the_payloads():
    u, _ = _world()
    _planet(u, ore=100, org=100, eq=100)
    assert _build(u, "SSS", name="Bob's Dock").ok
    ordered = event_facts(_events(u, EventKind.PORT_BUILD_ORDERED)[-1])
    assert ordered == {"port_class": "SSS", "planet_id": 7, "days": 2, "cost": 30000, "name": "Bob's Dock"}
    tick_day(u)
    assert event_facts(_events(u, EventKind.PORT_BUILD_PROGRESS)[-1]) == {"days_left": 1, "days_total": 2}
    tick_day(u)
    assert event_facts(_events(u, EventKind.PORT_BUILT)[-1]) == {"port_class": "SSS", "name": "Bob's Dock"}


def test_port_built_names_no_builder_and_gives_rivals_no_last_seen():
    u, player = _world()
    rival = _rival(u)
    _planet(u, ore=100, org=100, eq=100)
    assert _build(u, "SSS").ok
    # the builder leaves before the port opens
    u.sectors[12].occupant_ids.remove("A")
    player.sector_id = 3
    u.sectors[3].occupant_ids.append("A")
    tick_day(u)
    tick_day(u)
    built = _events(u, EventKind.PORT_BUILT)[-1]
    assert built.actor_id is None
    obs = build_observation(u, rival.id).model_dump(mode="json")
    seen = [e for e in obs["recent_events"] if e["kind"] == "port_built"]
    assert seen and seen[-1]["actor_id"] is None and "exp" not in seen[-1].get("facts", {})
    row = next(r for r in obs["rivals"] if r["id"] == "A")
    assert row.get("last_seen_sector") != 12
    for kind in ("port_build_ordered", "port_build_progress"):
        assert not [e for e in obs["recent_events"] if e["kind"] == kind]


def test_units_must_be_whole():
    u, player = _world()
    port = _port(u)
    bad = _up(u, "equipment", 2.5)
    assert not bad.ok and "whole number" in (bad.error or "")
    assert port.stock[EQ].maximum == 3000 and player.credits == 5_000_000
    assert _up(u, "equipment", 2.0).ok
    assert port.stock[EQ].maximum == 3020


def test_a_radiating_sector_holds_its_slot_until_cleared():
    u, _ = _world()
    _planet(u, ore=500, org=500, eq=500)
    other = next(s for s in sorted(u.sectors) if s not in K.FEDSPACE_SECTORS and s != 12 and u.sectors[s].port)
    u.port_cap = port_count(u)  # full
    u.sectors[other].port = None
    u.sectors[other].port_destroyed_day = u.day
    assert port_count(u) == u.port_cap
    assert _kinds(u)["port_build"].reason == "the universe cannot support another port"
    assert _kinds(u)["port_build"].params["ports_free"] == 0
    u.day += K.PORT_BUILD_RADIATION_DAYS
    assert _kinds(u)["port_build"].params["ports_free"] == 1
    assert _build(u, "SSS").ok


def test_trade_upgrade_rob_and_planet_trade_refused_while_building():
    u, _ = _world()
    _planet(u, ore=100, org=100, eq=100)
    assert _build(u, "BBB").ok
    for kind in ("trade", "port_upgrade", "planet_trade", "rob", "steal"):
        row = _kinds(u).get(kind)
        assert row is None or not row.legal, kind
    for kind, args in ((ActionKind.ROB, {"credits": 10}), (ActionKind.STEAL, {"commodity": "equipment", "qty": 1})):
        assert not apply_action(u, "A", Action(kind=kind, args=args)).ok
