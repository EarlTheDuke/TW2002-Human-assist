"""Ship fleet + transporter (docs/playtests/ships/SHIP_FLEET.md, FLEET_MODE).

A trader owns player.ship (the manned ship) plus every ParkedShip with owner_id == pid. Moving
between hulls moves Ship OBJECTS: a parked hull never aliases player.ship (fl3), because the death
path strips player.ship in place. Nothing here draws from universe.rng (fl29).
"""

from __future__ import annotations

import math
from collections import deque
from fractions import Fraction
from typing import Any

from . import constants as K
from .actions import Action, ActionResult
from .combat import _are_allied
from .models import Commodity, EventKind, MineType, ParkedShip, Ship, ShipClass, Universe

# ---- registry -------------------------------------------------------------------------------


def owned_parked(universe: Universe, pid: str) -> list[ParkedShip]:
    """This pilot's parked ships, by fleet id (deterministic order)."""
    return [p for _i, p in sorted(universe.parked_ships.items()) if p.owner_id == pid]


def fleet_size(universe: Universe, pid: str) -> int:
    """fl2: the manned ship counts."""
    return 1 + len(owned_parked(universe, pid))


def classes_owned_anywhere(universe: Universe) -> set[str]:
    """fl6: hull classes flown or parked by anyone (unique ISS check)."""
    out = {p.ship.ship_class.value for p in universe.players.values()}
    out.update(p.ship.ship_class.value for p in universe.parked_ships.values())
    return out


def _new_ship_id(universe: Universe) -> int:
    sid = int(universe.next_ship_id)
    universe.next_ship_id = sid + 1
    return sid


def _ensure_fleet_id(universe: Universe, ship: Ship) -> int:
    if ship.fleet_id is None:
        ship.fleet_id = _new_ship_id(universe)
    return int(ship.fleet_id)


def _parse_id(raw: Any) -> int | None:
    if isinstance(raw, str) and raw.startswith("ship:"):
        raw = raw.split(":", 1)[1]
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _remove(universe: Universe, ship_id: int) -> ParkedShip | None:
    rec = universe.parked_ships.pop(int(ship_id), None)
    if rec is not None:
        _drop_hull_limpets(universe, int(ship_id))
    return rec


def drop_owner_fleet(universe: Universe, pid: str) -> int:
    """fl26: elimination removes the owner's parked ships (deliberate)."""
    ids = [p.id for p in owned_parked(universe, pid)]
    for sid in ids:
        _remove(universe, sid)
    return len(ids)


# ---- hops (fl10 / fl11) -----------------------------------------------------------------------


def hops_between(universe: Universe, src: int, dst: int, metric: str | None = None) -> int | None:
    """Shortest warp-path hop count, warp direction followed under "directed", avoids ignored."""
    src, dst = int(src), int(dst)
    if src == dst:
        return 0
    metric = metric or K.FLEET_XPORT_METRIC
    adj: dict[int, list[int]] | None = None
    if metric == "undirected":
        adj = {}
        for sid in sorted(universe.sectors):
            for w in universe.sectors[sid].warps:
                adj.setdefault(int(sid), []).append(int(w))
                adj.setdefault(int(w), []).append(int(sid))
    seen = {src}
    q: deque[tuple[int, int]] = deque([(src, 0)])
    while q:
        cur, d = q.popleft()
        if adj is not None:
            nbrs = adj.get(cur, [])
        else:
            sec = universe.sectors.get(cur)
            nbrs = [int(w) for w in sec.warps] if sec is not None else []
        for n in nbrs:
            if n in seen:
                continue
            if n == dst:
                return d + 1
            seen.add(n)
            q.append((n, d + 1))
    return None


# ---- limpets (fl19) ---------------------------------------------------------------------------


def _limpets_leave_hull(universe: Universe, pid: str, fleet_id: int) -> None:
    if K.FLEET_LIMPET_POLICY != "hull":
        return
    for key in sorted(universe.limpets):
        lt = universe.limpets[key]
        if lt.target_id == pid and lt.target_ship_id is None:
            lt.target_ship_id = int(fleet_id)
            universe.limpets.pop(key)
            universe.limpets[f"{lt.owner_id}:ship:{fleet_id}"] = lt


