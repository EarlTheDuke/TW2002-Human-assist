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


# ---- plant follow-ups (QC slice 55): each test below failed against one planted bug ----------------


def test_build_refused_where_a_port_stands():
    u, player = _world()
    _port(u)
    _planet(u, ore=100, org=100, eq=100)
    row = _kinds(u)["port_build"]
    assert not row.legal and row.reason == "this sector already has a port"
    res = _build(u, "SSS")
    assert not res.ok and res.error == "this sector already has a port"
    assert player.credits == 5_000_000


def test_bot_never_upgrades_a_selling_commodity_or_fuel_ore():
    from tw2k.agents.seat_brain import SeatBrain
    from tw2k.engine.models import PortClass
    u, player = _world()
    _port(u, cls=PortClass.CLASS_1_BSS, current=0, maximum=100)  # BSS: buys fuel, sells organics/equipment
    _planet(u, ore=6000, org=6000, eq=6000)
    player.credits = 400_000
    obs = build_observation(u, "A").model_dump(mode="json")
    assert SeatBrain().decide(obs)["kind"] != "port_upgrade"


def test_bot_keeps_the_upgrade_reserve():
    from tw2k.agents.seat_brain import SeatBrain
    u, player = _world()
    _port(u, current=0, maximum=100)
    _planet(u, org=6000)
    player.credits = K.BOT_PORT_UPGRADE_RESERVE + 3 * K.PORT_UPGRADE_UNIT_COST["organics"]
    act = SeatBrain().decide(build_observation(u, "A").model_dump(mode="json"))
    assert act["kind"] != "port_upgrade" or act["args"]["units"] <= 3


def test_a_rival_in_the_sector_does_not_see_the_upgrade():
    u, _ = _world()
    _port(u)
    rival = _rival(u, sector=12)
    assert _up(u, "equipment", 5).ok
    obs = build_observation(u, rival.id).model_dump(mode="json")
    assert not [e for e in obs["recent_events"] if e["kind"] == "port_upgraded"]
    mine = build_observation(u, "A").model_dump(mode="json")
    assert [e for e in mine["recent_events"] if e["kind"] == "port_upgraded"]


def test_build_params_never_list_a_rival_planet_and_name_only_ports_free():
    u, _ = _world()
    _planet(u, owner="B", ore=500, org=500, eq=500)
    params = _kinds(u)["port_build"].params
    assert params["planets"] == []
    assert set(params) == {"classes", "planets", "ports_free", "turn_cost"}


def test_built_buy_side_opens_with_full_room():
    u, _ = _world()
    _planet(u, ore=2000, org=2000, eq=2000)
    assert _build(u, "BBB").ok
    for _ in range(K.PORT_BUILD_DAYS["BBB"]):
        tick_day(u)
    port = u.sectors[12].port
    assert port.construction is None
    assert all(row.current == 0 and row.maximum == 100 for row in port.stock.values())


def test_build_refused_in_fedspace():
    u, player = _world()
    sid = next(s for s in sorted(K.FEDSPACE_SECTORS) if s != K.STARDOCK_SECTOR and s in u.sectors)
    u.sectors[12].occupant_ids.remove("A")
    player.sector_id = sid
    u.sectors[sid].occupant_ids.append("A")
    u.sectors[sid].port = None
    _planet(u, ore=100, org=100, eq=100, sector=sid)
    assert _kinds(u)["port_build"].reason == "FedSpace cannot hold a built port"
    assert not _build(u, "SSS").ok


def test_build_needs_the_credits_and_costs_one_turn():
    u, player = _world()
    _planet(u, ore=100, org=100, eq=100)
    player.credits = K.PORT_BUILD_COST["SSS"] - 1
    poor = _build(u, "SSS")
    assert not poor.ok and player.credits == K.PORT_BUILD_COST["SSS"] - 1 and u.sectors[12].port is None
    player.credits = K.PORT_BUILD_COST["SSS"]
    turns = player.turns_today
    res = _build(u, "SSS")
    assert res.ok and res.turns_spent == 1 and player.turns_today == turns + 1 and player.credits == 0


