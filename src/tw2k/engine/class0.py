"""Class 0 ports and Terra (CLASS0_TERRA.md / CLASS0_MODE).

Helpers for Terra pool, Alpha Centauri / Rylos placement, MSL set, Extern sweep,
and the shared Class 0 service check used by legal list + handlers.
Legacy mode never calls the placement / sweep paths that mutate the universe.
"""

from __future__ import annotations

import math
import random
from collections import deque
from typing import Any

from . import constants as K
from .actions import Action, ActionResult
from .models import (
    EventKind,
    MineDeployment,
    Planet,
    Port,
    PortClass,
    Universe,
)

CLASS0_ITEMS = ("fighters", "shields", "holds")
MSL_NOTE = "Major Space Lane: removed at Extern"


def class0_tw2002() -> bool:
    return K.CLASS0_MODE == "tw2002"


def shield_unit_price(day: int) -> int:
    """Credits for one shield today.

    mirror (tw2002 default): fighter wave in opposite phase, 160..239.
    flat / legacy: 10.
    """
    if K.SHIELD_PRICE_MODE != "mirror" or not class0_tw2002():
        return 10
    raw = 200 - math.sin(int(day) / 87 * 2 * math.pi) * 40
    price = round(raw)
    if price < 160:
        return 160
    if price > 239:
        return 239
    return price


def class0_rng(seed: int) -> random.Random:
    """Dedicated RNG so Class 0 placement never touches generator / universe.rng."""
    return random.Random(f"class0:{seed}")


def class0_service_here(universe: Universe, pid: str) -> bool:
    """True at sector 1 or an Alpha Centauri / Rylos sector (limpet removal / Class 0 buy)."""
    player = universe.players.get(pid)
    if player is None:
        return False
    sid = int(player.sector_id)
    if sid == K.STARDOCK_SECTOR:
        return True
    if not class0_tw2002():
        return False
    specials = getattr(universe, "class0_sectors", None) or {}
    return sid in specials.values()


def is_class0_sector(universe: Universe, sector_id: int) -> bool:
    if int(sector_id) == K.STARDOCK_SECTOR:
        return True
    specials = getattr(universe, "class0_sectors", None) or {}
    return int(sector_id) in {int(v) for v in specials.values()}


def is_msl_sector(universe: Universe, sector_id: int) -> bool:
    msl = getattr(universe, "msl_sectors", None) or []
    return int(sector_id) in msl


def special_port_at(universe: Universe, sector_id: int) -> Port | None:
    sector = universe.sectors.get(int(sector_id))
    if sector is None or sector.port is None:
        return None
    special = getattr(sector.port, "special", None)
    if special in ("alpha_centauri", "rylos"):
        return sector.port
    return None


def class0_buy_ok(universe: Universe, pid: str) -> tuple[bool, str]:
    """Whether buy_equip is allowed here (StarDock or Class 0 special)."""
    player = universe.players.get(pid)
    if player is None:
        return False, "unknown player"
    sid = int(player.sector_id)
    if sid == K.STARDOCK_SECTOR:
        return True, ""
    if class0_tw2002() and special_port_at(universe, sid) is not None:
        return True, ""
    return False, "must be at StarDock (sector 1) or a Class 0 port"


def bfs_hops(universe: Universe, start: int) -> dict[int, int]:
    """Fewest hops from start, honoring one-way warps."""
    dist: dict[int, int] = {int(start): 0}
    q: deque[int] = deque([int(start)])
    while q:
        cur = q.popleft()
        sector = universe.sectors.get(cur)
        if sector is None:
            continue
        for nxt in sector.warps:
            nid = int(nxt)
            if nid in dist:
                continue
            dist[nid] = dist[cur] + 1
            q.append(nid)
    return dist


