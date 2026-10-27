"""Progression + victory scoring.

Pulled out of `engine.runner` during the Phase 6 split. This module holds:

    * Rank / alignment labels (pure lookup into constants)
    * Experience awards (`_award_xp`) — cross-cutting helper invoked by
      action handlers (runner), combat resolution (combat), and day-tick
      planet advancement (planets).
    * Net-worth math — single planet value, corp-treasury share per member,
      and the authoritative `full_net_worth` that rolls them all together.
    * `check_victory` — end-of-action / end-of-day winner determination.

All functions here are pure w.r.t. the Universe: they read or mutate
Universe state and emit Events, but they don't perform I/O, call LLMs, or
depend on anything in `runner`. That's what lets `runner → victory` stay a
clean one-way import.
"""

from __future__ import annotations

from . import constants as K
from .models import EventKind, Universe


def rank_level(experience: int) -> int:
    """r1: 0 below 2 experience, then one level per doubling up to 22."""
    level = 0
    for i, thresh in enumerate(K.RANK_THRESHOLDS):
        if int(experience) >= thresh:
            level = i
        else:
            break
    return level


def side(alignment: int) -> str:
    """r4: zero or more is blue (good), negative is red (evil)."""
    return "good" if int(alignment) >= 0 else "evil"


def rank_for(experience: int, alignment: int = 0) -> str:
    if K.rank_tw2002():
        ladder = K.GOOD_RANKS if side(alignment) == "good" else K.EVIL_RANKS
        return ladder[rank_level(experience)]
    name = "Civilian"
    for thresh, label in K.RANK_TABLE:
        if experience >= thresh:
            name = label
        else:
            break
    return name


def alignment_label(alignment: int) -> str:
    if K.rank_tw2002():
        a = int(alignment)
        return "Good" if a > 0 else ("Evil" if a < 0 else "Neutral")
    label = "Neutral"
    for thresh, name in K.ALIGNMENT_TIERS:
        if alignment >= thresh:
            label = name
        else:
            break
    return label


def _award_xp(universe: Universe, pid: str, key: str, multiplier: int = 1) -> None:
    """Bump experience for the named achievement; safe no-op for unknown keys."""
    amount = K.xp_award(key) * multiplier
    if amount <= 0:
        return
    p = universe.players.get(pid)
    if p is None or not p.alive:
        return
    p.experience += amount


def is_fedsafe(player) -> bool:
    """u1: blue with 999 experience or less.

    FED_MODE tw2002 (FEDSPACE_POLICE.md f9): the SOURCE-CONFLICT floors are switches -
    K.FEDSAFE_MIN_ALIGNMENT (0; Iago/Bible "positive" reading = 1) and K.FEDSAFE_MAX_FIGHTERS
    (None; Iago "ftrs on your ship is 50 or less" = 50). Defaults keep the u1 rule.
    NOTE 117 reads that 50 through fedsafe_max_fighters when the profile is on.
    """
    min_align = 0
    max_figs = None
    if K.FED_MODE == "tw2002":
        min_align = int(K.FEDSAFE_MIN_ALIGNMENT)
        max_figs = K.fedsafe_max_fighters()
    if int(player.alignment) < min_align or int(player.experience) > K.FEDSAFE_MAX_EXPERIENCE:
        return False
    if max_figs is not None:
        ship = getattr(player, "ship", None)
        if ship is None or int(ship.fighters) > int(max_figs):
            return False
    return True


def fedspace_protects(target) -> bool:
    """u1: in FedSpace, legacy shields everyone; tw2002 only a fedsafe trader."""
    if not K.rank_tw2002():
        return True
    return hasattr(target, "experience") and is_fedsafe(target)


def is_commissioned(player) -> bool:
    """u2: 1,000 or more alignment is a Federal Commission."""
    return int(player.alignment) >= K.COMMISSION_ALIGNMENT


def _colours(mine: int, theirs: int) -> str:
    if mine == 0 or theirs == 0:
        return "neutral"
    return "same" if (mine > 0) == (theirs > 0) else "opposite"


def _toward_zero(num: int, den: int) -> int:
    q = abs(num) // den
    return q if num >= 0 else -q


