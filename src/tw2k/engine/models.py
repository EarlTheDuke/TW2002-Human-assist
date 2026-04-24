"""Data models for the TW2K-AI engine.

All game state lives here as Pydantic models. The engine mutates these
in-place (wrapped by apply_action) and emits Events describing every change.
"""

from __future__ import annotations

import contextvars
import random
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, PrivateAttr

from . import constants as K

# ---------------------------------------------------------------------------
# actor_kind override (H2 copilot path)
#
# When the AI copilot dispatches an action on behalf of a human, every
# downstream event emitted inside apply_action must carry
# actor_kind="copilot" (not "human") so replay / forensics / spectator UI
# can distinguish "the human typed warp 874" from "the copilot executed
# warp 874 for the human".
#
# We thread the override via contextvar rather than plumbing an extra
# parameter through apply_action's ~500 lines of branches. Any code path
# can wrap a call site with `actor_kind_override("copilot")` and every
# Universe.emit() inside will pick it up. The contextvar nesting is
# async-safe (each task/subtask gets its own copy).
# ---------------------------------------------------------------------------

_actor_kind_override: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tw2k_actor_kind_override", default=None
)


class actor_kind_override:  # noqa: N801 - contextmanager style
    """Scope a non-None actor_kind onto every Universe.emit() in the with-block.

    Used by the copilot path to tag events it triggered on behalf of a
    HUMAN player. Nested scopes stack — innermost wins until exit.
    """

    __slots__ = ("_kind", "_token")

    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._token: contextvars.Token | None = None

    def __enter__(self) -> actor_kind_override:
        self._token = _actor_kind_override.set(self._kind)
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._token is not None:
            _actor_kind_override.reset(self._token)
            self._token = None

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PlayerKind(str, Enum):
    """What is driving a Player's actions.

    Added in Phase H0 for the human-player feature. The runner branches
    on this to decide how to source the next action for a player:
      * HEURISTIC -> call the deterministic rule engine
      * LLM       -> send the observation to the configured provider
      * HUMAN     -> wait on the HumanAgent queue (blocking) until the
                     /api/human/action endpoint or UI posts an Action.

    Stored on the Player as `agent_kind: str` (not this enum) for backward
    compatibility with replay meta.json and existing spectator snapshots
    that already serialize the string form. Construct this enum lazily
    with `PlayerKind(player.agent_kind)` when you need an exhaustive match.
    """

    HEURISTIC = "heuristic"
    LLM = "llm"
    HUMAN = "human"


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
    PLANET_CLAIMED = "planet_claimed"
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
    # Tier 0 agency metrics — emitted once when the match runner stops. Payload
    # from `match_metrics.build_match_metrics_payload` (counts, LLM health).
    MATCH_METRICS = "match_metrics"
    # Emitted by the runner after every successful LLM call. Payload carries
    # provider, model, input/output/cached token counts, incremental USD cost,
    # and the player's running total so the spectator UI / cost report can
    # render a live budget meter without rescanning the full event log.
    LLM_USAGE = "llm_usage"
    # Emitted once when an LLMAgent gives up after consecutive failures and
    # switches to its HeuristicAgent fallback. Payload carries provider,
    # model, the final failure reason, and the player id. Pairs with the
    # AGENT_THOUGHT "heuristic fallback" lines for operator visibility.
    AGENT_FALLBACK = "agent_fallback"
    # Emitted by the scheduler right before it blocks waiting for a human
    # player's Action (Phase H0). Lets the /play UI pop a "your move"
    # banner and the spectator UI render a "waiting on human" idle state
    # instead of looking frozen. Payload: {"turns_today", "turns_per_day",
    # "sector_id"}. The scheduler then awaits HumanAgent.submit_action().
    HUMAN_TURN_START = "human_turn_start"


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
    # Warp graph for sectors this player has VISITED or SCANNED. Key is the
    # source sector_id, value is the list of direct warps out of that sector
    # as the player observed them. This is the single most important piece
    # of navigational memory: without it, an LLM agent deadloops between
    # a pair of sectors because it cannot remember that "406.warps_out =
    # [475]" meant it had to backtrack first to reach a third sector.
    # Populated on warp entry (for the DESTINATION's warps) and on every
    # scan (for the scanned sector's warps). Never pruned — the map only
    # grows. Stale data is not a concern: sector warps are static in this
    # engine. Port stock drifts, warps don't.
    known_warps: dict[int, list[int]] = Field(default_factory=dict)
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
    # Phase D.2 — set to True by the runner when the PREVIOUS turn's action
    # was a WAIT synthesized from an LLM timeout (i.e. the tick was lost
    # with no real decision made). The next observation surfaces this as a
    # "your last turn was lost to a timeout — re-read your scratchpad"
    # hint so the agent notices the discontinuity instead of silently
    # skipping over it. Cleared after any non-timeout action.
    last_action_was_timeout: bool = False
    # Match 13 — consecutive LLM timeouts for this player. Reset to 0 on any
    # non-timeout action, incremented on each timeout WAIT. Used by
    # build_observation to shrink the observation payload once the agent is
    # demonstrably struggling under 90s (trade_log, known_ports, recent_events).
    recent_timeouts: int = 0
    # Match 13 — captured by _destroy_ship BEFORE the ship gets reset so the
    # post-death re-arm hint can say "you had only {Y} fighters when you
    # died" on the NEXT observation. last_death_day stays set until the
    # player is back to fighters >= 500 AND shields >= 1, at which point
    # the hint self-clears (see observation.py).
    last_death_day: int | None = None
    last_death_fighters: int = 0
    last_death_reason: str = ""

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
    # Who originated the action, categorically. Set by `Universe.emit()`:
    #   * "heuristic" / "llm" / "human"  -> normal autonomous Player action
    #   * "copilot"                      -> action executed on behalf of a
    #                                       human by the AI copilot (H2+)
    #   * "engine" / "ferrengi" / None   -> non-player or unknown origin
    # Auto-resolved from the player's `agent_kind` when actor_id is a known
    # player id; callers can override (e.g. copilot-mediated human turns)
    # by passing `actor_kind=` into `emit`. Optional so existing event
    # logs from before H0 still decode cleanly.
    actor_kind: str | None = None
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
    # When True, every agent spawns at StarDock (sector 1) instead of cycling
    # through FedSpace 1..10. Preserves full freedom of action after spawn;
    # only the opening geometry changes (useful when you want immediate
    # access to buy_ship / buy_equip without a navigation slog back to 1).
    all_start_stardock: bool = False
    action_delay_s: float = 0.6
    # Match 13: bumped 60s -> 90s. Match 12 logged 241 LLM timeouts (P2 alone
    # took 145) against qwen3.5:122b — heavy late-match observations were
    # hitting the 60s cap and forcing a WAIT, losing the decision. 90s is
    # empirically enough headroom for 79-day observations on local GPUs.
    # A match can still override per-run via TW2K_THINK_CAP_S.
    llm_think_cap_s: float = 90.0
    enable_ferrengi: bool = True
    enable_planets: bool = True
    enable_corps: bool = True
    corp_max_members: int = K.CORP_MAX_MEMBERS_DEFAULT
    planet_spawn_probability: float = 0.03
    ferrengi_per_day: int = K.FERRENGI_SPAWN_PER_DAY
    # If True, suppress the elimination and economic sudden-death wins so
    # the match always runs the full `max_days` and is decided by
    # `time_net_worth`. Useful for long watch-mode matches where the
    # point is to exercise late-game mechanics (citadels, corp share,
    # stockpile growth) rather than crown an early winner. The "0 alive"
    # safety branch still fires so a fully-wiped match can't hang the
    # scheduler, and the Universe.finished flag still trips on day cap.
    play_to_day_cap: bool = False


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

    # Per-universe deterministic PRNG. PrivateAttr so it's instance-scoped
    # (not shared across Universe objects, not serialized by model_dump), and
    # lazy-initialized on first `rng` access from `config.seed`. The multiplier
    # matches the legacy module-level _rngs dict (`seed * 7919 + 1`) so any
    # existing seeded match reproduces byte-for-byte after this refactor.
    #
    # Deserializing a saved Universe (model_validate) resets the PRNG to a
    # fresh seeded instance — intentional: we never persisted RNG state under
    # the old global-dict scheme either, and replay rebuilds from seed + the
    # recorded action log rather than from live RNG state.
    _rng: random.Random | None = PrivateAttr(default=None)

    # C1 — first-of-match dedup set. Each kind/key inserted here
    # the first time it is seen gets `is_first: true` stamped on
    # its payload; later emits of the same key pass through unmarked.
    # Private because we never want to persist/serialize this and
    # rebuild it from the event log on replay instead (replays replay
    # emits in order, so the dedup set naturally re-accumulates).
    _firsts_seen: set[str] = PrivateAttr(default_factory=set)

    @property
    def rng(self) -> random.Random:
        """Deterministic per-universe PRNG seeded from `config.seed`.

        Replaces the legacy module-level `_rngs: dict[id(universe), Random]`
        singleton in `engine.runner`, which (a) leaked memory as Universe
        objects were GC'd and (b) could in principle collide on recycled
        `id()` values. Instance-scoped is the right scope.
        """
        if self._rng is None:
            self._rng = random.Random(self.config.seed * 7919 + 1)
        return self._rng

    # ------------- event helpers ------------- #
    def emit(
        self,
        kind: EventKind,
        *,
        actor_id: str | None = None,
        actor_kind: str | None = None,
        sector_id: int | None = None,
        payload: dict | None = None,
        summary: str = "",
    ) -> Event:
        self.seq += 1
        pl = dict(payload) if payload else {}
        # Auto-tag actor_kind from the player record if not explicitly
        # provided. The copilot path (H2+) will pass actor_kind="copilot"
        # — usually via the actor_kind_override() contextmanager so every
        # emit inside a single apply_action picks it up without threading
        # an extra parameter through the whole engine. Explicit kwarg
        # wins over contextvar wins over the player record default.
        if actor_kind is None:
            override = _actor_kind_override.get()
            if override is not None and actor_id is not None:
                actor_kind = override
        if actor_kind is None and actor_id is not None:
            p = self.players.get(actor_id) if isinstance(actor_id, str) else None
            if p is not None:
                actor_kind = p.agent_kind
        # Snapshot who was in the sector AT emit time. Used by the fog-of-war
        # filter in observation.build_observation so that players can only see
        # events that happened in rooms they were actually present in. Using
        # a frozen snapshot (rather than re-reading sector occupants at
        # observation time) keeps visibility correct even if players move
        # away before the event leaves the recent-events window.
        # Prefix underscore marks this as private metadata — it's scrubbed
        # before the event dict is exposed to any LLM agent.
        if sector_id is not None and "_witnesses" not in pl:
            sector = self.sectors.get(sector_id) if isinstance(sector_id, int) else None
            if sector is not None:
                pl["_witnesses"] = list(sector.occupant_ids)
            else:
                pl["_witnesses"] = []
        # C1 — stamp `is_first` on notable-kind payloads the first time
        # they are emitted. Spectators key the FIRST chip off this flag
        # (A4 previously heuristic-detected client-side; now authoritative).
        fkey = _first_chip_key(kind, pl)
        if fkey and fkey not in self._firsts_seen:
            self._firsts_seen.add(fkey)
            pl["is_first"] = True
        ev = Event(
            seq=self.seq,
            tick=self.tick,
            day=self.day,
            kind=kind,
            actor_id=actor_id,
            actor_kind=actor_kind,
            sector_id=sector_id,
            payload=pl,
            summary=summary,
        )
        self.events.append(ev)
        return ev

