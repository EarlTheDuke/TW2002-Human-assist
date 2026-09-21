"""ExternalAgent — a seat driven by an out-of-process bot over REST.

Plan: docs/plans/2026-09-20-external-harness.md (§1, §2.1).

The agent plugs into the same ``BaseAgent.act(Observation) -> Action``
contract as heuristic / LLM / human agents. It is ``HumanAgent`` plus:

* ``turn_seq`` — increments every time the scheduler enters ``act()``. A
  bot must echo the current value when it POSTs, so a slow reply meant
  for an earlier turn is rejected instead of being applied out of context.
* ``turn_due`` — an ``asyncio.Event`` the REST layer long-polls on, so a
  bot can block on "is it my turn?" without hammering the server.
* ``token`` — the per-seat bearer secret. Stored on the instance only;
  never serialized into meta.json, events, or snapshots.
* ``last_result`` — the engine's verdict on the previous action, recorded
  by the runner so the bot can see "warp ok" / "not enough turns" on its
  next status call without parsing the event feed.

The agent does **not** enforce a timeout itself. The runner owns the
deadline (``MatchSpec.external_timeout_s``) exactly the way it owns
``human_deadline_s`` — on timeout it synthesizes a WAIT and emits
AGENT_ERROR. Keeping the deadline in one place means replay, tests and
the spectator all agree about who decided the bot was too slow.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ..engine import Action, Observation
from .base import BaseAgent


class HarnessError(RuntimeError):
    """Base class for seat-submission errors the REST layer maps to 4xx."""


class NotYourTurnError(HarnessError):
    """Scheduler is not blocked on this seat right now."""


class StaleTurnError(HarnessError):
    """The submitted ``turn_seq`` does not match the current turn."""

    def __init__(self, submitted: int, current: int) -> None:
        super().__init__(f"stale turn_seq {submitted}; current turn_seq is {current}")
        self.submitted = submitted
        self.current = current


class QueueFullError(HarnessError):
    """An action for this turn has already been accepted."""


class ExternalAgent(BaseAgent):
    kind = "external"

    def __init__(self, player_id: str, name: str, *, token: str = "") -> None:
        super().__init__(player_id, name)
        # Exactly one action per turn. A second POST for the same turn is a
        # client bug and gets QueueFullError rather than silently queueing.
        self._queue: asyncio.Queue[Action] = asyncio.Queue(maxsize=1)
        self._token: str = token or ""
        self.turn_seq: int = 0
        self.awaiting_input: bool = False
        self.turn_started_at: float | None = None
        self.turn_due: asyncio.Event = asyncio.Event()
        self.current_observation: Observation | None = None
        self.last_result: dict[str, Any] | None = None
        self.closed: bool = False

    # ---- auth ------------------------------------------------------------

    @property
    def token(self) -> str:
        return self._token

    def set_token(self, token: str) -> None:
        self._token = token or ""

    # ---- inbound: REST layer / tests --------------------------------------

    async def submit_action(self, action: Action, turn_seq: int | None = None) -> int:
        """Accept the action for the current turn. Returns the turn_seq it was bound to."""
        if not self.awaiting_input:
            raise NotYourTurnError(f"seat {self.player_id} is not awaiting input")
        if turn_seq is not None and int(turn_seq) != self.turn_seq:
            raise StaleTurnError(int(turn_seq), self.turn_seq)
        if self._queue.full():
            raise QueueFullError(f"seat {self.player_id} already has an action for turn {self.turn_seq}")
        # Bots may never impersonate the copilot path.
        action.actor_kind = None
        await self._queue.put(action)
        return self.turn_seq

    async def wait_for_turn(self, timeout_s: float) -> bool:
        """Long-poll helper. True once ``act()`` has been entered for a new turn."""
        if self.awaiting_input:
            return True
        if timeout_s <= 0:
            return False
        try:
            await asyncio.wait_for(self.turn_due.wait(), timeout=timeout_s)
        except TimeoutError:
            return False
        return self.awaiting_input

    def record_result(self, ok: bool, error: str | None, event_seqs: list[int]) -> None:
        self.last_result = {
            "turn_seq": self.turn_seq,
            "ok": bool(ok),
            "error": error or None,
            "event_seqs": list(event_seqs),
            "recorded_at": time.time(),
        }

    @property
    def pending(self) -> int:
        return self._queue.qsize()

    def status(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "awaiting_input": self.awaiting_input,
            "turn_seq": self.turn_seq,
            "turn_started_at": self.turn_started_at,
            "pending": self.pending,
            "last_result": self.last_result,
        }

    # ---- outbound: scheduler ---------------------------------------------

    async def act(self, observation: Observation) -> Action:
        self.turn_seq += 1
        self.current_observation = observation
        self.turn_started_at = time.time()
        self.awaiting_input = True
        self.turn_due.set()
        try:
            return await self._queue.get()
        finally:
            # Runs on normal return, on the runner's wait_for timeout
            # (CancelledError into queue.get), and on match stop.
            self.awaiting_input = False
            self.turn_due.clear()
            self.current_observation = None
            self._drain()

    def _drain(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def close(self) -> None:
        self.closed = True
        self.awaiting_input = False
        # Wake any long-pollers so they can observe `closed` and return.
        self.turn_due.set()
        self._drain()