def combat_rewards(universe: Universe, pid: str, enemy_alignment: int, fighters_lost: int,
                   *, sector_fighters: bool = False) -> tuple[int, int]:
    """x12/a1 (ship) and x14/a3 (sector fighters): what the attacker's lost fighters earn."""
    if not K.rank_tw2002() or fighters_lost <= 0:
        return 0, 0
    p = universe.players.get(pid)
    if p is None or not p.alive:
        return 0, 0
    lost = int(fighters_lost)
    theirs = int(enemy_alignment)
    kind = _colours(int(p.alignment), theirs)
    exp = lost // K.COMBAT_EXP_DIVISOR[kind]
    if sector_fighters:
        den = K.FIGHTER_ALIGN_DIVISOR["same" if kind == "same" else "opposite"]
    else:
        den = K.COMBAT_ALIGN_DIVISOR
    align = -_toward_zero(lost * theirs, den)
    p.experience = int(p.experience) + exp
    p.alignment = int(p.alignment) + align
    return exp, align


def kill_rewards(universe: Universe, killer_id: str, victim_experience: int, victim_alignment: int) -> None:
    """x13/a2: 10 percent of the victim's experience and half its alignment, sign reversed."""
    if not K.rank_tw2002():
        return
    p = universe.players.get(killer_id)
    if p is None or not p.alive:
        return
    p.experience = int(p.experience) + int(max(0, int(victim_experience)) * K.KILL_EXP_SHARE)
    p.alignment = int(p.alignment) - int(int(victim_alignment) * K.KILL_ALIGN_SHARE)


def planet_stock_unit_price(commodity_value: str) -> int:
    """Published base for one unit of planet stock.

    The revision history names the original sell "100% Planetary Trading":
    a mobile planet sells its goods to the port it sits on. That port's live
    bid moves with hidden MCIC, so the score uses the published base. The
    base already follows ECONOMY_SCALE_MODE. PLANET_ECONOMY_MODE does not
    change this price.
    """
    return int(K.COMMODITY_BASE_PRICE.get(commodity_value, 0) or 0)


