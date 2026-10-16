"""Read-only rules, scoring, ship stats, and StarDock prices.

Every number is read from the engine table named on the row. Nothing here
is a second copy of a price.
"""

from __future__ import annotations

from typing import Any

from tw2k.engine import constants as K


def _ship_rows() -> list[dict[str, Any]]:
    rows = []
    for key, spec in K.ship_specs().items():
        rows.append({
            "id": key,
            "name": spec.get("display_name") or key,
            "cost": int(spec.get("cost") or 0),
            "holds": int(spec.get("holds") or 0),
            "max_fighters": int(spec.get("max_fighters") or 0),
            "max_shields": int(spec.get("max_shields") or 0),
            "turns_per_warp": int(spec.get("turns_per_warp") or 0),
            "source": "src/tw2k/engine/constants.py ship_specs()",
        })
    return rows


def _price(name: str, amount: int, source: str) -> dict[str, Any]:
    return {"name": name, "price": int(amount), "source": source}


def _prices() -> list[dict[str, Any]]:
    base = "src/tw2k/engine/constants.py"
    return [
        _price("Fuel ore, base", K.COMMODITY_BASE_PRICE["fuel_ore"], base + " COMMODITY_BASE_PRICE"),
        _price("Organics, base", K.COMMODITY_BASE_PRICE["organics"], base + " COMMODITY_BASE_PRICE"),
        _price("Equipment, base", K.COMMODITY_BASE_PRICE["equipment"], base + " COMMODITY_BASE_PRICE"),
        _price("Colonist", K.COLONIST_PRICE, base + " COLONIST_PRICE"),
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
        _price("Fighter, net-worth value", K.nw_fighter_value(), base + " nw_fighter_value()"),
        _price("Shield, net-worth value", K.nw_shield_value(), base + " nw_shield_value()"),
    ]


def game_reference() -> dict[str, Any]:
    fighter = int(K.nw_fighter_value())
    shield = int(K.nw_shield_value())
    hull = K.NW_HULL_FRACTION
    scoring = (
        f"Ship net worth is Player.net_worth in src/tw2k/engine/models.py. "
        f"A fighter counts as {fighter} cr (constants.py nw_fighter_value). "
        f"A shield counts as {shield} cr (nw_shield_value). "
        f"The hull counts as {hull} of ship_cost (NW_HULL_FRACTION). "
        f"Cargo counts at COMMODITY_BASE_PRICE. Colonists in the holds count at COLONIST_PRICE. "
        f"Other gear counts at the StarDock price in the prices section. "
        f"The bank balance is added when the bank is on and BANK_IN_NET_WORTH is true. "
        f"The number on V is victory.py full_net_worth: that ship total, plus each planet's "
        f"asset value, plus this seat's share of the corp treasury, plus parked ships."
    )
    rules = (
        "Play from the cockpit. V is day, turns, credits, bank, net worth, rank, experience, "
        "and alignment. I is this ship: holds in use, empty holds, and fighter and shield room. "
        "The sector line shows the port, each planet and its class, traders, ships, fighters, "
        "mines, a beacon, and the warps. A warp in parentheses is not on this map yet. "
        "The port table is the trade screen. Computer, then R, is the port report. "
        "Computer, then K, is the known universe. Computer, then O, is the avoid list. "
        "The numbers in the other sections are read from the engine tables named on each row."
    )
    return {
        "sections": [
            {"id": "rules", "title": "Rules", "source": "src/tw2k/server/reference.py", "body": rules},
            {
                "id": "scoring",
                "title": "Scoring and net worth",
                "source": "src/tw2k/engine/models.py Player.net_worth; src/tw2k/engine/victory.py full_net_worth",
                "body": scoring,
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
                "rows": _prices(),
            },
        ]
    }
