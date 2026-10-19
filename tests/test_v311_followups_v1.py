"""COMMANDER NOTE 75 item 1: free start colonists are not in net worth."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.models import Commodity, Player
from tw2k.engine.planets import spend_free_start
from tw2k.engine.runner import grant_starting_planet
from tw2k.engine.victory import full_net_worth


def _seat(seed: int = 75):
    cfg = GameConfig(
        seed=seed, universe_size=80, max_days=3, turns_per_day=250,
        starting_credits=300, enable_ferrengi=False, enable_planets=True,
    )
    universe = generate_universe(cfg)
    player = Player(id="P1", name="Seat", sector_id=1, credits=300, turns_per_day=250)
    universe.players["P1"] = player
    universe.sectors[1].occupant_ids.append("P1")
    return universe, player


def test_the_switch_stays_legacy_until_the_profile_is_on(monkeypatch) -> None:
    assert K.START_COLONIST_NW_MODE == "legacy"
    assert K.start_colonist_nw_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.start_colonist_nw_live() is True
    assert K.START_COLONIST_NW_MODE == "legacy"


def test_day_zero_net_worth_skips_the_free_start_and_counts_terra_cargo(monkeypatch) -> None:
    """A new v3.11 game's day-0 net worth has no colonist value. Terra cargo does.

    Iago War Manual, Colonists: one hold is one thousand people. S1 / TWFAQ_20PLANET
    heads the production table "colonists (thousands)". COLONIST_PRICE is that
    handbook thousand (row 66), so 1,000 people in the hold are one Terra hold.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    universe, player = _seat()
    grant_starting_planet(universe, player)
    planet = next(pl for pl in universe.planets.values() if pl.owner_id == "P1")
    assert planet.free_start_colonists == sum(int(n) for n in planet.colonists.values())
    bare = full_net_worth(universe, player)
    saved = dict(planet.colonists)
    for key in list(planet.colonists):
        planet.colonists[key] = 0
    planet.free_start_colonists = 0
    assert full_net_worth(universe, player) == bare
    planet.colonists.update(saved)
    planet.free_start_colonists = sum(int(n) for n in saved.values())
    player.ship.cargo[Commodity.COLONISTS] = 1000
    assert full_net_worth(universe, player) - bare == K.COLONIST_PRICE
    player.ship.cargo[Commodity.COLONISTS] = 1000 * int(K.colonists_per_hold())
    assert full_net_worth(universe, player) - bare == 1000 * K.COLONIST_PRICE


def test_hauled_colonists_count_and_a_departure_spends_the_free_start_first(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    universe, player = _seat()
    grant_starting_planet(universe, player)
    planet = next(pl for pl in universe.planets.values() if pl.owner_id == "P1")
    pool = Commodity.FUEL_ORE
    planet.colonists[pool] -= 1000
    spend_free_start(planet, 1000)
    assert planet.free_start_colonists == sum(int(n) for n in planet.colonists.values())
    before = full_net_worth(universe, player)
    planet.colonists[pool] += 1000
    gained = full_net_worth(universe, player) - before
    assert gained == K.COLONIST_PRICE


def test_profile_off_still_counts_the_191000(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    universe, player = _seat()
    grant_starting_planet(universe, player)
    planet = next(pl for pl in universe.planets.values() if pl.owner_id == "P1")
    assert planet.free_start_colonists == 0
    assert planet.colonists[Commodity.COLONISTS] == K.LIVE_STARTING_COLONISTS
    with_people = full_net_worth(universe, player)
    planet.colonists[Commodity.COLONISTS] = 0
    assert with_people - full_net_worth(universe, player) == K.LIVE_STARTING_COLONISTS * K.COLONIST_PRICE