def _planet_asset_value(planet, *, tax_basis: bool = False) -> int:
    """Value of a single owned planet, used in full_net_worth.

    Breakdown:
      * Citadel investment: the sum of all tier costs the player has
        actually paid for to reach `citadel_level`. L1 alone is 5,000 cr;
        L6 is 315,000 cr cumulative. This is sunk-cost valuation —
        the player can't actually liquidate a citadel, but for
        victory-scoring purposes it's the most defensible number.
      * Colonist pools: every colonist (idle + productively assigned)
        valued at K.COLONIST_PRICE. The agent paid that to acquire them
        at Terra; ferrying them here didn't make them cheaper, if
        anything it made them worth more because they now produce.
      * Stockpile: commodity inventory at base prices. Organics in
        this pile are also the growth gate (`planets.planet_growth_status`);
        the score still prices them as inventory only, with no forecast.
      * Treasury: raw credits sitting on-planet.
      * Planet defense: fighters at K.nw_fighter_value(), planet shields at
        K.nw_planet_shield_value() (NET_WORTH_MODE; legacy 50 / 10).
    """
    citadel_cost = 0
    if K.citadel_fidelity_on():
        class_id = planet.class_id.value
        table = K.CITADEL_CLASS_COSTS.get(class_id) or ()
        fuel = organics = equipment = 0
        for tier_idx in range(planet.citadel_level):
            if tier_idx >= len(table):
                break
            _colonists, tier_fuel, tier_org, tier_eq, _raw_days = table[tier_idx]
            fuel += tier_fuel
            organics += tier_org
            equipment += tier_eq
        citadel_cost += fuel * planet_stock_unit_price("fuel_ore")
        citadel_cost += organics * planet_stock_unit_price("organics")
        citadel_cost += equipment * planet_stock_unit_price("equipment")
    else:
        for tier_idx in range(planet.citadel_level):
            if tier_idx < len(K.CITADEL_TIER_COST):
                credit_cost, colonist_cost, _days = K.CITADEL_TIER_COST[tier_idx]
                citadel_cost += credit_cost
                # Colonists consumed by the citadel build are baked in at
                # COLONIST_PRICE — same valuation as colonists in cargo or
                # in the idle pool, keeps the math consistent.
                citadel_cost += colonist_cost * K.COLONIST_PRICE

    colonist_total = sum(planet.colonists.values()) if planet.colonists else 0
    # NOTE 75. Free start colonists still on this planet are not an asset.
    if not tax_basis and K.start_colonist_nw_live():
        exempt = min(colonist_total, int(getattr(planet, "free_start_colonists", 0) or 0))
        colonist_total -= exempt
    # Class M under the fidelity switch stores people. The handbook unit is
    # one thousand of them (S1, NOTE 19). COLONIST_PRICE is that unit, not
    # one person. The growth dividend keeps the per-person basis.
    if (
        not tax_basis
        and getattr(planet.class_id, "value", planet.class_id) == "M"
        and K.class_m_fidelity_live()
    ):
        colonist_total //= int(K.CLASS_M_PEOPLE_PER_THOUSAND)
    elif (
        not tax_basis
        and K.colonist_nw_units()
        and not K.colonist_units_live()
        and str(getattr(planet.class_id, "value", planet.class_id)) != "M"
        and int(K.colonists_per_hold()) > 1
    ):
        # The cargo-unit switch is off, so a Terra drop still stored people
        # in the handbook pool. Score the thousands. When that switch is on
        # the pool is already handbook units and dividing again would zero it.
        colonist_total //= int(K.colonists_per_hold())
    colonist_value = colonist_total * K.COLONIST_PRICE

    stockpile_value = 0
    cap_stock = (not tax_basis) and K.planet_value_score_mode() == "stock_cap"
    limits = K.PLANET_MAX_STOCK.get(planet.class_id.value, {}) if cap_stock else {}
    if planet.stockpile:
        for commodity, qty in planet.stockpile.items():
            if qty <= 0:
                continue
            counted = int(qty)
            if cap_stock:
                counted = min(counted, int(limits.get(commodity.value, counted)))
            stockpile_value += counted * planet_stock_unit_price(commodity.value)

    if (
        K.genesis_score_fair()
        and getattr(planet, "origin", "") == "genesis"
        and int(planet.citadel_level or 0) == 0
        and planet.stockpile
    ):
        _colonists, fuel, organics, equipment, _days = K.citadel_class_cost(planet.class_id.value, 1)
        seeded = {"fuel_ore": fuel, "organics": organics, "equipment": equipment}
        for commodity, qty in planet.stockpile.items():
            excluded = min(int(qty), int(seeded.get(commodity.value, 0)))
            if excluded > 0:
                stockpile_value -= excluded * planet_stock_unit_price(commodity.value)
        if stockpile_value < 0:
            stockpile_value = 0

    if tax_basis:
        # The growth dividend keeps its pre-NET_WORTH_MODE basis, so the valuation change moves the
        # score only, not credits (FULLGAME_FIXES_V1.md).
        defense_value = planet.fighters * K.FIGHTER_COST + planet.shields * 10
    else:
        fighter_each = 0 if K.planet_value_score_mode() == "no_fighters" else K.nw_fighter_value()
        defense_value = planet.fighters * fighter_each + planet.shields * K.nw_planet_shield_value()
    held = 0
    if K.planet_nw_live() and not tax_basis:
        held = _construction_contents(planet)
    if (not tax_basis) and K.planet_value_score_mode() == "colonists":
        return colonist_value
    return citadel_cost + colonist_value + stockpile_value + planet.treasury + defense_value + held


def _construction_contents(planet) -> int:
    """Goods already spent on the level that is still building.

    The stockpile no longer holds them, and citadel_level does not count them
    until the day the level finishes. Scoring them here keeps the planet's
    value flat across that wait. A finished level is already in citadel_cost.
    """
    target = int(getattr(planet, "citadel_target", 0) or 0)
    level = int(planet.citadel_level or 0)
    if target <= level:
        return 0
    if level == 0 and K.genesis_score_fair() and getattr(planet, "origin", "") == "genesis":
        # A genesis planet's seed is exactly the level-1 goods. Under GENESIS_SCORE fair
        # those do not count until level 1 is built, so spending them on that build adds nothing yet.
        return 0
    next_level = level + 1
    if K.citadel_fidelity_on() or K.CITADEL_COST_MODE == "class":
        colonists, fuel, organics, equipment, _days = K.citadel_class_cost(planet.class_id.value, next_level)
        value = (
            fuel * planet_stock_unit_price("fuel_ore")
            + organics * planet_stock_unit_price("organics")
            + equipment * planet_stock_unit_price("equipment")
        )
        if K.CITADEL_COST_MODE == "class" and not K.citadel_fidelity_on():
            value += colonists * K.COLONIST_PRICE
        return value
    tier_idx = next_level - 1
    if tier_idx < len(K.CITADEL_TIER_COST):
        credit_cost, colonist_cost, _days = K.CITADEL_TIER_COST[tier_idx]
        return credit_cost + colonist_cost * K.COLONIST_PRICE
    return 0


