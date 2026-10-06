"""Planted bugs for bots-use-rob-steal-hardware-v1.

Each test calls a SeatBrain helper that decide() uses, on a real observation
or on that observation with one field flipped. The numbers  -100, 6, 21, 99,
and the hull photon cap are written here, not imported and compared to themselves.
"""

from __future__ import annotations

import pytest

from tw2k.agents.prompts import SYSTEM_PROMPT
from tw2k.agents.seat_acceptance import validate_action
from tw2k.agents.seat_brain import STARDOCK, SeatBrain, SeatMemory, View
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.models import Commodity, MineType, Player, PortClass, Ship, ShipClass
from tw2k.engine.observation import build_observation


def _open(u, pid="A", sector=1, credits=20_000, ship=None):
    p = Player(id=pid, name=pid, credits=credits, ship=ship or Ship(), sector_id=sector)
    u.players[pid] = p
    sec = u.sectors[sector]
    if pid not in sec.occupant_ids:
        sec.occupant_ids.append(pid)
    p.known_sectors.add(sector)
    return p


def _trade_port(u) -> int:
    for sector in u.sectors.values():
        port = sector.port
        if port is None or sector.id == STARDOCK:
            continue
        if port.class_id in (PortClass.STARDOCK, PortClass.FEDERAL):
            continue
        return int(sector.id)
    raise AssertionError("no trading port")


def _view(u, pid, brain: SeatBrain) -> View:
    obs = build_observation(u, pid).model_dump(mode="json")
    if brain.mem is None:
        brain.mem = SeatMemory()
    return View(obs)


def _brain() -> SeatBrain:
    brain = SeatBrain()
    brain.mem = SeatMemory()
    return brain


def test_good_alignment_does_not_invent_rob() -> None:
    u = generate_universe(GameConfig(seed=4701, universe_size=40, enable_ferrengi=False, enable_planets=False))
    sid = _trade_port(u)
    p = _open(u, sector=sid, credits=5_000)
    p.alignment = 50
    p.experience = 500
    p.ship.cargo[Commodity.FUEL_ORE] = p.ship.holds
    u.sectors[sid].port.credits = 50_000
    brain = _brain()
    v = _view(u, "A", brain)
    assert v.obs["alignment"] == 50
    assert brain._crime_action(v) is None
    # Legal list flipped to yes. Alignment still blocks it.
    v.legal["rob"] = {"kind": "rob", "legal": True, "params": {"amount": {"max": 50_000}}}
    assert brain._crime_action(v) is None
    decided = brain.decide(build_observation(u, "A").model_dump(mode="json"))
    assert decided["kind"] != "rob"
    assert validate_action(build_observation(u, "A").model_dump(mode="json"), decided) == []


def test_rob_stays_inside_the_experience_cap() -> None:
    u = generate_universe(GameConfig(seed=4702, universe_size=40, enable_ferrengi=False, enable_planets=False))
    sid = _trade_port(u)
    p = _open(u, sector=sid, credits=5_000)
    p.alignment = -200
    p.experience = 10  # safe rob is 10 * 6 = 60
    p.ship.cargo[Commodity.FUEL_ORE] = p.ship.holds
    u.sectors[sid].port.credits = 80_000
    brain = _brain()
    v = _view(u, "A", brain)
    assert v.ok("rob"), v.reason("rob")
    action = brain._crime_action(v)
    assert action is not None and action["kind"] == "rob"
    assert action["args"]["amount"] == 60
    assert action["args"]["amount"] <= 60


def test_no_rob_at_stardock_or_class0() -> None:
    u = generate_universe(GameConfig(seed=4703, universe_size=40, enable_ferrengi=False, enable_planets=False))
    p = _open(u, sector=1, credits=5_000)
    p.alignment = -500
    p.experience = 1_000
    p.ship.cargo[Commodity.FUEL_ORE] = p.ship.holds
    brain = _brain()
    v = _view(u, "A", brain)
    assert brain._crime_action(v) is None
    v.obs["sector"]["class0_port"] = {"name": "Terra"}
    v.here = 40
    v.legal["rob"] = {"kind": "rob", "legal": True, "params": {"amount": {"max": 1000}}}
    assert brain._crime_action(v) is None


