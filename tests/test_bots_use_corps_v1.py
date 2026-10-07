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


def _pair(monkeypatch, *seats: str):
    from tw2k.agents.corp_brain import configure
    monkeypatch.setattr(K, "BOT_CORP_POLICY", "pair")
    configure(list(seats), seed=31)


def _brain_view(obs: dict):
    from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View
    brain = SeatBrain()
    brain.mem = SeatMemory()
    return brain, View(obs)


def _legal(kind: str, **params) -> dict:
    return {"kind": kind, "legal": True, "params": params}


def test_pb1_the_founder_sets_a_password_before_the_invite(monkeypatch):
    from tw2k.agents.corp_brain import clear, next_action
    _pair(monkeypatch, "P1", "P2")
    try:
        brain, view = _brain_view({
            "self_id": "P1", "self_name": "Ada", "day": 1,
            "corp_ticker": "ADA", "corp": {"password": "", "members": [{"id": "P1"}]},
            "legal_actions": [_legal("corp_set_password"), _legal("corp_invite", target={"choices": ["P2"]})],
        })
        action = next_action(brain, view)
        assert action is not None and action["kind"] == "corp_set_password"
        assert action["args"]["password"]
    finally:
        clear()


def test_pb2_the_partner_joins_with_the_invite_password(monkeypatch):
    from tw2k.agents.corp_brain import clear, next_action
    _pair(monkeypatch, "P1", "P2")
    try:
        brain, view = _brain_view({
            "self_id": "P2", "day": 1,
            "inbox": [{"kind": "corp_invite", "from": "P1", "ticker": "ADA", "password": "abc123"}],
            "legal_actions": [_legal("corp_join", ticker={"choices": ["ADA"]})],
        })
        action = next_action(brain, view)
        assert action is not None and action["args"]["password"] == "abc123"
    finally:
        clear()


def test_pb3_a_taken_ticker_falls_back(monkeypatch):
    from tw2k.agents.corp_brain import ticker_for
    assert ticker_for("Ada", "P1", {"ADA"}) == "P01"


def test_pb4_the_password_stays_out_of_the_thought(monkeypatch):
    from tw2k.agents.corp_brain import clear, next_action, password_for
    _pair(monkeypatch, "P1", "P2")
    try:
        brain, view = _brain_view({
            "self_id": "P1", "day": 1, "corp_ticker": "ADA",
            "corp": {"members": [{"id": "P1"}]},
            "legal_actions": [_legal("corp_set_password")],
        })
        action = next_action(brain, view)
        secret = password_for("ADA")
        assert secret not in action["thought"]
    finally:
        clear()


def test_pb5_the_password_stays_out_of_seat_memory(monkeypatch):
    from tw2k.agents.corp_brain import clear, next_action, password_for
    _pair(monkeypatch, "P1", "P2")
    try:
        brain, view = _brain_view({
            "self_id": "P1", "day": 1, "corp_ticker": "ADA",
            "corp": {"members": [{"id": "P1"}]},
            "legal_actions": [_legal("corp_set_password")],
        })
        next_action(brain, view)
        assert password_for("ADA") not in brain.mem.dump()
    finally:
        clear()


def test_pb6_a_non_partner_invite_is_ignored(monkeypatch):
    from tw2k.agents.corp_brain import clear, next_action
    _pair(monkeypatch, "P1", "P2")
    try:
        brain, view = _brain_view({
            "self_id": "P2", "day": 1,
            "inbox": [{"kind": "corp_invite", "from": "P9", "ticker": "RIV", "password": "abc123"}],
            "legal_actions": [_legal("corp_join", ticker={"choices": ["RIV"]})],
        })
        assert next_action(brain, view) is None
    finally:
        clear()


