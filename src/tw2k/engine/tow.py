"""Ship towing (tractor beam) + Type 2 TransWarp tow jumps (TOW_MODE). docs/playtests/ships/SHIP_TOW.md.

The lock lives on the TOWER hull (Ship.tow_lock, tt1). Slice 48 (ship_transwarp.py) and slice 50 (fleet.py)
call into this module, never the reverse. Nothing here draws from universe.rng (tt27).
Capture, furbing, corp ships / passwords and citadel ship exchange are not here (tt32).
"""

from __future__ import annotations

from typing import Any

from . import constants as K
from .actions import Action, ActionKind, ActionResult
from .models import EventKind, ParkedShip, Player, Ship, TowLock, Universe

PORT_VERBS = frozenset({"trade", "rob", "steal"})
ATTACK_VERBS = frozenset({"attack", "photon_missile"})


def tow_on() -> bool:
    return K.tow_on()


def lock_of(ship: Ship | None) -> TowLock | None:
    return getattr(ship, "tow_lock", None) if ship is not None else None


def tpw_of(ship: Ship) -> int:
    spec = K.hull_spec(ship.ship_class.value) or {}
    return int(spec.get("turns_per_warp") or K.TURN_COST["warp"])


def tow_warp_cost(tower_ship: Ship, towee_ship: Ship) -> int:
    """tt6: tower TPW + TOW_TOWEE_TPW_MULT x towee TPW, per sector, charged to the tower only."""
    return tpw_of(tower_ship) + int(K.TOW_TOWEE_TPW_MULT) * tpw_of(towee_ship)


def _key(lock: TowLock) -> tuple[str, Any]:
    return ("ship", int(lock.ship_id)) if lock.kind == "ship" else ("player", str(lock.player_id))


def _towee(universe: Universe, lock: TowLock) -> ParkedShip | Player | None:
    if lock.kind == "ship":
        return universe.parked_ships.get(int(lock.ship_id)) if lock.ship_id is not None else None
    p = universe.players.get(str(lock.player_id))
    return p if p is not None and p.alive else None


def _sector_of(obj: ParkedShip | Player) -> int:
    return int(obj.sector_id)


def _ship_of(obj: ParkedShip | Player) -> Ship:
    return obj.ship


def _hull_locks(universe: Universe) -> list[tuple[str | None, Ship, TowLock]]:
    """Every lock in the game: (pilot id or None for a parked hull, hull, lock); sorted, no rng."""
    out: list[tuple[str | None, Ship, TowLock]] = []
    for pid in sorted(universe.players):
        p = universe.players[pid]
        if p.alive and lock_of(p.ship) is not None:
            out.append((pid, p.ship, p.ship.tow_lock))
    for sid in sorted(universe.parked_ships):
        rec = universe.parked_ships[sid]
        if lock_of(rec.ship) is not None:
            out.append((None, rec.ship, rec.ship.tow_lock))
    return out


def towed_by(universe: Universe, kind: str, ident: Any) -> str | None:
    """Pilot whose MANNED hull locks this target (tt1), else None."""
    want = (kind, int(ident) if kind == "ship" else str(ident))
    for pid, _ship, lock in _hull_locks(universe):
        if pid is not None and _key(lock) == want:
            return pid
    return None


def _locked_anywhere(universe: Universe, kind: str, ident: Any) -> bool:
    want = (kind, int(ident) if kind == "ship" else str(ident))
    return any(_key(lock) == want for _p, _s, lock in _hull_locks(universe))


def towing(universe: Universe, pid: str) -> TowLock | None:
    p = universe.players.get(pid)
    if p is None or not p.alive:
        return None
    return lock_of(p.ship)


def engaged(universe: Universe, pid: str) -> tuple[TowLock, ParkedShip | Player] | None:
    """The manned hull's lock with a valid towee in the same sector (not dormant), else None."""
    if not tow_on():
        return None
    lock = towing(universe, pid)
    if lock is None:
        return None
    obj = _towee(universe, lock)
    if obj is None or _sector_of(obj) != int(universe.players[pid].sector_id):
        return None
    return lock, obj


def _manned_in_fedspace(obj: ParkedShip | Player) -> bool:
    return isinstance(obj, Player) and int(obj.sector_id) in K.FEDSPACE_SECTORS


