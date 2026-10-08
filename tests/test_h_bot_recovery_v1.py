"""H and N1 rebuy a cargo hull after a death. N2 and N3 keep today's Scout buy."""

from __future__ import annotations

HULLS = {
    "choices": ["cargotran", "merchant_freighter", "merchant_cruiser", "scout_marauder"],
    "net_cost_by": {
        "cargotran": 50_000,
        "merchant_freighter": 30_000,
        "merchant_cruiser": 40_000,
        "scout_marauder": 10_000,
    },
}


def test_hr1_h_withdraws_for_the_freighter_and_leaves_the_cruiser_reserve():
    from tests.test_bots_bank_economy_v1 import _h_obs
    from tw2k.agents.heuristic import HeuristicAgent

    asyncio, Observation = _h_obs()
    obs = Observation
    obs.legal_actions = [
        {"kind": "buy_ship", "legal": True, "params": {"ship_class": HULLS}},
        {"kind": "bank_withdraw", "legal": True, "params": {"max_amount": 80_000}},
    ]
    act = asyncio.run(HeuristicAgent("P6", "H", seed=1).act(obs))
    assert act.kind.value == "bank_withdraw"
    assert act.args["amount"] == 30_000


def test_hr2_h_buys_the_freighter_once_the_cash_is_aboard():
    from tests.test_bots_bank_economy_v1 import _h_obs
    from tw2k.agents.heuristic import HeuristicAgent

    asyncio, Observation = _h_obs(credits=30_000, bank_balance=50_000, net_worth=80_000)
    obs = Observation
    obs.legal_actions = [
        {"kind": "buy_ship", "legal": True, "params": {"ship_class": HULLS}},
        {"kind": "bank_withdraw", "legal": True, "params": {"max_amount": 50_000}},
    ]
    act = asyncio.run(HeuristicAgent("P6", "H", seed=1).act(obs))
    assert act.kind.value == "buy_ship"
    assert act.args["ship_class"] == "merchant_freighter"


def _n1():
    from tw2k.agents.seat_brain import SeatBrain
    return SeatBrain(feed_organics=False, citadel_floor_ratio=None, citadel_fuel_shield=False,
                     citadel_multiday_floor=False, value_allocator=False)


def test_hr3_n1_withdraws_for_the_freighter():
    from tests.test_bots_bank_economy_v1 import _la
    from tw2k.agents.seat_acceptance import synthetic_obs

    pod = synthetic_obs(sector=1, credits=0, ship_class="escape_pod", holds=5)
    pod["bank_balance"] = 80_000
    pod["net_worth"] = 80_000
    _la(pod, "buy_ship", ship_class=HULLS)
    _la(pod, "bank_withdraw", max_amount=80_000, balance=80_000)
    withdrawn = _n1().decide(pod)
    assert withdrawn["kind"] == "bank_withdraw"
    assert withdrawn["args"]["amount"] == 30_000


def test_hr4_n2_still_asks_for_the_cargotran():
    from tests.test_bots_bank_economy_v1 import _la
    from tw2k.agents.seat_acceptance import synthetic_obs
    from tw2k.agents.seat_brain import SeatBrain

    pod = synthetic_obs(sector=1, credits=5_000, ship_class="escape_pod", holds=5)
    pod["bank_balance"] = 80_000
    pod["net_worth"] = 80_000
    _la(pod, "buy_ship", ship_class={
        "choices": ["cargotran", "scout_marauder"],
        "net_cost_by": {"cargotran": 40_000, "scout_marauder": 5_000},
    })
    _la(pod, "bank_withdraw", max_amount=80_000, balance=80_000)
    withdrawn = SeatBrain(value_allocator=False).decide(pod)
    assert withdrawn["kind"] == "bank_withdraw"
    assert withdrawn["args"]["amount"] == 40_000 + 2_000 - 5_000


def test_hr6_a_hidden_freighter_is_still_worth_a_withdraw():
    from tests.test_bots_bank_economy_v1 import _h_obs
    from tw2k.agents.heuristic import HeuristicAgent

    asyncio, Observation = _h_obs(credits=0)
    obs = Observation
    obs.legal_actions = [
        {"kind": "buy_ship", "legal": True, "params": {"ship_class": {
            "choices": ["scout_marauder"],
            "net_cost_by": HULLS["net_cost_by"],
            "blocked_by": {
                "cargotran": "insufficient credits (0 < 50000)",
                "merchant_freighter": "insufficient credits (0 < 30000)",
                "merchant_cruiser": "insufficient credits (0 < 40000)",
            },
        }}},
        {"kind": "bank_withdraw", "legal": True, "params": {"max_amount": 80_000}},
    ]
    act = asyncio.run(HeuristicAgent("P6", "H", seed=1).act(obs))
    assert act.kind.value == "bank_withdraw"
    assert act.args["amount"] == 30_000


