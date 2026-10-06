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
    # SHIP_FLEET.md fl19: a track on a parked hull is not on the pilot's current ship.
    return [k for k, lt in universe.limpets.items() if lt.target_id == target_id and lt.target_ship_id is None]


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
        from .corp import deploy_friend
        if deploy_friend(universe, pid, md):
            continue
        return True
    dep = sector.fighters
    if dep is None or int(dep.count) <= 0:
        return False
    from .corp import deploy_friend
    if deploy_friend(universe, pid, dep):
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
    from .class0 import class0_service_here, class0_tw2002
    if not class0_service_here(universe, pid):
        if class0_tw2002():
            return ActionResult(ok=False, error="must be at StarDock or a Class 0 port")
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


# ---------------------------------------------------------------------------
# ship-hardware-v2: corbomite, marker beacons, psychic probe, atomic detonator,
# NavHaz and the hostile-entry order. docs/playtests/ships/SHIP_HARDWARE_V2.md.
# Same HARDWARE_MODE switch: under "legacy" none of this is sold, offered or read.
# ---------------------------------------------------------------------------

V2_SHIP_FIELD = {
    "corbomite": "corbomite",
    "marker_beacon": "marker_beacons",
    "psychic_probe": "psychic_probe",
    "atomic_detonator": "atomic_detonators",
}


def v2_have(ship) -> dict[str, int]:
    """Units of each v2 item aboard, keyed by the buy_equip item name."""
    return {item: int(getattr(ship, field, 0) or 0) for item, field in V2_SHIP_FIELD.items()}


def v2_add(ship, item: str, qty: int) -> None:
    field = V2_SHIP_FIELD[item]
    setattr(ship, field, int(getattr(ship, field, 0) or 0) + int(qty))


def strip_v2(ship) -> None:
    """A lost ship carries nothing over (DEATH_ESCAPE_PODS.md d15), cloak state included."""
    for field in V2_SHIP_FIELD.values():
        setattr(ship, field, 0)
    ship.cloaks = 0
    ship.mine_disruptors = 0
    ship.cloaked = False
    ship.cloak_activated_day = None


def _soak(ship_or_npc, damage: int) -> None:
    """Shields first, then fighters (quasar / corbomite / NavHaz damage)."""
    shields = int(ship_or_npc.shields or 0)
    soaked = min(shields, int(damage))
    ship_or_npc.shields = shields - soaked
    rest = int(damage) - soaked
    if rest > 0:
        ship_or_npc.fighters = max(0, int(ship_or_npc.fighters or 0) - rest)


# --- NavHaz (v20-v25) ---------------------------------------------------------

def navhaz_pct(sector) -> int:
    raw = float(getattr(sector, "nav_hazard", 0.0) or 0.0)
    return max(0, min(int(K.NAVHAZ_MAX_PCT), round(raw)))


def add_navhaz(sector, pct: int) -> int:
    """Raise a sector's NavHaz (capped). StarDock never takes any (v25, revision history)."""
    if sector.id == K.STARDOCK_SECTOR or int(pct) <= 0:
        return navhaz_pct(sector)
    sector.nav_hazard = float(min(int(K.NAVHAZ_MAX_PCT), navhaz_pct(sector) + int(pct)))
    return navhaz_pct(sector)


def tick_navhaz(universe: Universe) -> None:
    """Extern: FedSpace is cleared of NavHaz; elsewhere it disperses a little each night."""
    if not K.hardware_tw2002():
        return
    for sector in universe.sectors.values():
        pct = navhaz_pct(sector)
        if pct <= 0:
            continue
        if sector.id in K.FEDSPACE_SECTORS:
            sector.nav_hazard = 0.0
        else:
            sector.nav_hazard = float(max(0, pct - int(K.NAVHAZ_DISPERSION_PER_DAY)))


