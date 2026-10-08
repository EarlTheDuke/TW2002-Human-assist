"""Game constants — prices, caps, costs. Tunable but defaults match classic TW2002."""

from __future__ import annotations

import math

# --- Commodities --------------------------------------------------------------

# "tw2002" is the Bible / economy2 scale. "legacy" is the table from ae1d5c4.
ECONOMY_SCALE_MODE = "tw2002"

_COMMODITY_BASE_LEGACY = {
    "fuel_ore": 18,
    "organics": 25,
    "equipment": 36,
}
# One base per commodity. Solved so the 100 percent, MCIC 50 / -50, experience 0
# spread matches economy2.html, with both ports at the chart's 100 percent:
# the selling port full, the buying port empty (economy2: a buying port with 0
# product is at 100 percent). The 179 / 389 / 719 table solved the same spread
# against a full buying port and put every quote about 7x over the chart.
# See ECONOMY_CALIBRATION.md.
_COMMODITY_BASE_TW2002 = {
    "fuel_ore": 26,
    "organics": 56,
    "equipment": 102,
}


class _ScalePrices(dict):
    """Reads the legacy or tw2002 base, whichever ECONOMY_SCALE_MODE names."""

    def _live(self) -> dict[str, int]:
        if ECONOMY_SCALE_MODE == "tw2002":
            return _COMMODITY_BASE_TW2002
        return _COMMODITY_BASE_LEGACY

    def __getitem__(self, key: str) -> int:
        return self._live()[key]

    def get(self, key: str, default: int | None = None) -> int | None:
        return self._live().get(key, default)

    def items(self):
        return self._live().items()

    def values(self):
        return self._live().values()

    def keys(self):
        return self._live().keys()

    def __iter__(self):
        return iter(self._live())

    def __contains__(self, key: object) -> bool:
        return key in self._live()

    def __len__(self) -> int:
        return len(self._live())


COMMODITY_BASE_PRICE = _ScalePrices(_COMMODITY_BASE_LEGACY)

# --- Port class matrix --------------------------------------------------------
# True = port BUYS from player, False = port SELLS to player, None = not traded.
# Order in each tuple: (fuel_ore, organics, equipment)
PORT_CLASS_TRADES: dict[int, tuple[bool | None, bool | None, bool | None]] = {
    0: (None, None, None),   # Federal — special / StarDock
    1: (True, False, False), # BSS
    2: (True, False, True),  # BSB
    3: (False, True, True),  # SBB
    4: (False, False, True), # SSB
    5: (False, True, False), # SBS
    6: (True, True, False),  # BBS
    7: (True, True, True),   # BBB
    8: (None, None, None),   # StarDock — services only
    9: (False, False, False),  # SSS — built ports only (port-upgrade-build-v1)
}

# Weights for random port class placement (class 0 and 8 placed explicitly)
PORT_CLASS_WEIGHTS = {
    1: 0.16,
    2: 0.16,
    3: 0.16,
    4: 0.16,
    5: 0.16,
    6: 0.16,
    7: 0.04,
}

PORT_SPAWN_PROBABILITY = 0.65
STARDOCK_SECTOR = 1
FEDSPACE_SECTORS = set(range(1, 11))

PORT_DEFAULT_MAX_STOCK = 3000
PORT_REGEN_PER_DAY = 0.05  # standard 5% per day. A sample game used 1%. See TURNS_REGEN.md.
# New ports open with this fraction of max stock. The changelog says 0%.
PORT_START_STOCK_PERCENT = 0
# First successful trade of a visit. A later trade in that sector costs 0.
PORT_DOCK_TURN_COST = 1

# Hidden port personality. docs/playtests/ports/PRICE_MODEL.md.
# MCIC is max change in cost, one number per commodity, -100..100.
# Positive sells that product. Negative buys it. 50 or -50 is called average.
# A player-made port sells at 50 and buys at -60. A missing value uses those.
PORT_MCIC_MIN = -100
PORT_MCIC_MAX = 100
PORT_MCIC_DEFAULT_SELL = 50
PORT_MCIC_DEFAULT_BUY = -60
# Planet-trade equipment chart: about 0.55% of the quote per MCIC point.
PORT_MCIC_POINT = 0.0055
# Buying gets cheaper and selling pays more until about 1000 experience.
PORT_PRICE_EXPERIENCE_CAP = 1000
PORT_EXPERIENCE_BUY_DISCOUNT = 0.226  # 11760 -> 9097 at a +50 sell port
PORT_EXPERIENCE_SELL_BONUS = 0.069  # 32405 -> 34646 at a -50 buy port
# MBBS productivity cap is 3276 (32,760 holds). Gold mode is 6553.
# Not used for regen in this slice.
PORT_PRODUCTIVITY_MAX = 3276
# A unit quote stays inside 1 .. base * this.
PORT_UNIT_PRICE_MAX_MULT = 4

# Hidden haggle room. docs/playtests/ports/HAGGLE.md.
# Worst port: 110% of the first offer. Best ore port: 149%.
# The percent rises with abs(MCIC), and abs(MCIC) stops at the span.
PORT_HAGGLE_MIN_PCT = 110
PORT_HAGGLE_MAX_PCT = 149
PORT_HAGGLE_MCIC_SPAN = 100
# A counter past the limit wastes one turn (haggling.html). A successful
# trade still costs TURN_COST["trade"].
PORT_HAGGLE_FAIL_TURNS = 1
# A good accepted counter earns experience. The library does not print the
# amount. One deal stops at this cap.
PORT_HAGGLE_XP_CAP = 10

# --- Ships --------------------------------------------------------------------

SHIP_SPECS: dict[str, dict] = {
    "merchant_cruiser": {
        "display_name": "Merchant Cruiser",
        "cost": 41300,
        "holds": 20,
        "max_fighters": 2500,
        "max_shields": 400,
        "turns_per_warp": 3,
        "base_hold_cost": 500,
    },
    "scout_marauder": {
        "display_name": "Scout Marauder",
        "cost": 75000,
        "holds": 25,
        "max_fighters": 250,
        "max_shields": 100,
        "turns_per_warp": 2,
        "base_hold_cost": 800,
    },
    "missile_frigate": {
        "display_name": "Missile Frigate",
        "cost": 100000,
        "holds": 40,
        "max_fighters": 5000,
        "max_shields": 400,
        "turns_per_warp": 3,
        "base_hold_cost": 1000,
    },
    "battleship": {
        "display_name": "BattleShip",
        "cost": 880000,
        "holds": 80,
        "max_fighters": 10000,
        "max_shields": 400,
        "turns_per_warp": 3,
        "base_hold_cost": 1500,
    },
    "corporate_flagship": {
        "display_name": "Corporate Flagship",
        "cost": 650000,
        "holds": 85,
        "max_fighters": 20000,
        "max_shields": 1500,
        "turns_per_warp": 3,
        "base_hold_cost": 1500,
        "corp_only": True,
    },
    "colonial_transport": {
        "display_name": "Colonial Transport",
        "cost": 63000,
        "holds": 50,
        "max_fighters": 200,
        "max_shields": 100,
        "turns_per_warp": 3,
        "base_hold_cost": 700,
    },
    "cargotran": {
        "display_name": "CargoTran",
        "cost": 43500,
        "holds": 75,
        "max_fighters": 400,
        "max_shields": 100,
        "turns_per_warp": 3,
        "base_hold_cost": 600,
    },
    "merchant_freighter": {
        "display_name": "Merchant Freighter",
        "cost": 350000,
        "holds": 65,
        "max_fighters": 2500,
        "max_shields": 750,
        "turns_per_warp": 3,
        "base_hold_cost": 1200,
    },
    "havoc_gunstar": {
        "display_name": "Havoc Gunstar",
        "cost": 445000,
        "holds": 65,
        "max_fighters": 10000,
        "max_shields": 3000,
        "turns_per_warp": 3,
        "base_hold_cost": 1300,
    },
    "imperial_starship": {
        "display_name": "Imperial StarShip",
        "cost": 4400000,
        "holds": 150,
        "max_fighters": 50000,
        "max_shields": 5000,
        "turns_per_warp": 3,
        "base_hold_cost": 2000,
        "min_alignment": 2000,
        "unique": True,
    },
}

STARTING_SHIP = "merchant_cruiser"
STARTING_CREDITS = 20_000
STARTING_FIGHTERS = 20
STARTING_HOLDS = 20
STARTING_TURNS_PER_DAY = 1000

# --- Operator directives ------------------------------------------------------

# Human steering text is injected into LLM observations, so cap it at the model
# boundary rather than letting UI/API callers grow prompt size without limit.
OPERATOR_DIRECTIVE_MAX_CHARS = 1200
OPERATOR_DIALOGUE_MESSAGE_MAX_CHARS = 600
OPERATOR_DIALOGUE_MAX_MESSAGES = 8

# --- Turn costs ---------------------------------------------------------------

TURN_COST = {
    "warp": 2,
    "trade": PORT_DOCK_TURN_COST,
    "attack": 5,
    "deploy_fighters": 1,
    "deploy_mines": 1,
    "land_planet": 3,
    "liftoff": 1,
    "scan": 1,
    "transmit": 0,
    "hyperwarp": 5,
    "wait": 1,
    # Match 13: claim an orphaned planet (was owned by an eliminated player,
    # owner_id currently None). Must already be landed on it — same
    # land-first gating as build_citadel. Cheap because the siege cost
    # (if any) was already paid at land-time combat.
    "claim_planet": 2,
    "deposit_planet_defense": 1,
    "withdraw_planet_defense": 1,
    "set_military_reaction": 1,
    "deposit_treasury": 1,
    "withdraw_treasury": 1,
    "set_quasar_sector": 1,
    "set_quasar_atm": 1,
    "planet_transwarp": 1,
    "planet_buy_transporter": 0,
    "planet_transport": 1,
    "planet_destroy": 1,
    "recall_deployed": 1,
    "surrender": 1,
    "pay_toll": 0,
    "rob": PORT_DOCK_TURN_COST,
    "steal": PORT_DOCK_TURN_COST,
    "ship_transport": 1,  # fl14: flat, whatever the hops or the hull's turns per warp
    "tow_engage": 0,  # SHIP_TOW.md tt5 UNVERIFIED: no source charges for <W>
    "tow_release": 0,
}

# --- Combat / fighters / mines ------------------------------------------------

FIGHTER_COST = 50  # legacy flat price, and the no-day net-worth value

# Bible_TWGS_edit_2007_Clme.htm ship-cost column. Every ship we have is on it.
SHIP_COST_TW2002 = {
    "merchant_cruiser": 41_300,
    "scout_marauder": 15_950,
    "missile_frigate": 100_800,
    "battleship": 88_500,
    "corporate_flagship": 163_500,
    "colonial_transport": 63_600,
    "cargotran": 51_950,
    "merchant_freighter": 33_400,
    "havoc_gunstar": 79_000,
    "imperial_starship": 339_000,
    "star_master": 61_300,
    "constellation": 72_500,
    "tkhasi_orion": 42_500,
    "tholian_sentinel": 47_500,
    "taurean_mule": 63_600,
    "interdictor_cruiser": 539_000,
}


# The escape pod (death-escape-pods-v1, docs/playtests/combat/DEATH_ESCAPE_PODS.md d2).
# Bible chart caps and odds. `holds` is what a fresh pod carries (MBBS figure). Not in any
# roster dict, so the yard never sells it; hull_spec() finds it.
ESCAPE_POD = "escape_pod"
POD_SPEC: dict = {
    "display_name": "Escape Pod",
    "cost": 0,
    "holds": 5,
    "max_holds": 50,
    "max_fighters": 50,
    "max_shields": 50,
    "max_mines": 0,
    "max_genesis": 0,
    "max_photons": 0,
    "turns_per_warp": 6,
    "fighters_per_attack": 10,
    "offensive_odds": 0.6,
    "base_hold_cost": 500,
}


# Bible chart caps. `holds` is what buy_ship grants. `max_holds` is the yard cap.
# offensive_odds and fighters_per_attack drive tw2002 combat (combat_hull below).
# See docs/playtests/ships/SHIP_ROSTER.md.
SHIP_SPECS_TW2002: dict[str, dict] = {
    "merchant_cruiser": {
        "display_name": "Merchant Cruiser",
        "cost": 41_300,
        "holds": 20,
        "max_holds": 75,
        "max_fighters": 2500,
        "max_shields": 400,
        "max_mines": 50,
        "max_genesis": 5,
        "max_photons": 0,
        "turns_per_warp": 3,
        "fighters_per_attack": 750,
        "offensive_odds": 1.0,
        "base_hold_cost": 500,
    },
    "scout_marauder": {
        "display_name": "Scout Marauder",
        "cost": 15_950,
        "holds": 25,
        "max_holds": 25,
        "max_fighters": 150,
        "max_shields": 100,
        "max_mines": 0,
        "max_genesis": 0,
        "max_photons": 0,
        "turns_per_warp": 2,
        "fighters_per_attack": 250,
        "offensive_odds": 2.0,
        "base_hold_cost": 800,
    },
    "missile_frigate": {
        "display_name": "Missile Frigate",
        "cost": 100_800,
        "holds": 40,
        "max_holds": 60,
        "max_fighters": 5000,
        "max_shields": 400,
        "max_mines": 5,
        "max_genesis": 0,
        "max_photons": 10,
        "turns_per_warp": 3,
        "fighters_per_attack": 3000,
        "offensive_odds": 1.3,
        "base_hold_cost": 1000,
    },
    "battleship": {
        "display_name": "BattleShip",
        "cost": 88_500,
        "holds": 80,
        "max_holds": 80,
        "max_fighters": 10000,
        "max_shields": 750,
        "max_mines": 25,
        "max_genesis": 1,
        "max_photons": 0,
        "turns_per_warp": 4,
        "fighters_per_attack": 3000,
        "offensive_odds": 1.6,
        "base_hold_cost": 1500,
    },
    "corporate_flagship": {
        "display_name": "Corporate Flagship",
        "cost": 163_500,
        "holds": 85,
        "max_holds": 85,
        "max_fighters": 20000,
        "max_shields": 1500,
        "max_mines": 100,
        "max_genesis": 10,
        "max_photons": 0,
        "turns_per_warp": 3,
        "fighters_per_attack": 6000,
        "offensive_odds": 1.2,
        "base_hold_cost": 1500,
        "corp_only": True,
    },
    "colonial_transport": {
        "display_name": "Colonial Transport",
        "cost": 63_600,
        "holds": 50,
        "max_holds": 250,
        "max_fighters": 200,
        "max_shields": 500,
        "max_mines": 0,
        "max_genesis": 5,
        "max_photons": 0,
        "turns_per_warp": 6,
        "fighters_per_attack": 100,
        "offensive_odds": 0.6,
        "base_hold_cost": 700,
    },
    "cargotran": {
        "display_name": "CargoTran",
        "cost": 51_950,
        "holds": 75,
        "max_holds": 125,
        "max_fighters": 400,
        "max_shields": 1000,
        "max_mines": 1,
        "max_genesis": 2,
        "max_photons": 0,
        "turns_per_warp": 4,
        "fighters_per_attack": 125,
        "offensive_odds": 0.8,
        "base_hold_cost": 600,
    },
    "merchant_freighter": {
        "display_name": "Merchant Freighter",
        "cost": 33_400,
        "holds": 65,
        "max_holds": 65,
        "max_fighters": 300,
        "max_shields": 500,
        "max_mines": 2,
        "max_genesis": 2,
        "max_photons": 0,
        "turns_per_warp": 2,
        "fighters_per_attack": 100,
        "offensive_odds": 0.8,
        "base_hold_cost": 1200,
    },
    "havoc_gunstar": {
        "display_name": "Havoc Gunstar",
        "cost": 79_000,
        "holds": 50,
        "max_holds": 50,
        "max_fighters": 10000,
        "max_shields": 3000,
        "max_mines": 5,
        "max_genesis": 1,
        "max_photons": 0,
        "turns_per_warp": 3,
        "fighters_per_attack": 1000,
        "offensive_odds": 1.2,
        "base_hold_cost": 1300,
    },
    "imperial_starship": {
        "display_name": "Imperial StarShip",
        "cost": 339_000,
        "holds": 150,
        "max_holds": 150,
        "max_fighters": 50000,
        "max_shields": 2000,
        "max_mines": 125,
        "max_genesis": 10,
        "max_photons": 5,
        "turns_per_warp": 4,
        "fighters_per_attack": 10000,
        "offensive_odds": 1.5,
        "base_hold_cost": 2000,
        "min_alignment": 2000,
        "unique": True,
    },
    "star_master": {
        "display_name": "Star Master",
        "cost": 61_300,
        "holds": 30,
        "max_holds": 73,
        "max_fighters": 5000,
        "max_shields": 2000,
        "max_mines": 50,
        "max_genesis": 5,
        "max_photons": 0,
        "turns_per_warp": 3,
        "fighters_per_attack": 1000,
        "offensive_odds": 1.4,
        "base_hold_cost": 500,
    },
    "constellation": {
        "display_name": "Constellation",
        "cost": 72_500,
        "holds": 20,
        "max_holds": 80,
        "max_fighters": 5000,
        "max_shields": 750,
        "max_mines": 25,
        "max_genesis": 2,
        "max_photons": 0,
        "turns_per_warp": 3,
        "fighters_per_attack": 2000,
        "offensive_odds": 1.4,
        "base_hold_cost": 500,
    },
    "tkhasi_orion": {
        "display_name": "T'Khasi Orion",
        "cost": 42_500,
        "holds": 30,
        "max_holds": 60,
        "max_fighters": 750,
        "max_shields": 750,
        "max_mines": 5,
        "max_genesis": 1,
        "max_photons": 0,
        "turns_per_warp": 2,
        "fighters_per_attack": 250,
        "offensive_odds": 1.1,
        "base_hold_cost": 500,
    },
    "tholian_sentinel": {
        "display_name": "Tholian Sentinel",
        "cost": 47_500,
        "holds": 10,
        "max_holds": 50,
        "max_fighters": 2500,
        "max_shields": 4000,
        "max_mines": 50,
        "max_genesis": 1,
        "max_photons": 0,
        "turns_per_warp": 4,
        "fighters_per_attack": 800,
        "offensive_odds": 1.0,
        "base_hold_cost": 500,
    },
    "taurean_mule": {
        "display_name": "Taurean Mule",
        "cost": 63_600,
        "holds": 40,
        "max_holds": 150,
        "max_fighters": 300,
        "max_shields": 600,
        "max_mines": 0,
        "max_genesis": 1,
        "max_photons": 0,
        "turns_per_warp": 4,
        "fighters_per_attack": 150,
        "offensive_odds": 0.5,
        "base_hold_cost": 500,
    },
    "interdictor_cruiser": {
        "display_name": "Interdictor Cruiser",
        "cost": 539_000,
        "holds": 20,
        "max_holds": 40,
        "max_fighters": 100000,
        "max_shields": 4000,
        "max_mines": 200,
        "max_genesis": 20,
        "max_photons": 0,
        "turns_per_warp": 15,
        "fighters_per_attack": 15000,
        "offensive_odds": 1.2,
        "base_hold_cost": 500,
    },
}


