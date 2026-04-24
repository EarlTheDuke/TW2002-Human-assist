"""Game constants — prices, caps, costs. Tunable but defaults match classic TW2002."""

from __future__ import annotations

# --- Commodities --------------------------------------------------------------

COMMODITY_BASE_PRICE = {
    "fuel_ore": 18,
    "organics": 25,
    "equipment": 36,
}

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
PORT_REGEN_PER_DAY = 0.05  # 5% per game day toward max

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

# --- Turn costs ---------------------------------------------------------------

TURN_COST = {
    "warp": 2,
    "trade": 3,
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
}

# --- Combat / fighters / mines ------------------------------------------------

FIGHTER_COST = 50  # cr per fighter at StarDock
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
GENESIS_DEPLOY_TURN_COST = 4
# Minimum hops from sector 1 (StarDock) for legal Genesis deployment.
# Classic TW2002 required planets to be "deep" — you couldn't drop one in
# the Federation's back yard. FedSpace only covers 1..10, but many of those
# sectors have >10-hop reachability paths and some outer sectors are
# 1-hop from StarDock; a hops-based rule guarantees real distance.
GENESIS_MIN_HOPS_FROM_STARDOCK = 3
# Founding population Genesis torpedoes bring to life. Tuned so Citadel L1
# (1,000 colonists) is immediately buildable and natural growth can start.
GENESIS_SEED_COLONISTS = 2_500
# Price per colonist when buying from Terra/StarDock (classic TW2002: ~10 cr).
# Cheap enough that you can fully load a 20-hold merchant cruiser for 200 cr,
# but the REAL cost is the turns spent ferrying them to a distant planet.
COLONIST_PRICE = 10
PLANET_CLASS_WEIGHTS = {
    "M": 0.32, "K": 0.14, "L": 0.14, "O": 0.14,
    "H": 0.10, "U": 0.10, "C": 0.06,
}

# --- Player elimination -------------------------------------------------------
MAX_DEATHS_BEFORE_ELIM = 3

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