def test_no_second_rob_in_the_same_sector() -> None:
    u = generate_universe(GameConfig(seed=4704, universe_size=40, enable_ferrengi=False, enable_planets=False))
    sid = _trade_port(u)
    p = _open(u, sector=sid, credits=5_000)
    p.alignment = -200
    p.experience = 100
    p.ship.cargo[Commodity.FUEL_ORE] = p.ship.holds
    u.sectors[sid].port.credits = 20_000
    brain = _brain()
    v = _view(u, "A", brain)
    first = brain._crime_action(v)
    assert first is not None and first["kind"] == "rob"
    assert brain._crime_action(v) is None


def test_rich_hardware_does_not_buy_past_the_reserve() -> None:
    u = generate_universe(GameConfig(seed=4705, universe_size=30, enable_ferrengi=False, enable_planets=False))
    p = _open(u, sector=1, credits=250_000)
    brain = _brain()
    brain.working_capital = 10**9
    v = _view(u, "A", brain)
    assert brain._maybe_buy_rich_hardware(v) is None


def test_photon_refused_on_a_merchant_hull_and_off_the_lane() -> None:
    u = generate_universe(GameConfig(seed=4706, universe_size=30, enable_ferrengi=False, enable_planets=False))
    ship = Ship(ship_class=ShipClass.MERCHANT_CRUISER)
    ship.photon_missiles = 1
    _open(u, sector=1, credits=50_000, ship=ship)
    brain = _brain()
    v = _view(u, "A", brain)
    neighbor = int(u.sectors[1].warps[0])
    v.legal["photon_missile"] = {"kind": "photon_missile", "legal": True,
                                 "params": {"target": {"choices": [neighbor]}}}
    assert brain._photon_action(v, neighbor) is None
    assert brain._photon_action(v, neighbor + 999) is None
    assert brain._disruptor_action(v, neighbor + 999) is None
    v.ship["cloaks"] = 0
    v.legal["cloak"] = {"kind": "cloak", "legal": True, "params": {}}
    assert brain._cloak_action(v) is None


def test_no_armids_or_fighter_park_in_fedspace() -> None:
    u = generate_universe(GameConfig(seed=4707, universe_size=30, enable_ferrengi=False, enable_planets=False))
    ship = Ship()
    ship.mines[MineType.ARMID] = 5
    _open(u, sector=1, credits=50_000, ship=ship)
    brain = _brain()
    brain.mem.home_sector = 1
    v = _view(u, "A", brain)
    v.sector["is_fedspace"] = True
    v.legal["deploy_mines"] = {"kind": "deploy_mines", "legal": True,
                               "params": {"kind": {"choices": ["armid"]}, "qty": {"max_by": {"armid": 5}}}}
    v.legal["deploy_fighters"] = {"kind": "deploy_fighters", "legal": True,
                                  "params": {"qty": {"max": 200}}}
    assert brain._maybe_lay_armids(v) is None
    assert brain._lay_fighters(v, 99) is None


def test_navhaz_warp_prefers_the_clear_exit() -> None:
    u = generate_universe(GameConfig(seed=4708, universe_size=30, enable_ferrengi=False, enable_planets=False))
    _open(u, sector=1, credits=5_000)
    brain = _brain()
    v = _view(u, "A", brain)
    warps = [int(w) for w in u.sectors[1].warps]
    assert len(warps) >= 1
    extra = warps[0] + 1
    v.legal["warp"] = {"kind": "warp", "legal": True, "params": {"target": {"choices": [warps[0], extra]}}}
    v.obs["adjacent"] = [
        {"id": warps[0], "navhaz": 40},
        {"id": extra, "navhaz": 0},
    ]
    chosen = brain._legal_warps(v)
    assert extra in chosen
    assert warps[0] not in chosen


