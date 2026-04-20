"""Combat resolution + ship destruction + IFF + limpet attach.

Pulled out of `engine.runner` during the Phase 6 split. Contains:

    * `_are_allied(universe, a, b)` — corp-mate / active-alliance IFF.
    * `_attach_limpet(universe, owner, target)` — plant a tracker on a hull.
    * `_resolve_fighter_sector_combat(...)` — attacker vs. sector fighter
      deployment (warp-in offensive mode, or explicit attack-sector).
    * `_resolve_ship_combat(...)` — player-vs-target 3-exchange duel.
    * `_resolve_ship_combat_attacker_npc(...)` — same math, Ferrengi on offense.
    * `_destroy_ship(...)` — eject, respawn at StarDock, decrement lives,
      orphan unowned planets, mark player eliminated past the death cap.

Depends on `victory` for the `_award_xp` / `_destroy_ship`-adjacent XP
payouts. Does NOT import `runner` — that's the rule that makes the split
a DAG.
"""

from __future__ import annotations

from . import constants as K
from .models import (
    EventKind,
    FighterDeployment,
    FighterMode,
    LimpetTrack,
    MineType,
    Universe,
)
from .victory import _award_xp


def _are_allied(universe: Universe, a_id: str, b_id: str) -> bool:
    """True if a and b are corp mates OR in the same active alliance."""
    if a_id == b_id:
        return True
    a = universe.players.get(a_id)
    b = universe.players.get(b_id)
    if a is None or b is None:
        return False
    if a.corp_ticker is not None and a.corp_ticker == b.corp_ticker:
        return True
    for ally_id in a.alliances:
        ally = universe.alliances.get(ally_id)
        if ally is not None and ally.active and b_id in ally.member_ids:
            return True
    return False


def _attach_limpet(universe: Universe, owner_id: str, target_id: str) -> None:
    """Place a limpet so `owner_id` can later query `target_id`'s sector."""
    key = f"{owner_id}:{target_id}"
    target = universe.players.get(target_id)
    if target is None:
        return
    universe.limpets[key] = LimpetTrack(
        owner_id=owner_id,
        target_id=target_id,
        placed_sector=target.sector_id,
        placed_day=universe.day,
    )


def _resolve_fighter_sector_combat(
    universe: Universe,
    attacker_id: str,
    sector_id: int,
    incoming_fighters: int | None = None,
    incoming_mode: FighterMode | None = None,
) -> None:
    """Attacker tries to displace the sector's fighter deployment."""
    sector = universe.sectors[sector_id]
    defender_dep = sector.fighters
    if defender_dep is None:
        return
    attacker = universe.players[attacker_id]
    attack_pool = incoming_fighters if incoming_fighters is not None else attacker.ship.fighters

    defender_count = defender_dep.count
    rng = universe.rng
    # Stochastic duel — each side loses losses proportional to opposing pool
    att_losses = min(attack_pool, int(defender_count * rng.uniform(0.8, 1.1)))
    def_losses = min(defender_count, int(attack_pool * rng.uniform(0.8, 1.1)))

    attack_pool -= att_losses
    defender_count -= def_losses

    if incoming_fighters is None:
        attacker.ship.fighters = attack_pool

    if defender_count <= 0:
        sector.fighters = None
        if attack_pool > 0 and incoming_fighters is not None:
            sector.fighters = FighterDeployment(
                owner_id=attacker_id,
                count=attack_pool,
                mode=incoming_mode or FighterMode.DEFENSIVE,
            )
    else:
        defender_dep.count = defender_count

    universe.emit(
        EventKind.COMBAT,
        actor_id=attacker_id,
        sector_id=sector_id,
        payload={
            "vs": "fighter_sector",
            "defender_owner": defender_dep.owner_id,
            "attacker_losses": att_losses,
            "defender_losses": def_losses,
            "sector_claimed": defender_count <= 0,
        },
        summary=(
            f"Fighter clash in {sector_id}: {attacker.name} lost {att_losses}, "
            f"defenders lost {def_losses}"
            + (" — SECTOR SEIZED" if defender_count <= 0 else "")
        ),
    )


