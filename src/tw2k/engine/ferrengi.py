"""Ferrengi NPC pirates: spawn + roam + opportunistic hunt.

Pulled out of `engine.runner` during the Phase 6 split. Called from
`runner.tick_day` after port regeneration:

    * `_spawn_ferrengi(universe)` — adds `ferrengi_per_day` new raiders in
      random deep sectors (outside FedSpace). Fighter/shield scale with
      rolled aggression.
    * `_ferrengi_roam_and_hunt(universe)` — per-day movement + decision:
      stay put, roam one warp, flee an overmatching target, or attack a
      co-located player (lower aggression threshold if the target is
      unarmed).
    * `_ferrengi_by_name(universe, key)` — lookup helper used by the
      ATTACK action handler to let agents name a specific raider.

Depends on `combat._resolve_ship_combat_attacker_npc` for the actual
damage exchange. Does NOT import `runner`.
"""

from __future__ import annotations

from . import constants as K
from .combat import _resolve_ship_combat_attacker_npc
from .models import EventKind, FerrengiShip, ShipClass, Universe


def _spawn_ferrengi(universe: Universe) -> None:
    rng = universe.rng

    for _ in range(universe.config.ferrengi_per_day):
        sid = rng.randint(max(K.FEDSPACE_SECTORS) + 1, universe.config.universe_size)
        aggr = rng.randint(1, K.FERRENGI_MAX_AGGRESSION)
        fid = f"ferr_{universe.day}_{sid}"
        ship = FerrengiShip(
            id=fid,
            name=f"Ferrengi Raider {fid[-4:].upper()}",
            sector_id=sid,
            aggression=aggr,
            fighters=100 + aggr * 300,
            shields=aggr * 50,
            ship_class=ShipClass.BATTLESHIP if aggr >= 8 else ShipClass.MISSILE_FRIGATE,
        )
        universe.ferrengi[fid] = ship
        universe.emit(
            EventKind.FERRENGI_SPAWN,
            sector_id=sid,
            payload={"id": fid, "aggression": aggr, "fighters": ship.fighters},
            summary=f"Ferrengi raider appeared in {sid} (aggression {aggr})",
        )


def _ferrengi_by_name(universe: Universe, key: str):
    for f in universe.ferrengi.values():
        if f.id == key or f.name == key:
            return f
    return None


def _ferrengi_roam_and_hunt(universe: Universe) -> None:
    """Each living Ferrengi: maybe move 1 sector; if a player is co-located, attack."""
    rng = universe.rng
    # Startup grace when everyone starts at StarDock — Ferrengi can still
    # roam (keeps the event feed honest) but skip attacking for the first
    # few days. Without this, a day-0 initial raider in a sector adjacent
    # to StarDock routinely one-shots the first player who warps out.
    grace_active = bool(
        getattr(universe.config, "all_start_stardock", False)
        and universe.day < K.FERRENGI_STARTUP_GRACE_DAYS
    )
    for ferr in list(universe.ferrengi.values()):
        if not ferr.alive:
            continue
        sec = universe.sectors.get(ferr.sector_id)
        if sec is None:
            continue
        if rng.random() < K.FERRENGI_MOVE_PROB:
            choices = [w for w in sec.warps if w not in K.FEDSPACE_SECTORS]
            if choices:
                old_sid = ferr.sector_id
                ferr.sector_id = rng.choice(choices)
                universe.emit(
                    EventKind.FERRENGI_MOVE,
                    sector_id=ferr.sector_id,
                    payload={"id": ferr.id, "from": old_sid, "to": ferr.sector_id},
                    summary=f"Ferrengi {ferr.name} prowled {old_sid} → {ferr.sector_id}",
                )
        if grace_active:
            # Roam is fine; no hunting during startup grace.
            continue
        # Attack a player in the same sector if any
        victims = [
            p for p in universe.players.values()
            if p.alive and p.sector_id == ferr.sector_id and p.sector_id not in K.FEDSPACE_SECTORS
        ]
        if not victims:
            continue
        victim = min(victims, key=lambda p: p.ship.fighters)
        # Opportunistic hunt: a clearly defenseless target (0 fighters + 0
        # shields) lowers the aggression bar. Even timid raiders will pounce
        # when the victim can't shoot back — matches real TW2002, where
        # unarmed cargo haulers are Ferrengi bait regardless of aggression
        # rating. Armed targets still need the normal threshold.
        unarmed = victim.ship.fighters == 0 and victim.ship.shields == 0
        required_aggression = (
            K.FERRENGI_OPPORTUNIST_AGGRESSION_THRESHOLD
            if unarmed
            else K.FERRENGI_HUNT_AGGRESSION_THRESHOLD
        )
        if ferr.aggression < required_aggression:
            continue
        # Flee if outclassed
        if victim.ship.fighters > ferr.fighters * K.FERRENGI_FLEE_FIGHTER_RATIO:
            choices = [w for w in sec.warps if w not in K.FEDSPACE_SECTORS]
            if choices:
                old_sid = ferr.sector_id
                ferr.sector_id = rng.choice(choices)
                universe.emit(
                    EventKind.FERRENGI_MOVE,
                    sector_id=ferr.sector_id,
                    payload={"id": ferr.id, "from": old_sid, "to": ferr.sector_id, "reason": "fled"},
                    summary=f"Ferrengi {ferr.name} fled {victim.name}: {old_sid} → {ferr.sector_id}",
                )
            continue
        universe.emit(
            EventKind.FERRENGI_ATTACK,
            actor_id=ferr.id,
            sector_id=ferr.sector_id,
            payload={"victim": victim.id},
            summary=f"!!! Ferrengi {ferr.name} attacks {victim.name} in {ferr.sector_id} !!!",
        )
        # Reuse ship-vs-ship combat with ferrengi as attacker (treat victim as defender)
        _resolve_ship_combat_attacker_npc(universe, ferr, victim)