def ship_specs() -> dict[str, dict]:
    """The hull table the yard, the legal list, and warp cost read.

    Legacy mode is the old ten-ship dict. Combat odds stay on that dict too.
    """
    if ECONOMY_SCALE_MODE == "tw2002":
        return SHIP_SPECS_TW2002
    return SHIP_SPECS


def hull_spec(class_key: str) -> dict | None:
    """The spec of a hull a ship can be flying: the roster, or the escape pod (never for sale)."""
    if class_key == ESCAPE_POD:
        return POD_SPEC
    return ship_specs().get(class_key)


def ship_cost(class_key: str) -> int:
    """What StarDock charges for this hull, before trade-in."""
    if class_key == ESCAPE_POD:
        return 0
    if ECONOMY_SCALE_MODE == "tw2002":
        return int(SHIP_COST_TW2002[class_key])
    return int(SHIP_SPECS[class_key]["cost"])


def trade_in_credit(class_key: str) -> int:
    """25 percent of the hull price. The yard applies this to the next hull.

    An escape pod is worth a Scout (DEATH_ESCAPE_PODS.md d17): it trades for a Scout outright
    (net_hull_cost), and toward any other hull it counts as a Scout's trade-in. Worth more, a
    lost ship would beat trading the live one in, and surrendering would mint credits.
    """
    if class_key == ESCAPE_POD:
        return int(ship_cost("scout_marauder") * 0.25)
    return int(ship_cost(class_key) * 0.25)


def net_hull_cost(old_key: str, new_key: str) -> int:
    """Credits a trade-in actually moves. A surplus is not paid out."""
    if old_key == ESCAPE_POD and new_key == "scout_marauder":
        return 0  # d17: the pod buys a Scout outright
    net = ship_cost(new_key) - trade_in_credit(old_key)
    if net < 0:
        return 0
    return net


_EQUIP_CAP_FIELD = {
    "fighters": "max_fighters",
    "shields": "max_shields",
    "holds": "max_holds",
    "genesis": "max_genesis",
    "photon_missiles": "max_photons",
    "armid_mines": "max_mines",
    "limpet_mines": "max_mines",
    "atomic_mines": "max_mines",
}


def equip_room(class_key: str, item: str, have: int) -> int | None:
    """How many more of `item` this hull can take.

    `have` for a mine type is the total of every mine type already aboard.
    None means this roster does not cap that item (legacy mines, genesis, photons).
    Holds with no per-ship max still stop at 150.
    Cloaks / disruptors use HARDWARE_MODE global caps when tw2002.
    """
    if item == "cloak":
        if not hardware_tw2002():
            return 0
        return max(0, int(CLOAK_MAX) - int(have))
    if item == "mine_disruptor":
        if not hardware_tw2002():
            return 0
        return max(0, int(DISRUPTOR_MAX) - int(have))
    if item == "transwarp_drive":
        if not ship_tw_on():
            return 0
        return 0 if int(have) else 1
    if item in HARDWARE_V2_ITEMS:
        if not hardware_tw2002():
            return 0
        return max(0, hardware_v2_cap(class_key, item) - int(have))
    spec = hull_spec(class_key) or {}
    field = _EQUIP_CAP_FIELD.get(item)
    if field is None:
        return None
    if field not in spec:
        if item == "holds":
            return max(0, 150 - int(have))
        return None
    return max(0, int(spec[field]) - int(have))


HARDWARE_V2_ITEMS = ("corbomite", "marker_beacon", "psychic_probe", "atomic_detonator")


def hardware_v2_cap(class_key: str, item: str) -> int:
    """Per-ship cap of a ship-hardware-v2 item (SHIP_HARDWARE_V2.md)."""
    if item == "corbomite":
        return 0 if class_key == ESCAPE_POD else int(CORBOMITE_MAX)
    if item == "marker_beacon":
        return int(BEACON_MAX_BY_HULL.get(class_key, 0))
    if item == "psychic_probe":
        return 0 if class_key == ESCAPE_POD else int(PSYCHIC_PROBE_MAX)
    if item == "atomic_detonator":
        return 0 if class_key == ESCAPE_POD else int(ATOMIC_DETONATOR_MAX)
    return 0


def hardware_v2_prices() -> dict[str, int]:
    """Hardware Emporium prices for the v2 items; empty under HARDWARE_MODE legacy."""
    if not hardware_tw2002():
        return {}
    return {
        "corbomite": int(CORBOMITE_COST),
        "marker_beacon": int(BEACON_COST),
        "psychic_probe": int(PSYCHIC_PROBE_COST),
        "atomic_detonator": int(ATOMIC_DETONATOR_COST),
    }


def atomic_mines_sold() -> bool:
    """v19: legacy always sells atomic_mines; tw2002 only while ATOMIC_MINES_PORT_NUKE is kept."""
    return (not hardware_tw2002()) or bool(ATOMIC_MINES_PORT_NUKE)


def fighter_unit_price(day: int) -> int:
    """Credits for one fighter on this game day.

    Legacy is the flat 50. The tw2002 wave is the Hekate note:
    (160 + 40) + sin(day / 87 * 2 * pi) * 40, clamped to 160..239.
    """
    if ECONOMY_SCALE_MODE != "tw2002":
        return FIGHTER_COST
    raw = (160 + 40) + math.sin(int(day) / 87 * 2 * math.pi) * 40
    price = round(raw)
    if price < 160:
        return 160
    if price > 239:
        return 239
    return price


def hold_day_base(day: int) -> int:
    """Daily B in the hold formula. 151, up to 249 on day 9, back over 18 days."""
    span = 249 - 151
    pos = int(day) % 18
    if pos <= 9:
        return 151 + round(span * pos / 9)
    return 151 + round(span * (18 - pos) / 9)


def hold_next_price(class_key: str, holds_already: int, day: int) -> int:
    """Credits for the next single hold."""
    if ECONOMY_SCALE_MODE != "tw2002":
        return int((SHIP_SPECS.get(class_key) or POD_SPEC)["base_hold_cost"])
    return hold_day_base(day) + 20 * int(holds_already)


