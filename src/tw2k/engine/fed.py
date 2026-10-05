"""FedSpace police (FED_MODE). docs/playtests/fedspace/FEDSPACE_POLICE.md."""

from __future__ import annotations

import random
from typing import Any

from . import constants as K
from .actions import Action, ActionResult
from .models import EventKind, Federal, ShipClass, Universe
from .victory import rank_for


def fed_tw2002() -> bool:
    return K.FED_MODE == "tw2002"


__all__ = ["Federal"]  # re-exported: the model lives in models.py (typed Universe.federals)


FED_SPECS: tuple[tuple[str, str, int], ...] = (
    ("Zyrain", "Captain", K.FED_DENSITY_ZYRAIN),
    ("Nelson", "Admiral", K.FED_DENSITY_NELSON),
    ("Clausewitz", "Fleet Admiral", K.FED_DENSITY_CLAUSEWITZ),
)


def fed_rng(seed: int) -> random.Random:
    return random.Random(f"fed:{seed}")


def tow_rng(seed: int, day: int, player_id: str) -> random.Random:
    return random.Random(f"tow:{seed}:{day}:{player_id}")


def hop_rng(seed: int, day: int, name: str) -> random.Random:
    return random.Random(f"fed:{seed}:{day}:{name}")


def _bfs_hops(universe: Universe, start: int) -> dict[int, int]:
    hops = {start: 0}
    order = [start]
    i = 0
    while i < len(order):
        cur = order[i]
        i += 1
        for nxt in universe.sectors[cur].warps:
            nxt = int(nxt)
            if nxt in hops or nxt not in universe.sectors:
                continue
            hops[nxt] = hops[cur] + 1
            order.append(nxt)
    return hops


def _sector_has_player_fighters(universe: Universe, sector_id: int) -> bool:
    sector = universe.sectors.get(sector_id)
    if sector is None:
        return False
    dep = sector.fighters
    return dep is not None and int(dep.count) > 0


def _sector_has_mines(universe: Universe, sector_id: int) -> bool:
    sector = universe.sectors.get(sector_id)
    if sector is None:
        return False
    return any(int(m.count) > 0 for m in (sector.mines or []))


def _fed_blocked(universe: Universe, sector_id: int) -> bool:
    """f4/f25: fighters (and optional mines); never enter open challenges."""
    if _sector_has_player_fighters(universe, sector_id):
        return True
    if K.FED_BLOCKED_BY_MINES and _sector_has_mines(universe, sector_id):
        return True
    # f25: skip sectors with an open fighter challenge
    for p in universe.players.values():
        ch = getattr(p, "fighter_challenge", None)
        if ch and int(ch.get("sector_id", -1)) == int(sector_id):
            return True
    return False


def place_federals(universe: Universe) -> None:
    """Spawn the three Feds (f1/f3). No-op under legacy. Isolated rng."""
    if not fed_tw2002():
        universe.federals = []
        return
    seed = int(universe.config.seed)
    rng = fed_rng(seed)
    hops = _bfs_hops(universe, K.STARDOCK_SECTOR)
    candidates = [
        sid
        for sid, h in hops.items()
        if sid >= 11
        and h >= K.FED_START_MIN_HOPS
        and len(universe.sectors[sid].warps) >= 2
    ]
    candidates = sorted(candidates)
    picks: list[int] = []
    pool = list(candidates)
    for _ in range(2):
        if not pool:
            # Fallback: any sector 11+ with a warp
            pool = sorted(
                sid
                for sid in universe.sectors
                if sid >= 11 and universe.sectors[sid].warps
            )
        if not pool:
            picks.append(K.FED_ZYRAIN_START)
            continue
        choice = rng.choice(pool)
        picks.append(choice)
        pool = [s for s in pool if s != choice]

    federals: list[Federal] = []
    for (name, title, density), start in zip(
        FED_SPECS,
        [K.FED_ZYRAIN_START, picks[0] if picks else 11, picks[1] if len(picks) > 1 else 12],
        strict=False,
    ):
        federals.append(
            Federal(
                name=name,
                title=title,
                sector_id=int(start),
                density=int(density),
                home_sector=int(start),
            )
        )
    universe.federals = federals


def federals_in_sector(universe: Universe, sector_id: int) -> list[Federal]:
    return [f for f in getattr(universe, "federals", []) or [] if int(f.sector_id) == int(sector_id)]


