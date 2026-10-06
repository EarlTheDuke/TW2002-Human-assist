"""Action schema — the contract between agents and the engine."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActionKind(str, Enum):
    WARP = "warp"
    TRADE = "trade"
    SCAN = "scan"
    DEPLOY_FIGHTERS = "deploy_fighters"
    DEPLOY_MINES = "deploy_mines"
    ATTACK = "attack"
    LAND_PLANET = "land_planet"
    LIFTOFF = "liftoff"
    ASSIGN_COLONISTS = "assign_colonists"
    LOAD_PLANET_CARGO = "load_planet_cargo"
    DUMP_PLANET_CARGO = "dump_planet_cargo"
    BUILD_CITADEL = "build_citadel"
    DEPLOY_GENESIS = "deploy_genesis"
    CLAIM_PLANET = "claim_planet"
    PLOT_COURSE = "plot_course"
    PHOTON_MISSILE = "photon_missile"
    CLOAK = "cloak"
    FIRE_DISRUPTOR = "fire_disruptor"
    REMOVE_LIMPET = "remove_limpet"
    LAUNCH_BEACON = "launch_beacon"
    TERRA_COLONISTS = "terra_colonists"
    DEPLOY_ATOMIC = "deploy_atomic"
    QUERY_LIMPETS = "query_limpets"
    PROBE = "probe"
    CORP_DEPOSIT = "corp_deposit"
    CORP_WITHDRAW = "corp_withdraw"
    CORP_MEMO = "corp_memo"
    PROPOSE_ALLIANCE = "propose_alliance"
    ACCEPT_ALLIANCE = "accept_alliance"
    BREAK_ALLIANCE = "break_alliance"
    BUY_SHIP = "buy_ship"
    BUY_EQUIP = "buy_equip"
    CORP_CREATE = "corp_create"
    CORP_INVITE = "corp_invite"
    CORP_JOIN = "corp_join"
    CORP_LEAVE = "corp_leave"
    HAIL = "hail"
    BROADCAST = "broadcast"
    WAIT = "wait"
    DEPOSIT_PLANET_DEFENSE = "deposit_planet_defense"
    WITHDRAW_PLANET_DEFENSE = "withdraw_planet_defense"
    SET_MILITARY_REACTION = "set_military_reaction"
    DEPOSIT_TREASURY = "deposit_treasury"
    WITHDRAW_TREASURY = "withdraw_treasury"
    SET_QUASAR_SECTOR = "set_quasar_sector"
    SET_QUASAR_ATM = "set_quasar_atm"
    PLANET_TRANSWARP = "planet_transwarp"
    PLANET_BUY_TRANSPORTER = "planet_buy_transporter"
    PLANET_TRANSPORT = "planet_transport"
    PLANET_DESTROY = "planet_destroy"
    RECALL_DEPLOYED = "recall_deployed"
    SURRENDER = "surrender"
    RETREAT = "retreat"
    PAY_TOLL = "pay_toll"
    ROB = "rob"
    STEAL = "steal"
    APPLY_COMMISSION = "apply_commission"
    POST_REWARD = "post_reward"
    CLAIM_REWARD = "claim_reward"
    SHIP_TRANSWARP = "ship_transwarp"
    SELL_SHIP = "sell_ship"  # ship-fleet-transporter-v1
    SHIP_TRANSPORT = "ship_transport"
    TOW_ENGAGE = "tow_engage"  # ship-tow-transwarp2-v1
    TOW_RELEASE = "tow_release"
    PLANET_TRADE = "planet_trade"  # planetary-trading-v1 (port menu <N>)


class Action(BaseModel):
    kind: ActionKind
    args: dict[str, Any] = Field(default_factory=dict)
    thought: str = ""
    scratchpad_update: str | None = None
    # Optional 3-horizon goal updates the agent wrote this turn. Each is
    # persisted on the Player model and surfaced in its *next* observation's
    # action_hint so the plan survives across turns. None = "don't change
    # what I wrote last turn"; "" = "clear this goal"; a string = "replace".
    goal_short: str | None = None
    goal_medium: str | None = None
    goal_long: str | None = None
    # Override for `actor_kind` on every event emitted while this Action is
    # being applied. Set by the copilot path (H2+) to "copilot" so spectator
    # UI / replay / forensics can distinguish "the human warped to 874"
    # from "the copilot warped to 874 for the human". Scheduler wraps the
    # apply_action call in `actor_kind_override(...)` when this is non-None.
    # Default None means: use the player's agent_kind (same as today).
    actor_kind: str | None = None


class ActionResult(BaseModel):
    ok: bool
    error: str | None = None
    turns_spent: int = 0
    # Event sequence numbers emitted as part of applying this action (for callers to broadcast)
    event_seqs: list[int] = Field(default_factory=list)
