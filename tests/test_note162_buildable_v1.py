"""NOTE 162. Five v3.11 switches, each off until its mode or V311_PROFILE is v311.

The string "1" does not turn a helper on. A normal game keeps the old catalog.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_tw2002_live_profile_v1 import HELPERS
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.fed import check_iss_repo_on_move
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, Corporation, FighterDeployment, Player, Ship, ShipClass

MODES = (
    ("FEDERATION_HALL_MODE", "federation_hall_live"),
    ("CORP_CARGO_TREASURY_MODE", "corp_cargo_treasury_live"),
    ("UG_NAME_MODE", "ug_name_live"),
    ("FED_HUNT_MODE", "fed_hunt_live"),
    ("CIM_MODE", "cim_live"),
)


def _world():
    universe = generate_universe(
        GameConfig(seed=4, universe_size=20, max_days=5, enable_planets=False, enable_ferrengi=False)
    )
    for pid, name in (("P1", "Ann"), ("P2", "Bo")):
        player = Player(id=pid, name=name, ship=Ship(name="Ship"), credits=5_000)
        player.sector_id = 1
        universe.players[pid] = player
        if pid not in universe.sectors[1].occupant_ids:
            universe.sectors[1].occupant_ids.append(pid)
    return universe


def _corp(universe):
    universe.corporations["ABC"] = Corporation(
        ticker="ABC", name="Able", ceo_id="P1", member_ids=["P1", "P2"], password="pw", formed_day=1,
    )
    universe.players["P1"].corp_ticker = "ABC"
    universe.players["P2"].corp_ticker = "ABC"


def _kinds(universe, pid="P1"):
    return {la.kind for la in legal_actions(universe, pid)}


def _legacy(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    for mode, _helper in MODES:
        monkeypatch.setattr(K, mode, "legacy")


def test_switches_default_legacy_and_one_does_not_flip(monkeypatch) -> None:
    _legacy(monkeypatch)
    for mode, helper in MODES:
        assert getattr(K, mode) == "legacy"
        assert getattr(K, helper)() is False
        monkeypatch.setattr(K, mode, "1")
        assert getattr(K, helper)() is False
        monkeypatch.setattr(K, mode, "legacy")
    assert K.UG_NAME_CHANGE is False
    for _mode, helper in MODES:
        assert helper not in HELPERS


def test_v311_profile_turns_each_helper_on_without_moving_the_flag(monkeypatch) -> None:
    _legacy(monkeypatch)
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    for mode, helper in MODES:
        assert getattr(K, mode) == "legacy"
        assert getattr(K, helper)() is True
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    for _mode, helper in MODES:
        assert getattr(K, helper)() is False


def test_federation_hall_is_absent_until_the_switch(monkeypatch) -> None:
    _legacy(monkeypatch)
    universe = _world()
    _corp(universe)
    assert "federation_hall" not in {la.kind for la in legal_actions(universe, "P1")}
    equip = next(la for la in legal_actions(universe, "P1") if la.kind == "buy_equip")
    assert "shop_screen" not in equip.params
    refused = apply_action(universe, "P1", Action(kind=ActionKind.FEDERATION_HALL, args={}))
    assert refused.ok is False

    monkeypatch.setattr(K, "FEDERATION_HALL_MODE", "v311")
    opened = legal_actions(universe, "P1")
    hall = next(la for la in opened if la.kind == "federation_hall")
    assert hall.legal is True
    assert hall.params["hall"]["listed"][0]["registration"] == "ABC"
    assert hall.params["hall"]["listed"][0]["members"][0]["ceo"] is True
    equip = next(la for la in opened if la.kind == "buy_equip")
    assert equip.params["shop_screen"]
    assert all("line" in row and "price" in row for row in equip.params["shop_screen"])
    result = apply_action(universe, "P1", Action(kind=ActionKind.FEDERATION_HALL, args={}))
    assert result.ok is True
    assert universe.events[-1].payload["ranked"][0]["registration"] == "ABC"


def test_cargo_and_treasury_fail_off_and_pass_on(monkeypatch) -> None:
    _legacy(monkeypatch)
    universe = _world()
    _corp(universe)
    universe.players["P1"].ship.cargo[Commodity.FUEL_ORE] = 4
    deposit = Action(kind=ActionKind.CORP_DEPOSIT, args={"amount": 100})
    cargo = Action(
        kind=ActionKind.CORP_TRANSFER,
        args={"target": "P2", "item": "fuel_ore", "qty": 2, "direction": "give"},
    )
    assert apply_action(universe, "P1", deposit).error == "unsupported action"
    assert apply_action(universe, "P1", cargo).error == "invalid transfer"
    assert universe.corporations["ABC"].treasury == 0
    assert universe.players["P2"].ship.cargo[Commodity.FUEL_ORE] == 0
    choices = next(la for la in legal_actions(universe, "P1") if la.kind == "corp_transfer")
    assert "fuel_ore" not in choices.params["item"]["choices"]

    monkeypatch.setattr(K, "CORP_CARGO_TREASURY_MODE", "v311")
    assert apply_action(universe, "P1", cargo).ok is True
    assert universe.players["P1"].ship.cargo[Commodity.FUEL_ORE] == 2
    assert universe.players["P2"].ship.cargo[Commodity.FUEL_ORE] == 2
    assert apply_action(universe, "P1", deposit).ok is True
    assert universe.corporations["ABC"].treasury == 100
    assert universe.players["P1"].credits == 4_900
    withdrawn = apply_action(universe, "P2", Action(kind=ActionKind.CORP_WITHDRAW, args={"amount": 40}))
    assert withdrawn.ok is False
    assert apply_action(universe, "P1", Action(kind=ActionKind.CORP_WITHDRAW, args={"amount": 40})).ok is True
    assert universe.corporations["ABC"].treasury == 60


def test_underground_name_fails_off_and_passes_for_a_total_unknown(monkeypatch) -> None:
    _legacy(monkeypatch)
    universe = _world()
    player = universe.players["P1"]
    player.alignment = 0
    player.experience = 1
    player.ug_entered_day = int(universe.day)
    player.ug_password_known = True
    assert "underground_rename" not in {la.kind for la in legal_actions(universe, "P1")}
    refused = apply_action(universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"name": "Nyx"}))
    assert refused.ok is False
    assert player.name == "Ann"

    monkeypatch.setattr(K, "UG_NAME_MODE", "v311")
    known = next(la for la in legal_actions(universe, "P1") if la.kind == "underground_rename")
    assert known.legal is True
    assert known.params["cost"] == 100
    assert apply_action(universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"name": "Nyx"})).ok is True
    assert player.name == "Nyx"
    assert player.credits == 4_900

    player.experience = 5
    player.ug_entered_day = int(universe.day)
    priced = apply_action(universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"name": "Hex"}))
    assert priced.ok is False
    assert priced.error == "the Underground has not priced this trader"
    assert player.name == "Nyx"
    assert K.UG_NAME_CHANGE is False


def test_a_federal_destroys_an_evil_ship_only_when_the_hunt_is_on(monkeypatch) -> None:
    _legacy(monkeypatch)
    universe = _world()
    player = universe.players["P1"]
    player.alignment = -40
    player.sector_id = 5
    if "P1" not in universe.sectors[5].occupant_ids:
        universe.sectors[5].occupant_ids.append("P1")
    fed = universe.federals[0]
    home = fed.sector_id
    fed.sector_id = 5
    check_iss_repo_on_move(universe, "P1")
    assert player.deaths == 0
    assert player.ship.ship_class != ShipClass.ESCAPE_POD

    monkeypatch.setattr(K, "FED_HUNT_MODE", "v311")
    fed.sector_id = home
    check_iss_repo_on_move(universe, "P1")
    assert player.deaths == 0
    fed.sector_id = 5
    check_iss_repo_on_move(universe, "P1")
    assert player.deaths == 1
    assert player.ship.ship_class == ShipClass.ESCAPE_POD


def test_cim_is_absent_until_the_switch_and_hides_a_blocked_port(monkeypatch) -> None:
    _legacy(monkeypatch)
    universe = _world()
    player = universe.players["P1"]
    player.known_sectors.add(2)
    player.known_warps[2] = [1]
    player.known_ports[2] = {"code": "BBS", "class": "2"}
    universe.sectors[2].fighters = FighterDeployment(owner_id="P9", count=4)
    assert "cim" not in {la.kind for la in legal_actions(universe, "P1")}
    assert apply_action(universe, "P1", Action(kind=ActionKind.CIM, args={"query": "I"})).ok is False

    monkeypatch.setattr(K, "CIM_MODE", "v311")
    assert next(la for la in legal_actions(universe, "P1") if la.kind == "cim").legal is True
    assert apply_action(universe, "P1", Action(kind=ActionKind.CIM, args={"query": "I"})).ok is True
    assert universe.events[-1].payload["sectors"] == [{"sector_id": 2, "warps": [1]}]
    assert apply_action(universe, "P1", Action(kind=ActionKind.CIM, args={"query": "R"})).ok is True
    port = universe.events[-1].payload["ports"][0]
    assert port == {"sector_id": 2, "info": "unavailable"}
    assert "count" not in port and "owner" not in port
    universe.sectors[2].fighters = None
    assert apply_action(universe, "P1", Action(kind=ActionKind.CIM, args={"query": "R"})).ok is True
    assert universe.events[-1].payload["ports"][0]["port"] == "BBS"
    routed = apply_action(universe, "P1", Action(kind=ActionKind.CIM, args={"query": "F", "target": 1}))
    assert routed.ok is True
    assert universe.events[-1].payload["route"]["ok"] is True
    assert apply_action(universe, "P1", Action(kind=ActionKind.CIM, args={"query": "Q"})).ok is True