def moving_towee(universe: Universe, pid: str) -> tuple[TowLock, ParkedShip | Player] | None:
    """The towee that would follow a move right now (a manned towee in FedSpace is released first, tt7)."""
    got = engaged(universe, pid)
    if got is None or _manned_in_fedspace(got[1]):
        return None
    return got


def move_cost(universe: Universe, player: Player) -> int:
    """Turns for one sector move (warp / interdictor attempt): the tt6 tow cost while towing."""
    from .runner import _warp_cost_for
    got = moving_towee(universe, player.id)
    if got is None:
        return int(_warp_cost_for(player))
    return tow_warp_cost(player.ship, _ship_of(got[1]))


def _label(universe: Universe, lock: TowLock) -> tuple[str, str | None]:
    obj = _towee(universe, lock)
    if obj is None:
        return ("ship " + str(lock.ship_id)) if lock.kind == "ship" else str(lock.player_id), None
    hull = _ship_of(obj).ship_class.value
    if isinstance(obj, Player):
        return obj.name, hull
    return f"{obj.ship.name} (ship {obj.id})", hull


def release(universe: Universe, ship: Ship, tower_pid: str | None, reason: str, owner_id: str | None = None) -> None:
    """Clear the lock on `ship` and tell the tower, a manned towee and the spectator (tt29)."""
    lock = lock_of(ship)
    if lock is None:
        return
    name, hull = _label(universe, lock)
    ship.tow_lock = None
    actor = tower_pid or owner_id
    witnesses = sorted({p for p in (actor, lock.player_id if lock.kind == "player" else None) if p})
    tower = universe.players.get(actor) if actor else None
    universe.emit(
        EventKind.TOW_RELEASED,
        actor_id=actor,
        sector_id=int(tower.sector_id) if tower is not None else None,
        payload={"reason": reason, "kind": lock.kind, "ship_id": lock.ship_id,
                 "target": lock.player_id if lock.kind == "player" else lock.ship_id,
                 "hull": hull, "_witnesses": witnesses},
        summary=f"Tractor beam on {name} released ({reason})",
    )


# ---- engage (tt2-tt5) --------------------------------------------------------------------------


def _tower_block(universe: Universe, pid: str) -> str | None:
    player = universe.players[pid]
    if not tow_on():
        return "towing is off (TOW_MODE legacy)"
    if not player.alive:
        return "player is destroyed"
    if player.planet_landed is not None:
        return "must be in space"
    if player.fighter_challenge:
        return "fighters challenge you here"
    if player.ship.ship_class.value in K.TOW_EXCLUDED_HULLS:
        return "an escape pod has no tractor beam"
    if lock_of(player.ship) is not None:
        return "your tractor beam is already locked (tow_release first)"
    if not K.TOW_CHAIN and towed_by(universe, "player", pid) is not None:
        return "you are in tow yourself"
    return None


def _ship_target_block(universe: Universe, pid: str, rec: ParkedShip | None) -> str | None:
    player = universe.players[pid]
    if not K.fleet_on():
        return "no unmanned ships (FLEET_MODE legacy)"
    if rec is None:
        return "no such ship"
    if rec.owner_id != pid:
        if not K.corpship_on():
            return "not your ship (own ships only)"
        from .corpships import tow_block
        why = tow_block(universe, pid, rec)
        if why is not None:
            return why
    if (K.hull_spec(rec.ship.ship_class.value) or {}).get("corp_only") and player.corp_ticker is None:
        return "corporation hull: you are no longer in a corporation"
    if int(rec.sector_id) != int(player.sector_id):
        return "that ship is not in your sector"
    if K.TOW_UNMANNED_FIGHTERS == "refuse" and int(rec.ship.fighters) > 0:
        return "that ship carries fighters"
    if _locked_anywhere(universe, "ship", rec.id):
        return "that ship is already locked in a tractor beam"
    if not K.TOW_CHAIN and lock_of(rec.ship) is not None:
        return "that ship holds a tow lock of its own"
    return None


