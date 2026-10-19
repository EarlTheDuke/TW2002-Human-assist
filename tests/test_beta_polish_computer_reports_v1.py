"""COMMANDER NOTE 88: computer reports, rules in force, bank-cap warning, bot float, turn log."""

from __future__ import annotations

import json
import socket
import time
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.agents.bank_brain import full_hold_cash, route_buy_price
from tw2k.agents.external import ExternalAgent
from tw2k.agents.seat_brain import SeatBrain, View
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.models import Player
from tw2k.engine.runner import last_turns_regenerated
from tw2k.server.reference import game_reference

REPO = Path(__file__).resolve().parents[1]
SHOTS = REPO / "docs" / "playtests" / "beta-polish-computer-reports-v1"
REDESIGN = (REPO / "web" / "redesign.js").read_text(encoding="utf-8")
TOK = "n88-e2e-token-p2-000000000000000"


def _la(obs, kind, legal=True, **params):
    obs["legal_actions"] = [row for row in obs["legal_actions"] if row["kind"] != kind]
    obs["legal_actions"].append({
        "kind": kind, "legal": legal, "reason": None, "detail": "precise", "params": params,
    })
    return obs


def _ports():
    return [
        {"sector_id": 5, "stock": {"fuel_ore": {
            "price": 40, "side": "sells_to_player", "current": 100, "max": 200,
        }}},
        {"sector_id": 6, "stock": {"fuel_ore": {
            "price": 80, "side": "buys_from_player", "current": 10, "max": 200,
        }}},
    ]


def test_trader_rankings_were_already_on_the_computer_menu():
    assert '["L", "Trader Rankings", null]' in REDESIGN
    assert "function traderRankings()" in REDESIGN


def test_the_computer_menu_names_the_missing_reports():
    for label in ("Ship Catalog", "Personal Planets", "Planetary Specs", "Daily Log"):
        assert label in REDESIGN
    for name in ("bot.html", "bot.js", "bot-parity.js"):
        text = (REPO / "web" / name).read_text(encoding="utf-8")
        assert "Ship Catalog" not in text
        assert "Rules in force" not in text
        assert "data-bank-warn" not in text


def test_rules_in_force_reads_the_live_numbers(monkeypatch):
    legacy = game_reference(max_days=10)
    section = next(row for row in legacy["sections"] if row["id"] == "rules_in_force")
    assert section["title"] == "Rules in force"
    numbers = {row["name"]: row["value"] for row in section["rows"] if "value" in row}
    assert numbers["Turns per day"] == K.STARTING_TURNS_PER_DAY
    assert numbers["Tax rate"] == f"{K.TAX_RATE_PCT}%"
    assert numbers["Tax threshold"] == K.TAX_THRESHOLD
    assert numbers["Bank cap"] == K.BANK_MAX_BALANCE
    assert numbers["Haggle band"] == f"{K.PORT_HAGGLE_MIN_PCT}% to {K.PORT_HAGGLE_MAX_PCT}% of the offer"
    assert "CITADEL_COST_MODE" in {row["name"] for row in section["rows"] if row.get("on")}
    assert "BOT_BANK_FLOAT_MODE" not in {row["name"] for row in section["rows"] if row.get("on")}

    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    live = game_reference(max_days=10)
    live_section = next(row for row in live["sections"] if row["id"] == "rules_in_force")
    live_numbers = {row["name"]: row["value"] for row in live_section["rows"] if "value" in row}
    rate, over, _align = K.tax_terms()
    assert live_numbers["Tax rate"] == f"{rate}%"
    assert live_numbers["Tax threshold"] == over
    assert live_numbers["Haggle band"] == (
        f"{K.PORT_HAGGLE_LIVE_ROOM_PCT}% to {K.PORT_HAGGLE_LIVE_END_PCT}% of the offer"
    )
    on = {row["name"] for row in live_section["rows"] if row.get("on")}
    assert "BOT_BANK_FLOAT_MODE" in on
    assert "TAX_RULE_MODE" in on


