"""Classic alien traders (ALIEN_TRADERS.md).

Placement, hops, and mine hits draw only the alien rng. The universe rng
is not touched. Combat, capture, and the bot policy are wired separately.
"""

from __future__ import annotations

import random

from . import constants as K
from .models import AlienTrader, EventKind, MineType, Ship, ShipClass, Universe

_SALT_PLACE = 11
_SALT_RESPAWN = 12
_SALT_HOP = 13
_SALT_MINE = 14


def alien_rng(seed: int, day: int, salt: int) -> random.Random:
    return random.Random(int(seed) * 7349 + int(day) * 101 + int(salt))


def alien_brief(alien: AlienTrader) -> dict:
    """What a sector view and a scan show. Rank and side, never credits."""
    from .victory import rank_for, side

    return {
        "id": alien.id,
        "name": alien.name,
        "ship_name": alien.ship_name,
        "hull": alien.ship.ship_class.value,
        "rank": rank_for(int(alien.experience), int(alien.alignment)),
        "side": side(int(alien.alignment)),
        "fighters": int(alien.ship.fighters),
        "shields": int(alien.ship.shields),
    }


def population(universe: Universe) -> int:
    if not K.alien_on() or K.ALIEN_SOURCE == "off":
        return 0
    per = int(K.ALIEN_POPULATION_PER_1000)
    if per <= 0:
        return 0
    size = int(getattr(universe.config, "universe_size", 1000) or 1000)
    return max(1, round(per * size / 1000))


def _has_deployment(universe: Universe, sector_id: int) -> bool:
    sector = universe.sectors.get(sector_id)
    if sector is None:
        return True
    fighters = sector.fighters
    if fighters is not None and int(fighters.count) > 0:
        return True
    return any(int(md.count) > 0 for md in sector.mines)


def _fighter_blocked(universe: Universe, sector_id: int) -> bool:
    sector = universe.sectors.get(sector_id)
    if sector is None:
        return True
    fighters = sector.fighters
    return fighters is not None and int(fighters.count) > 0


def _hulls_for_day(day: int) -> tuple[str, ...]:
    chosen = K.ALIEN_HULLS_BY_DAY[0][1]
    for start, hulls in K.ALIEN_HULLS_BY_DAY:
        if int(day) >= int(start):
            chosen = hulls
    return tuple(chosen)


def _spawn(universe: Universe, sector_id: int, rng: random.Random) -> AlienTrader:
    n = int(universe.next_alien_id)
    universe.next_alien_id = n + 1
    names = tuple(K.ALIEN_NAMES)
    base = names[(n - 1) % len(names)] if names else "Alien"
    used = sum(1 for a in universe.aliens.values() if a.name == base or a.name.startswith(base + " "))
    name = base if used == 0 else f"{base} {used + 1}"
    good = rng.randrange(100) < int(K.ALIEN_GOOD_PCT)
    mag = rng.randint(int(K.ALIEN_ALIGN_MIN), int(K.ALIEN_ALIGN_MAX))
    alignment = mag if good else -mag
    hulls = _hulls_for_day(universe.day)
    hull = hulls[rng.randrange(len(hulls))]
    spec = K.hull_spec(hull) or {}
    scale = 0.5 + rng.random() * 0.5
    day = int(universe.day)
    fighters = min(
        int(spec.get("max_fighters") or 0),
        int((int(K.ALIEN_FIGHTERS_BASE) + day * int(K.ALIEN_FIGHTERS_PER_DAY)) * scale),
    )
    shields = min(
        int(spec.get("max_shields") or 0),
        int((int(K.ALIEN_SHIELDS_BASE) + day * int(K.ALIEN_SHIELDS_PER_DAY)) * scale),
    )
    exp_hi = min(int(K.ALIEN_EXP_CAP), int(K.ALIEN_EXP_START) + day * int(K.ALIEN_EXP_PER_DAY))
    experience = rng.randint(0, max(0, exp_hi))
    cred_hi = min(int(K.ALIEN_CREDITS_CAP), int(K.ALIEN_CREDITS_START) + day * int(K.ALIEN_CREDITS_PER_DAY))
    credits = rng.randint(int(K.ALIEN_CREDITS_MIN), max(int(K.ALIEN_CREDITS_MIN), cred_hi))
    corbo_cap = int(spec.get("max_corbomite") or spec.get("corbomite") or int(K.ALIEN_CORBOMITE_MAX))
    corbomite = rng.randint(0, min(int(K.ALIEN_CORBOMITE_MAX), max(0, corbo_cap)))
    ship = Ship(
        ship_class=ShipClass(hull),
        fighters=fighters,
        shields=shields,
        corbomite=corbomite,
    )
    label = spec.get("label") or hull.replace("_", " ")
    alien = AlienTrader(
        id=f"alien:{n}",
        name=name,
        ship_name=f"{name}'s {label}",
        sector_id=int(sector_id),
        ship=ship,
        experience=experience,
        alignment=alignment,
        credits=credits,
        alive=True,
        born_day=day,
    )
    universe.aliens[alien.id] = alien
    universe.emit(
        EventKind.ALIEN_SPAWN,
        actor_id=alien.id,
        sector_id=alien.sector_id,
        payload={"id": alien.id, "name": alien.name, "hull": hull},
        summary=f"{alien.name} entered in sector {alien.sector_id}",
    )
    return alien


