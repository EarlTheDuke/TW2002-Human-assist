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
# "legacy": a fighter drop in FedSpace is refused and the ship is unchanged.
# "live": the drop is annihilated. The ship loses 10 percent of its fighters
# and 10 percent of its holds. A half rounds up, so 35 holds lose 4.
# The fighters you tried to drop do not stay in the sector and are not taken
# off on top of that 10 percent. 30 fighters became 27. 20 fighters became 18.
FEDSPACE_DEPLOY_MODE = "legacy"  # "legacy" | "live"


def fedspace_deploy_live() -> bool:
    """True when a FedSpace fighter drop is annihilated instead of refused."""
    return FEDSPACE_DEPLOY_MODE == "live" or tw2002_live_profile() or v311_profile()


def fedspace_tenth_loss(count: int) -> int:
    """Ten percent of a count, with a half rounded up."""
    number = max(0, int(count))
    return (number * 10 + 50) // 100

PORT_DEFAULT_MAX_STOCK = 3000
PORT_REGEN_PER_DAY = 0.05  # standard 5% per day. A sample game used 1%. See TURNS_REGEN.md.
# New ports open with this fraction of max stock. The changelog says 0%.
PORT_START_STOCK_PERCENT = 0
# "legacy": open at PORT_START_STOCK_PERCENT and regen productivity * PORT_REGEN_PER_DAY.
# "full": open at 100% of max and regen that same 5% of max per day (live TWGS Big Bang).
# Default stays legacy so existing digests and the pin do not move. Flip this on purpose.
PORT_OPEN_STOCK_MODE = "legacy"  # "legacy" | "full"


def port_open_full() -> bool:
    """True when ports open full and each day puts back 5% of max stock."""
    return PORT_OPEN_STOCK_MODE == "full"


# "legacy": class 1 is BSS, class 6 is BBS, and StarDock (class 8) trades nothing.
# "live": v3.34b letters for those two, and the sector-1 StarDock buys all three.
# Class 7 stays BBB. Live class 7 is SSS and live class 8 is a normal BBB port,
# but class 8 is the StarDock id until Ben moves StarDock off sector 1.
# Class 0 still trades no commodities. Sol does not either. Class 9 stays the
# built SSS port. Default stays legacy so the pin and the digests do not move.
PORT_CLASS_MAP_MODE = "legacy"  # "legacy" | "live"

_PORT_CLASS_TRADES_LIVE: dict[int, tuple[bool | None, bool | None, bool | None]] = {
    0: (None, None, None),
    1: (True, True, False),   # BBS
    2: (True, False, True),   # BSB
    3: (False, True, True),   # SBB
    4: (False, False, True),  # SSB
    5: (False, True, False),  # SBS, not seen live
    6: (True, False, False),  # BSS
    7: (True, True, True),    # BBB kept; see the plan
    8: (True, True, True),    # StarDock buys fuel, organics, and equipment
    9: (False, False, False),  # built SSS
}


def port_class_live() -> bool:
    """True when class 1/6 letters match v3.34b and StarDock buys goods."""
    return PORT_CLASS_MAP_MODE == "live" or tw2002_live_profile() or v311_profile()


def port_class_trades(class_id: int) -> tuple[bool | None, bool | None, bool | None]:
    """Buy/sell book for a class number. True means the port buys from the player."""
    cid = int(class_id)
    table = _PORT_CLASS_TRADES_LIVE if port_class_live() else PORT_CLASS_TRADES
    # NOTE 98 TRD-c. Live class 7 is SSS. Class 8 stays the StarDock id, so a
    # generated BBB cannot take that number. The dock's buy-all book is already
    # the BBB tuple. Legacy numbers are unchanged while the fix is off.
    if port_class_number_fix() and port_class_live() and cid == 7:
        return (False, False, False)
    return table.get(cid, (None, None, None))
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

# Cabal haggling.html counter percent, in tenths (1494 means 149.4%).
# Fuel prints -46 twice and skips -47. The unit prices step by 0.2, so the
# first of those two rows is the missing -47. Every other MCIC is the printed label.
HAGGLE_COUNTER_TABLE: dict[str, tuple[tuple[int, int], ...]] = {
    "fuel_ore": (
        (-90, 1494),
        (-89, 1488),
        (-88, 1482),
        (-87, 1476),
        (-86, 1470),
        (-85, 1464),
        (-84, 1458),
        (-83, 1452),
        (-82, 1446),
        (-81, 1440),
        (-80, 1434),
        (-79, 1429),
        (-78, 1423),
        (-77, 1417),
        (-76, 1411),
        (-75, 1405),
        (-74, 1399),
        (-73, 1393),
        (-72, 1387),
        (-71, 1381),
        (-70, 1375),
        (-69, 1369),
        (-68, 1363),
        (-67, 1357),
        (-66, 1351),
        (-65, 1345),
        (-64, 1342),
        (-63, 1336),
        (-62, 1330),
        (-61, 1324),
        (-60, 1318),
        (-59, 1312),
        (-58, 1306),
        (-57, 1300),
        (-56, 1294),
        (-55, 1291),
        (-54, 1285),
        (-53, 1279),
        (-52, 1273),
        (-51, 1267),
        (-50, 1261),
        (-49, 1255),
        (-48, 1249),
        (-47, 1246),
        (-46, 1240),
        (-45, 1234),
        (-44, 1228),
        (-43, 1222),
        (-42, 1219),
        (-41, 1209),
        (-40, 1208),
    ),
    "organics": (
        (-75, 1405),
        (-74, 1399),
        (-73, 1393),
        (-72, 1387),
        (-71, 1381),
        (-70, 1375),
        (-69, 1369),
        (-68, 1363),
        (-67, 1357),
        (-66, 1351),
        (-65, 1345),
        (-64, 1339),
        (-63, 1336),
        (-62, 1330),
        (-61, 1324),
        (-60, 1318),
        (-59, 1312),
        (-58, 1306),
        (-57, 1300),
        (-56, 1294),
        (-55, 1291),
        (-54, 1285),
        (-53, 1279),
        (-52, 1273),
        (-51, 1267),
        (-50, 1261),
        (-49, 1255),
        (-48, 1252),
        (-47, 1246),
        (-46, 1236),
        (-45, 1233),
        (-44, 1227),
        (-43, 1224),
        (-42, 1214),
        (-41, 1213),
        (-40, 1203),
        (-39, 1200),
        (-38, 1194),
        (-37, 1191),
        (-36, 1181),
        (-35, 1178),
        (-34, 1172),
        (-33, 1166),
        (-32, 1160),
        (-31, 1157),
        (-30, 1154),
    ),
    "equipment": (
        (-65, 1347),
        (-64, 1341),
        (-63, 1336),
        (-62, 1330),
        (-61, 1324),
        (-60, 1319),
        (-59, 1313),
        (-58, 1307),
        (-57, 1302),
        (-56, 1296),
        (-55, 1291),
        (-54, 1285),
        (-53, 1279),
        (-52, 1274),
        (-51, 1268),
        (-50, 1262),
        (-49, 1254),
        (-48, 1247),
        (-47, 1246),
        (-46, 1241),
        (-45, 1235),
        (-44, 1229),
        (-43, 1224),
        (-42, 1218),
        (-41, 1213),
        (-40, 1208),
        (-39, 1201),
        (-38, 1196),
        (-37, 1190),
        (-36, 1185),
        (-35, 1180),
        (-34, 1174),
        (-33, 1169),
        (-32, 1164),
        (-31, 1158),
        (-30, 1152),
        (-29, 1149),
        (-28, 1144),
        (-27, 1136),
        (-26, 1132),
        (-25, 1126),
        (-24, 1122),
        (-23, 1117),
        (-22, 1110),
        (-21, 1105),
        (-20, 1102),
    ),
}

def haggle_table_tenths(commodity: str | None, mcic: int) -> int | None:
    """Cabal counter percent in tenths, or None when that product has no printed row.

    Between two printed MCICs the page says to interpolate. Outside the printed
    span the straight 110 to 149 line still applies.
    """
    token = str(getattr(commodity, "value", commodity) or "")
    rows = HAGGLE_COUNTER_TABLE.get(token)
    if not rows:
        return None
    target = int(mcic)
    if target < rows[0][0] or target > rows[-1][0]:
        return None
    for index, (mark, tenths) in enumerate(rows):
        if mark == target:
            return int(tenths)
        if mark > target:
            left_mark, left = rows[index - 1]
            span = mark - left_mark
            pos = target - left_mark
            return int(round(left + (tenths - left) * pos / span))
    return None



# "legacy": the hidden room is 110% to 149% of the first offer, by MCIC.
# "live": a one-shot counter is taken only inside the band seen on TWGS
# v3.34b. A sell may ask up to +8%. A buy may bid down to -8% (the same
# 108 figure, folded: 200 - 108 = 92). A sell past about 130% is the wild
# bid that ended a trade. Counter rounds between the band and that wild
# bid were not built. The exact edge was not probed, so this is that
# written band, not a fitted formula. A failed haggle still costs
# PORT_HAGGLE_FAIL_TURNS. Default stays legacy so the pin and the digests
# do not move.
HAGGLE_WINDOW_MODE = "legacy"  # "legacy" | "live"
PORT_HAGGLE_LIVE_ROOM_PCT = 108
PORT_HAGGLE_LIVE_END_PCT = 130


def haggle_window_live() -> bool:
    """True when a counter has to sit inside the live +8% / -8% band."""
    return HAGGLE_WINDOW_MODE == "live" or tw2002_live_profile() or v311_profile()


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

# starting-package-v1. "legacy" is today's opening: 20,000 credits, 20 fighters,
# 1,000 turns, no home planet, and a full turn refill at each new day.
# "live" is the TWGS Big Bang opening that was played: 300 credits, 30 fighters,
# 250 turns, a free class M planet, and turns coming back by the hour instead
# of a midnight refill to full. Default stays legacy so digests do not move.
STARTING_PACKAGE_MODE = "legacy"  # "legacy" | "live"
LIVE_STARTING_CREDITS = 300
LIVE_STARTING_FIGHTERS = 30
LIVE_STARTING_TURNS = 250
LIVE_STARTING_COLONISTS = 191_000
# 250 turns spread over a day. Live play measured about 10 to 11 an hour.
LIVE_TURN_RECOVERY_NUM = 250
LIVE_TURN_RECOVERY_DEN = 24 * 3600


def starting_package_live() -> bool:
    """True when a new game uses the TWGS opening pocket."""
    return STARTING_PACKAGE_MODE == "live" or tw2002_live_profile() or v311_profile()


# NOTE 65 item 0. None keeps today's opening. A number is the credits every
# seat starts with (human and bot, no slot skew). 0 to 10,000,000.
CREDITS_OVERRIDE_MAX = 10_000_000


def parse_credits_override(value: object) -> int | None:
    """Per-game opening credits, or None for the original package."""
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, bool):
        raise ValueError("starting credits must be a whole number")
    try:
        number = int(str(value).strip().replace(",", "").replace("_", ""))
    except (TypeError, ValueError):
        raise ValueError("starting credits must be a whole number") from None
    if not 0 <= number <= CREDITS_OVERRIDE_MAX:
        raise ValueError(f"starting credits must be between 0 and {CREDITS_OVERRIDE_MAX}")
    return number


def opening_original_credits() -> int:
    """What a seat starts with when the game did not pick an override."""
    return LIVE_STARTING_CREDITS if starting_package_live() else STARTING_CREDITS


def starting_credits_line(override: int | None, original: int) -> str:
    """Game-info sentence. An override is a test setting."""
    if override is None:
        return f"Starting credits: {int(original):,} (original)"
    return f"Starting credits: {int(override):,} (test setting)"


# NOTE 93. None keeps today's pocket. A number is the turns every seat gets.
# 50 to 5,000. The lobby's Original choice does not set this.
TURNS_OVERRIDE_MIN = 50
TURNS_OVERRIDE_MAX = 5_000


def parse_turns_override(value: object) -> int | None:
    """Per-game turns per day, or None for the original pocket."""
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, bool):
        raise ValueError("turns per day must be a whole number")
    try:
        number = int(str(value).strip().replace(",", "").replace("_", ""))
    except (TypeError, ValueError):
        raise ValueError("turns per day must be a whole number") from None
    if not TURNS_OVERRIDE_MIN <= number <= TURNS_OVERRIDE_MAX:
        raise ValueError(
            f"turns per day must be between {TURNS_OVERRIDE_MIN} and {TURNS_OVERRIDE_MAX}"
        )
    return number


def opening_original_turns() -> int:
    """The pocket a seat gets when the game did not pick an override."""
    return LIVE_STARTING_TURNS if starting_package_live() else STARTING_TURNS_PER_DAY


def turns_per_day_line(override: int | None, original: int) -> str:
    """Game-info sentence. An override is a game setting."""
    if override is None:
        return f"Turns per day: {int(original):,} (original)"
    return f"Turns per day: {int(override):,} (game setting)"


# NOTE 131 full-length-turn-limits-v1. Stored default is legacy. "1" does not
# turn this on, and V311_PROFILE does not either. It is not a profile helper.
# "v311" is the only value that lets a full-length game replace the daily pocket.
FULL_LENGTH_TURN_LIMITS_MODE = "legacy"  # "legacy" | "v311"
# Cabal glossary "Classic": 250 turns per day. RULINGS s2 uses the same 250
# (LIVE_STARTING_TURNS). Gypsy's 750 is one sample game, not this default.
FULL_LENGTH_TURNS_PER_DAY = 250
# A classic game is VICTORY_DEFAULT_MAX_DAYS (30). 30 x 250 = 7,500 turns.
FULL_LENGTH_REFERENCE_DAYS = 30
FULL_LENGTH_DAY_SECONDS = 24 * 3600


def full_length_turn_limits_on() -> bool:
    """True only when this process set FULL_LENGTH_TURN_LIMITS_MODE to v311."""
    return FULL_LENGTH_TURN_LIMITS_MODE == "v311"


def full_length_daily_cap(max_days: int) -> int:
    """Turns per day for a full-length game.

    Thirty days or fewer keep the v3.11 sysop pocket of 250. A longer game
    lowers the daily limit so the whole game stays near 7,500 turns, and the
    limit stays inside the existing 50 to 5,000 range.
    """
    days = max(1, int(max_days))
    if days <= FULL_LENGTH_REFERENCE_DAYS:
        cap = FULL_LENGTH_TURNS_PER_DAY
    else:
        cap = (FULL_LENGTH_TURNS_PER_DAY * FULL_LENGTH_REFERENCE_DAYS) // days
    if cap < TURNS_OVERRIDE_MIN:
        cap = TURNS_OVERRIDE_MIN
    if cap > TURNS_OVERRIDE_MAX:
        cap = TURNS_OVERRIDE_MAX
    return int(cap)


def parse_game_length(value: object) -> str | None:
    """'full' for a full-length game. Fast, legacy, and a blank stay omitted."""
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in ("", "fast", "legacy", "test", "none"):
        return None
    if text == "full":
        return "full"
    raise ValueError("game length must be fast or full")


def full_length_turns_override(config: object, existing: int | None) -> int | None:
    """The daily cap when this process and this game both asked for full-length.

    Flag off, or a fast test day, returns `existing` unchanged.
    """
    if not full_length_turn_limits_on():
        return existing
    if getattr(config, "game_length", None) != "full":
        return existing
    return full_length_daily_cap(int(getattr(config, "max_days", None) or FULL_LENGTH_REFERENCE_DAYS))


def opening_loadout(spec_credits: int, spec_turns: int, slot: int,
                    credits_override: int | None = None,
                    turns_override: int | None = None) -> tuple[int, int, int]:
    """Credits, turns per day, and fighters for seat `slot`.

    Legacy keeps the ±1000 credit skew. Live uses the measured pocket and
    skips the skew, which is larger than the whole 300-credit stake.
    A credits_override replaces the credits only, for every seat, with no skew.
    A turns_override replaces the turn pocket only, for every seat.
    None leaves that half of this function byte-for-byte as it was.
    """
    if starting_package_live():
        # The engine default of 1,000 means the caller did not ask. A live
        # game then keeps the measured 250. Any other number, including a
        # CLI --turns-per-day, is the number the seat actually gets.
        turns = int(spec_turns)
        if not live_pace() or turns == STARTING_TURNS_PER_DAY:
            turns = LIVE_STARTING_TURNS
        credits, fighters = LIVE_STARTING_CREDITS, LIVE_STARTING_FIGHTERS
    else:
        skew = (slot * 317) % 2001 - 1000
        credits, turns, fighters = int(spec_credits) + skew, int(spec_turns), STARTING_FIGHTERS
    if credits_override is not None:
        credits = int(credits_override)
    if turns_override is not None:
        turns = int(turns_override)
    return credits, turns, fighters

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

# "legacy": landing costs 3 turns and lifting off costs 1, on every planet.
# "live": landing on a planet you already own costs 0. Lifting off still costs 1.
# The pair is 1 turn, taken when you lift off. A planet you do not own stays at 3 plus 1.
OWN_PLANET_TURN_MODE = "legacy"  # "legacy" | "live"


def own_planet_turn_live() -> bool:
    """True when an owned-planet landing is free and the turn is taken on liftoff."""
    return OWN_PLANET_TURN_MODE == "live" or tw2002_live_profile() or v311_profile()


def land_turn_cost(owned_by_you: bool) -> int:
    """Turns a landing spends. Your own planet is free only in live mode."""
    if owned_by_you and own_planet_turn_live():
        return 0
    return int(TURN_COST["land_planet"])


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
        table = SHIP_SPECS_TW2002
    else:
        table = SHIP_SPECS
    if not ship_roster_live():
        return table
    out = dict(table)
    # v311-rulings-v1 item 3, RULINGS_v311.md s4: "Original answer (base cost / initial-max
    # holds / max fighters / turns per warp / offensive odds), from the real v3.34b shipyard
    # catalog" and "load the full table above". Keys the active table does not carry stay out.
    for key, row in SHIP_ROSTER_LIVE_TABLE.items():
        spec = out.get(key)
        if spec is None:
            continue
        spec = dict(spec)
        cost, holds, max_holds, max_fighters, tpw, odds = row
        spec.update(cost=cost, holds=holds, max_holds=max_holds, max_fighters=max_fighters,
                    turns_per_warp=tpw, offensive_odds=odds)
        out[key] = spec
    iss = out.get("imperial_starship")
    if iss is not None:
        iss = dict(iss)
        iss["cost"] = SHIP_ROSTER_ISS_COST
        out["imperial_starship"] = iss
    scout = out.get("scout_marauder")
    if scout is not None:
        scout = dict(scout)
        scout["max_fighters"] = SHIP_ROSTER_SCOUT_FIGHTERS
        out["scout_marauder"] = scout
    return out


def hull_spec(class_key: str) -> dict | None:
    """The spec of a hull a ship can be flying: the roster, or the escape pod (never for sale)."""
    if class_key == ESCAPE_POD:
        if ship_roster_live():
            # RULINGS_v311.md s4: "Escape Pod 14,446 | 1-5 | 50 | 6 | 0.8". The yard still never sells it.
            cost, holds, max_holds, max_fighters, tpw, odds = SHIP_ROSTER_LIVE_POD
            return {**POD_SPEC, "cost": cost, "holds": holds, "max_holds": max_holds,
                    "max_fighters": max_fighters, "turns_per_warp": tpw, "offensive_odds": odds}
        return POD_SPEC
    return ship_specs().get(class_key)


def ship_cost(class_key: str) -> int:
    """What StarDock charges for this hull, before trade-in."""
    if class_key == ESCAPE_POD:
        return 0
    if ship_roster_live() and class_key == "imperial_starship":
        return SHIP_ROSTER_ISS_COST
    if ship_roster_live() and class_key in SHIP_ROSTER_LIVE_TABLE:
        return int(SHIP_ROSTER_LIVE_TABLE[class_key][0])
    if ECONOMY_SCALE_MODE == "tw2002":
        return int(SHIP_COST_TW2002[class_key])
    return int(SHIP_SPECS[class_key]["cost"])


# "legacy": the yard pays 25% of the hull sticker and keeps any surplus.
# "live": the yard pays 90% of the hull sticker and pays the surplus as cash.
# TRADE_IN_MODE stays that gate. Itemised parts (holds, drive, computer,
# fighters, shields, scanner) are TRADE_IN_PARTS_MODE, off unless that switch
# or the v3.11 profile is on. A pod still counts as a Scout's hull while the
# parts switch is off. Default stays legacy so the pin and the digests do not move.
TRADE_IN_MODE = "legacy"  # "legacy" | "live"
TRADE_IN_FRACTION_LEGACY = 0.25
TRADE_IN_FRACTION_LIVE = 0.90
# Catalog unit the measured receipts used for a fighter (144 = 90% of 160;
# tradein_compare_20261018.md). No receipt separated a shield line, so a
# shield uses that same catalog. TWINSTR.DOC line 1524 takes fighters,
# accessories and mines, not cargo.
FIGHTER_TRADE_CATALOG = 160
SHIELD_TRADE_CATALOG = 160
# (hull, drive, computer, stock holds). Live v3.34b catalog
# (ships_catalog.txt / the Tyrriny ship list) checked against the measured
# receipts. The escape pod is its own parts, never a Scout's hull:
# hull 5,000 -> 4,499, one hold -> 179, drive 4,246 -> 3,821, computer 4,700 -> 4,229.
SHIP_PARTS: dict[str, tuple[int, int, int, int]] = {
    "merchant_cruiser": (10_000, 1_000, 20_300, 20),
    "scout_marauder": (2_750, 3_000, 5_200, 10),
    "missile_frigate": (11_000, 1_000, 82_800, 12),
    "battleship": (18_000, 1_000, 61_500, 16),
    "corporate_flagship": (28_500, 5_000, 120_000, 20),
    "colonial_transport": (25_200, 1_000, 10_400, 50),
    "cargotran": (12_900, 1_000, 11_050, 50),
    "merchant_freighter": (6_800, 2_000, 9_600, 30),
    "imperial_starship": (65_000, 10_000, 231_000, 40),
    "havoc_gunstar": (15_000, 10_000, 48_000, 12),
    "star_master": (12_300, 10_000, 29_000, 20),
    "constellation": (13_000, 10_000, 39_500, 20),
    "tkhasi_orion": (6_750, 10_000, 10_500, 30),
    "tholian_sentinel": (7_500, 10_000, 25_000, 10),
    "taurean_mule": (15_300, 10_000, 10_300, 50),
    "interdictor_cruiser": (104_000, 50_000, 380_000, 10),
    "escape_pod": (5_000, 4_246, 4_700, 1),
}


def trade_in_live() -> bool:
    """True when the yard pays 90% of the hull and hands back a surplus."""
    return TRADE_IN_MODE == "live" or tw2002_live_profile() or v311_profile()


def trade_in_fraction() -> float:
    if trade_in_live():
        return TRADE_IN_FRACTION_LIVE
    return TRADE_IN_FRACTION_LEGACY


def part_trade_credit(price: int) -> int:
    """90% of a catalog price, one credit less when that tenth lands exactly.

    10,000 -> 8,999. A price that is not an exact tenth stays at the floored 90%.
    """
    price = int(price)
    if price <= 0:
        return 0
    credit = (price * 9) // 10
    if (price * 9) % 10 == 0 and credit > 0:
        credit -= 1
    return credit


def hold_catalog_price(n: int) -> int:
    """Catalog price of n holds: 200n + 9n(n-1). Not the day's Class 0 quote."""
    n = int(n)
    if n <= 0:
        return 0
    return 200 * n + 9 * n * (n - 1)


def hold_trade_value(n: int) -> int:
    """What the yard pays for n holds. 20 -> 6,677, 1 -> 179, 42 -> 21,508."""
    return part_trade_credit(hold_catalog_price(n))


def ship_parts(class_key: str) -> tuple[int, int, int, int]:
    """Hull, drive, computer, and the stock hold count for a trade-in."""
    row = SHIP_PARTS.get(class_key)
    if row is not None:
        return row
    spec = hull_spec(class_key) or {}
    return (int(ship_cost(class_key)), 0, 0, int(spec.get("holds") or 0))