def planet_tax_value(planet) -> int:
    """Planet value the growth dividend is measured on (fighters 50, shields 10 in every mode)."""
    return _planet_asset_value(planet, tax_basis=True)


def _corp_treasury_share(universe: Universe, player) -> int:
    """Per-member share of the corp treasury, for net_worth attribution.

    Corp treasury used to be orphaned value — credits got deposited and
    never showed up in anyone's score. That made `corp_deposit` a
    strictly-dominated action for non-CEO members (who can't withdraw).
    Now every ALIVE member gets an equal share of the treasury credited
    to their net worth. Eliminated members drop out so the share grows
    as rivals die. Deposit still moves credits out of player.credits,
    so you won't satisfy the economic-victory threshold by hoarding in
    the treasury — but you WILL get credit for it under time net worth.
    """
    ticker = getattr(player, "corp_ticker", None)
    if not ticker:
        return 0
    corp = universe.corporations.get(ticker)
    if corp is None or corp.treasury <= 0:
        return 0
    alive_members = [
        mid for mid in corp.member_ids
        if mid in universe.players and universe.players[mid].alive
    ]
    if not alive_members or player.id not in alive_members:
        return 0
    return corp.treasury // len(alive_members)


def economic_threshold(max_days: int) -> int:
    """Credits on hand that end the game. 100,000,000 at 30 days, never under 500,000."""
    threshold = int(K.VICTORY_CREDITS_THRESHOLD * (int(max_days) / K.VICTORY_DEFAULT_MAX_DAYS))
    return max(500_000, threshold)


def end_rule_line(max_days: int) -> str:
    """The one line Game Status and Help print. Numbers come from this game."""
    days = int(max_days)
    bar = f"{economic_threshold(days):,}"
    if K.planet_value_score_mode() == "experience":
        measure = (
            "the trader with the most experience wins "
            "(v3.11 ranks traders by experience; the original game has no end date, this beta adds one)"
        )
    else:
        measure = "the trader with the highest net worth wins"
    if K.econ_win_off_live():  # NOTE 178: no instant credits win in v3.11
        return f"How this game ends: at the end of Day {days} {measure}."
    return (
        f"How this game ends: at the end of Day {days} {measure}. "
        f"Instant win: {bar} credits on hand."
    )


def _place_word(n: int) -> str:
    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _ranking_bits(universe: Universe, player, scores: dict) -> tuple[str, str]:
    ordered = sorted(scores.items(), key=lambda item: (-int(item[1]), str(item[0])))
    bits = []
    place = None
    for index, (pid, score) in enumerate(ordered, 1):
        who = universe.players.get(pid)
        name = who.name if who is not None else str(pid)
        bits.append(f"{_place_word(index)} {name} {int(score)}")
        if pid == player.id:
            place = index
    yours = f" You finished {_place_word(place)} of {len(ordered)}." if place else ""
    return ", ".join(bits), yours


def game_over_panel(universe: Universe, player) -> str | None:
    """The end screen, from the game-over record. None until the game has ended."""
    if not universe.finished:
        return None
    ev = None
    for row in reversed(universe.events):
        if row.kind is EventKind.GAME_OVER:
            ev = row
            break
    if ev is None:
        return None
    payload = ev.payload or {}
    reason = str(payload.get("reason") or universe.win_reason or "")
    creator = reason == "creator"
    if reason not in ("time_experience", "time_net_worth", "creator"):
        return None
    if creator and payload.get("score_kind") == "experience":
        scores = payload.get("all_scores")
        kind = "experience"
    elif creator:
        scores = payload.get("all_worths")
        kind = "net worth"
    else:
        scores = payload.get("all_scores") if reason == "time_experience" else payload.get("all_worths")
        kind = "experience" if payload.get("score_kind") == "experience" or reason == "time_experience" else "net worth"
    if creator and (not isinstance(scores, dict) or not scores):
        return "GAME OVER - Ended by the game's creator."
    if not isinstance(scores, dict) or not scores:
        return None
    bits, yours = _ranking_bits(universe, player, scores)
    if creator:
        return f"GAME OVER - Ended by the game's creator. Decided by {kind}: {bits}.{yours}"
    return (
        f"GAME OVER - time ran out after day {int(universe.config.max_days)}. "
        f"Decided by {kind}: {bits}.{yours}"
    )


