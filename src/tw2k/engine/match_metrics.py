"""Aggregate per-match diagnostics from the event log (Tier 0 agency metrics)."""

from __future__ import annotations

import os
from typing import Any

from .models import Event, EventKind


def build_match_metrics_payload(
    events: list[Event],
    *,
    winner_id: str | None = None,
    win_reason: str | None = None,
) -> dict[str, Any]:
    """Derive summary stats for ``match_metrics`` events and CLI summaries."""
    by_kind: dict[str, int] = {}
    by_actor: dict[str, dict[str, int]] = {}

    parse_errors = 0
    llm_errors = 0
    timeouts = 0
    standing_down = 0
    warmup_thoughts = 0

    game_start_payload: dict[str, Any] | None = None
    game_over_payload: dict[str, Any] | None = None

    for ev in events:
        k = ev.kind.value
        by_kind[k] = by_kind.get(k, 0) + 1

        if ev.kind is EventKind.GAME_START:
            game_start_payload = dict(ev.payload or {})
        if ev.kind is EventKind.GAME_OVER:
            game_over_payload = dict(ev.payload or {})

        aid = ev.actor_id or "_engine"
        row = by_actor.setdefault(aid, {})

        if ev.kind is EventKind.AGENT_THOUGHT:
            row["agent_thought"] = row.get("agent_thought", 0) + 1
            thought = str((ev.payload or {}).get("thought") or "")
            if "Warming up" in thought:
                warmup_thoughts += 1
            if "[parse error]" in thought:
                parse_errors += 1
                row["parse_error"] = row.get("parse_error", 0) + 1
            if "[LLM error]" in thought:
                llm_errors += 1
                row["llm_error_thought"] = row.get("llm_error_thought", 0) + 1
            if "[LLM timeout" in thought:
                timeouts += 1
                row["llm_timeout_thought"] = row.get("llm_timeout_thought", 0) + 1
            if "Standing down for the day" in thought:
                standing_down += 1
                row["standing_down"] = row.get("standing_down", 0) + 1
        elif ev.kind is EventKind.AGENT_ERROR:
            row["agent_error"] = row.get("agent_error", 0) + 1

    last = events[-1] if events else None
    return {
        "hint_level": os.environ.get("TW2K_HINT_LEVEL", "full"),
        "event_count": len(events),
        "by_kind": dict(sorted(by_kind.items())),
        "by_actor": dict(sorted(by_actor.items())),
        "llm_health": {
            "parse_error_thoughts": parse_errors,
            "llm_error_thoughts": llm_errors,
            "llm_timeout_thoughts": timeouts,
            "standing_down_thoughts": standing_down,
            "warmup_thoughts": warmup_thoughts,
            "agent_error_events": by_kind.get("agent_error", 0),
        },
        "final_day": int(last.day) if last else 0,
        "final_tick": int(last.tick) if last else 0,
        "winner_id": winner_id,
        "win_reason": win_reason or "",
        "game_start": game_start_payload,
        "game_over_summary": (game_over_payload or {}).get("summary")
        if game_over_payload
        else None,
    }
