"""The war estimate matches the engine planet fight on generated cases."""

from __future__ import annotations

from types import SimpleNamespace

from tw2k.agents.war_brain import armid_sector, planet_fight, threat_map
from tw2k.engine.runner import _planet_odds_fight


def _case(seed: int) -> tuple[int, int, int, int, str, bool]:
    attackers = (seed * 17 + 40) % 8000
    defenders = (seed * 13) % 3000
    shields = (seed * 3) % 400
    pct = (seed * 5) % 101
    hull = ("merchant_cruiser", "scout_marauder", "imperial_starship")[seed % 3]
    photon = seed % 4 == 0
    return attackers, defenders, shields, pct, hull, photon


def test_planet_fight_matches_the_engine_on_fifty_cases() -> None:
    for seed in range(50):
        attackers, defenders, shields, pct, hull, photon = _case(seed)
        player = SimpleNamespace(
            ship=SimpleNamespace(fighters=attackers, ship_class=SimpleNamespace(value=hull)),
            deaths=0,
            photon_damped_sector_id=1 if photon else None,
        )
        planet = SimpleNamespace(
            fighters=defenders, shields=shields, military_reaction_pct=pct,
            citadel_level=6 if not photon else 2, sector_id=1,
        )
        eng_a, eng_d, eng_s, _rounds = _planet_odds_fight(player, planet)
        got_a, got_d, got_s = planet_fight(
            attackers, defenders, shields, pct, hull, photon_damped=photon,
        )
        assert (got_a, got_d, got_s) == (eng_a, eng_d, eng_s), seed


def test_armids_avoid_a_corridor_and_fedspace() -> None:
    assert armid_sector(home=14, home_is_corridor=False, dead_end_entrance=8, own_planet_sector=14, here_is_fedspace=False) == 14
    assert armid_sector(home=14, home_is_corridor=True, dead_end_entrance=8, own_planet_sector=20, here_is_fedspace=False) == 8
    assert armid_sector(home=14, home_is_corridor=True, dead_end_entrance=None, own_planet_sector=20, here_is_fedspace=False) == 20
    assert armid_sector(home=1, home_is_corridor=False, dead_end_entrance=None, own_planet_sector=1, here_is_fedspace=True) is None


def test_bw15_estimate() -> None:
    attackers, defenders, shields, pct, hull = 400, 80, 0, 50, "merchant_cruiser"
    player = SimpleNamespace(
        ship=SimpleNamespace(fighters=attackers, ship_class=SimpleNamespace(value=hull)),
        deaths=0,
        photon_damped_sector_id=None,
    )
    planet = SimpleNamespace(
        fighters=defenders, shields=shields, military_reaction_pct=pct,
        citadel_level=6, sector_id=1,
    )
    eng_a, eng_d, eng_s, _rounds = _planet_odds_fight(player, planet)
    got_a, got_d, got_s = planet_fight(attackers, defenders, shields, pct, hull)
    assert (got_a, got_d, got_s) == (eng_a, eng_d, eng_s)


def test_bw2_threat_map() -> None:
    test_threat_map_drops_the_oldest_past_the_cap()


def test_threat_map_drops_the_oldest_past_the_cap() -> None:
    rows = [{"sector": n} for n in range(70)]
    kept = threat_map(rows, limit=64)
    assert len(kept) == 64 and kept[0]["sector"] == 6 and kept[-1]["sector"] == 69
