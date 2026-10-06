"""QC for bots-use-rob-steal-hardware-v1 (seed 250925 regressions).

1. Armids: N1-P5 mined its home 14, the only gate to N2-P3's dead-end home
   428, and killed P3's colonist ferry three times. A home that other seats
   pass through gets no armids.
2. Heuristic (H) seat: holding 20 organics it orbited three ports that do not
   buy organics, then orbited two drained ports with empty holds. It now skips
   ports that cannot buy its cargo and ports it just failed to trade at.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from tw2k.agents.heuristic import HeuristicAgent
from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.models import MineType, Player, Ship
from tw2k.engine.observation import build_observation

# ---------------------------------------------------------------- armids


def _home_view(home: int = 20) -> tuple[SeatBrain, View]:
    u = generate_universe(
        GameConfig(seed=4790, universe_size=40, enable_ferrengi=False, enable_planets=False)
    )
    ship = Ship()
    ship.mines[MineType.ARMID] = 5
    p = Player(id="A", name="A", credits=50_000, ship=ship, sector_id=home)
    u.players["A"] = p
    u.sectors[home].occupant_ids.append("A")
    p.known_sectors.add(home)
    brain = SeatBrain()
    brain.mem = SeatMemory()
    brain.mem.home_sector = home
    v = View(build_observation(u, "A").model_dump(mode="json"))
    v.sector["is_fedspace"] = False
    v.sector["is_msl"] = False
    v.sector["planets"] = []
    v.legal["deploy_mines"] = {
        "kind": "deploy_mines",
        "legal": True,
        "params": {"kind": {"choices": ["armid"]}, "qty": {"max_by": {"armid": 5}}},
    }
    v.known_warps = {}
    for adj in v.obs.get("adjacent") or []:
        adj.pop("warps", None)
        adj.pop("seen", None)
    return brain, v


def test_armids_still_laid_on_a_quiet_home() -> None:
    brain, v = _home_view()
    act = brain._maybe_lay_armids(v)
    assert act is not None and act["kind"] == "deploy_mines"
    assert act["args"] == {"kind": "armid", "qty": 5}


def test_own_planet_does_not_block_armids() -> None:
    brain, v = _home_view()
    v.sector["planets"] = [{"id": 1, "owner_id": "A"}]
    assert brain._maybe_lay_armids(v) is not None


def test_no_armids_beside_a_rival_planet_in_the_sector() -> None:
    brain, v = _home_view()
    v.sector["planets"] = [{"id": 1, "owner_id": "A"}, {"id": 2, "owner_id": "B"}]
    assert brain._maybe_lay_armids(v) is None


def test_no_armids_with_a_rival_ship_in_the_sector() -> None:
    brain, v = _home_view()
    v.sector["occupants"] = ["A", "B"]
    assert brain._maybe_lay_armids(v) is None


def test_no_armids_on_the_gate_to_a_dead_end() -> None:
    # Seed 250925: 428's only warp is 14. Mines on 14 hit whoever lives at 428.
    brain, v = _home_view()
    adj = int(v.obs["adjacent"][0]["id"])
    v.known_warps = {adj: (int(v.here),)}
    assert brain._maybe_lay_armids(v) is None


def test_no_armids_when_density_shows_a_one_warp_neighbor() -> None:
    brain, v = _home_view()
    v.obs["adjacent"][0]["warps"] = 1
    assert brain._maybe_lay_armids(v) is None
    v.obs["adjacent"][0]["warps"] = 2
    assert brain._maybe_lay_armids(v) is not None


# ---------------------------------------------------------------- heuristic


def _obs(here: int, adjacent: list[dict], cargo: dict | None = None, port: dict | None = None, day: int = 3):
    cargo = cargo or {}
    return SimpleNamespace(
        sector={"id": here, "port": port, "ferrengi": []},
        ship={
            "class": "merchant_cruiser",
            "cargo": cargo,
            "cargo_free": 20 - sum(cargo.values()),
            "fighters": 30,
            "scanner": None,
        },
        adjacent=adjacent,
        day=day,
        credits=40_000,
        turns_remaining=100,
        legal_actions=[],
        fighter_challenge=None,
    )


def _act(agent: HeuristicAgent, obs) -> object:
    return asyncio.run(agent.act(obs))


@pytest.fixture
def fogged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(K, "INFO_MODE", "tw2002")


def test_heuristic_skips_ports_that_cannot_buy_the_cargo(fogged) -> None:
    # 674 BSB, 708 BSS: neither buys organics (letter 2). 318 has no port.
    agent = HeuristicAgent("P6", "H", seed=1)
    adj = [
        {"id": 674, "port": "BSB", "known": True},
        {"id": 708, "port": "BSS", "known": True},
        {"id": 318, "port": None, "known": True},
    ]
    act = _act(agent, _obs(261, adj, cargo={"organics": 20}))
    assert act.kind.value == "warp" and act.args["target"] == 318


def test_heuristic_ruled_out_port_still_beats_a_worn_dead_end(fogged) -> None:
    # Seed 250925 (QC rerun): hub 985, dead-end leaves 434 / 986, 975 BSS does not buy organics.
    # Skipping 975 outright trapped the seat for 7 days; visit counts must still win.
    agent = HeuristicAgent("P6", "H", seed=1)
    agent._visit_counts.update({434: 12, 986: 12})
    agent._last_from = 434
    adj = [
        {"id": 434, "port": None, "known": True},
        {"id": 975, "port": "BSS", "known": True},
        {"id": 986, "port": None, "known": True},
    ]
    act = _act(agent, _obs(985, adj, cargo={"organics": 20}))
    assert act.args["target"] == 975


def test_heuristic_still_hops_to_a_port_that_buys_the_cargo(fogged) -> None:
    agent = HeuristicAgent("P6", "H", seed=1)
    adj = [
        {"id": 674, "port": "BSB", "known": True},
        {"id": 709, "port": "SBS", "known": True},
        {"id": 318, "port": None, "known": True},
    ]
    act = _act(agent, _obs(261, adj, cargo={"organics": 20}))
    assert act.args["target"] == 709


def test_heuristic_leaves_a_drained_port_pair(fogged) -> None:
    # Seed 250925 days 5-10: 572 hub, 687 / 744 ports with nothing left to trade.
    agent = HeuristicAgent("P6", "H", seed=1)
    dry = {"class_id": 1, "code": "BSS", "buys": [], "sells": [], "stock": {}}
    act = _act(agent, _obs(687, [{"id": 572, "port": None, "known": True}], port=dry))
    assert act.args["target"] == 572
    adj = [
        {"id": 313, "port": None, "known": True},
        {"id": 687, "port": "BSS", "known": True},
        {"id": 744, "port": "SBB", "known": True},
    ]
    agent._last_from = 744  # just came from the other drained port
    act = _act(agent, _obs(572, adj))
    assert act.args["target"] == 313
    # Two days later the port may have restocked: it is a candidate again.
    agent._last_from = 744
    agent._visit_counts[313] = 50
    act = _act(agent, _obs(572, adj, day=5))
    assert act.args["target"] == 687
    assert "hopping to known port" in act.thought  # chosen as a port again, not by drifting


def test_heuristic_port_trade_is_not_marked_dry(fogged) -> None:
    agent = HeuristicAgent("P6", "H", seed=1)
    port = {
        "class_id": 1,
        "code": "SBB",
        "buys": ["organics", "equipment"],
        "sells": ["fuel_ore"],
        "stock": {"fuel_ore": {"current": 500, "max": 1000, "price": 30}},
    }
    act = _act(agent, _obs(744, [{"id": 572, "port": None, "known": True}], port=port))
    assert act.kind.value == "trade"
    full = _obs(744, [{"id": 572, "port": None, "known": True}], cargo={"fuel_ore": 20}, port=port)
    act = _act(agent, full)
    assert act.kind.value == "warp"
    assert 744 not in agent._dry_port


def test_legacy_info_keeps_the_old_heuristic_walk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(K, "INFO_MODE", "legacy")
    agent = HeuristicAgent("P6", "H", seed=1)
    adj = [
        {"id": 674, "port": "BSB", "known": True},
        {"id": 708, "port": "BSS", "known": True},
        {"id": 318, "port": None, "known": True},
    ]
    act = _act(agent, _obs(261, adj, cargo={"organics": 20}))
    assert act.args["target"] in (674, 708)
    dry = {"class_id": 1, "code": "BSS", "buys": [], "sells": [], "stock": {}}
    _act(agent, _obs(687, [{"id": 572, "port": None, "known": True}], port=dry))
    assert agent._dry_port == {}


# ---------------------------------------------------------------- psychic probe


def _sell_view(price: int = 200, side: str = "buys_from_player") -> tuple[SeatBrain, View]:
    brain, v = _home_view()
    v.sector["port"] = {
        "class": "1",
        "stock": {"equipment": {"current": 100, "max": 1000, "price": price, "side": side}},
    }
    brain._psychic_aboard = 1
    brain.mem.psychic_pct = 80.0
    return brain, v


def test_probe_reading_raises_a_live_sell_inside_the_port_room() -> None:
    brain, v = _sell_view()
    out = brain._haggle_live(v, {"commodity": "equipment", "qty": 10, "side": "sell"})
    # 80% read -> the best was 250; ask is capped at 109% of 200 = 218 (room is never under 110%).
    assert out["unit_price"] == 218
    assert out["unit_price"] < round(200 * K.PORT_HAGGLE_MIN_PCT / 100)


def test_probe_haggle_never_triggers_without_probe_or_on_buys() -> None:
    brain, v = _sell_view()
    args = {"commodity": "equipment", "qty": 10, "side": "buy"}
    assert brain._haggle_live(v, args) is args
    brain._psychic_aboard = 0
    args = {"commodity": "equipment", "qty": 10, "side": "sell"}
    assert brain._haggle_live(v, args) is args
    brain._psychic_aboard = 1
    brain.mem.psychic_pct = 97.0
    assert brain._haggle_live(v, args) is args
    brain, v = _sell_view(price=30)  # too cheap for a safe whole-credit step
    assert brain._haggle_live(v, args) is args


def test_probe_haggle_is_accepted_by_the_engine() -> None:
    from tw2k.engine.economy import haggle_bound

    for listed in (50, 51, 99, 200, 1234):
        brain, v = _sell_view(price=listed)
        brain.mem.psychic_pct = 50.0
        out = brain._haggle_live(v, {"commodity": "equipment", "qty": 1, "side": "sell"})
        assert listed < out["unit_price"] <= haggle_bound(listed, 0, "sell")


def test_probe_haggle_off_under_legacy_hardware(monkeypatch: pytest.MonkeyPatch) -> None:
    brain, v = _sell_view()
    monkeypatch.setattr(K, "HARDWARE_MODE", "legacy")
    args = {"commodity": "equipment", "qty": 10, "side": "sell"}
    assert brain._haggle_live(v, args) is args


def test_no_crime_at_stardock_even_if_listed_legal() -> None:
    # Cur's StarDock check relied on the legal list; the brain's own gate must hold too.
    from tw2k.agents.seat_brain import STARDOCK
    from tw2k.engine.models import Commodity

    u = generate_universe(
        GameConfig(seed=4791, universe_size=40, enable_ferrengi=False, enable_planets=False)
    )
    p = Player(id="A", name="A", credits=5_000, ship=Ship(), sector_id=STARDOCK)
    u.players["A"] = p
    u.sectors[STARDOCK].occupant_ids.append("A")
    p.alignment = -500
    p.experience = 1_000
    p.ship.cargo[Commodity.FUEL_ORE] = p.ship.holds
    brain = SeatBrain()
    brain.mem = SeatMemory()
    v = View(build_observation(u, "A").model_dump(mode="json"))
    v.sector["port"] = {}
    v.legal["rob"] = {"kind": "rob", "legal": True, "params": {"amount": {"max": 1000}}}
    assert brain._crime_action(v) is None
    v.here = 7  # same view off StarDock: the rob goes through, so the gate above is what stopped it
    assert brain._crime_action(v) is not None


def test_terra_take_never_exceeds_free_holds() -> None:
    brain, v = _home_view(home=1)
    v.legal["terra_colonists"] = {
        "kind": "terra_colonists",
        "legal": True,
        "params": {"mode": {"choices": ["take", "leave"]}, "qty": {"max_by": {"take": 500}}},
    }
    v.cargo_free = 3
    act = brain._load_colonists(v, 10, 0, "ferry")
    assert act is not None and act["kind"] == "terra_colonists"
    assert act["args"] == {"mode": "take", "qty": 3}


def test_heuristic_flee_waits_when_out_of_turns() -> None:
    # Seed 99 P6: three "warp: out of turns for this day" refusals fleeing Ferrengi.
    agent = HeuristicAgent("P6", "H", seed=1)
    obs = _obs(50, [{"id": 51, "port": None, "known": True}])
    obs.sector["ferrengi"] = [{"id": "F1", "aggression": 5, "fighters": 500}]
    obs.turns_remaining = 0
    act = _act(agent, obs)
    assert act.kind.value == "wait"
    obs.turns_remaining = 40
    act = _act(agent, obs)
    assert act.kind.value == "warp" and act.args["target"] == 51


# ---------------------------------------------------------------- FedSpace overnight


def _plot_view(fighters: int, turns: int, here: int = 600) -> tuple[SeatBrain, View]:
    brain, v = _home_view()
    v.here = here
    v.ship["fighters"] = fighters
    v.obs["turns_remaining"] = turns
    v.legal["warp"] = {
        "kind": "warp",
        "legal": True,
        "turn_cost": 2,
        "params": {"target": {"choices": [525]}},
    }
    v.legal["plot_course"] = {"kind": "plot_course", "legal": True, "params": {}}
    v.known_warps = {600: (525,), 525: (1, 600), 1: (447, 525), 447: (1,)}
    return brain, v


def test_plot_stops_short_of_fedspace_when_turns_end_there_armed() -> None:
    # Seed 20260925 N3-P1 day 6: plot 525 -> 447 via sector 1, out of turns in sector 1, towed.
    brain, v = _plot_view(fighters=200, turns=4)
    act = brain._plot(v, 447, "earn: sell organics at 447")
    assert act is not None and act["kind"] == "warp" and act["args"]["target"] == 525
    brain, v = _plot_view(fighters=200, turns=2, here=525)
    assert brain._plot(v, 447, "earn") is None  # the only hop today lands in FedSpace


def test_plot_unchanged_when_unarmed_or_turns_cover_the_route() -> None:
    brain, v = _plot_view(fighters=98, turns=4)
    assert brain._plot(v, 447, "earn")["args"]["target"] == 447  # 98 is under the tow (99+)
    brain, v = _plot_view(fighters=200, turns=6)
    assert brain._plot(v, 447, "earn")["args"]["target"] == 447  # reaches 447 today


def test_plot_fed_stop_off_under_fed_legacy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(K, "FED_MODE", "legacy")
    brain, v = _plot_view(fighters=200, turns=4)
    assert brain._plot(v, 447, "earn")["args"]["target"] == 447


def test_armed_late_day_steps_by_hand_near_fedspace() -> None:
    # The autopilot uses its own shortest path; near sector 1 the seat walks its known route.
    brain, v = _plot_view(fighters=200, turns=4)
    v.known_warps = {600: (525, 1), 525: (700, 600), 700: (800,), 800: (447,), 1: (600,)}
    v.legal["warp"]["params"]["target"]["choices"] = [525, 1]
    act = brain._plot(v, 447, "earn")
    assert act["kind"] == "warp" and act["args"]["target"] == 525
    v.known_warps = {600: (525,), 525: (700, 600), 700: (800,), 800: (447,)}  # no FedSpace known nearby
    assert brain._plot(v, 447, "earn")["kind"] == "plot_course"
