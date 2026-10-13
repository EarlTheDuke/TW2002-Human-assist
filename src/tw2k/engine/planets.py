"""Planet day-tick behaviors: citadel promotion + colonist production.

Pulled out of `engine.runner` during the Phase 6 split. Called from
`runner.tick_day` after port regen + Ferrengi movement:

    * `_complete_citadels(universe)` — promote any planet whose
      `citadel_complete_day` has arrived; apply the gift constants
      (0 adds nothing) and award XP to the owner.
    * `_advance_planets(universe)` — per-class production matrix
      converts colonist head-count into commodity stockpile, plus a
      light organics-gated growth step.

Depends on `victory._award_xp` for the citadel promotion XP payout.
Does NOT import `runner`.
"""

from __future__ import annotations

from . import constants as K
from .models import Commodity, EventKind, PlanetClass, Universe
from .victory import _award_xp, planet_tax_value

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
        days = ORGANICS_DAYS_SUSTAINABLE if end >= stock else stock // (stock - end)
    return {
        "production": production,
        "organics_consumption_per_day": rate,
        "growth_active": growth_active,
        "organics_days_left": days,
    }


def colonist_trend(class_id: PlanetClass | str, total: int) -> str:
    """One line for the planet panel. Live die-off, otherwise the 5% growth."""
    count = int(total)
    if _class_id(class_id).value == "M" and K.class_m_fidelity_live():
        cap = int(K.CLASS_M_CATEGORY_CAP)
        shown = f"{count:,} (i.e. {count // 1000:,} thousands)"
        if count > cap:
            return f"{shown}; above a product pool cap, about 5% of the extra die off each day"
        return f"{shown}; each product pool holds 30,000 thousand"
    if not K.planet_prod_live():
        return "about 5% more each day while organics last"
    cap = int(K.PLANET_MAX_COLONISTS[_class_id(class_id).value])
    half = cap // 2
    if count > half:
        return f"above half the class cap ({cap}), about 5% die off each day"
    if count < half:
        return f"below half the class cap ({cap}), about 5% more each day while organics last"
    return f"at half the class cap ({cap})"


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
            # Gift floor at L2 and up. A zero constant changes nothing.
            if planet.citadel_level >= 2:
                gift_fighters = K.CITADEL_GIFT_FIGHTERS_PER_LEVEL * planet.citadel_level
                gift_shields = K.CITADEL_GIFT_SHIELDS_PER_LEVEL * planet.citadel_level
                if gift_fighters > 0:
                    planet.fighters = max(planet.fighters, gift_fighters)
                if gift_shields > 0:
                    planet.shields = max(planet.shields, gift_shields)
            universe.emit(
                EventKind.CITADEL_COMPLETE,
                sector_id=planet.sector_id,
                payload={"planet_id": planet.id, "from": old, "to": planet.citadel_level},
                summary=f"=== Citadel L{planet.citadel_level} on {planet.name} now operational ===",
            )
            if planet.owner_id is not None:
                _award_xp(universe, planet.owner_id, "build_citadel_lvl",
                          multiplier=planet.citadel_level)


def _accrue_planet_treasury(universe: Universe) -> None:
    """2% interest, once per day, for citadels at level 1 or higher."""
    cap = K.PLANET_TREASURY_CAP
    pct = K.PLANET_TREASURY_INTEREST_PCT
    for planet in universe.planets.values():
        if int(planet.citadel_level or 0) < 1 or int(planet.treasury) <= 0:
            continue
        gain = int(planet.treasury) * pct // 100
        if gain <= 0:
            continue
        planet.treasury = min(cap, int(planet.treasury) + gain)


def fighters_from_colonists(class_id: PlanetClass | str, colonists: dict) -> int:
    """Fighters one day of product-pool colonists would add, before the cap.

    Each pool divides on its own, then the rate scales the sum. A divisor of
    0 adds nothing. The idle colonists pool is not a product pool.
    """
    table = K.PLANET_FIGHTER_COLONISTS_PER[_class_id(class_id).value]
    made = 0
    for name, divisor in table.items():
        if int(divisor) <= 0:
            continue
        made += _pool_count(colonists, name) // int(divisor)
    return made * int(K.PLANET_FIGHTER_RATE_PCT) // 100


