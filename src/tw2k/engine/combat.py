"""Combat resolution + ship destruction + IFF + limpet attach.

Pulled out of `engine.runner` during the Phase 6 split. Contains:

    * `_are_allied(universe, a, b)` — corp-mate / active-alliance IFF.
    * `_attach_limpet(universe, owner, target)` — plant a tracker on a hull.
    * `_resolve_fighter_sector_combat(...)` — attacker vs. sector fighter
      deployment (warp-in offensive mode, or explicit attack-sector).
    * `_resolve_ship_combat(...)` — player-vs-target 3-exchange duel.
    * `_resolve_ship_combat_attacker_npc(...)` — same math, Ferrengi on offense.
    * `_destroy_ship(...)` — DEATH_MODE tw2002 escape pod / Ship Destroyed, or legacy StarDock respawn,
      orphan unowned planets, mark player eliminated past the death cap.

Depends on `victory` for the `_award_xp` / `_destroy_ship`-adjacent XP
payouts. Does NOT import `runner` — that's the rule that makes the split
a DAG.
"""

from __future__ import annotations

import math
import random
from fractions import Fraction

from . import constants as K
from .models import (
    AlienTrader,
    EventKind,
    FerrengiShip,
    FighterDeployment,
    FighterMode,
    LimpetTrack,
    MineType,
    Universe,
)
from .victory import _award_xp, combat_rewards, kill_rewards


