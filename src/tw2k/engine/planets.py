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

from . import constants as K
from .models import Commodity, EventKind, PlanetClass, Universe
from .victory import _award_xp, _planet_asset_value

# Units produced per 100 colonists assigned to that pool. Shared with the
# owner-only growth observation so the seat sees the same arithmetic the
# day tick applies. H-class organics is 0: that world cannot feed itself.
PLANET_PROD_COEFF: dict[PlanetClass, dict[Commodity, int]] = {
    PlanetClass.M: {Commodity.FUEL_ORE: 3, Commodity.ORGANICS: 5, Commodity.EQUIPMENT: 3},
    PlanetClass.K: {Commodity.FUEL_ORE: 6, Commodity.ORGANICS: 1, Commodity.EQUIPMENT: 1},
    PlanetClass.L: {Commodity.FUEL_ORE: 5, Commodity.ORGANICS: 3, Commodity.EQUIPMENT: 1},
    PlanetClass.O: {Commodity.FUEL_ORE: 1, Commodity.ORGANICS: 6, Commodity.EQUIPMENT: 3},
    PlanetClass.H: {Commodity.FUEL_ORE: 8, Commodity.ORGANICS: 0, Commodity.EQUIPMENT: 1},
    PlanetClass.U: {Commodity.FUEL_ORE: 1, Commodity.ORGANICS: 1, Commodity.EQUIPMENT: 6},
    PlanetClass.C: {Commodity.FUEL_ORE: 1, Commodity.ORGANICS: 3, Commodity.EQUIPMENT: 5},
}
# Reported when production covers the burn and the day-boundary stockpile
# is not falling. Not a real horizon — just "not hungry".
ORGANICS_DAYS_SUSTAINABLE = 9999


def _class_id(class_id: PlanetClass | str) -> PlanetClass:
    return class_id if isinstance(class_id, PlanetClass) else PlanetClass(class_id)


def _pool_count(colonists: dict, name: str) -> int:
    for key, value in colonists.items():
        token = key.value if isinstance(key, Commodity) else str(key)
        if token == name:
            return int(value or 0)
    return 0


def organics_coeff(class_id: PlanetClass | str) -> int:
    """Organics column of the class production matrix."""
    return int(PLANET_PROD_COEFF[_class_id(class_id)][Commodity.ORGANICS])


def organics_consumption(total_colonists: int) -> int:
    """Organics stockpile burned on a growth day. See `_advance_planets`."""
    return max(1, int(total_colonists) // 100)


def organics_worker_target(total_colonists: int, coeff: int) -> int:
    """Workers on the organics pool so daily production exceeds the burn.

    ``int(workers * coeff / 100) >= burn + 1`` makes the day-boundary
    stockpile climb. Coeff 0 (H class) cannot; the target is 0 and the
    seat has to import. Coeff 1 (K and U) only breaks even with the
    entire population, which zeroes fuel and equipment income — cap the pool at
    half and import the rest. The target is never above the population.
    """
    total = int(total_colonists)
    if coeff <= 0 or total <= 0:
        return 0
    need = organics_consumption(total) + 1
    target = (need * 100 + coeff - 1) // coeff
    # A coeff-1 world cannot surplus-feed itself. Half the colony still
    # slows the burn; the rest keeps producing fuel and equipment.
    if target > total // 2:
        target = total // 2
    return min(total, target)


def planet_growth_status(class_id: PlanetClass | str, colonists: dict, organics_stock: int) -> dict:
    """Owner-only growth snapshot. Same arithmetic as `_advance_planets`.

    `production` is each pool's daily output. `organics_consumption_per_day`
    is the burn a growth day applies (`max(1, colonists // 100)`), including
    when the gate is currently shut so a restock can be sized.
    `growth_active` is true when this coming tick enters the growth block
    (stock on hand plus today's organics output is positive).
    `organics_days_left` is how many day-boundaries the current stockpile
    survives. Already empty is 0. A stockpile that is not falling is
    `ORGANICS_DAYS_SUSTAINABLE`.
    """
    coeffs = PLANET_PROD_COEFF[_class_id(class_id)]
    production = {
        commodity.value: int(_pool_count(colonists, commodity.value) * coeff / 100)
        for commodity, coeff in coeffs.items()
    }
    total = sum(_pool_count(colonists, c.value) for c in (
        Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT, Commodity.COLONISTS,
    ))
    # Colonist dicts sometimes carry only the producing pools.
    if total == 0 and colonists:
        total = sum(int(v or 0) for v in colonists.values())
    stock = int(organics_stock)
    # Appetite of one growth day. Reported even while the gate is shut so a
    # restock can be sized; the engine subtracts it only when post-production
    # organics are positive (see `_advance_planets`).
    rate = organics_consumption(total) if total > 0 or stock > 0 else 0
    prod_org = production.get(Commodity.ORGANICS.value, 0)
    post = stock + prod_org
    growth_active = post > 0
    if not growth_active or stock <= 0:
        days = 0
    else:
        end = max(0, post - rate)
        if end >= stock:
            days = ORGANICS_DAYS_SUSTAINABLE
        else:
            days = stock // (stock - end)
    return {
        "production": production,
        "organics_consumption_per_day": rate,
        "growth_active": growth_active,
        "organics_days_left": days,
    }


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
    for planet in universe.planets.values():
        coeffs = PLANET_PROD_COEFF[planet.class_id]
        for commodity, coeff in coeffs.items():
            colonists = planet.colonists.get(commodity, 0)
            produced = int(colonists * coeff / 100)
            planet.stockpile[commodity] = planet.stockpile.get(commodity, 0) + produced
        # Growth — only if organics stockpile positive after today's output.
        if planet.stockpile.get(Commodity.ORGANICS, 0) > 0:
            total_col = sum(planet.colonists.values())
            growth = int(total_col * 0.05)
            # Distribute growth proportionally
            if total_col > 0 and growth > 0:
                for c in list(planet.colonists.keys()):
                    share = int(growth * planet.colonists[c] / total_col)
                    planet.colonists[c] += share
            planet.stockpile[Commodity.ORGANICS] = max(
                0, planet.stockpile[Commodity.ORGANICS] - organics_consumption(total_col)
            )


def _pay_planet_value_tax(universe: Universe) -> None:
    """Pay owners a small credit dividend on new planet value only."""
    for planet in universe.planets.values():
        current_value = _planet_asset_value(planet)
        previous_value = max(0, int(getattr(planet, "last_tax_value", 0) or 0))
        owner_id = planet.owner_id
        owner = universe.players.get(owner_id) if owner_id is not None else None

        if owner is not None and owner.alive:
            gain = max(0, current_value - previous_value)
            payout = int(gain * K.PLANET_VALUE_TAX_RATE)
            if payout >= K.PLANET_VALUE_TAX_MIN_PAYOUT:
                owner.credits += payout
                universe.emit(
                    EventKind.PLANET_TAX_PAYOUT,
                    actor_id=owner.id,
                    sector_id=planet.sector_id,
                    payload={
                        "planet_id": planet.id,
                        "planet_name": planet.name,
                        "owner_id": owner.id,
                        "previous_value": previous_value,
                        "current_value": current_value,
                        "gain": gain,
                        "rate": K.PLANET_VALUE_TAX_RATE,
                        "payout": payout,
                    },
                    summary=(
                        f"{owner.name} collected {payout}cr planet growth dividend "
                        f"from {planet.name} (+{gain} value)"
                    ),
                )

        planet.last_tax_value = current_value
