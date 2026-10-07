"""Purse math for bots-bank-death-economy-v1. The seat brain does not call it yet."""

from __future__ import annotations

from tw2k.agents.bank_brain import (
    away_reserve,
    deposit_amount,
    nest_egg,
    purse,
    risk_flags,
    tax_keep,
    trade_capital,
    withdraw_amount,
)


def test_bb22_bank_report_counts_treasury_and_losses():
    from types import SimpleNamespace
    from scripts.run_scripted_match import fold_bank_events

    def ev(kind, actor, **payload):
        return SimpleNamespace(kind=kind, actor_id=actor, payload=payload)

    rows = fold_bank_events([
        ev("bank_deposit", "P1", amount=10_000),
        ev("planet_treasury", "P1", direction="deposit", amount=4_000),
        ev("planet_treasury", "P1", direction="withdraw", amount=1_500),
        ev("ship_destroyed", "P2", victim="P1", credits_lost=80_000),
        ev("ship_destroyed", "P2", victim="P1", credits_lost=20_000),
    ], ["P1"])
    assert rows["P1"]["deposited"] == 10_000
    assert rows["P1"]["treasury_deposited"] == 4_000
    assert rows["P1"]["treasury_withdrawn"] == 1_500
    assert rows["P1"]["credits_lost"] == 100_000
    assert rows["P1"]["credits_lost_count"] == 2
    assert rows["P1"]["credits_lost_largest"] == 80_000


def test_bb24_scenario_lab():
    from scripts.bots_bank_scenario_lab import main
    assert main() == 0


def test_bb6_nest_egg():
    assert nest_egg(0) == 10_000
    assert nest_egg(149_999) == 10_000
    assert nest_egg(150_000) == 50_000
    assert nest_egg(500_000) == 100_000


def test_bb2_purse():
    assert purse(20_000, 0, 10_000, 0) == 10_000
    assert purse(5_000, 80_000, 10_000, 40_000) == 45_000
    assert purse(1_000, 0, 10_000, 0) == 0


def test_bb5_away_reserve():
    assert trade_capital(10) == 5_000
    assert trade_capital(40) == 10_000
    assert away_reserve(20, [], 0, owns_fighters=True) == 5_000
    assert away_reserve(20, [], 0, owns_fighters=False) == 7_000
    assert away_reserve(40, [40_000], 0, owns_fighters=True) == 50_000
    assert away_reserve(40, [200_000], 0, owns_fighters=True) == 210_000
    assert away_reserve(20, [20_000, 20_000, 20_000], 0, owns_fighters=True) == 65_000
    # A pile of small buys still stops at the cap. One risk flag halves that cap.
    assert away_reserve(20, [20_000] * 10, 0, owns_fighters=True) == 150_000
    assert away_reserve(20, [20_000] * 10, 1, owns_fighters=True) == 75_000
    # The floor is the trade capital plus the largest single buy.
    assert away_reserve(40, [40_000], 5, owns_fighters=True) == 50_000


def test_bb3_withdraw_the_shortfall():
    assert withdraw_amount(25_000, 2_000, 5_000, 80_000, 10_000, 70_000, recovery=False) == 22_000
    assert withdraw_amount(25_000, 2_000, 5_000, 10_000, 10_000, 70_000, recovery=False) == 0
    assert withdraw_amount(25_000, 2_000, 5_000, 10_000, 10_000, 70_000, recovery=True) == 10_000


def _la(obs, kind, legal=True, **params):
    obs["legal_actions"] = [row for row in obs["legal_actions"] if row["kind"] != kind]
    obs["legal_actions"].append({
        "kind": kind, "legal": legal, "reason": None, "detail": "precise", "params": params,
    })
    return obs