def _apply_volley(
    dmg: int, shields: int, fighters: int, disabled: bool
) -> tuple[int, int, int, int]:
    """Apply one volley of damage; return (new_shields, new_fighters, shield_absorbed, fighters_lost).

    Mirrors the shield-first absorption used in ship and planet combat. When
    ``disabled`` is True (photon-offline fighters), damage bypasses shields
    and hits fighters directly.
    """
    if disabled:
        new_f = max(0, fighters - dmg)
        return shields, new_f, 0, fighters - new_f
    absorbed = min(dmg, shields)
    new_s = shields - absorbed
    rem = dmg - absorbed
    new_f = max(0, fighters - rem)
    return new_s, new_f, absorbed, fighters - new_f


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
    pot = int(defender_dep.toll_credits or 0)
    rng = universe.rng
    # Stochastic duel — each side loses losses proportional to opposing pool
    att_losses = min(attack_pool, int(defender_count * rng.uniform(0.8, 1.1)))
    def_losses = min(defender_count, int(attack_pool * rng.uniform(0.8, 1.1)))

    attack_pool -= att_losses
    defender_count -= def_losses

    if incoming_fighters is None:
        attacker.ship.fighters = attack_pool

    if defender_count <= 0:
        # Iago: destroying toll fighters pays what they have collected.
        # The number stays off the combat facts.
        if K.sector_fighter_tw2002() and pot > 0:
            attacker.credits += pot
        sector.fighters = None
        if attack_pool > 0 and incoming_fighters is not None:
            placed = attack_pool
            if K.sector_fighter_tw2002():
                cap = K.sector_fighter_cap(bool(sector.planet_ids))
                if placed > cap:
                    placed = cap
            excess = attack_pool - placed
            if excess > 0:
                attacker.ship.fighters += excess
            sector.fighters = FighterDeployment(
                owner_id=attacker_id,
                count=placed,
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


def _exchange_outcome(rounds: list[dict], attacker_f: int, defender_f: int) -> dict:
    """Attacker-point-of-view result for a ship exchange (video cockpit V2).

    ``destroyed`` — the defender's fighters hit 0 (counts as a hit).
    ``miss`` — the attacker was destroyed, or dealt no fighter damage.
    ``hit`` — the defender lost fighters and both ships are still up.
    Losses are the fighter counts each side actually dropped across rounds.
    """
    att = sum(int(r.get("attacker_fighters_lost") or 0) for r in rounds)
    dfn = sum(int(r.get("defender_fighters_lost") or 0) for r in rounds)
    if defender_f <= 0:
        outcome = "destroyed"
    elif attacker_f <= 0 or dfn <= 0:
        outcome = "miss"
    else:
        outcome = "hit"
    return {"attacker_losses": att, "defender_losses": dfn, "outcome": outcome}


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

    rounds: list[dict] = []
    for round_idx in range(1, 4):
        a_mult = rng.uniform(0.8, 1.2)
        d_mult = rng.uniform(0.8, 1.2)
        a_damage = int(a_offense * a_mult)
        d_damage = int(d_offense * d_mult)

        d_shields, d_fighters, d_sh_abs, d_f_lost = _apply_volley(
            a_damage, d_shields, d_fighters, d_disabled
        )
        a_shields, a_fighters, a_sh_abs, a_f_lost = _apply_volley(
            d_damage, a_shields, a_fighters, a_disabled
        )
        ended = d_fighters <= 0 or a_fighters <= 0
        rounds.append(
            {
                "round": round_idx,
                "attacker_damage_mult": round(a_mult, 4),
                "defender_damage_mult": round(d_mult, 4),
                "attacker_offense": a_offense,
                "defender_offense": d_offense,
                "attacker_volley": a_damage,
                "defender_volley": d_damage,
                "defender_shield_absorbed": d_sh_abs,
                "defender_fighters_lost": d_f_lost,
                "attacker_shield_absorbed": a_sh_abs,
                "attacker_fighters_lost": a_f_lost,
                "defender_f_after": d_fighters,
                "defender_s_after": d_shields,
                "attacker_f_after": a_fighters,
                "attacker_s_after": a_shields,
                "attacker_photon_disabled": a_disabled,
                "defender_photon_disabled": d_disabled,
                "ended_here": ended,
            }
        )
        # After the first exchange the disable wears off (1 tick of vulnerability).
        a_disabled = False
        d_disabled = False
        a_offense = a_fighters
        d_offense = d_fighters
        if ended:
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
    defender_id = getattr(target, "id", None)
    exchange_kind = "ferrengi_vs_ship" if isinstance(target, FerrengiShip) else "ship_vs_ship"
    universe.emit(
        EventKind.COMBAT,
        actor_id=attacker_id,
        sector_id=attacker.sector_id,
        payload={
            "exchange_kind": exchange_kind,
            "exchange_max_rounds": 3,
            "attacker": attacker_id,
            "defender": defender_id,
            "attacker_f": a_fighters,
            "attacker_s": a_shields,
            "defender_f": d_fighters,
            "defender_s": d_shields,
            "rounds": rounds,
            **_exchange_outcome(rounds, a_fighters, d_fighters),
        },
        summary=summary,
    )

    # Destruction check.
    #
    # IMPORTANT: both Player and FerrengiShip carry `alive: bool` on their
    # models, so `hasattr(target, "alive")` is NOT a valid discriminator —
    # an earlier version of this code used that check and crashed with
    # AttributeError on `target.aggression` the first time a player was
    # killed in PvP (match 2, seed 17, d1t49 — see docs/MATCH_PLAY_NOTES.md
    # "M2-1"). Worse, it had already mutated `target.alive = False` before
    # the raise, leaving the victim as a permanently-frozen zombie (no
    # respawn, no death count). Use isinstance() for type-safe branching.
    if not isinstance(target, FerrengiShip):
        lost = sum(int(r.get("attacker_fighters_lost") or 0) for r in rounds)
        combat_rewards(universe, attacker_id, int(target.alignment), lost)
    if d_fighters <= 0:
        _defender_destroyed(universe, attacker_id, target)
    if a_fighters <= 0:
        _destroy_ship(universe, attacker_id, reason="combat", killer_id=getattr(target, "id", None))


def _defender_destroyed(universe: Universe, attacker_id: str, target) -> None:
    """Bounty path for a Ferrengi, the existing death path for a player."""
    attacker = universe.players[attacker_id]
    if isinstance(target, AlienTrader):
        from .alien import on_alien_killed
        on_alien_killed(universe, attacker_id, target)
        return
    if isinstance(target, FerrengiShip):
        from .ferrengi import clear_ferrengi_encounter, record_ferrengi_grudge
        target.alive = False
        bounty = K.FERRENGI_BOUNTY_PER_AGG * target.aggression
        salvage = int(getattr(target, "credits", 0) or 0)
        attacker.credits += bounty + salvage
        attacker.alignment += int(K.FERRENGI_ALIGN_ON_KILL)
        _award_xp(universe, attacker_id, "kill_ferr", multiplier=target.aggression)
        record_ferrengi_grudge(universe, attacker_id)
        clear_ferrengi_encounter(universe, attacker_id)
        for good, qty in list((getattr(target, "cargo", None) or {}).items()):
            qty = int(qty or 0)
            if qty <= 0:
                continue
            free = int(attacker.ship.cargo_free)
            take = min(qty, free)
            if take > 0:
                attacker.ship.cargo[good] = int(attacker.ship.cargo.get(good, 0) or 0) + take
        universe.emit(
            EventKind.SHIP_DESTROYED,
            actor_id=attacker_id,
            sector_id=attacker.sector_id,
            payload={"victim": target.id, "kind": "ferrengi", "bounty": bounty, "salvage": salvage},
            summary=f"{attacker.name} destroyed {target.name} (+{bounty}cr bounty)",
        )
    else:
        # Player target: route through _destroy_ship so respawn,
        # death-count, elimination, credit penalty, ship downgrade
        # all fire correctly.
        _award_xp(universe, attacker_id, "kill_player")
        # x13/a2: the killer's share reads the victim before the pod or Ship Destroyed loss.
        kill_rewards(universe, attacker_id, int(target.experience), int(target.alignment))
        # Furb reads the hull that is about to die, but the event must not bump universe.seq
        # before the pod picks a sector (that seed includes seq). Capture does not furb, so a
        # furb emit here would land the pod somewhere a plain destroy does not.
        furb_ship = None
        if K.corpship_on() and K.FURB_FERRENGI is False:
            furb_ship = target.ship.model_copy(deep=True)
        _destroy_ship(universe, target.id, reason="combat", killer_id=attacker_id, by_other=True)
        if furb_ship is not None:
            from .corpships import apply_furb
            apply_furb(universe, attacker_id, furb_ship, target.id)


# ---------------------------------------------------------------------------
# tw2002 ship combat (COMBAT_MODE). docs/playtests/combat/SHIP_COMBAT.md.
# ---------------------------------------------------------------------------


def _odds(value: float) -> Fraction:
    return Fraction(str(value))


def combat_odds_of(target) -> Fraction:
    """Offensive odds of a player's hull, or the Ferrengi figure."""
    if isinstance(target, FerrengiShip):
        from .ferrengi import ferrengi_odds
        return _odds(ferrengi_odds(target))
    return _odds(K.combat_hull(target.ship.ship_class.value)[0])


def attack_cap(player) -> int:
    """Most fighters one attack may send: aboard, capped by the hull's fighters per attack."""
    per_attack = K.combat_hull(player.ship.ship_class.value)[1]
    return max(0, min(int(player.ship.fighters), int(per_attack)))


def interdictor_planet(universe: Universe, pid: str, sector):
    """A planet hostile to `pid` in `sector` that can interdict now. Read only (no fuel burn)."""
    from .models import Commodity

    for item in sorted(sector.planet_ids):
        planet = universe.planets.get(item)
        if planet is None:
            continue
        if planet.owner_id is None or _are_allied(universe, pid, planet.owner_id):
            continue
        if int(planet.citadel_level or 0) < K.INTERDICTOR_MIN_LEVEL:
            continue
        if int(planet.stockpile.get(Commodity.FUEL_ORE, 0)) < K.INTERDICTOR_FUEL:
            continue
        return planet
    return None


def challenge_group(universe: Universe, pid: str, sector):
    """Hostile defensive or toll fighters here that challenge `pid`, or None."""
    from .hardware import sector_photon_active
    if sector_photon_active(sector):
        return None
    dep = sector.fighters
    if dep is None or int(dep.count) <= 0:
        return None
    from .corp import deploy_friend
    if deploy_friend(universe, pid, dep):
        return None
    if dep.mode not in (FighterMode.DEFENSIVE, FighterMode.TOLL):
        return None
    return dep


def live_challenge(universe: Universe, pid: str, *, settle: bool = False) -> dict | None:
    """The player's open challenge if it still stands, else None.

    Read only unless ``settle`` is set: then a stale challenge (the group is gone,
    turned friendly or offensive, or the ship left) is cleared on the player.
    """
    player = universe.players.get(pid)
    if player is None:
        return None
    ch = player.fighter_challenge
    if not ch:
        return None
    sector = universe.sectors.get(player.sector_id)
    stale = (
        not K.challenge_on()
        or not player.alive
        or sector is None
        or int(ch.get("sector_id", -1)) != player.sector_id
        or player.planet_landed is not None
        or challenge_group(universe, pid, sector) is None
    )
    if stale:
        if settle:
            player.fighter_challenge = None
        return None
    return ch


def retreat_block(universe: Universe, pid: str) -> str | None:
    """Why the challenged player may not retreat now, or None."""
    player = universe.players[pid]
    ch = player.fighter_challenge or {}
    sector = universe.sectors[player.sector_id]
    back = ch.get("from_sector")
    if getattr(player, "arrived_by_transwarp", False):
        return "cannot retreat after a TransWarp arrival"
    if getattr(player, "arrived_by_transport", False):
        return "cannot retreat after a transporter arrival"  # SHIP_FLEET.md fl17c (inferred)
    if back is None or int(back) not in sector.warps:
        return "no warp back to the sector you came from"
    if interdictor_planet(universe, pid, sector) is not None:
        return "a planetary interdictor holds this sector"
    return None


def open_challenge(universe: Universe, pid: str, sector, from_sector: int) -> bool:
    """Start a challenge if hostile defensive or toll fighters are here."""
    if not K.challenge_on():
        return False
    dep = challenge_group(universe, pid, sector)
    if dep is None:
        return False
    player = universe.players[pid]
    player.fighter_challenge = {"sector_id": sector.id, "from_sector": int(from_sector), "mode": dep.mode.value}
    universe.emit(
        EventKind.FIGHTER_CHALLENGE,
        actor_id=pid,
        sector_id=sector.id,
        payload={"mode": dep.mode.value, "count": int(dep.count), "victim": pid},
        summary=(
            f"{int(dep.count)} {dep.mode.value} fighters challenge {player.name} in {sector.id}: "
            + ("pay, attack, retreat or surrender" if dep.mode == FighterMode.TOLL else "attack, retreat or surrender")
        ),
    )
    return True


def _resolve_fighter_attack_tw2002(universe: Universe, attacker_id: str, sector_id: int, qty: int) -> bool:
    """Send `qty` fighters at the sector group at the hull's odds. True when the group is gone."""
    sector = universe.sectors[sector_id]
    dep = sector.fighters
    attacker = universe.players[attacker_id]
    if dep is None:
        return True
    count = int(dep.count)
    a_odds = combat_odds_of(attacker)
    d_odds = _odds(K.SECTOR_FIGHTER_ODDS)
    power = qty * a_odds
    defense = count * d_odds
    pot = int(dep.toll_credits or 0)
    if power >= defense:
        att_losses = min(qty, math.ceil(defense / a_odds))
        def_losses = count
    else:
        att_losses = qty
        def_losses = min(count, math.floor(power / d_odds))
    attacker.ship.fighters = int(attacker.ship.fighters) - att_losses
    cleared = def_losses >= count
    owner = dep.owner_id
    if owner in universe.players and owner != attacker_id:
        combat_rewards(universe, attacker_id, int(universe.players[owner].alignment), att_losses,
                       sector_fighters=True)
    if cleared:
        if K.sector_fighter_tw2002() and pot > 0:
            attacker.credits += pot
        sector.fighters = None
    else:
        dep.count = count - def_losses
    universe.emit(
        EventKind.COMBAT,
        actor_id=attacker_id,
        sector_id=sector_id,
        payload={
            "vs": "fighter_sector",
            "defender_owner": owner,
            "sent": qty,
            "attacker_losses": att_losses,
            "defender_losses": def_losses,
            "sector_claimed": cleared,
        },
        summary=(
            f"{attacker.name} sent {qty} fighters at the fighters in {sector_id}: lost {att_losses}, "
            f"destroyed {def_losses}" + (" - SECTOR CLEARED" if cleared else "")
        ),
    )
    return cleared


def _flee_destination(universe: Universe, defender, sector) -> int | None:
    """One hop to a neighbor with no fighters but the defender's own or friendly ones."""
    picks: list[int] = []
    for wid in sorted(sector.warps):
        dest = universe.sectors.get(int(wid))
        if dest is None:
            continue
        dep = dest.fighters
        from .corp import deploy_friend
        if dep is not None and int(dep.count) > 0 and not deploy_friend(universe, defender.id, dep):
            continue
        picks.append(int(wid))
    if not picks:
        return None
    return universe.rng.choice(picks)


def _flee_blocked(universe: Universe, attacker, defender, sector) -> bool:
    if defender.ship.ship_class.value in K.COMBAT_NEVER_FLEE_HULLS:
        return True
    if attacker.ship.ship_class.value in K.COMBAT_INTERDICT_HULLS:
        return True
    if defender.planet_landed is not None:
        return True
    return interdictor_planet(universe, defender.id, sector) is not None


def _flee(universe: Universe, defender, dest_id: int) -> None:
    sector = universe.sectors[defender.sector_id]
    try:
        sector.occupant_ids.remove(defender.id)
    except ValueError:
        pass
    dest = universe.sectors[dest_id]
    defender.sector_id = dest_id
    defender.end_port_visit()
    defender.photon_damped_sector_id = None
    defender.fighter_challenge = None
    dest.occupant_ids.append(defender.id)
    defender.known_sectors.add(dest_id)
    defender.known_warps[dest_id] = list(dest.warps)
    defender.flee_penalty = True


def _resolve_ship_attack_tw2002(universe: Universe, attacker_id: str, target, qty: int) -> None:
    """One attack: the attacker sends `qty` fighters. Exact odds, shields first, then the flee check."""
    attacker = universe.players[attacker_id]
    if hasattr(target, "alive") and not target.alive:
        return
    is_ferr = isinstance(target, FerrengiShip)
    is_alien = isinstance(target, AlienTrader)
    if is_ferr:
        from .ferrengi import record_ferrengi_grudge
        record_ferrengi_grudge(universe, attacker_id)
    d_f = int(target.fighters if is_ferr else target.ship.fighters)
    d_s = int(target.shields if is_ferr else target.ship.shields)
    d_disabled = (not is_ferr) and getattr(target.ship, "photon_disabled_ticks", 0) > 0
    a_odds = combat_odds_of(attacker)
    d_odds = combat_odds_of(target)
    s_eff = 0 if d_disabled else d_s
    power = qty * a_odds
    defense = (s_eff + d_f) * d_odds
    beaten = power >= defense
    if beaten:
        att_losses = min(qty, math.ceil(defense / a_odds))
        sh_lost, f_lost = s_eff, d_f
    else:
        att_losses = qty
        units = math.floor(power / d_odds)
        sh_lost = min(s_eff, units)
        f_lost = min(d_f, units - sh_lost)
    attacker.ship.fighters = int(attacker.ship.fighters) - att_losses
    if not is_ferr:
        combat_rewards(universe, attacker_id, int(target.alignment), att_losses)
    d_f -= f_lost
    d_s -= sh_lost
    if is_ferr:
        target.fighters, target.shields = d_f, d_s
    else:
        target.ship.fighters, target.ship.shields = d_f, d_s

    sector = universe.sectors[attacker.sector_id]
    flee_to = None
    if not beaten and is_alien and K.ALIEN_FLEE_RULE == "player":
        if Fraction(int(attacker.ship.fighters)) > (d_f + d_s) * _odds(K.COMBAT_FLEE_RATIO):
            from .alien import alien_flee_destination
            flee_to = alien_flee_destination(universe, target)
    elif not beaten and not is_ferr and not _flee_blocked(universe, attacker, target, sector):
        if Fraction(int(attacker.ship.fighters)) > (d_f + d_s) * _odds(K.COMBAT_FLEE_RATIO):
            flee_to = _flee_destination(universe, target, sector)

    a_f, a_s = int(attacker.ship.fighters), int(attacker.ship.shields)
    will_capture = False
    if beaten and is_alien:
        from .capture import alien_would_capture
        will_capture = alien_would_capture(universe, attacker, target, qty, defense, a_odds)
    elif beaten and not is_ferr:
        from .capture import manned_would_capture
        will_capture = manned_would_capture(universe, attacker, target, qty, defense, a_odds)
    outcome = (
        "captured" if will_capture
        else ("destroyed" if beaten else ("hit" if (f_lost + sh_lost) > 0 else "miss"))
    )
    rounds = [{
        "round": 1,
        "attacker_damage_mult": float(a_odds),
        "defender_damage_mult": float(d_odds),
        "attacker_offense": qty,
        "defender_offense": 0,
        "attacker_volley": math.floor(power),
        "defender_volley": 0,
        "defender_shield_absorbed": sh_lost,
        "defender_fighters_lost": f_lost,
        "attacker_shield_absorbed": 0,
        "attacker_fighters_lost": att_losses,
        "defender_f_after": d_f,
        "defender_s_after": d_s,
        "attacker_f_after": a_f,
        "attacker_s_after": a_s,
        "attacker_photon_disabled": False,
        "defender_photon_disabled": d_disabled,
        "ended_here": True,
    }]
    universe.emit(
        EventKind.COMBAT,
        actor_id=attacker_id,
        sector_id=attacker.sector_id,
        payload={
            "exchange_kind": (
                "ferrengi_vs_ship" if is_ferr else ("alien_vs_ship" if is_alien else "ship_vs_ship")
            ),
            "exchange_max_rounds": 1,
            "attacker": attacker_id,
            "defender": getattr(target, "id", None),
            "attacker_f": a_f,
            "attacker_s": a_s,
            "defender_f": d_f,
            "defender_s": d_s,
            "sent": qty,
            "defender_fled": flee_to is not None,
            "rounds": rounds,
            "attacker_losses": att_losses,
            "defender_losses": f_lost,
            "outcome": outcome,
        },
        summary=(
            f"Combat in {attacker.sector_id}: {attacker.name} sent {qty} fighters, lost {att_losses}; "
            f"{getattr(target, 'name', 'target')} lost {sh_lost} shields and {f_lost} fighters"
            + (" - CAPTURED" if will_capture else (" - DESTROYED" if beaten else ""))
            + (" - the target fled" if flee_to is not None else "")
        ),
    )
    if will_capture and is_alien:
        from .alien import apply_alien_capture
        apply_alien_capture(universe, attacker_id, target)
    elif will_capture:
        from .capture import apply_manned_capture
        apply_manned_capture(universe, attacker_id, target)
    elif beaten:
        _defender_destroyed(universe, attacker_id, target)
    elif flee_to is not None and is_alien:
        target.sector_id = int(flee_to)
        universe.emit(
            EventKind.ALIEN_FLED,
            actor_id=attacker_id,
            sector_id=attacker.sector_id,
            payload={"id": target.id, "to": int(flee_to)},
            summary=f"{target.name} fled to sector {flee_to}",
        )
    elif flee_to is not None:
        _flee(universe, target, flee_to)


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

    rounds: list[dict] = []
    for round_idx in range(1, 4):
        a_mult = rng.uniform(0.8, 1.2)
        d_mult = rng.uniform(0.8, 1.2)
        a_dmg = int(a_offense * a_mult)
        d_dmg = int(d_offense * d_mult)

        if d_disabled:
            d_shields, d_fighters, d_sh_abs, d_f_lost = _apply_volley(
                a_dmg, d_shields, d_fighters, True
            )
        else:
            d_shields, d_fighters, d_sh_abs, d_f_lost = _apply_volley(
                a_dmg, d_shields, d_fighters, False
            )
        a_shields, a_fighters, a_sh_abs, a_f_lost = _apply_volley(
            d_dmg, a_shields, a_fighters, False
        )
        ended = d_fighters <= 0 or a_fighters <= 0
        rounds.append(
            {
                "round": round_idx,
                "attacker_damage_mult": round(a_mult, 4),
                "defender_damage_mult": round(d_mult, 4),
                "attacker_offense": a_offense,
                "defender_offense": d_offense,
                "attacker_volley": a_dmg,
                "defender_volley": d_dmg,
                "defender_shield_absorbed": d_sh_abs,
                "defender_fighters_lost": d_f_lost,
                "attacker_shield_absorbed": a_sh_abs,
                "attacker_fighters_lost": a_f_lost,
                "defender_f_after": d_fighters,
                "defender_s_after": d_shields,
                "attacker_f_after": a_fighters,
                "attacker_s_after": a_shields,
                "defender_photon_disabled": d_disabled,
                "ended_here": ended,
            }
        )
        d_disabled = False
        a_offense = a_fighters
        d_offense = d_fighters
        if ended:
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
            "exchange_kind": "ferrengi_vs_ship",
            "exchange_max_rounds": 3,
            "attacker": attacker_npc.id,
            "defender": victim.id,
            "attacker_f": a_fighters,
            "attacker_s": a_shields,
            "defender_f": d_fighters,
            "defender_s": d_shields,
            "rounds": rounds,
            **_exchange_outcome(rounds, a_fighters, d_fighters),
        },
        summary=(
            f"Ferrengi combat in {victim.sector_id}: "
            f"{attacker_npc.name}[F{a_fighters} S{a_shields}] vs "
            f"{victim.name}[F{d_fighters} S{d_shields}]"
        ),
    )

    if d_fighters <= 0:
        _destroy_ship(universe, victim.id, reason="ferrengi", killer_id=attacker_npc.id, by_other=True)
    if a_fighters <= 0:
        attacker_npc.alive = False


