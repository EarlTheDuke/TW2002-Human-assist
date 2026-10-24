"""Read-only rules, scoring, ship stats, and StarDock prices.

Every number is read from the engine table named on the row. Nothing here
is a second copy of a price. The cockpit prints the words. The source
fields stay on the JSON for the bot seat.
"""

from __future__ import annotations

from typing import Any

from tw2k.engine import constants as K


def _ship_rows() -> list[dict[str, Any]]:
    rows = []
    extra = (
        "max_holds", "offensive_odds", "fighters_per_attack",
        "max_mines", "max_photons", "max_genesis",
    )
    for key, spec in K.ship_specs().items():
        row: dict[str, Any] = {
            "id": key,
            "name": spec.get("display_name") or key,
            "cost": int(spec.get("cost") or 0),
            "holds": int(spec.get("holds") or 0),
            "max_fighters": int(spec.get("max_fighters") or 0),
            "max_shields": int(spec.get("max_shields") or 0),
            "turns_per_warp": int(spec.get("turns_per_warp") or 0),
            "source": "src/tw2k/engine/constants.py ship_specs()",
        }
        for field in extra:
            if field in spec and spec[field] is not None:
                row[field] = spec[field]
        rows.append(row)
    return rows


def _price(name: str, amount: int, source: str) -> dict[str, Any]:
    return {"name": name, "price": int(amount), "source": source}


def _prices(ship_class: str, holds: int, day: int) -> list[dict[str, Any]]:
    base = "src/tw2k/engine/constants.py"
    rows = [
        _price("Fuel ore, base", K.COMMODITY_BASE_PRICE["fuel_ore"], base + " COMMODITY_BASE_PRICE"),
        _price("Organics, base", K.COMMODITY_BASE_PRICE["organics"], base + " COMMODITY_BASE_PRICE"),
        _price("Equipment, base", K.COMMODITY_BASE_PRICE["equipment"], base + " COMMODITY_BASE_PRICE"),
        _price("Fighter", K.fighter_unit_price(day), base + " fighter_unit_price()"),
        _price("Shield", K.shield_unit_price(day), base + " shield_unit_price()"),
        _price("Next cargo hold", K.hold_next_price(ship_class, holds, day), base + " hold_next_price()"),
        _price("Armid mine", K.armid_mine_cost(), base + " armid_mine_cost()"),
        _price("Limpet mine", K.limpet_mine_cost(), base + " limpet_mine_cost()"),
        _price("Atomic mine", K.ATOMIC_MINE_COST, base + " ATOMIC_MINE_COST"),
        _price("Photon missile", K.photon_missile_cost(), base + " photon_missile_cost()"),
        _price("Ether probe", K.ether_probe_cost(), base + " ether_probe_cost()"),
        _price("Genesis torpedo", K.genesis_torpedo_cost(), base + " genesis_torpedo_cost()"),
        _price("Cloaking device", K.CLOAK_COST, base + " CLOAK_COST"),
        _price("Mine disruptor", K.disruptor_cost(), base + " disruptor_cost()"),
        _price("Corbomite", K.CORBOMITE_COST, base + " CORBOMITE_COST"),
        _price("Marker beacon", K.BEACON_COST, base + " BEACON_COST"),
        _price("Psychic probe", K.psychic_probe_cost(), base + " psychic_probe_cost()"),
        _price("Atomic detonator", K.atomic_detonator_cost(), base + " atomic_detonator_cost()"),
        _price("Density scanner", K.DENSITY_SCANNER_COST, base + " DENSITY_SCANNER_COST"),
        _price("Holographic scanner", K.HOLO_SCANNER_COST, base + " HOLO_SCANNER_COST"),
        _price("Planet scanner", K.PLANET_SCANNER_COST, base + " PLANET_SCANNER_COST"),
    ]
    if K.ship_tw_on():
        rows.append(_price("TransWarp type 1", K.ship_tw_type1_cost(), base + " ship_tw_type1_cost()"))
        if K.tow_on():
            rows.append(_price("TransWarp type 2", K.ship_tw_type2_cost(), base + " ship_tw_type2_cost()"))
            rows.append(_price("TransWarp upgrade", K.ship_tw_upgrade_cost(), base + " ship_tw_upgrade_cost()"))
    return rows


