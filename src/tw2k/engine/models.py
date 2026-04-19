"""Data models for the TW2K-AI engine.

All game state lives here as Pydantic models. The engine mutates these
in-place (wrapped by apply_action) and emits Events describing every change.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from . import constants as K

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Commodity(str, Enum):
    FUEL_ORE = "fuel_ore"
    ORGANICS = "organics"
    EQUIPMENT = "equipment"
    COLONISTS = "colonists"  # pseudo-commodity, filled in holds, not traded at ports


TRADE_COMMODITIES: tuple[Commodity, ...] = (
    Commodity.FUEL_ORE,
    Commodity.ORGANICS,
    Commodity.EQUIPMENT,
)


class PortClass(int, Enum):
    FEDERAL = 0
    CLASS_1_BSS = 1
    CLASS_2_BSB = 2
    CLASS_3_SBB = 3
    CLASS_4_SSB = 4
    CLASS_5_SBS = 5
    CLASS_6_BBS = 6
    CLASS_7_BBB = 7
    STARDOCK = 8

    @property
    def code(self) -> str:
        codes = {0: "FED", 1: "BSS", 2: "BSB", 3: "SBB", 4: "SSB",
                 5: "SBS", 6: "BBS", 7: "BBB", 8: "STARDOCK"}
        return codes[self.value]


class ShipClass(str, Enum):
    MERCHANT_CRUISER = "merchant_cruiser"
    SCOUT_MARAUDER = "scout_marauder"
    MISSILE_FRIGATE = "missile_frigate"
    BATTLESHIP = "battleship"
    CORPORATE_FLAGSHIP = "corporate_flagship"
    COLONIAL_TRANSPORT = "colonial_transport"
    CARGOTRAN = "cargotran"
    MERCHANT_FREIGHTER = "merchant_freighter"
    HAVOC_GUNSTAR = "havoc_gunstar"
    IMPERIAL_STARSHIP = "imperial_starship"


class FighterMode(str, Enum):
    DEFENSIVE = "defensive"
    OFFENSIVE = "offensive"
    TOLL = "toll"


class MineType(str, Enum):
    ARMID = "armid"
    LIMPET = "limpet"
    ATOMIC = "atomic"


class PlanetClass(str, Enum):
    M = "M"  # Earth-type
    K = "K"
    L = "L"
    O = "O"
    H = "H"
    U = "U"
    C = "C"


class EventKind(str, Enum):
    GAME_START = "game_start"
    DAY_TICK = "day_tick"
    WARP = "warp"
    WARP_BLOCKED = "warp_blocked"
    AUTOPILOT = "autopilot"
    TRADE = "trade"
    TRADE_FAILED = "trade_failed"
    SCAN = "scan"
    PROBE = "probe"
    DEPLOY_FIGHTERS = "deploy_fighters"
    DEPLOY_MINES = "deploy_mines"
    MINE_DETONATED = "mine_detonated"
    LIMPET_REPORT = "limpet_report"
    PHOTON_FIRED = "photon_fired"
    PHOTON_HIT = "photon_hit"
    ATOMIC_DETONATION = "atomic_detonation"
    PORT_DESTROYED = "port_destroyed"
    COMBAT = "combat"
    SHIP_DESTROYED = "ship_destroyed"
    PLAYER_ELIMINATED = "player_eliminated"
    PLANET_ORPHANED = "planet_orphaned"
    FERRENGI_SPAWN = "ferrengi_spawn"
    FERRENGI_MOVE = "ferrengi_move"
    FERRENGI_ATTACK = "ferrengi_attack"
    LAND_PLANET = "land_planet"
    LIFTOFF = "liftoff"
    GENESIS_DEPLOYED = "genesis_deployed"
    ASSIGN_COLONISTS = "assign_colonists"
    BUILD_CITADEL = "build_citadel"
    CITADEL_COMPLETE = "citadel_complete"
    BUY_SHIP = "buy_ship"
    BUY_EQUIP = "buy_equip"
    CORP_CREATE = "corp_create"
    CORP_INVITE = "corp_invite"
    CORP_JOIN = "corp_join"
    CORP_LEAVE = "corp_leave"
    CORP_DEPOSIT = "corp_deposit"
    CORP_WITHDRAW = "corp_withdraw"
    CORP_MEMO = "corp_memo"
    ALLIANCE_PROPOSED = "alliance_proposed"
    ALLIANCE_FORMED = "alliance_formed"
    ALLIANCE_BROKEN = "alliance_broken"
    HAIL = "hail"
    BROADCAST = "broadcast"
    AGENT_THOUGHT = "agent_thought"
    AGENT_ERROR = "agent_error"
    FED_RESPONSE = "fed_response"
    GAME_OVER = "game_over"


# ---------------------------------------------------------------------------
# Ports
# ---------------------------------------------------------------------------


class PortStock(BaseModel):
    current: int
    maximum: int


class Port(BaseModel):
    class_id: PortClass
    stock: dict[Commodity, PortStock] = Field(default_factory=dict)
    experience: dict[str, float] = Field(default_factory=dict)  # per-player familiarity 0..1
    name: str = ""

    @property
    def code(self) -> str:
        return self.class_id.code

    def buys(self, commodity: Commodity) -> bool:
        trades = K.PORT_CLASS_TRADES.get(int(self.class_id), (None, None, None))
        idx = {Commodity.FUEL_ORE: 0, Commodity.ORGANICS: 1, Commodity.EQUIPMENT: 2}
        if commodity not in idx:
            return False
        entry = trades[idx[commodity]]
        return entry is True

    def sells(self, commodity: Commodity) -> bool:
        trades = K.PORT_CLASS_TRADES.get(int(self.class_id), (None, None, None))
        idx = {Commodity.FUEL_ORE: 0, Commodity.ORGANICS: 1, Commodity.EQUIPMENT: 2}
        if commodity not in idx:
            return False
        entry = trades[idx[commodity]]
        return entry is False


# ---------------------------------------------------------------------------
# Sector-level state
# ---------------------------------------------------------------------------


class FighterDeployment(BaseModel):
    owner_id: str
    count: int
    mode: FighterMode = FighterMode.DEFENSIVE


class MineDeployment(BaseModel):
    owner_id: str
    kind: MineType
    count: int


class Sector(BaseModel):
    id: int
    warps: list[int] = Field(default_factory=list)
    port: Port | None = None
    planet_ids: list[int] = Field(default_factory=list)
    fighters: FighterDeployment | None = None
    mines: list[MineDeployment] = Field(default_factory=list)
    # Players currently in this sector (bookkeeping mirror of player.sector_id)
    occupant_ids: list[str] = Field(default_factory=list)
    nav_hazard: float = 0.0
    # Display hint for the map view (computed at generation time)
    x: float = 0.0
    y: float = 0.0


# ---------------------------------------------------------------------------
# Planets
# ---------------------------------------------------------------------------


class Planet(BaseModel):
    id: int
    sector_id: int
    name: str
    class_id: PlanetClass
    owner_id: str | None = None
    corp_ticker: str | None = None
    citadel_level: int = 0
    # When upgrading, target_level > citadel_level until citadel_complete_day arrives.
    citadel_target: int = 0
    citadel_complete_day: int | None = None
    colonists: dict[Commodity, int] = Field(default_factory=lambda: {
        Commodity.FUEL_ORE: 0,
        Commodity.ORGANICS: 0,
        Commodity.EQUIPMENT: 0,
        Commodity.COLONISTS: 0,  # "fighters" pool — colonists assigned to defense
    })
    stockpile: dict[Commodity, int] = Field(default_factory=lambda: {
        Commodity.FUEL_ORE: 0,
        Commodity.ORGANICS: 0,
        Commodity.EQUIPMENT: 0,
    })
    fighters: int = 0
    shields: int = 0
    treasury: int = 0


# ---------------------------------------------------------------------------
# Ships & Players
# ---------------------------------------------------------------------------


class Ship(BaseModel):
    ship_class: ShipClass = ShipClass.MERCHANT_CRUISER
    name: str = "Unnamed"
    holds: int = K.STARTING_HOLDS
    cargo: dict[Commodity, int] = Field(default_factory=lambda: {c: 0 for c in Commodity})
    fighters: int = K.STARTING_FIGHTERS
    shields: int = 0
    mines: dict[MineType, int] = Field(default_factory=lambda: {
        MineType.ARMID: 0, MineType.LIMPET: 0, MineType.ATOMIC: 0,
    })
    genesis: int = 0
    photon_missiles: int = 0
    ether_probes: int = 0
    # If > 0, fighters are disabled for this many remaining ticks (photon hit).
    photon_disabled_ticks: int = 0
    # Weighted-average unit cost paid for the current holdings of each
    # commodity. Lets the agent see "I have 75 organics bought @ avg 19cr"
    # when planning a sell — without this they have to reconstruct cost
    # basis from their scratchpad or a rolling event feed which scrolls.
    # Only meaningful for commodities with cargo[c] > 0; on buy we do a
    # weighted-avg update; on sell the avg stays put (we're just reducing
    # qty, not changing what we paid for what's left); on assign_colonists /
    # genesis / other non-trade consumption qty hits zero and the cost is
    # cleared. Seeded "free" cargo (e.g. starter colonists) has cost 0.
    cargo_cost: dict[Commodity, float] = Field(
        default_factory=lambda: {c: 0.0 for c in Commodity}
    )

    @property
    def cargo_used(self) -> int:
        return sum(self.cargo.values())

    @property
    def cargo_free(self) -> int:
        return self.holds - self.cargo_used


class Player(BaseModel):
    id: str
    name: str
    credits: int = K.STARTING_CREDITS
    alignment: int = 0
    experience: int = 0
    ship: Ship = Field(default_factory=Ship)
    sector_id: int = K.STARDOCK_SECTOR
    planet_landed: int | None = None
    corp_ticker: str | None = None
    turns_today: int = 0
    turns_per_day: int = K.STARTING_TURNS_PER_DAY
    alive: bool = True
    # Persistent knowledge / memory
    known_ports: dict[int, dict] = Field(default_factory=dict)  # sector_id -> {class, stock_snapshot, last_seen_day}
    known_sectors: set[int] = Field(default_factory=set)
    inbox: list[dict] = Field(default_factory=list)
    # Agent's own working scratchpad (opaque to engine)
    scratchpad: str = ""
    # Structured 3-horizon goals the agent writes on each turn and sees in the
    # next turn's observation. Separated from the free-form scratchpad so the
    # observation can surface them prominently and so behavior over many
    # turns is anchored in an explicit target ("reach 45k and buy cargotran")
    # rather than drifting. Each field stays <=240 chars — the engine trims.
    goal_short: str = ""   # this turn + next ~2-3 (e.g. "finish trip, warp 267->181->487")
    goal_medium: str = ""  # next in-game day (e.g. "grind org pair to 45k, buy cargotran")
    goal_long: str = ""    # whole-match plan (e.g. "100M cr victory via 2 citadel L3 planets")
    # Rolling ledger of this player's own trades — last 50 entries. Each is
    # a dict of {day, tick, sector_id, commodity, qty, side, unit, total,
    # realized_profit}. realized_profit is non-None only on `sell` and is the
    # (unit - basis_avg) * qty the sell actually realized, using the cargo
    # cost basis at time of sale. Lets the agent audit "what did my last 5
    # trades actually earn me?" without re-deriving from the global feed.
    trade_log: list[dict] = Field(default_factory=list)
    # Metadata — agent kind for display
    agent_kind: str = "heuristic"
    color: str = "#6ee7ff"
    # Number of times this player's ship has been destroyed (eliminated when reaches MAX).
    deaths: int = 0
    # Active alliance ticker symbols (with other players, separate from corp).
    alliances: list[str] = Field(default_factory=list)
    # Recent ether-probe readings keyed by sector_id -> {day, payload}.
    probe_log: dict[int, dict] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        # Ensure known_sectors is a set after Pydantic deserialization
        if isinstance(self.known_sectors, list):
            self.known_sectors = set(self.known_sectors)

    @property
    def net_worth(self) -> int:
        """Ship-side net worth (credits + everything on this Player's ship).

        Does NOT include owned planets — for full net worth use the
        `full_net_worth(universe, player)` helper in engine.runner which
        layers planet assets on top. We keep two flavors because:

          * Many internal uses (tests, quick sampling, history tick)
            don't have a universe reference handy.
          * Victory checks / observation / spectator snapshot always
            have the universe and should use the full number so planet
            investment actually wins you the game.

        Composition:
          credits
          + tradable cargo at base prices (FO/Org/Eq/Colonists)
          + ship hull resale (50% of buy price)
          + fighters, shields, mines, photon missiles, ether probes,
            genesis torpedoes at their StarDock prices
        """
        cargo_value = (
            self.ship.cargo.get(Commodity.FUEL_ORE, 0) * K.COMMODITY_BASE_PRICE["fuel_ore"]
            + self.ship.cargo.get(Commodity.ORGANICS, 0) * K.COMMODITY_BASE_PRICE["organics"]
            + self.ship.cargo.get(Commodity.EQUIPMENT, 0) * K.COMMODITY_BASE_PRICE["equipment"]
            # Colonists in cargo were almost certainly bought from StarDock
            # at K.COLONIST_PRICE per head — value them at what they cost
            # to acquire, not at zero.
            + self.ship.cargo.get(Commodity.COLONISTS, 0) * K.COLONIST_PRICE
        )
        ship_value = int(K.SHIP_SPECS[self.ship.ship_class.value]["cost"] * 0.5)
        # Ship equipment — all valued at StarDock buy price (mirrors
        # _handle_buy_equip). Shields are 10cr/unit, mines/missiles/probes
        # at their respective constants. This means a player who just
        # bought a Genesis torpedo (25,000cr) shows up 25,000cr richer in
        # net worth UNTIL they deploy it, at which point the value flips
        # to a (potentially much larger) planet asset.
        equip_value = (
            self.ship.fighters * K.FIGHTER_COST
            + self.ship.shields * 10
            + self.ship.mines.get(MineType.ARMID, 0) * K.ARMID_MINE_COST
            + self.ship.mines.get(MineType.LIMPET, 0) * K.LIMPET_MINE_COST
            + self.ship.mines.get(MineType.ATOMIC, 0) * K.ATOMIC_MINE_COST
            + self.ship.photon_missiles * K.PHOTON_MISSILE_COST
            + self.ship.ether_probes * K.ETHER_PROBE_COST
            + self.ship.genesis * K.GENESIS_TORPEDO_COST
        )
        return self.credits + cargo_value + ship_value + equip_value


# ---------------------------------------------------------------------------
# Corporations
# ---------------------------------------------------------------------------


class Corporation(BaseModel):
    ticker: str
    name: str
    ceo_id: str
    member_ids: list[str] = Field(default_factory=list)
    treasury: int = 0
    planet_ids: list[int] = Field(default_factory=list)
    invited_ids: list[str] = Field(default_factory=list)
    formed_day: int = 0


# ---------------------------------------------------------------------------
# Diplomacy / intel
# ---------------------------------------------------------------------------


class Alliance(BaseModel):
    id: str           # short id, e.g. "A1"
    member_ids: list[str]
    proposed_by: str
    formed_day: int
    active: bool = False  # False until both sides accept


class LimpetTrack(BaseModel):
    """A limpet stuck to a player's hull — owner can query its location."""
    owner_id: str       # the deployer (intel consumer)
    target_id: str      # which player is being tracked
    placed_sector: int
    placed_day: int


# ---------------------------------------------------------------------------
# Ferrengi
# ---------------------------------------------------------------------------


class FerrengiShip(BaseModel):
    id: str
    name: str
    sector_id: int
    aggression: int
    fighters: int
    shields: int
    ship_class: ShipClass = ShipClass.MERCHANT_CRUISER
    alive: bool = True


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class Event(BaseModel):
    seq: int
    tick: int
    day: int
    kind: EventKind
    actor_id: str | None = None
    sector_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    # Short human-readable summary for the event feed
    summary: str = ""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class GameConfig(BaseModel):
    seed: int = 42
    universe_size: int = K.DEFAULT_UNIVERSE_SIZE
    avg_warps: float = K.DEFAULT_AVG_WARPS
    one_way_fraction: float = K.DEFAULT_ONE_WAY_FRACTION
    max_days: int = K.VICTORY_DEFAULT_MAX_DAYS
    turns_per_day: int = K.STARTING_TURNS_PER_DAY
    # Per-player starting credit balance. Defaults to the canonical 20k so a
    # fresh match feels "authentic TW2002", but we allow overrides so sanity
    # runs can skip the 2-day trade ramp-up and land on a ship-upgrade /
    # genesis-deploy decision inside the observable window.
    starting_credits: int = K.STARTING_CREDITS
    action_delay_s: float = 0.6
    llm_think_cap_s: float = 20.0
    enable_ferrengi: bool = True
    enable_planets: bool = True
    enable_corps: bool = True
    corp_max_members: int = K.CORP_MAX_MEMBERS_DEFAULT
    planet_spawn_probability: float = 0.03
    ferrengi_per_day: int = K.FERRENGI_SPAWN_PER_DAY


# ---------------------------------------------------------------------------
# Root state
# ---------------------------------------------------------------------------


class Universe(BaseModel):
    config: GameConfig
    sectors: dict[int, Sector]
    players: dict[str, Player] = Field(default_factory=dict)
    corporations: dict[str, Corporation] = Field(default_factory=dict)
    planets: dict[int, Planet] = Field(default_factory=dict)
    ferrengi: dict[str, FerrengiShip] = Field(default_factory=dict)
    alliances: dict[str, Alliance] = Field(default_factory=dict)
    # Active limpet tracks; keyed by f"{owner}:{target}"
    limpets: dict[str, LimpetTrack] = Field(default_factory=dict)
    next_planet_id: int = 1
    next_alliance_id: int = 1
    events: list[Event] = Field(default_factory=list)
    day: int = 1
    tick: int = 0
    seq: int = 0
    finished: bool = False
    winner_id: str | None = None
    win_reason: str = ""

    # ------------- event helpers ------------- #
    def emit(
        self,
        kind: EventKind,
        *,
        actor_id: str | None = None,
        sector_id: int | None = None,
        payload: dict | None = None,
        summary: str = "",
    ) -> Event:
        self.seq += 1
        ev = Event(
            seq=self.seq,
            tick=self.tick,
            day=self.day,
            kind=kind,
            actor_id=actor_id,
            sector_id=sector_id,
            payload=payload or {},
            summary=summary,
        )
        self.events.append(ev)
        return ev