def _destroy_ship(
    universe: Universe, pid: str, reason: str, killer_id: str | None = None, by_other: bool = False,
    *, always_escape: bool = False,
) -> None:
    """A ship is lost. `by_other` marks a kill someone else pressed the keys for (pods.html)."""
    player = universe.players[pid]
    if not player.alive:
        return
    if killer_id == K.ROGUE_OWNER_ID:  # CORP_RULES.md cr13: a ship rogue fighters destroy has no killer
        killer_id, by_other = None, False
    from .hardware import apply_corbomite, corbomite_armed, strip_v2
    corbomite = corbomite_armed(player, reason, killer_id)  # read before the hull is stripped
    if K.death_tw2002():
        _destroy_ship_tw2002(universe, pid, reason, killer_id, by_other, always_escape=always_escape)
    else:
        _destroy_ship_legacy(universe, pid, reason, killer_id)
    if K.info_tw2002():
        player.ship.scanner = None  # SCANNERS_HIDDEN_INFO.md s4: the scanner went down with the ship
    if K.hardware_tw2002():
        strip_v2(player.ship)  # d15: corbomite, beacons, probe, detonators, cloaks go with the hull
    if corbomite > 0 and killer_id:
        apply_corbomite(universe, pid, killer_id, corbomite)  # v3: the killer takes the blast


