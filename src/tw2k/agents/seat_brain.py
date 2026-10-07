"""Goal-driven seat brain (seat-bot S3).

docs/plans/2026-09-24-seat-bot-competitive.md. Replaces the hand-patched
Path-B ladder in scripts/commander_p4_brain.py with one pure decision
function that reads ONLY the seat's own fogged observation (the object the
harness mailbox hands over): legal_actions + envelopes, ship/cargo, credits,
known_warps, owned_planets (S1 colonists/origin), sector, scratchpad.

    brain = SeatBrain()
    action = brain.decide(observation)   # dict: {kind, args, thought, goal_*, scratchpad_update}

Goal ladder (first rung that yields a legal action wins):
  1. Landed: assign colonists aboard -> build citadel -> liftoff (never ferry
     colonists onto a claimed neutral; only genesis worlds are work sites).
  2. Genesis aboard: deploy when `deploy_genesis` is legal, else carry it
     away from StarDock / FedSpace guided by `legal_actions.reason`.
  3. At home with a reason (colonists aboard, citadel buildable): land.
  4. Before the first world: the fixed N1/N2 ladder. At StarDock, CargoTran
     before the first genesis (a 20-hold hull that spends its bank on the
     torpedo does not get the holds back). Then genesis, then the colonist
     ferry the citadel still needs.
  5. After the first world (N3): value per turn, not a fixed rung order.
     Trade (profit / turns), a colonist ferry (only when it unlocks a
     planned citadel tier or refills a starving world), genesis #N
     (25k purchase is net-worth neutral; the value is colonist growth
     after L1, not a fighter grant), organics resupply, and a stockpile sale
     (``load_planet_cargo`` to a port that pays above base price).
     ``target_planets`` rises above 2 while another torpedo is affordable.
  6. Colonists or organics already aboard are delivered before a new choice.
  7. Exploration is frontier-directed: plot through known warps to the nearest
     known sector that still has an unvisited neighbour. Not a greedy local
     warp (that ABA-bounces).

Loops are judged by `tw2k.agents.stall.StallDetector` (no progress toward
the declared intent), never by target alternation: StarDock <-> home ferry
legs and same-target replots are fine. When the detector says stalled the
brain spends a few turns exploring, then resumes the ladder.

Memory (home planet, deploy sector, visit counts) is written back through
`scratchpad_update` so a restarted brain resumes where it left off.

Rule numbers used (citadel tier costs) are the public rulebook the system
prompt also states; everything situational comes from the observation.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any

from ..engine.constants import (
    CITADEL_GIFT_FIGHTERS_PER_LEVEL,
    CITADEL_GIFT_SHIELDS_PER_LEVEL,
    CITADEL_TIER_COST,
    COLONIST_PRICE,
    COMMODITY_BASE_PRICE,
    DENSITY_SCANNER_COST,
    GENESIS_SEED_COLONISTS,
    GENESIS_TORPEDO_COST,
    HOLO_SCANNER_COST,
    SCANNER_DENSITY,
    SCANNER_HOLO,
    TERRA_COLONIST_PRICE,
    TERRA_LOAD_TURNS,
    class0_tw2002,
    combat_hull,
    fighter_unit_price,
    info_tw2002,
    scanner_room,
    ship_cost,
    ship_specs,
    slow_hull_hint_on,
)
from ..engine.planets import (
    organics_coeff,
    organics_worker_target,
    planet_growth_status,
)
from .pathb_client import TurnContext, legal_heuristic_policy
from .stall import Intent, StallDetector, known_distance

STARDOCK = 1


def _colonist_acquire_unit() -> int:
    """Credits to acquire one colonist right now (CLASS0_TERRA.md).

    Under tw2002 Terra is free (0 cr) and costs TERRA_LOAD_TURNS; net-worth
    valuation of population still uses COLONIST_PRICE.
    """
    if class0_tw2002():
        return int(TERRA_COLONIST_PRICE)
    return int(COLONIST_PRICE)


def _colonist_ferry_turn_overhead() -> int:
    """Extra turns per Terra load under tw2002 (0 under legacy buy_equip)."""
    return int(TERRA_LOAD_TURNS) if class0_tw2002() else 0

MEMORY_TAG = "SEATBRAIN "
# CORP_RULES.md cr29 "pair" policy (match check only)
PAIR_CEO_ID = "P1"
PAIR_MATE_ID = "P2"
PAIR_TICKER = "PAR"
PAIR_CORP_NAME = "Pair Traders"
PAIR_PASSWORD = "pair1"

STALL_BREAK_TURNS = 3
# fedspace-police-v1: FedSpace sectors; leave this many spare warps when heading out before Extern.
FEDSPACE_IDS = frozenset(range(1, 11))
FED_TOW_EXIT_MARGIN_WARPS = 3
FED_TOW_UNKNOWN_EXIT_HOPS = 3
# S6: self-failure events a seat can see about its own actions.
FAIL_KINDS = ("agent_error", "trade_failed", "warp_blocked")
BAN_DECISIONS = 12          # a failed exact action is not retried for this many decisions
KIND_BAN_AFTER = 2          # same verb failing this many times in a day -> verb shelved for the day
PRESSURE_NW_RATIO = 1.15    # a rival this far ahead on public net worth = we are trailing
PRESSURE_NW_GAP = 10_000
ORPHAN_MAX_HOPS = 8
CLAIM_WORLD_MIN_COLONISTS = 1_000
# Buy when the owner-only runway is under this many day-boundaries.
ORGANICS_FEED_DAYS = 2
# 75 organics at a full port used to be about 19 cr, when the organics base was 25.
# The cheap line and the ceiling scale with the live base so a normal quote
# still counts after the tw2002 price table. Empty shelves are a stock check,
# not a price check.
_ORGANICS_CHEAP_AT_BASE_25 = 19


def _organics_cheap_price() -> int:
    base = int(COMMODITY_BASE_PRICE["organics"])
    return max(1, round(_ORGANICS_CHEAP_AT_BASE_25 * base / 25))


def _organics_price_ceiling() -> int:
    """A buy at or under the organics base. The old gate was 25, that base."""
    return int(COMMODITY_BASE_PRICE["organics"])


ORGANICS_LOAD = 75
# Build the next citadel inside this many days of max_days even if it
# spends the growth base - the match will not compound past the cap.
CITADEL_LAST_DAYS = 2
# Genesis above the second world, only while the purchase still leaves
# L1 cash. Four is the cap: more worlds than that starve the turn budget.
MAX_TARGET_PLANETS = 4
# Buy hull upgrades and defence once a seat is this rich (fogged credits).
RICH_CREDITS = 200_000
# ship-transwarp-v1: buy a drive only with this much left over.
SHIP_TW_SPARE_CASH = 150_000
# Drive owners jump only when walking would cost at least this many MORE turns than the jump, and keep just
# the ore for the planned jump (never sold, topped up at an ore port). No plan, no reserve. Seats without a
# drive are untouched (Ben 2026-10-05).
SHIP_TW_MIN_TURNS_SAVED = 8
DEFENSE_CASH_GATE = 100_000
DEFENSE_FIGHTERS_FLOOR = 200
DEFENSE_SHIELDS_FLOOR = 100
# Legal-list combat hulls, preferred when already past CargoTran.
COMBAT_HULLS = (
    "imperial_starship",
    "havoc_gunstar",
    "battleship",
    "star_master",
    "constellation",
    "missile_frigate",
)
# Shields the seat buys are scored at 10cr. A citadel does not mint them.
SHIELD_VALUE = 10


@dataclass
class SeatMemory:
    home_planet: int | None = None
    home_sector: int | None = None
    deploy_sector: int | None = None
    visits: dict[int, int] = field(default_factory=dict)
    stall_breaks: int = 0
    break_left: int = 0
    # "sector:commodity" -> day a remembered buyer refused us (stale / full); skipped that day.
    bad_sells: dict[str, int] = field(default_factory=dict)
    # S6 failure replanning (all derived from the seat's own events).
    decisions: int = 0
    last_action_sig: str | None = None
    last_event_seq: int = 0
    banned: dict[str, int] = field(default_factory=dict)        # action signature -> banned until decision N
    kind_fails: dict[str, list[int]] = field(default_factory=dict)  # verb -> [day, count]
    banned_kinds: dict[str, int] = field(default_factory=dict)  # verb -> day shelved
    ban_day: int = 0
    replans: int = 0
    # N1: port sectors this seat has actually seen (adjacent / known_sectors / known_ports).
    # StarDock is never recorded - it is not a trade port.
    ports_seen: set[int] = field(default_factory=set)
    # (seller, buyer) of the first priced route. One-hop port neighbours of these two
    # get priced once; the cluster does not grow when a neighbour becomes an endpoint.
    trade_anchors: tuple[int, int] | None = None
    # Previous local warp (from, to). Plotting clears it so a trade autopilot is not an ABA bounce.
    last_warp: tuple[int, int] | None = None
    # Sector whose fighters this seat retreated from -> [day, fighter count]. Avoided for the rest of
    # that day unless the seat can now beat the group, so it does not warp in, retreat, and warp in
    # again all day (ship-combat-core-v1 QC).
    held: dict[int, list[int]] = field(default_factory=dict)
    # Planet the organics currently in the hold were bought for. Trade cargo is not flagged.
    organics_drop: int | None = None
    # Planet a colonist ferry was bought for. None -> the home world (N1/N2).
    colonist_drop: int | None = None
    # (planet_id, commodity) once a stockpile sale has been chosen.
    stock_load: tuple[int, str] | None = None
    # Declined the first genesis because CargoTran was not affordable yet.
    # Stops the seat from autopiloting back to StarDock on genesis money alone.
    hull_wait: bool = False
    # Worlds whose legal list showed no room for a colonist unload.
    no_colonist_room: set[int] = field(default_factory=set)
    # Sectors where this seat has seen Ferrengi (fogged sector / events).
    hot_sectors: set[int] = field(default_factory=set)
    # Last sector this seat robbed or stole in. A second try there is a fake bust.
    last_crime_sector: int | None = None
    # Sectors where this seat already launched a beacon (a second one explodes both).
    beacons_laid: set[int] = field(default_factory=set)
    # Armids and the home beacon are bought once. Laying them must not start a rebuy loop.
    armids_stocked: bool = False
    beacon_stocked: bool = False
    # Last psychic-probe reading this seat saw (percent of the port's best price).
    psychic_pct: float | None = None
    psychic_commodity: str | None = None
    psychic_unit: int | None = None
    # bots-use-planet-trade-v1: actions spent steering the genesis torpedo under a buying port.
    pt_detour: int = 0
    # port-upgrade-build-v1 QC: "sector:commodity" buy ports this seat gave its one starter upgrade.
    port_starters: set[str] = field(default_factory=set)
    # galactic-bank-tax-v1: one deposit per StarDock visit. Stays off the scratchpad while false.
    bank_deposited: bool = False
    # bb18: this visit deposited, and no buy has happened since. A withdraw of those credits waits.
    bank_unspent: bool = False
    # bb12: the planet id already used for this landing. Omitted until a deposit happens.
    treasury_planet: int | None = None
    # bb11: the day this seat already detoured to the bank. Omitted until one happens.
    bank_detour_day: int = -1
    # bb21: the StarDock buy a withdraw already funded. Omitted until one is pending.
    pending_buy: str | None = None
    # bb18: bank verbs used on bank_verbs_day, and StarDock withdraws this visit.
    bank_verbs_day: int = -1
    bank_verbs: int = 0
    bank_withdraws: int = 0
    # bots-use-corps-v1. The password itself is never stored.
    corp_partner: str | None = None
    corp_role: str | None = None
    corp_free_day: int = -1
    corp_free_actions: int = 0
    corp_invites: int = 0
    corp_invite_day: int = -1
    corp_transfer_day: int = -1
    corp_fighter_day: int = -1
    corp_join_day: int = -1
    corp_last_invite: str | None = None

    def dump(self) -> str:
        payload = {
            "home_planet": self.home_planet, "home_sector": self.home_sector,
            "deploy_sector": self.deploy_sector, "stall_breaks": self.stall_breaks,
            "last_event_seq": self.last_event_seq, "last_action_sig": self.last_action_sig,
            # keep the scratchpad small: only the 40 most visited sectors
            "visits": dict(sorted(self.visits.items(), key=lambda kv: -kv[1])[:40]),
            "ports_seen": sorted(self.ports_seen)[:80],
            "trade_anchors": list(self.trade_anchors) if self.trade_anchors else None,
            "organics_drop": self.organics_drop,
            "colonist_drop": self.colonist_drop,
            "stock_load": list(self.stock_load) if self.stock_load else None,
            "hull_wait": self.hull_wait,
            "no_colonist_room": sorted(self.no_colonist_room)[:20],
            "hot_sectors": sorted(self.hot_sectors)[:40],
        }
        # Defaults stay off the scratchpad so an all-legacy run matches the previous digest.
        if self.last_crime_sector is not None:
            payload["last_crime_sector"] = self.last_crime_sector
        if self.beacons_laid:
            payload["beacons_laid"] = sorted(self.beacons_laid)[:40]
        if self.armids_stocked:
            payload["armids_stocked"] = True
        if self.beacon_stocked:
            payload["beacon_stocked"] = True
        if self.psychic_pct is not None:
            payload["psychic_pct"] = self.psychic_pct
        if self.psychic_commodity is not None:
            payload["psychic_commodity"] = self.psychic_commodity
        if self.psychic_unit is not None:
            payload["psychic_unit"] = self.psychic_unit
        if self.pt_detour:
            payload["pt_detour"] = self.pt_detour
        if self.port_starters:
            payload["port_starters"] = sorted(self.port_starters)[:20]
        if self.bank_deposited:
            payload["bank_deposited"] = True
        if self.bank_unspent:
            payload["bank_unspent"] = True
        if self.treasury_planet is not None:
            payload["treasury_planet"] = int(self.treasury_planet)
        if self.bank_detour_day >= 0:
            payload["bank_detour_day"] = int(self.bank_detour_day)
        if self.pending_buy:
            payload["pending_buy"] = self.pending_buy
        if self.bank_verbs_day >= 0:
            payload["bank_verbs_day"] = int(self.bank_verbs_day)
            payload["bank_verbs"] = int(self.bank_verbs)
            payload["bank_withdraws"] = int(self.bank_withdraws)
        if self.corp_partner:
            payload["corp_partner"] = self.corp_partner
        if self.corp_role:
            payload["corp_role"] = self.corp_role
        if self.corp_invites:
            payload["corp_invites"] = int(self.corp_invites)
        if self.corp_free_actions:
            payload["corp_free_actions"] = int(self.corp_free_actions)
            payload["corp_free_day"] = int(self.corp_free_day)
        if self.corp_invite_day >= 0:
            payload["corp_invite_day"] = int(self.corp_invite_day)
        if self.corp_transfer_day >= 0:
            payload["corp_transfer_day"] = int(self.corp_transfer_day)
        if self.corp_fighter_day >= 0:
            payload["corp_fighter_day"] = int(self.corp_fighter_day)
        if self.corp_join_day >= 0:
            payload["corp_join_day"] = int(self.corp_join_day)
        if self.corp_last_invite:
            payload["corp_last_invite"] = self.corp_last_invite
        return MEMORY_TAG + json.dumps(payload, separators=(",", ":"))

    @classmethod
    def load(cls, scratchpad: str | None) -> SeatMemory:
        mem = cls()
        if not scratchpad or MEMORY_TAG not in scratchpad:
            return mem
        try:
            data = json.loads(scratchpad.split(MEMORY_TAG, 1)[1].strip().splitlines()[0])
        except (ValueError, IndexError):
            return mem
        mem.home_planet = data.get("home_planet")
        mem.home_sector = data.get("home_sector")
        mem.deploy_sector = data.get("deploy_sector")
        mem.stall_breaks = int(data.get("stall_breaks") or 0)
        mem.visits = {int(k): int(v) for k, v in (data.get("visits") or {}).items()}
        mem.last_event_seq = int(data.get("last_event_seq") or 0)
        mem.last_action_sig = data.get("last_action_sig")
        mem.ports_seen = {int(s) for s in (data.get("ports_seen") or []) if int(s) != STARDOCK}
        anchors = data.get("trade_anchors")
        if isinstance(anchors, (list, tuple)) and len(anchors) == 2:
            mem.trade_anchors = (int(anchors[0]), int(anchors[1]))
        drop = data.get("organics_drop")
        mem.organics_drop = int(drop) if isinstance(drop, int) else None
        cdrop = data.get("colonist_drop")
        mem.colonist_drop = int(cdrop) if isinstance(cdrop, int) else None
        stock = data.get("stock_load")
        if isinstance(stock, (list, tuple)) and len(stock) == 2 and isinstance(stock[1], str):
            mem.stock_load = (int(stock[0]), str(stock[1]))
        mem.hull_wait = bool(data.get("hull_wait"))
        mem.no_colonist_room = {int(pid) for pid in (data.get("no_colonist_room") or [])}
        mem.hot_sectors = {int(sid) for sid in (data.get("hot_sectors") or [])}
        crime = data.get("last_crime_sector")
        mem.last_crime_sector = int(crime) if isinstance(crime, int) else None
        mem.beacons_laid = {int(sid) for sid in (data.get("beacons_laid") or [])}
        pct = data.get("psychic_pct")
        mem.armids_stocked = bool(data.get("armids_stocked"))
        mem.beacon_stocked = bool(data.get("beacon_stocked"))
        mem.psychic_pct = float(pct) if isinstance(pct, (int, float)) else None
        mem.psychic_commodity = data.get("psychic_commodity") if isinstance(data.get("psychic_commodity"), str) else None
        unit = data.get("psychic_unit")
        mem.psychic_unit = int(unit) if isinstance(unit, int) else None
        mem.pt_detour = int(data.get("pt_detour") or 0)
        mem.port_starters = {str(k) for k in (data.get("port_starters") or []) if isinstance(k, str)}
        mem.bank_deposited = bool(data.get("bank_deposited"))
        mem.bank_unspent = bool(data.get("bank_unspent"))
        landed_id = data.get("treasury_planet")
        mem.treasury_planet = int(landed_id) if isinstance(landed_id, int) else None
        detour_day = data.get("bank_detour_day")
        mem.bank_detour_day = int(detour_day) if isinstance(detour_day, int) else -1
        pending = data.get("pending_buy")
        mem.pending_buy = str(pending) if isinstance(pending, str) else None
        verbs_day = data.get("bank_verbs_day")
        mem.bank_verbs_day = int(verbs_day) if isinstance(verbs_day, int) else -1
        mem.bank_verbs = int(data.get("bank_verbs") or 0)
        mem.bank_withdraws = int(data.get("bank_withdraws") or 0)
        partner = data.get("corp_partner")
        mem.corp_partner = str(partner) if isinstance(partner, str) else None
        role = data.get("corp_role")
        mem.corp_role = str(role) if isinstance(role, str) else None
        mem.corp_invites = int(data.get("corp_invites") or 0)
        mem.corp_free_actions = int(data.get("corp_free_actions") or 0)
        mem.corp_free_day = int(data.get("corp_free_day") if data.get("corp_free_day") is not None else -1)
        mem.corp_invite_day = int(data.get("corp_invite_day") if data.get("corp_invite_day") is not None else -1)
        mem.corp_transfer_day = int(data.get("corp_transfer_day") if data.get("corp_transfer_day") is not None else -1)
        mem.corp_fighter_day = int(data.get("corp_fighter_day") if data.get("corp_fighter_day") is not None else -1)
        mem.corp_join_day = int(data.get("corp_join_day") if data.get("corp_join_day") is not None else -1)
        last = data.get("corp_last_invite")
        mem.corp_last_invite = str(last) if isinstance(last, str) else None
        return mem


class View:
    """Read-only helpers over one observation dict."""

    def __init__(self, obs: dict[str, Any]) -> None:
        self.obs = obs
        self.legal = {la.get("kind"): la for la in (obs.get("legal_actions") or [])}
        sector = obs.get("sector") or {}
        self.here = sector.get("id")
        self.sector = sector
        ship = obs.get("ship") or {}
        self.ship = ship
        self.cargo = ship.get("cargo") or {}
        self.credits = int(obs.get("credits") or 0)
        self.colonists_aboard = int(self.cargo.get("colonists") or 0)
        self.genesis_aboard = int(ship.get("genesis") or 0)
        self.cargo_free = int(ship.get("cargo_free") or 0)
        self.ship_class = ship.get("class")
        self.scanner = ship.get("scanner")
        self.landed = obs.get("planet_landed")
        self.owned = [p for p in (obs.get("owned_planets") or []) if isinstance(p, dict)]
        self.known_warps = {int(k): tuple(int(x) for x in (v or ())) for k, v in (obs.get("known_warps") or {}).items()}
        ks = obs.get("known_sectors")
        self.known_ids = ({int(s["id"]) for s in ks if isinstance(s, dict) and "id" in s}
                          if isinstance(ks, list) else set(self.known_warps))
        self.self_id = obs.get("self_id")
        self.day = int(obs.get("day") or 0)
        self.net_worth = int(obs.get("net_worth") or self.credits)
        self.rivals = [r for r in (obs.get("rivals") or []) if isinstance(r, dict)]
        self.events = [e for e in (obs.get("recent_events") or []) if isinstance(e, dict)]
        self.failures = [f for f in (obs.get("recent_failures") or []) if isinstance(f, dict)]
        # Only planets the ENGINE lists as true former-player orphans; never inferred.
        self.orphans = {int(p["id"]): p for p in (obs.get("orphaned_planets") or [])
                        if isinstance(p, dict) and p.get("id") is not None}

    def ok(self, kind: str) -> bool:
        return bool((self.legal.get(kind) or {}).get("legal"))

    def reason(self, kind: str) -> str:
        return str((self.legal.get(kind) or {}).get("reason") or "")

    def params(self, kind: str) -> dict[str, Any]:
        return (self.legal.get(kind) or {}).get("params") or {}

    def choices(self, kind: str, name: str) -> list[Any]:
        p = self.params(kind).get(name)
        return list(p.get("choices") or []) if isinstance(p, dict) else []

    def max_by(self, kind: str, name: str, key: str) -> int:
        p = self.params(kind).get(name)
        if not isinstance(p, dict):
            return 0
        return int((p.get("max_by") or {}).get(key) or 0)

    @property
    def stardock_known(self) -> bool:
        return self.here == STARDOCK or STARDOCK in self.known_ids

    def planet(self, pid: int | None) -> dict[str, Any] | None:
        return next((p for p in self.owned if p.get("id") == pid), None)

    def genesis_planets(self) -> list[dict[str, Any]]:
        return [p for p in self.owned if p.get("origin") == "genesis"]

    def worlds(self) -> list[dict[str, Any]]:
        """Planets worth developing: own genesis worlds, plus claimed worlds that already
        carry a citadel or a real colony (e.g. an inherited orphan). Empty neutral claims
        stay excluded - that was the Kimi3 planet-20 trap."""
        return [p for p in self.owned if p.get("origin") == "genesis"
                or int(p.get("citadel_level") or 0) >= 1
                or _colonists_total(p) >= CLAIM_WORLD_MIN_COLONISTS]


def _colonists_total(p: dict[str, Any]) -> int:
    t = p.get("colonists_total")
    if isinstance(t, int):
        return t
    c = p.get("colonists")
    return sum(int(v or 0) for v in c.values()) if isinstance(c, dict) else int(c or 0)


def next_tier(planet: dict[str, Any], *, lookahead: bool = False) -> tuple[int, int] | None:
    """(credits, colonists) for the next citadel build.

    lookahead=False: the build that is possible NOW (None while one is under
    construction). lookahead=True: the next build to prepare for, i.e. the tier
    after the one under construction.
    """
    lvl = int(planet.get("citadel_level") or 0)
    tgt = int(planet.get("citadel_target") or 0)
    if tgt > lvl and not lookahead:
        return None
    base = max(lvl, tgt)
    if base >= len(CITADEL_TIER_COST):
        return None
    cred, col, _days = CITADEL_TIER_COST[base]
    return cred, col


def _defense_value(level: int, day: int = 1) -> int:
    """Fighters and shields a finished citadel adds to net worth.

    The engine gifts ``CITADEL_GIFT_*_PER_LEVEL`` at level 2 and up, and both
    constants are 0. Fighters the seat buys later cost the day's public wave.
    Shields the seat buys later cost ``SHIELD_VALUE``. Those purchases are
    not part of this number.
    """
    if level < 2:
        return 0
    fighters = CITADEL_GIFT_FIGHTERS_PER_LEVEL * level
    shields = CITADEL_GIFT_SHIELDS_PER_LEVEL * level
    return fighters * fighter_unit_price(day) + shields * SHIELD_VALUE


def _tier_bonus(current_level: int) -> int:
    """Credit and colonist cost of the next citadel tier, as net worth records it.

    Level 1 is a build visit, not a haul. Fighters and shields are separate
    purchases and are not included.
    """
    nxt = current_level + 1
    if nxt < 2 or nxt - 1 >= len(CITADEL_TIER_COST):
        return 0
    cred, col, _days = CITADEL_TIER_COST[nxt - 1]
    return int(cred) + int(col) * COLONIST_PRICE


def _project_pop(pop: int, days: int, growing: bool) -> int:
    """Colonists after ``days`` growth ticks. Same ``int(pop * 0.05)`` the day tick uses."""
    pop = max(0, int(pop))
    if not growing or pop <= 0 or days <= 0:
        return pop
    for _ in range(int(days)):
        pop += int(pop * 0.05)
    return pop


def _planned_tier(planet: dict[str, Any]) -> tuple[int, int, int, int] | None:
    """(credits, colonists, defense bonus, level) of the tier a ferry would unlock.

    L1 adds no defense, so it is a build visit, not a ferry. While a tier is
    already under construction the planned one is the tier after it, and only
    when that tier is L2. Stocking an L3+ colony during a build is a turn sink
    and, when the credit reserve leaves no colonist money, a StarDock ping-pong.
    A bonus of 0 means the citadel grants nothing, so there is no ferry.
    """
    lvl = int(planet.get("citadel_level") or 0)
    tgt = int(planet.get("citadel_target") or 0)
    building = tgt > lvl
    tier = next_tier(planet, lookahead=building)
    if tier is None:
        return None
    cred, col = tier
    level = max(lvl, tgt) + 1
    if building and level > 2:
        return None
    bonus = _tier_bonus(level - 1)
    if bonus <= 0:
        return None
    return cred, col, bonus, level


def _world_starving(planet: dict[str, Any]) -> bool:
    """No population, or the growth gate is shut and nothing is compounding."""
    if _colonists_total(planet) <= 0:
        return True
    g = growth_view(planet)
    if not g:
        return False
    return int(g.get("organics_days_left") or 0) <= 0 and not g.get("growth_active")


def _refill_value(qty: int, days_left: int) -> int:
    """Net-worth of restarting growth with one small colonist load."""
    end = _project_pop(qty, min(max(0, days_left), 8), True)
    return max(0, end - qty) * COLONIST_PRICE + max(1, qty) * COLONIST_PRICE // 10


def next_tier_days(planet: dict[str, Any]) -> int:
    """Build duration of the tier `next_tier` would start now (0 if none)."""
    lvl = int(planet.get("citadel_level") or 0)
    tgt = int(planet.get("citadel_target") or 0)
    if tgt > lvl:
        return 0
    base = max(lvl, tgt)
    if base >= len(CITADEL_TIER_COST):
        return 0
    return int(CITADEL_TIER_COST[base][2])


def _pool(planet: dict[str, Any], name: str) -> int:
    cols = planet.get("colonists")
    if not isinstance(cols, dict):
        return 0
    return int(cols.get(name) or 0)


def _class_coeff(planet: dict[str, Any]) -> int | None:
    cls = planet.get("class")
    if not cls:
        return None
    try:
        return organics_coeff(cls)
    except ValueError:
        return None


def growth_view(planet: dict[str, Any]) -> dict[str, Any] | None:
    """Growth snapshot from the observation, or recomputed when stockpile+class are present.

    Synthetic storyboards omit stockpile on purpose: those worlds are not hungry.
    """
    keys = ("production", "organics_days_left", "organics_consumption_per_day", "growth_active")
    if all(k in planet for k in keys):
        return planet
    if "class" not in planet or "stockpile" not in planet:
        return None
    stock = (planet.get("stockpile") or {}).get("organics", 0)
    cols = planet.get("colonists") if isinstance(planet.get("colonists"), dict) else {}
    try:
        return planet_growth_status(planet["class"], cols, int(stock or 0))
    except (ValueError, TypeError):
        return None


def _unload_pool(planet: dict[str, Any], qty: int) -> str:
    """Which labor pool a ship-load of colonists should join.

    Sized from the class organics coefficient so production covers the burn.
    No class (older fixtures): the M-class ``total // 5`` rule.
    """
    workers = _pool(planet, "organics")
    total = _colonists_total(planet) + max(0, int(qty))
    coeff = _class_coeff(planet)
    if coeff is None:
        return "organics" if workers < total // 5 else "fuel_ore"
    # Coeff-1 cannot cover burn. Once the stockpile is empty, further organics
    # unloads just steal fuel from citadel payments (seed 250925 planet 32).
    # Coeff-1 cannot surplus-feed. Park only a tiny organics crew so citadel
    # fuel keeps getting the ferry (seed 250925 class U home).
    if coeff == 1:
        return "organics" if workers < max(1, total // 40) else "fuel_ore"
    if coeff > 0 and workers < organics_worker_target(total, coeff):
        return "organics"
    return "fuel_ore"


def _signature(action: dict[str, Any], v: View | None = None) -> str:
    """Identity of an action for failure bookkeeping: verb + the argument that decides it."""
    kind = str(action.get("kind"))
    a = action.get("args") or {}
    if kind in ("warp", "plot_course", "probe", "attack", "photon_missile", "hail"):
        key = a.get("target")
    elif kind in ("land_planet", "build_citadel", "assign_colonists", "claim_planet",
                  "load_planet_cargo", "dump_planet_cargo"):
        key = a.get("planet_id")
    elif kind == "trade":
        return f"trade:{a.get('commodity')}:{a.get('side')}"
    elif kind == "buy_equip":
        key = a.get("item")
    elif kind == "buy_ship":
        key = a.get("ship_class")
    elif kind == "deploy_genesis" and v is not None:
        key = v.here
    else:
        key = ""
    return f"{kind}:{key}"


class SeatBrain:
    def __init__(self, *, target_planets: int = 2, cash_buffer: int = 2_000, working_capital: int = 8_000,
                 stall_window: int = 8, feed_organics: bool = True,
                 citadel_floor_ratio: float | None = None, citadel_fuel_shield: bool = False,
                 citadel_multiday_floor: bool = True, value_allocator: bool = True) -> None:
        self.target_planets = target_planets
        # N3. Off is the N1/N2 ladder (`n1_brain` / `n2_brain`).
        self.value_allocator = value_allocator
        self.cash_buffer = cash_buffer
        # Never spend below this on colonists / extra genesis: it keeps a trade
        # loop funded so the seat can always earn its way back (Kimi3 lesson).
        self.working_capital = working_capital
        # N2. feed_organics off, floor None, fuel shield off, and multiday floor
        # off is the N1 policy (`n1_brain` in the acceptance script).
        self.feed_organics = feed_organics
        # Blanket floor (remaining >= ratio * tier cost on every tier). A/B'd
        # at 1.0: it delayed the one-day L2 fighter bonus and missed 4/5
        # day-10 seeds, so the default is off.
        self.citadel_floor_ratio = citadel_floor_ratio
        # Citadel drain takes fuel_ore first. Requiring that pool to cover the
        # cost also blocked L2 on the same A/B, so the default is off.
        self.citadel_fuel_shield = citadel_fuel_shield
        # L3+ takes 2+ days. Credits and colonists leave net worth when the
        # build starts; the fighter bonus arrives only when it finishes.
        # Require remaining colonists >= that tier's cost so a fast-growing
        # colony is not emptied for a citadel that is still under construction.
        # Waived in the last ~2 days. This is the floor the day-10 A/B kept.
        self.citadel_multiday_floor = citadel_multiday_floor
        self.detector = StallDetector(window=stall_window)
        self.mem: SeatMemory | None = None
        self._intent = Intent()
        self.last_report = None
        self.pressure: dict[str, Any] | None = None

    # ------------------------------------------------------------------ entry
    def decide(self, obs: Any) -> dict[str, Any]:
        o = obs if isinstance(obs, dict) else obs.model_dump(mode="json")
        o = tw_reserve_view(o, self._planned_tw_hops(o))
        v = View(o)
        if self.mem is None:
            self.mem = SeatMemory.load(o.get("scratchpad"))
        mem = self.mem
        if v.here is not None:
            mem.visits[int(v.here)] = mem.visits.get(int(v.here), 0) + 1
        mem.decisions += 1
        self._ingest_failures(v)
        self._note_colonist_room(v)
        self.pressure = self._rival_pressure(v)
        self._remember_ports(v)
        self._refresh_home(v)
        if mem.organics_drop is not None and int(v.cargo.get("organics") or 0) <= 0:
            mem.organics_drop = None
        if mem.colonist_drop is not None and v.colonists_aboard <= 0:
            mem.colonist_drop = None
        self._note_ferrengi(v)
        self._note_psychic(v)
        if self.feed_organics or self.value_allocator:
            self._sync_target_planets(v)

        report = self.detector.observe(o, self._intent)
        self.last_report = report
        if report.stalled and mem.break_left == 0:
            mem.break_left = STALL_BREAK_TURNS
            mem.stall_breaks += 1
            self.detector.reset()

        answer = self._answer_challenge(v)
        if answer is not None:  # ship-combat-core-v1: fighters hold the ship; answer before the ladder
            self._intent = Intent()
            mem.last_action_sig = _signature(answer, v)
            mem.last_warp = None
            return self._finish(v, answer)
        answer = self._extern_tow(v) or self._board_spare(v) or self._top_up_tw_ore(v)
        if answer is not None:  # ship-fleet-transporter-v1 / TransWarp ore reserve: own-ship only branches
            self._intent = Intent()
            mem.last_action_sig = _signature(answer, v)
            mem.last_warp = None
            return self._finish(v, answer)
        if self._reserve_on():
            answer = self._bank_recovery(v)
            if answer is not None:  # a pod withdraws for the replacement hull before it buys a Scout
                self._intent = Intent()
                mem.last_action_sig = _signature(answer, v)
                mem.last_warp = None
                return self._finish(v, answer)
        answer = self._leave_pod(v)
        if answer is not None:  # death-escape-pods-v1: a pod flies to StarDock and trades itself in
            self._intent = Intent()
            mem.last_action_sig = _signature(answer, v)
            mem.last_warp = None
            return self._finish(v, answer)
        answer = self._avoid_fed_tow(v) or self._police_hq(v)
        if answer is not None:  # fedspace-police-v1: leave FedSpace before Extern; free Police HQ verbs
            self._intent = Intent()
            mem.last_action_sig = _signature(answer, v)
            mem.last_warp = None
            return self._finish(v, answer)
        answer = self._cloak_for_navhaz(v) or self._hunt(v)
        if answer is not None:  # fullgame-fixes-v2: N3 attacks a ship it clearly beats (HUNT_MODE)
            self._intent = Intent()
            mem.last_action_sig = _signature(answer, v)
            mem.last_warp = None
            return self._finish(v, answer)
        answer = self._corp_pair(v) or self._bank(v) or self._treasury(v) or self._port_upgrade(v) or self._port_build(v)
        if answer is not None:  # port-upgrade-build-v1: widen a buying port, or (policy on) order one
            self._intent = Intent()
            mem.last_action_sig = _signature(answer, v)
            mem.last_warp = None
            return self._finish(v, answer)
        answer = self._planet_trade(v)
        if answer is not None:  # planetary-trading-v1: sell a planet's surplus straight to this port
            self._intent = Intent()
            mem.last_action_sig = _signature(answer, v)
            mem.last_warp = None
            return self._finish(v, answer)

        action, intent = (None, Intent())
        if mem.break_left > 0:
            mem.break_left -= 1
            action, intent = self._explore(v, f"stall break ({report.summary()})")
            if action is not None and self._banned_why(action, v):
                action, intent = None, Intent()
        if action is None:
            action, intent = self._ladder(v)
        action, intent = self._bank_detour(v, action, intent)
        action, intent = self._avoid_held(v, action, intent)
        action = self._transwarp_instead(v, action, intent)
        self._intent = intent
        mem.last_action_sig = _signature(action, v)
        if action.get("kind") == "warp" and v.here is not None and action.get("args", {}).get("target") is not None:
            mem.last_warp = (int(v.here), int(action["args"]["target"]))
        elif action.get("kind") in ("plot_course", "ship_transwarp"):
            mem.last_warp = None
        return self._finish(v, action)

    def _answer_challenge(self, v: View) -> dict[str, Any] | None:
        """Hostile defensive or toll fighters hold the ship: pay, else retreat, else win, else surrender.

        "Win" counts every fighter aboard at the hull's odds (one attack per legal wave), not one wave.
        A seat that is only short of turns waits for the next day instead of surrendering the ship.
        """
        ch = v.obs.get("fighter_challenge")
        if not ch:
            return None
        count = int(ch.get("count") or 0)
        sector = int(ch["sector_id"]) if ch.get("sector_id") is not None else None
        can_win = self._can_beat(v, count)
        qty = int((v.params("attack").get("qty") or {}).get("max") or 0)
        if v.ok("pay_toll"):
            return self._act("pay_toll", {}, f"pay the {ch.get('toll')} cr toll in {v.here}")
        again = sector is not None and (self.mem.held.get(sector) or [None])[0] == v.day
        if again and v.ok("attack") and qty > 0 and can_win:  # second time here today: clear it
            return self._act("attack", {"target": "fighters", "qty": qty}, f"attack {ch.get('count')} fighters")
        if v.ok("retreat"):
            if sector is not None:
                self.mem.held[sector] = [v.day, count]
            return self._act("retreat", {}, f"retreat from {ch.get('count')} {ch.get('mode')} fighters")
        if v.ok("attack") and qty > 0 and can_win:
            return self._act("attack", {"target": "fighters", "qty": qty}, f"attack {ch.get('count')} fighters")
        if v.reason("retreat").startswith("out of turns") or (can_win and v.reason("attack").startswith("out of turns")):
            if v.ok("wait"):
                return self._act("wait", {}, "held by fighters and short of turns - wait for tomorrow")
            return self._act("query_limpets", {}, "held by fighters and out of turns - free no-op")
        if v.ok("surrender"):
            return self._act("surrender", {}, "no way past the fighters - surrender")
        return self._act("query_limpets", {}, "challenged and out of turns - free no-op")

    def _can_beat(self, v: View, count: int) -> bool:
        """Every fighter aboard at the hull's odds clears `count` sector fighters (over legal waves)."""
        aboard = int(v.ship.get("fighters") or 0)
        return aboard > 0 and aboard * combat_hull(str(v.ship_class or ""))[0] >= count

    def _held_today(self, v: View) -> set[int]:
        """Sectors retreated from today whose fighters this seat still cannot beat."""
        if self.mem is None:  # helpers called before the first decide()
            return set()
        return {sector for sector, (day, count) in self.mem.held.items()
                if day == v.day and not self._can_beat(v, count)}

    def _avoid_held(self, v: View, action: dict[str, Any], intent: Intent) -> tuple[dict[str, Any], Intent]:
        """Do not walk back into fighters this seat retreated from today (no warp / retreat ping-pong)."""
        held = self._held_today(v)
        kind = action.get("kind")
        if not held or kind not in ("warp", "plot_course"):
            return action, intent
        try:
            target = int((action.get("args") or {}).get("target"))
        except (TypeError, ValueError):
            return action, intent
        if kind == "warp" and target not in held:
            return action, intent
        if kind == "plot_course" and target not in held:
            hop = self._known_hop_toward(v, target)  # the known graph skips held sectors today
            if hop is not None and not self._banned_why({"kind": "warp", "args": {"target": hop}}, v):
                return self._act("warp", {"target": hop}, f"hop {hop} toward {target} around held fighters"), intent
        alt, alt_intent = self._explore(v, "around fighters held today")
        if alt is not None:
            return alt, alt_intent
        return action, intent

    def _leave_pod(self, v: View) -> dict[str, Any] | None:
        """In an escape pod: trade it at StarDock (it buys a Scout outright), else fly there."""
        if v.ship_class != "escape_pod" or v.landed is not None:
            return None
        if v.here == STARDOCK:
            if not v.ok("buy_ship"):
                return None
            choices = v.choices("buy_ship", "ship_class")
            net = (v.params("buy_ship").get("ship_class") or {}).get("net_cost_by", {})
            for key, keep in (("cargotran", self.cash_buffer), ("scout_marauder", 0)):
                cost = int(net.get(key) if net.get(key) is not None else 10**12)
                if key in choices and v.credits - cost >= keep:
                    return self._act("buy_ship", {"ship_class": key}, f"trade the escape pod for a {key} ({cost} cr net)")
            return None
        plot = self._plot(v, STARDOCK, "escape pod - autopilot to StarDock to trade it in")
        if plot is None or self._banned_why(plot, v):
            return None
        return self._avoid_held(v, plot, Intent())[0]  # not back through fighters it fled today

    # ------------------------------------------------------------------ S6: failures / rivals
    def _ingest_failures(self, v: View) -> None:
        """Turn the seat's own failure events into bans so a rejected action is not retried blindly.

        Sources (all in the seat's observation): new `agent_error` / `trade_failed` /
        `warp_blocked` events for this seat since the last decision (attributed to the
        action we sent last), their `facts` (blocked warp target, failed commodity), and
        the engine's aggregated `recent_failures` (count >= 2).
        """
        mem = self.mem
        if v.day != mem.ban_day:  # a new day brings new turns/credits: give every action a fresh try
            mem.banned.clear()
            mem.ban_day = v.day
        seqs = [int(e.get("seq") or 0) for e in v.events]
        new = [e for e in v.events if int(e.get("seq") or 0) > mem.last_event_seq
               and e.get("kind") in FAIL_KINDS and (v.self_id is None or e.get("actor_id") == v.self_id)]
        if seqs:
            mem.last_event_seq = max(mem.last_event_seq, max(seqs))
        for e in new:
            facts = e.get("facts") or {}
            sigs: set[str] = set()
            if e.get("kind") == "warp_blocked" and facts.get("target") is not None:
                sigs |= {f"warp:{facts['target']}", f"plot_course:{facts['target']}"}
            elif e.get("kind") == "trade_failed" and facts.get("commodity"):
                sigs.add(f"trade:{facts['commodity']}:{facts.get('side')}")
            if mem.last_action_sig:
                sigs.add(mem.last_action_sig)
            for sig in sigs:
                mem.banned[sig] = mem.decisions + BAN_DECISIONS
            verb = (mem.last_action_sig or e.get("kind") or "").split(":")[0]
            day, count = mem.kind_fails.get(verb, [v.day, 0])
            count = count + 1 if day == v.day else 1
            mem.kind_fails[verb] = [v.day, count]
            if count >= KIND_BAN_AFTER and verb not in ("wait", "liftoff"):
                mem.banned_kinds[verb] = v.day
            mem.replans += 1
        for f in v.failures:
            if int(f.get("count") or 0) < 2:
                continue
            label = str(f.get("target_label") or "")
            if f.get("kind") == "warp_blocked":
                tgt = "".join(ch for ch in label if ch.isdigit())
                if tgt:
                    mem.banned.setdefault(f"warp:{tgt}", mem.decisions + BAN_DECISIONS)
                    mem.banned.setdefault(f"plot_course:{tgt}", mem.decisions + BAN_DECISIONS)
            elif f.get("kind") == "agent_error" and label.endswith(" rejected"):
                verb = label[: -len(" rejected")]
                if verb and verb not in ("unknown", "wait", "liftoff"):
                    mem.banned_kinds.setdefault(verb, v.day)

    def _banned_why(self, action: dict[str, Any], v: View) -> str | None:
        mem = self.mem
        kind = action.get("kind")
        if kind in ("wait", "query_limpets"):
            return None
        if kind in ("warp", "plot_course"):
            try:
                if int((action.get("args") or {}).get("target")) in self._held_today(v):
                    return "fighters held that sector today"
            except (TypeError, ValueError):
                pass
        if mem.banned_kinds.get(kind) == v.day:
            return f"{kind} failed repeatedly today"
        sig = _signature(action, v)
        if mem.banned.get(sig, 0) > mem.decisions:
            return f"{sig} just failed"
        return None

    def _rival_pressure(self, v: View) -> dict[str, Any] | None:
        """Public race signals only: rivals' net worth (public in the observation) and
        empire events we actually witnessed (genesis / citadel / planet claims)."""
        ahead = [r for r in v.rivals if r.get("alive", True)
                 and int(r.get("net_worth") or 0) >= max(v.net_worth * PRESSURE_NW_RATIO, v.net_worth + PRESSURE_NW_GAP)]
        empire_kinds = ("genesis_deployed", "build_citadel", "citadel_complete", "planet_claimed")
        seen = [e for e in v.events if e.get("kind") in empire_kinds
                and e.get("actor_id") not in (None, v.self_id)]
        if not ahead and not (seen and not v.worlds()):
            return None
        leader = max(ahead, key=lambda r: int(r.get("net_worth") or 0)) if ahead else None
        return {
            "leader": leader.get("id") if leader else None,
            "leader_nw": int(leader.get("net_worth") or 0) if leader else None,
            "empire_signals": [e.get("kind") for e in seen][-3:],
        }

    # ------------------------------------------------------------------ ladder
    def _ladder(self, v: View) -> tuple[dict[str, Any], Intent]:
        skipped: list[str] = []
        if self.value_allocator and v.worlds():
            tail = (self._allocate,)
        else:
            tail = (self._at_stardock, self._travel, self._feed_organics, self._go_stardock, self._earn)
        for rung in (self._landed, self._genesis_aboard, self._land_home, self._land_orphan, *tail):
            out = rung(v)
            if out is None or out[0] is None:
                continue
            why = self._banned_why(out[0], v)
            if why:
                skipped.append(why)
                continue
            if skipped:
                out[0]["thought"] += f" [replanned: {'; '.join(skipped)}]"
            return out
        return self._idle(v, skipped)

    def _landed(self, v: View):
        if v.landed is None:
            return None
        # Claim only a planet the engine itself lists as a true orphan, while landed on it.
        # Candidates in priority order; banned ones fall through so liftoff stays the fallback.
        candidates: list[dict[str, Any]] = []
        if int(v.landed) in v.orphans and v.ok("claim_planet"):
            choices = [int(c) for c in v.choices("claim_planet", "planet_id")]
            if not choices or int(v.landed) in choices:
                o = v.orphans[int(v.landed)]
                candidates.append(self._act("claim_planet", {"planet_id": int(v.landed)},
                                            f"claim orphan {o.get('name', v.landed)} (L{o.get('citadel_level', 0)}, "
                                            f"{o.get('fighters', 0)} fighters)"))
        planet = v.planet(v.landed)
        work_site = planet is not None and planet in v.worlds()
        if work_site:
            pid = int(planet["id"])
            if (self._hauling_organics(v) and int(self.mem.organics_drop) == pid and v.ok("dump_planet_cargo")
                    and "organics" in v.choices("dump_planet_cargo", "commodity")):
                qty = int(v.cargo.get("organics") or 0)
                qty = min(qty, v.max_by("dump_planet_cargo", "qty", "organics") or qty)
                if qty > 0:
                    g = growth_view(planet) or {}
                    candidates.append(self._act(
                        "dump_planet_cargo", {"planet_id": pid, "commodity": "organics", "qty": int(qty)},
                        f"stock {qty} organics on planet {pid} ({g.get('organics_days_left', '?')}d left)"))
            # Build before reshuffling. The seed fuel pool is exactly an L1
            # payment; moving it onto organics first blocks the citadel forever.
            if (v.ok("build_citadel") and pid in v.choices("build_citadel", "planet_id")
                    and self._citadel_ready(planet, v) and not self._mate_waits_on_citadel(v)):
                nxt = v.params("build_citadel").get("next") or {}
                candidates.append(self._act("build_citadel", {"planet_id": pid},
                                            f"build citadel L{nxt.get('level', '?')} on planet {pid}"))
            if v.colonists_aboard > 0 and v.ok("assign_colonists"):
                # A 0 max is a full class, not "unknown". Falling back to the
                # whole hold retries an unload the engine will refuse.
                qty = v.max_by("assign_colonists", "qty", "ship")
                if qty > 0:
                    pool = self._ship_pool(planet, qty)
                    candidates.append(self._act("assign_colonists",
                                                {"planet_id": pid, "from": "ship", "to": pool, "qty": int(qty)},
                                                f"unload {qty} colonists to {pool} on planet {pid}"))
            rebalance = self._rebalance_organics(v, planet) if self.feed_organics else None
            if rebalance is not None:
                candidates.append(rebalance)
            shield = self._move_fuel_shield(v, planet)
            if shield is not None:
                candidates.append(shield)
            loaded = self._stockpile_load_action(v, planet) if self.value_allocator else None
            if loaded is not None:
                candidates.append(loaded)
            dump = self._unsellable_goods(v)
            if dump and v.ok("dump_planet_cargo") and dump[0] in v.choices("dump_planet_cargo", "commodity"):
                c, qty = dump
                qty = min(qty, v.max_by("dump_planet_cargo", "qty", c) or qty)
                candidates.append(self._act("dump_planet_cargo", {"planet_id": pid, "commodity": c, "qty": int(qty)},
                                            f"stock {qty} unsellable {c} on planet {pid} to free holds"))
        if v.ok("liftoff"):
            why = "nothing more to do here" if work_site else "not a world worth investing in"
            candidates.append(self._act("liftoff", {}, f"liftoff ({why})"))
        skipped = []
        for action in candidates:
            why = self._banned_why(action, v)
            if why:
                skipped.append(why)
                continue
            if action["kind"] == "dump_planet_cargo" and (action.get("args") or {}).get("commodity") == "organics":
                self.mem.organics_drop = None
            if action["kind"] == "load_planet_cargo":
                self.mem.stock_load = None
            if action["kind"] == "assign_colonists" and (action.get("args") or {}).get("from") == "ship":
                self.mem.colonist_drop = None
            if skipped:
                action["thought"] += f" [replanned: {'; '.join(skipped)}]"
            return action, Intent("colonize")
        return None

    def _genesis_aboard(self, v: View):
        if v.genesis_aboard <= 0 or v.landed is not None:
            return None
        if v.ok("deploy_genesis"):
            detour = self._pt_genesis_detour(v)
            if detour is not None:
                return detour, Intent("colonize")
            self.mem.pt_detour = 0
            self.mem.deploy_sector = int(v.here)
            return self._act("deploy_genesis", {}, f"deploy genesis in sector {v.here}"), Intent("colonize")
        reason = v.reason("deploy_genesis").lower()
        if "fedspace" in reason or "too close" in reason or "5 planets" in reason or "holds 5" in reason:
            warp = self._warp_away_from_stardock(v)
            if warp is not None:
                return self._act("warp", {"target": warp}, f"carry genesis elsewhere ({v.reason('deploy_genesis')})"), Intent("explore")
            # No legal exit: drop through so the ladder can sell / wait, not spin.
        return None

    def _note_colonist_room(self, v: View) -> None:
        """Remember a world whose legal list will not take colonists from the ship."""
        if self.mem is None or v.landed is None or v.colonists_aboard <= 0:
            return
        pid = int(v.landed)
        choices = {str(item) for item in v.choices("assign_colonists", "from")}
        if "ship" not in choices or v.max_by("assign_colonists", "qty", "ship") <= 0:
            self.mem.no_colonist_room.add(pid)
        else:
            self.mem.no_colonist_room.discard(pid)

    def _land_home(self, v: View):
        if v.landed is not None or not v.ok("land_planet"):
            return None
        choices = [int(c) for c in v.choices("land_planet", "planet_id")]
        for planet in self._work_sites(v):
            pid = int(planet["id"])
            if pid not in choices:
                continue
            can_build = self._citadel_ready(planet, v)
            dump = self._unsellable_goods(v)
            haul = self._hauling_organics(v) and int(planet["id"]) == int(self.mem.organics_drop)
            stock = self.mem.stock_load is not None and int(planet["id"]) == int(self.mem.stock_load[0])
            # A full world is not an unload stop. The legal list already said
            # the ship max is 0. Citadel, organics, and stock still land.
            unload = v.colonists_aboard > 0 and pid not in self.mem.no_colonist_room
            if unload or can_build or dump or haul or stock:
                why = ("unload colonists" if unload else "citadel is buildable" if can_build
                       else "deliver organics" if haul else "load stockpile for sale" if stock
                       else f"stock unsellable {dump[0]}")
                return self._act("land_planet", {"planet_id": pid}, f"land home planet {pid} ({why})"), Intent("colonize")
        return None

    def _land_orphan(self, v: View):
        """Land on an engine-listed orphan in this sector when inheriting it beats the genesis path."""
        if v.landed is not None or not v.ok("land_planet"):
            return None
        choices = [int(c) for c in v.choices("land_planet", "planet_id")]
        contested = {int(c) for c in ((v.params("land_planet").get("planet_id") or {}).get("contested") or [])}
        for pid, o in v.orphans.items():
            if o.get("sector_id") == v.here and pid in choices and pid not in contested and self._wants_orphan(v, o):
                return self._act("land_planet", {"planet_id": pid},
                                 f"land on orphan {pid} to claim it (L{o.get('citadel_level', 0)})"), Intent("colonize")
        return None

    def _wants_orphan(self, v: View, o: dict[str, Any]) -> bool:
        if int(o.get("citadel_level") or 0) >= 1:
            return True  # an inherited citadel is worth more than a fresh genesis seed
        if v.worlds():
            return False
        genesis_slow = v.credits < GENESIS_TORPEDO_COST + CITADEL_TIER_COST[0][0]
        return genesis_slow or self.pressure is not None

    def _at_stardock(self, v: View):
        if v.here != STARDOCK or self._hauling_organics(v):
            return None
        back = self._return_colonists_to_terra(v)
        if back is not None:
            return back, Intent("acquire")
        reserve = self._citadel_reserve(v)
        l1_credits = CITADEL_TIER_COST[0][0]
        genesis_price = int((v.params("buy_equip").get("item") or {}).get("unit_price_by", {}).get("genesis")
                            or GENESIS_TORPEDO_COST)
        gplanets = v.genesis_planets()
        # Upgrade hull first: 75 holds make every later ferry trip ~4x cheaper in turns.
        # Deliberately NOT deferred under rival pressure: offline sweeps showed
        # genesis-before-hull cost 5-140k net worth by day 6 on every seed tried.
        if v.ok("buy_ship") and v.ship_class != "cargotran" and "cargotran" in v.choices("buy_ship", "ship_class"):
            net = int((v.params("buy_ship").get("ship_class") or {}).get("net_cost_by", {}).get("cargotran") or 10**12)
            if v.credits - net >= self.cash_buffer and v.ship_class in ("merchant_cruiser", "scout_marauder"):
                return self._act("buy_ship", {"ship_class": "cargotran"}, f"upgrade to CargoTran ({net} cr net)"), Intent("acquire")
        # Long-range scanner: expert habit is buy at StarDock (density early, holo when the
        # hull allows and cash is there). Fits before combat/genesis so fogged seats can map.
        scan_buy = self._maybe_buy_hardware(v) or self._buy_scanner(v)
        if scan_buy is not None:
            return scan_buy, Intent("acquire")
        if self.feed_organics or self.value_allocator:
            # Combat hull / defence spend trade capital. Only arm after Ferrengi
            # are fogged (hot_sectors) — solo N2/N3 acceptance has none, and
            # early N3 defence buys were breaking the day-10 NW band.
            if self._fogged_hot():
                combat = self._buy_combat_hull(v)
                if combat is not None:
                    return combat, Intent("acquire")
                defense = self._buy_defense(v)
                if defense is not None:
                    return defense, Intent("acquire")
        drive = self._buy_transwarp_drive(v)
        if drive is not None:
            return drive, Intent("acquire")
        # N3: the first torpedo waits until CargoTran is affordable. Buying it
        # on a 20-hold hull (seed 250925: day 1, 20cr left) pushes the upgrade
        # out to day 7 and the extra holds never pay the turns back.
        if (self.value_allocator and not gplanets and self.pressure is None
                and self._cargotran_net(v) is not None and not self._cargotran_affordable(v)):
            self.mem.hull_wait = True
            return None
        # Genesis: the first as soon as it leaves L1 money; more when rich (sooner when trailing).
        if v.genesis_aboard == 0 and v.ok("buy_equip") and "genesis" in v.choices("buy_equip", "item"):
            price = genesis_price
            # Calm: keep L1 in the bank (the torpedo is wasted without it). Pressure spends
            # that reserve - the trip gate uses the same floor so we never fly here unable to buy.
            keep = 0 if self.pressure is not None else l1_credits
            first = not gplanets and v.credits - price >= keep
            # A 2nd world keeps the full reserve even when trailing: funding it from working
            # capital starved the first citadel (seed 99: -110k NW by day 6).
            more = bool(gplanets) and len(gplanets) < self.target_planets and v.credits - price >= reserve
            if first or more:
                why = f" - trailing {self.pressure.get('leader')}" if self.pressure and self.pressure.get("leader") else ""
                return self._act("buy_equip", {"item": "genesis", "qty": 1},
                                 f"buy genesis #{len(gplanets) + 1} ({price} cr){why}"), Intent("acquire")
        if v.worlds() and self._fogged_hot():
            hw = self._maybe_buy_rich_hardware(v)
            if hw is not None:
                return hw, Intent("acquire")
        # Ferry load: only what the next citadel tier still needs, never below the reserve.
        need = self._colonists_needed(v)
        if v.worlds() and need > 0 and self._buildable_elsewhere(v) is None and v.cargo_free > 0:
            loaded = self._load_colonists(v, need, reserve,
                                         f"load colonists for the ferry ({need} still needed)")
            if loaded is not None:
                return loaded, Intent("colonize", self.mem.home_sector)
        hw = self._maybe_buy_rich_hardware(v)
        if hw is not None and v.worlds() and self._colonists_needed(v) <= 0:
            return hw, Intent("acquire")
        limp = self._maybe_remove_limpet(v)
        if limp is not None:
            return limp, Intent("acquire")
        return None

    def _travel(self, v: View):
        if v.landed is not None:
            return None
        # QC class0-terra-v1: the defence trip may end at Alpha Centauri / Rylos, where
        # _at_stardock never runs - buy here or the seat ping-pongs back to the port forever.
        if v.here != STARDOCK and self._at_equip_port(v):
            defense = self._buy_defense(v)
            if defense is not None:
                return defense, Intent("acquire")
        if self._needs_dock_defense(v):
            dock = self._defence_dock(v)
            label = ("under-armed with cash - Class 0 for fighters/shields"
                     if dock != STARDOCK else
                     "under-armed with cash - StarDock for fighters/shields")
            plot = self._plot(v, dock, label)
            if plot is not None:
                return plot, Intent("acquire", dock)
        laid = self._maybe_lay_armids(v)
        if laid is not None:
            return laid, Intent("acquire")
        if self.mem is not None and self.mem.home_sector is not None and v.here == self.mem.home_sector:
            beacon = self._beacon_action(v)
            if beacon is not None:
                return beacon, Intent("acquire")
        if self._hauling_organics(v):
            planet = v.planet(self.mem.organics_drop)
            if planet is None:
                self.mem.organics_drop = None
            else:
                sid = int(planet["sector_id"])
                if v.here != sid:
                    plot = self._plot(v, sid, f"deliver organics to planet {planet['id']}")
                    if plot:
                        return plot, Intent("colonize", sid)
        home = self.mem.home_sector
        home_full = self.mem.home_planet in self.mem.no_colonist_room
        if v.colonists_aboard > 0 and home is not None and v.here != home and not home_full:
            plot = self._plot(v, home, "ferry colonists home")
            if plot:
                return plot, Intent("colonize", home)
        if (self._stuck_colonists(v) and v.here != STARDOCK
                and getattr(self, "_terra_full_day", None) != v.day):
            plot = self._plot(v, STARDOCK, "home world is full - return colonists to Terra")
            if plot:
                return plot, Intent("acquire", STARDOCK)
        # Another genesis world can start its next citadel right now: go build it.
        other = self._buildable_elsewhere(v)
        if other is not None and v.colonists_aboard == 0:
            plot = self._plot(v, int(other["sector_id"]), f"citadel buildable on planet {other['id']}")
            if plot:
                return plot, Intent("colonize", int(other["sector_id"]))
        dump = self._unsellable_goods(v)
        if dump and home is not None and v.here != home:
            plot = self._plot(v, home, f"no known buyer for {dump[0]} - stock it at home")
            if plot:
                return plot, Intent("colonize", home)
        # A listed orphan within reach that beats the genesis path: go land on it.
        if v.colonists_aboard == 0 and v.genesis_aboard == 0:
            for _pid, o in sorted(v.orphans.items(), key=lambda kv: -int(kv[1].get("citadel_level") or 0)):
                sid = o.get("sector_id")
                d = known_distance(v.known_warps, v.here, sid)
                if sid != v.here and d is not None and d <= ORPHAN_MAX_HOPS and self._wants_orphan(v, o):
                    plot = self._plot(v, int(sid), f"inherit orphan {o.get('name', _pid)} (L{o.get('citadel_level', 0)})")
                    if plot:
                        return plot, Intent("colonize", int(sid))
        return None

    def _go_stardock(self, v: View):
        """Autopilot to sector 1 when the ladder can pay for CargoTran or genesis.

        ``plot_course`` routes the real map, so sector 1 does not have to be
        explored first. FedSpace headings and ether probes are not a strategy.
        If the engine already rejected this plot, S6 bans it and we frontier-explore
        instead of issuing it again.
        """
        if v.landed is not None or v.here == STARDOCK or not self._needs_stardock(v):
            return None
        plot = self._plot(v, STARDOCK, self._stardock_reason(v))
        if plot is None:
            return None
        why = self._banned_why(plot, v)
        if why:
            return self._explore(v, f"StarDock plot rejected ({why})")
        kind = "colonize" if v.worlds() else "acquire"
        return plot, Intent(kind, STARDOCK)

    def _earn(self, v: View):
        crime = self._crime_action(v)
        if crime is not None:
            return crime, Intent("trade")
        self._note_refused_sells(v)
        # Price the one-hop port neighbours of the first route before milking a thin pair.
        # Empty holds only - cargo already aboard goes to a buyer first.
        survey = None if self._held_goods(v) else self._survey_target(v)
        if survey is not None:
            g = self._nav_graph(v)
            here = int(v.here)
            act = None
            intent_target = None
            if survey in g.get(here, ()) and survey in self._legal_warps(v):
                act = self._act("warp", {"target": survey}, f"earn: price the port at {survey}")
            elif survey not in g.get(here, ()):
                act = self._plot(v, survey, f"earn: price the port at {survey}")
                intent_target = survey
            if act is not None and not self._banned_why(act, v):
                return act, Intent("trade", intent_target)
        # Under tw2002 fog, map neighbors before committing to a blind trade/explore.
        scanned = self._maybe_scan(v)
        if scanned is not None:
            return scanned, Intent("explore")
        # Trade here if the envelope-driven heuristic finds a profitable buy/sell.
        ctx = TurnContext(seat="", turn_seq=0, observation=v.obs, llm_user_message=None, rules={},
                          status={}, deadline_at=None, server_skew=0.0)
        a = legal_heuristic_policy(ctx)
        if a.get("kind") == "trade" and not self._empty_shelf_buy(v, a):
            return self._act("trade", self._haggle_live(v, a.get("args") or {}),
                             f"earn: {a.get('thought', '')}"), Intent("trade")
        # Otherwise head for the best remembered route (sell what we carry, or fetch a cheap load).
        target, why = self._best_route(v)
        if target is not None:
            plot = self._plot(v, target, f"earn: {why}")
            if plot:
                return plot, Intent("trade", target)
        return self._explore(v, "earn: look for ports")

    # ------------------------------------------------------------------ N3 value per turn
    def _allocate(self, v: View):
        """Post-genesis choice: the option with the best net-worth per turn."""
        committed = self._commit_haul(v)
        if committed is not None:
            return committed
        if v.here == STARDOCK and v.worlds() and self._fogged_hot():
            hw = self._maybe_buy_rich_hardware(v)
            if hw is not None:
                return hw, Intent("acquire")
            limp = self._maybe_remove_limpet(v)
            if limp is not None:
                return limp, Intent("acquire")
        saved = (self.mem.colonist_drop, self.mem.stock_load, self.mem.organics_drop)
        options: list[tuple[float, dict[str, Any], Intent, dict[str, Any]]] = []
        for opt in (self._opt_upgrade(v), self._opt_scanner(v), self._opt_scan(v), self._opt_defense(v), self._opt_hunt_arm(v),
                    self._opt_organics(v), self._opt_build(v),
                    self._opt_genesis(v), self._opt_ferry(v), self._opt_stockpile(v), self._opt_planet_sell(v),
                    self._opt_trade(v),
                    self._opt_survey(v)):
            if opt is None:
                continue
            action = opt[1]
            if self._banned_why(action, v):
                continue
            side = opt[3] if len(opt) > 3 else {}
            options.append((opt[0], action, opt[2], side))
        self.mem.colonist_drop, self.mem.stock_load, self.mem.organics_drop = saved
        if not options:
            return self._explore(v, "no priced option")
        vpt, action, intent, side = max(options, key=lambda row: row[0])
        if "colonist_drop" in side:
            self.mem.colonist_drop = side["colonist_drop"]
        if "stock_load" in side:
            self.mem.stock_load = side["stock_load"]
        if "organics_drop" in side:
            self.mem.organics_drop = side["organics_drop"]
        action["thought"] += f" [{vpt:.0f} cr/turn]"
        return action, intent

    def _commit_haul(self, v: View):
        """Finish a haul already in the holds before opening a new option."""
        if v.landed is not None:
            return None
        if self._hauling_organics(v):
            planet = v.planet(self.mem.organics_drop)
            if planet is None:
                self.mem.organics_drop = None
            else:
                sid = int(planet["sector_id"])
                if v.here != sid:
                    plot = self._plot(v, sid, f"deliver organics to planet {planet['id']}")
                    if plot:
                        return plot, Intent("colonize", sid)
                return None
        dest = self._colonist_planet(v)
        if v.colonists_aboard > 0 and dest is not None:
            sid = int(dest["sector_id"])
            if v.here != sid:
                plot = self._plot(v, sid, f"ferry colonists to planet {dest['id']}")
                if plot:
                    return plot, Intent("colonize", sid)
            return None
        if self._held_goods(v):
            sold = self._sell_here(v)
            if sold is not None:
                return sold
            target, why = self._best_route(v)
            if target is not None and why.startswith("sell"):
                plot = self._plot(v, target, f"earn: {why}")
                if plot:
                    return plot, Intent("trade", target)
            dump = self._unsellable_goods(v)
            home = self.mem.home_sector
            if dump and home is not None and v.here != home:
                plot = self._plot(v, home, f"no known buyer for {dump[0]} - stock it at home")
                if plot:
                    return plot, Intent("colonize", home)
        return None

    def _sell_here(self, v: View):
        ctx = TurnContext(seat="", turn_seq=0, observation=v.obs, llm_user_message=None, rules={},
                          status={}, deadline_at=None, server_skew=0.0)
        a = legal_heuristic_policy(ctx)
        args = a.get("args") or {}
        if a.get("kind") == "trade" and args.get("side") == "sell":
            return self._act("trade", self._haggle_live(v, args), f"earn: {a.get('thought', '')}"), Intent("trade")
        return None

    def _tpw(self, v: View) -> int:
        spec = ship_specs().get(v.ship_class or "") or {}
        return max(1, int(spec.get("turns_per_warp") or 3))

    def _holds(self, v: View) -> int:
        holds = v.ship.get("holds")
        if isinstance(holds, int) and holds > 0:
            return holds
        used = sum(int(q or 0) for q in v.cargo.values())
        return max(1, v.cargo_free + used)

    def _distances_from(self, v: View, src: int) -> dict[int, int]:
        """One BFS per source per decision. Pairwise ``known_distance`` was the day-10 hotspot."""
        cache = getattr(self, "_bfs_cache", None)
        if cache is None or cache[0] is not v:
            cache = (v, {})
            self._bfs_cache = cache
        bucket: dict[int, dict[int, int]] = cache[1]
        src = int(src)
        hit = bucket.get(src)
        if hit is not None:
            return hit
        g = self._nav_graph(v)
        dist = {src: 0}
        frontier = [src]
        depth = 0
        while frontier:
            depth += 1
            nxt: list[int] = []
            for sector in frontier:
                for n in g.get(sector, ()):
                    if n not in dist:
                        dist[n] = depth
                        nxt.append(n)
            frontier = nxt
        bucket[src] = dist
        return dist

    def _hops(self, v: View, src: int | None, dst: int | None) -> int | None:
        if src is None or dst is None:
            return None
        if int(src) == int(dst):
            return 0
        return self._distances_from(v, int(src)).get(int(dst))

    def _hops_to_stardock(self, v: View) -> int:
        """Known hops to sector 1, or a short prior when the autopilot can still find it."""
        if v.here == STARDOCK:
            return 0
        hops = self._hops(v, v.here, STARDOCK)
        return hops if hops is not None else 6

    def _days_left(self, v: View) -> int:
        max_days = v.obs.get("max_days")
        if isinstance(max_days, int):
            return max(0, max_days - int(v.day))
        return 12

    def _sync_target_planets(self, v: View) -> None:
        """Raise the genesis cap above 2 while another torpedo leaves L1 cash.

        N1 keeps ``target_planets=2`` (``feed_organics`` off). N2/N3 raise the
        cap from fogged credits so rich seats plant more than two worlds.
        """
        if not (self.feed_organics or self.value_allocator):
            return
        # Fog + ladder: N2 needs a fatter spare-credits gate before raising past
        # two worlds. Thin-float third-planet ferries erase scanner-unlocked trade
        # (seed 250925 N2 behind N1). Rich N2 (bot-growth) and N3 allocator still
        # raise; the fatter step only binds the mid-ladder fog case.
        have = len(v.genesis_planets())
        step = GENESIS_TORPEDO_COST + CITADEL_TIER_COST[0][0] + self.working_capital
        if info_tw2002() and not self.value_allocator:
            step += 100_000
        spare = self._plan_budget(v) - self._unfinished_l2_cash(v)
        more = max(0, spare // step) if step else 0
        # Raise only while every current genesis world still has organics
        # runway (and at least two are fed, or fewer than two exist). Free
        # raise on N3 planted starved coeff-1 maps that then hit organics 0
        # (N3 acceptance forbids any zero). Same gate keeps N2 beating N1.
        raised = min(MAX_TARGET_PLANETS, max(2, have + more))
        worlds = v.genesis_planets()
        fed = sum(1 for w in worlds if int((growth_view(w) or {}).get("organics_days_left") or 0) > 0)
        if fed >= min(2, len(worlds)) and (not worlds or fed == len(worlds)):
            self.target_planets = raised

    def _unfinished_l2_cash(self, v: View) -> int:
        """L2 credit cost still unpaid on worlds that have not started that tier."""
        locked = 0
        for planet in v.genesis_planets():
            level = int(planet.get("citadel_level") or 0)
            target = int(planet.get("citadel_target") or 0)
            if level < 2 and target <= level:
                locked += CITADEL_TIER_COST[1][0]
        return locked

    def _trade_quote(self, v: View) -> tuple[float, int, int, int, str] | None:
        """(cr/turn, seller, buyer, margin, commodity) of the best empty-hold route."""
        pair = self._best_buy_pair(v)
        if pair is None or v.here is None:
            return None
        seller, buyer, margin = pair
        commodity = self._pair_commodity(v, seller, buyer, margin)
        d1 = 0 if seller == int(v.here) else self._hops(v, v.here, seller)
        d2 = self._hops(v, seller, buyer)
        if d1 is None or d2 is None or margin <= 0:
            return None
        turns = d1 * self._tpw(v) + 3 + d2 * self._tpw(v) + 3
        value = margin * self._holds(v)
        return value / max(1, turns), seller, buyer, margin, commodity or ""

    def _pair_commodity(self, v: View, seller: int, buyer: int, margin: int) -> str | None:
        found: str | None = None
        for sid, kp in self._priced_ports(v).items():
            if sid != seller:
                continue
            for commodity, st in (kp.get("stock") or {}).items():
                if not isinstance(st, dict) or st.get("side") != "sells_to_player":
                    continue
                ask = st.get("price")
                if not isinstance(ask, int):
                    continue
                for bsid, bkp in self._priced_ports(v).items():
                    if bsid != buyer:
                        continue
                    bst = (bkp.get("stock") or {}).get(commodity) or {}
                    bid = bst.get("price") if isinstance(bst, dict) else None
                    if isinstance(bid, int) and bid - ask == margin:
                        found = str(commodity)
        return found

    def _opt_upgrade(self, v: View):
        combat = self._combat_hull_option(v)
        if combat is not None:
            return combat
        if not self._cargotran_affordable(v):
            return None
        holds = self._holds(v)
        if holds >= 75:
            return None
        quote = self._trade_quote(v)
        base = quote[0] if quote is not None else 40.0
        uplift = base * (75 / max(1, holds) - 1)
        future = max(200, min(self._days_left(v), 8) * 600)
        value = uplift * future
        turns = self._hops_to_stardock(v) * self._tpw(v) + 1
        if v.here == STARDOCK and v.ok("buy_ship") and "cargotran" in v.choices("buy_ship", "ship_class"):
            net = int((v.params("buy_ship").get("ship_class") or {}).get("net_cost_by", {}).get("cargotran")
                      or self._cargotran_net(v) or 0)
            if v.credits < net:
                return None
            action = self._act("buy_ship", {"ship_class": "cargotran"}, f"upgrade to CargoTran ({net} cr net)")
        else:
            action = self._plot(v, STARDOCK, "CargoTran is affordable - autopilot to StarDock (sector 1)")
            if action is None:
                return None
        return value / max(1, turns), action, Intent("acquire", STARDOCK)

    def _opt_trade(self, v: View):
        if self._held_goods(v) or v.colonists_aboard or self._hauling_organics(v):
            return None
        quote = self._trade_quote(v)
        if quote is None or v.here is None:
            return None
        vpt, seller, _buyer, margin, commodity = quote
        if int(v.here) == seller:
            ctx = TurnContext(seat="", turn_seq=0, observation=v.obs, llm_user_message=None, rules={},
                              status={}, deadline_at=None, server_skew=0.0)
            a = legal_heuristic_policy(ctx)
            if a.get("kind") != "trade" or self._empty_shelf_buy(v, a):
                return None
            action = self._act("trade", a.get("args") or {}, f"earn: {a.get('thought', '')} ({commodity} ~{margin})")
            return vpt, action, Intent("trade")
        plot = self._plot(v, seller, f"earn: buy at {seller} (margin {margin})")
        if plot is None:
            return None
        return vpt, plot, Intent("trade", seller)

    def _opt_survey(self, v: View):
        if self._mate_skips_survey(v) or self._held_goods(v):
            return None
        quote = self._trade_quote(v)
        # A fat route does not pause for another port. A thin or missing one does.
        if quote is not None and quote[0] >= 60:
            return None
        sid = self._survey_target(v)
        if sid is None:
            return None
        g = self._nav_graph(v)
        here = int(v.here) if v.here is not None else None
        if here is not None and sid in g.get(here, ()) and sid in self._legal_warps(v):
            action = self._act("warp", {"target": sid}, f"earn: price the port at {sid}")
            intent = Intent("trade")
        else:
            action = self._plot(v, sid, f"earn: price the port at {sid}")
            if action is None:
                return None
            intent = Intent("trade", sid)
        floor = 30.0 if quote is None else quote[0] * 0.5
        return max(floor, 1.0), action, intent

    def _opt_genesis(self, v: View):
        if v.genesis_aboard > 0 or v.colonists_aboard > 0 or self._hauling_organics(v):
            return None
        if self._cargotran_net(v) is not None and not self._cargotran_affordable(v):
            return None
        have = len(v.genesis_planets())
        if have >= self.target_planets or have >= MAX_TARGET_PLANETS:
            return None
        # The second world can be in the air. A third waits until every world
        # already bought has started the L2 credit tier. That cash is what the
        # engine charges. The citadel does not add fighters.
        if have >= 2 and any(int(p.get("citadel_level") or 0) < 2 for p in v.genesis_planets()):
            return None
        if not self._genesis_affordable_now(v) or self._no_genesis_hull(v):
            return None
        if v.here == STARDOCK:
            if not (v.ok("buy_equip") and "genesis" in v.choices("buy_equip", "item")):
                return None
            price = int((v.params("buy_equip").get("item") or {}).get("unit_price_by", {}).get("genesis")
                        or GENESIS_TORPEDO_COST)
            action = self._act("buy_equip", {"item": "genesis", "qty": 1},
                               f"buy genesis #{have + 1} ({price} cr, NW-neutral plus growth)")
        else:
            action = self._plot(v, STARDOCK, f"genesis #{have + 1} is affordable - autopilot to StarDock")
            if action is None:
                return None
        turns = self._hops_to_stardock(v) * self._tpw(v) + 6 * self._tpw(v) + 8
        return self._genesis_expected_value(v) / max(1, turns), action, Intent("acquire", STARDOCK)

    def _genesis_affordable_now(self, v: View) -> bool:
        price = GENESIS_TORPEDO_COST
        if v.here == STARDOCK:
            price = int((v.params("buy_equip").get("item") or {}).get("unit_price_by", {}).get("genesis")
                        or GENESIS_TORPEDO_COST)
        keep = CITADEL_TIER_COST[0][0] + self.working_capital + self._unfinished_l2_cash(v)
        return v.credits - price >= keep

    def _genesis_expected_value(self, v: View) -> int:
        """Colonist growth after L1, plus the next tier's credit and colonist cost.

        The 25k torpedo becomes 2,500 colonists at the same price, so the
        purchase itself is not the value. Fighters and shields are not included.
        """
        days_left = self._days_left(v)
        grow_days = max(0, days_left - 2)
        end = _project_pop(GENESIS_SEED_COLONISTS - CITADEL_TIER_COST[0][1], grow_days, True)
        growth_value = max(0, end - (GENESIS_SEED_COLONISTS - CITADEL_TIER_COST[0][1])) * COLONIST_PRICE
        bonus = 0
        if days_left >= 8:
            bonus = _tier_bonus(1)
        elif days_left >= 5:
            bonus = _tier_bonus(1) // 2
        return bonus + growth_value

    def _opt_ferry(self, v: View):
        if v.colonists_aboard > 0 or v.genesis_aboard > 0 or self._hauling_organics(v) or self._held_goods(v):
            return None
        holds = max(1, v.cargo_free or self._holds(v))
        best: tuple[float, dict[str, Any], Intent] | None = None
        for planet in v.worlds():
            opt = self._ferry_for_planet(v, planet, holds)
            if opt is not None and (best is None or opt[0] > best[0]):
                best = opt
        return best

    def _ferry_for_planet(self, v: View, planet: dict[str, Any], holds: int):
        planned = _planned_tier(planet)
        starving = _world_starving(planet)
        if planned is None and not starving:
            return None
        have = _colonists_total(planet)
        gap = 0
        bonus = 0
        cred = 0
        level = int(planet.get("citadel_level") or 0) + 1
        tier_ferry = False
        if planned is not None and v.credits >= planned[0] and have < planned[1]:
            cred, col, bonus, level = planned
            gap = col - have
            # One colonist must still be buyable after the tier's credit cost is
            # reserved. A plot to StarDock that cannot buy is a trade ping-pong.
            unit_cost = _colonist_acquire_unit()
            tier_ferry = bonus > 0 and gap > 0 and (
                v.credits - cred >= unit_cost if unit_cost > 0 else v.credits >= cred
            )
        if not tier_ferry and starving:
            gap = min(holds, max(holds // 5, 15))
            bonus = _refill_value(gap, self._days_left(v))
            cred = 0
            level = int(planet.get("citadel_level") or 0)
        elif not tier_ferry:
            return None
        if gap <= 0 or bonus <= 0:
            return None
        trips = max(1, (gap + holds - 1) // holds)
        sid = int(planet["sector_id"])
        outbound = self._hops_to_stardock(v)
        back = self._hops(v, STARDOCK, sid)
        if back is None:
            back = self._hops(v, v.here, sid)
        if back is None:
            return None
        round_turns = (outbound + back) * self._tpw(v) + 6 + _colonist_ferry_turn_overhead()
        turns = max(1, trips * max(1, round_turns))
        vpt = bonus / turns
        # Keep the tier's credit cost in the bank. The cash buffer is for
        # trading, not for blocking the load that unlocks the citadel.
        afford_credits = v.credits - cred
        if v.here == STARDOCK:
            unit = _colonist_acquire_unit()
            afford = (holds if unit <= 0 else max(0, afford_credits // max(1, unit)))
            qty = min(holds, gap, afford)
            why = (f"ferry: load {qty} colonists to unlock L{level} on planet {planet['id']}"
                   if tier_ferry else f"ferry: refill starving planet {planet['id']} with {qty} colonists")
            action = self._load_colonists(v, qty, cred if unit > 0 else 0, why)
            if action is None or qty <= 0:
                return None
            return vpt, action, Intent("colonize", sid), {"colonist_drop": int(planet["id"])}
        label = (f"ferry: StarDock for {gap} colonists to unlock L{level} on planet {planet['id']}"
                 if tier_ferry else f"ferry: StarDock to refill starving planet {planet['id']}")
        plot = self._plot(v, STARDOCK, label)
        if plot is None:
            return None
        return vpt, plot, Intent("colonize", STARDOCK), {}

    def _opt_organics(self, v: View):
        if not self.feed_organics:
            return None
        hungry = self._hungry_worlds(v)
        if not hungry:
            return None
        world = hungry[0]
        g = growth_view(world) or {}
        days = int(g.get("organics_days_left") or 0)
        saved = self.mem.organics_drop
        # One day of runway dies at the next tick. The ladder still waits
        # (urgent=False) so an N2 colonist ferry is not stolen; the allocator
        # prices that day as already empty.
        plan = self._feed_organics(v, urgent=True)
        if plan is None:
            self.mem.organics_drop = saved
            return None
        action, intent = plan
        # Drop is committed only if this option wins. A losing feed must not
        # look like a haul we already bought.
        drop = self.mem.organics_drop
        if int(v.cargo.get("organics") or 0) <= 0:
            self.mem.organics_drop = saved
        pop = max(1, _colonists_total(world))
        # A day with the gate shut drops the whole colony off the 5% curve.
        at_risk = pop * COLONIST_PRICE
        vpt = 8_000.0 + at_risk / 20 if days <= 1 else 1_200.0 + at_risk / 80
        side = {"organics_drop": drop} if isinstance(drop, int) else {}
        return vpt, action, intent, side

    def _opt_build(self, v: View):
        if v.landed is not None or v.colonists_aboard or self._hauling_organics(v):
            return None
        best: tuple[float, dict[str, Any], Intent] | None = None
        for planet in v.worlds():
            # Spend the trade float on the trip only when the tier adds defense value.
            bonus_now = _tier_bonus(int(planet.get("citadel_level") or 0))
            floor = 0 if (self.pressure is not None or bonus_now >= 100_000) else self.working_capital
            if planet.get("sector_id") == v.here or not self._citadel_ready(planet, v, credit_pad=floor):
                continue
            sid = int(planet["sector_id"])
            hops = self._hops(v, v.here, sid)
            if hops is None:
                continue
            level = int(planet.get("citadel_level") or 0)
            bonus = _tier_bonus(level)
            if bonus <= 0:
                bonus = _tier_bonus(1)
            turns = hops * self._tpw(v) + 4
            vpt = bonus / max(1, turns)
            plot = self._plot(v, sid, f"citadel buildable on planet {planet['id']}")
            if plot is None:
                continue
            if best is None or vpt > best[0]:
                best = (vpt, plot, Intent("colonize", sid))
        return best

    def _opt_stockpile(self, v: View):
        if v.landed is not None or v.colonists_aboard or self._hauling_organics(v) or v.genesis_aboard:
            return None
        if self._held_goods(v):
            return None
        best: tuple[float, dict[str, Any], Intent, tuple[int, str]] | None = None
        holds = self._holds(v)
        for planet in v.worlds():
            stock = planet.get("stockpile") or {}
            if not isinstance(stock, dict):
                continue
            sid = int(planet["sector_id"])
            g = growth_view(planet) or {}
            burn = max(1, int(g.get("organics_consumption_per_day") or 1))
            for commodity, base in COMMODITY_BASE_PRICE.items():
                qty = int(stock.get(commodity) or 0)
                if commodity == "organics":
                    qty = max(0, qty - max(ORGANICS_LOAD, burn * 4))
                if qty <= 0:
                    continue
                if self._pt_held(v, planet, commodity):
                    continue  # bots-use-planet-trade-v1: sold by planet_trade at the port above it
                buyer = self._best_buyer(v, commodity)
                if buyer is None or buyer[1] <= base:
                    continue
                bsid, price = buyer
                load = min(qty, holds, v.cargo_free or holds)
                if load <= 0:
                    continue
                gain = (price - base) * load
                hops_to = 0 if v.here == sid else self._hops(v, v.here, sid)
                hops_sell = self._hops(v, sid, bsid)
                if hops_to is None or hops_sell is None:
                    continue
                turns = hops_to * self._tpw(v) + hops_sell * self._tpw(v) + 8
                vpt = gain / max(1, turns)
                if vpt <= 0:
                    continue
                action, intent = self._stockpile_move(v, planet, commodity)
                if action is None:
                    continue
                if best is None or vpt > best[0]:
                    best = (vpt, action, intent, (int(planet["id"]), commodity))
        if best is None:
            return None
        return best[0], best[1], best[2], {"stock_load": best[3]}

    def _stockpile_move(self, v: View, planet: dict[str, Any], commodity: str):
        sid = int(planet["sector_id"])
        pid = int(planet["id"])
        if v.here != sid:
            plot = self._plot(v, sid, f"sell planet {pid} {commodity} stockpile")
            if plot is None:
                return None, Intent()
            return plot, Intent("trade", sid)
        if v.landed is None:
            if not v.ok("land_planet") or pid not in [int(c) for c in v.choices("land_planet", "planet_id")]:
                return None, Intent()
            return self._act("land_planet", {"planet_id": pid}, f"land planet {pid} to load {commodity}"), Intent("trade")
        return self._stockpile_load_action(v, planet), Intent("trade")

    def _stockpile_load_action(self, v: View, planet: dict[str, Any]) -> dict[str, Any] | None:
        mark = self.mem.stock_load
        if mark is None or int(mark[0]) != int(planet["id"]):
            return None
        commodity = mark[1]
        if not v.ok("load_planet_cargo") or commodity not in v.choices("load_planet_cargo", "commodity"):
            return None
        stock = planet.get("stockpile") or {}
        qty = int(stock.get(commodity) or 0) if isinstance(stock, dict) else 0
        if commodity == "organics":
            g = growth_view(planet) or {}
            burn = max(1, int(g.get("organics_consumption_per_day") or 1))
            qty = max(0, qty - max(ORGANICS_LOAD, burn * 4))
        cap = v.max_by("load_planet_cargo", "qty", commodity) or qty
        qty = min(qty, cap, v.cargo_free or qty)
        if qty <= 0:
            self.mem.stock_load = None
            return None
        return self._act("load_planet_cargo",
                         {"planet_id": int(planet["id"]), "commodity": commodity, "qty": int(qty)},
                         f"load {qty} {commodity} from planet {planet['id']} to sell above base price")

    def _best_buyer(self, v: View, commodity: str) -> tuple[int, int] | None:
        best: tuple[int, int] | None = None
        day = int(v.day)
        for sid, kp in self._priced_ports(v).items():
            st = (kp.get("stock") or {}).get(commodity) or {}
            if not isinstance(st, dict) or st.get("side") != "buys_from_player":
                continue
            if st.get("max") is not None and int(st.get("current") or 0) >= int(st["max"]):
                continue
            if self.mem.bad_sells.get(f"{sid}:{commodity}") == day:
                continue
            price = st.get("price")
            if not isinstance(price, int):
                continue
            if best is None or price > best[1]:
                best = (int(sid), price)
        return best

    def _colonist_planet(self, v: View) -> dict[str, Any] | None:
        if self.mem.colonist_drop is not None:
            planet = v.planet(self.mem.colonist_drop)
            if planet is not None:
                return planet
        if self.mem.home_planet is not None:
            return v.planet(self.mem.home_planet)
        return None

    def _remember_ports(self, v: View) -> None:
        """Sectors whose port this seat has seen. Fogged fields only; StarDock is not a trade port."""
        seen = self.mem.ports_seen

        def add(sid: Any, is_port: bool) -> None:
            if not is_port or sid is None:
                return
            try:
                n = int(sid)
            except (TypeError, ValueError):
                return
            if n != STARDOCK:
                seen.add(n)

        for adj in v.obs.get("adjacent") or []:
            if isinstance(adj, dict):
                add(adj.get("id"), bool(adj.get("port")))
        for ks in v.obs.get("known_sectors") or []:
            if isinstance(ks, dict):
                add(ks.get("id"), bool(ks.get("port")))
        for kp in v.obs.get("known_ports") or []:
            if isinstance(kp, dict):
                add(kp.get("sector_id"), bool(kp.get("class") or kp.get("stock")))

    def _priced_ports(self, v: View) -> dict[int, dict[str, Any]]:
        out: dict[int, dict[str, Any]] = {}
        for kp in v.obs.get("known_ports") or []:
            if not isinstance(kp, dict) or kp.get("sector_id") is None:
                continue
            stock = kp.get("stock") or {}
            if any(isinstance(st, dict) and isinstance(st.get("price"), int) for st in stock.values()):
                out[int(kp["sector_id"])] = kp
        return out

    def _seen_buy_qty(self, v: View, commodity: str) -> int | None:
        """Units for sale here, from a port this seat has already seen. None if unseen."""
        if v.here is None or not commodity:
            return None
        for kp in v.obs.get("known_ports") or []:
            if not isinstance(kp, dict) or kp.get("sector_id") is None:
                continue
            if int(kp["sector_id"]) != int(v.here):
                continue
            st = (kp.get("stock") or {}).get(str(commodity))
            if isinstance(st, dict) and "current" in st:
                return int(st.get("current") or 0)
        return None

    def _empty_shelf_buy(self, v: View, action: dict[str, Any]) -> bool:
        """A buy with nothing on the shelf. A positive legal qty is stock the seat can see now.

        Remembered ``known_ports`` stock can be from an earlier day. The legal
        list is this turn. A sell of carried goods is not a buy.
        """
        if action.get("kind") != "trade":
            return False
        args = action.get("args") or {}
        if args.get("side") != "buy":
            return False
        if int(args.get("qty") or 0) > 0:
            return False
        seen = self._seen_buy_qty(v, str(args.get("commodity") or ""))
        return seen is None or seen <= 0

    def _best_buy_pair(self, v: View) -> tuple[int, int, int] | None:
        """(seller, buyer, unit margin) of the best empty-hold route over priced ports."""
        if v.here is None:
            return None
        sells: dict[str, list[tuple[int, int]]] = {}
        buys: dict[str, list[tuple[int, int]]] = {}
        for sid, kp in self._priced_ports(v).items():
            for c, st in (kp.get("stock") or {}).items():
                price = st.get("price") if isinstance(st, dict) else None
                if not isinstance(price, int):
                    continue
                if st.get("side") == "sells_to_player" and int(st.get("current") or 0) > 0:
                    sells.setdefault(c, []).append((sid, price))
                elif st.get("side") == "buys_from_player":
                    full = st.get("max") is not None and int(st.get("current") or 0) >= int(st["max"])
                    if not full and self.mem.bad_sells.get(f"{sid}:{c}") != int(v.obs.get("day") or 0):
                        buys.setdefault(c, []).append((sid, price))
        holds = max(1, v.cargo_free)
        here = int(v.here)
        from_here = self._distances_from(v, here)
        from_seller: dict[int, dict[int, int]] = {}
        best: tuple[float, int, int, int] | None = None
        for c, srcs in sells.items():
            for seller, ask in srcs:
                for buyer, bid in buys.get(c, []):
                    if bid <= ask or seller == buyer:
                        continue
                    d1 = 0 if seller == here else from_here.get(seller)
                    if seller not in from_seller:
                        from_seller[seller] = self._distances_from(v, seller)
                    d2 = from_seller[seller].get(buyer)
                    if d1 is None or d2 is None:
                        continue
                    margin = bid - ask
                    score = margin * holds / (d1 + d2 + 2)
                    if best is None or score > best[0]:
                        best = (score, seller, buyer, margin)
        if best is None:
            return None
        return best[1], best[2], best[3]

    def _cluster_sectors(self, v: View) -> set[int]:
        anchors = self.mem.trade_anchors
        if not anchors:
            return set()
        g = self._nav_graph(v)
        cluster = {int(a) for a in anchors}
        for ep in anchors:
            for nxt in g.get(int(ep), ()):
                if nxt in self.mem.ports_seen and nxt != STARDOCK:
                    cluster.add(int(nxt))
        return cluster

    def _survey_target(self, v: View) -> int | None:
        """An unpriced port one hop off the first trade pair, nearest first.

        Milking the first thin pair (and never looking at the ports beside it) is how a
        20k seat misses the route that actually pays for genesis. The cluster is frozen
        at that first pair so the survey cannot DFS the whole map.
        """
        if v.here is None or self._held_goods(v):
            return None
        if self.mem.trade_anchors is None:
            pair = self._best_buy_pair(v)
            if pair is None:
                return None
            self.mem.trade_anchors = (pair[0], pair[1])
        priced = set(self._priced_ports(v))
        g = self._nav_graph(v)
        here = int(v.here)
        todo: list[int] = []
        for sid in self._cluster_sectors(v):
            # One visit is enough. A sector with no port never gains a price; retrying it
            # is the 4↔47 ABA that stalls the ferry (S3 offline).
            if sid in (here, STARDOCK) or sid in priced or self.mem.visits.get(sid, 0) > 0:
                continue
            adjacent = sid in g.get(here, ())
            if adjacent or known_distance(g, here, sid) is not None:
                todo.append(sid)
        if not todo:
            return None

        def rank(sid: int) -> tuple[int, int, int]:
            if sid in g.get(here, ()):
                return (0, 0, sid)
            dist = known_distance(g, here, sid)
            return (1, dist if dist is not None else 99, sid)

        for sid in sorted(todo, key=rank):
            adjacent = sid in g.get(here, ())
            action = ({"kind": "warp", "args": {"target": sid}} if adjacent
                      else {"kind": "plot_course", "args": {"target": sid, "execute": True}})
            if not self._banned_why(action, v):
                return sid
        return None

    def _best_route(self, v: View) -> tuple[int | None, str]:
        """Route from REMEMBERED port snapshots (known_ports) over known warps only."""
        sells: dict[str, list[tuple[int, int]]] = {}
        buys: dict[str, list[tuple[int, int]]] = {}
        day = int(v.obs.get("day") or 0)
        for kp in v.obs.get("known_ports") or []:
            sid = kp.get("sector_id")
            for c, st in (kp.get("stock") or {}).items():
                price = st.get("price") if isinstance(st, dict) else None
                if not isinstance(price, int) or sid is None:
                    continue
                if st.get("side") == "sells_to_player" and int(st.get("current") or 0) > 0:
                    sells.setdefault(c, []).append((int(sid), price))
                elif st.get("side") == "buys_from_player":
                    full = st.get("max") is not None and int(st.get("current") or 0) >= int(st["max"])
                    if not full and self.mem.bad_sells.get(f"{sid}:{c}") != day:
                        buys.setdefault(c, []).append((int(sid), price))

        def dist(a, b):
            if a is None or b is None:
                return None
            if int(a) == int(b):
                return 0
            return self._distances_from(v, int(a)).get(int(b))

        # Carrying goods: go to the best-paying known buyer we can route to.
        for c, qty in sorted(v.cargo.items(), key=lambda kv: -int(kv[1] or 0)):
            if c == "colonists" or int(qty or 0) <= 0:
                continue
            options = [(p, s) for s, p in buys.get(c, []) if s != v.here and dist(v.here, s) is not None]
            if options:
                price, sid = max(options)
                return sid, f"sell {qty} {c} at {sid} (~{price})"
        # Empty: fetch the load with the best profit per hop.
        holds = max(1, v.cargo_free)
        best = None
        for c, srcs in sells.items():
            for a_sid, pa in srcs:
                for b_sid, pb in buys.get(c, []):
                    if pb <= pa or a_sid == b_sid:
                        continue
                    d1, d2 = dist(v.here, a_sid), dist(a_sid, b_sid)
                    if d1 is None or d2 is None:
                        continue
                    score = (pb - pa) * holds / (d1 + d2 + 2)
                    if best is None or score > best[0]:
                        best = (score, a_sid, c, b_sid, pa, pb)
        if best and best[1] != v.here:
            _, a_sid, c, b_sid, pa, pb = best
            return a_sid, f"buy {c} at {a_sid} (~{pa}) for {b_sid} (~{pb})"
        return None, ""

    def _idle(self, v: View, skipped: list[str] | None = None):
        note = f" [replanned: {'; '.join(skipped)}]" if skipped else ""
        out = self._explore(v, "nothing better to do")
        if out[0] is not None and not self._banned_why(out[0], v):
            out[0]["thought"] += note
            return out
        if v.ok("wait"):
            return self._act("wait", {}, f"pass{note}"), Intent()
        return self._act("query_limpets", {}, "out of turns - free no-op"), Intent()

    # ------------------------------------------------------------------ helpers
    def _held_goods(self, v: View) -> list[tuple[str, int]]:
        return sorted(((c, int(q or 0)) for c, q in v.cargo.items() if c != "colonists" and int(q or 0) > 0),
                      key=lambda cq: -cq[1])

    def _note_refused_sells(self, v: View) -> None:
        """At a port we remembered as a buyer, but the engine won't take it now: skip it today."""
        port = v.sector.get("port") or {}
        if not port or not self._held_goods(v):
            return
        sellable = self._sellable_here(v)
        day = int(v.obs.get("day") or 0)
        for c, _q in self._held_goods(v):
            if c in (port.get("buys") or []) and c not in sellable:
                self.mem.bad_sells[f"{v.here}:{c}"] = day

    def _buildable_elsewhere(self, v: View) -> dict[str, Any] | None:
        """A world in another sector whose next citadel can start now (colonists + credits).
        Trailing a rival, we spend the working capital on citadels instead of holding it."""
        floor = 0 if self.pressure is not None else self.working_capital
        for planet in v.worlds():
            if planet.get("sector_id") == v.here:
                continue
            if self._citadel_ready(planet, v, credit_pad=floor):
                return planet
        return None

    def _sellable_here(self, v: View) -> set[str]:
        if not v.ok("trade"):
            return set()
        return set((v.params("trade").get("commodity") or {}).get("sell_choices") or [])

    def _unsellable_goods(self, v: View) -> tuple[str, int] | None:
        """Largest held commodity with no buyer here and no reachable known buyer."""
        goods = self._held_goods(v)
        if not goods or not v.worlds():
            return None
        if any(c in self._sellable_here(v) for c, _ in goods):
            return None
        _, why = self._best_route(v)
        if why.startswith("sell"):
            return None
        return goods[0]

    def _shared_corp_home(self, v: View) -> dict[str, Any] | None:
        """bc10: the partner works the corp planet instead of founding a second home."""
        from ..engine import constants as engine_k
        from . import corp_brain
        if not engine_k.BOT_CORP_SHARED_HOME or engine_k.bot_corp_policy() not in ("pair", "team"):
            return None
        if not corp_brain.active() or corp_brain.role_of(str(v.self_id or "")) != "mate":
            return None
        planets = [p for p in ((v.obs.get("corp") or {}).get("planets") or [])
                   if isinstance(p, dict) and p.get("planet_id") is not None and p.get("sector_id") is not None]
        if not planets:
            return None
        return max(planets, key=lambda p: (int(p.get("citadel_level") or 0), int(p.get("population") or 0)))

    def _refresh_home(self, v: View) -> None:
        mem = self.mem
        shared = self._shared_corp_home(v)
        if mem.home_planet is not None and v.planet(mem.home_planet) is None:
            if shared is None or int(shared.get("planet_id") or -1) != int(mem.home_planet):
                mem.home_planet = mem.home_sector = None
        if shared is not None:
            mem.home_planet = int(shared["planet_id"])
            mem.home_sector = int(shared["sector_id"])
            return
        candidates = v.genesis_planets() or v.worlds()
        if candidates and mem.home_planet is None:
            best = max(candidates, key=lambda p: (int(p.get("citadel_level") or 0), _colonists_total(p)))
            mem.home_planet = int(best["id"])
            mem.home_sector = int(best["sector_id"])

    def _work_sites(self, v: View) -> list[dict[str, Any]]:
        sites = [p for p in v.worlds() if p.get("sector_id") == v.here]
        sites.sort(key=lambda p: p.get("id") != self.mem.home_planet)
        return sites

    def _citadel_reserve(self, v: View) -> int:
        """Credits we never spend on colonists/genesis: next citadel tier + working capital."""
        home = v.planet(self.mem.home_planet)
        tier = next_tier(home, lookahead=True) if home else None
        return (tier[0] if tier else 0) + self.working_capital

    def _colonists_needed(self, v: View) -> int:
        if self.mem.home_planet in self.mem.no_colonist_room:
            return 0
        home = v.planet(self.mem.home_planet)
        tier = next_tier(home, lookahead=True) if home else None
        if tier is None:
            return 0
        _cred, col = tier
        total = _colonists_total(home)
        aboard = v.colonists_aboard
        need_pop = col
        if self.citadel_floor_ratio is not None and not self._last_days(v):
            need_pop = col + int(col * self.citadel_floor_ratio)
        need = max(0, need_pop - total - aboard)
        if self.citadel_fuel_shield and not self._last_days(v):
            need = max(need, max(0, col - _pool(home, "fuel_ore") - aboard))
        return need

    def _last_days(self, v: View) -> bool:
        max_days = v.obs.get("max_days")
        if not isinstance(max_days, int):
            return False
        return max_days - int(v.day) <= CITADEL_LAST_DAYS

    def _citadel_ready(self, planet: dict[str, Any], v: View, *, credit_pad: int = 0) -> bool:
        """Next tier keeps a growth base, unless the match is in its last ~2 days.

        Floor: colonists remaining after the build stay at least
        ``ratio * tier colonist cost`` (1.0 means remaining >= the cost just paid).
        Fuel shield: the fuel_ore pool, which the engine drains first, covers
        the whole cost so organics workers survive the build.
        """
        tier = next_tier(planet)
        if tier is None:
            return False
        cred, col = tier
        total = _colonists_total(planet)
        if total < col or v.credits < cred + credit_pad:
            return False
        if self._last_days(v):
            return True
        if self.citadel_floor_ratio is not None and total - col < int(col * self.citadel_floor_ratio):
            return False
        if self.citadel_fuel_shield and _pool(planet, "fuel_ore") < col:
            return False
        # Multi-day tiers only. Remaining colonists must cover another build
        # of the same size, so the growth base is still there while the
        # citadel is under construction.
        if self.citadel_multiday_floor and next_tier_days(planet) > 1 and total - col < col:
            return False
        return True

    def _hauling_organics(self, v: View) -> bool:
        return bool(self.feed_organics and self.mem and self.mem.organics_drop is not None
                    and int(v.cargo.get("organics") or 0) > 0)

    def _hungry_worlds(self, v: View) -> list[dict[str, Any]]:
        if not self.feed_organics:
            return []
        rows: list[tuple] = []
        for planet in v.worlds():
            g = growth_view(planet)
            if not g:
                continue
            # Coeff-1 (K/U) cannot cover burn at a profit under 26/56/102
            # (seed 250925 planet 32). N2 skips them (held zeros). N3's bar
            # forbids any organics stock hitting 0, so value_allocator still
            # imports a lifeline. Coeff 0 (H) always imports to keep growth.
            coeff = _class_coeff(planet)
            if coeff == 1 and not self.value_allocator:
                continue
            days = int(g.get("organics_days_left") or 0)
            # Under tw2002 fog, preventive organics trips steal the trade float that
            # scanners unlock (N2 ferry ~34% vs N1 ~0% on seed 250925, RANK legacy).
            # Ladder feeds only empty stockpiles; N3 allocator keeps the 2-day runway.
            limit = 1 if info_tw2002() and not self.value_allocator else ORGANICS_FEED_DAYS
            if days < limit:
                rows.append((days, -int(g.get("organics_consumption_per_day") or 0), int(planet.get("id") or 0), planet))
        rows.sort()
        fed = [planet for *_rest, planet in rows]
        if self.value_allocator or len(fed) <= 2:
            return fed
        # Ladder: keep organics trips on the two earliest genesis ids so extra
        # rich-world plants do not steal equipment trades (seed 250925 ~4k gap).
        keep = sorted((int(p["id"]), p) for p in v.genesis_planets())[:2]
        keep_ids = {i for i, _ in keep}
        return [p for p in fed if int(p["id"]) in keep_ids]

    def _pending_colonist_cost(self, planet: dict[str, Any]) -> int:
        """Colonists the next citadel tier will drain (0 if no tier is coming)."""
        tier = next_tier(planet) or next_tier(planet, lookahead=True)
        return tier[1] if tier else 0

    def _ship_pool(self, planet: dict[str, Any], qty: int) -> str:
        """Where a ship-load of colonists goes: fuel shield first, then the organics target."""
        if not self.feed_organics:
            return "organics" if _pool(planet, "organics") < _colonists_total(planet) // 5 else "fuel_ore"
        if self.citadel_fuel_shield and _pool(planet, "fuel_ore") < self._pending_colonist_cost(planet):
            return "fuel_ore"
        return _unload_pool(planet, qty)

    def _rebalance_organics(self, v: View, planet: dict[str, Any]) -> dict[str, Any] | None:
        """Pull labor onto the organics pool until class production beats the burn.

        Coeff-1 worlds (K/U) cannot surplus-feed even with half the colony on
        organics. Reshuffling there burns turns and still hits 0; skip them entirely.
        """
        coeff = _class_coeff(planet)
        if coeff is None or coeff <= 0 or not v.ok("assign_colonists"):
            return None
        total = _colonists_total(planet)
        # Coeff-1 worlds cannot surplus-feed even with half the colony on organics.
        # The reshuffle burns turns and still hits 0 (seed 250925 class U: 2 turns
        # and ~15k behind N1 at the old scale; worse under 26/56/102). Import is
        # also a losing detour on those maps, so skip the labor move entirely.
        if coeff <= 1:
            return None
        target = organics_worker_target(total, coeff)
        # If covering the burn needs more than half the colony, the class cannot
        # surplus-feed; reshuffling only burns turns (same failure mode as coeff-1).
        if target > total // 2:
            return None
        workers = _pool(planet, "organics")
        if workers >= target:
            return None
        short = target - workers
        choices = {str(c) for c in v.choices("assign_colonists", "from")}
        pid = int(planet["id"])
        sources: list[tuple[str, int]] = []
        for src in ("colonists", "equipment"):
            avail = _pool(planet, src)
            if avail > 0:
                sources.append((src, avail))
        # Fuel is drained first by citadel construction. Only the surplus above
        # that payment may move onto organics.
        fuel = _pool(planet, "fuel_ore")
        shield = self._pending_colonist_cost(planet) if self.citadel_fuel_shield else 0
        if fuel > shield:
            sources.append(("fuel_ore", fuel - shield))
        for src, avail in sources:
            if src not in choices:
                continue
            cap = v.max_by("assign_colonists", "qty", src) or avail
            qty = min(short, avail, cap)
            if qty > 0:
                return self._act("assign_colonists",
                                 {"planet_id": pid, "from": src, "to": "organics", "qty": int(qty)},
                                 f"move {qty} {src}->organics (class {planet.get('class')} needs {target})")
        return None

    def _move_fuel_shield(self, v: View, planet: dict[str, Any]) -> dict[str, Any] | None:
        """Park the next citadel's colonist cost in fuel_ore, which the engine drains first."""
        if not self.citadel_fuel_shield or self._last_days(v) or not v.ok("assign_colonists"):
            return None
        tier = next_tier(planet)
        if tier is None:
            return None
        _cred, col = tier
        fuel = _pool(planet, "fuel_ore")
        if fuel >= col or _colonists_total(planet) < col:
            return None
        if self.citadel_floor_ratio is not None and _colonists_total(planet) - col < int(col * self.citadel_floor_ratio):
            return None  # population floor still blocks the build; ferry instead of reshuffling
        if v.credits < tier[0]:
            return None
        short = col - fuel
        choices = {str(c) for c in v.choices("assign_colonists", "from")}
        sources: list[tuple[str, int]] = []
        coeff = _class_coeff(planet)
        if coeff is not None and coeff > 0:
            extra = _pool(planet, "organics") - organics_worker_target(_colonists_total(planet), coeff)
            if extra > 0:
                sources.append(("organics", extra))
        for name in ("colonists", "equipment"):
            avail = _pool(planet, name)
            if avail > 0:
                sources.append((name, avail))
        pid = int(planet["id"])
        for src, avail in sources:
            if src not in choices:
                continue
            cap = v.max_by("assign_colonists", "qty", src) or avail
            qty = min(short, avail, cap)
            if qty > 0:
                return self._act("assign_colonists",
                                 {"planet_id": pid, "from": src, "to": "fuel_ore", "qty": int(qty)},
                                 f"park {qty} {src}->fuel_ore so L{int(planet.get('citadel_level') or 0) + 1} spares organics")
        return None

    def _organics_offer_here(self, v: View) -> tuple[int, int] | None:
        if not v.ok("trade"):
            return None
        params = v.params("trade")
        comm = params.get("commodity") or {}
        if "organics" not in (comm.get("buy_choices") or []):
            return None
        listed = ((params.get("unit_price") or {}).get("listed_by") or {}).get("organics") or {}
        cap = ((params.get("qty") or {}).get("max_by") or {}).get("organics") or {}
        price, buy_cap = listed.get("buy"), cap.get("buy") if isinstance(cap, dict) else None
        if not isinstance(price, int) or not isinstance(buy_cap, int) or buy_cap <= 0:
            return None
        return price, buy_cap

    def _cheapest_organics_seller(self, v: View) -> tuple[int, int] | None:
        best: tuple[int, int] | None = None
        here = self._organics_offer_here(v)
        if here is not None and v.here is not None:
            best = (int(v.here), here[0])
        for sid, kp in self._priced_ports(v).items():
            st = (kp.get("stock") or {}).get("organics") or {}
            if st.get("side") != "sells_to_player" or int(st.get("current") or 0) <= 0:
                continue
            price = st.get("price")
            if not isinstance(price, int):
                continue
            if best is None or price < best[1] or (price == best[1] and v.here is not None and sid == int(v.here)):
                best = (int(sid), price)
        return best

    def _feed_organics(self, v: View, *, urgent: bool = False):
        """Buy the cheapest organics we know and haul them when a world has <2 days left.

        ``urgent`` (the N3 allocator) treats a 1-day runway like an empty
        stockpile: the next day tick is what the proof samples. The fixed
        ladder leaves that day alone so a funded colonist ferry still runs.
        """
        if not self.feed_organics or v.landed is not None or self._hauling_organics(v):
            return None
        if v.colonists_aboard > 0 or v.genesis_aboard > 0 or v.cargo_free <= 0:
            return None
        hungry = self._hungry_worlds(v)
        if not hungry:
            return None
        world = hungry[0]
        g = growth_view(world) or {}
        days = int(g.get("organics_days_left") or 0)
        must = days <= 0 or (urgent and days <= 1)
        # Fog + ladder: never divert for a still-green runway. Opportunistic
        # organics buys while days>=1 were the N2 income cliff under scanners.
        if info_tw2002() and not self.value_allocator and not must:
            return None
        # A one-day runway can wait for a StarDock trip that is already funded
        # (genesis or the colonist ferry). An empty stockpile cannot.
        if not must and self._needs_stardock(v):
            return None
        burn = max(1, int(g.get("organics_consumption_per_day") or 1))
        want = max(ORGANICS_LOAD, burn * 3)
        offer = self._organics_offer_here(v)
        seller = self._cheapest_organics_seller(v)
        # Standing at a non-premium seller: fill holds. Don't detour for a
        # cheaper port while a day of runway remains - that detour is a
        # colonist ferry we don't get back (seeds 250925 and 31).
        # Both the ladder and the allocator buy at the live price scale. The
        # ladder's old fixed 19/25 gate never matched a tw2002 quote, so a
        # hungry world sent it to a seller it then refused to buy from
        # (ECONOMY_CALIBRATION.md).
        cheap = _organics_cheap_price()
        ceiling = _organics_price_ceiling()
        if offer is not None and offer[0] <= ceiling and (must or offer[0] <= cheap
                                                         or seller is None or int(seller[0]) == int(v.here)):
            price, cap = offer
            keep = 0 if must else self.cash_buffer
            afford = max(0, (v.credits - keep) // max(1, price))
            qty = min(want, cap, afford, v.cargo_free)
            if qty > 0:
                self.mem.organics_drop = int(world["id"])
                tag = "cheap" if price <= cheap else "cheapest known"
                return (self._act("trade", {"commodity": "organics", "qty": int(qty), "side": "buy"},
                                  f"buy {qty} {tag} organics @{price} ({days}d left on planet {world['id']})"),
                        Intent("colonize", world.get("sector_id")))
        if must and seller is not None and v.here is not None and int(seller[0]) != int(v.here):
            sid, price = seller
            plot = self._plot(v, sid, f"organics seller {sid} (~{price}) for planet {world['id']} ({days}d left)")
            if plot is not None and not self._banned_why(plot, v):
                return plot, Intent("colonize", sid)
        return None


    def _note_ferrengi(self, v: View) -> None:
        """Remember sectors where Ferrengi are (or were) visible to this seat."""
        if self.mem is None:
            return
        ferr = (v.sector or {}).get("ferrengi") or []
        if ferr and v.here is not None:
            self.mem.hot_sectors.add(int(v.here))
        for e in v.events:
            kind = e.get("kind")
            if kind not in ("ferrengi_move", "ferrengi_attack", "ferrengi_spawn"):
                continue
            facts = e.get("facts") or {}
            for key in ("to", "sector_id", "from"):
                sid = facts.get(key)
                if isinstance(sid, int):
                    self.mem.hot_sectors.add(int(sid))
            # Summaries sometimes carry the sector; parse digits only when short.
            if e.get("sector_id") is not None:
                try:
                    self.mem.hot_sectors.add(int(e["sector_id"]))
                except (TypeError, ValueError):
                    pass

    def _ship_fighters(self, v: View) -> int:
        return int(v.ship.get("fighters") or 0)

    def _ship_shields(self, v: View) -> int:
        return int(v.ship.get("shields") or 0)

    def _under_defended(self, v: View) -> bool:
        return (self._ship_fighters(v) < DEFENSE_FIGHTERS_FLOOR
                or self._ship_shields(v) < DEFENSE_SHIELDS_FLOOR)

    def _fogged_hot(self) -> bool:
        """True when Ferrengi have been seen this seat (mem may be unset on helper-only calls)."""
        return bool(self.mem and self.mem.hot_sectors)

    def _should_avoid_hot(self, v: View) -> bool:
        return (self.feed_organics or self.value_allocator) and self._under_defended(v) and self._fogged_hot()

    def _load_colonists(self, v: View, need: int, reserve: int, why: str) -> dict[str, Any] | None:
        """Take colonists at sector 1: terra_colonists under tw2002, else buy_equip."""
        need = int(need)
        if need <= 0 or v.cargo_free <= 0:
            return None
        if class0_tw2002():
            if not v.ok("terra_colonists"):
                return None
            if "take" not in {str(x) for x in v.choices("terra_colonists", "mode")}:
                return None
            room = v.max_by("terra_colonists", "qty", "take")
            qty = min(need, room, v.cargo_free)
            if qty <= 0:
                return None
            return self._act("terra_colonists", {"mode": "take", "qty": int(qty)}, why)
        if not v.ok("buy_equip") or "colonists" not in v.choices("buy_equip", "item"):
            return None
        unit = int((v.params("buy_equip").get("item") or {}).get("unit_price_by", {}).get("colonists")
                   or COLONIST_PRICE)
        afford = max(0, (v.credits - int(reserve)) // max(1, unit))
        qty = min(v.max_by("buy_equip", "qty", "colonists"), afford, need, v.cargo_free)
        if qty <= 0:
            return None
        return self._act("buy_equip", {"item": "colonists", "qty": int(qty)}, why)

    def _known_class0_sectors(self, v: View) -> list[int]:
        """StarDock plus any Alpha Centauri / Rylos the seat has actually seen."""
        found = [STARDOCK]
        for entry in (v.obs.get("known_ports") or []):
            if not isinstance(entry, dict):
                continue
            sid = entry.get("sector_id", entry.get("id"))
            try:
                sid_i = int(sid)
            except (TypeError, ValueError):
                continue
            cls = str(entry.get("class") or "")
            special = entry.get("special")
            name = str(entry.get("name") or "")
            if cls == "0" or special in ("alpha_centauri", "rylos") or name in ("Alpha Centauri", "Rylos"):
                if sid_i not in found:
                    found.append(sid_i)
        # Current sector class0_port block
        sector = v.obs.get("sector") or {}
        if isinstance(sector, dict) and sector.get("class0_port"):
            try:
                sid_i = int(sector.get("id") or v.here)
            except (TypeError, ValueError):
                sid_i = int(v.here)
            if sid_i not in found:
                found.append(sid_i)
        return found

    def _nearest_equip_port(self, v: View) -> int:
        """Nearest known Class 0 / StarDock for fighters/shields/holds (CLASS0_TERRA.md)."""
        best = STARDOCK
        best_hops = self._hops(v, v.here, STARDOCK)
        if best_hops is None:
            best_hops = 10**9
        for sid in self._known_class0_sectors(v):
            h = self._hops(v, v.here, sid)
            if h is None:
                continue
            if h < best_hops or (h == best_hops and sid < best):
                best_hops = h
                best = sid
        return best

    def _stuck_colonists(self, v: View) -> bool:
        """tw2002: colonists aboard that the full home world refused (holds otherwise stay full forever)."""
        return (class0_tw2002() and v.colonists_aboard > 0 and self.mem is not None
                and self.mem.home_planet in self.mem.no_colonist_room)

    def _return_colonists_to_terra(self, v: View) -> dict[str, Any] | None:
        """QC class0-terra-v1: hand refused colonists back with terra_colonists mode=leave.

        Seed 250925 solo N2: the last 75-colonist load hit the 3000 cap at home and
        the CargoTran traded with full holds for two days (NW 350k -> 174k).
        """
        if not self._stuck_colonists(v):
            return None
        modes = {str(x) for x in v.choices("terra_colonists", "mode")} if v.ok("terra_colonists") else set()
        qty = min(v.colonists_aboard, v.max_by("terra_colonists", "qty", "leave")) if "leave" in modes else 0
        if qty <= 0:
            self._terra_full_day = v.day  # Terra refilled: do not fly back again today (no ping-pong)
            return None
        return self._act("terra_colonists", {"mode": "leave", "qty": int(qty)},
                         f"home world is full - leave {qty} colonists at Terra")

    def _defence_dock(self, v: View) -> int:
        """Where the N2 defence trip goes: StarDock while the seat has business there.

        QC class0-terra-v1: the old StarDock trip was also where a 20-hold N2 seat
        bought its CargoTran and loaded colonists (the ferry gate needs 25 free
        holds). Sending it to Alpha Centauri / Rylos instead silently ended
        colonisation (seed 250925 P3: 1745 -> 20 colonists by day 10).
        """
        if self._cargotran_affordable(v) or self._needs_stardock(v):
            return STARDOCK
        if v.worlds() and v.colonists_aboard == 0 and self._colonists_needed(v) > 0:
            return STARDOCK
        return self._nearest_equip_port(v)

    def _at_equip_port(self, v: View) -> bool:
        if v.here == STARDOCK:
            return True
        if not class0_tw2002():
            return False
        sector = v.obs.get("sector") or {}
        return bool(isinstance(sector, dict) and sector.get("class0_port"))

    def _needs_dock_defense(self, v: View) -> bool:
        if not (self.feed_organics or self.value_allocator):
            return False
        # Only divert a trade route after Ferrengi have been seen (fogged).
        if not self._fogged_hot():
            return False
        if v.credits < DEFENSE_CASH_GATE or not self._under_defended(v):
            return False
        if self._at_equip_port(v):
            return False
        return True


    def _fed_tow_risk(self, v: View) -> bool:
        """fedspace-police-v1: parked in FedSpace with 99+ fighters, or beyond the visible parking limit."""
        hint = v.obs.get("fedspace") if isinstance(v.obs, dict) else None
        if not isinstance(hint, dict):
            return False  # no hint outside FedSpace or under FED_MODE legacy
        fighters = int(self._ship_fighters(v))
        limit = int(hint.get("tow_fighter_limit") or 98)
        return bool(hint.get("will_be_towed")) or fighters > limit

    def _fed_exit_plan(self, v: View) -> tuple[int | None, int]:
        """(first warp toward the nearest known sector outside FedSpace, hops to get there)."""
        if v.here is None or not v.ok("warp"):
            return None, 0
        legal = [int(c) for c in (v.choices("warp", "target") or [])]
        outside = [c for c in legal if c not in FEDSPACE_IDS]
        if outside:
            return min(outside), 1
        dist = self._distances_from(v, int(v.here))
        exits = sorted((d, sid) for sid, d in dist.items() if sid not in FEDSPACE_IDS and d > 0)
        for d, sid in exits:
            hop = self._known_hop_toward(v, sid)
            if hop is not None:
                return hop, d
        return (min(legal), FED_TOW_UNKNOWN_EXIT_HOPS) if legal else (None, 0)

    def _fed_turns_short(self, v: View, hops: int) -> bool:
        """True once the turns left today only just cover the trip out of FedSpace (tows run at Extern)."""
        left = int(v.obs.get("turns_remaining") or 0) if isinstance(v.obs, dict) else 0
        cost = int((v.legal.get("warp") or {}).get("turn_cost") or 1)
        return left <= (max(1, hops) + FED_TOW_EXIT_MARGIN_WARPS) * max(1, cost)

    def _avoid_fed_tow(self, v: View) -> dict[str, Any] | None:
        """fedspace-police-v1: do not overnight in FedSpace with 99+ fighters or as an extra parked ship.

        Tows run only at Extern (day end), so a seat may do its StarDock business armed and leave
        when the day's turns run short. Leaving at once on every visit ping-ponged sector 1 (QC).
        """
        if not self._fed_tow_risk(v):
            return None
        hop, hops = self._fed_exit_plan(v)
        if hop is None or not self._fed_turns_short(v, hops):
            return None
        return self._act("warp", {"target": hop},
                         f"leave FedSpace before the Extern tow (figs={self._ship_fighters(v)}, {hops} hops out)")

    def _transwarp_instead(self, v: View, action: dict[str, Any], intent: Intent) -> dict[str, Any]:
        """ship-transwarp-v1: swap a long walk for a locked jump to the same sector.

        Only a sector on the legal list (own / corp / ally fighter, or FedSpace when commissioned) -
        never blind. Only when the walk is SHIP_TW_MIN_HOPS+ hops and the hold keeps the same ore
        again for the way back. Under SHIP_TW_MODE legacy there is no ship_transwarp entry, so this no-ops.
        """
        if action.get("kind") not in ("warp", "plot_course") or not v.ok("ship_transwarp"):
            return action
        target = (action.get("args") or {}).get("target") if action.get("kind") == "plot_course" else None
        if target is None:
            target = intent.target
        try:
            target = int(target)
        except (TypeError, ValueError):
            return action
        spec = v.params("ship_transwarp").get("sector_id") or {}
        if target not in {int(c) for c in (spec.get("choices") or [])}:
            return action
        hops = int((spec.get("hops_by") or {}).get(str(target)) or 0)
        ore_need = int((spec.get("ore_by") or {}).get(str(target)) or 0)
        ore = int(v.obs.get("_tw_ore_aboard", v.cargo.get("fuel_ore")) or 0)  # the real hold, reserve included
        saved = tw_turns_saved(self._tpw(v), hops)
        if saved < SHIP_TW_MIN_TURNS_SAVED or ore_need <= 0 or ore < ore_need:
            return action
        return self._act("ship_transwarp", {"sector_id": target},
                         f"TransWarp to {target} ({hops} hops, {ore_need} ore, saves {saved} turns)")

    def _planned_tw_hops(self, o: dict[str, Any]) -> int | None:
        """Drive owners: hops of the jump the seat is heading for (last turn's travel target), when that target
        is a lock (listed now, or FedSpace under the commission lock) and the jump saves
        SHIP_TW_MIN_TURNS_SAVED+ turns. That jump's ore is the whole reserve; None = keep nothing."""
        tw = (o.get("ship") or {}).get("transwarp")
        target = self._intent.target if self._intent is not None else None
        if not isinstance(tw, dict) or tw.get("fitted") != "type1" or target is None:
            return None
        v = View(o)
        if v.here is None or int(target) == int(v.here):
            return None
        spec = v.params("ship_transwarp").get("sector_id") or {}
        hops = (spec.get("hops_by") or {}).get(str(int(target)))
        if hops is None:
            from ..engine import constants as engine_k
            if not (tw.get("fed_lock") and int(target) in engine_k.FEDSPACE_SECTORS):
                return None
            hops = self._hops(v, v.here, int(target))
            if hops is None:
                return None
        hops = int(hops)
        if tw_turns_saved(self._tpw(v), hops) < SHIP_TW_MIN_TURNS_SAVED:
            return None
        return hops

    def _top_up_tw_ore(self, v: View) -> dict[str, Any] | None:
        """Drive owners only: at a port that sells fuel ore, fill the hold up to the TransWarp reserve."""
        keep = int(v.obs.get("_tw_ore_reserve") or 0)
        have = int(v.obs.get("_tw_ore_aboard") or 0)
        if keep <= 0 or have >= keep or v.landed is not None or not v.ok("trade"):
            return None
        params = v.params("trade")
        if "fuel_ore" not in ((params.get("commodity") or {}).get("buy_choices") or []):
            return None
        room = int((((params.get("qty") or {}).get("max_by") or {}).get("fuel_ore") or {}).get("buy", 0) or 0)
        qty = min(keep - have, room, max(0, v.cargo_free))
        if qty <= 0:
            return None
        return self._act("trade", {"commodity": "fuel_ore", "qty": int(qty), "side": "buy"},
                         f"top up the TransWarp ore reserve ({have}+{qty} of {keep})")

    def _extern_tow(self, v: View) -> dict[str, Any] | None:
        """ship-tow-transwarp2-v1 (BOT_TOW_POLICY extern_hold_only): at day end (no turns left for a warp) in
        FedSpace beside an own unmanned ship Extern would repossess, lock it in tow (0 turns); with turns again
        (next morning), release the lock before anything else. Never tows traders, never buys Type 2."""
        from ..engine import constants as engine_k
        if engine_k.BOT_TOW_POLICY != "extern_hold_only" or not engine_k.tow_on():
            return None
        tow = (v.obs.get("ship") or {}).get("tow") or {}
        left = int(v.obs.get("turns_remaining") or 0)
        if tow.get("target") is not None or tow.get("engaged"):
            if left >= self._tpw(v) and v.ok("tow_release"):
                return self._act("tow_release", {}, "morning: release the overnight tow lock")
            if left < self._tpw(v):  # day over: sit still with the lock (a free no-op, nothing that docks)
                return self._act("query_limpets", {}, "holding my unmanned ship in tow over Extern")
            return None
        if left >= self._tpw(v) or not v.ok("tow_engage") or v.here not in engine_k.FEDSPACE_SECTORS:
            return None
        choices = {str(c) for c in v.choices("tow_engage", "target")}
        for s in ((v.obs.get("fleet") or {}).get("ships") or []):
            t = f"ship:{int(s.get('ship_id') or 0)}"
            if t in choices and s.get("repo_at_extern") and int(s.get("sector_id") or -1) == int(v.here):
                return self._act("tow_engage", {"target": t},
                                 f"lock my unmanned {s.get('hull')} in tow so Extern does not repossess it")
        return None

    def _stardock_hull_need(self, v: View, balance: int) -> int:
        """Cash that must be on hand for the next hull the ladder would buy, counting the bank."""
        if not v.ok("buy_ship"):
            return 0
        choices = set(str(c) for c in v.choices("buy_ship", "ship_class"))
        nets = (v.params("buy_ship").get("ship_class") or {}).get("net_cost_by") or {}
        purse = int(v.credits) + int(balance)
        if v.ship_class == "escape_pod":
            picks = (("cargotran", self.cash_buffer), ("scout_marauder", 0))
        elif v.ship_class in ("merchant_cruiser", "scout_marauder") and "cargotran" in choices:
            picks = (("cargotran", self.cash_buffer),)
        else:
            return 0
        for key, reserve in picks:
            if key not in choices:
                continue
            cost = int(nets.get(key) or 0)
            if cost > 0 and purse - cost >= reserve:
                return cost + reserve
        return 0

    def _bank_keep(self, v: View, hull_need: int) -> int:
        """Spare above this stays on the ship: the float, the pending hull, or the first genesis plus L1."""
        from ..engine import constants as engine_k
        keep = max(int(engine_k.BOT_BANK_FLOAT), int(hull_need))
        if hull_need > 0:
            return keep
        if (v.genesis_aboard == 0 and not v.genesis_planets() and v.ok("buy_equip")
                and "genesis" in set(str(c) for c in v.choices("buy_equip", "item"))):
            price = int((v.params("buy_equip").get("item") or {}).get("unit_price_by", {}).get("genesis")
                        or GENESIS_TORPEDO_COST)
            keep = max(keep, price + int(CITADEL_TIER_COST[0][0]))
        # A torpedo or a world still needs its citadel cash. That is the next purchase, not spare.
        if v.genesis_aboard and not v.worlds():
            keep = max(keep, int(CITADEL_TIER_COST[0][0]) + self.working_capital)
        if v.worlds():
            keep = max(keep, self._citadel_reserve(v))
        return keep

    def _mate_skips_survey(self, v: View) -> bool:
        """bc16: the partner trades. The C.E.O. is the one who spends turns surveying."""
        from ..engine import constants as engine_k
        from . import corp_brain
        if engine_k.BOT_CORP_EXPLORER != "ceo" or engine_k.bot_corp_policy() not in ("pair", "team"):
            return False
        if not corp_brain.active() or not v.stardock_known:
            return False
        if corp_brain.role_of(str(v.self_id or "")) != "mate":
            return False
        corp = v.obs.get("corp") or {}
        ceo = str(corp.get("ceo_id") or "")
        for member in corp.get("members") or []:
            if isinstance(member, dict) and str(member.get("id") or "") == ceo:
                return bool(member.get("alive", True))
        return False

    def _mate_waits_on_citadel(self, v: View) -> bool:
        """bc11: the partner does not pay the same citadel step while the C.E.O. is alive."""
        from ..engine import constants as engine_k
        from . import corp_brain
        if not engine_k.BOT_CORP_SINGLE_BUILDER or engine_k.bot_corp_policy() not in ("pair", "team"):
            return False
        if not corp_brain.active() or corp_brain.role_of(str(v.self_id or "")) != "mate":
            return False
        corp = v.obs.get("corp") or {}
        ceo = str(corp.get("ceo_id") or "")
        for member in corp.get("members") or []:
            if isinstance(member, dict) and str(member.get("id") or "") == ceo:
                return bool(member.get("alive", True))
        return False

    def _hull_upgrade_cost(self, hull: str | None) -> int:
        from ..engine import constants as engine_k
        from . import corp_brain
        nxt = corp_brain.next_hull(str(hull or ""))
        if nxt is None:
            return 0
        return int(engine_k.SHIP_COST_TW2002[nxt])

    def _corp_top_up(self, v: View, state: Any, partner: str, row: dict[str, Any]) -> dict[str, Any] | None:
        """bc14: once a day, take spare fighters or shields before a fight, a FedSpace exit, or a home drop."""
        from ..engine import constants as engine_k
        from . import corp_brain
        if int(getattr(state, "corp_fighter_day", -1)) == int(v.day):
            return None
        hostiles = bool(v.sector.get("ferrengi")) or any(
            isinstance(t, dict) and str(t.get("id") or "") not in {partner, str(v.self_id or "")}
            for t in (v.sector.get("traders") or [])
        )
        leaving_fed = bool(v.sector.get("is_fedspace")) and int(v.here or 0) != int(engine_k.STARDOCK_SECTOR)
        home_drop = self.mem is not None and self.mem.home_sector is not None and v.here == self.mem.home_sector and v.ok("deploy_fighters")
        if not ((v.ok("attack") and hostiles) or leaving_fed or home_drop):
            return None
        have = row.get("take_max") or {}
        keep = int(engine_k.BOT_CORP_KEEP_FIGHTERS_PCT)
        for item, room_key in (("fighters", "fighter_headroom"), ("shields", "shield_headroom")):
            qty = corp_brain.gear_take(int(have.get(item) or 0), int(v.ship.get(room_key) or 0), keep)
            if qty is None:
                continue
            state.corp_fighter_day = int(v.day)
            return self._act("corp_transfer",
                             {"target": partner, "item": item, "qty": int(qty), "direction": "take"},
                             "pair: top up from my partner")
        return None

    def _corp_support(self, v: View) -> dict[str, Any] | None:
        """bc12 and bc13: one credit handoff per pair per day, and only to the configured partner."""
        from ..engine import constants as engine_k
        from . import corp_brain
        if not v.ok("corp_transfer") or v.landed is not None:
            return None
        me = str(v.self_id or "")
        partner = corp_brain.partner_of(me)
        state = self.mem
        if not partner or state is None:
            return None
        row = next((p for p in (v.params("corp_transfer").get("partners") or [])
                    if isinstance(p, dict) and str(p.get("player_id") or "") == partner), None)
        if row is None:
            return None
        topped = self._corp_top_up(v, state, partner, row)
        if topped is not None:
            return topped
        if int(state.corp_transfer_day) == int(v.day):
            return None
        mate_credits = int((row.get("take_max") or {}).get("credits") or 0)
        traders = {str(t.get("id")): t for t in (v.sector.get("traders") or []) if isinstance(t, dict)}
        mate_hull = str((traders.get(partner) or {}).get("ship_class") or "")
        reserve = int(engine_k.working_capital_reserve(int(v.ship.get("holds") or 0))) if engine_k.buy_reserve_on() else 0
        qty = corp_brain.credit_give(
            int(v.credits), self._hull_upgrade_cost(v.ship_class), mate_credits, self._hull_upgrade_cost(mate_hull),
            reserve=reserve, pad=int(engine_k.BOT_CORP_TRANSFER_PAD), minimum=int(engine_k.BOT_CORP_MIN_TRANSFER),
        )
        if qty is None and engine_k.BOT_CORP_TAX_SHIELD and engine_k.bank_on():
            sides = {str(r.get("id")): str(r.get("side") or "") for r in v.rivals}
            if sides.get(partner) == "evil" and int(v.obs.get("alignment") or 0) >= int(engine_k.TAX_MIN_ALIGNMENT):
                qty = corp_brain.tax_give(int(v.credits), int(engine_k.TAX_THRESHOLD),
                                          minimum=int(engine_k.BOT_CORP_MIN_TRANSFER))
        if qty is None:
            return None
        state.corp_transfer_day = int(v.day)
        return self._act("corp_transfer",
                         {"target": partner, "item": "credits", "qty": int(qty), "direction": "give"},
                         "pair: hand my partner the shortfall")

    def _corp_pair(self, v: View) -> dict[str, Any] | None:
        """CORP_RULES.md cr29 BOT_CORP_POLICY "pair" (match check only): seat 1 makes the corp, sets the
        password and hands seat 2 a pass; seat 2 joins with the password from that pass. Deployments then
        take K.CORP_DEPLOY_DEFAULT (corporate). Never transfers, takes, leaves or drops. All verbs 0 turns."""
        from ..engine import constants as engine_k
        from . import corp_brain
        if engine_k.bot_corp_policy() not in ("pair", "team"):
            return None
        if corp_brain.active():
            opening = corp_brain.next_action(self, v)
            return opening if opening is not None else self._corp_support(v)
        me = str(v.self_id or "")
        mine = v.obs.get("corp_ticker")
        if me == PAIR_CEO_ID:
            if not mine:
                taken = set((v.params("corp_create").get("ticker") or {}).get("taken") or ())
                if v.ok("corp_create") and PAIR_TICKER not in taken:
                    return {"kind": "corp_create", "args": {"ticker": PAIR_TICKER, "name": PAIR_CORP_NAME},
                            "thought": "pair policy: make the corp"}
                return None
            corp = v.obs.get("corp") or {}
            if not corp.get("password") and v.ok("corp_set_password"):
                return {"kind": "corp_set_password", "args": {"password": PAIR_PASSWORD},
                        "thought": "pair policy: set the corporate password"}
            member_ids = {str(m.get("id")) for m in (corp.get("members") or []) if isinstance(m, dict)}
            if (not getattr(self, "_pair_invited", False) and PAIR_MATE_ID not in member_ids
                    and v.ok("corp_invite") and PAIR_MATE_ID in v.choices("corp_invite", "target")):
                self._pair_invited = True
                return {"kind": "corp_invite", "args": {"target": PAIR_MATE_ID},
                        "thought": "pair policy: hand my partner a pass"}
            return None
        if me == PAIR_MATE_ID and not mine and v.ok("corp_join"):
            passes = [m for m in (v.obs.get("inbox") or []) if isinstance(m, dict)
                      and m.get("kind") == "corp_invite" and m.get("from") == PAIR_CEO_ID and m.get("password")]
            if passes and str(passes[-1].get("ticker")) in v.choices("corp_join", "ticker"):
                return {"kind": "corp_join", "args": {"ticker": str(passes[-1]["ticker"]),
                                                       "password": str(passes[-1]["password"])},
                        "thought": "pair policy: join with the pass"}
        return None

    def _reserve_on(self) -> bool:
        from ..engine import constants as engine_k
        return engine_k.bots_bank_on() and engine_k.BOT_BANK_POLICY == "reserve"

    def _plan_budget(self, v: View) -> int:
        """Credits the planet target may count. Banking must not shrink it."""
        if not self._reserve_on():
            return int(v.credits)
        from .bank_brain import nest_egg
        balance = int(v.obs.get("bank_balance") or 0)
        return int(v.credits) + balance - nest_egg(v.net_worth)

    def _bank_verb_open(self, v: View, kind: str) -> bool:
        """bb18: eight bank verbs a day, and three StarDock withdraws a visit."""
        if not self._reserve_on() or self.mem is None:
            return True
        from ..engine import constants as engine_k
        mem = self.mem
        used = mem.bank_verbs if mem.bank_verbs_day == int(v.day) else 0
        if used >= int(engine_k.BOT_BANK_MAX_VERBS_PER_DAY):
            return False
        if kind == "bank_withdraw" and mem.bank_withdraws >= int(engine_k.BOT_BANK_MAX_WITHDRAWS_PER_VISIT):
            return False
        return True

    def _take_bank_verb(self, v: View, action: dict[str, Any]) -> dict[str, Any]:
        mem = self.mem
        if self._reserve_on() and mem is not None:
            if mem.bank_verbs_day != int(v.day):
                mem.bank_verbs_day = int(v.day)
                mem.bank_verbs = 0
            mem.bank_verbs += 1
            if action.get("kind") == "bank_withdraw":
                mem.bank_withdraws += 1
        return action

    def _bank_recovery(self, v: View) -> dict[str, Any] | None:
        """At StarDock in a pod, withdraw the replacement hull before the Scout buy."""
        from ..engine import constants as engine_k
        if v.ship_class != "escape_pod" or v.landed is not None:
            return None
        if int(v.here or 0) != int(engine_k.STARDOCK_SECTOR) or not v.ok("bank_withdraw"):
            return None
        if self.mem is not None and self.mem.bank_unspent:
            return None
        balance = int(v.obs.get("bank_balance") or 0)
        need = self._stardock_hull_need(v, balance)
        from .bank_brain import nest_egg, withdraw_amount
        amount = withdraw_amount(
            need, 0, int(v.credits), balance, nest_egg(v.net_worth),
            int(v.params("bank_withdraw").get("max_amount") or 0), recovery=True,
        )
        if amount < 1 or not self._bank_verb_open(v, "bank_withdraw"):
            return None
        if self.mem is not None and self.mem.pending_buy == "hull":
            return None
        if self.mem is not None:
            self.mem.pending_buy = "hull"
        return self._take_bank_verb(v, {"kind": "bank_withdraw", "args": {"amount": amount},
                                        "thought": "withdraw the replacement hull from the nest egg"})

    def _genesis_shortfall(self, v: View) -> tuple[int, bool]:
        """(withdraw amount, buy is already on hand). Zero means genesis is not this visit's buy."""
        if v.here != STARDOCK or v.genesis_aboard > 0 or v.colonists_aboard > 0 or self._hauling_organics(v):
            return 0, False
        if self._cargotran_net(v) is not None and not self._cargotran_affordable(v):
            return 0, False
        have = len(v.genesis_planets())
        if have >= self.target_planets or have >= MAX_TARGET_PLANETS:
            return 0, False
        if have >= 2 and any(int(p.get("citadel_level") or 0) < 2 for p in v.genesis_planets()):
            return 0, False
        if self._no_genesis_hull(v):
            return 0, False
        if not (v.ok("buy_equip") and "genesis" in set(str(c) for c in v.choices("buy_equip", "item"))):
            return 0, False
        price = int((v.params("buy_equip").get("item") or {}).get("unit_price_by", {}).get("genesis")
                    or GENESIS_TORPEDO_COST)
        keep = CITADEL_TIER_COST[0][0] + self.working_capital + self._unfinished_l2_cash(v)
        from .bank_brain import nest_egg, purse, withdraw_amount
        balance = int(v.obs.get("bank_balance") or 0)
        egg = nest_egg(v.net_worth)
        legal = int(v.params("bank_withdraw").get("max_amount") or 0)
        if purse(int(v.credits), balance, egg, legal) - price < keep:
            return 0, False
        if int(v.credits) - price >= keep:
            return 0, True
        amount = withdraw_amount(price, keep, int(v.credits), balance, egg, legal, recovery=False)
        return amount, False

    def _off_dock_planned(self, v: View) -> list[int]:
        planned: list[int] = []
        if v.genesis_aboard and not v.worlds():
            planned.append(CITADEL_TIER_COST[0][0] + self.working_capital)
        elif v.worlds():
            planned.append(max(self._citadel_reserve(v), self._unfinished_l2_cash(v)))
        return planned

    def _threat_hops(self, v: View) -> int | None:
        """0 if a Ferrengi is in this sector, 1 if one is next door. Own sight only."""
        if (v.sector or {}).get("ferrengi"):
            return 0
        for row in v.obs.get("adjacent") or []:
            if isinstance(row, dict) and row.get("ferrengi"):
                return 1
        return None

    def _risk_count(self, v: View) -> int:
        from .bank_brain import risk_flags
        last = v.obs.get("last_death_day")
        days = None if last is None else max(0, int(v.day) - int(last))
        fighters = int(v.ship.get("fighters") or v.ship.get("fighter_count") or 0)
        return risk_flags(
            days_since_loss=days,
            ship_class=str(v.ship_class or ""),
            alignment=int(v.obs.get("alignment") or 0),
            fedsafe=v.obs.get("fedsafe", True) is not False,
            threat_hops=self._threat_hops(v),
            fighters=fighters,
        )

    def _away_cash(self, v: View) -> int:
        from .bank_brain import away_reserve
        planned = self._off_dock_planned(v)
        holds = int(v.ship.get("holds") or 0)
        fighters = int(v.ship.get("fighters") or v.ship.get("fighter_count") or 0)
        return away_reserve(holds, planned, self._risk_count(v), fighters > 0)

    def _reserve_hull_need(self, v: View, spendable_balance: int) -> int:
        """Hull cash, including a CargoTran the legal list hides until the bank is withdrawn."""
        need = self._stardock_hull_need(v, spendable_balance)
        if need > 0:
            return need
        if v.ship_class not in ("merchant_cruiser", "scout_marauder", "escape_pod"):
            return 0
        nets = (v.params("buy_ship").get("ship_class") or {}).get("net_cost_by") or {}
        cost = int(nets.get("cargotran") or 0)
        purse = int(v.credits) + int(spendable_balance)
        if cost > 0 and purse - cost >= self.cash_buffer:
            return cost + self.cash_buffer
        return 0

    def _bank_reserve(self, v: View) -> dict[str, Any] | None:
        """Withdraw the StarDock shortfall, else deposit cash above the away reserve. No genesis hold."""
        from .bank_brain import deposit_amount, nest_egg, tax_keep, withdraw_amount
        mem = self.mem
        balance = int(v.obs.get("bank_balance") or 0)
        egg = nest_egg(v.net_worth)
        need = self._reserve_hull_need(v, max(0, balance - egg))
        if need > int(v.credits) and v.ok("bank_withdraw") and not (mem is not None and mem.bank_unspent):
            amount = withdraw_amount(
                need, 0, int(v.credits), balance, egg,
                int(v.params("bank_withdraw").get("max_amount") or 0), recovery=False,
            )
            if amount >= 1 and self._bank_verb_open(v, "bank_withdraw") and not (
                    mem is not None and mem.pending_buy == "hull"):
                if mem is not None:
                    mem.pending_buy = "hull"
                return self._take_bank_verb(v, {
                    "kind": "bank_withdraw", "args": {"amount": amount},
                    "thought": "withdraw the shortfall for the StarDock buy",
                })
        if need > 0 and int(v.credits) >= need:
            return None
        short, ready = self._genesis_shortfall(v)
        if short >= 1 and self._bank_verb_open(v, "bank_withdraw") and not (
                mem is not None and (mem.pending_buy == "genesis" or mem.bank_unspent)):
            if mem is not None:
                mem.pending_buy = "genesis"
            return self._take_bank_verb(v, {
                "kind": "bank_withdraw", "args": {"amount": short},
                "thought": "withdraw the genesis shortfall",
            })
        if ready:
            return None
        if mem is not None and mem.bank_deposited:
            return None
        if not v.ok("bank_deposit"):
            return None
        planned = self._off_dock_planned(v)
        reserve = tax_keep(
            self._away_cash(v), max(planned) if planned else 0, int(v.obs.get("alignment") or 0),
        )
        gap = max(0, egg - balance)
        if gap:
            from ..engine import constants as engine_k
            reserve = min(reserve, max(int(engine_k.BOT_BANK_MIN_FLOAT), int(v.credits) - gap))
        amount = deposit_amount(
            int(v.credits), reserve,
            int(v.params("bank_deposit").get("max_amount") or 0),
            day1=int(v.day) <= 1,
        )
        if amount < 1 or not self._bank_verb_open(v, "bank_deposit"):
            return None
        if mem is not None:
            mem.bank_deposited = True
            mem.bank_unspent = True
        return self._take_bank_verb(
            v, {"kind": "bank_deposit", "args": {"amount": amount}, "thought": "bank the spare cash"},
        )

    def _citadel_cash_short(self, v: View, planet: dict[str, Any]) -> int:
        """Credits still needed for the next citadel step. Zero when cash is not what blocks it."""
        tier = next_tier(planet)
        if tier is None:
            return 0
        cred, col = tier
        total = _colonists_total(planet)
        if total < col:
            return 0
        if not self._last_days(v):
            if self.citadel_floor_ratio is not None and total - col < int(col * self.citadel_floor_ratio):
                return 0
            if self.citadel_fuel_shield and _pool(planet, "fuel_ore") < col:
                return 0
            if self.citadel_multiday_floor and next_tier_days(planet) > 1 and total - col < col:
                return 0
        return max(0, int(cred) - int(v.credits))

    def _hull_treasury_short(self, v: View) -> int:
        """Hull cash the bank cannot cover. A pod may spend the nest egg; a live hull may not."""
        if v.ship_class not in ("merchant_cruiser", "scout_marauder", "escape_pod"):
            return 0
        from ..engine.constants import net_hull_cost
        from .bank_brain import nest_egg
        need = net_hull_cost(str(v.ship_class), "cargotran") + self.cash_buffer
        balance = int(v.obs.get("bank_balance") or 0)
        spendable = balance if v.ship_class == "escape_pod" else max(0, balance - nest_egg(v.net_worth))
        return max(0, need - int(v.credits) - int(spendable))

    def _treasury_withdraw(self, v: View, planet: dict[str, Any]) -> dict[str, Any] | None:
        citadel = self._citadel_cash_short(v, planet)
        short = citadel or self._hull_treasury_short(v)
        if short < 1 or not v.ok("withdraw_treasury"):
            return None
        choices = v.choices("withdraw_treasury", "planet_id")
        maximum = int((v.params("withdraw_treasury").get("amount") or {}).get("max") or 0)
        amount = min(maximum, short)
        if amount < 1 or not choices or not self._bank_verb_open(v, "withdraw_treasury"):
            return None
        if self.mem is not None:
            self.mem.treasury_planet = int(v.landed)
        why = "the citadel step" if citadel >= 1 else "the hull the bank cannot cover"
        return self._take_bank_verb(v, {
            "kind": "withdraw_treasury", "args": {"planet_id": int(choices[0]), "amount": amount},
            "thought": f"withdraw the shortfall for {why}",
        })

    def _treasury(self, v: View) -> dict[str, Any] | None:
        """bb12: park spare cash in an owned citadel, or withdraw a citadel or hull shortfall."""
        from ..engine import constants as engine_k
        mem = self.mem
        if v.landed is None:
            if mem is not None:
                mem.treasury_planet = None
            return None
        if not self._reserve_on() or engine_k.BOT_TREASURY_POLICY == "off":
            return None
        planet = v.planet(int(v.landed))
        if planet is None or int(planet.get("citadel_level") or 0) < 1:
            return None
        if (v.sector or {}).get("ferrengi"):
            return None
        here = int(v.here or -1)
        rivals_here = [r for r in v.rivals if int(r.get("sector_id") or -2) == here]
        if rivals_here and int(planet.get("shields") or 0) <= 0:
            return None
        if mem is not None and mem.treasury_planet == int(v.landed):
            return None
        withdrawn = self._treasury_withdraw(v, planet)
        if withdrawn is not None:
            return withdrawn
        if engine_k.BOT_TREASURY_POLICY == "overflow" and int(v.obs.get("bank_room") or 0) > 0:
            return None
        if not v.ok("deposit_treasury"):
            return None
        choices = v.choices("deposit_treasury", "planet_id")
        maximum = int((v.params("deposit_treasury").get("amount") or {}).get("max") or 0)
        spare = int(v.credits) - self._away_cash(v)
        amount = min(maximum, spare)
        if amount < 1 or not choices or not self._bank_verb_open(v, "deposit_treasury"):
            return None
        if mem is not None:
            mem.treasury_planet = int(v.landed)
        return self._take_bank_verb(v, {
            "kind": "deposit_treasury", "args": {"planet_id": int(choices[0]), "amount": amount},
            "thought": "park the spare cash in this citadel",
        })

    def _bank(self, v: View) -> dict[str, Any] | None:
        """gb29-gb31: withdraw the exact hull shortfall, else deposit spare once per StarDock visit."""
        from ..engine import constants as engine_k
        mem = self.mem
        at_dock = int(v.here or 0) == int(engine_k.STARDOCK_SECTOR)
        if mem is not None and not at_dock:
            mem.bank_deposited = False
            mem.bank_unspent = False
            mem.bank_withdraws = 0
            mem.pending_buy = None
        if engine_k.BOT_BANK_POLICY == "off" or not engine_k.bank_on() or not at_dock:
            return None
        if self._reserve_on():
            return self._bank_reserve(v)
        balance = int(v.obs.get("bank_balance") or 0)
        need = self._stardock_hull_need(v, balance)
        if need > int(v.credits) and v.ok("bank_withdraw"):
            shortfall = need - int(v.credits)
            maximum = int(v.params("bank_withdraw").get("max_amount") or 0)
            amount = min(maximum, shortfall)
            if amount >= 1:
                return {"kind": "bank_withdraw", "args": {"amount": amount},
                        "thought": "withdraw the shortfall for the StarDock buy"}
        if need > 0 and int(v.credits) >= need:
            return None  # the ladder buys the hull before any deposit
        # Spare cash waits while StarDock will still sell the next torpedo. QC 56 kept this hold: without it
        # an N2 seat banks its colonist money and the empire loop never buys colonists (test_seat_bot_s4,
        # test_class0_terra_qc_v1, test_seat_bot_n2). Ben's call in GALACTIC_BANK_TAX.md QC.
        if (len(v.genesis_planets()) < self.target_planets and v.ok("buy_equip")
                and "genesis" in set(str(c) for c in v.choices("buy_equip", "item"))):
            return None
        if mem is not None and mem.bank_deposited:
            return None
        keep = self._bank_keep(v, need)
        if v.ok("bank_deposit"):
            spare = int(v.credits) - keep
            maximum = int(v.params("bank_deposit").get("max_amount") or 0)
            amount = min(maximum, spare)
            if amount >= 1:
                if mem is not None:
                    mem.bank_deposited = True
                return {"kind": "bank_deposit", "args": {"amount": amount}, "thought": "bank the spare cash"}
        return None

    def _port_upgrade(self, v: View) -> dict[str, Any] | None:
        """pu28: widen a buying port when a held planet's organics or equipment will not fit."""
        from ..engine import constants as engine_k
        if engine_k.BOT_PORT_UPGRADE_POLICY != "planet_room" or not engine_k.port_upgrade_on():
            return None
        if int(engine_k.BOT_PORT_UPGRADE_PAYBACK_DAYS) <= 0 or not v.ok("port_upgrade"):
            return None
        commodities = v.params("port_upgrade").get("commodities") or {}
        seen = ((v.sector.get("port") or {}).get("stock") or {})
        best: tuple[int, str, int] | None = None
        for commodity, row in commodities.items():
            if commodity == "fuel_ore" or not isinstance(row, dict) or row.get("side") != "buys_from_player":
                continue
            slot = seen.get(commodity) or {}
            room = int(slot.get("max") or 0) - int(slot.get("current") or 0)
            bid = int(slot.get("price") or 0)
            holds = max(1, int(row.get("holds_per_unit") or 10))
            unit_cost = int(row.get("unit_cost") or 0)
            legal_max = int(row.get("max_units") or 0)
            if unit_cost <= 0 or legal_max < 1 or bid <= 0:
                continue
            lot = 0
            for planet in v.owned:
                if int(planet.get("sector_id") or -1) != int(v.here or -1):
                    continue
                lot = max(lot, int((planet.get("stockpile") or {}).get(commodity) or 0))
            short = lot - room
            if short <= 0:
                continue
            afford = max(0, (int(v.credits) - int(engine_k.BOT_PORT_UPGRADE_RESERVE)) // unit_cost)
            units = min((short + holds - 1) // holds, legal_max, int(engine_k.BOT_PORT_UPGRADE_MAX_UNITS), afford)
            if units < 1:
                continue
            sold = min(short, units * holds)
            base = int(engine_k.COMMODITY_BASE_PRICE[commodity])
            # pu28: lot * bid * quote% - base. Multiplication binds first, so base comes off once.
            gain = int(bid * sold * int(engine_k.BOT_PLANET_TRADE_QUOTE_PCT) / 100) - base
            cost = units * unit_cost
            if gain <= cost:
                continue
            if best is None or gain - cost > best[0]:
                best = (gain - cost, commodity, units)
        if best is None:
            return self._port_upgrade_starter(v, commodities)
        return self._act("port_upgrade", {"commodity": best[1], "units": int(best[2])},
                         f"upgrade {best[1]} so the planet's lot fits this port")

    def _port_upgrade_starter(self, v: View, commodities: dict[str, Any]) -> dict[str, Any] | None:
        """QC slice 55: the planet_room payback never fires at this scale (planet lots stay far below port room),
        so a rich seat gives the buy port over its own stocked planet one small upgrade, once per port and commodity.
        Bounded: BOT_PORT_UPGRADE_STARTER_UNITS units only while credits >= BOT_PORT_UPGRADE_STARTER_CREDITS."""
        from ..engine import constants as engine_k
        units_cap = int(engine_k.BOT_PORT_UPGRADE_STARTER_UNITS)
        if units_cap <= 0 or int(v.credits) < int(engine_k.BOT_PORT_UPGRADE_STARTER_CREDITS):
            return None
        here = int(v.here or -1)
        planets = [p for p in v.owned if int(p.get("sector_id") or -1) == here]
        for commodity in ("equipment", "organics"):
            row = commodities.get(commodity)
            key = f"{here}:{commodity}"
            if not isinstance(row, dict) or row.get("side") != "buys_from_player" or key in self.mem.port_starters:
                continue
            if not any(int((p.get("stockpile") or {}).get(commodity) or 0) > 0 for p in planets):
                continue
            units = min(units_cap, int(row.get("max_units") or 0), int(engine_k.BOT_PORT_UPGRADE_MAX_UNITS))
            if units < 1:
                continue
            self.mem.port_starters.add(key)
            return self._act("port_upgrade", {"commodity": commodity, "units": units},
                             f"starter upgrade: widen this {commodity} buy port over my planet")
        return None

    def _port_build(self, v: View) -> dict[str, Any] | None:
        """pu29: off unless BOT_PORT_BUILD_POLICY is near_planet."""
        from ..engine import constants as engine_k
        from ..engine.port_build import class_buys
        if engine_k.BOT_PORT_BUILD_POLICY != "near_planet" or not engine_k.port_upgrade_on():
            return None
        if not v.ok("port_build"):
            return None
        params = v.params("port_build")
        classes = params.get("classes") or {}
        best: tuple[int, str, int] | None = None
        for planet in v.owned:
            if int(planet.get("sector_id") or -1) != int(v.here or -1):
                continue
            pile = planet.get("stockpile") or {}
            product = max(("organics", "equipment", "fuel_ore"), key=lambda c: int(pile.get(c) or 0))
            if int(pile.get(product) or 0) <= 0:
                continue
            for code, row in classes.items():
                if not isinstance(row, dict) or product not in class_buys(code):
                    continue
                price = int(row.get("cost") or 0)
                if price <= 0 or int(v.credits) <= price * 4 or not row.get("affordable"):
                    continue
                if best is None or price < best[0]:
                    best = (price, code, int(planet["id"]))
        if best is None:
            return None
        return self._act("port_build", {"port_class": best[1], "planet_id": best[2]},
                         f"order a class {best[1]} port under this planet")

    def _planet_trade(self, v: View) -> dict[str, Any] | None:
        """planetary-trading-v1 (BOT_PLANET_TRADE_POLICY sell_surplus): docked at a port with an own / corp planet in
        the sector, sell an organics or equipment lot of BOT_PLANET_TRADE_MIN_LOT+ units at the port's quote. Never
        a counter (no wasted-haggle turn), never fuel ore (PTW "Don't sell fuel ore"); organics keep the colony's
        feed reserve (the same reserve as the stockpile haul)."""
        from ..engine import constants as engine_k
        if engine_k.BOT_PLANET_TRADE_POLICY != "sell_surplus" or not engine_k.planet_trade_on():
            return None
        if not v.ok("planet_trade"):
            return None
        params = v.params("planet_trade")
        min_lot = max(1, int(engine_k.BOT_PLANET_TRADE_MIN_LOT))
        if int(params.get("turn_cost", 1) or 0) == 0:
            # bots-use-planet-trade-v1: the port visit is already paid (pt9), so a small lot costs no turn.
            min_lot = min(min_lot, max(1, int(engine_k.BOT_PLANET_TRADE_FREE_LOT)))
        best: tuple[int, int, str, int] | None = None
        for row in (params.get("planets") or []):
            if not isinstance(row, dict) or row.get("planet_id") is None:
                continue
            pid = int(row["planet_id"])
            planet = v.planet(pid)
            for commodity, mx in sorted((row.get("sellable") or {}).items()):
                if commodity == "fuel_ore" and engine_k.BOT_PLANET_TRADE_KEEP_ORE:
                    continue
                qty = int(mx or 0)
                if commodity == "organics":
                    g = (growth_view(planet) or {}) if planet else {}
                    burn = max(1, int(g.get("organics_consumption_per_day") or 1))
                    keep = max(ORGANICS_LOAD, burn * 4)
                    stock = int(((planet or {}).get("stockpile") or {}).get("organics") or 0) if planet else qty + keep
                    qty = min(qty, max(0, stock - keep))
                if qty < min_lot:
                    continue
                unit = int((row.get("unit_bid") or {}).get(commodity) or 0)
                if best is None or unit * qty > best[0]:
                    best = (unit * qty, pid, commodity, qty)
        if best is None:
            return None
        _value, pid, commodity, qty = best
        return self._act("planet_trade", {"planet_id": pid, "commodity": commodity, "qty": int(qty)},
                         f"Planetary Trade Agreement: sell {qty} {commodity} from planet {pid} to this port at its quote")

    # ---- bots-use-planet-trade-v1 -------------------------------------------------------------------------------
    @staticmethod
    def _pt_bot_on() -> bool:
        from ..engine import constants as engine_k
        return engine_k.BOT_PLANET_TRADE_POLICY == "sell_surplus" and engine_k.planet_trade_on()

    def _port_info(self, v: View, sid: int) -> dict[str, Any] | None:
        """The port this seat knows at `sid` (the live sector block here, else known_ports). StarDock never."""
        if sid == STARDOCK:
            return None
        if v.here is not None and int(v.here) == int(sid):
            port = v.sector.get("port")
            return port if isinstance(port, dict) else None
        for kp in v.obs.get("known_ports") or []:
            if isinstance(kp, dict) and kp.get("sector_id") is not None and int(kp["sector_id"]) == int(sid):
                return kp
        return None

    def _port_buys(self, v: View, sid: int, commodity: str) -> bool:
        port = self._port_info(v, sid)
        if not port:
            return False
        cls = port.get("class_id", port.get("class"))
        if cls in (0, 8, "0", "8"):
            return False
        st = (port.get("stock") or {}).get(commodity)
        if isinstance(st, dict) and st.get("side"):
            return st.get("side") == "buys_from_player"
        return commodity in (port.get("buys") or [])

    def _pt_held(self, v: View, planet: dict[str, Any], commodity: str) -> bool:
        """A world under a port that buys `commodity`: keep that stock for planet_trade (no ship haul)."""
        from ..engine import constants as engine_k
        if not (self._pt_bot_on() and engine_k.BOT_PLANET_TRADE_HOLD):
            return False
        if commodity == "fuel_ore" and engine_k.BOT_PLANET_TRADE_KEEP_ORE:
            return False
        if commodity not in ("organics", "equipment", "fuel_ore"):
            return False
        return self._port_buys(v, int(planet["sector_id"]), commodity)

    def _pt_sellable(self, planet: dict[str, Any], commodity: str) -> int:
        stock = planet.get("stockpile") or {}
        qty = int(stock.get(commodity) or 0) if isinstance(stock, dict) else 0
        if commodity == "organics":
            g = growth_view(planet) or {}
            burn = max(1, int(g.get("organics_consumption_per_day") or 1))
            qty = max(0, qty - max(ORGANICS_LOAD, burn * 4))
        return qty

    def _opt_planet_sell(self, v: View):
        """Value per turn of flying to a world under a buying port to sell its kept lot with planet_trade."""
        from ..engine import constants as engine_k
        if not self._pt_bot_on() or not engine_k.BOT_PLANET_TRADE_HOLD:
            return None
        if v.landed is not None or v.colonists_aboard or self._hauling_organics(v) or v.genesis_aboard:
            return None
        min_lot = max(1, int(engine_k.BOT_PLANET_TRADE_MIN_LOT))
        best: tuple[float, dict[str, Any], Intent] | None = None
        for planet in v.worlds():
            sid = int(planet["sector_id"])
            if v.here is not None and sid == int(v.here):
                continue  # here: the pre-ladder planet_trade sells it (or the port has no room today)
            port = self._port_info(v, sid) or {}
            gain = 0
            for commodity in ("organics", "equipment"):
                if not self._pt_held(v, planet, commodity):
                    continue
                qty = self._pt_sellable(planet, commodity)
                st = (port.get("stock") or {}).get(commodity) or {}
                if isinstance(st, dict) and st.get("max") is not None:
                    qty = min(qty, max(0, int(st["max"]) - int(st.get("current") or 0)))
                if qty < min_lot:
                    continue
                base = COMMODITY_BASE_PRICE.get(commodity, 0)
                price = st.get("price") if isinstance(st, dict) and isinstance(st.get("price"), int) else base
                gain += int(price * qty * engine_k.BOT_PLANET_TRADE_QUOTE_PCT / 100) - base * qty
            if gain <= 0:
                continue
            hops = self._hops(v, v.here, sid)
            if hops is None:
                continue
            vpt = gain / max(1, hops * self._tpw(v) + 1)
            if best is not None and vpt <= best[0]:
                continue
            plot = self._plot(v, sid, f"planet trade: sell planet {planet['id']}'s kept stock to the port there")
            if plot is not None:
                best = (vpt, plot, Intent("trade", sid))
        return best

    def _pt_genesis_detour(self, v: View) -> dict[str, Any] | None:
        """Steer a genesis torpedo a few known hops so the new world sits under a port that buys organics or
        equipment (a TW2002 "blue" sells its planet's goods there with the Planetary Trade Agreement)."""
        from ..engine import constants as engine_k
        hops_cap = int(engine_k.BOT_PLANET_TRADE_GENESIS_HOPS)
        if not self._pt_bot_on() or hops_cap <= 0 or v.here is None:
            return None
        here = int(v.here)
        if self._port_buys(v, here, "equipment") or self._port_buys(v, here, "organics"):
            return None
        if self.mem.pt_detour > hops_cap:
            return None
        best: tuple[int, int] | None = None
        for kp in v.obs.get("known_ports") or []:
            if not isinstance(kp, dict) or kp.get("sector_id") is None:
                continue
            sid = int(kp["sector_id"])
            if sid == here or sid in engine_k.FEDSPACE_SECTORS:
                continue
            if not (self._port_buys(v, sid, "equipment") or self._port_buys(v, sid, "organics")):
                continue
            hops = self._hops(v, here, sid)
            if hops is None or hops > hops_cap:
                continue
            if best is None or (hops, sid) < best:
                best = (hops, sid)
        if best is None:
            return None
        plot = self._plot(v, best[1], f"carry genesis to {best[1]}: its port buys planet goods (planet trade)")
        if plot is None:
            return None
        self.mem.pt_detour += 1
        return plot

    def _board_spare(self, v: View) -> dict[str, Any] | None:
        """ship-fleet-transporter-v1 (BOT_FLEET_POLICY spare_only): after a pod / Ship Destroyed, beam into an
        own parked hull in transporter range that beats the hull we are in. A captured hull is just another
        parked ship. Never buys, sells or attacks."""
        from ..engine import constants as engine_k
        if engine_k.BOT_FLEET_POLICY != "spare_only" or not v.ok("ship_transport"):
            return None
        if v.ship_class not in ("escape_pod", "scout_marauder"):
            return None
        if v.ship_class == "scout_marauder" and int(v.obs.get("deaths") or 0) <= 0:
            return None
        here_value = ship_cost(v.ship_class) if v.ship_class != "escape_pod" else 0
        choices = {int(c) for c in v.choices("ship_transport", "ship_id")}
        best = None
        for s in ((v.obs.get("fleet") or {}).get("ships") or []):
            sid = int(s.get("ship_id") or 0)
            hull = str(s.get("hull") or "")
            if sid not in choices or hull == "escape_pod" or hull not in ship_specs():
                continue
            value = ship_cost(hull)
            if value > here_value and (best is None or (value, -sid) > (best[0], -best[1])):
                best = (value, sid, hull)
        if best is None:
            return None
        return self._act("ship_transport", {"ship_id": best[1]},
                         f"beam into my parked {best[2]} (ship {best[1]}) instead of flying a {v.ship_class}")

    def _buy_transwarp_drive(self, v: View) -> dict[str, Any] | None:
        """Type 1 drive at StarDock on an ISS / FlagShip / Havoc only, and only out of spare cash."""
        if v.here != STARDOCK or not v.ok("buy_equip"):
            return None
        if "transwarp_drive" not in {str(x) for x in v.choices("buy_equip", "item")}:
            return None  # the engine lists it only for a TW hull without a drive (legacy: never)
        price = int(((v.params("buy_equip").get("item") or {}).get("unit_price_by") or {}).get("transwarp_drive") or 0)
        if price <= 0 or v.credits - price < max(self.working_capital, SHIP_TW_SPARE_CASH):
            return None
        return self._act("buy_equip", {"item": "transwarp_drive", "qty": 1},
                         f"fit a Type 1 TransWarp drive ({price} cr) from spare cash")

    def _police_hq(self, v: View) -> dict[str, Any] | None:
        """fedspace-police-v1: free Police HQ wins in sector 1 - claim a bounty, take the commission."""
        if v.ok("claim_reward"):
            return self._act("claim_reward", {}, "claim the Federation bounty for a kill")
        if v.ok("apply_commission"):
            return self._act("apply_commission", {}, "apply for the Federal Commission (alignment to 1000)")
        return None


    def _buy_defense(self, v: View) -> dict[str, Any] | None:
        """Buy shields then fighters at StarDock or a known Class 0 when cash is high."""
        if not (self.feed_organics or self.value_allocator):
            return None
        if not self._at_equip_port(v) or not v.ok("buy_equip"):
            return None
        if v.credits < DEFENSE_CASH_GATE:
            return None
        # N2 solo ladder (no Ferrengi) should not drain the bank on shields.
        if not self._fogged_hot():
            return None
        items = set(str(x) for x in v.choices("buy_equip", "item"))
        prices = (v.params("buy_equip").get("item") or {}).get("unit_price_by") or {}
        # Shields first: cheap HP buffer against Ferrengi.
        if "shields" in items and self._ship_shields(v) < DEFENSE_SHIELDS_FLOOR:
            unit = int(prices.get("shields") or SHIELD_VALUE)
            room = v.max_by("buy_equip", "qty", "shields")
            need = max(0, DEFENSE_SHIELDS_FLOOR - self._ship_shields(v))
            afford = max(0, (v.credits - self.cash_buffer) // max(1, unit))
            qty = min(room, need if need else room, afford, 200)
            if qty > 0:
                return self._act("buy_equip", {"item": "shields", "qty": int(qty)},
                                 f"buy {qty} shields before carrying cash")
        if "fighters" in items and self._ship_fighters(v) < DEFENSE_FIGHTERS_FLOOR:
            unit = int(prices.get("fighters") or fighter_unit_price(int(v.day) or 1))
            room = v.max_by("buy_equip", "qty", "fighters")
            need = max(0, DEFENSE_FIGHTERS_FLOOR - self._ship_fighters(v))
            afford = max(0, (v.credits - self.cash_buffer) // max(1, unit))
            qty = min(room, need if need else min(room, 300), afford, 400)
            # fedspace-police-v1: late in the day, do not buy past the Extern arms limit in FedSpace
            hint = v.obs.get("fedspace") if isinstance(v.obs, dict) else None
            if isinstance(hint, dict) and self._fed_turns_short(v, self._fed_exit_plan(v)[1]):
                room_under = max(0, int(hint.get("tow_fighter_limit") or 98) - int(self._ship_fighters(v)))
                qty = min(qty, room_under)
            if qty > 0:
                return self._act("buy_equip", {"item": "fighters", "qty": int(qty)},
                                 f"buy {qty} fighters before carrying cash")
        # When already at the floor but still rich, top up toward the fogged cap.
        if v.credits >= RICH_CREDITS:
            for item, floor in (("shields", DEFENSE_SHIELDS_FLOOR), ("fighters", DEFENSE_FIGHTERS_FLOOR)):
                if item not in items:
                    continue
                have = self._ship_shields(v) if item == "shields" else self._ship_fighters(v)
                room = v.max_by("buy_equip", "qty", item)
                if room <= 0 or have >= floor * 2:
                    continue
                unit = int(prices.get(item) or (SHIELD_VALUE if item == "shields" else fighter_unit_price(int(v.day) or 1)))
                afford = max(0, (v.credits - RICH_CREDITS // 2) // max(1, unit))
                qty = min(room, afford, 200)
                if qty > 0:
                    return self._act("buy_equip", {"item": item, "qty": int(qty)},
                                     f"top up {qty} {item} while rich")
        return self._hunt_arm(v, items, prices)

    def _hunt_arm(self, v: View, items: set[str], prices: dict[str, Any], *, mark: bool = True) -> dict[str, Any] | None:
        """HUNT_MODE tw2002, N3 only: arm a hunting hull so _hunt has something it clearly beats.

        Runs only where _buy_defense would buy nothing (so legacy is untouched): on a hull with
        offensive odds >= HUNT_ARM_MIN_ODDS that can send HUNT_ARM_FIGHTERS in one attack, with
        credits >= HUNT_ARM_CASH_GATE, buy toward HUNT_ARM_FIGHTERS: one buy a game day, at most
        HUNT_ARM_SPEND_SHARE of the cash above working capital and never below the gate, so the
        seat keeps trading.
        """
        import tw2k.engine.constants as _HK
        if not self.value_allocator or not _HK.hunt_on() or "fighters" not in items:
            return None
        odds, per_attack = combat_hull(str(v.ship_class or ""))
        target = int(_HK.HUNT_ARM_FIGHTERS)
        if odds < float(_HK.HUNT_ARM_MIN_ODDS) or per_attack < target:
            return None
        have = self._ship_fighters(v)
        if have >= target or v.credits < int(_HK.HUNT_ARM_CASH_GATE):
            return None
        if getattr(self, "_hunt_arm_day", None) == v.day:
            return None  # one arming buy a day: the rest of the cash keeps trading
        unit = int(prices.get("fighters") or fighter_unit_price(int(v.day) or 1))
        spare = v.credits - max(int(self.working_capital), int(self.cash_buffer))
        budget = int(max(0, spare) * float(_HK.HUNT_ARM_SPEND_SHARE))
        budget = min(budget, v.credits - int(_HK.HUNT_ARM_CASH_GATE))  # never below the gate
        qty = min(v.max_by("buy_equip", "qty", "fighters"), target - have, budget // max(1, unit))
        hint = v.obs.get("fedspace") if isinstance(v.obs, dict) else None
        if isinstance(hint, dict) and self._fed_turns_short(v, self._fed_exit_plan(v)[1]):
            qty = min(qty, max(0, int(hint.get("tow_fighter_limit") or 98) - int(have)))
        if qty < int(_HK.HUNT_ARM_MIN_BUY):
            return None
        if mark:
            self._hunt_arm_day = v.day
        return self._act("buy_equip", {"item": "fighters", "qty": int(qty)},
                         f"arm for hunting: {qty} fighters toward {target} ({unit} cr each)")

    def _buy_combat_hull(self, v: View) -> dict[str, Any] | None:
        if not self._fogged_hot():
            return None
        if v.here != STARDOCK or not v.ok("buy_ship") or v.credits < RICH_CREDITS:
            return None
        if v.ship_class in ("merchant_cruiser", "scout_marauder"):
            return None  # CargoTran first
        choice = self._best_combat_hull(v)
        if choice is None:
            return None
        hull, net = choice
        if v.credits - net < self.working_capital:
            return None
        return self._act("buy_ship", {"ship_class": hull}, f"upgrade to {hull} ({net} cr net) for defence")

    def _best_combat_hull(self, v: View) -> tuple[str, int] | None:
        """Pick the best affordable combat hull from the fogged buy_ship list."""
        if not v.ok("buy_ship"):
            return None
        choices = set(str(c) for c in v.choices("buy_ship", "ship_class"))
        nets = (v.params("buy_ship").get("ship_class") or {}).get("net_cost_by") or {}
        cur = ship_specs().get(v.ship_class or "") or {}
        cur_f = int(cur.get("max_fighters") or 0)
        best: tuple[int, int, int, int, str] | None = None  # fighters, holds, pref, -net, hull
        for i, hull in enumerate(COMBAT_HULLS):
            if hull not in choices or hull == v.ship_class:
                continue
            net = int(nets.get(hull) or 10**12)
            if v.credits - net < self.working_capital:
                continue
            spec = ship_specs().get(hull) or {}
            fighters = int(spec.get("max_fighters") or 0)
            if fighters <= cur_f:
                continue
            # Never trade away cargo capacity: havoc (50) is worse than cargotran (75).
            new_holds = int(spec.get("holds") or 0)
            cur_holds = int(cur.get("holds") or 0)
            if new_holds < cur_holds:
                continue
            # SLOW_HULL_HINT_MODE: a hull with more turns per warp than the current one costs trade
            # warps every day (BattleShip 4/warp); a defence upgrade must not slow the route.
            if slow_hull_hint_on() and int(spec.get("turns_per_warp") or 0) > int(cur.get("turns_per_warp") or 99):
                continue
            row = (fighters, new_holds, -i, -net, hull)
            if best is None or row[:4] > best[:4]:
                best = row
        if best is None:
            return None
        return best[4], -best[3]

    def _combat_hull_option(self, v: View):
        if not self._fogged_hot():
            return None
        choice = self._best_combat_hull(v)
        if choice is None or v.credits < RICH_CREDITS:
            return None
        hull, net = choice
        turns = self._hops_to_stardock(v) * self._tpw(v) + 1
        # Defence value: surviving a Ferrengi hit saves ~25% of credits once.
        value = min(v.credits * 0.25, 500_000)
        if v.here == STARDOCK and v.ok("buy_ship") and hull in v.choices("buy_ship", "ship_class"):
            action = self._act("buy_ship", {"ship_class": hull}, f"upgrade to {hull} ({net} cr net) for defence")
        else:
            action = self._plot(v, STARDOCK, f"{hull} affordable - StarDock for a tougher hull")
            if action is None:
                return None
        return value / max(1, turns), action, Intent("acquire", STARDOCK)

    def _opt_defense(self, v: View):
        # Never divert a trade day to StarDock for fighters until cash clears the
        # defence gate AND Ferrengi have been fogged. A RICH-only bypass was
        # still plotting to StarDock in solo N3 (no hot_sectors), wasting turns
        # then buying nothing (_buy_defense also requires hot_sectors).
        # When already at the fighter/shield floor, do not leave a trade route
        # for a top-up: _buy_defense may no-op once have >= floor*2, and even a
        # top-up is not worth a StarDock divert. Top-ups happen when the seat is
        # already docked (_at_stardock).
        if v.credits < DEFENSE_CASH_GATE:
            return None
        if not self._fogged_hot():
            return None
        if not self._under_defended(v):
            return None
        dock = self._nearest_equip_port(v)
        hops = self._hops(v, v.here, dock)
        turns = (hops if hops is not None else self._hops_to_stardock(v)) * self._tpw(v) + 1
        value = min(v.credits * 0.2, 250_000) if self._under_defended(v) else 20_000
        if self._at_equip_port(v):
            action = self._buy_defense(v)
            if action is None:
                return None
        else:
            action = self._plot(v, dock, "buy defence before travelling with cash")
            if action is None:
                return None
        return value / max(1, turns), action, Intent("acquire", dock)


    def _opt_hunt_arm(self, v: View):
        """HUNT_MODE tw2002, N3 options path: the arming buy when already docked (never a divert).

        _opt_defense stays silent once the 200-fighter floor is met, so a docked BattleShip never
        armed (seed 20260925: P1/P2 flew BattleShips with 200 fighters from day 7-8).
        """
        import tw2k.engine.constants as _HK
        if not _HK.hunt_on() or not self.value_allocator or not self._at_equip_port(v) or not v.ok("buy_equip"):
            return None
        if not self._fogged_hot():
            return None
        items = {str(x) for x in v.choices("buy_equip", "item")}
        prices = (v.params("buy_equip").get("item") or {}).get("unit_price_by") or {}
        action = self._hunt_arm(v, items, prices, mark=False)
        if action is None:
            return None
        return float(_HK.HUNT_ARM_OPTION_VALUE), action, Intent("acquire", v.here)

    def _fitted_scanner(self, v: View) -> str | None:
        return v.scanner or (v.ship.get("scanner") if isinstance(v.ship, dict) else None)

    def _scanner_item_choice(self, v: View) -> tuple[str, int] | None:
        """Scanner at StarDock: holo when the hull allows and cash covers it; else density."""
        if not info_tw2002() or v.here != STARDOCK or not v.ok("buy_equip"):
            return None
        items = set(str(x) for x in v.choices("buy_equip", "item"))
        prices = (v.params("buy_equip").get("item") or {}).get("unit_price_by") or {}
        room = scanner_room(str(v.ship_class or ""))
        fitted = self._fitted_scanner(v)
        if room is None:
            return None
        # Expert habit (SCANNERS_HIDDEN_INFO): holo where the hull allows, density otherwise.
        # Fall back to density when holo is unaffordable so day-1 never leaves blind.
        if room == SCANNER_HOLO and "holo_scanner" in items and fitted != SCANNER_HOLO:
            unit = int(prices.get("holo_scanner") or HOLO_SCANNER_COST)
            # Holo (first or density->holo) always keeps working_capital — a 25k buy
            # on a thin buffer starves the CargoTran/genesis ladder (N2 day-10 bar).
            keep = self.working_capital
            if v.credits >= unit + keep:
                return "holo_scanner", unit
        if fitted is None and "density_scanner" in items:
            unit = int(prices.get("density_scanner") or DENSITY_SCANNER_COST)
            return "density_scanner", unit
        if room == SCANNER_DENSITY and fitted is None and "density_scanner" in items:
            unit = int(prices.get("density_scanner") or DENSITY_SCANNER_COST)
            return "density_scanner", unit
        return None


    def _hardware_on(self) -> bool:
        import tw2k.engine.constants as _HK
        return bool(_HK.hardware_tw2002())

    def _in_swept_lane(self, v: View) -> bool:
        """FedSpace or a Major Space Lane. Mines and parked fighters are swept or towed."""
        sector = v.sector or {}
        if sector.get("is_fedspace") or sector.get("is_msl"):
            return True
        return int(v.here or 0) == STARDOCK

    def _navhaz_pct(self, v: View, sector_id: int) -> int:
        for adj in v.obs.get("adjacent") or []:
            if not isinstance(adj, dict):
                continue
            try:
                if int(adj.get("id")) != int(sector_id):
                    continue
            except (TypeError, ValueError):
                continue
            raw = adj.get("navhaz", adj.get("nav_hazard_pct"))
            try:
                return int(raw or 0)
            except (TypeError, ValueError):
                return 0
        here = (v.sector or {}).get("nav_hazard_pct")
        if v.here is not None and int(sector_id) == int(v.here) and here is not None:
            try:
                return int(here)
            except (TypeError, ValueError):
                return 0
        return 0

    def _note_psychic(self, v: View) -> None:
        if self.mem is None:
            return
        self._psychic_aboard = int(v.ship.get("psychic_probe") or 0)
        for e in v.events:
            if e.get("kind") != "psychic_probe":
                continue
            facts = e.get("facts") or {}
            if facts.get("pct") is None:
                continue
            try:
                self.mem.psychic_pct = float(facts["pct"])
            except (TypeError, ValueError):
                continue
            if isinstance(facts.get("commodity"), str):
                self.mem.psychic_commodity = facts["commodity"]
            if isinstance(facts.get("unit"), int):
                self.mem.psychic_unit = int(facts["unit"])

    def _haggle_from_memory(self, args: dict[str, Any]) -> dict[str, Any]:
        """One small step toward the price the psychic probe said was better.

        No probe, no reading, or a reading already near the best: the trade
        args are unchanged, so a seat that never bought the probe haggles
        exactly as before.
        """
        mem = self.mem
        if mem is None or mem.psychic_pct is None:
            return args
        if int(getattr(self, "_psychic_aboard", 0) or 0) <= 0:
            return args
        if args.get("unit_price") is not None:
            return args
        if str(args.get("side") or "") != "sell":
            return args
        if str(args.get("commodity") or "") != str(mem.psychic_commodity or ""):
            return args
        try:
            pct = float(mem.psychic_pct)
            unit = int(mem.psychic_unit or 0)
        except (TypeError, ValueError):
            return args
        if unit <= 0 or pct >= 95 or pct <= 0:
            return args
        step = max(1, unit // 50)
        offer = min(int(unit * 100 / pct), unit + step)
        if offer <= unit:
            return args
        out = dict(args)
        out["unit_price"] = int(offer)
        return out

    def _haggle_live(self, v: View, args: dict[str, Any]) -> dict[str, Any]:
        """QC: the probe reading now steers real sells (spec p10; it was bought, never used).

        Base is this port's listed bid, not the last port's price. The ask is
        capped at 109% of it: every port's hidden counter room is at least 110%
        of the listed bid (PORT_HAGGLE_MIN_PCT), so this haggle never makes a
        port lose patience. A reading near the best (>= 95%) asks nothing extra.
        """
        if not self._hardware_on() or str(args.get("side") or "") != "sell" or args.get("unit_price") is not None:
            return args
        mem = self.mem
        if mem is None or mem.psychic_pct is None or int(getattr(self, "_psychic_aboard", 0) or 0) <= 0:
            return args
        port = (v.sector or {}).get("port") or {}
        st = ((port.get("stock") or {}) if isinstance(port, dict) else {}).get(str(args.get("commodity") or "")) or {}
        if st.get("side") != "buys_from_player":
            return args
        try:
            listed = int(st.get("price") or 0)
            pct = float(mem.psychic_pct)
        except (TypeError, ValueError):
            return args
        if listed < 50 or pct >= 95 or pct <= 0:
            return args
        offer = min(int(listed * 100 / pct), listed * 109 // 100)
        if offer <= listed:
            return args
        out = dict(args)
        out["unit_price"] = int(offer)
        return out

    def _haggle_unit(self, args: dict[str, Any], listed: int) -> dict[str, Any]:
        """Test seam: remember `listed` as the last psychic unit, then haggle."""
        if self.mem is not None and self.mem.psychic_unit is None:
            self.mem.psychic_unit = int(listed)
        return self._haggle_from_memory(args)

    def _crime_action(self, v: View) -> dict[str, Any] | None:
        """Rob or steal only when the original gates are already true.

        Alignment must be at or under ROB_MIN_ALIGNMENT. StarDock, Class 0,
        a bust, and a second try in the same sector are refused. The amount
        is the safe experience cap, never the whole vault.
        """
        import tw2k.engine.constants as _K
        from tw2k.engine.rob_steal import max_rob_credits, max_steal_holds
        if not _K.rob_tw2002():
            return None
        try:
            align = int(v.obs.get("alignment") or 0)
        except (TypeError, ValueError):
            align = 0
        if align > int(_K.ROB_MIN_ALIGNMENT):
            return None
        sector = v.sector or {}
        port = sector.get("port") or {}
        if not isinstance(port, dict):
            port = {}
        cls = str(port.get("class") or "")
        if int(v.here or 0) == STARDOCK or sector.get("class0_port") or cls in ("0", "stardock"):
            return None
        if self.mem is not None and self.mem.last_crime_sector is not None and v.here is not None:
            if int(self.mem.last_crime_sector) == int(v.here):
                return None
        if "busted" in v.reason("rob").lower() or "busted" in v.reason("steal").lower():
            return None
        try:
            exp = int(v.obs.get("experience") or 0)
        except (TypeError, ValueError):
            exp = 0
        holds_full = v.cargo_free <= 0
        knows_buyer = bool(self.mem and self.mem.ports_seen)
        if (not holds_full) and knows_buyer and v.ok("steal"):
            choices = [str(c) for c in v.choices("steal", "commodity")]
            if not choices:
                return None
            commodity = choices[0]
            room = v.max_by("steal", "qty", commodity)
            qty = min(room, max_steal_holds(exp), v.cargo_free)
            if qty <= 0:
                return None
            if self.mem is not None and v.here is not None:
                self.mem.last_crime_sector = int(v.here)
            return self._act("steal", {"commodity": commodity, "qty": int(qty)},
                             f"steal {qty} {commodity} inside the experience cap")
        if holds_full and v.ok("rob"):
            legal_max = int((v.params("rob").get("amount") or {}).get("max") or 0)
            amount = min(legal_max, max_rob_credits(exp))
            if amount <= 0:
                return None
            if self.mem is not None and v.here is not None:
                self.mem.last_crime_sector = int(v.here)
            return self._act("rob", {"amount": int(amount)},
                             f"rob {amount} cr inside the experience cap")
        return None

    def _is_fed_target(self, v: View, target: str) -> bool:
        name = str(target or "").lower()
        if any(tok in name for tok in ("zyrain", "nelson", "clausewitz", "federal")):
            return True
        for occ in (v.sector or {}).get("occupants") or []:
            if not isinstance(occ, dict):
                continue
            label = str(occ.get("name") or occ.get("id") or "")
            if label != str(target) and str(occ.get("id") or "") != str(target):
                continue
            if occ.get("federal") or occ.get("is_fed") or "federal" in str(occ.get("ship") or "").lower():
                return True
        return False

    def _hunt(self, v: View) -> dict[str, Any] | None:
        """HUNT_MODE tw2002, N3 only: attack a Ferrengi or trader in this sector that it clearly beats.

        One attack is deterministic (power = qty x hull odds; the target dies when power >= (shields +
        fighters) x its odds), so "clearly" is HUNT_STRENGTH_MARGIN over the worst case the seat can see:
        a Ferrengi shows fighters, shields and hull; a trader shows fighters and hull, so its hull's
        max shields are assumed. A kill must not take the seat below HUNT_ALIGN_FLOOR alignment.
        Ferrengi first (the one hailing us, then the biggest bounty), then traders. FULLGAME_FIXES_V2.md.
        """
        import math

        import tw2k.engine.constants as _HK
        if not self.value_allocator or not _HK.hunt_on():
            return None
        sector = v.sector or {}
        if sector.get("is_fedspace") or v.landed is not None or v.ship_class == "escape_pod":
            return None
        if not v.ok("attack"):
            return None
        tparams = v.params("attack").get("target") or {}
        choices = {str(c) for c in tparams.get("choices") or []}
        players = {str(c) for c in tparams.get("players") or []}
        cap = int((v.params("attack").get("qty") or {}).get("max") or 0)
        if cap <= 0 or not choices:
            return None
        my_odds = combat_hull(str(v.ship_class or ""))[0]
        power = cap * my_odds
        margin = float(_HK.HUNT_STRENGTH_MARGIN)
        tally = getattr(self, "_hunt_tally", None)
        if tally is None or tally.get("day") != v.day:
            tally = self._hunt_tally = {"day": v.day}

        def fresh(tid: str) -> bool:
            return int(tally.get(tid, 0)) < int(_HK.HUNT_MAX_ATTACKS_PER_TARGET_DAY)

        enc = v.obs.get("ferrengi_encounter") or {}
        best: tuple[tuple, str, str] | None = None
        for f in sector.get("ferrengi") or []:
            if not isinstance(f, dict):
                continue
            fid = str(f.get("id") or "")
            if fid not in choices or not fresh(fid):
                continue
            defense = (int(f.get("fighters") or 0) + int(f.get("shields") or 0)) * _HK.ferrengi_odds_for_hull(f.get("hull"))
            if power < margin * defense:
                continue
            agg = int(f.get("aggression") or 0)
            key = (0, 0 if str(enc.get("ferr_id") or "") == fid else 1, -agg, fid)
            why = (f"hunt Ferrengi {f.get('name') or fid} (aggression {agg}): power {power:.0f} vs defence "
                   f"{defense:.0f} - bounty {agg * _HK.FERRENGI_BOUNTY_PER_AGG} cr")
            if best is None or key < best[0]:
                best = (key, fid, why)
        if best is None:
            from . import corp_brain
            mates = corp_brain.friends(v)
            sides = {str(r.get("id")): r.get("side") for r in v.rivals}
            my_align = int(v.obs.get("alignment") or 0)
            specs = ship_specs()
            for t in sector.get("traders") or []:
                if not isinstance(t, dict):
                    continue
                tid = str(t.get("id") or "")
                hull = str(t.get("ship_class") or "")
                if tid in mates or tid not in players or not fresh(tid) or hull == "escape_pod" or self._is_fed_target(v, tid):
                    continue
                scanned = t.get("shields") is not None
                if scanned:  # Combat Scanner hull (COMBAT_SCANNER_MODE)
                    worst_shields = int(t.get("shields") or 0)
                else:
                    worst_shields = int((specs.get(hull) or {}).get("max_shields") or 0)
                defense = (int(t.get("fighters") or 0) + worst_shields) * combat_hull(hull)[0]
                if power < margin * defense:
                    continue
                losses = math.ceil(defense / my_odds) if my_odds > 0 else cap
                cost = _HK.hunt_alignment_cost(my_align, losses, sides.get(tid))
                if my_align - cost < int(_HK.HUNT_ALIGN_FLOOR):
                    continue
                key = (1, 0, -int(defense), tid)
                why = (f"hunt {t.get('name') or tid} in a {hull}: power {power:.0f} vs {'scanned' if scanned else 'worst-case'} defence "
                       f"{defense:.0f}, alignment cost ~{cost}")
                if best is None or key < best[0]:
                    best = (key, tid, why)
        if best is None and str(getattr(_HK, "BOT_ALIEN_POLICY", "ignore")) == "align_hunt":
            if int(tally.get("__alien__", 0)) < 1 and not sector.get("is_fedspace"):
                my_side = "good" if int(v.obs.get("alignment") or 0) >= 0 else "evil"
                alien_margin = float(_HK.BOT_ALIEN_MARGIN)
                for row in sector.get("aliens") or []:
                    if not isinstance(row, dict):
                        continue
                    aid = str(row.get("id") or "")
                    if aid not in choices or str(row.get("side") or "") == my_side:
                        continue
                    hull = str(row.get("hull") or "")
                    defense = (int(row.get("fighters") or 0) + int(row.get("shields") or 0)) * combat_hull(hull)[0]
                    if power < alien_margin * defense:
                        continue
                    key = (2, 0, -int(defense), aid)
                    why = f"hunt alien {row.get('name') or aid}: power {power:.0f} vs defence {defense:.0f}"
                    if best is None or key < best[0]:
                        best = (key, aid, why)
        if best is None:
            return None
        if str(best[1]).startswith("alien:"):
            tally["__alien__"] = 1
        tally[best[1]] = int(tally.get(best[1], 0)) + 1
        return self._act("attack", {"target": best[1], "qty": cap}, best[2])

    def _ship_attack(self, v: View, target: str) -> dict[str, Any] | None:
        """Never fire on a Federal starship. Other ships are not hunted this slice.

        BOT_CAPTURE_POLICY incidental and off both omit qty, so the engine sends the hull
        cap. That is not the capture minimum. A captured hull is just a parked ship.
        """
        import tw2k.engine.constants as _C
        if _C.BOT_CAPTURE_POLICY not in ("incidental", "off"):
            return None
        if self._is_fed_target(v, target):
            return None
        if not v.ok("attack"):
            return None
        return self._act("attack", {"target": target}, "attack a hostile ship")

    def _photon_action(self, v: View, target: int) -> dict[str, Any] | None:
        if not self._hardware_on():
            return None
        spec = ship_specs().get(str(v.ship_class or "")) or {}
        if int(spec.get("max_photons") or 0) <= 0:
            return None
        if int(v.ship.get("photon_missiles") or 0) <= 0:
            return None
        if not v.ok("photon_missile"):
            return None
        choices = {int(c) for c in v.choices("photon_missile", "target")}
        if int(target) not in choices:
            return None
        return self._act("photon_missile", {"target": int(target)},
                         f"photon the adjacent sector {target}, then warp in")

    def _disruptor_action(self, v: View, target: int) -> dict[str, Any] | None:
        if not self._hardware_on():
            return None
        if int(v.ship.get("mine_disruptors") or v.ship.get("disruptors") or 0) <= 0:
            return None
        if not v.ok("fire_disruptor"):
            return None
        choices = {int(c) for c in v.choices("fire_disruptor", "target")}
        if int(target) not in choices:
            return None
        return self._act("fire_disruptor", {"target": int(target)},
                         f"disrupt mines in adjacent sector {target}")

    def _cloak_action(self, v: View) -> dict[str, Any] | None:
        if not self._hardware_on():
            return None
        if int(v.ship.get("cloaks") or 0) <= 0:
            return None
        if v.ship.get("cloaked"):
            return None
        if not v.ok("cloak"):
            return None
        return self._act("cloak", {}, "cloak before the hazard")

    def _cloak_for_navhaz(self, v: View) -> dict[str, Any] | None:
        """Cloak only when every legal exit is a known NavHaz and a device is aboard."""
        if not self._hardware_on() or v.landed is not None:
            return None
        warps = [int(c) for c in v.choices("warp", "target")] if v.ok("warp") else []
        if len(warps) < 1:
            return None
        if any(self._navhaz_pct(v, w) < 10 for w in warps):
            return None
        return self._cloak_action(v)

    def _beacon_action(self, v: View) -> dict[str, Any] | None:
        if not self._hardware_on():
            return None
        if int(v.ship.get("marker_beacons") or 0) <= 0:
            return None
        if not v.ok("launch_beacon"):
            return None
        if v.params("launch_beacon").get("beacon_here"):
            return None
        if self.mem is not None and v.here is not None and int(v.here) in self.mem.beacons_laid:
            return None
        if self.mem is not None and v.here is not None:
            self.mem.beacons_laid.add(int(v.here))
            self.mem.beacon_stocked = True
        return self._act("launch_beacon", {"message": "marked"}, "one beacon; a second in this sector explodes")

    def _atomic_action(self, v: View) -> dict[str, Any] | None:
        """Detonate only with the colonists already gone. Otherwise the blast is ours."""
        if not self._hardware_on():
            return None
        if v.colonists_aboard > 0:
            return None
        if not v.ok("deploy_atomic"):
            return None
        if v.params("deploy_atomic").get("colonists_alive"):
            return None
        choices = [int(c) for c in v.choices("deploy_atomic", "planet_id")]
        if not choices:
            return None
        return self._act("deploy_atomic", {"planet_id": choices[0]},
                         "detonate only after the colonists are gone")

    def _lay_fighters(self, v: View, qty: int) -> dict[str, Any] | None:
        """Do not park fighters where FedSpace will tow them or an MSL sweep clears them."""
        if self._in_swept_lane(v):
            return None
        if not v.ok("deploy_fighters"):
            return None
        room = int((v.params("deploy_fighters").get("qty") or {}).get("max") or 0)
        send = min(int(qty), room)
        if send <= 0:
            return None
        return self._act("deploy_fighters", {"qty": int(send), "mode": "defensive", **self._pair_ownership(v, "deploy_fighters")},
                         f"deploy {send} fighters outside FedSpace")

    def _maybe_lay_armids(self, v: View) -> dict[str, Any] | None:
        if not self._hardware_on() or self._in_swept_lane(v):
            return None
        if self.mem is None or self.mem.home_sector is None or v.here != self.mem.home_sector:
            return None
        if not v.ok("deploy_mines") or "armid" not in {str(c) for c in v.choices("deploy_mines", "kind")}:
            return None
        if self._home_is_corridor(v):
            return None
        room = v.max_by("deploy_mines", "qty", "armid")
        qty = min(room, 5)
        if qty <= 0:
            return None
        if self.mem is not None:
            self.mem.armids_stocked = True
        return self._act("deploy_mines", {"kind": "armid", "qty": int(qty), **self._pair_ownership(v, "deploy_mines")},
                         "lay armids on the home sector, not a swept lane")

    @staticmethod
    def _pair_ownership(v: View, kind: str) -> dict[str, str]:
        """cr29 "pair": corp members deploy corporate explicitly; otherwise the engine default applies."""
        from ..engine import constants as engine_k
        if engine_k.bot_corp_policy() in ("pair", "team") and "corporate" in v.choices(kind, "ownership"):
            return {"ownership": "corporate"}
        return {}

    def _home_is_corridor(self, v: View) -> bool:
        """Armids hit every ship but the owner's. Keep them out of a sector other seats use.

        QC (seed 250925): N1-P5 mined its home 14, the only gate to N2-P3's dead-end
        home 428, and the armids killed P3's colonist ferry three times.
        """
        me = v.self_id
        here = int(v.here or 0)
        sector = v.sector or {}
        for pl in sector.get("planets") or []:
            owner = pl.get("owner_id") if isinstance(pl, dict) else None
            if owner is not None and owner != me:
                return True  # a rival's planet: its owner ferries through here
        if any(o != me for o in sector.get("occupants") or []):
            return True  # rival traffic in the sector right now
        for adj in v.obs.get("adjacent") or []:
            if not isinstance(adj, dict):
                continue
            try:
                aid = int(adj.get("id"))
            except (TypeError, ValueError):
                continue
            # A dead end behind this sector: whoever lives there must pass through.
            if tuple(v.known_warps.get(aid) or ()) == (here,) or adj.get("warps") == 1:
                return True
            seen = (adj.get("seen") or {}).get("planets") or []
            if any(isinstance(pl, dict) and pl.get("owner_id") not in (None, me) for pl in seen):
                return True
        return False

    def _maybe_remove_limpet(self, v: View) -> dict[str, Any] | None:
        if not self._hardware_on() or not v.ok("remove_limpet"):
            return None
        fee = int(v.params("remove_limpet").get("fee") or 0)
        if v.credits < fee + self.cash_buffer:
            return None
        return self._act("remove_limpet", {}, "pay StarDock to cut the limpet")

    def _afford_hardware(self, v: View, price: int, qty: int = 1) -> bool:
        keep = self.working_capital + int(CITADEL_TIER_COST[0][0])
        if self._fogged_hot():
            return v.credits >= int(price) * int(qty) + keep
        return v.credits >= RICH_CREDITS and v.credits >= int(price) * int(qty) + keep

    def _maybe_buy_rich_hardware(self, v: View) -> dict[str, Any] | None:
        """One gadget per visit, only once cash clears the citadel reserve.

        Disruptors stay off this path: 40k early steals the ferry. A disruptor
        is bought only when a neighbor already shows mines.
        """
        import tw2k.engine.constants as _HK
        if not _HK.hardware_tw2002() or int(v.here or 0) != STARDOCK or not v.ok("buy_equip"):
            return None
        if v.credits < RICH_CREDITS and not self._fogged_hot():
            return None
        items = {str(x) for x in v.choices("buy_equip", "item")}
        prices = (v.params("buy_equip").get("item") or {}).get("unit_price_by") or {}
        ship = v.ship

        def price_of(item: str, default: int) -> int:
            return int(prices.get(item) or default)

        if "psychic_probe" in items and int(ship.get("psychic_probe") or 0) <= 0:
            price = price_of("psychic_probe", _HK.PSYCHIC_PROBE_COST)
            if self._afford_hardware(v, price):
                return self._act("buy_equip", {"item": "psychic_probe", "qty": 1},
                                 "one psychic probe, then haggle from its reading")
        have_corb = int(ship.get("corbomite") or 0)
        if "corbomite" in items and have_corb < 10:
            price = price_of("corbomite", _HK.CORBOMITE_COST)
            qty = min(10 - have_corb, v.max_by("buy_equip", "qty", "corbomite") or (10 - have_corb))
            if qty > 0 and self._afford_hardware(v, price, qty):
                return self._act("buy_equip", {"item": "corbomite", "qty": int(qty)},
                                 f"buy {qty} corbomite before carrying cash")
        mines = ship.get("mines") or {}
        have_armid = int(mines.get("armid") or ship.get("armid_mines") or 0)
        if "armid_mines" in items and have_armid < 5 and not (self.mem and self.mem.armids_stocked):
            price = price_of("armid_mines", 100)
            qty = min(5 - have_armid, v.max_by("buy_equip", "qty", "armid_mines") or (5 - have_armid))
            if qty > 0 and self._afford_hardware(v, price, qty):
                if self.mem is not None:
                    self.mem.armids_stocked = True
                return self._act("buy_equip", {"item": "armid_mines", "qty": int(qty)},
                                 f"buy {qty} armids for the home sector")
        if "marker_beacon" in items and int(ship.get("marker_beacons") or 0) <= 0 and not (self.mem and self.mem.beacon_stocked):
            price = price_of("marker_beacon", _HK.BEACON_COST)
            if self._afford_hardware(v, price):
                if self.mem is not None:
                    self.mem.beacon_stocked = True
                return self._act("buy_equip", {"item": "marker_beacon", "qty": 1},
                                 "one marker beacon")
        if self._fogged_hot() and "cloak" in items and int(ship.get("cloaks") or 0) <= 0:
            price = price_of("cloak", _HK.CLOAK_COST)
            if self._afford_hardware(v, price):
                return self._act("buy_equip", {"item": "cloak", "qty": 1},
                                 "cloak while Ferrengi are on the map")
        mined = False
        for adj in v.obs.get("adjacent") or []:
            if isinstance(adj, dict) and (adj.get("mines") or adj.get("mine_count")):
                mined = True
        dis_have = int(ship.get("mine_disruptors") or ship.get("disruptors") or 0)
        if mined and "mine_disruptor" in items and dis_have <= 0:
            price = price_of("mine_disruptor", _HK.DISRUPTOR_COST)
            if self._afford_hardware(v, price):
                return self._act("buy_equip", {"item": "mine_disruptor", "qty": 1},
                                 "disruptor for a mined lane")
        return None

    def _maybe_buy_hardware(self, v):
        """HARDWARE_MODE: carry a cloak with photons (no auto-buy of disruptors)."""
        import tw2k.engine.constants as _HK
        # Use sector id directly — never call _at_stardock here (it buys scanners/hardware).
        if not _HK.hardware_tw2002() or int(getattr(v, "here", 0) or 0) != 1 or not v.ok("buy_equip"):
            return None
        items = set(str(x) for x in v.choices("buy_equip", "item"))
        prices = (v.params("buy_equip").get("item") or {}).get("unit_price_by") or {}
        ship = {}
        try:
            raw = getattr(v, "raw", None)
            if isinstance(raw, dict):
                ship = ((raw.get("self") or {}).get("ship")) or {}
            elif hasattr(v, "ship") and isinstance(v.ship, dict):
                ship = v.ship
        except Exception:
            ship = {}
        cloaks = int(ship.get("cloaks") or 0)
        photons = int(ship.get("photon_missiles") or 0)
        if photons > 0 and cloaks <= 0 and "cloak" in items:
            price = int(prices.get("cloak") or _HK.CLOAK_COST)
            if int(v.credits) >= price + 5000:
                return self._act("buy_equip", {"item": "cloak", "qty": 1},
                                 "hardware: carry a cloak with the photon")
        # Do not auto-buy disruptors here — expensive and steals ferry capital on bars.
        return None

    def _buy_scanner(self, v: View) -> dict[str, Any] | None:
        """Buy the best affordable scanner this hull can carry. Never past credits."""
        choice = self._scanner_item_choice(v)
        if choice is None:
            return None
        item, unit = choice
        # Match _scanner_item_choice: holo keeps working_capital; density keeps cash_buffer.
        keep = self.working_capital if item == "holo_scanner" else self.cash_buffer
        if v.credits < unit + keep:
            return None
        return self._act("buy_equip", {"item": item, "qty": 1},
                         f"fit {item} ({unit} cr) so fogged neighbors can be mapped")

    def _blind_neighbors(self, v: View) -> bool:
        """True when some adjacent sector still needs a scan this visit.

        Empty `seen` dicts are falsy, so key off `seen_day` / `scan_day`
        rather than `bool(seen)`. One scan per neighbour-set per day is enough;
        upgrading density->holo can wait for the next visit.
        """
        for adj in v.obs.get("adjacent") or []:
            if not isinstance(adj, dict):
                continue
            if adj.get("port") or adj.get("seen_day") == v.day or adj.get("scan_day") == v.day:
                continue
            return True
        return False

    def _scan_tier_choice(self, v: View) -> str | None:
        if not v.ok("scan"):
            return None
        tiers = [str(t) for t in v.choices("scan", "tier")]
        if not tiers:
            return ""
        if SCANNER_HOLO in tiers:
            return SCANNER_HOLO
        if SCANNER_DENSITY in tiers:
            return SCANNER_DENSITY
        return tiers[0]

    def _maybe_scan(self, v: View, *, force: bool = False) -> dict[str, Any] | None:
        """Run the best legal scan when neighbors are unknown (or force for explore)."""
        if not info_tw2002():
            if force and v.ok("scan"):
                return self._act("scan", {}, "scan")
            return None
        if not self._fitted_scanner(v):
            return None
        if not force and not self._blind_neighbors(v):
            return None
        tier = self._scan_tier_choice(v)
        if tier is None:
            return None
        args: dict[str, Any] = {}
        if tier:
            args["tier"] = tier
        label = tier or "basic"
        return self._act("scan", args, f"{label} scan to map adjacent ports")

    def _opt_scanner(self, v: View):
        """Value going to StarDock (or buying here) for a scanner under the fog."""
        if not info_tw2002():
            return None
        # Rival pressure + existing worlds: empire rungs (citadel) beat a scanner ferry.
        if self.pressure is not None and v.worlds():
            return None
        fitted = self._fitted_scanner(v)
        room = scanner_room(str(v.ship_class or ""))
        if room is None:
            return None
        if fitted == SCANNER_HOLO or (fitted == SCANNER_DENSITY and room == SCANNER_DENSITY):
            return None
        turns = self._hops_to_stardock(v) * self._tpw(v) + 1
        # Prefer an affordable density early; chase holo only once cash is comfortable.
        if fitted is None:
            if room == SCANNER_HOLO and v.credits >= HOLO_SCANNER_COST + self.working_capital:
                cost, value = HOLO_SCANNER_COST, 80_000
            else:
                cost, value = DENSITY_SCANNER_COST, 120_000
        else:
            if v.credits < HOLO_SCANNER_COST + self.working_capital + 40_000:
                return None
            cost, value = HOLO_SCANNER_COST, 30_000
        if v.credits < cost + self.cash_buffer:
            return None
        if v.here == STARDOCK:
            action = self._buy_scanner(v)
            if action is None:
                return None
        else:
            action = self._plot(v, STARDOCK, "StarDock for a long-range scanner")
            if action is None:
                return None
        return value / max(1, turns), action, Intent("acquire", STARDOCK)

    def _opt_scan(self, v: View):
        if not info_tw2002() or not self._fitted_scanner(v):
            return None
        if not self._blind_neighbors(v):
            return None
        action = self._maybe_scan(v)
        if action is None:
            return None
        return 35_000.0, action, Intent("explore")


    def _cargotran_net(self, v: View) -> int | None:
        """Trade-in net for CargoTran from a starter hull, or None if we already outgrew it."""
        if v.ship_class not in ("merchant_cruiser", "scout_marauder"):
            return None
        spec_key = v.ship_class
        trade_in = int(ship_cost(spec_key) * 0.25)
        return int(ship_cost("cargotran")) - trade_in

    def _cargotran_affordable(self, v: View) -> bool:
        net = self._cargotran_net(v)
        return net is not None and v.credits - net >= self.cash_buffer

    def _no_genesis_hull(self, v: View) -> bool:
        """GENESIS_HULL_MODE tw2002: this hull carries no Genesis Torpedo (the free Scout after a loss).

        The trip to StarDock for one is wasted (QC seed 20260925: N2-P3 / N1-P5 ping-ponged
        StarDock <-> a port for nine days). Legacy observations carry no genesis_cap.
        """
        import tw2k.engine.constants as _GK
        if not _GK.genesis_hull_on():
            return False
        cap = v.ship.get("genesis_cap")
        return cap is not None and int(cap) <= 0

    def _genesis_trip_cost(self, v: View) -> int:
        """What 'genesis is affordable' means for the flight to StarDock.

        Calm keeps the L1 citadel price in hand (seed 250925: a 20k seat can earn
        that on day 1 and still have the turns to autopilot; waiting on the extra
        cash buffer never arrives). Pressure drops to the torpedo price itself.
        """
        if self.pressure is not None:
            return GENESIS_TORPEDO_COST
        return GENESIS_TORPEDO_COST + CITADEL_TIER_COST[0][0]

    def _needs_stardock(self, v: View) -> bool:
        gplanets = v.genesis_planets()
        if v.genesis_aboard > 0:
            return False
        if not v.worlds():
            if (self.value_allocator and self.mem.hull_wait and self.pressure is None
                    and self._cargotran_net(v) is not None and not self._cargotran_affordable(v)):
                return False
            return self._cargotran_affordable(v) or (v.credits >= self._genesis_trip_cost(v)
                                                     and not self._no_genesis_hull(v))
        reserve = self._citadel_reserve(v)
        if (len(gplanets) < self.target_planets and v.credits >= GENESIS_TORPEDO_COST + reserve
                and not self._no_genesis_hull(v)):
            return True
        # Ferry trip: colonists still needed, holds mostly free (sell/stock goods first),
        # and at least a small load affordable above the reserve.
        return (v.colonists_aboard == 0 and v.cargo_free >= 25 and self._colonists_needed(v) > 0
                and v.credits - reserve >= 250)

    def _stardock_reason(self, v: View) -> str:
        if not v.worlds():
            if self._cargotran_affordable(v):
                return "CargoTran is affordable - autopilot to StarDock (sector 1)"
            return "genesis is affordable - autopilot to StarDock (sector 1)"
        return "go to StarDock for colonists"

    def _bank_detour(self, v: View, action: dict[str, Any], intent: Intent) -> tuple[dict[str, Any], Intent]:
        """bb11: one StarDock stop when spare cash is large and the dock is only a few hops off the plan."""
        from ..engine import constants as engine_k
        if not self._reserve_on() or v.landed is not None or v.here in (None, STARDOCK):
            return action, intent
        kind = action.get("kind")
        target = (action.get("args") or {}).get("target")
        if kind not in ("warp", "plot_course") or target is None or int(target) == int(STARDOCK):
            return action, intent
        mem = self.mem
        if mem is not None and mem.bank_detour_day == int(v.day):
            return action, intent
        cargo = v.cargo or {}
        if any(int(cargo.get(name) or 0) > 0 for name in ("fuel_ore", "organics", "equipment")):
            return action, intent
        if int(v.credits) - self._away_cash(v) < int(engine_k.BOT_BANK_DETOUR_CASH):
            return action, intent
        limit = int(engine_k.BOT_BANK_DETOUR_HOPS_ON if engine_k.bots_bank_on() else engine_k.BOT_BANK_DETOUR_HOPS)
        direct = self._hops(v, v.here, int(target))
        via_dock = self._hops(v, v.here, STARDOCK)
        after = self._hops(v, STARDOCK, int(target))
        if direct is None or via_dock is None or after is None:
            return action, intent
        if via_dock + after - direct > limit:
            return action, intent
        path = self._known_path(v, int(v.here), int(STARDOCK))
        if not path or any(sid in self._held_today(v) for sid in path):
            return action, intent
        plotted = self._plot(v, int(STARDOCK), "bank the spare cash on the way")
        if plotted is None:
            return action, intent
        if mem is not None:
            mem.bank_detour_day = int(v.day)
        return plotted, intent

    def _plot(self, v: View, target: int, why: str) -> dict[str, Any] | None:
        # The engine rejects plot_course execute when the first hop's turn cost
        # cannot be paid (it used to return ok with 0 hops). Still refuse to
        # send the action unless a single warp is legal.
        if target is None or target == v.here or not v.ok("plot_course") or not v.ok("warp"):
            return None
        step = self._fed_overnight_stop(v, int(target))
        if step is not None:
            if step == v.here:
                return None
            # One warp at a time along the known route: the autopilot takes its own shortest
            # path, which may cut through sector 1 even when the known route does not.
            return self._act("warp", {"target": int(step)},
                             f"{why} (warp {step} toward {target}, not autopilot: today's turns end near "
                             f"FedSpace with {self._ship_fighters(v)} fighters)")
        return self._act("plot_course", {"target": int(target), "execute": True}, f"{why} (plot {target})")

    def _fed_overnight_stop(self, v: View, target: int) -> int | None:
        """QC (seed 20260925 N3-P1 day 6): a plot through StarDock ran out of turns in sector 1
        with 200 fighters and the Feds towed it at Extern.

        Armed past the tow limit, with a route today's turns cannot finish and FedSpace within
        reach: step one known warp at a time (re-checked every hop) instead of the autopilot.
        Returns the next warp, `v.here` for "do not move toward it", or None for "plot as asked".
        """
        import tw2k.engine.constants as _K
        if not _K.fed_tw2002() or v.here is None:
            return None
        if int(self._ship_fighters(v)) <= int(_K.FED_TOW_FIGHTER_LIMIT):
            return None
        path = self._known_path(v, int(v.here), int(target))
        if not path:
            return None
        left = int(v.obs.get("turns_remaining") or 0) if isinstance(v.obs, dict) else 0
        cost = max(1, int((v.legal.get("warp") or {}).get("turn_cost") or 1))
        hops = left // cost
        if hops >= len(path) or hops <= 0:
            return None  # reaches the target today, or cannot move at all
        near_fed = path[hops - 1] in FEDSPACE_IDS or any(
            (d := known_distance(v.known_warps, int(v.here), fid, cap=hops)) is not None and d <= hops
            for fid in FEDSPACE_IDS)
        if not near_fed:
            return None
        if path[0] in FEDSPACE_IDS and hops <= 1:
            return int(v.here)  # the only warp today would end in FedSpace: no plot
        legal = {int(c) for c in v.choices("warp", "target")} if v.ok("warp") else set()
        if path[0] not in legal:
            return None
        if path[0] in FEDSPACE_IDS and all(sid in FEDSPACE_IDS for sid in path[:hops]):
            return int(v.here)
        return int(path[0])

    @staticmethod
    def _known_path(v: View, src: int, dst: int) -> list[int]:
        """Shortest known route src->dst (excluding src) over the seat's warp memory."""
        prev: dict[int, int] = {src: src}
        frontier = [src]
        while frontier and dst not in prev:
            nxt: list[int] = []
            for s in frontier:
                for n in v.known_warps.get(s, ()):
                    if n not in prev:
                        prev[n] = s
                        nxt.append(n)
            frontier = nxt
        if dst not in prev:
            return []
        out = [dst]
        while out[-1] != src:
            out.append(prev[out[-1]])
        return list(reversed(out[:-1]))

    def _warp_away_from_stardock(self, v: View) -> int | None:
        choices = [int(c) for c in v.choices("warp", "target")] if v.ok("warp") else []
        choices = [t for t in choices if not self._banned_why({"kind": "warp", "args": {"target": t}}, v)]
        if not choices:
            return None

        def score(t: int):
            d = known_distance(v.known_warps, STARDOCK, t)
            return (-(d if d is not None else 99), self.mem.visits.get(t, 0), t)

        return sorted(choices, key=score)[0]

    def _legal_warps(self, v: View) -> list[int]:
        if not v.ok("warp"):
            return []
        choices = [int(c) for c in v.choices("warp", "target")]
        if self._should_avoid_hot(v):
            hot = self.mem.hot_sectors if self.mem else set()
            safe = [c for c in choices if c not in hot]
            if safe:
                return safe
        if self._hardware_on():
            calm = [c for c in choices if self._navhaz_pct(v, c) < 10]
            if calm and len(calm) < len(choices):
                return calm
        return choices

    def _came_from(self, v: View) -> int | None:
        last = self.mem.last_warp
        if last and v.here is not None and last[1] == int(v.here):
            return last[0]
        return None

    def _nav_graph(self, v: View) -> dict[int, tuple[int, ...]]:
        """Known-warp graph, plus the live exits of the sector we are standing in."""
        g = {int(k): tuple(int(x) for x in (n or ())) for k, n in v.known_warps.items()}
        if v.here is not None and int(v.here) not in g:
            outs = v.sector.get("warps_out") or v.choices("warp", "target")
            g[int(v.here)] = tuple(int(x) for x in outs)
        held = self._held_today(v) - ({int(v.here)} if v.here is not None else set())
        if held:
            g = {k: tuple(n for n in outs if n not in held) for k, outs in g.items() if k not in held}
        return g

    def _nearest_frontiers(self, v: View) -> list[tuple[int, tuple[int, ...]]]:
        """Known sectors, at the minimum known-warp distance, that have an unvisited neighbour.

        Unvisited = a warp target whose own exits are not in the graph yet. The current
        sector counts as known even before the engine has filed its warp list.
        """
        g = self._nav_graph(v)
        if v.here is None:
            return []
        here = int(v.here)
        seen = {here}
        queue: list[tuple[int, int]] = [(here, 0)]
        i = 0
        best_d: int | None = None
        found: list[tuple[int, tuple[int, ...]]] = []
        while i < len(queue):
            sector, dist = queue[i]
            i += 1
            if best_d is not None and dist > best_d:
                break
            unvis = tuple(n for n in g.get(sector, ()) if n not in g)
            if unvis:
                if best_d is None:
                    best_d = dist
                if dist == best_d:
                    found.append((sector, unvis))
                continue
            if best_d is None:
                for nxt in g.get(sector, ()):
                    if nxt not in seen and nxt in g:
                        seen.add(nxt)
                        queue.append((nxt, dist + 1))
        return found

    def _explore(self, v: View, why: str):
        """Move toward the nearest known sector that still has an unvisited neighbour.

        Greedy 'warp to the least-visited adjacent' ABA-bounces on dead-ends. Plotting
        through known warps to the frontier crosses that dead-end once and keeps going.
        """
        if v.here is None:
            return None, Intent()
        here = int(v.here)
        found = self._nearest_frontiers(v)
        came = self._came_from(v)
        ports = self.mem.ports_seen

        legal = self._legal_warps(v)

        def banned_warp(target: int) -> bool:
            return target not in legal or bool(self._banned_why({"kind": "warp", "args": {"target": target}}, v))

        if found:
            local = next((unvis for sector, unvis in found if sector == here), None)
            if local:
                ordered = sorted(local, key=lambda t: (t == came, t not in ports, self.mem.visits.get(t, 0), t))
                for target in ordered:
                    if not banned_warp(target):
                        return self._act("warp", {"target": target}, f"explore -> {target} ({why})"), Intent("explore")
            else:
                ordered_sectors = sorted(found, key=lambda su: (su[0] not in ports, su[0]))
                for sector, _unvis in ordered_sectors:
                    plot = self._plot(v, sector, f"frontier {sector} ({why})")
                    if plot is not None and not self._banned_why(plot, v):
                        return plot, Intent("explore", sector)
                    hop = self._known_hop_toward(v, sector)
                    if hop is not None and not banned_warp(hop):
                        return (self._act("warp", {"target": hop}, f"frontier hop {hop} toward {sector} ({why})"),
                                Intent("explore", sector))
        choices = [t for t in legal if not self._banned_why({"kind": "warp", "args": {"target": t}}, v)]
        if choices:
            choices.sort(key=lambda t: (t == came, self.mem.visits.get(t, 0), t))
            return self._act("warp", {"target": choices[0]}, f"explore -> {choices[0]} ({why})"), Intent("explore")
        scanned = self._maybe_scan(v, force=here not in v.known_warps)
        if scanned is not None:
            return scanned, Intent("explore")
        return None, Intent()

    def _known_hop_toward(self, v: View, target: int) -> int | None:
        """First hop from here toward ``target`` along known warps (legal warp exits only)."""
        g = self._nav_graph(v)
        if v.here is None or not v.ok("warp"):
            return None
        here = int(v.here)
        if target == here:
            return None
        parent: dict[int, int | None] = {here: None}
        queue = [here]
        i = 0
        while i < len(queue) and target not in parent:
            sector = queue[i]
            i += 1
            for nxt in g.get(sector, ()):
                if nxt in parent:
                    continue
                if nxt != target and nxt not in g:
                    continue
                parent[nxt] = sector
                if nxt != target:
                    queue.append(nxt)
        if target not in parent:
            return None
        hop: int | None = target
        while hop is not None and parent.get(hop) != here:
            hop = parent.get(hop)
        legal = {int(c) for c in v.choices("warp", "target")}
        if hop is None or hop not in legal:
            return None
        return hop

    def _act(self, kind: str, args: dict[str, Any], thought: str) -> dict[str, Any]:
        # The psychic helper can raise a sell by one step. The live ladder does not
        # attach that price: a counter the port refuses spends the turn.
        return {"kind": kind, "args": args, "thought": f"SeatBrain: {thought}"}

    def _finish(self, v: View, action: dict[str, Any]) -> dict[str, Any]:
        mem = self.mem
        if mem is not None and str(action.get("kind") or "").startswith("buy_"):
            mem.bank_unspent = False
        if str(action.get("thought") or "").startswith("SeatBrain: arm for hunting"):
            self._hunt_arm_day = v.day  # _opt_hunt_arm: one arming buy a game day
        gplanets = v.genesis_planets()
        home = v.planet(mem.home_planet)
        if not v.worlds() and v.genesis_aboard == 0 and not self._needs_stardock(v) and v.here != STARDOCK:
            short = "Trade known ports until CargoTran or genesis is affordable, then autopilot to StarDock."
        elif not gplanets and v.genesis_aboard == 0:
            short = "Afford and buy a genesis torpedo at StarDock."
        elif v.genesis_aboard:
            short = "Deploy genesis in a legal deep sector, then land and build a citadel."
        elif self.value_allocator:
            short = (f"Best value per turn: trade, citadel tiers, genesis up to {self.target_planets}, "
                     f"organics, or a stockpile sale.")
        else:
            short = f"Ferry colonists StarDock -> sector {mem.home_sector}; grow citadel on planet {mem.home_planet}."
        medium = (f"Home planet {mem.home_planet} (L{home.get('citadel_level')}, "
                  f"{_colonists_total(home)} colonists)" if home else "Found a genesis home world")
        if self.pressure and self.pressure.get("leader"):
            medium += f"; trailing {self.pressure['leader']} ({self.pressure['leader_nw']} NW) - empire rungs first"
        action["goal_short"] = short
        action["goal_medium"] = medium
        action["goal_long"] = f"Hold {self.target_planets}+ genesis worlds with rising citadels; win on net worth."
        action["scratchpad_update"] = mem.dump()
        return action


__all__ = ["SeatBrain", "SeatMemory", "View", "next_tier"]


def tw_turns_saved(tpw: int, hops: int) -> int:
    """Turns a TransWarp jump saves over walking `hops` warps (SHIP_TW_TURN_COST "tpw": one TPW per jump)."""
    from ..engine import constants as engine_k
    tpw, hops = max(1, int(tpw)), max(0, int(hops))
    jump = tpw * max(1, hops) if engine_k.SHIP_TW_TURN_COST == "hops" else tpw
    return tpw * hops - jump


def tw_reserve_view(o: dict[str, Any], plan_hops: int | None = None) -> dict[str, Any]:
    """TransWarp ore reserve (Ben 2026-10-05): a seat that OWNS a Type 1 drive sees the ore for its planned
    jump (`plan_hops` hops, from SeatBrain._planned_tw_hops) as not for sale, so the trade ladder never sells
    it; with no planned jump nothing is held back. Any other seat gets the observation back untouched,
    so non-owner play stays byte-identical. The real hold stays readable as `_tw_ore_aboard`."""
    ship = o.get("ship") or {}
    tw = ship.get("transwarp")
    if not isinstance(tw, dict) or tw.get("fitted") != "type1":
        return o
    per_hop = max(1, int(tw.get("ore_per_hop") or 3))
    keep = min(per_hop * max(0, int(plan_hops or 0)), int(ship.get("holds") or 0))
    have = int((ship.get("cargo") or {}).get("fuel_ore") or 0)
    out = dict(o)
    out["_tw_ore_aboard"] = have
    out["_tw_ore_reserve"] = keep
    hidden = min(have, keep)
    if hidden <= 0:
        return out
    out["ship"] = dict(ship)
    out["ship"]["cargo"] = dict(ship.get("cargo") or {})
    out["ship"]["cargo"]["fuel_ore"] = have - hidden
    legal = []
    for la in o.get("legal_actions") or []:
        if isinstance(la, dict) and la.get("kind") == "trade" and la.get("params"):
            la = copy.deepcopy(la)
            params = la["params"]
            row = ((params.get("qty") or {}).get("max_by") or {}).get("fuel_ore")
            if isinstance(row, dict) and "sell" in row:
                row["sell"] = max(0, min(int(row.get("sell") or 0), have - hidden))
                comm = params.get("commodity") or {}
                if row["sell"] <= 0 and "fuel_ore" in (comm.get("sell_choices") or []):
                    comm["sell_choices"] = [c for c in comm["sell_choices"] if c != "fuel_ore"]
        legal.append(la)
    out["legal_actions"] = legal
    return out