def test_route_hold_cash_is_a_full_hold_at_the_buy_price(monkeypatch):
    brain = SeatBrain()
    obs = {
        "sector": {"id": 5},
        "ship": {"holds": 20, "cargo_free": 20, "class": "merchant_cruiser", "fighters": 10},
        "known_warps": {"5": [6], "6": [5]},
        "known_ports": _ports(),
        "day": 3,
        "legal_actions": [],
    }
    assert brain._route_hold_cash(View(obs)) == 0
    assert full_hold_cash(20, _ports()) == 0
    monkeypatch.setattr(K, "BOT_BANK_FLOAT_MODE", "live")
    assert route_buy_price(_ports()) == 40
    assert brain._route_hold_cash(View(obs)) == 800
    assert full_hold_cash(20, _ports()) == 800
    assert K.BOT_BANK_FLOAT_MODE == "live"


def test_the_float_survives_the_nest_egg_drain(monkeypatch):
    from tw2k.agents.seat_acceptance import synthetic_obs

    obs = synthetic_obs(sector=1, credits=80_000, ship_class="cargotran", day=3)
    obs["alignment"] = 50
    obs["bank_balance"] = 0
    obs["net_worth"] = 80_000
    _la(obs, "buy_equip", item={"choices": [], "unit_price_by": {}})
    _la(obs, "bank_deposit", max_amount=80_000, balance=0, room=500_000)
    monkeypatch.setattr(SeatBrain, "_away_cash", lambda self, v: 5_000)
    monkeypatch.setattr(SeatBrain, "_route_hold_cash", lambda self, v: 0)
    off = SeatBrain().decide(obs)
    assert off["kind"] == "bank_deposit"
    assert off["args"]["amount"] == 75_000

    monkeypatch.setattr(K, "BOT_BANK_FLOAT_MODE", "live")
    monkeypatch.setattr(SeatBrain, "_route_hold_cash", lambda self, v: 40_000)
    on = SeatBrain().decide(obs)
    assert on["kind"] == "bank_deposit"
    assert on["args"]["amount"] == 40_000


def test_heuristic_keeps_the_float_past_the_tax_line(monkeypatch):
    from tw2k.agents.heuristic import HeuristicAgent
    from tw2k.engine.observation import Observation

    ports = [
        {"sector_id": 12, "stock": {"equipment": {
            "price": 6_000, "side": "sells_to_player", "current": 50, "max": 80,
        }}},
        {"sector_id": 13, "stock": {"equipment": {
            "price": 9_000, "side": "buys_from_player", "current": 0, "max": 80,
        }}},
    ]
    base = dict(
        day=3, tick=1, max_days=10, finished=False,
        self_id="P6", self_name="Orion", credits=200_000, alignment=100,
        turns_remaining=40, turns_per_day=40,
        ship={"class": "merchant_cruiser", "fighters": 30, "cargo": {}, "cargo_free": 20, "holds": 20},
        corp_ticker=None, planet_landed=None, scratchpad="",
        sector={"id": 1, "ferrengi": []},
        adjacent=[], known_ports=ports, other_players=[], inbox=[], recent_events=[],
        net_worth=200_000, bank_balance=0, legal_actions=[
            {"kind": "bank_deposit", "legal": True, "params": {"max_amount": 200_000, "room": 500_000}},
        ],
    )
    agent = HeuristicAgent("P6", "Orion", seed=1)
    off = agent._h_bank(Observation(**base), recovery=False)
    assert off is not None and off.kind.value == "bank_deposit"
    assert off.args["amount"] == 190_000

    monkeypatch.setattr(K, "BOT_BANK_FLOAT_MODE", "live")
    agent._h_deposited = False
    on = agent._h_bank(Observation(**base), recovery=False)
    assert on is not None and on.args["amount"] == 80_000


