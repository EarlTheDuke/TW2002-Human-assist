"""NOTE 92 code-bot-upgrades-v1.

Item 4 (answer a hail or an alliance) is already BOT_DIPLOMACY_MODE.
HeuristicAgent._diplomacy answers one hail or one proposal on the bot's turn,
and tests/test_note73_beta_addendum_v1.py::test_code_bot_answers_a_proposal_on_its_turn
covers it. No new switch.
"""

from __future__ import annotations

import asyncio

import tw2k.engine.constants as K
from scripts.run_scripted_match import run_match
from tw2k.agents.bot_upgrades import (
    dock_step,
    escape_course,
    ferrengi_loss_sectors,
    recovery_course,
)
from tw2k.agents.heuristic import HeuristicAgent
from tw2k.agents.seat_brain import SeatBrain, View
from tw2k.engine import ActionKind, GameConfig, generate_universe
from tw2k.engine.models import Player, Ship, ShipClass
from tw2k.engine.observation import build_observation


def _world(seed: int = 92):
    return generate_universe(GameConfig(
        seed=seed, universe_size=40, max_days=3, turns_per_day=40,
        starting_credits=20_000, enable_ferrengi=False, enable_planets=False,
    ))


def _seat(u, *, sector=1, holds=20, fighters=30, credits=200_000, pid="P1"):
    player = Player(
        id=pid, name="Code",
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=fighters, shields=0, holds=holds),
        sector_id=sector, credits=credits, alignment=100, experience=0, turns_per_day=40,
    )
    u.players[pid] = player
    row = u.sectors[sector]
    if pid not in row.occupant_ids:
        row.occupant_ids.append(pid)
    return player


def _move(u, player, sector_id: int) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = sector_id
    dest = u.sectors[sector_id]
    if player.id not in dest.occupant_ids:
        dest.occupant_ids.append(player.id)


def _act(bot, obs):
    return asyncio.run(bot.act(obs))


def test_upgrade_buys_holds_then_a_bigger_hull_only_when_on(monkeypatch):
    assert K.BOTS_UPGRADE_MODE == "legacy"
    assert K.bots_upgrade_live() is False
    world = _world()
    player = _seat(world, holds=20, credits=200_000)
    obs = build_observation(world, player.id)
    off = _act(HeuristicAgent("P1", "Code", seed=1), obs)
    assert not (off.kind == ActionKind.BUY_EQUIP and off.args.get("item") == "holds")

    monkeypatch.setattr(K, "BOTS_UPGRADE_MODE", "live")
    bought = _act(HeuristicAgent("P1", "Code", seed=1), obs)
    assert bought.kind == ActionKind.BUY_EQUIP
    assert bought.args["item"] == "holds"
    assert bought.args["qty"] >= 1
    assert "fighters" not in str(bought.args.get("item"))

    player.ship.holds = int(obs.ship["hold_cap"])
    rich = build_observation(world, player.id)
    hull = _act(HeuristicAgent("P1", "Code", seed=1), rich)
    assert hull.kind == ActionKind.BUY_SHIP
    assert hull.args["ship_class"] in ("merchant_freighter", "cargotran", "colonial_transport")
    # Short of the net cost: do not sell the fighter stack to make the hull affordable.
    player.ship.holds = int(obs.ship["hold_cap"])
    player.credits = 1_000
    player.ship.fighters = 40
    poor = build_observation(world, player.id)
    step = dock_step(
        here=1, class_key="merchant_cruiser", holds=int(poor.ship["holds"]),
        max_holds=int(poor.ship["hold_cap"]), fighters=40, credits=1_000, day=1,
        legal_actions=poor.legal_actions,
    )
    assert step is None or step["kind"] != "buy_ship"


def test_upgrade_switch_off_leaves_the_dock_step_empty():
    step = dock_step(
        here=1, class_key="merchant_cruiser", holds=20, max_holds=75, fighters=30,
        credits=200_000, day=1, legal_actions=[{
            "kind": "buy_equip", "legal": True,
            "params": {"item": {"choices": ["holds"], "max_by": {"holds": 55}}},
        }],
    )
    assert step is None