def _destroy_ship_legacy(universe: Universe, pid: str, reason: str, killer_id: str | None) -> None:
    """DEATH_MODE legacy: StarDock, a fresh Merchant Cruiser, credits x0.75."""
    player = universe.players[pid]

    death_sector = player.sector_id
    # Snapshot witnesses BEFORE the eject. Emit reads occupants at emit time;
    # moving the victim to StarDock first used to hide their own ship_destroyed.
    sector = universe.sectors.get(death_sector)
    witnesses = list(sector.occupant_ids) if sector is not None else []
    if pid not in witnesses:
        witnesses.append(pid)
    player.deaths += 1
    # Match 13 — snapshot pre-reset defense state so the NEXT observation's
    # post-death re-arm hint can say "you had only {Y} fighters when you
    # died to {reason}". Without this, the hint loses the concrete number
    # (ship fighters get reset to STARTING_FIGHTERS one line below) and
    # becomes generic — which agents have already proven they ignore.
    player.last_death_day = universe.day
    player.last_death_sector = death_sector
    player.last_death_killer_id = str(killer_id or "")
    player.last_death_fighters = int(player.ship.fighters)
    player.last_death_reason = str(reason)
    # Eject pilot to StarDock, downgrade ship, lose 25 % credits.
    try:
        universe.sectors[player.sector_id].occupant_ids.remove(pid)
    except ValueError:
        pass
    player.sector_id = K.STARDOCK_SECTOR
    player.end_port_visit()
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
    player.photon_damped_sector_id = None
    player.fighter_challenge = None
    player.flee_penalty = False

    universe.emit(
        EventKind.SHIP_DESTROYED,
        actor_id=killer_id,
        sector_id=death_sector,
        payload={
            "victim": pid,
            "reason": reason,
            "deaths": player.deaths,
            "death_sector": death_sector,
            "killer_id": killer_id,
            "_witnesses": witnesses,
        },
        summary=(
            f"*** {player.name}'s ship destroyed ({reason}); "
            f"ejected to StarDock [death #{player.deaths}/{K.MAX_DEATHS_BEFORE_ELIM}] ***"
        ),
    )

    threshold = K.elimination_deaths(universe.config)
    if threshold and player.deaths >= threshold:
        _eliminate(universe, player, killer_id)


