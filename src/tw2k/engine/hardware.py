"""Ship hardware (HARDWARE_MODE tw2002). docs/playtests/ships/SHIP_HARDWARE.md."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from . import constants as K
from .actions import Action, ActionResult
from .models import EventKind, MineType

if TYPE_CHECKING:
    from .models import Player, Sector, Universe


def hardware_tw2002() -> bool:
    return K.hardware_tw2002()


def photon_hull_ok(player: Player) -> bool:
    """h5: only Missile Frigate / ISS may fire (and buy via max_photons)."""
    spec = K.hull_spec(player.ship.ship_class.value) or {}
    return int(spec.get("max_photons", 0) or 0) > 0


def can_buy_photon(player: Player) -> bool:
    return photon_hull_ok(player)


def sector_photon_active(sector: Sector) -> bool:
    return int(getattr(sector, "photon_wave_remaining", 0) or 0) > 0


def armid_detonation_hits(count: int, rng) -> tuple[int, int]:
    """Return (hits, damage_per_hit) for hostile armids.

    tw2002: floor(count/2) hits at ARMID_DAMAGE_TW2002.
    legacy: min(count, rand 1..MINE_MAX_HITS) at ARMID_DAMAGE.
    """
    count = int(count)
    if count <= 0:
        return 0, 0
    if K.hardware_tw2002():
        hits = count // 2
        if hits <= 0:
            # Bible/cabal: 50% rounding down — a lone mine does not detonate.
            return 0, int(K.ARMID_DAMAGE_TW2002)
        return hits, int(K.ARMID_DAMAGE_TW2002)
    hits = min(count, rng.randint(1, K.MINE_MAX_HITS_PER_MOVE))
    return hits, int(K.ARMID_DAMAGE)


def decloak_ship(universe: Universe, player: Player, *, reason: str) -> None:
    if not getattr(player.ship, "cloaked", False):
        return
    player.ship.cloaked = False
    player.ship.cloak_activated_day = None
    universe.emit(
        EventKind.CLOAK_OFF,
        actor_id=player.id,
        sector_id=player.sector_id,
        payload={"reason": reason},
        summary=f"{player.name}'s cloak failed ({reason})",
    )


def decloak_sector(universe: Universe, sector_id: int) -> int:
    n = 0
    for pid in list(universe.sectors[sector_id].occupant_ids):
        p = universe.players.get(pid)
        if p is None or not getattr(p.ship, "cloaked", False):
            continue
        decloak_ship(universe, p, reason="photon")
        n += 1
    return n


def tick_photon_waves(universe: Universe) -> None:
    for sector in universe.sectors.values():
        rem = int(getattr(sector, "photon_wave_remaining", 0) or 0)
        if rem > 0:
            sector.photon_wave_remaining = rem - 1


def tick_cloak_fails(universe: Universe, rng) -> None:
    """h16: 3% fail check on day tick while still cloaked (24h -> day-tick mapping)."""
    if not K.hardware_tw2002():
        return
    rate = float(K.CLOAK_FAIL_RATE)
    for player in universe.players.values():
        if not player.alive or not getattr(player.ship, "cloaked", False):
            continue
        if rng.random() < rate:
            decloak_ship(universe, player, reason="fail_rate")


def limpets_on_target(universe: Universe, target_id: str) -> list[str]:
    return [k for k, lt in universe.limpets.items() if lt.target_id == target_id]


def clear_mines_up_to(sector: Sector, clear_n: int) -> int:
    """Remove up to clear_n mine units (armid then limpet), return units cleared."""
    left = int(clear_n)
    cleared = 0
    for md in list(sector.mines):
        if left <= 0:
            break
        if md.kind not in (MineType.ARMID, MineType.LIMPET):
            continue
        take = min(int(md.count), left)
        if take <= 0:
            continue
        md.count = int(md.count) - take
        cleared += take
        left -= take
        if md.count <= 0:
            sector.mines.remove(md)
    return cleared


def total_sweepable_mines(sector: Sector) -> int:
    return sum(int(m.count) for m in sector.mines if m.kind in (MineType.ARMID, MineType.LIMPET))


def _damp_planets_in_sector(universe: Universe, shooter_id: str, sector_id: int) -> None:
    """Mark photon_damped_sector_id for shooter (and occupants) when planets can be damped."""
    sector = universe.sectors.get(sector_id)
    if sector is None:
        return
    vulnerable = False
    for planet_id in sector.planet_ids:
        planet = universe.planets.get(int(planet_id))
        if planet is None:
            continue
        level = int(planet.citadel_level or 0)
        shields = int(planet.shields or 0)
        if level >= 5 and shields >= K.QUASAR_PHOTON_SHIELD_MIN:
            continue
        vulnerable = True
        universe.emit(
            EventKind.QUASAR_DAMPED,
            actor_id=shooter_id,
            sector_id=sector_id,
            payload={"planet_id": planet.id, "damped": True},
            summary=f"Photon damped the cannons on {planet.name}",
        )
    if not vulnerable:
        return
    shooter = universe.players.get(shooter_id)
    if shooter is not None:
        shooter.photon_damped_sector_id = sector_id
    for oid in list(sector.occupant_ids):
        other = universe.players.get(oid)
        if other is None:
            continue
        other.photon_damped_sector_id = sector_id


def mark_sector_photon_wave(universe: Universe, shooter_id: str, sector_id: int) -> dict[str, Any]:
    """Apply photon wave to an adjacent sector (h7)."""
    sector = universe.sectors[sector_id]
    sector.photon_wave_remaining = int(K.PHOTON_WAVE_DURATION)
    decloaked = decloak_sector(universe, sector_id)
    _damp_planets_in_sector(universe, shooter_id, sector_id)
    return {
        "sector_id": sector_id,
        "wave": int(sector.photon_wave_remaining),
        "decloaked": decloaked,
        "mines_sitting": total_sweepable_mines(sector),
        "fighters_sitting": int(sector.fighters.count) if sector.fighters else 0,
    }


def _allied(universe: Universe, a: str, b: str) -> bool:
    from .combat import _are_allied
    return _are_allied(universe, a, b)


def carried_photon_hazard(universe: Universe, pid: str, sector) -> bool:
    """True if carrying photons into hostile armids or offensive fighters (h8)."""
    player = universe.players[pid]
    if int(player.ship.photon_missiles or 0) <= 0:
        return False
    for md in sector.mines:
        if md.kind != MineType.ARMID or int(md.count) <= 0:
            continue
        if md.owner_id == pid or _allied(universe, pid, md.owner_id):
            continue
        return True
    dep = sector.fighters
    if dep is None or int(dep.count) <= 0:
        return False
    if dep.owner_id == pid or _allied(universe, pid, dep.owner_id):
        return False
    from .models import FighterMode

    return dep.mode == FighterMode.OFFENSIVE


def apply_carried_photon_blast(universe: Universe, pid: str) -> None:
    player = universe.players[pid]
    lost = int(player.ship.photon_missiles or 0)
    player.ship.photon_missiles = 0
    player.turns_today = int(player.turns_per_day)
    universe.emit(
        EventKind.PHOTON_BLAST,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"lost": lost},
        summary=f"{player.name}'s photon missile detonated on contact ({lost} lost; day turns spent)",
    )


def handle_cloak(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.hardware_tw2002():
        return ActionResult(ok=False, error="cloak unavailable (HARDWARE_MODE legacy)")
    player = universe.players[pid]
    if int(getattr(player.ship, "cloaks", 0) or 0) <= 0:
        return ActionResult(ok=False, error="no cloaking device aboard (buy_equip cloak at StarDock)")
    if getattr(player.ship, "cloaked", False):
        return ActionResult(ok=False, error="already cloaked")
    player.ship.cloaks = int(player.ship.cloaks) - 1
    player.ship.cloaked = True
    player.ship.cloak_activated_day = int(universe.day)
    universe.emit(
        EventKind.CLOAK_ON,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={},
        summary=f"{player.name} activated a cloaking device",
    )
    return ActionResult(ok=True, turns_spent=0)


def handle_fire_disruptor(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.hardware_tw2002():
        return ActionResult(ok=False, error="mine disruptor unavailable (HARDWARE_MODE legacy)")
    player = universe.players[pid]
    if int(getattr(player.ship, "mine_disruptors", 0) or 0) <= 0:
        return ActionResult(ok=False, error="no mine disruptors aboard")
    raw = action.args.get("target")
    try:
        target_id = int(raw)
    except (TypeError, ValueError):
        return ActionResult(ok=False, error="fire_disruptor needs adjacent sector target")
    cur = universe.sectors[player.sector_id]
    if target_id not in cur.warps:
        return ActionResult(ok=False, error="disruptor target must be an adjacent sector")
    if target_id not in universe.sectors:
        return ActionResult(ok=False, error="invalid target sector")
    cost = int(K.TURN_COST.get("attack", 1))
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    import random
    rng = getattr(universe, "_rng", None) or random.Random(int(getattr(universe.config, "seed", 0)) + int(universe.day))
    sector = universe.sectors[target_id]
    sitting = total_sweepable_mines(sector)
    # Still consume the disruptor when the lane is empty.
    want = 0 if sitting <= 0 else min(sitting, rng.randint(1, int(K.DISRUPTOR_CLEAR_MAX)))
    player.ship.mine_disruptors = int(player.ship.mine_disruptors) - 1
    cleared = clear_mines_up_to(sector, want) if want else 0
    universe.emit(
        EventKind.DISRUPTOR_FIRED,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"target": target_id, "cleared": cleared},
        summary=f"{player.name} fired a mine disruptor into {target_id} (cleared {cleared})",
    )
    return ActionResult(ok=True, turns_spent=cost)


def handle_remove_limpet(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.hardware_tw2002():
        return ActionResult(ok=False, error="limpet removal unavailable (HARDWARE_MODE legacy)")
    player = universe.players[pid]
    if player.sector_id != K.STARDOCK_SECTOR:
        return ActionResult(ok=False, error="must be at StarDock")
    keys = limpets_on_target(universe, pid)
    if not keys:
        return ActionResult(ok=False, error="no limpet attached")
    fee = int(K.LIMPET_REMOVAL_COST)
    if player.credits < fee:
        return ActionResult(ok=False, error=f"insufficient credits ({player.credits} < {fee})")
    player.credits -= fee
    for k in keys:
        universe.limpets.pop(k, None)
    universe.emit(
        EventKind.LIMPET_REMOVED,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"fee": fee, "removed": len(keys)},
        summary=f"{player.name} paid {fee} cr to remove {len(keys)} limpet(s) at StarDock",
    )
    return ActionResult(ok=True, turns_spent=0)


def handle_photon_tw2002(universe: Universe, pid: str, action: Action) -> ActionResult:
    """Adjacent-sector photon wave (h5-h9)."""
    player = universe.players[pid]
    if not photon_hull_ok(player):
        return ActionResult(ok=False, error="only Missile Frigate or Imperial StarShip may fire photons")
    if player.ship.photon_missiles <= 0:
        return ActionResult(ok=False, error="no photon missiles loaded")
    raw = action.args.get("target")
    try:
        target_id = int(raw)
    except (TypeError, ValueError):
        return ActionResult(ok=False, error="photon needs an adjacent sector target")
    cur = universe.sectors[player.sector_id]
    if target_id not in cur.warps:
        return ActionResult(ok=False, error="photon target must be an adjacent sector")
    if target_id not in universe.sectors:
        return ActionResult(ok=False, error="invalid target sector")
    # FedSpace: keep existing penalty shape when firing from FedSpace at a protected situation.
    if player.sector_id in K.FEDSPACE_SECTORS:
        # Align with legacy: firing weapons in FedSpace costs alignment when RANK_MODE off,
        # or when protected traders are involved. For sector-target photons, refuse in FedSpace
        # the same way attack refuses without inventing new rules — deduct if RANK not on.
        if not K.rank_tw2002():
            player.alignment -= 100
            return ActionResult(ok=False, error="FedSpace forbids weapons fire")
    cost = K.TURN_COST["attack"]
    if player.turns_today + cost > player.turns_per_day:
        return ActionResult(ok=False, error="out of turns")
    player.ship.photon_missiles -= 1
    info = mark_sector_photon_wave(universe, pid, target_id)
    universe.emit(
        EventKind.PHOTON_FIRED,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"target_sector": target_id, **info},
        summary=f"{player.name} launched a PHOTON MISSILE into sector {target_id}!",
    )
    universe.emit(
        EventKind.PHOTON_HIT,
        actor_id=pid,
        sector_id=target_id,
        payload={"target_sector": target_id, "wave": info["wave"], "decloaked": info["decloaked"]},
        summary=(
            f"!!! Photon wave in {target_id}: mines/fighters neutralized for "
            f"{info['wave']} day-tick(s); {info['decloaked']} ship(s) decloaked !!!"
        ),
    )
    return ActionResult(ok=True, turns_spent=cost)