def _limpets_board_hull(universe: Universe, pid: str, fleet_id: int) -> None:
    if K.FLEET_LIMPET_POLICY != "hull":
        return
    for key in sorted(universe.limpets):
        lt = universe.limpets[key]
        if lt.target_ship_id == int(fleet_id):
            lt.target_ship_id = None
            lt.target_id = pid
            universe.limpets.pop(key)
            universe.limpets[f"{lt.owner_id}:{pid}"] = lt


def _drop_pilot_limpets(universe: Universe, pid: str) -> None:
    for key in sorted(universe.limpets):
        lt = universe.limpets[key]
        if lt.target_id == pid and lt.target_ship_id is None:
            universe.limpets.pop(key)


def _drop_hull_limpets(universe: Universe, fleet_id: int) -> None:
    for key in sorted(universe.limpets):
        if universe.limpets[key].target_ship_id == int(fleet_id):
            universe.limpets.pop(key)


def limpet_location(universe: Universe, lt) -> tuple[int | None, str | None]:
    """(sector, hull) a limpet track reports: the parked hull's sector while the hull sits unmanned."""
    if lt.target_ship_id is not None:
        rec = universe.parked_ships.get(int(lt.target_ship_id))
        if rec is None:
            return None, None
        return int(rec.sector_id), rec.ship.ship_class.value
    target = universe.players.get(lt.target_id)
    if target is None:
        return None, None
    return int(target.sector_id), target.ship.ship_class.value


# ---- buy without trade-in / sell (fl4-fl7) -----------------------------------------------------


def wants_spare(action: Action) -> bool:
    """buy_ship trade_in=false. Only read under FLEET_MODE tw2002 (legacy ignores the arg)."""
    raw = action.args.get("trade_in", True)
    if isinstance(raw, str):
        return raw.strip().lower() in ("false", "0", "no", "n")
    return raw is False or raw == 0


def spare_blocked(universe: Universe, pid: str, class_key: str) -> str | None:
    """fl6 gates + fl2 cap + full price. None = the spare can be bought."""
    player = universe.players[pid]
    spec = K.ship_specs().get(class_key or "")
    if spec is None:
        return f"unknown ship class {class_key!r}"
    if spec.get("corp_only") and player.corp_ticker is None:
        return "corporation-only"
    from .corp import flagship_buy_block
    blocked = flagship_buy_block(universe, pid, class_key)
    if blocked:
        return blocked
    if K.ship_min_alignment(spec, 0) > player.alignment:
        return f"alignment too low (needs {K.ship_min_alignment(spec, 0)})"
    if spec.get("unique") and class_key in classes_owned_anywhere(universe):
        return "already owned elsewhere"
    if fleet_size(universe, pid) >= int(K.FLEET_MAX_SHIPS):
        return f"fleet full ({K.FLEET_MAX_SHIPS} ships)"
    cost = K.ship_cost(class_key)
    if player.credits < cost:
        return f"insufficient credits ({player.credits} < {cost})"
    return None


def spare_params(universe: Universe, pid: str) -> dict[str, Any]:
    cost_by: dict[str, int] = {}
    blocked_by: dict[str, str] = {}
    for key in K.ship_specs():
        cost_by[key] = int(K.ship_cost(key))
        why = spare_blocked(universe, pid, key)
        if why is not None:
            blocked_by[key] = why
    return {"type": "bool", "required": False, "default": True, "spare_cost_by": cost_by,
            "spare_blocked_by": blocked_by,
            "note": "false = buy a spare: full price, you stay aboard, it waits unmanned at StarDock"}


def new_spare_ship(class_key: str) -> Ship:
    """fl5: a very basic model - holds only, nothing else aboard."""
    spec = K.ship_specs()[class_key]
    return Ship(
        ship_class=ShipClass(class_key),
        name=str(spec.get("display_name") or class_key),
        holds=int(spec["holds"]),
        cargo={c: 0 for c in Commodity},
        fighters=0,
        shields=0,
        mines={MineType.ARMID: 0, MineType.LIMPET: 0, MineType.ATOMIC: 0},
    )