def _apply_one_day(planet) -> None:
    # Snapshot before growth. Newborns from today's 5% do not make fighters
    # until the next day, so 1500 fuel colonists on class M stay 50 fighters.
    worked = {
        name: _pool_count(planet.colonists, name)
        for name in ("fuel_ore", "organics", "equipment")
    }
    if K.planet_prod_live():
        _produce_and_grow_live(planet)
    else:
        _produce_and_grow_legacy(planet)
    if planet.owner_id is None:
        return
    gain = fighters_from_colonists(planet.class_id, worked)
    if gain > 0:
        room = max(0, K.PLANET_FIGHTER_CAP - int(planet.fighters))
        planet.fighters = int(planet.fighters) + min(room, gain)
    _trim_class_m_excess(planet)


def _trim_class_m_excess(planet) -> None:
    """Only colonists past a class M product pool die. The 5% is unverified."""
    if planet.class_id.value != "M" or not K.class_m_fidelity_live():
        return
    cap = int(K.CLASS_M_CATEGORY_CAP)
    for name in ("fuel_ore", "organics", "equipment", "colonists"):
        have = int(planet.colonists.get(name, 0) or 0)
        if have <= cap:
            continue
        die = int((have - cap) * 0.05)
        if die > 0:
            planet.colonists[name] = have - die