def fed_density_bonus(universe: Universe, sector_id: int) -> int:
    """f2: add Fed densities under INFO tw2002."""
    if not fed_tw2002() or not K.info_tw2002():
        return 0
    return sum(int(f.density) for f in federals_in_sector(universe, sector_id))


def _ship_cloaked(player) -> bool:
    return bool(K.hardware_tw2002() and getattr(player.ship, "cloaked", False))


def _is_iss(player) -> bool:
    return player.ship.ship_class == ShipClass.IMPERIAL_STARSHIP


def _destroy_evil_iss(universe: Universe, pid: str, *, via: str) -> None:
    """f6/f22: Federal destroys an evil ISS."""
    from .combat import _destroy_ship

    player = universe.players.get(pid)
    if player is None or not player.alive or not _is_iss(player):
        return
    if int(player.alignment) >= 0:
        return
    if _ship_cloaked(player):
        return
    sector_id = player.sector_id
    universe.emit(
        EventKind.FED_REPOSSESS,
        actor_id=pid,
        sector_id=sector_id,
        payload={"reason": via, "victim": pid, "_witnesses": list(
            universe.sectors[sector_id].occupant_ids
        ) if sector_id in universe.sectors else [pid]},
        summary=f"Captain Zyrain repossesses {player.name}'s Imperial StarShip ({via})",
    )
    _destroy_ship(universe, pid, reason="federal", killer_id=None, by_other=True)


def check_evil_iss_in_sector(universe: Universe, sector_id: int) -> None:
    """f6: any Fed sharing a sector with an evil uncloaked ISS destroys it."""
    if not fed_tw2002():
        return
    if not federals_in_sector(universe, sector_id):
        return
    sector = universe.sectors.get(int(sector_id))
    if sector is None:
        return
    for pid in list(sector.occupant_ids):
        pl = universe.players.get(pid)
        if pl is None or not pl.alive:
            continue
        if _is_iss(pl) and int(pl.alignment) < 0 and not _ship_cloaked(pl):
            _destroy_evil_iss(universe, pid, via="fed_presence")


def check_evil_iss_presence_all(universe: Universe) -> None:
    if not fed_tw2002():
        return
    for fed in list(getattr(universe, "federals", []) or []):
        sector = universe.sectors.get(int(fed.sector_id))
        if sector is None:
            continue
        for pid in list(sector.occupant_ids):
            p = universe.players.get(pid)
            if p is None or not p.alive:
                continue
            if _is_iss(p) and int(p.alignment) < 0 and not _ship_cloaked(p):
                _destroy_evil_iss(universe, pid, via="fed_presence")


def maybe_fed_hail(universe: Universe, pid: str) -> None:
    """f23: first time alignment goes negative in an ISS."""
    if not fed_tw2002():
        return
    player = universe.players.get(pid)
    if player is None or not player.alive:
        return
    if not _is_iss(player) or int(player.alignment) >= 0:
        return
    if getattr(player, "fed_hail_sent", False):
        return
    player.fed_hail_sent = True
    universe.emit(
        EventKind.FED_HAIL,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"message": K.FED_HAIL_MESSAGE},
        summary=f"Captain Zyrain hails {player.name}: {K.FED_HAIL_MESSAGE}",
    )


def check_iss_repo_on_move(universe: Universe, pid: str) -> None:
    """f22: after a warp, destroy evil ISS per ISS_REPO_MODE (unless cloaked)."""
    if not fed_tw2002():
        return
    player = universe.players.get(pid)
    if player is None or not player.alive:
        return
    maybe_fed_hail(universe, pid)
    if not _is_iss(player) or int(player.alignment) >= 0:
        return
    if _ship_cloaked(player):
        return
    if K.ISS_REPO_MODE == "mbbs":
        # Safe only in a sector holding this pilot's own deployed fighters.
        sector = universe.sectors.get(player.sector_id)
        dep = sector.fighters if sector is not None else None
        if dep is not None and int(dep.count) > 0 and dep.owner_id == pid:
            # Still subject to f6 if a Fed is here — checked separately.
            check_evil_iss_presence_all(universe)
            return
    _destroy_evil_iss(universe, pid, via="evil_iss_move")
    check_evil_iss_presence_all(universe)


def _legal_fed_hops(universe: Universe, fed: Federal) -> list[int]:
    sector = universe.sectors.get(int(fed.sector_id))
    if sector is None:
        return []
    out = []
    for wid in sector.warps:
        wid = int(wid)
        if wid in universe.sectors and not _fed_blocked(universe, wid):
            out.append(wid)
    return sorted(out)