def test_psychic_reading_steps_the_next_sell() -> None:
    brain = _brain()
    brain._psychic_aboard = 1
    brain.mem.psychic_pct = 50.0
    brain.mem.psychic_commodity = "equipment"
    brain.mem.psychic_unit = 100
    out = brain._haggle_from_memory({"commodity": "equipment", "qty": 10, "side": "sell"})
    assert out["unit_price"] > 100
    assert out["unit_price"] <= 102  # one step, not a guess at the whole best price


def test_terra_load_not_buy_equip_and_not_when_full() -> None:
    u = generate_universe(GameConfig(seed=4710, universe_size=30, enable_ferrengi=False, enable_planets=True))
    p = _open(u, sector=1, credits=80_000)
    brain = _brain()
    v = _view(u, "A", brain)
    if v.ok("terra_colonists"):
        loaded = brain._load_colonists(v, 10, 0, "ferry")
        assert loaded is not None
        assert loaded["kind"] == "terra_colonists"
        assert loaded["args"]["mode"] == "take"
    v.cargo_free = 0
    assert brain._load_colonists(v, 10, 0, "ferry") is None
    assert p.ship.cargo_free >= 0


def test_prompt_and_hint_name_the_new_verbs() -> None:
    text = SYSTEM_PROMPT
    for needle in ("Ports:       rob steal", "terra_colonists", "NavHaz", "Zyrain", "99"):
        assert needle in text, needle
    u = generate_universe(GameConfig(seed=4711, universe_size=30, enable_ferrengi=False, enable_planets=False))
    _open(u, sector=1, credits=5_000)
    hint = build_observation(u, "A").action_hint
    assert "terra_colonists" in hint
    assert "99" in hint


def test_federal_ship_is_not_attacked() -> None:
    u = generate_universe(GameConfig(seed=4712, universe_size=30, enable_ferrengi=False, enable_planets=False))
    _open(u, sector=1, credits=5_000)
    brain = _brain()
    v = _view(u, "A", brain)
    v.legal["attack"] = {"kind": "attack", "legal": True, "params": {}}
    assert brain._ship_attack(v, "Zyrain") is None
    assert brain._ship_attack(v, "Nelson") is None
    assert brain._ship_attack(v, "Clausewitz") is None
    other = brain._ship_attack(v, "P2")
    assert other is not None and other["kind"] == "attack"


def test_one_beacon_and_no_atomic_with_colonists() -> None:
    u = generate_universe(GameConfig(seed=4713, universe_size=30, enable_ferrengi=False, enable_planets=False))
    ship = Ship()
    ship.marker_beacons = 1
    _open(u, sector=1, credits=5_000, ship=ship)
    brain = _brain()
    v = _view(u, "A", brain)
    v.legal["launch_beacon"] = {"kind": "launch_beacon", "legal": True, "params": {"beacon_here": False}}
    first = brain._beacon_action(v)
    assert first is not None and first["kind"] == "launch_beacon"
    assert brain._beacon_action(v) is None
    v.legal["deploy_atomic"] = {"kind": "deploy_atomic", "legal": True,
                                "params": {"planet_id": {"choices": [3]}, "colonists_alive": False}}
    v.colonists_aboard = 4
    assert brain._atomic_action(v) is None


def test_legacy_modes_do_not_rob_or_buy_hardware(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(K, "ROB_MODE", "legacy")
    monkeypatch.setattr(K, "HARDWARE_MODE", "legacy")
    monkeypatch.setattr(K, "CLASS0_MODE", "legacy")
    u = generate_universe(GameConfig(seed=4714, universe_size=30, enable_ferrengi=False, enable_planets=False))
    sid = _trade_port(u)
    p = _open(u, sector=sid, credits=400_000)
    p.alignment = -500
    p.experience = 500
    p.ship.cargo[Commodity.FUEL_ORE] = p.ship.holds
    u.sectors[sid].port.credits = 10_000
    brain = _brain()
    v = _view(u, "A", brain)
    assert brain._crime_action(v) is None
    v.here = STARDOCK
    assert brain._maybe_buy_rich_hardware(v) is None
    assert brain._hardware_on() is False
