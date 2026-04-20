"""Phase H4 — copilot safety checks.

Evaluates a player's current Observation + recent engine events and
returns a `SafetySignal` indicating whether the TaskAgent (autopilot)
should pause, warn, or force an escalation back to manual control.

Levels:
  - "ok"       → nothing to report.
  - "notice"   → informational; surfaces in the chat log but autopilot
                 keeps running.
  - "warning"  → autopilot emits a spoken warning; task keeps running
                 but the human should probably intervene.
  - "critical" → autopilot hard-stops, the UI raises an escalation
                 banner, and the copilot drops back to ADVISORY mode
                 so the human has full control.

The check is intentionally conservative and rule-based — we don't want
LLM latency between "enemy appears" and "autopilot stops". Tests cover
each level.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..engine import Observation


@dataclass
class SafetySignal:
    level: str  # "ok" | "notice" | "warning" | "critical"
    reason: str
    code: str = ""
    detail: dict[str, Any] | None = None

    @property
    def is_stop(self) -> bool:
        return self.level == "critical"


OK = SafetySignal(level="ok", reason="")


# ---------------------------------------------------------------------------
# Heuristics
# ---------------------------------------------------------------------------


_COMBAT_EVENT_KINDS = {
    "combat",
    "photon_fired",
    "fighter_attack",
    "enemy_hail",
    "ferrengi_attack",
}

_HOSTILE_HAIL_HINTS = ("attack", "die", "surrender", "destroy")


def evaluate_observation(
    obs: Observation,
    *,
    recent_events: list[dict[str, Any]] | None = None,
    min_turns_reserve: int = 3,
    low_credit_abs: int = 0,
) -> SafetySignal:
    """Pure function: inspect observation + optional event dicts.

    `recent_events` is a list of event envelopes (typically from
    `obs.events` or the scheduler's tail) — each a dict with `kind`,
    `actor_id`, and `payload`/`summary` fields. We look for combat,
    hostile hails, player eliminations, and port destruction near the
    player's current sector.

    Keyword args let tests tune thresholds — production callers
    typically accept the defaults.
    """
    # 1) Combat / hostile entity in current sector.
    sector = obs.sector or {}
    occupants = sector.get("other_players", []) or []
    hostile_here = [
        o
        for o in occupants
        if isinstance(o, dict)
        and (o.get("aggression") in ("hostile", "aggressive") or o.get("aggression_level", 0) >= 2)
    ]
    sector_fighters = sector.get("fighters") or {}
    if sector_fighters and sector_fighters.get("owner_id") not in (None, obs.self_id):
        return SafetySignal(
            level="critical",
            reason=(
                f"enemy fighters in sector {sector.get('id')} "
                f"(owner {sector_fighters.get('owner_id')}, "
                f"{sector_fighters.get('count', '?')} units) — pausing autopilot"
            ),
            code="hostile_fighters_here",
            detail={"sector_id": sector.get("id"), "fighters": sector_fighters},
        )

    if hostile_here:
        return SafetySignal(
            level="critical",
            reason=(
                f"hostile player(s) in sector {sector.get('id')}: "
                + ", ".join(str(o.get("id", "?")) for o in hostile_here)
            ),
            code="hostile_player_here",
            detail={"sector_id": sector.get("id"), "occupants": hostile_here},
        )

    # 2) Turns exhaustion — about to be stranded mid-task.
    if obs.turns_remaining <= min_turns_reserve:
        return SafetySignal(
            level="warning",
            reason=(
                f"only {obs.turns_remaining} turns left today — "
                "autopilot will stall at end-of-day"
            ),
            code="low_turns",
            detail={"turns_remaining": obs.turns_remaining},
        )

    # 3) Credits floor — can't afford to keep trading.
    if low_credit_abs > 0 and obs.credits < low_credit_abs:
        return SafetySignal(
            level="warning",
            reason=f"credits ({obs.credits:,}) below floor {low_credit_abs:,}",
            code="low_credits",
            detail={"credits": obs.credits, "floor": low_credit_abs},
        )

    # 4) Ship in bad shape — shields depleted + fighters gone.
    ship = obs.ship or {}
    shields = int(ship.get("shields", 0) or 0)
    fighters = int(ship.get("fighters", 0) or 0)
    holds = int(ship.get("holds", 0) or 0)
    if shields == 0 and fighters == 0 and holds > 0:
        # Has cargo but no defense — if anything hostile is nearby this
        # is a problem. Emit a notice, not critical, because context
        # matters (empty galaxy is fine).
        return SafetySignal(
            level="notice",
            reason="no shields or fighters — avoid high-traffic lanes",
            code="undefended",
            detail={"shields": shields, "fighters": fighters, "holds": holds},
        )

    # 5) Recent events — cheap scan.
    if recent_events:
        for ev in recent_events[-20:]:
            kind = str(ev.get("kind", "")).lower()
            actor_id = ev.get("actor_id")
            if kind in _COMBAT_EVENT_KINDS and actor_id == obs.self_id:
                return SafetySignal(
                    level="critical",
                    reason=f"recent combat event: {kind} — pausing autopilot",
                    code="recent_combat",
                    detail={"event": ev},
                )
            if kind == "hail":
                summary = str(ev.get("summary", "") or ev.get("payload", {}).get("text", ""))
                if any(h in summary.lower() for h in _HOSTILE_HAIL_HINTS):
                    return SafetySignal(
                        level="warning",
                        reason=f"hostile hail: {summary[:120]}",
                        code="hostile_hail",
                        detail={"event": ev},
                    )
            if kind == "player_eliminated" and actor_id == obs.self_id:
                return SafetySignal(
                    level="critical",
                    reason="this player was eliminated — match over",
                    code="eliminated",
                    detail={"event": ev},
                )
            if kind == "port_destroyed":
                # If the *destination* port we were heading to went boom,
                # autopilot's plan is stale; caller should replan.
                return SafetySignal(
                    level="notice",
                    reason=f"port destroyed nearby: {ev.get('summary', '')[:120]}",
                    code="port_destroyed",
                    detail={"event": ev},
                )

    return OK


def describe_short(sig: SafetySignal) -> str:
    """One-line spoken version for TTS / chat."""
    if sig.level == "ok":
        return ""
    prefix = {
        "notice": "Heads-up",
        "warning": "Warning",
        "critical": "Stopping autopilot",
    }.get(sig.level, "Advisory")
    return f"{prefix}: {sig.reason}"