def tick_federals(universe: Universe) -> None:
    """f5: Nelson/Clausewitz wander; Zyrain returns home after an incident."""
    if not fed_tw2002():
        return
    seed = int(universe.config.seed)
    day = int(universe.day)
    for fed in list(getattr(universe, "federals", []) or []):
        if fed.name == "Zyrain":
            if fed.on_incident or int(fed.sector_id) != int(fed.home_sector):
                fed.sector_id = int(fed.home_sector)
                fed.on_incident = False
            continue
        rng = hop_rng(seed, day, fed.name)
        for _ in range(int(K.FED_HOPS_PER_DAY)):
            choices = _legal_fed_hops(universe, fed)
            if not choices:
                break  # trapped
            fed.sector_id = int(rng.choice(choices))
            check_evil_iss_presence_all(universe)


def summon_zyrain(universe: Universe, sector_id: int) -> Federal | None:
    """f8: teleport Zyrain to the incident sector (ignores fighters)."""
    if not fed_tw2002():
        return None
    for fed in getattr(universe, "federals", []) or []:
        if fed.name == "Zyrain":
            fed.sector_id = int(sector_id)
            fed.on_incident = True
            universe.emit(
                EventKind.FED_ZYRAIN,
                actor_id=None,
                sector_id=sector_id,
                payload={"fed": "Zyrain", "sector": sector_id},
                summary=f"Captain Zyrain warps into sector {sector_id}!",
            )
            return fed
    return None


def _always_escape_destroy(universe: Universe, pid: str, reason: str) -> None:
    """f7: pod the attacker; always escape regardless of DEATH_MODE pod odds."""
    from .combat import _destroy_ship

    _destroy_ship(
        universe, pid, reason=reason, killer_id=None, by_other=True, always_escape=True
    )


def attack_federal(
    universe: Universe, pid: str, fed_name: str, action_args: dict | None = None
) -> ActionResult:
    """f7: attack a Federal — suicide pod, -10 align, -10% exp."""
    player = universe.players[pid]
    feds = [f for f in getattr(universe, "federals", []) or [] if f.name == fed_name]
    if not feds or int(feds[0].sector_id) != int(player.sector_id):
        return ActionResult(ok=False, error="target not in this sector")
    cost = int(K.TURN_COST["attack"])
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    if K.combat_tw2002() and action_args is not None:
        # Same gate as the legal list and a player attack: fighters aboard, not photon-offline, qty 1..cap.
        from .actions import Action as _Action
        from .runner import _attack_qty
        _qty, bad = _attack_qty(player, _Action(kind="attack", args=dict(action_args)))
        if bad is not None:
            return bad
    player.alignment = int(player.alignment) - int(K.FED_ATTACK_ALIGN_PENALTY)
    if not K.death_tw2002():
        # cabal formulas.html: "Attacking a Fed: -10, but you get podded | Loose 10%" and, same page,
        # "If you are podded, you loose 10% of your exp" - the 10% IS the pod. DEATH_MODE tw2002
        # already takes it in the forced pod (POD_EXP_LOSS); only legacy death (no pod loss) needs it here.
        exp = int(player.experience)
        player.experience = int(exp * K.FED_ATTACK_EXP_KEEP)  # floor toward zero for non-neg
    _always_escape_destroy(universe, pid, reason="federal")
    return ActionResult(ok=True, turns_spent=cost)


def protect_fedspace_attack(universe: Universe, pid: str, target) -> ActionResult:
    """f8: Zyrain response to attacking a fedsafe trader in FedSpace."""
    player = universe.players[pid]
    # Always keep today's -200 so RANK tests do not drift.
    player.alignment = int(player.alignment) - 200
    summon_zyrain(universe, player.sector_id)
    universe.emit(
        EventKind.FED_RESPONSE,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"reason": "attempted PvP in FedSpace"},
        summary=f"Federation warns {player.name} — no combat in FedSpace!",
    )
    if K.FED_PROTECT_PUNISH == "pod" and fed_tw2002():
        _always_escape_destroy(universe, pid, reason="federal")
        return ActionResult(ok=False, error="FedSpace — Captain Zyrain pods you")
    return ActionResult(ok=False, error="FedSpace — combat forbidden")