def _eliminate(universe: Universe, player, killer_id: str | None) -> None:
    """Remove a player for good (the elimination threshold was reached)."""
    pid = player.id
    player.alive = False
    if K.fleet_on():  # SHIP_FLEET.md fl26: elimination removes the owner's parked ships (deliberate)
        from .fleet import drop_owner_fleet
        drop_owner_fleet(universe, pid)
    # Drop them off the occupant list (StarDock in legacy, the pod's sector in tw2002).
    try:
        universe.sectors[player.sector_id].occupant_ids.remove(pid)
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


# ---------------------------------------------------------------------------
# DEATH_MODE tw2002: escape pods. docs/playtests/combat/DEATH_ESCAPE_PODS.md.
# ---------------------------------------------------------------------------


def _pod_safe(universe: Universe, pid: str, sector_id: int) -> bool:
    """d4: a sector with no deployed fighters but your own or a friendly player's."""
    sector = universe.sectors.get(sector_id)
    if sector is None:
        return False
    dep = sector.fighters
    if dep is None or int(dep.count) <= 0:
        return True
    from .corp import deploy_friend
    return deploy_friend(universe, pid, dep)


def _pod_rng(universe: Universe, pid: str) -> random.Random:
    """Seeded per loss, apart from the universe stream so other dice do not shift."""
    return random.Random(f"pod:{universe.config.seed}:{universe.day}:{universe.tick}:{universe.seq}:{pid}")


