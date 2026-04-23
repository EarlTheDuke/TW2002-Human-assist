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


def rank_for(experience: int) -> str:
    name = "Civilian"
    for thresh, label in K.RANK_TABLE:
        if experience >= thresh:
            name = label
        else:
            break
    return name


def alignment_label(alignment: int) -> str:
    label = "Neutral"
    for thresh, name in K.ALIGNMENT_TIERS:
        if alignment >= thresh:
            label = name
        else:
            break
    return label


def _award_xp(universe: Universe, pid: str, key: str, multiplier: int = 1) -> None:
    """Bump experience for the named achievement; safe no-op for unknown keys."""
    amount = K.XP_AWARDS.get(key, 0) * multiplier
    if amount <= 0:
        return
    p = universe.players.get(pid)
    if p is None or not p.alive:
        return
    p.experience += amount


def _planet_asset_value(planet) -> int:
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
      * Stockpile: commodity inventory at base prices.
      * Treasury: raw credits sitting on-planet.
      * Planet defense: fighters/shields at StarDock equivalent prices.
    """
    citadel_cost = 0
    for tier_idx in range(planet.citadel_level):
        if tier_idx < len(K.CITADEL_TIER_COST):
            credit_cost, colonist_cost, _days = K.CITADEL_TIER_COST[tier_idx]
            citadel_cost += credit_cost
            # Colonists consumed by the citadel build are baked in at
            # COLONIST_PRICE — same valuation as colonists in cargo or
            # in the idle pool, keeps the math consistent.
            citadel_cost += colonist_cost * K.COLONIST_PRICE

    colonist_total = sum(planet.colonists.values()) if planet.colonists else 0
    colonist_value = colonist_total * K.COLONIST_PRICE

    stockpile_value = 0
    if planet.stockpile:
        for commodity, qty in planet.stockpile.items():
            if qty <= 0:
                continue
            base = K.COMMODITY_BASE_PRICE.get(commodity.value, 0)
            stockpile_value += qty * base

    defense_value = planet.fighters * K.FIGHTER_COST + planet.shields * 10
    return citadel_cost + colonist_value + stockpile_value + planet.treasury + defense_value


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
    if not play_to_cap:
        threshold = int(
            K.VICTORY_CREDITS_THRESHOLD
            * (universe.config.max_days / K.VICTORY_DEFAULT_MAX_DAYS)
        )
        threshold = max(500_000, threshold)
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
