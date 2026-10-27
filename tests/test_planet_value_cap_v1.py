"""Planet stock and fighters do not have to decide the rank.

The recorded score stays. A game can cap the stock that counts, leave
fighters out, count colonists only, or rank by experience.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.models import Commodity, Planet, PlanetClass, Player
from tw2k.engine.victory import check_victory, full_net_worth, planet_stock_unit_price

pytestmark = pytest.mark.legacy_profile


def _world():
    cfg = GameConfig(
        seed=21, universe_size=40, max_days=3, turns_per_day=1000,
        starting_credits=20_000, enable_ferrengi=False, enable_planets=False,
    )
    u = generate_universe(cfg)
    p = Player(id="P1", name="Seat", sector_id=1, credits=1_000, turns_per_day=1000)
    u.players["P1"] = p
    u.sectors[1].occupant_ids.append("P1")
    planet = Planet(
        id=1, sector_id=1, name="Home", class_id=PlanetClass.M, owner_id="P1",
        stockpile={Commodity.FUEL_ORE: 150_000},
        fighters=1_000,
        colonists={Commodity.COLONISTS: 500},
    )
    u.planets[1] = planet
    u.sectors[1].planet_ids.append(1)
    return u, p, planet


def test_default_score_is_unchanged_and_the_options_drop_the_pile(monkeypatch) -> None:
    u, _p, planet = _world()
    legacy = full_net_worth(u, u.players["P1"])
    monkeypatch.setattr(K, "PLANET_VALUE_SCORE_MODE", "stock_cap")
    capped = full_net_worth(u, u.players["P1"])
    extra = 50_000 * planet_stock_unit_price("fuel_ore")
    assert legacy - capped == extra
    monkeypatch.setattr(K, "PLANET_VALUE_SCORE_MODE", "no_fighters")
    no_guns = full_net_worth(u, u.players["P1"])
    assert legacy - no_guns == planet.fighters * K.nw_fighter_value()
    monkeypatch.setattr(K, "PLANET_VALUE_SCORE_MODE", "colonists")
    only = full_net_worth(u, u.players["P1"])
    assert only == u.players["P1"].net_worth + 500 * K.COLONIST_PRICE


def test_experience_ranks_the_day_cap(monkeypatch) -> None:
    u, rich, _planet = _world()
    rich.experience = 1
    rich.credits = 5_000_000
    poor = Player(id="P2", name="Other", sector_id=2, credits=0, turns_per_day=1000, experience=9)
    u.players["P2"] = poor
    u.sectors[2].occupant_ids.append("P2")
    u.day = u.config.max_days + 1
    monkeypatch.setattr(K, "PLANET_VALUE_SCORE_MODE", "experience")
    check_victory(u)
    assert u.winner_id == "P2"
    assert "experience" in u.events[-1].summary
