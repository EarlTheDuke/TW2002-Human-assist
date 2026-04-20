"""Engine runner — apply_action dispatch, day tick, victory checks.

The engine is synchronous and pure. Agent-facing entry points:
    apply_action(universe, player_id, action) -> ActionResult
    tick_day(universe)
    is_finished(universe) -> bool
"""

from __future__ import annotations

import random
from collections import deque
from collections.abc import Callable

from . import constants as K
from .actions import Action, ActionKind, ActionResult
from .combat import (
    _are_allied,
    _attach_limpet,
    _destroy_ship,
    _resolve_fighter_sector_combat,
    _resolve_ship_combat,
)
from .economy import execute_trade, regenerate_ports
from .ferrengi import _ferrengi_by_name, _ferrengi_roam_and_hunt, _spawn_ferrengi
from .models import (
    Alliance,
    Commodity,
    Corporation,
    EventKind,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Planet,
    PlanetClass,
    PortClass,
    Universe,
)
from .planets import _advance_planets, _complete_citadels
from .victory import (
    _award_xp,
    _check_victory,
    _corp_treasury_share,
    _planet_asset_value,
    alignment_label,
    check_victory,
    full_net_worth,
    rank_for,
)

# Public re-exports for callers that used to import these names from
# `tw2k.engine.runner`. Keeps the Phase 6 runner-split backward-compatible
# for server/runner.py, scripts/, tests/, and engine/observation.py.
__all__ = [  # noqa: RUF022 — grouped by origin module, not alphabetized
    "apply_action",
    "is_finished",
    "tick_day",
    # Re-exported combat helpers
    "_are_allied",
    "_attach_limpet",
    "_destroy_ship",
    "_resolve_fighter_sector_combat",
    "_resolve_ship_combat",
    # Re-exported ferrengi
    "_ferrengi_by_name",
    "_ferrengi_roam_and_hunt",
    "_spawn_ferrengi",
    # Re-exported planet tick helpers
    "_advance_planets",
    "_complete_citadels",
    # Re-exported victory / progression
    "_award_xp",
    "_check_victory",
    "_corp_treasury_share",
    "_planet_asset_value",
    "alignment_label",
    "check_victory",
    "full_net_worth",
    "rank_for",
    # Local utilities kept in runner (still used by tests/callers)
    "_bfs_path",
    "_record_port_intel",
    "_rng_for",
]


def _rng_for(universe: Universe) -> random.Random:
    """Return the deterministic per-universe PRNG.

    Thin back-compat shim over `Universe.rng` (which now holds the RNG as a
    `PrivateAttr`, instance-scoped). Kept so any external/legacy code still
    importing this name from `tw2k.engine.runner` continues to work.
    """
    return universe.rng


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def apply_action(universe: Universe, player_id: str, action: Action) -> ActionResult:
    player = universe.players.get(player_id)
    if player is None:
        return ActionResult(ok=False, error=f"unknown player {player_id}")
    if not player.alive:
        return ActionResult(ok=False, error="player is destroyed")

    universe.tick += 1

    # Always log the thought; never validate
    if action.thought:
        universe.emit(
            EventKind.AGENT_THOUGHT,
            actor_id=player_id,
            sector_id=player.sector_id,
            payload={"thought": action.thought[:2000]},
            summary=_truncate_for_feed(action.thought),
        )
    if action.scratchpad_update is not None:
        player.scratchpad = action.scratchpad_update[:8000]
    # Persist structured goal updates (None=leave alone, string=replace incl.
    # empty clear). Cap per-field at 240 chars so the action_hint stays terse.
    if action.goal_short is not None:
        player.goal_short = action.goal_short[:240]
    if action.goal_medium is not None:
        player.goal_medium = action.goal_medium[:240]
    if action.goal_long is not None:
        player.goal_long = action.goal_long[:240]

    # Dispatch
    handler = _DISPATCH.get(action.kind)
    if handler is None:
        return ActionResult(ok=False, error=f"unsupported action {action.kind}")

    before_seq = universe.seq
    result = handler(universe, player_id, action)
    result.event_seqs = [e.seq for e in universe.events if e.seq > before_seq]

    # Count turns
    if result.ok and result.turns_spent > 0:
        player.turns_today += result.turns_spent

    # Check victory after every applied action
    _check_victory(universe)

    return result


def tick_day(universe: Universe) -> None:
    """Advance the game by one day: reset turns, regenerate ports, spawn Ferrengi, grow planets."""
    universe.day += 1
    for player in universe.players.values():
        player.turns_today = 0
        # Photon scramble decays one tick per real game day
        if player.ship.photon_disabled_ticks > 0:
            player.ship.photon_disabled_ticks = max(0, player.ship.photon_disabled_ticks - 1)

    regenerate_ports(universe)

    if universe.config.enable_ferrengi:
        _spawn_ferrengi(universe)
        _ferrengi_roam_and_hunt(universe)
    if universe.config.enable_planets:
        _advance_planets(universe)
        _complete_citadels(universe)

    universe.emit(
        EventKind.DAY_TICK,
        payload={"day": universe.day},
        summary=f"-- Day {universe.day} dawns --",
    )
    _check_victory(universe)


def is_finished(universe: Universe) -> bool:
    return universe.finished


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------


def _truncate_for_feed(s: str, limit: int = 140) -> str:
    s = s.strip().replace("\n", " ")
    if len(s) <= limit:
        return s
    return s[: limit - 1] + "…"


def _learn_sector(player, universe: Universe, sector_id: int) -> None:
    """Record `sector_id` AND its warp edges in the player's persistent memory.

    Every site that used to do `player.known_sectors.add(sid)` gets upgraded
    to this helper so the `known_warps` graph stays in sync with the sector
    set. Idempotent: re-visiting a known sector just overwrites the same
    warp list with identical contents (sector warps are static).

    Why it matters: without the warp graph, an LLM agent that visits
    sector 406 and sees warps_out=[475] has no way to remember that fact
    after the observation scrolls past the event. Agents deadloop because
    the map they're trying to plan against lives only in the scratchpad
    (if they remembered to write it there) or the last 12 events
    (if the relevant warp intel hasn't aged out yet).
    """
    if sector_id not in universe.sectors:
        return
    player.known_sectors.add(sector_id)
    sec = universe.sectors[sector_id]
    # Copy to list to avoid sharing mutable state with the engine's sector
    # warps, and to survive Pydantic round-trips on save/replay.
    player.known_warps[sector_id] = list(sec.warps)


def _warp_cost_for(player) -> int:
    """Per-ship turns/warp; falls back to global TURN_COST['warp']."""
    spec = K.SHIP_SPECS.get(player.ship.ship_class.value)
    if spec and "turns_per_warp" in spec:
        return int(spec["turns_per_warp"])
    return K.TURN_COST["warp"]