def test_bb4_reserve_deposits_above_the_away_reserve_not_the_old_float(monkeypatch):
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain
    from tw2k.engine import constants as engine_k

    brain = SeatBrain()
    obs = synthetic_obs(sector=1, credits=80_000, ship_class="cargotran", day=3)
    obs["bank_balance"] = 0
    obs["net_worth"] = 80_000
    _la(obs, "buy_equip", item={"choices": [], "unit_price_by": {}})
    _la(obs, "bank_deposit", max_amount=80_000, balance=0, room=500_000)
    first = brain.decide(obs)
    # 75 holds * 250 = 18,750 trade capital, plus the 2,000 toll because no fighters are aboard.
    assert first["kind"] == "bank_deposit"
    assert first["args"]["amount"] == 80_000 - (18_750 + 2_000)
    assert brain.decide(obs)["kind"] != "bank_deposit"

    monkeypatch.setattr(engine_k, "BOTS_BANK_MODE", "legacy")
    legacy = SeatBrain().decide(obs)
    assert legacy["kind"] == "bank_deposit"
    assert legacy["args"]["amount"] == 80_000 - int(engine_k.BOT_BANK_FLOAT)


def test_bb8_day1_seat_deposits_the_cap():
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain

    brain = SeatBrain()
    obs = synthetic_obs(sector=1, credits=80_000, ship_class="cargotran", day=1)
    obs["bank_balance"] = 0
    obs["net_worth"] = 80_000
    _la(obs, "buy_equip", item={"choices": [], "unit_price_by": {}})
    _la(obs, "bank_deposit", max_amount=80_000, balance=0, room=500_000)
    first = brain.decide(obs)
    assert first["kind"] == "bank_deposit" and first["args"]["amount"] == 10_000


def test_bb13_a_pod_withdraws_before_it_buys_the_scout():
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain

    pod = synthetic_obs(sector=1, credits=0, ship_class="escape_pod", holds=5)
    pod["bank_balance"] = 80_000
    pod["net_worth"] = 80_000
    _la(pod, "buy_ship", ship_class={
        "choices": ["cargotran", "scout_marauder"],
        "net_cost_by": {"cargotran": 40_000, "scout_marauder": 5_000},
    })
    _la(pod, "bank_withdraw", max_amount=80_000, balance=80_000)
    withdrawn = SeatBrain().decide(pod)
    assert withdrawn["kind"] == "bank_withdraw"
    assert withdrawn["args"]["amount"] == 40_000 + 2_000


def test_bb21_pending_buy_survives_save_load():
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain, SeatMemory

    pod = synthetic_obs(sector=1, credits=0, ship_class="escape_pod", holds=5, day=3)
    pod["bank_balance"] = 80_000
    pod["net_worth"] = 80_000
    _la(pod, "buy_ship", ship_class={
        "choices": ["cargotran", "scout_marauder"],
        "net_cost_by": {"cargotran": 40_000, "scout_marauder": 5_000},
    })
    _la(pod, "bank_withdraw", max_amount=80_000, balance=80_000)
    brain = SeatBrain()
    assert brain.decide(pod)["kind"] == "bank_withdraw"
    restored = SeatBrain()
    restored.mem = SeatMemory.load(brain.mem.dump())
    assert restored.mem.pending_buy == "hull"
    assert restored.decide(pod)["kind"] != "bank_withdraw"


def test_bb12_overflow_deposits_once_when_the_bank_is_full():
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain

    planet = {"id": 7, "sector_id": 5, "citadel_level": 1, "citadel_target": 1,
              "shields": 10, "origin": "genesis", "colonists": {}}
    obs = synthetic_obs(sector=5, credits=300_000, ship_class="cargotran", day=4, landed=7, planets=[planet])
    obs["bank_balance"] = 500_000
    obs["bank_room"] = 0
    obs["net_worth"] = 800_000
    obs["alignment"] = 100
    _la(obs, "deposit_treasury", planet_id={"type": "int", "choices": [7]},
        amount={"type": "int", "min": 1, "max": 300_000})
    brain = SeatBrain()
    first = brain.decide(obs)
    assert first["kind"] == "deposit_treasury"
    assert first["args"]["planet_id"] == 7
    assert 200_000 < first["args"]["amount"] < 300_000
    assert brain.decide(obs)["kind"] != "deposit_treasury"

    roomy = synthetic_obs(sector=5, credits=300_000, ship_class="cargotran", day=4, landed=7, planets=[planet])
    roomy["bank_room"] = 40_000
    roomy["alignment"] = 100
    _la(roomy, "deposit_treasury", planet_id={"type": "int", "choices": [7]},
        amount={"type": "int", "min": 1, "max": 300_000})
    assert SeatBrain().decide(roomy)["kind"] != "deposit_treasury"

    bare = dict(planet)
    bare["citadel_level"] = 0
    bare["citadel_target"] = 0
    blocked = synthetic_obs(sector=5, credits=300_000, ship_class="cargotran", day=4, landed=7, planets=[bare])
    blocked["bank_room"] = 0
    blocked["alignment"] = 100
    _la(blocked, "deposit_treasury", planet_id={"type": "int", "choices": [7]},
        amount={"type": "int", "min": 1, "max": 300_000})
    assert SeatBrain().decide(blocked)["kind"] != "deposit_treasury"


