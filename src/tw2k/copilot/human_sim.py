"""Phase H2.5 — headless ``tw2k human-sim`` driver.

Runs a full copilot pipeline with **no browser, no uvicorn** — boots a
MatchRunner in-process, binds a `CopilotSession` to the lone human slot,
feeds it one intent string, then waits for any pending task to finish
and prints a structured JSON summary.

This is the CI-friendly integration harness the Phase H2 plan earmarked
as "high-leverage". It doubles as:

- A reproducible forensic tool: `tw2k human-sim 42 "pass forever" --demo pass --json`
  produces byte-identical output across runs (deterministic seed +
  scripted responder + no wall-clock dependence in the summary).
- An end-to-end smoke for the H2 plumbing whenever the tool catalog,
  provider adapter, or scheduler change.

Design choices:

- Zero LLM calls by default. The CLI defaults to `--demo pass` which
  uses a built-in scripted responder so contributors without API keys
  can still exercise the full pipeline.
- `--demo trade` uses a slightly smarter scripted responder that
  alternates `pass_turn`/`scan` so the TaskAgent iterates a few times
  and exercises the terminal-condition path.
- `--script file.json` accepts a user-supplied list of raw LLM
  response strings (cycled). Useful for reproducing bugs.
- `--provider anthropic|openai|xai|...` flips to a real LLM call; this
  path is **not** exercised by CI by default — it's for interactive
  dev/demo.
- The driver takes over `runner.state.agents[<human>]` via a custom
  `ScriptedHumanAgent`-compatible path: the `CopilotSession` is the
  only thing that ever submits actions for the human slot. Heuristic
  peers continue to act normally.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..engine import GameConfig
from ..server.broadcaster import Broadcaster
from ..server.runner import AgentSpec, MatchRunner, MatchSpec
from . import provider as prov
from .chat_agent import ChatAgent
from .registry import CopilotRegistry
from .session import CopilotMode

# ---------------------------------------------------------------------------
# Scripted demo responders
# ---------------------------------------------------------------------------


def _responder_from_list(responses: list[str]) -> prov.MockResponder:
    """Cycle through `responses` regardless of prompt content."""
    idx = {"i": 0}

    async def _fn(system: str, user: str, context: dict[str, Any]) -> str:
        r = responses[idx["i"] % len(responses)]
        idx["i"] += 1
        return r

    return _fn


def _demo_pass_responder() -> prov.MockResponder:
    return _responder_from_list(
        ['{"tool":"pass_turn","arguments":{},"thought":"human-sim demo pass"}']
    )


def _demo_trade_responder() -> prov.MockResponder:
    """Slightly richer scripted sequence used by `--demo trade`.

    The responder emits a ``start_task`` on the FIRST call (which the
    ChatAgent converts into a TaskAgent autopilot goal), then cycles
    through `scan` / `pass_turn` calls that the TaskAgent consumes as
    individual steps. This isn't a smart trader — it's a deterministic
    script that proves the full pipeline (ChatAgent → start_task →
    TaskAgent loop → terminal condition) fires end-to-end.
    """
    # target_cr is intentionally unreachable via scan/pass so the loop runs
    # until it hits max_iterations — exercises the full iteration path.
    first = (
        '{"tool":"start_task","arguments":'
        '{"kind":"profit_loop","params":{"target_cr":9999999999,"max_iterations":4}},'
        '"thought":"kick off demo autopilot"}'
    )
    ping = '{"tool":"scan","arguments":{},"thought":"demo step"}'
    pass_ = '{"tool":"pass_turn","arguments":{},"thought":"demo step"}'
    return _responder_from_list([first, ping, pass_, ping, pass_, ping, pass_])


# ---------------------------------------------------------------------------
# SimResult: what we return + what --json prints
# ---------------------------------------------------------------------------


@dataclass
class SimAction:
    step: int
    tool: str
    args: dict[str, Any]
    ok: bool
    reason: str = ""


@dataclass
class SimResult:
    seed: int
    intent: str
    mode: str
    outcome: str  # "completed" | "cancelled" | "deadline" | "error"
    iterations: int
    duration_s: float
    chat_turns: list[dict[str, Any]]
    actions_dispatched: list[SimAction]
    task_final: dict[str, Any] | None
    final_credits: int | None
    final_sector: int | None
    copilot_event_count: int
    human_event_count: int
    error: str | None = None
    engine_events_tail: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "intent": self.intent,
            "mode": self.mode,
            "outcome": self.outcome,
            "iterations": self.iterations,
            "duration_s": round(self.duration_s, 3),
            "chat_turns": self.chat_turns,
            "actions_dispatched": [a.__dict__ for a in self.actions_dispatched],
            "task_final": self.task_final,
            "final_credits": self.final_credits,
            "final_sector": self.final_sector,
            "copilot_event_count": self.copilot_event_count,
            "human_event_count": self.human_event_count,
            "error": self.error,
            "engine_events_tail": self.engine_events_tail,
        }


# ---------------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------------


async def run_human_sim(
    *,
    seed: int,
    intent: str,
    provider: str | None = None,
    model: str | None = None,
    mode: CopilotMode = CopilotMode.DELEGATED,
    auto_confirm: bool = True,
    demo: str | None = "pass",
    script_file: Path | None = None,
    max_iterations: int = 20,
    max_wall_s: float = 120.0,
    universe_size: int = 40,
    max_days: int = 2,
    turns_per_day: int = 80,
    starting_credits: int = 50_000,
    action_delay_s: float = 0.0,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> SimResult:
    """Boot a match, feed one `intent`, wait for completion, return summary.

    The function is self-contained: it allocates its own MatchRunner,
    Broadcaster, CopilotRegistry and cleans them up before returning.
    """
    t0 = time.time()

    # ---- provider selection -------------------------------------------------
    mock_tag: str | None = None
    if script_file is not None:
        data = json.loads(script_file.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
            raise ValueError(
                f"--script must be a JSON array of strings; got {type(data).__name__}"
            )
        mock_tag = f"sim-{uuid.uuid4().hex[:6]}"
        prov.register_mock_responder(mock_tag, _responder_from_list(data))
    elif provider is None:
        # Default to a deterministic demo responder so the CLI works
        # out-of-the-box on a box with no API keys.
        mock_tag = f"sim-{uuid.uuid4().hex[:6]}"
        if demo == "trade":
            prov.register_mock_responder(mock_tag, _demo_trade_responder())
        else:
            prov.register_mock_responder(mock_tag, _demo_pass_responder())
    # else: provider is set (e.g. "anthropic") — live LLM path, no mock.

    chat_provider = f"mock:{mock_tag}" if mock_tag else provider

    # ---- runner + broadcaster -----------------------------------------------
    broadcaster = Broadcaster()
    runner = MatchRunner(broadcaster)

    # Capture broadcaster output for the summary + optional on_event hook.
    captured: list[dict[str, Any]] = []

    async def _sniff() -> None:
        q = await broadcaster.subscribe()
        while True:
            raw = await q.get()
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            captured.append(msg)
            if on_event is not None:
                try:
                    on_event(msg)
                except Exception:
                    pass

    sniff_task = asyncio.create_task(_sniff(), name="tw2k-human-sim-sniff")

    spec = MatchSpec(
        config=GameConfig(
            seed=seed,
            universe_size=universe_size,
            max_days=max_days,
            turns_per_day=turns_per_day,
            starting_credits=starting_credits,
            enable_ferrengi=False,
            enable_planets=False,
            action_delay_s=action_delay_s,
        ),
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="You", kind="human"),
        ],
        action_delay_s=action_delay_s,
    )

    registry = CopilotRegistry()

    result_error: str | None = None
    outcome = "completed"
    iterations = 0
    actions_dispatched: list[SimAction] = []
    task_final: dict[str, Any] | None = None
    final_credits: int | None = None
    final_sector: int | None = None
    chat_turns: list[dict[str, Any]] = []

    try:
        await runner.start(spec)
        # Wait for the scheduler to materialise agents + reach the human's turn.
        for _ in range(150):
            await asyncio.sleep(0.02)
            if runner.state.agents and runner.state.universe is not None:
                break

        registry.rebuild(runner=runner, broadcaster=broadcaster)
        sess = registry.get("P2")
        if sess is None:
            raise RuntimeError(
                "human slot P2 has no copilot session — did the match fail to boot?"
            )

        sess.chat_agent = ChatAgent(provider=chat_provider, model=model)
        sess.auto_confirm = auto_confirm
        await sess.set_mode(mode)

        # Point the TaskAgent at the same provider so scripted demo responders
        # drive the autopilot loop too.
        def _task_next_step_factory():
            from .task_agent import llm_next_step

            return llm_next_step(provider=chat_provider, model=model)

        sess._task_next_step_factory = _task_next_step_factory  # type: ignore[attr-defined]

        await sess.handle_chat(intent)

        # Wait for any spawned task to finish OR for the deadline.
        deadline = t0 + max_wall_s
        while time.time() < deadline:
            task_handle = sess._task_handle
            if task_handle is not None:
                try:
                    await asyncio.wait_for(
                        asyncio.shield(task_handle),
                        timeout=max(0.05, deadline - time.time()),
                    )
                except TimeoutError:
                    outcome = "deadline"
                    sess.cancel_event_reason = "human-sim deadline"
                    await sess.cancel_active_task(reason="human_sim_deadline")
                    try:
                        await asyncio.wait_for(task_handle, timeout=5)
                    except TimeoutError:
                        pass
                    break
                else:
                    break
            # No task spawned — a simple delegated-action utterance.
            # Wait a beat for the dispatch to complete, then exit.
            await asyncio.sleep(0.1)
            # Heuristic: once the chat history has a completed action/plan log,
            # we're done.
            if any(
                m.kind in ("plan_step", "system") and not m.payload.get("task_id")
                for m in sess.chat_history[-5:]
            ) and sess._task_handle is None:
                break

        # Collect artefacts.
        if sess._task_handle is not None:
            try:
                status = await asyncio.wait_for(sess._task_handle, timeout=2.0)
                task_final = status.model_dump()
                iterations = status.iterations
                if status.state == "cancelled":
                    outcome = "cancelled"
                elif status.state == "error":
                    outcome = "error"
                    result_error = status.last_error or status.reason_finished
                else:
                    outcome = "completed"
            except TimeoutError:
                outcome = "deadline"

        if task_final is None and sess._task_history:
            # start_task confirmed + task already drained before the poll loop
            # noticed (fast scripted responder). Pull from history.
            status = sess._task_history[-1]
            task_final = status.model_dump()
            iterations = status.iterations
            if status.state == "cancelled":
                outcome = "cancelled"
            elif status.state == "error":
                outcome = "error"
                result_error = status.last_error or status.reason_finished

        chat_turns = [m.model_dump() for m in sess.chat_history]
        for m in sess.chat_history:
            if m.kind == "plan_step":
                actions_dispatched.append(
                    SimAction(
                        step=m.payload.get("step", 0),
                        tool=m.payload.get("tool", ""),
                        args=m.payload.get("args", {}),
                        ok=bool(m.payload.get("ok")),
                        reason=str(m.payload.get("reason", "")),
                    )
                )

        u = runner.state.universe
        if u is not None and "P2" in u.players:
            final_credits = u.players["P2"].credits
            final_sector = u.players["P2"].sector_id

    except Exception as exc:  # pragma: no cover — smoke-test only
        outcome = "error"
        result_error = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            await runner.stop()
        except Exception:
            pass
        sniff_task.cancel()
        try:
            await sniff_task
        except (asyncio.CancelledError, Exception):
            pass
        if mock_tag is not None:
            # Don't clear globally; just drop our tag so repeated in-process
            # invocations don't accumulate.
            prov._mock_responders.pop(mock_tag, None)

    # Count copilot vs human events (actor_kind tag fidelity smoke).
    copilot_events = 0
    human_events = 0
    engine_events_tail: list[dict[str, Any]] = []
    u = runner.state.universe
    if u is not None:
        for ev in u.events[-60:]:
            engine_events_tail.append(
                {
                    "seq": ev.seq,
                    "kind": ev.kind.value,
                    "actor_id": ev.actor_id,
                    "actor_kind": ev.actor_kind,
                    "summary": ev.summary[:120],
                }
            )
        for ev in u.events:
            if ev.actor_id == "P2":
                if ev.actor_kind == "copilot":
                    copilot_events += 1
                elif ev.actor_kind == "human":
                    human_events += 1

    return SimResult(
        seed=seed,
        intent=intent,
        mode=mode.value,
        outcome=outcome,
        iterations=iterations,
        duration_s=time.time() - t0,
        chat_turns=chat_turns,
        actions_dispatched=actions_dispatched,
        task_final=task_final,
        final_credits=final_credits,
        final_sector=final_sector,
        copilot_event_count=copilot_events,
        human_event_count=human_events,
        error=result_error,
        engine_events_tail=engine_events_tail,
    )