def end_match_by_creator(universe: Universe) -> bool:
    """Stop this match now and rank whoever is still alive.

    Match infrastructure (creator-end-game-v1), not a rule switch: nothing here
    runs unless the creator ends the game. A second call is a no-op. Rankings
    use the same day-cap measure this process already uses.
    """
    if universe.finished:
        return False
    alive = [p for p in universe.players.values() if p.alive]
    universe.finished = True
    universe.win_reason = "creator"
    if not alive:
        universe.emit(
            EventKind.GAME_OVER,
            payload={"reason": "creator"},
            summary="Ended by the game's creator.",
        )
        return True
    if K.planet_value_score_mode() == "experience":
        scores = {p.id: int(p.experience) for p in alive}
        winner = max(alive, key=lambda p: scores[p.id])
        universe.winner_id = winner.id
        summary = f"Ended by the game's creator. {winner.name} leads on experience ({scores[winner.id]})"
        universe.emit(
            EventKind.GAME_OVER,
            actor_id=winner.id,
            payload={"reason": "creator", "score_kind": "experience", "all_scores": scores, "summary": summary},
            summary=summary,
        )
        return True
    worths = {p.id: full_net_worth(universe, p) for p in alive}
    winner = max(alive, key=lambda p: worths[p.id])
    universe.winner_id = winner.id
    summary = f"Ended by the game's creator. {winner.name} leads on net worth ({worths[winner.id]})"
    universe.emit(
        EventKind.GAME_OVER,
        actor_id=winner.id,
        payload={"reason": "creator", "all_worths": worths, "summary": summary},
        summary=summary,
    )
    return True


def full_net_worth(universe: Universe, player) -> int:
    """Total net worth = ship-side (Player.net_worth) + all planet assets
    + per-member share of corp treasury.

    Every call site that has a universe reference (victory check,
    observation build, server snapshot) should use this so the three
    sources of "net worth" all agree. Without it, a commander who
    ferries 3,000 colonists into a Citadel L1 planet sees their visible
    net worth go DOWN by 30,000 cr (the credits they spent) while the
    planet contribution reads zero — which is what caused
    time_net_worth = 24.2k to misrepresent Captain Reyes's actual
    value after deploying and building two planets.

    Corp treasury is now split equally across alive members so that
    `corp_deposit` isn't a strictly dominated action for non-CEOs —
    see `_corp_treasury_share`.
    """
    total = player.net_worth
    for planet in universe.planets.values():
        if planet.owner_id == player.id:
            total += _planet_asset_value(planet)
    total += _corp_treasury_share(universe, player)
    if K.nw_estimate_live():
        # Fighters this seat left in sectors, at the same rate as fighters aboard.
        # Planet fighters stay inside the planet value above.
        for sector in universe.sectors.values():
            group = sector.fighters
            if group is not None and group.owner_id == player.id:
                total += int(group.count) * int(K.nw_fighter_value())
    if universe.parked_ships:  # SHIP_FLEET.md fl27: own parked hulls, valued like the manned ship
        from .fleet import fleet_net_worth
        total += fleet_net_worth(universe, player.id)
    return total


