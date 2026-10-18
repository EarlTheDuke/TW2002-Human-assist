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
        _price("Photon missile", K.PHOTON_MISSILE_COST, base + " PHOTON_MISSILE_COST"),
        _price("Ether probe", K.ether_probe_cost(), base + " ether_probe_cost()"),
        _price("Genesis torpedo", K.genesis_torpedo_cost(), base + " genesis_torpedo_cost()"),
        _price("Cloaking device", K.CLOAK_COST, base + " CLOAK_COST"),
        _price("Mine disruptor", K.disruptor_cost(), base + " disruptor_cost()"),
        _price("Corbomite", K.CORBOMITE_COST, base + " CORBOMITE_COST"),
        _price("Marker beacon", K.BEACON_COST, base + " BEACON_COST"),
        _price("Psychic probe", K.psychic_probe_cost(), base + " psychic_probe_cost()"),
        _price("Atomic detonator", K.ATOMIC_DETONATOR_COST, base + " ATOMIC_DETONATOR_COST"),
        _price("Density scanner", K.DENSITY_SCANNER_COST, base + " DENSITY_SCANNER_COST"),
        _price("Holographic scanner", K.HOLO_SCANNER_COST, base + " HOLO_SCANNER_COST"),
        _price("Planet scanner", K.PLANET_SCANNER_COST, base + " PLANET_SCANNER_COST"),
    ]
    if K.ship_tw_on():
        rows.append(_price("TransWarp type 1", K.SHIP_TW_TYPE1_COST, base + " SHIP_TW_TYPE1_COST"))
        if K.tow_on():
            rows.append(_price("TransWarp type 2", K.SHIP_TW_TYPE2_COST, base + " SHIP_TW_TYPE2_COST"))
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


def game_reference(player=None, day: int = 1, max_days: int | None = None) -> dict[str, Any]:
    from tw2k.engine.victory import end_rule_line

    ship = getattr(player, "ship", None)
    ship_class = getattr(getattr(ship, "ship_class", None), "value", None) or "merchant_cruiser"
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
    out: dict[str, Any] = {
        "day": today,
        "ship_class": ship_class,
        "holds": holds,
        "sections": [
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
        ],
    }
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
