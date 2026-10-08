"""Scout, interdictor, defend-range, and turn-cap gates."""

from __future__ import annotations

from tw2k.agents.war_brain import (
    defend_reachable,
    fighters_needed,
    interdictor_blocks,
    land_tries_left,
    planet_fight,
    probes_left,
    scout_turns_left,
    war_turn_cap,
)


def test_interdictor_blocks_until_the_hold_is_priced() -> None:
    assert interdictor_blocks(6, fuel_left=800, hold_priced=False) is True
    assert interdictor_blocks(6, fuel_left=800, hold_priced=True) is False
    assert interdictor_blocks(6, fuel_left=100, hold_priced=False) is False
    assert interdictor_blocks(5, fuel_left=800, hold_priced=False) is False


def test_scout_and_probes_wait_for_day_fighters_and_skill() -> None:
    assert scout_turns_left("N3", day=6, fighters=2000, has_scanner=True, spent=4) == 6
    assert scout_turns_left("N3", day=4, fighters=2000, has_scanner=True, spent=0) == 0
    assert scout_turns_left("N1", day=8, fighters=9000, has_scanner=True, spent=0) == 0
    assert scout_turns_left("N2", day=8, fighters=1999, has_scanner=True, spent=0) == 0
    assert probes_left("N3", day=6, fighters=2000, used=0) == 1
    assert probes_left("N3", day=6, fighters=2000, used=1) == 0


def test_land_tries_defend_hops_and_turn_cap() -> None:
    assert land_tries_left(0) == 3
    assert land_tries_left(3) == 0
    assert defend_reachable(8) is True
    assert defend_reachable(9) is False
    assert defend_reachable(None) is False
    assert war_turn_cap("N3", 1000) == 400
    assert war_turn_cap("N2", 1000) == 300
    assert war_turn_cap("H", 1000) == 0


def test_bw12_an_l5_planet_with_1700_shields_can_be_taken() -> None:
    need = fighters_needed(0, 1700, 0, "imperial_starship")
    left_a, left_d, left_s = planet_fight(need, 0, 1700, 0, "imperial_starship")
    assert need < 50_000_000
    assert left_s == 0 and left_d == 0 and left_a > 0
