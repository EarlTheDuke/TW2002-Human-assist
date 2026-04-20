"""TaskAgent — long-running autopilot loop.

VoiceAgent returns `start_task(kind, params)` when the human gives it a
multi-turn goal ("run my trade loop until 30k credits"). CopilotSession
spawns a TaskAgent in the background to pursue that goal one engine
action at a time, reporting progress back over the broadcast channel.

Every iteration:
  1. Check `cancel_event`. If set, finish cleanly.
  2. Fetch the player's current Observation.
  3. Check the task's terminal condition (e.g. credits >= target_cr).
  4. Ask the LLM for the next tool call (single-step).
  5. Evaluate standing orders.
  6. Submit the action through the HumanAgent path (same route manual
     clicks take), wrapped in `actor_kind_override("copilot")`.
  7. Emit a `task_progress` chat event.
  8. Sleep briefly so the log is readable and other players can move.

The loop is ctor-injected with a `next_step_fn` so tests can drive it
with a scripted strategy and skip any LLM call at all. That's the
mechanism the H2 exit-criterion integration test uses to demo the
trade-loop end-to-end without a real API key.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from ..engine import Observation
from . import provider as prov
from . import safety as _safety
from .tools import ToolCall

# ---------------------------------------------------------------------------
# Public status model
# ---------------------------------------------------------------------------


class TaskStatus(BaseModel):
    id: str
    kind: str
    params: dict[str, Any] = Field(default_factory=dict)
    state: str = "pending"  # pending | running | done | cancelled | error
    iterations: int = 0
    last_action: str | None = None
    last_error: str | None = None
    reason_finished: str | None = None
    started_at: float = 0.0
    ended_at: float | None = None


# ---------------------------------------------------------------------------
# Glue types
# ---------------------------------------------------------------------------


ObsFetcher = Callable[[], Observation]
"""Returns the player's current Observation snapshot."""

ActionDispatcher = Callable[[ToolCall], Awaitable[tuple[bool, str]]]
"""Submit a tool call through the human-agent / scheduler path.
Returns (ok, reason_or_empty). Must be async — the session awaits the
HumanAgent's action-applied signal so each iteration is single-flight."""

NextStepFn = Callable[
    ["TaskContext"], Awaitable[ToolCall | None]
]
"""Produce the next ToolCall, or None to declare the task done.
The default implementation uses an LLM via `llm_next_step`; tests
inject a scripted fn for determinism."""

ProgressReporter = Callable[[str, dict[str, Any]], Awaitable[None]]
"""Emit a chat-panel progress event ({"type": "task_progress", ...})."""


# ---------------------------------------------------------------------------
# Task context passed to next_step_fn
# ---------------------------------------------------------------------------


@dataclass
class TaskContext:
    status: TaskStatus
    observation: Observation
    history: list[dict[str, Any]] = field(default_factory=list)  # last N actions


# ---------------------------------------------------------------------------
# Terminal condition helpers
# ---------------------------------------------------------------------------


def _terminal_for(status: TaskStatus, obs: Observation) -> str | None:
    """Return a reason-string if the task should stop, else None."""
    p = status.params or {}
    if status.kind == "profit_loop":
        target = int(p.get("target_cr", 0))
        if target > 0 and obs.credits >= target:
            return f"reached target {target:,} cr (now {obs.credits:,})"
        max_iter = int(p.get("max_iterations", 500))
        if status.iterations >= max_iter:
            return f"hit iteration cap {max_iter}"
    return None


# ---------------------------------------------------------------------------
# Default LLM-backed next-step function
# ---------------------------------------------------------------------------


TASK_SYSTEM_PROMPT = """\
You are a Trade Wars 2002 autopilot agent. The human delegated a
long-running goal to you. Each turn you pick ONE tool call that makes
progress toward the goal, respecting standing orders and basic safety.

Reply with a SINGLE JSON object, nothing else:

  {"tool": "<tool>", "arguments": {...}, "thought": "<= 30 words"}

Preferred strategies for common task kinds:
  - profit_loop: warp to a known buy-port → buy → warp to matching
    sell-port → sell → repeat. If stuck, scan or plot_course.

Never emit start_task or cancel_task here — you are inside a task.
If you cannot make progress, emit a short `speak` followed by `pass_turn`.
"""


def llm_next_step(
    *,
    provider: str | None = None,
    model: str | None = None,
    timeout_s: float = 20.0,
) -> NextStepFn:
    async def _fn(ctx: TaskContext) -> ToolCall | None:
        user = (
            f"GOAL: {ctx.status.kind} {ctx.status.params}\n"
            f"iteration: {ctx.status.iterations}\n"
            f"OBSERVATION (JSON): {json.dumps(_compact(ctx.observation))}\n"
            f"LAST_ACTIONS: {ctx.history[-6:]}\n\n"
            "Pick the next tool call."
        )
        try:
            raw = await prov.call_llm(
                system=TASK_SYSTEM_PROMPT,
                user=user,
                provider=provider,
                model=model,
                timeout_s=timeout_s,
            )
        except Exception as exc:
            # Swallow errors — the loop treats None as "end the task with
            # last_error set" via the outer handler.
            ctx.status.last_error = f"{type(exc).__name__}: {exc}"
            return None
        calls = prov.parse_tool_response(raw)
        if not calls:
            ctx.status.last_error = "unparseable LLM response"
            return None
        return calls[0]

    return _fn


