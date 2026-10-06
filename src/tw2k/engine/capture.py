"""Ship capture (docs/playtests/ships/SHIP_CAPTURE.md, CAPTURE_MODE).

An ordinary attack that beats a ship with exactly the minimum fighters takes the hull instead of
destroying it. Pods and Scout Marauders are never captured. One fighter too many destroys as today.
When TOW_MODE is tw2002, capturing the tower releases its tow, a towed unmanned hull stays
locked and the tower is told, and capturing a manned towee drops the tow. Nothing here draws
from universe.rng; CAPTURE_FAIL_PCT 0 draws nothing at all.
"""

from __future__ import annotations

import math
import random
from fractions import Fraction

from . import constants as K
from .fleet import _ensure_fleet_id, _limpets_leave_hull, fleet_size
from .models import EventKind, FerrengiShip, ParkedShip, Player


def tow_hooks_active() -> bool:
    """True once slice 51's tow lock is on this tree. Legacy tow never grows a capture hook."""
    return getattr(K, "TOW_MODE", "legacy") == "tw2002" and hasattr(EventKind, "TOW_RELEASED")


def min_capture_qty(defense: Fraction, a_odds: Fraction) -> int:
    """Fighters that beat the whole real defense: ceil(defense / odds), at least one."""
    if a_odds <= 0 or defense <= 0:
        return 1
    return max(1, math.ceil(defense / a_odds))


def capture_rng(universe, attacker_id: str, target_key: str) -> random.Random:
    """Dedicated generator. Never universe.rng. Only constructed when CAPTURE_FAIL_PCT > 0."""
    seed = int(getattr(getattr(universe, "config", None), "seed", 0) or 0)
    return random.Random(f"tw2k-capture:{seed}:{int(universe.day)}:{attacker_id}:{target_key}")


def _pods_used_today(universe, player) -> int:
    if int(getattr(player, "pods_day", -1)) != int(universe.day):
        return 0
    return int(getattr(player, "pods_today", 0) or 0)


def _hull_capturable(attacker, ship, *, manned: bool) -> bool:
    hull = ship.ship_class.value
    if hull == K.ESCAPE_POD:
        return False  # a pod cannot be captured at all, under every CAPTURE_PODLESS setting
    policy = K.CAPTURE_PODLESS
    if hull in K.PODLESS_HULLS:
        if policy == "never":
            return False
        if policy == "unoccupied" and manned:
            return False
    if K.CAPTURE_CFS_NEEDS_CORP and hull == "corporate_flagship":
        if getattr(attacker, "corp_ticker", None) is None:
            return False
    return True


def capture_decision(
    universe,
    attacker,
    *,
    qty: int,
    defense: Fraction,
    a_odds: Fraction,
    beaten: bool,
    ship,
    manned: bool,
    target_key: str,
    npc_target: bool = False,
) -> bool:
    """True only when this beaten attack takes the hull. Every other beaten attack is a destroy."""
    if not K.capture_on() or K.CAPTURE_RULE != "min_qty":
        return False
    if npc_target or isinstance(attacker, FerrengiShip) or not isinstance(attacker, Player):
        return False
    if not K.CAPTURE_NPC and not isinstance(attacker, Player):
        return False
    if not beaten:
        return False
    need = min_capture_qty(defense, a_odds)
    if int(qty) > need + int(K.CAPTURE_SLACK):
        return False
    if not _hull_capturable(attacker, ship, manned=manned):
        return False
    if fleet_size(universe, attacker.id) >= int(K.FLEET_MAX_SHIPS):
        return False
    # cp9: a pilot with no pod left today can still lose the hull ("capture") or blow up with it ("destroy").
    if manned and K.CAPTURE_WHEN_SD == "destroy":
        victim = universe.players.get(target_key)
        if victim is not None and ship.ship_class.value not in K.PODLESS_HULLS:
            if _pods_used_today(universe, victim) >= int(K.PODS_PER_DAY):
                return False
    pct = int(K.CAPTURE_FAIL_PCT)
    if pct > 0:
        roll = capture_rng(universe, attacker.id, target_key)
        if roll.random() * 100 < pct:
            return False
    return True


def manned_would_capture(universe, attacker, target, qty: int, defense: Fraction, a_odds: Fraction) -> bool:
    if isinstance(target, FerrengiShip) or not isinstance(target, Player):
        return False
    ship = target.ship
    return capture_decision(
        universe, attacker, qty=qty, defense=defense, a_odds=a_odds, beaten=True,
        ship=ship, manned=True, target_key=target.id, npc_target=False,
    )


def unmanned_would_capture(universe, attacker, rec, qty: int, defense: Fraction, a_odds: Fraction) -> bool:
    return capture_decision(
        universe, attacker, qty=qty, defense=defense, a_odds=a_odds, beaten=True,
        ship=rec.ship, manned=False, target_key=f"ship:{rec.id}", npc_target=False,
    )


