"""fullgame-fixes-v1: net-worth valuation of fighters / shields and the LLM buy reserve.

Seed 250925 full game (commit 2756bdc): the Grok seat bought 815 fighters for 171,965 cr, kept 151 cr,
and its net worth fell from 217k to 88k because a fighter counted 50 while StarDock charged ~211.
See docs/playtests/fullgame/FULLGAME_FIXES_V1.md.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.agents.llm import apply_buy_reserve_cap
from tw2k.agents.prompts import get_system_prompt
from tw2k.engine import Action, ActionKind, GameConfig, generate_universe
from tw2k.engine.models import Commodity, Planet, PlanetClass, Player, Ship, ShipClass
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import full_net_worth, planet_tax_value, tick_day


@pytest.fixture
def tw(monkeypatch):
    for name in ("ECONOMY_SCALE_MODE", "CLASS0_MODE", "NET_WORTH_MODE", "BUY_RESERVE_MODE"):
        monkeypatch.setattr(K, name, "tw2002")
    monkeypatch.setattr(K, "SHIELD_PRICE_MODE", "mirror")
    monkeypatch.setattr(K, "LLM_BUY_RESERVE_SOFT_CAP", False)


@pytest.fixture
def legacy_nw(tw, monkeypatch):
    monkeypatch.setattr(K, "NET_WORTH_MODE", "legacy")
    monkeypatch.setattr(K, "BUY_RESERVE_MODE", "legacy")


def _world(*, credits: int = 172_116, ship_class=ShipClass.BATTLESHIP, holds: int = 80, fighters: int = 20,
           sector: int = 1, day: int = 4):
    u = generate_universe(GameConfig(seed=250925, universe_size=1000, enable_ferrengi=False, enable_planets=True))
    u.day = day
    u.players["A"] = Player(id="A", name="Grok", credits=credits, sector_id=sector,
                            ship=Ship(ship_class=ship_class, holds=holds, fighters=fighters, shields=0))
    u.sectors[sector].occupant_ids.append("A")
    return u


# ---- valuation -------------------------------------------------------------------------------------

def test_tw2002_values_fighters_and_shields_at_half_the_wave_midpoint(tw):
    assert K.NW_WAVE_MID_PRICE == 200 and K.NW_HARDWARE_FRACTION == 0.5 == K.NW_HULL_FRACTION
    assert K.nw_fighter_value() == 100
    assert K.nw_shield_value() == 100
    assert K.nw_planet_shield_value() == 100 * K.PLANET_SHIELD_SHIP_COST
    # The wave the value is measured on: every day's price is within 160..239 of the 200 midpoint.
    assert all(160 <= K.fighter_unit_price(d) <= 239 for d in range(0, 90))


def test_legacy_values_are_the_old_flat_prices(legacy_nw):
    assert (K.nw_fighter_value(), K.nw_shield_value(), K.nw_planet_shield_value()) == (50, 10, 10)


def test_flat_prices_keep_flat_values_even_in_tw2002(tw, monkeypatch):
    monkeypatch.setattr(K, "ECONOMY_SCALE_MODE", "legacy")  # fighters cost a flat 50
    monkeypatch.setattr(K, "SHIELD_PRICE_MODE", "flat")     # shields cost a flat 10
    assert K.nw_fighter_value() == K.FIGHTER_COST == 50
    assert K.nw_shield_value() == 10


def test_grok_fighter_buy_costs_half_not_three_quarters_of_its_price(tw):
    """815 fighters at the day-4 price: the NW drop is price - 100 per fighter, not price - 50."""
    u = _world()
    p = u.players["A"]
    unit = K.fighter_unit_price(4)
    before = p.net_worth
    p.credits -= 815 * unit
    p.ship.fighters += 815
    assert before - p.net_worth == 815 * (unit - 100)


def test_legacy_fighter_buy_matches_the_old_formula(legacy_nw):
    u = _world()
    p = u.players["A"]
    before = p.net_worth
    p.ship.fighters += 815
    p.ship.shields += 100
    assert p.net_worth - before == 815 * 50 + 100 * 10


def _planet(u, owner="A", **kw):
    pl = Planet(id=901, sector_id=120, name="Keep", class_id=PlanetClass.M, owner_id=owner, **kw)
    u.planets[pl.id] = pl
    return pl


def test_planet_defense_uses_the_same_values_as_the_ship(tw):
    u = _world()
    p = u.players["A"]
    base = full_net_worth(u, p)
    _planet(u, fighters=300, shields=7)
    assert full_net_worth(u, p) - base == 300 * 100 + 7 * 1000
    # Depositing 10 ship shields as 1 planet shield, or fighters 1:1, moves no net worth.
    assert 10 * K.nw_shield_value() == K.nw_planet_shield_value()


def test_growth_dividend_keeps_its_old_basis_in_both_modes(tw, monkeypatch):
    """NET_WORTH_MODE moves the score only: planet fighter production pays the same credits."""
    payouts = []
    for mode in ("tw2002", "legacy"):
        monkeypatch.setattr(K, "NET_WORTH_MODE", mode)
        u = _world(credits=1_000)
        pl = _planet(u)
        pl.colonists[Commodity.FUEL_ORE] = 1_000
        pl.last_tax_value = planet_tax_value(pl)
        tick_day(u)
        assert pl.fighters > 0
        assert planet_tax_value(pl) == pl.last_tax_value
        payouts.append(u.players["A"].credits)
    assert payouts[0] == payouts[1] > 1_000


# ---- buy reserve: hints ------------------------------------------------------------------------------

def test_reserve_is_the_floor_or_a_full_trade_load():
    assert K.working_capital_reserve(80) == K.BUY_RESERVE_FLOOR_CREDITS == 20_000
    assert K.working_capital_reserve(125) == 125 * K.BUY_RESERVE_CR_PER_HOLD
    assert K.reserve_max_qty(172_116, 211, None, 20_000) == (172_116 - 20_000) // 211
    assert K.reserve_max_qty(172_116, 211, 100, 20_000) == 100
    assert K.reserve_max_qty(10_000, 211, None, 20_000) == 0


def test_stardock_hint_names_the_reserve_keeping_max(tw):
    u = _world()
    hint = build_observation(u, "A").action_hint
    unit = K.fighter_unit_price(4)
    keep = (172_116 - 20_000) // unit
    assert f"fighters {172_116 // unit}" in hint  # the old max line is still there
    assert "Working capital: keep >= 20,000 cr" in hint
    assert f"fighters {keep}" in hint
    assert f"fighters cost {unit} cr, count 100 toward net worth" in hint


def test_no_reserve_line_when_the_hull_cap_binds_first(tw):
    u = _world(credits=5_000_000, ship_class=ShipClass.SCOUT_MARAUDER, holds=25)
    assert "Working capital" not in build_observation(u, "A").action_hint


def test_reserve_hint_off_in_legacy(legacy_nw):
    u = _world()
    assert "Working capital" not in build_observation(u, "A").action_hint


def test_class0_port_hint_names_the_reserve(tw):
    from tw2k.engine.class0 import special_port_at
    u = _world()
    sid = next(s for s in u.sectors if special_port_at(u, s) is not None)
    u.sectors[1].occupant_ids.remove("A")
    u.players["A"].sector_id = sid
    u.sectors[sid].occupant_ids.append("A")
    assert "Working capital: keep >= 20,000 cr" in build_observation(u, "A").action_hint


def test_undefended_hint_carries_the_value_and_the_reserve(tw):
    u = _world(sector=500)
    hint = build_observation(u, "A").action_hint
    assert "UNDEFENDED IN DEEP SPACE" in hint
    assert "Each counts 100 cr toward net worth; keep 20,000 cr working capital." in hint


def test_undefended_hint_unchanged_in_legacy(legacy_nw):
    hint = build_observation(_world(sector=500), "A").action_hint
    assert "UNDEFENDED IN DEEP SPACE" in hint and "toward net worth" not in hint


def test_price_sheet_shows_the_live_fighter_and_shield_prices(tw, monkeypatch):
    monkeypatch.delenv("TW2K_HINT_LEVEL", raising=False)
    text = get_system_prompt()
    assert "fighters        50 cr each" not in text and "shields         10 cr per point" not in text
    assert "fighters        160-239 cr each" in text and "each counts 100 toward net worth" in text
    assert "shields         160-239 cr per point" in text
    assert "Working capital: after fighter/shield buys keep >= 20,000 cr" in text


def test_price_sheet_legacy_unchanged(legacy_nw, monkeypatch):
    monkeypatch.delenv("TW2K_HINT_LEVEL", raising=False)
    text = get_system_prompt()
    assert "fighters        50 cr each" in text and "Working capital" not in text


# ---- buy reserve: LLM soft cap -------------------------------------------------------------------------

def _buy(item: str, qty: int) -> Action:
    return Action(kind=ActionKind.BUY_EQUIP, args={"item": item, "qty": qty}, thought="buy max")


def test_soft_cap_is_off_by_default(tw):
    assert K.LLM_BUY_RESERVE_SOFT_CAP is False
    obs = build_observation(_world(), "A")
    act = _buy("fighters", 815)
    assert apply_buy_reserve_cap(obs, act) is act


def test_soft_cap_cuts_a_bank_draining_buy(tw, monkeypatch):
    monkeypatch.setattr(K, "LLM_BUY_RESERVE_SOFT_CAP", True)
    obs = build_observation(_world(), "A")
    unit = K.fighter_unit_price(4)
    out = apply_buy_reserve_cap(obs, _buy("fighters", 815))
    assert out.kind == ActionKind.BUY_EQUIP
    assert out.args["qty"] == (172_116 - 20_000) // unit
    assert "reserve cap" in out.thought


def test_soft_cap_waits_when_nothing_fits(tw, monkeypatch):
    monkeypatch.setattr(K, "LLM_BUY_RESERVE_SOFT_CAP", True)
    obs = build_observation(_world(credits=15_000), "A")
    out = apply_buy_reserve_cap(obs, _buy("shields", 50))
    assert out.kind == ActionKind.WAIT and "skipped" in out.thought


def test_soft_cap_leaves_small_and_other_buys_alone(tw, monkeypatch):
    monkeypatch.setattr(K, "LLM_BUY_RESERVE_SOFT_CAP", True)
    obs = build_observation(_world(), "A")
    small = _buy("fighters", 100)
    genesis = _buy("genesis", 1)
    assert apply_buy_reserve_cap(obs, small) is small
    assert apply_buy_reserve_cap(obs, genesis) is genesis
