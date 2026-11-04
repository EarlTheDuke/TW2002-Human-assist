"""NOTE 167. Commander, for Ben, 2026-10-20. The slate stands.

R1, R4, and R7 are new profile rows 213-215. The other rulings were already
the stored game or an existing switch. StarDock stays in sector 1.
"""

from __future__ import annotations

from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine.models import Commodity, GameConfig, Player
from tw2k.engine.runner import grant_starting_planet
from tw2k.engine.universe import generate_universe

_DOC = Path("docs/plans/V311_RULINGS_FOR_BEN.md")
_PROFILE = Path("docs/plans/v311-profile-v1.md")


def _universe():
    return generate_universe(GameConfig(
        seed=167, universe_size=40, max_days=3, enable_ferrengi=False, enable_planets=True,
    ))


def test_rows_213_through_215_are_the_new_helpers() -> None:
    text = _PROFILE.read_text(encoding="utf-8")
    assert len(K.V311_PROFILE_HELPERS) == 140
    assert "## The switch set (140 helpers)" in text
    for name, switch, row in (
        ("printed_terra_live", "PRINTED_TERRA_MODE", "213"),
        ("printed_class_m_live", "PRINTED_CLASS_M_MODE", "214"),
        ("genesis_bible_price_live", "GENESIS_BIBLE_PRICE_MODE", "215"),
    ):
        assert K.V311_PROFILE_HELPERS[name][0] == switch
        assert f"| {row} |" in text
        assert switch in text
    for retired in (
        "terra_colonist_live",
        "class_m_fidelity_live",
        "class_m_nw_units",
        "class_m_drop_units",
        "class_m_genesis_units",
        "colonist_units_live",
        "colonist_nw_units",
    ):
        assert retired not in K.V311_PROFILE_HELPERS
    rulings = _DOC.read_text(encoding="utf-8")
    assert "Rulings (decided by Commander for Ben, 2026-10-20)" in rulings
    for label in ("R1 A", "R2 A", "R3 A", "R4 A", "R5 B", "R6 A", "R7 A", "R8 A", "R9 B", "R10 A", "R11 A", "R12 A", "R13 A", "R14 A"):
        assert label in rulings


def test_one_and_the_live_profile_do_not_turn_the_rulings_on(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.printed_terra_live() is False
    assert K.printed_class_m_live() is False
    assert K.genesis_bible_price_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.v311_profile() is False
    assert K.printed_terra_live() is False
    assert K.printed_class_m_live() is False
    assert K.genesis_bible_price_live() is False
    assert K.terra_colonist_live() is True
    assert K.class_m_fidelity_live() is True


def test_profile_keeps_the_printed_numbers_and_the_modes_stay_legacy(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.PRINTED_TERRA_MODE == "legacy"
    assert K.PRINTED_CLASS_M_MODE == "legacy"
    assert K.GENESIS_BIBLE_PRICE_MODE == "legacy"
    assert K.printed_terra_live() is True
    assert K.printed_class_m_live() is True
    assert K.genesis_bible_price_live() is True
    assert K.terra_colonist_live() is False
    assert K.colonist_units_live() is False
    assert K.colonist_nw_units() is False
    assert K.class_m_fidelity_live() is False
    assert K.class_m_nw_units() is False
    assert K.class_m_drop_units() is False
    assert K.class_m_genesis_units() is False
    assert K.terra_start_pool() == 100_000
    assert K.colonists_per_hold() == 1
    assert K.citadel_class_cost("M", 1)[0] == 1_000
    assert K.planet_colonist_cap("M") == 30_000
    assert K.genesis_torpedo_cost() == 25_000
    assert K.hardware_price_live() is True
    assert K.armid_mine_cost() == 1_000
    assert K.STARDOCK_SECTOR == 1
    assert K.planet_realtime_prod() is False
    assert K.universe_topology_live() is False
    assert K.gold_alien_live() is False
    assert K.alliance_live() is False
    assert K.planet_dividend_off() is True
    assert K.home_planet_count(K.HOME_PLANET_FUEL) == 45
    assert K.home_planet_count(K.HOME_PLANET_ORGANICS) == 65
    assert K.home_planet_count(K.HOME_PLANET_EQUIPMENT) == 81


def test_legacy_and_the_explicit_modes_still_do_the_other_reading(monkeypatch) -> None:
    assert K.v311_profile() is False
    assert K.terra_start_pool() == 100_000
    assert K.colonists_per_hold() == 1
    assert K.genesis_torpedo_cost() == 25_000
    assert K.citadel_class_cost("M", 1)[0] == 1_000
    monkeypatch.setattr(K, "TERRA_COLONIST_MODE", "live")
    assert K.terra_start_pool() == 30_000
    assert K.colonists_per_hold() == 1_000
    monkeypatch.setattr(K, "TERRA_COLONIST_MODE", "legacy")
    monkeypatch.setattr(K, "CLASS_M_FIDELITY_MODE", "live")
    assert K.citadel_class_cost("M", 1)[0] == 1_000_000
    monkeypatch.setattr(K, "CLASS_M_FIDELITY_MODE", "legacy")
    monkeypatch.setattr(K, "HARDWARE_PRICE_MODE", "live")
    assert K.genesis_torpedo_cost() == 20_000
    assert K.limpet_mine_cost() == 10_000


def test_profile_home_planet_uses_the_transcript_figures(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    universe = _universe()
    player = Player(id="P9", name="N9", sector_id=1, credits=300, turns_per_day=250)
    universe.players["P9"] = player
    universe.sectors[1].occupant_ids.append("P9")
    grant_starting_planet(universe, player)
    planet = next(item for item in universe.planets.values() if item.owner_id == "P9")
    assert planet.colonists[Commodity.FUEL_ORE] == 45
    assert planet.colonists[Commodity.ORGANICS] == 65
    assert planet.colonists[Commodity.EQUIPMENT] == 81
    assert sum(planet.colonists.values()) == 191


def test_explicit_home_mode_still_places_the_people_counts(monkeypatch) -> None:
    monkeypatch.setattr(K, "HOME_PLANET_MODE", "live")
    assert K.printed_class_m_live() is False
    universe = _universe()
    player = Player(id="P8", name="N8", sector_id=1, credits=300, turns_per_day=250)
    universe.players["P8"] = player
    universe.sectors[1].occupant_ids.append("P8")
    grant_starting_planet(universe, player)
    planet = next(item for item in universe.planets.values() if item.owner_id == "P8")
    assert planet.colonists[Commodity.FUEL_ORE] == 45_000
    assert planet.colonists[Commodity.ORGANICS] == 65_000
    assert planet.colonists[Commodity.EQUIPMENT] == 81_000


def test_already_settled_rulings_have_no_second_switch() -> None:
    assert "fed_tow_limit_live" in K.V311_PROFILE_HELPERS
    assert "self_destruct_align_live" in K.V311_PROFILE_HELPERS
    assert "fedsafe_fighter_cap_live" in K.V311_PROFILE_HELPERS
    assert "ferrengi_odds_live" in K.V311_PROFILE_HELPERS
    assert "times_blown_live" in K.V311_PROFILE_HELPERS
    assert K.ROB_CREDIT_FACTOR == 6
    assert K.STEAL_HOLD_DIVISOR == 21
    assert K.CFS_CEO_RULE == "purchase"
    assert K.PLANET_REALTIME_PROD_MODE == "legacy"
    assert K.UNIVERSE_TOPOLOGY_MODE == "legacy"
    assert K.ALLIANCE_MODE == "legacy"