def test_hr7_a_free_scout_after_ship_destroyed_withdraws_for_the_freighter():
    from tests.test_bots_bank_economy_v1 import _h_obs
    from tw2k.agents.heuristic import HeuristicAgent

    asyncio, Observation = _h_obs(deaths=1)
    obs = Observation
    obs.ship = dict(obs.ship)
    obs.ship["class"] = "scout_marauder"
    obs.legal_actions = [
        {"kind": "buy_ship", "legal": False, "reason": "no ship you can buy right now",
         "params": {"ship_class": {
             "choices": [],
             "net_cost_by": HULLS["net_cost_by"],
             "blocked_by": {
                 "cargotran": "insufficient credits (0 < 50000)",
                 "merchant_freighter": "insufficient credits (0 < 30000)",
                 "merchant_cruiser": "insufficient credits (0 < 40000)",
                 "scout_marauder": "insufficient credits (0 < 10000)",
             },
         }}},
        {"kind": "bank_withdraw", "legal": True, "params": {"max_amount": 80_000}},
    ]
    act = asyncio.run(HeuristicAgent("P6", "H", seed=1).act(obs))
    assert act.kind.value == "bank_withdraw"
    assert act.args["amount"] == 30_000


def test_hr8_a_short_bank_does_not_drain_the_reserve():
    """42213 in the bank cannot buy a freighter and still leave a cruiser or a scout."""
    from tw2k.agents.bank_brain import recovery_hull_step

    step = recovery_hull_step(
        [],
        {"cargotran": 47_963, "merchant_freighter": 29_413, "merchant_cruiser": 37_313,
         "scout_marauder": 11_963},
        0, 42_213, 42_213,
        {"cargotran": "insufficient credits (0 < 47963)",
         "merchant_freighter": "insufficient credits (0 < 29413)",
         "merchant_cruiser": "insufficient credits (0 < 37313)"},
    )
    assert step == ("bank_withdraw", 29_413)


def test_hr9_a_fat_purse_plots_back_to_stardock():
    from tests.test_bots_bank_economy_v1 import _h_obs
    from tw2k.agents.heuristic import HeuristicAgent

    asyncio, Observation = _h_obs(credits=80_000, bank_balance=10_000, net_worth=90_000)
    obs = Observation
    obs.sector = {"id": 40, "ferrengi": []}
    obs.ship = {"class": "merchant_freighter", "fighters": 50, "cargo": {}, "cargo_free": 65, "holds": 65}
    obs.legal_actions = [
        {"kind": "plot_course", "legal": True, "params": {}},
        {"kind": "warp", "legal": True, "params": {}},
    ]
    act = asyncio.run(HeuristicAgent("P6", "H", seed=1).act(obs))
    assert act.kind.value == "plot_course"
    assert act.args["target"] == 1


def test_hr10_an_empty_bank_plots_home_before_the_purse_is_spent():
    from tests.test_bots_bank_economy_v1 import _h_obs
    from tw2k.agents.heuristic import HeuristicAgent

    asyncio, Observation = _h_obs(credits=20_000, bank_balance=0, net_worth=36_000)
    obs = Observation
    obs.sector = {"id": 40, "ferrengi": []}
    obs.ship = {"class": "scout_marauder", "fighters": 0, "cargo": {}, "cargo_free": 25, "holds": 25}
    obs.legal_actions = [
        {"kind": "plot_course", "legal": True, "params": {}},
        {"kind": "warp", "legal": True, "params": {}},
    ]
    act = asyncio.run(HeuristicAgent("P6", "H", seed=1).act(obs))
    assert act.kind.value == "plot_course"
    assert act.args["target"] == 1


