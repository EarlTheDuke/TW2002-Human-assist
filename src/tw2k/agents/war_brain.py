"""Pure planetary-war decisions. No universe, no rng.

BOTS_USE_PLANET_WARFARE.md bw15. The planet fight copies runner._planet_odds_fight
so a bot can price a siege without calling the engine.
"""

from __future__ import annotations

from typing import Any

from ..engine import constants as K


def planet_fight(
    attacker_fighters: int,
    defender_fighters: int,
    defender_shields: int,
    reaction_pct: int,
    ship_class: str,
    *,
    photon_damped: bool = False,
) -> tuple[int, int, int]:
    """Return attacker fighters left, defender fighters left, and shields left.

    Same order as the engine: one shield soak, reaction waves, then the grind.
    A photon damp skips the reaction waves.
    """
    a_fighters = int(attacker_fighters)
    d_fighters = int(defender_fighters)
    d_shields = int(defender_shields)
    if d_shields > 0:
        removed = min(d_shields, a_fighters // int(K.PLANET_SHIELD_ODDS))
        d_shields -= removed
        if d_shields > 0:
            return a_fighters, d_fighters, d_shields
    pct = max(0, min(100, int(reaction_pct)))
    reaction = d_fighters * pct // 100
    defenders = d_fighters - reaction
    if photon_damped:
        reaction = 0
        defenders = d_fighters
    spec = K.SHIP_SPECS[ship_class] if ship_class in K.SHIP_SPECS else (K.hull_spec(ship_class) or {})
    wave_cap = (int(K.PLANET_OFFENSE_WAVE_NUM) * (
        int(spec.get("max_fighters", 0) or 0) + int(spec.get("max_shields", 0) or 0)
    )) // int(K.PLANET_OFFENSE_WAVE_DEN)
    if wave_cap < 1:
        wave_cap = 1
    while reaction > 0 and a_fighters > 0:
        sent = min(reaction, wave_cap)
        kill = sent * int(K.PLANET_OFFENSE_ODDS)
        if kill >= a_fighters:
            needed = min(sent, (a_fighters + int(K.PLANET_OFFENSE_ODDS) - 1) // int(K.PLANET_OFFENSE_ODDS))
            a_fighters = 0
            reaction -= needed
        else:
            a_fighters -= kill
            reaction -= sent
        d_fighters = defenders + reaction
        if a_fighters <= 0:
            return 0, d_fighters, d_shields
    d_fighters = defenders + reaction
    if d_fighters > 0 and a_fighters > 0:
        killed = min(d_fighters, a_fighters // int(K.PLANET_DEFENSE_ODDS))
        a_fighters -= killed * int(K.PLANET_DEFENSE_ODDS)
        d_fighters -= killed
    return a_fighters, d_fighters, d_shields


def fighters_needed(
    defender_fighters: int,
    defender_shields: int,
    reaction_pct: int,
    ship_class: str,
    *,
    photon_damped: bool = False,
) -> int:
    """Smallest attacker stack that leaves the planet with no shields and no fighters."""
    lo, hi = 0, max(1, int(defender_shields) * int(K.PLANET_SHIELD_ODDS) + int(defender_fighters) * 8 + 1)
    while planet_fight(hi, defender_fighters, defender_shields, reaction_pct, ship_class, photon_damped=photon_damped)[1] > 0 or planet_fight(hi, defender_fighters, defender_shields, reaction_pct, ship_class, photon_damped=photon_damped)[2] > 0:
        hi *= 2
        if hi > 50_000_000:
            return hi
    while lo < hi:
        mid = (lo + hi) // 2
        left_a, left_d, left_s = planet_fight(mid, defender_fighters, defender_shields, reaction_pct, ship_class, photon_damped=photon_damped)
        if left_d <= 0 and left_s <= 0 and left_a > 0:
            hi = mid
        else:
            lo = mid + 1
    return lo


def armid_sector(
    *,
    home: int | None,
    home_is_corridor: bool,
    dead_end_entrance: int | None,
    own_planet_sector: int | None,
    here_is_fedspace: bool,
) -> int | None:
    """Where bought armids go. A shared corridor is not mined. FedSpace is never mined."""
    if here_is_fedspace:
        return None
    if home is not None and not home_is_corridor:
        return int(home)
    if dead_end_entrance is not None:
        return int(dead_end_entrance)
    if own_planet_sector is not None:
        return int(own_planet_sector)
    return None


def threat_map(entries: list[dict[str, Any]], *, limit: int | None = None) -> list[dict[str, Any]]:
    """Keep the newest sightings. The cap drops the oldest. Nothing here reads a universe."""
    cap = int(K.BOT_WAR_MAP_MAX if limit is None else limit)
    kept = [dict(row) for row in entries if isinstance(row, dict)]
    if len(kept) > cap:
        kept = kept[-cap:]
    return kept


def siege_estimate(planet_seen: dict[str, Any], my_ship: dict[str, Any], sector_seen: dict[str, Any] | None = None, turns: int = 0) -> dict[str, Any]:
    """Price one landing. Hazards and quasar are added by the caller once they are seen."""
    ship_class = str(my_ship.get("ship_class") or "merchant_cruiser")
    have = int(my_ship.get("fighters") or 0)
    d_f = int(planet_seen.get("fighters") or 0)
    d_s = int(planet_seen.get("shields") or 0)
    pct = int(planet_seen.get("military_reaction_pct") or 0)
    photon = bool(my_ship.get("photon_damped"))
    needed = fighters_needed(d_f, d_s, pct, ship_class, photon_damped=photon)
    left, def_left, shields_left = planet_fight(have, d_f, d_s, pct, ship_class, photon_damped=photon)
    survive = def_left <= 0 and shields_left <= 0 and left > 0
    return {
        "fighters_needed": needed,
        "expected_fighters_left": left if survive else 0,
        "survive": survive,
        "turns": int(turns),
        "sector_seen": bool(sector_seen),
    }


def pad_stale(value: int, *, day: int, seen_day: int) -> int:
    """A sighting older than the stale window is padded. A fresh one is kept."""
    if int(day) - int(seen_day) > int(K.BOT_WAR_INTEL_STALE_DAYS):
        return int(value) * (100 + int(K.BOT_WAR_INTEL_STALE_PAD_PCT)) // 100
    return int(value)


def picket_qty(
    fighters_aboard: int,
    *,
    floor: int,
    already: int = 0,
    room: int | None = None,
    dead_end_entrance: bool = False,
    travel: bool = False,
) -> dict[str, Any] | None:
    """Defensive picket. Offensive only at a dead-end entrance. Travel pickets stay off."""
    if travel and not K.BOT_WAR_TRAVEL_PICKETS:
        return None
    aboard = int(fighters_aboard)
    keep = aboard * int(K.BOT_WAR_KEEP_ABOARD_PCT) // 100
    spare = max(0, aboard - max(int(floor), keep))
    target = max(int(K.BOT_WAR_PICKET_MIN), spare * int(K.BOT_WAR_WALL_PCT) // 100)
    send = min(target - int(already), spare)
    if room is not None:
        send = min(send, int(room))
    if send <= 0:
        return None
    offensive = bool(dead_end_entrance) and bool(K.BOT_WAR_OFFENSIVE_AT_ENTRANCE) and not travel
    return {"qty": int(send), "mode": "offensive" if offensive else "defensive"}


def defence_budget(liquid_net_worth: int) -> int:
    """The day's citadel budget: a percent of liquid net worth."""
    return max(0, int(liquid_net_worth)) * int(K.BOT_WAR_DEFENCE_BUDGET_PCT) // 100


def stock_deposit(
    citadel_level: int,
    *,
    planet_fighters: int,
    planet_shields: int,
    aboard_fighters: int,
    aboard_shields: int,
    credit_budget: int,
    fighter_price: int,
    shield_price: int,
) -> dict[str, int]:
    """Gap to the level ladder, capped by what is aboard and by the credit budget."""
    level = int(citadel_level)
    if level not in K.BOT_WAR_PLANET_FIGHTERS_BY_LEVEL:
        return {"fighters": 0, "shields": 0}
    want_f = min(
        max(0, int(K.BOT_WAR_PLANET_FIGHTERS_BY_LEVEL[level]) - int(planet_fighters)),
        int(aboard_fighters),
    )
    want_s = min(
        max(0, int(K.BOT_WAR_PLANET_SHIELDS_BY_LEVEL[level]) - int(planet_shields)),
        int(aboard_shields),
    )
    budget = max(0, int(credit_budget))
    fighter_cost = max(0, int(fighter_price))
    shield_cost = max(0, int(shield_price))
    if fighter_cost > 0:
        want_f = min(want_f, budget // fighter_cost)
    left = budget - want_f * fighter_cost
    if shield_cost > 0:
        want_s = min(want_s, left // shield_cost)
    return {"fighters": int(want_f), "shields": int(want_s)}


def reaction_setting(citadel_level: int, *, already: bool) -> int | None:
    """Set military reaction once, at citadel 2 or higher."""
    if already or int(citadel_level) < 2:
        return None
    return int(K.BOT_WAR_REACTION_PCT)


def quasar_settings(citadel_level: int, *, already: bool, planet_ore: int) -> dict[str, int] | None:
    """Set both cannons once, at citadel 3 or higher, while ore stays at the floor."""
    if already or int(citadel_level) < 3 or int(planet_ore) < int(K.BOT_WAR_QUASAR_ORE_FLOOR):
        return None
    return {
        "sector_pct": int(K.BOT_WAR_QUASAR_SECTOR_PCT),
        "atm_pct": int(K.BOT_WAR_QUASAR_ATM_PCT),
    }


def retreat_reason(
    *,
    fighters: int,
    fighters_needed_remaining: int,
    shields: int,
    atmospheric_quasar: bool,
    rival_stronger: bool,
    turns_left: int,
) -> str | None:
    """Why a siege stops. None means the landing can continue."""
    needed = int(fighters_needed_remaining) * (100 + int(K.BOT_WAR_SIEGE_MARGIN_PCT)) // 100
    if int(fighters) < needed:
        return "margin"
    if int(shields) <= 0 and atmospheric_quasar:
        return "quasar"
    if rival_stronger:
        return "rival"
    if int(turns_left) < int(K.BOT_WAR_RESERVE_TURNS):
        return "turns"
    return None