def _rank_rows() -> list[dict[str, Any]]:
    if K.rank_tw2002():
        source = "src/tw2k/engine/victory.py rank_for; src/tw2k/engine/constants.py RANK_THRESHOLDS, GOOD_RANKS, EVIL_RANKS"
        return [
            {"experience": int(thresh), "good": K.GOOD_RANKS[i], "evil": K.EVIL_RANKS[i], "source": source}
            for i, thresh in enumerate(K.RANK_THRESHOLDS)
        ]
    return [
        {"experience": int(thresh), "good": name, "evil": name, "source": "src/tw2k/engine/constants.py RANK_TABLE"}
        for thresh, name in K.RANK_TABLE
    ]


def _haggle_band() -> str:
    if K.haggle_window_live():
        low, high = int(K.PORT_HAGGLE_LIVE_ROOM_PCT), int(K.PORT_HAGGLE_LIVE_END_PCT)
        return f"{low}% to {high}% of the offer"
    low, high = int(K.PORT_HAGGLE_MIN_PCT), int(K.PORT_HAGGLE_MAX_PCT)
    return f"{low}% to {high}% of the offer"


def stardock_class_label() -> int:
    """CV-e. Live map shows StarDock as Class 9. The stored id stays 8 (TRD-c)."""
    if K.port_class_live():
        return 9
    from tw2k.engine.models import PortClass

    return int(PortClass.STARDOCK)


def _planet_class_rows() -> list[dict[str, Any]]:
    """J catalog. Ratios, caps, and citadel costs are the engine tables."""
    goods = ("fuel_ore", "organics", "equipment")
    rows = []
    for letter, title in K.PLANET_CLASS_NAMES.items():
        ratio = K.PLANET_PROD_PER_UNIT[letter]
        citadel = []
        for level in range(1, int(K.CITADEL_LEVELS) + 1):
            colonists, fuel, organics, equipment, days = K.citadel_class_cost(letter, level)
            citadel.append({
                "level": level,
                "colonists": int(colonists),
                "fuel_ore": int(fuel),
                "organics": int(organics),
                "equipment": int(equipment),
                "days": int(days),
            })
        shown = "/".join(str(int(n)) for n in ratio)
        cap = int(K.PLANET_MAX_COLONISTS[letter])
        rows.append({
            "letter": letter,
            "name": title,
            "per_unit": {good: int(ratio[i]) for i, good in enumerate(goods)},
            "max_colonists": cap,
            "citadel": citadel,
            "value": f"{shown} colonists per unit, max colonists {cap}",
            "source": "src/tw2k/engine/constants.py PLANET_PROD_PER_UNIT, PLANET_MAX_COLONISTS, citadel_class_cost()",
        })
    return rows


def _citadel_rows() -> list[dict[str, Any]]:
    rows = []
    for letter in K.PLANET_CLASS_NAMES:
        for level in range(1, int(K.CITADEL_LEVELS) + 1):
            colonists, fuel, organics, equipment, days = K.citadel_class_cost(letter, level)
            rows.append({
                "name": f"{letter} L{level}",
                "value": (
                    f"colonists {int(colonists)}, fuel {int(fuel)}, organics {int(organics)}, "
                    f"equipment {int(equipment)}, days {int(days)}"
                ),
                "source": "src/tw2k/engine/constants.py citadel_class_cost()",
            })
    return rows


