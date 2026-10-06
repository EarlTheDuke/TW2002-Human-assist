"""Type 1 ship TransWarp (SHIP_TW_MODE). docs/playtests/ships/SHIP_TRANSWARP.md.

Type 2 tow, multi-ship, the ship transporter, and tractor towing are not here.
The hop search is a local BFS. It does not draw from universe.rng.
"""

from __future__ import annotations

from typing import Any

from . import constants as K
from .actions import Action, ActionResult
from .combat import _are_allied
from .models import Commodity, EventKind, Universe
from .victory import is_commissioned


def ship_tw_on() -> bool:
    return K.SHIP_TW_MODE == "tw2002"


def hull_can_fit(class_key: str | None) -> bool:
    return str(class_key or "") in K.SHIP_TW_HULLS


def drive_fitted(ship) -> bool:
    return str(getattr(ship, "transwarp_drive", None) or "") == "type1"


def fuel_ore(ship) -> int:
    cargo = getattr(ship, "cargo", None) or {}
    try:
        return int(cargo.get(Commodity.FUEL_ORE, 0) or 0)
    except (TypeError, ValueError):
        return 0


def hop_count(universe: Universe, start: int, dest: int) -> int | None:
    """Edge count of the shortest warp path. Ignores avoids. None if no path.

    Same sector is 0. One-way links count only along warps out.
    """
    start, dest = int(start), int(dest)
    if start == dest:
        return 0
    seen = {start}
    wave = [start]
    dist = 0
    while wave:
        dist += 1
        nxt: list[int] = []
        for sid in wave:
            sector = universe.sectors.get(sid)
            if sector is None:
                continue
            for raw in sector.warps:
                n = int(raw)
                if n in seen:
                    continue
                if n == dest:
                    return dist
                seen.add(n)
                nxt.append(n)
        wave = nxt
    return None


def _fed_lock(player, sector_id: int) -> bool:
    if K.SHIP_TW_FED_LOCK != "commissioned":
        return False
    if not is_commissioned(player):
        return False
    return int(sector_id) in K.FEDSPACE_SECTORS


def _fighter_lock(universe: Universe, pid: str, sector_id: int) -> bool:
    sector = universe.sectors.get(int(sector_id))
    dep = getattr(sector, "fighters", None) if sector is not None else None
    if dep is None or int(getattr(dep, "count", 0) or 0) <= 0:
        return False
    owner = str(getattr(dep, "owner_id", "") or "")
    if not owner:
        return False
    if K.SHIP_TW_FRIENDLY == "own_only":
        return owner == pid
    if owner == pid:
        return True
    return _are_allied(universe, pid, owner)


def has_lock(universe: Universe, pid: str, sector_id: int) -> bool:
    player = universe.players[pid]
    return _fighter_lock(universe, pid, sector_id) or _fed_lock(player, sector_id)


def turn_cost(player, hops: int) -> int:
    """tw11: one ship turns-per-warp (same helper as a normal warp); "hops" = TPW * hops."""
    from .runner import _warp_cost_for
    tpw = int(_warp_cost_for(player))
    if K.SHIP_TW_TURN_COST == "hops":
        return tpw * max(1, int(hops))
    return tpw


def ore_cost(hops: int) -> int:
    return int(K.SHIP_TW_ORE_PER_HOP) * int(hops)


def drive_buyable(player) -> bool:
    """StarDock shelf: eligible hull, no drive yet. Credits are checked by the caller."""
    if not ship_tw_on():
        return False
    if player.sector_id != K.STARDOCK_SECTOR:
        return False
    if not hull_can_fit(player.ship.ship_class.value):
        return False
    if drive_fitted(player.ship):
        return False
    return True


def buy_drive(universe: Universe, pid: str, qty: int) -> ActionResult:
    player = universe.players[pid]
    if not ship_tw_on():
        return ActionResult(ok=False, error="transwarp drive unavailable (SHIP_TW_MODE legacy)")
    if qty != 1:
        return ActionResult(ok=False, error="a TransWarp drive is bought one at a time")
    if player.sector_id != K.STARDOCK_SECTOR:
        return ActionResult(ok=False, error="TransWarp drives are sold at StarDock only")
    if not hull_can_fit(player.ship.ship_class.value):
        return ActionResult(ok=False, error="only an Imperial StarShip, Corporate FlagShip, or Havoc Gunstar can fit a TransWarp drive")
    if drive_fitted(player.ship):
        return ActionResult(ok=False, error="already fitted")
    cost = int(K.SHIP_TW_TYPE1_COST)
    if player.credits < cost:
        return ActionResult(ok=False, error=f"insufficient credits ({player.credits} < {cost})")
    player.credits -= cost
    player.ship.transwarp_drive = "type1"
    universe.emit(
        EventKind.BUY_EQUIP,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"item": "transwarp_drive", "qty": 1, "total": cost},
        summary=f"{player.name} bought a Type 1 TransWarp drive for {cost}cr",
    )
    return ActionResult(ok=True, turns_spent=0)