def test_pb7_a_join_is_not_retried_the_same_day(monkeypatch):
    from tw2k.agents.corp_brain import clear, next_action
    _pair(monkeypatch, "P1", "P2")
    try:
        brain, view = _brain_view({
            "self_id": "P2", "day": 1,
            "inbox": [{"kind": "corp_invite", "from": "P1", "ticker": "ADA", "password": "abc123"}],
            "legal_actions": [_legal("corp_join", ticker={"choices": ["ADA"]})],
        })
        assert next_action(brain, view)["kind"] == "corp_join"
        assert next_action(brain, view) is None
    finally:
        clear()
    u = _u()
    _seat(u, "A")
    _seat(u, "B")
    assert apply_action(u, "A", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "ZZ", "name": "Zed"})).ok
    assert apply_action(u, "A", Action(kind=ActionKind.CORP_SET_PASSWORD, args={"password": "secret"})).ok
    first = apply_action(u, "B", Action(kind=ActionKind.CORP_JOIN, args={"ticker": "ZZ", "password": "nope"}))
    second = apply_action(u, "B", Action(kind=ActionKind.CORP_JOIN, args={"ticker": "ZZ", "password": "nope"}))
    assert first.error == "wrong password"
    assert second.error == "one break-in attempt per day"


def test_pb8_a_corp_bot_deploys_as_corporate(monkeypatch):
    from tw2k.agents.seat_brain import SeatBrain, View
    monkeypatch.setattr(K, "BOT_CORP_POLICY", "pair")
    view = View({"legal_actions": [_legal("deploy_fighters", ownership={"choices": ["personal", "corporate"]})]})
    assert SeatBrain._pair_ownership(view, "deploy_fighters") == {"ownership": "corporate"}


def test_pb9_a_solo_bot_sends_no_ownership_argument():
    from tw2k.agents.seat_brain import SeatBrain, View
    view = View({"legal_actions": [_legal("deploy_fighters", ownership={"choices": ["personal", "corporate"]})]})
    assert SeatBrain._pair_ownership(view, "deploy_fighters") == {}


def test_pb10_friends_come_from_the_corp_block():
    from tw2k.agents.corp_brain import friends
    from tw2k.agents.seat_brain import View
    view = View({
        "self_id": "P1", "alliances": [],
        "corp": {"members": [{"id": "P1"}, {"id": "P2"}]},
    })
    assert friends(view) == {"P2"}


def test_pb11_hunt_skips_a_corp_mate(monkeypatch):
    from tw2k.agents.corp_brain import clear
    from tw2k.agents.seat_brain import SeatBrain, View
    _pair(monkeypatch, "P1", "P2")
    try:
        brain = SeatBrain()

        def hunt(tid: str) -> dict | None:
            obs = {
                "self_id": "P1", "day": 1, "alignment": 500, "credits": 1000,
                "sector": {"id": 20, "traders": [{"id": tid, "ship_class": "scout", "fighters": 0, "shields": 0}]},
                "ship": {"class": "battleship"},
                "corp": {"members": [{"id": "P1"}, {"id": "P2"}]},
                "legal_actions": [_legal("attack", target={"choices": [tid], "players": [tid]}, qty={"max": 40})],
            }
            return brain._hunt(View(obs))

        assert hunt("P2") is None
        stranger = hunt("P9")
        assert stranger is not None and stranger["args"]["target"] == "P9"
    finally:
        clear()


def test_pb12_a_rogue_group_is_not_friendly_after_the_ceo_is_gone():
    from types import SimpleNamespace

    from tw2k.engine.corp import deploy_friend
    u = _u()
    _seat(u, "A")
    rogue = SimpleNamespace(owner_id=K.ROGUE_OWNER_ID, corp_ticker="ZZ")
    assert deploy_friend(u, "A", rogue) is False