def test_bb12_withdraws_the_citadel_shortfall_once():
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain

    planet = {"id": 7, "sector_id": 5, "citadel_level": 1, "citadel_target": 1,
              "shields": 10, "origin": "genesis", "colonists": {"fuel_ore": 2_000}}
    obs = synthetic_obs(sector=5, credits=0, ship_class="cargotran", day=4, landed=7, planets=[planet])
    obs["bank_balance"] = 0
    obs["alignment"] = 100
    _la(obs, "withdraw_treasury", planet_id={"type": "int", "choices": [7]},
        amount={"type": "int", "min": 1, "max": 25_000})
    brain = SeatBrain()
    first = brain.decide(obs)
    assert first["kind"] == "withdraw_treasury"
    assert first["args"] == {"planet_id": 7, "amount": 10_000}
    assert brain.decide(obs)["kind"] != "withdraw_treasury"

    short_people = dict(planet)
    short_people["colonists"] = {}
    blocked = synthetic_obs(sector=5, credits=0, ship_class="cargotran", day=4, landed=7, planets=[short_people])
    _la(blocked, "withdraw_treasury", planet_id={"type": "int", "choices": [7]},
        amount={"type": "int", "min": 1, "max": 25_000})
    assert SeatBrain().decide(blocked)["kind"] != "withdraw_treasury"


def test_bb12_withdraws_a_hull_the_bank_cannot_cover():
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain
    from tw2k.engine.constants import net_hull_cost

    planet = {"id": 7, "sector_id": 5, "citadel_level": 1, "citadel_target": 1,
              "shields": 10, "origin": "genesis", "colonists": {}}
    need = net_hull_cost("escape_pod", "cargotran") + 2_000
    obs = synthetic_obs(sector=5, credits=0, ship_class="escape_pod", holds=5, day=4, landed=7, planets=[planet])
    obs["bank_balance"] = 0
    obs["net_worth"] = 0
    obs["alignment"] = 100
    _la(obs, "withdraw_treasury", planet_id={"type": "int", "choices": [7]},
        amount={"type": "int", "min": 1, "max": 80_000})
    action = SeatBrain().decide(obs)
    assert action["kind"] == "withdraw_treasury"
    assert action["args"]["amount"] == need

    covered = synthetic_obs(sector=5, credits=0, ship_class="escape_pod", holds=5, day=4, landed=7, planets=[planet])
    covered["bank_balance"] = need
    covered["net_worth"] = need
    _la(covered, "withdraw_treasury", planet_id={"type": "int", "choices": [7]},
        amount={"type": "int", "min": 1, "max": 80_000})
    assert SeatBrain().decide(covered)["kind"] != "withdraw_treasury"


def test_bb9_each_risk_flag_counts_once():
    quiet = dict(days_since_loss=None, ship_class="cargotran", alignment=100,
                 fedsafe=True, threat_hops=None, fighters=100)
    assert risk_flags(**quiet) == 0
    assert risk_flags(**{**quiet, "days_since_loss": 2}) == 1
    assert risk_flags(**{**quiet, "days_since_loss": 9}) == 0
    assert risk_flags(**{**quiet, "ship_class": "scout_marauder"}) == 1
    assert risk_flags(**{**quiet, "ship_class": "escape_pod"}) == 1
    assert risk_flags(**{**quiet, "alignment": -10}) == 1
    assert risk_flags(**{**quiet, "fedsafe": False}) == 1
    assert risk_flags(**{**quiet, "threat_hops": 2}) == 1
    assert risk_flags(**{**quiet, "threat_hops": 4}) == 0
    assert risk_flags(**{**quiet, "fighters": 10}) == 1
    calm = away_reserve(20, [40_000, 40_000, 40_000], 0, owns_fighters=True)
    halved = away_reserve(20, [40_000, 40_000, 40_000], 1, owns_fighters=True)
    assert calm == 125_000
    assert halved == 75_000