def test_construction_stalls_when_the_planet_leaves():
    u, _ = _world()
    pl = _planet(u, ore=100, org=100, eq=100)
    assert _build(u, "SSS").ok
    u.sectors[12].planet_ids.remove(7)
    pl.sector_id = 3
    u.sectors[3].planet_ids.append(7)
    tick_day(u)
    assert u.sectors[12].port.construction["days_left"] == 2
    assert pl.stockpile[EQ] == 100


def test_rob_and_steal_not_offered_while_building(monkeypatch):
    u, player = _world()
    player.alignment = -10_000
    player.experience = 10_000
    port = _port(u)
    port.credits = 50_000
    open_rows = {k: _kinds(u)[k].legal for k in ("rob", "steal")}
    u.sectors[12].port = None
    _planet(u, ore=100, org=100, eq=100)
    assert _build(u, "SSS").ok
    player.turns_today = 0
    building = _kinds(u)
    assert any(open_rows.values())  # the guard below is meaningful
    for k in ("rob", "steal", "trade"):
        assert not building[k].legal, k


def test_sector_view_of_a_construction_port_shows_no_builder():
    u, _ = _world()
    rival = _rival(u, sector=12)
    _planet(u, ore=100, org=100, eq=100)
    assert _build(u, "SSS").ok
    port = build_observation(u, rival.id).model_dump(mode="json")["sector"]["port"]
    assert set(port["under_construction"]) == {"class", "days_left", "days_total"}


def test_specials_show_not_upgradable():
    from tw2k.engine.models import PortClass
    u, _ = _world()
    for cls, want in ((PortClass.STARDOCK, False), (PortClass.FEDERAL, False), (PortClass.CLASS_6_BBS, True)):
        _port(u, cls=cls)
        assert build_observation(u, "A").model_dump(mode="json")["sector"]["port"]["upgradable"] is want


def test_port_upgrade_releases_a_tow(monkeypatch):
    from tw2k.engine.fleet import _new_ship_id
    from tw2k.engine.models import ParkedShip, ShipClass
    monkeypatch.setattr(K, "TOW_MODE", "tw2002")
    monkeypatch.setattr(K, "FLEET_MODE", "tw2002")
    u, player = _world()
    _port(u)
    player.ship.ship_class = ShipClass.MERCHANT_CRUISER
    ship = Ship(ship_class=ShipClass.MERCHANT_FREIGHTER, name="spare", holds=65, fighters=0)
    fid = _new_ship_id(u)
    ship.fleet_id = fid
    u.parked_ships[fid] = ParkedShip(id=fid, owner_id="A", sector_id=12, ship=ship, parked_day=u.day)
    assert apply_action(u, "A", Action(kind=ActionKind.TOW_ENGAGE, args={"target": f"ship:{fid}"})).ok
    assert player.ship.tow_lock is not None
    assert _up(u, "equipment", 1).ok
    assert player.ship.tow_lock is None


def test_upgrade_and_build_wait_for_a_fighter_challenge(monkeypatch):
    import tw2k.engine.combat as C
    u, _ = _world()
    _port(u)
    assert _kinds(u)["port_upgrade"].legal
    monkeypatch.setattr(C, "live_challenge", lambda *a, **k: {"group": "x"})
    row = _kinds(u)["port_upgrade"]
    assert not row.legal and "answer the fighters" in (row.reason or "")


def test_flee_penalty_lands_on_a_port_upgrade():
    u, player = _world()
    _port(u)
    player.flee_penalty = True
    res = _up(u, "equipment", 1)
    assert res.ok and res.turns_spent == 1 + K.FLEE_PENALTY_TURNS


def test_build_name_length_limit():
    u, _ = _world()
    _planet(u, ore=100, org=100, eq=100)
    assert not _build(u, "SSS", name="x" * (K.PORT_BUILD_NAME_MAX + 1)).ok
    assert _build(u, "SSS", name="x" * K.PORT_BUILD_NAME_MAX).ok


def _detonate(u, sid):
    from tw2k.engine.models import MineType
    from tw2k.engine.runner import _handle_atomic_detonation
    player = u.players["A"]
    player.ship.mines[MineType.ATOMIC] = 3
    for row in u.sectors[sid].port.stock.values():
        row.current = 0
    return _handle_atomic_detonation(u, "A", 3, u.sectors[sid], 0)