def _player_target_block(universe: Universe, pid: str, other: Player | None) -> str | None:
    from .combat import _are_allied
    player = universe.players[pid]
    if K.TOW_MANNED == "off":
        return "towing traders is off (TOW_MANNED off)"
    if other is None or other.id == pid or not other.alive:
        return "no such trader"
    if int(other.sector_id) != int(player.sector_id):
        return "that trader is not in your sector"
    if K.TOW_MANNED == "corp_ally":
        same_corp = player.corp_ticker is not None and player.corp_ticker == other.corp_ticker
        if not same_corp and not _are_allied(universe, pid, other.id):
            return "only corp mates and allies can be towed (TOW_MANNED corp_ally)"
    if K.hardware_tw2002() and getattr(other.ship, "cloaked", False):
        return "no such trader"  # a cloaked ship is not there to lock (Iago)
    if other.planet_landed is not None:
        return "that trader is on a planet"
    if int(other.ship.fighters) > int(K.TOW_MANNED_MAX_FIGHTERS):
        return "towing a ship with fighters aboard is not possible"
    if int(other.sector_id) in K.FEDSPACE_SECTORS:
        return "you cannot tow a trader in FedSpace"
    if _locked_anywhere(universe, "player", other.id):
        return "that trader is already in tow"
    if not K.TOW_CHAIN and lock_of(other.ship) is not None:
        return "that trader is towing a ship"
    if other.fighter_challenge or getattr(other, "ferrengi_encounter", None):
        return "that trader is busy with a challenge"
    return None


def engage_choices(universe: Universe, pid: str) -> tuple[list[str], dict[str, int], dict[str, str]]:
    player = universe.players[pid]
    choices: list[str] = []
    cost_by: dict[str, int] = {}
    kind_by: dict[str, str] = {}
    if _tower_block(universe, pid) is not None:
        return choices, cost_by, kind_by
    if K.fleet_on():
        for sid in sorted(universe.parked_ships):
            rec = universe.parked_ships[sid]
            if _ship_target_block(universe, pid, rec) is None:
                t = f"ship:{sid}"
                choices.append(t)
                cost_by[t] = tow_warp_cost(player.ship, rec.ship)
                kind_by[t] = "ship"
    sector = universe.sectors[player.sector_id]
    for oid in sorted(set(sector.occupant_ids)):
        other = universe.players.get(oid)
        if oid != pid and other is not None and _player_target_block(universe, pid, other) is None:
            t = f"player:{oid}"
            choices.append(t)
            cost_by[t] = tow_warp_cost(player.ship, other.ship)
            kind_by[t] = "player"
    return choices, cost_by, kind_by