def apply_manned_capture(universe, attacker_id: str, target) -> None:
    """cp8: rewards, pod the pilot off a copy, park the real hull on the attacker."""
    from .combat import _destroy_ship
    from .victory import _award_xp, kill_rewards

    attacker = universe.players[attacker_id]
    _award_xp(universe, attacker_id, "kill_player")
    kill_rewards(universe, attacker_id, int(target.experience), int(target.alignment))

    hull = target.ship
    own_tow = None
    hauler = None
    if tow_hooks_active():
        from .tow import release, towed_by, towing
        own_tow = towing(universe, target.id)
        hauler = towed_by(universe, "player", target.id)
    copy = hull.model_copy(deep=True)
    copy.corbomite = 0
    copy.fleet_id = None  # the pod must not keep the captured hull's id
    if hasattr(copy, "tow_lock"):
        copy.tow_lock = None
    target.ship = copy
    fid = _ensure_fleet_id(universe, hull)
    _limpets_leave_hull(universe, target.id, fid)
    if own_tow is not None:
        release(universe, hull, target.id, "tower_captured")
    if hauler and towing(universe, hauler) is not None:
        release(universe, universe.players[hauler].ship, hauler, "towee_gone")
    sector = universe.sectors.get(int(attacker.sector_id))
    witnesses = list(sector.occupant_ids) if sector is not None else []
    if target.id not in witnesses:
        witnesses.append(target.id)
    if attacker_id not in witnesses:
        witnesses.append(attacker_id)
    # The death path strips player.ship in place. That object is the copy, not the captured hull.
    _destroy_ship(universe, target.id, reason="captured", killer_id=attacker_id, by_other=True)

    hull.fighters = 0
    hull.shields = 0
    former = target.name
    universe.parked_ships[fid] = ParkedShip(
        id=fid, owner_id=attacker_id, sector_id=int(attacker.sector_id), ship=hull,
        parked_day=int(universe.day), captured_from=former, captured_day=int(universe.day),
    )
    universe.emit(
        EventKind.SHIP_CAPTURED,
        actor_id=attacker_id,
        sector_id=int(attacker.sector_id),
        payload={
            "ship_id": int(fid),
            "hull": hull.ship_class.value,
            "manned": True,
            "captor": attacker.name,
            "former_owner": former,
            "victim": target.id,
            "_witnesses": witnesses,
        },
        summary=f"{attacker.name} captured {former}'s {hull.name} in sector {attacker.sector_id}",
    )


def apply_unmanned_capture(universe, attacker_id: str, rec) -> None:
    """cp12: the record stays. The owner changes. Corbomite stays aboard and does not fire."""
    attacker = universe.players[attacker_id]
    former_id = rec.owner_id
    former = universe.players.get(former_id)
    former_name = former.name if former is not None else former_id
    hauler = None
    if tow_hooks_active():
        from .tow import release, towed_by, towing
        hauler = towed_by(universe, "ship", rec.id)
        if hauler and not K.CAPTURE_KEEPS_TOW and towing(universe, hauler) is not None:
            release(universe, universe.players[hauler].ship, hauler, "towee_gone")
            hauler = None
    rec.owner_id = attacker_id
    rec.parked_day = int(universe.day)
    rec.ship.fighters = 0
    rec.ship.shields = 0
    rec.captured_from = former_name
    rec.captured_day = int(universe.day)
    sector = universe.sectors.get(int(attacker.sector_id))
    witnesses = list(sector.occupant_ids) if sector is not None else [attacker_id, former_id]
    if int(K.CAPTURE_UNMANNED_EXP):
        attacker.experience = int(attacker.experience) + int(K.CAPTURE_UNMANNED_EXP)
    universe.emit(
        EventKind.SHIP_CAPTURED,
        actor_id=attacker_id,
        sector_id=int(attacker.sector_id),
        payload={
            "ship_id": int(rec.id),
            "hull": rec.ship.ship_class.value,
            "manned": False,
            "captor": attacker.name,
            "former_owner": former_name,
            "victim": former_id,
            "_witnesses": witnesses,
        },
        summary=f"{attacker.name} captured {former_name}'s unmanned {rec.ship.name} in sector {attacker.sector_id}",
    )
    if hauler and K.CAPTURE_TELL_TOWER:
        universe.emit(
            EventKind.TOW_TARGET_CAPTURED,
            actor_id=hauler,
            sector_id=int(attacker.sector_id),
            payload={"ship_id": int(rec.id), "captor": attacker.name, "victim": hauler,
                     "_witnesses": [hauler]},
            summary=f"{attacker.name} captured the ship {hauler} is towing",
        )