def place_aliens(universe: Universe) -> None:
    """Scatter the opening population. No-op unless the mode is on."""
    if not K.alien_on() or K.ALIEN_START != "scatter":
        return
    want = population(universe)
    if want <= 0:
        return
    open_sectors = [
        sid for sid in sorted(universe.sectors)
        if sid not in K.FEDSPACE_SECTORS and not _has_deployment(universe, sid)
    ]
    if not open_sectors:
        return
    live = sum(1 for alien in universe.aliens.values() if alien.alive)
    rng = alien_rng(universe.config.seed, universe.day, _SALT_PLACE)
    for _ in range(max(0, want - live)):
        _spawn(universe, rng.choice(open_sectors), rng)


def apply_mines_to_alien(universe: Universe, alien: AlienTrader, rng: random.Random) -> None:
    """Armids hit an entering alien. Limpets do not attach. A kill pays nothing."""
    sector = universe.sectors.get(alien.sector_id)
    if sector is None:
        return
    from .hardware import armid_detonation_hits

    damage = 0
    owners: list[str] = []
    for md in list(sector.mines):
        if md.kind != MineType.ARMID or int(md.count) <= 0:
            continue
        hits, each = armid_detonation_hits(md.count, rng)
        if hits <= 0:
            continue
        damage += hits * each
        if md.owner_id and md.owner_id not in owners:
            owners.append(md.owner_id)
    if damage <= 0:
        return
    soaked = min(int(alien.ship.shields), damage)
    alien.ship.shields = int(alien.ship.shields) - soaked
    rest = damage - soaked
    if rest > 0:
        alien.ship.fighters = max(0, int(alien.ship.fighters) - rest)
    witnesses = list(sector.occupant_ids) + owners
    universe.emit(
        EventKind.ALIEN_MINED,
        actor_id=alien.id,
        sector_id=alien.sector_id,
        payload={"id": alien.id, "damage": damage, "_witnesses": witnesses},
        summary=f"{alien.name} hit mines in sector {alien.sector_id}",
    )
    if int(alien.ship.fighters) <= 0 and int(alien.ship.shields) <= 0:
        alien.alive = False
        alien.ship.corbomite = 0
        universe.emit(
            EventKind.SHIP_DESTROYED,
            actor_id=None,
            sector_id=alien.sector_id,
            payload={"victim": alien.id, "kind": "alien", "reason": "mines", "hull": alien.ship.ship_class.value},
            summary=f"{alien.name} was destroyed by mines in sector {alien.sector_id}",
        )