def _combat_rows() -> list[dict[str, Any]]:
    rows = [
        {
            "name": "Planet offense",
            "value": f"{int(K.PLANET_OFFENSE_ODDS)} to 1",
            "source": "src/tw2k/engine/constants.py PLANET_OFFENSE_ODDS",
        },
        {
            "name": "Planet defense",
            "value": f"{int(K.PLANET_DEFENSE_ODDS)} attacker fighters per planet fighter",
            "source": "src/tw2k/engine/constants.py PLANET_DEFENSE_ODDS",
        },
        {
            "name": "Planet shields",
            "value": f"{int(K.PLANET_SHIELD_ODDS)} attacker fighters per shield",
            "source": "src/tw2k/engine/constants.py PLANET_SHIELD_ODDS",
        },
    ]
    for key, spec in K.ship_specs().items():
        odds = spec.get("offensive_odds")
        if odds is None:
            continue
        rows.append({
            "name": spec.get("display_name") or key,
            "value": f"{odds} to 1, {int(spec.get('fighters_per_attack') or 0)} fighters per attack",
            "source": "src/tw2k/engine/constants.py ship_specs()",
        })
    return rows


def _exp_rows() -> list[dict[str, Any]]:
    source = "src/tw2k/engine/constants.py xp_award()"
    keys = (
        "trade", "warp", "kill_player", "kill_ferr", "build_citadel_lvl",
        "deploy_genesis", "claim_planet", "alliance", "scan", "probe",
        "first_dock", "daily", "destroy_planet", "destroy_port",
    )
    rows = [
        {"name": key, "value": int(K.xp_award(key)), "source": source}
        for key in keys
        if int(K.xp_award(key)) or key in ("warp",)
    ]
    rows.extend([
        {"name": "Kill experience share", "value": K.KILL_EXP_SHARE, "source": "src/tw2k/engine/constants.py KILL_EXP_SHARE"},
        {"name": "Kill alignment share", "value": K.KILL_ALIGN_SHARE, "source": "src/tw2k/engine/constants.py KILL_ALIGN_SHARE"},
        {
            "name": "Combat experience divisor",
            "value": ", ".join(f"{name} {int(num)}" for name, num in K.COMBAT_EXP_DIVISOR.items()),
            "source": "src/tw2k/engine/constants.py COMBAT_EXP_DIVISOR",
        },
        {"name": "Daily alignment", "value": int(K.DAILY_ALIGNMENT), "source": "src/tw2k/engine/constants.py DAILY_ALIGNMENT"},
        {"name": "Genesis alignment", "value": int(K.GENESIS_ALIGNMENT), "source": "src/tw2k/engine/constants.py GENESIS_ALIGNMENT"},
    ])
    return rows


def _rules_in_force(player, turns_per_day: int) -> dict[str, Any]:
    """DOC-b. Switches that are on, and the numbers this game is using."""
    rate, over, align = K.tax_terms()
    numbers = [
        {"name": "Turns per day", "value": int(turns_per_day), "source": "player.turns_per_day"},
        {"name": "Tax rate", "value": f"{int(rate)}%", "source": "src/tw2k/engine/constants.py tax_terms()"},
        {"name": "Tax threshold", "value": int(over), "source": "src/tw2k/engine/constants.py tax_terms()"},
        {"name": "Tax alignment", "value": int(align), "source": "src/tw2k/engine/constants.py tax_terms()"},
        {"name": "Bank cap", "value": int(K.BANK_MAX_BALANCE), "source": "src/tw2k/engine/constants.py BANK_MAX_BALANCE"},
        {"name": "Haggle band", "value": _haggle_band(), "source": "src/tw2k/engine/constants.py haggle window"},
    ]
    switches = []
    for helper, (switch, why) in K.V311_PROFILE_HELPERS.items():
        if getattr(K, helper)():
            switches.append({"name": switch, "on": True, "why": why, "source": f"src/tw2k/engine/constants.py {helper}()"})
    return {
        "id": "rules_in_force",
        "title": "Rules in force",
        "source": "src/tw2k/engine/constants.py",
        "body": "These are the fidelity switches on in this game, and the numbers they use.",
        "rows": numbers + switches,
    }