def _compact(obs: Observation) -> dict[str, Any]:
    sec = obs.sector or {}
    port = sec.get("port")
    return {
        "credits": obs.credits,
        "turns_remaining": obs.turns_remaining,
        "sector": sec.get("id"),
        "warps": sec.get("warps", []),
        "cargo": obs.ship.get("cargo", {}),
        "port": (
            {
                "buying": port.get("buying"),
                "selling": port.get("selling"),
                "prices": port.get("prices"),
                "stock": port.get("stock"),
            }
            if port
            else None
        ),
        "known_ports": obs.known_ports[:12],
    }


# ---------------------------------------------------------------------------
# The runner
# ---------------------------------------------------------------------------


class TaskAgent:
    """Owns one autopilot task. Created per start_task; lives until done/cancelled."""

    def __init__(
        self,
        status: TaskStatus,
        *,
        obs_fn: ObsFetcher,
        dispatch_fn: ActionDispatcher,
        next_step_fn: NextStepFn,
        report_fn: ProgressReporter,
        iter_delay_s: float = 0.05,
        max_consecutive_errors: int = 3,
        safety_fn: Callable[[Observation], _safety.SafetySignal] | None = None,
        on_escalation: Callable[[_safety.SafetySignal], Awaitable[None]] | None = None,
    ):
        self.status = status
        self._obs_fn = obs_fn
        self._dispatch = dispatch_fn
        self._next_step = next_step_fn
        self._report = report_fn
        self._iter_delay_s = iter_delay_s
        self._max_consecutive_errors = max_consecutive_errors
        self._safety_fn = safety_fn or _safety.evaluate_observation
        self._on_escalation = on_escalation
        self.cancel_event = asyncio.Event()
        self.history: list[dict[str, Any]] = []

    def cancel(self, reason: str = "human_cancel") -> None:
        if self.status.state not in ("running", "pending"):
            return
        self.status.reason_finished = f"cancelled: {reason}"
        self.cancel_event.set()

    async def run(self) -> TaskStatus:
        self.status.state = "running"
        self.status.started_at = time.time()
        await self._report(
            "task_started",
            {"task": self.status.model_dump()},
        )

        consecutive_errors = 0
        try:
            while not self.cancel_event.is_set():
                self.status.iterations += 1
                obs = self._obs_fn()

                # Safety check runs BEFORE the LLM call so hostile sectors,
                # low-turn exhaustion, and player-elimination events hard-stop
                # the autopilot before we waste another step. Critical signals
                # cancel the task and let the session surface an escalation.
                try:
                    sig = self._safety_fn(obs)
                except Exception:  # pragma: no cover — defensive
                    sig = _safety.OK
                if sig.level != "ok":
                    await self._report(
                        "safety_signal",
                        {
                            "level": sig.level,
                            "reason": sig.reason,
                            "code": sig.code,
                            "detail": sig.detail or {},
                        },
                    )
                if sig.is_stop:
                    if self._on_escalation is not None:
                        try:
                            await self._on_escalation(sig)
                        except Exception:  # pragma: no cover
                            pass
                    self.status.state = "cancelled"
                    self.status.reason_finished = f"safety_stop: {sig.reason}"
                    break

                # Terminal-condition check before spending another LLM call.
                reason = _terminal_for(self.status, obs)
                if reason is not None:
                    self.status.state = "done"
                    self.status.reason_finished = reason
                    break

                ctx = TaskContext(
                    status=self.status, observation=obs, history=self.history
                )
                call = await self._next_step(ctx)
                if call is None:
                    # next_step_fn gave up (parse error / LLM error / nothing to do).
                    self.status.state = "done"
                    self.status.reason_finished = (
                        self.status.last_error or "next_step_fn returned None"
                    )
                    break

                # Honour explicit task-level control via the tool itself.
                if call.name == "cancel_task":
                    self.status.state = "cancelled"
                    self.status.reason_finished = str(
                        call.arguments.get("reason", "self-cancel")
                    )
                    break

                ok, reason_str = await self._dispatch(call)
                self.status.last_action = call.name
                if ok:
                    self.status.last_error = None
                    consecutive_errors = 0
                    self.history.append(
                        {
                            "iter": self.status.iterations,
                            "tool": call.name,
                            "args": call.arguments,
                            "ok": True,
                        }
                    )
                else:
                    self.status.last_error = reason_str
                    consecutive_errors += 1
                    self.history.append(
                        {
                            "iter": self.status.iterations,
                            "tool": call.name,
                            "args": call.arguments,
                            "ok": False,
                            "reason": reason_str,
                        }
                    )
                    if consecutive_errors >= self._max_consecutive_errors:
                        self.status.state = "error"
                        self.status.reason_finished = (
                            f"aborted after {consecutive_errors} consecutive "
                            f"errors (last: {reason_str})"
                        )
                        break

                await self._report(
                    "task_progress",
                    {
                        "task_id": self.status.id,
                        "iter": self.status.iterations,
                        "tool": call.name,
                        "ok": ok,
                        "reason": reason_str,
                        "last_action": self.status.last_action,
                    },
                )

                if self._iter_delay_s > 0:
                    try:
                        await asyncio.wait_for(
                            self.cancel_event.wait(),
                            timeout=self._iter_delay_s,
                        )
                        # cancel fired during the sleep — exit on next loop check.
                    except TimeoutError:
                        pass

            if self.cancel_event.is_set() and self.status.state == "running":
                self.status.state = "cancelled"
                self.status.reason_finished = (
                    self.status.reason_finished or "cancelled"
                )

        finally:
            self.status.ended_at = time.time()
            await self._report(
                "task_finished",
                {"task": self.status.model_dump()},
            )

        return self.status