def apply_navhaz(universe: Universe, pid: str, sector, rng) -> int:
    """v21: chance equal to the %, damage = % x 10. No dice are rolled in a clean sector."""
    pct = navhaz_pct(sector)
    if pct <= 0:
        return 0
    if rng.random() * 100.0 >= pct:
        return 0
    player = universe.players[pid]
    damage = pct * int(K.NAVHAZ_DAMAGE_PER_PCT)
    _soak(player.ship, damage)
    universe.emit(
        EventKind.NAVHAZ_HIT,
        actor_id=pid,
        sector_id=sector.id,
        payload={"pct": pct, "damage": damage, "victim": pid},
        summary=f"{player.name} hit {pct}% navigational hazard entering {sector.id} ({damage} dmg)",
    )
    if int(player.ship.shields) <= 0 and int(player.ship.fighters) <= 0:
        from .combat import _destroy_ship
        _destroy_ship(universe, pid, reason="navhaz")
    return damage


def hostile_mines_present(universe: Universe, pid: str, sector) -> bool:
    """Mines that would treat this ship as hostile (for the avoid prompt, v28)."""
    for md in sector.mines:
        if int(md.count) <= 0 or md.kind not in (MineType.ARMID, MineType.LIMPET):
            continue
        from .corp import deploy_friend
        if deploy_friend(universe, pid, md):
            continue
        return True
    return False


def drop_other_limpets(universe: Universe, target_id: str) -> int:
    """v27: a new limpet makes any previously attached limpet fall off (cabal formulas.html)."""
    keys = limpets_on_target(universe, target_id)
    for k in keys:
        universe.limpets.pop(k, None)
    return len(keys)


# --- Corbomite (v1-v4) ----------------------------------------------------------

CORBOMITE_TRIGGERS = frozenset({"combat", "ferrengi"})


def corbomite_armed(player, reason: str, killer_id: str | None) -> int:
    """Units that go off when this ship is destroyed by another ship (0 if none)."""
    if not K.hardware_tw2002() or reason not in CORBOMITE_TRIGGERS or not killer_id:
        return 0
    return int(getattr(player.ship, "corbomite", 0) or 0)


def apply_corbomite(universe: Universe, victim_id: str, killer_id: str, units: int) -> None:
    """v3: the ship that destroyed you takes units x 20 damage, shields first."""
    if units <= 0:
        return
    damage = int(units) * int(K.CORBOMITE_DAMAGE_PER_UNIT)
    victim = universe.players.get(victim_id)
    victim_name = victim.name if victim is not None else victim_id
    killer = universe.players.get(killer_id)
    sector_id = None
    if killer is not None:
        if not killer.alive:
            return
        _soak(killer.ship, damage)
        sector_id = killer.sector_id
        dead = int(killer.ship.shields) <= 0 and int(killer.ship.fighters) <= 0
        name = killer.name
    else:
        npc = universe.ferrengi.get(killer_id)
        if npc is None or not npc.alive:
            return
        _soak(npc, damage)
        sector_id = npc.sector_id
        dead = int(npc.shields) <= 0 and int(npc.fighters) <= 0
        name = npc.name
    universe.emit(
        EventKind.CORBOMITE_BLAST,
        actor_id=victim_id,
        sector_id=sector_id,
        payload={"victim": killer_id, "damage": damage, "destroyed": dead},
        summary=f"{victim_name}'s ship was booby-trapped with Corbomite: {name} took {damage} damage",
    )
    if not dead:
        return
    if killer is not None:
        from .combat import _destroy_ship
        _destroy_ship(universe, killer_id, reason="corbomite", killer_id=victim_id, by_other=True)
    else:
        npc.alive = False
        universe.emit(
            EventKind.SHIP_DESTROYED,
            actor_id=victim_id,
            sector_id=sector_id,
            payload={"victim": killer_id, "kind": "ferrengi", "reason": "corbomite"},
            summary=f"{name} was destroyed by the Corbomite blast",
        )


# --- Marker beacons (v5-v9) ------------------------------------------------------

def beacon_message_error(message: Any) -> str | None:
    if not isinstance(message, str):
        return "launch_beacon needs a text message"
    text = message.strip()
    if not text:
        return "beacon message is empty"
    if len(text) > int(K.BEACON_MESSAGE_MAX):
        return f"beacon message is longer than {K.BEACON_MESSAGE_MAX} characters"
    if any(ord(ch) < 32 for ch in text):
        return "beacon message has control characters"
    return None