def _pod_safe_path(universe: Universe, pid: str, start: int) -> int:
    """d4: random targets 3..20 hops out; walk each shortest path while it stays safe.

    The pod takes the path that gets farthest. No safe first hop: it stays put.
    """
    parent: dict[int, int | None] = {start: None}
    depth = {start: 0}
    order = [start]
    i = 0
    while i < len(order):
        cur = order[i]
        i += 1
        if depth[cur] >= K.POD_PATH_MAX_HOPS:
            continue
        for nxt in sorted(universe.sectors[cur].warps):
            nxt = int(nxt)
            if nxt in parent or nxt not in universe.sectors:
                continue
            parent[nxt] = cur
            depth[nxt] = depth[cur] + 1
            order.append(nxt)
    targets = [s for s in order if K.POD_PATH_MIN_HOPS <= depth[s] <= K.POD_PATH_MAX_HOPS]
    if not targets:
        return start
    picks = _pod_rng(universe, pid).sample(sorted(targets), min(K.POD_PATH_TRIES, len(targets)))
    best, best_hops = start, 0
    for target in picks:
        path: list[int] = []
        node: int | None = target
        while node is not None and node != start:
            path.append(node)
            node = parent[node]
        path.reverse()
        hops = 0
        reach = start
        for sid in path:
            if not _pod_safe(universe, pid, sid):
                break
            hops += 1
            reach = sid
        if hops > best_hops:
            best, best_hops = reach, hops
    return best