def test_bb10_tax_line_keeps_a_good_seat_under_the_line():
    assert tax_keep(150_000, 0, 50) == 100_000
    assert tax_keep(20_750, 0, 50) == 20_750
    assert tax_keep(150_000, 120_000, 50) == 150_000
    assert tax_keep(150_000, 0, -100) == 150_000


def test_bb10_good_seat_deposits_down_to_the_tax_line(monkeypatch):
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain

    brain = SeatBrain()
    obs = synthetic_obs(sector=1, credits=400_000, ship_class="cargotran", day=3)
    obs["alignment"] = 50
    obs["bank_balance"] = 0
    obs["net_worth"] = 400_000
    _la(obs, "buy_equip", item={"choices": [], "unit_price_by": {}})
    _la(obs, "bank_deposit", max_amount=400_000, balance=0, room=500_000)
    monkeypatch.setattr(SeatBrain, "_away_cash", lambda self, v: 150_000)
    first = brain.decide(obs)
    assert first["kind"] == "bank_deposit"
    assert first["args"]["amount"] == 300_000

    evil = SeatBrain()
    obs["alignment"] = -100
    monkeypatch.setattr(SeatBrain, "_away_cash", lambda self, v: 150_000)
    deposited = evil.decide(obs)
    assert deposited["kind"] == "bank_deposit"
    assert deposited["args"]["amount"] == 250_000


def test_bb8_day1_cap():
    assert deposit_amount(40_000, 10_000, 500_000, day1=False) == 30_000
    assert deposit_amount(20_000, 8_000, 500_000, day1=True) == 10_000
    assert deposit_amount(15_000, 8_000, 500_000, day1=True) == 0
    assert deposit_amount(40_000, 10_000, 5_000, day1=False) == 5_000


def _h_obs(**overrides):
    import asyncio
    from tw2k.engine.observation import Observation
    base = dict(
        day=2, tick=1, max_days=10, finished=False,
        self_id="P6", self_name="H", credits=0, alignment=100,
        turns_remaining=40, turns_per_day=40,
        ship={"class": "escape_pod", "fighters": 0, "cargo": {}, "cargo_free": 0, "holds": 5},
        corp_ticker=None, planet_landed=None, scratchpad="",
        sector={"id": 1, "ferrengi": []},
        adjacent=[{"id": 2, "known": True, "port": None, "density": 0}],
        known_ports=[], other_players=[], inbox=[], recent_events=[],
        net_worth=80_000, bank_balance=80_000, legal_actions=[],
    )
    base.update(overrides)
    return asyncio, Observation(**base)


def test_bb14_h_pod_withdraws_before_it_buys():
    asyncio, Observation = _h_obs()
    from tw2k.agents.heuristic import HeuristicAgent
    obs = Observation
    obs.legal_actions = [
        {"kind": "buy_ship", "legal": True, "params": {"ship_class": {
            "choices": ["cargotran", "scout_marauder"],
            "net_cost_by": {"cargotran": 40_000, "scout_marauder": 0},
        }}},
        {"kind": "bank_withdraw", "legal": True, "params": {"max_amount": 80_000}},
    ]
    agent = HeuristicAgent("P6", "H", seed=1)
    act = asyncio.run(agent.act(obs))
    assert act.kind.value == "bank_withdraw"
    assert act.args["amount"] == 60_000


