"""Human-driven agents — Phase H0.

This module adds two agents that plug into the same `BaseAgent.act()`
contract the match runner already uses for heuristic and LLM agents:

  * HumanAgent          — blocks on an asyncio.Queue until the server
                          endpoint (POST /api/human/action) pushes the
                          next Action. This is the real cockpit path.
  * ScriptedHumanAgent  — dequeues from a pre-seeded list in order. Used
                          by tests and headless fixtures so we can
                          exercise the scheduler-waits-for-human code
                          path without spinning up FastAPI.

Both set `kind = "human"` so the scheduler can detect them and the UI
can render the right banner. Neither touches the engine directly —
they only produce Action objects; the scheduler calls apply_action
exactly the same way it does for autonomous agents. This keeps the
determinism / replay / save-sink plumbing working without special
human code paths inside apply_action.
"""

from __future__ import annotations

import asyncio
from typing import Any

from ..engine import Action, ActionKind, Observation
from .base import BaseAgent


class HumanAgent(BaseAgent):
    """Runner-side proxy for an interactive human player.

    Lifecycle (per turn):
      1. Match runner detects `agent.kind == "human"`.
      2. Runner emits HUMAN_TURN_START and calls `await agent.act(obs)`.
      3. `act()` blocks on `self._queue.get()` until somebody calls
         `agent.submit_action(action)` — typically the FastAPI route
         `/api/human/action` invoked by the /play cockpit UI.
      4. The dequeued Action is returned; runner calls apply_action as
         normal. If the action is invalid the engine's TRADE_FAILED /
         WARP_BLOCKED / AGENT_ERROR paths fire exactly as they would
         for an LLM — the human sees the error and tries again.

    Why a queue and not just a Future or Event?
      * Allows the player to QUEUE a second action while the first is
        still being resolved by the engine (no lost submissions during
        the event-broadcast round trip).
      * Survives scheduler quirks (spurious retries, pause/resume)
        without needing careful state machines.

    Cancellation:
      `MatchRunner.stop()` cancels the outer match task. asyncio
      propagates CancelledError into `queue.get()` cleanly; the
      scheduler catches it at the top of its loop and exits. No
      sentinel object needed.
    """

    kind = "human"

    def __init__(
        self,
        player_id: str,
        name: str,
        *,
        queue_maxsize: int = 16,
    ) -> None:
        super().__init__(player_id, name)
        # Bounded queue so a runaway script can't memory-balloon the
        # server. Typical human throughput is <1 action/sec; 16 is
        # plenty of headroom. If the queue fills, submit_action raises
        # so the UI can show "too many pending commands".
        self._queue: asyncio.Queue[Action] = asyncio.Queue(maxsize=queue_maxsize)
        # Metadata about the *last* action the scheduler dispatched for
        # this player. Surfaced through the REST API so the /play UI
        # can render "waiting" / "executing" / "applied" states without
        # parsing the event feed.
        self.last_observation_seq: int = 0

    # ---- inbound: called by the FastAPI endpoint (or tests) ----

    async def submit_action(self, action: Action) -> None:
        """Push an Action into the queue. Raises if the queue is full.

        Async because asyncio.Queue.put is async; callers (the FastAPI
        route, the /play UI test harness) are in an event loop anyway.
        """
        if self._queue.full():
            raise RuntimeError(
                f"human agent {self.player_id} queue full "
                f"({self._queue.maxsize} pending) — slow down or let "
                f"the scheduler drain."
            )
        await self._queue.put(action)

    def submit_action_nowait(self, action: Action) -> None:
        """Non-async variant for synchronous test paths."""
        self._queue.put_nowait(action)

    @property
    def pending(self) -> int:
        return self._queue.qsize()

    def drop_leading_waits(self) -> int:
        """Remove any contiguous run of WAIT actions from the head of the queue.

        Called by the scheduler after its 4-wait auto-end-day guard fires.
        Without this, queued waits sitting behind productive actions (scan,
        warp, attack, build_citadel, ...) re-trigger the same guard on the
        next day, stalling the productive action for multiple days until
        the wait streak drains. This is the M2-7 regression.

        Returns the number of waits dropped (for logging / tests).
        """
        drained: list[Action] = []
        while not self._queue.empty():
            try:
                drained.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        dropped = 0
        while drained and drained[0].kind == ActionKind.WAIT:
            drained.pop(0)
            dropped += 1
        for action in drained:
            try:
                self._queue.put_nowait(action)
            except asyncio.QueueFull:
                break
        return dropped

    def clear_queue(self) -> int:
        """Drop every pending action. Returns the count dropped.

        Used by the admin-facing ``DELETE /api/human/queue`` endpoint to
        recover from a stuck external client (M2-8). Safe to call while
        ``act()`` is blocked on ``queue.get()`` — that coroutine just
        keeps waiting for the next push.
        """
        dropped = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                dropped += 1
            except asyncio.QueueEmpty:
                break
        return dropped

    # ---- outbound: called by the match runner's main loop ----

    async def act(self, observation: Observation) -> Action:
        self.last_observation_seq = int(getattr(observation, "seq", 0) or 0)
        action = await self._queue.get()
        return action

    async def close(self) -> None:
        # Drain any pending actions so a subsequent re-start doesn't
        # inherit stale submissions. We don't need to set any stop
        # flag — runner.stop() cancels the enclosing task, which
        # propagates CancelledError through the awaiting queue.get.
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break


class ScriptedHumanAgent(BaseAgent):
    """Deterministic human stand-in for tests and headless fixtures.

    Dequeues from a pre-seeded list in order. After the list is
    exhausted, returns WAIT forever so the scheduler can run the rest
    of the match to completion without blocking indefinitely.

    Accepts either pre-built `Action` objects or plain dicts that
    `Action.model_validate()` will accept — so tests can spell their
    scripts as `[{"kind": "warp", "args": {"to": 7}}, ...]`.
    """

    kind = "human"

    def __init__(
        self,
        player_id: str,
        name: str,
        actions: list[Action | dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(player_id, name)
        self._actions: list[Action] = []
        for a in actions or []:
            if isinstance(a, Action):
                self._actions.append(a)
            else:
                self._actions.append(Action.model_validate(a))
        self._idx: int = 0
        # Tracks how many times we've WAIT-padded past end-of-script.
        # Tests can assert this is zero to catch "script too short for
        # the match horizon" bugs.
        self.wait_pads: int = 0

    async def act(self, observation: Observation) -> Action:
        if self._idx >= len(self._actions):
            self.wait_pads += 1
            return Action(kind=ActionKind.WAIT)
        action = self._actions[self._idx]
        self._idx += 1
        return action

    @property
    def remaining(self) -> int:
        return max(0, len(self._actions) - self._idx)