def test_pb13_the_mate_does_not_pay_the_same_citadel_step(monkeypatch):
    from tw2k.agents.corp_brain import clear
    _pair(monkeypatch, "P1", "P2")
    try:
        brain, alive = _brain_view({
            "self_id": "P2",
            "corp": {"ceo_id": "P1", "members": [{"id": "P1", "alive": True}, {"id": "P2", "alive": True}]},
        })
        _, gone = _brain_view({
            "self_id": "P2",
            "corp": {"ceo_id": "P1", "members": [{"id": "P1", "alive": False}, {"id": "P2", "alive": True}]},
        })
        assert brain._mate_waits_on_citadel(alive) is True
        assert brain._mate_waits_on_citadel(gone) is False
    finally:
        clear()


def test_pb15_credits_move_once_per_day(monkeypatch):
    from tw2k.agents.corp_brain import clear
    _pair(monkeypatch, "P1", "P2")
    try:
        brain, view = _brain_view({
            "self_id": "P1", "day": 2, "credits": 200_000, "alignment": 100,
            "sector": {"id": 20, "traders": [{"id": "P2", "ship_class": "cargotran"}]},
            "ship": {"class": "battleship", "holds": 20},
            "rivals": [{"id": "P2", "side": "evil"}],
            "legal_actions": [_legal("corp_transfer", partners=[{"player_id": "P2", "take_max": {"credits": 21_300}}])],
        })
        first = brain._corp_support(view)
        second = brain._corp_support(view)
        assert first is not None and first["args"]["qty"] == 41_000
        assert second is None
    finally:
        clear()


def test_pb16_the_tax_shield_pays_an_evil_mate_only(monkeypatch):
    from tw2k.agents.corp_brain import clear
    _pair(monkeypatch, "P1", "P2")
    try:
        def handoff(side: str):
            brain, view = _brain_view({
                "self_id": "P1", "day": 2, "credits": 150_000, "alignment": 100,
                "sector": {"id": 20, "traders": [{"id": "P2", "ship_class": "battleship"}]},
                "ship": {"class": "battleship", "holds": 20},
                "rivals": [{"id": "P2", "side": side}],
                "legal_actions": [_legal("corp_transfer", partners=[{"player_id": "P2", "take_max": {"credits": 900_000}}])],
            })
            return brain._corp_support(view)

        assert handoff("good") is None
        paid = handoff("evil")
        assert paid is not None and paid["args"]["qty"] == 50_000
    finally:
        clear()


def test_pb17_a_top_up_stays_inside_the_room_and_the_keep():
    from tw2k.agents.corp_brain import gear_take
    assert gear_take(100, 50, 30) == 50
    assert gear_take(10, 50, 30) == 7
    assert gear_take(-5, 50, 30) is None


def test_pb18_a_negative_transfer_is_refused():
    u = _u()
    _seat(u, "A", sector=4, credits=80_000)
    _seat(u, "B", sector=4, credits=10_000)
    assert apply_action(u, "A", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "ZZ", "name": "Zed"})).ok
    assert apply_action(u, "A", Action(kind=ActionKind.CORP_SET_PASSWORD, args={"password": "secret"})).ok
    assert apply_action(u, "A", Action(kind=ActionKind.CORP_INVITE, args={"target": "B"})).ok
    assert apply_action(u, "B", Action(kind=ActionKind.CORP_JOIN, args={"ticker": "ZZ", "password": "secret"})).ok
    refused = apply_action(u, "A", Action(
        kind=ActionKind.CORP_TRANSFER, args={"target": "B", "item": "credits", "qty": -5, "direction": "give"}))
    assert not refused.ok and refused.error == "invalid transfer"


def test_pb19_a_fifteen_hop_meetup_is_refused():
    from tw2k.agents.corp_brain import within_meetup
    assert within_meetup(3, 30) is True
    assert within_meetup(15, 10) is False


def test_pb20_an_affordable_purchase_does_not_wait_for_a_transfer():
    from tw2k.agents.corp_brain import credit_give
    assert credit_give(80_000, 0, 70_000, 61_300, reserve=20_000, pad=1_000, minimum=5_000) is None