def _known(player, sector_id: int) -> bool:
    if int(sector_id) == int(player.sector_id):
        return True
    known = getattr(player, "known_sectors", None) or set()
    return int(sector_id) in {int(s) for s in known}


def locked_choices(universe: Universe, pid: str) -> list[dict[str, int]]:
    """Locked destinations this seat can name, with hop and ore cost. No blind targets."""
    player = universe.players[pid]
    if not ship_tw_on() or not drive_fitted(player.ship) or not hull_can_fit(player.ship.ship_class.value):
        return []
    if player.planet_landed is not None or player.fighter_challenge:
        return []
    here = int(player.sector_id)
    ore = fuel_ore(player.ship)
    names: set[int] = set()
    for sid in list(getattr(player, "known_sectors", None) or []):
        names.add(int(sid))
    if _fed_lock(player, K.STARDOCK_SECTOR):
        names.update(int(s) for s in K.FEDSPACE_SECTORS if int(s) in universe.sectors)
    names.add(here)
    if is_commissioned(player) and K.SHIP_TW_FED_LOCK == "commissioned":
        names.update(int(s) for s in K.FEDSPACE_SECTORS)
    rows: list[tuple[int, int, int]] = []
    for sid in names:
        if sid == here or not has_lock(universe, pid, sid):
            continue
        hops = hop_count(universe, here, sid)
        if hops is None or hops <= 0:
            continue
        need = ore_cost(hops)
        if ore < need:
            continue
        if player.turns_today + turn_cost(player, hops) > player.turns_per_day:
            continue
        rows.append((sid, hops, need))
    rows.sort(key=lambda r: (r[1], r[0]))
    cap = int(K.SHIP_TW_LIST_CAP)
    return [{"sector_id": sid, "hops": hops, "ore": need} for sid, hops, need in rows[:cap]]


def legal_spec(universe: Universe, pid: str) -> tuple[bool, str | None, dict[str, Any], int]:
    player = universe.players[pid]
    if not ship_tw_on():
        return False, "ship TransWarp is off (SHIP_TW_MODE legacy)", {}, 0
    if not hull_can_fit(player.ship.ship_class.value):
        return False, "this hull cannot TransWarp", {}, 0
    if not drive_fitted(player.ship):
        return False, "no TransWarp drive (buy_equip transwarp_drive at StarDock)", {}, 0
    if player.planet_landed is not None:
        return False, "must be in space", {}, 0
    if player.fighter_challenge:
        return False, "fighters challenge you here", {}, 0
    choices = locked_choices(universe, pid)
    if not choices:
        if fuel_ore(player.ship) < int(K.SHIP_TW_ORE_PER_HOP):
            return False, "not enough fuel ore", {}, 0
        return False, "no TransWarp lock in range", {}, 0
    params = {
        "sector_id": {
            "type": "int",
            "required": True,
            "choices": [row["sector_id"] for row in choices],
            "hops_by": {str(row["sector_id"]): row["hops"] for row in choices},
            "ore_by": {str(row["sector_id"]): row["ore"] for row in choices},
        }
    }
    cheapest = min(turn_cost(player, row["hops"]) for row in choices)
    return True, None, params, cheapest


def _spend_ore(player, amount: int) -> None:
    have = fuel_ore(player.ship)
    player.ship.cargo[Commodity.FUEL_ORE] = max(0, have - int(amount))


def _density(universe: Universe, sector_id: int) -> int:
    from .scanners import density_reading
    return int(density_reading(universe, sector_id).get("density") or 0)