def test_ferrengi_recovery_plots_to_dock_and_avoids_the_sector(monkeypatch):
    assert recovery_course(here=12, holds=4, plot_legal=True, warp_legal=True) is None
    events = [{
        "kind": "ferrengi_tribute", "day": 4, "sector_id": 77, "actor_id": "P1",
        "facts": {"holds_stolen": 5, "victim": "P1"},
    }]
    assert ferrengi_loss_sectors(events, 4, "P1") == set()

    monkeypatch.setattr(K, "BOTS_FERRENGI_RECOVERY_MODE", "live")
    course = recovery_course(here=12, holds=4, plot_legal=True, warp_legal=True)
    assert course["kind"] == "plot_course"
    assert course["args"]["target"] == 1
    assert recovery_course(here=1, holds=4, plot_legal=True, warp_legal=True) is None
    assert recovery_course(here=12, holds=10, plot_legal=True, warp_legal=True) is None
    assert ferrengi_loss_sectors(events, 4, "P1") == {77}
    assert ferrengi_loss_sectors(events, 7, "P1") == set()

    from tw2k.engine.models import EventKind

    world = _world(93)
    player = _seat(world, sector=1, holds=20, credits=5_000, fighters=10)
    home = next(
        s for s in world.sectors.values()
        if s.id > 10 and len(s.warps) >= 2 and s.port is None
    )
    _move(world, player, home.id)
    loss = int(home.warps[0])
    other = int(home.warps[1])
    world.emit(
        EventKind.FERRENGI_TRIBUTE, actor_id="P1", sector_id=loss,
        payload={"holds_stolen": 5, "ferr_id": "F1"}, summary="tribute",
    )
    obs = build_observation(world, player.id)
    bot = HeuristicAgent("P1", "Code", seed=1)
    for wid in home.warps:
        bot._visit_counts[int(wid)] = 9
    bot._visit_counts[loss] = 0
    action = _act(bot, obs)
    assert action.kind == ActionKind.WARP
    assert int(action.args["target"]) != loss
    assert int(action.args["target"]) == other or int(action.args["target"]) not in (loss,)


def test_escape_plots_out_of_a_dead_end_only_when_on(monkeypatch):
    trail = [(8, False), (9, False)] * 10
    assert escape_course(
        here=8, adjacent_ids=[9], last_from=9, trail=trail, plot_legal=True, warp_legal=True,
    ) is None
    monkeypatch.setattr(K, "BOTS_ESCAPE_MODE", "live")
    dead = escape_course(
        here=8, adjacent_ids=[], last_from=9, trail=[], plot_legal=True, warp_legal=True,
    )
    assert dead["kind"] == "plot_course"
    assert dead["args"]["target"] == 1
    loop = escape_course(
        here=8, adjacent_ids=[9], last_from=9, trail=trail, plot_legal=True, warp_legal=True,
    )
    assert loop["kind"] == "plot_course"
    trading = [(8, True), (9, False)] * 10
    assert escape_course(
        here=8, adjacent_ids=[9], last_from=9, trail=trading, plot_legal=True, warp_legal=True,
    ) is None


def test_seat_brain_upgrade_hook_stays_quiet_until_the_switch(monkeypatch):
    brain = SeatBrain()
    obs = {
        "sector": {"id": 1}, "credits": 200_000, "day": 1, "self_id": "P1",
        "ship": {"class": "merchant_cruiser", "holds": 20, "hold_cap": 75, "fighters": 30, "cargo": {}},
        "legal_actions": [{
            "kind": "buy_equip", "legal": True,
            "params": {"item": {"choices": ["holds"], "max_by": {"holds": 55},
                                "unit_price_by": {"holds": 500}}},
        }, {
            "kind": "buy_ship", "legal": True,
            "params": {"ship_class": {"choices": ["cargotran"], "net_cost_by": {"cargotran": 20_000},
                                      "blocked_by": {}}},
        }],
    }
    assert brain._note92_dock(View(obs)) is None
    assert brain._note92_move(View({**obs, "sector": {"id": 12}, "ship": {**obs["ship"], "holds": 4}})) is None
    monkeypatch.setattr(K, "BOTS_UPGRADE_MODE", "live")
    step = brain._note92_dock(View(obs))
    assert step["kind"] == "buy_equip"
    assert step["args"]["item"] == "holds"


def _stuck_days(rows: list, days: list) -> list[int]:
    """A day with no trade that also holds a 20-action one- or two-sector loop."""
    by_day: dict[int, list] = {}
    for row, day in zip(rows, days, strict=True):
        by_day.setdefault(int(day), []).append(row)
    stuck: list[int] = []
    for day, chunk in by_day.items():
        if any(row[1] == "trade" for row in chunk):
            continue
        if len(chunk) < 20:
            continue
        for i in range(0, len(chunk) - 19):
            window = chunk[i:i + 20]
            kinds = [row[1] for row in window]
            if len({row[0] for row in window}) <= 2 and all(
                k in ("warp", "plot_course", "wait") for k in kinds
            ):
                stuck.append(day)
                break
    return stuck


def test_profile_on_day_10_holds_and_no_dead_end_day(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    result = run_match(["N3", "N2", "N1", "H"], seed=250925, days=10, include_rows=True)
    for row in result["players"].values():
        assert int(row["holds"]) >= 10, row
        assert _stuck_days(row["rows"], row["row_days"]) == [], row["name"]
