"""Ferrengi NPC pirates: spawn + roam + hunt + tribute (ferrengi-aliens-v1).

Called from `runner.tick_day` after port regeneration:

    * `place_ferrengal(universe)` — once at generation (from universe.py)
    * `_spawn_ferrengi(universe)` — daily raiders
    * `_ferrengi_roam_and_hunt(universe)` — move / encounter / auto-combat
    * `_ferrengi_regen(universe)` — 20% toward hull max (tw2002)
    * tribute helpers used by runner surrender / retreat / attack paths

FERRENGI_MODE legacy keeps the pre-slice formulas and auto-combat.
"""

from __future__ import annotations

import random
from collections import deque

from . import constants as K
from .combat import _resolve_ship_combat_attacker_npc
from .models import (
    EventKind,
    FerrengiShip,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    ShipClass,
    Universe,
)


def _ferrengi_rng(seed: int) -> random.Random:
    return random.Random(f"ferrengi:{seed}")


def _tw_actor(ferr_id: str | None = None) -> dict:
    """Event actor fields added by ferrengi-aliens-v1; legacy events keep their old shape."""
    if not K.ferrengi_tw2002():
        return {} if ferr_id is None else {"actor_id": ferr_id}
    out = {"actor_kind": "ferrengi"}
    if ferr_id is not None:
        out["actor_id"] = ferr_id
    return out


def _ferrengal_rng(seed: int) -> random.Random:
    return random.Random(f"ferrengal:{seed}")


def _bfs_hops(universe: Universe, start: int) -> dict[int, int]:
    hops = {start: 0}
    q: deque[int] = deque([start])
    while q:
        cur = q.popleft()
        sec = universe.sectors.get(cur)
        if sec is None:
            continue
        for w in sec.warps:
            if w not in hops:
                hops[w] = hops[cur] + 1
                q.append(w)
    return hops


def hull_for_aggression(aggression: int) -> str:
    a = int(aggression)
    if a >= 8:
        return K.FERRENGI_HULL_DREAD
    if a >= 5:
        return K.FERRENGI_HULL_CRUISER
    return K.FERRENGI_HULL_ASSAULT


def hull_spec(hull: str) -> dict:
    return dict(K.FERRENGI_HULL_SPECS.get(hull) or K.FERRENGI_HULL_SPECS[K.FERRENGI_HULL_ASSAULT])


def ferrengi_density(ferr: FerrengiShip) -> int:
    if K.ferrengi_tw2002() and ferr.hull:
        return int(hull_spec(ferr.hull)["density"])
    return int(K.DENSITY_PER_SHIP)


def ferrengi_odds(ferr: FerrengiShip) -> float:
    if K.ferrengi_tw2002() and ferr.hull:
        return float(K.FERRENGI_ODDS_BY_HULL.get(ferr.hull, K.FERRENGI_COMBAT_ODDS))
    return float(K.FERRENGI_COMBAT_ODDS)


def _ferrengi_strength_scale(universe: Universe) -> float:
    ramp_days = max(0, int(getattr(universe.config, "ferrengi_strength_ramp_days", 0) or 0))
    min_scale = float(
        getattr(universe.config, "ferrengi_min_strength_scale", K.FERRENGI_MIN_STRENGTH_SCALE)
    )
    min_scale = max(0.0, min(1.0, min_scale))
    if ramp_days <= 0:
        return 1.0
    progress = max(0.0, min(1.0, float(universe.day) / float(ramp_days)))
    return min_scale + (1.0 - min_scale) * progress


def _scaled_ferrengi_stats(universe: Universe, aggression: int, hull: str = "") -> tuple[int, int]:
    """Scale fighters/shields by day ramp; tw2002 caps at hull max."""
    scale = _ferrengi_strength_scale(universe)
    if K.ferrengi_tw2002() and hull:
        spec = hull_spec(hull)
        fighters = max(1, int(int(spec["max_fighters"]) * scale))
        shields = max(0, int(int(spec["max_shields"]) * scale))
        return fighters, shields
    fighters = max(1, int((100 + aggression * 300) * scale))
    shields = max(0, int(aggression * 50 * scale))
    return fighters, shields


def _legacy_ship_class(aggression: int) -> ShipClass:
    return ShipClass.BATTLESHIP if aggression >= 8 else ShipClass.MISSILE_FRIGATE