def scanner_trade_credit(name: str | None) -> int:
    """90% of the density or holo price the emporium charges. Nothing if bare."""
    if name in ("density", "density_scanner"):
        return part_trade_credit(DENSITY_SCANNER_COST)
    if name in ("holo", "holo_scanner"):
        return part_trade_credit(HOLO_SCANNER_COST)
    return 0


def trade_in_receipt(
    class_key: str,
    *,
    ship=None,
    holds: int | None = None,
    fighters: int | None = None,
    shields: int | None = None,
    scanner: str | None = None,
) -> dict[str, int | str | None]:
    """Itemised yard credit for the ship as it sits.

    Mines and the other gear are stripped with the old hull and are not on
    this receipt (UNVERIFIED: the measured receipts did not price them).
    Shield credits use SHIELD_TRADE_CATALOG (UNVERIFIED, same 160 base as fighters).
    """
    hull, drive, computer, stock = ship_parts(class_key)
    if ship is not None:
        holds = int(ship.holds)
        fighters = int(ship.fighters)
        shields = int(ship.shields)
        scanner = getattr(ship, "scanner", None)
    else:
        holds = stock if holds is None else int(holds)
        fighters = 0 if fighters is None else int(fighters)
        shields = 0 if shields is None else int(shields)
    hull_c = part_trade_credit(hull)
    drive_c = part_trade_credit(drive)
    computer_c = part_trade_credit(computer)
    holds_c = hold_trade_value(int(holds))
    fighter_c = part_trade_credit(FIGHTER_TRADE_CATALOG * int(fighters))
    shield_c = part_trade_credit(SHIELD_TRADE_CATALOG * int(shields))
    scan_c = scanner_trade_credit(scanner)
    total = hull_c + holds_c + drive_c + computer_c + fighter_c + shield_c + scan_c
    return {
        "hull": hull_c,
        "holds": holds_c,
        "hold_count": int(holds),
        "drive": drive_c,
        "computer": computer_c,
        "fighters": fighter_c,
        "fighter_count": int(fighters),
        "shields": shield_c,
        "shield_count": int(shields),
        "scanner": scan_c,
        "scanner_name": scanner,
        "total": total,
    }


def extra_hold_trade_value(class_key: str, holds: int) -> int:
    """Trade-in of the holds above the hull's stock count. Stock itself is in the hull."""
    stock = int(ship_parts(class_key)[3])
    extra = int(holds) - stock
    if extra <= 0:
        return 0
    return hold_trade_value(int(holds)) - hold_trade_value(stock)


def trade_in_credit(
    class_key: str,
    *,
    ship=None,
    holds: int | None = None,
    fighters: int | None = None,
    shields: int | None = None,
    scanner: str | None = None,
) -> int:
    """The yard's credit for this hull.

    Parts mode off: an escape pod counts as a Scout (DEATH_ESCAPE_PODS.md d17)
    and the extra keyword arguments are ignored, so a legacy call stays the
    sticker fraction. Parts mode on: the itemised receipt, stock fit when no
    ship is passed.
    """
    if trade_in_parts_live():
        return int(trade_in_receipt(
            class_key, ship=ship, holds=holds, fighters=fighters, shields=shields, scanner=scanner,
        )["total"])
    fraction = trade_in_fraction()
    if class_key == ESCAPE_POD:
        return int(ship_cost("scout_marauder") * fraction)
    return int(ship_cost(class_key) * fraction)


def net_hull_cost(old_key: str, new_key: str, *, ship=None) -> int:
    """Credits a trade-in moves. Negative means the yard pays the player.

    Legacy never pays a surplus, and a pod buys a Scout for nothing. Live pays
    the difference when the credit is larger than the new hull. `ship` is the
    old hull; it only changes the credit while TRADE_IN_PARTS_MODE is live.
    """
    if not trade_in_live() and old_key == ESCAPE_POD and new_key == "scout_marauder":
        return 0  # d17: the pod buys a Scout outright
    net = ship_cost(new_key) - trade_in_credit(old_key, ship=ship)
    if net < 0 and not trade_in_live():
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
    if item == "ether_probes":
        # NOTE 82 SD-e. Bible: any ship, 25. The pod is not on the chart
        # (UNVERIFIED); the same 25 applies. Off, probes stay uncapped.
        if not ship_chart_cap_live():
            return None
        return max(0, int(PROBE_CHART_MAX) - int(have))
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
    if item == "planet_scanner":
        if not planet_scanner_live():
            return 0
        return 0 if int(have) else 1
    if item in HARDWARE_V2_ITEMS:
        if not hardware_tw2002():
            return 0
        return max(0, hardware_v2_cap(class_key, item) - int(have))
    if item == "genesis" and planet_class_live() and class_key == "merchant_freighter":
        return max(0, 1 - int(have))
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
        "psychic_probe": int(psychic_probe_cost()),
        "atomic_detonator": int(ATOMIC_DETONATOR_COST),
    }


def atomic_mines_sold() -> bool:
    """v19: legacy always sells atomic_mines; tw2002 only while ATOMIC_MINES_PORT_NUKE is kept.

    NOTE 78: ATOMIC_DETONATOR_MODE live retires the port-nuke mine. The stored
    ATOMIC_MINES_PORT_NUKE flag stays True. The detonator kills the planet
    (colonists first, then the planet).
    """
    if atomic_detonator_live():
        return False
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
    # NOTE 87: the cabal total, even while SHOP_PRICE_MODE is also on.
    if class0_hold_formula_live():
        return hold_day_base(day) + 20 * int(holds_already)
    if shop_price_live():
        return 550 + 20 * (int(holds_already) - 20)
    return hold_day_base(day) + 20 * int(holds_already)