def _warp_world():
    universe = generate_universe(GameConfig(
        seed=7, universe_size=80, max_days=2, turns_per_day=250,
        enable_ferrengi=False, enable_planets=False,
    ))
    sector = next(s for s in universe.sectors.values() if s.warps and s.id > 10)
    player = Player(id="P1", name="A", sector_id=sector.id, turns_per_day=250, turns_today=10)
    universe.players["P1"] = player
    sector.occupant_ids.append("P1")
    return universe, player, sector


def test_a_warp_logs_its_charge_apart_from_the_refill(monkeypatch, tmp_path):
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    monkeypatch.setattr(K, "TURN_REGEN_DAY_SECONDS", 250.0)
    universe, player, sector = _warp_world()
    before = int(player.turns_today)
    player.turn_regen_frac = 0.0
    player.turn_regen_at = time.time() - 1.2
    result = apply_action(universe, player.id, Action(kind=ActionKind.WARP, args={"target": sector.warps[0]}))
    assert result.ok, result.error
    regen = last_turns_regenerated()
    net = int(player.turns_today) - before
    assert result.turns_spent == 3
    assert regen == 1
    assert net == 2
    agent = ExternalAgent("P1", "A", token="t" * 8)
    agent.action_log_path = tmp_path / "external_actions.jsonl"
    agent.record_result(True, None, result.event_seqs, action_kind="warp", auto=False,
                        turns_used=result.turns_spent, turns_regenerated=regen)
    row = json.loads(agent.action_log_path.read_text(encoding="utf-8").splitlines()[-1])
    assert row["event"] == "result"
    assert row["turns_used"] == 3
    assert row["turns_regenerated"] == 1
    assert row["turns_used"] != net


def test_an_auto_wait_logs_its_own_cost_and_the_refill(monkeypatch, tmp_path):
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    monkeypatch.setattr(K, "TURN_REGEN_DAY_SECONDS", 250.0)
    universe, player, _sector = _warp_world()
    before = int(player.turns_today)
    player.turn_regen_frac = 0.0
    player.turn_regen_at = time.time() - 1.2
    result = apply_action(universe, player.id, Action(kind=ActionKind.WAIT, args={}, thought="[external idle] auto-WAIT"))
    assert result.ok, result.error
    regen = last_turns_regenerated()
    net = int(player.turns_today) - before
    assert result.turns_spent == 1
    assert regen == 1
    assert net == 0
    agent = ExternalAgent("P1", "A", token="t" * 8)
    agent.action_log_path = tmp_path / "external_actions.jsonl"
    agent.record_result(True, None, result.event_seqs, action_kind="wait", auto=True,
                        turns_used=result.turns_spent, turns_regenerated=regen)
    row = json.loads(agent.action_log_path.read_text(encoding="utf-8").splitlines()[-1])
    assert row["auto"] is True
    assert row["turns_used"] == 1
    assert row["turns_regenerated"] == 1
    assert row["turns_used"] != net


def _safe_port() -> int:
    for port in (8058, 8053, 8054, 8059, 8052):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("no safe cockpit port")


def test_redesign_reports_rules_and_the_bank_warning(tmp_path, monkeypatch):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    from tests._cu_host import CuHost

    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.setattr("tests._cu_host.free_port", lambda start=8050: _safe_port())
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK, park_at=1, fuel=0) as host, sync() as pw:
        world = host.runner.state.universe
        me = world.players["P2"]
        planet = next(iter(world.planets.values()))
        planet.owner_id = "P2"
        me.bank_balance = 500_000 - 32_992
        me.credits = 80_000
        # The cockpit paints the turn snapshot. Rebuild it after the live edits.
        from tw2k.engine.observation import build_observation

        agent = next(a for a in host.runner.state.agents if a.player_id == "P2")
        agent.current_observation = build_observation(world, "P2")
        browser = pw.chromium.launch()
        try:
            _walk(browser, host, 1280, 800, "1280")
            _walk(browser, host, 390, 844, "390")
            legacy = browser.new_page(viewport={"width": 1280, "height": 800})
            legacy.goto(f"{host.base}/bot?seat=P2&token={TOK}")
            legacy.wait_for_selector("#sbCredits", timeout=20_000)
            assert legacy.locator("text=Ship Catalog").count() == 0
            assert legacy.locator("text=Rules in force").count() == 0
            legacy.close()
        finally:
            browser.close()