def _pod_destination(universe: Universe, player, death_sector: int, by_other: bool) -> int:
    """d4/d5: killed by someone else, the safe path; self-inflicted, the previous sector."""
    if by_other:
        return _pod_safe_path(universe, player.id, death_sector)
    prev = player.prev_sector_id
    if prev is not None and prev in universe.sectors:
        return int(prev)
    return death_sector


def _strip_ship(player, class_key: str) -> None:
    """d15: the new hull carries nothing over."""
    from .models import ShipClass as SC
    player.ship.ship_class = SC(class_key)
    player.ship.holds = int((K.hull_spec(class_key) or {}).get("holds", 0))
    player.ship.cargo = {c: 0 for c in player.ship.cargo}
    player.ship.cargo_cost = {c: 0.0 for c in player.ship.cargo_cost}
    player.ship.fighters = 0
    player.ship.shields = 0
    player.ship.photon_disabled_ticks = 0
    player.ship.genesis = 0
    player.ship.photon_missiles = 0
    player.ship.ether_probes = 0
    player.ship.mines = {MineType.ARMID: 0, MineType.LIMPET: 0, MineType.ATOMIC: 0}
    player.ship.transwarp_drive = None
    player.arrived_by_transwarp = False
    player.arrived_by_transport = False


def _place(universe: Universe, player, sector_id: int) -> None:
    try:
        universe.sectors[player.sector_id].occupant_ids.remove(player.id)
    except ValueError:
        pass
    player.sector_id = sector_id
    player.end_port_visit()
    if player.id not in universe.sectors[sector_id].occupant_ids:
        universe.sectors[sector_id].occupant_ids.append(player.id)
    # The pilot sees where the pod (or the free Scout) lands: it goes on the pilot's map.
    player.known_sectors.add(sector_id)
    player.known_warps[sector_id] = list(universe.sectors[sector_id].warps)