def _resolve_ship_combat(universe: Universe, attacker_id: str, target) -> None:
    rng = universe.rng
    attacker = universe.players[attacker_id]
    if hasattr(target, "alive") and not target.alive:
        return

    a_fighters = attacker.ship.fighters
    a_shields = attacker.ship.shields
    d_fighters = target.fighters if hasattr(target, "fighters") else target.ship.fighters
    d_shields = getattr(target, "shields", None)
    if d_shields is None:
        d_shields = target.ship.shields

    # Photon disable: fighters present but cannot fire OR absorb (offline).
    a_disabled = getattr(attacker.ship, "photon_disabled_ticks", 0) > 0
    d_disabled = (
        hasattr(target, "ship")
        and getattr(target.ship, "photon_disabled_ticks", 0) > 0
    )
    a_offense = 0 if a_disabled else a_fighters
    d_offense = 0 if d_disabled else d_fighters

    # 3 exchanges
    for _ in range(3):
        a_damage = int(a_offense * rng.uniform(0.8, 1.2))
        d_damage = int(d_offense * rng.uniform(0.8, 1.2))

        def apply(dmg: int, shields: int, fighters: int, disabled: bool) -> tuple[int, int]:
            if disabled:
                # Disabled fighters can't even absorb hits — they take losses raw,
                # bypassing shields too (helpless target).
                fighters = max(0, fighters - dmg)
                return shields, fighters
            absorbed = min(dmg, shields)
            shields -= absorbed
            dmg -= absorbed
            fighters = max(0, fighters - dmg)
            return shields, fighters

        d_shields, d_fighters = apply(a_damage, d_shields, d_fighters, d_disabled)
        a_shields, a_fighters = apply(d_damage, a_shields, a_fighters, a_disabled)
        # After the first exchange the disable wears off (1 tick of vulnerability).
        a_disabled = False
        d_disabled = False
        a_offense = a_fighters
        d_offense = d_fighters
        if d_fighters <= 0 or a_fighters <= 0:
            break

    attacker.ship.fighters = a_fighters
    attacker.ship.shields = a_shields
    if hasattr(target, "ship"):
        target.ship.fighters = d_fighters
        target.ship.shields = d_shields
    else:
        target.fighters = d_fighters
        target.shields = d_shields

    summary = (
        f"Combat in {attacker.sector_id}: "
        f"{attacker.name}[F{a_fighters} S{a_shields}] vs "
        f"{getattr(target, 'name', 'target')}[F{d_fighters} S{d_shields}]"
    )
    universe.emit(
        EventKind.COMBAT,
        actor_id=attacker_id,
        sector_id=attacker.sector_id,
        payload={
            "attacker": attacker_id,
            "defender": getattr(target, "id", None),
            "attacker_f": a_fighters, "attacker_s": a_shields,
            "defender_f": d_fighters, "defender_s": d_shields,
        },
        summary=summary,
    )

    # Destruction check
    if d_fighters <= 0:
        if hasattr(target, "alive"):
            # Ferrengi
            target.alive = False
            bounty = K.FERRENGI_BOUNTY_PER_AGG * target.aggression
            attacker.credits += bounty
            attacker.alignment += 10
            _award_xp(universe, attacker_id, "kill_ferr", multiplier=target.aggression)
            universe.emit(
                EventKind.SHIP_DESTROYED,
                actor_id=attacker_id,
                sector_id=attacker.sector_id,
                payload={"victim": target.id, "kind": "ferrengi", "bounty": bounty},
                summary=f"{attacker.name} destroyed {target.name} (+{bounty}cr bounty)",
            )
        else:
            _award_xp(universe, attacker_id, "kill_player")
            _destroy_ship(universe, target.id, reason="combat", killer_id=attacker_id)
    if a_fighters <= 0:
        _destroy_ship(universe, attacker_id, reason="combat", killer_id=getattr(target, "id", None))