def _walk(browser, host, width, height, tag):
    page = browser.new_page(viewport={"width": width, "height": height})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#keys button[data-key=C]", timeout=20_000)
    page.locator("#keys button[data-key=C]").click()
    page.wait_for_selector("#menu[data-screen=computer]", timeout=10_000)
    menu = page.locator("#menu").inner_text()
    for label in ("Ship Catalog", "Personal Planets", "Planetary Specs", "Daily Log", "Trader Rankings"):
        assert label in menu
    page.screenshot(path=str(SHOTS / f"{tag}-computer.png"))
    page.keyboard.press("C")
    page.wait_for_selector("#menu[data-screen=ship-catalog] [data-ship]", timeout=10_000)
    catalog = page.locator("#menu").inner_text()
    assert "cr" in catalog and "turns per warp" in catalog
    page.screenshot(path=str(SHOTS / f"{tag}-catalog.png"))
    page.keyboard.press("Escape")
    page.keyboard.press("C")
    page.keyboard.press("Y")
    page.wait_for_selector("#menu[data-screen=planets] [data-planet]", timeout=10_000)
    page.screenshot(path=str(SHOTS / f"{tag}-planets.png"))
    page.keyboard.press("Escape")
    page.keyboard.press("C")
    page.keyboard.press("J")
    # NOTE 97: J opens the class catalog. Your planets is the path to one world's specs.
    page.wait_for_selector("#menu[data-screen=planet-catalog] [data-planet-class]", timeout=10_000)
    assert "Your planets" in page.locator("#menu").inner_text()
    page.locator("#menu [data-your-planets]").click()
    page.wait_for_selector("#menu[data-screen=planet-specs] [data-spec=Class]", timeout=10_000)
    page.locator("#menu [data-planet-pick]").first.click()
    page.wait_for_selector("#menu[data-screen=planet-specs] [data-spec=Class]", timeout=10_000)
    page.screenshot(path=str(SHOTS / f"{tag}-specs.png"))
    page.keyboard.press("Escape")
    page.keyboard.press("C")
    page.keyboard.press("D")
    page.wait_for_selector("#menu[data-screen=daily-log]", timeout=10_000)
    page.screenshot(path=str(SHOTS / f"{tag}-log.png"))
    page.keyboard.press("Escape")
    page.keyboard.press("Z")
    page.wait_for_selector("#menu[data-screen=rules] [data-rule=number]", timeout=10_000)
    rules = page.locator("#menu").inner_text()
    assert "Rules in force" in rules
    assert "500,000" in rules
    assert "Bank cap" in rules
    page.screenshot(path=str(SHOTS / f"{tag}-rules.png"))
    page.keyboard.press("Escape")
    page.locator("#here button[data-kind=bank]").click()
    page.wait_for_selector("#formSlot input[data-n=amount]", timeout=10_000)
    page.locator("#formSlot input[data-n=amount]").fill("40000")
    page.locator("#formSlot input[data-n=amount]").dispatch_event("input")
    warn = page.locator("[data-bank-warn=cap]")
    page.wait_for_function(
        """() => {
          const el = document.querySelector("[data-bank-warn=cap]");
          return el && !el.hidden && el.textContent.includes("32,992");
        }""",
        timeout=5_000,
    )
    text = warn.inner_text()
    assert "500,000" in text and "32,992" in text and "still fits" in text
    page.locator("#formSlot button", has_text="CONFIRM").click()
    assert page.locator("#formSlot [data-screen=bank]").count() == 1
    page.screenshot(path=str(SHOTS / f"{tag}-bank.png"))
    page.close()
