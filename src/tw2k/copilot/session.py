"""CopilotSession — per-human state container and public API.

One `CopilotSession` per HUMAN player in a running match. Owns:

- Current `CopilotMode` (Manual / Advisory / Delegated / Autopilot).
- Chat transcript (human utterances + copilot replies).
- Pending plan (awaiting Confirm/Cancel) and active autopilot task.
- Standing-order list with an `evaluate()` gate before any dispatch.
- A `ChatAgent` instance for turn-by-turn utterance handling.

Sessions don't live forever — CopilotRegistry creates one per human when
a match starts, cleans up on match stop. No state persists across
matches in H2; scratchpad-like memory is revisited in H3+.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..agents.human import HumanAgent
from ..engine import Action, ActionKind, Observation, Universe, build_observation
from . import memory as mem_mod
from . import safety
from . import standing_orders as so
from . import whatif as wi
from .chat_agent import ChatAgent, ChatResponse
from .task_agent import TaskAgent, TaskStatus, llm_next_step
from .tools import TOOL_CATALOG, ToolCall
from .trace import CopilotTracer

# ---------------------------------------------------------------------------
# Mode
# ---------------------------------------------------------------------------


class CopilotMode(str, Enum):
    MANUAL = "manual"         # copilot never dispatches; chat stays silent unless queried
    ADVISORY = "advisory"     # copilot replies with suggestions; human still clicks buttons
    DELEGATED = "delegated"   # single actions are executed on human's behalf per utterance
    AUTOPILOT = "autopilot"   # multi-turn tasks run in the background


# ---------------------------------------------------------------------------
# Chat message record (for /api/copilot/state)
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    id: str
    ts: float = Field(default_factory=time.time)
    role: str  # 'human' | 'copilot' | 'system'
    text: str
    kind: str = "speak"  # speak | plan | action | task_progress | error | ...
    payload: dict[str, Any] = Field(default_factory=dict)


class PendingPlan(BaseModel):
    id: str
    plan: list[ToolCall]
    thought: str = ""
    created_at: float = Field(default_factory=time.time)
    task_kind: str | None = None  # if confirm launches a TaskAgent
    task_params: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


# Callable signatures used by CopilotRegistry to inject runner + broadcaster
# without this module having to import them directly (clean layering).
AgentLookup = callable  # player_id -> HumanAgent
UniverseLookup = callable  # () -> Universe
Broadcast = callable  # async (message: dict) -> None


class CopilotSession:
    def __init__(
        self,
        *,
        player_id: str,
        human_agent: HumanAgent,
        universe_fn,  # () -> Universe
        broadcast_fn,  # async (msg: dict) -> None
        chat_agent: ChatAgent | None = None,
        task_next_step_factory=None,  # () -> NextStepFn; default = llm_next_step()
        iter_delay_s: float = 0.05,
        memory_store: mem_mod.MemoryStore | None = None,
        tracer: CopilotTracer | None = None,
    ):
        self.player_id = player_id
        self.human_agent = human_agent
        self._universe_fn = universe_fn
        self._broadcast_fn = broadcast_fn
        self.chat_agent = chat_agent or ChatAgent()
        self._task_next_step_factory = task_next_step_factory or (
            lambda: llm_next_step()
        )
        self._iter_delay_s = iter_delay_s

        self.mode: CopilotMode = CopilotMode.ADVISORY
        self.chat_history: list[ChatMessage] = []
        self.standing_orders: list[so.StandingOrder] = []
        self.pending_plan: PendingPlan | None = None

        self._active_task: TaskAgent | None = None
        self._task_handle: asyncio.Task[TaskStatus] | None = None
        self._task_history: list[TaskStatus] = []

        # H5.1/H5.2 — long-term memory + decision tracer. Both degrade
        # gracefully to in-memory / no-op when no store/tracer is wired.
        self._memory_store = memory_store or mem_mod.MemoryStore()
        self.memory: mem_mod.CopilotMemory = self._memory_store.load(player_id)
        self.memory.bump_stat("session_count")
        self._memory_store.save(self.memory)
        self.tracer: CopilotTracer = tracer or CopilotTracer(
            player_id=player_id, root_dir=None, enable=False
        )

        # Optional auto-confirm (tests / --copilot-autoconfirm CLI flag). When
        # True, plans and start_task proposals skip the Confirm step.
        self.auto_confirm: bool = False

    # --------------------- public API ------------------------------------

    def state_snapshot(self) -> dict[str, Any]:
        """JSON-serialisable snapshot for GET /api/copilot/state."""
        return {
            "player_id": self.player_id,
            "mode": self.mode.value,
            "auto_confirm": self.auto_confirm,
            "chat": [m.model_dump() for m in self.chat_history[-100:]],
            "standing_orders": [o.model_dump() for o in self.standing_orders],
            "pending_plan": (
                self.pending_plan.model_dump() if self.pending_plan else None
            ),
            "active_task": (
                self._active_task.status.model_dump()
                if self._active_task is not None
                and self._active_task.status.state in ("running", "pending")
                else None
            ),
            "tool_catalog": sorted(TOOL_CATALOG.keys()),
            "task_history": [t.model_dump() for t in self._task_history[-10:]],
            "memory": {
                "summary": self.memory.summary_line(),
                "preferences": dict(self.memory.preferences),
                "learned_rules": list(self.memory.learned_rules),
                "favorite_sectors": list(self.memory.favorite_sectors),
                "stats": dict(self.memory.stats),
            },
            "whatif": (
                self.whatif_snapshot() if self.pending_plan is not None else None
            ),
        }

    # --------------------- memory API (H5.1) -----------------------------

    async def remember(self, key: str, value: str) -> bool:
        key = (key or "").strip()
        value = (value or "").strip()
        if not key or not value:
            return False
        self.memory.remember(key, value)
        self._memory_store.save(self.memory)
        await self.tracer.trace_memory_update("remember", key, value)
        await self._log_system(
            f"remembered {key}={value}",
            kind="memory_update",
            payload={"op": "remember", "key": key, "value": value},
        )
        return True

    async def forget(self, key: str) -> bool:
        had = self.memory.forget(key)
        self._memory_store.save(self.memory)
        await self.tracer.trace_memory_update("forget", key)
        await self._log_system(
            f"forgot {key}" if had else f"(nothing to forget for {key!r})",
            kind="memory_update",
            payload={"op": "forget", "key": key, "existed": had},
        )
        return had

    async def add_learned_rule(self, rule: str) -> None:
        rule = (rule or "").strip()
        if not rule:
            return
        self.memory.add_learned_rule(rule)
        self._memory_store.save(self.memory)
        await self.tracer.trace_memory_update("learn", rule[:80])

    def memory_snapshot(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "summary": self.memory.summary_line(),
            "prompt_block": self.memory.prompt_block(),
            "preferences": dict(self.memory.preferences),
            "learned_rules": list(self.memory.learned_rules),
            "favorite_sectors": list(self.memory.favorite_sectors),
            "stats": dict(self.memory.stats),
            "created_at": self.memory.created_at,
            "updated_at": self.memory.updated_at,
        }

    # --------------------- what-if (H5.4) --------------------------------

    def whatif_snapshot(self) -> dict[str, Any] | None:
        """Predict the outcome of the current pending plan, if any."""
        u = self._universe_fn()
        if u is None:
            return None
        if self.pending_plan is None:
            return None
        plan = self.pending_plan.plan
        if not plan:
            return {
                "plan_id": self.pending_plan.id,
                "steps": [],
                "credit_delta": 0,
                "turn_cost": 0,
                "cargo_delta": {},
                "warnings": [],
                "one_liner": "≈ autopilot task (outcome depends on runtime)",
            }
        try:
            summary = wi.preview_plan(u, self.player_id, plan)
        except Exception as exc:  # pragma: no cover — defensive
            return {
                "plan_id": self.pending_plan.id,
                "steps": [],
                "credit_delta": 0,
                "turn_cost": 0,
                "cargo_delta": {},
                "warnings": [f"preview failed: {exc}"],
                "one_liner": "preview unavailable",
            }
        return {
            "plan_id": self.pending_plan.id,
            "one_liner": summary.one_liner(),
            **summary.model_dump(),
        }

    async def set_mode(self, mode: CopilotMode | str) -> None:
        if not isinstance(mode, CopilotMode):
            mode = CopilotMode(mode)
        self.mode = mode
        await self.tracer.trace_mode_change(mode.value)
        await self._log_system(f"mode → {mode.value}", kind="mode_change")

    async def add_standing_order(self, order: so.StandingOrder) -> None:
        # Replace-by-id so the UI can PUT the same rule repeatedly without
        # accumulating duplicates.
        self.standing_orders = [o for o in self.standing_orders if o.id != order.id]
        self.standing_orders.append(order)
        await self._log_system(
            f"standing order added: {order.summary()}",
            kind="standing_order_added",
            payload={"order": order.model_dump()},
        )

    async def remove_standing_order(self, order_id: str) -> bool:
        before = len(self.standing_orders)
        self.standing_orders = [o for o in self.standing_orders if o.id != order_id]
        ok = len(self.standing_orders) < before
        if ok:
            await self._log_system(
                f"standing order removed: {order_id}",
                kind="standing_order_removed",
                payload={"id": order_id},
            )
        return ok

    async def handle_chat(self, utterance: str) -> ChatResponse:
        """The /api/copilot/chat main entry point."""
        utterance = (utterance or "").strip()
        if not utterance:
            return ChatResponse(kind="noop", message="(empty message)")

        await self._log(role="human", text=utterance, kind="utterance")
        await self.tracer.trace_utterance(utterance, self.mode.value)

        # H5.1 — "remember X = Y" / "forget X" directives short-circuit
        # the LLM. Keeps ChatAgent free of memory-housekeeping prompts
        # and lets memory ops work even in mock-only test runs.
        remember = mem_mod.parse_remember_directive(utterance)
        if remember is not None:
            k, v = remember
            ok = await self.remember(k, v)
            resp = ChatResponse(
                kind="speak",
                message=(
                    f"Got it — I'll remember {k} = {v}."
                    if ok
                    else "(couldn't parse that remember directive)"
                ),
                thought="memory.remember",
            )
            await self._log_response(resp)
            return resp
        forget_key = mem_mod.parse_forget_directive(utterance)
        if forget_key is not None:
            had = await self.forget(forget_key)
            resp = ChatResponse(
                kind="speak",
                message=(
                    f"Forgot {forget_key}." if had else f"(nothing to forget for {forget_key!r})"
                ),
                thought="memory.forget",
            )
            await self._log_response(resp)
            return resp

        if self.mode == CopilotMode.MANUAL:
            resp = ChatResponse(
                kind="speak",
                message=(
                    "Copilot is in Manual mode — type /mode advisory to enable "
                    "suggestions, /mode delegated for one-shot execution, or "
                    "/mode autopilot for long-running tasks."
                ),
                thought="manual mode guard",
            )
            await self._log_response(resp)
            return resp

        obs = self._fetch_observation()
        if obs is None:
            resp = ChatResponse(
                kind="speak",
                message="(copilot: no observation available — is the match running?)",
            )
            await self._log_response(resp)
            return resp

        resp = await self.chat_agent.respond(utterance, obs, mode=self.mode.value)
        await self._log_response(resp)
        await self.tracer.trace_chat_response(resp.kind, resp.message, resp.thought)

        # Dispatch according to mode.
        if resp.kind == "cancel":
            await self.cancel_active_task(reason="human_chat_cancel")
            return resp

        if resp.kind == "action":
            if self.mode in (CopilotMode.DELEGATED, CopilotMode.AUTOPILOT):
                await self._execute_plan(resp.plan, plan_id=None)
            else:
                # Advisory: don't execute, just show the suggestion.
                await self._log_system(
                    f"(advisory: copilot suggests {resp.plan[0].name} — click "
                    f"the button to run it)",
                    kind="advisory",
                )
            return resp

        if resp.kind == "plan":
            pid = uuid.uuid4().hex[:8]
            self.pending_plan = PendingPlan(
                id=pid, plan=resp.plan, thought=resp.thought
            )
            await self._log_system(
                f"plan ready ({len(resp.plan)} steps) — /confirm {pid} or /cancel",
                kind="plan_preview",
                payload={"plan_id": pid, "plan": [c.model_dump() for c in resp.plan]},
            )
            if self.auto_confirm:
                await self.confirm_pending(pid)
            return resp

        if resp.kind == "start_task":
            pid = uuid.uuid4().hex[:8]
            self.pending_plan = PendingPlan(
                id=pid,
                plan=[],
                thought=resp.thought,
                task_kind=resp.task_kind,
                task_params=resp.task_params,
            )
            await self._log_system(
                f"autopilot proposal: {resp.task_kind} {resp.task_params} — "
                f"/confirm {pid} or /cancel",
                kind="task_preview",
                payload={
                    "plan_id": pid,
                    "task_kind": resp.task_kind,
                    "task_params": resp.task_params,
                },
            )
            if self.auto_confirm:
                await self.confirm_pending(pid)
            return resp

        # speak / clarify / noop — nothing to execute.
        return resp

    async def confirm_pending(self, plan_id: str) -> bool:
        pp = self.pending_plan
        if pp is None or pp.id != plan_id:
            await self._log_system(
                f"no pending plan with id {plan_id}",
                kind="confirm_rejected",
            )
            return False
        self.pending_plan = None
        # H5.1 — auto-learn: each confirmed plan reinforces its thought.
        if pp.thought:
            await self.add_learned_rule(pp.thought[:160])
        self.memory.bump_stat("plans_confirmed")
        self._memory_store.save(self.memory)
        if pp.task_kind is not None:
            await self._start_task(pp.task_kind, pp.task_params)
        else:
            await self._execute_plan(pp.plan, plan_id=pp.id)
        return True

    async def cancel_pending(self, plan_id: str | None = None) -> bool:
        pp = self.pending_plan
        if pp is None:
            return False
        if plan_id is not None and pp.id != plan_id:
            return False
        self.pending_plan = None
        await self._log_system(
            f"plan {pp.id} cancelled",
            kind="plan_cancelled",
            payload={"plan_id": pp.id},
        )
        return True

    async def cancel_active_task(self, reason: str = "human_cancel") -> bool:
        t = self._active_task
        if t is None:
            return False
        t.cancel(reason=reason)
        return True

    def safety_snapshot(self) -> dict[str, Any]:
        """Return a SafetySignal for the human's current Observation.

        Used by GET /api/copilot/safety and by the `/play` panel to
        render the escalation banner BEFORE a task is even spawned
        (e.g. when the human switches to Autopilot in a hostile sector).
        Falls back to `level="unknown"` if no match is running.
        """
        obs = self._fetch_observation()
        if obs is None:
            return {"level": "unknown", "reason": "no match running", "code": ""}
        # Pull tail of universe events for richer signals.
        u = self._universe_fn()
        tail: list[dict[str, Any]] = []
        if u is not None:
            for ev in list(u.events)[-20:]:
                tail.append(
                    {
                        "kind": ev.kind.value,
                        "actor_id": ev.actor_id,
                        "actor_kind": ev.actor_kind,
                        "summary": ev.summary,
                        "payload": dict(ev.payload or {}),
                    }
                )
        sig = safety.evaluate_observation(obs, recent_events=tail)
        return {
            "level": sig.level,
            "reason": sig.reason,
            "code": sig.code,
            "detail": sig.detail or {},
        }

    # --------------------- internals -------------------------------------

    def _fetch_observation(self) -> Observation | None:
        u = self._universe_fn()
        if u is None:
            return None
        if self.player_id not in u.players:
            return None
        # Build observation using scheduler's current event horizon. 40 is the
        # engine default for LLM agents; keep the copilot in sync.
        return build_observation(u, self.player_id, event_history=40)

    def tool_to_action(self, call: ToolCall) -> Action | tuple[None, str]:
        """Convert a ToolCall into an engine Action, or return an error tuple.

        Handles the buy/sell → TRADE and plot_course → PLOT_COURSE remappings.
        Non-action tools (planning/dialog/orchestration) return
        ``(None, reason)``. Callers must special-case those.
        """
        spec = call.spec()
        if spec is None or spec.group != "action":
            return (None, f"{call.name!r} is not an engine action tool")

        args = dict(call.arguments)
        if call.name == "buy":
            args["side"] = "buy"
            kind = ActionKind.TRADE
            if "unit_price" in args and args["unit_price"] is None:
                args.pop("unit_price")
        elif call.name == "sell":
            args["side"] = "sell"
            kind = ActionKind.TRADE
            if "unit_price" in args and args["unit_price"] is None:
                args.pop("unit_price")
        else:
            kind = ActionKind(spec.engine_action)
            # Tool schema uses `target` but TRADE uses commodity; action tools
            # already match engine args.

        return Action(
            kind=kind,
            args=args,
            thought=call.thought or f"copilot:{call.name}",
            actor_kind="copilot",
        )

    async def _execute_plan(
        self, plan: list[ToolCall], plan_id: str | None
    ) -> list[tuple[bool, str]]:
        """Submit every ToolCall in order, stopping on first rejection.

        Each step is awaited via `_dispatch_one` which blocks until the
        scheduler applies the action. Standing orders are evaluated per
        call — if ANY order blocks a step, we stop and log.
        """
        results: list[tuple[bool, str]] = []
        for i, call in enumerate(plan):
            ok, reason = await self._dispatch_one(call)
            results.append((ok, reason))
            await self._log_system(
                f"step {i + 1}/{len(plan)}: {call.name} → {'ok' if ok else reason}",
                kind="plan_step",
                payload={
                    "plan_id": plan_id,
                    "step": i + 1,
                    "tool": call.name,
                    "args": call.arguments,
                    "ok": ok,
                    "reason": reason,
                },
            )
            if not ok:
                break
        return results

    async def _dispatch_one(self, call: ToolCall) -> tuple[bool, str]:
        """Run standing-order check, convert to Action, submit, await application.

        Returns (ok, reason). On success, reason is an empty string.
        """
        # Structural validation of arguments first.
        parse_err = call.validate_against_catalog()
        if parse_err is not None:
            return (False, parse_err)

        u = self._universe_fn()
        if u is None:
            return (False, "no universe (match not running)")

        # Standing-order gate.
        verdict = so.evaluate(self.standing_orders, u, self.player_id, call)
        if not verdict.allowed:
            await self.tracer.trace_standing_order_block(
                call.name, verdict.blocked_by, verdict.reasons
            )
            await self._log_system(
                "blocked by standing order(s): " + "; ".join(verdict.reasons),
                kind="standing_order_block",
                payload={
                    "tool": call.name,
                    "args": call.arguments,
                    "blocked_by": verdict.blocked_by,
                    "reasons": verdict.reasons,
                },
            )
            return (False, "blocked by standing order: " + "; ".join(verdict.reasons))

        # Non-action tools are no-ops engine-side in H2 (planning/dialog live
        # entirely inside the copilot). Treat them as immediate success so
        # the chat flow can continue.
        spec = call.spec()
        if spec is None or spec.group != "action":
            return (True, "")

        act = self.tool_to_action(call)
        if isinstance(act, tuple):  # error tuple (None, reason)
            return (False, act[1])

        # Snapshot universe event seq before submit so we can detect which
        # events were produced by this action and report failure reasons.
        pre_seq = u.seq

        try:
            await self.human_agent.submit_action(act)
        except Exception as exc:
            return (False, f"submit failed: {exc}")

        # Wait for the scheduler to drain the queue (i.e. apply the action).
        # The scheduler advances u.seq as it emits events, so we watch for
        # it to move AND for the HumanAgent queue to be empty.
        ok, reason = await self._wait_for_applied(u, pre_seq)
        await self.tracer.trace_action_dispatched(
            call.name, dict(call.arguments), ok, reason
        )
        # H5.1 — remember sectors we've warped to, so the cockpit can
        # show "favourite" markers and the LLM can bias plans toward
        # known-good spots.
        if ok and call.name in ("warp", "plot_course"):
            tgt = call.arguments.get("target")
            if isinstance(tgt, int):
                self.memory.mark_favorite_sector(tgt)
                self._memory_store.save(self.memory)
        return (ok, reason)

    async def _wait_for_applied(
        self, u: Universe, pre_seq: int, timeout_s: float = 10.0
    ) -> tuple[bool, str]:
        """Poll until HumanAgent.pending drops to 0 and events have advanced.

        Returns (ok, reason). `ok=False` if an error event was emitted for
        this player between pre_seq and post_seq, or on timeout.
        """
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if self.human_agent.pending == 0 and u.seq > pre_seq:
                # Scan new events for this player for failure signals.
                for ev in u.events:
                    if ev.seq <= pre_seq:
                        continue
                    if ev.actor_id != self.player_id:
                        continue
                    if ev.kind.value in (
                        "trade_failed",
                        "warp_blocked",
                        "fed_response",
                        "agent_error",
                    ):
                        return (
                            False,
                            f"{ev.kind.value}: {ev.payload.get('reason') or ev.summary}",
                        )
                return (True, "")
            await asyncio.sleep(0.02)
        return (False, f"timed out after {timeout_s:.0f}s waiting for scheduler")

    async def _start_task(self, kind: str, params: dict[str, Any]) -> None:
        # Abort any existing task first.
        await self.cancel_active_task(reason="replaced_by_new_task")
        status = TaskStatus(id=uuid.uuid4().hex[:8], kind=kind, params=dict(params))

        async def dispatch(call: ToolCall) -> tuple[bool, str]:
            return await self._dispatch_one(call)

        def obs_fn() -> Observation:
            o = self._fetch_observation()
            if o is None:
                raise RuntimeError("observation unavailable (match stopped)")
            return o

        # H4: track the timestamp of the last progress emission per-task for
        # the idle-report watchdog.
        last_progress_ts = [time.time()]

        async def report(kind_: str, payload: dict[str, Any]) -> None:
            last_progress_ts[0] = time.time()
            await self._log_system(
                f"task {status.id}: {kind_}",
                kind=kind_,
                payload=payload,
            )

        async def on_escalation(sig: safety.SafetySignal) -> None:
            """Critical safety signal → switch to ADVISORY + emit escalation.

            The UI listens for `kind=escalation` messages and raises a
            modal banner + triggers urgent TTS. Switching to ADVISORY
            stops the copilot from auto-dispatching further actions
            until the human confirms they want to keep going.
            """
            await self.tracer.trace_escalation(sig.reason, sig.code)
            await self._log_system(
                safety.describe_short(sig)
                or f"escalation: {sig.reason} — switching to advisory mode",
                kind="escalation",
                payload={
                    "level": sig.level,
                    "code": sig.code,
                    "reason": sig.reason,
                    "detail": sig.detail or {},
                    "task_id": status.id,
                },
            )
            # Force the mode back so subsequent human utterances don't auto-
            # dispatch while the human is reading the banner.
            if self.mode == CopilotMode.AUTOPILOT:
                await self.set_mode(CopilotMode.ADVISORY)

        task = TaskAgent(
            status,
            obs_fn=obs_fn,
            dispatch_fn=dispatch,
            next_step_fn=self._task_next_step_factory(),
            report_fn=report,
            iter_delay_s=self._iter_delay_s,
            safety_fn=safety.evaluate_observation,
            on_escalation=on_escalation,
        )
        self._active_task = task

        # H4: idle-report watchdog — if no progress for `idle_report_s`, push
        # a one-liner status so the voice channel doesn't go silent while
        # the LLM is thinking. Cancels automatically when the task finishes.
        idle_report_s = 7.5

        async def idle_watchdog() -> None:
            try:
                while self._active_task is task and task.status.state in (
                    "pending",
                    "running",
                ):
                    await asyncio.sleep(idle_report_s / 2)
                    gap = time.time() - last_progress_ts[0]
                    if gap >= idle_report_s:
                        last_progress_ts[0] = time.time()
                        msg = (
                            f"still on it — iter {task.status.iterations}"
                            + (
                                f", last action {task.status.last_action}"
                                if task.status.last_action
                                else ""
                            )
                        )
                        await self._log_system(
                            msg,
                            kind="task_idle",
                            payload={
                                "task_id": status.id,
                                "idle_s": round(gap, 1),
                                "iterations": task.status.iterations,
                                "last_action": task.status.last_action,
                            },
                        )
            except asyncio.CancelledError:
                return
            except Exception:  # pragma: no cover
                return

        watchdog_task = asyncio.create_task(
            idle_watchdog(), name=f"tw2k-idle-watchdog-{status.id}"
        )

        async def runner() -> TaskStatus:
            try:
                return await task.run()
            finally:
                watchdog_task.cancel()
                try:
                    await watchdog_task
                except (asyncio.CancelledError, Exception):
                    pass
                self._task_history.append(status)
                if self._active_task is task:
                    self._active_task = None

        self._task_handle = asyncio.create_task(runner())

    # --------------------- chat log helpers ------------------------------

    async def _log_response(self, resp: ChatResponse) -> None:
        if resp.kind == "action" and resp.plan:
            c = resp.plan[0]
            text = f"→ {c.name}({c.arguments})"
            kind = "action"
            payload = {"tool": c.name, "args": c.arguments}
        elif resp.kind == "plan":
            text = f"plan ({len(resp.plan)} steps): " + " → ".join(
                c.name for c in resp.plan
            )
            kind = "plan"
            payload = {"plan": [c.model_dump() for c in resp.plan]}
        elif resp.kind == "start_task":
            text = f"autopilot: {resp.task_kind} {resp.task_params}"
            kind = "start_task"
            payload = {"task_kind": resp.task_kind, "task_params": resp.task_params}
        elif resp.kind == "clarify":
            text = f"? {resp.message}"
            kind = "clarify"
            payload = {"options": resp.options}
        elif resp.kind == "cancel":
            text = "cancel"
            kind = "cancel"
            payload = {}
        else:
            text = resp.message
            kind = resp.kind
            payload = {}
        await self._log(
            role="copilot", text=text, kind=kind, payload=payload, thought=resp.thought
        )

    async def _log_system(
        self, text: str, *, kind: str = "system", payload: dict[str, Any] | None = None
    ) -> None:
        await self._log(role="system", text=text, kind=kind, payload=payload or {})

    async def _log(
        self,
        *,
        role: str,
        text: str,
        kind: str,
        payload: dict[str, Any] | None = None,
        thought: str = "",
    ) -> None:
        msg = ChatMessage(
            id=uuid.uuid4().hex[:8],
            role=role,
            text=text,
            kind=kind,
            payload=dict(payload or {}, **({"thought": thought} if thought else {})),
        )
        self.chat_history.append(msg)
        # Broadcast to the /play WS. The cockpit frontend renders these
        # incrementally without polling GET /api/copilot/state.
        await self._broadcast_fn(
            {
                "type": "copilot_chat",
                "player_id": self.player_id,
                "message": msg.model_dump(),
            }
        )