def _make_ferrengi(
    universe: Universe,
    *,
    fid: str,
    sid: int,
    aggression: int,
) -> FerrengiShip:
    hull = hull_for_aggression(aggression) if K.ferrengi_tw2002() else ""
    fighters, shields = _scaled_ferrengi_stats(universe, aggression, hull)
    credits = 0
    if K.ferrengi_tw2002():
        credits = int(aggression) * int(K.FERRENGI_SPAWN_CREDITS_PER_AGG)
    label = hull_spec(hull)["label"] if hull else "Ferrengi Raider"
    return FerrengiShip(
        id=fid,
        name=f"{label} {fid[-4:].upper()}",
        sector_id=sid,
        aggression=aggression,
        fighters=fighters,
        shields=shields,
        ship_class=_legacy_ship_class(aggression),
        hull=hull,
        credits=credits,
        cargo={},
    )


def place_ferrengal(universe: Universe) -> None:
    """n6/n7: pick Ferrengal home, plant mines + fighters. No-op under legacy or with Ferrengi off."""
    if not K.ferrengi_tw2002() or not getattr(universe.config, "enable_ferrengi", True):
        universe.ferrengal_sector = None
        return
    if getattr(universe, "ferrengal_sector", None):
        return
    seed = int(universe.config.seed)
    rng = _ferrengal_rng(seed)
    hops = _bfs_hops(universe, K.STARDOCK_SECTOR)
    # Prefer dead-ends (out-degree 1) far from StarDock.
    dead = sorted(
        sid
        for sid, h in hops.items()
        if sid >= 11
        and h >= K.FERRENGAL_MIN_HOPS
        and len(universe.sectors[sid].warps) == 1
    )
    pool = dead
    if not pool:
        # Near-dead-end: minimum out-degree among far sectors
        far = [
            sid
            for sid, h in hops.items()
            if sid >= 11 and h >= K.FERRENGAL_MIN_HOPS and universe.sectors[sid].warps
        ]
        if far:
            min_deg = min(len(universe.sectors[s].warps) for s in far)
            pool = sorted(s for s in far if len(universe.sectors[s].warps) == min_deg)
    if not pool:
        pool = sorted(sid for sid in universe.sectors if sid >= 11 and universe.sectors[sid].warps)
    if not pool:
        universe.ferrengal_sector = None
        return
    sid = int(rng.choice(pool))
    universe.ferrengal_sector = sid
    sector = universe.sectors[sid]
    # Clear any prior mines then plant Ferrengal mines.
    sector.mines = [
        m for m in sector.mines if m.owner_id != K.FERRENGI_OWNER_ID
    ]
    sector.mines.append(
        MineDeployment(owner_id=K.FERRENGI_OWNER_ID, kind=MineType.ARMID, count=int(K.FERRENGAL_MINES))
    )
    # Defensive Ferrengi fighters (UNVERIFIED count).
    sector.fighters = FighterDeployment(
        owner_id=K.FERRENGI_OWNER_ID,
        count=int(K.FERRENGAL_FIGHTERS),
        mode=FighterMode.DEFENSIVE,
    )
    universe.emit(
        EventKind.FERRENGAL_PLACE,
        sector_id=sid,
        actor_kind="ferrengi",
        payload={"sector_id": sid, "mines": int(K.FERRENGAL_MINES), "fighters": int(K.FERRENGAL_FIGHTERS)},
        summary=f"Ferrengal established in sector {sid}",
    )


def _sectors_near_ferrengal(universe: Universe, radius: int) -> list[int]:
    home = getattr(universe, "ferrengal_sector", None)
    if not home:
        return []
    hops = _bfs_hops(universe, int(home))
    return sorted(
        sid
        for sid, h in hops.items()
        if h <= radius and sid not in K.FEDSPACE_SECTORS and sid >= 11
    )


def _pick_spawn_sector(universe: Universe, rng: random.Random) -> int:
    deep_start = max(K.FEDSPACE_SECTORS) + 1
    max_sid = universe.config.universe_size
    if K.ferrengi_tw2002():
        near = _sectors_near_ferrengal(universe, K.FERRENGAL_SPAWN_RADIUS)
        if near:
            return int(rng.choice(near))
    return int(rng.randint(deep_start, max_sid))