def buy_spare(universe: Universe, pid: str, class_key: str) -> ActionResult:
    player = universe.players[pid]
    if player.sector_id != K.STARDOCK_SECTOR:
        return ActionResult(ok=False, error="must be at StarDock")
    why = spare_blocked(universe, pid, class_key)
    if why is not None:
        if why in ("corporation-only",):
            why = "ship is corporation-only"
        elif why == "already owned elsewhere":
            why = "this ship class is already owned elsewhere"
        return ActionResult(ok=False, error=why)
    cost = int(K.ship_cost(class_key))
    player.credits -= cost
    ship = new_spare_ship(class_key)
    if K.corpship_on():
        from .corpships import on_new_spare
        on_new_spare(player, ship)
    sid = _ensure_fleet_id(universe, ship)
    universe.parked_ships[sid] = ParkedShip(id=sid, owner_id=pid, sector_id=K.STARDOCK_SECTOR, ship=ship,
                                            parked_day=int(universe.day))
    spec = K.ship_specs()[class_key]
    universe.emit(
        EventKind.FLEET_SPARE_BOUGHT,
        actor_id=pid,
        sector_id=K.STARDOCK_SECTOR,
        payload={"ship_class": class_key, "ship_id": sid, "cost": cost},
        summary=f"{player.name} bought a spare {spec['display_name']} ({cost} cr); it waits in orbit at StarDock",
    )
    return ActionResult(ok=True, turns_spent=0)


def sell_credit(rec: ParkedShip) -> int:
    """fl7: the yard's 25% trade-in credit. Extras aboard add nothing. A parked pod is worth nothing."""
    key = rec.ship.ship_class.value
    if key == K.ESCAPE_POD:
        return 0
    return int(K.trade_in_credit(key))


def sellable(universe: Universe, pid: str) -> list[ParkedShip]:
    player = universe.players[pid]
    if player.sector_id != K.STARDOCK_SECTOR:
        return []
    return [p for p in owned_parked(universe, pid) if int(p.sector_id) == K.STARDOCK_SECTOR]