def shortest_path(universe: Universe, src: int, dst: int) -> list[int]:
    """Fewest-hop path; tie-break = lexicographically smallest sector-id sequence."""
    src, dst = int(src), int(dst)
    if src == dst:
        return [src]
    # parent[v] = u means best path to v came from u
    parent: dict[int, int | None] = {src: None}
    # best path list to each node (for lex compare)
    best_path: dict[int, list[int]] = {src: [src]}
    q: deque[int] = deque([src])
    while q:
        cur = q.popleft()
        if cur == dst:
            break
        sector = universe.sectors.get(cur)
        if sector is None:
            continue
        cur_path = best_path[cur]
        cur_len = len(cur_path)
        for nxt in sorted(int(w) for w in sector.warps):
            cand = [*cur_path, nxt]
            if nxt not in best_path:
                best_path[nxt] = cand
                parent[nxt] = cur
                q.append(nxt)
            elif len(best_path[nxt]) == cur_len + 1 and cand < best_path[nxt]:
                best_path[nxt] = cand
                parent[nxt] = cur
    return best_path.get(dst, [])


def compute_msl_sectors(universe: Universe) -> list[int]:
    specials = getattr(universe, "class0_sectors", None) or {}
    ac = specials.get("alpha_centauri")
    ry = specials.get("rylos")
    if ac is None or ry is None:
        return []
    pairs = [
        (K.STARDOCK_SECTOR, int(ac)),
        (int(ac), K.STARDOCK_SECTOR),
        (K.STARDOCK_SECTOR, int(ry)),
        (int(ry), K.STARDOCK_SECTOR),
        (int(ac), int(ry)),
        (int(ry), int(ac)),
    ]
    found: set[int] = {int(ac), int(ry), K.STARDOCK_SECTOR}
    for a, b in pairs:
        for sid in shortest_path(universe, a, b):
            found.add(int(sid))
    return sorted(found)


def _out_degree(universe: Universe, sid: int) -> int:
    sector = universe.sectors.get(int(sid))
    return len(sector.warps) if sector is not None else 0


def place_class0_ports(universe: Universe) -> dict[str, Any]:
    """Place Alpha Centauri and Rylos; init Terra; compute MSL. Mutates universe."""
    summary: dict[str, Any] = {"replaced_ports": [], "alpha_centauri": None, "rylos": None}
    if not class0_tw2002():
        universe.terra_colonists = None
        universe.terra_max = 0
        universe.class0_sectors = {}
        universe.msl_sectors = []
        return summary

    universe.terra_max = int(K.TERRA_MAX_COLONISTS)
    universe.terra_colonists = int(K.TERRA_MAX_COLONISTS)

    rng = class0_rng(int(universe.config.seed))
    hops = bfs_hops(universe, K.STARDOCK_SECTOR)
    fed = set(K.FEDSPACE_SECTORS)
    n = int(universe.config.universe_size)

    def candidates(allow_port: bool, exclude: set[int]) -> list[int]:
        out: list[int] = []
        for sid in range(11, n + 1):
            if sid in exclude or sid in fed:
                continue
            h = hops.get(sid)
            if h is None or h < int(K.CLASS0_MIN_HOPS) or h > int(K.CLASS0_MAX_HOPS):
                continue
            sector = universe.sectors[sid]
            if sector.planet_ids:
                continue
            if sector.port is not None and not allow_port:
                continue
            out.append(sid)
        # rank: out-degree desc, then rng tie-break via shuffle of equal bands
        out.sort(key=lambda s: (-_out_degree(universe, s), s))
        # stable group shuffle by out-degree
        ranked: list[int] = []
        i = 0
        while i < len(out):
            j = i
            deg = _out_degree(universe, out[i])
            while j < len(out) and _out_degree(universe, out[j]) == deg:
                j += 1
            group = out[i:j]
            rng.shuffle(group)
            ranked.extend(group)
            i = j
        return ranked

    exclude: set[int] = set()
    ac_list = candidates(False, exclude)
    if not ac_list:
        ac_list = candidates(True, exclude)
    if not ac_list:
        # last resort: any non-fed deep sector
        ac_list = [s for s in range(11, n + 1) if s not in fed]
        rng.shuffle(ac_list)
    ac = int(ac_list[0])
    exclude.add(ac)

    def far_enough(sid: int) -> bool:
        d = bfs_hops(universe, ac).get(sid)
        return d is not None and d >= int(K.CLASS0_MIN_SEPARATION)

    ry_list = [s for s in candidates(False, exclude) if far_enough(s)]
    if not ry_list:
        ry_list = [s for s in candidates(True, exclude) if far_enough(s)]
    if not ry_list:
        ry_list = [s for s in range(11, n + 1) if s not in exclude and s not in fed and far_enough(s)]
        rng.shuffle(ry_list)
    if not ry_list:
        ry_list = [s for s in range(11, n + 1) if s not in exclude and s not in fed]
        rng.shuffle(ry_list)
    ry = int(ry_list[0])

    def install(sid: int, key: str, name: str) -> None:
        sector = universe.sectors[sid]
        if sector.port is not None and getattr(sector.port, "special", None) is None:
            summary["replaced_ports"].append({"sector_id": sid, "was": sector.port.name or sector.port.code})
        sector.port = Port(
            class_id=PortClass.FEDERAL,
            name=name,
            special=key,
        )
        summary[key] = sid

    install(ac, "alpha_centauri", "Alpha Centauri")
    install(ry, "rylos", "Rylos")
    universe.class0_sectors = {"alpha_centauri": ac, "rylos": ry}
    universe.msl_sectors = compute_msl_sectors(universe)
    return summary