def test_pb22_a_flagship_pilot_cannot_join_with_the_password():
    u = _u()
    _seat(u, "A")
    _seat(u, "B", hull=ShipClass.CORPORATE_FLAGSHIP)
    assert apply_action(u, "A", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "ZZ", "name": "Zed"})).ok
    assert apply_action(u, "A", Action(kind=ActionKind.CORP_SET_PASSWORD, args={"password": "secret"})).ok
    joined = apply_action(u, "B", Action(kind=ActionKind.CORP_JOIN, args={"ticker": "ZZ", "password": "secret"}))
    assert not joined.ok and joined.error == "a FlagShip pilot cannot join a corporation"


def test_pb23_rivals_do_not_see_planet_production():
    u = _u()
    _seat(u, "A")
    _seat(u, "B")
    assert apply_action(u, "A", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "ZZ", "name": "Zed"})).ok
    planet = next(pl for pl in u.planets.values() if pl.sector_id not in K.FEDSPACE_SECTORS)
    planet.corp_ticker = "ZZ"
    public = build_observation(u, "B").model_dump().get("corporations") or []
    assert public and "planets" not in public[0]
    assert "production" not in public[0] and "stock" not in public[0]


def test_pb24_corp_brain_does_not_draw_the_universe_rng():
    from pathlib import Path

    import tw2k.agents.corp_brain as corp_brain
    body = Path(corp_brain.__file__).read_text(encoding="utf-8").split('"""', 2)[-1]
    assert "universe.rng" not in body


def test_pb25_the_free_action_cap_resets_on_the_next_day(monkeypatch):
    from tw2k.agents.corp_brain import clear, next_action
    _pair(monkeypatch, "P1", "P2")
    try:
        mate, day1 = _brain_view({
            "self_id": "P2", "day": 1,
            "inbox": [{"kind": "corp_invite", "from": "P1", "ticker": "ADA", "password": "abc123"}],
            "legal_actions": [_legal("corp_join", ticker={"choices": ["ADA"]})],
        })
        mate.mem.corp_free_actions = 6
        mate.mem.corp_free_day = 1
        assert next_action(mate, day1) is None
        _, day2 = _brain_view({
            "self_id": "P2", "day": 2,
            "inbox": [{"kind": "corp_invite", "from": "P1", "ticker": "ADA", "password": "abc123"}],
            "legal_actions": [_legal("corp_join", ticker={"choices": ["ADA"]})],
        })
        joined = next_action(mate, day2)
        assert joined is not None and joined["kind"] == "corp_join"
    finally:
        clear()


def test_pb26_survey_returns_when_the_ceo_is_gone(monkeypatch):
    from tw2k.agents.corp_brain import clear
    _pair(monkeypatch, "P1", "P2")
    try:
        brain, alive = _brain_view({
            "self_id": "P2", "sector": {"id": 1},
            "corp": {"ceo_id": "P1", "members": [{"id": "P1", "alive": True}]},
        })
        assert brain._mate_skips_survey(alive) is True
        _, gone = _brain_view({
            "self_id": "P2", "sector": {"id": 1},
            "corp": {"ceo_id": "P1", "members": [{"id": "P1", "alive": False}]},
        })
        assert brain._mate_skips_survey(gone) is False
    finally:
        clear()


def test_team_groups_are_three_consecutive_seats(monkeypatch):
    from tw2k.agents.corp_brain import clear, configure, partner_of, role_of, team_of
    monkeypatch.setattr(K, "BOT_CORP_POLICY", "team")
    configure(["P1", "P2", "P3", "P4", "P5"], seed=31)
    try:
        assert role_of("P1") == "ceo" and team_of("P1") == ["P2", "P3"]
        assert partner_of("P2") == "P1" and partner_of("P3") == "P1"
        assert role_of("P4") == "ceo" and partner_of("P5") == "P4"
    finally:
        clear()


def test_scenario_lab_passes():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "scripts" / "corp_bots_scenario_lab.py"
    spec = importlib.util.spec_from_file_location("corp_bots_scenario_lab", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main() == 0