def _handle_warp(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    target = action.args.get("target")
    if target is None:
        return ActionResult(ok=False, error="warp requires 'target' sector id")
    try:
        target_id = int(target)
    except (ValueError, TypeError):
        return ActionResult(ok=False, error=f"invalid target {target!r}")

    cur = universe.sectors.get(player.sector_id)
    if cur is None or target_id not in cur.warps:
        universe.emit(
            EventKind.WARP_BLOCKED,
            actor_id=pid,
            sector_id=player.sector_id,
            payload={"target": target_id},
            summary=f"{player.name} tried to warp to {target_id} (no warp)",
        )
        return ActionResult(ok=False, error=f"no warp from {player.sector_id} to {target_id}")

    cost = _warp_cost_for(player)
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns for this day")

    # Mine check
    dest = universe.sectors[target_id]
    rng = _rng_for(universe)
    damage = 0
    for md in list(dest.mines):
        if md.owner_id == pid:
            continue
        # Corp mate / ally mines don't trigger
        if _are_allied(universe, pid, md.owner_id):
            continue
        if md.kind == MineType.ARMID:
            hits = min(md.count, rng.randint(1, K.MINE_MAX_HITS_PER_MOVE))
            damage += hits * K.ARMID_DAMAGE
            md.count -= hits
            if md.count <= 0:
                dest.mines.remove(md)
            universe.emit(
                EventKind.MINE_DETONATED,
                actor_id=md.owner_id,
                sector_id=target_id,
                payload={"hits": hits, "damage": hits * K.ARMID_DAMAGE, "victim": pid},
                summary=f"{hits} armid mines hit {player.name} entering {target_id} ({hits * K.ARMID_DAMAGE} dmg)",
            )
        elif md.kind == MineType.LIMPET:
            # Silently attach 1 limpet tracker; consume one mine.
            md.count -= 1
            if md.count <= 0:
                dest.mines.remove(md)
            _attach_limpet(universe, md.owner_id, pid)

    if damage > 0:
        player.ship.shields = max(0, player.ship.shields - damage)
        overflow = damage - player.ship.shields
        if player.ship.shields == 0 and overflow > 0:
            player.ship.fighters = max(0, player.ship.fighters - overflow)

    if player.ship.fighters == 0 and damage > 0:
        # Ship destroyed on entry; player ejected and respawns at StarDock
        _destroy_ship(universe, pid, reason="mines")

    # Hostile sector fighter check
    if dest.fighters and dest.fighters.owner_id != pid:
        f_mode = dest.fighters.mode
        owner = universe.players.get(dest.fighters.owner_id)
        allied = owner is not None and _are_allied(universe, pid, owner.id)
        if not allied:
            if f_mode == FighterMode.OFFENSIVE:
                # Auto-attack
                _resolve_fighter_sector_combat(universe, pid, target_id)
            elif f_mode == FighterMode.TOLL:
                toll = dest.fighters.count  # 1 cr / fighter simplified = high disincentive
                toll = min(player.credits, max(10, min(10000, dest.fighters.count)))
                player.credits -= toll
                if owner is not None:
                    owner.credits += toll
                universe.emit(
                    EventKind.TRADE,
                    actor_id=pid,
                    sector_id=target_id,
                    payload={"toll_to": dest.fighters.owner_id, "amount": toll},
                    summary=f"{player.name} paid {toll} cr toll to pass through {target_id}",
                )

    # If destroyed by fighters, handler already ejected player
    if not player.alive or (player.sector_id == K.STARDOCK_SECTOR and damage > 0):
        # Leave as-is after destruction
        pass

    if player.alive:
        # Leave old sector
        try:
            universe.sectors[player.sector_id].occupant_ids.remove(pid)
        except ValueError:
            pass
        player.sector_id = target_id
        dest.occupant_ids.append(pid)
        _learn_sector(player, universe, target_id)
        # Log port if present
        if dest.port is not None:
            _record_port_intel(player, dest.id, dest.port, universe=universe)

        universe.emit(
            EventKind.WARP,
            actor_id=pid,
            sector_id=target_id,
            payload={"from": cur.id, "to": target_id},
            summary=f"{player.name} warped {cur.id} → {target_id}",
        )
        _award_xp(universe, pid, "warp")

    return ActionResult(ok=True, turns_spent=cost)


def _handle_trade(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    if sector.port is None or sector.port.class_id == PortClass.STARDOCK:
        return ActionResult(ok=False, error="no trading port in this sector")
    port = sector.port

    try:
        commodity = Commodity(action.args.get("commodity"))
    except ValueError:
        return ActionResult(ok=False, error=f"invalid commodity {action.args.get('commodity')!r}")
    qty = int(action.args.get("qty", 0))
    side = action.args.get("side", "").lower()
    offered = action.args.get("unit_price")
    if offered is not None:
        offered = int(offered)

    if side not in ("buy", "sell"):
        return ActionResult(ok=False, error="side must be 'buy' or 'sell'")

    cost = K.TURN_COST["trade"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns for this day")

    rng = _rng_for(universe)
    ok, total, unit, msg, realized = execute_trade(
        universe, player, port, commodity, qty, side, offered, rng
    )

    if not ok:
        universe.emit(
            EventKind.TRADE_FAILED,
            actor_id=pid,
            sector_id=sector.id,
            payload={"commodity": commodity.value, "qty": qty, "side": side, "reason": msg},
            summary=f"{player.name} trade failed: {msg}",
        )
        return ActionResult(ok=False, error=msg, turns_spent=cost)

    _record_port_intel(player, sector.id, port, universe=universe)
    # Persistent trade ledger — last 50 entries per player. The observation
    # surfaces the last 5 so the agent can audit "what did my loop actually
    # earn me?" without re-deriving from the global rolling feed which can
    # scroll them out of view in a busy match.
    entry = {
        "day": universe.day,
        "tick": universe.tick,
        "sector_id": sector.id,
        "commodity": commodity.value,
        "qty": qty,
        "side": side,
        "unit": unit,
        "total": total,
        "realized_profit": realized,  # None on buy, int (can be negative) on sell
    }
    player.trade_log.append(entry)
    if len(player.trade_log) > 50:
        del player.trade_log[: len(player.trade_log) - 50]

    note = ""
    if msg and msg != "ok":
        note = f"  [{msg}]"
    # On sells, suffix the summary with realized profit so the spectator feed
    # shows per-trade P&L directly — no mental math needed to know whether
    # the trade was actually good.
    pnl_tag = ""
    if side == "sell" and realized is not None:
        sign = "+" if realized >= 0 else ""
        pnl_tag = f"  ({sign}{realized}cr profit)"
    universe.emit(
        EventKind.TRADE,
        actor_id=pid,
        sector_id=sector.id,
        payload={
            "commodity": commodity.value,
            "qty": qty,
            "side": side,
            "total": total,
            "unit": unit,
            "note": msg,
            "realized_profit": realized,
        },
        summary=f"{player.name} {side} {qty} {commodity.value} @ {unit}cr = {total}cr{note}{pnl_tag}",
    )
    _award_xp(universe, pid, "trade")
    return ActionResult(ok=True, turns_spent=cost)


def _handle_scan(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Tiered scan.

    args:
      tier: 'basic' (default — 1-hop with port codes & fighter counts),
            'density' (2-hop, just sector occupant/port presence — no detailed prices),
            'holo'    (1-hop full intel including stock levels)
    """
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    cost = K.TURN_COST["scan"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    tier = (action.args.get("tier") or K.SCAN_TIER_BASIC).lower()
    if tier not in (K.SCAN_TIER_BASIC, K.SCAN_TIER_DENSITY, K.SCAN_TIER_HOLO):
        return ActionResult(ok=False, error=f"unknown scan tier {tier!r}")

    # Scanning your current sector reveals its warp lanes — persist them
    # into known_warps so the agent can plan routes turn after turn.
    # Adjacent sectors' warps stay unknown (fog-of-war on topology).
    _learn_sector(player, universe, sector.id)

    neigh_info: list[dict] = []
    if tier == K.SCAN_TIER_BASIC:
        for wid in sector.warps:
            w = universe.sectors[wid]
            neigh_info.append({
                "id": wid,
                "port": w.port.code if w.port else None,
                "fighters": w.fighters.count if w.fighters else 0,
                "fighter_owner": w.fighters.owner_id if w.fighters else None,
                "has_planets": bool(w.planet_ids),
                "occupants": list(w.occupant_ids),
            })
            player.known_sectors.add(wid)
            if w.port is not None:
                _record_port_intel(player, wid, w.port, universe=universe)
        summary = f"{player.name} scanned {sector.id}"
    elif tier == K.SCAN_TIER_DENSITY:
        # 2-hop sector density — only counts, no detail
        seen: set[int] = set(sector.warps)
        for wid in sector.warps:
            for w2 in universe.sectors[wid].warps:
                seen.add(w2)
            player.known_sectors.add(wid)
        for wid in sorted(seen):
            w = universe.sectors[wid]
            neigh_info.append({
                "id": wid,
                "port": w.port.code if w.port else None,
                "occupants": len(w.occupant_ids),
                "planets": len(w.planet_ids),
                "fighters": w.fighters.count if w.fighters else 0,
            })
        summary = f"{player.name} ran density scan from {sector.id} ({len(seen)} sectors)"
    else:  # holo
        for wid in sector.warps:
            w = universe.sectors[wid]
            entry: dict = {
                "id": wid,
                "port": w.port.code if w.port else None,
                "fighters": w.fighters.count if w.fighters else 0,
                "fighter_owner": w.fighters.owner_id if w.fighters else None,
                "occupants": list(w.occupant_ids),
                "planets": [universe.planets[pl].name for pl in w.planet_ids if pl in universe.planets],
                "mines_total": sum(m.count for m in w.mines),
            }
            if w.port is not None:
                from .economy import port_buy_price, port_sell_price
                entry["port_stock"] = {
                    c.value: {
                        "current": s.current,
                        "max": s.maximum,
                        "price": (
                            port_buy_price(w.port, c) if w.port.buys(c)
                            else port_sell_price(w.port, c)
                        ),
                        "side": "buys_from_player" if w.port.buys(c) else "sells_to_player",
                    }
                    for c, s in w.port.stock.items()
                }
                _record_port_intel(player, wid, w.port, universe=universe)
            player.known_sectors.add(wid)
            neigh_info.append(entry)
        summary = f"{player.name} ran HoloScan from {sector.id}"

    universe.emit(
        EventKind.SCAN,
        actor_id=pid,
        sector_id=sector.id,
        payload={"tier": tier, "neighbors": neigh_info},
        summary=summary,
    )
    _award_xp(universe, pid, "scan")
    return ActionResult(ok=True, turns_spent=cost)


def _handle_deploy_fighters(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    qty = int(action.args.get("qty", 0))
    mode_raw = action.args.get("mode", "defensive")
    try:
        mode = FighterMode(mode_raw)
    except ValueError:
        return ActionResult(ok=False, error=f"invalid fighter mode {mode_raw!r}")
    if qty <= 0 or qty > player.ship.fighters:
        return ActionResult(ok=False, error="invalid fighter quantity")
    if sector.id in K.FEDSPACE_SECTORS:
        return ActionResult(ok=False, error="cannot deploy fighters in FedSpace")

    cost = K.TURN_COST["deploy_fighters"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")

    if sector.fighters is None:
        sector.fighters = FighterDeployment(owner_id=pid, count=qty, mode=mode)
    elif sector.fighters.owner_id == pid:
        sector.fighters.count += qty
        sector.fighters.mode = mode
    else:
        # Conflict — resolve combat between fighter groups
        _resolve_fighter_sector_combat(universe, pid, sector.id, incoming_fighters=qty, incoming_mode=mode)
        player.ship.fighters -= qty  # incoming group was consumed in combat
        return ActionResult(ok=True, turns_spent=cost)

    player.ship.fighters -= qty
    universe.emit(
        EventKind.DEPLOY_FIGHTERS,
        actor_id=pid,
        sector_id=sector.id,
        payload={"qty": qty, "mode": mode.value},
        summary=f"{player.name} deployed {qty} {mode.value} fighters in {sector.id}",
    )
    return ActionResult(ok=True, turns_spent=cost)


def _handle_deploy_mines(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    qty = int(action.args.get("qty", 0))
    try:
        kind = MineType(action.args.get("kind", "armid"))
    except ValueError:
        return ActionResult(ok=False, error="invalid mine type")
    if qty <= 0 or qty > player.ship.mines.get(kind, 0):
        return ActionResult(ok=False, error="insufficient mines")
    if sector.id in K.FEDSPACE_SECTORS:
        return ActionResult(ok=False, error="cannot deploy mines in FedSpace")

    cost = K.TURN_COST["deploy_mines"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")

    # ATOMIC mines detonate immediately — they don't sit in the sector.
    if kind == MineType.ATOMIC:
        return _handle_atomic_detonation(universe, pid, qty, sector, cost)

    existing = next((m for m in sector.mines if m.owner_id == pid and m.kind == kind), None)
    if existing:
        existing.count += qty
    else:
        sector.mines.append(MineDeployment(owner_id=pid, kind=kind, count=qty))
    player.ship.mines[kind] -= qty

    universe.emit(
        EventKind.DEPLOY_MINES,
        actor_id=pid,
        sector_id=sector.id,
        payload={"qty": qty, "kind": kind.value},
        summary=f"{player.name} seeded {qty} {kind.value} mines in {sector.id}",
    )
    return ActionResult(ok=True, turns_spent=cost)


def _handle_atomic_detonation(
    universe: Universe, pid: str, qty: int, sector, cost: int
) -> ActionResult:
    """ATOMIC mines: destroy port stock + damage planet citadel/treasury + nuke fighters in sector."""
    player = universe.players[pid]
    player.ship.mines[MineType.ATOMIC] -= qty
    player.alignment -= 50 * qty  # major alignment hit per warhead

    # Aggregate effects scaled by qty
    port_destroyed = False
    planet_hits: list[int] = []
    sector_fighters_destroyed = 0
    if sector.port is not None and sector.port.class_id not in (PortClass.STARDOCK, PortClass.FEDERAL):
        for c, s in list(sector.port.stock.items()):
            loss = int(s.current * min(1.0, K.ATOMIC_PORT_DAMAGE * qty))
            sector.port.stock[c].current = max(0, s.current - loss)
        if all(s.current == 0 for s in sector.port.stock.values()) and qty >= 3:
            sector.port = None
            port_destroyed = True

    for plid in list(sector.planet_ids):
        planet = universe.planets[plid]
        loss_t = int(planet.treasury * min(1.0, K.ATOMIC_PLANET_DAMAGE * qty))
        planet.treasury = max(0, planet.treasury - loss_t)
        loss_f = int(planet.fighters * min(1.0, K.ATOMIC_PLANET_DAMAGE * qty))
        planet.fighters = max(0, planet.fighters - loss_f)
        if planet.citadel_level > 0 and qty >= 2:
            planet.citadel_level = max(0, planet.citadel_level - max(1, qty // 2))
        planet_hits.append(plid)

    if sector.fighters is not None:
        if sector.fighters.owner_id != pid:
            sector_fighters_destroyed = sector.fighters.count
            sector.fighters = None

    if port_destroyed:
        universe.emit(
            EventKind.PORT_DESTROYED,
            actor_id=pid,
            sector_id=sector.id,
            payload={"qty": qty},
            summary=f"!!! Port in {sector.id} OBLITERATED by {qty}x atomic detonation !!!",
        )
    universe.emit(
        EventKind.ATOMIC_DETONATION,
        actor_id=pid,
        sector_id=sector.id,
        payload={
            "qty": qty,
            "port_destroyed": port_destroyed,
            "planet_hits": planet_hits,
            "sector_fighters_destroyed": sector_fighters_destroyed,
        },
        summary=(
            f"*** {player.name} detonated {qty} atomic warheads in {sector.id} "
            f"(alignment {player.alignment}) ***"
        ),
    )
    return ActionResult(ok=True, turns_spent=cost)


def _handle_attack(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    target_id = action.args.get("target")
    if target_id is None:
        return ActionResult(ok=False, error="attack requires target player id")
    target = universe.players.get(target_id) or _ferrengi_by_name(universe, str(target_id))
    if target is None:
        return ActionResult(ok=False, error=f"target {target_id} not found")
    if getattr(target, "sector_id", -1) != player.sector_id:
        return ActionResult(ok=False, error="target not in this sector")
    # Block friendly fire (corp mates + active alliances)
    if isinstance(target_id, str) and target_id in universe.players and _are_allied(universe, pid, target_id):
        return ActionResult(ok=False, error="cannot attack a corp mate or ally")
    if player.sector_id in K.FEDSPACE_SECTORS:
        universe.emit(
            EventKind.FED_RESPONSE,
            actor_id=pid,
            sector_id=player.sector_id,
            payload={"reason": "attempted PvP in FedSpace"},
            summary=f"Federation warns {player.name} — no combat in FedSpace!",
        )
        player.alignment -= 200
        return ActionResult(ok=False, error="FedSpace — combat forbidden")

    cost = K.TURN_COST["attack"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")

    _resolve_ship_combat(universe, pid, target)
    return ActionResult(ok=True, turns_spent=cost)


def _handle_wait(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    cost = K.TURN_COST["wait"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    return ActionResult(ok=True, turns_spent=cost)


def _handle_land_planet(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    planet_id = action.args.get("planet_id")
    if planet_id is None or int(planet_id) not in sector.planet_ids:
        return ActionResult(ok=False, error="no such planet in this sector")
    planet = universe.planets[int(planet_id)]
    cost = K.TURN_COST["land_planet"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")

    hostile = (
        planet.owner_id is not None
        and planet.owner_id != pid
        and not (
            planet.corp_ticker
            and player.corp_ticker
            and planet.corp_ticker == player.corp_ticker
        )
    )
    if hostile and planet.fighters > 0:
        # Citadel combat: planet fights back with its own fighters/shields.
        rng = _rng_for(universe)
        a_fighters = player.ship.fighters
        a_shields = player.ship.shields
        d_fighters = planet.fighters
        d_shields = planet.shields
        # 3 exchanges, planet absorbs first via shields then fighters, just like ships.
        for _ in range(3):
            a_dmg = int(a_fighters * rng.uniform(0.8, 1.2))
            d_dmg = int(d_fighters * rng.uniform(0.8, 1.2))
            absorbed = min(a_dmg, d_shields)
            d_shields -= absorbed
            d_fighters = max(0, d_fighters - (a_dmg - absorbed))
            absorbed = min(d_dmg, a_shields)
            a_shields -= absorbed
            a_fighters = max(0, a_fighters - (d_dmg - absorbed))
            if a_fighters <= 0 or d_fighters <= 0:
                break
        player.ship.fighters = a_fighters
        player.ship.shields = a_shields
        planet.fighters = d_fighters
        planet.shields = d_shields
        universe.emit(
            EventKind.COMBAT,
            actor_id=pid,
            sector_id=sector.id,
            payload={
                "vs": "planet",
                "planet_id": planet.id,
                "attacker_f": a_fighters, "attacker_s": a_shields,
                "defender_f": d_fighters, "defender_s": d_shields,
            },
            summary=(
                f"Siege of {planet.name}: "
                f"{player.name}[F{a_fighters} S{a_shields}] vs Citadel L{planet.citadel_level}"
                f"[F{d_fighters} S{d_shields}]"
            ),
        )
        if a_fighters <= 0:
            _destroy_ship(universe, pid, reason="planet_defense", killer_id=planet.owner_id)
            return ActionResult(ok=True, turns_spent=cost)
        if d_fighters > 0:
            return ActionResult(ok=False, error="planetary defenses repelled landing", turns_spent=cost)
        # Planet defenders wiped — fall through and seize.
        planet.owner_id = pid
        planet.corp_ticker = player.corp_ticker
        planet.citadel_level = max(0, planet.citadel_level - 1)  # damaged in siege
        planet.treasury = int(planet.treasury * 0.5)
    elif hostile:
        # Hostile but no defenders — block per legacy behavior (was outright refusal).
        planet.owner_id = pid
        planet.corp_ticker = player.corp_ticker
    elif planet.owner_id is None:
        planet.owner_id = pid
        planet.corp_ticker = player.corp_ticker

    player.planet_landed = planet.id
    universe.emit(
        EventKind.LAND_PLANET,
        actor_id=pid,
        sector_id=sector.id,
        payload={"planet_id": planet.id, "class": planet.class_id.value, "seized": hostile},
        summary=(
            f"{player.name} landed on {planet.name} ({planet.class_id.value})"
            + (" — SEIZED!" if hostile else "")
        ),
    )
    return ActionResult(ok=True, turns_spent=cost)


def _handle_liftoff(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if player.planet_landed is None:
        return ActionResult(ok=False, error="not landed on a planet")
    cost = K.TURN_COST["liftoff"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    planet_id = player.planet_landed
    player.planet_landed = None
    universe.emit(
        EventKind.LIFTOFF,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"planet_id": planet_id},
        summary=f"{player.name} lifted off",
    )
    return ActionResult(ok=True, turns_spent=cost)


def _handle_assign_colonists(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Move colonists between ship cargo / planet work-pools.

    args:
      planet_id: target planet (must be in current sector)
      from: 'ship' | 'fuel_ore' | 'organics' | 'equipment' | 'colonists' (the planet pool)
      to:   same options
      qty: number to move
    """
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    planet_id = action.args.get("planet_id")
    if planet_id is None or int(planet_id) not in sector.planet_ids:
        return ActionResult(ok=False, error="no such planet in this sector")
    planet = universe.planets[int(planet_id)]
    if planet.owner_id != pid and not (
        planet.corp_ticker
        and player.corp_ticker
        and planet.corp_ticker == player.corp_ticker
    ):
        return ActionResult(ok=False, error="planet not owned by you or your corp")
    if player.planet_landed != planet.id:
        return ActionResult(ok=False, error="must be landed on the planet first")

    qty = int(action.args.get("qty", 0))
    if qty <= 0:
        return ActionResult(ok=False, error="qty must be positive")
    src = (action.args.get("from") or "ship").lower()
    dst = (action.args.get("to") or "").lower()
    pool_keys = {
        "fuel_ore": Commodity.FUEL_ORE,
        "organics": Commodity.ORGANICS,
        "equipment": Commodity.EQUIPMENT,
        "colonists": Commodity.COLONISTS,
        "fighters": Commodity.COLONISTS,  # alias
    }
    if dst not in pool_keys and dst != "ship":
        return ActionResult(ok=False, error=f"invalid 'to' pool {dst!r}")
    if src not in pool_keys and src != "ship":
        return ActionResult(ok=False, error=f"invalid 'from' pool {src!r}")

    cost = K.TURN_COST.get("liftoff", 1)
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")

    # Withdraw
    if src == "ship":
        avail = player.ship.cargo.get(Commodity.COLONISTS, 0)
        if avail < qty:
            return ActionResult(ok=False, error=f"only {avail} colonists in cargo")
        player.ship.cargo[Commodity.COLONISTS] = avail - qty
    else:
        key = pool_keys[src]
        avail = planet.colonists.get(key, 0)
        if avail < qty:
            return ActionResult(ok=False, error=f"only {avail} on {src} pool")
        planet.colonists[key] = avail - qty

    # Deposit
    if dst == "ship":
        used = player.ship.cargo_used
        if used + qty > player.ship.holds:
            # Refund withdrawal to avoid losing colonists
            if src == "ship":
                player.ship.cargo[Commodity.COLONISTS] += qty
            else:
                planet.colonists[pool_keys[src]] += qty
            return ActionResult(ok=False, error="not enough cargo holds")
        player.ship.cargo[Commodity.COLONISTS] = (
            player.ship.cargo.get(Commodity.COLONISTS, 0) + qty
        )
    else:
        key = pool_keys[dst]
        planet.colonists[key] = planet.colonists.get(key, 0) + qty

    universe.emit(
        EventKind.ASSIGN_COLONISTS,
        actor_id=pid,
        sector_id=sector.id,
        payload={"planet_id": planet.id, "from": src, "to": dst, "qty": qty},
        summary=f"{player.name} moved {qty} colonists {src} → {dst} on {planet.name}",
    )
    return ActionResult(ok=True, turns_spent=cost)


def _handle_build_citadel(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    planet_id = action.args.get("planet_id")
    if planet_id is None or int(planet_id) not in sector.planet_ids:
        return ActionResult(ok=False, error="no such planet in this sector")
    planet = universe.planets[int(planet_id)]
    if planet.owner_id != pid and not (
        planet.corp_ticker
        and player.corp_ticker
        and planet.corp_ticker == player.corp_ticker
    ):
        return ActionResult(ok=False, error="planet not owned by you or your corp")
    if player.planet_landed != planet.id:
        return ActionResult(ok=False, error="must be landed on the planet first")
    if planet.citadel_target > planet.citadel_level:
        return ActionResult(
            ok=False,
            error=f"citadel L{planet.citadel_target} already under construction (done day {planet.citadel_complete_day})",
        )

    next_level = planet.citadel_level + 1
    if next_level > K.CITADEL_LEVELS:
        return ActionResult(ok=False, error="citadel already at max level")
    cred_cost, col_cost, days = K.CITADEL_TIER_COST[next_level - 1]

    # Pay from corp treasury first if member, otherwise personal credits
    using_corp = False
    paid_from = "personal"
    if player.corp_ticker:
        corp = universe.corporations.get(player.corp_ticker)
        if corp is not None and corp.treasury >= cred_cost:
            using_corp = True
    if using_corp:
        universe.corporations[player.corp_ticker].treasury -= cred_cost
        paid_from = f"corp[{player.corp_ticker}]"
    elif player.credits >= cred_cost:
        player.credits -= cred_cost
    else:
        return ActionResult(ok=False, error=f"need {cred_cost}cr to start citadel L{next_level}")

    # Colonists for construction crew
    avail_col = sum(planet.colonists.get(c, 0) for c in planet.colonists)
    if avail_col < col_cost:
        # Refund
        if using_corp:
            universe.corporations[player.corp_ticker].treasury += cred_cost
        else:
            player.credits += cred_cost
        return ActionResult(ok=False, error=f"need {col_cost} colonists on planet (have {avail_col})")
    # Drain colonists evenly
    remaining = col_cost
    for c in list(planet.colonists.keys()):
        if remaining <= 0:
            break
        take = min(planet.colonists[c], remaining)
        planet.colonists[c] -= take
        remaining -= take

    cost = K.TURN_COST.get("land_planet", 3)
    if player.turns_today + cost > player.turns_per_day:
        cost = 0  # don't refuse the build for this; small cost only

    planet.citadel_target = next_level
    planet.citadel_complete_day = universe.day + days
    universe.emit(
        EventKind.BUILD_CITADEL,
        actor_id=pid,
        sector_id=sector.id,
        payload={
            "planet_id": planet.id,
            "level_target": next_level,
            "completes_day": planet.citadel_complete_day,
            "cost_cr": cred_cost,
            "cost_col": col_cost,
            "paid_from": paid_from,
        },
        summary=(
            f"{player.name} began Citadel L{next_level} on {planet.name} "
            f"({cred_cost}cr from {paid_from}, {col_cost} colonists, ETA day {planet.citadel_complete_day})"
        ),
    )
    return ActionResult(ok=True, turns_spent=cost)


def _handle_deploy_genesis(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    if player.ship.genesis <= 0:
        return ActionResult(ok=False, error="no genesis torpedoes loaded")
    if sector.id in K.FEDSPACE_SECTORS:
        return ActionResult(ok=False, error="cannot deploy genesis in FedSpace")
    # Enforce real distance from StarDock. In classic TW2002 planets had to
    # be built "deep" — you couldn't park a citadel next to Sol. Without
    # this check a single-hop-from-StarDock sector would qualify just by
    # being outside FedSpace, trivializing the colonist-ferry phase.
    hops_from_stardock = len(_bfs_path(universe, K.STARDOCK_SECTOR, sector.id))
    if hops_from_stardock > 0 and hops_from_stardock < K.GENESIS_MIN_HOPS_FROM_STARDOCK:
        return ActionResult(
            ok=False,
            error=(
                f"too close to StarDock ({hops_from_stardock} hops, "
                f"need >={K.GENESIS_MIN_HOPS_FROM_STARDOCK}); warp deeper"
            ),
        )
    if player.planet_landed is not None:
        return ActionResult(ok=False, error="must be in space to deploy genesis")
    cost = K.GENESIS_DEPLOY_TURN_COST
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")

    rng = _rng_for(universe)
    cls_name = _weighted_choice(rng, K.PLANET_CLASS_WEIGHTS)
    cls = PlanetClass(cls_name)
    pid_planet = universe.next_planet_id
    universe.next_planet_id += 1
    name_roots = ["New", "Genesis", "Phoenix", "Wyrd", "Eden"]
    planet_name = f"{rng.choice(name_roots)} {sector.id}-{pid_planet}"
    planet = Planet(
        id=pid_planet,
        sector_id=sector.id,
        name=planet_name,
        class_id=cls,
        owner_id=pid,
        corp_ticker=player.corp_ticker,
    )
    # Seed a founding population so the citadel/production path is actually
    # reachable. Without this, new planets had 0 colonists and growth = 0 * 5%
    # forever — locking out the entire S3/S4/S5 progression arc.
    #
    # Distribution favors fuel-ore workers (most broadly useful commodity) but
    # leaves a healthy construction reserve in the "colonists" pool so the
    # first Citadel L1 (which costs 1,000 colonists) can be built immediately
    # after the player ferries the standard tier if they choose, or from the
    # seed alone in a pinch.
    seed_total = K.GENESIS_SEED_COLONISTS
    planet.colonists[Commodity.FUEL_ORE] = int(seed_total * 0.40)
    planet.colonists[Commodity.ORGANICS] = int(seed_total * 0.25)
    planet.colonists[Commodity.EQUIPMENT] = int(seed_total * 0.15)
    planet.colonists[Commodity.COLONISTS] = (
        seed_total
        - planet.colonists[Commodity.FUEL_ORE]
        - planet.colonists[Commodity.ORGANICS]
        - planet.colonists[Commodity.EQUIPMENT]
    )
    # Small organics stockpile so colonist growth can start immediately —
    # growth is gated on `stockpile[ORGANICS] > 0`.
    planet.stockpile[Commodity.ORGANICS] = max(
        planet.stockpile.get(Commodity.ORGANICS, 0), 25
    )
    universe.planets[pid_planet] = planet
    sector.planet_ids.append(pid_planet)
    player.ship.genesis -= 1

    universe.emit(
        EventKind.GENESIS_DEPLOYED,
        actor_id=pid,
        sector_id=sector.id,
        payload={"planet_id": pid_planet, "class": cls.value, "name": planet_name},
        summary=f"{player.name} detonated a Genesis torpedo — new {cls.value}-class planet {planet_name} forms in {sector.id}",
    )
    _award_xp(universe, pid, "deploy_genesis")
    return ActionResult(ok=True, turns_spent=cost)


def _weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    total = sum(weights.values())
    roll = rng.uniform(0.0, total)
    cum = 0.0
    for k, w in weights.items():
        cum += w
        if roll <= cum:
            return k
    return next(iter(weights))


def _handle_buy_ship(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if player.sector_id != K.STARDOCK_SECTOR:
        return ActionResult(ok=False, error="must be at StarDock")
    class_key = action.args.get("ship_class")
    spec = K.SHIP_SPECS.get(class_key or "")
    if spec is None:
        return ActionResult(ok=False, error=f"unknown ship class {class_key!r}")
    if spec.get("corp_only") and player.corp_ticker is None:
        return ActionResult(ok=False, error="ship is corporation-only")
    if spec.get("min_alignment", 0) > player.alignment:
        return ActionResult(ok=False, error=f"alignment too low for {class_key}")
    if spec.get("unique"):
        # Only one Imperial StarShip in the universe
        for p in universe.players.values():
            if p.ship.ship_class.value == class_key:
                return ActionResult(ok=False, error="this ship class is already owned elsewhere")

    trade_in = int(K.SHIP_SPECS[player.ship.ship_class.value]["cost"] * 0.25)
    net_cost = spec["cost"] - trade_in
    if player.credits < net_cost:
        return ActionResult(ok=False, error=f"insufficient credits ({player.credits} < {net_cost})")

    player.credits -= net_cost
    from .models import ShipClass as SC  # local import to avoid cycle in runtime edits
    player.ship.ship_class = SC(class_key)
    player.ship.holds = spec["holds"]
    # Preserve cargo sum but drop excess
    total = player.ship.cargo_used
    if total > spec["holds"]:
        keep = spec["holds"]
        for c in [Commodity.EQUIPMENT, Commodity.ORGANICS, Commodity.FUEL_ORE, Commodity.COLONISTS]:
            n = player.ship.cargo.get(c, 0)
            if keep <= 0:
                player.ship.cargo[c] = 0
            elif n > keep:
                player.ship.cargo[c] = keep
                keep = 0
            else:
                keep -= n

    universe.emit(
        EventKind.BUY_SHIP,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"ship_class": class_key, "net_cost": net_cost},
        summary=f"{player.name} bought a {spec['display_name']} ({net_cost} cr)",
    )
    return ActionResult(ok=True, turns_spent=0)


def _handle_buy_equip(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if player.sector_id != K.STARDOCK_SECTOR:
        return ActionResult(ok=False, error="must be at StarDock")
    item = action.args.get("item")
    qty = int(action.args.get("qty", 0))
    if qty <= 0:
        return ActionResult(ok=False, error="qty must be positive")
    prices = {
        "fighters": K.FIGHTER_COST,
        "shields": 10,
        "armid_mines": K.ARMID_MINE_COST,
        "limpet_mines": K.LIMPET_MINE_COST,
        "atomic_mines": K.ATOMIC_MINE_COST,
        "photon_missiles": K.PHOTON_MISSILE_COST,
        "ether_probes": K.ETHER_PROBE_COST,
        "genesis": K.GENESIS_TORPEDO_COST,
        "holds": K.SHIP_SPECS[player.ship.ship_class.value]["base_hold_cost"],
        # Colonists are sold by Terra (classic TW2002: ~10 cr/unit). StarDock
        # doubles as the Federation's colonist exchange here — fold them into
        # buy_equip so the ferry-to-your-planet loop actually exists in game.
        "colonists": K.COLONIST_PRICE,
    }
    unit = prices.get(item or "")
    if unit is None:
        return ActionResult(ok=False, error=f"unknown item {item!r}")
    total = unit * qty
    if player.credits < total:
        return ActionResult(ok=False, error=f"insufficient credits ({player.credits} < {total})")
    spec = K.SHIP_SPECS[player.ship.ship_class.value]
    if item == "fighters":
        if player.ship.fighters + qty > spec["max_fighters"]:
            return ActionResult(ok=False, error="exceeds ship fighter capacity")
        player.ship.fighters += qty
    elif item == "shields":
        if player.ship.shields + qty > spec["max_shields"]:
            return ActionResult(ok=False, error="exceeds ship shield capacity")
        player.ship.shields += qty
    elif item == "armid_mines":
        player.ship.mines[MineType.ARMID] = player.ship.mines.get(MineType.ARMID, 0) + qty
    elif item == "limpet_mines":
        player.ship.mines[MineType.LIMPET] = player.ship.mines.get(MineType.LIMPET, 0) + qty
    elif item == "atomic_mines":
        player.ship.mines[MineType.ATOMIC] = player.ship.mines.get(MineType.ATOMIC, 0) + qty
    elif item == "photon_missiles":
        player.ship.photon_missiles += qty
    elif item == "ether_probes":
        player.ship.ether_probes += qty
    elif item == "genesis":
        player.ship.genesis += qty
    elif item == "holds":
        # Classic TW caps at 75 or 150 based on ship; here we accept anything up to 150 total
        new_holds = player.ship.holds + qty
        if new_holds > 150:
            return ActionResult(ok=False, error="max holds reached")
        player.ship.holds = new_holds
    elif item == "colonists":
        # Buying colonists loads them as cargo. They must fit — each colonist
        # is 1 unit of hold capacity, same as any commodity.
        used = player.ship.cargo_used
        if used + qty > player.ship.holds:
            return ActionResult(
                ok=False,
                error=f"not enough cargo holds (need {qty}, free {player.ship.holds - used})",
            )
        player.ship.cargo[Commodity.COLONISTS] = (
            player.ship.cargo.get(Commodity.COLONISTS, 0) + qty
        )
    player.credits -= total

    universe.emit(
        EventKind.BUY_EQUIP,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"item": item, "qty": qty, "total": total},
        summary=f"{player.name} bought {qty} {item} for {total}cr",
    )
    return ActionResult(ok=True, turns_spent=0)


def _handle_corp_create(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if player.corp_ticker is not None:
        return ActionResult(ok=False, error="already in a corporation")
    if player.sector_id != K.STARDOCK_SECTOR:
        return ActionResult(ok=False, error="must be at StarDock")
    if player.credits < K.CORP_FORMATION_COST:
        return ActionResult(ok=False, error=f"need {K.CORP_FORMATION_COST} cr to incorporate")
    ticker = (action.args.get("ticker") or "").upper().strip()[:3]
    name = action.args.get("name") or f"Corp {ticker}"
    if not ticker or ticker in universe.corporations:
        return ActionResult(ok=False, error="invalid or taken ticker")
    player.credits -= K.CORP_FORMATION_COST
    corp = Corporation(
        ticker=ticker,
        name=name,
        ceo_id=pid,
        member_ids=[pid],
        formed_day=universe.day,
    )
    universe.corporations[ticker] = corp
    player.corp_ticker = ticker
    universe.emit(
        EventKind.CORP_CREATE,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"ticker": ticker, "name": name},
        summary=f"{player.name} incorporated {name} [{ticker}]",
    )
    return ActionResult(ok=True, turns_spent=0)


def _handle_corp_invite(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if player.corp_ticker is None:
        return ActionResult(ok=False, error="not in a corporation")
    corp = universe.corporations[player.corp_ticker]
    if corp.ceo_id != pid:
        return ActionResult(ok=False, error="only CEO may invite")
    target = action.args.get("target")
    if target not in universe.players:
        return ActionResult(ok=False, error="unknown target")
    if target in corp.invited_ids or target in corp.member_ids:
        return ActionResult(ok=False, error="already invited/member")
    corp.invited_ids.append(target)
    # Deliver as inbox message
    universe.players[target].inbox.append({
        "from": pid,
        "kind": "corp_invite",
        "ticker": corp.ticker,
        "message": f"You are invited to join {corp.name} [{corp.ticker}].",
        "day": universe.day,
    })
    universe.emit(
        EventKind.CORP_INVITE,
        actor_id=pid,
        payload={"ticker": corp.ticker, "target": target},
        summary=f"{player.name} invited {universe.players[target].name} to {corp.ticker}",
    )
    return ActionResult(ok=True, turns_spent=0)


def _handle_corp_join(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    ticker = (action.args.get("ticker") or "").upper()
    corp = universe.corporations.get(ticker)
    if corp is None:
        return ActionResult(ok=False, error="no such corporation")
    if pid not in corp.invited_ids:
        return ActionResult(ok=False, error="not invited")
    if len(corp.member_ids) >= universe.config.corp_max_members:
        return ActionResult(ok=False, error="corp is full")
    corp.member_ids.append(pid)
    corp.invited_ids.remove(pid)
    player.corp_ticker = ticker
    universe.emit(
        EventKind.CORP_JOIN,
        actor_id=pid,
        payload={"ticker": ticker},
        summary=f"{player.name} joined {corp.name} [{ticker}]",
    )
    return ActionResult(ok=True, turns_spent=0)


def _handle_corp_leave(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if player.corp_ticker is None:
        return ActionResult(ok=False, error="not in a corp")
    corp = universe.corporations[player.corp_ticker]
    corp.member_ids = [m for m in corp.member_ids if m != pid]
    player.corp_ticker = None
    if not corp.member_ids:
        universe.corporations.pop(corp.ticker, None)
    universe.emit(
        EventKind.CORP_LEAVE,
        actor_id=pid,
        payload={"ticker": corp.ticker},
        summary=f"{player.name} left {corp.ticker}",
    )
    return ActionResult(ok=True, turns_spent=0)


def _handle_hail(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    target_id = action.args.get("target")
    message = action.args.get("message", "")[:1000]
    if target_id not in universe.players:
        return ActionResult(ok=False, error="unknown target")
    universe.players[target_id].inbox.append({
        "from": pid,
        "kind": "hail",
        "message": message,
        "day": universe.day,
        "tick": universe.tick,
    })
    universe.emit(
        EventKind.HAIL,
        actor_id=pid,
        payload={"target": target_id, "message": message},
        summary=f"{player.name} → {universe.players[target_id].name}: {_truncate_for_feed(message, 100)}",
    )
    return ActionResult(ok=True, turns_spent=0)


def _handle_broadcast(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    message = action.args.get("message", "")[:1000]
    for other_id, other in universe.players.items():
        if other_id == pid:
            continue
        other.inbox.append({
            "from": pid,
            "kind": "broadcast",
            "message": message,
            "day": universe.day,
            "tick": universe.tick,
        })
    universe.emit(
        EventKind.BROADCAST,
        actor_id=pid,
        payload={"message": message},
        summary=f"{player.name} (broadcast): {_truncate_for_feed(message, 120)}",
    )
    return ActionResult(ok=True, turns_spent=0)


def _handle_plot_course(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Compute shortest warp path from current sector to target.

    Does NOT move the ship; only writes a `course_plan` to scratchpad-adjacent
    state so the agent can act on it. Movement still uses warp(target=…) one
    sector at a time. (Optional `execute=true` chains warps until turns run out.)
    """
    player = universe.players[pid]
    target = action.args.get("target")
    if target is None:
        return ActionResult(ok=False, error="plot_course requires 'target' sector id")
    try:
        target_id = int(target)
    except (ValueError, TypeError):
        return ActionResult(ok=False, error=f"invalid target {target!r}")
    if target_id == player.sector_id:
        return ActionResult(ok=True, turns_spent=0)

    path = _bfs_path(universe, player.sector_id, target_id, max_depth=K.PLOT_COURSE_MAX_DEPTH * 6)
    if not path:
        universe.emit(
            EventKind.WARP_BLOCKED,
            actor_id=pid,
            sector_id=player.sector_id,
            payload={"target": target_id, "reason": "no_route"},
            summary=f"{player.name}: no route from {player.sector_id} to {target_id}",
        )
        return ActionResult(ok=False, error="no route to target")

    execute = bool(action.args.get("execute", False))
    if not execute:
        universe.emit(
            EventKind.AUTOPILOT,
            actor_id=pid,
            sector_id=player.sector_id,
            payload={"target": target_id, "path": path, "executed": False},
            summary=f"{player.name} plotted course → {target_id} via {len(path)} warps: {path[:5]}{'…' if len(path)>5 else ''}",
        )
        return ActionResult(ok=True, turns_spent=0)

    # Execute: walk path, consuming turns; stop at obstacle/out-of-turns
    turns_spent_total = 0
    hops_done = 0
    for nxt in path:
        sub_action = Action(kind=ActionKind.WARP, args={"target": nxt})
        sub = _handle_warp(universe, pid, sub_action)
        if not sub.ok:
            break
        turns_spent_total += sub.turns_spent
        # apply turn cost incrementally to player so subsequent _handle_warp
        # checks the correct remaining turns (apply_action does this once per
        # call; we're calling _handle_warp directly, so update here).
        player.turns_today += sub.turns_spent
        hops_done += 1
        if not player.alive or universe.players[pid].sector_id != nxt:
            break

    universe.emit(
        EventKind.AUTOPILOT,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"target": target_id, "path": path, "executed": True, "hops_done": hops_done},
        summary=f"{player.name} autopilot — completed {hops_done}/{len(path)} hops toward {target_id}",
    )
    # Roll back the manual increments so the outer apply_action accounting stays sane;
    # we tell apply_action turns_spent=0 and we already updated turns_today directly.
    return ActionResult(ok=True, turns_spent=0)


def _bfs_path(universe: Universe, src: int, dst: int, max_depth: int = 60) -> list[int]:
    """Shortest path (excluding src) from src→dst over directed warps. Empty if no path."""
    if src == dst:
        return []
    visited: dict[int, int | None] = {src: None}
    q: deque[int] = deque([src])
    depth = {src: 0}
    while q:
        cur = q.popleft()
        if depth[cur] >= max_depth:
            continue
        for nxt in universe.sectors[cur].warps:
            if nxt in visited:
                continue
            visited[nxt] = cur
            depth[nxt] = depth[cur] + 1
            if nxt == dst:
                # reconstruct
                path: list[int] = []
                node: int | None = nxt
                while node is not None and node != src:
                    path.append(node)
                    node = visited[node]
                path.reverse()
                return path
            q.append(nxt)
    return []


def _handle_photon_missile(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if player.ship.photon_missiles <= 0:
        return ActionResult(ok=False, error="no photon missiles loaded")
    target_id = action.args.get("target")
    if target_id is None or target_id not in universe.players:
        return ActionResult(ok=False, error="photon needs a player target")
    if _are_allied(universe, pid, target_id):
        return ActionResult(ok=False, error="cannot fire on a corp mate or ally")
    target = universe.players[target_id]
    if target.sector_id != player.sector_id:
        return ActionResult(ok=False, error="target not in this sector")
    if player.sector_id in K.FEDSPACE_SECTORS:
        player.alignment -= 100
        return ActionResult(ok=False, error="FedSpace forbids weapons fire")
    cost = K.TURN_COST["attack"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    player.ship.photon_missiles -= 1
    target.ship.photon_disabled_ticks = K.PHOTON_DURATION_TICKS + 1
    universe.emit(
        EventKind.PHOTON_FIRED,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"target": target_id},
        summary=f"{player.name} launched a PHOTON MISSILE at {target.name}!",
    )
    universe.emit(
        EventKind.PHOTON_HIT,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"target": target_id, "disabled_ticks": target.ship.photon_disabled_ticks},
        summary=f"!!! {target.name}'s fighters scrambled — offline for {target.ship.photon_disabled_ticks} ticks !!!",
    )
    return ActionResult(ok=True, turns_spent=cost)


def _handle_query_limpets(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Read-out of where every limpet you've placed currently is."""
    reports: list[dict] = []
    for _key, lt in universe.limpets.items():
        if lt.owner_id != pid:
            continue
        target = universe.players.get(lt.target_id)
        if target is None:
            continue
        reports.append({
            "target_id": lt.target_id,
            "target_name": target.name,
            "current_sector": target.sector_id,
            "ship_class": target.ship.ship_class.value,
            "placed_sector": lt.placed_sector,
            "placed_day": lt.placed_day,
        })
    universe.emit(
        EventKind.LIMPET_REPORT,
        actor_id=pid,
        payload={"reports": reports},
        summary=f"{universe.players[pid].name} consulted limpet beacons ({len(reports)} active)",
    )
    return ActionResult(ok=True, turns_spent=0)


def _handle_probe(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Ether probe — remote single-sector intel. Consumes one probe, no proximity needed."""
    player = universe.players[pid]
    if player.ship.ether_probes <= 0:
        return ActionResult(ok=False, error="no ether probes loaded")
    target = action.args.get("target")
    if target is None or int(target) not in universe.sectors:
        return ActionResult(ok=False, error="invalid target sector")
    target_id = int(target)
    cost = K.TURN_COST["scan"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    player.ship.ether_probes -= 1
    sector = universe.sectors[target_id]
    intel = {
        "sector_id": target_id,
        "warps_out": list(sector.warps),
        "port_code": sector.port.code if sector.port else None,
        "fighters_owner": sector.fighters.owner_id if sector.fighters else None,
        "fighters_count": sector.fighters.count if sector.fighters else 0,
        "fighters_mode": sector.fighters.mode.value if sector.fighters else None,
        "occupants": list(sector.occupant_ids),
        "planets": [universe.planets[pl].name for pl in sector.planet_ids if pl in universe.planets],
        "mines_total": sum(m.count for m in sector.mines),
        "ferrengi_count": sum(1 for f in universe.ferrengi.values() if f.sector_id == target_id and f.alive),
    }
    player.probe_log[target_id] = {"day": universe.day, "tick": universe.tick, "intel": intel}
    # Probe reveals the target's warps_out → feed the warp graph too, not
    # just the sector set. Otherwise the agent would see the probe intel
    # in the short-lived event feed and lose the topology once it scrolls.
    _learn_sector(player, universe, target_id)
    if sector.port is not None:
        _record_port_intel(player, target_id, sector.port, universe=universe)

    universe.emit(
        EventKind.PROBE,
        actor_id=pid,
        sector_id=target_id,
        payload=intel,
        summary=f"{player.name} probed {target_id}: port={intel['port_code']} occupants={len(intel['occupants'])} fig={intel['fighters_count']}",
    )
    _award_xp(universe, pid, "probe")
    return ActionResult(ok=True, turns_spent=cost)


def _handle_corp_deposit(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if player.corp_ticker is None or player.corp_ticker not in universe.corporations:
        return ActionResult(ok=False, error="not in a corporation")
    qty = int(action.args.get("amount", 0))
    if qty <= 0 or qty > player.credits:
        return ActionResult(ok=False, error="invalid amount")
    corp = universe.corporations[player.corp_ticker]
    player.credits -= qty
    corp.treasury += qty
    universe.emit(
        EventKind.CORP_DEPOSIT,
        actor_id=pid,
        payload={"ticker": corp.ticker, "amount": qty, "new_treasury": corp.treasury},
        summary=f"{player.name} deposited {qty}cr into {corp.ticker} (treasury {corp.treasury}cr)",
    )
    return ActionResult(ok=True, turns_spent=0)


def _handle_corp_withdraw(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if player.corp_ticker is None or player.corp_ticker not in universe.corporations:
        return ActionResult(ok=False, error="not in a corporation")
    corp = universe.corporations[player.corp_ticker]
    if corp.ceo_id != pid:
        return ActionResult(ok=False, error="only CEO may withdraw")
    qty = int(action.args.get("amount", 0))
    if qty <= 0 or qty > corp.treasury:
        return ActionResult(ok=False, error="invalid amount")
    corp.treasury -= qty
    player.credits += qty
    universe.emit(
        EventKind.CORP_WITHDRAW,
        actor_id=pid,
        payload={"ticker": corp.ticker, "amount": qty, "new_treasury": corp.treasury},
        summary=f"{player.name} withdrew {qty}cr from {corp.ticker} (treasury {corp.treasury}cr)",
    )
    return ActionResult(ok=True, turns_spent=0)


def _handle_corp_memo(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if player.corp_ticker is None or player.corp_ticker not in universe.corporations:
        return ActionResult(ok=False, error="not in a corporation")
    corp = universe.corporations[player.corp_ticker]
    msg = (action.args.get("message") or "")[:1000]
    for mid in corp.member_ids:
        if mid == pid:
            continue
        target = universe.players.get(mid)
        if target is None:
            continue
        target.inbox.append({
            "from": pid,
            "kind": "corp_memo",
            "ticker": corp.ticker,
            "message": msg,
            "day": universe.day,
            "tick": universe.tick,
        })
    universe.emit(
        EventKind.CORP_MEMO,
        actor_id=pid,
        payload={"ticker": corp.ticker, "message": msg},
        summary=f"{player.name} → [{corp.ticker} memo]: {_truncate_for_feed(msg, 100)}",
    )
    return ActionResult(ok=True, turns_spent=0)


def _handle_propose_alliance(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    target_id = action.args.get("target")
    if target_id not in universe.players or target_id == pid:
        return ActionResult(ok=False, error="invalid target")
    target = universe.players[target_id]
    # Skip if any existing active alliance already covers this pair
    for ally in universe.alliances.values():
        if ally.active and pid in ally.member_ids and target_id in ally.member_ids:
            return ActionResult(ok=False, error="alliance already exists with this player")
    aid = f"A{universe.next_alliance_id}"
    universe.next_alliance_id += 1
    universe.alliances[aid] = Alliance(
        id=aid,
        member_ids=[pid, target_id],
        proposed_by=pid,
        formed_day=universe.day,
        active=False,
    )
    target.inbox.append({
        "from": pid,
        "kind": "alliance_proposal",
        "alliance_id": aid,
        "message": (action.args.get("terms") or f"{player.name} proposes a non-aggression pact."),
        "day": universe.day,
        "tick": universe.tick,
    })
    universe.emit(
        EventKind.ALLIANCE_PROPOSED,
        actor_id=pid,
        payload={"alliance_id": aid, "target": target_id},
        summary=f"{player.name} proposed alliance [{aid}] with {target.name}",
    )
    return ActionResult(ok=True, turns_spent=0)


def _handle_accept_alliance(universe: Universe, pid: str, action: Action) -> ActionResult:
    aid = action.args.get("alliance_id")
    ally = universe.alliances.get(aid) if aid else None
    if ally is None:
        return ActionResult(ok=False, error="unknown alliance id")
    if pid not in ally.member_ids:
        return ActionResult(ok=False, error="not a member of this alliance proposal")
    if ally.active:
        return ActionResult(ok=False, error="alliance already active")
    if ally.proposed_by == pid:
        return ActionResult(ok=False, error="proposer cannot accept own proposal")
    ally.active = True
    for mid in ally.member_ids:
        p = universe.players.get(mid)
        if p is not None and ally.id not in p.alliances:
            p.alliances.append(ally.id)
    names = " + ".join(universe.players[m].name for m in ally.member_ids if m in universe.players)
    universe.emit(
        EventKind.ALLIANCE_FORMED,
        actor_id=pid,
        payload={"alliance_id": ally.id, "members": ally.member_ids},
        summary=f"=== ALLIANCE FORMED [{ally.id}]: {names} ===",
    )
    for mid in ally.member_ids:
        _award_xp(universe, mid, "alliance")
    return ActionResult(ok=True, turns_spent=0)


def _handle_break_alliance(universe: Universe, pid: str, action: Action) -> ActionResult:
    aid = action.args.get("alliance_id")
    ally = universe.alliances.get(aid) if aid else None
    if ally is None or pid not in ally.member_ids:
        return ActionResult(ok=False, error="not in that alliance")
    ally.active = False
    for mid in ally.member_ids:
        p = universe.players.get(mid)
        if p is not None and ally.id in p.alliances:
            p.alliances.remove(ally.id)
    breaker = universe.players[pid].name
    universe.emit(
        EventKind.ALLIANCE_BROKEN,
        actor_id=pid,
        payload={"alliance_id": ally.id, "breaker": pid},
        summary=f"!!! ALLIANCE [{ally.id}] BROKEN by {breaker} — {ally.member_ids} now hostile !!!",
    )
    return ActionResult(ok=True, turns_spent=0)


_DISPATCH: dict[ActionKind, Callable] = {
    ActionKind.WARP: _handle_warp,
    ActionKind.TRADE: _handle_trade,
    ActionKind.SCAN: _handle_scan,
    ActionKind.DEPLOY_FIGHTERS: _handle_deploy_fighters,
    ActionKind.DEPLOY_MINES: _handle_deploy_mines,
    ActionKind.ATTACK: _handle_attack,
    ActionKind.LAND_PLANET: _handle_land_planet,
    ActionKind.LIFTOFF: _handle_liftoff,
    ActionKind.ASSIGN_COLONISTS: _handle_assign_colonists,
    ActionKind.BUILD_CITADEL: _handle_build_citadel,
    ActionKind.DEPLOY_GENESIS: _handle_deploy_genesis,
    ActionKind.PLOT_COURSE: _handle_plot_course,
    ActionKind.PHOTON_MISSILE: _handle_photon_missile,
    ActionKind.QUERY_LIMPETS: _handle_query_limpets,
    ActionKind.PROBE: _handle_probe,
    ActionKind.BUY_SHIP: _handle_buy_ship,
    ActionKind.BUY_EQUIP: _handle_buy_equip,
    ActionKind.CORP_CREATE: _handle_corp_create,
    ActionKind.CORP_INVITE: _handle_corp_invite,
    ActionKind.CORP_JOIN: _handle_corp_join,
    ActionKind.CORP_LEAVE: _handle_corp_leave,
    ActionKind.CORP_DEPOSIT: _handle_corp_deposit,
    ActionKind.CORP_WITHDRAW: _handle_corp_withdraw,
    ActionKind.CORP_MEMO: _handle_corp_memo,
    ActionKind.PROPOSE_ALLIANCE: _handle_propose_alliance,
    ActionKind.ACCEPT_ALLIANCE: _handle_accept_alliance,
    ActionKind.BREAK_ALLIANCE: _handle_break_alliance,
    ActionKind.HAIL: _handle_hail,
    ActionKind.BROADCAST: _handle_broadcast,
    ActionKind.WAIT: _handle_wait,
}


# ---------------------------------------------------------------------------
# Intel / observation helpers
# ---------------------------------------------------------------------------


def _record_port_intel(player, sector_id: int, port, *, universe=None) -> None:
    """Persist a per-port intel snapshot the player's observation will show next
    turn. We include live buy/sell prices so the LLM can compare ports across
    sectors without re-visiting — this is the mechanic that lets it plan
    trade routes like `buy fuel_ore@13 at s46, sell@22 at s44, profit=9/unit`.

    `last_seen_day` is stamped from `universe.day` when available so the
    observation can show staleness ("intel is 2 days old") — critical
    because ports regenerate / drain between visits and a 3-day-old
    stock snapshot is often misleading. Falls back to preserving the
    existing value when no universe is passed (a few legacy callers).
    """
    from .economy import port_buy_price, port_sell_price

    stock: dict[str, dict[str, int | str]] = {}
    for c, s in port.stock.items():
        entry: dict[str, int | str] = {
            "current": s.current,
            "max": s.maximum,
        }
        if port.buys(c):
            entry["price"] = port_buy_price(port, c)
            entry["side"] = "buys_from_player"
        elif port.sells(c):
            entry["price"] = port_sell_price(port, c)
            entry["side"] = "sells_to_player"
        stock[c.value] = entry
    # Prefer live universe.day, fall back to whatever was last recorded
    # (so a callsite that forgot to pass universe doesn't wipe freshness).
    last_day = (
        getattr(universe, "day", None)
        if universe is not None
        else (player.known_ports.get(sector_id) or {}).get("last_seen_day")
    )
    snapshot = {
        "class": port.class_id.code,
        "stock": stock,
        "last_seen_day": last_day,
    }
    player.known_ports[sector_id] = snapshot