def regen_terra(universe: Universe) -> None:
    if not class0_tw2002():
        return
    if universe.terra_colonists is None:
        return
    mx = int(universe.terra_max or K.TERRA_MAX_COLONISTS)
    universe.terra_colonists = min(mx, int(universe.terra_colonists) + int(K.TERRA_REGEN_PER_DAY))


def apply_extern_planet_rule(universe: Universe, sector_id: int) -> None:
    rule = K.CLASS0_EXTERN_PLANET_RULE
    if rule == "keep":
        return
    sector = universe.sectors.get(int(sector_id))
    if sector is None:
        return
    for pid in list(sector.planet_ids):
        planet = universe.planets.get(pid)
        if planet is None:
            continue
        if rule == "cap_l2":
            if int(planet.citadel_level or 0) > 2:
                planet.citadel_level = 2
            if int(planet.citadel_target or 0) > 2:
                planet.citadel_target = 2
        elif rule == "remove":
            for pl in universe.players.values():
                if pl.planet_landed == pid:
                    pl.planet_landed = None
            universe.planets.pop(pid, None)
            if pid in sector.planet_ids:
                sector.planet_ids.remove(pid)


def extern_sweep(universe: Universe) -> int:
    """Remove fighters/mines on MSL + Class 0 sectors. Returns sweep event count."""
    if not class0_tw2002():
        return 0
    msl = set(getattr(universe, "msl_sectors", None) or [])
    for sid in getattr(universe, "class0_sectors", {}).values():
        msl.add(int(sid))
    msl.add(K.STARDOCK_SECTOR)
    events = 0
    for sid in sorted(msl):
        sector = universe.sectors.get(int(sid))
        if sector is None:
            continue
        fighters = 0
        mines = 0
        owner_id = None
        if sector.fighters is not None and int(sector.fighters.count) > 0:
            fighters = int(sector.fighters.count)
            owner_id = sector.fighters.owner_id
            # toll credits lost (UNVERIFIED)
            sector.fighters = None
        mine_owners: dict[str, int] = {}
        if sector.mines:
            kept: list[MineDeployment] = []
            for m in sector.mines:
                # beacons are not mines; leave sector.beacon alone
                mines += int(m.count)
                mine_owners[m.owner_id] = mine_owners.get(m.owner_id, 0) + int(m.count)
            sector.mines = kept  # all removed
        if fighters or mines:
            # Notify each owner separately (owner-only event).
            owners: set[str] = set(mine_owners)
            if owner_id:
                owners.add(owner_id)
            if not owners:
                owners.add("")
            for oid in sorted(owners):
                # Each owner learns only what THEY lost (no rival fighter counts / hidden limpets).
                own_f = fighters if (not oid or oid == owner_id) else 0
                own_m = mine_owners.get(oid, 0) if oid else mines
                universe.emit(
                    EventKind.EXTERN_SWEEP,
                    actor_id=oid or None,
                    sector_id=int(sid),
                    payload={
                        "sector_id": int(sid),
                        "fighters": own_f,
                        "mines": own_m,
                    },
                    summary=f"Extern swept sector {sid}: your {own_f} fighters, {own_m} mines cleared",
                )
                events += 1
        apply_extern_planet_rule(universe, int(sid))
    return events


