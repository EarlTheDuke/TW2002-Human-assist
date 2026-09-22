"""ExternalAgent â€” a seat driven by an out-of-process bot over REST.

Plan: docs/plans/2026-09-20-external-harness.md (Â§1, Â§2.1).

The agent plugs into the same ``BaseAgent.act(Observation) -> Action``
contract as heuristic / LLM / human agents. It is ``HumanAgent`` plus:

* ``turn_seq`` â€” increments every time the scheduler enters ``act()``. A
  bot must echo the current value when it POSTs, so a slow reply meant
  for an earlier turn is rejected instead of being applied out of context.
* ``turn_due`` â€” an ``asyncio.Event`` the REST layer long-polls on, so a
  bot can block on "is it my turn?" without hammering the server.
* ``token`` â€” the per-seat bearer secret. Stored on the instance only;
  never serialized into meta.json, events, or snapshots.
* ``last_result`` â€” the engine's verdict on the previous action, recorded
  by the runner so the bot can see "warp ok" / "not enough turns" on its
  next status call without parsing the event feed.

The agent does **not** enforce a timeout itself. The runner owns the
deadline (``MatchSpec.external_timeout_s``) exactly the way it owns
``human_deadline_s`` â€” on timeout it synthesizes a WAIT and emits
AGENT_ERROR. Keeping the deadline in one place means replay, tests and
the spectator all agree about who decided the bot was too slow.
"""

from __future__ import annotations

import asyncio
import os
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
        # Wall-clock of the last authenticated harness request for this seat.
        # The runner uses it to tell an *attended* seat (a bot / the /bot
        # page is polling) from an *unattended* one, so idle seats can
        # auto-WAIT quickly instead of burning the full external timeout.
        self.last_client_seen_at: float | None = None
        # Effective wall-clock deadline for the current turn, set by the runner
        # immediately before `act()` (already includes the idle-wait rule).
        # Surfaced to bots via the turn_due webhook and harness status.
        self.turn_deadline_at: float | None = None

    # ---- attendance --------------------------------------------------------

    def touch_client(self) -> None:
        self.last_client_seen_at = time.time()

    def is_attended(self, window_s: float) -> bool:
        if self.last_client_seen_at is None or window_s <= 0:
            return False
        return (time.time() - self.last_client_seen_at) <= window_s

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
            "last_client_seen_at": self.last_client_seen_at,
        }

    # ---- outbound: scheduler ---------------------------------------------

    def _webhook_urls(self) -> list[str]:
        urls: list[str] = []
        per = (os.environ.get(f"TW2K_GROKBOT_WEBHOOK_{self.player_id}") or "").strip()
        if per:
            urls.append(per)
        shared = (os.environ.get("TW2K_GROKBOT_WEBHOOK_URL") or "").strip()
        if shared and shared not in urls:
            urls.append(shared)
        return urls

    @staticmethod
    def _base_url() -> str:
        """Where the bot should call back. Public tunnel URL if the host set one."""
        for key in ("TW2K_PUBLIC_BASE_URL", "TW2K_HARNESS_BASE_URL"):
            v = (os.environ.get(key) or "").strip()
            if v:
                return v.rstrip("/")
        return "http://127.0.0.1:8000"

    def turn_due_payload(self, observation: Observation) -> dict[str, Any]:
        """Webhook body (Parity S1 / F8).

        * `deadline_at` is the runner's *effective* deadline for this turn
          (`turn_deadline_at`, set by the scheduler right before `act()`, so it
          already reflects the idle-wait rule). Falls back to the env timeout
          only if the runner did not set it (tests / direct use).
        * The full Observation is NOT sent: the bot pulls it with its own token
          from `base_url` (`GET /harness/v1/{pid}/observation`). Set
          `TW2K_GROKBOT_WEBHOOK_FULL_OBS=1` to restore the old fat payload.
        """
        started = self.turn_started_at or time.time()
        deadline = self.turn_deadline_at
        if deadline is None:
            try:
                deadline = started + float(os.environ.get("TW2K_EXTERNAL_TIMEOUT_S", "180"))
            except ValueError:
                deadline = started + 180.0
        sector = observation.sector or {}
        payload: dict[str, Any] = {
            "event": "turn_due",
            "player_id": self.player_id,
            "name": self.name,
            "turn_seq": self.turn_seq,
            "started_at": started,
            "deadline_at": deadline,
            "base_url": self._base_url(),
            "observation_url": f"{self._base_url()}/harness/v1/{self.player_id}/observation",
            "action_url": f"{self._base_url()}/harness/v1/{self.player_id}/action",
            "brief": {
                "day": observation.day,
                "tick": observation.tick,
                "sector_id": sector.get("id"),
                "turns_remaining": observation.turns_remaining,
                "credits": observation.credits,
            },
        }
        if (os.environ.get("TW2K_GROKBOT_WEBHOOK_FULL_OBS") or "").strip().lower() in ("1", "true", "yes"):
            payload["observation"] = observation.model_dump(mode="json")
        return payload

    async def _fire_turn_due_webhook(self, observation: Observation) -> None:
        """Notify Grok Bot (webhook routine) that this seat needs a decision."""
        urls = self._webhook_urls()
        if not urls:
            return
        try:
            import httpx
        except ImportError:
            return
        payload = self.turn_due_payload(observation)
        async with httpx.AsyncClient(timeout=8.0) as client:
            for url in urls:
                try:
                    await client.post(url, json=payload)
                except Exception:
                    # Never block the match on notify failure.
                    pass

    async def act(self, observation: Observation) -> Action:
        self.turn_seq += 1
        self.current_observation = observation
        self.turn_started_at = time.time()
        self.awaiting_input = True
        self.turn_due.set()
        # Fire-and-forget; keep a reference so the task isn't GC'd mid-flight.
        self._webhook_task = asyncio.create_task(self._fire_turn_due_webhook(observation))
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

