"""NOTE 166. Five bottom rows that have a printed source.

5.14 is a new switch, profile row 204. 9.8 and 10.1 are already the stored
reading, so they are Match with no new switch. 1.15 and 5.20 were already
behind NOTE 117. The grade moves. No second switch is added for them.
"""

from __future__ import annotations

from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.combat import _destroy_ship_tw2002
from tw2k.engine.corp import flagship_buy_block
from tw2k.engine.models import Corporation, GameConfig, Player, Ship, ShipClass
from tw2k.engine.ship_exit import handle_self_destruct
from tw2k.engine.universe import generate_universe
from tw2k.public.manual import render

_PROFILE = Path("docs/plans/v311-profile-v1.md")
ROOT = Path(__file__).resolve().parents[1]


def _world():
    return generate_universe(GameConfig(seed=166, universe_size=40, enable_ferrengi=False, enable_planets=False))


def _pilot(universe, align: int, exp: int) -> Player:
    pid = "P"
    universe.players[pid] = Player(
        id=pid, name=pid, ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=10),
        sector_id=1, alignment=align, experience=exp, alive=True,
    )
    if pid not in universe.sectors[1].occupant_ids:
        universe.sectors[1].occupant_ids.append(pid)
    return universe.players[pid]


def _boom(universe, monkeypatch, mode: str):
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "SHIP_EXIT_MODE", "tw2002")
    monkeypatch.setattr(K, "SELF_DESTRUCT_ALIGN_MODE", mode)
    return handle_self_destruct(universe, "P", Action(kind=ActionKind.SELF_DESTRUCT))


def test_row_204_is_the_only_new_helper() -> None:
    text = _PROFILE.read_text(encoding="utf-8")
    assert K.V311_PROFILE_HELPERS["self_destruct_align_live"][0] == "SELF_DESTRUCT_ALIGN_MODE"
    assert f"## The switch set ({len(K.V311_PROFILE_HELPERS)} helpers)" in text
    assert len(K.V311_PROFILE_HELPERS) == 140
    assert "| 204 |" in text
    assert "SELF_DESTRUCT_ALIGN_MODE" in text


def test_self_destruct_alignment_fails_off_and_passes_on(monkeypatch) -> None:
    """GAP 5.14. Off halves either sign. On leaves a good alignment alone."""
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.self_destruct_align_live() is False
    good = _world()
    _pilot(good, 80, 1000)
    result = _boom(good, monkeypatch, "legacy")
    assert result.ok
    assert good.players["P"].experience == 500
    assert good.players["P"].alignment == 40
    red = _world()
    _pilot(red, -80, 1000)
    assert _boom(red, monkeypatch, "v311").ok
    assert red.players["P"].experience == 500
    assert red.players["P"].alignment == -40
    kept = _world()
    _pilot(kept, 80, 1000)
    assert _boom(kept, monkeypatch, "v311").ok
    assert kept.players["P"].experience == 500
    assert kept.players["P"].alignment == 80


def test_a_kill_still_halves_a_good_alignment(monkeypatch) -> None:
    monkeypatch.setattr(K, "SELF_DESTRUCT_ALIGN_MODE", "v311")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    universe = _world()
    _pilot(universe, 80, 1000)
    _destroy_ship_tw2002(universe, "P", "attack", None, True, force_destroyed=True)
    assert universe.players["P"].alignment == 40
    assert universe.players["P"].experience == 500


def test_profile_enables_the_button_and_the_other_strings_do_not(monkeypatch) -> None:
    monkeypatch.setattr(K, "SELF_DESTRUCT_ALIGN_MODE", "legacy")
    monkeypatch.setattr(K, "SHIP_EXIT_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.self_destruct_align_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.v311_profile() is False
    assert K.self_destruct_align_live() is False
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.SELF_DESTRUCT_ALIGN_MODE == "legacy"
    assert K.self_destruct_align_live() is True
    universe = _world()
    _pilot(universe, 80, 200)
    result = handle_self_destruct(universe, "P", Action(kind=ActionKind.SELF_DESTRUCT))
    assert result.ok
    assert universe.players["P"].alignment == 80
    assert universe.players["P"].experience == 100


def test_printed_rows_that_were_already_the_game() -> None:
    """9.8 and 10.1 match with the stored values. 1.15 and 5.20 already have switches."""
    assert K.ROB_CREDIT_FACTOR == 6
    assert K.STEAL_HOLD_DIVISOR == 21
    assert K.CFS_CEO_RULE == "purchase"
    assert "self_destruct_align_live" in K.V311_PROFILE_HELPERS
    assert "fed_tow_limit_live" in K.V311_PROFILE_HELPERS
    assert "fedsafe_fighter_cap_live" in K.V311_PROFILE_HELPERS
    universe = _world()
    universe.players["A"] = Player(id="A", name="A", ship=Ship(), sector_id=1, corp_ticker="ZZ")
    universe.players["B"] = Player(id="B", name="B", ship=Ship(), sector_id=1, corp_ticker="ZZ")
    universe.corporations["ZZ"] = Corporation(ticker="ZZ", name="Zed", ceo_id="A", member_ids=["A", "B"])
    assert flagship_buy_block(universe, "B", "corporate_flagship") == "only a C.E.O. may buy a Corporate FlagShip"
    assert flagship_buy_block(universe, "A", "corporate_flagship") is None


def test_tow_and_fedsafe_stay_the_existing_switches(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "FED_TOW_LIMIT_MODE", "legacy")
    monkeypatch.setattr(K, "FEDSAFE_FIGHTER_CAP_MODE", "legacy")
    assert K.fed_tow_fighter_limit() == 98
    assert K.fedsafe_max_fighters() is None
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.FED_TOW_LIMIT_MODE == "legacy"
    assert K.FEDSAFE_FIGHTER_CAP_MODE == "legacy"
    assert K.fed_tow_fighter_limit() == 50
    assert K.fedsafe_max_fighters() == 50


def test_the_manual_names_the_switch_and_bot_is_untouched() -> None:
    page = render("Galaxy War Command")
    assert "SELF_DESTRUCT_ALIGN_MODE" in page
    assert "cuts alignment in half, good or bad" in page
    for name in ("bot.html", "bot.js", "bot-parity.js"):
        assert "SELF_DESTRUCT_ALIGN_MODE" not in (ROOT / "web" / name).read_text(encoding="utf-8")
