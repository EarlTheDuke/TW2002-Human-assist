"""Planet day-tick behaviors: citadel promotion + colonist production.

Pulled out of `engine.runner` during the Phase 6 split. Called from
`runner.tick_day` after port regen + Ferrengi movement:

    * `_complete_citadels(universe)` — promote any planet whose
      `citadel_complete_day` has arrived; grant the L2+ defense bonus
      and award XP to the owner.
    * `_advance_planets(universe)` — per-class production matrix
      converts colonist head-count into commodity stockpile, plus a
      light organics-gated growth step.

Depends on `victory._award_xp` for the citadel promotion XP payout.
Does NOT import `runner`.
"""

from __future__ import annotations

from .models import Commodity, EventKind, PlanetClass, Universe
from .victory import _award_xp


def _complete_citadels(universe: Universe) -> None:
    """Promote planets whose citadel build window has elapsed."""
    for planet in universe.planets.values():
        if (
            planet.citadel_target > planet.citadel_level
            and planet.citadel_complete_day is not None
            and universe.day >= planet.citadel_complete_day
        ):
            old = planet.citadel_level
            planet.citadel_level = planet.citadel_target
            planet.citadel_complete_day = None
            # L2 = Quasar Cannons → big planet fighter boost
            if planet.citadel_level >= 2:
                planet.fighters = max(planet.fighters, 1000 * planet.citadel_level)
                planet.shields = max(planet.shields, 250 * planet.citadel_level)
            universe.emit(
                EventKind.CITADEL_COMPLETE,
                sector_id=planet.sector_id,
                payload={"planet_id": planet.id, "from": old, "to": planet.citadel_level},
                summary=f"=== Citadel L{planet.citadel_level} on {planet.name} now operational ===",
            )
            if planet.owner_id is not None:
                _award_xp(universe, planet.owner_id, "build_citadel_lvl",
                          multiplier=planet.citadel_level)


def _advance_planets(universe: Universe) -> None:
    prod_matrix = {
        PlanetClass.M: {Commodity.FUEL_ORE: 3, Commodity.ORGANICS: 5, Commodity.EQUIPMENT: 3},
        PlanetClass.K: {Commodity.FUEL_ORE: 6, Commodity.ORGANICS: 1, Commodity.EQUIPMENT: 1},
        PlanetClass.L: {Commodity.FUEL_ORE: 5, Commodity.ORGANICS: 3, Commodity.EQUIPMENT: 1},
        PlanetClass.O: {Commodity.FUEL_ORE: 1, Commodity.ORGANICS: 6, Commodity.EQUIPMENT: 3},
        PlanetClass.H: {Commodity.FUEL_ORE: 8, Commodity.ORGANICS: 0, Commodity.EQUIPMENT: 1},
        PlanetClass.U: {Commodity.FUEL_ORE: 1, Commodity.ORGANICS: 1, Commodity.EQUIPMENT: 6},
        PlanetClass.C: {Commodity.FUEL_ORE: 1, Commodity.ORGANICS: 3, Commodity.EQUIPMENT: 5},
    }
    for planet in universe.planets.values():
        coeffs = prod_matrix[planet.class_id]
        for commodity, coeff in coeffs.items():
            colonists = planet.colonists.get(commodity, 0)
            produced = int(colonists * coeff / 100)
            planet.stockpile[commodity] = planet.stockpile.get(commodity, 0) + produced
        # Growth — only if organics stockpile positive
        if planet.stockpile.get(Commodity.ORGANICS, 0) > 0:
            total_col = sum(planet.colonists.values())
            growth = int(total_col * 0.05)
            # Distribute growth proportionally
            if total_col > 0 and growth > 0:
                for c in list(planet.colonists.keys()):
                    share = int(growth * planet.colonists[c] / total_col)
                    planet.colonists[c] += share
            planet.stockpile[Commodity.ORGANICS] = max(
                0, planet.stockpile[Commodity.ORGANICS] - max(1, total_col // 100)
            )