def _tow_destinations(universe: Universe) -> list[int]:
    if K.FED_TOW_DEST == "msl":
        msl = [int(s) for s in (getattr(universe, "msl_sectors", None) or [])
               if int(s) not in K.FEDSPACE_SECTORS]
        if msl:
            return sorted(msl)
    return sorted(
        sid for sid in universe.sectors
        if sid not in K.FEDSPACE_SECTORS and sid != K.STARDOCK_SECTOR
    )


def _tow_player(universe: Universe, pid: str, *, reason: str) -> int | None:
    """Move player out of FedSpace; returns destination or None."""
    player = universe.players.get(pid)
    if player is None or not player.alive:
        return None
    from_sid = int(player.sector_id)
    dests = _tow_destinations(universe)
    if not dests:
        return None
    rng = tow_rng(int(universe.config.seed), int(universe.day), pid)
    dest = int(rng.choice(dests))
    try:
        universe.sectors[from_sid].occupant_ids.remove(pid)
    except ValueError:
        pass
    player.sector_id = dest
    player.end_port_visit()
    player.planet_landed = None
    player.fighter_challenge = None
    if pid not in universe.sectors[dest].occupant_ids:
        universe.sectors[dest].occupant_ids.append(pid)
    player.known_sectors.add(dest)
    player.known_warps[dest] = list(universe.sectors[dest].warps)
    # Cloak stays on (f13).
    universe.emit(
        EventKind.FED_TOW,
        actor_id=pid,
        sector_id=from_sid,
        payload={"from": from_sid, "to": dest, "reason": reason},
        summary=f"Feds tow {player.name} from {from_sid} to {dest} ({reason})",
    )
    return dest


def run_tows(universe: Universe) -> int:
    """f11-f14: Extern tows after overnight retreats / class0 MSL sweep."""
    if not fed_tw2002():
        return 0
    towed = 0
    # f11: arms limit — anyone in FedSpace with fighters > limit
    for pid in sorted(universe.players):
        p = universe.players[pid]
        if not p.alive:
            continue
        if int(p.sector_id) not in K.FEDSPACE_SECTORS:
            continue
        if int(p.ship.fighters) > int(K.FED_TOW_FIGHTER_LIMIT):
            if _tow_player(universe, pid, reason="arms") is not None:
                towed += 1
    # f12: parking — per FedSpace sector, keep at most FED_SHIPS_PER_SECTOR;
    # tow latest arrivals first (reverse occupant_ids).
    limit = int(K.FED_SHIPS_PER_SECTOR)
    for sid in sorted(K.FEDSPACE_SECTORS):
        sector = universe.sectors.get(sid)
        if sector is None:
            continue
        # Live occupants still in this sector (and still alive players)
        occupants = [
            oid for oid in sector.occupant_ids
            if oid in universe.players and universe.players[oid].alive
            and int(universe.players[oid].sector_id) == int(sid)
        ]
        if len(occupants) <= limit:
            continue
        # Latest arrivals are at the end of occupant_ids; tow from the end.
        excess = list(reversed(occupants))[: len(occupants) - limit]
        for oid in excess:
            # Re-check still here (a prior tow in this loop may have moved them — shouldn't)
            if int(universe.players[oid].sector_id) != int(sid):
                continue
            if _tow_player(universe, oid, reason="parking") is not None:
                towed += 1
    return towed


def posted_total(universe: Universe, target_id: str) -> int:
    rows = (getattr(universe, "posted_rewards", None) or {}).get(target_id) or []
    return sum(int(r.get("amount", 0)) for r in rows)


def most_wanted(universe: Universe) -> list[dict[str, Any]]:
    """f20: up to 10 evil players; titles not alignment numbers."""
    rows = []
    for p in universe.players.values():
        if not p.alive or int(p.alignment) >= 0:
            continue
        rewards = (getattr(universe, "posted_rewards", None) or {}).get(p.id) or []
        rows.append({
            "id": p.id,
            "name": p.name,
            "title": rank_for(int(p.experience), int(p.alignment)),
            "corp": None,
            "reward_count": len(rewards),
            "total_reward": sum(int(r.get("amount", 0)) for r in rewards),
            "_align": int(p.alignment),
        })
    rows.sort(key=lambda r: (r["_align"], -r["total_reward"], r["id"]))
    out = []
    for r in rows[:10]:
        out.append({k: v for k, v in r.items() if not k.startswith("_")})
    return out


