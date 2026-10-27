"""NOTE 129. Measured StarDock prices stay behind legacy-default switches.

Captures, 19 Oct 2026, TWGS v2.20b / TW2002 3.34b, TW Test Game 2:
docs/playtests/twgs-live/stardock-menus.txt, name-change.txt, illegal-goods.txt.

The stored drink, food, shield, and cineplex prices do not move. V311_PROFILE
turns the measured prices on. The string "1" does not. TW2002_LIVE_PROFILE does
not. Fighters at 218 that day stay on the wave. The library and the singles bar
stay unbuilt.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests.test_tw2002_live_profile_v1 import HELPERS
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]
MENUS = ROOT / "docs" / "playtests" / "twgs-live" / "stardock-menus.txt"
NAME = ROOT / "docs" / "playtests" / "twgs-live" / "name-change.txt"
GOODS = ROOT / "docs" / "playtests" / "twgs-live" / "illegal-goods.txt"

MODES = (
    ("SHIELD_POINT_MODE", "shield_point_live"),
    ("TAVERN_BAR_PRICE_MODE", "tavern_bar_price_live"),
    ("CINEPLEX_PRICE_MODE", "cineplex_price_live"),
)


def _capture() -> tuple[str, str, str]:
    return (
        MENUS.read_text(encoding="utf-8"),
        NAME.read_text(encoding="utf-8"),
        GOODS.read_text(encoding="utf-8"),
    )


def _world():
    return generate_universe(GameConfig(
        seed=3, universe_size=20, max_days=6, enable_planets=False, enable_ferrengi=False,
    ))


def _seat(universe, *, credits=1_000, experience=1, name="N129Cur"):
    player = Player(
        id="P1", name=name, ship=Ship(), credits=credits,
        sector_id=int(K.STARDOCK_SECTOR), experience=experience, alignment=0,
    )
    universe.players["P1"] = player
    universe.sectors[int(K.STARDOCK_SECTOR)].occupant_ids.append("P1")
    return player


def _kinds(universe):
    return {row.kind: row for row in legal_actions(universe, "P1")}


def test_captures_print_the_measured_numbers() -> None:
    menus, name, goods = _capture()
    assert "131 credits per point" in menus
    assert "218 credits per fighter" in menus
    assert "It'll be 80 credits" in menus
    assert "24 credits/plate" in menus
    assert "100 credit charge for posting an announcement" in menus
    assert "Credits 228, then 96." in menus
    assert 228 - 96 == 132
    assert "total unknown" in name
    assert "new identity for 100 credits" in name
    assert "100 Credits Please" in goods
    assert "Vulcan Thunder" in goods
    assert "fell by 47" in goods
    assert "no goods for sale" in goods.lower() or "sells no good" in goods.lower() or "no goods" in goods.lower()


def test_stored_prices_stay_and_one_does_not_flip(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    assert K.TAVERN_DRINK_COST == 20
    assert K.TAVERN_FOOD_COST == 20
    assert K.TAVERN_ANNOUNCE_COST == 100
    assert K.CINEPLEX_COST == 0
    assert K.UG_NAME_CHANGE is False
    assert K.tavern_drink_cost() == 20
    assert K.tavern_food_cost() == 20
    assert K.cineplex_cost() == 0
    assert K.shield_unit_price(1) != K.shield_unit_price(9)
    assert 160 <= K.shield_unit_price(1) <= 239
    for mode, helper in MODES:
        assert getattr(K, mode) == "legacy"
        assert getattr(K, helper)() is False
        assert helper not in HELPERS
        monkeypatch.setattr(K, mode, "1")
        assert getattr(K, helper)() is False
        monkeypatch.setattr(K, mode, "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    for _mode, helper in MODES:
        assert getattr(K, helper)() is False


def test_v311_profile_uses_the_measured_prices_without_moving_the_flags(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    for mode, _helper in MODES:
        monkeypatch.setattr(K, mode, "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    for mode, helper in MODES:
        assert getattr(K, mode) == "legacy"
        assert getattr(K, helper)() is True
        assert K.V311_PROFILE_HELPERS[helper][0] == mode
    assert K.shield_unit_price(1) == 131
    assert K.shield_unit_price(9) == 131
    assert K.SHIELD_POINT_LIVE == 131
    assert K.tavern_drink_cost() == 80
    assert K.tavern_food_cost() == 24
    assert K.cineplex_cost() == 100
    assert K.fighter_unit_price(1) != K.fighter_unit_price(9)
    assert K.UG_NAME_CHANGE is False


def test_one_shield_costs_131_when_the_switch_is_on(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "SHIELD_POINT_MODE", "v311")
    monkeypatch.setattr(K, "SHIELD_PRICE_MODE", "flat")
    universe = _world()
    player = _seat(universe, credits=228)
    before = int(player.ship.shields)
    result = apply_action(
        universe, "P1", Action(kind=ActionKind.BUY_EQUIP, args={"item": "shields", "qty": 1}),
    )
    assert result.ok is True, result.error
    assert player.ship.shields == before + 1
    assert player.credits == 228 - 131
    assert K.fighter_unit_price(int(universe.day)) != 218 or K.fighter_unit_price(int(universe.day) + 9) != 218


def test_tavern_drink_and_food_follow_the_switch(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    universe = _world()
    player = _seat(universe, credits=100)
    assert _kinds(universe)["tavern_order"].params["cost_by"] == {"drink": 20, "food": 20}
    assert apply_action(
        universe, "P1", Action(kind=ActionKind.TAVERN_ORDER, args={"item": "drink"}),
    ).ok
    assert player.credits == 80

    monkeypatch.setattr(K, "TAVERN_BAR_PRICE_MODE", "v311")
    broke = _seat(universe, credits=30)
    broke.id = "P1"
    universe.players["P1"] = broke
    order = _kinds(universe)["tavern_order"]
    assert order.legal is True
    assert order.params["cost_by"] == {"drink": 80, "food": 24}
    refused = apply_action(
        universe, "P1", Action(kind=ActionKind.TAVERN_ORDER, args={"item": "drink"}),
    )
    assert refused.ok is False
    assert broke.credits == 30
    assert apply_action(
        universe, "P1", Action(kind=ActionKind.TAVERN_ORDER, args={"item": "food"}),
    ).ok
    assert broke.credits == 6
    announce = apply_action(
        universe, "P1", Action(kind=ActionKind.TAVERN_ANNOUNCE, args={"text": "posted"}),
    )
    assert announce.ok is False
    monkeypatch.setattr(K, "TAVERN_BAR_PRICE_MODE", "legacy")
    rich = _seat(universe, credits=100)
    universe.players["P1"] = rich
    assert apply_action(
        universe, "P1", Action(kind=ActionKind.TAVERN_ANNOUNCE, args={"text": "posted"}),
    ).ok
    assert rich.credits == 0


def test_cineplex_show_1_costs_100_and_other_titles_are_not_sold(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    universe = _world()
    player = _seat(universe, credits=50)
    free = _kinds(universe)["cineplex"]
    assert free.legal is True
    assert free.params["cost"] == 0
    assert "title" not in free.params
    assert apply_action(universe, "P1", Action(kind=ActionKind.CINEPLEX, args={})).ok
    assert player.credits == 50

    monkeypatch.setattr(K, "CINEPLEX_PRICE_MODE", "v311")
    short = _kinds(universe)["cineplex"]
    assert short.legal is False
    assert short.params["cost"] == 100
    assert short.params["show"] == 1
    assert short.params["title"] == "Vulcan Thunder"
    assert "Ferrengi Nights" not in short.params
    refused = apply_action(universe, "P1", Action(kind=ActionKind.CINEPLEX, args={}))
    assert refused.ok is False
    assert player.credits == 50

    player.credits = 140
    paid = apply_action(universe, "P1", Action(kind=ActionKind.CINEPLEX, args={}))
    assert paid.ok is True
    assert player.credits == 40
    shown = [
        event.summary for event in universe.events
        if getattr(event.kind, "value", event.kind) == "cineplex"
    ]
    assert 'You\'ll LOVE "Vulcan Thunder"' in shown[-1]
    assert "100 credits" in shown[-1]
    assert not any("librar" in kind.value or "single" in kind.value for kind in ActionKind)


def test_total_unknown_name_change_quotes_the_capture(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "UG_NAME_MODE", "legacy")
    universe = _world()
    player = _seat(universe, credits=140, experience=1, name="N129Cur")
    player.ug_entered_day = int(universe.day)
    player.ug_password_known = True
    assert "underground_rename" not in _kinds(universe)
    refused = apply_action(
        universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"name": "Nyx"}),
    )
    assert refused.ok is False
    assert player.name == "N129Cur"
    assert player.credits == 140

    monkeypatch.setattr(K, "UG_NAME_MODE", "v311")
    known = _kinds(universe)["underground_rename"]
    assert known.legal is True
    assert known.params["cost"] == 100
    done = apply_action(
        universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"name": "Nyx"}),
    )
    assert done.ok is True
    assert player.name == "Nyx"
    assert player.credits == 40
    summary = universe.events[-1].summary
    assert "total unknown" in summary
    assert "this'll be cheap" in summary
    assert "new identity for 100 credits" in summary
    assert K.UG_NAME_CHANGE is False

    player.experience = 2
    player.ug_entered_day = int(universe.day)
    later = apply_action(
        universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"name": "Hex"}),
    )
    assert later.ok is False
    assert later.error == "the Underground has not priced this trader"
    assert player.name == "Nyx"
    assert player.credits == 40
