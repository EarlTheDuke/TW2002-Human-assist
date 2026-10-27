"""COMMANDER NOTE 104. Lobby overlay, empty selling ports, and the finished line.

Engine defaults stay legacy. The overlay is what a new lobby game turns on.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.models import Commodity, PortClass
from tw2k.public import pages
from tw2k.public import workers as WM
from tw2k.public.security import parse_game_form
from tw2k.public.worker import health_payload

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]


def _settings(rules: str, package: str = "classic") -> dict:
    return parse_game_form({"name": "Alpha", "rules": rules, "starting_package": package}).settings()


def _selling_and_buying(seed: int = 1620537492):
    universe = generate_universe(GameConfig(
        seed=seed, universe_size=200, max_days=10, turns_per_day=250,
        enable_ferrengi=False, enable_planets=False,
    ))
    selling = []
    buying = []
    for sector in universe.sectors.values():
        port = sector.port
        if port is None:
            continue
        # Class 0 decorative ports and StarDock have no trade book.
        if int(port.class_id) in (int(PortClass.FEDERAL), int(PortClass.STARDOCK)):
            continue
        for commodity in (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT):
            stock = port.stock.get(commodity)
            if stock is None:
                continue
            if port.sells(commodity):
                selling.append(int(stock.current) == int(stock.maximum) and int(stock.maximum) > 0)
            elif port.buys(commodity):
                buying.append(int(stock.current))
    return selling, buying


def test_switch_overlay_for_legacy_and_v311() -> None:
    legacy = WM.switch_overlay(_settings("legacy"))
    assert legacy["PORT_STOCK_FIDELITY_MODE"] == "live"
    assert legacy["LEGACY_DAY_CLOCK_MODE"] == "live"
    assert legacy["SEAT_IDLE_START_MODE"] == "live"
    assert legacy["V311_PROFILE"] == "legacy"  # R-4: the stored default is v311
    package = WM.switch_overlay(_settings("legacy", "v311"))
    assert package["STARTING_PACKAGE_MODE"] == "live"
    assert package["PORT_STOCK_FIDELITY_MODE"] == "live"
    assert package["LEGACY_DAY_CLOCK_MODE"] == "live"
    v311 = WM.switch_overlay(_settings("v311", "v311"))
    assert v311 == {
        "DAY_ROLL_CLOCK_MODE": "live",
        "LEGACY_DAY_CLOCK_MODE": "live",
        "V311_PROFILE": "v311",
    }


def test_legacy_overlay_opens_every_selling_side_full(monkeypatch) -> None:
    overlay = WM.switch_overlay(_settings("legacy"))
    monkeypatch.setattr(K, "PORT_STOCK_FIDELITY_MODE", overlay["PORT_STOCK_FIDELITY_MODE"])
    selling, buying = _selling_and_buying()
    assert selling and all(selling)
    assert buying and set(buying) == {0}


def test_engine_default_still_opens_selling_sides_empty() -> None:
    assert K.PORT_STOCK_FIDELITY_MODE == "legacy"
    assert K.PORT_START_STOCK_PERCENT == 0
    selling, _buying = _selling_and_buying()
    assert selling and not any(selling)


def test_new_game_form_names_the_port_open_and_the_hold() -> None:
    html = pages.new_game("Galaxy War Command")
    assert "Ports open full and restock 5% of max each dawn." in html
    assert 'id="rulesPortHint"' in html
    assert 'id="hold_until_human"' in html and "checked" in html
    held = parse_game_form({"name": "Alpha", "rules": "legacy", "hold_until_human": "on"})
    assert held.hold_until_human is True
    assert "--hold-until-human" in WM.serve_command(held.settings(), 8101, ROOT)


def _game(**extra) -> dict:
    settings = {
        "rules": "legacy", "universe_size": 200, "day_seconds": 600, "bots": 3,
        "humans": 1, "max_days": 10, "turns_per_day": 250,
    }
    settings.update(extra.pop("settings", {}))
    base = {
        "id": "2aaa6308", "name": "Playtest", "status": "running", "open_seats": 0,
        "listed": True, "settings": settings,
    }
    base.update(extra)
    return base


def test_a_finished_ten_day_game_names_the_winner() -> None:
    info = {
        "day": 11, "finished": True, "winner": "Guest 1", "win_reason": "time_net_worth",
    }
    html = pages.lobby(
        "Galaxy War Command", games=[_game()], mine=[], owned=[], closed=False, full=False,
        live={"2aaa6308": info},
    )
    assert "finished, day 10 of 10, winner Guest 1 (time_net_worth)" in html
    assert "day 11" not in html
    running = pages.lobby(
        "Galaxy War Command", games=[_game()], mine=[], owned=[], closed=False, full=False,
        live={"2aaa6308": {"day": 4, "finished": False, "winner": None, "win_reason": None}},
    )
    assert "day 4" in running
    assert "finished, day" not in running
    done = _game(status="finished")
    finished_page = pages.lobby(
        "Galaxy War Command", games=[], mine=[done], owned=[], closed=False, full=False,
        live={"2aaa6308": info},
    )
    assert "finished, day 10 of 10, winner Guest 1 (time_net_worth)" in finished_page


def test_healthz_names_the_winner_when_the_engine_has_finished() -> None:
    player = SimpleNamespace(name="Guest 1", turns_per_day=250)
    universe = SimpleNamespace(
        finished=True, day=11, win_reason="time_experience", winner_id="P1",
        players={"P1": player},
    )
    runner = SimpleNamespace(
        state=SimpleNamespace(status="running", universe=universe),
        _spec=None,
        _hold_until_human=False,
    )
    body = health_payload(runner)
    assert body["finished"] is True
    assert body["status"] == "running"
    assert body["day"] == 11
    assert body["winner"] == "Guest 1"
    assert body["win_reason"] == "time_experience"
    universe.finished = False
    universe.win_reason = ""
    universe.winner_id = None
    quiet = health_payload(runner)
    assert quiet["finished"] is False
    assert quiet["winner"] is None
    assert quiet["win_reason"] is None