def reward_targets(universe: Universe, poster_id: str) -> list[str]:
    """Targets the poster may name under REWARD_TARGET_RULE."""
    if K.REWARD_TARGET_RULE == "listed":
        return [r["id"] for r in most_wanted(universe) if r["id"] != poster_id]
    return sorted(
        pid for pid, p in universe.players.items()
        if pid != poster_id and p.alive and int(p.alignment) < 0
    )


def police_ok(universe: Universe, pid: str) -> tuple[bool, str]:
    if not fed_tw2002():
        return False, "unsupported action"
    player = universe.players[pid]
    if int(player.sector_id) != K.STARDOCK_SECTOR:
        return False, "Police HQ is in sector 1"
    if int(player.alignment) < int(K.POLICE_MIN_ALIGNMENT):
        return False, "alignment too low for Police HQ"
    if getattr(player, "fighter_challenge", None) is not None:
        from .combat import live_challenge
        if live_challenge(universe, pid) is not None:
            return False, "resolve the fighter challenge first"
    return True, ""


def handle_apply_commission(universe: Universe, pid: str, action: Action) -> ActionResult:
    ok, err = police_ok(universe, pid)
    if not ok:
        return ActionResult(ok=False, error=err)
    player = universe.players[pid]
    align = int(player.alignment)
    if align < int(K.COMMISSION_APPLY_MIN) or align >= int(K.COMMISSION_ALIGNMENT):
        return ActionResult(ok=False, error="commission requires alignment 500..999")
    if K.COMMISSION_ONCE and getattr(player, "commission_used", False):
        return ActionResult(ok=False, error="commission already used")
    player.alignment = int(K.COMMISSION_ALIGNMENT)
    player.commission_used = True
    universe.emit(
        EventKind.COMMISSION_GRANTED,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"alignment": player.alignment},
        summary=f"{player.name} receives a Federal Commission (alignment {player.alignment})",
    )
    return ActionResult(ok=True, turns_spent=0)


def handle_post_reward(universe: Universe, pid: str, action: Action) -> ActionResult:
    ok, err = police_ok(universe, pid)
    if not ok:
        return ActionResult(ok=False, error=err)
    player = universe.players[pid]
    target_id = action.args.get("target_id") or action.args.get("target")
    raw_amt = action.args.get("amount")
    try:
        amount = int(raw_amt)
    except (TypeError, ValueError):
        return ActionResult(ok=False, error="invalid reward amount")
    if amount < int(K.REWARD_MIN):
        return ActionResult(ok=False, error=f"reward minimum is {K.REWARD_MIN}")
    if amount > int(player.credits):
        return ActionResult(ok=False, error="insufficient credits")
    if target_id not in reward_targets(universe, pid):
        return ActionResult(ok=False, error="invalid reward target")
    target = universe.players[target_id]
    if int(target.alignment) >= 0:
        return ActionResult(ok=False, error="target is not evil")
    player.credits -= amount
    gain = amount // int(K.REWARD_ALIGN_PER)
    player.alignment = int(player.alignment) + gain
    if not hasattr(universe, "posted_rewards") or universe.posted_rewards is None:
        universe.posted_rewards = {}
    universe.posted_rewards.setdefault(target_id, []).append(
        {"poster_id": pid, "amount": amount, "day": int(universe.day)}
    )
    universe.emit(
        EventKind.REWARD_POSTED,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"target_id": target_id, "amount": amount, "align_gain": gain},
        summary=f"{player.name} posts {amount} cr reward on {target.name}",
    )
    return ActionResult(ok=True, turns_spent=0)


def handle_claim_reward(universe: Universe, pid: str, action: Action) -> ActionResult:
    ok, err = police_ok(universe, pid)
    if not ok:
        return ActionResult(ok=False, error=err)
    pending = int((getattr(universe, "pending_rewards", None) or {}).get(pid, 0) or 0)
    if pending <= 0:
        return ActionResult(ok=False, error="no pending reward to claim")
    player = universe.players[pid]
    player.credits = int(player.credits) + pending
    universe.pending_rewards[pid] = 0
    universe.emit(
        EventKind.REWARD_CLAIMED,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"amount": pending},
        summary=f"{player.name} claims {pending} cr in Federation bounties",
    )
    return ActionResult(ok=True, turns_spent=0)


