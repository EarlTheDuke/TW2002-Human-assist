"""Pure picket, stock, and retreat decisions. No universe."""

from __future__ import annotations

from tw2k.agents.war_brain import (
    defence_budget,
    pad_stale,
    picket_qty,
    quasar_settings,
    reaction_setting,
    retreat_reason,
    siege_refusal,
    stock_deposit,
)


def test_stale_sighting_is_padded_and_a_fresh_one_is_not() -> None:
    assert pad_stale(100, day=10, seen_day=7) == 100
    assert pad_stale(100, day=10, seen_day=6) == 150


def test_picket_keeps_forty_percent_and_never_uses_toll() -> None:
    laid = picket_qty(1000, floor=0)
    assert laid == {"qty": 120, "mode": "defensive"}
    assert picket_qty(1000, floor=0, dead_end_entrance=True)["mode"] == "offensive"
    assert picket_qty(1000, floor=0, already=120) is None
    assert picket_qty(1000, floor=0, room=5)["qty"] == 5
    assert picket_qty(1000, floor=0, travel=True) is None


def test_stock_fills_the_level_ladder_inside_the_budget() -> None:
    assert defence_budget(1_000) == 250
    filled = stock_deposit(
        3,
        planet_fighters=0,
        planet_shields=0,
        aboard_fighters=10_000,
        aboard_shields=200,
        credit_budget=6_000,
        fighter_price=1,
        shield_price=1,
    )
    assert filled == {"fighters": 5_000, "shields": 50}
    tight = stock_deposit(
        3,
        planet_fighters=0,
        planet_shields=0,
        aboard_fighters=10_000,
        aboard_shields=200,
        credit_budget=100,
        fighter_price=1,
        shield_price=1,
    )
    assert tight == {"fighters": 100, "shields": 0}
    assert stock_deposit(
        0,
        planet_fighters=0,
        planet_shields=0,
        aboard_fighters=100,
        aboard_shields=100,
        credit_budget=1_000,
        fighter_price=1,
        shield_price=1,
    ) == {"fighters": 0, "shields": 0}


def test_reaction_and_quasar_are_set_once_at_the_level_gate() -> None:
    assert reaction_setting(1, already=False) is None
    assert reaction_setting(2, already=False) == 20
    assert reaction_setting(6, already=True) is None
    assert quasar_settings(2, already=False, planet_ore=5_000) is None
    assert quasar_settings(3, already=False, planet_ore=1_999) is None
    assert quasar_settings(3, already=False, planet_ore=2_000) == {"sector_pct": 30, "atm_pct": 60}
    assert quasar_settings(6, already=True, planet_ore=9_000) is None


def test_retreat_stops_on_margin_quasar_rival_or_turns() -> None:
    assert retreat_reason(
        fighters=100, fighters_needed_remaining=100, shields=50,
        atmospheric_quasar=False, rival_stronger=False, turns_left=40,
    ) == "margin"
    assert retreat_reason(
        fighters=125, fighters_needed_remaining=100, shields=0,
        atmospheric_quasar=True, rival_stronger=False, turns_left=40,
    ) == "quasar"
    assert retreat_reason(
        fighters=200, fighters_needed_remaining=100, shields=10,
        atmospheric_quasar=False, rival_stronger=True, turns_left=40,
    ) == "rival"
    assert retreat_reason(
        fighters=200, fighters_needed_remaining=100, shields=10,
        atmospheric_quasar=False, rival_stronger=False, turns_left=19,
    ) == "turns"
    assert retreat_reason(
        fighters=200, fighters_needed_remaining=100, shields=10,
        atmospheric_quasar=False, rival_stronger=False, turns_left=20,
    ) is None


def test_bw3_fog() -> None:
    test_stale_sighting_is_padded_and_a_fresh_one_is_not()


def test_bw17_retreat() -> None:
    test_retreat_stops_on_margin_quasar_rival_or_turns()


def test_bw14_targets() -> None:
    ok = dict(skill="N3", policy="full", day=6, owner_evil=True)
    assert siege_refusal(**ok) is None
    assert siege_refusal(**{**ok, "skill": "N1"}) == "defend"
    assert siege_refusal(**{**ok, "skill": "H"}) == "defend"
    assert siege_refusal(**{**ok, "policy": "off"}) == "off"
    assert siege_refusal(**{**ok, "day": 4}) == "early"
    assert siege_refusal(**{**ok, "sieges_today": 1}) == "already"
    assert siege_refusal(**{**ok, "failed_day": 5}) == "cooldown"
    assert siege_refusal(**{**ok, "day": 8, "failed_day": 6}) == "cooldown"
    assert siege_refusal(**{**ok, "day": 9, "failed_day": 6}) is None
    assert siege_refusal(**{**ok, "mate": True}) == "mate"
    assert siege_refusal(**{**ok, "ally": True}) == "ally"
    assert siege_refusal(**{**ok, "fedspace": True}) == "fedspace"
    assert siege_refusal(**{**ok, "orphan": True}) == "orphan"


def test_bw23_alignment() -> None:
    base = dict(skill="N2", policy="full", day=6)
    assert siege_refusal(**base, attacker_good=True, owner_evil=False) == "alignment"
    assert siege_refusal(**base, attacker_good=True, owner_evil=True) is None
    assert siege_refusal(**base, attacker_good=True, owner_evil=False, attacked_us=True) is None
    assert siege_refusal(**base, attacker_good=False, owner_evil=False) is None
