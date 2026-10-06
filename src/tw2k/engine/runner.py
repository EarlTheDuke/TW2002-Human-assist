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
from .class0 import handle_terra_colonists
from .combat import (
    _apply_volley,
    _are_allied,
    _attach_limpet,
    _destroy_ship,
    _resolve_fighter_attack_tw2002,
    _resolve_fighter_sector_combat,
    _resolve_ship_attack_tw2002,
    _resolve_ship_combat,
    attack_cap,
    live_challenge,
    open_challenge,
    retreat_block,
)
from .economy import (
    _stored_mcic,
    begin_port_visit,
    execute_trade,
    port_buy_price,
    port_sell_price,
    regenerate_ports,
    trade_turn_cost,
)
from .ferrengi import (
    _ferrengi_by_name,
    _ferrengi_regen,
    _ferrengi_roam_and_hunt,
    _spawn_ferrengi,
    apply_ferrengi_tribute,
    clear_ferrengi_encounter,
    live_ferrengi_encounter,
)
from .hardware import (
    add_navhaz,
    apply_carried_photon_blast,
    apply_navhaz,
    armid_detonation_hits,
    carried_photon_hazard,
    colonists_on,
    detonator_reason,
    drop_other_limpets,
    emit_psychic_probe,
    handle_cloak,
    handle_fire_disruptor,
    handle_launch_beacon,
    handle_photon_tw2002,
    handle_remove_limpet,
    hostile_mines_present,
    sector_photon_active,
    tick_cloak_fails,
    tick_navhaz,
    tick_photon_waves,
    v2_add,
    v2_have,
)
from .legality import planet_destroy_reason
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
from .planets import _accrue_planet_treasury, _advance_planets, _complete_citadels, _pay_planet_value_tax
from .rob_steal import clear_all_busts, handle_rob, handle_steal
from .victory import (
    _award_xp,
    _check_victory,
    _corp_treasury_share,
    _planet_asset_value,
    alignment_label,
    check_victory,
    fedspace_protects,
    full_net_worth,
    planet_tax_value,
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
    "_apply_volley",
    # Re-exported ferrengi
    "_ferrengi_by_name",
    "_ferrengi_roam_and_hunt",
    "_spawn_ferrengi",
    # Re-exported planet tick helpers
    "_advance_planets",
    "_complete_citadels",
    "_pay_planet_value_tax",
    # Re-exported victory / progression
    "_award_xp",
    "_check_victory",
    "_corp_treasury_share",
    "_planet_asset_value",
    "alignment_label",
    "check_victory",
    "full_net_worth",
    "planet_tax_value",
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

    # Always log the thought; never validate.
    # Feed-summary cap is intentionally generous for thoughts (500 chars
    # vs. the 140-char default for trade/combat/etc.) so spectators
    # actually see the reasoning instead of "...in adjac…". Full text
    # is always available in payload.thought (cap 2000).
    if action.thought:
        universe.emit(
            EventKind.AGENT_THOUGHT,
            actor_id=player_id,
            sector_id=player.sector_id,
            payload={"thought": action.thought[:2000]},
            summary=_truncate_for_feed(action.thought, limit=500),
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
    if action.kind == ActionKind.DEPLOY_ATOMIC and not K.hardware_tw2002():
        handler = None  # HARDWARE_MODE legacy: deploy_atomic was never a dispatched verb
    if handler is None:
        return ActionResult(ok=False, error=f"unsupported action {action.kind}")

    # An open fighter challenge takes an answer before anything else (SHIP_COMBAT.md).
    if K.challenge_on() and live_challenge(universe, player_id, settle=True) is not None:
        if action.kind not in CHALLENGE_VERBS:
            return _reject_free(CHALLENGE_REFUSAL)

    # ferrengi-aliens-v1: open tribute encounter (Flee / Attack / Surrender).
    # Any other action ignores the hail: the Ferrengi take tribute first, then it runs.
    ferr_enc = live_ferrengi_encounter(universe, player_id, settle=True)
    if ferr_enc is not None and action.kind == ActionKind.SHIP_TRANSPORT and K.fleet_on():
        return _reject_free("answer the Ferrengi first")  # SHIP_FLEET.md fl16
    if ferr_enc is not None and not _answers_ferrengi(action, ferr_enc):
        apply_ferrengi_tribute(universe, player_id, ignored=True)

    before_seq = universe.seq
    turns_before = player.turns_today
    tow_snap = None
    if K.tow_on():  # SHIP_TOW.md tt11 / tt12: locks before the action, break rules after it
        from .tow import snapshot as tow_snapshot
        tow_snap = tow_snapshot(universe)
    dividend_before = None
    if action.kind in DIVIDEND_TRANSFER_VERBS and K.dividend_transfers_neutral():
        dividend_before = _dividend_snapshot(universe, player)
    result = handler(universe, player_id, action)
    if dividend_before:
        _shift_dividend_baseline(universe, dividend_before)
    if tow_snap:
        from .tow import after_action as tow_after_action
        tow_after_action(universe, player_id, action, result, tow_snap)
    if K.fed_tw2002():
        # FEDSPACE_POLICE.md f23: warn the ISS pilot when the action that made him evil ends,
        # not on the warp that already costs the ship (twgs repossesses on that same move).
        from .fed import maybe_fed_hail
        maybe_fed_hail(universe, player_id)
    result.event_seqs = _seqs_after(universe.events, before_seq)

    # Count turns. A repelled planet landing stays ok=False so callers
    # still see that the ship did not land, but the fight spent the turn.
    # A haggle past the hidden limit also spends its turn, and does not trade.
    charged_fail = (not result.ok) and result.error in {
        "planetary defenses repelled landing",
        "interdicted by a planet",
        "the port lost patience",
        "We're not interested.",  # PLANETARY_TRADING.md pt12: a refused counter still spends the visit turn
    }
    if result.turns_spent > 0 and (result.ok or charged_fail):
        player.turns_today += result.turns_spent
    # Ship Destroyed already spent the day (DEATH_ESCAPE_PODS.md d9); do not run past it.
    if K.death_tw2002() and player.turns_today > player.turns_per_day:
        player.turns_today = player.turns_per_day

    # Flee penalty: the first turn-using action after a flee settles it. Land or port pays extra.
    if player.flee_penalty and player.turns_today > turns_before:
        if action.kind in (ActionKind.LAND_PLANET, ActionKind.TRADE, ActionKind.PLANET_TRADE):
            extra = min(K.FLEE_PENALTY_TURNS, max(0, player.turns_per_day - player.turns_today))
            player.turns_today += extra
            result.turns_spent += extra
        player.flee_penalty = False

    # Check victory after every applied action
    _check_victory(universe)

    return result


def _seqs_after(events: list, before_seq: int) -> list[int]:
    """Seqs of the events emitted after `before_seq`, oldest first.

    Universe.emit is the only writer of the feed and numbers events in append
    order, so they are the tail: walk back from the end instead of scanning a
    whole match's history on every action (SOAK_30DAY_V1.md).
    """
    i = len(events)
    while i and events[i - 1].seq > before_seq:
        i -= 1
    return [e.seq for e in events[i:]]


def tick_day(universe: Universe) -> None:
    """Advance the game by one day: reset turns, regenerate ports, spawn Ferrengi, grow planets."""
    _overnight_retreats(universe)
    _overnight_ferrengi_encounters(universe)
    if K.tow_on():  # SHIP_TOW.md tt11j: an overnight retreat / flee drops the tow
        from .tow import sweep as tow_sweep
        tow_sweep(universe, "retreat")
    universe.day += 1
    for player in universe.players.values():
        player.turns_today = 0
        if K.rank_tw2002() and player.alive:
            # x3: the first login after midnight, +1 experience and +1 alignment.
            player.experience = int(player.experience) + K.xp_award("daily")
            player.alignment = int(player.alignment) + K.DAILY_ALIGNMENT
        player.photon_damped_sector_id = None
        # Photon scramble decays one tick per real game day
        if player.ship.photon_disabled_ticks > 0:
            player.ship.photon_disabled_ticks = max(0, player.ship.photon_disabled_ticks - 1)

    # CLASS0_TERRA.md t20/t3: Extern sweep (after overnight retreats so a
    # challenge answered overnight still sees the fighters), then Terra regen.
    # Both run before regenerate_ports.
    from .class0 import class0_tw2002, extern_sweep, regen_terra
    if class0_tw2002():
        extern_sweep(universe)
        regen_terra(universe)

    # fedspace-police-v1: tows after MSL sweep, then Fed wander (f5/f11-f14)
    from .fed import fed_tw2002, run_tows, tick_federals
    if K.fleet_on():  # SHIP_FLEET.md fl23: Extern repossesses unmanned ships in FedSpace (before tows)
        from .fleet import extern_repossess
        extern_repossess(universe)
    if fed_tw2002():
        run_tows(universe)
        if K.tow_on():  # tt23: a Fed tow of the tower releases its lock; the held ship stays
            from .tow import sweep as tow_sweep
            tow_sweep(universe, "fed_tow")
        tick_federals(universe)

    regenerate_ports(universe)
    if K.rob_tw2002():
        clear_all_busts(universe)
    if K.hardware_tw2002():
        tick_photon_waves(universe)
        tick_cloak_fails(universe, _rng_for(universe))
        tick_navhaz(universe)

    if universe.config.enable_ferrengi:
        _ferrengi_regen(universe)
        _spawn_ferrengi(universe)
        _ferrengi_roam_and_hunt(universe)
    if universe.config.enable_planets:
        _advance_planets(universe)
        _complete_citadels(universe)
        _pay_planet_value_tax(universe)
        _accrue_planet_treasury(universe)

    universe.emit(
        EventKind.DAY_TICK,
        payload={"day": universe.day},
        summary=f"-- Day {universe.day} dawns --",
    )
    _check_victory(universe)


def _overnight_retreats(universe: Universe) -> None:
    """Fighters stop a ship "entering or remaining in" their sector (SHIP_COMBAT.md).

    A challenge still open when the day ends (the seat only waited) ends in a free retreat to
    the sector the ship came from, so waiting never keeps a ship in a held sector past the day.
    A ship that may not retreat (one-way lane, interdictor) stays held and must still answer.
    """
    if not K.challenge_on():
        return
    for pid in sorted(universe.players):
        player = universe.players[pid]
        if not player.fighter_challenge:
            continue
        ch = live_challenge(universe, pid, settle=True)
        if ch is None or retreat_block(universe, pid) is not None:
            continue
        _retreat_move(universe, player, int(ch["from_sector"]), overnight=True)


def _overnight_ferrengi_encounters(universe: Universe) -> None:
    """Clear open Ferrengi boarding at day end so idle seats cannot stall forever.

    Prefer flee to any neighbour; if none, auto-tribute (ship lives).
    """
    if not K.ferrengi_tw2002() or K.FERRENGI_ENCOUNTER != "tribute":
        return
    for pid in sorted(universe.players):
        enc = live_ferrengi_encounter(universe, pid, settle=True)
        if enc is None:
            continue
        player = universe.players[pid]
        sector = universe.sectors.get(player.sector_id)
        choices: list[int] = []
        if sector is not None:
            choices = [w for w in sector.warps if w not in K.FEDSPACE_SECTORS] or list(sector.warps)
        if choices:
            clear_ferrengi_encounter(universe, pid)
            _retreat_move(universe, player, int(choices[0]), overnight=True)
            player.flee_penalty = True
        else:
            apply_ferrengi_tribute(universe, pid)


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


CHALLENGE_VERBS = frozenset({
    ActionKind.ATTACK, ActionKind.RETREAT, ActionKind.SURRENDER, ActionKind.PAY_TOLL,
    ActionKind.HAIL, ActionKind.BROADCAST, ActionKind.QUERY_LIMPETS,
    # WAIT passes a turn and answers nothing; it keeps auto-WAIT seats (idle, timeout) from stalling a day.
    ActionKind.WAIT,
})
CHALLENGE_REFUSAL = "answer the fighters first: attack, retreat, pay the toll or surrender"

# PLANET_DIVIDEND_MODE tw2002: ship<->planet transfers move the dividend baseline (FULLGAME_FIXES_V2.md).
DIVIDEND_TRANSFER_VERBS = frozenset({
    ActionKind.LOAD_PLANET_CARGO, ActionKind.DUMP_PLANET_CARGO, ActionKind.ASSIGN_COLONISTS,
    ActionKind.DEPOSIT_TREASURY, ActionKind.WITHDRAW_TREASURY,
    ActionKind.DEPOSIT_PLANET_DEFENSE, ActionKind.WITHDRAW_PLANET_DEFENSE,
})


def _dividend_snapshot(universe: Universe, player) -> dict[int, int]:
    """Dividend value of every planet in the player's sector, before a transfer verb runs."""
    sector = universe.sectors.get(player.sector_id)
    if sector is None:
        return {}
    return {
        pid_: planet_tax_value(universe.planets[pid_])
        for pid_ in sector.planet_ids
        if pid_ in universe.planets
    }


def _shift_dividend_baseline(universe: Universe, before: dict[int, int]) -> None:
    """Move each planet's baseline by what the transfer moved, so it never counts as growth."""
    for pid_, value in before.items():
        planet = universe.planets.get(pid_)
        if planet is None:
            continue
        delta = planet_tax_value(planet) - value
        if delta:
            planet.last_tax_value = int(planet.last_tax_value or 0) + delta


FERRENGI_ENCOUNTER_VERBS = frozenset({
    ActionKind.ATTACK, ActionKind.RETREAT, ActionKind.SURRENDER,
    ActionKind.HAIL, ActionKind.BROADCAST,
})
FERRENGI_ENCOUNTER_NOTE = "ignoring the Ferrengi pays tribute first (all cargo and some holds, or credits)"


def _answers_ferrengi(action: Action, enc: dict) -> bool:
    """Attack on the boarding Ferrengi, retreat, surrender, or free comms."""
    if action.kind == ActionKind.ATTACK:
        return str((action.args or {}).get("target")) == str(enc.get("ferr_id"))
    return action.kind in FERRENGI_ENCOUNTER_VERBS


def _reject_free(error: str) -> ActionResult:
    """Reject an action on a precondition without consuming turns.

    Audit result for Match 13: existing handlers already return
    `turns_spent=0` (the default) on precondition-fail paths — only
    trade-haggle-rejected (line 405) and planet-defense-repelled (line
    795) charge turns on failure, and both are correct because real
    game work was resolved there. This helper codifies the free-reject
    pattern for the new `claim_planet` handler and any future addition,
    so the convention is explicit instead of implicit. It also makes
    the intent greppable for later auditing (`_reject_free`).
    """
    return ActionResult(ok=False, error=error, turns_spent=0)


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
    spec = K.hull_spec(player.ship.ship_class.value)
    if spec and "turns_per_warp" in spec:
        return int(spec["turns_per_warp"])
    return K.TURN_COST["warp"]


def _hostile_toll(universe: Universe, pid: str, sector):
    """Hostile toll deployment in this sector, or None."""
    dep = sector.fighters
    if dep is None or dep.mode != FighterMode.TOLL:
        return None
    if dep.owner_id == pid or _are_allied(universe, pid, dep.owner_id):
        return None
    return dep


def _toll_blocks(universe: Universe, pid: str, sector) -> bool:
    """True when tw2002 toll fighters are here and the ship cannot pay the whole bill."""
    if not K.sector_fighter_tw2002() or K.challenge_on():
        return False
    dep = _hostile_toll(universe, pid, sector)
    if dep is None:
        return False
    bill = int(dep.count) * K.SECTOR_TOLL_CREDITS_PER_FIGHTER
    return bill > 0 and universe.players[pid].credits < bill


def _apply_sector_hazards(universe: Universe, pid: str, sector, *, entry_verb: str = "entering") -> int:
    """Mines, then the other side's sector fighters. Same math as a warp entry.

    Returns the armid damage dealt. A mine kill ejects through `_destroy_ship`.
    Offensive fighters clash. Toll fighters charge. Defensive fighters do not
    attack, matching warp. Own, corp, and alliance hazards are skipped.
    `entry_verb` is "entering" on a warp and "landing" on a hostile landing.
    """
    player = universe.players[pid]
    rng = _rng_for(universe)
    damage = 0
    # HARDWARE_MODE tw2002 entry order (SHIP_HARDWARE_V2.md v26): NavHaz, one limpet,
    # armids, sector quasar, fighters. Legacy keeps list-order mines then fighters.
    entry_order = K.hardware_tw2002()
    entering = entry_verb == "entering"
    deaths_before = player.deaths
    if entry_order and entering:
        apply_navhaz(universe, pid, sector, rng)
        if player.deaths != deaths_before or not player.alive:
            return 0
    mines = list(sector.mines)
    if entry_order:
        mines.sort(key=lambda m: 0 if m.kind == MineType.LIMPET else 1)
    limpet_taken = False
    for md in mines:
        if md.owner_id == pid:
            continue
        # Corp mate / ally mines don't trigger
        if _are_allied(universe, pid, md.owner_id):
            continue
        if md.kind == MineType.ARMID:
            if sector_photon_active(sector):
                continue  # h7: photon wave neutralizes mines
            hits, dmg_each = armid_detonation_hits(md.count, rng)
            if hits <= 0:
                continue
            dmg = hits * dmg_each
            damage += dmg
            md.count -= hits
            if md.count <= 0:
                sector.mines.remove(md)
            universe.emit(
                EventKind.MINE_DETONATED,
                actor_id=md.owner_id,
                sector_id=sector.id,
                payload={"hits": hits, "damage": dmg, "victim": pid, "per_mine": dmg_each},
                summary=f"{hits} armid mines hit {player.name} {entry_verb} {sector.id} ({dmg} dmg)",
            )
        elif md.kind == MineType.LIMPET:
            if sector_photon_active(sector):
                continue  # h7: photon wave neutralizes limpets too
            if entry_order:
                if limpet_taken:
                    continue  # v27: one limpet per entry
                limpet_taken = True
                drop_other_limpets(universe, pid)  # any earlier limpet falls off
            # Silently attach 1 limpet tracker; consume one mine.
            md.count -= 1
            if md.count <= 0:
                sector.mines.remove(md)
            _attach_limpet(universe, md.owner_id, pid)

    if damage > 0:
        shields_before = player.ship.shields
        player.ship.shields = max(0, player.ship.shields - damage)
        # MINE_OVERFLOW_MODE (FULLGAME_FIXES_V2.md): only the damage the shields did not absorb.
        overflow = damage - (shields_before if K.mine_overflow_fixed() else player.ship.shields)
        if player.ship.shields == 0 and overflow > 0:
            player.ship.fighters = max(0, player.ship.fighters - overflow)

    if player.ship.fighters == 0 and damage > 0:
        # Ship destroyed on entry; player ejected and respawns at StarDock
        _destroy_ship(universe, pid, reason="mines")

    if entry_order:
        if player.deaths != deaths_before or not player.alive:
            return damage
        if entering:
            _apply_sector_quasar(universe, pid, sector)  # v26: quasar before the fighters
            if player.deaths != deaths_before or not player.alive:
                return damage

    # Hostile sector fighter check
    if sector.fighters and sector.fighters.owner_id != pid:
        f_mode = sector.fighters.mode
        owner = universe.players.get(sector.fighters.owner_id)
        allied = owner is not None and _are_allied(universe, pid, owner.id)
        if not allied:
            if sector_photon_active(sector):
                pass  # h7: photon wave neutralizes sector fighters
            elif f_mode == FighterMode.OFFENSIVE:
                # Auto-attack
                _resolve_fighter_sector_combat(universe, pid, sector.id)
            elif f_mode == FighterMode.TOLL:
                if K.challenge_on():
                    # The toll is answered at the challenge (pay_toll), not billed on entry.
                    pass
                elif K.sector_fighter_tw2002():
                    bill = int(sector.fighters.count) * K.SECTOR_TOLL_CREDITS_PER_FIGHTER
                    if bill > 0 and player.credits >= bill:
                        player.credits -= bill
                        sector.fighters.toll_credits = int(sector.fighters.toll_credits) + bill
                        universe.emit(
                            EventKind.TRADE,
                            actor_id=pid,
                            sector_id=sector.id,
                            payload={"toll_to": sector.fighters.owner_id, "amount": bill},
                            summary=f"{player.name} paid {bill} cr toll to pass through {sector.id}",
                        )
                else:
                    toll = sector.fighters.count  # 1 cr / fighter simplified = high disincentive
                    toll = min(player.credits, max(10, min(10000, sector.fighters.count)))
                    player.credits -= toll
                    if owner is not None:
                        owner.credits += toll
                    universe.emit(
                        EventKind.TRADE,
                        actor_id=pid,
                        sector_id=sector.id,
                        payload={"toll_to": sector.fighters.owner_id, "amount": toll},
                        summary=f"{player.name} paid {toll} cr toll to pass through {sector.id}",
                    )
    return damage


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
    if K.tow_on():  # SHIP_TOW.md tt6: tower TPW + 2 x towed TPW while a tow is engaged
        from .tow import move_cost as tow_move_cost
        cost = tow_move_cost(universe, player)
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns for this day")

    dest = universe.sectors[target_id]
    held = _try_interdict(universe, pid, cur)
    if held is not None:
        return held
    if _toll_blocks(universe, pid, dest):
        return ActionResult(ok=False, error="toll fighters demand payment")
    tow_ctx = None
    if K.tow_on():  # tt7 / tt11h: a manned towee in FedSpace is released before the tower moves
        from .tow import begin_move as tow_begin_move
        tow_ctx = tow_begin_move(universe, pid)
    if player.photon_damped_sector_id == player.sector_id and target_id != player.sector_id:
        _clear_photon_damp(player, player.sector_id)
    deaths_before = player.deaths
    # A manual warp makes the sector left the previous sector (DEATH_ESCAPE_PODS.md d6).
    # Set before the hazards: a ship that dies entering never left.
    player.prev_sector_id = cur.id
    if K.hardware_tw2002() and carried_photon_hazard(universe, pid, dest):
        apply_carried_photon_blast(universe, pid)
    mined = K.hardware_tw2002() and not sector_photon_active(dest) and hostile_mines_present(universe, pid, dest)
    damage = _apply_sector_hazards(universe, pid, dest)

    # If destroyed by fighters, handler already ejected player
    if not player.alive or (player.sector_id == K.STARDOCK_SECTOR and damage > 0):
        # Leave as-is after destruction
        pass

    # A tw2002 loss on entry leaves the pilot where the pod went (legacy moves on, as before).
    died_entering = K.death_tw2002() and player.deaths != deaths_before
    if player.alive and not died_entering:
        player.arrived_by_transwarp = False
        player.arrived_by_transport = False
        # Leave old sector
        try:
            universe.sectors[player.sector_id].occupant_ids.remove(pid)
        except ValueError:
            pass
        player.sector_id = target_id
        player.end_port_visit()
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
        if tow_ctx is not None:  # tt7: the towee arrives only after the tower is safely in
            from .tow import finish_move as tow_finish_move
            tow_finish_move(universe, pid, tow_ctx, cur.id, target_id, "warp")
            tow_ctx = None
        if not K.hardware_tw2002() and player.deaths == deaths_before and player.sector_id == target_id:
            _apply_sector_quasar(universe, pid, dest)
        if player.alive and player.deaths == deaths_before and player.sector_id == target_id:
            open_challenge(universe, pid, dest, cur.id)
        if mined and player.alive and player.deaths == deaths_before and player.sector_id == target_id:
            # v28: "you will be asked whether you want to avoid the sector" - back at the prompt.
            universe.emit(
                EventKind.HAZARD_AVOID_PROMPT,
                actor_id=pid,
                sector_id=target_id,
                payload={"sector": target_id, "reason": "mines"},
                summary=f"Mines in sector {target_id}: avoid this sector? (autopilot stops here)",
            )

    if tow_ctx is not None:  # tt9: the tower died entering; the towee stays behind
        from .tow import finish_move as tow_finish_move
        tow_finish_move(universe, pid, tow_ctx, cur.id, target_id, "warp")

    # fedspace-police-v1 f6/f22: evil ISS after move
    if player.alive:
        from .fed import check_iss_repo_on_move
        check_iss_repo_on_move(universe, pid)

    return ActionResult(ok=True, turns_spent=cost)


def _handle_trade(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    if sector.port is None or sector.port.class_id == PortClass.STARDOCK:
        return ActionResult(ok=False, error="no trading port in this sector")
    port = sector.port
    if K.rob_tw2002() and getattr(port, "bust_player_id", None) == pid:
        return ActionResult(ok=False, error="you are busted at this port until it clears")

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

    cost = trade_turn_cost(player)
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns for this day")

    rng = _rng_for(universe)
    unused_port = not port.experience  # x2: nobody has traded here yet
    psychic = K.hardware_tw2002() and int(getattr(player.ship, "psychic_probe", 0) or 0) > 0
    if psychic:
        xp_now = int(player.experience)
        listed_now = (port_sell_price(port, commodity, xp_now) if side == "buy"
                      else port_buy_price(port, commodity, xp_now))
        mcic_now = _stored_mcic(port, commodity)
    ok, total, unit, msg, realized = execute_trade(
        universe, player, port, commodity, qty, side, offered, rng
    )
    if ok and unused_port:
        _award_xp(universe, pid, "first_dock")

    if not ok:
        universe.emit(
            EventKind.TRADE_FAILED,
            actor_id=pid,
            sector_id=sector.id,
            payload={"commodity": commodity.value, "qty": qty, "side": side, "reason": msg},
            summary=f"{player.name} trade failed: {msg}",
        )
        return ActionResult(ok=False, error=msg, turns_spent=K.PORT_HAGGLE_FAIL_TURNS if msg == "the port lost patience" else cost)

    _record_port_intel(player, sector.id, port, universe=universe)
    begin_port_visit(player)
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
    if psychic:
        # v11: after the trade, the probe tells you how close you came (actor-only event).
        emit_psychic_probe(universe, pid, commodity.value, side, listed_now, unit, mcic_now)
    _award_xp(universe, pid, "trade")
    return ActionResult(ok=True, turns_spent=cost)


def _handle_scan(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Tiered scan.

    args:
      tier: 'basic' (default — 1-hop with port codes & fighter counts),
            'density' (2-hop, just sector occupant/port presence — no detailed prices),
            'holo'    (1-hop full intel including stock levels)
    """
    if K.info_tw2002():  # SCANNERS_HIDDEN_INFO.md: bought density / holo scanners only
        from .scanners import handle_scan

        return handle_scan(universe, pid, action)
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
                            port_buy_price(w.port, c, player.experience) if w.port.buys(c)
                            else port_sell_price(w.port, c, player.experience)
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

    if K.sector_fighter_tw2002() and (sector.fighters is None or sector.fighters.owner_id == pid):
        cap = K.SECTOR_FIGHTER_CAP_WITH_PLANET if sector.planet_ids else K.SECTOR_FIGHTER_CAP
        have = int(sector.fighters.count) if sector.fighters is not None else 0
        if have + qty > cap:
            return ActionResult(ok=False, error="sector fighter cap")

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
    if kind == MineType.ATOMIC and not K.atomic_mines_sold():
        return ActionResult(ok=False, error="atomic mines are retired (ATOMIC_MINES_PORT_NUKE off)")
    if qty <= 0 or qty > player.ship.mines.get(kind, 0):
        return ActionResult(ok=False, error="insufficient mines")
    if sector.id in K.FEDSPACE_SECTORS:
        return ActionResult(ok=False, error="cannot deploy mines in FedSpace")

    cost = K.TURN_COST["deploy_mines"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")

    if kind != MineType.ATOMIC and K.sector_fighter_tw2002():
        sitting = sum(int(m.count) for m in sector.mines)
        if sitting + qty > K.SECTOR_MINE_CAP:
            return ActionResult(ok=False, error="sector mine cap")

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
    player.alignment -= 50 * qty  # major alignment hit per warhead (a7)

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
            # Destroying toll fighters pays the pot to the detonator, same as combat.
            if K.sector_fighter_tw2002():
                pot = int(sector.fighters.toll_credits or 0)
                if pot > 0:
                    player.credits += pot
            sector.fighters = None

    if port_destroyed:
        _award_xp(universe, pid, "destroy_port")  # x11
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
    if K.challenge_on() and live_challenge(universe, pid) is not None:
        if target_id != "fighters":
            return _reject_free(CHALLENGE_REFUSAL)
        return _attack_sector_fighters(universe, pid, action)
    # fedspace-police-v1 f7: Federal targets use fed:<name>
    from .fed import fed_tw2002 as _fed_tw
    if _fed_tw() and str(target_id).startswith("fed:"):
        from .fed import attack_federal
        return attack_federal(universe, pid, str(target_id).split(":", 1)[1], action.args)
    if K.fleet_on() and str(target_id).startswith("ship:"):  # SHIP_FLEET.md fl24: unmanned ships
        from .fleet import attack_unmanned
        return attack_unmanned(universe, pid, str(target_id), action)
    target = universe.players.get(target_id) or _ferrengi_by_name(universe, str(target_id))
    if target is None:
        return ActionResult(ok=False, error=f"target {target_id} not found")
    if (
        K.hardware_tw2002()
        and target_id in universe.players
        and getattr(universe.players[target_id].ship, "cloaked", False)
    ):
        return ActionResult(ok=False, error="target is cloaked")
    if getattr(target, "sector_id", -1) != player.sector_id:
        return ActionResult(ok=False, error="target not in this sector")
    # Block friendly fire (corp mates + active alliances)
    if isinstance(target_id, str) and target_id in universe.players and _are_allied(universe, pid, target_id):
        return ActionResult(ok=False, error="cannot attack a corp mate or ally")
            # fedspace-police-v1 f8: FedSpace protect (Zyrain under tw2002; legacy path unchanged)
    if player.sector_id in K.FEDSPACE_SECTORS and fedspace_protects(target):
        from .fed import fed_tw2002, protect_fedspace_attack
        if fed_tw2002():
            return protect_fedspace_attack(universe, pid, target)
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

    if K.combat_tw2002():
        qty, bad = _attack_qty(player, action)
        if bad is not None:
            return bad
        _resolve_ship_attack_tw2002(universe, pid, target, qty)
        clear_ferrengi_encounter(universe, pid)
        return ActionResult(ok=True, turns_spent=cost)
    _resolve_ship_combat(universe, pid, target)
    clear_ferrengi_encounter(universe, pid)
    return ActionResult(ok=True, turns_spent=cost)


def _attack_qty(player, action: Action) -> tuple[int, ActionResult | None]:
    """Fighters sent by one tw2002 attack: 1..attack_cap. Missing qty sends the cap."""
    if getattr(player.ship, "photon_disabled_ticks", 0) > 0:
        return 0, _reject_free("your fighters are offline (photon)")
    cap = attack_cap(player)
    if cap <= 0:
        return 0, _reject_free("no fighters aboard to attack with")
    raw = action.args.get("qty")
    try:
        qty = cap if raw is None else int(raw)
    except (TypeError, ValueError):
        return 0, _reject_free("invalid fighter quantity")
    if qty <= 0 or qty > cap:
        return 0, _reject_free(f"fighters per attack must be 1..{cap}")
    return qty, None


def _attack_sector_fighters(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Answer a challenge by attacking the group. Defensive and toll fighters do not shoot first."""
    player = universe.players[pid]
    if live_challenge(universe, pid) is None:
        return _reject_free("no fighters challenge you here")
    cost = K.TURN_COST["attack"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    qty, bad = _attack_qty(player, action)
    if bad is not None:
        return bad
    if _resolve_fighter_attack_tw2002(universe, pid, player.sector_id, qty):
        player.fighter_challenge = None
    return ActionResult(ok=True, turns_spent=cost)


def _handle_wait(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    cost = K.TURN_COST["wait"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    return ActionResult(ok=True, turns_spent=cost)


def _photon_damps_planet(player, planet) -> bool:
    """True when this ship's photon damp skips this planet's cannons.

    A citadel of level 5 or higher with at least QUASAR_PHOTON_SHIELD_MIN
    shields ignores the photon. Below L5 or below that shield count is damped.
    """
    if getattr(player, "photon_damped_sector_id", None) != planet.sector_id:
        return False
    level = int(planet.citadel_level or 0)
    shields = int(planet.shields or 0)
    if level >= 5 and shields >= K.QUASAR_PHOTON_SHIELD_MIN:
        return False
    return True


def _clear_photon_damp(player, sector_id: int) -> None:
    if getattr(player, "photon_damped_sector_id", None) == sector_id:
        player.photon_damped_sector_id = None


def _mark_photon_planet_damp(universe: Universe, shooter_id: str, target) -> None:
    """Mark the hit ship when its sector has a planet the photon can damp.

    The flag stays through a later warp into that sector so the sector cannon
    can skip, then through the landing. Leaving the sector or finishing the
    landing clears it. Planets at citadel L5 with enough shields are not marked.
    """
    sector = universe.sectors.get(target.sector_id)
    if sector is None:
        return
    vulnerable = []
    for planet_id in sector.planet_ids:
        planet = universe.planets.get(int(planet_id))
        if planet is None:
            continue
        level = int(planet.citadel_level or 0)
        shields = int(planet.shields or 0)
        if level >= 5 and shields >= K.QUASAR_PHOTON_SHIELD_MIN:
            continue
        vulnerable.append(planet)
    if not vulnerable:
        return
    target.photon_damped_sector_id = sector.id
    for planet in vulnerable:
        universe.emit(
            EventKind.QUASAR_DAMPED,
            actor_id=shooter_id,
            sector_id=sector.id,
            payload={"planet_id": planet.id, "damped": True},
            summary=f"Photon damped the cannons on {planet.name}",
        )


def _planet_odds_fight(player, planet, on_shields_down=None) -> tuple[int, int, int, list[dict]]:
    """One shield soak, then reaction waves, then the defensive grind.

    The survivor rule is the comment on PLANET_OFFENSE_ODDS.
    """
    a_fighters = int(player.ship.fighters)
    d_fighters = int(planet.fighters)
    d_shields = int(planet.shields)
    rounds: list[dict] = []
    n = 1
    if d_shields > 0:
        removed = min(d_shields, a_fighters // K.PLANET_SHIELD_ODDS)
        d_shields -= removed
        rounds.append({
            "round": n,
            "phase": "shields",
            "shields_removed": removed,
            "attacker_fighters_lost": 0,
            "defender_fighters_lost": 0,
            "defender_f_after": d_fighters,
            "defender_s_after": d_shields,
            "attacker_f_after": a_fighters,
        })
        n += 1
        if d_shields > 0:
            return a_fighters, d_fighters, d_shields, rounds
        if on_shields_down is not None:
            deaths = player.deaths
            on_shields_down()
            if player.deaths > deaths or int(player.ship.fighters) <= 0:
                return 0, d_fighters, d_shields, rounds
            a_fighters = int(player.ship.fighters)
    pct = max(0, min(100, int(getattr(planet, "military_reaction_pct", 0) or 0)))
    reaction = d_fighters * pct // 100
    defenders = d_fighters - reaction
    # A photon damp skips offensive reaction fighters. Shields already ran,
    # and the defensive grind below still runs.
    if _photon_damps_planet(player, planet):
        reaction = 0
        defenders = d_fighters
    # The original ten stay on the legacy table. A hull that table does not
    # list uses the live spec, or this wave falls through to 1.
    class_key = player.ship.ship_class.value
    spec = K.SHIP_SPECS[class_key] if class_key in K.SHIP_SPECS else (K.hull_spec(class_key) or {})
    wave_cap = (K.PLANET_OFFENSE_WAVE_NUM * (
        int(spec.get("max_fighters", 0) or 0) + int(spec.get("max_shields", 0) or 0)
    )) // K.PLANET_OFFENSE_WAVE_DEN
    if wave_cap < 1:
        wave_cap = 1
    while reaction > 0 and a_fighters > 0:
        sent = min(reaction, wave_cap)
        kill = sent * K.PLANET_OFFENSE_ODDS
        if kill >= a_fighters:
            needed = min(sent, (a_fighters + K.PLANET_OFFENSE_ODDS - 1) // K.PLANET_OFFENSE_ODDS)
            lost = a_fighters
            a_fighters = 0
            reaction -= needed
        else:
            needed = sent
            lost = kill
            a_fighters -= kill
            reaction -= sent
        d_fighters = defenders + reaction
        rounds.append({
            "round": n,
            "phase": "offense",
            "wave": needed,
            "attacker_fighters_lost": lost,
            "defender_fighters_lost": needed,
            "defender_f_after": d_fighters,
            "defender_s_after": d_shields,
            "attacker_f_after": a_fighters,
        })
        n += 1
        if a_fighters <= 0:
            return 0, d_fighters, d_shields, rounds
    d_fighters = defenders + reaction
    if d_fighters > 0 and a_fighters > 0:
        killed = min(d_fighters, a_fighters // K.PLANET_DEFENSE_ODDS)
        spent = killed * K.PLANET_DEFENSE_ODDS
        a_fighters -= spent
        d_fighters -= killed
        rounds.append({
            "round": n,
            "phase": "defense",
            "attacker_fighters_lost": spent,
            "defender_fighters_lost": killed,
            "defender_f_after": d_fighters,
            "defender_s_after": d_shields,
            "attacker_f_after": a_fighters,
        })
    return a_fighters, d_fighters, d_shields, rounds


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

    same_corp = bool(
        planet.corp_ticker
        and player.corp_ticker
        and planet.corp_ticker == player.corp_ticker
    )
    # An ally is still hostile for the landing. Sector hazards skip allied
    # mines and fighters on their own.
    hostile = planet.owner_id is not None and planet.owner_id != pid and not same_corp
    if hostile and _toll_blocks(universe, pid, sector):
        return ActionResult(ok=False, error="toll fighters demand payment")
    if hostile:
        deaths_before = player.deaths
        fighters_before = player.ship.fighters
        _apply_sector_hazards(universe, pid, sector, entry_verb="landing")
        if player.deaths > deaths_before:
            _clear_photon_damp(player, sector.id)
            return ActionResult(ok=True, turns_spent=cost)
        if fighters_before > 0 and player.ship.fighters <= 0:
            killer = sector.fighters.owner_id if sector.fighters is not None else None
            _destroy_ship(universe, pid, reason="sector_fighters", killer_id=killer)
            _clear_photon_damp(player, sector.id)
            return ActionResult(ok=True, turns_spent=cost)
        if _fire_atmospheric_quasar(universe, pid, planet):
            _clear_photon_damp(player, sector.id)
            return ActionResult(ok=True, turns_spent=cost)
        if int(planet.shields) <= 0 and _fire_atmospheric_quasar(universe, pid, planet):
            _clear_photon_damp(player, sector.id)
            return ActionResult(ok=True, turns_spent=cost)

    shields_already_down = hostile and int(planet.shields) <= 0
    if hostile and planet.fighters <= 0 and planet.shields > 0 and player.ship.fighters <= 0:
        # An empty ship cannot break shields, and there are no planet fighters
        # to destroy it. Repel with the shields and the ship unchanged.
        _clear_photon_damp(player, sector.id)
        return ActionResult(ok=False, error="planetary defenses repelled landing", turns_spent=cost)
    if hostile and (planet.fighters > 0 or planet.shields > 0):
        def _atm_after_shields() -> None:
            _fire_atmospheric_quasar(universe, pid, planet)

        deaths_at_fight = player.deaths
        a_fighters, d_fighters, d_shields, rounds = _planet_odds_fight(
            player, planet, None if shields_already_down else _atm_after_shields,
        )
        if player.deaths == deaths_at_fight:
            player.ship.fighters = a_fighters
        planet.fighters = d_fighters
        planet.shields = d_shields
        universe.emit(
            EventKind.COMBAT,
            actor_id=pid,
            sector_id=sector.id,
            payload={
                "exchange_kind": "planet_siege",
                "exchange_max_rounds": len(rounds),
                "vs": "planet",
                "planet_id": planet.id,
                "planet_name": planet.name,
                "citadel_level": planet.citadel_level,
                "defender_owner_id": planet.owner_id,
                "attacker_f": a_fighters,
                "attacker_s": player.ship.shields,
                "defender_f": d_fighters,
                "defender_s": d_shields,
                "rounds": rounds,
            },
            summary=(
                f"Siege of {planet.name}: "
                f"{player.name}[F{a_fighters} S{player.ship.shields}] vs Citadel L{planet.citadel_level}"
                f"[F{d_fighters} S{d_shields}]"
            ),
        )
        if a_fighters <= 0 or player.deaths > deaths_at_fight:
            if player.deaths == deaths_at_fight:
                _destroy_ship(universe, pid, reason="planet_defense", killer_id=planet.owner_id)
            _clear_photon_damp(player, sector.id)
            return ActionResult(ok=True, turns_spent=cost)
        if d_shields > 0 or d_fighters > 0:
            _clear_photon_damp(player, sector.id)
            return ActionResult(ok=False, error="planetary defenses repelled landing", turns_spent=cost)
        # Planet defenders wiped — fall through and seize.
        planet.owner_id = pid
        planet.corp_ticker = player.corp_ticker
        planet.origin = "other"
        planet.citadel_level = max(0, planet.citadel_level - 1)  # damaged in siege
        planet.citadel_target = planet.citadel_level
        planet.citadel_complete_day = None
        planet.treasury = int(planet.treasury * 0.5)
        planet.last_tax_value = planet_tax_value(planet)
    elif hostile:
        # Hostile but no defenders — block per legacy behavior (was outright refusal).
        planet.owner_id = pid
        planet.corp_ticker = player.corp_ticker
        planet.origin = "other"
        planet.last_tax_value = planet_tax_value(planet)
    elif planet.owner_id is None:
        # Empty neutral map-start planets are claimed by landing. True
        # orphans from an eliminated player keep owner_id=None until the
        # explicit claim_planet action, so the citadel/fighter inheritance
        # step remains visible and intentional.
        if _planet_was_orphaned(universe, planet.id):
            pass
        else:
            planet.owner_id = pid
            planet.corp_ticker = player.corp_ticker
            planet.origin = "claim"
            planet.last_tax_value = planet_tax_value(planet)

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
    _clear_photon_damp(player, sector.id)
    return ActionResult(ok=True, turns_spent=cost)


def _planet_was_orphaned(universe: Universe, planet_id: int) -> bool:
    """Return True for planets made ownerless by a player elimination."""
    for ev in reversed(universe.events):
        if ev.kind is EventKind.PLANET_ORPHANED and ev.payload.get("planet_id") == planet_id:
            return True
    return False


def _handle_liftoff(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if player.planet_landed is None:
        return ActionResult(ok=False, error="not landed on a planet")
    cost = K.TURN_COST["liftoff"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    planet_id = player.planet_landed
    player.planet_landed = None
    player.arrived_by_transwarp = False
    player.arrived_by_transport = False
    universe.emit(
        EventKind.LIFTOFF,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"planet_id": planet_id},
        summary=f"{player.name} lifted off",
    )
    return ActionResult(ok=True, turns_spent=cost)


def _require_landed_owned_planet(universe: Universe, pid: str, planet_id_raw):
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    if planet_id_raw is None:
        return None, ActionResult(ok=False, error="planet_id is required")
    try:
        planet_id = int(planet_id_raw)
    except (TypeError, ValueError):
        return None, ActionResult(ok=False, error=f"invalid planet_id {planet_id_raw!r}")
    if planet_id not in sector.planet_ids:
        return None, ActionResult(ok=False, error="no such planet in this sector")
    planet = universe.planets[planet_id]
    if planet.owner_id != pid and not (
        planet.corp_ticker
        and player.corp_ticker
        and planet.corp_ticker == player.corp_ticker
    ):
        return None, ActionResult(ok=False, error="planet not owned by you or your corp")
    if player.planet_landed != planet.id:
        return None, ActionResult(ok=False, error="must be landed on the planet first")
    return planet, None


def _parse_transfer_commodity(action: Action) -> tuple[Commodity | None, ActionResult | None]:
    raw = (action.args.get("commodity") or "").lower()
    try:
        commodity = Commodity(raw)
    except ValueError:
        return None, ActionResult(ok=False, error=f"invalid commodity {raw!r}")
    return commodity, None


def _parse_colonist_pool(action: Action) -> tuple[Commodity | None, ActionResult | None]:
    raw = (action.args.get("pool") or "colonists").lower()
    pool_keys = {
        "fuel_ore": Commodity.FUEL_ORE,
        "organics": Commodity.ORGANICS,
        "equipment": Commodity.EQUIPMENT,
        "colonists": Commodity.COLONISTS,
    }
    pool = pool_keys.get(raw)
    if pool is None:
        return None, ActionResult(ok=False, error=f"invalid colonist pool {raw!r}")
    return pool, None


def _handle_load_planet_cargo(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    planet, error = _require_landed_owned_planet(universe, pid, action.args.get("planet_id"))
    if error is not None:
        return error
    commodity, error = _parse_transfer_commodity(action)
    if error is not None:
        return error
    qty = int(action.args.get("qty", 0))
    if qty <= 0:
        return ActionResult(ok=False, error="qty must be positive")

    cost = K.TURN_COST.get("liftoff", 1)
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    if player.ship.cargo_used + qty > player.ship.holds:
        return ActionResult(ok=False, error="not enough cargo holds")

    pool_label = None
    if commodity == Commodity.COLONISTS:
        pool, error = _parse_colonist_pool(action)
        if error is not None:
            return error
        pool_label = pool.value
        avail = planet.colonists.get(pool, 0)
        if avail < qty:
            return ActionResult(ok=False, error=f"only {avail} colonists in {pool_label} pool")
        planet.colonists[pool] = avail - qty
    else:
        avail = planet.stockpile.get(commodity, 0)
        if avail < qty:
            return ActionResult(ok=False, error=f"only {avail} {commodity.value} in stockpile")
        planet.stockpile[commodity] = avail - qty

    old_qty = player.ship.cargo.get(commodity, 0)
    old_avg = player.ship.cargo_cost.get(commodity, 0.0) if old_qty > 0 else 0.0
    new_qty = old_qty + qty
    # Planet-produced goods have no ship-side purchase cost. If mixed with
    # bought cargo, preserve a weighted basis so later trade P&L is honest.
    player.ship.cargo[commodity] = new_qty
    player.ship.cargo_cost[commodity] = (old_qty * old_avg) / new_qty if new_qty > 0 else 0.0

    universe.emit(
        EventKind.PLANET_CARGO_TRANSFER,
        actor_id=pid,
        sector_id=planet.sector_id,
        payload={
            "planet_id": planet.id,
            "commodity": commodity.value,
            "qty": qty,
            "direction": "load",
            "pool": pool_label,
        },
        summary=f"{player.name} loaded {qty} {commodity.value} from {planet.name}",
    )
    return ActionResult(ok=True, turns_spent=cost)


def _handle_dump_planet_cargo(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    planet, error = _require_landed_owned_planet(universe, pid, action.args.get("planet_id"))
    if error is not None:
        return error
    commodity, error = _parse_transfer_commodity(action)
    if error is not None:
        return error
    qty = int(action.args.get("qty", 0))
    if qty <= 0:
        return ActionResult(ok=False, error="qty must be positive")

    cost = K.TURN_COST.get("liftoff", 1)
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    avail = player.ship.cargo.get(commodity, 0)
    if avail < qty:
        return ActionResult(ok=False, error=f"only {avail} {commodity.value} in cargo")

    pool_label = None
    if commodity == Commodity.COLONISTS:
        pool, error = _parse_colonist_pool(action)
        if error is not None:
            return error
        total_col = sum(int(n) for n in planet.colonists.values())
        room = K.planet_colonist_room(planet.class_id.value, total_col)
        if room is not None and qty > room:
            cap = K.PLANET_MAX_COLONISTS[planet.class_id.value]
            return ActionResult(ok=False, error=f"planet colonist cap is {cap}")
        pool_label = pool.value
        planet.colonists[pool] = planet.colonists.get(pool, 0) + qty
    else:
        before = int(planet.stockpile.get(commodity, 0))
        room = K.planet_stock_room(planet.class_id.value, commodity.value, before)
        if room is not None and qty > room:
            cap = K.PLANET_MAX_STOCK[planet.class_id.value][commodity.value]
            return ActionResult(ok=False, error=f"planet {commodity.value} cap is {cap}")
        planet.stockpile[commodity] = before + qty

    remaining = avail - qty
    player.ship.cargo[commodity] = remaining
    if remaining <= 0:
        player.ship.cargo_cost[commodity] = 0.0

    universe.emit(
        EventKind.PLANET_CARGO_TRANSFER,
        actor_id=pid,
        sector_id=planet.sector_id,
        payload={
            "planet_id": planet.id,
            "commodity": commodity.value,
            "qty": qty,
            "direction": "dump",
            "pool": pool_label,
        },
        summary=f"{player.name} dumped {qty} {commodity.value} onto {planet.name}",
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
    if src == "ship" and dst != "ship":
        total_col = sum(int(n) for n in planet.colonists.values())
        room = K.planet_colonist_room(planet.class_id.value, total_col)
        if room is not None and qty > room:
            cap = K.PLANET_MAX_COLONISTS[planet.class_id.value]
            return ActionResult(ok=False, error=f"planet colonist cap is {cap}")

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


def _start_class_citadel(universe: Universe, player, sector, planet, next_level: int) -> ActionResult:
    """Charge the planet stockpile. Credits stay put. A shortage changes nothing."""
    colonists, fuel, organics, equipment, days = K.citadel_class_cost(planet.class_id.value, next_level)
    have_fuel = int(planet.stockpile.get(Commodity.FUEL_ORE, 0))
    have_org = int(planet.stockpile.get(Commodity.ORGANICS, 0))
    have_eq = int(planet.stockpile.get(Commodity.EQUIPMENT, 0))
    avail_col = sum(planet.colonists.get(c, 0) for c in planet.colonists)
    short = (
        (have_fuel < fuel, f"need {fuel} fuel_ore on planet (have {have_fuel})"),
        (have_org < organics, f"need {organics} organics on planet (have {have_org})"),
        (have_eq < equipment, f"need {equipment} equipment on planet (have {have_eq})"),
        (avail_col < colonists, f"need {colonists} colonists on planet (have {avail_col})"),
    )
    for missing, message in short:
        if missing:
            return ActionResult(ok=False, error=message)
    planet.stockpile[Commodity.FUEL_ORE] = have_fuel - fuel
    planet.stockpile[Commodity.ORGANICS] = have_org - organics
    planet.stockpile[Commodity.EQUIPMENT] = have_eq - equipment
    remaining = colonists
    for pool in list(planet.colonists.keys()):
        if remaining <= 0:
            break
        take = min(planet.colonists[pool], remaining)
        planet.colonists[pool] -= take
        remaining -= take
    cost = K.TURN_COST.get("land_planet", 3)
    if player.turns_today + cost > player.turns_per_day:
        cost = 0
    planet.citadel_target = next_level
    planet.citadel_complete_day = universe.day + days
    universe.emit(
        EventKind.BUILD_CITADEL,
        actor_id=player.id,
        sector_id=sector.id,
        payload={
            "planet_id": planet.id,
            "level_target": next_level,
            "completes_day": planet.citadel_complete_day,
            "cost_cr": 0,
            "cost_col": colonists,
            "paid_from": "stockpile",
        },
        summary=(
            f"{player.name} began Citadel L{next_level} on {planet.name} "
            f"({colonists} colonists, {fuel} fuel ore, {organics} organics, "
            f"{equipment} equipment, ETA day {planet.citadel_complete_day})"
        ),
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
    if K.CITADEL_COST_MODE == "class":
        return _start_class_citadel(universe, player, sector, planet, next_level)
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
    if not K.sector_has_planet_room(len(sector.planet_ids)):
        return ActionResult(ok=False, error="sector already holds 5 planets")

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
        origin="genesis",
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
    planet.last_tax_value = planet_tax_value(planet)
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
    if K.rank_tw2002() and int(player.alignment) != 0:
        # x6: +10 good, 0 neutral, -10 evil.
        player.alignment += K.GENESIS_ALIGNMENT if player.alignment > 0 else -K.GENESIS_ALIGNMENT
    return ActionResult(ok=True, turns_spent=cost)


def _handle_claim_planet(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Claim an ORPHANED planet (owner_id is None) the player is already
    landed on.

    Match 13 addition. Orphaned planets accumulate when a player is
    eliminated (see combat.py _destroy_ship) and previously were
    strategically dead — genesis_deploy was the only way to gain a new
    planet, leaving the citadel / fighters / stockpile the dead player
    built to rot. claim_planet lets survivors inherit that investment.

    Preconditions (all free-reject):
      * must be landed
      * landed planet's owner_id must be None
      * corp-owned planets can't be claimed this way (corp_ticker != None)

    Cost: 2 turns. No combat (orphan has no owner to defend it).
    """
    player = universe.players[pid]
    planet_id = player.planet_landed
    if planet_id is None:
        return _reject_free("must be landed on the orphaned planet first")
    planet = universe.planets.get(int(planet_id))
    if planet is None:
        return _reject_free(f"unknown planet {planet_id}")
    if planet.owner_id is not None:
        return _reject_free(
            f"planet {planet.name} is already owned by {planet.owner_id}"
        )
    if planet.corp_ticker is not None:
        return _reject_free(
            f"planet {planet.name} is corp-owned ([{planet.corp_ticker}]); "
            "cannot claim an abandoned corp holding this way"
        )
    if not _planet_was_orphaned(universe, planet.id):
        return _reject_free(
            f"planet {planet.name} is neutral, not a former-player orphan; "
            "land_planet claims neutral planets automatically"
        )
    cost = K.TURN_COST.get("claim_planet", 2)
    if player.turns_today + cost > player.turns_per_day:
        return _reject_free("out of turns")

    planet.owner_id = pid
    planet.corp_ticker = player.corp_ticker
    planet.origin = "claim"
    planet.last_tax_value = planet_tax_value(planet)
    universe.emit(
        EventKind.PLANET_CLAIMED,
        actor_id=pid,
        sector_id=planet.sector_id,
        payload={
            "planet_id": planet.id,
            "planet_name": planet.name,
            "citadel_level": planet.citadel_level,
            "fighters": planet.fighters,
        },
        summary=(
            f"{player.name} claimed orphaned {planet.name} "
            f"(L{planet.citadel_level} citadel, {planet.fighters} fighters)"
        ),
    )
    _award_xp(universe, pid, "claim_planet")
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
    if K.fleet_on():
        from .fleet import buy_spare, wants_spare
        if wants_spare(action):  # SHIP_FLEET.md fl4: buy without trade-in (legacy ignores the arg)
            return buy_spare(universe, pid, str(action.args.get("ship_class") or ""))
    if player.sector_id != K.STARDOCK_SECTOR:
        return ActionResult(ok=False, error="must be at StarDock")
    class_key = action.args.get("ship_class")
    spec = K.ship_specs().get(class_key or "")
    if spec is None:
        return ActionResult(ok=False, error=f"unknown ship class {class_key!r}")
    if spec.get("corp_only") and player.corp_ticker is None:
        return ActionResult(ok=False, error="ship is corporation-only")
    if K.ship_min_alignment(spec, 0) > player.alignment:
        return ActionResult(ok=False, error=f"alignment too low for {class_key}")
    if spec.get("unique"):
        # Only one Imperial StarShip in the universe
        for p in universe.players.values():
            if p.ship.ship_class.value == class_key:
                return ActionResult(ok=False, error="this ship class is already owned elsewhere")
        for parked in universe.parked_ships.values():  # fl6: parked ships count (empty under legacy)
            if parked.ship.ship_class.value == class_key:
                return ActionResult(ok=False, error="this ship class is already owned elsewhere")

    net_cost = K.net_hull_cost(player.ship.ship_class.value, class_key)
    if player.credits < net_cost:
        return ActionResult(ok=False, error=f"insufficient credits ({player.credits} < {net_cost})")

    player.credits -= net_cost
    from .models import ShipClass as SC  # local import to avoid cycle in runtime edits
    player.ship.ship_class = SC(class_key)
    player.ship.holds = spec["holds"]
    if K.info_tw2002():
        player.ship.scanner = None  # s4: the scanner stays with the old ship
    from .ship_transwarp import clear_drive
    clear_drive(player.ship)  # tw5: the drive stays with the old hull
    if K.corpship_on():
        from .corpships import on_new_hull
        on_new_hull(player)
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
    """StarDock / Class 0 equipment purchase (CLASS0_TERRA.md t8/t11-t14)."""
    from .class0 import (
        CLASS0_ITEMS,
        class0_buy_ok,
        class0_tw2002,
        shield_unit_price,
        special_port_at,
    )
    from .economy import begin_port_visit, trade_turn_cost

    player = universe.players[pid]
    ok_here, where_err = class0_buy_ok(universe, pid)
    if not ok_here:
        return ActionResult(ok=False, error=where_err.replace(
            "must be at StarDock (sector 1) or a Class 0 port", "must be at StarDock"
        ) if not class0_tw2002() else where_err)
    item = action.args.get("item")
    qty = int(action.args.get("qty", 0))
    if item == "transwarp_drive":
        from .ship_transwarp import buy_drive
        return buy_drive(universe, pid, qty)
    if item in ("transwarp_type2", "transwarp_upgrade") and K.tow_on() and K.ship_tw_on():
        from .tow import buy_type2  # SHIP_TOW.md tt16
        return buy_type2(universe, pid, item, qty)
    if qty <= 0:
        return ActionResult(ok=False, error="qty must be positive")
    day = int(universe.day)
    class_key = player.ship.ship_class.value
    at_special = special_port_at(universe, player.sector_id) is not None
    at_stardock = player.sector_id == K.STARDOCK_SECTOR

    # Class 0 special ports: fighters / shields / holds only.
    if at_special and class0_tw2002():
        if item not in CLASS0_ITEMS:
            return ActionResult(
                ok=False,
                error="Class 0 ports sell only fighters, shields and holds",
            )

    prices = {
        "fighters": K.fighter_unit_price(day),
        "shields": shield_unit_price(day) if class0_tw2002() else 10,
        "armid_mines": K.ARMID_MINE_COST,
        "limpet_mines": K.LIMPET_MINE_COST,
        "atomic_mines": K.ATOMIC_MINE_COST,
        "photon_missiles": K.PHOTON_MISSILE_COST,
        "ether_probes": K.ETHER_PROBE_COST,
        "genesis": K.GENESIS_TORPEDO_COST,
        "holds": K.hold_next_price(class_key, player.ship.holds, day),
        # Colonists: legacy StarDock shelf only. tw2002 uses terra_colonists.
        "colonists": K.COLONIST_PRICE,
    }
    if class0_tw2002() and at_stardock:
        prices.pop("colonists", None)
    if at_special and class0_tw2002():
        prices = {k: prices[k] for k in CLASS0_ITEMS}
        prices["holds"] = K.hold_next_price(class_key, player.ship.holds, day)
    if K.hardware_tw2002() and at_stardock:
        prices["cloak"] = K.CLOAK_COST
        prices["mine_disruptor"] = K.DISRUPTOR_COST
        prices.update(K.hardware_v2_prices())
        if not K.atomic_mines_sold():
            prices.pop("atomic_mines", None)
    if K.info_tw2002() and at_stardock and item in ("density_scanner", "holo_scanner"):
        return _buy_scanner(universe, pid, str(item), qty)
    if class0_tw2002() and item == "colonists":
        return ActionResult(
            ok=False,
            error="colonists come from Terra: use terra_colonists",
        )
    unit = prices.get(item or "")
    if unit is None:
        return ActionResult(ok=False, error=f"unknown item {item!r}")
    if at_special and class0_tw2002():
        # t14: the dock turn must be affordable before anything is bought (legal list == handler).
        dock_need = trade_turn_cost(player)
        if dock_need > 0 and player.turns_today + dock_need > player.turns_per_day:
            return ActionResult(ok=False, error="out of turns")
    total = (
        K.hold_total_price(class_key, player.ship.holds, qty, day)
        if item == "holds"
        else unit * qty
    )
    if player.credits < total:
        return ActionResult(ok=False, error=f"insufficient credits ({player.credits} < {total})")
    mines_aboard = sum(int(v) for v in player.ship.mines.values())
    have = {
        "fighters": int(player.ship.fighters),
        "shields": int(player.ship.shields),
        "holds": int(player.ship.holds),
        "genesis": int(player.ship.genesis),
        "photon_missiles": int(player.ship.photon_missiles),
        "armid_mines": mines_aboard,
        "limpet_mines": mines_aboard,
        "atomic_mines": mines_aboard,
        "cloak": int(getattr(player.ship, "cloaks", 0) or 0),
        "mine_disruptor": int(getattr(player.ship, "mine_disruptors", 0) or 0),
        **v2_have(player.ship),
    }
    if item == "photon_missiles" and K.hardware_tw2002():
        from .hardware import photon_hull_ok
        if not photon_hull_ok(player):
            return ActionResult(ok=False, error="only Missile Frigate or Imperial StarShip may buy photons")
    room = K.equip_room(class_key, item, have.get(item, 0))
    if room is not None and qty > room:
        if item == "fighters":
            return ActionResult(ok=False, error="exceeds ship fighter capacity")
        if item == "shields":
            return ActionResult(ok=False, error="exceeds ship shield capacity")
        if item == "holds":
            return ActionResult(ok=False, error="max holds reached")
        if item in ("armid_mines", "limpet_mines", "atomic_mines"):
            return ActionResult(ok=False, error="exceeds ship mine capacity")
        if item == "genesis":
            return ActionResult(ok=False, error="exceeds ship genesis capacity")
        if item == "photon_missiles":
            return ActionResult(ok=False, error="exceeds ship photon capacity")
        if item == "cloak":
            return ActionResult(ok=False, error="exceeds ship cloak capacity")
        if item == "mine_disruptor":
            return ActionResult(ok=False, error="exceeds ship disruptor capacity")
        if item in K.HARDWARE_V2_ITEMS:
            return ActionResult(ok=False, error=f"exceeds ship {item} capacity")
    if item == "fighters":
        player.ship.fighters += qty
    elif item == "shields":
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
        player.ship.holds += qty
    elif item == "cloak":
        player.ship.cloaks = int(getattr(player.ship, "cloaks", 0) or 0) + qty
    elif item == "mine_disruptor":
        player.ship.mine_disruptors = int(getattr(player.ship, "mine_disruptors", 0) or 0) + qty
    elif item in K.HARDWARE_V2_ITEMS:
        v2_add(player.ship, item, qty)
    elif item == "colonists":
        # Legacy StarDock shelf only (CLASS0_MODE legacy).
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

    # t14: first buy of a visit at Alpha Centauri / Rylos costs the dock turn.
    turns = 0
    if at_special and class0_tw2002():
        turns = trade_turn_cost(player)
        begin_port_visit(player)

    universe.emit(
        EventKind.BUY_EQUIP,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"item": item, "qty": qty, "total": total},
        summary=f"{player.name} bought {qty} {item} for {total}cr",
    )
    return ActionResult(ok=True, turns_spent=turns)


def _buy_scanner(universe: Universe, pid: str, item: str, qty: int) -> ActionResult:
    """SCANNERS_HIDDEN_INFO.md s1-s3: one scanner per hull, a holo replaces a density one."""
    player = universe.players[pid]
    offer = K.scanner_offer(player.ship.ship_class.value, player.ship.scanner)
    if item not in offer:
        if K.scanner_room(player.ship.ship_class.value) is None:
            return ActionResult(ok=False, error="this hull cannot carry a long range scanner")
        return ActionResult(ok=False, error=f"{item} would not be an upgrade on this ship")
    if qty != 1:
        return ActionResult(ok=False, error="a ship carries one scanner (qty 1)")
    total = offer[item]
    if player.credits < total:
        return ActionResult(ok=False, error=f"insufficient credits ({player.credits} < {total})")
    player.credits -= total
    player.ship.scanner = K.SCANNER_HOLO if item == "holo_scanner" else K.SCANNER_DENSITY
    universe.emit(
        EventKind.BUY_EQUIP,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"item": item, "qty": 1, "total": total},
        summary=f"{player.name} fitted a {item.replace('_', ' ')} for {total}cr",
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


def _owner_still_plays(universe: Universe, owner_id: str | None) -> bool:
    if not owner_id:
        return False
    owner = universe.players.get(owner_id)
    return owner is not None and owner.alive


def _release_dissolved_corp_planets(universe: Universe, ticker: str) -> None:
    """Drop a dissolved corp's ticker. Live owners keep the planet.

    A planet whose owner is still a living player keeps that owner and loses
    the ticker. A planet with no live owner is cleared and gets the existing
    planet_orphaned event. Nothing else about the planet changes.
    """
    for planet in list(universe.planets.values()):
        if planet.corp_ticker != ticker:
            continue
        if _owner_still_plays(universe, planet.owner_id):
            planet.corp_ticker = None
            continue
        former = planet.owner_id
        planet.owner_id = None
        planet.corp_ticker = None
        universe.emit(
            EventKind.PLANET_ORPHANED,
            actor_id=former,
            sector_id=planet.sector_id,
            payload={
                "planet_id": planet.id,
                "planet_name": planet.name,
                "former_owner": former,
                "citadel_level": planet.citadel_level,
                "fighters": planet.fighters,
            },
            summary=(
                f"Planet {planet.name} (L{planet.citadel_level} citadel, "
                f"{planet.fighters} fighters) is now UNCLAIMED after [{ticker}] disbanded."
            ),
        )


def _detach_leaver_planets(universe: Universe, pid: str, ticker: str) -> None:
    """A partial leave drops the ticker from the leaver's own planets.

    Planets owned by anyone else keep the ticker. The leaver keeps owner_id,
    fighters, shields, treasury, and stockpile.
    """
    for planet in universe.planets.values():
        if planet.owner_id == pid and planet.corp_ticker == ticker:
            planet.corp_ticker = None


def _handle_corp_leave(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    if player.corp_ticker is None:
        return ActionResult(ok=False, error="not in a corp")
    corp = universe.corporations[player.corp_ticker]
    corp.member_ids = [m for m in corp.member_ids if m != pid]
    player.corp_ticker = None
    # There is no separate disband action. The last member leaving removes
    # the corp. While anyone remains, only the leaver's own planets lose
    # the ticker.
    if not corp.member_ids:
        if K.corpship_on():
            from .corpships import on_corp_extinct
            on_corp_extinct(universe, corp.ticker)
        _release_dissolved_corp_planets(universe, corp.ticker)
        universe.corporations.pop(corp.ticker, None)
    else:
        if K.corpship_on():
            from .corpships import on_member_leave
            on_member_leave(universe, pid, corp.ticker)
        _detach_leaver_planets(universe, pid, corp.ticker)
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

    # Execute walks the path one warp at a time. The first hop must be payable
    # up front: otherwise the loop used to stop immediately and return ok with
    # 0 hops and 0 turns — a free action other seats could repeat forever.
    hop_cost = _warp_cost_for(player)
    if K.tow_on():
        from .tow import move_cost as tow_move_cost
        hop_cost = tow_move_cost(universe, player)
    turns_left = int(player.turns_per_day - player.turns_today)
    if turns_left < hop_cost:
        return ActionResult(
            ok=False,
            error=f"first hop unaffordable (need {hop_cost} turns, have {turns_left})",
        )

    # Execute: walk path, consuming turns; stop at obstacle/out-of-turns
    turns_spent_total = 0
    hops_done = 0
    last_error = "plot_course execute made no hops"
    for nxt in path:
        sub_action = Action(kind=ActionKind.WARP, args={"target": nxt})
        seq_before_hop = universe.seq
        sub = _handle_warp(universe, pid, sub_action)
        if not sub.ok:
            last_error = sub.error or last_error
            if last_error == "interdicted by a planet":
                universe.emit(
                    EventKind.AUTOPILOT,
                    actor_id=pid,
                    sector_id=player.sector_id,
                    payload={
                        "target": target_id,
                        "path": path,
                        "executed": True,
                        "hops_done": hops_done,
                        "stopped": "interdict",
                    },
                    summary=(
                        f"{player.name} autopilot stopped by an interdict "
                        f"after {hops_done}/{len(path)} hops toward {target_id}"
                    ),
                )
                return ActionResult(ok=False, error=last_error, turns_spent=sub.turns_spent)
            break
        turns_spent_total += sub.turns_spent
        # apply turn cost incrementally to player so subsequent _handle_warp
        # checks the correct remaining turns (apply_action does this once per
        # call; we're calling _handle_warp directly, so update here).
        player.turns_today += sub.turns_spent
        hops_done += 1
        if not player.alive or universe.players[pid].sector_id != nxt:
            break
        if player.fighter_challenge:
            break
        if K.hardware_tw2002() and any(
            e.seq > seq_before_hop and e.kind == EventKind.HAZARD_AVOID_PROMPT and e.actor_id == pid
            for e in universe.events[-8:]
        ):
            break  # v28: the avoid prompt returns the pilot to the command prompt

    if hops_done == 0:
        return ActionResult(ok=False, error=last_error)

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
    if K.hardware_tw2002():
        return handle_photon_tw2002(universe, pid, action)
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
    if player.sector_id in K.FEDSPACE_SECTORS and fedspace_protects(target):
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
    _mark_photon_planet_damp(universe, pid, target)
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
        current, hull = target.sector_id, target.ship.ship_class.value
        if lt.target_ship_id is not None:  # SHIP_FLEET.md fl19: the limpet stayed on a parked hull
            from .fleet import limpet_location
            current, hull = limpet_location(universe, lt)
            if current is None:
                continue
        reports.append({
            "target_id": lt.target_id,
            "target_name": target.name,
            "current_sector": current,
            "ship_class": hull,
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
    if K.info_tw2002():  # SCANNERS_HIDDEN_INFO.md s13: the probe flies a route
        from .scanners import handle_probe

        return handle_probe(universe, pid, action)
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


def _parse_defense_kind(action: Action) -> tuple[str | None, ActionResult | None]:
    kind = str(action.args.get("kind") or "").lower()
    if kind not in ("fighters", "shields"):
        return None, ActionResult(ok=False, error="kind must be fighters or shields")
    return kind, None


def _parse_defense_qty(action: Action) -> tuple[int | None, ActionResult | None]:
    try:
        qty = int(action.args.get("qty", 0))
    except (TypeError, ValueError):
        return None, ActionResult(ok=False, error="qty must be positive")
    if qty <= 0:
        return None, ActionResult(ok=False, error="qty must be positive")
    return qty, None


def _ship_defense_caps(player) -> tuple[int, int]:
    spec = K.hull_spec(player.ship.ship_class.value) or {}
    return int(spec.get("max_fighters", 0) or 0), int(spec.get("max_shields", 0) or 0)


def _emit_defense_transfer(universe: Universe, player, planet, kind: str, qty: int, direction: str) -> None:
    universe.emit(
        EventKind.PLANET_DEFENSE_TRANSFER,
        actor_id=player.id,
        sector_id=planet.sector_id,
        payload={"planet_id": planet.id, "kind": kind, "qty": qty, "direction": direction},
        summary=f"{player.name} {'deposited' if direction == 'deposit' else 'withdrew'} {qty} {kind} on {planet.name}",
    )


def _parse_treasury_amount(action: Action) -> tuple[int | None, ActionResult | None]:
    try:
        amount = int(action.args.get("amount", 0))
    except (TypeError, ValueError):
        return None, ActionResult(ok=False, error="amount must be positive")
    if amount <= 0:
        return None, ActionResult(ok=False, error="amount must be positive")
    return amount, None


def _treasury_ready(universe: Universe, pid: str, action: Action, cost_key: str):
    player = universe.players[pid]
    planet, error = _require_landed_owned_planet(universe, pid, action.args.get("planet_id"))
    if error is not None:
        return player, None, error
    if int(planet.citadel_level or 0) < 1:
        return player, planet, ActionResult(ok=False, error="treasury requires citadel level 1")
    amount, error = _parse_treasury_amount(action)
    if error is not None:
        return player, planet, error
    cost = int(K.TURN_COST[cost_key])
    if player.turns_today + cost > player.turns_per_day:
        return player, planet, ActionResult(ok=False, error="out of turns")
    return player, planet, amount


def _emit_treasury(universe: Universe, player, planet, direction: str, amount: int) -> None:
    word = "deposited" if direction == "deposit" else "withdrew"
    universe.emit(
        EventKind.PLANET_TREASURY,
        actor_id=player.id,
        sector_id=planet.sector_id,
        payload={"planet_id": planet.id, "direction": direction, "amount": amount},
        summary=f"{player.name} {word} {amount} cr in {planet.name}'s treasury",
    )


def _handle_deposit_treasury(universe: Universe, pid: str, action: Action) -> ActionResult:
    player, planet, ready = _treasury_ready(universe, pid, action, "deposit_treasury")
    if isinstance(ready, ActionResult):
        return ready
    amount = ready
    if int(player.credits) < amount:
        return ActionResult(ok=False, error="not enough credits")
    if int(planet.treasury) + amount > K.PLANET_TREASURY_CAP:
        return ActionResult(ok=False, error=f"planet treasury cap is {K.PLANET_TREASURY_CAP}")
    player.credits -= amount
    planet.treasury += amount
    _emit_treasury(universe, player, planet, "deposit", amount)
    return ActionResult(ok=True, turns_spent=int(K.TURN_COST["deposit_treasury"]))


def _handle_withdraw_treasury(universe: Universe, pid: str, action: Action) -> ActionResult:
    player, planet, ready = _treasury_ready(universe, pid, action, "withdraw_treasury")
    if isinstance(ready, ActionResult):
        return ready
    amount = ready
    if int(planet.treasury) < amount:
        return ActionResult(ok=False, error="cannot take planet treasury below 0")
    planet.treasury -= amount
    player.credits += amount
    _emit_treasury(universe, player, planet, "withdraw", amount)
    return ActionResult(ok=True, turns_spent=int(K.TURN_COST["withdraw_treasury"]))


def _handle_set_military_reaction(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    planet, error = _require_landed_owned_planet(universe, pid, action.args.get("planet_id"))
    if error is not None:
        return error
    try:
        pct = int(action.args.get("pct", -1))
    except (TypeError, ValueError):
        return ActionResult(ok=False, error="pct must be from 0 to 100")
    if pct < 0 or pct > 100:
        return ActionResult(ok=False, error="pct must be from 0 to 100")
    cost = int(K.TURN_COST["set_military_reaction"])
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    planet.military_reaction_pct = pct
    universe.emit(
        EventKind.PLANET_MILITARY_REACTION,
        actor_id=player.id,
        sector_id=planet.sector_id,
        payload={"planet_id": planet.id},
        summary=f"{player.name} set military reaction on {planet.name}",
    )
    return ActionResult(ok=True, turns_spent=cost)


def _quasar_shot(fuel: int, pct: int) -> tuple[int, int]:
    """pct is an integer 0-100, not a fraction.

    Burned fuel is fuel * pct // 100. Damage is that burned fuel // 3.
    10,000 fuel at 10% burns 1,000 and deals 333. The next shot on the
    remaining 9,000 burns 900 and deals 300.
    """
    burned = fuel * pct // 100
    return burned, burned // 3


def _apply_quasar_to_ship(universe: Universe, pid: str, damage: int, planet, mode: str) -> None:
    """Shields soak first, then fighters. Destroy when both are gone.

    This is not the sector-fighter clash (fighters only) and not the mine
    overflow path. A remaining shield or fighter keeps the ship.
    """
    player = universe.players[pid]
    soaked = min(int(player.ship.shields), damage)
    player.ship.shields = int(player.ship.shields) - soaked
    rest = damage - soaked
    if rest > 0:
        player.ship.fighters = max(0, int(player.ship.fighters) - rest)
    universe.emit(
        EventKind.QUASAR_FIRE,
        actor_id=planet.owner_id,
        sector_id=planet.sector_id,
        payload={"planet_id": planet.id, "mode": mode, "damage": damage},
        summary=f"Quasar on {planet.name} hit {player.name} for {damage}",
    )
    if damage > 0 and player.ship.shields <= 0 and player.ship.fighters <= 0:
        _destroy_ship(universe, pid, reason="quasar", killer_id=planet.owner_id)


def _try_interdict(universe: Universe, pid: str, sector) -> ActionResult | None:
    """Hold one hostile warp. Photon damp does not affect the interdictor."""
    player = universe.players[pid]
    planets = [universe.planets[item] for item in sector.planet_ids if item in universe.planets]
    for planet in sorted(planets, key=lambda item: item.id):
        if planet.owner_id is None or _are_allied(universe, pid, planet.owner_id):
            continue
        if int(planet.citadel_level or 0) < K.INTERDICTOR_MIN_LEVEL:
            continue
        fuel = int(planet.stockpile.get(Commodity.FUEL_ORE, 0))
        if fuel < K.INTERDICTOR_FUEL:
            continue
        planet.stockpile[Commodity.FUEL_ORE] = fuel - K.INTERDICTOR_FUEL
        universe.emit(
            EventKind.INTERDICT,
            actor_id=planet.owner_id,
            sector_id=sector.id,
            payload={"planet_id": planet.id, "ship_name": player.name},
            summary=f"{planet.name} interdicted {player.name}",
        )
        _fire_interdict_quasar(universe, pid, planet)
        held_cost = _warp_cost_for(player)
        if K.tow_on():  # SHIP_TOW.md tt10: the interdictor holds the whole tow at the tow cost
            from .tow import move_cost as tow_move_cost
            held_cost = tow_move_cost(universe, player)
        return ActionResult(ok=False, error="interdicted by a planet", turns_spent=held_cost)
    return None


def _fire_interdict_quasar(universe: Universe, pid: str, planet) -> None:
    """One sector shot on the fuel left after the interdictor burn."""
    if int(planet.citadel_level or 0) < K.QUASAR_MIN_LEVEL:
        return
    pct = int(planet.quasar_sector_pct or 0)
    if pct <= 0:
        return
    fuel = int(planet.stockpile.get(Commodity.FUEL_ORE, 0))
    if fuel <= 0:
        return
    burned, damage = _quasar_shot(fuel, pct)
    if burned <= 0:
        return
    planet.stockpile[Commodity.FUEL_ORE] = fuel - burned
    _apply_quasar_to_ship(universe, pid, damage, planet, "sector")


def _apply_sector_quasar(universe: Universe, pid: str, sector) -> None:
    """Hostile warp only. Lowest planet id first. Stop once the ship is dead."""
    player = universe.players[pid]
    deaths_before = player.deaths
    planets = [universe.planets[pid_] for pid_ in sector.planet_ids if pid_ in universe.planets]
    for planet in sorted(planets, key=lambda item: item.id):
        if player.deaths > deaths_before:
            return
        if planet.owner_id is None or _are_allied(universe, pid, planet.owner_id):
            continue
        if _photon_damps_planet(player, planet):
            continue
        if int(planet.citadel_level or 0) < K.QUASAR_MIN_LEVEL:
            continue
        pct = int(planet.quasar_sector_pct or 0)
        if pct <= 0:
            continue
        fuel = int(planet.stockpile.get(Commodity.FUEL_ORE, 0))
        if fuel <= 0:
            continue
        burned, damage = _quasar_shot(fuel, pct)
        if burned <= 0:
            continue
        planet.stockpile[Commodity.FUEL_ORE] = fuel - burned
        _apply_quasar_to_ship(universe, pid, damage, planet, "sector")


def _atm_quasar_shot(fuel: int, pct: int) -> tuple[int, int]:
    """pct is an integer 0-100.

    Burned fuel is fuel * pct // 100. Damage is that fuel times QUASAR_ATM_FACTOR.
    10,000 fuel at 10% burns 1,000 and deals 2,000. The next shot on the
    remaining 9,000 burns 900 and deals 1,800.
    """
    burned = fuel * pct // 100
    return burned, burned * K.QUASAR_ATM_FACTOR


def _fire_atmospheric_quasar(universe: Universe, pid: str, planet) -> bool:
    """One atmosphere shot. True when this shot destroyed the ship."""
    player = universe.players[pid]
    if _photon_damps_planet(player, planet):
        return False
    if int(planet.citadel_level or 0) < K.QUASAR_MIN_LEVEL:
        return False
    pct = int(planet.quasar_atm_pct or 0)
    if pct <= 0:
        return False
    fuel = int(planet.stockpile.get(Commodity.FUEL_ORE, 0))
    if fuel <= 0:
        return False
    burned, damage = _atm_quasar_shot(fuel, pct)
    if burned <= 0:
        return False
    deaths = player.deaths
    planet.stockpile[Commodity.FUEL_ORE] = fuel - burned
    _apply_quasar_to_ship(universe, pid, damage, planet, "atmosphere")
    return player.deaths > deaths


def _handle_set_quasar_sector(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    planet, error = _require_landed_owned_planet(universe, pid, action.args.get("planet_id"))
    if error is not None:
        return error
    if int(planet.citadel_level or 0) < K.QUASAR_MIN_LEVEL:
        return ActionResult(ok=False, error="quasar requires citadel level 3")
    try:
        pct = int(action.args.get("pct", -1))
    except (TypeError, ValueError):
        return ActionResult(ok=False, error="pct must be from 0 to 100")
    if pct < 0 or pct > 100:
        return ActionResult(ok=False, error="pct must be from 0 to 100")
    cost = int(K.TURN_COST["set_quasar_sector"])
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    planet.quasar_sector_pct = pct
    return ActionResult(ok=True, turns_spent=cost)


def _handle_set_quasar_atm(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    planet, error = _require_landed_owned_planet(universe, pid, action.args.get("planet_id"))
    if error is not None:
        return error
    if int(planet.citadel_level or 0) < K.QUASAR_MIN_LEVEL:
        return ActionResult(ok=False, error="quasar requires citadel level 3")
    try:
        pct = int(action.args.get("pct", -1))
    except (TypeError, ValueError):
        return ActionResult(ok=False, error="pct must be from 0 to 100")
    if pct < 0 or pct > 100:
        return ActionResult(ok=False, error="pct must be from 0 to 100")
    cost = int(K.TURN_COST["set_quasar_atm"])
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    planet.quasar_atm_pct = pct
    return ActionResult(ok=True, turns_spent=cost)


def _dest_fighter_holds(universe: Universe, planet, sector) -> bool:
    """True when dest fighters belong to the planet owner or that owner's corp."""
    group = sector.fighters
    if group is None or int(group.count) < 1 or not group.owner_id:
        return False
    if group.owner_id == planet.owner_id:
        return True
    holder = universe.players.get(group.owner_id)
    owner = universe.players.get(planet.owner_id) if planet.owner_id else None
    if holder is None or owner is None:
        return False
    return bool(owner.corp_ticker and holder.corp_ticker and owner.corp_ticker == holder.corp_ticker)


def _handle_planet_transwarp(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    planet, error = _require_landed_owned_planet(universe, pid, action.args.get("planet_id"))
    if error is not None:
        return error
    if int(planet.citadel_level or 0) < K.PLANET_TRANSWARP_MIN_LEVEL:
        return ActionResult(ok=False, error="transwarp requires citadel level 4")
    if planet.last_transwarp_day == universe.day:
        return ActionResult(ok=False, error="planet already moved today")
    raw = action.args.get("dest_sector")
    if raw is None:
        return ActionResult(ok=False, error="dest_sector is required")
    try:
        dest_id = int(raw)
    except (TypeError, ValueError):
        return ActionResult(ok=False, error=f"invalid dest_sector {raw!r}")
    if dest_id == planet.sector_id:
        return ActionResult(ok=False, error="destination is this sector")
    dest = universe.sectors.get(dest_id)
    if dest is None:
        return ActionResult(ok=False, error="no such sector")
    if dest_id == K.STARDOCK_SECTOR or dest_id in K.FEDSPACE_SECTORS:
        return ActionResult(ok=False, error="cannot transwarp to FedSpace")
    if not K.sector_has_planet_room(len(dest.planet_ids)):
        return ActionResult(ok=False, error="sector already holds 5 planets")
    path = _bfs_path(universe, planet.sector_id, dest_id)
    if not path:
        return ActionResult(ok=False, error="no route to destination")
    cost_fuel = len(path) * K.PLANET_TRANSWARP_FUEL_PER_SECTOR
    fuel = int(planet.stockpile.get(Commodity.FUEL_ORE, 0))
    if fuel < cost_fuel:
        return ActionResult(ok=False, error="not enough planet fuel")
    if not _dest_fighter_holds(universe, planet, dest):
        return ActionResult(ok=False, error="destination needs a fighter of the planet owner")
    cost = int(K.TURN_COST["planet_transwarp"])
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")

    old_id = planet.sector_id
    old_sector = universe.sectors[old_id]
    old_sector.planet_ids = [item for item in old_sector.planet_ids if item != planet.id]
    if planet.id not in dest.planet_ids:
        dest.planet_ids.append(planet.id)
    planet.sector_id = dest_id
    planet.stockpile[Commodity.FUEL_ORE] = fuel - cost_fuel
    planet.last_transwarp_day = universe.day
    for other in universe.players.values():
        if other.planet_landed == planet.id:
            try:
                old_sector.occupant_ids.remove(other.id)
            except ValueError:
                pass
            other.sector_id = dest_id
            other.end_port_visit()
            if other.id not in dest.occupant_ids:
                dest.occupant_ids.append(other.id)
        if other.photon_damped_sector_id == old_id:
            other.photon_damped_sector_id = None
    witnesses = []
    for item in list(old_sector.occupant_ids) + list(dest.occupant_ids) + [planet.owner_id, pid]:
        if item and item not in witnesses:
            witnesses.append(item)
    universe.emit(
        EventKind.PLANET_TRANSWARP,
        actor_id=pid,
        sector_id=dest_id,
        payload={
            "planet_id": planet.id,
            "from_sector": old_id,
            "to_sector": dest_id,
            "_witnesses": witnesses,
        },
        summary=f"{planet.name} transwarped from {old_id} to {dest_id}",
    )
    return ActionResult(ok=True, turns_spent=cost)


def _handle_planet_buy_transporter(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    planet, error = _require_landed_owned_planet(universe, pid, action.args.get("planet_id"))
    if error is not None:
        return error
    if int(planet.citadel_level or 0) < 1:
        return ActionResult(ok=False, error="transporter requires citadel level 1")
    if planet.has_transporter:
        return ActionResult(ok=False, error="transporter already bought")
    price = K.PLANET_TRANSPORTER_COST_FIRST
    if int(player.credits) < price:
        return ActionResult(ok=False, error="not enough credits")
    player.credits -= price
    planet.has_transporter = True
    universe.emit(
        EventKind.PLANET_TRANSPORTER_BOUGHT,
        actor_id=pid,
        sector_id=planet.sector_id,
        payload={"planet_id": planet.id},
        summary=f"{player.name} bought a transporter on {planet.name}",
    )
    return ActionResult(ok=True, turns_spent=int(K.TURN_COST["planet_buy_transporter"]))


def _handle_planet_transport(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Move the landed player. The planet stays. Failures spend nothing."""
    player = universe.players[pid]
    planet, error = _require_landed_owned_planet(universe, pid, action.args.get("planet_id"))
    if error is not None:
        return error
    if not planet.has_transporter:
        return ActionResult(ok=False, error="planet has no transporter")
    raw = action.args.get("dest_sector")
    if raw is None:
        return ActionResult(ok=False, error="dest_sector is required")
    try:
        dest_id = int(raw)
    except (TypeError, ValueError):
        return ActionResult(ok=False, error=f"invalid dest_sector {raw!r}")
    if dest_id == player.sector_id:
        return ActionResult(ok=False, error="destination is this sector")
    dest = universe.sectors.get(dest_id)
    if dest is None:
        return ActionResult(ok=False, error="no such sector")
    if dest_id == K.STARDOCK_SECTOR or dest_id in K.FEDSPACE_SECTORS:
        return ActionResult(ok=False, error="cannot transport to FedSpace")
    path = _bfs_path(universe, player.sector_id, dest_id)
    if not path:
        return ActionResult(ok=False, error="no route to destination")
    hops = len(path)
    credit_cost = K.PLANET_TRANSPORTER_COST_FIRST + K.PLANET_TRANSPORTER_COST_EXTRA * (hops - 1)
    fuel_cost = hops * K.PLANET_TRANSPORTER_FUEL_PER_SECTOR
    fuel = int(planet.stockpile.get(Commodity.FUEL_ORE, 0))
    if int(player.credits) < credit_cost:
        return ActionResult(ok=False, error="not enough credits")
    if fuel < fuel_cost:
        return ActionResult(ok=False, error="not enough planet fuel")
    if not _dest_fighter_holds(universe, planet, dest):
        return ActionResult(ok=False, error="destination needs a fighter of the planet owner")
    cost = int(K.TURN_COST["planet_transport"])
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")

    old_id = player.sector_id
    old_sector = universe.sectors[old_id]
    try:
        old_sector.occupant_ids.remove(pid)
    except ValueError:
        pass
    player.sector_id = dest_id
    player.end_port_visit()
    player.planet_landed = None
    if pid not in dest.occupant_ids:
        dest.occupant_ids.append(pid)
    player.credits -= credit_cost
    planet.stockpile[Commodity.FUEL_ORE] = fuel - fuel_cost
    witnesses = []
    for item in list(old_sector.occupant_ids) + list(dest.occupant_ids) + [planet.owner_id, pid]:
        if item and item not in witnesses:
            witnesses.append(item)
    universe.emit(
        EventKind.PLANET_TRANSPORT,
        actor_id=pid,
        sector_id=dest_id,
        payload={
            "planet_id": planet.id,
            "from_sector": old_id,
            "to_sector": dest_id,
            "_witnesses": witnesses,
        },
        summary=f"{player.name} transported from {old_id} to {dest_id}",
    )
    # FEDSPACE_POLICE.md f6/f22: the transporter moves the pilot's own ship.
    from .fed import check_iss_repo_on_move
    check_iss_repo_on_move(universe, pid)
    return ActionResult(ok=True, turns_spent=cost)


def _handle_deposit_planet_defense(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    planet, error = _require_landed_owned_planet(universe, pid, action.args.get("planet_id"))
    if error is not None:
        return error
    kind, error = _parse_defense_kind(action)
    if error is not None:
        return error
    qty, error = _parse_defense_qty(action)
    if error is not None:
        return error
    cost = int(K.TURN_COST["deposit_planet_defense"])
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    if int(planet.citadel_level or 0) < K.PLANET_DEFENSE_MIN_LEVEL:
        return ActionResult(ok=False, error="planet citadel level is below the defense stocking minimum")
    if kind == "fighters":
        if int(player.ship.fighters) < qty:
            return ActionResult(ok=False, error="not enough fighters on the ship")
        if int(planet.fighters) + qty > K.PLANET_FIGHTER_CAP:
            return ActionResult(ok=False, error=f"planet fighter cap is {K.PLANET_FIGHTER_CAP}")
        player.ship.fighters -= qty
        planet.fighters += qty
    else:
        need = qty * K.PLANET_SHIELD_SHIP_COST
        if int(player.ship.shields) < need:
            return ActionResult(ok=False, error="not enough shields on the ship (10 ship shields = 1 planet shield)")
        player.ship.shields -= need
        planet.shields += qty
    _emit_defense_transfer(universe, player, planet, kind, qty, "deposit")
    return ActionResult(ok=True, turns_spent=cost)


def _handle_withdraw_planet_defense(universe: Universe, pid: str, action: Action) -> ActionResult:
    player = universe.players[pid]
    planet, error = _require_landed_owned_planet(universe, pid, action.args.get("planet_id"))
    if error is not None:
        return error
    kind, error = _parse_defense_kind(action)
    if error is not None:
        return error
    qty, error = _parse_defense_qty(action)
    if error is not None:
        return error
    cost = int(K.TURN_COST["withdraw_planet_defense"])
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    if int(planet.citadel_level or 0) < K.PLANET_DEFENSE_MIN_LEVEL:
        return ActionResult(ok=False, error="planet citadel level is below the defense stocking minimum")
    fighter_cap, shield_cap = _ship_defense_caps(player)
    if kind == "fighters":
        if int(planet.fighters) < qty:
            return ActionResult(ok=False, error="cannot take planet fighters below 0")
        if int(player.ship.fighters) + qty > fighter_cap:
            return ActionResult(ok=False, error="that would put the ship over its fighter cap")
        planet.fighters -= qty
        player.ship.fighters += qty
    else:
        gain = qty * K.PLANET_SHIELD_SHIP_COST
        if int(planet.shields) < qty:
            return ActionResult(ok=False, error="cannot take planet shields below 0")
        if int(player.ship.shields) + gain > shield_cap:
            return ActionResult(ok=False, error="that would put the ship over its shield cap")
        planet.shields -= qty
        player.ship.shields += gain
    _emit_defense_transfer(universe, player, planet, kind, qty, "withdraw")
    return ActionResult(ok=True, turns_spent=cost)


def _handle_planet_destroy(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Zero colonists, then a second call removes the planet. Failures spend nothing."""
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    planet_id = action.args.get("planet_id")
    if planet_id is None or int(planet_id) not in sector.planet_ids:
        return ActionResult(ok=False, error="no such planet in this sector")
    planet = universe.planets[int(planet_id)]
    blocked = planet_destroy_reason(universe, player, planet)
    if blocked:
        return ActionResult(ok=False, error=blocked)
    if not K.PLANET_DESTROY_COLONISTS_TO_ZERO:
        return ActionResult(ok=False, error="planet destruction is off")
    cost = K.TURN_COST["planet_destroy"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    if not K.rank_tw2002():
        player.alignment -= K.PLANET_DESTROY_ALIGNMENT
    colonists_left = sum(int(n) for n in planet.colonists.values())
    if colonists_left > 0:
        for pool in list(planet.colonists.keys()):
            planet.colonists[pool] = 0
        universe.emit(
            EventKind.PLANET_COLONISTS_KILLED,
            actor_id=pid,
            sector_id=sector.id,
            payload={"planet_id": planet.id},
            summary=f"{player.name} killed the colonists on {planet.name}",
        )
        return ActionResult(ok=True, turns_spent=cost)
    if K.hardware_tw2002():
        # v15: the last step sets an atomic detonator (planet_destroy_reason checked one is aboard).
        player.ship.atomic_detonators = int(player.ship.atomic_detonators) - 1
    _remove_planet(universe, pid, planet)
    return ActionResult(ok=True, turns_spent=cost)


def _remove_planet(universe: Universe, pid: str, planet, *, via: str = "planet_destroy") -> None:
    """The planet goes: landers lift off, x7 rank award, NavHaz (tw2002), PLANET_DESTROYED."""
    player = universe.players[pid]
    sector = universe.sectors[planet.sector_id]
    gone = planet.id
    sector_id = planet.sector_id
    for other in universe.players.values():
        if other.planet_landed == gone:
            other.planet_landed = None
    sector.planet_ids = [sid for sid in sector.planet_ids if sid != gone]
    del universe.planets[gone]
    if K.rank_tw2002():
        # x7 / conflict 14: -1 alignment and +50 experience when the planet goes.
        player.alignment -= K.PLANET_DESTROY_ALIGNMENT_TW2002
        _award_xp(universe, pid, "destroy_planet")
    if K.hardware_tw2002():
        add_navhaz(sector, int(K.NAVHAZ_PER_PLANET_DESTROYED))  # v22: the debris is NavHaz
    payload: dict = {"planet_id": gone, "sector_id": sector_id}
    if via != "planet_destroy":
        payload["via"] = via
    universe.emit(
        EventKind.PLANET_DESTROYED,
        actor_id=pid,
        sector_id=sector_id,
        payload=payload,
        summary=f"{player.name} destroyed the planet in sector {sector_id}",
    )


def _handle_deploy_atomic(universe: Universe, pid: str, action: Action) -> ActionResult:
    """v13-v18: set an atomic detonator on the planet you are landed on.

    Colonists still alive disarm it and the blast takes your ship (Bible). With none left the
    planet is destroyed. Failures spend nothing. Never dispatched under HARDWARE_MODE legacy.
    """
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    raw = action.args.get("planet_id", player.planet_landed)
    try:
        planet_id = int(raw)
    except (TypeError, ValueError):
        return ActionResult(ok=False, error="deploy_atomic needs the planet_id you are landed on")
    planet = universe.planets.get(planet_id) if planet_id in sector.planet_ids else None
    if planet is None:
        return ActionResult(ok=False, error="no such planet in this sector")
    blocked = detonator_reason(universe, player, planet)
    if blocked:
        return ActionResult(ok=False, error=blocked)
    cost = int(K.TURN_COST["planet_destroy"])
    player.ship.atomic_detonators = int(player.ship.atomic_detonators) - 1
    if colonists_on(planet) > 0:
        universe.emit(
            EventKind.ATOMIC_DETONATOR,
            actor_id=pid,
            sector_id=sector.id,
            payload={"planet_id": planet.id, "outcome": "backfire"},
            summary=f"Colonists on {planet.name} tried to disarm {player.name}'s atomic detonator - it went off",
        )
        player.planet_landed = None
        _destroy_ship(universe, pid, reason="atomic_detonator")
        return ActionResult(ok=True, turns_spent=cost)
    if not K.rank_tw2002():
        player.alignment -= K.PLANET_DESTROY_ALIGNMENT  # Bible: -50 for destroying a planet
    universe.emit(
        EventKind.ATOMIC_DETONATOR,
        actor_id=pid,
        sector_id=sector.id,
        payload={"planet_id": planet.id, "outcome": "planet_destroyed"},
        summary=f"{player.name}'s atomic detonator destroyed {planet.name}",
    )
    _remove_planet(universe, pid, planet, via="atomic_detonator")
    return ActionResult(ok=True, turns_spent=cost)


def _handle_recall_deployed(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Pick up your own fighters or mines in the sector you are standing in."""
    if not K.sector_fighter_tw2002():
        return ActionResult(ok=False, error="legacy sector fighters have no recall")
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    what = action.args.get("what")
    if what not in ("fighters", "mines"):
        return ActionResult(ok=False, error="what must be fighters or mines")
    cost = K.TURN_COST["recall_deployed"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")

    if what == "fighters":
        dep = sector.fighters
        if dep is None or dep.owner_id != pid or int(dep.count) <= 0:
            return ActionResult(ok=False, error="no fighters of yours here")
        room = K.equip_room(player.ship.ship_class.value, "fighters", int(player.ship.fighters))
        if room is None:
            room = int(dep.count)
        raw = action.args.get("qty")
        qty = int(dep.count) if raw is None else int(raw)
        if qty <= 0 or qty > int(dep.count) or qty > room:
            return ActionResult(ok=False, error="invalid fighter quantity")
        share = 0
        pot = int(dep.toll_credits or 0)
        if pot > 0:
            share = pot if qty == int(dep.count) else pot * qty // int(dep.count)
            dep.toll_credits = pot - share
        dep.count = int(dep.count) - qty
        if dep.count <= 0:
            sector.fighters = None
        player.ship.fighters = int(player.ship.fighters) + qty
        player.credits += share
        universe.emit(
            EventKind.RECALL_DEPLOYED,
            actor_id=pid,
            sector_id=sector.id,
            payload={"what": "fighters", "qty": qty},
            summary=f"{player.name} recalled {qty} fighters in {sector.id}",
        )
        return ActionResult(ok=True, turns_spent=cost)

    try:
        kind = MineType(action.args.get("kind", "armid"))
    except ValueError:
        return ActionResult(ok=False, error="invalid mine type")
    if kind == MineType.ATOMIC:
        return ActionResult(ok=False, error="atomic mines do not sit in a sector")
    existing = next((m for m in sector.mines if m.owner_id == pid and m.kind == kind), None)
    if existing is None or int(existing.count) <= 0:
        return ActionResult(ok=False, error="no mines of yours here")
    aboard = sum(int(v) for v in (player.ship.mines or {}).values())
    room = K.equip_room(player.ship.ship_class.value, "armid_mines", aboard)
    if room is None:
        room = int(existing.count)
    raw = action.args.get("qty")
    qty = int(existing.count) if raw is None else int(raw)
    if qty <= 0 or qty > int(existing.count) or qty > room:
        return ActionResult(ok=False, error="invalid mine quantity")
    existing.count = int(existing.count) - qty
    if existing.count <= 0:
        sector.mines.remove(existing)
    player.ship.mines[kind] = int(player.ship.mines.get(kind, 0)) + qty
    universe.emit(
        EventKind.RECALL_DEPLOYED,
        actor_id=pid,
        sector_id=sector.id,
        payload={"what": "mines", "qty": qty, "kind": kind.value},
        summary=f"{player.name} recalled {qty} {kind.value} mines in {sector.id}",
    )
    return ActionResult(ok=True, turns_spent=cost)


def _surrender_deployment(universe: Universe, pid: str, sector):
    dep = sector.fighters
    if dep is None or int(dep.count) <= 0:
        return None
    if dep.owner_id == pid or _are_allied(universe, pid, dep.owner_id):
        return None
    if dep.mode not in (FighterMode.DEFENSIVE, FighterMode.TOLL):
        return None
    return dep


def _handle_surrender(universe: Universe, pid: str, action: Action) -> ActionResult:
    # ferrengi-aliens-v1 n15: tribute to Ferrengi
    if live_ferrengi_encounter(universe, pid) is not None:
        cost = K.TURN_COST["surrender"]
        player = universe.players[pid]
        if player.turns_today + cost > player.turns_per_day:
            return ActionResult(ok=False, error="out of turns")
        result = apply_ferrengi_tribute(universe, pid)
        if not result.get("ok"):
            return _reject_free(result.get("error") or "tribute failed")
        return ActionResult(ok=True, turns_spent=cost)
    if not K.sector_fighter_tw2002():
        return ActionResult(ok=False, error="legacy sector fighters do not take a surrender")
    if not K.combat_tw2002():
        return ActionResult(ok=False, error="surrender waits for the defensive challenge")
    player = universe.players[pid]
    if live_challenge(universe, pid) is None:
        return _reject_free("no fighters challenge you here")
    sector = universe.sectors[player.sector_id]
    dep = _surrender_deployment(universe, pid, sector)
    if dep is None:
        return _reject_free("no fighters challenge you here")
    cost = K.TURN_COST["surrender"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    universe.emit(
        EventKind.SURRENDER,
        actor_id=pid,
        sector_id=sector.id,
        payload={"mode": dep.mode.value, "victim": pid},
        summary=f"{player.name} surrendered to the {dep.mode.value} fighters in {sector.id}",
    )
    player.fighter_challenge = None
    # The death path (DEATH_ESCAPE_PODS.md d20): a pod back to the previous sector, or Ship Destroyed.
    _destroy_ship(universe, pid, reason="surrender", killer_id=dep.owner_id)
    return ActionResult(ok=True, turns_spent=cost)


def _handle_retreat(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Back to the sector the ship came from. No hazards fire there. Fighters unchanged."""
    player = universe.players[pid]
    ferr_enc = live_ferrengi_encounter(universe, pid)
    if ferr_enc is not None:
        # n17: flee any neighbour (Ferrengi boarded in-sector; no from_sector).
        sector = universe.sectors[player.sector_id]
        choices = [w for w in sector.warps if w not in K.FEDSPACE_SECTORS] or list(sector.warps)
        if not choices:
            return _reject_free("no warp out to flee the Ferrengi")
        dest = int(choices[0])
        cost = _warp_cost_for(player)
        if player.turns_today + cost > player.turns_per_day:
            return ActionResult(ok=False, error="out of turns for this day")
        clear_ferrengi_encounter(universe, pid)
        _retreat_move(universe, player, dest)
        player.flee_penalty = True
        return ActionResult(ok=True, turns_spent=cost)
    if not K.challenge_on():
        return _reject_free("retreat needs tw2002 combat")
    ch = live_challenge(universe, pid)
    if ch is None:
        return _reject_free("no fighters challenge you here")
    why = retreat_block(universe, pid)
    if why is not None:
        return _reject_free(why)
    cost = _warp_cost_for(player)
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns for this day")
    _retreat_move(universe, player, int(ch["from_sector"]))
    # FEDSPACE_POLICE.md f6/f22: a retreat is a move of the pilot's own ship.
    from .fed import check_iss_repo_on_move
    check_iss_repo_on_move(universe, pid)
    return ActionResult(ok=True, turns_spent=cost)


def _retreat_move(universe: Universe, player, back: int, *, overnight: bool = False) -> None:
    """Move a challenged ship back to the sector it came from. No hazards fire there."""
    pid = player.id
    here = player.sector_id
    try:
        universe.sectors[here].occupant_ids.remove(pid)
    except ValueError:
        pass
    if player.photon_damped_sector_id == here:
        _clear_photon_damp(player, here)
    player.fighter_challenge = None
    player.prev_sector_id = here  # d6: a retreat sets the previous sector too
    player.sector_id = back
    player.end_port_visit()
    universe.sectors[back].occupant_ids.append(pid)
    _learn_sector(player, universe, back)
    payload: dict = {"from": here, "to": back}
    if overnight:
        payload["overnight"] = True
    universe.emit(
        EventKind.RETREAT,
        actor_id=pid,
        sector_id=back,
        payload=payload,
        summary=(f"{player.name} fell back {here} → {back} at the end of the day (the fighters hold {here})"
                 if overnight else f"{player.name} retreated {here} → {back}"),
    )


def _handle_pay_toll(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Pay 5 credits per toll fighter into the pot on the group. Ends the challenge."""
    if not K.challenge_on():
        return _reject_free("pay_toll needs tw2002 combat")
    player = universe.players[pid]
    ch = live_challenge(universe, pid)
    if ch is None:
        return _reject_free("no fighters challenge you here")
    sector = universe.sectors[player.sector_id]
    dep = _hostile_toll(universe, pid, sector)
    if dep is None:
        return _reject_free("these fighters take no toll")
    bill = int(dep.count) * K.SECTOR_TOLL_CREDITS_PER_FIGHTER
    if player.credits < bill:
        return _reject_free(f"the toll is {bill} credits")
    player.credits -= bill
    dep.toll_credits = int(dep.toll_credits or 0) + bill
    player.fighter_challenge = None
    universe.emit(
        EventKind.TRADE,
        actor_id=pid,
        sector_id=sector.id,
        payload={"toll_to": dep.owner_id, "amount": bill},
        summary=f"{player.name} paid {bill} cr toll to pass through {sector.id}",
    )
    return ActionResult(ok=True, turns_spent=K.TURN_COST["pay_toll"])


_DISPATCH: dict[ActionKind, Callable] = {
    ActionKind.WARP: _handle_warp,
    ActionKind.TRADE: _handle_trade,
    ActionKind.ROB: handle_rob,
    ActionKind.STEAL: handle_steal,
    ActionKind.SCAN: _handle_scan,
    ActionKind.DEPLOY_FIGHTERS: _handle_deploy_fighters,
    ActionKind.DEPLOY_MINES: _handle_deploy_mines,
    ActionKind.ATTACK: _handle_attack,
    ActionKind.LAND_PLANET: _handle_land_planet,
    ActionKind.LIFTOFF: _handle_liftoff,
    ActionKind.ASSIGN_COLONISTS: _handle_assign_colonists,
    ActionKind.LOAD_PLANET_CARGO: _handle_load_planet_cargo,
    ActionKind.DUMP_PLANET_CARGO: _handle_dump_planet_cargo,
    ActionKind.BUILD_CITADEL: _handle_build_citadel,
    ActionKind.DEPLOY_GENESIS: _handle_deploy_genesis,
    ActionKind.CLAIM_PLANET: _handle_claim_planet,
    ActionKind.PLOT_COURSE: _handle_plot_course,
    ActionKind.PHOTON_MISSILE: _handle_photon_missile,
    ActionKind.CLOAK: handle_cloak,
    ActionKind.FIRE_DISRUPTOR: handle_fire_disruptor,
    ActionKind.REMOVE_LIMPET: handle_remove_limpet,
    ActionKind.LAUNCH_BEACON: handle_launch_beacon,
    ActionKind.TERRA_COLONISTS: handle_terra_colonists,
    ActionKind.DEPLOY_ATOMIC: _handle_deploy_atomic,
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
    ActionKind.SET_MILITARY_REACTION: _handle_set_military_reaction,
    ActionKind.DEPOSIT_TREASURY: _handle_deposit_treasury,
    ActionKind.WITHDRAW_TREASURY: _handle_withdraw_treasury,
    ActionKind.DEPOSIT_PLANET_DEFENSE: _handle_deposit_planet_defense,
    ActionKind.WITHDRAW_PLANET_DEFENSE: _handle_withdraw_planet_defense,
    ActionKind.SET_QUASAR_SECTOR: _handle_set_quasar_sector,
    ActionKind.SET_QUASAR_ATM: _handle_set_quasar_atm,
    ActionKind.PLANET_TRANSWARP: _handle_planet_transwarp,
    ActionKind.PLANET_BUY_TRANSPORTER: _handle_planet_buy_transporter,
    ActionKind.PLANET_TRANSPORT: _handle_planet_transport,
    ActionKind.PLANET_DESTROY: _handle_planet_destroy,
    ActionKind.RECALL_DEPLOYED: _handle_recall_deployed,
    ActionKind.SURRENDER: _handle_surrender,
    ActionKind.RETREAT: _handle_retreat,
    ActionKind.PAY_TOLL: _handle_pay_toll,
    ActionKind.SHIP_TRANSWARP: None,  # bound below; legacy handler refuses
}


def _bind_ship_tw() -> None:
    from .ship_transwarp import handle_ship_transwarp
    _DISPATCH[ActionKind.SHIP_TRANSWARP] = handle_ship_transwarp


def _bind_fleet() -> None:
    from .fleet import handle_sell_ship, handle_ship_transport
    _DISPATCH[ActionKind.SELL_SHIP] = handle_sell_ship  # legacy: the handlers answer "unsupported action"
    _DISPATCH[ActionKind.SHIP_TRANSPORT] = handle_ship_transport


def _bind_tow() -> None:
    from .tow import handle_tow_engage, handle_tow_release
    _DISPATCH[ActionKind.TOW_ENGAGE] = handle_tow_engage  # legacy: the handlers answer "unsupported action"
    _DISPATCH[ActionKind.TOW_RELEASE] = handle_tow_release


def _bind_planet_trade() -> None:
    from .planet_trade import handle_planet_trade
    _DISPATCH[ActionKind.PLANET_TRADE] = handle_planet_trade  # legacy: the handler answers "unsupported action"


def _bind_corpships() -> None:
    from .corpships import handle_set_corporate, handle_set_password, handle_set_personal
    _DISPATCH[ActionKind.SHIP_SET_CORPORATE] = handle_set_corporate
    _DISPATCH[ActionKind.SHIP_SET_PERSONAL] = handle_set_personal
    _DISPATCH[ActionKind.SHIP_SET_PASSWORD] = handle_set_password


def _bind_fed_handlers() -> None:
    from .fed import handle_apply_commission, handle_claim_reward, handle_post_reward
    _DISPATCH[ActionKind.APPLY_COMMISSION] = handle_apply_commission
    _DISPATCH[ActionKind.POST_REWARD] = handle_post_reward
    _DISPATCH[ActionKind.CLAIM_REWARD] = handle_claim_reward


_bind_ship_tw()
_bind_fleet()
_bind_tow()
_bind_planet_trade()
_bind_corpships()
_bind_fed_handlers()



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
            entry["price"] = port_buy_price(port, c, player.experience)
            entry["side"] = "buys_from_player"
        elif port.sells(c):
            entry["price"] = port_sell_price(port, c, player.experience)
            entry["side"] = "sells_to_player"
        stock[c.value] = entry
    # Prefer live universe.day, fall back to whatever was last recorded
    # (so a callsite that forgot to pass universe doesn't wipe freshness).
    last_day = (
        getattr(universe, "day", None)
        if universe is not None
        else (player.known_ports.get(sector_id) or {}).get("last_seen_day")
    )
    port_class = port.class_id.code
    snap_extra = {}
    special = getattr(port, "special", None)
    if special in ("alpha_centauri", "rylos"):
        port_class = "0"
        snap_extra["name"] = port.name
        snap_extra["special"] = special
        snap_extra["sells"] = ["fighters", "shields", "holds"]
    snapshot = {
        "class": port_class,
        "stock": stock,
        "last_seen_day": last_day,
        **snap_extra,
    }
    player.known_ports[sector_id] = snapshot