def hold_total_price(class_key: str, holds_already: int, qty: int, day: int) -> int:
    """Credits to buy `qty` holds starting from `holds_already`."""
    if ECONOMY_SCALE_MODE != "tw2002":
        return int((SHIP_SPECS.get(class_key) or POD_SPEC)["base_hold_cost"]) * int(qty)
    held = int(holds_already)
    count = int(qty)
    # NOTE 87: Cost = (B*H) + 20*H*(H-1)/2 from zero, including under the shop slope.
    if class0_hold_formula_live():
        base = hold_day_base(day)
        return count * base + 20 * (count * held + count * (count - 1) // 2)
    if shop_price_live():
        return count * 150 + 20 * (count * held + count * (count - 1) // 2)
    base = hold_day_base(day)
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

# "legacy": the four shop prices and the armid hit stay as written above
# (and the hardware-mode hit of 20). "live": the v3.34b shop card.
# Armid 1,000 and "up to 30" points. Limpet 10,000. Genesis 20,000.
# Ether probe 3,000. Combat was not played, so 30 is the shop's ceiling,
# not a measured hit. Atomic detonators stay out of this switch: the live
# item is a planet killer, and this copy's atomic mine is a different thing.
# Default stays legacy so the pin and the digests do not move.
HARDWARE_PRICE_MODE = "legacy"  # "legacy" | "live"
ARMID_MINE_COST_LIVE = 1_000
LIMPET_MINE_COST_LIVE = 10_000
ETHER_PROBE_COST_LIVE = 3_000
GENESIS_TORPEDO_COST_LIVE = 20_000
ARMID_DAMAGE_LIVE = 30


def hardware_price_live() -> bool:
    """True when the shop uses the live armid, limpet, genesis, and ether prices."""
    return HARDWARE_PRICE_MODE == "live" or tw2002_live_profile() or v311_profile()


def armid_mine_cost() -> int:
    if hardware_price_live():
        return ARMID_MINE_COST_LIVE
    return ARMID_MINE_COST


def limpet_mine_cost() -> int:
    if hardware_price_live():
        return LIMPET_MINE_COST_LIVE
    return LIMPET_MINE_COST


def ether_probe_cost() -> int:
    if hardware_price_live() or detect_gear_live():
        return ETHER_PROBE_COST_LIVE
    return ETHER_PROBE_COST


def genesis_torpedo_cost() -> int:
    if hardware_price_live() or planet_class_live():
        return GENESIS_TORPEDO_COST_LIVE
    return GENESIS_TORPEDO_COST


def armid_hit_damage() -> int:
    """Points one armid hit deals. Live uses the shop ceiling of 30."""
    if hardware_price_live():
        return ARMID_DAMAGE_LIVE
    if hardware_tw2002():
        return ARMID_DAMAGE_TW2002
    return ARMID_DAMAGE

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
# "credits" is the legacy credit table. "class" charges the commodity table
# below and consumes colonists. Nothing reads an env var or an action to flip this.
CITADEL_COST_MODE = "credits"
# "tw2002": class-table ore, organics, and equipment are spent. Colonists are a
# population requirement and are not consumed. There is no credit cost.
# "legacy": the credits table (or CITADEL_COST_MODE "class") stays as it was.
# "class" still wins when it is set, so that hidden path keeps consuming colonists.
CITADEL_FIDELITY_MODE = "tw2002"
# Original citadel days times this scale, dropped to a whole number, never below 1.
CITADEL_BUILD_TIME_SCALE = 0.25
# "legacy": that scale stays, so a class M level 1 still takes 1 day.
# "live": the v3.34b screen's raw count is used, so that level takes 4 days.
# The S1 colonist count stays 1,000. The live screen said 1,000,000.
# That conflict is not settled here.
CITADEL_DAYS_MODE = "legacy"  # "legacy" | "live"
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
def citadel_days_live() -> bool:
    """True when a citadel uses the screen's raw day count."""
    return CITADEL_DAYS_MODE == "live" or tw2002_live_profile() or v311_profile()


def citadel_build_days(raw_days: int) -> int:
    """Build days for one citadel level. Legacy scales them. Live keeps the raw count."""
    days = int(raw_days)
    if citadel_days_live():
        return max(1, days)
    return max(1, int(days * CITADEL_BUILD_TIME_SCALE))


def citadel_class_cost(class_id: str, level: int) -> tuple[int, int, int, int, int]:
    """Colonists, fuel ore, organics, equipment, and scaled days for one level."""
    colonists, fuel, organics, equipment, raw_days = CITADEL_CLASS_COSTS[class_id][level - 1]
    if citadel_table_fix_live():
        colonists = CITADEL_S1_COLONISTS.get((class_id, level), colonists)
    days = citadel_build_days(raw_days)
    if class_id == "M" and class_m_fidelity_live():
        colonists *= CLASS_M_PEOPLE_PER_THOUSAND
        days = max(1, int(raw_days))
    return colonists, fuel, organics, equipment, days


def citadel_fidelity_on() -> bool:
    """True when the live citadel rule is the class-table goods requirement."""
    return CITADEL_FIDELITY_MODE == "tw2002"


def citadel_fidelity_rules() -> bool:
    """Goods requirement. An explicit class-mode charge keeps its own path."""
    return citadel_fidelity_on() and CITADEL_COST_MODE != "class"


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
# "legacy": stocked shields fight at any citadel level.
# "live": shields can still be loaded earlier, and they fight only at level 5 and up.
# The free shield gift stays 0. No new shield count is invented.
PLANET_SHIELD_ACTIVE_MODE = "legacy"  # "legacy" | "live"
PLANET_DEFENSE_MIN_LEVEL = 0
# Daily interest is this percent of planet.treasury, integer division, at citadel level >= 1.
PLANET_TREASURY_INTEREST_PCT = 2
# Cap so 2% daily interest cannot grow a planet bank toward the 100,000,000 credit victory by itself.
# Ten million is a stockpile the owner can withdraw, not a second win.
PLANET_TREASURY_CAP = 10_000_000
# One planet shield absorbs 20 points of attacker damage, so the attacker needs 20 fighters per planet shield.
PLANET_SHIELD_ODDS = 20


def planet_shields_active() -> bool:
    """True when stocked shields fight only at citadel level 5 and up."""
    return PLANET_SHIELD_ACTIVE_MODE == "live" or tw2002_live_profile() or v311_profile()


def fighting_planet_shields(planet) -> int:
    """Shields that stop a landing. Legacy uses the stock. Live waits for level 5."""
    stocked = int(getattr(planet, "shields", 0) or 0)
    if (planet_shields_active() or citadel_perk_live()) and int(getattr(planet, "citadel_level", 0) or 0) < 5:
        return 0
    return stocked


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
# EIS CompDisplays.html Planetary Specs: J lists planet types, not one world.
# Names from TWFAQ_20PLANET.txt, except H, which S1_planet_handbook_v1.01.html
# calls Volcanic (line 772).
PLANET_CLASS_NAMES = {
    "M": "Earth",
    "K": "Desert",
    "L": "Mountainous",
    "O": "Oceanic",
    "C": "Glacial",
    "H": "Volcanic",
    "U": "Gaseous",
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
    if genesis_start_live() or planet_limits_on():
        return int(count) < PLANETS_PER_SECTOR_CAP
    return True


def planet_colonist_room(class_id: str, current: int) -> int | None:
    """How many more colonists fit. None means the legacy path has no cap."""
    if not planet_limits_on():
        return None
    return max(0, planet_colonist_cap(class_id) - int(current))


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
    """The best scanner this hull can carry (s3).

    The v3.05 revision lets a Ferrengi Assault Trader carry a density or holo
    scanner, and the Bible chart prints Both. That room is on only while
    FERRENGI_ODDS_MODE is live. Off, the assault trader stays off this table.
    """
    if class_key == "assault_trader" and ferrengi_odds_live():
        return SCANNER_HOLO
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
    if key == "warp" and exp_score_live():
        return 0
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


def photon_limpet_live() -> bool:
    """True when a limpet still attaches in a sector whose photon wave is up."""
    return PHOTON_LIMPET_MODE == "v311" or v311_profile()


# Armid (h1/h2). Legacy keeps ARMID_DAMAGE=100 and MINE_MAX_HITS_PER_MOVE random.
ARMID_DAMAGE_TW2002 = 20
# Photon wave duration in day-ticks (h7). TEDIT sample "1 seconds" -> 1 tick.
PHOTON_WAVE_DURATION = 1
# NOTE 148 GAP 4.10. S1 "The Photon Advantage" skips armids, the quasar, and
# sector fighters. Item 2, a limpet, is not on that skip list. "legacy" keeps
# today's skip. "v311" lets the limpet attach while the wave is up.
PHOTON_LIMPET_MODE = "legacy"  # "legacy" | "v311"
# Cloak (h12-h16)
CLOAK_COST = 25_000
CLOAK_MAX = 5
CLOAK_FAIL_RATE = 0.03  # TEDIT FailRate 3%; checked on tick_day while cloaked
# Mine disruptor (h18-h20)
DISRUPTOR_COST = 40_000


def disruptor_cost() -> int:
    """Shop price. Live play paid 6,000. The clear-up-to-12 effect stays."""
    if detect_gear_live():
        return 6_000
    return DISRUPTOR_COST
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
CORBOMITE_OWN_SHIP = "fires"        # cl4 UNVERIFIED for the owner | "inert"
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


def psychic_probe_cost() -> int:
    """Shop price. Live play paid 10,000. One per ship stays."""
    if detect_gear_live():
        return 10_000
    return PSYCHIC_PROBE_COST
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
# Bible ship chart (docs/reference/tw2002/S3_tw2002_bible_v1.htm): Assault
# Trader 1.2:1, Battle Cruiser 1.4:1, Dreadnaught 1.4:1. The stored dict above
# stays the FERRSPEC column. FERRENGI_ODDS_MODE reads this table.
FERRENGI_BIBLE_ODDS_BY_HULL = {
    "assault_trader": 1.2,
    "battle_cruiser": 1.4,
    "dreadnought": 1.4,
}
# Bible "Fig Max / Fig Per Attack" for the Assault Trader is 3,000 / 2,000.
# FERRSPEC prints 1,000 for that cell. Battle Cruiser 2,000 and Dreadnought
# 5,000 match FERRSPEC, so only the assault cell changes with the odds switch.
FERRENGI_BIBLE_ASSAULT_FIGHTERS_PER_ATTACK = 2_000
# TWFAQ_FERRSPEC_ferrengi.txt "Fighters per Attack". The odds above are the
# same file's approximate column. A Ferrengi that attacks still sends every
# fighter through the three-round roll until FERRENGI_ATTACK_MODE is v311.
FERRENGI_FIGHTERS_PER_ATTACK = {
    FERRENGI_HULL_ASSAULT: 1_000,
    FERRENGI_HULL_CRUISER: 2_000,
    FERRENGI_HULL_DREAD: 5_000,
}
# Encounter: "tribute" opens Flee/Attack/Surrender; "auto_combat" = legacy immediate fight.
FERRENGI_ENCOUNTER = "tribute"
FERRENGI_FIGHTER_BLOCK = False  # Iago: Ferrengi ignore deployed fighters
FERRENGI_HIT_MINES = True
FERRENGI_ALIGN_ON_KILL = 10
# UNVERIFIED, searched: TWBible_original_v1x.txt lines 475-480 and
# Bible_TWGS_edit_2007_Clme.htm (same "BIG alignment raise", bounty either
# alignment, no number and no experience by hull); TWFAQ_FERRSPEC_ferrengi.txt
# (hull chart, no awards); classictw_docs_wiki Ferrengi_Assault_Trader.html,
# Ferrengi_BattleCruiser.html, Ferrengi_Dreadnaught.html (specs only);
# cabal formulas.html (player and fighter alignment, no Ferrengi kill award);
# wiki.classictw.com Bible v1.1 and Xeulian Field Manual (no hull award).
# These stand in for that award when FERRENGI_REWARD_MODE is live. A hull
# that is not listed keeps the clone formula (kill_ferr x aggression).
# Queued in docs/plans/live-twgs-test-queue-v1.md.
FERRENGI_XP_BY_HULL = {
    FERRENGI_HULL_ASSAULT: 50,
    FERRENGI_HULL_CRUISER: 100,
    FERRENGI_HULL_DREAD: 150,
}
FERRENGI_REGEN_PCT = 0.20  # TEDIT 20% of hull max
FERRENGAL_MINES = 50  # Bible
FERRENGAL_FIGHTERS = 1000  # UNVERIFIED stand-in for "cloud of Ferrengi ftrs"
# UNVERIFIED, searched: S1_planet_handbook_v1.01.html lines 583-585 (a planet
# with 10,000 ore at 10% sector burns 1,000 and deals 333; that is the example,
# not Ferrengal's setting); Iago_War_Manual.txt lines 3823-3829 (v1.03d, not
# v3.11: Ferrengal "usually" starts at 10,000 ore, 30% atmosphere, 0% sector);
# eis CitadelMenu.html Quasar Cannon R-level (the owner sets both percents);
# cabal twgs.html "<#> Invincible Ferrengal : No" (no strength). The shot
# uses these constants and does not burn ore. Queued for a live entry.
FERRENGAL_QUASAR_FUEL = 10_000
FERRENGAL_QUASAR_PCT = 10
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
# "legacy": a genesis planet's opening citadel goods count in net worth.
# "fair": those goods do not count until the citadel is at least level 1.
# Default stays legacy so digests do not move. Game 5 scored a fresh class U
# planet at about 308,600 from these goods alone.
GENESIS_SCORE_MODE = "legacy"   # "legacy" | "fair"
NW_HULL_FRACTION = 0.5           # hull counts half its StarDock price
NW_HARDWARE_FRACTION = 0.5       # wave-priced fighters / shields: the hull's share
NW_WAVE_MID_PRICE = 200          # wave midpoint: base 160 + amp 80 / 2


def net_worth_tw2002() -> bool:
    return NET_WORTH_MODE == "tw2002"


def genesis_score_fair() -> bool:
    """True when a fresh genesis planet does not score its seeded citadel goods."""
    return GENESIS_SCORE_MODE == "fair" or v311_profile()


# action-result-v1. "legacy" answers POST /action as soon as the move is queued,
# and a plotted route reports 0 turns after spending them. "report" waits for
# the engine and adds result {ok, rejected, error, turns_spent}. The route
# result names the turns the hops spent. Default stays legacy so the pin and
# the digests do not move. POST /hold is unchanged. A failed haggle still costs
# its turn.
ACTION_RESULT_MODE = "legacy"   # "legacy" | "report"
ACTION_RESULT_WAIT_S = 5.0


def action_result_report() -> bool:
    """True when the action POST includes the engine's ok or reject."""
    return ACTION_RESULT_MODE == "report" or v311_profile()


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


# NOTE 148 GAP 8.1. FERRSPEC fighters per attack: 1,000 / 2,000 / 5,000.
# "legacy" keeps the three-round roll that can send every fighter.
# "v311" sends one volley, capped at that chart, at the hull odds.
FERRENGI_ATTACK_MODE = "legacy"  # "legacy" | "v311"


def ferrengi_attack_live() -> bool:
    """True when a Ferrengi attack uses the chart volley instead of three rolls."""
    return FERRENGI_ATTACK_MODE == "v311" or v311_profile()


def ferrengi_fighters_per_attack(hull: str | None) -> int:
    """Fighters one attack from this hull may send.

    FERRSPEC is the stored chart. The Bible assault cell is 2,000, and that
    cell is used only while FERRENGI_ODDS_MODE is on. FERRENGI_ATTACK_MODE
    still decides whether the volley is capped at all.
    """
    key = str(hull or "")
    if key == FERRENGI_HULL_ASSAULT and ferrengi_odds_live():
        return int(FERRENGI_BIBLE_ASSAULT_FIGHTERS_PER_ATTACK)
    return int(FERRENGI_FIGHTERS_PER_ATTACK.get(key, 1_000))


def ferrengi_odds_for_hull(hull: str | None) -> float:
    """Public odds of a Ferrengi hull (what sector.ferrengi shows), same table the engine uses."""
    if hull and ferrengi_tw2002():
        table = FERRENGI_BIBLE_ODDS_BY_HULL if ferrengi_odds_live() else FERRENGI_ODDS_BY_HULL
        return float(table.get(hull, FERRENGI_COMBAT_ODDS))
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
BOUNTY_ALIGN_PER = 250           # formulas.html: -1 alignment per 250 credits on a good trader

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
CORPSHIP_EXMEMBER_TRADEIN = "refuse"  # cl3 | "allow"
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
TOW_EXTERN_HOLDER = "owner_or_corp"  # cl2 CABT #4 | "owner"
TOW_EXTERN_ALLY_HOLDS = False        # cl2 UNVERIFIED: an ally who is not a corp mate does not hold
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
DEATH_CREDITS_RETURN_FIRE = "defender"  # CORP_LOOSE_ENDS.md cl11
DEATH_CREDITS_PLANET_DEFENCE = "owner"   # CORP_LOOSE_ENDS.md cl11
DEATH_CREDITS_CORBOMITE = "owner"        # CORP_LOOSE_ENDS.md cl12: a living owner, including a pod
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
H_RECOVERY_MODE = "tw2002"             # H_BOT_RECOVERY.md | "legacy". Unread until the bot hooks land.


def bank_on() -> bool:
    return BANK_MODE == "tw2002"


def bots_bank_on() -> bool:
    return BOTS_BANK_MODE == "tw2002" and bank_on()


def h_recovery_on() -> bool:
    """H and N1 rebuy a cargo hull after a death. Legacy keeps the Scout buy."""
    return H_RECOVERY_MODE == "tw2002"


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
TAVERN_TRICRON = "on"                   # tv20 built in stardock-leftovers-v1; gated by STARDOCK_EXTRA_MODE
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
BOT_WAR_START_DAY = 5                    # bw13, bw22
BOT_WAR_SIEGES_PER_DAY = 1               # bw14
BOT_WAR_SIEGE_COOLDOWN_DAYS = 2          # bw14
BOT_WAR_GOOD_ATTACKS_ANY = False         # D6, bw23
BOT_WAR_RISK_NW_PCT = 40                 # bw15, the stake is net worth, not the ship
BOT_WAR_SIEGE_MIN_LEFT = 100             # bw15, fighters still aboard after the estimate
BOT_WAR_PRIZE_MIN_RATIO = 1.5            # bw15, seen treasury must cover this times the fighters spent
BOT_WAR_NW_DROP_STOP_PCT = 30            # bw22
BOT_WAR_COOLDOWN_DAYS = 3                # bw22, defend this many days after a drop
BOT_WAR_SCOUT_MIN_FIGHTERS = 2_000        # bw13
BOT_WAR_SCOUT_TURNS_PER_DAY = 10          # bw13
BOT_WAR_PROBES_PER_DAY = 1                # bw13
BOT_WAR_LAND_TRIES = 3                    # bw16
BOT_WAR_DEFEND_MAX_HOPS = 8               # bw19
BOT_WAR_MAX_TURNS_PCT = {"N3": 40, "N2": 30}  # bw25


def bots_war_on() -> bool:
    return BOTS_WAR_MODE == "tw2002"


# --- Bots use the tavern (BOTS_TAVERN_MODE) ----------------------------------
# docs/playtests/bots/BOTS_USE_TAVERN.md. The engine tavern stays on TAVERN_MODE.
BOTS_TAVERN_MODE = "tw2002"              # bt1: "tw2002" | "legacy"
BOT_TAVERN_TRACE_GAP_DAYS = 10           # one paid ask in each 10-day stretch
BOT_TAVERN_RESERVE = 20_000              # cash left after a tavern buy


def bots_tavern_on() -> bool:
    return BOTS_TAVERN_MODE == "tw2002"


# --- Bots deploy defenses (BOTS_DEPLOY_MODE) ---------------------------------
# docs/playtests/bots/BOTS_DEPLOY_DEFENSES.md. Engine deploy verbs stay on HARDWARE_MODE.
BOTS_DEPLOY_MODE = "tw2002"              # bd1: "tw2002" | "legacy"
BOT_DEPLOY_MINE_GAP_DAYS = 1             # at most one lay trip per day
BOT_DEPLOY_MINE_QTY = 5                  # armids/limpets laid per visit
BOT_DEPLOY_MINE_SPEND_PCT = 5            # mine buys under this % of trading profit
BOT_DEPLOY_FIGHTER_FLOOR = 10            # keep this many fighters aboard


def bots_deploy_on() -> bool:
    return BOTS_DEPLOY_MODE == "tw2002"


# --- StarDock leftovers (STARDOCK_EXTRA_MODE) --------------------------------
# Tri-Cron is the tavern game on the live TWGS screen (ante 100, 10 rounds,
# 2:1, jackpot 5000). The slice blurb called it a news board; the screen does not.
STARDOCK_EXTRA_MODE = "tw2002"           # sd1: "tw2002" | "legacy"
TRICRON_ANTE = 100
TRICRON_ROUNDS = 10
TRICRON_OPENING_JACKPOT = 5_000
TRICRON_OPENING_CHAMPION = 5_000
CINEPLEX_COST = 0                        # UNVERIFIED: live player did not enter; Bible says a nominal sum and an ANSI, no number


def stardock_extra_on() -> bool:
    return STARDOCK_EXTRA_MODE == "tw2002"


# --- Corporations (CORP_MODE) -------------------------------------------------
# docs/playtests/corps/CORP_RULES.md. "legacy" is the engine at 57dec11.
CORP_MODE = "tw2002"                      # "tw2002" | "legacy"
CORP_FIX_MODE = "tw2002"                  # CORP_LOOSE_ENDS.md cl1 | "legacy"
ROGUE_TOLL_POT_CAP = None                 # cl8 UNVERIFIED: no cap
ROGUE_TOLL_CHARGES = True                 # cl8 UNVERIFIED: a rogue group still collects tolls
LIMPET_CORP_VIEW = "corporate_only"       # cl6 | "all_corp"
CORP_CREATE_COST = 0                      # cr2: REPORT.md line 279 (free; 500_000 is CORP_FORMATION_COST, legacy path only)
CORP_TURN_COST = 0                        # cr2 UNVERIFIED
CORP_NEW_PASSWORD = ""                    # cr3 UNVERIFIED: blank means closed
CORP_APPROVER = "member"                  # cr4 SOURCE-CONFLICT: "member" | "ceo"
CORP_BREAKIN_PER_DAY = 1                  # cr6
CORP_BREAKIN_RULE = "wrong_guesses"       # cl7 | "attempts"
CORP_BREAKIN_ALIGN_LOSS = 0               # cr6 UNVERIFIED
CORP_BREAKIN_TELL_CEO = False             # cr6 UNVERIFIED
CORP_MAX_MEMBERS = 5                      # cr7 CONFIRMED
CORP_ALIGNMENT_RULE = "mixed"             # cr8: "mixed" | "same_side" | "join_check"
CORP_SIDE_OF_ZERO = "good"                # cr8 UNVERIFIED
MIXED_CORP_EXP_RULE = "highest_good"      # cr9: "highest_good" | "least_extreme"
MIXED_CORP_EXP_DIVISOR = 4                # cr9
MIXED_CORP_EXP_FLOOR = 1                  # cr9 UNVERIFIED; a live overnight read is still open
# D22-1. "legacy" puts the formula loss in the CORP_EXP_PENALTY summary and
# loss field. "taken" names the experience actually removed (the floor).
# The experience math is the same either way. V311 turns "taken" on.
CORP_EXP_PENALTY_MODE = "legacy"          # "legacy" | "taken"
CORP_LEAVER_PLANETS = "corp_keeps"        # cr10: "corp_keeps" | "leaver_keeps"
# D22-2. "legacy": a leaver's corporate fighters and mines keep his owner_id.
# "to_ceo": that owner_id becomes the C.E.O. The corp ticker stays.
# Live TWGS v3.34b: those fighters stay with the corp under the C.E.O.
# The stored default stays "legacy"; V311 turns "to_ceo" on.
CORP_LEAVER_DEPLOYMENTS = "legacy"        # "legacy" | "to_ceo"
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


def corp_fix_on(*, corp: bool = False) -> bool:
    """Kill rows read the mode alone. Corp rows also stay off when CORP_MODE is legacy."""
    if CORP_FIX_MODE != "tw2002":
        return False
    if corp and CORP_MODE != "tw2002":
        return False
    return True


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
# al16. Half the alien's alignment, subtracted, so an evil alien raises a good
# trader. UNVERIFIED, searched: TWBible_original_v1x.txt lines 466-467 (the half
# and the quarter are experience; alignment goes up "depending on their
# alignment"), Gypsy_Big_Dummies_Guide.html (no half or quarter sentence),
# classictw_docs_wiki/Alignment.html "Kill aliens" (no fraction).
ALIEN_KILL_ALIGN_SHARE = 0.5
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
LLM_QUASAR_NUDGE_MODE = "on"              # "on" | "off" (off = no brief line)
LLM_QUASAR_NUDGE_ORE_FLOOR = 500          # fuel ore on the planet; not BOT_WAR_QUASAR_ORE_FLOOR


def planet_nudge_on() -> bool:
    return LLM_PLANET_NUDGE_MODE == "tw2002"


def quasar_nudge_on() -> bool:
    return LLM_QUASAR_NUDGE_MODE == "on"


# assign-colonists-pool-fix-v1. Appended so later slices can rebase cleanly.
# "legacy": with citadel fidelity on, assign_colonists to=colonists lands in fuel_ore.
# "live": to=colonists stays in the colonists pool. The named goods pools stay named.
ASSIGN_POOL_FIX_MODE = "legacy"  # "legacy" | "live"


def assign_pool_fix_live() -> bool:
    """True when assign_colonists to=colonists stays in the colonists pool."""
    return ASSIGN_POOL_FIX_MODE == "live" or tw2002_live_profile() or v311_profile()


# hold-endpoint-rules-v1. Appended so later slices can rebase cleanly.
# "legacy": rules text and the action hint stay as they are. POST /hold is unchanged.
# "live": the prompt, the action hint, and the action answer name the end-slot rule.
HOLD_RULES_MODE = "legacy"  # "legacy" | "live"
HOLD_RULES_NOTE = (
    "POST /hold {hold:true} keeps your slot for the next action. "
    "POST /hold {hold:false} ends the slot and spends no turn. "
    "A normal action ends the slot even when it spends 0 turns, unless hold is on. "
    "accepted true means queued. ok means the engine applied it. rejected means the engine refused it. "
    "A 0-turn ok still ends the slot."
)


def hold_rules_live() -> bool:
    """True when the rules text names POST /hold and ok versus rejected."""
    return HOLD_RULES_MODE == "live" or tw2002_live_profile() or v311_profile()


# planet-nw-construction-v1. Appended so later slices can rebase cleanly.
# "legacy": goods spent on a citadel leave net worth until that level finishes.
# "live": those goods stay in the score while the level is still building.
PLANET_NW_MODE = "legacy"  # "legacy" | "live"


def planet_nw_live() -> bool:
    """True when a citadel under construction keeps the goods it already spent."""
    return PLANET_NW_MODE == "live" or tw2002_live_profile() or v311_profile()


# trade-dock-turn-v1. Appended so later slices can rebase cleanly.
# The visit rule is already the engine: the first deal costs 1 turn, later
# deals in that sector cost 0. "legacy" keeps that. "live" names the same rule.
TRADE_TURN_MODE = "legacy"  # "legacy" | "live"


def trade_turn_live() -> bool:
    """True when the dock rule is selected by name. The numbers match legacy."""
    return TRADE_TURN_MODE == "live" or tw2002_live_profile()


def trade_visit_free() -> bool:
    """True when a later deal in the same sector costs no turn."""
    return TRADE_TURN_MODE in ("legacy", "live")


# warp-turn-cost-v1. Appended so later slices can rebase cleanly.
# A warp already costs that hull's turns_per_warp (3, freighter 2 on the
# tw2002 table). "legacy" keeps that. "live" names the same number.
WARP_COST_MODE = "legacy"  # "legacy" | "live"


def warp_cost_live() -> bool:
    """True when the per-ship warp cost is selected by name. The numbers match legacy."""
    return WARP_COST_MODE == "live" or tw2002_live_profile()


def warp_turns(class_key: str) -> int:
    """Turns one warp spends for this hull. Both switch positions use the table."""
    spec = hull_spec(class_key) or {}
    if WARP_COST_MODE in ("legacy", "live") and "turns_per_warp" in spec:
        return int(spec["turns_per_warp"])
    return int(TURN_COST["warp"])


# port-price-curve-v1. Appended so later slices can rebase cleanly.
# "legacy": the current stock curve. "live": full-port anchors from the live
# screen, then the same slope, MCIC, and experience cap (1000).
PORT_PRICE_MODE = "legacy"  # "legacy" | "live"
# Full-port sell anchors. Fuel 16 and equipment 36 are the screen. Organics 35
# is the queue's full-port figure; the screen also showed 18.6.
PORT_PRICE_LIVE_SELL_FULL = {"fuel_ore": 16, "organics": 35, "equipment": 36}
# Full-port buy anchors, midpoints of the seen ranges. The stock on those
# screens was not written down, so treating them as full is UNVERIFIED.
# NOTE 69: PORT_BUY_PRICE_ANCHOR_MODE live treats these as the hungry quotes.
PORT_PRICE_LIVE_BUY_FULL = {"fuel_ore": 38, "organics": 73, "equipment": 102}
PORT_PRICE_SELL_FULL_MULT = 0.60  # 1.25 - 0.65 at a full port
PORT_PRICE_BUY_FULL_MULT = 0.75   # 1.45 - 0.70 at a full port


def port_price_live() -> bool:
    """True when quotes use the live full-port anchors."""
    return PORT_PRICE_MODE == "live" or tw2002_live_profile() or v311_profile()


# v311-port-buy-price-v1 (NOTE 69). "legacy" keeps the full-hold anchor above:
# a buying port pays PORT_PRICE_LIVE_BUY_FULL only when current == maximum, so a
# hungry port (current 0, which PORT_STOCK_FIDELITY opens) quotes about 1.93x.
# "live" prices a buying port from remaining demand. A hungry port pays the
# anchor, and the quote eases as the hold fills. 0.25 makes a port go from 51%
# remaining demand to 37% about 4% cheaper (live v3.34b equipment 105 -> 100.8).
# Stored default stays legacy. Appended so later slices can rebase cleanly.
PORT_BUY_PRICE_ANCHOR_MODE = "legacy"  # "legacy" | "live"
PORT_BUY_FILL_EASE = 0.25


def port_buy_price_anchor_on() -> bool:
    """True when a buying port's anchor is the hungry quote, not a full hold."""
    return PORT_BUY_PRICE_ANCHOR_MODE == "live" or tw2002_live_profile() or v311_profile()


# NOTE 112 row 165. GAP 2.5. ECONOMY_SCALE_MODE is already "tw2002", and one
# base still cannot hit both sides of the economy2 100% chart
# (ECONOMY_CALIBRATION.md). Bible hull prices already come from
# SHIP_COST_TW2002 on that scale. This switch prices each side from the
# chart total, then keeps the existing stock, MCIC, and experience slope.
# It wins over PORT_PRICE_MODE. Stored default stays legacy so the digests
# do not move. Shields have no sourced unit price and stay off this switch.
PRICE_SCALE_MODE = "legacy"  # "legacy" | "live"
# 250-hold totals. Selling port full, MCIC 50. Buying port empty, MCIC -50.
# Experience 0, no haggle. economy2.html 100% charts. The experience table
# on that page averages equipment at 11,760 / 32,405. SOURCE-CONFLICT.
# This follows the 100% chart, as ECONOMY_CALIBRATION.md does.
PRICE_SCALE_SELL_250 = {"fuel_ore": 3_675, "organics": 6_964, "equipment": 12_190}
PRICE_SCALE_BUY_250 = {"fuel_ore": 8_791, "organics": 17_712, "equipment": 31_910}
PRICE_SCALE_HOLDS = 250
PRICE_SCALE_SELL_MCIC = 50
PRICE_SCALE_BUY_MCIC = -50


def price_scale_live() -> bool:
    """True when a port quote starts from the economy2 chart, not one base."""
    return PRICE_SCALE_MODE == "live" or tw2002_live_profile() or v311_profile()


def price_scale_unit(total: int) -> int:
    """Nearest whole credit per hold for a 250-hold chart total."""
    holds = PRICE_SCALE_HOLDS
    return (int(total) + holds // 2) // holds


# port-regen-mcic-v1. Appended so later slices can rebase cleanly.
# "legacy": a day adds 5% of that commodity's productivity.
# "live": a day adds 5% of the max stock. One visit cannot move more than
# that max. Per-port MCIC and productivity are already on the port.
PORT_REGEN_MODE = "legacy"  # "legacy" | "live"


def port_regen_live() -> bool:
    """True when a day puts back 5 percent of max stock."""
    return PORT_REGEN_MODE == "live" or tw2002_live_profile() or v311_profile()


# hold-fighter-shield-price-v1. Appended so later slices can rebase cleanly.
# "legacy": the next hold is the daily base plus 20 per hold already owned.
# "live": 550 + 20 per hold past 20, including below 20. The same slope.
# Fighters and shields stay on the 160-239 wave. Day 1 was 188 and 161,
# day 2 was 190 and 159. Two days are not a new curve.
SHOP_PRICE_MODE = "legacy"  # "legacy" | "live"


def shop_price_live() -> bool:
    """True when the next hold uses the flat 550 screen formula."""
    return SHOP_PRICE_MODE == "live" or tw2002_live_profile() or v311_profile()


# ship-roster-stats-v1. Appended so later slices can rebase cleanly.
# "legacy": the Bible chart, ISS at 339,000 and a Scout with 150 fighters.
# "live": the screen, ISS at 329,000 and a Scout with 250 fighters.
# The other named hulls already match that screen.
SHIP_ROSTER_MODE = "legacy"  # "legacy" | "live"
SHIP_ROSTER_ISS_COST = 329_000
SHIP_ROSTER_SCOUT_FIGHTERS = 250
# v311-rulings-v1 item 3. RULINGS_v311.md s4, the real v3.34b shipyard catalog:
# (cost, initial holds, max holds, max fighters, turns per warp, offensive odds).
SHIP_ROSTER_LIVE_TABLE: dict[str, tuple[int, int, int, int, int, float]] = {
    "merchant_cruiser": (41_300, 20, 75, 2_500, 3, 1.0),
    "scout_marauder": (15_950, 10, 25, 250, 2, 2.0),
    "missile_frigate": (100_800, 12, 60, 5_000, 3, 1.3),
    "battleship": (88_500, 16, 80, 10_000, 4, 1.6),
    "corporate_flagship": (163_500, 20, 85, 20_000, 3, 1.2),
    "colonial_transport": (63_600, 50, 250, 200, 6, 0.6),
    "cargotran": (51_950, 50, 125, 400, 4, 0.8),
    "merchant_freighter": (33_400, 30, 65, 300, 2, 0.8),
    "imperial_starship": (329_000, 40, 150, 50_000, 4, 1.5),
    "havoc_gunstar": (79_000, 12, 50, 10_000, 3, 1.2),
    "star_master": (61_300, 20, 73, 5_000, 3, 1.4),
    "constellation": (72_500, 20, 80, 5_000, 3, 1.4),
    "tkhasi_orion": (42_250, 30, 60, 750, 2, 1.1),
    "tholian_sentinel": (47_500, 10, 50, 2_500, 4, 1.0),
    "taurean_mule": (63_600, 50, 150, 300, 4, 0.5),
    "interdictor_cruiser": (539_000, 10, 40, 100_000, 15, 1.2),
}
SHIP_ROSTER_LIVE_POD: tuple[int, int, int, int, int, float] = (14_446, 1, 5, 50, 6, 0.8)


def ship_roster_live() -> bool:
    """True when the yard uses the full RULINGS s4 table (ISS price, Scout cap, holds, odds)."""
    return SHIP_ROSTER_MODE == "live" or tw2002_live_profile() or v311_profile()


# genesis-start-and-cap-v1. Appended so later slices can rebase cleanly.
# "legacy": a new planet keeps the 2,500 colonist seed and the citadel goods.
# "live": a new planet starts empty. A sector still holds at most 5 planets.
# The torpedo price stays on the hardware-price switch.
GENESIS_START_MODE = "legacy"  # "legacy" | "live"


def genesis_start_live() -> bool:
    """True when a genesis planet starts with no colonists and no goods."""
    return GENESIS_START_MODE == "live" or tw2002_live_profile() or v311_profile()


# terra-colonists-v1. Appended so later slices can rebase cleanly.
# "legacy": the pool opens full at 100,000 and one colonist fills one hold.
# "live": the pool opens at 30,000 and one hold carries 1,000 colonists.
# The price stays 0, the turn stays 1, and a day still adds 750.
TERRA_COLONIST_MODE = "legacy"  # "legacy" | "live"
TERRA_LIVE_START = 30_000
TERRA_LIVE_PER_HOLD = 1_000


def terra_colonist_live() -> bool:
    """True when Terra opens at 30,000 and a hold carries 1,000 colonists."""
    return TERRA_COLONIST_MODE == "live" or tw2002_live_profile() or v311_profile()


def terra_start_pool() -> int:
    """Colonists in the Terra pool when the universe is created."""
    if terra_colonist_live():
        return TERRA_LIVE_START
    return TERRA_MAX_COLONISTS


def colonists_per_hold() -> int:
    """Colonists that fill one cargo hold."""
    if terra_colonist_live():
        return TERRA_LIVE_PER_HOLD
    return 1


# planet-production-ratios-v1. Appended so later slices can rebase cleanly.
# "legacy": units per 100 colonists, and a flat 5 percent growth.
# "live": colonists per unit from the S1 table. Below half the class cap
# the same 5 percent is growth. Above half it is a die-off. The 1,500 fuel
# example makes 500, so the ratio is not scaled by a second curve.
PLANET_PROD_MODE = "legacy"  # "legacy" | "live"
# Fuel, organics, equipment. 0 means that class does not make that good.
PLANET_PROD_PER_UNIT = {
    "M": (3, 7, 13),
    "K": (2, 100, 500),
    "L": (2, 5, 20),
    "O": (20, 2, 100),
    "C": (50, 100, 500),
    "H": (1, 0, 500),
    "U": (0, 0, 0),
}


def planet_prod_live() -> bool:
    """True when a day uses the S1 colonists-per-unit table."""
    return PLANET_PROD_MODE == "live" or tw2002_live_profile() or v311_profile()


# citadel-perks-live-v1. Appended so later slices can rebase cleanly.
# "legacy": the perk lines still say level 2 and level 5 are missing, and the
# 2-to-1 and 3-to-1 odds run at every citadel level.
# "live": those lines name the computer and the shields. Setting the reaction
# percent waits for level 2. Stocked shields fight only at level 5. Quasar
# stays at level 3, and fighters already stay quiet below level 2.
CITADEL_PERK_MODE = "legacy"  # "legacy" | "live"


def citadel_perk_live() -> bool:
    """True when citadel perks use the level gates from the handbook."""
    return CITADEL_PERK_MODE == "live" or tw2002_live_profile() or v311_profile()


def citadel_perks() -> list[tuple[int, str, str]]:
    """Perk lines. The stored list stays the old wording."""
    if not citadel_perk_live():
        return CITADEL_PERK
    out: list[tuple[int, str, str]] = []
    for level, name, text in CITADEL_PERK:
        if level == 2:
            text = (
                "Combat Control Computer: planet fighters attack at 2 to 1 "
                "and defend at 3 to 1. The military reaction percent sets how many attack."
            )
        elif level == 5:
            text = (
                "Planetary shields: stocked shields fight at citadel level 5. "
                "A citadel L5 with 200 shields ignores a photon damp."
            )
        out.append((level, name, text))
    return out


# exp-score-v1. Appended so later slices can rebase cleanly.
# "legacy": the rank line and the end table follow net worth. A warp still
# uses the rank table (0 on the tw2002 table, 1 on the old table).
# "live": the rank line and the end table follow experience. Net worth stays
# on the row as the second column. A warp gives 0 experience either way.
EXP_SCORE_MODE = "legacy"  # "legacy" | "live"


def exp_score_live() -> bool:
    """True when the public rank follows experience, not net worth."""
    return EXP_SCORE_MODE == "live" or tw2002_live_profile() or v311_profile()


# alignment-v1. Appended so later slices can rebase cleanly.
# "legacy" and "live" use the same rules. A kill already moves alignment by
# the fighters you lost times the enemy's alignment, divided by 5000.
# A trader with 0 or more alignment and 999 experience or less is already
# protected in FedSpace. The switch stays off.
ALIGNMENT_MODE = "legacy"  # "legacy" | "live"


def alignment_live() -> bool:
    """True when the slice names the alignment rules that are already on."""
    return ALIGNMENT_MODE == "live" or tw2002_live_profile()


# rank-titles-v1. Appended so later slices can rebase cleanly.
# "legacy" and "live" use the same 22 good titles and 22 evil titles.
# Thresholds double from 2 up to 4,194,304. Below 2 is Civilian.
# The switch stays off.
RANK_TITLES_MODE = "legacy"  # "legacy" | "live"


def rank_titles_live() -> bool:
    """True when the slice names the title ladders that are already on."""
    return RANK_TITLES_MODE == "live" or tw2002_live_profile()


# death-pod-v1. Appended so later slices can rebase cleanly.
# "legacy": a pod keeps the Bible chart start (5 holds, nothing else) and loses
# 10 percent of experience. Two pods a day, then Ship Destroyed.
# "live": the fresh pod is the one seen in the clean game: 1 hold, 1 fighter,
# 30 shields, a density scanner. Experience stays a 10 percent loss. The clean
# game also showed a flat -25, which is not used.
DEATH_POD_MODE = "legacy"  # "legacy" | "live"


def death_pod_live() -> bool:
    """True when a fresh pod uses the clean-game loadout."""
    return DEATH_POD_MODE == "live" or tw2002_live_profile() or v311_profile()


# ship-combat-odds-v1. Appended so later slices can rebase cleanly.
# "legacy" and "live" use the same Bible chart. A merchant cruiser attacks
# at 1 to 1 and may send 750 fighters. A scout attacks at 2 to 1 and may
# send 250. The switch stays off.
COMBAT_ODDS_MODE = "legacy"  # "legacy" | "live"


def combat_odds_live() -> bool:
    """True when the slice names the per-ship odds that are already on."""
    return COMBAT_ODDS_MODE == "live" or tw2002_live_profile()


# corp-rules-v2. Appended so later slices can rebase cleanly.
# The rules below are already on through CORP_MODE tw2002. This switch stays
# off and does not turn them off. A joiner must match the C.E.O.'s alignment.
# The C.E.O. can drop a member. Members can transfer. The cap is 5.
CORP_RULES_V2_MODE = "legacy"  # "legacy" | "live"


def corp_rules_v2_live() -> bool:
    """True when the slice names the corporation rules that are already on."""
    return CORP_RULES_V2_MODE == "live" or tw2002_live_profile()


# cockpit-api-parity-v1. Appended so later slices can rebase cleanly.
# The bot screen lists every verb. This switch stays off and does not hide
# those buttons. A default game would be short a control if it did.
COCKPIT_PARITY_MODE = "legacy"  # "legacy" | "live"


def cockpit_parity_live() -> bool:
    """True when a later slice wants the parity screen called out as live."""
    return COCKPIT_PARITY_MODE == "live" or tw2002_live_profile()


# tw2002-live-profile-v1. Appended so later slices can rebase cleanly.
# One switch for a test game. Off, every flag above stays as written.
# On, each live helper above is true together. The stored values stay
# legacy, so the pin does not move.
TW2002_LIVE_PROFILE = "legacy"  # "legacy" | "live"


def tw2002_live_profile() -> bool:
    """True when a test game wants every live helper on at once."""
    return TW2002_LIVE_PROFILE == "live"


# port-attack-defense-v1. Off, an attack aimed at "port" is still "target not found".
# On, the attack asks first. Yes costs 5 alignment and the fighters you send.
# Class 6 is the one measured port: rating 98, barrage 598 (REPORT2 section 8).
# Other classes have no measured barrage, so the ship is not destroyed for them.
PORT_ATTACK_MODE = "legacy"  # "legacy" | "live"
PORT_ATTACK_ALIGNMENT = -5
PORT_DEFENSE_RATING = {6: 98}
PORT_LASER_BARRAGE = {6: 598}
PORT_ATTACK_CONFIRM = "Attacks on Federation ports are prohibited! Are you sure?"


def port_attack_live() -> bool:
    return PORT_ATTACK_MODE == "live" or tw2002_live_profile() or v311_profile()


# haggle-detail-v1. Off, the older haggle window is unchanged.
# On, a sale takes up to +3% of the opening quote. +4% to +12% gets a counter
# at +1%. Above that the trade ends: "Swine" until +37%, then "Get lost creep".
# A buy takes down to -12%. -13% to -23% gets a counter at -4%. Worse ends it.
# The gaps +13%..+16% and -13%..-15% were not measured. They follow the next
# measured outcome: an ended sale, and a buy counter.
HAGGLE_LIVE_MODE = "legacy"  # "legacy" | "live"


def haggle_live() -> bool:
    return HAGGLE_LIVE_MODE == "live" or tw2002_live_profile() or v311_profile()


# NOTE 150 GAP 2.6. Cabal haggling.html prints a counter percent per product
# and MCIC. The straight 110-149 line stays the stored path. "v311" uses the
# printed table, and interpolates only between two printed rows. A product or
# MCIC the page does not print keeps the line. This wins over the later
# measured window when both are on.
HAGGLE_TABLE_MODE = "legacy"  # "legacy" | "v311"


def haggle_table_live() -> bool:
    """True when a counter uses the cabal product table instead of one line."""
    return HAGGLE_TABLE_MODE == "v311" or v311_profile()


# discovery-exp-daily-bonus-v1. Off, the first trader at a port still gets the
# one point, and the midnight bonus still follows the rank switch.
# On, each player gets one point the first time they trade at a port, and the
# midnight point of experience and alignment is only for someone who spent a turn.
DISCOVERY_EXP_MODE = "legacy"  # "legacy" | "live"


def discovery_exp_live() -> bool:
    return DISCOVERY_EXP_MODE == "live" or tw2002_live_profile() or v311_profile()


# fed-ships-ferrengi-v1. Off, the three police captains stay as they are.
# Ferrengi already regain 20% of hull max. This switch does not change that.
# On, Intrepid sits at StarDock. Valiant and Lexington sit at the next two
# sector ids. The live map's 289 and 379 were that game's placement.
FED_SHIPS_MODE = "legacy"  # "legacy" | "live"


def fed_ships_live() -> bool:
    return FED_SHIPS_MODE == "live" or tw2002_live_profile() or v311_profile()


# planet-class-types-v1. Off, genesis still rolls every class, costs 4 turns,
# and a good trader gains 10 alignment. The class M colonist count stays 1,000.
# On, a new planet is M or U, the launch costs no turn and 10 alignment,
# a freighter holds one torpedo, and the torpedo costs 20,000.
# Class U level 1 and the M and U product caps were already in the tables.
PLANET_CLASS_MODE = "legacy"  # "legacy" | "live"


def planet_class_live() -> bool:
    return PLANET_CLASS_MODE == "live" or tw2002_live_profile()


# offline-turn-regen-v1. Off, a new day still refills every turn.
# On, spent turns come back across the day, about 10 an hour when the
# cap is 250, and never past the cap. A new day does not refill them.
# 194 turns in half an hour at a 50,000 cap does not match this rate
# (that rate would return about 1,042). No second rate was measured.
TURN_REGEN_MODE = "legacy"  # "legacy" | "live"
TURN_REGEN_DAY_SECONDS = 24 * 3600


def turn_regen_live() -> bool:
    return TURN_REGEN_MODE == "live" or tw2002_live_profile() or v311_profile()


def regen_now() -> float:
    """Clock for turn regen and planet accrual. A scripted match replaces this so two runs agree."""
    import time
    return time.time()


# detect-gear-v1. Off, the shop prices stay as written above.
# On, a disruptor is 6,000, a psychic probe is 10,000, and an ether probe
# is 3,000. Density, holo, cloak, beacon, and corbomite already match.
# A planet scanner's effect was not measured, so it is not sold.
# The 15,000 atomic is a planet killer. This copy's detonator is not that
# weapon, so its price stays 60,000.
DETECT_GEAR_MODE = "legacy"  # "legacy" | "live"


def detect_gear_live() -> bool:
    return DETECT_GEAR_MODE == "live" or tw2002_live_profile() or v311_profile()


# avoid-list-v1. Off, the computer has no avoid list. A death does not
# record the sector, and a plotted course may pass through it.
# On, a sector can be added, 0 clears the list, a death adds that sector,
# and a plotted course goes around the list.
AVOID_MODE = "legacy"  # "legacy" | "live"


def avoid_live() -> bool:
    return AVOID_MODE == "live" or tw2002_live_profile() or v311_profile()


# bank-live-v1. Off, the account still stops at 500,000.
# On, there is no cap. The live game never showed a ceiling.
# There is still no fee and no interest. The bank is still only at StarDock.
# A typed amount can be larger than five digits. The five-digit cut was the
# live input box, and a second deposit already moves the rest.
# The daily tax stays the one cash-tax-v1 measured. This switch does not change it.
BANK_LIVE_MODE = "legacy"  # "legacy" | "live"


def bank_live() -> bool:
    return BANK_LIVE_MODE == "live" or tw2002_live_profile()


# seat-deadline-autopass-v1. Off, a human or a bot still uses the deadline
# the match already set. On, that wait is 75 seconds. Three misses in a row
# and the seat is passed for the rest of the day. A new day clears the count.
SEAT_DEADLINE_MODE = "legacy"  # "legacy" | "live"
SEAT_DEADLINE_S = 75
SEAT_DEADLINE_STREAK = 3


def seat_deadline_live() -> bool:
    mode = _forced_mode("TW2K_SEAT_DEADLINE_MODE", SEAT_DEADLINE_MODE)
    if mode == "off":
        return False
    return mode == "live" or tw2002_live_profile()


# async-days-v1. Off, seats still move one at a time and a day ends only
# when every seat is out of turns. On, the seats answer together and the
# day also ends when the clock hits the cap. Answers are applied in seat
# order, so a code-only game stays repeatable.
ASYNC_DAY_MODE = "legacy"  # "legacy" | "live"
ASYNC_DAY_CAP_S = 20 * 60


def async_day_live() -> bool:
    mode = _forced_mode("TW2K_ASYNC_DAY_MODE", ASYNC_DAY_MODE)
    if mode == "off":
        return False
    return mode == "live" or tw2002_live_profile()


# own-planet-landing-fighters-v1. Off, a fighter challenge still blocks
# every verb but the answer. On, the owner can land on their own planet
# anyway, and a toll challenge names the credit amount.
OWN_PLANET_FIGHTER_MODE = "legacy"  # "legacy" | "live"


def own_planet_fighter_live() -> bool:
    return OWN_PLANET_FIGHTER_MODE == "live" or tw2002_live_profile() or v311_profile()


# alliance-flow-v1. Off, a hail is only a message and an ally still
# fights the planet. On, an ally lands in peace, a declined proposal
# says so, and a proposal left overnight expires.
ALLIANCE_MODE = "legacy"  # "legacy" | "live"


def alliance_live() -> bool:
    return ALLIANCE_MODE == "live" or tw2002_live_profile()


# rank-display-options-v1. Off, the screens stay as they are.
# exp, networth, or both choose which place the screens show.
RANK_DISPLAY_MODE = "legacy"  # "legacy" | "exp" | "networth" | "both"


def rank_display() -> str:
    if RANK_DISPLAY_MODE == "legacy" and (tw2002_live_profile() or v311_profile()):
        return "exp"
    return RANK_DISPLAY_MODE


def rank_display_live() -> bool:
    return rank_display() != "legacy"


# api-arg-hardening-v1. Off, a queued action still answers accepted.
# On, a reject names the argument, a tight retry is refused, and 20
# identical rejects in a row are flagged.
API_ARGS_MODE = "legacy"  # "legacy" | "live"
API_RETRY_LIMIT = 30
API_RETRY_WINDOW_S = 10
API_REJECT_STREAK = 20


def api_args_live() -> bool:
    return API_ARGS_MODE == "live" or tw2002_live_profile() or v311_profile()


def async_day_should_roll(all_done: bool, elapsed_s: float) -> bool:
    if not async_day_live():
        return False
    return bool(all_done) or float(elapsed_s) >= float(ASYNC_DAY_CAP_S)


# planet-colonist-cap-fidelity-v1. Appended so later slices can rebase cleanly.
# The handbook, the Gypsy guide, and the modern manual agree: a class U planet
# holds 3,000 colonists. A class U citadel level 3 asks for 8,000 (S1; the
# stored table says 5,000, see CITADEL_TABLE_FIX_MODE), so that level cannot be started. Legacy keeps the handbook number. Live raises a
# class only when its handbook cap is below the most colonists any citadel
# level on that class asks for. Class U becomes 8,000 (level 5). Class M
# stays 30,000. Four sources say 30,000. The million figure is the unsettled
# citadel level-1 screen, not this cap.
PLANET_COLONIST_CAP_MODE = "legacy"  # "legacy" | "live"


def planet_colonist_cap_live() -> bool:
    """True when a class can hold every citadel level it is asked to build."""
    return PLANET_COLONIST_CAP_MODE == "live" or tw2002_live_profile() or v311_profile()


def planet_colonist_cap(class_id: str) -> int:
    """Colonists this class may hold. Legacy is the handbook. Live can go higher."""
    handbook = PLANET_MAX_COLONISTS[class_id]
    if not planet_colonist_cap_live():
        return handbook
    levels = CITADEL_CLASS_COSTS.get(class_id) or ()
    needed = max((int(row[0]) for row in levels), default=0)
    return max(handbook, needed)


# landed-state-v1. Appended so later slices can rebase cleanly.
# Legacy keeps a landing after the ship has warped away, and a warp from the
# surface is allowed. Live drops a landing whose planet is not in this sector,
# and a ship still on that planet must lift off before warp, trade, or an
# executing plot.
LANDED_STATE_MODE = "legacy"  # "legacy" | "live"


def landed_state_live() -> bool:
    """True when a landing has to match the sector the ship is in."""
    return LANDED_STATE_MODE == "live" or tw2002_live_profile() or v311_profile()


# planet-dividend-fidelity-v1. Appended so later slices can rebase cleanly.
# The credit dividend is not in the original. It stays on, because the
# recorded games already include it. "off" pays nothing. The baseline still
# moves, so turning it back on does not pay the missed days in one lump.
PLANET_DIVIDEND_PAY_MODE = "legacy"  # "legacy" | "off"


def planet_dividend_off() -> bool:
    """True when a planet's new value does not pay credits."""
    return PLANET_DIVIDEND_PAY_MODE == "off" or tw2002_live_profile() or v311_profile()


def _forced_mode(env_name: str, current: str) -> str:
    """A process env of legacy, live, or off beats the stored switch."""
    import os
    raw = (os.environ.get(env_name) or "").strip().lower()
    if raw in ("legacy", "live", "off"):
        return raw
    return current


# live-profile-pace-fix-v1. Appended so later slices can rebase cleanly.
# Off, a live opening still forces 250 turns and a spent day can roll
# again immediately. On, a requested turn count is kept, spent seats get
# their hourly turns back before the day is allowed to roll, and a day
# that just rolled waits out that hour instead of racing.
LIVE_PACE_MODE = "legacy"  # "legacy" | "live"


def live_pace() -> bool:
    """True when a live game waits on the clock instead of racing the day."""
    return LIVE_PACE_MODE == "live" or tw2002_live_profile() or v311_profile()


# planet-value-cap-v1. Appended so later slices can rebase cleanly.
# "legacy" is the score the recorded games already use. The other names
# are options for a game where a planet's stock and fighters dwarf the
# ship. The original ranks by experience, so the live profile uses that
# one. The growth dividend still uses the old planet value.
PLANET_VALUE_SCORE_MODE = "legacy"  # "legacy" | "stock_cap" | "no_fighters" | "colonists" | "experience"


def planet_value_score_mode() -> str:
    """Which number ranks a seat when the day cap hits."""
    mode = PLANET_VALUE_SCORE_MODE
    if mode != "legacy":
        return mode
    if tw2002_live_profile() or v311_profile():
        return "experience"
    return "legacy"


def planet_value_scored() -> bool:
    """True when rank is not the recorded credit score."""
    return planet_value_score_mode() != "legacy"


# planet-realtime-prod-v1. Appended so later slices can rebase cleanly.
# "legacy": a planet's goods and colonists change when the day ticks.
# "live": that same daily amount also accrues as time passes, spread across
# 24 hours. The day tick pays only the seconds the clock has not paid.
# A long pause pays at most one day, then waits for the day to tick.
PLANET_REALTIME_PROD_MODE = "legacy"  # "legacy" | "live"


def planet_realtime_prod() -> bool:
    """True when planet goods accrue during the day, not only at midnight."""
    return PLANET_REALTIME_PROD_MODE == "live" or tw2002_live_profile()


# universe-topology-v1. Appended so later slices can rebase cleanly.
# "legacy": every sector has a way out, and a way back to sector 1.
# "live": a sector may have no way out, a one-way may trap a ship, and a
# few tunnels join distant sectors. One pair is closed into a bubble.
# FedSpace stays two-way. Sector 1 can still reach every sector.
UNIVERSE_TOPOLOGY_MODE = "legacy"  # "legacy" | "live"


def universe_topology_live() -> bool:
    """True when the map may contain dead ends, traps, tunnels, and a bubble."""
    return UNIVERSE_TOPOLOGY_MODE == "live" or tw2002_live_profile()


# planet-scanner-v1. Appended so later slices can rebase cleanly.
# "legacy": StarDock does not sell a planet scanner, and a stranger still
# cannot read a planet's fighters. "live": the scanner costs 30,000.
# It shows the fighters of a planet that has no shields. A shielded
# planet stays dark. Live TWGS sold it at 30,000 (REPORT.md).
PLANET_SCANNER_MODE = "legacy"  # "legacy" | "live"
PLANET_SCANNER_COST = 30_000


def planet_scanner_live() -> bool:
    """True when StarDock sells a planet scanner."""
    return PLANET_SCANNER_MODE == "live" or tw2002_live_profile() or v311_profile()


# scanner-fog-v1. Appended so later slices can rebase cleanly.
# "legacy": a sector list still names a planet's owner, and the owner
# still sees fighters without landing. "live": owner, fighters, and
# shields stay hidden unless you have landed, or a planet scanner is
# reading a planet that has no shields. The scanner shows owner and
# fighters, not shields.
SCANNER_FOG_MODE = "legacy"  # "legacy" | "live"


def scanner_fog_live() -> bool:
    """True when a planet's owner and fighters are hidden until a scan or a landing."""
    return SCANNER_FOG_MODE == "live" or tw2002_live_profile() or v311_profile()


# citadel-parking-v1. Appended so later slices can rebase cleanly.
# "legacy": landing on a citadel leaves the ship in the sector.
# "live": a ship on your own level-1 citadel is inside it. A Fed tow
# skips it, and another trader cannot attack it there. A hull you
# leave on that citadel can be boarded again only from that citadel.
CITADEL_PARK_MODE = "legacy"  # "legacy" | "live"


def citadel_park_live() -> bool:
    """True when a ship on your citadel is parked inside it."""
    return CITADEL_PARK_MODE == "live" or tw2002_live_profile() or v311_profile()


# radio-channels-v1. Appended so later slices can rebase cleanly.
# "legacy": corp chat is the one memo. "live": a corp shares a subspace
# channel from 0 to 60000. Only corp mates tuned to that channel hear it.
# The Bible names that range. CONFIRMED as corp chat.
RADIO_CHANNEL_MODE = "legacy"  # "legacy" | "live"
RADIO_CHANNEL_MAX = 60_000


def radio_channel_live() -> bool:
    """True when corp mates can share a subspace radio channel."""
    return RADIO_CHANNEL_MODE == "live" or tw2002_live_profile() or v311_profile()


# daily-stats-v1. Appended so later slices can rebase cleanly.
# "legacy": the seat does not get the V-screen counts.
# "live": the observation carries ports, planets, traders, aliens,
# and fighters and mines in use. A live game showed the port count
# and a fighters-and-mines line. Whether cargo fighters count the
# same way as deployed ones is UNVERIFIED; this count includes both.
# Fighters on unmanned ships are left out (docs wiki Interdictor_Cruiser,
# GAP 14.4). That exclusion is display-only and rides on this switch.
DAILY_STATS_MODE = "legacy"  # "legacy" | "live"


def daily_stats_live() -> bool:
    """True when the V-screen counts are on the observation."""
    return DAILY_STATS_MODE == "live" or tw2002_live_profile() or v311_profile()


# fedcomm-v1. Appended so later slices can rebase cleanly.
# "legacy": Extern still clears the lanes and keeps the old sweep note.
# "live": the owner also gets the Federation line about the lane.
FEDCOMM_MODE = "legacy"  # "legacy" | "live"
FEDCOMM_MSL_LINE = "Don't deploy fighters in the MSL's."


def fedcomm_live() -> bool:
    """True when a lane sweep also sends the Federation note."""
    return FEDCOMM_MODE == "live" or tw2002_live_profile() or v311_profile()


# corp-rankings-v1. Appended so later slices can rebase cleanly.
# "legacy": the seat does not get a corporation ranking.
# "live": corporations are listed by combined member experience,
# with the members' alignment added together.
CORP_RANK_MODE = "legacy"  # "legacy" | "live"


def corp_rank_live() -> bool:
    """True when the corporation ranking is on the observation."""
    return CORP_RANK_MODE == "live" or tw2002_live_profile() or v311_profile()


# gold-aliens-v1. Appended so later slices can rebase cleanly.
# "legacy": a kill does not start a race grudge.
# "live": destroying an alien while another of that race is in the
# sector puts the killer at the top of that race's list of ten.
# The list is not saved. How much harder they hit is not published,
# so the fight itself does not change. Banding has no published
# group size, so clusters are not invented.
GOLD_ALIEN_MODE = "legacy"  # "legacy" | "live"
GOLD_GRUDGE_LIMIT = 10


def gold_alien_live() -> bool:
    """True when a witnessed alien kill starts a race grudge."""
    return GOLD_ALIEN_MODE == "live" or tw2002_live_profile()


# class-m-fidelity-v1. Appended so later slices can rebase cleanly.
# Ben's rule: the original counts class M colonists in thousands.
# The live screen's 1,000,000 is the handbook's 1,000.
# "legacy": class M still uses the handbook unit as stored.
# "live": a citadel level asks for that many thousands of people,
# each product pool holds 30,000 thousand, and only the extra
# above that pool dies. The 5% on the extra is not a published rate.
CLASS_M_FIDELITY_MODE = "legacy"  # "legacy" | "live"
CLASS_M_PEOPLE_PER_THOUSAND = 1_000
CLASS_M_CATEGORY_CAP = 30_000 * CLASS_M_PEOPLE_PER_THOUSAND


def class_m_fidelity_live() -> bool:
    """True when class M uses people, not the handbook unit, as stored."""
    return CLASS_M_FIDELITY_MODE == "live" or tw2002_live_profile() or v311_profile()


# port-stock-and-trade-reason-v1. Appended so later slices can rebase cleanly.
# "legacy": a port opens empty and a day adds stock on both sides.
# "live": a selling side opens full and regains 5% of max a day.
# A buying side opens wanting a full load, and a day gives room back.
# It never takes room away. PORT_OPEN_STOCK_MODE stays legacy.
PORT_STOCK_FIDELITY_MODE = "legacy"  # "legacy" | "live"


def port_stock_fidelity_live() -> bool:
    """True when selling ports open full and buying ports open hungry."""
    return PORT_STOCK_FIDELITY_MODE == "live" or tw2002_live_profile() or v311_profile()


# ship-exit-v1. Off, Jettison and Self-destruct stay "not in this game".
# On, jettison dumps cargo and self-destruct costs half your experience
# and alignment and keeps you out today and tomorrow.
SHIP_EXIT_MODE = "legacy"  # "legacy" | "tw2002"


def ship_exit_on() -> bool:
    """True when Jettison and Self-destruct are real commands."""
    return SHIP_EXIT_MODE == "tw2002" or tw2002_live_profile() or v311_profile()


# combat-clarity-v1. Off, a same-sector rival's fighters and shields stay out of
# the seat view, so the bank pin stays put. On, the sector line can show them.
RIVAL_STRENGTH_MODE = "legacy"  # "legacy" | "live"


def rival_strength_live() -> bool:
    """True when a trader in your sector shows fighters and shields."""
    return RIVAL_STRENGTH_MODE == "live" or tw2002_live_profile() or v311_profile()


# combat-clarity-v1. Legacy keeps today's kill: the killer is paid the victim's
# cash on hand (DEATH_CREDITS_RECOVER_PCT, currently 100) through bank.on_ship_lost.
# tw2002 pays the killer nothing. Holds salvage is a different path and stays.
# v311-kill-cash-addendum-v1 (NOTE 59): V311_PROFILE turns it on. RULINGS_v311.md
# Addendum A, live v3.34b: "in normal play the killer gets nothing from a logged-off
# victim, and the victim's on-hand cash is destroyed (the pod has 25 credits)".
KILL_CASH_MODE = "legacy"  # "legacy" | "tw2002"


def kill_cash_held() -> bool:
    """True when a kill does not hand the victim's cash to the killer."""
    return KILL_CASH_MODE == "tw2002" or tw2002_live_profile() or v311_profile()


# hazards-scans-v1. Legacy keeps today's landing: a rival planet whose
# fighters are not defending is claimed by landing, fighters included.
# tw2002 fights the planet's fighters and shields first and claims it
# only if that fight clears them.
PLANET_LANDING_COMBAT_MODE = "legacy"  # "legacy" | "tw2002"


def planet_landing_combat_on() -> bool:
    """True when landing on a defended planet fights before it can be claimed."""
    return PLANET_LANDING_COMBAT_MODE == "tw2002" or tw2002_live_profile() or v311_profile()


# hazards-scans-v1. Legacy keeps today's entry clash: one exchange, and a
# wiped group is removed. The published wave (shields absorb, survivors
# stay) is not a number in the local references, so tw2002 only spends
# the attacker's losses against shields before the same exchange. A wiped
# group is still removed. Ben decides any flip.
OFFENSIVE_CLASH_MODE = "legacy"  # "legacy" | "tw2002"


def offensive_clash_held() -> bool:
    """True when offensive sector fighters send the RULINGS s6 wave (combat._offensive_wave_tw2002)."""
    return OFFENSIVE_CLASH_MODE == "tw2002" or tw2002_live_profile() or v311_profile()


# hazards-scans-v1. Legacy keeps mine hits, landings, and fighter clashes
# on the actor and the people in the sector. tw2002 also shows the mine
# owner, the planet's old owner, and the fighter group's owner.
OWNER_HAZARD_NOTICE_MODE = "legacy"  # "legacy" | "tw2002"


def owner_hazard_notice_on() -> bool:
    """True when the owner is told about a landing, a clash, or a mine hit."""
    return OWNER_HAZARD_NOTICE_MODE == "tw2002" or tw2002_live_profile() or v311_profile()


# d8-combat-planet-fixes-v1. Legacy flees after the exchange, on whatever
# fighters and shields are left. tw2002 flees only when the fighters sent
# are strictly more than 1.25 times the defender's fighters plus shields
# before the hit (GAP 5.9).
SHIP_FLEE_MODE = "legacy"  # "legacy" | "tw2002"


def ship_flee_published() -> bool:
    """True when a ship flees on the fighters sent, against the strength before the hit."""
    return SHIP_FLEE_MODE == "tw2002" or tw2002_live_profile() or v311_profile()


# d8. Legacy still lets a citadel below level 5 take planet shields.
# tw2002 refuses: the Planetary Shielding System is level 5.
PLANET_SHIELD_MODE = "legacy"  # "legacy" | "tw2002"


def planet_shield_l5() -> bool:
    """True when planet shields require a level 5 citadel."""
    return PLANET_SHIELD_MODE == "tw2002" or tw2002_live_profile() or v311_profile()


# d8. Legacy Ferrengi hunt only on their own roam. tw2002 also engages an
# armed trader who enters their sector, and strikes back after an attack.
FERRENGI_ENGAGE_MODE = "legacy"  # "legacy" | "tw2002"


def ferrengi_engage_on() -> bool:
    """True when a Ferrengi engages on entry and retaliates in the same sector."""
    return FERRENGI_ENGAGE_MODE == "tw2002" or tw2002_live_profile() or v311_profile()


# d8. Legacy siege facts stay the after-counts already on the event.
# tw2002 adds how many fighters and shields each side lost.
SIEGE_REPORT_MODE = "legacy"  # "legacy" | "tw2002"


def siege_report_on() -> bool:
    """True when a landing fight reports the losses on both sides."""
    return SIEGE_REPORT_MODE == "tw2002" or tw2002_live_profile() or v311_profile()


# note49-polish-v1. Legacy still burns max(1, colonists // 100) organics
# and grows 5% only while organics remain. tw2002 does not eat organics.
# Below half of PLANET_MAX_COLONISTS the colony grows about 5% a day, and
# above that half it shrinks about 5% a day. The handbook states the half
# cap and a proportional rate, and this engine already used 5% for that
# shape. Ben decides any flip.
PLANET_GROWTH_MODE = "legacy"  # "legacy" | "tw2002"


def planet_growth_tw2002() -> bool:
    """True when colonists follow the half-cap rule and do not eat organics."""
    return PLANET_GROWTH_MODE == "tw2002" or tw2002_live_profile() or v311_profile()


# cockpit-ai-seat-v1. Legacy games do not start this seat. tw2002 lets a
# test run the client that reads only the cockpit harness. The server never
# constructs that client. Ben decides any flip.
AI_COCKPIT_SEAT_MODE = "legacy"  # "legacy" | "tw2002"


def ai_cockpit_seat_on() -> bool:
    """True when a test may run the cockpit-only seat. Default games never do."""
    return AI_COCKPIT_SEAT_MODE == "tw2002" or tw2002_live_profile()


# lobby-ai-opponents-v1 (NOTE 100). Off leaves the Galaxy War Command form and
# the worker command as they are today. On lets a lobby game add 0-4
# cockpit-only AI seats. Stored default off. V311_PROFILE does not turn this
# on, and it is not a profile helper. The server never stores or ships an LLM key.
LOBBY_AI_SEAT_MODE = "off"  # "off" | "on"

# UNVERIFIED: one model call per turn is the planning estimate. A refused
# turn that is chosen again can spend another call.
LOBBY_AI_CALLS_PER_TURN = 1
# Per game, across that game's LLM seats. Past this the seat plays heuristic.
# UNVERIFIED: 400 is a hosting guard, not a measured TWGS figure.
LOBBY_AI_CALL_CAP = 400
# Calls that may start in any 60-second window. A turn past the limit plays heuristic.
# UNVERIFIED: 6 per minute is a hosting guard.
LOBBY_AI_CALLS_PER_MINUTE = 6


def lobby_ai_seat_on() -> bool:
    """True only when this process set LOBBY_AI_SEAT_MODE to on."""
    return LOBBY_AI_SEAT_MODE == "on"


# cockpit-gaps-v1 (NOTE 56). Legacy observations carry no cockpit block.
# tw2002 adds one block to the seat's own harness observation: the last
# action's verdict, the port's quote and counter, this seat's last-seen
# prices, and the StarDock hold total. Ben decides any flip.
COCKPIT_FIELDS_MODE = "legacy"  # "legacy" | "tw2002"


def cockpit_fields_on() -> bool:
    """True when the harness observation carries the cockpit block."""
    return COCKPIT_FIELDS_MODE == "tw2002" or tw2002_live_profile()


# v311-rulings-v1 (NOTE 57) item 6. RULINGS_v311.md s7: "good traders (alignment above 0)
# carrying over 49,999 credits on the ship pay 10% of the cash on hand, once per day when
# they enter; +1 alignment per 1,500 credits paid; evil traders are never taxed. MBBS mode
# uses 5% over 100,000 (not the default)." Legacy keeps the MBBS figures above.
TAX_RULE_MODE = "legacy"  # "legacy" | "v311"
V311_TAX_RATE_PCT = 10
V311_TAX_OVER = 49_999
V311_TAX_MIN_ALIGNMENT = 1


def tax_v311() -> bool:
    """True when the nightly tax uses the v3 TWGS default (10% at 50,000 or more, good only)."""
    return TAX_RULE_MODE == "v311" or tw2002_live_profile() or v311_profile()


def tax_terms() -> tuple[int, int, int]:
    """(rate percent, cash a trader must carry MORE than, lowest taxed alignment)."""
    if tax_v311():
        return int(V311_TAX_RATE_PCT), int(V311_TAX_OVER), int(V311_TAX_MIN_ALIGNMENT)
    return int(TAX_RATE_PCT), int(TAX_THRESHOLD), int(TAX_MIN_ALIGNMENT)


# v311-rulings-v1 (NOTE 57) item 8. One switch for a game run on the v3.11 rulings:
# RULINGS_v311.md s2-s7 and Addendum A plus every MASTER_PLAN switch marked yes. Its own
# switch, separate from TW2002_LIVE_PROFILE. docs/plans/v311-profile-v1.md lists the set
# with reasons.
V311_PROFILE = "legacy"  # "legacy" | "v311"


def v311_profile() -> bool:
    """True when a game wants the documented v3.11 switch set (V311_PROFILE_HELPERS)."""
    return V311_PROFILE == "v311"


# helper -> (switch it reads, why it is in the set). Every helper here returns True
# under V311_PROFILE alone. rank_display() and planet_value_score_mode() also return
# "exp" and "experience". citadel_fidelity_rules is already on by default.
V311_PROFILE_HELPERS: dict[str, tuple[str, str]] = {
    "starting_package_live": ("STARTING_PACKAGE_MODE", "RULINGS s2"),
    "citadel_days_live": ("CITADEL_DAYS_MODE", "RULINGS s3"),
    "citadel_fidelity_rules": ("CITADEL_COST_MODE", "RULINGS s3; MASTER_PLAN yes, after check"),
    "ship_roster_live": ("SHIP_ROSTER_MODE", "RULINGS s4"),
    "turn_regen_live": ("TURN_REGEN_MODE", "RULINGS s5"),
    "live_pace": ("LIVE_PACE_MODE", "RULINGS s5"),
    "offensive_clash_held": ("OFFENSIVE_CLASH_MODE", "RULINGS s6"),
    "tax_v311": ("TAX_RULE_MODE", "RULINGS s7"),
    "fedspace_deploy_live": ("FEDSPACE_DEPLOY_MODE", "MASTER_PLAN yes"),
    "port_class_live": ("PORT_CLASS_MAP_MODE", "MASTER_PLAN yes"),
    "haggle_window_live": ("HAGGLE_WINDOW_MODE", "MASTER_PLAN yes"),
    "own_planet_turn_live": ("OWN_PLANET_TURN_MODE", "MASTER_PLAN yes"),
    "trade_in_live": ("TRADE_IN_MODE", "MASTER_PLAN yes"),
    "hardware_price_live": ("HARDWARE_PRICE_MODE", "MASTER_PLAN yes"),
    "planet_shields_active": ("PLANET_SHIELD_ACTIVE_MODE", "MASTER_PLAN yes"),
    "genesis_score_fair": ("GENESIS_SCORE_MODE", "MASTER_PLAN yes (fair)"),
    "action_result_report": ("ACTION_RESULT_MODE", "MASTER_PLAN yes for AI-seat games (report)"),
    "assign_pool_fix_live": ("ASSIGN_POOL_FIX_MODE", "MASTER_PLAN yes"),
    "hold_rules_live": ("HOLD_RULES_MODE", "MASTER_PLAN yes"),
    "planet_nw_live": ("PLANET_NW_MODE", "MASTER_PLAN yes"),
    "port_price_live": ("PORT_PRICE_MODE", "MASTER_PLAN yes"),
    "port_regen_live": ("PORT_REGEN_MODE", "MASTER_PLAN yes"),
    "shop_price_live": ("SHOP_PRICE_MODE", "MASTER_PLAN yes"),
    "genesis_start_live": ("GENESIS_START_MODE", "MASTER_PLAN yes"),
    "terra_colonist_live": ("TERRA_COLONIST_MODE", "MASTER_PLAN yes"),
    "planet_prod_live": ("PLANET_PROD_MODE", "MASTER_PLAN yes"),
    "citadel_perk_live": ("CITADEL_PERK_MODE", "MASTER_PLAN yes"),
    "exp_score_live": ("EXP_SCORE_MODE", "MASTER_PLAN yes, Ben confirm"),
    "death_pod_live": ("DEATH_POD_MODE", "MASTER_PLAN yes"),
    "port_attack_live": ("PORT_ATTACK_MODE", "MASTER_PLAN yes"),
    "haggle_live": ("HAGGLE_LIVE_MODE", "MASTER_PLAN yes"),
    "discovery_exp_live": ("DISCOVERY_EXP_MODE", "MASTER_PLAN yes"),
    "fed_ships_live": ("FED_SHIPS_MODE", "MASTER_PLAN yes"),
    "detect_gear_live": ("DETECT_GEAR_MODE", "MASTER_PLAN yes"),
    "avoid_live": ("AVOID_MODE", "MASTER_PLAN yes"),
    "own_planet_fighter_live": ("OWN_PLANET_FIGHTER_MODE", "MASTER_PLAN yes"),
    "rank_display_live": ("RANK_DISPLAY_MODE", "MASTER_PLAN yes (exp)"),
    "api_args_live": ("API_ARGS_MODE", "MASTER_PLAN yes for AI-seat games"),
    "planet_colonist_cap_live": ("PLANET_COLONIST_CAP_MODE", "MASTER_PLAN yes"),
    "landed_state_live": ("LANDED_STATE_MODE", "MASTER_PLAN yes"),
    "planet_dividend_off": ("PLANET_DIVIDEND_PAY_MODE", "MASTER_PLAN yes (off)"),
    "planet_value_scored": ("PLANET_VALUE_SCORE_MODE", "MASTER_PLAN yes (experience)"),
    "planet_scanner_live": ("PLANET_SCANNER_MODE", "MASTER_PLAN yes"),
    "scanner_fog_live": ("SCANNER_FOG_MODE", "MASTER_PLAN yes"),
    "citadel_park_live": ("CITADEL_PARK_MODE", "MASTER_PLAN yes"),
    "radio_channel_live": ("RADIO_CHANNEL_MODE", "MASTER_PLAN yes"),
    "daily_stats_live": ("DAILY_STATS_MODE", "MASTER_PLAN yes"),
    "fedcomm_live": ("FEDCOMM_MODE", "MASTER_PLAN yes"),
    "corp_rank_live": ("CORP_RANK_MODE", "MASTER_PLAN yes"),
    "class_m_fidelity_live": ("CLASS_M_FIDELITY_MODE", "MASTER_PLAN yes (Ben NOTE 19)"),
    "port_stock_fidelity_live": ("PORT_STOCK_FIDELITY_MODE", "MASTER_PLAN yes"),
    "ship_exit_on": ("SHIP_EXIT_MODE", "MASTER_PLAN yes"),
    "rival_strength_live": ("RIVAL_STRENGTH_MODE", "MASTER_PLAN yes"),
    "planet_landing_combat_on": ("PLANET_LANDING_COMBAT_MODE", "MASTER_PLAN yes"),
    "owner_hazard_notice_on": ("OWNER_HAZARD_NOTICE_MODE", "MASTER_PLAN yes"),
    "ship_flee_published": ("SHIP_FLEE_MODE", "MASTER_PLAN yes"),
    "planet_shield_l5": ("PLANET_SHIELD_MODE", "MASTER_PLAN yes"),
    "ferrengi_engage_on": ("FERRENGI_ENGAGE_MODE", "MASTER_PLAN yes"),
    "siege_report_on": ("SIEGE_REPORT_MODE", "MASTER_PLAN yes"),
    "planet_growth_tw2002": ("PLANET_GROWTH_MODE", "MASTER_PLAN yes"),
    "kill_cash_held": ("KILL_CASH_MODE", "RULINGS Addendum A (killer not paid)"),
    "pod_cash_live": ("POD_CASH_MODE", "RULINGS Addendum A (the pod has 25 credits)"),
    "yard_stats_on": ("YARD_STATS_MODE", "RULINGS s4 (the yard shows the s4 roster figures)"),
    "citadel_table_fix_live": ("CITADEL_TABLE_FIX_MODE", "S1 section VII (class U citadel L3 colonists)"),
    "home_planet_live": ("HOME_PLANET_MODE", "REVISION.TXT 1558 and the new-character transcript (45/65/81 thousand)"),
    "class_m_nw_units": ("CLASS_M_NW_MODE", "S1 / NOTE 19 (class M net worth is thousands, not people)"),
    "class_m_drop_units": ("CLASS_M_DROP_MODE", "S1 / NOTE 19 and terra-colonists-v1 (a hold of Terra colonists is one thousand people)"),
    "class_m_genesis_units": ("CLASS_M_GENESIS_MODE", "S1 class M L1 is 1,000 thousand; the 2,500 seed is handbook units"),
    "corp_exp_penalty_taken": ("CORP_EXP_PENALTY_MODE", "Hekate TWGS table: the event names the experience taken, not the formula"),
    "corp_leaver_to_ceo": ("CORP_LEAVER_DEPLOYMENTS", "live TWGS v3.34b: a leaver's corporate fighters stay with the corp under the C.E.O."),
    "corp_join_check": ("CORP_ALIGNMENT_RULE", "EIS join: signs must agree, 0 fits either side, later drift is not an oust"),
    "mixed_corp_least_extreme": ("MIXED_CORP_EXP_RULE", "Cabal MIN(ABS(lowest alignment), highest alignment) / 4"),
    "alien_combat_fix_live": ("ALIEN_COMBAT_FIX_MODE", "NOTE 71: alien fighters trade 1:1 and shields soak first"),
    "haggle_counter_live": ("HAGGLE_COUNTER_MODE", "NOTE 71: a port counter keeps the turn; holds are checked first"),
    "bot_hazard_memory_live": ("BOT_HAZARD_MEMORY_MODE", "NOTE 71: a bot does not flee back into Ferrengal or a mined sector"),
    "trade_in_parts_live": ("TRADE_IN_PARTS_MODE", "NOTE 73: the yard itemises the old ship"),
    "trader_rank_list_live": ("TRADER_RANK_LIST_MODE", "NOTE 73: the computer lists every trader by experience"),
    "nw_estimate_live": ("NW_ESTIMATE_MODE", "NOTE 73: the net-worth estimate follows what you paid"),
    "seat_idle_start_live": ("SEAT_IDLE_START_MODE", "NOTE 73: a seat's idle clock starts at the first connect"),
    "bot_diplomacy_live": ("BOT_DIPLOMACY_MODE", "NOTE 73: a code bot answers a hail and an alliance"),
    "day_roll_clock_live": ("DAY_ROLL_CLOCK_MODE", "NOTE 74: the day rolls on the clock while a seat holds the turn"),
    "start_colonist_nw_live": ("START_COLONIST_NW_MODE", "NOTE 75: free start colonists are left out of net worth"),
    "port_buy_price_anchor_on": (
        "PORT_BUY_PRICE_ANCHOR_MODE",
        "D25-1 (NOTE 69): hungry buy quotes use the live anchors, not the 1.93x full-hold curve",
    ),
    # NOTE 82 rows 94, 96, 97. Rows 95 and 98 were already on this tip.
    "bust_record_clear_live": (
        "BUST_CLEAR_MODE",
        "NOTE 82 TRD-k: a game may clear bust records daily or every 7 days",
    ),
    "ship_chart_cap_live": (
        "SHIP_CHART_CAP_MODE",
        "NOTE 82 SD-e: an ether probe cap of 25, with the Bible chart caps",
    ),
    "corp_planet_disband_v306": (
        "CORP_PLANET_DISBAND_MODE",
        "NOTE 82 PLN-q: on disband the C.E.O.'s sector stays, the rest go unclaimed",
    ),
    # NOTE 79 rows 90 and 93. Rows 91 and 92 were already on this tip.
    "photon_follow_damp_live": (
        "PHOTON_FOLLOW_DAMP_MODE",
        "NOTE 79 SD-o: a ship that enters a live photon wave has the quasar damped",
    ),
    "death_delay_live": (
        "DEATH_DELAY_MODE",
        "NOTE 79 CMB-n: a pod can be locked out for N midnights",
    ),
    "treasury_cap_live": (
        "TREASURY_CAP_MODE",
        "PLN-r (NOTE 78): S1 treasury cap is 999,999,999,999,999",
    ),
    "course_max_live": (
        "COURSE_MAX_MODE",
        "MOV-g (NOTE 78): a plotted course longer than 45 hops is refused (45 UNVERIFIED for 3.11)",
    ),
    "big_bang_density_live": (
        "BIG_BANG_DENSITY_MODE",
        "MOV-h, MOV-i (NOTE 78): ports about 40%, planets up to 20%, no decorative Fed ports in 2-10",
    ),
    "one_way_share_live": (
        "ONE_WAY_SHARE_MODE",
        "MOV-f (NOTE 78): one-way share about 3% when the game does not set one_way_fraction",
    ),
    "atomic_detonator_live": (
        "ATOMIC_DETONATOR_MODE",
        "SD-l (NOTE 78): the detonator is the planet killer; the port-nuke atomic mine is retired",
    ),
    "special_hull_rules_on": (
        "SPECIAL_HULL_RULES_MODE",
        "NOTE 86 CMB-m: an Interdictor holds every other ship, and a Tholian defends a corp planet at 4:1",
    ),
    "ferrengi_grudge_on": (
        "FERRENGI_GRUDGE_MODE",
        "NOTE 86 FER-c: a Ferrengi that was attacked seeks that trader, and neighbours band on a strong target",
    ),
    "ferrengi_pace_on": (
        "FERRENGI_PACE_MODE",
        "NOTE 86 FER-d: Ferrengi move 1 in 20 every 30 s of the live clock, and regenerate 20% a day",
    ),
    "probe_shootdown_live": (
        "PROBE_SHOOTDOWN_MODE",
        "NOTE 85 MOV-c: a shot-down probe names the sector and who owned the fighters",
    ),
    "ferrengi_reward_live": (
        "FERRENGI_REWARD_MODE",
        "NOTE 85 FER-e: alignment up for a good trader, experience by hull",
    ),
    "ferrengal_quasar_live": (
        "FERRENGAL_QUASAR_MODE",
        "NOTE 85 FER-h: Ferrengal fires a quasar shot at a ship that enters",
    ),
    "autopilot_port_stop_live": (
        "AUTOPILOT_PORT_STOP_MODE",
        "NOTE 90 MOV-k: an express warp pauses at a port sector when the cockpit asks it to",
    ),
    "genesis_name_live": (
        "GENESIS_NAME_MODE",
        "NOTE 90: a Genesis deploy can take the name the player typed",
    ),
    # NOTE 98 rows 138 and 142. Rows 139, 140 and 141 were already the stored rule.
    "port_attack_all_classes": (
        "PORT_ATTACK_ALL_CLASSES_MODE",
        "NOTE 98 TRD-n: a port with a known rating can be destroyed; unmeasured classes stay unset",
    ),
    "port_class_number_fix": (
        "PORT_CLASS_NUMBER_FIX_MODE",
        "NOTE 98 TRD-c: live class 7 is SSS while StarDock stays id 8",
    ),
    "class0_hold_formula_live": (
        "CLASS0_HOLD_FORMULA_MODE",
        "NOTE 87: Class 0 holds use the cabal B*H + 20*H*(H-1)/2 total",
    ),
    "haggle_exp_live": (
        "HAGGLE_EXP_MODE",
        "NOTE 87: a good haggle is +1 experience and a great one is +2",
    ),
    "ship_rename_live": (
        "SHIP_RENAME_MODE",
        "NOTE 87: the shipyard sells a new registration and ship name",
    ),
    "exp_sources_live": (
        "EXP_SOURCES_MODE",
        "NOTE 102 GAP 9.2: destroying a port pays 50 experience and costs 50 alignment",
    ),
    "special_port_defence_live": (
        "SPECIAL_PORT_DEFENCE_MODE",
        "NOTE 102 GAP 11.10: StarDock and Class 0 take a huge fighter budget and the Feds rebuild them",
    ),
    "planet_collision_live": (
        "PLANET_COLLISION_MODE",
        "NOTE 102 GAP 6.6: an overloaded sector can lose two planets at Extern",
    ),
    "planet_bust_exp_live": (
        "PLANET_BUST_EXP_MODE",
        "NOTE 102 GAP 14.3: the owner can create and destroy a planet for 75 experience",
    ),
    "bot_bank_float_live": (
        "BOT_BANK_FLOAT_MODE",
        "NOTE 88 row 114: a code bot keeps a full hold at its route buy price before it deposits",
    ),
    "capture_credit_line_live": (
        "CAPTURE_CREDIT_LINE_MODE",
        "NOTE 105: a capture already takes credits on hand the same way as a destroy; the cockpit says so",
    ),
    "mail_live": (
        "MAIL_MODE",
        "NOTE 103: a hail flashes for an open cockpit and waits as mail when the seat is offline",
    ),
    "legacy_day_clock_live": (
        "LEGACY_DAY_CLOCK_MODE",
        "NOTE 104: a legacy game with its own day length rolls on that clock while a seat holds the turn",
    ),
    "price_scale_live": (
        "PRICE_SCALE_MODE",
        "NOTE 112 GAP 2.5: each side of a trade quotes the economy2 100% chart, then the existing slope",
    ),
    "colonist_units_live": (
        "COLONIST_UNITS_MODE",
        "NOTE 89: a non-M drop turns Terra people into handbook colonists, one thousand per hold",
    ),
    "colonist_nw_units": (
        "COLONIST_NW_UNITS_MODE",
        "NOTE 89: cargo colonists stored as people are scored as handbook thousands",
    ),
    "evil_trade_loop_live": (
        "EVIL_TRADE_LOOP_MODE",
        "NOTE 115 GAP 14.5: a negative-alignment seat steals, dumps, and beams, or robs and beams",
    ),
    "fedsafe_fighter_cap_live": (
        "FEDSAFE_FIGHTER_CAP_MODE",
        "NOTE 117 GAP 5.20: more than 50 fighters removes FedSpace protection",
    ),
    "fed_tow_limit_live": (
        "FED_TOW_LIMIT_MODE",
        "NOTE 117 GAP 1.15: Extern tows a FedSpace ship with more than 50 fighters",
    ),
    "corp_breakin_align_live": (
        "CORP_BREAKIN_ALIGN_MODE",
        "NOTE 117 GAP 9.5: the first wrong corp password in a day costs 1 alignment",
    ),
    "planet_zdy_live": (
        "PLANET_ZDY_MODE",
        "NOTE 143 GAP 6.10: destroying a planet kills a trader who is on it for enemy experience x 0.1666 and alignment x -0.3333",
    ),
    "quasar_atm_order_live": (
        "QUASAR_ATM_ORDER_MODE",
        "NOTE 143: a landing takes one atmosphere shot, and a second only after the last shield falls",
    ),
    "planet_interdict_safe_live": (
        "PLANET_INTERDICT_SAFE_MODE",
        "NOTE 143: an interdictor does not hold a ship at StarDock, and Terra is that sector",
    ),
    "haggle_table_live": (
        "HAGGLE_TABLE_MODE",
        "NOTE 150 GAP 2.6: a counter uses the cabal product table",
    ),
    "ferrengi_attack_live": (
        "FERRENGI_ATTACK_MODE",
        "NOTE 148 GAP 8.1: a Ferrengi attack sends one chart volley",
    ),
    "photon_limpet_live": (
        "PHOTON_LIMPET_MODE",
        "NOTE 148 GAP 4.10: a limpet still attaches during a photon wave",
    ),
    "comms_v311_live": (
        "COMMS_V311_MODE",
        "NOTE 142: sub-space radio, Fed Comm, a same-sector hail, and the corporation memo",
    ),
    "inactive_user_live": (
        "INACTIVE_USER_MODE",
        "NOTE 151 GAP 12.4: an inactive trader is deleted after 30 real days",
    ),
    "inactivity_timeout_live": (
        "INACTIVITY_TIMEOUT_MODE",
        "NOTE 151 GAP 12.4: a quiet game sleeps after 14400 seconds",
    ),
    "two_way_warp_live": (
        "TWO_WAY_WARP_MODE",
        "NOTE 157 GAP 1.2: extra two-way lanes are 30% of the sector count",
    ),
    "reentry_fighters_live": (
        "REENTRY_FIGHTERS_MODE",
        "NOTE 158: the free Scout after Ship Destroyed gets min(250, initial fighters)",
    ),
    "navpoint_live": (
        "NAVPOINT_MODE",
        "NOTE 159 GAP 14.1: four named NavPoints, plus Terra and StarDock, as course destinations",
    ),
    # NOTE 162 rows 182-186. Row 181 is NavPoints, already in this dict.
    "federation_hall_live": (
        "FEDERATION_HALL_MODE",
        "NOTE 162 GAP 1.8: Federation Hall lists corp registrations, and the hardware counter shows a shop screen",
    ),
    "corp_cargo_treasury_live": (
        "CORP_CARGO_TREASURY_MODE",
        "NOTE 162 GAP 10.6: corp mates can move cargo, and credits can go into the corp treasury",
    ),
    "ug_name_live": (
        "UG_NAME_MODE",
        "NOTE 162 GAP 11.7: the Underground sells a new name to a total unknown for 100 credits",
    ),
    "fed_hunt_live": (
        "FED_HUNT_MODE",
        "NOTE 162 GAP 11.9: an evil ship that meets a Federal is destroyed",
    ),
    "cim_live": (
        "CIM_MODE",
        "NOTE 162 GAP 14.1: CIM lists explored sectors and ports, and plots a path",
    ),
    "bounty_good_live": (
        "BOUNTY_GOOD_MODE",
        "NOTE 163 GAP 9.5: a bounty on a good trader costs 1 alignment per 250 credits and no experience",
    ),
    "cfs_ceo_use_live": (
        "CFS_CEO_USE_MODE",
        "NOTE 177 GAP 10.1: only a C.E.O. may board a Corporate FlagShip (Gypsy: only C.E.O.'s can use them)",
    ),
    "planet_blow_align_live": (
        "PLANET_BLOW_ALIGN_MODE",
        "NOTE 177 GAP 6.10: destroying a planet costs 50 alignment (Bible), not 1",
    ),
    "ferrengi_odds_live": (
        "FERRENGI_ODDS_MODE",
        "NOTE 164 GAP 8.1: Bible Ferrengi odds are 1.2 / 1.4 / 1.4, and an Assault Trader sends 2,000",
    ),
    "corp_ship_disband_live": (
        "CORP_SHIP_DISBAND_MODE",
        "NOTE 164 GAP 6.11: a parked corporate ship in the living C.E.O.'s sector becomes the C.E.O.'s",
    ),
    "times_blown_live": (
        "TIMES_BLOWN_MODE",
        "NOTE 164 GAP 12.6: with elimination off, the destroy line says times blown up are unlimited",
    ),
    "fighter_report_live": (
        "FIGHTER_REPORT_MODE",
        "NOTE 164 GAP 13.4: the fighter report lists owned fighters and omits a count of 0",
    ),
}


# NOTE 151 GAP 12.4. Cabal twgs.html and the modern manual print 30 days until an
# inactive user is deleted. Gypsy's v2.03 sample prints 7. Off, nobody is deleted
# for a quiet stretch. On, Extern deletes a trader with no successful action for
# 30 wall-clock days. Game days do not count: a fast test day is still one real
# day on the clock. A connected seat and an AI cockpit seat stay. A game that
# was generated before this switch was on is not armed, so turning the switch
# on later does not delete anyone in that game. A C.E.O. deleted this way
# leaves the corporation in place.
INACTIVE_USER_MODE = "legacy"  # "legacy" | "v311"
INACTIVE_USER_DAYS = 30
INACTIVE_USER_SPAN_S = INACTIVE_USER_DAYS * 24 * 60 * 60
# The same editor prints an inactivity timeout of 14,400 seconds. Off, the lobby
# keeps its own idle setting. On, a quiet lobby game sleeps after that long.
INACTIVITY_TIMEOUT_MODE = "legacy"  # "legacy" | "v311"
INACTIVITY_TIMEOUT_S = 14_400


def inactive_user_live() -> bool:
    """True when Extern may delete a trader after 30 quiet wall-clock days.

    The game also has to have been generated while this was already on.
    """
    return INACTIVE_USER_MODE == "v311" or v311_profile()


def inactivity_timeout_live() -> bool:
    """True when a quiet lobby game uses the 14,400 second inactivity timeout."""
    return INACTIVITY_TIMEOUT_MODE == "v311" or v311_profile()


def lobby_idle_limit_s(configured: float) -> float:
    """Seconds a lobby game may sit with no tab before it sleeps."""
    if inactivity_timeout_live():
        return float(INACTIVITY_TIMEOUT_S)
    return float(configured)


# beta-polish-computer-reports-v1 (NOTE 88) row 114. A code bot that banks its
# whole purse then buys one unit at a time. "legacy" keeps today's reserve.
# "live" leaves enough cash for a full hold at the route's buy price. Stored
# default stays legacy so the profile-off digests do not move. Row 115 is unused.
BOT_BANK_FLOAT_MODE = "legacy"  # "legacy" | "live"


def bot_bank_float_live() -> bool:
    """True when a code bot keeps a full hold of cash before it deposits."""
    return BOT_BANK_FLOAT_MODE == "live" or tw2002_live_profile() or v311_profile()


# v311-kill-cash-addendum-v1 (NOTE 59). RULINGS_v311.md Addendum A: "In every trial the
# victim's cash was gone and the pod held 25 credits." Legacy leaves the pod with what
# bank.on_ship_lost left (0 under DEATH_CREDITS_ON_HAND "lost"). "live" puts 25 credits
# in the pod after a kill by another player. Appended so later slices can rebase cleanly.
POD_CASH_MODE = "legacy"  # "legacy" | "live"
POD_CASH_CREDITS = 25


def pod_cash_live() -> bool:
    """True when a pod after a player kill holds POD_CASH_CREDITS."""
    return POD_CASH_MODE == "live" or tw2002_live_profile() or v311_profile()


# v311-daylen-and-yard-v1 (NOTE 60) item 1. RULINGS_v311.md s5: "turns come back hourly,
# pro-rated from the daily allowance". A real TWGS day is 86,400 s; a local, test or showcase
# game may pick a shorter one with TW2K_TURN_REGEN_DAY_SECONDS, `tw2k serve --day-seconds` or
# GameConfig.turn_regen_day_seconds. Nothing set keeps TURN_REGEN_DAY_SECONDS as it is.
TURN_REGEN_DAY_SECONDS_ENV = "TW2K_TURN_REGEN_DAY_SECONDS"
TURN_REGEN_DAY_SECONDS_MIN = 10.0
TURN_REGEN_DAY_SECONDS_MAX = 7 * 86_400.0


def parse_day_seconds(raw) -> float:
    """A day length in seconds, or ValueError with a sentence that says what is wrong."""
    if isinstance(raw, bool):
        raise ValueError(f"day length must be a number of seconds, not {raw!r}")
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        raise ValueError(f"day length must be a number of seconds, not {raw!r}") from None
    if not math.isfinite(value) or not TURN_REGEN_DAY_SECONDS_MIN <= value <= TURN_REGEN_DAY_SECONDS_MAX:
        raise ValueError(
            f"day length must be between {TURN_REGEN_DAY_SECONDS_MIN:g} and {TURN_REGEN_DAY_SECONDS_MAX:g}"
            f" seconds, not {raw!r}")
    return value


def day_seconds_from_env() -> float | None:
    """TW2K_TURN_REGEN_DAY_SECONDS, checked, or None when it is not set."""
    import os

    raw = (os.environ.get(TURN_REGEN_DAY_SECONDS_ENV) or "").strip()
    return parse_day_seconds(raw) if raw else None


# v311-daylen-and-yard-v1 (NOTE 60) item 5. Legacy sends no hull figures with buy_ship and the
# cockpit reads its own table. "live" adds stats_by (name, cost, trade-in, holds, fighters,
# shields, turns per warp, odds) from ship_specs(), so the yard shows the roster in play
# (RULINGS_v311.md s4 under SHIP_ROSTER_MODE live). Appended so later slices can rebase cleanly.
YARD_STATS_MODE = "legacy"  # "legacy" | "live"


def yard_stats_on() -> bool:
    """True when buy_ship carries each hull's figures from the server's ship list."""
    return YARD_STATS_MODE == "live" or tw2002_live_profile() or v311_profile()


def colonist_drop_room(class_id: str, pools: dict, total: int) -> int | None:
    """How many more colonists fit. Class M live uses one cap per pool."""
    if class_id == "M" and class_m_fidelity_live():
        best = 0
        for name in ("fuel_ore", "organics", "equipment", "colonists"):
            have = int(pools.get(name, 0) or 0)
            best = max(best, CLASS_M_CATEGORY_CAP - have)
        return max(0, best)
    return planet_colonist_room(class_id, total)


def colonist_drop_error(class_id: str, pool_count: int, total: int, qty: int) -> str | None:
    """A refusal sentence, or nothing when the drop fits."""
    if class_id == "M" and class_m_fidelity_live():
        if int(pool_count) + int(qty) > CLASS_M_CATEGORY_CAP:
            return f"planet colonist cap is {CLASS_M_CATEGORY_CAP}"
        return None
    room = planet_colonist_room(class_id, total)
    if room is not None and int(qty) > room:
        return f"planet colonist cap is {planet_colonist_cap(class_id)}"
    return None


# class-m-production-units-v1 (NOTE 64 ADDENDUM). S1_planet_handbook_v1.01.html section VII, class U
# row "Colo 3000 3000 8000 6000 8000 6000", and TWFAQ_20PLANET.txt: a class U citadel level 3 asks
# for 8,000 colonists. CITADEL_CLASS_COSTS keeps its 5,000, so "legacy" builds as before; "live"
# asks for the S1 count. Appended so later slices can rebase cleanly.
CITADEL_TABLE_FIX_MODE = "legacy"  # "legacy" | "live"
CITADEL_S1_COLONISTS: dict[tuple[str, int], int] = {("U", 3): 8_000}


def citadel_table_fix_live() -> bool:
    """True when a citadel level asks for the S1 colonist count where the stored table differs."""
    return CITADEL_TABLE_FIX_MODE == "live" or tw2002_live_profile() or v311_profile()


# terra-and-planet-ownership-v1 (NOTE 66). "legacy" keeps the home planet in the
# seat's start sector with all 191,000 colonists unassigned. "live" places it in
# an empty sector outside FedSpace and splits the start 45 / 65 / 81 thousand
# (transcript.txt, new character: Fuel Ore 45, Organics 65, Equipment 81).
# Appended so later slices can rebase cleanly.
HOME_PLANET_MODE = "legacy"  # "legacy" | "live"
HOME_PLANET_FUEL = 45_000
HOME_PLANET_ORGANICS = 65_000
HOME_PLANET_EQUIPMENT = 81_000


def home_planet_live() -> bool:
    """True when a new seat's class M world is placed and stocked the v3.11 way."""
    return HOME_PLANET_MODE == "live" or tw2002_live_profile() or v311_profile()


# class-m-planet-units-v1. Appended so later slices can rebase cleanly.
# Class M under class_m_fidelity_live stores people. S1 and NOTE 19 count
# those people in thousands (CLASS_M_PEOPLE_PER_THOUSAND). Three switches,
# each "legacy" until a profile turns it on:
#   net worth prices a thousand, not one person (COLONIST_PRICE);
#   a Terra drop lands as people, and one thousand fills one hold;
#   a genesis seed of GENESIS_SEED_COLONISTS is that many thousands.
# The genesis scale runs only when the seed is still placed. V311 also
# turns genesis_start_live on, and S1 / GAP 6.5 leave that planet empty.
CLASS_M_NW_MODE = "legacy"  # "legacy" | "live"
CLASS_M_DROP_MODE = "legacy"  # "legacy" | "live"
CLASS_M_GENESIS_MODE = "legacy"  # "legacy" | "live"


def class_m_nw_units() -> bool:
    """True when class M net worth prices handbook thousands."""
    return CLASS_M_NW_MODE == "live" or tw2002_live_profile() or v311_profile()


def class_m_drop_units() -> bool:
    """True when a class M colonist drop converts Terra holds into people."""
    return CLASS_M_DROP_MODE == "live" or tw2002_live_profile() or v311_profile()


def class_m_genesis_units() -> bool:
    """True when a class M genesis seed is stored as people."""
    return CLASS_M_GENESIS_MODE == "live" or tw2002_live_profile() or v311_profile()


def class_m_transfer_on(class_id: str) -> bool:
    """True when this planet stores class M people and drops convert units."""
    token = getattr(class_id, "value", class_id)
    return str(token) == "M" and class_m_drop_units() and class_m_fidelity_live()


def class_m_people_for_cargo(qty: int) -> int:
    """People a class M planet gains for `qty` cargo colonists.

    Terra live already stores people (1,000 per hold). Legacy Terra stores
    one colonist per hold, and that colonist is one handbook thousand.
    """
    per = int(colonists_per_hold())
    thousand = int(CLASS_M_PEOPLE_PER_THOUSAND)
    amount = int(qty)
    if per <= 1:
        return amount * thousand
    return amount * thousand // per


def class_m_cargo_for_people(people: int) -> int:
    """Cargo colonists for `people` stored on a class M planet."""
    per = int(colonists_per_hold())
    thousand = int(CLASS_M_PEOPLE_PER_THOUSAND)
    amount = int(people)
    if per <= 1:
        return amount // thousand
    return amount * per // thousand


def colonist_holds_for_cargo(amount: int) -> int:
    """Holds filled by this many cargo colonists. Matches Ship.cargo_used."""
    per = int(colonists_per_hold())
    count = int(amount)
    if count <= 0:
        return 0
    if per <= 1:
        return count
    return (count + per - 1) // per


def corp_exp_penalty_taken() -> bool:
    """True when a mixed-corp event names the experience that was taken."""
    return CORP_EXP_PENALTY_MODE == "taken" or v311_profile()


def corp_leaver_to_ceo() -> bool:
    """True when a leaver's corporate fighters and mines move to the C.E.O."""
    return CORP_LEAVER_DEPLOYMENTS == "to_ceo" or v311_profile()


def corp_alignment_rule() -> str:
    """Effective cr8 rule. Stored default stays mixed. V311 checks signs at join."""
    if CORP_ALIGNMENT_RULE == "mixed" and v311_profile():
        return "join_check"
    return CORP_ALIGNMENT_RULE


def corp_join_check() -> bool:
    """True when a join is refused for opposite alignment signs and drift is kept."""
    return corp_alignment_rule() == "join_check"


def mixed_corp_exp_rule() -> str:
    """Effective cr9 formula. Stored default stays highest_good. V311 uses least extreme."""
    if MIXED_CORP_EXP_RULE == "least_extreme" or v311_profile():
        return "least_extreme"
    return MIXED_CORP_EXP_RULE


def mixed_corp_least_extreme() -> bool:
    """True when the Extern loss is min(most good, most evil) / 4."""
    return mixed_corp_exp_rule() == "least_extreme"


# beta-combat-haggle-v1 (NOTE 71). "legacy" keeps the odds formula, where a
# defender odds below 1 can make shields absorb more than the volley.
# "live" trades alien fighters 1:1 and lets shields soak first, never more
# than the volley or more than they hold. Appended so later slices rebase.
ALIEN_COMBAT_FIX_MODE = "legacy"  # "legacy" | "live"


def alien_combat_fix_live() -> bool:
    """True when an alien exchange uses the 1:1 shield-first numbers."""
    return ALIEN_COMBAT_FIX_MODE == "live" or tw2002_live_profile() or v311_profile()


# beta-combat-haggle-v1 (NOTE 71). "legacy" answers a counter and then the
# seat's turn ends. "live" keeps the seat for the next offer or accept
# (HAGGLE_COUNTER_ROUNDS times; the live game showed 3-4) and checks empty
# holds or cargo on board before credits or the port's stock cap. An offer
# past the counter can still be taken inside the existing band.
HAGGLE_COUNTER_MODE = "legacy"  # "legacy" | "live"
HAGGLE_COUNTER_ROUNDS = 4


def haggle_counter_live() -> bool:
    """True when a port counter keeps the turn open and holds are checked first."""
    return HAGGLE_COUNTER_MODE == "live" or tw2002_live_profile() or v311_profile()


# beta-combat-haggle-v1 (NOTE 71). "legacy" flees and routes with no memory
# of Ferrengal or a sector that just mined the ship. "live" refuses those
# warps unless every exit is one of them, in which case the bot stays.
BOT_HAZARD_MEMORY_MODE = "legacy"  # "legacy" | "live"


def bot_hazard_memory_live() -> bool:
    """True when a bot will not re-enter Ferrengal or a hazard it met today."""
    return BOT_HAZARD_MEMORY_MODE == "live" or tw2002_live_profile() or v311_profile()


# beta-playtest-addendum-v1 (NOTE 73). Each stored default is legacy. The v3.11
# profile turns them on. Appended so later slices can rebase cleanly.
TRADE_IN_PARTS_MODE = "legacy"  # "legacy" | "live"


def trade_in_parts_live() -> bool:
    """True when a trade-in is the itemised parts of the ship as it sits."""
    return TRADE_IN_PARTS_MODE == "live" or tw2002_live_profile() or v311_profile()


TRADER_RANK_LIST_MODE = "legacy"  # "legacy" | "live"


def trader_rank_list_live() -> bool:
    """True when every seat can see the experience ranking, and the end rule."""
    return TRADER_RANK_LIST_MODE == "live" or tw2002_live_profile() or v311_profile()


NW_ESTIMATE_MODE = "legacy"  # "legacy" | "live"
NW_ESTIMATE_NOTE = "Bought holds count at their trade-in value; cargo at what you paid; sector fighters count."


def nw_estimate_live() -> bool:
    """True when the estimate follows paid cargo, extra holds, and sector fighters.

    It does not change who wins. Under the v3.11 profile the winner is still
    the trader with the most experience.
    """
    return NW_ESTIMATE_MODE == "live" or tw2002_live_profile() or v311_profile()


SEAT_IDLE_START_MODE = "legacy"  # "legacy" | "live"


def seat_idle_start_live() -> bool:
    """True when an unconnected seat does not auto-WAIT before its first client."""
    return SEAT_IDLE_START_MODE == "live" or tw2002_live_profile() or v311_profile()


BOT_DIPLOMACY_MODE = "legacy"  # "legacy" | "live"


def bot_diplomacy_live() -> bool:
    """True when a code bot answers an alliance proposal and a hail on its turn."""
    return BOT_DIPLOMACY_MODE == "live" or tw2002_live_profile() or v311_profile()


# day-roll-on-clock-v1 (NOTE 74). The regen day used to roll only when the
# scheduler loop reached the top, so a seat that held its turn froze the day,
# and the next mark was set to "now", which added the wait onto the day.
# "live" rolls when the mark passes, even during that wait, and the next mark
# is the old mark plus the day length. Default stays legacy.
DAY_ROLL_CLOCK_MODE = "legacy"  # "legacy" | "live"


def day_roll_clock_live() -> bool:
    """True when a held turn still lets the day roll on the clock."""
    return DAY_ROLL_CLOCK_MODE == "live" or v311_profile()


# beta-playtest2-blockers-v1 (NOTE 104) row 164. Legacy used to roll the day only
# when every seat was out of turns, so one human with a turn left held the galaxy.
# "live" and a game that set its own day length (serve --day-seconds, or a lobby
# game) roll that day on the clock, mark plus the day length, whoever still has
# turns, including while a seat holds the turn. Dawn still refills turns. No day
# length does nothing, so a scripted match stays put. The v3.11 regen clock
# already rolls, so this path stays quiet under it. Rows 160, 162 and 163 stay
# unused. Stored default stays legacy.
LEGACY_DAY_CLOCK_MODE = "legacy"  # "legacy" | "live"


def legacy_day_clock_live() -> bool:
    """True when a legacy game with its own day length rolls that day on the clock."""
    return LEGACY_DAY_CLOCK_MODE == "live" or tw2002_live_profile() or v311_profile()


# v311-evil-trading-loops-v1 (NOTE 115) row 166. Glossary SDT and RTR: steal
# equipment, land, dump, beam to the other ship; or rob, beam, rob. Rob, steal,
# bust, and the transporter already run. This only picks that cycle. Row 165
# is the price scale. Stored default stays legacy so a profile-off match does not move.
EVIL_TRADE_LOOP_MODE = "legacy"  # "legacy" | "live"


def evil_trade_loop_live() -> bool:
    """True when a negative-alignment seat runs the steal-dump and rob-transport loops."""
    return EVIL_TRADE_LOOP_MODE == "live" or tw2002_live_profile() or v311_profile()


# v311 gap-partials-batch-1 (NOTE 117) rows 167-169. Stored flags stay legacy.
# 167: Iago "50 or less" and the Bible "more than 50" (S3 bible, FedSpace protection).
# One Iago line says "less than 50"; FEDSPACE_POLICE.md f9 keeps the 50-or-less reading.
# 168: Bible "over 50 fighters" towed. Gypsy 99+ stays FED_TOW_FIGHTER_LIMIT 98.
# 169: formulas.html, breaking into another corp, -1 alignment, one time per extern, exp 0.
FEDSAFE_FIGHTER_CAP_MODE = "legacy"  # "legacy" | "live"
FEDSAFE_FIGHTER_CAP = 50
FED_TOW_LIMIT_MODE = "legacy"  # "legacy" | "live"
FED_TOW_LIVE_LIMIT = 50
CORP_BREAKIN_ALIGN_MODE = "legacy"  # "legacy" | "live"
CORP_BREAKIN_ALIGN_LIVE = 1


def fedsafe_fighter_cap_live() -> bool:
    """True when more than 50 fighters removes FedSpace protection."""
    return FEDSAFE_FIGHTER_CAP_MODE == "live" or tw2002_live_profile() or v311_profile()


def fedsafe_max_fighters() -> int | None:
    """Fighter ceiling for is_fedsafe. None means fighter count does not matter."""
    if fedsafe_fighter_cap_live():
        return int(FEDSAFE_FIGHTER_CAP)
    return FEDSAFE_MAX_FIGHTERS


def fed_tow_limit_live() -> bool:
    """True when Extern uses the Bible tow line instead of the stored Gypsy line."""
    return FED_TOW_LIMIT_MODE == "live" or tw2002_live_profile() or v311_profile()


def fed_tow_fighter_limit() -> int:
    """Tow a FedSpace ship with more fighters than this."""
    if fed_tow_limit_live():
        return int(FED_TOW_LIVE_LIMIT)
    return int(FED_TOW_FIGHTER_LIMIT)


def corp_breakin_align_live() -> bool:
    """True when the first wrong corp password in a day costs alignment."""
    return CORP_BREAKIN_ALIGN_MODE == "live" or tw2002_live_profile() or v311_profile()


def corp_breakin_align_loss() -> int:
    """Alignment taken for one corp break-in this day. Zero keeps the stored path."""
    if corp_breakin_align_live():
        return int(CORP_BREAKIN_ALIGN_LIVE)
    return int(CORP_BREAKIN_ALIGN_LOSS)


# v311-followups-v1 (NOTE 75). The free home-planet colonists are a clone
# grant. Under "live" they do not add to net worth while they are still on
# that planet. Bought, hauled and grown colonists still count. Default legacy.
START_COLONIST_NW_MODE = "legacy"  # "legacy" | "live"


def start_colonist_nw_live() -> bool:
    """True when free start colonists still on the home planet are not in net worth."""
    return START_COLONIST_NW_MODE == "live" or tw2002_live_profile() or v311_profile()


def ferrengi_kill_xp(hull: str | None, aggression: int) -> int:
    """Experience for one Ferrengi kill under the live reward.

    A known hull pays the flat UNVERIFIED award. Anything else keeps the clone
    formula so an unlisted hull does not invent a new number.
    """
    award = FERRENGI_XP_BY_HULL.get(str(hull or ""))
    if award is None:
        return int(aggression) * int(xp_award("kill_ferr"))
    return int(award)


# v311-hazard-scanner-gaps-v1 (NOTE 85). Stored defaults stay legacy. The profile
# turns the helpers on. Rows 100 and 103 are unused: density/holo scanners and
# corporate deploy are already the stored rule (INFO_MODE, CORP_MODE).
PROBE_SHOOTDOWN_MODE = "legacy"  # "legacy" | "live"


def probe_shootdown_live() -> bool:
    """True when a destroyed probe's event names who owned the fighters."""
    return PROBE_SHOOTDOWN_MODE == "live" or tw2002_live_profile() or v311_profile()


FERRENGI_REWARD_MODE = "legacy"  # "legacy" | "live"


def ferrengi_reward_live() -> bool:
    """True when a Ferrengi kill pays alignment only to a good trader, and xp by hull."""
    return FERRENGI_REWARD_MODE == "live" or tw2002_live_profile() or v311_profile()


FERRENGAL_QUASAR_MODE = "legacy"  # "legacy" | "live"


def ferrengal_quasar_live() -> bool:
    """True when entering Ferrengal draws a quasar shot."""
    return FERRENGAL_QUASAR_MODE == "live" or tw2002_live_profile() or v311_profile()


# v311-extern-gaps-v1 (NOTE 82) TRD-k, row 94. REV v3.05: a TEDIT setting
# chooses how often Extern clears bust records. It defaults to nightly and
# can be as high as every 28th day. The cabal editor sample is "Clear Busts
# Every : 1 Days". "legacy" keeps today's clear-every-Extern. "live" reads
# GameConfig.bust_clear_days (1 or 7). REPORT.md is on Ben's PC (UNVERIFIED).
# The missed-Extern catch-up is not built: this day tick always runs.
BUST_CLEAR_MODE = "legacy"  # "legacy" | "live"


def bust_record_clear_live() -> bool:
    """True when this game's bust-clear interval is honored (1 day or 7)."""
    return BUST_CLEAR_MODE == "live" or tw2002_live_profile() or v311_profile()


# v311-extern-gaps-v1 (NOTE 82) SD-e, row 96. The Bible ship chart already
# caps mines, genesis and photons on SHIP_SPECS_TW2002, and cloaks are 5
# (CLOAK_MAX, "the maximum any ship can carry is five"). Probes were uncapped.
# The Bible says any ship carries at most 25. "legacy" leaves probes uncapped.
PROBE_CHART_MAX = 25
SHIP_CHART_CAP_MODE = "legacy"  # "legacy" | "live"


def ship_chart_cap_live() -> bool:
    """True when a ship stops at 25 ether probes."""
    return SHIP_CHART_CAP_MODE == "live" or tw2002_live_profile() or v311_profile()


# v311-extern-gaps-v1 (NOTE 82) PLN-q, row 97. Today's rule is
# CORP_DISBAND_PLANETS "owner_keeps". REV v3.06 gives the C.E.O. the planets
# in his sector and leaves the rest unclaimed. "legacy" keeps owner_keeps.
# The older constant "v306" still selects that path on its own.
CORP_PLANET_DISBAND_MODE = "legacy"  # "legacy" | "v306"


def corp_planet_disband_v306() -> bool:
    """True when a disband follows REV v3.06 for planets."""
    if CORP_DISBAND_PLANETS == "v306" or CORP_PLANET_DISBAND_MODE == "v306":
        return True
    return tw2002_live_profile() or v311_profile()


# v311-combat-gaps-v1 (NOTE 79) SD-o, row 90. A photon into the next sector
# already neutralizes that sector's mines and fighters for the wave
# (hardware.mark_sector_photon_wave, runner sector_photon_active) and damps
# the quasars for the shooter and anyone already there. "live" also damps
# the quasars for a ship that enters while the wave is still up. S1: below
# citadel L5, or under 200 shields, the cannon does not fire. L5 with 200
# shields still fires. Stored default stays legacy.
PHOTON_FOLLOW_DAMP_MODE = "legacy"  # "legacy" | "live"


def photon_follow_damp_live() -> bool:
    """True when a following ship inherits the photon wave's quasar damp."""
    return PHOTON_FOLLOW_DAMP_MODE == "live" or tw2002_live_profile() or v311_profile()


# v311-combat-gaps-v1 (NOTE 79) CMB-n, row 93. S7 #16: death delay 0 lets the
# pod fly at once. 1 or more keeps the pilot out until that many midnights
# pass. A pod destroyed while that sentence is running has the same number
# added again. A flying pod does not start a new sentence. UNVERIFIED, searched:
# S7_softdocs_slice-10.txt #16 lines 353-378 (the extra days apply while knocked
# out; 0, 1 and 2 are examples and no ceiling is printed); cabal twgs.html
# line 253 "<7> Death Delay : Yes" (a sample flag, not a maximum);
# OldBBS_TW.faq.txt and OldBBS_TW2002V8.faq.txt #12; TWGS_v2_Revision_History.html
# (a sub-setting for deaths before #SD#, not the day maximum). Stored default
# stays legacy, which ignores GameConfig.death_delay. Queued in
# docs/plans/live-twgs-test-queue-v1.md.
DEATH_DELAY_MODE = "legacy"  # "legacy" | "live"


def death_delay_live() -> bool:
    """True when GameConfig.death_delay locks a fresh pod out."""
    return DEATH_DELAY_MODE == "live" or tw2002_live_profile() or v311_profile()


def death_delay_days(config) -> int:
    """Midnights a new pod must wait. 0 when the switch is off or unset."""
    if not death_delay_live():
        return 0
    raw = getattr(config, "death_delay", None)
    if raw is None:
        return 0
    return max(0, int(raw))


# v311-universe-planet-gaps-v1 (NOTE 78). Each stored default is legacy.
# V311_PROFILE turns the five helpers on. Appended so later slices can rebase.
# Rows 85-89. Rows 83-84 are reserved for NOTE 75.

TREASURY_CAP_MODE = "legacy"  # "legacy" | "live"
# S1_planet_handbook_v1.01.html. Fifteen 9s.
S1_PLANET_TREASURY_CAP = 999_999_999_999_999


def treasury_cap_live() -> bool:
    """True when a planet treasury uses the S1 cap."""
    return TREASURY_CAP_MODE == "live" or tw2002_live_profile() or v311_profile()


def planet_treasury_cap() -> int:
    """Credits a citadel treasury may hold. Legacy stays PLANET_TREASURY_CAP."""
    if treasury_cap_live():
        return int(S1_PLANET_TREASURY_CAP)
    return int(PLANET_TREASURY_CAP)


COURSE_MAX_MODE = "legacy"  # "legacy" | "live"
# UNVERIFIED, searched: classictw_docs_wiki/Big_Bang.html "B - Maximum Course
# Length" (lines 201-210: the setting shapes the map and slows course plots;
# it is not the refusal limit); cabal twgs.html line 214, post-bang General
# Editor Two, "<:> Maximum Course Length : 45" (a sample value, not stated as
# the plot cap; range 20-255 is option B); tw-attac revision history line 538
# "Long course plots are not longer truncated at 160 characters" (display
# width, not hops). The clone autopilot searches PLOT_COURSE_MAX_DEPTH * 6.
# Queued in live-twgs-test-queue-v1.md.
V311_COURSE_MAX_HOPS = 45


def course_max_live() -> bool:
    """True when a plotted course longer than V311_COURSE_MAX_HOPS is refused."""
    return COURSE_MAX_MODE == "live" or tw2002_live_profile() or v311_profile()


def plot_course_hop_limit() -> int:
    """Hops a plotted course may take. Legacy is 60. Live is 45 (UNVERIFIED, searched: Big_Bang.html option B and cabal twgs.html General Editor Two)."""
    if course_max_live():
        return int(V311_COURSE_MAX_HOPS)
    return int(PLOT_COURSE_MAX_DEPTH) * 6


BIG_BANG_DENSITY_MODE = "legacy"  # "legacy" | "live"
# Big_Bang.html: port density default 40% (clone PORT_SPAWN_PROBABILITY is 0.65
# of sectors past FedSpace). Planet density default 20%, range 2-40% (clone
# GameConfig.planet_spawn_probability is 0.03). Decorative Fed ports in
# sectors 2-10 have no source.
V311_PORT_DENSITY = 0.40
V311_PLANET_DENSITY = 0.20


def big_bang_density_live() -> bool:
    """True when a new universe uses the Big Bang port and planet densities."""
    return BIG_BANG_DENSITY_MODE == "live" or tw2002_live_profile() or v311_profile()


ONE_WAY_SHARE_MODE = "legacy"  # "legacy" | "live"
# Big_Bang.html option G. Default is 3%. The clone stored default stays 0.15.
V311_ONE_WAY_FRACTION = 0.03


def one_way_share_live() -> bool:
    """True when an unset one-way share is about 3%."""
    return ONE_WAY_SHARE_MODE == "live" or tw2002_live_profile() or v311_profile()


TWO_WAY_WARP_MODE = "legacy"  # "legacy" | "v311"
# Big_Bang.html option F and cabal twgs.html. The printed density is 30% of
# the sector count. 100% is one two-way warp per sector. A total of 30% cannot
# connect the map, so the live count is that many extra lanes on the spanning
# tree (GAP_MAP 1.2). A game that sets avg_warps keeps that average.
V311_TWO_WAY_WARP_FRACTION = 0.30


def two_way_warp_live() -> bool:
    """True when extra two-way lanes are 30% of the sector count."""
    return TWO_WAY_WARP_MODE == "v311" or v311_profile()


def two_way_edge_target(n: int, avg_warps: float, *, game_set_average: bool) -> int:
    """Undirected lanes, including the spanning tree. Off keeps average 2.7."""
    if game_set_average or not two_way_warp_live():
        return int(n * avg_warps / 2)
    return (n - 1) + int(n * V311_TWO_WAY_WARP_FRACTION)


def one_way_fraction_for(config) -> float:
    """The bang's one-way share. A game setting that sets it always wins."""
    fields = getattr(config, "model_fields_set", ())
    if "one_way_fraction" in fields:
        return float(config.one_way_fraction)
    if one_way_share_live():
        return float(V311_ONE_WAY_FRACTION)
    return float(getattr(config, "one_way_fraction", DEFAULT_ONE_WAY_FRACTION))


ATOMIC_DETONATOR_MODE = "legacy"  # "legacy" | "live"


def atomic_detonator_live() -> bool:
    """True when the detonator is the planet killer and the port-nuke mine is retired."""
    return ATOMIC_DETONATOR_MODE == "live" or tw2002_live_profile() or v311_profile()


def atomic_mine_retired_error() -> str:
    """Why an atomic mine cannot be deployed. The stored flag's sentence stays for that switch."""
    if atomic_detonator_live():
        return "atomic mines are retired; an atomic detonator kills the colonists first, then the planet"
    return "atomic mines are retired (ATOMIC_MINES_PORT_NUKE off)"


# v311-fed-ferrengi-gaps-v1 (NOTE 86). Stored default stays legacy, so a profile-off
# game keeps today's Fed response, commission, Ferrengi roam, and hull combat.
# CMB-l and SD-q are already that default (fed.py protect_fedspace_attack and
# check_iss_repo_on_move); this slice does not add a switch for them.
SPECIAL_HULL_RULES_MODE = "legacy"  # "legacy" | "live"
# Docs wiki Tholian Sentinel flavor: "combat odds of 1:1 shoot up to 4:1 when
# defending a corporate planet."
THOLIAN_CORP_DEFENSE_ODDS = 4.0
FERRENGI_GRUDGE_MODE = "legacy"  # "legacy" | "live"
FERRENGI_PACE_MODE = "legacy"  # "legacy" | "live"
# cabal twgs.html <H> "Ferrengi moveCh : 1 in 20". v3.00 revision: that chance
# is once every 30 seconds, not once per player turn.
FERRENGI_MOVE_ONE_IN = 20
FERRENGI_MOVE_INTERVAL_S = 30
# A neighbour bands when the target has more fighters than this Ferrengi.
# UNVERIFIED, searched: TWBible_original_v1x.txt line 177 ("travel in groups",
# no fighter cutoff); TWFAQ_FERRSPEC_ferrengi.txt (no banding rule);
# tw-attac revision history lines 697-706 (v3.00: Ferrengi move on a 30 s
# clock, not when they attack). Queued in live-twgs-test-queue-v1.md.
FERRENGI_BAND_STRONG = "more_fighters_than_this_ship"


def special_hull_rules_on() -> bool:
    """True when Interdictor and Tholian specials apply to roster hulls."""
    return SPECIAL_HULL_RULES_MODE == "live" or tw2002_live_profile() or v311_profile()


def ferrengi_grudge_on() -> bool:
    """True when an attacked Ferrengi seeks that trader and neighbours band."""
    return FERRENGI_GRUDGE_MODE == "live" or tw2002_live_profile() or v311_profile()


def ferrengi_pace_on() -> bool:
    """True when Ferrengi hop on the 30 s clock instead of the once-a-day roll."""
    return FERRENGI_PACE_MODE == "live" or tw2002_live_profile() or v311_profile()


# v311-live-rulings-v2 (NOTE 90). Stored defaults stay legacy.
# Ship-vs-ship odds already follow the Bible chart on every exchange, so no
# SHIP_ODDS_MODE. Alien hops into FedSpace are not forbidden by a v3.11 line
# found in the docs, so no ALIEN_FEDSPACE_MODE. Rows 118 and 121 stay unused.
AUTOPILOT_PORT_STOP_MODE = "legacy"  # "legacy" | "live"
# Help text in live_twgs/transcript.txt (AUTOPILOT MENU): express pauses in
# sectors with ports. The cockpit sends stop_at_ports. A code bot does not.
GENESIS_NAME_MODE = "legacy"  # "legacy" | "live"
# live_twgs/transcript.txt after a Genesis launch: "What do you want to name
# this planet?" The prompt prints no length. 30 matches the home-planet rule.
GENESIS_NAME_MAX = 30


def autopilot_port_stop_live() -> bool:
    """True when an express warp may pause at a port the cockpit asked about."""
    return AUTOPILOT_PORT_STOP_MODE == "live" or tw2002_live_profile() or v311_profile()


def genesis_name_live() -> bool:
    """True when a Genesis deploy keeps a name the player typed."""
    return GENESIS_NAME_MODE == "live" or tw2002_live_profile() or v311_profile()


# v311-rules-gaps-v4 (NOTE 98). Stored defaults stay legacy.
# Row 139 is unused: deploy_genesis is already 25 in XP_AWARDS_TW2002 and
# GENESIS_ALIGNMENT is already 10 (runner._handle_deploy_genesis).
# Row 140 is unused: citadel_fidelity_rules() is already the S1 goods path
# with no credits, for a default game and for V311.
# Row 141 is unused: ALIEN_KILL_EXP_RULE "bible" is already half or quarter
# experience. Alignment stays half the alien's alignment. The half-experience
# alignment reading is not in the Bible or Gypsy.
PORT_ATTACK_ALL_CLASSES_MODE = "legacy"  # "legacy" | "live"
# cabal formulas.html safe minimum. The page says the 22 is approximate.
PORT_BLOW_FIGS_PER_RATING = 22
# classictw_docs_wiki Alignment.html: destroying a port is -50 alignment.
# The attack itself is still PORT_ATTACK_ALIGNMENT (-5), so a blow is -55,
# the same -55 the cabal subtracts when a trader dies on a blown port.
PORT_BLOW_ALIGNMENT = -50
# Class 6 is the only measured pair (REPORT2 section 8): rating 98, barrage 598.
# Classes 0-5 and 7-9 have no rating and no barrage in the sources below.
# UNVERIFIED, searched: docs/reference/tw2002/eis_tw2002_v3_docs/Tactical.html
# (no class table; Starport Construction says destroy a port when the universe
# is full), stardock_manuals_and_text_docs/TWBible_original_v1x.txt
# "Destroying Class 0 Ports" (no rating), cabal_strategy_site/formulas.html
# "Destroying a port, Defensive Rating vs Figs Needed" (rating times about 22
# divided by odds; the return shot "has no consistent pattern"; class 0 and
# StarDock do not use the formula), classictw_docs_wiki/Alignment.html
# (destroying a port is -50 alignment and 50 experience). No page gives port
# fighters from the port's size, and no page gives a capture outcome.
PORT_CLASS_NUMBER_FIX_MODE = "legacy"  # "legacy" | "live"


def port_attack_all_classes() -> bool:
    """True when a known port rating can destroy the port."""
    return PORT_ATTACK_ALL_CLASSES_MODE == "live" or tw2002_live_profile() or v311_profile()


def port_figs_to_blow(rating: int, odds: float) -> int:
    """Fighters one wave must send. Truncates the way the cabal example does."""
    safe = float(odds) if float(odds) > 0 else 1.0
    return int(int(rating) * PORT_BLOW_FIGS_PER_RATING / safe)


def port_class_number_fix() -> bool:
    """True when live class 7 trades and displays as SSS. StarDock stays id 8."""
    return PORT_CLASS_NUMBER_FIX_MODE == "live" or tw2002_live_profile() or v311_profile()
# v311-exp-alignment-trade-gaps-v1 (NOTE 87) TRD-i, row 109.
# Cabal formulas.html: Cost = (B*H) + ((I*H)*(H-1))/2, I always 20, B the
# daily base (151..249). SHOP_PRICE_MODE live replaces that with the 550 slope.
# This switch puts the cabal formula back, including while the slope is also on.
# Stored default stays legacy so the profile-off digests do not move.
CLASS0_HOLD_FORMULA_MODE = "legacy"  # "legacy" | "live"


def class0_hold_formula_live() -> bool:
    """True when Class 0 holds use the cabal total, not the 550 slope."""
    return CLASS0_HOLD_FORMULA_MODE == "live" or tw2002_live_profile() or v311_profile()


# v311-exp-alignment-trade-gaps-v1 (NOTE 87) TRD-q, row 110.
# +1 for a good haggle and +2 for a great one. UNVERIFIED, searched:
# docs/reference/tw2002/eis_tw2002_v3_docs/HardwareMenu.html lines 240-241
# ("a good deal... The better the deal, the more points"), S2_cabal_formulas.html
# (no haggle-xp table), S7_softdocs_slice-10.txt ("haggle for 2 points", a
# player method, not a split), and Eugene Hung's player tips (exact best
# price pays 5). None of those is REPORT2 s3/s7, and the 5 disagrees with
# the +1/+2 reading, so the amounts stay. Which counter is great stays the
# hidden bound: see economy.haggle_experience. DISCOVERY_EXP_MODE stays the
# first-dock award. Stored default stays legacy (the credit gap, capped at
# PORT_HAGGLE_XP_CAP).
HAGGLE_EXP_MODE = "legacy"  # "legacy" | "live"
HAGGLE_EXP_GOOD = 1
HAGGLE_EXP_GREAT = 2


def haggle_exp_live() -> bool:
    """True when an accepted haggle awards +1 or +2 instead of the credit gap."""
    return HAGGLE_EXP_MODE == "live" or tw2002_live_profile() or v311_profile()


# v311-exp-alignment-trade-gaps-v1 (NOTE 87) SD-n, row 112.
# EIS ShipyardMenu.html lines 104-112: "a hefty fee" and a new name. The page
# prints no price, no length, and no turn cost. UNVERIFIED, searched: that
# page, the TW2002 Bible ship-name paragraph (no fee), and GAP 3.17 (about
# 5,000 in a sample TEDIT). The fee stays 5,000, the name stays 30 characters,
# and the action spends 0 turns (class0.handle_ship_rename).
SHIP_RENAME_MODE = "legacy"  # "legacy" | "live"
SHIP_RENAME_COST = 5_000  # UNVERIFIED (GAP 3.17 sample TEDIT; EIS prints no number)
SHIP_RENAME_NAME_MAX = 30  # UNVERIFIED (EIS ShipyardMenu prints no length)


def ship_rename_live() -> bool:
    """True when the shipyard will change this ship's registration and name."""
    return SHIP_RENAME_MODE == "live" or tw2002_live_profile() or v311_profile()


# NOTE 103 GAP 13.1 / 13.3, row 161. EIS GeneralUpdated.html "New Mail", and the
# v3.11 revision history: a message lasts about 10 seconds. A hail to a seat
# with an open cockpit (or any code bot) is that flash. A hail to an offline
# trader is stored mail, and the cockpit says New Mail. Stored default stays
# legacy, so every hail still lands in the inbox and the digests do not move.
# Rows 162 and 163 stay unused: backtrack, quick stats, and find route read
# the seat's known map in the cockpit, and fighter reports are lines on the
# daily log the owner can already see. NavPoints are NOTE 159, row 181.
MAIL_MODE = "legacy"  # "legacy" | "live"
HAIL_SHOW_SECONDS = 10
NAVPOINT_SLOTS = 4  # EIS GeneralNew.html: four programmable NavPoints


def mail_live() -> bool:
    """True when an offline hail is stored mail and an online hail only flashes."""
    return MAIL_MODE == "live" or tw2002_live_profile() or v311_profile()


# NOTE 142. EIS GlobalCommands: Fed Comm (`), sub-space radio ('), hailing (=).
# EIS CompMisc: channel 0 turns the radio off; Fed Comm and hails can be turned off.
# EIS CorporateMenu: a corporate memo goes to the corporation.
# v3.11 revision history: a live message lasts about 10 seconds and is not mail.
# A line is 155 characters (GlobalCommands). Stored default stays legacy.
# "1" does not turn this on. V311_PROFILE "v311" does.
COMMS_V311_MODE = "legacy"  # "legacy" | "v311"
COMMS_LINE_MAX = 155
COMMS_MIN_GAP_S = 2.0


def comms_v311_live() -> bool:
    """True when player messages follow the v3.11 comm-link rules."""
    return COMMS_V311_MODE == "v311" or v311_profile()


# NOTE 158. v3.11 revision history: a trader who comes back in a Scout Marauder
# gets the minimum of 250 fighters and the Initial Fighters setting, instead of
# up to 2,500. Cabal twgs.html leaves Initial fighters blank. RULINGS s2 prints
# 30. The stored start is STARTING_FIGHTERS (20). Off, the free Scout stays
# empty, which is what Ship Destroyed does today. On, the grant is that
# minimum, and also no more than the scout can hold. The stored ship table
# holds 150. The v3.11 roster holds 250. "1" does not turn this on.
REENTRY_FIGHTERS_MODE = "legacy"  # "legacy" | "v311"
REENTRY_FIGHTER_CAP = 250


def reentry_fighters_live() -> bool:
    """True when Ship Destroyed stocks the free Scout from the initial-fighter cap."""
    return REENTRY_FIGHTERS_MODE == "v311" or v311_profile()


# NOTE 163 GAP 9.5. cabal formulas.html "Posting a bounty on a Good":
# -1 alignment per 250 credits, and the experience cell is 0. A reward on an
# evil trader stays +1 per REWARD_ALIGN_PER. Off, a good target is still refused.
# "1" does not turn this on. TW2002_LIVE_PROFILE does not turn this on.
BOUNTY_GOOD_MODE = "legacy"  # "legacy" | "v311"


def bounty_good_live() -> bool:
    """True when Police HQ accepts a bounty on a trader whose alignment is above 0."""
    return BOUNTY_GOOD_MODE == "v311" or v311_profile()


def reentry_fighter_grant(initial: int | None = None) -> int:
    """Fighters on the free Scout. 0 while the switch is off."""
    if not reentry_fighters_live():
        return 0
    if initial is None:
        initial = LIVE_STARTING_FIGHTERS if starting_package_live() else STARTING_FIGHTERS
    grant = min(REENTRY_FIGHTER_CAP, max(0, int(initial)))
    spec = hull_spec(SD_RESTART_HULL) or {}
    room = spec.get("max_fighters")
    if room is not None:
        grant = min(grant, int(room))
    return grant


# NOTE 159 GAP 14.1, row 181. EIS GeneralNew.html, Navigate.html, Tactical.html:
# four programmable NavPoints, plus Terra (sector 1) and StarDock.
# The v3.11 history prints "No Scan" when the sector is not FedSpace,
# not where you are, and holds none of your fighters. Stored default stays
# legacy. "1" does not turn this on. V311_PROFILE "v311" does.
# The docs do not print a name length. 20 is the box this game uses.
NAVPOINT_MODE = "legacy"  # "legacy" | "v311"
NAVPOINT_NAME_MAX = 20


def navpoint_live() -> bool:
    """True when the computer menu can set, list, and clear NavPoints."""
    return NAVPOINT_MODE == "v311" or v311_profile()


# NOTE 162 GAP 1.8, row 182. Gypsy: Federation Hall lists a corporation's
# registration, the date, and the members, with the C.E.O. marked, and ranks
# them by experience. The hardware counter otherwise stays a buy list.
# Stored default stays legacy. "1" does not turn this on.
FEDERATION_HALL_MODE = "legacy"  # "legacy" | "v311"


def federation_hall_live() -> bool:
    """True when StarDock opens Federation Hall and the hardware shop screen."""
    return FEDERATION_HALL_MODE == "v311" or v311_profile()


# NOTE 162 GAP 10.6, row 183. EIS already moves credits, fighters, shields, and
# mines. Holds of fuel, organics, equipment, and colonists, and the corp
# treasury, stay refused until this is on. Stored default stays legacy.
CORP_CARGO_TREASURY_MODE = "legacy"  # "legacy" | "v311"
CORP_CARGO_ITEMS = ("fuel_ore", "organics", "equipment", "colonists")


def corp_cargo_treasury_live() -> bool:
    """True when corp mates can move cargo and use the corporation treasury."""
    return CORP_CARGO_TREASURY_MODE == "v311" or v311_profile()


# NOTE 162 GAP 11.7, row 184. Iago: alignment 200 or lower can change a name
# and post bounties. The door, the password, and the bounties are already in.
# A live capture priced a total unknown (experience 1) at 100 credits. A higher
# experience was not given a formula, so this refuses that trader. UG_NAME_CHANGE
# stays false. Stored default stays legacy. "1" does not turn this on.
UG_NAME_MODE = "legacy"  # "legacy" | "v311"
UG_NAME_UNKNOWN_COST = 100
UG_NAME_UNKNOWN_MAX_EXPERIENCE = 1
UG_NAME_MAX = 30  # UNVERIFIED (the live screen did not print a length)


def ug_name_live() -> bool:
    """True when the Underground will sell a new name to a total unknown."""
    return UG_NAME_MODE == "v311" or v311_profile()


# NOTE 162 GAP 11.9, row 185. Iago: meeting a Federal while evil is goodbye.
# An empty FedSpace sector is left alone. The live walk of sectors 1-7 with no
# Federal in them was left alone. An evil ISS is already repossessed. Stored
# default stays legacy. "1" does not turn this on.
FED_HUNT_MODE = "legacy"  # "legacy" | "v311"


def fed_hunt_live() -> bool:
    """True when a Federal in the sector destroys an evil ship that is not an ISS."""
    return FED_HUNT_MODE == "v311" or v311_profile()


# NOTE 162 GAP 14.1, row 186. Iago and the Bible: from the computer, CIM
# answers I (explored sectors), R (explored ports), F (a path), and Q.
# Hostile fighters hide that sector's port line. Avoids, the course plotter,
# and the known-map cockpit keys were already in. Stored default stays legacy.
CIM_MODE = "legacy"  # "legacy" | "v311"


def cim_live() -> bool:
    """True when the computer answers CIM for explored sectors, ports, and a path."""
    return CIM_MODE == "v311" or v311_profile()


# NOTE 164 GAP 8.1. S3 Bible ship chart: Assault Trader 1.2:1 and 2,000 fighters
# per attack, Battle Cruiser 1.4:1, Dreadnaught 1.4:1. The v3.05 revision lets
# the Assault Trader carry a density or holo scanner, and that chart prints
# Both. FERRSPEC stays the stored odds (1.0 / 1.2 / 1.4) and the stored
# assault volley (1,000). "1" does not turn this on. V311_PROFILE "v311" does.
# FERRENGI_ATTACK_MODE stays the one-volley gate and still reads the FERRSPEC
# counts while this switch is off.
FERRENGI_ODDS_MODE = "legacy"  # "legacy" | "v311"


def ferrengi_odds_live() -> bool:
    """True when Ferrengi odds, the assault volley, and that scanner follow the Bible chart."""
    return FERRENGI_ODDS_MODE == "v311" or v311_profile()


# NOTE 164 GAP 6.11. v3.06 revision history: when a corporation is disbanded,
# planets and ships in the C.E.O.'s sector become the C.E.O.'s. Outside that
# sector, ships become abandoned. Planets are already CORP_PLANET_DISBAND_MODE.
# Off, every parked corporate hull becomes defunct, which is what cs24 asserts.
# On, a parked hull in the living C.E.O.'s sector becomes that C.E.O.'s
# personal ship. A dead C.E.O. takes nothing. The ship the C.E.O. is flying
# waits until they leave it. "1" does not turn this on.
CORP_SHIP_DISBAND_MODE = "legacy"  # "legacy" | "v311"


def corp_ship_disband_live() -> bool:
    """True when a parked corporate ship in the living C.E.O.'s sector becomes the C.E.O.'s."""
    return CORP_SHIP_DISBAND_MODE == "v311" or v311_profile()


# NOTE 164 GAP 12.6. Cabal twgs.html prints Tournament Mode Off and Maximum
# times blown up Unlimited. A later lockout is not a v3.11 number and is not
# added. Off, the legacy destroy line still prints death #N/3. On, and only
# when elimination_deaths is 0, that line says unlimited and does not print
# /3. DEATH_MODE and DEATH_DELAY_MODE stay as they are. "1" does not turn
# this on.
TIMES_BLOWN_MODE = "legacy"  # "legacy" | "v311"


def times_blown_live() -> bool:
    """True when an unlimited game says so on the legacy destroy line."""
    return TIMES_BLOWN_MODE == "v311" or v311_profile()


# NOTE 164 GAP 13.4. The v3.11 revision stopped the fighter report from listing
# sectors with 0 fighters. The Bible tells a trader to leave one fighter so
# the report fires when someone finds the planet. Off, fighter_report returns
# nothing. On, it lists sectors where that trader owns a count above 0. No
# hit sentence is invented, and the list is not an observation field. "1"
# does not turn this on.
FIGHTER_REPORT_MODE = "legacy"  # "legacy" | "v311"


def fighter_report_live() -> bool:
    """True when fighter_report lists this trader's sectors and omits a count of 0."""
    return FIGHTER_REPORT_MODE == "v311" or v311_profile()


# NOTE 102 GAP 9.2. The midnight +1 for a trader who spent a turn, and the +1
# on a personal first dock, already run under DISCOVERY_EXP_MODE (runner.tick_day,
# runner._handle_trade). Atomic destruction of an ordinary port already pays
# xp_award("destroy_port"), which is 50 while RANK_MODE is tw2002.
# This switch is the missing pay on a StarDock or Class 0 kill: +50 experience
# and -50 alignment (EXPERIENCE_ALIGNMENT.md x11). Stored default stays legacy.
EXP_SOURCES_MODE = "legacy"  # "legacy" | "live"
PORT_DESTROY_EXPERIENCE = 50
PORT_DESTROY_ALIGNMENT = 50


def exp_sources_live() -> bool:
    """True when destroying a special port pays the documented 50 experience."""
    return EXP_SOURCES_MODE == "live" or tw2002_live_profile() or v311_profile()


# NOTE 102 GAP 11.10. Cabal formulas.html (Destroying a port): StarDock and the
# Class 0 ports do not use the ordinary rating × (22 / odds) line. A stock
# Interdictor needs about 248,000 fighters and 32,000 shields the first time
# (or about 280,000 fighters with no shields), in about 11 waves of 15,000.
# After any of those ports has been killed, the rest, including the rebuilt
# one, need about 890,000. Ratings are described as going from 2,500 to 5,000.
# UNVERIFIED, searched: cabal formulas.html, REV v3.10 (14-day Fed rebuild of
# Sol, Alpha Centauri, Rylos and Stargate Alpha I; StarDock rebuilds on the
# same radiation clear). Return fire has no consistent pattern in that page,
# so a wave only spends the fighters sent. It does not invent a barrage.
SPECIAL_PORT_DEFENCE_MODE = "legacy"  # "legacy" | "live"
SPECIAL_PORT_FIGS_FIRST = 248_000
SPECIAL_PORT_FIGS_AFTER = 890_000
SPECIAL_PORT_RATING_FIRST = 2_500
SPECIAL_PORT_RATING_AFTER = 5_000
SPECIAL_PORT_RADIATION_DAYS = 14


def special_port_defence_live() -> bool:
    """True when StarDock and Class 0 ports use the huge defence and Fed rebuild."""
    return SPECIAL_PORT_DEFENCE_MODE == "live" or tw2002_live_profile() or v311_profile()


def special_port_figs_needed(already_destroyed: int) -> int:
    """Fighters that have to be spent before that port goes down."""
    if int(already_destroyed) > 0:
        return SPECIAL_PORT_FIGS_AFTER
    return SPECIAL_PORT_FIGS_FIRST


def special_port_rating(already_destroyed: int) -> int:
    """The cabal's stated rating for the current rebuild tier."""
    if int(already_destroyed) > 0:
        return SPECIAL_PORT_RATING_AFTER
    return SPECIAL_PORT_RATING_FIRST


# NOTE 102 GAP 6.6. Iago's War Manual v1.1 (Leonard Adolph): an overloaded
# sector gets a daily log line with the sector number every Extern, and a
# collision is random, not guaranteed. The two planets that go are random,
# not by time, name or number. The destruction line names them and leaves
# the sector number out. Gypsy's "unstable planetary crusts" is the Class H
# blurb, not this rule. The chance is not printed.
# UNVERIFIED, searched: Iago_War_Manual.txt v1.1, Gypsy_Big_Dummies_Guide.html,
# Someguy_MBBS_manual.txt, OldBBS_TW.faq.txt, REV v3 (collisions generate NavHaz).
# 10 percent per planet over the cap of 5, never past 100, is the stand-in.
# Sector 1 is skipped (Old FAQ v2 says overload skips sector one).
PLANET_COLLISION_MODE = "legacy"  # "legacy" | "live"
PLANET_COLLISION_PCT_PER_EXCESS = 10


def planet_collision_live() -> bool:
    """True when Extern can collide planets in an overloaded sector."""
    return PLANET_COLLISION_MODE == "live" or tw2002_live_profile() or v311_profile()


# NOTE 102 GAP 14.3. Cabal glossary: one create-and-destroy loop is 75
# experience. Genesis already pays 25 and the destroy pays 50 (XP_AWARDS_TW2002),
# which is 75 and not more. The missing step is that the owner was refused
# ("planet is friendly"), so the loop could not be finished. This switch
# lets the owner destroy that planet. It does not add a third award.
PLANET_BUST_EXP_MODE = "legacy"  # "legacy" | "live"


def planet_bust_exp_live() -> bool:
    """True when the owner may destroy a planet they created."""
    return PLANET_BUST_EXP_MODE == "live" or tw2002_live_profile() or v311_profile()


# NOTE 105. gb15 and the MBBS manual: capturing a player takes the credits
# they are carrying, the same as a kill. The engine already does that
# (apply_manned_capture -> on_ship_lost). This switch is only the cockpit
# sentence. Stored default stays legacy, so a capture line stays as it was.
CAPTURE_CREDIT_LINE_MODE = "legacy"  # "legacy" | "live"


def capture_credit_line_live() -> bool:
    """True when a capture result says the credits that were on board."""
    return CAPTURE_CREDIT_LINE_MODE == "live" or tw2002_live_profile() or v311_profile()
# terra-colonist-units-fix-v1 (NOTE 89). Terra live stores people in the hold
# (TERRA_LIVE_PER_HOLD). Class M already converts. Every other class stores
# handbook colonists, so a drop of one hold must land as 1, not 1,000.
# "legacy" keeps the one-to-one copy. "live" divides on the way down and
# multiplies on the way up. A remainder is refused.
# The net-worth switch prices those people as handbook thousands. A non-M
# planet that already stores handbook units is not divided again.
COLONIST_UNITS_MODE = "legacy"  # "legacy" | "live"
COLONIST_NW_UNITS_MODE = "legacy"  # "legacy" | "live"
COLONIST_MOVE_BY_THOUSAND = "colonists move by the thousand"


def colonist_units_live() -> bool:
    """True when a non-M planet speaks handbook colonists and the hold speaks people."""
    return COLONIST_UNITS_MODE == "live" or tw2002_live_profile() or v311_profile()


def colonist_nw_units() -> bool:
    """True when people in a cargo hold are scored as handbook thousands."""
    return COLONIST_NW_UNITS_MODE == "live" or tw2002_live_profile() or v311_profile()


def colonist_handbook_transfer(class_id) -> bool:
    """True when this planet's colonist move crosses the people/handbook line.

    Class M keeps its own people path. Legacy Terra stores one colonist per
    hold, which is already the handbook unit, so there is nothing to convert.
    """
    token = str(getattr(class_id, "value", class_id))
    return token != "M" and colonist_units_live() and int(colonists_per_hold()) > 1


def colonist_people_to_handbook(people: int) -> tuple[int, bool]:
    """Handbook colonists for this many cargo people, and whether it was exact."""
    per = int(colonists_per_hold())
    amount = int(people)
    if per <= 1:
        return amount, True
    return amount // per, amount % per == 0


def colonist_handbook_to_people(units: int) -> int:
    """Cargo people for this many handbook colonists."""
    per = int(colonists_per_hold())
    amount = int(units)
    if per <= 1:
        return amount
    return amount * per


def colonist_score_qty(qty: int) -> int:
    """Colonists net worth should count. People in a hold become thousands.

    Iago War Manual: one hold is one thousand people. S1 / TWFAQ_20PLANET
    counts the handbook colonist in thousands, and COLONIST_PRICE is that unit.
    """
    amount = int(qty)
    if amount <= 0:
        return 0
    if colonist_nw_units() and int(colonists_per_hold()) > 1:
        return amount // int(colonists_per_hold())
    return amount


# colonist-units-clarity-v1 (NOTE 101). No new switch and no new helper row.
# The live switches already agree: one Terra hold is 1,000 people, and that
# thousand is one planet unit. This only names that unit. Profile-off leaves
# every count as it was, because none of these helpers is on.
def colonist_clarity_on() -> bool:
    """True when a screen should say colonists in thousands, with the people beside them."""
    return (
        class_m_fidelity_live()
        or colonist_units_live()
        or terra_colonist_live()
        or cockpit_fields_on()
    )


def colonist_stored_is_people(class_id) -> bool:
    """True when this planet's colonist pools are people, not handbook thousands."""
    token = str(getattr(class_id, "value", class_id))
    return token == "M" and class_m_fidelity_live()


def colonist_quote(stored: int, *, people: bool) -> dict[str, int | str]:
    """Handbook thousands and the people they stand for."""
    amount = max(0, int(stored))
    per = int(CLASS_M_PEOPLE_PER_THOUSAND)
    if people:
        return {"unit": "thousands", "thousands": amount // per, "people": amount}
    return {"unit": "thousands", "thousands": amount, "people": amount * per}


# The 30-hold haul is the NOTE 101 example (one Terra take). A published
# "trips remaining" figure was not found. UNVERIFIED as a screen quote.
CITADEL_HAUL_HOLDS = 30


# NOTE 143 GAP 6.10. cabal formulas.html, tested on Classic Gold and MBBS:
# killing a trader who is on the planet by destroying it pays
# (enemy experience x 0.1666) plus the planet blow, and
# (enemy alignment x -0.3333) plus the blow. The blow is already
# destroy_planet (50) and PLANET_DESTROY_ALIGNMENT_TW2002 (1).
# 10,000 x 0.1666 is 1,666. 10,000 x 0.3333 is 3,333.
# A citadel makes the blow experience "more". That extra is not printed.
# Colonist-kill alignment is an ellipsis on the Alignment page.
# "legacy" lifts the other trader off. "v311" pods them and pays the two products.
PLANET_ZDY_MODE = "legacy"  # "legacy" | "v311"
ZDY_EXP_NUM = 1666
ZDY_EXP_DEN = 10_000
ZDY_ALIGN_NUM = 3333
ZDY_ALIGN_DEN = 10_000


def planet_zdy_live() -> bool:
    """True when destroying a planet kills a trader who is sitting on it."""
    return PLANET_ZDY_MODE == "v311" or v311_profile()


def zdy_kill_experience(enemy_exp: int) -> int:
    """Experience for the trader, apart from the 50 for blowing the planet."""
    return int(int(enemy_exp) * ZDY_EXP_NUM / ZDY_EXP_DEN)


def zdy_kill_alignment(enemy_align: int) -> int:
    """Alignment for the trader, apart from the -1 for blowing the planet.

    Truncates toward zero so 10,000 x 0.3333 is 3,333, matching the printed examples.
    """
    scaled = int(int(enemy_align) * ZDY_ALIGN_NUM / ZDY_ALIGN_DEN)
    return -scaled


# NOTE 143. S1 atmosphere order: one shot, then shields, then another shot
# only after the last shield falls. Legacy also fires that second shot up
# front when no shields are fighting.
QUASAR_ATM_ORDER_MODE = "legacy"  # "legacy" | "v311"


def quasar_atm_order_live() -> bool:
    """True when a shieldless landing takes one atmosphere shot, not two."""
    return QUASAR_ATM_ORDER_MODE == "v311" or v311_profile()


# NOTE 143. Revision history through v3.11 (03/05/97): "Interdictor generators
# don't function at StarDock and Terra." Terra's colonists are in the StarDock
# sector, so that one sector is both places. Everywhere else the 500-fuel hold stays.
PLANET_INTERDICT_SAFE_MODE = "legacy"  # "legacy" | "v311"


def planet_interdict_safe_live() -> bool:
    """True when an interdictor is quiet at StarDock."""
    return PLANET_INTERDICT_SAFE_MODE == "v311" or v311_profile()


def planet_interdict_quiet(sector_id: int) -> bool:
    """True when this sector's interdictor must not hold a ship."""
    return planet_interdict_safe_live() and int(sector_id) == int(STARDOCK_SECTOR)


def citadel_colonist_quote(
    level: int, need_stored: int, have_stored: int, *, people: bool, haul_holds: int = CITADEL_HAUL_HOLDS,
) -> dict[str, int | str]:
    """Need, have, and the unit, plus one sentence a form can print."""
    need = colonist_quote(need_stored, people=people)
    have = colonist_quote(have_stored, people=people)
    haul = max(1, int(haul_holds))
    short = max(0, int(need["thousands"]) - int(have["thousands"]))
    trips = (short + haul - 1) // haul if short else 0
    plain = (
        f"Level {int(level)} needs {int(need['thousands']):,} (thousands) colonists = {int(need['people']):,}; "
        f"you have {int(have['thousands']):,} (thousands)"
    )
    if trips:
        plain += f"; about {trips} more Terra trips with {haul} holds"
    return {
        "need": int(need["thousands"]),
        "have": int(have["thousands"]),
        "unit": "thousands",
        "need_people": int(need["people"]),
        "have_people": int(have["people"]),
        "trips": trips,
        "haul_holds": haul,
        "plain": plain,
    }


# NOTE 177 GAP 10.1 (ruling, V311_SOURCE_CONFLICTS.md). bc24 CFS_CEO_RULE keeps
# "only the C.E.O. buys a FlagShip". Gypsy_Big_Dummies_Guide: "Only C.E.O.'s can
# use Corporate Flagships so they are not available for trade." On, a corp mate
# who is not the C.E.O. cannot board a parked Corporate FlagShip. Legacy lets him.
CFS_CEO_USE_MODE = "legacy"  # "legacy" | "v311"


def cfs_ceo_use_live() -> bool:
    """True when only a C.E.O. may board a Corporate FlagShip he does not own."""
    return CFS_CEO_USE_MODE == "v311" or v311_profile()


# NOTE 177 GAP 6.10 (ruling). Bible (S3): destroying a planet "takes your
# alignment down (50 points down)". Cabal formulas.html prints -1. The ruling
# takes the Bible. On, the blow costs PLANET_BLOW_ALIGN_V311; legacy keeps
# PLANET_DESTROY_ALIGNMENT_TW2002 (1). The +50 experience is the same both ways.
PLANET_BLOW_ALIGN_MODE = "legacy"  # "legacy" | "v311"
PLANET_BLOW_ALIGN_V311 = 50


def planet_blow_align_live() -> bool:
    """True when blowing a planet costs the Bible's 50 alignment."""
    return PLANET_BLOW_ALIGN_MODE == "v311" or v311_profile()


def planet_blow_alignment_loss() -> int:
    """Alignment the blow takes while RANK_MODE is tw2002."""
    if planet_blow_align_live():
        return int(PLANET_BLOW_ALIGN_V311)
    return int(PLANET_DESTROY_ALIGNMENT_TW2002)