def _land(universe: Universe, pid: str, dest_id: int, from_id: int) -> bool:
    """Run a normal sector entry. True if the pilot is still alive in dest."""
    from .combat import open_challenge
    from .hardware import (
        apply_carried_photon_blast,
        carried_photon_hazard,
        hostile_mines_present,
        sector_photon_active,
    )
    from .runner import _apply_sector_hazards, _learn_sector, _record_port_intel

    player = universe.players[pid]
    dest = universe.sectors[dest_id]
    if K.SHIP_TW_CLOAK_POLICY == "allow_decloak" and getattr(player.ship, "cloaked", False):
        player.ship.cloaked = False
        player.ship.cloak_activated_day = None
    deaths_before = player.deaths
    player.prev_sector_id = int(from_id)
    if K.hardware_tw2002() and carried_photon_hazard(universe, pid, dest):
        apply_carried_photon_blast(universe, pid)
    mined = K.hardware_tw2002() and not sector_photon_active(dest) and hostile_mines_present(universe, pid, dest)
    _apply_sector_hazards(universe, pid, dest)
    died = (not player.alive) or (K.death_tw2002() and player.deaths != deaths_before)
    if not player.alive or died:
        return False
    try:
        universe.sectors[player.sector_id].occupant_ids.remove(pid)
    except ValueError:
        pass
    player.sector_id = int(dest_id)
    player.end_port_visit()
    if pid not in dest.occupant_ids:
        dest.occupant_ids.append(pid)
    player.arrived_by_transwarp = True
    _learn_sector(player, universe, dest_id)
    if dest.port is not None:
        _record_port_intel(player, dest.id, dest.port, universe=universe)
    if not K.hardware_tw2002() and player.deaths == deaths_before and player.sector_id == dest_id:
        from .runner import _apply_sector_quasar
        _apply_sector_quasar(universe, pid, dest)
    if player.alive and player.deaths == deaths_before and player.sector_id == dest_id:
        open_challenge(universe, pid, dest, int(from_id))
    if mined and player.alive and player.deaths == deaths_before and player.sector_id == dest_id:
        universe.emit(
            EventKind.HAZARD_AVOID_PROMPT,
            actor_id=pid,
            sector_id=dest_id,
            payload={"sector": dest_id, "reason": "mines"},
            summary=f"Mines in sector {dest_id}: avoid this sector? (autopilot stops here)",
        )
    return player.alive and player.sector_id == dest_id


def handle_ship_transwarp(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if not ship_tw_on():
        return ActionResult(ok=False, error="unsupported action")
    raw = action.args.get("sector_id", action.args.get("target"))
    try:
        dest_id = int(raw)
    except (TypeError, ValueError):
        return ActionResult(ok=False, error="ship_transwarp requires sector_id")
    if dest_id not in universe.sectors:
        return ActionResult(ok=False, error=f"unknown sector {dest_id}")
    if not hull_can_fit(player.ship.ship_class.value):
        return ActionResult(ok=False, error="this hull cannot TransWarp")
    if not drive_fitted(player.ship):
        return ActionResult(ok=False, error="no TransWarp drive")
    if player.planet_landed is not None:
        return ActionResult(ok=False, error="must be in space")
    if player.fighter_challenge:
        return ActionResult(ok=False, error="fighters challenge you here")
    here = int(player.sector_id)
    if dest_id == here:
        return ActionResult(ok=False, error="already in that sector")
    hops = hop_count(universe, here, dest_id)
    if hops is None or hops <= 0:
        return ActionResult(ok=False, error="no warp path to that sector")
    need = ore_cost(hops)
    if fuel_ore(player.ship) < need:
        return ActionResult(ok=False, error=f"not enough fuel ore (need {need})")
    cost = turn_cost(player, hops)
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns for this day")
    locked = has_lock(universe, pid, dest_id)
    blind = not locked
    if blind and K.SHIP_TW_BLIND == "refuse":
        return ActionResult(ok=False, error="blind TransWarp is refused")
    # tw12b: a planetary Interdictor holds a TransWarp out like a warp (cabal planets.html).
    from .runner import _clear_photon_damp, _try_interdict
    held = _try_interdict(universe, pid, universe.sectors[here])
    if held is not None:
        return held
    if player.photon_damped_sector_id == here:
        _clear_photon_damp(player, here)
    _spend_ore(player, need)
    if blind and K.SHIP_TW_BLIND == "density0" and _density(universe, dest_id) > 0:
        from .combat import _destroy_ship
        universe.emit(
            EventKind.SHIP_TRANSWARP_FUSE,
            actor_id=pid,
            sector_id=here,
            payload={"from": here, "to": dest_id, "hops": hops, "ore": need, "locked": False},
            summary=f"{player.name}'s TransWarp into {dest_id} fused (density)",
        )
        _destroy_ship(universe, pid, reason="transwarp_fuse", killer_id=None)
        return ActionResult(ok=True, turns_spent=0 if K.SHIP_TW_FUSE_REFUNDS else cost)
    landed = _land(universe, pid, dest_id, here)
    universe.emit(
        EventKind.SHIP_TRANSWARP,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={
            "from": here, "to": dest_id, "hops": hops, "ore": need,
            "locked": bool(locked), "blind": bool(blind), "landed": bool(landed),
        },
        summary=f"{player.name} TransWarped {here} → {dest_id} ({hops} hops, {need} ore)",
    )
    if player.alive:
        from .fed import check_iss_repo_on_move  # fedspace-police-v1 f6/f22, as after a warp
        check_iss_repo_on_move(universe, pid)
    return ActionResult(ok=True, turns_spent=cost)


def clear_drive(ship) -> None:
    if hasattr(ship, "transwarp_drive"):
        ship.transwarp_drive = None