def test_detonation_starts_radiation_only_in_tw2002(monkeypatch):
    u, _ = _world()
    _port(u)
    _planet(u, ore=100, org=100, eq=100)
    _detonate(u, 12)
    assert u.sectors[12].port is None and u.sectors[12].port_destroyed_day == u.day
    assert _kinds(u)["port_build"].reason == "this sector is still radiating"
    u.day += K.PORT_BUILD_RADIATION_DAYS
    assert _build(u, "SSS").ok
    monkeypatch.setattr(K, "PORT_UPGRADE_MODE", "legacy")
    v, _ = _world()
    _port(v)
    _detonate(v, 12)
    assert v.sectors[12].port is None and v.sectors[12].port_destroyed_day is None


def test_legacy_dump_has_none_of_the_new_fields(monkeypatch):
    import json
    monkeypatch.setattr(K, "PORT_UPGRADE_MODE", "legacy")
    u, _ = _world()
    _port(u)
    _detonate(u, 12)
    dump = json.loads(u.model_dump_json())
    assert "port_cap" not in dump
    assert all("port_destroyed_day" not in s for s in dump["sectors"].values())
    assert all("port_upgrade_carry" not in p for p in dump["players"].values())
    assert all("construction" not in (s.get("port") or {}) for s in dump["sectors"].values())


# ---- bot starter upgrade (QC slice 55 tuning) ----------------------------------------------------------


def _starter_obs(u, credits):
    u.players["A"].credits = credits
    return build_observation(u, "A").model_dump(mode="json")


def test_bot_starter_upgrade_fires_once_per_port_when_rich(monkeypatch):
    from tw2k.agents.seat_brain import SeatBrain
    u, _ = _world()
    _port(u, current=1000, maximum=3000)  # BBS buys organics; room 2,000 dwarfs the 40-unit lot
    _planet(u, org=40)
    brain = SeatBrain()
    act = brain.decide(_starter_obs(u, K.BOT_PORT_UPGRADE_STARTER_CREDITS))
    assert act["kind"] == "port_upgrade"
    assert act["args"] == {"commodity": "organics", "units": K.BOT_PORT_UPGRADE_STARTER_UNITS}
    assert apply_action(u, "A", Action(kind=ActionKind.PORT_UPGRADE, args=act["args"])).ok
    again = brain.decide(_starter_obs(u, K.BOT_PORT_UPGRADE_STARTER_CREDITS * 2))
    assert again["kind"] != "port_upgrade"


def test_bot_starter_upgrade_needs_the_credits_a_stocked_planet_and_the_mode(monkeypatch):
    from tw2k.agents.seat_brain import SeatBrain
    from tw2k.engine.models import Commodity
    u, _ = _world()
    _port(u, current=1000, maximum=3000)
    pl = _planet(u, org=40)
    assert SeatBrain().decide(_starter_obs(u, K.BOT_PORT_UPGRADE_STARTER_CREDITS - 1))["kind"] != "port_upgrade"
    pl.stockpile[Commodity.ORGANICS] = 0
    assert SeatBrain().decide(_starter_obs(u, 10**7))["kind"] != "port_upgrade"
    pl.stockpile[Commodity.ORGANICS] = 40
    assert SeatBrain().decide(_starter_obs(u, 10**7))["kind"] == "port_upgrade"
    monkeypatch.setattr(K, "BOT_PORT_UPGRADE_STARTER_UNITS", 0)
    assert SeatBrain().decide(_starter_obs(u, 10**7))["kind"] != "port_upgrade"
    monkeypatch.setattr(K, "BOT_PORT_UPGRADE_STARTER_UNITS", 5)
    monkeypatch.setattr(K, "PORT_UPGRADE_MODE", "legacy")
    assert SeatBrain().decide(_starter_obs(u, 10**7))["kind"] != "port_upgrade"


def test_a_broke_trader_is_told_it_is_the_credits():
    u, player = _world()
    port = _port(u)
    player.credits = 100
    assert _kinds(u)["port_upgrade"].reason == "not enough credits for one upgrade unit"
    player.credits = 10**7
    for row in port.stock.values():
        row.maximum = K.PORT_UPGRADE_MAX_HOLDS
    assert _kinds(u)["port_upgrade"].reason == "this port cannot take another upgrade unit"
