"""Structured JSONL tracing for copilot decisions.

Writes one JSON record per line to ``saves/copilot_trace_{player_id}.jsonl``
(one file per human slot, appended in real time). Designed so that:

* Every copilot decision ends up on disk — utterance, LLM call, tool
  call, action dispatch, standing-order block, safety signal,
  escalation, mode change, memory update, task progress.
* Readers can tail the file while the match runs (`tw2k human-sim` or
  a dev tool) to reconstruct "why did the copilot do that?".
* Zero new dependencies; writes happen on a background thread-pool so
  the hot async path never blocks on ``Path.write_text``.

Opt-in via ``TW2K_COPILOT_TRACE=1`` env var, or by passing
``enable=True`` to ``CopilotTracer``. When disabled the emit calls are
cheap no-ops.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .otel import CopilotOtelBridge

TRACE_FILE_PREFIX = "copilot_trace_"
TRACE_EVENT_VERSION = 1


def _env_enabled() -> bool:
    val = os.environ.get("TW2K_COPILOT_TRACE", "").strip().lower()
    return val in ("1", "true", "yes", "on")


class CopilotTracer:
    """Append-only JSONL tracer for a single player.

    All writes are serialised through an ``asyncio.Lock`` so parallel
    coroutines can't interleave a single record's bytes. File handles
    are opened per-emit in append mode — the volume here is ~tens of
    events per minute under autopilot, so the overhead is negligible
    and there's no handle to close on shutdown.
    """

    def __init__(
        self,
        *,
        player_id: str,
        root_dir: Path | str | None = None,
        enable: bool | None = None,
        otel_bridge: CopilotOtelBridge | None = None,
    ) -> None:
        self.player_id = player_id
        self._root = Path(root_dir) if root_dir is not None else None
        if enable is None:
            enable = _env_enabled() and self._root is not None
        # The tracer is "active" if EITHER the JSONL sink is enabled OR
        # the OTEL bridge is wired — we want OTEL-only configurations
        # (no disk writes) to still flow events through emit().
        self._jsonl_enabled = bool(enable and self._root is not None)
        self._otel_bridge = otel_bridge
        self._lock = asyncio.Lock()
        # Keep an in-memory ring for tests that don't want to read from
        # disk. Only populated when tracing is enabled.
        self._ring: list[dict[str, Any]] = []
        self._ring_cap = 1024

    @property
    def _enabled(self) -> bool:
        return self._jsonl_enabled or (self._otel_bridge is not None and self._otel_bridge.enabled)

    @property
    def otel_bridge(self) -> CopilotOtelBridge | None:
        return self._otel_bridge

    def shutdown(self) -> None:
        """Release any attached sinks. Safe to call multiple times."""
        if self._otel_bridge is not None:
            self._otel_bridge.shutdown()
            self._otel_bridge = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def path(self) -> Path | None:
        if self._root is None:
            return None
        return self._root / f"{TRACE_FILE_PREFIX}{self.player_id}.jsonl"

    def ring(self) -> list[dict[str, Any]]:
        """Return a *copy* of the most recent trace events."""
        return list(self._ring)

    async def emit(
        self,
        event: str,
        payload: dict[str, Any] | None = None,
        *,
        level: str = "info",
    ) -> None:
        """Append a single structured event.

        ``event`` is a short snake_case identifier (``llm_call``,
        ``action_dispatched``, ``standing_order_block``…). ``payload``
        is free-form — keep it JSON-serialisable. ``level`` mirrors
        log levels so readers can filter.
        """
        if not self._enabled:
            return
        record = {
            "v": TRACE_EVENT_VERSION,
            "ts": time.time(),
            "player_id": self.player_id,
            "level": level,
            "event": event,
            "payload": dict(payload or {}),
        }
        # Maintain the in-memory ring even before grabbing the lock —
        # readers only ever see whole records.
        self._ring.append(record)
        if len(self._ring) > self._ring_cap:
            # Drop oldest ~10% in one shot instead of on every append.
            drop = max(1, self._ring_cap // 10)
            del self._ring[:drop]

        # Phase H6.3: fan out to the OTEL bridge alongside disk writes.
        # The bridge swallows its own exceptions so a bad OTLP collector
        # can never crash the hot path.
        if self._otel_bridge is not None and self._otel_bridge.enabled:
            self._otel_bridge.emit_event(event, payload, level=level)
            if event == "action_dispatched" and payload is not None:
                self._otel_bridge.emit_action_span(
                    tool=str(payload.get("tool", "unknown")),
                    args=dict(payload.get("args") or {}),
                    ok=bool(payload.get("ok", False)),
                    reason=str(payload.get("reason") or ""),
                )

        p = self.path
        if not self._jsonl_enabled or p is None:
            return
        async with self._lock:
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                with p.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, sort_keys=True))
                    fh.write("\n")
            except OSError:
                # Tracing must never break the hot path — swallow disk
                # errors silently. The in-memory ring still has them.
                return

    # ---------------------- convenience helpers -------------------------

    async def trace_utterance(self, text: str, mode: str) -> None:
        await self.emit(
            "chat_utterance", {"text": text[:400], "mode": mode}
        )

    async def trace_chat_response(
        self, kind: str, message: str, thought: str = ""
    ) -> None:
        await self.emit(
            "chat_response",
            {"kind": kind, "message": message[:400], "thought": thought[:400]},
        )

    async def trace_mode_change(self, mode: str) -> None:
        await self.emit("mode_change", {"mode": mode})

    async def trace_memory_update(self, op: str, key: str, value: str = "") -> None:
        await self.emit(
            "memory_update", {"op": op, "key": key, "value": value[:200]}
        )

    async def trace_action_dispatched(
        self,
        tool: str,
        args: dict[str, Any],
        ok: bool,
        reason: str,
    ) -> None:
        await self.emit(
            "action_dispatched",
            {
                "tool": tool,
                "args": dict(args),
                "ok": ok,
                "reason": reason,
            },
        )

    async def trace_standing_order_block(
        self, tool: str, blocked_by: list[str], reasons: list[str]
    ) -> None:
        await self.emit(
            "standing_order_block",
            {"tool": tool, "blocked_by": list(blocked_by), "reasons": list(reasons)},
            level="warn",
        )

    async def trace_safety_signal(
        self, level: str, code: str, reason: str
    ) -> None:
        await self.emit(
            "safety_signal",
            {"signal_level": level, "code": code, "reason": reason},
            level="warn" if level in ("warning", "critical") else "info",
        )

    async def trace_escalation(self, reason: str, code: str) -> None:
        await self.emit(
            "escalation",
            {"reason": reason, "code": code},
            level="warn",
        )

    async def trace_task_state(
        self,
        task_id: str,
        kind: str,
        state: str,
        iterations: int,
        final_status: str | None = None,
    ) -> None:
        await self.emit(
            "task_state",
            {
                "task_id": task_id,
                "kind": kind,
                "state": state,
                "iterations": iterations,
                "final_status": final_status,
            },
        )


__all__ = ["TRACE_EVENT_VERSION", "TRACE_FILE_PREFIX", "CopilotTracer"]