def test_hr11_a_small_bank_withdraws_the_keep_when_no_hull_fits():
    from tests.test_bots_bank_economy_v1 import _h_obs
    from tw2k.agents.heuristic import HeuristicAgent

    asyncio, Observation = _h_obs(credits=0, bank_balance=10_000, net_worth=18_000, deaths=1)
    obs = Observation
    obs.ship = dict(obs.ship)
    obs.ship["class"] = "scout_marauder"
    obs.ship["holds"] = 25
    obs.legal_actions = [
        {"kind": "buy_ship", "legal": False, "params": {"ship_class": {
            "choices": [],
            "net_cost_by": {
                "cargotran": 47_963, "merchant_freighter": 29_413, "merchant_cruiser": 37_313,
            },
            "blocked_by": {
                "cargotran": "insufficient credits (0 < 47963)",
                "merchant_freighter": "insufficient credits (0 < 29413)",
                "merchant_cruiser": "insufficient credits (0 < 37313)",
            },
        }}},
        {"kind": "bank_withdraw", "legal": True, "params": {"max_amount": 10_000}},
    ]
    act = asyncio.run(HeuristicAgent("P6", "H", seed=1).act(obs))
    assert act.kind.value == "bank_withdraw"
    assert act.args["amount"] == 10_000


def test_hr12_n1_plots_the_free_scout_home():
    from tests.test_bots_bank_economy_v1 import _la
    from tw2k.agents.seat_acceptance import synthetic_obs

    scout = synthetic_obs(sector=5, credits=0, ship_class="scout_marauder", holds=25)
    scout["deaths"] = 1
    scout["bank_balance"] = 10_000
    scout["adjacent"] = [{"id": 1, "known": True}]
    _la(scout, "plot_course")
    _la(scout, "warp")
    act = _n1().decide(scout)
    assert act["kind"] == "plot_course"
    assert act["args"]["target"] == 1


def test_hr13_a_trading_float_does_not_plot_home_forever():
    from tests.test_bots_bank_economy_v1 import _h_obs
    from tw2k.agents.heuristic import HeuristicAgent

    asyncio, Observation = _h_obs(credits=8_000, bank_balance=22_000, net_worth=40_000, deaths=1)
    obs = Observation
    obs.sector = {"id": 40, "ferrengi": []}
    obs.ship = {"class": "scout_marauder", "fighters": 0, "cargo": {}, "cargo_free": 25, "holds": 25}
    obs.adjacent = [{"id": 41, "known": True, "port": None, "density": 0}]
    obs.legal_actions = [
        {"kind": "plot_course", "legal": True, "params": {}},
        {"kind": "warp", "legal": True, "params": {}},
    ]
    act = asyncio.run(HeuristicAgent("P6", "H", seed=1).act(obs))
    assert act.kind.value == "warp"


def test_hr14_the_whole_purse_buys_the_freighter():
    from tests.test_bots_bank_economy_v1 import _h_obs
    from tw2k.agents.heuristic import HeuristicAgent

    asyncio, Observation = _h_obs(credits=8_000, bank_balance=22_184, net_worth=40_000, deaths=1)
    obs = Observation
    obs.ship = dict(obs.ship)
    obs.ship["class"] = "scout_marauder"
    obs.ship["holds"] = 25
    obs.legal_actions = [
        {"kind": "buy_ship", "legal": False, "params": {"ship_class": {
            "choices": [],
            "net_cost_by": {
                "cargotran": 47_963, "merchant_freighter": 29_413, "merchant_cruiser": 37_313,
            },
            "blocked_by": {
                "cargotran": "insufficient credits (8000 < 47963)",
                "merchant_freighter": "insufficient credits (8000 < 29413)",
                "merchant_cruiser": "insufficient credits (8000 < 37313)",
            },
        }}},
        {"kind": "bank_withdraw", "legal": True, "params": {"max_amount": 22_184}},
    ]
    act = asyncio.run(HeuristicAgent("P6", "H", seed=1).act(obs))
    assert act.kind.value == "bank_withdraw"
    assert act.args["amount"] == 29_413 - 8_000


def test_hr5_legacy_h_still_buys_the_scout(monkeypatch):
    import tw2k.engine.constants as K
    from tests.test_bots_bank_economy_v1 import _h_obs
    from tw2k.agents.heuristic import HeuristicAgent

    monkeypatch.setattr(K, "H_RECOVERY_MODE", "legacy")
    asyncio, Observation = _h_obs()
    obs = Observation
    obs.legal_actions = [
        {"kind": "buy_ship", "legal": True, "params": {"ship_class": {
            "choices": ["cargotran", "scout_marauder"],
            "net_cost_by": {"cargotran": 40_000, "scout_marauder": 0},
        }}},
        {"kind": "bank_withdraw", "legal": True, "params": {"max_amount": 80_000}},
    ]
    act = asyncio.run(HeuristicAgent("P6", "H", seed=1).act(obs))
    assert act.kind.value == "bank_withdraw"
    assert act.args["amount"] == 60_000