def launch_beacon_reason(universe: Universe, pid: str) -> str | None:
    player = universe.players[pid]
    if int(getattr(player.ship, "marker_beacons", 0) or 0) <= 0:
        return "no marker beacons aboard (buy_equip marker_beacon at StarDock)"
    if player.turns_today + int(K.BEACON_TURNS) > player.turns_per_day:
        return "out of turns"
    return None


def handle_launch_beacon(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not K.hardware_tw2002():
        return ActionResult(ok=False, error="marker beacons unavailable (HARDWARE_MODE legacy)")
    why = launch_beacon_reason(universe, pid)
    if why is not None:
        return ActionResult(ok=False, error=why)
    message = action.args.get("message")
    bad = beacon_message_error(message)
    if bad is not None:
        return ActionResult(ok=False, error=bad)
    player = universe.players[pid]
    sector = universe.sectors[player.sector_id]
    player.ship.marker_beacons = int(player.ship.marker_beacons) - 1
    if sector.beacon is not None:
        # v8: two beacons in one sector both explode.
        sector.beacon = None
        universe.emit(
            EventKind.BEACON_DESTROYED,
            actor_id=pid,
            sector_id=sector.id,
            payload={"sector": sector.id},
            summary=f"A beacon was already in {sector.id}: both beacons exploded",
        )
        return ActionResult(ok=True, turns_spent=int(K.BEACON_TURNS))
    sector.beacon = str(message).strip()
    universe.emit(
        EventKind.BEACON_LAUNCHED,
        actor_id=pid,
        sector_id=sector.id,
        payload={"sector": sector.id, "message": sector.beacon},
        summary=f"{player.name} launched a marker beacon in {sector.id}",
    )
    return ActionResult(ok=True, turns_spent=int(K.BEACON_TURNS))


# --- Psychic probe (v10-v12) ----------------------------------------------------

def psychic_reading(listed: int, final_unit: int, mcic: int, side: str) -> float:
    """Percent of the best price the port would have taken (Bible: shown after the trade).

    Sell: your price over the highest bid it would pay. Buy: the lowest ask it would take
    over what you paid. 100.0 means you hit the port's limit.
    """
    from .economy import haggle_bound

    bound = int(haggle_bound(int(listed), int(mcic), side))
    if side == "sell":
        pct = 100.0 * int(final_unit) / bound if bound > 0 else 100.0
    else:
        pct = 100.0 * bound / int(final_unit) if int(final_unit) > 0 else 100.0
    return round(min(100.0, pct), 2)


def emit_psychic_probe(universe: Universe, pid: str, commodity: str, side: str,
                       listed: int, final_unit: int, mcic: int) -> None:
    player = universe.players[pid]
    if not K.hardware_tw2002() or int(getattr(player.ship, "psychic_probe", 0) or 0) <= 0:
        return
    pct = psychic_reading(listed, final_unit, mcic, side)
    universe.emit(
        EventKind.PSYCHIC_PROBE,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={"commodity": commodity, "side": side, "unit": int(final_unit), "pct": pct},
        summary=f"Psychic probe: your {side} of {commodity} at {final_unit}cr was {pct}% of the best price",
    )


# --- Atomic detonator (v13-v19) -------------------------------------------------

def detonator_reason(universe: Universe, player, planet) -> str | None:
    """Why deploy_atomic is illegal on `planet` now (the legal list and the handler share this)."""
    if int(getattr(player.ship, "atomic_detonators", 0) or 0) <= 0:
        return "no atomic detonator aboard (buy_equip atomic_detonator at StarDock)"
    if planet is None or player.planet_landed != planet.id:
        return "must be landed on the planet first"
    owner = planet.owner_id
    if owner is not None and owner != player.id:
        same_corp = bool(planet.corp_ticker and player.corp_ticker and planet.corp_ticker == player.corp_ticker)
        if same_corp or _allied(universe, player.id, owner):
            return "planet belongs to a corp mate or ally"
        if int(planet.fighters) > 0 or int(planet.shields) > 0:
            return "planet still has defenders"
    if player.turns_today + int(K.TURN_COST["planet_destroy"]) > player.turns_per_day:
        return "out of turns"
    return None


def colonists_on(planet) -> int:
    return sum(int(n) for n in planet.colonists.values())
