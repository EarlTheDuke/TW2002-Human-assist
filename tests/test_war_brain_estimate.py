"""The war estimate matches the engine planet fight on generated cases."""

from __future__ import annotations

from types import SimpleNamespace

from tw2k.agents.war_brain import planet_fight
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