def _spawn_ferrengi(universe: Universe) -> None:
    rng = universe.rng
    per_day = max(0, int(getattr(universe.config, "ferrengi_per_day", 0) or 0))
    max_alive = getattr(universe.config, "ferrengi_max_alive", None)
    if max_alive is not None:
        max_alive = max(0, int(max_alive))
        alive = sum(1 for f in universe.ferrengi.values() if f.alive)
        if alive >= max_alive:
            return
        per_day = min(per_day, max_alive - alive)

    for i in range(per_day):
        sid = _pick_spawn_sector(universe, rng)
        aggr = rng.randint(1, K.FERRENGI_MAX_AGGRESSION)
        fid = f"ferr_{universe.day}_{i}_{sid}"
        while fid in universe.ferrengi:
            fid = f"ferr_{universe.day}_{i}_{sid}_{rng.randint(1, 9999)}"
        ship = _make_ferrengi(universe, fid=fid, sid=sid, aggression=aggr)
        universe.ferrengi[fid] = ship
        payload = {
            "id": fid,
            "aggression": aggr,
            "fighters": ship.fighters,
        }
        if ship.hull:
            payload["hull"] = ship.hull
        universe.emit(
            EventKind.FERRENGI_SPAWN,
            sector_id=sid,
            **_tw_actor(),
            payload=payload,
            summary=f"Ferrengi raider appeared in {sid} (aggression {aggr})",
        )


def _ferrengi_by_name(universe: Universe, key: str):
    for f in universe.ferrengi.values():
        if f.id == key or f.name == key:
            return f
    return None


def _ferrengi_regen(universe: Universe) -> None:
    """n9: each living Ferrengi regains floor(max * REGEN_PCT) toward hull max."""
    if not K.ferrengi_tw2002():
        return
    pct = float(K.FERRENGI_REGEN_PCT)
    for ferr in universe.ferrengi.values():
        if not ferr.alive or not ferr.hull:
            continue
        spec = hull_spec(ferr.hull)
        max_f = int(spec["max_fighters"])
        max_s = int(spec["max_shields"])
        gain_f = int(max_f * pct)
        gain_s = int(max_s * pct)
        before_f, before_s = int(ferr.fighters), int(ferr.shields)
        ferr.fighters = min(max_f, before_f + gain_f)
        ferr.shields = min(max_s, before_s + gain_s)
        if ferr.fighters != before_f or ferr.shields != before_s:
            universe.emit(
                EventKind.FERRENGI_REGEN,
                sector_id=ferr.sector_id,
                actor_id=ferr.id,
                actor_kind="ferrengi",
                payload={
                    "id": ferr.id,
                    "fighters": ferr.fighters,
                    "shields": ferr.shields,
                },
                summary=f"Ferrengi {ferr.name} regenerated in {ferr.sector_id}",
            )


def _apply_mines_to_ferrengi(universe: Universe, ferr: FerrengiShip) -> None:
    """n12: Ferrengi hit armid mines on entry."""
    if not K.ferrengi_tw2002() or not K.FERRENGI_HIT_MINES:
        return
    sector = universe.sectors.get(ferr.sector_id)
    if sector is None:
        return
    from .hardware import armid_detonation_hits

    rng = universe.rng
    damage = 0
    for md in list(sector.mines):
        if md.kind != MineType.ARMID or int(md.count) <= 0:
            continue
        # Own Ferrengal mines do not hurt Ferrengi.
        if md.owner_id == K.FERRENGI_OWNER_ID:
            continue
        hits, dmg_each = armid_detonation_hits(md.count, rng)
        damage += hits * dmg_each
    if damage <= 0:
        return
    soaked = min(int(ferr.shields), damage)
    ferr.shields = int(ferr.shields) - soaked
    rest = damage - soaked
    if rest > 0:
        ferr.fighters = max(0, int(ferr.fighters) - rest)
    if int(ferr.fighters) <= 0 and int(ferr.shields) <= 0:
        ferr.alive = False
        universe.emit(
            EventKind.SHIP_DESTROYED,
            actor_id=ferr.id,
            actor_kind="ferrengi",
            sector_id=ferr.sector_id,
            payload={"victim": ferr.id, "kind": "ferrengi", "reason": "mines"},
            summary=f"Ferrengi {ferr.name} destroyed by mines in {ferr.sector_id}",
        )


def _player_cloaked(player) -> bool:
    return bool(
        not K.FERRENGI_SEES_CLOAK
        and K.hardware_tw2002()
        and getattr(player.ship, "cloaked", False)
    )