def _destroy_ship_tw2002(
    universe: Universe, pid: str, reason: str, killer_id: str | None, by_other: bool,
    *, always_escape: bool = False,
) -> None:
    """d1-d11: the pod, or Ship Destroyed. Elimination only by setting (d19).

    Credits stay under BANK_MODE legacy (d14). tw2002 hands them to bank.on_ship_lost first (gb13).
    """
    player = universe.players[pid]
    death_sector = player.sector_id
    sector = universe.sectors.get(death_sector)
    witnesses = list(sector.occupant_ids) if sector is not None else []
    if pid not in witnesses:
        witnesses.append(pid)
    player.deaths += 1
    player.last_death_day = universe.day
    player.last_death_sector = death_sector
    player.last_death_killer_id = str(killer_id or "")
    player.last_death_fighters = int(player.ship.fighters)
    player.last_death_reason = str(reason)
    if player.pods_day != universe.day:
        player.pods_day = universe.day
        player.pods_today = 0
    hull = player.ship.ship_class.value
    podded = always_escape or (hull not in K.PODLESS_HULLS and player.pods_today < K.PODS_PER_DAY)
    from .bank import on_ship_lost
    credits_lost = on_ship_lost(universe, player, killer_id, by_other, hull)
    if K.tow_on() and getattr(player.ship, "tow_lock", None) is not None:
        from .tow import release  # SHIP_TOW.md tt9: the beam dies with the hull; the towee stays put
        release(universe, player.ship, pid, "tower_destroyed")
    player.planet_landed = None
    player.photon_damped_sector_id = None
    player.fighter_challenge = None
    player.flee_penalty = False
    exp_before = int(player.experience)
    align_before = int(player.alignment)
    if podded:
        player.pods_today += 1
        dest = _pod_destination(universe, player, death_sector, by_other)
        if exp_before > 0:
            player.experience = exp_before - int(exp_before * K.POD_EXP_LOSS)
        _strip_ship(player, K.ESCAPE_POD)
        _place(universe, player, dest)
        outcome = "escape_pod"
        # The summary reaches the killer and every witness; where the pod went does not (fog).
        tail = f"escaped in a pod [pod {player.pods_today}/{K.PODS_PER_DAY} today]"
    else:
        dest = K.STARDOCK_SECTOR
        if exp_before > 0:
            player.experience = exp_before - int(exp_before * K.SD_EXP_LOSS)
        player.alignment = align_before - int(align_before * K.SD_ALIGN_LOSS)
        _strip_ship(player, K.SD_RESTART_HULL)
        _place(universe, player, dest)
        # d9/d11: out until midnight; the free scout waits at StarDock.
        player.turns_today = max(int(player.turns_today), int(player.turns_per_day))
        outcome = "ship_destroyed"
        tail = "SHIP DESTROYED - out until tomorrow, a free Scout waits at StarDock"

    universe.emit(
        EventKind.SHIP_DESTROYED,
        actor_id=killer_id,
        sector_id=death_sector,
        payload={
            "victim": pid,
            "reason": reason,
            "deaths": player.deaths,
            "death_sector": death_sector,
            "killer_id": killer_id,
            "outcome": outcome,
            "pod_sector": dest,
            "pods_today": player.pods_today,
            "exp_lost": exp_before - int(player.experience),
            "align_lost": align_before - int(player.alignment),
            "_witnesses": witnesses,
        },
        summary=f"*** {player.name}'s ship destroyed ({reason}); {tail} ***",
    )
    if K.bank_on():
        universe.events[-1].payload["credits_lost"] = credits_lost
    # fedspace-police-v1 f19: bounty only on real death (not pod)
    from .fed import record_bounty_on_death
    record_bounty_on_death(universe, pid, killer_id, outcome)
    threshold = K.elimination_deaths(universe.config)
    if threshold and player.deaths >= threshold:
        _eliminate(universe, player, killer_id)