def _resolve_ship_combat_attacker_npc(universe: Universe, attacker_npc, victim) -> None:
    """Same shape as _resolve_ship_combat but the attacker is a Ferrengi NPC."""
    rng = universe.rng
    a_fighters = attacker_npc.fighters
    a_shields = attacker_npc.shields
    d_fighters = victim.ship.fighters
    d_shields = victim.ship.shields
    d_disabled = getattr(victim.ship, "photon_disabled_ticks", 0) > 0
    a_offense = a_fighters
    d_offense = 0 if d_disabled else d_fighters

    for _ in range(3):
        a_dmg = int(a_offense * rng.uniform(0.8, 1.2))
        d_dmg = int(d_offense * rng.uniform(0.8, 1.2))
        # damage on victim
        if d_disabled:
            d_fighters = max(0, d_fighters - a_dmg)
        else:
            absorbed = min(a_dmg, d_shields)
            d_shields -= absorbed
            d_fighters = max(0, d_fighters - (a_dmg - absorbed))
        # damage on Ferrengi
        absorbed = min(d_dmg, a_shields)
        a_shields -= absorbed
        a_fighters = max(0, a_fighters - (d_dmg - absorbed))
        d_disabled = False
        a_offense = a_fighters
        d_offense = d_fighters
        if d_fighters <= 0 or a_fighters <= 0:
            break

    attacker_npc.fighters = a_fighters
    attacker_npc.shields = a_shields
    victim.ship.fighters = d_fighters
    victim.ship.shields = d_shields

    universe.emit(
        EventKind.COMBAT,
        actor_id=attacker_npc.id,
        sector_id=victim.sector_id,
        payload={
            "attacker": attacker_npc.id,
            "defender": victim.id,
            "attacker_f": a_fighters, "attacker_s": a_shields,
            "defender_f": d_fighters, "defender_s": d_shields,
        },
        summary=(
            f"Ferrengi combat in {victim.sector_id}: "
            f"{attacker_npc.name}[F{a_fighters} S{a_shields}] vs "
            f"{victim.name}[F{d_fighters} S{d_shields}]"
        ),
    )

    if d_fighters <= 0:
        _destroy_ship(universe, victim.id, reason="ferrengi", killer_id=attacker_npc.id)
    if a_fighters <= 0:
        attacker_npc.alive = False


def _destroy_ship(universe: Universe, pid: str, reason: str, killer_id: str | None = None) -> None:
    player = universe.players[pid]
    if not player.alive:
        return

    player.deaths += 1
    # Eject pilot to StarDock, downgrade ship, lose 25 % credits.
    try:
        universe.sectors[player.sector_id].occupant_ids.remove(pid)
    except ValueError:
        pass
    player.sector_id = K.STARDOCK_SECTOR
    universe.sectors[K.STARDOCK_SECTOR].occupant_ids.append(pid)
    player.ship.cargo = {c: 0 for c in player.ship.cargo}
    from .models import ShipClass as SC
    player.ship.ship_class = SC.MERCHANT_CRUISER
    player.ship.holds = K.STARTING_HOLDS
    player.ship.fighters = K.STARTING_FIGHTERS
    player.ship.shields = 0
    player.ship.photon_disabled_ticks = 0
    player.ship.genesis = 0
    player.ship.photon_missiles = 0
    player.ship.ether_probes = 0
    player.ship.mines = {MineType.ARMID: 0, MineType.LIMPET: 0, MineType.ATOMIC: 0}
    player.credits = int(player.credits * 0.75)
    player.planet_landed = None

    universe.emit(
        EventKind.SHIP_DESTROYED,
        actor_id=killer_id,
        sector_id=player.sector_id,
        payload={"victim": pid, "reason": reason, "deaths": player.deaths},
        summary=(
            f"*** {player.name}'s ship destroyed ({reason}); "
            f"ejected to StarDock [death #{player.deaths}/{K.MAX_DEATHS_BEFORE_ELIM}] ***"
        ),
    )

    if player.deaths >= K.MAX_DEATHS_BEFORE_ELIM:
        player.alive = False
        # Drop them off the StarDock occupant list — they're out of the game.
        try:
            universe.sectors[K.STARDOCK_SECTOR].occupant_ids.remove(pid)
        except ValueError:
            pass
        # Release any planets they owned solo, and emit a discrete
        # planet_orphaned event for each — spectators and the UI need to
        # see which specific planets are now unclaimed (the previous
        # behavior silently cleared owner_id, leaving orphan citadels
        # invisible on commander cards and in the event feed).
        orphaned_ids: list[int] = []
        for planet in universe.planets.values():
            if planet.owner_id == pid and planet.corp_ticker is None:
                planet.owner_id = None
                orphaned_ids.append(planet.id)
                universe.emit(
                    EventKind.PLANET_ORPHANED,
                    actor_id=pid,
                    sector_id=planet.sector_id,
                    payload={
                        "planet_id": planet.id,
                        "planet_name": planet.name,
                        "former_owner": pid,
                        "citadel_level": planet.citadel_level,
                        "fighters": planet.fighters,
                    },
                    summary=(
                        f"Planet {planet.name} (L{planet.citadel_level} citadel, "
                        f"{planet.fighters} fighters) is now UNCLAIMED after "
                        f"{player.name}'s elimination."
                    ),
                )
        universe.emit(
            EventKind.PLAYER_ELIMINATED,
            actor_id=pid,
            payload={
                "killer": killer_id,
                "deaths": player.deaths,
                "orphaned_planets": orphaned_ids,
            },
            summary=f"!!! {player.name} ELIMINATED — {player.deaths} ship losses, removed from match !!!",
        )
