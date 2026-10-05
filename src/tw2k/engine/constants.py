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