def _split_units(daily: int, seconds: int, remain: int) -> tuple[int, int]:
    """Whole units for this slice, and the leftover numerator.

    The leftover stays inside one day. Slices that add up to a day pay
    ``daily`` once.
    """
    day = int(K.TURN_REGEN_DAY_SECONDS)
    total = int(daily) * int(seconds) + int(remain)
    if total >= 0:
        whole = total // day
    else:
        whole = -((-total) // day)
    return whole, total - whole * day


def _accrue_planet(planet, seconds: float) -> None:
    take = int(seconds)
    if take <= 0:
        return
    shadow = planet.model_copy(deep=True)
    _apply_one_day(shadow)
    remain = dict(planet.prod_remain or {})
    for commodity in (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT):
        delta = int(shadow.stockpile.get(commodity, 0)) - int(planet.stockpile.get(commodity, 0))
        key = f"s:{commodity.value}"
        whole, remain[key] = _split_units(delta, take, int(remain.get(key, 0)))
        if whole > 0:
            _stock_product(planet, commodity, whole)
        elif whole < 0:
            planet.stockpile[commodity] = max(0, int(planet.stockpile.get(commodity, 0)) + whole)
    for commodity in list(planet.colonists.keys()):
        delta = int(shadow.colonists.get(commodity, 0)) - int(planet.colonists.get(commodity, 0))
        key = f"c:{commodity.value}"
        whole, remain[key] = _split_units(delta, take, int(remain.get(key, 0)))
        if whole:
            planet.colonists[commodity] = max(0, int(planet.colonists.get(commodity, 0)) + whole)
    whole, remain["fighters"] = _split_units(
        int(shadow.fighters) - int(planet.fighters), take, int(remain.get("fighters", 0))
    )
    if whole:
        planet.fighters = max(0, int(planet.fighters) + whole)
    planet.prod_remain = {k: v for k, v in remain.items() if v}


def refresh_planet_production(universe, now: float | None = None) -> None:
    """Accrue planet goods for time just passed. No-op while the switch is off."""
    if not K.planet_realtime_prod():
        return
    import time

    if now is None:
        now = time.time()
    day = float(K.TURN_REGEN_DAY_SECONDS)
    for planet in universe.planets.values():
        last = planet.prod_clock_at
        planet.prod_clock_at = float(now)
        if last is None:
            continue
        elapsed = max(0.0, float(now) - float(last))
        room = day - float(planet.prod_paid_s or 0)
        take = min(elapsed, max(0.0, room))
        if take <= 0:
            continue
        _accrue_planet(planet, take)
        planet.prod_paid_s = int(planet.prod_paid_s or 0) + int(take)


def _close_realtime_production(universe, now: float | None = None) -> None:
    """Pay the rest of one day, then start the clock over."""
    refresh_planet_production(universe, now=now)
    day = int(K.TURN_REGEN_DAY_SECONDS)
    for planet in universe.planets.values():
        remain_s = day - int(planet.prod_paid_s or 0)
        if remain_s > 0:
            _accrue_planet(planet, remain_s)
        planet.prod_paid_s = 0
        planet.prod_remain = {}
        planet.prod_clock_at = None


def _advance_planets(universe: Universe) -> None:
    if K.planet_realtime_prod():
        _close_realtime_production(universe)
        return
    for planet in universe.planets.values():
        _apply_one_day(planet)


def _stock_product(planet, commodity: Commodity, produced: int) -> None:
    before = int(planet.stockpile.get(commodity, 0))
    room = K.planet_stock_room(planet.class_id.value, commodity.value, before)
    added = produced if room is None else min(produced, room)
    planet.stockpile[commodity] = before + added


def _produce_and_grow_legacy(planet) -> None:
    coeffs = PLANET_PROD_COEFF[planet.class_id]
    for commodity, coeff in coeffs.items():
        colonists = planet.colonists.get(commodity, 0)
        raw = int(colonists * coeff / 100)
        produced = raw if raw > 0 else 0
        _stock_product(planet, commodity, produced)
    if planet.stockpile.get(Commodity.ORGANICS, 0) > 0:
        total_col = sum(planet.colonists.values())
        growth = int(total_col * 0.05)
        room = K.planet_colonist_room(planet.class_id.value, total_col)
        if room is not None:
            growth = min(growth, room)
        if total_col > 0 and growth > 0:
            for c in list(planet.colonists.keys()):
                share = int(growth * planet.colonists[c] / total_col)
                planet.colonists[c] += share
        planet.stockpile[Commodity.ORGANICS] = max(
            0, planet.stockpile[Commodity.ORGANICS] - organics_consumption(total_col)
        )


def _produce_and_grow_live(planet) -> None:
    ratios = K.PLANET_PROD_PER_UNIT[planet.class_id.value]
    goods = (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT)
    for commodity, ratio in zip(goods, ratios):
        colonists = int(planet.colonists.get(commodity, 0))
        produced = 0 if int(ratio) <= 0 else colonists // int(ratio)
        _stock_product(planet, commodity, produced)
    total_col = sum(int(v) for v in planet.colonists.values())
    cap = int(K.PLANET_MAX_COLONISTS[planet.class_id.value])
    half = cap // 2
    if total_col < half and planet.stockpile.get(Commodity.ORGANICS, 0) > 0:
        growth = int(total_col * 0.05)
        room = K.planet_colonist_room(planet.class_id.value, total_col)
        if room is not None:
            growth = min(growth, room)
        if total_col > 0 and growth > 0:
            for c in list(planet.colonists.keys()):
                share = int(growth * planet.colonists[c] / total_col)
                planet.colonists[c] += share
        planet.stockpile[Commodity.ORGANICS] = max(
            0, planet.stockpile[Commodity.ORGANICS] - organics_consumption(total_col)
        )
    elif (
        total_col > half
        and total_col > 0
        and not (planet.class_id.value == "M" and K.class_m_fidelity_live())
    ):
        die = int(total_col * 0.05)
        if die > 0:
            for c in list(planet.colonists.keys()):
                share = int(die * planet.colonists[c] / total_col)
                planet.colonists[c] = max(0, int(planet.colonists[c]) - share)


def _pay_planet_value_tax(universe: Universe) -> None:
    """Pay owners a small credit dividend on new planet value only."""
    for planet in universe.planets.values():
        current_value = planet_tax_value(planet)
        previous_value = int(getattr(planet, "last_tax_value", 0) or 0)
        if not K.dividend_transfers_neutral():
            previous_value = max(0, previous_value)  # tw2002: a withdrawal may push it below 0
        owner_id = planet.owner_id
        owner = universe.players.get(owner_id) if owner_id is not None else None

        if K.planet_dividend_off():
            planet.last_tax_value = current_value
            continue
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