def check_victory(universe: Universe) -> None:
    """Decide if the match has ended and, if so, emit GAME_OVER.

    Called at the end of every `apply_action` and every `tick_day`. Three
    paths to victory:

      1. Elimination — only one player is still `alive`.
      2. Economic — any player's liquid credits exceed a length-scaled
         threshold (100M at 30 days default, floored at 500k).
      3. Day cap — `universe.day` has rolled past `max_days`; highest
         `full_net_worth` wins.
    """
    if universe.finished:
        return
    alive = [p for p in universe.players.values() if p.alive]
    play_to_cap = getattr(universe.config, "play_to_day_cap", False)

    # Safety: if EVERYONE is dead we end immediately regardless of flag,
    # otherwise the scheduler would idle for the rest of the match.
    if not alive and len(universe.players) > 0:
        universe.finished = True
        universe.win_reason = "no_survivors"
        universe.emit(
            EventKind.GAME_OVER,
            payload={"reason": "no_survivors"},
            summary="GAME OVER — all players eliminated",
        )
        return

    # Elimination — skipped when play_to_day_cap is set so the remaining
    # survivor keeps playing solo until time runs out.
    if not play_to_cap and len(alive) == 1 and len(universe.players) > 1:
        universe.finished = True
        universe.winner_id = alive[0].id
        universe.win_reason = "elimination"
        winner_worth = full_net_worth(universe, alive[0])
        universe.emit(
            EventKind.GAME_OVER,
            actor_id=alive[0].id,
            payload={"reason": "elimination", "net_worth": winner_worth},
            summary=f"GAME OVER — {alive[0].name} is the last player standing",
        )
        return

    # Credits victory — scale the bar to match length so short matches can
    # actually finish economically. Default 30-day match keeps the classic 100M
    # target; a 3-day match shrinks to ~1M (still hard to hit with pure trading
    # but attainable with aggressive upgrades + raiding + planet farming).
    # Also gated by play_to_day_cap so a long watch-match can't be cut short
    # by a credit spike.
    if not play_to_cap and not K.econ_win_off_live():  # NOTE 178 GAP 14.6
        threshold = economic_threshold(universe.config.max_days)
        for p in alive:
            if p.credits >= threshold:
                universe.finished = True
                universe.winner_id = p.id
                universe.win_reason = "economic"
                universe.emit(
                    EventKind.GAME_OVER,
                    actor_id=p.id,
                    payload={"reason": "economic", "credits": p.credits, "threshold": threshold},
                    summary=f"GAME OVER — {p.name} achieved economic dominance ({p.credits}cr, target {threshold}cr)",
                )
                return

    # Day cap. Rank by the FULL net worth (ship assets + every planet
    # the commander owns) so investing in Genesis + Citadels is the
    # winning strategy, not just hoarding cash at StarDock.
    if universe.day > universe.config.max_days:
        universe.finished = True
        if alive:
            if K.planet_value_score_mode() == "experience":
                # Experience is the score. Ship and planet figures are the real
                # full_net_worth parts, never experience minus credits.
                worths = {p.id: int(p.experience) for p in alive}
                winner = max(alive, key=lambda p: worths[p.id])
                winner_worth = worths[winner.id]
                universe.winner_id = winner.id
                universe.win_reason = "time_experience"
                summary = f"GAME OVER — time expired; {winner.name} wins on experience ({winner_worth})"
                ship_parts: dict[str, int] = {}
                planet_parts: dict[str, int] = {}
                for seat in alive:
                    ship_nw = int(seat.net_worth)
                    full = int(full_net_worth(universe, seat))
                    ship_parts[seat.id] = ship_nw
                    planet_parts[seat.id] = full - ship_nw
                universe.emit(
                    EventKind.GAME_OVER,
                    actor_id=winner.id,
                    payload={
                        "reason": "time_experience",
                        "score_kind": "experience",
                        "all_scores": worths,
                        "summary": summary,
                        "net_worth_ship": ship_parts,
                        "net_worth_planets": planet_parts,
                    },
                    summary=summary,
                )
            else:
                worths = {p.id: full_net_worth(universe, p) for p in alive}
                winner = max(alive, key=lambda p: worths[p.id])
                winner_worth = worths[winner.id]
                # Show the breakdown in the summary so spectators can see
                # WHY the winner won — ship vs planets. Crucial feedback for
                # tuning agent behavior.
                ship_side = winner.net_worth
                planet_side = winner_worth - ship_side
                universe.winner_id = winner.id
                universe.win_reason = "time_net_worth"
                summary = (
                    f"GAME OVER — time expired; {winner.name} wins on net worth "
                    f"({winner_worth}cr = {ship_side}cr ship + {planet_side}cr planets)"
                )
                universe.emit(
                    EventKind.GAME_OVER,
                    actor_id=winner.id,
                    payload={
                        "reason": "time_net_worth",
                        "net_worth": winner_worth,
                        "net_worth_ship": ship_side,
                        "net_worth_planets": planet_side,
                        "all_worths": worths,
                    },
                    summary=summary,
                )
        else:
            universe.emit(EventKind.GAME_OVER, summary="GAME OVER — no survivors")


# Legacy-name alias: pre-split code imported `_check_victory` from runner.
# We expose it under the public name above; the shim is kept both here
# and re-exported from runner.py so either call site keeps working.
_check_victory = check_victory