def handle_sell_ship(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.fleet_on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    if player.sector_id != K.STARDOCK_SECTOR:
        return ActionResult(ok=False, error="must be at StarDock")
    sid = _parse_id(action.args.get("ship_id"))
    if sid is None:
        return ActionResult(ok=False, error="sell_ship requires ship_id")
    if player.ship.fleet_id is not None and int(player.ship.fleet_id) == sid:
        return ActionResult(ok=False, error="cannot sell the ship you are flying")
    rec = universe.parked_ships.get(sid)
    if rec is None:
        return ActionResult(ok=False, error=f"no ship {sid}")
    if rec.owner_id != pid:
        return ActionResult(ok=False, error="not your ship")
    if int(rec.sector_id) != K.STARDOCK_SECTOR:
        return ActionResult(ok=False, error="that ship is not in orbit at StarDock")
    credit = sell_credit(rec)
    _remove(universe, sid)
    player.credits += credit
    hull = rec.ship.ship_class.value
    universe.emit(
        EventKind.SHIP_SOLD,
        actor_id=pid,
        sector_id=K.STARDOCK_SECTOR,
        payload={"ship_id": sid, "ship_class": hull, "credit": credit, "_witnesses": [pid]},
        summary=f"{player.name} sold the {rec.ship.name} ({hull}) for {credit} cr",
    )
    return ActionResult(ok=True, turns_spent=0)


# ---- transporter pad (fl8-fl20) ----------------------------------------------------------------


def transport_block(universe: Universe, pid: str) -> str | None:
    """fl16 pilot-side preconditions (not the target)."""
    player = universe.players[pid]
    if not player.alive:
        return "dead"
    if player.planet_landed is not None:
        return "must be in space (the planet transporter is planet_transport)"
    if player.fighter_challenge:
        return "fighters challenge you here"
    from .ferrengi import live_ferrengi_encounter
    if live_ferrengi_encounter(universe, pid) is not None:
        return "answer the Ferrengi first"
    if K.FLEET_XPORT_INTERDICT == "block":
        from .combat import interdictor_planet
        if interdictor_planet(universe, pid, universe.sectors[player.sector_id]) is not None:
            return "a planetary interdictor holds this sector"
    cost = int(K.TURN_COST["ship_transport"])
    if player.turns_today + cost > player.turns_per_day:
        return "out of turns"
    return None


def target_block(universe: Universe, pid: str, rec: ParkedShip | None) -> tuple[str | None, int | None]:
    """fl10-fl13 for one ship: (why refused, hops)."""
    player = universe.players[pid]
    if rec is None:
        return "no such ship", None
    if rec.owner_id != pid:
        if not K.corpship_on():
            return "not your ship (own ships only)", None
        from .corpships import board_block
        why = board_block(universe, pid, rec)
        if why is not None:
            return why, None
    if (K.hull_spec(rec.ship.ship_class.value) or {}).get("corp_only") and player.corp_ticker is None:
        return "corporation hull: you are no longer in a corporation", None
    hops = hops_between(universe, player.sector_id, rec.sector_id)
    rng = K.transport_range(player.ship.ship_class.value)
    if hops is None:
        return "no warp path to that ship", None
    if hops == 0 and not K.FLEET_XPORT_SAME_SECTOR:
        return "same-sector boarding is off", hops
    if hops > rng:
        return f"out of transporter range ({hops} hops > {rng})", hops
    return None, hops


def transport_choices(universe: Universe, pid: str) -> tuple[list[int], dict[str, int]]:
    from .corpships import transport_records
    choices: list[int] = []
    hops_by: dict[str, int] = {}
    records = transport_records(universe, pid) if K.corpship_on() else owned_parked(universe, pid)
    for rec in records:
        why, hops = target_block(universe, pid, rec)
        if why is None and hops is not None:
            choices.append(int(rec.id))
            hops_by[str(rec.id)] = int(hops)
    return choices, hops_by


def _park_manned(universe: Universe, pid: str) -> int | None:
    """fl17a: the hull you leave becomes a ParkedShip here (a pod is discarded by default)."""
    player = universe.players[pid]
    old = player.ship
    if old.ship_class.value == K.ESCAPE_POD and K.FLEET_POD_ON_LEAVE == "discard":
        _drop_pilot_limpets(universe, pid)
        return None
    if getattr(old, "cloaked", False) and K.FLEET_CLOAK_ON_LEAVE == "decloak":
        old.cloaked = False
        old.cloak_activated_day = None
    sid = _ensure_fleet_id(universe, old)
    if K.FLEET_LIMPET_POLICY == "hull":
        _limpets_leave_hull(universe, pid, sid)
    owner = pid
    if K.corpship_on():
        from .corpships import park_owner
        owner = park_owner(universe, pid, old)
    universe.parked_ships[sid] = ParkedShip(id=sid, owner_id=owner, sector_id=int(player.sector_id), ship=old,
                                            parked_day=int(universe.day))
    if owner == K.DEFUNCT_OWNER:
        universe.emit(
            EventKind.SHIP_DEFUNCT, actor_id=pid, sector_id=int(player.sector_id),
            payload={"ship_id": int(sid), "_witnesses": [pid]},
            summary=f"ship {sid} is now a defunct Corp ship",
        )
    return sid


def handle_ship_transport(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.fleet_on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    why = transport_block(universe, pid)
    if why is not None:
        return ActionResult(ok=False, error=why)
    sid = _parse_id(action.args.get("ship_id"))
    if sid is None:
        return ActionResult(ok=False, error="ship_transport requires ship_id")
    if player.ship.fleet_id is not None and int(player.ship.fleet_id) == sid:
        return ActionResult(ok=False, error="you are already aboard that ship")
    rec = universe.parked_ships.get(sid)
    bad, hops = target_block(universe, pid, rec)
    if bad is not None:
        return ActionResult(ok=False, error=bad)
    assert rec is not None and hops is not None
    if K.corpship_on() and rec.owner_id != pid:
        from .corpships import note_password_fail, password_block
        pw_why = password_block(pid, rec, (action.args or {}).get("password"))
        if pw_why is not None:
            note_password_fail(universe, pid)
            return ActionResult(ok=False, error=pw_why)
    from .runner import _learn_sector, _record_port_intel

    from_sid = int(player.sector_id)
    to_sid = int(rec.sector_id)
    old_hull = player.ship.ship_class.value
    parked_id = _park_manned(universe, pid)
    universe.parked_ships.pop(sid)
    player.ship = rec.ship  # the object moves; nothing is copied (fl3)
    if K.FLEET_LIMPET_POLICY == "hull":
        _limpets_board_hull(universe, pid, sid)
    if to_sid != from_sid:
        try:
            universe.sectors[from_sid].occupant_ids.remove(pid)
        except ValueError:
            pass
        if pid not in universe.sectors[to_sid].occupant_ids:
            universe.sectors[to_sid].occupant_ids.append(pid)
        player.sector_id = to_sid
    player.end_port_visit()
    player.planet_landed = None
    player.photon_damped_sector_id = None
    player.arrived_by_transwarp = False
    player.arrived_by_transport = True
    _learn_sector(player, universe, to_sid)
    dest = universe.sectors[to_sid]
    if dest.port is not None:
        _record_port_intel(player, dest.id, dest.port, universe=universe)
    witnesses = sorted(set(universe.sectors[from_sid].occupant_ids) | set(dest.occupant_ids) | {pid})
    hull = player.ship.ship_class.value
    universe.emit(
        EventKind.SHIP_TRANSPORT,
        actor_id=pid,
        sector_id=to_sid,
        payload={"from": from_sid, "to": to_sid, "ship_id": sid, "hull": hull, "hops": int(hops),
                 "left_ship_id": parked_id, "left_hull": old_hull, "_witnesses": witnesses},
        summary=f"{player.name} beamed from sector {from_sid} into the {player.ship.name} in sector {to_sid}",
    )
    from .fed import check_iss_repo_on_move
    check_iss_repo_on_move(universe, pid)  # fl17e: f22 for an evil pilot boarding an ISS
    return ActionResult(ok=True, turns_spent=int(K.TURN_COST["ship_transport"]))


# ---- Extern repossession (fl23) ----------------------------------------------------------------


def extern_repossess(universe: Universe) -> int:
    if not K.fleet_on() or K.FLEET_FED_REPO != "fedspace":
        return 0
    n = 0
    for sid in sorted(universe.parked_ships):
        rec = universe.parked_ships[sid]
        if int(rec.sector_id) not in K.FEDSPACE_SECTORS:
            continue
        if K.tow_on():  # SHIP_TOW.md tt22: an own fedsafe tower beside it with the ship locked in tow
            from .tow import emit_hold, extern_hold_why
            if extern_hold_why(universe, rec) is None:
                emit_hold(universe, rec)
                continue
        _remove(universe, sid)
        n += 1
        owner = universe.players.get(rec.owner_id)
        universe.emit(
            EventKind.FLEET_REPOSSESSED,
            actor_id=rec.owner_id,
            sector_id=int(rec.sector_id),
            payload={"ship_id": sid, "ship_class": rec.ship.ship_class.value, "sector": int(rec.sector_id),
                     "_witnesses": [rec.owner_id]},
            summary=(f"Extern repossessed {owner.name if owner else rec.owner_id}'s unmanned "
                     f"{rec.ship.name} in FedSpace sector {rec.sector_id}"),
        )
    return n


# ---- unmanned ships in space (fl22, fl24) ------------------------------------------------------


def _hidden(rec: ParkedShip) -> bool:
    return K.hardware_tw2002() and bool(getattr(rec.ship, "cloaked", False))


def unmanned_in(universe: Universe, sector_id: int) -> list[ParkedShip]:
    return [p for _i, p in sorted(universe.parked_ships.items()) if int(p.sector_id) == int(sector_id)]


def density_unmanned(universe: Universe, sector_id: int) -> tuple[int, bool]:
    """fl22: 38 per uncloaked unmanned ship; a cloaked one reads 0 and an anomaly (under "keep")."""
    dens, anomaly = 0, False
    for rec in unmanned_in(universe, sector_id):
        if _hidden(rec):
            anomaly = True
            continue
        dens += int(K.DENSITY_PER_UNMANNED)
    return dens, anomaly


def sector_unmanned_view(universe: Universe, viewer_id: str, sector_id: int) -> list[dict[str, Any]]:
    """fl22: {ship_id, hull, owner_name, own}. A rival hull shows fighters only where a rival manned
    ship already does (INFO_MODE tw2002 traders list); never cargo, hardware, drive or corbomite."""
    out = []
    for rec in unmanned_in(universe, sector_id):
        if _hidden(rec):
            continue
        owner = universe.players.get(rec.owner_id)
        own = rec.owner_id == viewer_id
        entry: dict[str, Any] = {"ship_id": int(rec.id), "hull": rec.ship.ship_class.value,
                                 "owner_name": owner.name if owner else rec.owner_id, "own": own}
        if K.corpship_on():
            from .corpships import sector_label
            entry["ownership"] = sector_label(universe, rec)
        if own:
            entry["fighters"] = int(rec.ship.fighters)
            entry["shields"] = int(rec.ship.shields)
        elif K.info_tw2002():
            entry["fighters"] = int(rec.ship.fighters)
        out.append(entry)
    return out


def unmanned_attack_block(universe: Universe, pid: str, rec: ParkedShip | None) -> str | None:
    player = universe.players[pid]
    if rec is None:
        return "not found"
    if int(rec.sector_id) != int(player.sector_id):
        return "target not in this sector"
    if _hidden(rec):
        return "target is cloaked"
    if not K.corpship_on():
        if rec.owner_id == pid:
            return "cannot attack your own ship"
        if _are_allied(universe, pid, rec.owner_id):
            return "cannot attack a corp mate or ally"
        if int(player.sector_id) in K.FEDSPACE_SECTORS:
            return "FedSpace - unmanned ships cannot be attacked here"
        return None
    if int(player.sector_id) in K.FEDSPACE_SECTORS:
        return "FedSpace - unmanned ships cannot be attacked here"
    from .corpships import attack_block
    return attack_block(universe, pid, rec)


def unmanned_attack_choices(universe: Universe, pid: str) -> list[str]:
    player = universe.players[pid]
    return [f"ship:{rec.id}" for rec in unmanned_in(universe, player.sector_id)
            if unmanned_attack_block(universe, pid, rec) is None]


def attack_unmanned(universe: Universe, pid: str, target: str, action: Action) -> ActionResult:
    """fl24: COMBAT_MODE tw2002 ship-attack math at half the hull's odds; it never flees."""
    from .combat import _odds, combat_odds_of
    from .runner import _attack_qty

    player = universe.players[pid]
    sid = _parse_id(target)
    rec = universe.parked_ships.get(sid) if sid is not None else None
    why = unmanned_attack_block(universe, pid, rec)
    if why == "not found":
        return ActionResult(ok=False, error=f"target {target} not found")
    if why is not None:
        return ActionResult(ok=False, error=why)
    assert rec is not None
    cost = K.TURN_COST["attack"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    qty, bad = _attack_qty(player, action)
    if bad is not None:
        return bad
    hull = rec.ship.ship_class.value
    d_f, d_s = int(rec.ship.fighters), int(rec.ship.shields)
    disabled = int(getattr(rec.ship, "photon_disabled_ticks", 0) or 0) > 0
    a_odds = combat_odds_of(player)
    d_odds = _odds(K.combat_hull(hull)[0]) * Fraction(str(K.FLEET_UNMANNED_ODDS_FACTOR))
    s_eff = 0 if disabled else d_s
    power = qty * a_odds
    defense = (s_eff + d_f) * d_odds
    beaten = power >= defense
    if beaten:
        att_losses = min(qty, math.ceil(defense / a_odds)) if defense > 0 else 0
        sh_lost, f_lost = s_eff, d_f
    else:
        att_losses = qty
        units = math.floor(power / d_odds)
        sh_lost = min(s_eff, units)
        f_lost = min(d_f, units - sh_lost)
    player.ship.fighters = int(player.ship.fighters) - att_losses
    rec.ship.fighters, rec.ship.shields = d_f - f_lost, d_s - sh_lost
    if K.FLEET_UNMANNED_ALIGN == "v2_penalty" and f_lost > 0:
        own_kill = K.corpship_on() and rec.owner_id == pid and int(K.CORPSHIP_OWN_KILL_ALIGN) == 0
        if not own_kill:
            player.alignment = int(player.alignment) - int(int(player.alignment) * 0.10 * f_lost / 1000)
    will_capture = False
    if beaten:
        from .capture import unmanned_would_capture
        will_capture = unmanned_would_capture(universe, player, rec, qty, defense, a_odds)
        if K.corpship_on():
            from .corpships import capture_allowed
            if not capture_allowed(player, rec):
                will_capture = False
    owner = universe.players.get(rec.owner_id)
    universe.emit(
        EventKind.COMBAT,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={
            "exchange_kind": "ship_vs_unmanned",
            "exchange_max_rounds": 1,
            "attacker": pid,
            "defender": f"ship:{rec.id}",
            "victim": rec.owner_id,
            "attacker_f": int(player.ship.fighters),
            "attacker_s": int(player.ship.shields),
            "sent": qty,
            "defender_fled": False,
            "attacker_losses": att_losses,
            "defender_losses": f_lost,
            "outcome": ("captured" if will_capture else
                        ("destroyed" if beaten else ("hit" if (f_lost + sh_lost) > 0 else "miss"))),
        },
        summary=(f"Combat in {player.sector_id}: {player.name} sent {qty} fighters at an unmanned {hull}, "
                 f"lost {att_losses}; it lost {sh_lost} shields and {f_lost} fighters"
                 + (" - CAPTURED" if will_capture else (" - DESTROYED" if beaten else ""))),
    )
    if will_capture:
        from .capture import apply_unmanned_capture
        apply_unmanned_capture(universe, pid, rec)
    elif beaten:
        label_before = None
        if K.corpship_on():
            from .corpships import sector_label
            label_before = sector_label(universe, rec)  # cs31 / REV 516: report the hull's real label
            from .corpships import apply_furb
            apply_furb(universe, pid, rec.ship, rec.owner_id)
        _remove(universe, int(rec.id))
        if K.FLEET_UNMANNED_KILL_EXP and not (K.corpship_on() and rec.owner_id == pid):  # cs16: no reward
            player.experience = int(player.experience) + int(K.FLEET_UNMANNED_KILL_EXP)
        universe.emit(
            EventKind.UNMANNED_SHIP_DESTROYED,
            actor_id=pid,
            sector_id=player.sector_id,
            payload={"ship_id": int(rec.id), "hull": hull, "owner_id": rec.owner_id, "victim": rec.owner_id,
                     **({"ownership": label_before} if label_before is not None else {})},
            summary=(f"{player.name} destroyed {owner.name if owner else rec.owner_id}'s unmanned "
                     f"{rec.ship.name} in sector {player.sector_id}"),
        )
        units = int(getattr(rec.ship, "corbomite", 0) or 0) if K.hardware_tw2002() else 0
        if units > 0 and not (pid == rec.owner_id and K.CORBOMITE_OWN_SHIP == "inert"):
            from .hardware import apply_corbomite
            apply_corbomite(universe, rec.owner_id, pid, units)
    return ActionResult(ok=True, turns_spent=cost)


# ---- net worth (fl27) / observation (fl30) -----------------------------------------------------


def parked_value(ship: Ship) -> int:
    """Valued exactly as Player.net_worth values the manned ship (credits 0)."""
    from .models import Player
    return int(Player.model_construct(credits=0, ship=ship).net_worth)


def fleet_net_worth(universe: Universe, pid: str) -> int:
    return sum(parked_value(p.ship) for p in owned_parked(universe, pid))


def fleet_block(universe: Universe, pid: str) -> dict[str, Any]:
    from .observation import _ship_dict

    player = universe.players[pid]
    rng = K.transport_range(player.ship.ship_class.value)
    ships = []
    for rec in owned_parked(universe, pid):
        why, hops = target_block(universe, pid, rec)
        view = _ship_dict(rec.ship)
        tw = view.get("transwarp") if isinstance(view.get("transwarp"), dict) else None
        ships.append({
            "ship_id": int(rec.id),
            "hull": rec.ship.ship_class.value,
            "name": rec.ship.name,
            "sector_id": int(rec.sector_id),
            "hops": hops,
            "in_range": why is None,
            "fighters": int(rec.ship.fighters),
            "shields": int(rec.ship.shields),
            "holds": int(rec.ship.holds),
            "cargo": {c.value: int(rec.ship.cargo.get(c, 0)) for c in Commodity},
            "transwarp": (tw or {}).get("fitted"),
            "repo_at_extern": K.FLEET_FED_REPO == "fedspace" and int(rec.sector_id) in K.FEDSPACE_SECTORS,
        })
        if K.corpship_on():
            from .corpships import sector_label
            ships[-1]["ownership"] = sector_label(universe, rec)
        if K.tow_on():  # SHIP_TOW.md tt23 / tt29
            from .tow import fleet_entry_extra
            extra = fleet_entry_extra(universe, rec)
            ships[-1].update(extra)
            if extra["extern_hold"]:
                ships[-1]["repo_at_extern"] = False
        if K.capture_on():
            ships[-1]["captured_from"] = rec.captured_from
            ships[-1]["captured_day"] = rec.captured_day
    return {"max_ships": int(K.FLEET_MAX_SHIPS), "transport_range": rng,
            "manned_ship_id": player.ship.fleet_id, "ships": ships}


# ---- legal list (fl4 / fl7 / fl8) --------------------------------------------------------------


def legal_specs(universe: Universe, pid: str) -> list[tuple[str, bool, str | None, int, dict[str, Any]]]:
    player = universe.players[pid]
    out: list[tuple[str, bool, str | None, int, dict[str, Any]]] = []
    sell = sellable(universe, pid)
    credit_by = {str(p.id): sell_credit(p) for p in sell}
    if player.sector_id != K.STARDOCK_SECTOR:
        why = "must be at StarDock (sector 1)"
    elif not sell:
        why = "no ship of yours in orbit at StarDock"
    else:
        why = None
    out.append(("sell_ship", why is None, why, 0,
                {"ship_id": {"type": "int", "required": True, "choices": [int(p.id) for p in sell],
                             "credit_by": credit_by}}))
    cost = int(K.TURN_COST["ship_transport"])
    choices, hops_by = transport_choices(universe, pid)
    why = transport_block(universe, pid)
    pool = owned_parked(universe, pid)
    if K.corpship_on():
        from .corpships import transport_records
        pool = transport_records(universe, pid)
    if why is None and not pool:
        why = "you own no other ship"
    elif why is None and not choices:
        why = "none of your ships is within transporter range"
    params: dict[str, Any] = {"ship_id": {"type": "int", "required": True, "choices": choices if why is None else [],
                                          "hops_by": hops_by if why is None else {},
                                          "range": K.transport_range(player.ship.ship_class.value)}}
    if K.corpship_on() and why is None:
        from .corpships import detail_for
        params["ship_id"]["detail_by"] = {
            str(sid): detail_for(universe, pid, universe.parked_ships[sid], hops_by.get(str(sid)))
            for sid in choices if sid in universe.parked_ships
        }
        params["password"] = {"type": "str", "required": False}
    out.append(("ship_transport", why is None, why, cost, params))
    return out