def test_bb14_legacy_h_does_not_bank(monkeypatch):
    import tw2k.engine.constants as K
    monkeypatch.setattr(K, "BOTS_BANK_MODE", "legacy")
    asyncio, Observation = _h_obs()
    from tw2k.agents.heuristic import HeuristicAgent
    obs = Observation
    obs.legal_actions = [
        {"kind": "buy_ship", "legal": True, "params": {"ship_class": {
            "choices": ["cargotran", "scout_marauder"],
            "net_cost_by": {"cargotran": 40_000, "scout_marauder": 0},
        }}},
        {"kind": "bank_withdraw", "legal": True, "params": {"max_amount": 80_000}},
    ]
    agent = HeuristicAgent("P6", "H", seed=1)
    act = asyncio.run(agent.act(obs))
    assert act.kind.value == "buy_ship"
    assert act.args["ship_class"] == "scout_marauder"


def test_bb14_h_deposits_spare_once_per_visit():
    asyncio, Observation = _h_obs(
        day=2, credits=40_000, net_worth=40_000, bank_balance=0,
        ship={"class": "scout_marauder", "fighters": 500, "cargo": {}, "cargo_free": 10, "holds": 20,
              "scanner": "density_scanner"},
    )
    from tw2k.agents.heuristic import HeuristicAgent
    obs = Observation
    obs.legal_actions = [
        {"kind": "bank_deposit", "legal": True, "params": {"max_amount": 500_000}},
        {"kind": "warp", "legal": True, "params": {}},
        {"kind": "wait", "legal": True, "params": {}},
    ]
    agent = HeuristicAgent("P6", "H", seed=1)
    first = asyncio.run(agent.act(obs))
    assert first.kind.value == "bank_deposit"
    assert first.args["amount"] == 30_000
    second = asyncio.run(agent.act(obs))
    assert second.kind.value == "warp"


def _detour_brain(sector: int, credits: int = 200_000, *, cargo: dict | None = None, day: int = 3):
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import Intent, SeatBrain, SeatMemory, View

    obs = synthetic_obs(sector=sector, credits=credits, ship_class="cargotran", day=day)
    obs["alignment"] = 100
    obs["bank_balance"] = 0
    obs["net_worth"] = credits
    if cargo:
        obs["ship"]["cargo"].update(cargo)
    brain = SeatBrain()
    brain.mem = SeatMemory()
    plan = {"kind": "plot_course", "args": {"target": 4, "execute": True}, "thought": "trade"}
    return brain, View(obs), plan, Intent()


def test_bb11_detour_is_once_a_day_and_within_three_hops():
    brain, view, plan, intent = _detour_brain(2)
    first, _ = brain._bank_detour(view, plan, intent)
    assert first["kind"] == "plot_course"
    assert first["args"]["target"] == 1
    second, _ = brain._bank_detour(view, plan, intent)
    assert second["args"]["target"] == 4

    far, far_view, far_plan, far_intent = _detour_brain(5)
    stayed, _ = far._bank_detour(far_view, far_plan, far_intent)
    assert stayed["args"]["target"] == 4

    loaded, loaded_view, loaded_plan, loaded_intent = _detour_brain(2, cargo={"fuel_ore": 10})
    kept, _ = loaded._bank_detour(loaded_view, loaded_plan, loaded_intent)
    assert kept["args"]["target"] == 4

    poor, poor_view, poor_plan, poor_intent = _detour_brain(2, credits=20_000)
    broke, _ = poor._bank_detour(poor_view, poor_plan, poor_intent)
    assert broke["args"]["target"] == 4

    held, held_view, held_plan, held_intent = _detour_brain(2)
    held.mem.held[1] = [3, 50]
    blocked, _ = held._bank_detour(held_view, held_plan, held_intent)
    assert blocked["args"]["target"] == 4


