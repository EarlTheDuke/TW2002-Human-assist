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

    # Per-player LLM cost rollup. Keyed by actor_id; each row
    # accumulates provider/model + token totals + USD so the final
    # metrics payload mirrors /api/cost without requiring the runner
    # to serialize MatchCostTracker separately.
    cost_by_actor: dict[str, dict[str, Any]] = {}
    grand_cost_usd = 0.0
    grand_calls = 0

    for ev in events:
        k = ev.kind.value
        by_kind[k] = by_kind.get(k, 0) + 1

        if ev.kind is EventKind.GAME_START:
            game_start_payload = dict(ev.payload or {})
        if ev.kind is EventKind.GAME_OVER:
            game_over_payload = dict(ev.payload or {})

        if ev.kind is EventKind.LLM_USAGE:
            aid_cost = ev.actor_id or "_engine"
            row = cost_by_actor.setdefault(
                aid_cost,
                {
                    "provider": "",
                    "model": "",
                    "calls": 0,
                    "input_tokens": 0,
                    "cached_input_tokens": 0,
                    "cache_write_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "price_is_fallback": False,
                },
            )
            pay = ev.payload or {}
            if not row["provider"]:
                row["provider"] = str(pay.get("provider") or "")
            if not row["model"]:
                row["model"] = str(pay.get("model") or "")
            usage_pay = pay.get("usage") or {}
            row["calls"] += 1
            row["input_tokens"] += int(usage_pay.get("input_tokens") or 0)
            row["cached_input_tokens"] += int(usage_pay.get("cached_input_tokens") or 0)
            row["cache_write_tokens"] += int(usage_pay.get("cache_write_tokens") or 0)
            row["output_tokens"] += int(usage_pay.get("output_tokens") or 0)
            row["cost_usd"] += float(pay.get("cost_usd") or 0.0)
            if pay.get("price_is_fallback"):
                row["price_is_fallback"] = True
            grand_cost_usd += float(pay.get("cost_usd") or 0.0)
            grand_calls += 1

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
    # Round USD totals to 6 decimals — more than enough for tiny
    # per-call numbers, and keeps the JSON diffable turn-over-turn.
    cost_rollup = {
        pid: {
            **row,
            "cost_usd": round(float(row["cost_usd"]), 6),
        }
        for pid, row in sorted(cost_by_actor.items())
    }
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
        "llm_cost": {
            "per_player": cost_rollup,
            "total": {
                "calls": grand_calls,
                "cost_usd": round(float(grand_cost_usd), 6),
            },
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
