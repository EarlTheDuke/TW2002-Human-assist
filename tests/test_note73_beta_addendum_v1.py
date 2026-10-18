"""NOTE 73 beta-playtest addendum (Track E).

Each item quotes the live number the receipt or the rule uses. Switches
default to legacy, so a profile-off game stays the old game.

Plants:
  p1 — a stock Merchant Cruiser trade-in drops the holds line and still totals 34,844.
  p2 — the day-cap record labels experience as net worth (reason time_net_worth, planets negative).
  p3 — trader_rankings carries credits or a sector.
  p4 — a finished game stays "running" while a tab is open.
  p5 — buying cargo changes the estimate by the base-price gap.
  p6 — the Terra button opens a form the player cannot see, and stays bright when illegal.
  p7 — a seat with no client auto-WAITs on the short clock.
  p8 — a code bot leaves an alliance proposal unanswered.
  p9 — help text hard-codes a bank cap, a hold price, or an end day.
  p10 — the gear list omits Genesis when the seat has 300 cr.
  p11 — a corporation is described as costing 500,000 while CORP_CREATE_COST is 0.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import tw2k.engine.constants as K
from tw2k.agents.heuristic import HeuristicAgent, _canned_hail
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.match_metrics import build_match_metrics_payload
from tw2k.engine.models import (
    Alliance,
    Commodity,
    EventKind,
    FighterDeployment,
    GameConfig,
    Player,
    ShipClass,
)
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action
from tw2k.engine.universe import generate_universe
from tw2k.engine.victory import check_victory, economic_threshold, end_rule_line, full_net_worth
from tw2k.public.config import LobbyConfig
from tw2k.public.lobby import Lobby, create_lobby_app
from tw2k.public.pages import lobby as lobby_page
from tw2k.server.reference import game_reference

ROOT = Path(__file__).resolve().parents[1]
REDESIGN = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")
APP_JS = (ROOT / "web" / "app.js").read_text(encoding="utf-8")


def _world(seed: int = 73):
    world = generate_universe(
        GameConfig(seed=seed, universe_size=40, enable_ferrengi=False, enable_planets=False)
    )
    return world


def _seat(world, pid: str, *, name: str, credits: int = 20_000, experience: int = 0, alignment: int = 0) -> Player:
    player = Player(
        id=pid, name=name, sector_id=K.STARDOCK_SECTOR, credits=credits,
        turns_per_day=250, experience=experience, alignment=alignment,
    )
    world.players[pid] = player
    world.sectors[K.STARDOCK_SECTOR].occupant_ids.append(pid)
    return player


# --------------------------------------------------------------------------- item 1
def test_part_trade_credit_matches_the_measured_receipts():
    """Stock Merchant Cruiser, 20 holds, 0 fighters = 34,844.
    With 30 start fighters = 39,163 (8,999 + 6,677 + 899 + 18,269 + 4,319).
    Scout Marauder = 12,380. Merchant Freighter = 29,003. Escape Pod = 12,728.
    Holds: 20 -> 6,677, 1 -> 179, 42 -> 21,508, 10 -> 2,528, 30 -> 12,446.
    30 fighters = 4,319.
    """
    assert K.TRADE_IN_PARTS_MODE == "legacy"
    assert K.trade_in_parts_live() is False
    assert K.part_trade_credit(10_000) == 8_999
    assert K.part_trade_credit(160) == 143  # 144 minus the exact tenth
    assert K.hold_trade_value(20) == 6_677
    assert K.hold_trade_value(1) == 179
    assert K.hold_trade_value(42) == 21_508
    assert K.hold_trade_value(10) == 2_528
    assert K.hold_trade_value(30) == 12_446
    assert K.part_trade_credit(160 * 30) == 4_319
    assert K.trade_in_credit("merchant_cruiser") == int(K.ship_cost("merchant_cruiser") * 0.25)


def test_live_parts_use_the_ship_as_it_sits_and_price_the_pod_itself(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.trade_in_parts_live() is True
    stock = K.trade_in_receipt("merchant_cruiser")
    assert stock["holds"] == 6_677
    assert stock["total"] == 34_844
    assert stock["total"] - stock["holds"] != stock["total"]  # a plant that drops the holds line
    armed = K.trade_in_receipt("merchant_cruiser", holds=20, fighters=30)
    assert armed["fighters"] == 4_319
    assert armed["total"] == 39_163
    assert K.trade_in_credit("scout_marauder") == 12_380
    assert K.trade_in_credit("merchant_freighter") == 29_003
    assert K.trade_in_credit(K.ESCAPE_POD) == 12_728
    assert K.trade_in_credit(K.ESCAPE_POD) != K.trade_in_credit("scout_marauder")


def test_ben_cruiser_trades_for_53994_and_the_new_ship_starts_empty(monkeypatch):
    """Ben's 42-hold 30-fighter Cruiser = 53,994. A Colonial Transport costs a net 9,606
    and the new ship has 0 fighters. Cargo that fits stays (UNVERIFIED)."""
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    world = _world()
    player = _seat(world, "P1", name="Ben", credits=20_000)
    player.ship.holds = 42
    player.ship.fighters = 30
    player.ship.shields = 0
    player.ship.cargo[Commodity.FUEL_ORE] = 5
    receipt = K.trade_in_receipt("merchant_cruiser", ship=player.ship)
    assert receipt["holds"] == 21_508
    assert receipt["fighters"] == 4_319
    assert receipt["total"] == 53_994
    assert K.net_hull_cost("merchant_cruiser", "colonial_transport", ship=player.ship) == 9_606
    # Four shields ride the same receipt and leave with the old hull.
    player.ship.shields = 4
    shield_c = K.part_trade_credit(K.SHIELD_TRADE_CATALOG * 4)
    armed = K.trade_in_receipt("merchant_cruiser", ship=player.ship)
    assert armed["shields"] == shield_c
    assert armed["total"] == 53_994 + shield_c
    net = 9_606 - shield_c
    bought = apply_action(
        world, "P1", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "colonial_transport"}),
    )
    assert bought.ok is True, bought.error
    assert player.credits == 20_000 - net
    assert player.ship.fighters == 0
    assert player.ship.shields == 0
    assert player.ship.holds == K.ship_specs()["colonial_transport"]["holds"]
    assert player.ship.cargo[Commodity.FUEL_ORE] == 5
    event = [ev for ev in world.events if ev.kind == EventKind.BUY_SHIP][-1]
    assert event.payload["trade_in"]["total"] == 53_994 + shield_c
    assert event.payload["trade_in"]["holds"] == 21_508
    assert event.payload["new_price"] == 63_600
    assert event.payload["net"] == net
    shown = next(
        row for row in legal_actions(world, "P1") if row.kind == ActionKind.BUY_SHIP
    )
    assert "trade_in_parts" not in shown.params["ship_class"] or shown.params["ship_class"]["trade_in_parts"]["total"] > 0


def test_legacy_buy_keeps_the_fighters_and_omits_the_receipt():
    world = _world(74)
    player = _seat(world, "P1", name="Legacy", credits=500_000)
    player.ship.fighters = 30
    bought = apply_action(
        world, "P1", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "scout_marauder"}),
    )
    assert bought.ok is True, bought.error
    assert player.ship.fighters == 30
    event = [ev for ev in world.events if ev.kind == EventKind.BUY_SHIP][-1]
    assert event.payload["ship_class"] == "scout_marauder"
    assert "net_cost" in event.payload
    assert "trade_in" not in event.payload and "new_price" not in event.payload
    assert "We'll give you" in REDESIGN and "go with the old ship" in REDESIGN


# --------------------------------------------------------------------------- item 2
def _finish(world):
    world.day = world.config.max_days + 1
    check_victory(world)
    return [ev for ev in world.events if ev.kind == EventKind.GAME_OVER][-1]


def test_legacy_day_cap_still_says_time_net_worth():
    world = _world(75)
    _seat(world, "P1", name="Ada", credits=1_000, experience=10)
    _seat(world, "P2", name="Bea", credits=2_000, experience=3)
    ev = _finish(world)
    assert world.win_reason == "time_net_worth"
    assert ev.payload["reason"] == "time_net_worth"
    assert "summary" not in ev.payload
    assert ev.payload["net_worth_planets"] >= 0 or ev.payload["net_worth"] == ev.payload["net_worth_ship"] + ev.payload["net_worth_planets"]
    metrics = build_match_metrics_payload(world.events, winner_id=world.winner_id, win_reason=world.win_reason)
    assert metrics["game_over_summary"] is None


def test_experience_record_names_experience_and_keeps_real_net_worth(monkeypatch):
    monkeypatch.setattr(K, "PLANET_VALUE_SCORE_MODE", "experience")
    world = _world(76)
    world.config.max_days = 10
    guest = _seat(world, "P1", name="Guest 1", credits=100, experience=665)
    orion = _seat(world, "P2", name="Orion", credits=50, experience=120)
    vega = _seat(world, "P3", name="Vega", credits=40, experience=113)
    ev = _finish(world)
    assert world.win_reason == "time_experience"
    assert ev.payload["reason"] == "time_experience"
    assert ev.payload["score_kind"] == "experience"
    assert ev.payload["all_scores"] == {"P1": 665, "P2": 120, "P3": 113}
    assert ev.payload["summary"] == ev.summary
    assert "net_worth" not in ev.payload
    for seat in (guest, orion, vega):
        ship = int(seat.net_worth)
        full = int(full_net_worth(world, seat))
        assert ev.payload["net_worth_ship"][seat.id] == ship
        assert ev.payload["net_worth_planets"][seat.id] == full - ship
        assert ev.payload["net_worth_planets"][seat.id] != seat.experience - seat.credits
    metrics = build_match_metrics_payload(world.events, winner_id=world.winner_id, win_reason=world.win_reason)
    assert metrics["game_over_summary"] == ev.summary
    assert "wins on experience (665)" in ev.summary


# --------------------------------------------------------------------------- item 3
def test_rankings_list_every_seat_by_experience_and_hide_credits(monkeypatch):
    monkeypatch.setattr(K, "TRADER_RANK_LIST_MODE", "live")
    monkeypatch.setattr(K, "PLANET_VALUE_SCORE_MODE", "experience")
    world = _world(77)
    world.config.max_days = 10
    _seat(world, "P1", name="Guest 1", experience=665)
    _seat(world, "P2", name="Orion", experience=120)
    _seat(world, "P3", name="Vega", experience=113)
    world.players["P2"].corp_ticker = "ORX"
    obs = build_observation(world, "P1")
    rows = obs.trader_rankings
    assert [row["name"] for row in rows] == ["Guest 1", "Orion", "Vega"]
    assert [row["experience"] for row in rows] == [665, 120, 113]
    assert rows[0]["rank"] == 1 and rows[0]["title"] and rows[0]["ship"] and rows[0]["alive"] is True
    assert rows[1]["corp"] == "ORX"
    for row in rows:
        assert "credits" not in row and "net_worth" not in row and "sector" not in row
    assert "Day 10" in obs.end_rule and "33,333,333" in obs.end_rule
    assert economic_threshold(10) == 33_333_333
    assert "most experience" in end_rule_line(10)
    assert "Day 30" in end_rule_line(30) and "100,000,000" in end_rule_line(30)
    monkeypatch.setattr(K, "PLANET_VALUE_SCORE_MODE", "legacy")
    assert "highest net worth" in end_rule_line(30)
    monkeypatch.setattr(K, "PLANET_VALUE_SCORE_MODE", "experience")
    _finish(world)
    done = build_observation(world, "P1")
    panel = done.game_over_panel
    assert panel.startswith("GAME OVER - time ran out after day 10. Decided by experience:")
    assert "1st Guest 1 665" in panel and "2nd Orion 120" in panel and "3rd Vega 113" in panel
    assert "You finished 1st of 3." in panel
    assert "Trader Rankings" in REDESIGN and "rankToggle" in REDESIGN
    assert "time_experience" in APP_JS and "wins by experience" in APP_JS


def test_rankings_stay_off_the_observation_until_the_switch_is_on():
    world = _world(78)
    _seat(world, "P1", name="Ada", experience=5)
    dumped = build_observation(world, "P1").model_dump()
    assert "trader_rankings" not in dumped
    assert "end_rule" not in dumped
    assert "game_over_panel" not in dumped
    assert "credits" in dumped  # the seat's own purse is unchanged


def test_help_end_line_follows_max_days():
    short = game_reference(max_days=10)
    long = game_reference(max_days=12)
    rules = next(row["body"] for row in short["sections"] if row["id"] == "rules")
    other = next(row["body"] for row in long["sections"] if row["id"] == "rules")
    assert "Day 10" in rules and "33,333,333" in rules
    assert "Day 12" in other and "Day 10" not in other
    assert [row["id"] for row in short["sections"]] == ["rules", "scoring", "ranks", "ships", "prices"]


# --------------------------------------------------------------------------- item 4
class _FakeWorker:
    def __init__(self) -> None:
        self.port = 1
        self.pid = 9
        self.stopping = False
        self.up = True

    def alive(self) -> bool:
        return self.up


def test_lobby_marks_a_finished_game_while_the_tab_is_open(tmp_path, monkeypatch):
    cfg = LobbyConfig(root=tmp_path / "lobby", port=47271, game_ports=range(47272, 47280), tick_s=3600.0, idle_s=30.0)
    lob = Lobby(cfg)
    lob.store.add_game(
        "g73", name="Done", creator="host", listed=True, seats=["P1"],
        settings={"humans": 1, "rules": "v311", "universe_size": 40, "day_seconds": 60, "bots": 0},
    )
    lob.store.set_game("g73", status="running", last_activity=10**12)
    lob.workers.workers["g73"] = _FakeWorker()
    lob.open_ws["g73"] = 1

    class _Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url):
            return type("R", (), {"status_code": 200, "json": lambda self: {"finished": True}})()

    monkeypatch.setattr("tw2k.public.lobby.httpx.AsyncClient", _Client)

    async def _stop(gid, **kwargs):
        lob.workers.workers[gid].up = False

    lob.workers.stop = _stop
    asyncio.run(lob.tick())
    assert lob.store.game("g73")["status"] == "finished"
    assert lob.workers.workers["g73"].alive() is True
    assert lob.live_games() == 0
    assert lob._worker_serves(lob.store.game("g73")) is True
    # Idle, no tab: the worker stops and the status stays finished.
    lob.open_ws["g73"] = 0
    lob.activity["g73"] = 0.0
    lob.store.set_game("g73", status="finished", last_activity=0.0)
    cfg.idle_s = 1.0
    asyncio.run(lob.tick())
    assert lob.store.game("g73")["status"] == "finished"
    assert lob.workers.workers["g73"].alive() is False


def test_game_root_redirects_to_the_watch_page(tmp_path):
    """A bare /g/<id> link opens the watch gate. /g/<id>/ stays the spectator page
    (the gate redirects there after the cookie), so it is not sent back to /watch."""
    from starlette.testclient import TestClient

    cfg = LobbyConfig(root=tmp_path / "lobby2", port=47281, game_ports=range(47282, 47290), tick_s=3600.0)
    app = create_lobby_app(cfg, port_probe=lambda _p: True)
    with TestClient(app) as client:
        bare = client.get("/g/abcd", follow_redirects=False)
        slash = client.get("/g/abcd/", follow_redirects=False)
    assert bare.status_code == 307 and bare.headers["location"].endswith("/g/abcd/watch")
    assert slash.status_code != 307


# --------------------------------------------------------------------------- item 5
def test_estimate_follows_what_was_paid_and_legacy_does_not(monkeypatch):
    world = _world(79)
    player = _seat(world, "P1", name="Ada", credits=10_000)
    player.ship.fighters = 30
    player.ship.holds = 20
    before = player.net_worth
    paid = 40
    qty = 10
    player.credits -= paid * qty
    player.ship.cargo[Commodity.EQUIPMENT] = qty
    player.ship.cargo_cost[Commodity.EQUIPMENT] = float(paid)
    legacy_delta = player.net_worth - before
    base = int(K.COMMODITY_BASE_PRICE["equipment"])
    assert legacy_delta == qty * base - paid * qty
    monkeypatch.setattr(K, "NW_ESTIMATE_MODE", "live")
    # Recompute from the same purse: credits already reduced, cargo at the paid average.
    paid_worth = player.net_worth
    empty = _seat(world, "P9", name="Empty", credits=10_000 - paid * qty)
    empty.ship.fighters = 30
    empty.ship.holds = 20
    assert paid_worth - empty.net_worth == paid * qty  # buying the cargo moved the estimate by 0
    hold_price = K.hold_next_price(player.ship.ship_class.value, player.ship.holds, 1)
    held = player.net_worth
    player.credits -= hold_price
    player.ship.holds += 1
    marginal = K.hold_trade_value(21) - K.hold_trade_value(20)
    assert player.net_worth - held == marginal - hold_price
    sector = world.sectors[K.STARDOCK_SECTOR]
    carried = full_net_worth(world, player)
    moved = 10
    player.ship.fighters -= moved
    sector.fighters = FighterDeployment(owner_id=player.id, count=moved)
    assert full_net_worth(world, player) - (carried - moved * K.nw_fighter_value()) == moved * K.nw_fighter_value()
    ref = game_reference()
    scoring = next(row["body"] for row in ref["sections"] if row["id"] == "scoring")
    assert K.NW_ESTIMATE_NOTE in scoring
    assert "nw_note" in REDESIGN


def test_legacy_estimate_omits_the_note():
    world = _world(80)
    _seat(world, "P1", name="Ada")
    dumped = build_observation(world, "P1").model_dump()
    assert "nw_note" not in dumped


# --------------------------------------------------------------------------- item 6
def test_terra_form_is_brought_into_view_and_greys_when_illegal():
    assert "function reveal(" in REDESIGN
    assert "Terra (1 turn, take or leave colonists)" in REDESIGN
    assert 'terraBtn.disabled = true' in REDESIGN
    assert "scrollIntoView" in REDESIGN


# --------------------------------------------------------------------------- item 7
def test_tokenless_copy_and_reopen_stay_in_the_claiming_browser():
    assert "This seat needs its join link" in REDESIGN
    assert "missing bearer token" in REDESIGN  # the cockpit maps the API string; it does not replace it
    assert "fragmentToken" in REDESIGN
    assert "tw2k-my-seats" in REDESIGN
    html = lobby_page("Galaxy War Command", games=[], mine=[], closed=False, full=False, live={})
    assert "Re-open my seat" in html
    assert "tw2k-my-seats" in html
    assert "example-token" not in html
    assert "#token=" in html  # the link is built in the browser, from localStorage


def test_unconnected_seat_does_not_auto_wait(tmp_path, monkeypatch):
    """No auto-WAIT before the first connect. The short clock starts after touch_client."""
    monkeypatch.setattr(K, "SEAT_IDLE_START_MODE", "live")
    from tw2k.agents.external import ExternalAgent
    from tw2k.engine.models import EventKind as EK
    from tw2k.server.broadcaster import Broadcaster
    from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec

    spec = MatchSpec(
        config=GameConfig(
            seed=11, universe_size=40, max_days=2, turns_per_day=8, starting_credits=5_000,
            enable_ferrengi=False, enable_planets=False, action_delay_s=0.0,
        ),
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="Here", kind="external", external_token="note73-p2-token-000000"),
            AgentSpec(player_id="P3", name="Away", kind="external", external_token="note73-p3-token-000000"),
        ],
        action_delay_s=0.0,
        external_timeout_s=30.0,
        external_idle_wait_s=0.2,
        external_attend_window_s=45.0,
    )
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")

    async def go() -> None:
        await runner.start(spec)
        for _ in range(200):
            if runner.state.agents and runner.state.universe is not None:
                break
            await asyncio.sleep(0.02)
        universe = runner.state.universe
        p2 = next(a for a in runner.state.agents if a.player_id == "P2")
        assert isinstance(p2, ExternalAgent)
        p2.touch_client()
        for _ in range(200):
            if p2.awaiting_input:
                break
            await asyncio.sleep(0.02)
        assert p2.awaiting_input
        await p2.submit_action(Action(kind=ActionKind.WAIT), turn_seq=p2.turn_seq)
        await asyncio.sleep(0.6)
        idle = [
            ev for ev in universe.events
            if ev.kind == EK.AGENT_THOUGHT and ev.actor_id == "P3" and (ev.payload or {}).get("external_idle")
        ]
        assert idle == []
        await runner.stop()

    asyncio.run(go())


# --------------------------------------------------------------------------- item 8
def _pair(monkeypatch, *, on: bool):
    if on:
        monkeypatch.setattr(K, "BOT_DIPLOMACY_MODE", "live")
    world = _world(81)
    me = _seat(world, "P1", name="Code", alignment=20, experience=10)
    them = _seat(world, "P2", name="Guest", alignment=15, experience=4)
    me.agent_kind = "heuristic"
    them.agent_kind = "external"
    world.alliances["A1"] = Alliance(
        id="A1", member_ids=["P2", "P1"], proposed_by="P2", formed_day=world.day, active=False,
    )
    bot = HeuristicAgent(player_id="P1", name="Code")
    bot._tw_universe = world
    return world, me, them, bot


def test_code_bot_answers_a_proposal_on_its_turn(monkeypatch):
    world, me, them, bot = _pair(monkeypatch, on=True)
    action = asyncio.run(bot.act(build_observation(world, "P1")))
    assert action.kind == ActionKind.ACCEPT_ALLIANCE
    assert action.args["alliance_id"] == "A1"
    them.alignment = -5
    bot._diplo_answered.clear()
    declined = asyncio.run(bot.act(build_observation(world, "P1")))
    assert declined.kind == ActionKind.BREAK_ALLIANCE
    world.events.append(type(world.events[0])(
        seq=10_000, tick=1, day=1, kind=EventKind.COMBAT, actor_id="P2",
        payload={"exchange_kind": "ship_vs_ship", "defender": "P1", "attacker": "P2"},
        summary="attack",
    ))
    me.alignment = 20
    them.alignment = 15
    bot._diplo_answered.clear()
    attacked = asyncio.run(bot.act(build_observation(world, "P1")))
    assert attacked.kind == ActionKind.BREAK_ALLIANCE
    assert "attacked" in (attacked.thought or "")
    me.inbox.append({"from": "P2", "kind": "hail", "message": "hello", "day": 1, "tick": 1})
    world.alliances.clear()
    bot._diplo_answered.clear()
    hail = asyncio.run(bot.act(build_observation(world, "P1")))
    assert hail.kind == ActionKind.HAIL
    assert hail.args["message"] == _canned_hail(world, me, me.inbox[-1])
    assert hail.args["message"] == _canned_hail(world, me, me.inbox[-1])
    dumped = build_observation(world, "P2").model_dump()
    assert "P1" in dumped["code_bots"]
    assert "(code bot)" in REDESIGN


def test_code_bot_ignores_diplomacy_when_the_switch_is_off(monkeypatch):
    world, _me, _them, bot = _pair(monkeypatch, on=False)
    action = asyncio.run(bot.act(build_observation(world, "P1")))
    assert action.kind not in (ActionKind.ACCEPT_ALLIANCE, ActionKind.BREAK_ALLIANCE, ActionKind.HAIL)
    dumped = build_observation(world, "P1").model_dump()
    assert "code_bots" not in dumped


# --------------------------------------------------------------------------- item 9
def test_help_numbers_come_from_the_engine(monkeypatch):
    legacy = game_reference(max_days=10)
    body = next(row["body"] for row in legacy["sections"] if row["id"] == "rules")
    assert f"{K.BANK_MAX_BALANCE:,}" in body
    assert f"{int(K.PORT_REGEN_PER_DAY * 100)}% per day" in body
    assert f"{K.hold_next_price('merchant_cruiser', 0, 1):,}" in body
    assert f"{K.TRICRON_ANTE:,}" in body and str(K.TRICRON_ROUNDS) in body
    assert f"{K.TRICRON_OPENING_JACKPOT:,}" in body and "2:1" in body
    assert "of " in REDESIGN and "capacity" in REDESIGN
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    live = game_reference(max_days=10)
    live_body = next(row["body"] for row in live["sections"] if row["id"] == "rules")
    assert "550 + 20 * (holds already owned - 20)" in live_body
    assert f"{K.hold_next_price('merchant_cruiser', 0, 1):,}" in live_body
    assert "most experience" in live_body
    assert "Ante " in REDESIGN and "Pays 2:1" in REDESIGN


# --------------------------------------------------------------------------- item 10
def test_unaffordable_genesis_stays_on_the_price_list():
    world = _world(82)
    player = _seat(world, "P1", name="Thin", credits=300)
    buy = next(row for row in legal_actions(world, player.id) if row.kind == ActionKind.BUY_EQUIP)
    prices = buy.params["item"]["unit_price_by"]
    assert "genesis" in prices
    assert "genesis" not in buy.params["item"]["choices"]
    assert prices["genesis"] == K.genesis_torpedo_cost()
    assert "function gearOptions" in REDESIGN
    assert "need " in REDESIGN and "have " in REDESIGN


# --------------------------------------------------------------------------- item 11
def test_a_corporation_is_not_priced_at_500000_while_it_is_free():
    assert K.CORP_CREATE_COST == 0
    text = (ROOT / "src" / "tw2k" / "engine" / "constants.py").read_text(encoding="utf-8")
    assert "REPORT.md line 279" in text
    ref = game_reference()
    blob = " ".join(str(row.get("body") or "") for row in ref["sections"])
    assert "A corporation costs nothing." in blob
    for sentence in blob.split("."):
        if "corporation" in sentence.lower():
            assert "500" not in sentence
    assert "500,000" not in REDESIGN or "corporation" not in REDESIGN.lower().split("500,000")[0][-80:]
