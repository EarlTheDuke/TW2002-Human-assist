"""Path-B reference client: one external seat, one brain, the harness protocol.

Parity S6 (docs/plans/2026-09-21-bot-human-parity.md). "Path B" is how a
competitive Grok Bot seat plays: it reads the SAME fogged Observation and
rules text an LLM seat gets (`observation?format=both`, `/rules`) and POSTs
actions with `turn_seq`. This module is the protocol plumbing so a brain
only has to implement ``decide(ctx) -> action``.

Design
------
* Async, `httpx.AsyncClient` injected -> runs against a live URL *or* an
  in-process ASGI app (tests). No xAI, no LLM call anywhere in this file.
* One `SeatClient` per seat. Run several in one process (`run_seats`) and you
  still have one brain object per seat - never a shared brain.
* Deadline-aware: the harness reports `current_turn.deadline_at` (server
  time) and `server_time`; the brain gets `ctx.seconds_left`. If the brain is
  late or raises, the client submits a safe `wait` before the deadline so the
  scheduler never has to auto-WAIT us.
* Policies shipped:
    - `legal_heuristic_policy` - deterministic scripted brain that reasons
      only from `legal_actions` envelopes (sell profitable cargo, buy what a
      known port pays more for, explore, scan). It is a *reference* and a
      test opponent, not a player.
    - `MailboxPolicy` - hands the decision to an out-of-process brain (a
      Grok Bot session): writes `<dir>/<seat>.pending.json` (observation +
      llm_user_message + rules once), waits for `<dir>/<seat>.decision.json`,
      falls back to `wait` shortly before the deadline.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx


@dataclass
class TurnContext:
    seat: str
    turn_seq: int
    observation: dict[str, Any]
    llm_user_message: str | None
    rules: dict[str, Any]
    status: dict[str, Any]
    deadline_at: float | None
    server_skew: float  # server_time - local time

    @property
    def seconds_left(self) -> float | None:
        if self.deadline_at is None:
            return None
        return self.deadline_at - (time.time() + self.server_skew)

    def legal(self, kind: str) -> dict[str, Any] | None:
        for la in self.observation.get("legal_actions") or []:
            if la.get("kind") == kind:
                return la
        return None


Policy = Callable[[TurnContext], Awaitable[dict[str, Any]] | dict[str, Any]]


@dataclass
class SeatStats:
    turns: int = 0
    ok: int = 0
    failed: int = 0
    stale: int = 0
    fallback_waits: int = 0
    kinds: dict[str, int] = field(default_factory=dict)
    last_error: str | None = None


class SeatClient:
    def __init__(
        self,
        http: httpx.AsyncClient,
        seat: str,
        token: str,
        policy: Policy,
        *,
        wait_s: float = 30.0,
        safety_margin_s: float = 3.0,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self.http = http
        self.seat = seat
        self.token = token
        self.policy = policy
        self.wait_s = wait_s
        self.safety_margin_s = safety_margin_s
        self.log = log or (lambda _m: None)
        self.rules: dict[str, Any] = {}
        self.stats = SeatStats()
        self._skew = 0.0

    # ---- protocol ---------------------------------------------------------
    def _h(self) -> dict[str, str]:
        return {"authorization": f"Bearer {self.token}"}

    async def fetch_rules(self) -> dict[str, Any]:
        r = await self.http.get("/harness/v1/rules", headers=self._h())
        r.raise_for_status()
        self.rules = r.json()
        return self.rules

    async def status(self) -> dict[str, Any]:
        r = await self.http.get(f"/harness/v1/{self.seat}/status", headers=self._h())
        r.raise_for_status()
        return r.json()

    async def wait_for_turn(self) -> dict[str, Any] | None:
        """Long-poll until it is our turn. Returns the body, or None if the seat closed."""
        r = await self.http.get(
            f"/harness/v1/{self.seat}/observation",
            params={"wait_s": self.wait_s, "format": "both"},
            headers=self._h(),
        )
        if r.status_code == 503:
            return None
        r.raise_for_status()
        body = r.json()
        st = body.get("server_time")
        if isinstance(st, (int, float)):
            self._skew = float(st) - time.time()
        return body

    async def submit(self, turn_seq: int, action: dict[str, Any]) -> tuple[bool, str | None]:
        r = await self.http.post(
            f"/harness/v1/{self.seat}/action",
            json={"turn_seq": turn_seq, "action": action},
            headers=self._h(),
        )
        if r.status_code == 409:
            self.stats.stale += 1
            return False, (r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else r.text)
        r.raise_for_status()
        return True, None

    # ---- one turn -----------------------------------------------------------
    async def play_turn(self, body: dict[str, Any]) -> dict[str, Any] | None:
        obs = body.get("observation") or {}
        ct = body.get("current_turn") or {}
        deadline = ct.get("deadline_at") if ct.get("player_id") == self.seat else body.get("deadline_at")
        ctx = TurnContext(
            seat=self.seat, turn_seq=int(body["turn_seq"]), observation=obs,
            llm_user_message=body.get("llm_user_message"), rules=self.rules, status=body,
            deadline_at=float(deadline) if isinstance(deadline, (int, float)) else None, server_skew=self._skew,
        )
        budget = None
        if ctx.seconds_left is not None:
            budget = max(0.5, ctx.seconds_left - self.safety_margin_s)
        action: dict[str, Any]
        try:
            out = self.policy(ctx)
            if asyncio.iscoroutine(out) or isinstance(out, Awaitable):
                out = await (asyncio.wait_for(out, timeout=budget) if budget else out)  # type: ignore[arg-type]
            action = dict(out) if out else {"kind": "wait"}
        except TimeoutError:
            self.stats.fallback_waits += 1
            action = {"kind": "wait", "thought": f"[{self.seat}] brain out of time - safe wait"}
        except Exception as exc:  # brain bug: never stall the match
            self.stats.fallback_waits += 1
            self.stats.last_error = f"policy error: {exc!r}"
            action = {"kind": "wait", "thought": f"[{self.seat}] brain error - safe wait"}
        action.setdefault("args", {})
        ok, err = await self.submit(ctx.turn_seq, action)
        self.stats.turns += 1
        self.stats.kinds[action["kind"]] = self.stats.kinds.get(action["kind"], 0) + 1
        if not ok:
            self.log(f"[{self.seat}] turn {ctx.turn_seq} stale/rejected: {err}")
            return None
        # Engine verdict
        await asyncio.sleep(0.05)
        st = await self.status()
        res = st.get("last_result") or {}
        if res.get("ok"):
            self.stats.ok += 1
        else:
            self.stats.failed += 1
            self.stats.last_error = res.get("error")
        self.log(f"[{self.seat}] D{st.get('day')} t{ctx.turn_seq}: {action['kind']} {action.get('args')} -> "
                 f"{'ok' if res.get('ok') else 'FAIL ' + str(res.get('error'))}")
        return res

    async def run(self, *, max_turns: int = 0, stop: asyncio.Event | None = None) -> SeatStats:
        if not self.rules:
            with contextlib.suppress(Exception):
                await self.fetch_rules()
        while not (stop and stop.is_set()):
            body = await self.wait_for_turn()
            if body is None:
                self.log(f"[{self.seat}] seat closed")
                break
            if body.get("match_status") in ("finished", "error"):
                self.log(f"[{self.seat}] match {body.get('match_status')}")
                break
            if not body.get("awaiting_input"):
                continue
            await self.play_turn(body)
            if max_turns and self.stats.turns >= max_turns:
                break
        return self.stats


async def run_seats(clients: list[SeatClient], *, max_turns: int = 0, stop: asyncio.Event | None = None) -> dict[str, SeatStats]:
    """Run several seats concurrently - one SeatClient (and one brain) each."""
    results = await asyncio.gather(*(c.run(max_turns=max_turns, stop=stop) for c in clients), return_exceptions=True)
    out: dict[str, SeatStats] = {}
    for c, r in zip(clients, results, strict=True):
        if isinstance(r, BaseException):
            c.stats.last_error = repr(r)
        out[c.seat] = c.stats
    return out


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


def legal_heuristic_policy(ctx: TurnContext) -> dict[str, Any]:
    """Deterministic reference brain driven ONLY by legal_actions envelopes.

    Order: sell cargo the port buys (profitable vs cost basis, else dump when
    holds full) -> buy what this port sells if a known port pays more -> warp
    to the least-visited legal target -> scan -> wait. No rule constants; every
    number comes from the Observation.
    """
    obs = ctx.observation
    trade = ctx.legal("trade") or {}
    ship = obs.get("ship") or {}
    basis = ship.get("cargo_cost_avg") or {}
    if trade.get("legal"):
        p = trade.get("params") or {}
        comm = p.get("commodity") or {}
        max_by = (p.get("qty") or {}).get("max_by") or {}
        listed = (p.get("unit_price") or {}).get("listed_by") or {}
        for c in comm.get("sell_choices") or []:
            qty = int((max_by.get(c) or {}).get("sell", 0))
            price = int((listed.get(c) or {}).get("sell", 0))
            if qty > 0 and (price > int(basis.get(c, 0) or 0) or int(ship.get("cargo_free") or 0) == 0):
                return {"kind": "trade", "args": {"commodity": c, "qty": qty, "side": "sell"}, "thought": f"sell {qty} {c} @~{price}"}
        # Buy only if some KNOWN port buys it for more than we pay here.
        known = obs.get("known_ports") or []
        here = (obs.get("sector") or {}).get("id")
        for c in comm.get("buy_choices") or []:
            qty = int((max_by.get(c) or {}).get("buy", 0))
            price = int((listed.get(c) or {}).get("buy", 0))
            best = 0
            for kp in known:
                if kp.get("sector_id") == here:
                    continue
                st = ((kp.get("stock") or {}).get(c) or {})
                if st.get("side") == "buys_from_player" and isinstance(st.get("price"), int):
                    best = max(best, int(st["price"]))
            if qty > 0 and best > price:
                return {"kind": "trade", "args": {"commodity": c, "qty": qty, "side": "buy"}, "thought": f"buy {qty} {c} @{price}, {best} elsewhere"}
    warp = ctx.legal("warp") or {}
    if warp.get("legal"):
        choices = list(((warp.get("params") or {}).get("target") or {}).get("choices") or [])
        if choices:
            known_ids = {int(k) for k in (obs.get("known_warps") or {})}
            # Prefer unexplored; tie-break deterministically by id.
            choices.sort(key=lambda t: (t in known_ids, t))
            return {"kind": "warp", "args": {"target": choices[0]}, "thought": "explore"}
    scan = ctx.legal("scan") or {}
    if scan.get("legal") and (obs.get("sector") or {}).get("id") not in {int(k) for k in (obs.get("known_warps") or {})}:
        return {"kind": "scan", "args": {}, "thought": "map this sector"}
    return {"kind": "wait", "args": {}, "thought": "nothing profitable; pass"}


class MailboxPolicy:
    """Decision by an out-of-process brain (a Grok Bot session) via files.

    pending:  <dir>/<seat>.pending.json  = {turn_seq, deadline_at, seconds_left, observation, llm_user_message, rules_once}
    decision: <dir>/<seat>.decision.json = {turn_seq, action: {...}}   (written by the brain, consumed here)
    """

    def __init__(self, directory: str | Path, *, poll_s: float = 0.5, margin_s: float = 5.0) -> None:
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.poll_s = poll_s
        self.margin_s = margin_s
        self._rules_sent: set[str] = set()

    def pending_path(self, seat: str) -> Path:
        return self.dir / f"{seat}.pending.json"

    def decision_path(self, seat: str) -> Path:
        return self.dir / f"{seat}.decision.json"

    async def __call__(self, ctx: TurnContext) -> dict[str, Any]:
        pend = self.pending_path(ctx.seat)
        dec = self.decision_path(ctx.seat)
        with contextlib.suppress(FileNotFoundError):
            dec.unlink()
        payload: dict[str, Any] = {
            "seat": ctx.seat, "turn_seq": ctx.turn_seq, "deadline_at": ctx.deadline_at,
            "seconds_left": ctx.seconds_left, "observation": ctx.observation,
            "llm_user_message": ctx.llm_user_message,
        }
        if ctx.seat not in self._rules_sent and ctx.rules:
            payload["rules"] = ctx.rules
            self._rules_sent.add(ctx.seat)
        pend.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        while True:
            left = ctx.seconds_left
            if left is not None and left <= self.margin_s:
                return {"kind": "wait", "args": {}, "thought": f"[{ctx.seat}] no decision in time - safe wait"}
            if dec.exists():
                try:
                    d = json.loads(dec.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    await asyncio.sleep(self.poll_s)
                    continue
                if int(d.get("turn_seq", -1)) == ctx.turn_seq and isinstance(d.get("action"), dict):
                    with contextlib.suppress(FileNotFoundError):
                        dec.unlink()
                    with contextlib.suppress(FileNotFoundError):
                        pend.unlink()
                    return d["action"]
            await asyncio.sleep(self.poll_s)


__all__ = ["MailboxPolicy", "SeatClient", "SeatStats", "TurnContext", "legal_heuristic_policy", "run_seats"]