def open_ferrengi_encounter(universe: Universe, ferr: FerrengiShip, victim) -> None:
    """n14: open tribute encounter instead of auto-combat."""
    victim.ferrengi_encounter = {
        "ferr_id": ferr.id,
        "sector_id": int(ferr.sector_id),
        "ferr_fighters": int(ferr.fighters),
        "ferr_hull": ferr.hull or "",
        "ferr_name": ferr.name,
    }
    universe.emit(
        EventKind.FERRENGI_ENCOUNTER,
        actor_id=ferr.id,
        actor_kind="ferrengi",
        sector_id=ferr.sector_id,
        payload={
            "victim": victim.id,
            "ferr_id": ferr.id,
            "ferr_fighters": int(ferr.fighters),
            "ferr_hull": ferr.hull or "",
            "your_fighters": int(victim.ship.fighters),
        },
        summary=(
            f"** Ferrengi Fighter Attack! ** {ferr.name} boards {victim.name} in {ferr.sector_id}: "
            f"flee, attack or surrender"
        ),
    )


def live_ferrengi_encounter(universe: Universe, pid: str, *, settle: bool = False):
    player = universe.players.get(pid)
    if player is None:
        return None
    enc = getattr(player, "ferrengi_encounter", None)
    if not enc:
        return None
    ferr = universe.ferrengi.get(enc.get("ferr_id", ""))
    stale = (
        not K.ferrengi_tw2002()
        or K.FERRENGI_ENCOUNTER != "tribute"
        or not player.alive
        or ferr is None
        or not ferr.alive
        or int(ferr.sector_id) != int(player.sector_id)
        or int(enc.get("sector_id", -1)) != int(player.sector_id)
    )
    if stale:
        if settle:
            player.ferrengi_encounter = None
        return None
    return enc


def apply_ferrengi_tribute(universe: Universe, pid: str, *, ignored: bool = False) -> dict:
    """n15: surrender cargo, some holds, then credits. ``ignored``: the seat acted without answering."""
    player = universe.players[pid]
    enc = live_ferrengi_encounter(universe, pid)
    if enc is None:
        return {"ok": False, "error": "no Ferrengi boards you here"}
    ferr = universe.ferrengi[enc["ferr_id"]]
    taken_cargo: dict[str, int] = {}
    for good in ("fuel_ore", "organics", "equipment"):
        qty = int(player.ship.cargo.get(good, 0) or 0)
        if qty > 0:
            player.ship.cargo[good] = 0
            ferr.cargo[good] = int(ferr.cargo.get(good, 0) or 0) + qty
            taken_cargo[good] = qty
    holds_stolen = 0
    # "some of your holds" — reduce max holds, with floor of ship-class minimum 1.
    steal_n = int(K.FERRENGI_TRIBUTE_HOLDS)
    if player.ship.holds > 1 and steal_n > 0:
        holds_stolen = min(steal_n, max(0, int(player.ship.holds) - 1))
        player.ship.holds = int(player.ship.holds) - holds_stolen
    credits_taken = 0
    if not taken_cargo:
        credits_taken = int(int(player.credits) * float(K.FERRENGI_TRIBUTE_CREDIT_PCT))
        credits_taken = max(0, min(int(player.credits), credits_taken))
        player.credits = int(player.credits) - credits_taken
        ferr.credits = int(ferr.credits) + credits_taken
    player.ferrengi_encounter = None
    universe.emit(
        EventKind.FERRENGI_TRIBUTE,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={
            "ferr_id": ferr.id,
            "cargo": taken_cargo,
            "holds_stolen": holds_stolen,
            "credits": credits_taken,
            **({"ignored": True} if ignored else {}),
        },
        summary=(
            f"{player.name} surrendered tribute to {ferr.name}: "
            f"cargo={taken_cargo or '-'} holds={holds_stolen} credits={credits_taken}"
        ),
    )
    return {
        "ok": True,
        "cargo": taken_cargo,
        "holds_stolen": holds_stolen,
        "credits": credits_taken,
    }


def record_ferrengi_grudge(universe: Universe, player_id: str) -> None:
    if not K.ferrengi_tw2002():
        return
    grudges = getattr(universe, "ferrengi_grudges", None)
    if grudges is None:
        universe.ferrengi_grudges = set()
        grudges = universe.ferrengi_grudges
    grudges.add(player_id)


def clear_ferrengi_encounter(universe: Universe, pid: str) -> None:
    player = universe.players.get(pid)
    if player is not None:
        player.ferrengi_encounter = None