# ---------------------------------------------------------------------
# Phase C.1 helpers — which event kinds qualify for a FIRST-of-match
# stamp, and how to dedup multi-instance kinds like citadel_complete
# (each level counts as a separate milestone).
# Kept at module scope so Universe.emit can call without paying a bound
# method lookup per event.
# ---------------------------------------------------------------------
_FIRST_CHIP_KINDS: set[EventKind] = {
    EventKind.CORP_CREATE,
    EventKind.ALLIANCE_FORMED,
    EventKind.CITADEL_COMPLETE,
    EventKind.SHIP_DESTROYED,
    EventKind.PLAYER_ELIMINATED,
    EventKind.GENESIS_DEPLOYED,
    EventKind.ATOMIC_DETONATION,
    EventKind.PORT_DESTROYED,
    EventKind.GAME_OVER,
}


def _first_chip_key(kind: EventKind, payload: dict) -> str | None:
    if kind not in _FIRST_CHIP_KINDS:
        return None
    if kind is EventKind.CITADEL_COMPLETE:
        # planets.py emits `{"from": old_level, "to": new_level}`.
        # Treat each *new* level as its own first — L1 -> L2 -> L3 -> L4.
        lvl = payload.get("to") or payload.get("level_target") or payload.get("level")
        return f"citadel_complete:{lvl}" if lvl is not None else "citadel_complete"
    return kind.value
