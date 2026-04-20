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
    BUILD_CITADEL = "build_citadel"
    DEPLOY_GENESIS = "deploy_genesis"
    PLOT_COURSE = "plot_course"
    PHOTON_MISSILE = "photon_missile"
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