def test_bb18_daily_bank_cap_resets_on_the_next_day():
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain, SeatMemory

    def obs_for(day: int):
        obs = synthetic_obs(sector=1, credits=80_000, ship_class="cargotran", day=day)
        obs["bank_balance"] = 0
        obs["net_worth"] = 80_000
        obs["alignment"] = 100
        _la(obs, "buy_equip", item={"choices": [], "unit_price_by": {}})
        _la(obs, "bank_deposit", max_amount=80_000, balance=0, room=500_000)
        return obs

    brain = SeatBrain()
    brain.mem = SeatMemory()
    brain.mem.bank_verbs_day = 3
    brain.mem.bank_verbs = 8
    assert brain.decide(obs_for(3))["kind"] != "bank_deposit"
    nxt = brain.decide(obs_for(4))
    assert nxt["kind"] == "bank_deposit"
    assert brain.mem.bank_verbs == 1
    restored = SeatMemory.load(brain.mem.dump())
    assert restored.bank_verbs_day == 4
    assert restored.bank_verbs == 1


def test_bb27_nest_egg_is_deposited_before_the_away_reserve():
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain

    def obs_for(balance: int):
        obs = synthetic_obs(sector=1, credits=80_000, ship_class="cargotran", day=3)
        obs["bank_balance"] = balance
        obs["net_worth"] = 80_000 + balance
        obs["alignment"] = 100
        _la(obs, "buy_equip", item={"choices": [], "unit_price_by": {}})
        _la(obs, "bank_deposit", max_amount=80_000, balance=balance, room=500_000 - balance)
        return obs

    brain = SeatBrain()
    brain._away_cash = lambda v: 150_000  # noqa: SLF001
    empty = brain.decide(obs_for(0))
    assert empty["kind"] == "bank_deposit"
    assert empty["args"]["amount"] == 10_000

    full = SeatBrain()
    full._away_cash = lambda v: 150_000  # noqa: SLF001
    assert full.decide(obs_for(10_000))["kind"] != "bank_deposit"


def test_bb23_tax_and_death_keeps_the_old_float(monkeypatch):
    import tw2k.engine.constants as K
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain

    monkeypatch.setattr(K, "BOT_BANK_POLICY", "tax_and_death")
    obs = synthetic_obs(sector=1, credits=80_000, ship_class="cargotran", day=3)
    obs["bank_balance"] = 0
    obs["net_worth"] = 80_000
    _la(obs, "buy_equip", item={"choices": [], "unit_price_by": {}})
    _la(obs, "bank_deposit", max_amount=80_000, balance=0, room=500_000)
    action = SeatBrain().decide(obs)
    assert action["kind"] == "bank_deposit"
    assert action["args"]["amount"] == 80_000 - int(K.BOT_BANK_FLOAT)


def test_bb23_h_does_not_bank_under_tax_and_death(monkeypatch):
    import tw2k.engine.constants as K
    monkeypatch.setattr(K, "BOT_BANK_POLICY", "tax_and_death")
    asyncio, Observation = _h_obs()
    from tw2k.agents.heuristic import HeuristicAgent
    obs = Observation
    obs.legal_actions = [
        {"kind": "buy_ship", "legal": True, "params": {"ship_class": {
            "choices": ["cargotran", "scout_marauder"],
            "net_cost_by": {"cargotran": 40_000, "scout_marauder": 0},
        }}},
        {"kind": "bank_withdraw", "legal": True, "params": {"max_amount": 80_000}},
    ]
    act = asyncio.run(HeuristicAgent("P6", "H", seed=1).act(obs))
    assert act.kind.value == "buy_ship"
    assert act.args["ship_class"] == "scout_marauder"


def test_bb12_spare_deposits_before_the_bank_is_full(monkeypatch):
    import tw2k.engine.constants as K
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain

    monkeypatch.setattr(K, "BOT_TREASURY_POLICY", "spare")
    planet = {"id": 7, "sector_id": 5, "citadel_level": 1, "citadel_target": 1,
              "shields": 10, "origin": "genesis", "colonists": {}}
    obs = synthetic_obs(sector=5, credits=300_000, ship_class="cargotran", day=4, landed=7, planets=[planet])
    obs["bank_balance"] = 0
    obs["bank_room"] = 500_000
    obs["alignment"] = 100
    _la(obs, "deposit_treasury", planet_id={"type": "int", "choices": [7]},
        amount={"type": "int", "min": 1, "max": 300_000})
    action = SeatBrain().decide(obs)
    assert action["kind"] == "deposit_treasury"
    assert 200_000 < action["args"]["amount"] < 300_000