def _replace_dead(universe: Universe) -> None:
    for aid in [aid for aid, alien in universe.aliens.items() if not alien.alive]:
        universe.aliens.pop(aid, None)
    live = sum(1 for alien in universe.aliens.values() if alien.alive)
    need = population(universe) - live
    if need <= 0:
        return
    rng = alien_rng(universe.config.seed, universe.day, _SALT_RESPAWN)
    for _ in range(need):
        _spawn(universe, K.STARDOCK_SECTOR, rng)


def on_alien_killed(universe: Universe, attacker_id: str, alien: AlienTrader) -> None:
    """Bible kill: half experience if opposite, a quarter if the same, alignment against the alien, its credits."""
    from .victory import side

    attacker = universe.players[attacker_id]
    exp = int(alien.experience)
    if K.ALIEN_KILL_EXP_RULE == "bible":
        same = side(attacker.alignment) == side(alien.alignment)
        attacker.experience = int(attacker.experience) + (exp // 4 if same else exp // 2)
    alien.alignment = int(alien.alignment)
    attacker.alignment = int(attacker.alignment) - int(alien.alignment * float(K.ALIEN_KILL_ALIGN_SHARE))
    looted = int(alien.credits) if K.ALIEN_LOOT_CREDITS else 0
    attacker.credits = int(attacker.credits) + looted
    units = int(alien.ship.corbomite)
    alien.alive = False
    alien.credits = 0
    universe.emit(
        EventKind.SHIP_DESTROYED,
        actor_id=attacker_id,
        sector_id=attacker.sector_id,
        payload={
            "victim": alien.id, "kind": "alien", "hull": alien.ship.ship_class.value,
            "credits": looted,
        },
        summary=f"{attacker.name} destroyed {alien.name}",
    )
    if units > 0:
        from .hardware import apply_corbomite
        apply_corbomite(universe, alien.id, attacker_id, units)


def alien_flee_destination(universe: Universe, alien: AlienTrader) -> int | None:
    sector = universe.sectors.get(alien.sector_id)
    if sector is None:
        return None
    if K.ALIEN_INTERDICTED:
        from .combat import interdictor_planet
        if interdictor_planet(universe, alien.id, sector) is not None:
            return None
    legal = [w for w in sorted(sector.warps) if not _fighter_blocked(universe, w)]
    if not legal:
        return None
    rng = alien_rng(universe.config.seed, universe.day, _SALT_HOP + 50)
    return int(rng.choice(legal))


def alien_day_step(universe: Universe) -> None:
    """Replace the dead, then hop. No-op unless the mode is on."""
    if not K.alien_on():
        return
    _replace_dead(universe)
    rng = alien_rng(universe.config.seed, universe.day, _SALT_HOP)
    mine_rng = alien_rng(universe.config.seed, universe.day, _SALT_MINE)
    for alien in [universe.aliens[aid] for aid in sorted(universe.aliens) if universe.aliens[aid].alive]:
        for _hop in range(int(K.ALIEN_HOPS_PER_DAY)):
            sector = universe.sectors.get(alien.sector_id)
            if sector is None:
                break
            legal = [w for w in sorted(sector.warps) if not _fighter_blocked(universe, w)]
            if not legal:
                break
            dest = rng.choice(legal)
            alien.sector_id = int(dest)
            arrived = universe.sectors.get(dest)
            if arrived is not None and arrived.occupant_ids:
                universe.emit(
                    EventKind.ALIEN_SIGHTED,
                    actor_id=alien.id,
                    sector_id=dest,
                    payload={"id": alien.id, "name": alien.name, "_witnesses": list(arrived.occupant_ids)},
                    summary=f"{alien.name} entered sector {dest}",
                )
            apply_mines_to_alien(universe, alien, mine_rng)
            if not alien.alive:
                break