def record_bounty_on_death(universe: Universe, victim_id: str, killer_id: str | None, outcome: str) -> None:
    """f19: only a real death (not pod) credits the killer's pending_rewards."""
    if not fed_tw2002():
        return
    if outcome != "ship_destroyed":
        return
    if not killer_id or killer_id not in universe.players or killer_id == victim_id:
        return
    rewards = (getattr(universe, "posted_rewards", None) or {}).get(victim_id) or []
    if not rewards:
        return
    total = sum(int(r.get("amount", 0)) for r in rewards)
    if total <= 0:
        return
    if not hasattr(universe, "pending_rewards") or universe.pending_rewards is None:
        universe.pending_rewards = {}
    universe.pending_rewards[killer_id] = int(universe.pending_rewards.get(killer_id, 0)) + total
    universe.posted_rewards[victim_id] = []


def commission_eligible(player) -> bool:
    align = int(player.alignment)
    if align < int(K.COMMISSION_APPLY_MIN) or align >= int(K.COMMISSION_ALIGNMENT):
        return False
    if K.COMMISSION_ONCE and getattr(player, "commission_used", False):
        return False
    return True


def police_observation(universe: Universe, player) -> dict[str, Any] | None:
    if not fed_tw2002() or int(player.sector_id) != K.STARDOCK_SECTOR:
        return None
    if int(player.alignment) < int(K.POLICE_MIN_ALIGNMENT):
        return None
    return {
        "most_wanted": most_wanted(universe),
        "my_pending_reward": int((getattr(universe, "pending_rewards", None) or {}).get(player.id, 0) or 0),
        "commission": {
            "eligible": commission_eligible(player),
            "used": bool(getattr(player, "commission_used", False)),
        },
    }


def fedspace_hint(universe: Universe, player) -> dict[str, Any] | None:
    if not fed_tw2002() or int(player.sector_id) not in K.FEDSPACE_SECTORS:
        return None
    sector = universe.sectors[player.sector_id]
    # Fog (h15): count only the ships this seat can see - itself plus uncloaked live ships.
    # Cloaked ships still count toward the real parking limit at Extern (f13); the seat cannot know.
    visible = [
        oid for oid in sector.occupant_ids
        if oid in universe.players and universe.players[oid].alive
        and (oid == player.id or not _ship_cloaked(universe.players[oid]))
    ]
    ships_here = len(visible)
    limit = int(K.FED_SHIPS_PER_SECTOR)
    my_f = int(player.ship.fighters)
    arms = my_f > int(K.FED_TOW_FIGHTER_LIMIT)
    # f12: the latest arrivals beyond the limit go (as far as this seat can see).
    parking = player.id in visible and visible.index(player.id) >= limit
    return {
        "ships_here": ships_here,
        "limit": limit,
        "my_fighters": my_f,
        "tow_fighter_limit": int(K.FED_TOW_FIGHTER_LIMIT),
        "will_be_towed": bool(arms or parking),
    }


def federal_briefs(universe: Universe, sector_id: int) -> list[dict[str, str]]:
    return [
        {"name": f.name, "title": f.title, "kind": "federal"}
        for f in federals_in_sector(universe, sector_id)
    ]


def police_legal_specs(universe: Universe, player_id: str) -> list[tuple[str, bool, str, dict]]:
    """Return (kind_value, legal, reason, params) for the three police verbs."""
    player = universe.players[player_id]
    specs: list[tuple[str, bool, str, dict]] = []
    ok, err = police_ok(universe, player_id)
    if not ok:
        reason = err
    elif not commission_eligible(player):
        reason = "commission requires alignment 500..999 (once)"
    else:
        reason = ""
    specs.append(("apply_commission", ok and commission_eligible(player), reason, {}))
    targets = reward_targets(universe, player_id) if ok else []
    if not ok:
        reason = err
    elif not targets:
        reason = "no evil targets to post a reward on"
    elif int(player.credits) < int(K.REWARD_MIN):
        reason = f"need at least {K.REWARD_MIN} credits"
    else:
        reason = ""
    post_legal = ok and bool(targets) and int(player.credits) >= int(K.REWARD_MIN)
    specs.append((
        "post_reward",
        post_legal,
        reason,
        {
            "target_id": {"type": "str", "required": True, "choices": targets},
            "amount": {"type": "int", "required": True, "min": int(K.REWARD_MIN), "max": int(player.credits)},
        },
    ))
    pending = int((getattr(universe, "pending_rewards", None) or {}).get(player_id, 0) or 0)
    if not ok:
        reason = err
    elif pending <= 0:
        reason = "no pending reward to claim"
    else:
        reason = ""
    specs.append(("claim_reward", ok and pending > 0, reason, {}))
    return specs