def _ferrengi_roam_and_hunt(universe: Universe) -> None:
    """Each living Ferrengi: maybe move 1 sector; if a player is co-located, attack/encounter."""
    rng = universe.rng
    grace_days = getattr(universe.config, "ferrengi_grace_days", None)
    grace_days = K.FERRENGI_STARTUP_GRACE_DAYS if grace_days is None else max(0, int(grace_days))
    grace_active = bool(
        getattr(universe.config, "all_start_stardock", False)
        and universe.day < grace_days
    )
    grudges = getattr(universe, "ferrengi_grudges", None) or set()

    for ferr in list(universe.ferrengi.values()):
        if not ferr.alive:
            continue
        sec = universe.sectors.get(ferr.sector_id)
        if sec is None:
            continue
        if rng.random() < K.FERRENGI_MOVE_PROB:
            choices = [w for w in sec.warps if w not in K.FEDSPACE_SECTORS]
            # n12: Ferrengi ignore player fighters (no filter unless FERRENGI_FIGHTER_BLOCK).
            if K.ferrengi_tw2002() and K.FERRENGI_FIGHTER_BLOCK:
                choices = [
                    w
                    for w in choices
                    if universe.sectors[w].fighters is None
                    or int(universe.sectors[w].fighters.count) <= 0
                    or universe.sectors[w].fighters.owner_id == K.FERRENGI_OWNER_ID
                ]
            if choices:
                old_sid = ferr.sector_id
                ferr.sector_id = rng.choice(choices)
                universe.emit(
                    EventKind.FERRENGI_MOVE,
                    sector_id=ferr.sector_id,
                    **({"actor_id": ferr.id, "actor_kind": "ferrengi"} if K.ferrengi_tw2002() else {}),
                    payload={"id": ferr.id, "from": old_sid, "to": ferr.sector_id},
                    summary=f"Ferrengi {ferr.name} prowled {old_sid} → {ferr.sector_id}",
                )
                _apply_mines_to_ferrengi(universe, ferr)
                if not ferr.alive:
                    continue
                sec = universe.sectors.get(ferr.sector_id)
                if sec is None:
                    continue
        if grace_active:
            continue
        victims = [
            p
            for p in universe.players.values()
            if p.alive
            and p.sector_id == ferr.sector_id
            and p.sector_id not in K.FEDSPACE_SECTORS
            and not _player_cloaked(p)
            and getattr(p, "ferrengi_encounter", None) is None
        ]
        if not victims:
            continue
        # Prefer grudge targets, else weakest.
        grudge_victims = [p for p in victims if p.id in grudges]
        pool = grudge_victims or victims
        victim = min(pool, key=lambda p: p.ship.fighters)
        unarmed = victim.ship.fighters == 0 and victim.ship.shields == 0
        required_aggression = (
            K.FERRENGI_OPPORTUNIST_AGGRESSION_THRESHOLD
            if unarmed
            else K.FERRENGI_HUNT_AGGRESSION_THRESHOLD
        )
        # Grudge: timid Ferrengi still pursue.
        if victim.id in grudges:
            required_aggression = min(
                required_aggression, K.FERRENGI_OPPORTUNIST_AGGRESSION_THRESHOLD
            )
        if ferr.aggression < required_aggression:
            continue
        if victim.ship.fighters > ferr.fighters * K.FERRENGI_FLEE_FIGHTER_RATIO:
            choices = [w for w in sec.warps if w not in K.FEDSPACE_SECTORS]
            if choices:
                old_sid = ferr.sector_id
                ferr.sector_id = rng.choice(choices)
                universe.emit(
                    EventKind.FERRENGI_MOVE,
                    sector_id=ferr.sector_id,
                    **({"actor_id": ferr.id, "actor_kind": "ferrengi"} if K.ferrengi_tw2002() else {}),
                    payload={
                        "id": ferr.id,
                        "from": old_sid,
                        "to": ferr.sector_id,
                        "reason": "fled",
                    },
                    summary=f"Ferrengi {ferr.name} fled {victim.name}: {old_sid} → {ferr.sector_id}",
                )
                _apply_mines_to_ferrengi(universe, ferr)
            continue
        universe.emit(
            EventKind.FERRENGI_ATTACK,
            **_tw_actor(ferr.id),
            sector_id=ferr.sector_id,
            payload={"victim": victim.id},
            summary=f"!!! Ferrengi {ferr.name} attacks {victim.name} in {ferr.sector_id} !!!",
        )
        if (
            K.ferrengi_tw2002()
            and K.FERRENGI_ENCOUNTER == "tribute"
        ):
            open_ferrengi_encounter(universe, ferr, victim)
        else:
            _resolve_ship_combat_attacker_npc(universe, ferr, victim)
