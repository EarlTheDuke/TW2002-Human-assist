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
import json
import logging
import os
import time
from collections import deque
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ..engine import Action, Observation
from ..engine.observation import status_fields
from .base import BaseAgent

log = logging.getLogger("tw2k.webhook")


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


class SlotReleased(Exception):  # noqa: N818 - control flow, not an error
    """G4 hold-my-slot: the seat ended its held scheduler slot without acting."""


_RELEASE = object()  # queue sentinel for SlotReleased
WEBHOOK_RETRY_DELAYS_S = (1.0, 2.0, 4.0)  # backoff between the 4 delivery attempts


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
        # Wall-clock of the last harness status or observation poll. Seat-drop
        # pause uses only this, not every authenticated request.
        self.last_poll_at: float | None = None
        # Effective wall-clock deadline for the current turn, set by the runner
        # immediately before `act()` (already includes the idle-wait rule).
        # Surfaced to bots via the turn_due webhook and harness status.
        self.turn_deadline_at: float | None = None
        # G4 per-seat deadline (None = MatchSpec.external_timeout_s).
        self.timeout_s: float | None = None
        # G4 hold-my-slot. While `hold_slot` is set the runner hands this seat
        # the next action right after the previous one (up to `hold_max`);
        # `hold_count` is how many continuation turns the current slot used.
        self.hold_slot: bool = False
        self.hold_count: int = 0
        self.hold_max: int = 0
        # G4 webhook delivery log (last 50 attempts) + optional JSONL sink the
        # runner points at the match save dir.
        self.webhook_log: deque[dict[str, Any]] = deque(maxlen=50)
        self.webhook_log_path: Path | None = None
        # G5 per-action log (runner points it at saves/<run>/external_actions.jsonl).
        self.action_log_path: Path | None = None
        self._posts: int = 0
        self._submitted_at: float | None = None
        # G6 run_route macro + slot digest.
        self.macro: dict[str, Any] | None = None
        self.macro_stop: str | None = None
        self._macro_used: bool = False
        self._slot_base: dict[str, Any] | None = None
        self._slot_actions: int = 0
        self._last_applied_seq: int | None = None
        self.last_digest: dict[str, Any] | None = None

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
            raise QueueFullError(f"seat {self.player_id} already has an action for turn {self.turn_seq}")        # Bots may never impersonate the copilot path.
        action.actor_kind = None
        self.note_post(200, getattr(action.kind, "value", str(action.kind)))
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

    def record_result(self, ok: bool, error: str | None, event_seqs: list[int],
                      action_kind: str | None = None, auto: bool = False, turns_used: int | None = None) -> None:
        if not auto:
            self._slot_actions += 1
            self._last_applied_seq = self.turn_seq
        if self.macro is not None and not ok:
            self._end_macro(f"step failed: {error or 'rejected'}")
        self.last_result = {
            "turn_seq": self.turn_seq,
            "ok": bool(ok),
            "error": error or None,
            "event_seqs": list(event_seqs),
            "recorded_at": time.time(),
        }
        started = self.turn_started_at
        submitted = self._submitted_at
        self.log_action("result", ok=bool(ok), error=error or None, kind=action_kind, auto=auto,
                        think_s=round(submitted - started, 3) if (submitted and started and not auto) else None,
                        posts=self._posts, held=self.in_held_continuation, turns_used=turns_used,
                        macro=self._submitted_at is None and not auto)

    # ---- run_route macro + slot digest (G6) ----------------------------------

    def start_macro(self, plan: dict[str, Any]) -> tuple[Action | None, str | None]:
        """First step for the current turn, or (None, why). Later steps come from `act()`."""
        from .route_macro import next_step

        if not self.awaiting_input or self.current_observation is None:
            raise NotYourTurnError(f"seat {self.player_id} is not awaiting input")
        step, why = next_step(self.current_observation.model_dump(mode="json"), plan)
        if step is None:
            return None, why
        plan["steps"] = 1
        self.macro, self.macro_stop, self._macro_used = plan, None, True
        self.hold_slot = True
        self.log_action("macro_start", plan={k: plan[k] for k in ("a", "b", "buy_at_a", "buy_at_b", "cycles")}, step=step)
        return Action(kind=step["kind"], args=step["args"], thought=f"[route macro] {step['kind']}"), None

    def _end_macro(self, why: str | None) -> None:
        if self.macro is None:
            return
        self.macro_stop = why or "stopped"
        self.log_action("macro_end", reason=self.macro_stop, cycles_done=self.macro.get("cycles_done"),
                        steps=self.macro.get("steps"))
        self.hold_slot = False

    def _macro_step(self, observation: Observation) -> Action | None:
        from .route_macro import next_step

        plan = self.macro
        step, why = next_step(observation.model_dump(mode="json"), plan)
        if step is None:
            self._end_macro(why)
            return None
        plan["steps"] += 1
        self.log_action("macro_step", step=step, cycles_done=plan["cycles_done"])
        return Action(kind=step["kind"], args=step["args"], thought=f"[route macro] {step['kind']}")

    def end_slot(self, reason: str, *, credits: int, turns_left: int, day: int) -> dict[str, Any] | None:
        """Runner hook when this seat's scheduler slot ends. Builds the one-screen digest."""
        base, plan = self._slot_base, self.macro
        digest = None
        if base is not None and (self._slot_actions > 1 or self._macro_used):
            digest = {
                "kind": "route" if self._macro_used else "chain",
                "actions": self._slot_actions,
                "turns_used": (base["turns_left"] - turns_left) if base["day"] == day else None,
                "credits_before": base["credits"],
                "credits_after": credits,
                "stopped": self.macro_stop or reason,
                "cycles_done": plan.get("cycles_done") if plan else None,
                "cycles": plan.get("cycles") if plan else None,
                "last_turn_seq": self._last_applied_seq,
            }
            self.last_digest = digest
            self.log_action("digest", **digest)
        self.macro, self.macro_stop, self._macro_used = None, None, False
        self._slot_base, self._slot_actions = None, 0
        return digest

    # ---- per-action log (G5 pilot) -----------------------------------------

    def log_action(self, event: str, **fields: Any) -> None:
        """Append one line to ``action_log_path`` (set by the runner): posts,
        rejections, engine results, slot releases. Never contains tokens."""
        if self.action_log_path is None:
            return
        row = {"at": round(time.time(), 3), "seat": self.player_id, "turn_seq": self.turn_seq, "event": event, **fields}
        try:
            with self.action_log_path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(row) + "\n")
        except OSError:
            pass

    def note_post(self, status: int, detail: str | None = None) -> None:
        """Harness hook: one POST /action attempt for the current turn."""
        self._posts += 1
        if status == 200:
            self._submitted_at = time.time()
        since = round(time.time() - self.turn_started_at, 3) if self.turn_started_at and self.awaiting_input else None
        self.log_action("post", status=status, detail=detail, since_turn_start_s=since, attempt=self._posts)

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
            "hold": {"on": self.hold_slot, "used": self.hold_count, "max": self.hold_max},
            "webhook": list(self.webhook_log)[-5:],
            "macro": ({"active": True, "cycles_done": self.macro.get("cycles_done"), "cycles": self.macro.get("cycles"),
                       "steps": self.macro.get("steps")} if self.macro else None),
            "digest": self.last_digest,
        }

    # ---- hold my slot (G4) --------------------------------------------------

    @property
    def in_held_continuation(self) -> bool:
        return self.hold_count > 0

    def set_hold(self, on: bool) -> bool:
        """Toggle hold. Releasing during a held continuation ends the slot now.

        Returns True if an in-progress continuation turn was released.
        """
        self.hold_slot = bool(on) and self.hold_max > 0
        if not self.hold_slot:
            self._end_macro("hold released")
        if not self.hold_slot and self.awaiting_input and self.in_held_continuation and self._queue.empty():
            self._queue.put_nowait(_RELEASE)  # type: ignore[arg-type]
            return True
        return False

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

    def _webhook_auth(self) -> str:
        """`Authorization` header for Commander's webhook routine (G6). SECRET: never logged.

        Env `TW2K_GROKBOT_WEBHOOK_AUTH_<SEAT>` > `TW2K_GROKBOT_WEBHOOK_AUTH` >
        gitignored `.tw2k/grokbot_webhook_auth_<SEAT>.txt` > `.tw2k/grokbot_webhook_auth.txt`.
        """
        for key in (f"TW2K_GROKBOT_WEBHOOK_AUTH_{self.player_id}", "TW2K_GROKBOT_WEBHOOK_AUTH"):
            v = (os.environ.get(key) or "").strip()
            if v:
                return v
        from ..server.harness_tokens import _repo_root

        for name in (f"grokbot_webhook_auth_{self.player_id}.txt", "grokbot_webhook_auth.txt"):
            try:
                v = (_repo_root() / ".tw2k" / name).read_text(encoding="utf-8").strip()
            except OSError:
                continue
            if v:
                return v
        return ""

    @staticmethod
    def _base_url() -> str:
        """Where the bot should call back: env > current tunnel URL file > bound port."""
        from ..server.seat_links import base_url

        return base_url()

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
        base = self._base_url()
        payload: dict[str, Any] = {
            "event": "turn_due",
            "seat": self.player_id,
            "player_id": self.player_id,
            "name": self.name,
            "turn_seq": self.turn_seq,
            "started_at": started,
            "deadline_at": deadline,
            "base_url": base,
            # G4: where a computer-use player opens its cockpit (sign-in = its seat link cookie).
            "bot_url": f"{base}/bot?seat={self.player_id}&mode=cu",
            "observation_url": f"{base}/harness/v1/{self.player_id}/observation",
            "action_url": f"{base}/harness/v1/{self.player_id}/action",
            "brief": {
                "day": observation.day,
                "tick": observation.tick,
                "sector_id": sector.get("id"),
                "turns_remaining": observation.turns_remaining,
                "credits": observation.credits,
                "status_line": status_fields(observation)["status_line"] if isinstance(observation, Observation) else None,
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
        seq = self.turn_seq
        async with httpx.AsyncClient(timeout=8.0) as client:
            await asyncio.gather(*(self._deliver(client, url, payload, seq) for url in urls))

    async def _deliver(self, client, url: str, payload: dict[str, Any], seq: int, *, only_while_open: bool = True) -> None:
        """POST with retry + backoff (while this turn is still open, unless told otherwise). Never raises."""
        parts = urlsplit(url)
        target = f"{parts.scheme}://{parts.netloc}"  # the path/query may carry a secret
        auth = self._webhook_auth()
        headers = {"Authorization": auth} if auth else {}
        for attempt in range(1, len(WEBHOOK_RETRY_DELAYS_S) + 2):
            status: int | None = None
            error = ""
            try:
                r = await client.post(url, json=payload, headers=headers)
                status = r.status_code
            except Exception as exc:
                error = type(exc).__name__
            ok = status is not None and 200 <= status < 300
            self._log_delivery({"at": time.time(), "turn_seq": seq, "target": target, "attempt": attempt,
                                "status": status, "ok": ok, "error": error or None})
            if ok or attempt > len(WEBHOOK_RETRY_DELAYS_S):
                return
            await asyncio.sleep(WEBHOOK_RETRY_DELAYS_S[attempt - 1])
            if only_while_open and (self.turn_seq != seq or not self.awaiting_input):
                return  # the turn moved on; a late ping would only mislead

    async def fire_game_over(self, result: dict[str, Any]) -> None:
        """G6: one final `game_over` ping (standings summary, no observation, no token)."""
        urls = self._webhook_urls()
        if not urls:
            return
        import httpx

        payload = {"event": "game_over", "seat": self.player_id, "name": self.name,
                   "bot_url": f"{self._base_url()}/bot?seat={self.player_id}&mode=cu", **result}
        async with httpx.AsyncClient(timeout=8.0) as client:
            await asyncio.gather(*(self._deliver(client, url, payload, self.turn_seq, only_while_open=False) for url in urls))

    async def test_webhook(self, observation: Observation) -> list[dict[str, Any]]:
        """One `turn_due_test` ping per URL via the normal delivery path. Returns the attempts."""
        import httpx

        payload = self.turn_due_payload(observation)
        payload["event"] = "turn_due_test"
        before = len(self.webhook_log)
        async with httpx.AsyncClient(timeout=8.0) as client:
            await asyncio.gather(*(self._deliver(client, url, payload, self.turn_seq) for url in self._webhook_urls()))
        return list(self.webhook_log)[before:]

    def _log_delivery(self, entry: dict[str, Any]) -> None:
        self.webhook_log.append(entry)
        log.info("turn_due %s seq=%s -> %s attempt=%s status=%s", self.player_id, entry["turn_seq"],
                 entry["target"], entry["attempt"], entry["status"] or entry["error"])
        if self.webhook_log_path is not None:
            try:
                with self.webhook_log_path.open("a", encoding="utf-8") as fp:
                    fp.write(json.dumps({"seat": self.player_id, **entry}) + "\n")
            except OSError:
                pass

    async def act(self, observation: Observation) -> Action:
        self.turn_seq += 1
        self._posts = 0
        self._submitted_at = None
        self.current_observation = observation
        self.turn_started_at = time.time()
        self.awaiting_input = True
        self.turn_due.set()
        # Fire-and-forget; keep a reference so the task isn't GC'd mid-flight.
        # A held continuation needs no ping: the player is already at the screen.
        if not self.in_held_continuation:
            self._slot_base = {"credits": getattr(observation, "credits", 0),
                               "turns_left": getattr(observation, "turns_remaining", 0), "day": getattr(observation, "day", 0)}
            self._slot_actions = 0
            self._webhook_task = asyncio.create_task(self._fire_turn_due_webhook(observation))
        try:
            if self.macro is not None and self.in_held_continuation:
                step = self._macro_step(observation)
                if step is None:
                    self.log_action("slot_released", held_actions=self.hold_count)
                    raise SlotReleased(self.player_id)
                return step
            got = await self._queue.get()
            if got is _RELEASE:
                self.log_action("slot_released", held_actions=self.hold_count)
                raise SlotReleased(self.player_id)
            return got
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