def handle_tow_engage(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not tow_on():
        return ActionResult(ok=False, error="unsupported action")
    why = _tower_block(universe, pid)
    if why is not None:
        return ActionResult(ok=False, error=why)
    raw = str((action.args or {}).get("target") or "")
    kind, _, ident = raw.partition(":")
    player = universe.players[pid]
    if kind == "ship":
        try:
            sid = int(ident)
        except ValueError:
            return ActionResult(ok=False, error=f"invalid tow target {raw!r}")
        rec = universe.parked_ships.get(sid)
        why = _ship_target_block(universe, pid, rec)
        if why is not None:
            return ActionResult(ok=False, error=why)
        assert rec is not None
        if K.corpship_on():
            from .corpships import note_password_fail, password_block
            pw_why = password_block(pid, rec, (action.args or {}).get("password"))
            if pw_why is not None:
                note_password_fail(universe, pid)
                return ActionResult(ok=False, error=pw_why)
        lock = TowLock(kind="ship", ship_id=sid, engaged_day=int(universe.day))
        towee_ship, name, manned = rec.ship, f"{rec.ship.name} (ship {sid})", None
    elif kind == "player":
        other = universe.players.get(ident)
        why = _player_target_block(universe, pid, other)
        if why is not None:
            return ActionResult(ok=False, error=why)
        assert other is not None
        lock = TowLock(kind="player", player_id=other.id, engaged_day=int(universe.day))
        towee_ship, name, manned = other.ship, other.name, other.id
    else:
        return ActionResult(ok=False, error="tow_engage target must be ship:<id> or player:<pid>")
    player.ship.tow_lock = lock
    cost = tow_warp_cost(player.ship, towee_ship)
    universe.emit(
        EventKind.TOW_ENGAGED,
        actor_id=pid,
        sector_id=int(player.sector_id),
        payload={"kind": kind, "ship_id": lock.ship_id, "target": manned or lock.ship_id,
                 "hull": towee_ship.ship_class.value, "cost": cost,
                 "_witnesses": sorted({pid} | ({manned} if manned else set()))},
        summary=f"{player.name} locked a tractor beam on {name} ({cost} turns per sector)",
    )
    return ActionResult(ok=True, turns_spent=int(K.TURN_COST["tow_engage"]))


def handle_tow_release(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not tow_on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    if lock_of(player.ship) is None:
        return ActionResult(ok=False, error="your tractor beam is not locked")
    release(universe, player.ship, pid, "manual")
    return ActionResult(ok=True, turns_spent=int(K.TURN_COST["tow_release"]))


# ---- moving with a tow (tt6-tt10, tt19) --------------------------------------------------------


def begin_move(universe: Universe, pid: str) -> tuple[Ship, TowLock, ParkedShip | Player] | None:
    """Before a tower moves: release a manned towee sitting in FedSpace (tt11h); return what will follow."""
    got = engaged(universe, pid)
    if got is None:
        return None
    lock, obj = got
    player = universe.players[pid]
    if _manned_in_fedspace(obj):
        release(universe, player.ship, pid, "fedspace")
        return None
    return player.ship, lock, obj


def _relocate_manned(universe: Universe, towee: Player, from_id: int, to_id: int, via: str) -> None:
    from .runner import _clear_photon_damp, _learn_sector, _record_port_intel
    try:
        universe.sectors[from_id].occupant_ids.remove(towee.id)
    except ValueError:
        pass
    dest = universe.sectors[to_id]
    if towee.id not in dest.occupant_ids:
        dest.occupant_ids.append(towee.id)
    towee.prev_sector_id = int(from_id)
    towee.sector_id = int(to_id)
    towee.end_port_visit()
    towee.planet_landed = None
    if towee.photon_damped_sector_id == from_id:
        _clear_photon_damp(towee, from_id)
    towee.arrived_by_transwarp = via == "transwarp"
    towee.arrived_by_transport = False
    _learn_sector(towee, universe, to_id)
    if dest.port is not None:
        _record_port_intel(towee, dest.id, dest.port, universe=universe)


def finish_move(universe: Universe, pid: str, ctx: tuple[Ship, TowLock, ParkedShip | Player] | None,
                from_id: int, to_id: int, via: str) -> bool:
    """After the tower's own entry: the towee follows only if the tower survived and is in `to_id` (tt7-tt9).
    The towee takes no entry hazard of any kind (tt8): it is placed, nothing fires."""
    if ctx is None:
        return False
    ship, lock, obj = ctx
    player = universe.players[pid]
    if player.ship is not ship or not player.alive:
        release(universe, ship, pid, "tower_destroyed")
        return False
    if lock_of(ship) is not lock:
        return False
    if int(player.sector_id) != int(to_id):
        return False
    from_witnesses = set(universe.sectors[from_id].occupant_ids)
    if isinstance(obj, ParkedShip):
        obj.sector_id = int(to_id)
        manned = None
    else:
        _relocate_manned(universe, obj, from_id, to_id, via)
        manned = obj.id
    hull = _ship_of(obj).ship_class.value
    witnesses = sorted(from_witnesses | set(universe.sectors[to_id].occupant_ids) | {pid})
    universe.emit(
        EventKind.TOWED,
        actor_id=pid,
        sector_id=int(to_id),
        payload={"from": int(from_id), "to": int(to_id), "hull": hull, "via": via, "kind": lock.kind,
                 "ship_id": lock.ship_id, "target": manned or lock.ship_id, "_witnesses": witnesses},
        summary=f"{player.name} towed a {hull} {from_id} → {to_id}",
    )
    if manned is not None and obj.alive:
        from .fed import check_iss_repo_on_move
        check_iss_repo_on_move(universe, manned)
    return True


def fuse_towee(universe: Universe, pid: str, ctx: tuple[Ship, TowLock, ParkedShip | Player] | None) -> None:
    """tt20: the tower fused on a blind tow jump. "stays" leaves the towee at the origin."""
    if ctx is None:
        return
    ship, lock, obj = ctx
    release(universe, ship, pid, "tower_destroyed")
    if K.TOW_FUSE_TOWEE != "destroyed":
        return
    if isinstance(obj, ParkedShip):
        from .fleet import _remove
        _remove(universe, int(obj.id))
    elif obj.alive:
        from .combat import _destroy_ship
        _destroy_ship(universe, obj.id, reason="transwarp_fuse", killer_id=None)


# ---- break conditions after any action (tt11, tt12) ---------------------------------------------


def snapshot(universe: Universe) -> list[tuple[str | None, Ship, TowLock, int | None, int | None]] | None:
    """Locks before an action: (pilot, hull, lock, tower sector, towee sector). None when there are none."""
    if not tow_on():
        return None
    locks = _hull_locks(universe)
    if not locks:
        return None
    out = []
    for pid, ship, lock in locks:
        obj = _towee(universe, lock)
        tsec = int(universe.players[pid].sector_id) if pid is not None else None
        out.append((pid, ship, lock, tsec, _sector_of(obj) if obj is not None else None))
    return out


def _parked_with(universe: Universe, ship: Ship) -> ParkedShip | None:
    for rec in universe.parked_ships.values():
        if rec.ship is ship:
            return rec
    return None


def _own_break(action: Action, result: ActionResult, actor: Player) -> str | None:
    kind = action.kind.value if isinstance(action.kind, ActionKind) else str(action.kind)
    if kind == "land_planet" and actor.planet_landed is not None:
        return "land"
    if kind in PORT_VERBS and (result.ok or result.turns_spent > 0):
        return "port"
    if kind in K.TOW_DOCK_VERBS and result.ok:
        return "dock"
    if kind in ATTACK_VERBS and result.ok and K.TOW_ON_ATTACK == "release":
        return "attack"
    return None


def after_action(universe: Universe, actor_id: str, action: Action, result: ActionResult,
                 snap: list[tuple[str | None, Ship, TowLock, int | None, int | None]] | None) -> None:
    if not snap:
        return
    actor = universe.players.get(actor_id)
    for pid, ship, lock, tsec, wsec in snap:
        if lock_of(ship) is not lock:
            continue  # released / replaced inside the action (warp, jump, manual)
        if pid is None:
            check_dormant(universe, ship)
            continue
        tower = universe.players[pid]
        if tower.ship is not ship:
            if _parked_with(universe, ship) is not None:  # tt12: the pilot beamed out of the tower
                if K.TOW_LOCK_ON_XPORT == "release":
                    release(universe, ship, None, "xport", owner_id=pid)
                else:
                    check_dormant(universe, ship)
            else:
                release(universe, ship, pid, "tower_destroyed")
            continue
        if not tower.alive:
            release(universe, ship, pid, "tower_destroyed")
            continue
        obj = _towee(universe, lock)
        if obj is None:
            release(universe, ship, pid, "towee_gone")
            continue
        reason = None
        if actor is not None and actor_id == pid:
            reason = _own_break(action, result, tower)
        elif actor is not None and isinstance(obj, Player) and obj.id == actor_id:
            reason = _own_break(action, result, obj)
            if reason is None and _sector_of(obj) != wsec:
                reason = "towee_moved"
        if reason is None and tower.planet_landed is not None:
            reason = "land"
        if reason is None and isinstance(obj, Player) and obj.planet_landed is not None:
            reason = "land"
        if reason is None and _sector_of(obj) != int(tower.sector_id):
            if _sector_of(obj) != wsec:
                reason = "towee_moved"
            elif K.TOW_ON_RETREAT == "drag" and actor_id == pid and wsec == tsec:
                finish_move(universe, pid, (ship, lock, obj), int(wsec), int(tower.sector_id), "retreat")
                continue
            else:
                reason = "retreat" if actor_id == pid else "towee_gone"
        if reason is not None:
            release(universe, ship, pid, reason)


def check_dormant(universe: Universe, ship: Ship) -> None:
    """tt12: a parked tower's lock stays dormant while tower and towee share a sector; else it is released."""
    lock = lock_of(ship)
    rec = _parked_with(universe, ship)
    if lock is None or rec is None:
        return
    obj = _towee(universe, lock)
    if obj is None and lock.kind == "ship":
        owner = universe.players.get(rec.owner_id)  # the owner may be flying the towee hull itself
        if owner is not None and owner.alive and owner.ship.fleet_id == lock.ship_id:
            obj = owner
    if obj is None or _sector_of(obj) != int(rec.sector_id):
        release(universe, ship, None, "towee_gone", owner_id=rec.owner_id)


def sweep(universe: Universe, reason: str) -> None:
    """Overnight: release every lock whose tower and towee are apart (Fed tows, retreats, flees)."""
    if not tow_on():
        return
    for pid, ship, lock in _hull_locks(universe):
        if pid is None:
            check_dormant(universe, ship)
            continue
        tower = universe.players[pid]
        obj = _towee(universe, lock)
        if obj is None:
            release(universe, ship, pid, "towee_gone")
        elif _sector_of(obj) != int(tower.sector_id) or tower.planet_landed is not None:
            release(universe, ship, pid, reason)


# ---- Extern tow-lock hold (tt22, tt23) --------------------------------------------------------


def _lock_holds_ship(lock: TowLock | None, rec: ParkedShip) -> bool:
    return lock is not None and lock.kind == "ship" and int(lock.ship_id or -1) == int(rec.id)


def _same_corp(owner: Player, other: Player) -> bool:
    ticker = getattr(owner, "corp_ticker", None)
    return bool(ticker) and ticker == getattr(other, "corp_ticker", None)


def holding_tower(universe: Universe, rec: ParkedShip) -> Player | None:
    """The pilot whose lock keeps this hull, or None. A corp mate counts only when the fix is on."""
    owner = universe.players.get(rec.owner_id)
    if owner is None:
        return None
    if _lock_holds_ship(lock_of(owner.ship), rec):
        return owner
    if not (K.corp_fix_on(corp=True) and K.TOW_EXTERN_HOLDER == "owner_or_corp"):
        return None
    for pid in sorted(universe.players):
        tower = universe.players[pid]
        if not tower.alive or tower.id == owner.id:
            continue
        if not _lock_holds_ship(lock_of(tower.ship), rec):
            continue
        if _same_corp(owner, tower):
            return tower
    return None


def extern_hold_why(universe: Universe, rec: ParkedShip) -> str | None:
    """None = this unmanned FedSpace ship survives Extern right now (cabal tips #4)."""
    if not tow_on() or K.TOW_EXTERN_LOCK != "hold":
        return "off"
    owner = universe.players.get(rec.owner_id)
    if owner is None or not owner.alive:
        return "no_owner"
    tower = holding_tower(universe, rec)
    if tower is None:
        for _p, _ship, other in _hull_locks(universe):
            if _p is None and other.kind == "ship" and int(other.ship_id or -1) == int(rec.id):
                return "dormant"
        return "no_lock"
    if int(tower.sector_id) != int(rec.sector_id):
        return "not_same_sector"
    if tower.planet_landed is not None:
        return "landed"
    if int(tower.ship.fighters) > int(K.FED_TOW_FIGHTER_LIMIT):
        return "tower_has_too_many_fighters"
    if K.TOW_EXTERN_REQUIRE_GOOD and int(tower.alignment) < 0:
        return "tower_not_good"
    return None


def emit_hold(universe: Universe, rec: ParkedShip) -> None:
    tower = holding_tower(universe, rec)
    witnesses = [rec.owner_id]
    if tower is not None and tower.id not in witnesses:
        witnesses.append(tower.id)
    universe.emit(
        EventKind.EXTERN_TOW_HOLD,
        actor_id=rec.owner_id,
        sector_id=int(rec.sector_id),
        payload={"ship_id": int(rec.id), "hull": rec.ship.ship_class.value, "sector": int(rec.sector_id),
                 "_witnesses": witnesses},
        summary=f"Extern: the {rec.ship.name} (ship {rec.id}) stayed in sector {rec.sector_id} - held in tow",
    )


# ---- Type 2 TransWarp shelf (tt16) -------------------------------------------------------------


def type2_offer(player: Player) -> dict[str, int]:
    """StarDock shelf items for this hull: transwarp_type2 (no drive) / transwarp_upgrade (type1 fitted)."""
    if not (tow_on() and K.ship_tw_on()) or player.sector_id != K.STARDOCK_SECTOR:
        return {}
    if player.ship.ship_class.value not in K.SHIP_TW_HULLS:
        return {}
    drive = getattr(player.ship, "transwarp_drive", None)
    if drive is None:
        return {"transwarp_type2": int(K.SHIP_TW_TYPE2_COST)}
    if drive == "type1":
        return {"transwarp_upgrade": int(K.SHIP_TW_UPGRADE_COST)}
    return {}


def buy_type2(universe: Universe, pid: str, item: str, qty: int) -> ActionResult:
    player = universe.players[pid]
    if qty != 1:
        return ActionResult(ok=False, error="a TransWarp drive is bought one at a time")
    if player.sector_id != K.STARDOCK_SECTOR:
        return ActionResult(ok=False, error="TransWarp drives are sold at StarDock only")
    if player.ship.ship_class.value not in K.SHIP_TW_HULLS:
        return ActionResult(ok=False, error="only an Imperial StarShip, Corporate FlagShip, or Havoc Gunstar can fit a TransWarp drive")
    offer = type2_offer(player)
    if item not in offer:
        drive = getattr(player.ship, "transwarp_drive", None)
        if item == "transwarp_upgrade" and drive is None:
            return ActionResult(ok=False, error="the upgrade needs a Type 1 drive fitted")
        return ActionResult(ok=False, error="already fitted")
    cost = int(offer[item])
    if player.credits < cost:
        return ActionResult(ok=False, error=f"insufficient credits ({player.credits} < {cost})")
    player.credits -= cost
    player.ship.transwarp_drive = "type2"
    label = "Type 2 TransWarp drive" if item == "transwarp_type2" else "TransWarp upgrade to Type 2"
    universe.emit(
        EventKind.BUY_EQUIP,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"item": item, "qty": 1, "total": cost},
        summary=f"{player.name} bought a {label} for {cost}cr",
    )
    return ActionResult(ok=True, turns_spent=0)


# ---- observation (tt21, tt29) ------------------------------------------------------------------


def ship_tow_view(universe: Universe, pid: str) -> dict[str, Any]:
    player = universe.players[pid]
    lock = lock_of(player.ship)
    target = None
    turns = None
    if lock is not None:
        obj = _towee(universe, lock)
        if obj is not None:
            target = {"kind": lock.kind, "hull": _ship_of(obj).ship_class.value}
            if isinstance(obj, Player):
                target["name"] = obj.name
            else:
                target["ship_id"] = int(obj.id)
            turns = tow_warp_cost(player.ship, _ship_of(obj))
    got = engaged(universe, pid)
    hold_why = None
    if lock is not None and lock.kind == "ship":
        rec = universe.parked_ships.get(int(lock.ship_id or -1))
        if rec is not None:
            hold_why = extern_hold_why(universe, rec)
    return {
        "engaged": got is not None,
        "dormant": False,
        "target": target,
        "turns_per_tow_warp": turns,
        "extern_hold_ok": lock is not None and lock.kind == "ship" and hold_why is None,
        "why_not": hold_why if lock is not None and lock.kind == "ship" else None,
    }


def in_tow_view(universe: Universe, pid: str) -> dict[str, Any] | None:
    tower_id = towed_by(universe, "player", pid)
    if tower_id is None:
        return None
    tower = universe.players[tower_id]
    return {"name": tower.name, "hull": tower.ship.ship_class.value}


def fleet_entry_extra(universe: Universe, rec: ParkedShip) -> dict[str, Any]:
    holder = towed_by(universe, "ship", rec.id)
    hold = holder is not None and int(rec.sector_id) in K.FEDSPACE_SECTORS and extern_hold_why(universe, rec) is None
    return {"in_tow": holder is not None, "extern_hold": bool(hold)}


# ---- legal list (tt5, verbs) ------------------------------------------------------------------


def legal_specs(universe: Universe, pid: str) -> list[tuple[str, bool, str | None, int, dict[str, Any]]]:
    out: list[tuple[str, bool, str | None, int, dict[str, Any]]] = []
    why = _tower_block(universe, pid)
    choices, cost_by, kind_by = engage_choices(universe, pid)
    if why is None and not choices:
        why = "no ship you can lock in this sector"
    params: dict[str, Any] = {"target": {"type": "str", "required": True, "choices": choices, "cost_by": cost_by,
                                         "kind_by": kind_by}}
    if K.corpship_on():
        from .corpships import detail_for
        params["password"] = {"type": "str", "required": False}
        params["target"]["detail_by"] = {  # QC: same {owner, class, password_required} as the X-port list
            t: detail_for(universe, pid, universe.parked_ships[int(t.split(":", 1)[1])], None)
            for t in choices if kind_by.get(t) == "ship"
        }
    out.append(("tow_engage", why is None, why, int(K.TURN_COST["tow_engage"]), params))
    has = lock_of(universe.players[pid].ship) is not None
    out.append(("tow_release", has, None if has else "your tractor beam is not locked",
                int(K.TURN_COST["tow_release"]), {}))
    return out