def handle_terra_colonists(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not class0_tw2002():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    if player.sector_id != K.STARDOCK_SECTOR:
        return ActionResult(ok=False, error="must be at Terra (sector 1)")
    if player.planet_landed is not None:
        return ActionResult(ok=False, error="must liftoff before loading Terra colonists")
    if player.fighter_challenge is not None:
        return ActionResult(ok=False, error="resolve the fighter challenge first")
    if universe.terra_colonists is None:
        return ActionResult(ok=False, error="Terra unavailable")
    cost = int(K.TERRA_LOAD_TURNS)
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    mode = str(action.args.get("mode") or "").lower()
    try:
        qty = int(action.args.get("qty") or 0)
    except (TypeError, ValueError):
        return ActionResult(ok=False, error="qty must be a whole number")
    if qty <= 0:
        return ActionResult(ok=False, error="qty must be positive")
    if mode == "take":
        free = int(player.ship.cargo_free)
        pool = int(universe.terra_colonists)
        if qty > pool:
            return ActionResult(ok=False, error=f"Terra only has {pool} colonists")
        if qty > free:
            return ActionResult(ok=False, error=f"not enough cargo holds (need {qty}, free {free})")
        from .models import Commodity
        player.ship.cargo[Commodity.COLONISTS] = (
            player.ship.cargo.get(Commodity.COLONISTS, 0) + qty
        )
        universe.terra_colonists = pool - qty
    elif mode == "leave":
        from .models import Commodity
        have = int(player.ship.cargo.get(Commodity.COLONISTS, 0))
        if qty > have:
            return ActionResult(ok=False, error=f"only {have} colonists in cargo")
        mx = int(universe.terra_max or K.TERRA_MAX_COLONISTS)
        room = mx - int(universe.terra_colonists)
        if qty > room:
            return ActionResult(ok=False, error=f"Terra only has room for {room}")
        player.ship.cargo[Commodity.COLONISTS] = have - qty
        if player.ship.cargo[Commodity.COLONISTS] <= 0:
            player.ship.cargo.pop(Commodity.COLONISTS, None)
        universe.terra_colonists = int(universe.terra_colonists) + qty
    else:
        return ActionResult(ok=False, error="mode must be take or leave")
    # Free (price 0); 1 turn.
    universe.emit(
        EventKind.TERRA_COLONISTS,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"mode": mode, "qty": qty, "pool_after": int(universe.terra_colonists)},
        summary=f"{player.name} {mode} {qty} colonists at Terra (pool {universe.terra_colonists})",
    )
    return ActionResult(ok=True, turns_spent=int(K.TERRA_LOAD_TURNS))


def terra_legal_params(universe: Universe, player) -> dict[str, Any] | None:
    """Params for terra_colonists legal entry, or None if not offerable."""
    if not class0_tw2002():
        return None
    if player.sector_id != K.STARDOCK_SECTOR:
        return None
    if player.planet_landed is not None:
        return None
    if player.fighter_challenge is not None:
        return None
    if universe.terra_colonists is None:
        return None
    from .models import Commodity
    pool = int(universe.terra_colonists)
    mx = int(universe.terra_max or K.TERRA_MAX_COLONISTS)
    free = int(player.ship.cargo_free)
    cargo_col = int(player.ship.cargo.get(Commodity.COLONISTS, 0))
    take_max = min(pool, free)
    leave_max = min(cargo_col, mx - pool)
    modes = []
    max_by = {}
    if take_max >= 1:
        modes.append("take")
        max_by["take"] = take_max
    if leave_max >= 1:
        modes.append("leave")
        max_by["leave"] = leave_max
    if not modes:
        return None
    return {
        "mode": {"type": "str", "required": True, "choices": modes},
        "qty": {"type": "int", "required": True, "min": 1, "max_by": max_by},
        "pool": pool,
        "max": mx,
        "turns": int(K.TERRA_LOAD_TURNS),
        "price": int(K.TERRA_COLONIST_PRICE),
    }


def class0_equip_prices(day: int) -> dict[str, int]:
    return {
        "fighters": K.fighter_unit_price(day),
        "shields": shield_unit_price(day),
        "holds": 0,  # filled per-ship by caller via hold_next_price
    }


def planet_citadel_level_cap(planet: Planet, level: int = 2) -> None:
    if int(planet.citadel_level or 0) > level:
        planet.citadel_level = level
    if int(getattr(planet, "citadel_target", 0) or 0) > level:
        planet.citadel_target = level