def hold_total_price(class_key: str, holds_already: int, qty: int, day: int) -> int:
    """Credits to buy `qty` holds starting from `holds_already`."""
    if ECONOMY_SCALE_MODE != "tw2002":
        return int((SHIP_SPECS.get(class_key) or POD_SPEC)["base_hold_cost"]) * int(qty)
    base = hold_day_base(day)
    held = int(holds_already)
    count = int(qty)
    return count * base + 20 * (count * held + count * (count - 1) // 2)


def holds_affordable(
    class_key: str, holds_already: int, credits: int, day: int, cap: int
) -> int:
    """Largest hold qty whose formula total fits in credits, and under cap."""
    best = 0
    limit = max(0, int(cap))
    for qty in range(1, limit + 1):
        if hold_total_price(class_key, holds_already, qty, day) > int(credits):
            break
        best = qty
    return best


ARMID_MINE_COST = 100
LIMPET_MINE_COST = 250
ATOMIC_MINE_COST = 4_000
PHOTON_MISSILE_COST = 12_000
ETHER_PROBE_COST = 5_000
GENESIS_TORPEDO_COST = 25000
ARMID_DAMAGE = 100
MINE_MAX_HITS_PER_MOVE = 10
ATOMIC_PORT_DAMAGE = 0.6      # fraction of port stock destroyed by atomic det.
ATOMIC_PLANET_DAMAGE = 0.5    # fraction of planet citadel/treasury wiped
# First planet_destroy zeroes colonist pools. The next one, with none left, removes the planet.
PLANET_DESTROY_COLONISTS_TO_ZERO = True
# Same hit as one atomic warhead, once per successful planet_destroy.
PLANET_DESTROY_ALIGNMENT = 50
PHOTON_DURATION_TICKS = 1     # one full tick of fighter-disable on hit

# --- Long-range navigation / scan tiers ---------------------------------------

PLOT_COURSE_MAX_DEPTH = 10           # max BFS depth for autopilot
SCAN_TIER_BASIC = "basic"
SCAN_TIER_DENSITY = "density"        # 2-hop, no port intel
SCAN_TIER_HOLO = "holo"              # 1-hop, full port intel + occupants
SCAN_TIER_ETHER = "ether"            # remote single-sector probe (consumes probe)

# --- Planets ------------------------------------------------------------------

CITADEL_LEVELS = 6
# (credit_cost, colonist_cost, days_to_build) per level (1..6)
CITADEL_TIER_COST: list[tuple[int, int, int]] = [
    (5_000,    1_000,  1),
    (10_000,   2_000,  1),
    (20_000,   4_000,  2),
    (40_000,   8_000,  2),
    (80_000,  16_000,  3),
    (160_000, 32_000,  4),
]
# "credits" is the live rule. "class" charges the commodity table below.
# Nothing reads an env var or an action to flip this.
CITADEL_COST_MODE = "credits"
# Original citadel days times this scale, dropped to a whole number, never below 1.
CITADEL_BUILD_TIME_SCALE = 0.25
# (colonists, fuel_ore, organics, equipment, raw_days) for levels 1..6.
# Raw days are the original counts, before CITADEL_BUILD_TIME_SCALE.
CITADEL_CLASS_COSTS: dict[str, tuple[tuple[int, int, int, int, int], ...]] = {
    "M": (
        (1000, 300, 200, 250, 4),
        (2000, 200, 50, 250, 4),
        (4000, 500, 250, 500, 5),
        (6000, 1000, 1200, 1000, 10),
        (6000, 300, 400, 1000, 5),
        (6000, 1000, 1200, 2000, 15),
    ),
    "K": (
        (1000, 400, 300, 600, 6),
        (2400, 300, 80, 400, 5),
        (4400, 600, 400, 650, 8),
        (7000, 700, 900, 800, 5),
        (8000, 800, 400, 1000, 4),
        (7000, 700, 900, 1600, 8),
    ),
    "O": (
        (1400, 500, 200, 400, 6),
        (2400, 200, 50, 300, 5),
        (4400, 600, 400, 650, 8),
        (7000, 700, 900, 800, 5),
        (8000, 300, 400, 1000, 4),
        (7000, 700, 900, 1600, 8),
    ),
    "L": (
        (400, 150, 100, 150, 2),
        (1400, 200, 50, 250, 5),
        (3600, 600, 250, 700, 5),
        (5600, 1000, 1200, 1000, 8),
        (7000, 300, 400, 1000, 5),
        (5600, 1000, 1200, 2000, 12),
    ),
    "C": (
        (1000, 400, 300, 600, 5),
        (2400, 300, 80, 400, 5),
        (4400, 600, 400, 650, 7),
        (6600, 700, 900, 700, 5),
        (9000, 300, 400, 1000, 4),
        (6600, 700, 900, 1400, 8),
    ),
    "H": (
        (800, 500, 300, 600, 4),
        (1600, 300, 100, 400, 5),
        (4400, 1200, 400, 1500, 8),
        (7000, 2000, 2000, 2500, 12),
        (10000, 3000, 1200, 2000, 5),
        (7000, 2000, 2000, 5000, 18),
    ),
    "U": (
        (3000, 1200, 400, 2500, 8),
        (3000, 300, 100, 400, 4),
        (5000, 500, 500, 2000, 5),
        (6000, 500, 200, 600, 5),
        (8000, 200, 200, 600, 4),
        (6000, 500, 200, 1200, 8),
    ),
}
# Free fighters and shields granted per new citadel level, at L2 and up.
# 0 adds nothing: no gift text, no zero-count event facts, no planet change.
# Raise both to restore the old floor (1000 fighters and 250 shields).
CITADEL_GIFT_FIGHTERS_PER_LEVEL = 0
CITADEL_GIFT_SHIELDS_PER_LEVEL = 0
# Sector quasar, atmospheric quasar, and both setters require this citadel level.
QUASAR_MIN_LEVEL = 3
# Atmospheric damage is burned fuel times this factor. Burned fuel is fuel * pct // 100.
QUASAR_ATM_FACTOR = 2
# Citadel L5 with at least this many shields ignores a photon damp.
QUASAR_PHOTON_SHIELD_MIN = 200
# Citadel L6 holds a hostile warp and burns this much fuel, then the sector cannon fires.
INTERDICTOR_MIN_LEVEL = 6
INTERDICTOR_FUEL = 500
# Planet TransWarp. Fuel is this much times the warp-path length.
PLANET_TRANSWARP_MIN_LEVEL = 4
PLANET_TRANSWARP_FUEL_PER_SECTOR = 400
# Planet Transporter. Credits are the player's. Fuel is the planet's.
PLANET_TRANSPORTER_COST_FIRST = 50_000
PLANET_TRANSPORTER_COST_EXTRA = 25_000
PLANET_TRANSPORTER_FUEL_PER_SECTOR = 10
# (level, name, one-line perk). Original order. The perk line says
# whether this game does that thing today. The completion gift is
# CITADEL_GIFT_FIGHTERS_PER_LEVEL and CITADEL_GIFT_SHIELDS_PER_LEVEL.
CITADEL_PERK: list[tuple[int, str, str]] = [
    (1, "Treasury", "Treasury: deposit and withdraw credits while landed, plus 2% daily interest"),
     (2, "Combat Control Computer",
     "Combat Control Computer (not yet in this game)."),
    (3, "Quasar cannon",
     "Quasar cannon: on a hostile warp into the sector, burn the set percent of fuel stockpile and damage the ship. On a hostile landing, burn the atmosphere percent before shields and again after shields fall. A photon damps these cannons for that ship's one approach unless the planet is citadel L5 with 200 shields."),
    (4, "Planet TransWarp",
     "Planet TransWarp: once a day, move the planet along the warp lanes for 400 fuel per sector, to a sector that already has a fighter of the owner."),
    (5, "Planetary shields",
     "Planetary shields (not yet in this game). A citadel L5 with 200 shields ignores a photon damp."),
    (6, "Interdictor",
     "Interdictor: a hostile warp out fails when fuel is at least 500, the planet burns 500 fuel, and the sector cannon fires on what remains."),
]
def citadel_build_days(raw_days: int) -> int:
    """Original days times CITADEL_BUILD_TIME_SCALE, never below 1."""
    return max(1, int(raw_days * CITADEL_BUILD_TIME_SCALE))


def citadel_class_cost(class_id: str, level: int) -> tuple[int, int, int, int, int]:
    """Colonists, fuel ore, organics, equipment, and scaled days for one level."""
    colonists, fuel, organics, equipment, raw_days = CITADEL_CLASS_COSTS[class_id][level - 1]
    return colonists, fuel, organics, equipment, citadel_build_days(raw_days)


GENESIS_DEPLOY_TURN_COST = 4
# Fighters move 1:1 onto a planet, up to this cap. Shields move
# PLANET_SHIELD_SHIP_COST ship shields per 1 planet shield, both ways.
# MIN_LEVEL 0: any planet can hold fighters. A later slice can raise it.
# Same ceiling as the original per-planet max of 1,000,000. Daily production stops here.
PLANET_FIGHTER_CAP = 1_000_000
# Colonists in a product pool to make 1 fighter. 0 means that pool makes none.
# Fuel, organics, equipment. The idle colonists pool is not in this table.
# M 30/70/130, K 30/1500/7500, O 300/30/1500, L 24/60/240,
# C 1250/2500/12500, H 50/0/25000, U 0/0/0.
PLANET_FIGHTER_COLONISTS_PER: dict[str, dict[str, int]] = {
    "M": {"fuel_ore": 30, "organics": 70, "equipment": 130},
    "K": {"fuel_ore": 30, "organics": 1500, "equipment": 7500},
    "O": {"fuel_ore": 300, "organics": 30, "equipment": 1500},
    "L": {"fuel_ore": 24, "organics": 60, "equipment": 240},
    "C": {"fuel_ore": 1250, "organics": 2500, "equipment": 12500},
    "H": {"fuel_ore": 50, "organics": 0, "equipment": 25000},
    "U": {"fuel_ore": 0, "organics": 0, "equipment": 0},
}
# 100 keeps the original daily count. Lower it to slow fighter growth in a short match.
PLANET_FIGHTER_RATE_PCT = 100
PLANET_SHIELD_SHIP_COST = 10
PLANET_DEFENSE_MIN_LEVEL = 0
# Daily interest is this percent of planet.treasury, integer division, at citadel level >= 1.
PLANET_TREASURY_INTEREST_PCT = 2
# Cap so 2% daily interest cannot grow a planet bank toward the 100,000,000 credit victory by itself.
# Ten million is a stockpile the owner can withdraw, not a second win.
PLANET_TREASURY_CAP = 10_000_000
# One planet shield absorbs 20 points of attacker damage, so the attacker needs 20 fighters per planet shield.
PLANET_SHIELD_ODDS = 20
# Planet fighter odds. The 3-round dice path is retired. Ship-vs-ship dice stay.
# Offense: each reaction fighter destroys this many attacker fighters.
# Defense: this many attacker fighters destroy one planet fighter.
PLANET_OFFENSE_ODDS = 2
PLANET_DEFENSE_ODDS = 3
# Offensive wave size is int(1.25 * (fighter cap + shield cap)) of the attacker
# ship class. Reaction fighters above one wave wait for the next wave.
PLANET_OFFENSE_WAVE_NUM = 5
PLANET_OFFENSE_WAVE_DEN = 4
# After one shield soak (attacker fighters // PLANET_SHIELD_ODDS), shields still
# above 0 repel the landing and planet fighters do not shoot. Ship shields are
# not spent. If attacker fighters are 0 after the odds, the existing destroy
# path runs and the planet is not captured, even when planet fighters also hit
# 0. If both sides still have fighters, those survivors stay and the landing
# is repelled.
# Minimum hops from sector 1 (StarDock) for legal Genesis deployment.
# Classic TW2002 required planets to be "deep" — you couldn't drop one in
# the Federation's back yard. FedSpace only covers 1..10, but many of those
# sectors have >10-hop reachability paths and some outer sectors are
# 1-hop from StarDock; a hops-based rule guarantees real distance.
GENESIS_MIN_HOPS_FROM_STARDOCK = 3
# Founding population Genesis torpedoes bring to life. Tuned so Citadel L1
# (1,000 colonists) is immediately buildable and natural growth can start.
GENESIS_SEED_COLONISTS = 2_500
# "tw2002" caps colonists and stock by class and stops a sixth planet in a
# sector. "legacy" keeps the old uncapped growth and no sector limit.
# The stock unit price does not follow this switch. It follows
# ECONOMY_SCALE_MODE, because that price was already the live base.
PLANET_ECONOMY_MODE = "tw2002"
PLANETS_PER_SECTOR_CAP = 5
# S1_planet_handbook_v1.01.html. Maximum Colonists is the same on every
# product row of a class, so it is the population cap. Max on Planet is the
# stock cap for that good. Fighter rows are not applied here.
PLANET_MAX_COLONISTS = {
    "M": 30_000,
    "K": 40_000,
    "L": 40_000,
    "O": 200_000,
    "C": 100_000,
    "H": 100_000,
    "U": 3_000,
}
PLANET_MAX_STOCK = {
    "M": {"fuel_ore": 100_000, "organics": 100_000, "equipment": 100_000},
    "K": {"fuel_ore": 200_000, "organics": 50_000, "equipment": 10_000},
    "L": {"fuel_ore": 200_000, "organics": 200_000, "equipment": 200_000},
    "O": {"fuel_ore": 100_000, "organics": 1_000_000, "equipment": 50_000},
    "C": {"fuel_ore": 20_000, "organics": 50_000, "equipment": 10_000},
    "H": {"fuel_ore": 1_000_000, "organics": 10_000, "equipment": 100_000},
    "U": {"fuel_ore": 10_000, "organics": 10_000, "equipment": 10_000},
}


def planet_limits_on() -> bool:
    return PLANET_ECONOMY_MODE == "tw2002"


# "tw2002" is the sector-fighter slice: recall, the v1.03d caps, a 5-credit
# toll that sits on the fighters, and surrender. "legacy" is the old path.
# Iago_War_Manual.txt for the v1.03d caps. v3 numbers were not found.
# formulas.html and Iago for the 5-credit toll.
SECTOR_FIGHTER_MODE = "tw2002"
SECTOR_FIGHTER_CAP = 5000
SECTOR_FIGHTER_CAP_WITH_PLANET = 30000
SECTOR_MINE_CAP = 99
SECTOR_TOLL_CREDITS_PER_FIGHTER = 5


def sector_fighter_tw2002() -> bool:
    return SECTOR_FIGHTER_MODE == "tw2002"


# Ship combat. docs/playtests/combat/SHIP_COMBAT.md.
# "tw2002": attack takes a fighter count capped by the hull, odds multiply,
# shields absorb first, the defender may flee at 1.25, and hostile defensive or
# toll fighters challenge an entering ship (attack, retreat, pay, surrender).
# "legacy": the old three-round dice and the old entry path.
COMBAT_MODE = "tw2002"
COMBAT_FLEE_RATIO = 1.25  # cabal fleeing.html: attacker fighters > (F + S) * 1.25
SECTOR_FIGHTER_ODDS = 1.0  # formulas.html odds table: tolled and defensive 1:1
FERRENGI_COMBAT_ODDS = 1.0  # TWFAQ_FERRSPEC: 1.0 for the smallest Ferrengi hull
FLEE_PENALTY_TURNS = 1  # classictw Glossary: one turn, next land or port only
COMBAT_NEVER_FLEE_HULLS = ("tholian_sentinel",)  # guardian ships never flee
COMBAT_INTERDICT_HULLS = ("interdictor_cruiser",)  # an active generator stops a flee


def combat_tw2002() -> bool:
    return COMBAT_MODE == "tw2002"


def challenge_on() -> bool:
    """Defensive and toll fighters challenge an entering ship."""
    return COMBAT_MODE == "tw2002" and SECTOR_FIGHTER_MODE == "tw2002"


def combat_hull(class_key: str) -> tuple[float, int]:
    """(offensive odds, fighters per attack) from the Bible chart, any economy mode."""
    spec = SHIP_SPECS_TW2002.get(class_key)
    if class_key == ESCAPE_POD:
        spec = POD_SPEC
    if spec is None:
        legacy = SHIP_SPECS.get(class_key) or {}
        return 1.0, int(legacy.get("max_fighters") or 10**9)
    return float(spec.get("offensive_odds", 1.0)), int(spec.get("fighters_per_attack") or 10**9)


def sector_fighter_cap(has_planet: bool) -> int:
    if has_planet:
        return SECTOR_FIGHTER_CAP_WITH_PLANET
    return SECTOR_FIGHTER_CAP


def sector_has_planet_room(count: int) -> bool:
    if not planet_limits_on():
        return True
    return int(count) < PLANETS_PER_SECTOR_CAP


def planet_colonist_room(class_id: str, current: int) -> int | None:
    """How many more colonists fit. None means the legacy path has no cap."""
    if not planet_limits_on():
        return None
    return max(0, PLANET_MAX_COLONISTS[class_id] - int(current))


def planet_stock_room(class_id: str, commodity: str, current: int) -> int | None:
    """How many more units of one good fit. None means the legacy path has no cap."""
    if not planet_limits_on():
        return None
    return max(0, PLANET_MAX_STOCK[class_id][commodity] - int(current))


# Price per colonist when buying from Terra/StarDock (classic TW2002: ~10 cr).
# Cheap enough that you can fully load a 20-hold merchant cruiser for 200 cr,
# but the REAL cost is the turns spent ferrying them to a distant planet.
COLONIST_PRICE = 10
PLANET_VALUE_TAX_RATE = 0.30
PLANET_VALUE_TAX_MIN_PAYOUT = 1
PLANET_CLASS_WEIGHTS = {
    "M": 0.32, "K": 0.14, "L": 0.14, "O": 0.14,
    "H": 0.10, "U": 0.10, "C": 0.06,
}

# --- Player elimination -------------------------------------------------------
MAX_DEATHS_BEFORE_ELIM = 3

# --- Death and escape pods (death-escape-pods-v1) ---------------------------------
# docs/playtests/combat/DEATH_ESCAPE_PODS.md. "legacy" is the old death: StarDock, a fresh
# Merchant Cruiser, credits x0.75, elimination at MAX_DEATHS_BEFORE_ELIM.
DEATH_MODE = "tw2002"
PODLESS_HULLS = ("scout_marauder", "escape_pod")  # d3: these go straight to Ship Destroyed
PODS_PER_DAY = 2  # d10: the third loss in one day is Ship Destroyed
POD_EXP_LOSS = 0.10  # d8: podded
SD_EXP_LOSS = 0.50  # d9: Ship Destroyed
SD_ALIGN_LOSS = 0.50  # d9
SD_RESTART_HULL = "scout_marauder"  # d11: the free ship after Ship Destroyed
POD_PATH_MIN_HOPS = 3  # d4: safe-path targets, pods.html "3-20"
POD_PATH_MAX_HOPS = 20
POD_PATH_TRIES = 5  # d4: "a bunch" of random targets. UNVERIFIED count.


def death_tw2002() -> bool:
    return DEATH_MODE == "tw2002"


# --- Scanners and hidden information (SCANNERS_HIDDEN_INFO.md) -----------------
# "tw2002": bought density / holo scanners, fogged adjacent sectors, path probes,
# live port reports. "legacy": today's free scan tiers and full adjacent view.
INFO_MODE = "tw2002"
DENSITY_SCANNER_COST = 2_000  # s1: Iago's StarDock list (TWGS dump says 500)
HOLO_SCANNER_COST = 25_000  # s2: Iago (TWGS dump says 6,250)
SCANNER_DENSITY = "density"
SCANNER_HOLO = "holo"
# s3: OldBBS_TW2002V8.faq.txt "S" column, MBBS manual and Gypsy for the restricted hulls.
SCANNER_BY_HULL: dict[str, str | None] = {
    "merchant_cruiser": SCANNER_HOLO,
    "scout_marauder": SCANNER_DENSITY,
    "missile_frigate": None,
    "battleship": SCANNER_HOLO,
    "corporate_flagship": SCANNER_HOLO,
    "colonial_transport": None,
    "cargotran": SCANNER_HOLO,
    "merchant_freighter": SCANNER_HOLO,
    "havoc_gunstar": SCANNER_HOLO,
    "imperial_starship": SCANNER_HOLO,
    "star_master": SCANNER_HOLO,
    "constellation": SCANNER_DENSITY,
    "tkhasi_orion": SCANNER_DENSITY,
    "tholian_sentinel": SCANNER_HOLO,
    "taurean_mule": SCANNER_HOLO,
    "interdictor_cruiser": SCANNER_HOLO,
    "escape_pod": None,
}
# s7: Bible / MBBS density chart. Only what this game has.
DENSITY_PER_FIGHTER = 5
DENSITY_PER_ARMID = 10
DENSITY_PER_LIMPET = 2
DENSITY_PER_SHIP = 40
DENSITY_PER_PORT = 100
DENSITY_PER_PLANET = 500
PROBE_MAX_HOPS = 45  # s13: TWGS "Maximum Course Length"
SCAN_TURNS_TW2002 = {SCANNER_DENSITY: 0, SCANNER_HOLO: 1}  # s5, s8


def info_tw2002() -> bool:
    return INFO_MODE == "tw2002"


def scanner_room(class_key: str) -> str | None:
    """The best scanner this hull can carry (s3)."""
    return SCANNER_BY_HULL.get(class_key)


def scan_tiers(scanner: str | None) -> list[str]:
    """Scan modes a fitted scanner runs: a holo scanner also scans density (s2)."""
    if scanner == SCANNER_HOLO:
        return [SCANNER_DENSITY, SCANNER_HOLO]
    if scanner == SCANNER_DENSITY:
        return [SCANNER_DENSITY]
    return []


def scanner_cost(item: str) -> int:
    return DENSITY_SCANNER_COST if item == "density_scanner" else HOLO_SCANNER_COST


def scanner_offer(class_key: str, fitted: str | None) -> dict[str, int]:
    """Scanner items StarDock will fit on this hull now: item -> price (s1-s3).

    A hull takes one scanner; a holo replaces a density one. Nothing is offered
    that the hull cannot carry or that would not be an upgrade.
    """
    room = scanner_room(class_key)
    out: dict[str, int] = {}
    if room is None:
        return out
    if fitted is None:
        out["density_scanner"] = DENSITY_SCANNER_COST
    if room == SCANNER_HOLO and fitted != SCANNER_HOLO:
        out["holo_scanner"] = HOLO_SCANNER_COST
    return out


def scanner_value(scanner: str | None) -> int:
    """Net-worth value of a fitted scanner (what it cost)."""
    if scanner == SCANNER_HOLO:
        return HOLO_SCANNER_COST
    if scanner == SCANNER_DENSITY:
        return DENSITY_SCANNER_COST
    return 0


def elimination_deaths(config=None) -> int:
    """Ship losses that remove a player for good. 0 means never (d19).

    GameConfig.elimination_deaths wins when set. Unset is the mode default:
    MAX_DEATHS_BEFORE_ELIM in legacy, off in tw2002.
    """
    value = getattr(config, "elimination_deaths", None)
    if value is not None:
        return max(0, int(value))
    if death_tw2002():
        return 0
    return MAX_DEATHS_BEFORE_ELIM

# --- Experience / alignment ranks --------------------------------------------
# Tuple of (threshold_xp, rank_name) inclusive; choose highest matching.
RANK_TABLE: list[tuple[int, str]] = [
    (0,        "Civilian"),
    (100,      "Private"),
    (500,      "Captain"),
    (2_000,    "Lieutenant"),
    (5_000,    "Commander"),
    (15_000,   "Captain First"),
    (40_000,   "Vice Admiral"),
    (100_000,  "Admiral"),
    (250_000,  "Fleet Admiral"),
]
ALIGNMENT_TIERS: list[tuple[int, str]] = [
    (-10_000, "Terrorist"),
    (-1_000,  "Pirate"),
    (-200,    "Smuggler"),
    (-50,     "Rogue"),
    (0,       "Neutral"),
    (100,     "Citizen"),
    (500,     "Patriot"),
    (2_000,   "Hero"),
    (10_000,  "Saint"),
]
# Experience awards (added to player.experience) for given event types.
XP_AWARDS = {
    "trade":      1,    # per trade tick (already small)
    "warp":       1,
    "kill_player": 200,
    "kill_ferr":  20,   # per aggression point
    "build_citadel_lvl": 50,
    "deploy_genesis": 100,
    "claim_planet": 75,  # 0.75x genesis — reward salvage, but less than creation
    "alliance":   25,
    "scan":       1,
    "probe":      3,
}

# --- Experience, alignment and rank (RANK_MODE) --------------------------------
# docs/playtests/ranks/EXPERIENCE_ALIGNMENT.md. "legacy" keeps RANK_TABLE,
# ALIGNMENT_TIERS and XP_AWARDS above exactly as they were.
RANK_MODE = "tw2002"


def rank_tw2002() -> bool:
    return RANK_MODE == "tw2002"


# r1/r2: 22 titles per side, thresholds 2, 4, 8 ... 4,194,304. r3: below 2 is "Civilian".
RANK_THRESHOLDS: tuple[int, ...] = (0, *tuple(2 ** n for n in range(1, 23)))
GOOD_RANKS: tuple[str, ...] = (
    "Civilian", "Private", "Private 1st Class", "Lance Corporal", "Corporal", "Sergeant",
    "Staff Sergeant", "Gunnery Sergeant", "1st Sergeant", "Sergeant Major", "Warrant Officer",
    "Chief Warrant Officer", "Ensign", "Lieutenant J.G.", "Lieutenant", "Lieutenant Commander",
    "Commander", "Captain", "Commodore", "Rear Admiral", "Vice Admiral", "Admiral", "Fleet Admiral",
)
EVIL_RANKS: tuple[str, ...] = (
    "Civilian", "Nuisance 3rd Class", "Nuisance 2nd Class", "Nuisance 1st Class", "Menace 3rd Class",
    "Menace 2nd Class", "Menace 1st Class", "Smuggler 3rd Class", "Smuggler 2nd Class",
    "Smuggler 1st Class", "Smuggler Savant", "Robber", "Terrorist", "Pirate", "Infamous Pirate",
    "Notorious Pirate", "Dread Pirate", "Galactic Scourge", "Enemy of the State", "Enemy of the People",
    "Enemy of Humankind", "Heinous Overlord", "Prime Evil",
)
# x1-x11: experience by event in tw2002. Keys missing here give nothing.
XP_AWARDS_TW2002 = {
    "trade": 1,             # x1: one point per successful trade (HAGGLE.md, gap 9.2)
    "kill_ferr": 20,        # x15: Ferrengi reward unchanged (no alien exp to share)
    "deploy_genesis": 25,   # x6
    "first_dock": 1,        # x2: first trade anyone makes at a port
    "daily": 1,             # x3: midnight login
    "destroy_planet": 50,   # x7
    "destroy_port": 50,     # x11
}
DAILY_ALIGNMENT = 1               # x3
GENESIS_ALIGNMENT = 10            # x6: +10 good, 0 neutral, -10 evil
PLANET_DESTROY_ALIGNMENT_TW2002 = 1  # x7 / conflict 14
FEDSAFE_MAX_EXPERIENCE = 999      # u1
COMMISSION_ALIGNMENT = 1000       # u2 / conflict 12
KILL_EXP_SHARE = 0.10             # x13
KILL_ALIGN_SHARE = 0.5            # a2
COMBAT_EXP_DIVISOR = {"opposite": 15, "same": 35, "neutral": 25}   # x12 / x14
COMBAT_ALIGN_DIVISOR = 5000                                         # a1: x 0.2 / 1000
FIGHTER_ALIGN_DIVISOR = {"opposite": 5000, "same": 10000}           # a3 (Gold/Classic)


def xp_award(key: str) -> int:
    table = XP_AWARDS_TW2002 if rank_tw2002() else XP_AWARDS
    return int(table.get(key, 0))


def ship_min_alignment(spec: dict, default: int) -> int:
    """u3: a hull that needs alignment needs a Federal Commission in tw2002.

    Legacy keeps each caller's default, so an evil trader stays barred from every
    hull there (today's build). In tw2002 a hull without the key has no floor.
    """
    if "min_alignment" not in spec:
        return -10**9 if rank_tw2002() else default
    if rank_tw2002():
        return COMMISSION_ALIGNMENT
    return int(spec["min_alignment"])


# --- Rob / steal at ports (ROB_MODE) ------------------------------------------
# docs/playtests/ports/ROB_STEAL.md. "legacy" = today's behaviour (not available).
ROB_MODE = "tw2002"


def rob_tw2002() -> bool:
    return ROB_MODE == "tw2002"


ROB_MIN_ALIGNMENT = -100          # r1: alignment <= this
ROB_CREDIT_FACTOR = 6             # r5: MBBS EXP * 6 (classic was 3)
STEAL_HOLD_DIVISOR = 21           # r8: MBBS EXP / 21 (classic was 30)
ROB_BUST_DENOMINATOR = 50         # r11: ~1 in 50
# r22 UNVERIFIED success awards (easy to retune)
ROB_SUCCESS_ALIGN_DIVISOR = 10_000
ROB_SUCCESS_EXP_DIVISOR = 10_000
STEAL_SUCCESS_ALIGN_DIVISOR = 6
STEAL_SUCCESS_EXP_DIVISOR = 15

# --- Ship hardware (HARDWARE_MODE) --------------------------------------------
# docs/playtests/ships/SHIP_HARDWARE.md. "legacy" = today's bars (armid random/100,
# same-sector player photon scramble, no cloak / disruptor / limpet removal).
HARDWARE_MODE = "tw2002"


def hardware_tw2002() -> bool:
    return HARDWARE_MODE == "tw2002"


# Armid (h1/h2). Legacy keeps ARMID_DAMAGE=100 and MINE_MAX_HITS_PER_MOVE random.
ARMID_DAMAGE_TW2002 = 20
# Photon wave duration in day-ticks (h7). TEDIT sample "1 seconds" -> 1 tick.
PHOTON_WAVE_DURATION = 1
# Cloak (h12-h16)
CLOAK_COST = 25_000
CLOAK_MAX = 5
CLOAK_FAIL_RATE = 0.03  # TEDIT FailRate 3%; checked on tick_day while cloaked
# Mine disruptor (h18-h20)
DISRUPTOR_COST = 40_000
DISRUPTOR_MAX = 10
DISRUPTOR_CLEAR_MAX = 12  # Bible ceiling
# Limpet removal (h22)
LIMPET_REMOVAL_COST = 1_250

# --- Ship hardware v2 (same HARDWARE_MODE switch) -----------------------------
# docs/playtests/ships/SHIP_HARDWARE_V2.md. Everything below is off under
# HARDWARE_MODE "legacy" (not sold, not offered, handlers refuse, no NavHaz read).
# Corbomite (v1-v4). TWGS 3.11 editor default price; Bible / HardwareMenu cap 1,500.
CORBOMITE_COST = 1_000
CORBOMITE_MAX = 1_500
# MBBS manual: 1,500 units "will blow 30,000 fighters off of the attacker";
# Misc_shipodds log: "damages of 30000 battle points". 30,000 / 1,500 = 20 per unit.
CORBOMITE_DAMAGE_PER_UNIT = 20
# Marker beacons (v5-v9). TWGS price 100; 41-character message (Gypsy "Release Beacon").
BEACON_COST = 100
BEACON_MESSAGE_MAX = 41
BEACON_TURNS = 0  # UNVERIFIED: releasing a beacon is not listed as a turn-using command
# "Beacon Max" from the ship data in Gypsy / Iago (TEDIT ship screens). Pod carries none.
BEACON_MAX_BY_HULL: dict[str, int] = {
    "merchant_cruiser": 50,
    "scout_marauder": 10,
    "missile_frigate": 5,
    "battleship": 50,
    "corporate_flagship": 100,
    "colonial_transport": 10,
    "cargotran": 20,
    "merchant_freighter": 20,
    "imperial_starship": 150,
    "havoc_gunstar": 5,
    "star_master": 50,
    "constellation": 50,
    "tkhasi_orion": 20,
    "tholian_sentinel": 10,
    "taurean_mule": 20,
    "interdictor_cruiser": 100,
}
# Psychic probe (v10-v12). TWGS price 2,500; one per ship (Slice-10 record: PsyProbe * 1).
PSYCHIC_PROBE_COST = 2_500
PSYCHIC_PROBE_MAX = 1
# Atomic detonator (v13-v19). TWGS price 60,000; Bible cap 5.
ATOMIC_DETONATOR_COST = 60_000
ATOMIC_DETONATOR_MAX = 5
# v19: the old `atomic_mines` port nuke is kept on purpose (only port-kill path in this
# game). False retires it under HARDWARE_MODE tw2002 (not sold, deploy refused).
ATOMIC_MINES_PORT_NUKE = True
# NavHaz (v20-v25). cabal glossary: each 1% does 10 damage, odds equal to the %.
NAVHAZ_DAMAGE_PER_PCT = 10
NAVHAZ_MAX_PCT = 100
# MBBS manual: "each planet destroyed produces 10% Haz"; density table 210 = destroyed planet.
NAVHAZ_PER_PLANET_DESTROYED = 10
# MBBS manual: "generally it'll be reduced by 3%" each night. FedSpace clears at Extern.
NAVHAZ_DISPERSION_PER_DAY = 3
DENSITY_PER_NAVHAZ_PCT = 21
DENSITY_PER_BEACON = 1

# --- Ferrengi behaviour -------------------------------------------------------
FERRENGI_MOVE_PROB = 0.6              # chance per day each Ferrengi moves
FERRENGI_HUNT_AGGRESSION_THRESHOLD = 3 # below this they ignore armed players (was 4)
# Opportunistic threshold: when a target has 0 fighters AND 0 shields, even
# low-aggression Ferrengi pounce. Makes "unarmed in deep space" a real risk
# every turn, not a 1-in-130 event (observed attack rate in seed 7777).
FERRENGI_OPPORTUNIST_AGGRESSION_THRESHOLD = 1
FERRENGI_FLEE_FIGHTER_RATIO = 1.5     # if player.fighters > theirs * this, they flee

# --- Ferrengi -----------------------------------------------------------------

FERRENGI_MAX_AGGRESSION = 10
FERRENGI_SPAWN_PER_DAY = 3
# Pre-seed at match start so there's tension from day 1 instead of day 2.
FERRENGI_INITIAL_SPAWN = 4
FERRENGI_BOUNTY_PER_AGG = 1000
FERRENGI_STRENGTH_RAMP_DAYS = 200
FERRENGI_MIN_STRENGTH_SCALE = 0.25
# Grace window (in-game days) during which Ferrengi will NOT engage
# players when the match started everyone at StarDock. Without this,
# an initial-spawn raider in sector 11 can jump a fresh cargotran on
# turn 1 of day 0 before the agent has even decided which port to
# visit — which destroys the LLM evaluation signal for the first day.
# Set to 0 to disable. Only applies when config.all_start_stardock.
#
# NB: extended from 2 to 5 after a match where a single raider camped
# StarDock (sector 1) from day 6 onward and destroyed one commander's
# ship once (death #1) and eliminated another commander entirely
# across days 7/8/10 after StarDock-respawn. 5 days of safety gives
# agents enough time to Genesis, build at least L1 citadel, and
# choose whether to stay near StarDock or push out before raiders
# become a threat. The LLM-evaluation signal for early-game trading
# / planet-building remains clean while still leaving the majority
# of a 30-365 day match for genuine ferrengi pressure.
FERRENGI_STARTUP_GRACE_DAYS = 5

# --- Ferrengi aliens (FERRENGI_MODE) ------------------------------------------
# ferrengi-aliens-v1 / docs/playtests/npc/FERRENGI.md
# "tw2002": three hulls, Ferrengal, tribute encounter, grudges, regen, mine hits.
# "legacy": pre-slice simplified raiders (byte-identical spawn/roam/combat).
FERRENGI_MODE = "tw2002"

def ferrengi_tw2002() -> bool:
    return FERRENGI_MODE == "tw2002"

# Hull specs: FERRSPEC + docs wiki + MBBS. Odds from FERRSPEC (SOURCE-CONFLICT vs Bible).
FERRENGI_HULL_ASSAULT = "assault_trader"
FERRENGI_HULL_CRUISER = "battle_cruiser"
FERRENGI_HULL_DREAD = "dreadnought"
FERRENGI_HULL_SPECS = {
    "assault_trader": {
        "label": "Ferrengi Assault Trader",
        "max_fighters": 3000,
        "max_shields": 200,
        "holds": 50,
        "tpw": 2,
        "odds": 1.0,
        "density": 40,
        "max_mines": 10,
        "photons": 0,
    },
    "battle_cruiser": {
        "label": "Ferrengi Battle Cruiser",
        "max_fighters": 8000,
        "max_shields": 800,
        "holds": 75,
        "tpw": 3,
        "odds": 1.2,
        "density": 100,
        "max_mines": 25,
        "photons": 0,
    },
    "dreadnought": {
        "label": "Ferrengi Dreadnought",
        "max_fighters": 15000,
        "max_shields": 1000,
        "holds": 100,
        "tpw": 4,
        "odds": 1.4,
        "density": 100,
        "max_mines": 50,
        "photons": 1,
    },
}
FERRENGI_ODDS_BY_HULL = {
    "assault_trader": 1.0,
    "battle_cruiser": 1.2,
    "dreadnought": 1.4,
}
# Encounter: "tribute" opens Flee/Attack/Surrender; "auto_combat" = legacy immediate fight.
FERRENGI_ENCOUNTER = "tribute"
FERRENGI_FIGHTER_BLOCK = False  # Iago: Ferrengi ignore deployed fighters
FERRENGI_HIT_MINES = True
FERRENGI_ALIGN_ON_KILL = 10
FERRENGI_REGEN_PCT = 0.20  # TEDIT 20% of hull max
FERRENGAL_MINES = 50  # Bible
FERRENGAL_FIGHTERS = 1000  # UNVERIFIED stand-in for "cloud of Ferrengi ftrs"
FERRENGAL_MIN_HOPS = 8
FERRENGAL_SPAWN_RADIUS = 3
FERRENGI_TRIBUTE_HOLDS = 5  # UNVERIFIED
FERRENGI_TRIBUTE_CREDIT_PCT = 0.10  # UNVERIFIED
FERRENGI_SPAWN_CREDITS_PER_AGG = 500  # UNVERIFIED
FERRENGI_SEES_CLOAK = False  # UNVERIFIED; consistent with HARDWARE cloak
FERRENGI_OWNER_ID = "ferrengi"  # mine / fighter owner marker


# --- Corp ---------------------------------------------------------------------

CORP_FORMATION_COST = 500_000
CORP_MAX_MEMBERS_DEFAULT = 2

# --- Victory ------------------------------------------------------------------

VICTORY_DOMINATION_SECTOR_PCT = 0.50
VICTORY_CREDITS_THRESHOLD = 100_000_000
VICTORY_DEFAULT_MAX_DAYS = 30

# --- Universe -----------------------------------------------------------------

DEFAULT_UNIVERSE_SIZE = 1000
DEFAULT_AVG_WARPS = 2.7
DEFAULT_ONE_WAY_FRACTION = 0.15

# --- Class 0 ports and Terra (CLASS0_MODE) ------------------------------------
# CLASS0_TERRA.md. Default tw2002: Terra colonist pool, Alpha Centauri / Rylos,
# shield price wave, MSL Extern sweep. legacy = pre-slice behaviour byte-identical.

CLASS0_MODE = "tw2002"


def class0_tw2002() -> bool:
    return CLASS0_MODE == "tw2002"


TERRA_MAX_COLONISTS = 100_000  # t2 SOURCE-CONFLICT: TEDIT 100k vs Iago 10k holds; TWGS taken
TERRA_REGEN_PER_DAY = 750  # t3 CONFIRMED TEDIT / MM
TERRA_LOAD_TURNS = 1  # t4 CONFIRMED REV
TERRA_COLONIST_PRICE = 0  # t5 UNVERIFIED by absence; net-worth still uses COLONIST_PRICE

# t13: "mirror" = fighter wave opposite phase; "flat" = 10 (also legacy).
SHIELD_PRICE_MODE = "mirror"

# t21 SOURCE-CONFLICT: TWGS keep vs Slice cap_l2 vs docs wiki remove. TWGS taken.
CLASS0_EXTERN_PLANET_RULE = "keep"

# t15 placement band (numbers UNVERIFIED; named constants).
CLASS0_MIN_HOPS = 4
CLASS0_MAX_HOPS = 12
CLASS0_MIN_SEPARATION = 4

CLASS0_SELL_ITEMS = ("fighters", "shields", "holds")

# t25 FedSpace Federal outposts (FED_OUTPOST_MODE). Original TW2002 has exactly three Class 0 ports
# (Sol, Alpha Centauri, Rylos) and every one sells fighters, shields and holds (cabal glossary
# "Class 0 Ports", EIS TradeWars.html, Iago). Our FedSpace sectors 2-10 also hold ours-only "Federal"
# ports (GAP 1.18, UNVERIFIED in the original) stored as class 0 that trade and sell nothing, so a seat
# starting there read "class_id 0" as a Class 0 port and buy_equip was refused.
# "tw2002": seats see them as Federal outposts (class_id null + class_display + note) and the buy_equip
# refusal names them. "legacy": shown as class 0 with the old reason (byte-identical).
# Generation is unchanged in both modes (no extra rng draws; same ports in the same sectors).
FED_OUTPOST_MODE = "tw2002"  # "tw2002" | "legacy"
FED_OUTPOST_CLASS_DISPLAY = "Federal outpost (not Class 0)"
FED_OUTPOST_NOTE = ("Federal outpost: not a Class 0 port. No commodity trading and no buy_equip here. "
                    "Fighters, shields and holds: StarDock (sector 1, Sol) or the Class 0 ports Alpha Centauri "
                    "and Rylos.")
FED_OUTPOST_NOTE_NO_CLASS0 = ("Federal outpost: not a Class 0 port. No commodity trading and no buy_equip here. "
                              "Equipment: StarDock (sector 1).")
FED_OUTPOST_BUY_REASON = "this FedSpace port is a Federal outpost, not a Class 0 port; it sells nothing"


def fed_outpost_tw2002() -> bool:
    return FED_OUTPOST_MODE == "tw2002"


def shield_unit_price(day: int) -> int:
    """Credits for one shield today (CLASS0_TERRA.md t13)."""
    from .class0 import shield_unit_price as _shield
    return _shield(day)


# --- Net-worth valuation (NET_WORTH_MODE) -------------------------------------
# docs/playtests/fullgame/FULLGAME_FIXES_V1.md. TW2002 keeps no net-worth score: players rank by
# experience and alignment (GAP_MAP 12.5), so this metric is ours. "legacy" = fighters at 50 and
# shields at 10 each, the pre-wave flat prices (byte-identical). "tw2002" = while StarDock charges the
# 160..239 wave (Hekate, Misc_FigShieldPrices.txt), a fighter or shield counts NW_HARDWARE_FRACTION
# of the wave midpoint - the same share of its price the hull gets. Other gear stays at cost.
NET_WORTH_MODE = "tw2002"        # "tw2002" | "legacy"
NW_HULL_FRACTION = 0.5           # hull counts half its StarDock price
NW_HARDWARE_FRACTION = 0.5       # wave-priced fighters / shields: the hull's share
NW_WAVE_MID_PRICE = 200          # wave midpoint: base 160 + amp 80 / 2


def net_worth_tw2002() -> bool:
    return NET_WORTH_MODE == "tw2002"


def _nw_wave_share() -> int:
    return round(NW_WAVE_MID_PRICE * NW_HARDWARE_FRACTION)


def nw_fighter_value() -> int:
    """Net-worth credit for one fighter (ship or planet).

    legacy, or a flat 50 cr fighter price: FIGHTER_COST. tw2002 with the fighter wave live: 100.
    """
    if not net_worth_tw2002() or ECONOMY_SCALE_MODE != "tw2002":
        return int(FIGHTER_COST)
    return _nw_wave_share()


def nw_shield_value() -> int:
    """Net-worth credit for one ship shield. legacy, or flat 10 cr shields: 10. Mirror wave live: 100."""
    if not net_worth_tw2002() or SHIELD_PRICE_MODE != "mirror" or not class0_tw2002():
        return 10
    return _nw_wave_share()


def nw_planet_shield_value() -> int:
    """One planet shield. legacy: 10. tw2002: PLANET_SHIELD_SHIP_COST ship shields, the deposit rate."""
    if not net_worth_tw2002():
        return 10
    return nw_shield_value() * int(PLANET_SHIELD_SHIP_COST)


# --- Buy reserve (BUY_RESERVE_MODE) --------------------------------------------
# Not a TW2002 rule: a planning aid for LLM seats (FULLGAME_FIXES_V1.md). Seed 250925 full game:
# the Grok seat bought 815 fighters (171,965 cr) off the "max buy" hint and kept 151 cr.
# "tw2002" = the action hint names a working-capital reserve and the largest fighter / shield buy
# that keeps it. "legacy" = no hint (byte-identical).
BUY_RESERVE_MODE = "tw2002"      # "tw2002" | "legacy"
BUY_RESERVE_FLOOR_CREDITS = 20_000  # trade stake kept after a hardware buy
BUY_RESERVE_CR_PER_HOLD = 200    # or a full load at about twice the equipment base (102)
BUY_RESERVE_ITEMS = ("fighters", "shields")
# True: an LLM seat's fighter / shield buy is cut to the reserve-keeping qty (none left: it waits).
LLM_BUY_RESERVE_SOFT_CAP = False


def buy_reserve_on() -> bool:
    return BUY_RESERVE_MODE == "tw2002"


def working_capital_reserve(holds: int) -> int:
    """Credits to keep after a fighter / shield buy: the floor, or a full trade load."""
    return max(int(BUY_RESERVE_FLOOR_CREDITS), max(0, int(holds or 0)) * int(BUY_RESERVE_CR_PER_HOLD))


def reserve_max_qty(credits: int, unit: int, room: int | None, reserve: int) -> int:
    """Largest qty at `unit` cr that leaves at least `reserve` credits, capped by `room`."""
    if int(unit) <= 0:
        return 0
    qty = max(0, int(credits) - int(reserve)) // int(unit)
    if room is not None:
        qty = min(qty, max(0, int(room)))
    return int(qty)


# --- Planet growth dividend (PLANET_DIVIDEND_MODE) ------------------------------
# docs/playtests/fullgame/FULLGAME_FIXES_V2.md. The dividend is ours (GAP_MAP 6.13): TW2002 planets
# grow only by daily production from colonists, and the citadel treasury earns interest
# (TWFAQ_20PLANET.txt; Iago_War_Manual.txt); a stored fighter, credit or colonist earns nothing.
# "legacy" = the baseline moves only at the daily tick, so a ship-to-planet deposit counts as growth
# (deposit 5000 fighters = 75,000 cr; withdraw and redeposit pays it again). "tw2002" = every
# ship<->planet transfer (DIVIDEND_TRANSFER_VERBS in runner.py) moves the baseline by the value moved,
# so only production, colonist growth, treasury interest and citadel completion pay.
PLANET_DIVIDEND_MODE = "tw2002"  # "tw2002" | "legacy"


def dividend_transfers_neutral() -> bool:
    return PLANET_DIVIDEND_MODE == "tw2002"


# --- Combat that happens (HUNT_MODE, COMBAT_FRAMING_MODE, SLOW_HULL_HINT_MODE) ----
# docs/playtests/fullgame/FULLGAME_FIXES_V2.md. In TW2002 traders hunt each other and the Ferrengi for
# experience, bounties and salvage (TWFAQ_FERRSPEC; GAP_MAP 9.x/11.x). The seed 250925 full game had no
# ship fight at all: N2/N3 never attacked a ship and the LLM prompt framed combat as optional.
# HUNT_MODE "tw2002" = an N3 seat (value_allocator) attacks a ship or Ferrengi in its own sector, outside
# FedSpace, when its one-attack power is >= HUNT_STRENGTH_MARGIN x the target's defence read from what it can
# see (Ferrengi fighters/shields/hull; a trader's fighters and hull with the hull's MAX shields assumed),
# and the estimated alignment cost keeps it >= HUNT_ALIGN_FLOOR. N1/N2 never hunt. "legacy" = no hunting.
HUNT_MODE = "tw2002"             # "tw2002" | "legacy"
HUNT_STRENGTH_MARGIN = 2.0       # power >= 2x visible worst-case defence
HUNT_ALIGN_FLOOR = 0             # never hunt yourself evil (side() flips below 0)
HUNT_ALIGN_UNCERTAINTY = 50      # a good target's alignment is hidden: assume yours + this
HUNT_MAX_ATTACKS_PER_TARGET_DAY = 2  # a target that survives (flees) is not chased all day
# Arming (seat_brain._hunt_arm): an N3 seat that never carries more than the 200-fighter defence floor
# can never clearly beat anyone (seed 250925 after1: 0 of 166 sightings winnable). On a hunting hull
# (odds >= HUNT_ARM_MIN_ODDS, one attack can send HUNT_ARM_FIGHTERS) with credits >= HUNT_ARM_CASH_GATE,
# it buys toward HUNT_ARM_FIGHTERS at an equipment port: one buy a game day, at most HUNT_ARM_SPEND_SHARE of
# spare cash, never leaving less than HUNT_ARM_CASH_GATE.
HUNT_ARM_FIGHTERS = 1500         # BattleShip 1500 x 1.6 = 2400 power: 2x a 761-ftr Ferrengi assault trader
HUNT_ARM_CASH_GATE = 150_000
HUNT_ARM_SPEND_SHARE = 0.25
HUNT_ARM_MIN_ODDS = 1.3          # BattleShip 1.6, Missile Frigate 1.3, Imperial 1.5, Constellation 1.4
HUNT_ARM_MIN_BUY = 50
HUNT_ARM_OPTION_VALUE = 40_000.0  # N3 options path, cr/turn: above a holo scan (35k), one turn, docked only
# COMBAT_FRAMING_MODE "tw2002" = the LLM prompt and hints present attack neutrally with the real rewards
# (XP, bounty, salvage, the victim's ship) and costs (fighters, alignment), and show the win check.
# "legacy" = the old text ("High-aggression will wreck you", "Surrender often safer").
COMBAT_FRAMING_MODE = "tw2002"   # "tw2002" | "legacy"
# SLOW_HULL_HINT_MODE "tw2002" = the price sheet and StarDock hint say a 4-turn hull makes ~turns/4 warps a day,
# and the N3 heuristic never picks a defence hull with more turns per warp than its current one.
SLOW_HULL_HINT_MODE = "tw2002"   # "tw2002" | "legacy"
SLOW_HULL_TURNS_PER_WARP = 4     # hint only for hulls this slow or slower
SLOW_HULL_HINT_MAX_TURNS_PER_DAY = 100  # ... and only when the day is this short


# COMBAT_SCANNER_MODE "tw2002" = the Battleship and the Missile Frigate carry the built-in Combat Scanner, which
# shows how many shields the other trader in your sector has (Someguy_MBBS_manual.txt: Battleship "built-in
# Combat Scanner which shows how many shields your victim has when you attack"; Missile Cruiser "comes with a
# combat scanner"). sector.traders then carries `shields`. "legacy" = shields hidden from every hull.
COMBAT_SCANNER_MODE = "tw2002"   # "tw2002" | "legacy"
COMBAT_SCANNER_HULLS = ("battleship", "missile_frigate")


# --- Hull recovery after a loss (GENESIS_HULL_MODE) ------------------------------------------
# docs/playtests/fullgame/FULLGAME_FIXES_V2.md. A seat whose ship dies flies on in the free Scout Marauder,
# and the Scout carries no Genesis Torpedo (max_genesis 0 in SHIP_SPECS_TW2002; TW2002 ship chart). QC seed
# 20260925: N2-P3 and N1-P5 lost their Merchant Cruisers to the Ferrengal armids on day 1, then spent days 2-10
# flying StarDock <-> a port because "genesis is affordable" while StarDock could never sell them one (net worth
# frozen at ~40k). "tw2002" = the N1/N2/N3 brains count genesis as reachable only when ship.genesis_cap > 0; in
# a 0-cap hull they trade toward the CargoTran trade-in instead. "legacy" = the old check (credits only).
GENESIS_HULL_MODE = "tw2002"     # "tw2002" | "legacy"
# MINE_OVERFLOW_MODE "tw2002" = armid damage past the shields comes off the fighters as (damage - shields
# the ship had). "legacy" = the overflow was computed after the shields were already zeroed, so a ship with
# some shields lost fighters for the full damage (shields counted twice against it).
MINE_OVERFLOW_MODE = "tw2002"    # "tw2002" | "legacy"


def genesis_hull_on() -> bool:
    return GENESIS_HULL_MODE == "tw2002"


def mine_overflow_fixed() -> bool:
    return MINE_OVERFLOW_MODE == "tw2002"


def hunt_on() -> bool:
    return HUNT_MODE == "tw2002"


def combat_scanner_on() -> bool:
    return COMBAT_SCANNER_MODE == "tw2002"


def combat_framing_on() -> bool:
    return COMBAT_FRAMING_MODE == "tw2002"


def slow_hull_hint_on() -> bool:
    return SLOW_HULL_HINT_MODE == "tw2002"


def ferrengi_odds_for_hull(hull: str | None) -> float:
    """Public odds of a Ferrengi hull (what sector.ferrengi shows), same table the engine uses."""
    if hull and ferrengi_tw2002():
        return float(FERRENGI_ODDS_BY_HULL.get(hull, FERRENGI_COMBAT_ODDS))
    return float(FERRENGI_COMBAT_ODDS)


def hunt_alignment_cost(my_alignment: int, losses: int, target_side: str | None) -> int:
    """Estimated alignment a kill costs (x12/a1 + x13/a2); an evil target costs nothing."""
    if target_side == "evil":
        return 0
    est = max(0, int(my_alignment)) + HUNT_ALIGN_UNCERTAINTY
    return int(est * KILL_ALIGN_SHARE) + (int(losses) * est) // COMBAT_ALIGN_DIVISOR


# --- FedSpace police (FED_MODE) ----------------------------------------------
# docs/playtests/fedspace/FEDSPACE_POLICE.md. "legacy" = pre-slice byte-identical.

FED_MODE = "tw2002"


def fed_tw2002() -> bool:
    return FED_MODE == "tw2002"


# Sub-switches
FED_PROTECT_PUNISH = "pod"       # "pod" | "refuse" (f8)
ISS_REPO_MODE = "twgs"           # "twgs" | "mbbs" (f22)
FED_TOW_DEST = "random"          # "random" | "msl" (f14)
REWARD_TARGET_RULE = "any_red"   # "any_red" | "listed" (f18)
FED_BLOCKED_BY_MINES = False     # f4 SOURCE-CONFLICT; off by default
COMMISSION_ONCE = True           # f17 MBBS tie-break

# Federals (f2/f3/f5)
FED_DENSITY_NELSON = 462
FED_DENSITY_ZYRAIN = 489
FED_DENSITY_CLAUSEWITZ = 512
FED_ZYRAIN_START = 7
FED_START_MIN_HOPS = 6           # UNVERIFIED stand-in for deep starts
FED_HOPS_PER_DAY = 3             # UNVERIFIED

# Attack penalties (f7)
FED_ATTACK_ALIGN_PENALTY = 10
FED_ATTACK_EXP_KEEP = 0.9        # lose 10%; UNVERIFIED rounding = int trunc

# Tows (f11/f12)
FED_TOW_FIGHTER_LIMIT = 98       # tow when fighters > this (Gypsy: 99+)
FED_SHIPS_PER_SECTOR = 5

# Police HQ (f16-f18)
POLICE_MIN_ALIGNMENT = 0
COMMISSION_APPLY_MIN = 500       # apply when 500 <= align < COMMISSION_ALIGNMENT
REWARD_MIN = 1000                # UNVERIFIED minimum
REWARD_ALIGN_PER = 1000          # +1 alignment per this many credits

# f9 optional floors (defaults keep today's is_fedsafe)
FEDSAFE_MIN_ALIGNMENT = 0
FEDSAFE_MAX_FIGHTERS = None      # None = no fighter floor

# f23
FED_HAIL_MESSAGE = "return your commission or lose the ship"


# --- Ship TransWarp Type 1 (SHIP_TW_MODE) ------------------------------------
# docs/playtests/ships/SHIP_TRANSWARP.md. "legacy" = no drive, no verb, no new keys.

SHIP_TW_MODE = "tw2002"          # "tw2002" | "legacy"
SHIP_TW_BLIND = "density0"       # "density0" | "refuse"
SHIP_TW_FED_LOCK = "commissioned"  # "commissioned" | "fighter_only"
SHIP_TW_TURN_COST = "tpw"        # "tpw" | "hops"
SHIP_TW_FRIENDLY = "own_corp_ally"  # "own_corp_ally" | "own_only"
SHIP_TW_CLOAK_POLICY = "allow_decloak"  # UNVERIFIED
SHIP_TW_FUSE_REFUNDS = False
SHIP_TW_TYPE1_COST = 12_500
SHIP_TW_ORE_PER_HOP = 3
SHIP_TW_LIST_CAP = 40
SHIP_TW_HULLS = frozenset({"imperial_starship", "corporate_flagship", "havoc_gunstar"})
# Which TransWarp hulls get the commissioned FedSpace lock (tw10). "all_tw" = ISS, CFS and Havoc (as shipped
# in slice 48); "iss_only" = only the Imperial StarShip (the commission perk read narrowly). Ben 2026-10-05.
SHIP_TW_FED_LOCK_HULLS = "all_tw"  # "all_tw" | "iss_only"


def ship_tw_on() -> bool:
    return SHIP_TW_MODE == "tw2002"


# --- Ship fleet + transporter (FLEET_MODE) ------------------------------------
# docs/playtests/ships/SHIP_FLEET.md. "legacy" = one ship per player, no new verbs, keys, events or rng draws.

FLEET_MODE = "tw2002"              # "tw2002" | "legacy"
FLEET_MAX_SHIPS = 5                # fl2 UNVERIFIED / ours: per player, the manned ship included
FLEET_XPORT_METRIC = "directed"    # fl10 UNVERIFIED: "directed" | "undirected"
FLEET_XPORT_SAME_SECTOR = True     # fl11 UNVERIFIED: distance 0 is in range for every hull (pod, Scout)
FLEET_XPORT_INTERDICT = "ignore"   # fl16 UNVERIFIED: "ignore" | "block"
FLEET_POD_ON_LEAVE = "discard"     # fl17a UNVERIFIED: "discard" | "park"
FLEET_CLOAK_ON_LEAVE = "decloak"   # fl20 UNVERIFIED: "decloak" | "keep"
FLEET_LIMPET_POLICY = "hull"       # fl19: "hull" | "pilot"
FLEET_FED_REPO = "fedspace"        # fl23: "fedspace" | "off"
FLEET_UNMANNED_ODDS_FACTOR = 0.5   # fl24 OldFAQ #18 (v2) - UNVERIFIED for v3
FLEET_UNMANNED_ALIGN = "v2_penalty"  # fl24 UNVERIFIED: "v2_penalty" | "none"
FLEET_UNMANNED_KILL_EXP = 0        # fl24 UNVERIFIED
FLEET_SELL_WHERE = "stardock_orbit"  # fl7: only an own ship in orbit at StarDock (sector 1)
BOT_FLEET_POLICY = "spare_only"    # "spare_only" | "off"
DENSITY_PER_UNMANNED = 38          # fl22 cabal formulas.html / REV v3.0x
# fl9 Bible ship chart "Transporter Range" = MBBS "Teleport Range" (MBBS prose ISS 15 = SOURCE-CONFLICT, not used).
SHIP_TRANSPORT_RANGE = {
    "escape_pod": 0, "merchant_cruiser": 5, "scout_marauder": 0, "missile_frigate": 2, "battleship": 8,
    "corporate_flagship": 10, "colonial_transport": 7, "cargotran": 5, "merchant_freighter": 5,
    "imperial_starship": 10, "havoc_gunstar": 6, "star_master": 3, "constellation": 6, "tkhasi_orion": 3,
    "tholian_sentinel": 3, "taurean_mule": 5, "interdictor_cruiser": 20,
}


def fleet_on() -> bool:
    return FLEET_MODE == "tw2002"


# --- Ship capture (CAPTURE_MODE) ------------------------------------------------
# docs/playtests/ships/SHIP_CAPTURE.md. "legacy" = every beaten ship is destroyed, no new events or keys.

CAPTURE_MODE = "tw2002"            # "tw2002" | "legacy"
CAPTURE_RULE = "min_qty"          # cp2: "min_qty" | "never"
CAPTURE_SLACK = 0                 # extra fighters above the minimum that still capture
CAPTURE_PODLESS = "never"        # cp4: "never" | "unoccupied" | "always" (TWGS = never)
CAPTURE_FAIL_PCT = 0             # cp3 Gold-only; 0 draws no rng
CAPTURE_OVER_CAP = "destroy"     # cp6 UNVERIFIED
CAPTURE_CFS_NEEDS_CORP = True     # cp5 UNVERIFIED
CAPTURE_WHEN_SD = "capture"      # cp9: "capture" | "destroy"
CAPTURE_KEEPS_TOW = True         # cp18; dormant until TOW_MODE (slice 51)
CAPTURE_CORBOMITE = "kept"       # cp15
CAPTURE_UNMANNED_EXP = 0         # cp12 UNVERIFIED
CAPTURE_NPC = False              # cp22: Ferrengi and Feds never capture
CAPTURE_CREDITS = "as_destroy"   # cp11: BANK_MODE legacy keeps d14; tw2002 loses cash as a destroy (gb15)
CAPTURE_TELL_TOWER = True        # cp18; dormant until TOW_MODE
BOT_CAPTURE_POLICY = "incidental"  # "incidental" | "off"

# --- Corporate ships, passwords, furbing (CORPSHIP_MODE) ----------------------
# docs/playtests/ships/CORP_SHIPS_FURB.md. "legacy" is the pre-slice engine.
CORPSHIP_MODE = "tw2002"             # "tw2002" | "legacy"
CORPSHIP_SET_SCOPE = "manned"       # cs2 UNVERIFIED
CORPSHIP_SET_TURNS = 0               # cs2 UNVERIFIED
CORPSHIP_NEW_DEFAULT = "personal"    # cs3 UNVERIFIED
CORPSHIP_PERSONAL_ACCESS = "owner"   # cs5 UNVERIFIED
CORPSHIP_PASSWORD_MAX_LEN = 8        # cs6 UNVERIFIED
CORPSHIP_PASSWORD_CASE = "exact"     # cs6 UNVERIFIED
CORPSHIP_BAD_PASSWORD = "refuse_free"  # cs8 UNVERIFIED
CORPSHIP_TELL_OWNER = False          # cs8 UNVERIFIED
CORPSHIP_OWNER_ON_BOARD = "pilot"    # cs9 UNVERIFIED
CORPSHIP_BOARD_CAP = True            # cs10 UNVERIFIED
CORPSHIP_PW_ON_BOARD = "keep"        # cs11 UNVERIFIED
CORPSHIP_TOW = "corp_with_password"  # cs13 SOURCE-CONFLICT (alt "owner_only")
CORPSHIP_OWN_KILL_ALIGN = 0          # cs16 UNVERIFIED
FURB_BONUS = 3                       # cs17
FURB_DIVISOR = 3
FURB_EXCLUDED_HULLS = frozenset({"escape_pod"})  # cs20 UNVERIFIED
FURB_FERRENGI = False                # cs20 deliberate
SALVAGE_OVERKILL = "none"           # cs22 SOURCE-CONFLICT (alt "ratio")
SALVAGE_OVERKILL_RATIO = 2
SALVAGE_CARGO = "none"               # cs23 UNVERIFIED
DEFUNCT_OWNER = "defunct"            # cs24
DEFUNCT_NONCORP_CAPTURE = "destroy"  # cs26 UNVERIFIED (alt "refuse")
DEFUNCT_NET_WORTH = 0                # cs27 UNVERIFIED
CORPSHIP_ON_LEAVE = "to_ceo"         # cs28 UNVERIFIED
CORPSHIP_CAPTURE_FLAG = "captor_default"  # cs29 UNVERIFIED
CORPSHIP_NW = "owner"                # cs32 UNVERIFIED
BOT_CORPSHIP_POLICY = "off"          # "off" | "furb"
BOT_FURB_POLICY = "off"


def corpship_on() -> bool:
    """Corporate ships, passwords and furbing. Legacy keeps owner-only transport and tow."""
    return CORPSHIP_MODE == "tw2002" and fleet_on()


def capture_on() -> bool:
    """Capture needs the fleet registry. Legacy combat or a legacy fleet destroys every beaten ship."""
    return CAPTURE_MODE == "tw2002" and combat_tw2002() and fleet_on()


def transport_range(class_key: str) -> int:
    """fl9: hops the ship you are IN can beam you. Hulls not on the chart get 0."""
    return int(SHIP_TRANSPORT_RANGE.get(str(class_key), 0))


# --- Ship towing + Type 2 TransWarp (TOW_MODE) --------------------------------
# docs/playtests/ships/SHIP_TOW.md. "legacy" = exactly the post-slice-50 engine (no tow verbs, no Type 2 items,
# Extern repossesses every unmanned FedSpace ship). Unmanned tows / the Extern hold also need FLEET_MODE tw2002;
# Type 2 items and tow jumps also need SHIP_TW_MODE tw2002.
TOW_MODE = "tw2002"                 # "tw2002" | "legacy"
TOW_MANNED = "any"                  # tt4: "any" (original) | "corp_ally" | "off"
TOW_MANNED_MAX_FIGHTERS = 0         # tt4 MBBS / Iago: no tow of a trader with ship fighters
TOW_UNMANNED_FIGHTERS = "allow"     # tt3 SOURCE-CONFLICT Gypsy (TWGS) allow vs Slice (v2) refuse
TOW_TOWEE_TPW_MULT = 2              # tt6 Slice / docs wiki: tower TPW + 2 x towed TPW
TOW_EXCLUDED_HULLS = frozenset({"escape_pod"})  # tt2 UNVERIFIED
TOW_CHAIN = False                   # tt4 UNVERIFIED: a towee that is itself towing cannot be locked
TOW_ON_ATTACK = "release"           # tt11d REV 02/28/97 | "keep" (cabal Pre-Lock)
TOW_ON_RETREAT = "drop"             # tt11j UNVERIFIED | "drag"
TOW_ON_FED_TOW = "release"          # tt11i UNVERIFIED
TOW_LOCK_ON_XPORT = "keep_hull"     # tt12 Slice v2 trick, UNVERIFIED for v3 | "release"
TOW_FUSE_TOWEE = "stays"            # tt20 UNVERIFIED | "destroyed"
TOW_EXTERN_LOCK = "hold"            # tt22 cabal tips #4 | "off"
TOW_EXTERN_REQUIRE_GOOD = False     # tt22 UNVERIFIED: fedsafe = fighters <= FED_TOW_FIGHTER_LIMIT only
TOW_DOCK_VERBS = frozenset({"buy_ship", "buy_equip", "sell_ship", "remove_limpet", "apply_commission",
                            "post_reward", "claim_reward"})  # tt11c (Police HQ verbs as dock: UNVERIFIED)
SHIP_TW_TYPE2_COST = 20_000         # tt16 cabal twgs.html TEDIT sample (OldFAQ v2 80,000: SOURCE-CONFLICT, unused)
SHIP_TW_UPGRADE_COST = 9_000        # tt16 TEDIT (OldFAQ v2 40,000: unused)
SHIP_TW_TOW_ORE_PER_HOP = 6         # tt19 docs wiki / OldFAQ #1
BOT_TOW_POLICY = "extern_hold_only"  # "extern_hold_only" | "off"


def tow_on() -> bool:
    return TOW_MODE == "tw2002"


# --- Planetary Trade Agreement (PLANET_TRADE_MODE) ----------------------------
# docs/playtests/planets/PLANETARY_TRADING.md (planetary-trading-v1, slice 54). Port menu <N>: sell a same-sector
# own / own-corp planet's stock straight to a commodity port. "legacy" = the post-slice-51 engine (no verb, no
# observation key, no event, no rng draws).
PLANET_TRADE_MODE = "tw2002"            # "tw2002" | "legacy"
PLANET_TRADE_PRICING = "curve"          # pt10 SOURCE-CONFLICT: "curve" (TWGS model) | "end" | "mbbs100" (MBBS/REV 100%)
PLANET_TRADE_CURVE_STEP = 100           # pt10 UNVERIFIED: units per curve step (the TWGS percentage is unknown)
PLANET_TRADE_WHO = "owner_or_corp"      # pt4 UNVERIFIED for listing: "owner_or_corp" | "owner"
PLANET_TRADE_HAGGLE = "as_ship_sell"    # pt12 UNVERIFIED: "as_ship_sell" (HAGGLE.md sell bound on the lot) | "no_counter"
PLANET_TRADE_PAYEE = "trader"           # pt13 UNVERIFIED destination: "trader" | "planet" (treasury)
PLANET_TRADE_EXP = "as_trade"           # pt15 UNVERIFIED: "as_trade" (one ship sale of qty) | "none"
PLANET_TRADE_TWARP_COOLDOWN = 0         # pt20 UNVERIFIED: days after a planet TransWarp before it may trade
PLANET_TRADE_FEED = "public_summary"    # pt24 UNVERIFIED: "public_summary" (witnesses, like a trade) | "actor_only"
BOT_PLANET_TRADE_POLICY = "sell_surplus"  # "sell_surplus" | "off"
BOT_PLANET_TRADE_MIN_LOT = 25           # lot floor when the agreement costs the dock turn (was 500; 10-day sweep)
# bots-use-planet-trade-v1 (PLANETARY_TRADING.md "Bots"): a world under a port that buys its organics / equipment
# keeps that stock for planet_trade instead of the ship stockpile haul, and a genesis torpedo may detour up to
# BOT_PLANET_TRADE_GENESIS_HOPS known hops to land the new world under such a port (0 = deploy where it stands).
BOT_PLANET_TRADE_FREE_LOT = 10          # lot floor when the agreement costs 0 turns (visit already paid)
BOT_PLANET_TRADE_HOLD = True
BOT_PLANET_TRADE_GENESIS_HOPS = 0       # measured: a 2-hop detour cost N2 17-23% net worth on 2 of 5 seeds
BOT_PLANET_TRADE_QUOTE_PCT = 90         # bot estimate of the lot quote as % of the unit bid x qty (curve)
BOT_PLANET_TRADE_KEEP_ORE = True        # PTW "Don't sell fuel ore"


def planet_trade_on() -> bool:
    return PLANET_TRADE_MODE == "tw2002"


# --- Starport upgrade and construction (PORT_UPGRADE_MODE) -------------------
# docs/playtests/ports/PORT_UPGRADE_BUILD.md (port-upgrade-build-v1, slice 55).
# "legacy" = the engine at 4b85e21: no verbs, no construction tick, no new dump fields.
PORT_UPGRADE_MODE = "tw2002"            # "tw2002" | "legacy"
PORT_UPGRADE_SPECIAL = False            # pu2 UNVERIFIED: StarDock and class 0 are not upgradable
PORT_UPGRADE_UNIT_COST = {"fuel_ore": 250, "organics": 500, "equipment": 900}  # pu4 CONFIRMED
PORT_UPGRADE_HOLDS_PER_UNIT = 10        # pu5 CONFIRMED
PORT_UPGRADE_MAX_HOLDS = 32760          # pu6 SOURCE-CONFLICT: TWGS 32760 (alt Gold 65530)
PORT_UPGRADE_CREDITS_TO_PORT = False    # pu8 UNVERIFIED: upgrade money is a sink
PORT_UPGRADE_EXP_PER_UNIT = {"fuel_ore": 0.1, "organics": 0.2, "equipment": 0.3}  # pu9 CONFIRMED
PORT_UPGRADE_ALIGN_PER_UNIT = {"fuel_ore": 0.05, "organics": 0.1, "equipment": 0.15}
PORT_UPGRADE_FRACTION = "carry"         # pu10 UNVERIFIED: "carry" | "floor"
PORT_UPGRADE_NEEDS_PLANET = False       # pu12 SOURCE-CONFLICT: TWGS does not require a planet
PORT_UPGRADE_TURN_COST = "visit"        # pu14 UNVERIFIED: "visit" | 1
PORT_UPGRADE_BUST_BLOCKS = True         # pu15 UNVERIFIED
PORT_BUILD_NEEDS_PLANET = True          # pu17 SOURCE-CONFLICT: EIS requires a planet
PORT_BUILD_PLANET_WHO = "owner_or_corp"  # pu17 UNVERIFIED: "owner_or_corp" | "owner"
PORT_BUILD_ALLOW_SSS = True             # pu18 DERIVED: SSS exists only for built ports
PORT_BUILD_COST = {                     # pu19 UNVERIFIED (Iago)
    "BBS": 39250, "BSB": 41500, "SBB": 48000, "SSB": 37500,
    "SBS": 34000, "BSS": 32500, "SSS": 30000, "BBB": 50000,
}
PORT_BUILD_DAYS = {                     # pu20 CONFIRMED
    "BBS": 6, "BSB": 7, "SBB": 8, "SSB": 5, "SBS": 4, "BSS": 3, "SSS": 2, "BBB": 10,
}
PORT_BUILD_DAILY_MATERIALS = {          # pu21 UNVERIFIED (Iago): fuel_ore, organics, equipment
    "BBS": (120, 120, 60), "BSB": (140, 70, 140), "SBB": (80, 160, 160), "SSB": (50, 50, 100),
    "SBS": (40, 80, 40), "BSS": (60, 30, 30), "SSS": (20, 20, 20), "BBB": (200, 200, 200),
}
PORT_BUILD_STALL = "pause"              # pu22 UNVERIFIED
PORT_BUILD_DOCKS_OPEN = False           # pu23 UNVERIFIED
PORT_BUILD_START_PRODUCTIVITY = 10      # pu24 IAGO: 100 units/day
PORT_BUILD_START_STOCK_PCT = 0          # pu24 UNVERIFIED
PORT_BUILD_MCIC = "home"                # pu24 UNVERIFIED: sell 50 / buy -60
PORT_BUILD_REWARD = {                   # pu25 CONFIRMED values (exp, align)
    "BBS": (25, 12), "BSB": (29, 14), "SBB": (34, 16), "SSB": (20, 10),
    "SBS": (16, 8), "BSS": (12, 6), "SSS": (7, 4), "BBB": (45, 20),
}
PORT_BUILD_REWARD_WHEN = "complete"     # pu25 UNVERIFIED: "complete" | "order"
PORT_BUILD_INITIAL_BUILT_PCT = 95       # pu26 DERIVED
PORT_BUILD_RADIATION_DAYS = 1           # pu27 SOURCE-CONFLICT: TWGS 1 (alt IAGO 14)
PORT_BUILD_FEDSPACE = False             # pu27 UNVERIFIED
PORT_BUILD_NAME_MAX = 30
BOT_PORT_UPGRADE_POLICY = "planet_room"  # pu28 DERIVED: "planet_room" | "off"
BOT_PORT_UPGRADE_MAX_UNITS = 50
BOT_PORT_UPGRADE_RESERVE = 50_000
BOT_PORT_UPGRADE_PAYBACK_DAYS = 5
# QC slice 55 DERIVED: the planet_room test above never fired in 10-day matches (planet lots <= ~100 vs port
# room >= ~1,750), so a seat holding this many credits gives the buy port over its stocked planet one starter
# upgrade of this many units, once per port and commodity (seed 250925: one seat, 2,500cr). 0 = off.
BOT_PORT_UPGRADE_STARTER_UNITS = 5
BOT_PORT_UPGRADE_STARTER_CREDITS = 300_000
BOT_PORT_BUILD_POLICY = "off"           # pu29 DERIVED: "off" | "near_planet"


def port_upgrade_on() -> bool:
    return PORT_UPGRADE_MODE == "tw2002"


# llm-new-day-goals (fullgame2 P7): an LLM seat whose own goals were written on an earlier day sees a
# NEW DAY line at the top of its action_hint until it writes fresh short/medium goals. Agent-side only
# (LLMAgent); observations, format_observation and the system prompt are unchanged, so no digest moves.
LLM_NEW_DAY_GOAL_NOTICE = True

# llm-route-autopilot (fullgame3 P7): the LLM prompt lists `plot_course` but never its `execute` arg, and
# _compact_legal drops params, so an LLM seat 10 hops from StarDock hand-picked ~40 single warps over
# 2+ days. With this on, an LLM seat in the starter hull that can afford an upgrade away from StarDock,
# or one ping-ponging on single warps, sees an AUTOPILOT line naming plot_course execute=true.
# Agent-side only (LLMAgent): observations, format_observation and the system prompt are unchanged.
LLM_ROUTE_NOTICE = True

# --- Galactic Bank and the good-trader tax (BANK_MODE) ------------------------
# docs/playtests/fedspace/GALACTIC_BANK_TAX.md (galactic-bank-tax-v1).
# "legacy" = the engine at 6b13b55: no account, no tax, credits stay on a lost ship.
BANK_MODE = "tw2002"                    # "tw2002" | "legacy"
BANK_MAX_BALANCE = 500_000              # gb4 SOURCE-CONFLICT: TWGS 500000 (alt Bible 100000)
BANK_OVERCAP = "refuse"                 # gb5 UNVERIFIED: "refuse" | "clip"
BANK_WITHDRAW_FEE = 0                   # gb7 UNVERIFIED
BANK_TRANSFER_SOURCE = "cash"           # gb8 SOURCE-CONFLICT: "cash" (EIS) | "account" (Bible)
BANK_TRANSFER_CORPMATES = True          # gb9 UNVERIFIED
BANK_TRANSFER_RESPECTS_CAP = True       # gb9 UNVERIFIED
BANK_SHOW_RECIPIENT_ROOM = True         # UNVERIFIED: transfer list shows room (alt False hides it)
BANK_INTEREST_PCT = 0                   # gb10 CONFIRMED
BANK_TURN_COST = 0                      # gb11 UNVERIFIED
BANK_IN_NET_WORTH = True                # gb26 DERIVED
BANK_BALANCE_VIEW = "always"            # gb27 DERIVED: "always" | "stardock"
DEATH_CREDITS_ON_HAND = "lost"          # gb13 UNVERIFIED: "lost" | "kept"
DEATH_CREDITS_TO_KILLER = "player_ship_kill"  # gb14
DEATH_CREDITS_RECOVER_PCT = 100         # gb14 UNVERIFIED
DEATH_CREDITS_FERRENGI = "to_ferrengi"  # gb14 UNVERIFIED: "to_ferrengi" | "sink"
TAX_MIN_ALIGNMENT = 0                   # gb17 SOURCE-CONFLICT: TWGS 0 (alt positive-only 1)
TAX_THRESHOLD = 100_000                 # gb18 SOURCE-CONFLICT: TWGS 100000 (alt Bible 50000)
TAX_RATE_PCT = 5                        # gb19 SOURCE-CONFLICT: TWGS 5 (alt Bible 10)
TAX_ROUNDING = "floor"                  # gb19 UNVERIFIED
TAX_CREDITS_PER_ALIGN = 1500            # gb21 CONFIRMED
TAX_EXP = 0                             # gb21 UNVERIFIED
TAX_ALIGN_AWARD_MAX = 31_999            # gb22 SOURCE-CONFLICT
TAX_ALIGN_OVERFLOW = "none"             # gb22: "none" | "clamp"
TAX_WHEN = "day_tick"                   # gb23 DERIVED
TAX_TO = "sink"                         # gb24 CONFIRMED
BOTS_BANK_MODE = "tw2002"              # bb1: "tw2002" | "legacy". Unread until the bot hooks land.
BOT_BANK_POLICY = "reserve"            # bb1: "reserve" | "tax_and_death" (the slice 56 bot) | "off"
BOT_BANK_FLOAT = 30_000                 # legacy keep. The new away reserve does not read this.
BOT_BANK_DETOUR_HOPS = 0                # legacy. Tw2002 detours use BOT_BANK_DETOUR_HOPS_ON.
BOT_BANK_DETOUR_HOPS_ON = 3             # bb11
BOT_BANK_DETOUR_CASH = 150_000          # bb11
BOT_BANK_DETOURS_PER_DAY = 1            # bb11
BOT_BANK_TRANSFER = False               # gb31 DERIVED
BOT_BANK_MAX_WITHDRAWS_PER_VISIT = 3    # bb3
BOT_BANK_MIN_FLOAT = 5_000              # bb5
BOT_BANK_CAPITAL_PER_HOLD = 250         # bb5
BOT_BANK_TOLL_BUDGET = 2_000            # bb5
BOT_BANK_AWAY_CAP = 150_000             # bb5
BOT_BANK_NEST_EGG_STAGES = ((0, 10_000), (150_000, 50_000), (500_000, 100_000))  # bb6
BOT_BANK_EOD_TURNS = 5                  # bb7
BOT_BANK_DAY1_DEPOSIT = 10_000          # bb8
BOT_BANK_RISK_DAYS = 3                  # bb9
BOT_BANK_RISK_HOPS = 3                  # bb9
BOT_BANK_RISK_FIGHTERS = 50             # bb9
BOT_BANK_MAX_VERBS_PER_DAY = 8          # bb18
BOT_BANK_BROKE_LINE = 10_000            # bb22
BOT_TREASURY_POLICY = "overflow"        # bb12: "overflow" | "spare" | "off"
BOT_BANK_H = True                       # bb14: H banks under tw2002. Legacy H never reads this.
BOT_BANK_H_KEEP = 10_000                # bb14 floor. Holds raise it by BOT_BANK_CAPITAL_PER_HOLD.


def bank_on() -> bool:
    return BANK_MODE == "tw2002"


def bots_bank_on() -> bool:
    return BOTS_BANK_MODE == "tw2002" and bank_on()


# --- Lost Trader's Tavern and the Underground (TAVERN_MODE) ------------------
# docs/playtests/fedspace/STARDOCK_TAVERN.md. Unread until the handlers land.
TAVERN_MODE = "tw2002"                  # tv1: "tw2002" | "legacy"
TAVERN_TURN_COST = 0                    # tv2 UNVERIFIED
TAVERN_ANNOUNCE_COST = 100              # tv3 CONFIRMED
TAVERN_TEXT_MAX = 160                   # tv3 UNVERIFIED
TAVERN_ANNOUNCE_SIGNED = True           # tv3 UNVERIFIED
TAVERN_TALK_COST = 0                    # tv4 UNVERIFIED
TAVERN_CONVERSATION_KEEP = 20           # tv4 OURS
TAVERN_CONVERSATION_SHOW = 10           # tv22 OURS
TAVERN_GRAFFITI_COST = 0                # tv5 UNVERIFIED
TAVERN_WALL_KEEP = 10                   # tv5 OURS
TAVERN_WALL_SHOW = 5                    # tv22 OURS
TAVERN_DRINK_COST = 20                  # tv6 UNVERIFIED
TAVERN_FOOD_COST = 20                   # tv6 UNVERIFIED
TAVERN_PRICE_SCALING = "flat"           # tv6 UNVERIFIED
GRIMY_TOPICS = ("trader", "underground", "mafia", "tricron")  # tv7
GRIMY_TRACE_COST = 3_000                # tv8 UNVERIFIED
GRIMY_TRACE_PORTS = 1                   # tv8 SOURCE-CONFLICT
GRIMY_TRACE_PICK = "hashed"             # tv8 OURS
GRIMY_CHARGE_ON_MISS = False            # tv8 UNVERIFIED
GRIMY_TRACE_LIES = False                # tv8 UNVERIFIED
GRIMY_DOCK_LOG_MAX = 10                 # tv9 UNVERIFIED
GRIMY_DOCK_ACTIONS = ("trade", "rob", "steal", "planet_trade", "port_upgrade")  # tv9
GRIMY_PASSWORD_COST = 2_000             # tv10 UNVERIFIED
GRIMY_CURSES_PER_DAY = 1                # tv13 SOURCE-CONFLICT
GRIMY_CURSE_TURNS = 1                   # tv13 UNVERIFIED
GRIMY_RUDE_MARKUP_PCT = 0               # tv13 UNVERIFIED
UG_PASSWORD_SOURCE = "seeded"           # tv10 OURS
UG_MAX_ALIGNMENT = 199                  # tv14 SOURCE-CONFLICT
UG_PASSWORD_MATCH = "loose"             # tv14 UNVERIFIED
UG_VERB_VISIBILITY = "known"            # tv14 OURS
UG_MUG_AT = 4                           # tv15 SOURCE-CONFLICT
UG_EXP_HALVE_AT = 5                     # tv15 SOURCE-CONFLICT
UG_MURDER_AT = 6                        # tv15 SOURCE-CONFLICT
UG_MURDER_POD = False                   # tv15 UNVERIFIED
UG_MURDER_COUNTS_DEATH = True           # tv15 UNVERIFIED
UG_CONTRACT_MIN = 1_000                 # tv16 UNVERIFIED
UG_CREDITS_PER_ALIGN = 250              # tv16 CONFIRMED
UG_CONTRACT_SELF = True                 # tv16 CONFIRMED
UG_CONTRACT_PAYOUT_ON = "ship_destroyed"  # tv17 UNVERIFIED
UG_CONTRACT_ON_ELIMINATION = "sink"     # tv17 UNVERIFIED
UG_SHOW_CONTRACTS = "totals"            # tv18 UNVERIFIED
UG_NAME_CHANGE = False                  # tv19
TAVERN_TRICRON = "off"                  # tv20
BOT_TAVERN_POLICY = "off"               # tv26


def tavern_on() -> bool:
    return TAVERN_MODE == "tw2002"


# --- Bots use planetary warfare (BOTS_WAR_MODE) ------------------------------
# docs/playtests/bots/BOTS_USE_PLANET_WARFARE.md. Unread until the war brain is wired.
BOTS_WAR_MODE = "tw2002"                 # bw1: "tw2002" | "legacy"
BOT_WAR_POLICY = "full"                  # D1: full | defend | off
BOT_WAR_MAP_MAX = 64                     # bw2
BOT_WAR_INTEL_STALE_DAYS = 3             # bw3
BOT_WAR_INTEL_STALE_PAD_PCT = 50         # bw3
BOT_WAR_HOME_MINES = 10                  # bw4
BOT_WAR_PICKET_MIN = 10                  # bw5
BOT_WAR_WALL_PCT = 20                    # bw5
BOT_WAR_KEEP_ABOARD_PCT = 40             # bw5
BOT_WAR_OFFENSIVE_AT_ENTRANCE = True     # bw5
BOT_WAR_TRAVEL_PICKETS = False           # D2
BOT_WAR_PLANET_FIGHTERS_BY_LEVEL = {1: 500, 2: 2_000, 3: 5_000, 4: 10_000, 5: 20_000, 6: 30_000}
BOT_WAR_PLANET_SHIELDS_BY_LEVEL = {1: 0, 2: 0, 3: 50, 4: 200, 5: 500, 6: 1_000}
BOT_WAR_DEFENCE_BUDGET_PCT = 25          # bw7
BOT_WAR_REACTION_PCT = 20                # bw8
BOT_WAR_QUASAR_SECTOR_PCT = 30           # bw9
BOT_WAR_QUASAR_ATM_PCT = 60              # bw9
BOT_WAR_QUASAR_ORE_FLOOR = 2_000         # bw9
BOT_WAR_SIEGE_MARGIN_PCT = 25            # bw17
BOT_WAR_RESERVE_TURNS = 20               # bw17


def bots_war_on() -> bool:
    return BOTS_WAR_MODE == "tw2002"


# --- Corporations (CORP_MODE) -------------------------------------------------
# docs/playtests/corps/CORP_RULES.md. "legacy" is the engine at 57dec11.
CORP_MODE = "tw2002"                      # "tw2002" | "legacy"
CORP_CREATE_COST = 0                      # cr2 UNVERIFIED (alt 500_000 = CORP_FORMATION_COST)
CORP_TURN_COST = 0                        # cr2 UNVERIFIED
CORP_NEW_PASSWORD = ""                    # cr3 UNVERIFIED: blank means closed
CORP_APPROVER = "member"                  # cr4 SOURCE-CONFLICT: "member" | "ceo"
CORP_BREAKIN_PER_DAY = 1                  # cr6
CORP_BREAKIN_ALIGN_LOSS = 0               # cr6 UNVERIFIED
CORP_BREAKIN_TELL_CEO = False             # cr6 UNVERIFIED
CORP_MAX_MEMBERS = 5                      # cr7 CONFIRMED
CORP_ALIGNMENT_RULE = "mixed"             # cr8 SOURCE-CONFLICT: "mixed" | "same_side"
CORP_SIDE_OF_ZERO = "good"                # cr8 UNVERIFIED
MIXED_CORP_EXP_RULE = "highest_good"      # cr9 SOURCE-CONFLICT: "highest_good" | "least_extreme"
MIXED_CORP_EXP_DIVISOR = 4                # cr9
MIXED_CORP_EXP_FLOOR = 1                  # cr9 UNVERIFIED
CORP_LEAVER_PLANETS = "corp_keeps"        # cr10: "corp_keeps" | "leaver_keeps"
CORP_DISBAND_MINES = "rogue"              # cr12 UNVERIFIED: "rogue" | "removed"
CORP_DISBAND_PLANETS = "owner_keeps"      # cr12: "owner_keeps" | "v306"
ROGUE_OWNER_ID = "rogue"                  # cr13
ROGUE_KEEP_MODE = True                    # cr13 UNVERIFIED
CORP_TRANSFER_LANDED = "refuse"           # cr16 UNVERIFIED
CORP_TRANSFER_TAKE = True                 # cr16 CONFIRMED
CORP_TRANSFER_MINE_KINDS = ("armid", "limpet")  # cr16 UNVERIFIED
CORP_DEPLOY_DEFAULT = "corporate"         # cr17 UNVERIFIED
ALLIANCE_DEPLOY_FRIENDLY = "all"          # cr18: "all" | "corporate" | "none"
CORP_RECLAIM_BY = "member"                # cr19 UNVERIFIED
CORP_TOLL_TO = "collector"                # cr20 UNVERIFIED
CORP_RANK_EXP = "sum"                     # cr24 UNVERIFIED
CORP_RANK_ALIGN = "sum"                   # cr24 UNVERIFIED
CORP_MEMO_SENDERS = "member"              # cr25 SOURCE-CONFLICT: "member" | "ceo"
CORP_TREASURY = "off"                     # cr26: "off" | "ours"
BOT_CORP_POLICY = "off"                   # bc1: "off" | "pair" | "team". The pair brain turns the default to pair.
CORP_BOTS_MODE = "tw2002"                 # bc1: "tw2002" | "legacy"
BOT_CORP_TEAM_SIZE = 3                    # bc1
BOT_CORP_PARTNERS = "consecutive"         # bc2
BOT_CORP_PASSWORD_LEN = 6                 # bc4
BOT_CORP_INVITE_RETRIES = 3               # bc5
BOT_CORP_ACCEPT_INVITES = "partner_only"  # bc6: "partner_only" | "any_bot" | "anyone"
BOT_CORP_MIXED_POLICY = "allow"           # bc7: "allow" | "same_side"
BOT_CORP_MIXED_MAX_PENALTY = 400          # bc7
BOT_CORP_SHARED_HOME = True               # bc10
BOT_CORP_SINGLE_BUILDER = True            # bc11
BOT_CORP_TRANSFER_PAD = 1_000             # bc12
BOT_CORP_MIN_TRANSFER = 5_000             # bc12
BOT_CORP_TAX_SHIELD = True                # bc13
BOT_CORP_KEEP_FIGHTERS_PCT = 30           # bc14
BOT_CORP_MEET_MAX_HOPS = 3                # bc15
BOT_CORP_MEET_MAX_TURNS = 30              # bc15
BOT_CORP_EXPLORER = "ceo"                 # bc16
BOT_CORP_FLAGSHIP = "ceo"                 # bc20
BOT_CORP_REFOUND = False                  # bc19
BOT_CORP_MAX_FREE_ACTIONS_PER_DAY = 6     # bc22
CFS_CEO_RULE = "purchase"                 # bc24 SOURCE-CONFLICT: "purchase" | "use"
CFS_HOLDER_MAY_JOIN = False               # bc25
CFS_HOLDER_MAY_CREATE = True              # bc25 UNVERIFIED
CFS_JOIN_CHECK = "flown"                  # bc25 UNVERIFIED: "flown" | "owned"


def corp_rules_on() -> bool:
    return CORP_MODE == "tw2002"


def corp_bots_on() -> bool:
    return CORP_BOTS_MODE == "tw2002" and corp_rules_on()


def bot_corp_policy() -> str:
    """bc1: CORP_MODE legacy and CORP_BOTS_MODE legacy both read the policy as off."""
    if not corp_bots_on():
        return "off"
    return BOT_CORP_POLICY


# --- Alien traders (ALIEN_MODE) ----------------------------------------------
# docs/playtests/npc/ALIEN_TRADERS.md. "legacy" is the engine at 5695588.
ALIEN_MODE = "tw2002"                     # "tw2002" | "legacy"
ALIEN_SOURCE = "classic"                  # al1 SOURCE-CONFLICT: "classic" | "off"
ALIEN_POPULATION_PER_1000 = 40            # al1 UNVERIFIED
ALIEN_NAMES = (
    "Vorn", "Kess", "Jax", "Ryn", "Sola", "Pek", "Nim", "Quill",
    "Tarn", "Bex", "Loro", "Hess", "Mira", "Cade", "Yew", "Orl",
)                                         # al2 UNVERIFIED flavour
ALIEN_START = "scatter"                   # al3 UNVERIFIED
ALIEN_RESPAWN_DELAY_DAYS = 1              # al4 UNVERIFIED
ALIEN_GOOD_PCT = 50                       # al5 UNVERIFIED
ALIEN_ALIGN_MIN = 50
ALIEN_ALIGN_MAX = 500
ALIEN_HULLS_BY_DAY = (
    (0, ("merchant_cruiser", "scout_marauder", "cargotran")),
    (30, ("merchant_cruiser", "scout_marauder", "cargotran",
          "missile_frigate", "merchant_freighter", "colonial_transport")),
    (90, ("merchant_cruiser", "scout_marauder", "cargotran",
          "missile_frigate", "merchant_freighter", "colonial_transport",
          "battleship", "havoc_gunstar", "constellation")),
)                                         # al6 UNVERIFIED
ALIEN_FIGHTERS_BASE = 300
ALIEN_FIGHTERS_PER_DAY = 20
ALIEN_SHIELDS_BASE = 50
ALIEN_SHIELDS_PER_DAY = 5
ALIEN_EXP_START = 100
ALIEN_EXP_PER_DAY = 10
ALIEN_EXP_CAP = 5000
ALIEN_CREDITS_MIN = 1000
ALIEN_CREDITS_START = 10_000
ALIEN_CREDITS_PER_DAY = 250
ALIEN_CREDITS_CAP = 100_000
ALIEN_CORBOMITE_MAX = 5
ALIEN_HOPS_PER_DAY = 3                    # al7 UNVERIFIED
ALIEN_MINE_KILL_REWARD = False            # al8 UNVERIFIED
ALIEN_LIMPETS = False
ALIEN_AGGRESSION = "never"                # al9 UNVERIFIED; any other value is refused below
ALIEN_FLEE_RULE = "player"                # al13 SOURCE-CONFLICT: "player" | "always"
ALIEN_INTERDICTED = True                  # al13 UNVERIFIED
ALIEN_KILL_EXP_RULE = "bible"             # al15 SOURCE-CONFLICT: "bible" | "player"
ALIEN_KILL_ALIGN_SHARE = 0.5              # al16 UNVERIFIED
ALIEN_LOOT_CREDITS = True                 # al17 UNVERIFIED
ALIEN_BOUNTY = 0
ALIEN_CAPTURE = True                      # al19
ALIEN_PORT_TRADE = False                  # al20 UNVERIFIED
ALIEN_NPC_FIGHT = False                   # al22 UNVERIFIED
ALIEN_REGEN = False                       # al12
BOT_ALIEN_POLICY = "ignore"               # al29: "ignore" | "align_hunt"
BOT_ALIEN_MARGIN = 1.5

if ALIEN_AGGRESSION != "never":
    raise RuntimeError("ALIEN_AGGRESSION only supports 'never'")


def alien_on() -> bool:
    return ALIEN_MODE == "tw2002" and ALIEN_SOURCE == "classic" and combat_tw2002() and rank_tw2002()


# --- LLM rules text (LLM_PARITY_MODE) ----------------------------------------
# docs/playtests/bots/LLM_RULES_PARITY.md. "legacy" is the prompt at c35b9b3.
LLM_PARITY_MODE = "tw2002"                # lp1: "tw2002" | "legacy"
LLM_HINT_CORP_MIN_CREDITS = 50_000        # lp5 OURS
LLM_LEGAL_HINTS = "args"                  # lp14: "args" | "off"
LLM_LEGAL_HINT_MAX_CHOICES = 6            # lp14
LLM_LEGAL_HINT_KEYS: tuple[str, ...] = (
    "target", "ship_class", "item", "commodity", "direction", "ticker",
    "corps", "partners", "planet_id", "qty", "units", "amount", "mode",
    "kind", "port_class", "to_player", "side", "ownership", "execute",
)                                         # lp14: never password
LLM_PROMPT_GROWTH_MAX_PCT = 8             # lp18
LLM_OBS_GROWTH_MAX_PCT = 10               # lp18
LLM_UNDOCUMENTED_VERBS: tuple[str, ...] = ()  # lp13


def llm_parity_on() -> bool:
    return LLM_PARITY_MODE == "tw2002"


# Agent-side only. Legacy leaves the prompt, the stage hint, and the turn notices unchanged.
LLM_SELL_FIRST = True                     # sell-at-a-profit notice and the cargo loop line
LLM_PLANET_NUDGE_MODE = "tw2002"          # "tw2002" | "legacy"
LLM_PLANET_NUDGE_CREDITS = 50_000


def planet_nudge_on() -> bool:
    return LLM_PLANET_NUDGE_MODE == "tw2002"

