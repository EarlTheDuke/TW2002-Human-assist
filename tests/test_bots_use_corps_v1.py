"""bots-use-corps-v1 engine gates: FlagShip purchase, FlagShip join, planet id."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, generate_universe
from tw2k.engine.models import Player, Ship, ShipClass
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action


def _u():
    return generate_universe(GameConfig(seed=59, universe_size=80, max_days=3, enable_ferrengi=False))


def _seat(u, pid, sector=1, hull=ShipClass.MERCHANT_CRUISER, credits=50_000):
    player = Player(
        id=pid, name=pid, sector_id=sector, credits=credits, alignment=100,
        ship=Ship(ship_class=hull, fighters=10),
    )
    u.players[pid] = player
    u.sectors[sector].occupant_ids.append(pid)
    return player


def test_bc1_legacy_reads_the_policy_as_off(monkeypatch):
    assert K.corp_bots_on()
    assert K.bot_corp_policy() == "off"
    monkeypatch.setattr(K, "BOT_CORP_POLICY", "pair")
    assert K.bot_corp_policy() == "pair"
    monkeypatch.setattr(K, "CORP_BOTS_MODE", "legacy")
    assert K.bot_corp_policy() == "off"


def test_bc24_only_the_ceo_buys_a_flagship():
    u = _u()
    _seat(u, "A")
    _seat(u, "B")
    assert apply_action(u, "A", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "ZZ", "name": "Zed"})).ok
    assert apply_action(u, "A", Action(kind=ActionKind.CORP_SET_PASSWORD, args={"password": "secret"})).ok
    assert apply_action(u, "A", Action(kind=ActionKind.CORP_INVITE, args={"target": "B"})).ok
    assert apply_action(u, "B", Action(kind=ActionKind.CORP_JOIN, args={"ticker": "ZZ", "password": "secret"})).ok
    refused = apply_action(u, "B", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "corporate_flagship"}))
    assert not refused.ok and refused.error == "only a C.E.O. may buy a Corporate FlagShip"
    ceo = apply_action(u, "A", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "corporate_flagship"}))
    assert ceo.error != "only a C.E.O. may buy a Corporate FlagShip"
    spare = apply_action(u, "B", Action(
        kind=ActionKind.BUY_SHIP, args={"ship_class": "corporate_flagship", "trade_in": False}))
    assert not spare.ok and spare.error == "only a C.E.O. may buy a Corporate FlagShip"


def test_bc25_a_flagship_pilot_cannot_join_and_may_create(monkeypatch):
    u = _u()
    _seat(u, "A")
    pilot = _seat(u, "B", hull=ShipClass.CORPORATE_FLAGSHIP)
    assert apply_action(u, "A", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "ZZ", "name": "Zed"})).ok
    assert apply_action(u, "A", Action(kind=ActionKind.CORP_SET_PASSWORD, args={"password": "secret"})).ok
    invited = apply_action(u, "A", Action(kind=ActionKind.CORP_INVITE, args={"target": "B"}))
    assert not invited.ok and invited.error == "a FlagShip pilot cannot join a corporation"
    assert apply_action(u, "B", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "YY", "name": "Yew"})).ok
    assert pilot.corp_ticker == "YY"
    monkeypatch.setattr(K, "CORP_BOTS_MODE", "legacy")
    u2 = _u()
    _seat(u2, "A")
    _seat(u2, "B", hull=ShipClass.CORPORATE_FLAGSHIP)
    assert apply_action(u2, "A", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "ZZ", "name": "Zed"})).ok
    assert apply_action(u2, "A", Action(kind=ActionKind.CORP_SET_PASSWORD, args={"password": "secret"})).ok
    assert apply_action(u2, "A", Action(kind=ActionKind.CORP_INVITE, args={"target": "B"})).ok


def test_bc2_consecutive_pairs_and_password_stay_out_of_memory():
    from tw2k.agents.corp_brain import clear, configure, partner_of, password_for, role_of, ticker_for
    from tw2k.agents.seat_brain import SeatMemory
    configure(["P1", "P2", "P3", "P4", "P5"], seed=31)
    try:
        assert role_of("P1") == "ceo" and partner_of("P1") == "P2"
        assert role_of("P3") == "ceo" and partner_of("P3") == "P4"
        assert partner_of("P5") is None
        assert ticker_for("Ann", "P1", set()) == "ANN"
        assert ticker_for("Ann", "P1", {"ANN"}) == "P01"
        secret = password_for("ANN")
        assert len(secret) == 6 and secret not in SeatMemory().dump()
    finally:
        clear()


def test_bc12_credit_give_covers_a_real_shortfall_only():
    from tw2k.agents.corp_brain import credit_give, tax_give
    assert credit_give(80_000, 0, 10_000, 40_000, reserve=20_000, pad=1_000, minimum=5_000) == 31_000
    assert credit_give(80_000, 0, 39_500, 40_000, reserve=20_000, pad=1_000, minimum=5_000) is None
    assert credit_give(30_000, 25_000, 10_000, 40_000, reserve=20_000, pad=1_000, minimum=5_000) is None
    assert tax_give(120_000, 100_000, minimum=5_000) == 20_000
    assert tax_give(104_000, 100_000, minimum=5_000) is None
    from tw2k.agents.corp_brain import gear_take
    assert gear_take(100, 50, 30) == 50
    assert gear_take(10, 50, 30) == 7
    assert gear_take(2, 50, 30) == 1
    assert gear_take(1, 50, 30) is None


def test_bc10_the_partner_adopts_the_corp_planet(monkeypatch):
    from tw2k.agents.corp_brain import clear, configure
    from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View
    monkeypatch.setattr(K, "BOT_CORP_POLICY", "pair")
    configure(["P1", "P2"], seed=1)
    try:
        brain = SeatBrain()
        brain.mem = SeatMemory()
        obs = {
            "self_id": "P2", "day": 1, "credits": 0,
            "sector": {"id": 1}, "ship": {}, "legal_actions": [],
            "owned_planets": [{"id": 3, "sector_id": 12, "citadel_level": 2, "origin": "genesis", "colonists": {}}],
            "corp": {"ceo_id": "P1", "members": [{"id": "P1", "alive": True}],
                     "planets": [{"planet_id": 9, "sector_id": 40, "citadel_level": 1, "population": 10}]},
        }
        brain._refresh_home(View(obs))
        assert brain.mem.home_planet == 9
        assert brain.mem.home_sector == 40
    finally:
        clear()


def test_bc12_credit_hand_off_is_the_shortfall_plus_pad():
    from tw2k.agents.corp_brain import credit_give, fighter_take, tax_give
    assert credit_give(200_000, 0, 21_300, 61_300, reserve=20_000, pad=1_000, minimum=5_000) == 41_000
    assert credit_give(80_000, 0, 70_000, 61_300, reserve=20_000, pad=1_000, minimum=5_000) is None
    assert tax_give(150_000, 100_000, minimum=5_000) == 50_000
    assert tax_give(102_000, 100_000, minimum=5_000) is None
    assert fighter_take(100, 50) == 50
    assert fighter_take(10, 0) == 0


def test_bc26_members_see_the_planet_id():
    u = _u()
    _seat(u, "A")
    _seat(u, "B")
    assert apply_action(u, "A", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "ZZ", "name": "Zed"})).ok
    planet = next(pl for pl in u.planets.values() if pl.sector_id not in K.FEDSPACE_SECTORS)
    planet.corp_ticker = "ZZ"
    block = build_observation(u, "A").model_dump()
    corp = block.get("corp") or {}
    listed = corp.get("planets") or []
    assert listed and listed[0]["planet_id"] == planet.id
    assert "production" in listed[0] and "stock" in listed[0]
    rival = build_observation(u, "B").model_dump()
    public = rival.get("corporations") or []
    assert public and "planets" not in public[0]


def test_scenario_lab_passes():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "scripts" / "corp_bots_scenario_lab.py"
    spec = importlib.util.spec_from_file_location("corp_bots_scenario_lab", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main() == 0