def game_reference(player=None, day: int = 1, max_days: int | None = None) -> dict[str, Any]:
    from tw2k.engine.victory import end_rule_line

    ship = getattr(player, "ship", None)
    ship_class = getattr(getattr(ship, "ship_class", None), "value", None) or "merchant_cruiser"
    turns_per_day = int(getattr(player, "turns_per_day", 0) or K.STARTING_TURNS_PER_DAY)
    holds = int(getattr(ship, "holds", 0) or 0)
    today = int(day or 1)
    days = int(max_days if max_days is not None else K.VICTORY_DEFAULT_MAX_DAYS)
    fighter = int(K.nw_fighter_value())
    shield = int(K.nw_shield_value())
    colonist = int(K.COLONIST_PRICE)
    next_hold = int(K.hold_next_price(ship_class, holds, today))
    if K.shop_price_live():
        hold_formula = "550 + 20 * (holds already owned - 20)"
    else:
        hold_formula = f"the day's base ({int(K.hold_day_base(today))}) + 20 per hold already owned"
    regen_pct = int(round(float(K.PORT_REGEN_PER_DAY) * 100))
    if int(K.CORP_CREATE_COST) == 0:
        corp_line = "A corporation costs nothing."
    else:
        corp_line = f"A corporation costs {int(K.CORP_CREATE_COST):,} cr."
    estimate = f" {K.NW_ESTIMATE_NOTE}" if K.nw_estimate_live() else ""
    scoring = (
        f"The number on V is your net worth. It adds your credits, the cargo in your holds at the base prices, "
        f"and colonists in the holds at {colonist} cr each. "
        f"A fighter on your ship counts as {fighter} cr. A shield counts as {shield} cr. "
        f"The hull counts at half its price. Other gear counts at its StarDock price. "
        f"Your bank balance counts when the bank is on. "
        f"V also adds each planet, your share of the corp treasury, and parked ships. "
        f"Taking colonists at Terra does not charge credits.{estimate} "
        f"Experience ranks are listed below. Zero alignment or above uses the good title. "
        f"Below zero uses the evil title."
    )
    rules = (
        "Play from the cockpit. V is day, turns, credits, bank, net worth, rank, experience, "
        "and alignment. I is this ship: holds in use, empty holds, and fighter and shield room. "
        "The sector line shows the port, each planet with its class first, traders, ships, fighters, "
        "mines, a beacon, NavHaz when this sector has it, and the warps. A warp in parentheses is not on this map yet. "
        "The port table is the trade screen. Computer, then R, is the port report. "
        "Computer, then K, is the known universe. Computer, then O, is the avoid list. "
        "The prices below are what StarDock charges today, including a fighter, a shield, and the next cargo hold on this ship. "
        f"The bank holds at most {int(K.BANK_MAX_BALANCE):,} cr. "
        f"A port buys only until it is full. The price eases as it fills. Stock grows back at {regen_pct}% per day. "
        f"The next hold on this ship costs {next_hold:,} cr. Formula: {hold_formula}. "
        f"{end_rule_line(days)} "
        f"Tri-Cron: ante {int(K.TRICRON_ANTE):,} cr, {int(K.TRICRON_ROUNDS)} rounds, pays 2:1, "
        f"jackpot {int(K.TRICRON_OPENING_JACKPOT):,} cr. "
        f"{corp_line}"
    )
    from tw2k.engine.models import PortClass

    rules += (
        f" StarDock is shown as Class {stardock_class_label()}. "
        f"Its stored id stays {int(PortClass.STARDOCK)}."
    )
    out: dict[str, Any] = {
        "day": today,
        "ship_class": ship_class,
        "holds": holds,
        "sections": [
            _rules_in_force(player, turns_per_day),
            {"id": "rules", "title": "Rules", "source": "src/tw2k/server/reference.py", "body": rules},
            {
                "id": "scoring",
                "title": "Scoring and net worth",
                "source": "src/tw2k/engine/models.py Player.net_worth; src/tw2k/engine/victory.py full_net_worth",
                "body": scoring,
            },
            {
                "id": "ranks",
                "title": "Experience ranks",
                "source": "src/tw2k/engine/victory.py rank_for",
                "rows": _rank_rows(),
            },
            {
                "id": "ships",
                "title": "Ship stats",
                "source": "src/tw2k/engine/constants.py ship_specs()",
                "rows": _ship_rows(),
            },
            {
                "id": "prices",
                "title": "StarDock prices",
                "source": "src/tw2k/engine/constants.py",
                "rows": _prices(ship_class, holds, today),
            },
            {
                "id": "planet_classes",
                "title": "Planet classes",
                "source": "docs/reference/tw2002/eis_tw2002_v3_docs/CompDisplays.html Planetary Specs; S1_planet_handbook_v1.01.html",
                "body": "Computer J lists one row per planet class. Your own worlds stay under Your planets.",
                "rows": _planet_class_rows(),
            },
            {
                "id": "citadel_tables",
                "title": "Citadel tables",
                "source": "docs/reference/tw2002/S1_planet_handbook_v1.01.html; src/tw2k/engine/constants.py citadel_class_cost()",
                "rows": _citadel_rows(),
            },
            {
                "id": "combat_odds",
                "title": "Combat odds",
                "source": "docs/reference/tw2002/S2_cabal_formulas.html; src/tw2k/engine/constants.py ship_specs()",
                "rows": _combat_rows(),
            },
            {
                "id": "flee_rule",
                "title": "Flee rule",
                "source": "src/tw2k/engine/constants.py COMBAT_FLEE_RATIO, FLEE_PENALTY_TURNS",
                "body": "An attacker with more fighters than this multiple of the defender's fighters plus shields can be fled.",
                "rows": [
                    {
                        "name": "Flee ratio",
                        "value": K.COMBAT_FLEE_RATIO,
                        "source": "src/tw2k/engine/constants.py COMBAT_FLEE_RATIO",
                    },
                    {
                        "name": "Flee penalty",
                        "value": int(K.FLEE_PENALTY_TURNS),
                        "source": "src/tw2k/engine/constants.py FLEE_PENALTY_TURNS",
                    },
                ],
            },
            {
                "id": "haggle_bands",
                "title": "Haggle bands",
                "source": "docs/reference/tw2002/eis_tw2002_v3_docs/HardwareMenu.html; src/tw2k/engine/constants.py",
                "body": (
                    "A better deal is worth more experience. The +1 and +2 split is UNVERIFIED, "
                    "searched: HardwareMenu.html, S2, S7, and the Eugene Hung tips (those say 5 for an exact best price)."
                ),
                "rows": [
                    {"name": "Offer window", "value": _haggle_band(), "source": "src/tw2k/engine/constants.py haggle window"},
                    {"name": "Good haggle", "value": int(K.HAGGLE_EXP_GOOD), "source": "src/tw2k/engine/constants.py HAGGLE_EXP_GOOD"},
                    {"name": "Great haggle", "value": int(K.HAGGLE_EXP_GREAT), "source": "src/tw2k/engine/constants.py HAGGLE_EXP_GREAT"},
                    {"name": "Legacy cap", "value": int(K.PORT_HAGGLE_XP_CAP), "source": "src/tw2k/engine/constants.py PORT_HAGGLE_XP_CAP"},
                ],
            },
            {
                "id": "exp_alignment",
                "title": "Experience and alignment",
                "source": "docs/reference/tw2002/S2_cabal_formulas.html; src/tw2k/engine/constants.py xp_award()",
                "rows": _exp_rows(),
            },
        ],
    }
    out["stardock_class"] = stardock_class_label()
    rate, over, _min_align = K.tax_terms()
    out["tax"] = {"rate_pct": int(rate), "over": int(over)}
    if K.cockpit_fields_on():
        out["sections"].append(_not_in_original())
    return out


def _not_in_original() -> dict[str, Any]:
    """cockpit-gaps-v1 item 4. Listed as missing on purpose, with no hint."""
    return {
        "id": "not_in_original",
        "title": "Not shown in the original",
        "source": "live_twgs/REPORT2.md line 32; S3_tw2002_bible_v1.htm around lines 3150-3188",
        "body": (
            "How a port's stock moves its prices is not printed on any screen of the original game, "
            "so the cockpit does not print it either. Players learn it from play and keep their own notes."
        ),
    }
