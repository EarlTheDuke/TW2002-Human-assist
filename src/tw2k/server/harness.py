"""``/harness/v1`` — REST surface for external (Grok Bot) seats.

Plan: docs/plans/2026-09-20-external-harness.md §3.

A bot **pulls** its observation and **pushes** one Action per turn. The
server never calls out. Every route (except nothing — all of them) needs
``Authorization: Bearer <seat token>``; the token must belong to the seat
named in the path, so one bot can never move another bot's ship.

Loopback only by default: the request must originate from 127.0.0.1 / ::1
unless ``TW2K_HARNESS_ALLOW_REMOTE=1``. This is belt-and-braces on top of
``tw2k serve --host 127.0.0.1``.

Error model (FastAPI ``{"detail": ...}``):

    401  missing / unknown bearer token
    403  token is valid but for a different seat, or non-loopback client
    404  no such player in the live match
    409  seat is not kind=external          detail = "not_external"
    409  scheduler not waiting on this seat detail = {"code": "not_awaiting", ...}
    409  turn_seq mismatch                   detail = {"code": "stale_turn", "current_turn_seq": N}
    422  body failed Action validation
    429  an action was already accepted for this turn
    503  no match running / seat closed
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..agents.external import (
    ExternalAgent,
    NotYourTurnError,
    QueueFullError,
    StaleTurnError,
)
from ..agents.prompts import format_observation, get_system_prompt
from ..engine import build_observation
from ..engine.actions import Action, ActionKind
from ..engine.observation import _event_visible_to, event_view
from . import harness_tokens as ht

ENV_ALLOW_REMOTE = "TW2K_HARNESS_ALLOW_REMOTE"
_LOOPBACK = {"127.0.0.1", "::1", "localhost", "testclient"}
MAX_WAIT_S = 60.0
# Parity S1: a seat may peek at its own fogged Observation between turns.
# build_observation is pure but not free (~ms); cache per seat for this long.
PEEK_CACHE_S = 0.5
EVENTS_MAX_LIMIT = 500


class ActionSubmission(BaseModel):
    turn_seq: int | None = None
    action: dict[str, Any] = Field(default_factory=dict)


def _allow_remote() -> bool:
    return (os.environ.get(ENV_ALLOW_REMOTE) or "").strip().lower() in ("1", "true", "yes")


def _bearer(request: Request) -> str:
    raw = request.headers.get("authorization") or ""
    scheme, _, token = raw.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


def build_harness_router(runner) -> APIRouter:
    router = APIRouter(prefix="/harness/v1", tags=["harness"])

    # ---- helpers -----------------------------------------------------------

    def _external_agents() -> list[ExternalAgent]:
        return [a for a in runner.state.agents if isinstance(a, ExternalAgent)]

    def _check_loopback(request: Request) -> None:
        if _allow_remote():
            return
        host = (request.client.host if request.client else "") or ""
        if host not in _LOOPBACK:
            raise HTTPException(status_code=403, detail="harness is loopback-only")

    def _require_match() -> None:
        if not runner.state.agents or runner.state.universe is None:
            raise HTTPException(status_code=503, detail="match not running")

    def _authenticate_any(request: Request) -> ExternalAgent:
        """Any valid seat token → returns the seat it belongs to."""
        _check_loopback(request)
        _require_match()
        token = _bearer(request)
        if not token:
            raise HTTPException(status_code=401, detail="missing bearer token")
        for a in _external_agents():
            if ht.verify(token, a.token):
                return a
        raise HTTPException(status_code=401, detail="invalid token")

    def _require_seat(player_id: str, request: Request) -> ExternalAgent:
        _check_loopback(request)
        _require_match()
        token = _bearer(request)
        if not token:
            raise HTTPException(status_code=401, detail="missing bearer token")
        owner: ExternalAgent | None = None
        for a in _external_agents():
            if ht.verify(token, a.token):
                owner = a
                break
        if owner is None:
            raise HTTPException(status_code=401, detail="invalid token")
        if owner.player_id != player_id:
            # Token is real but for another seat. Check the path seat exists
            # so the bot gets a precise error.
            if not any(a.player_id == player_id for a in runner.state.agents):
                raise HTTPException(status_code=404, detail=f"no such player {player_id}")
            if not any(a.player_id == player_id for a in _external_agents()):
                raise HTTPException(status_code=409, detail="not_external")
            raise HTTPException(status_code=403, detail="token does not belong to this seat")
        if owner.closed:
            raise HTTPException(status_code=503, detail="seat closed")
        # Mark the seat attended: the runner shortens the idle auto-WAIT for
        # seats nobody is polling (Phase D P0).
        owner.touch_client()
        return owner

    def _current_turn() -> dict[str, Any] | None:
        """Who the scheduler is blocked on right now (any kind), with a deadline if known."""
        u = runner.state.universe
        agents = runner.state.agents
        idx = runner.state.current_player_idx
        if u is None or not agents or not (0 <= idx < len(agents)):
            return None
        cur = agents[idx]
        p = u.players.get(cur.player_id)
        out: dict[str, Any] = {
            "player_id": cur.player_id,
            "name": cur.name,
            "kind": getattr(cur, "kind", None) or (p.agent_kind if p is not None else None),
            "started_at": None,
            "deadline_at": None,
            "attended": None,
        }
        spec = runner._spec
        if isinstance(cur, ExternalAgent):
            out["started_at"] = cur.turn_started_at
            out["awaiting_input"] = cur.awaiting_input
            window = float(getattr(spec, "external_attend_window_s", 45.0) or 0.0) if spec else 45.0
            out["attended"] = cur.is_attended(window)
            timeout_s = float(getattr(spec, "external_timeout_s", 0.0) or 0.0) if spec else 0.0
            idle_s = float(getattr(spec, "external_idle_wait_s", 0.0) or 0.0) if spec else 0.0
            eff = timeout_s
            if idle_s > 0 and not out["attended"]:
                eff = min(timeout_s, idle_s) if timeout_s else idle_s
            if cur.awaiting_input and cur.turn_started_at and eff > 0:
                out["deadline_at"] = cur.turn_started_at + eff
        else:
            phase = runner.state.llm_phase or {}
            if phase.get("player_id") == cur.player_id and phase.get("started_at"):
                out["started_at"] = float(phase["started_at"])
                cap = float(getattr(u.config, "llm_think_cap_s", 0.0) or 0.0)
                if cap > 0:
                    out["deadline_at"] = out["started_at"] + cap
        return out

    def _seat_status(agent: ExternalAgent) -> dict[str, Any]:
        u = runner.state.universe
        p = u.players.get(agent.player_id) if u is not None else None
        deadline_at = None
        timeout_s = float(getattr(runner._spec, "external_timeout_s", 0.0) or 0.0) if runner._spec else 0.0
        if agent.awaiting_input and agent.turn_started_at and timeout_s > 0:
            deadline_at = agent.turn_started_at + timeout_s
        return {
            "current_turn": _current_turn(),
            **agent.status(),
            "alive": bool(p.alive) if p is not None else False,
            "sector_id": p.sector_id if p is not None else None,
            "turns_remaining": (p.turns_per_day - p.turns_today) if p is not None else None,
            "match_status": runner.state.status,
            "day": u.day if u is not None else None,
            "tick": u.tick if u is not None else None,
            "timeout_s": timeout_s,
            "deadline_at": deadline_at,
            "server_time": time.time(),
        }

    # ---- routes ------------------------------------------------------------

    def _seat_public(agent: ExternalAgent) -> dict[str, Any]:
        """Lobby view of a seat: who / attended / whose turn - never their intel.

        Parity S6 (fog): `/seats` is readable with ANY valid seat token, so it
        must not expose a sibling's sector, last_result or queue state. Use
        `/{pid}/status` with that seat's own token for the full view.
        """
        u = runner.state.universe
        p = u.players.get(agent.player_id) if u is not None else None
        spec = runner._spec
        window = float(getattr(spec, "external_attend_window_s", 45.0) or 0.0) if spec else 45.0
        return {
            "player_id": agent.player_id,
            "name": agent.name,
            "kind": "external",
            "alive": bool(p.alive) if p is not None else False,
            "awaiting_input": agent.awaiting_input,
            "attended": agent.is_attended(window),
            "turn_seq": agent.turn_seq,
        }

    @router.get("/seats")
    async def seats(request: Request) -> dict[str, Any]:
        _authenticate_any(request)
        u = runner.state.universe
        return {
            "seats": [_seat_public(a) for a in _external_agents()],
            "current_turn": _current_turn(),
            "match_status": runner.state.status,
            "day": u.day if u is not None else None,
            "tick": u.tick if u is not None else None,
            "server_time": time.time(),
        }

    @router.get("/rules")
    async def rules(request: Request) -> dict[str, Any]:
        _authenticate_any(request)
        return {
            "system_prompt": get_system_prompt(),
            "verbs": [k.value for k in ActionKind],
            "action_schema": Action.model_json_schema(),
            "notes": [
                "Echo `turn_seq` from status/observation in your POST so stale replies are rejected.",
                "`observation.sector.warps_out` lists the only legal warp targets this turn.",
                "`action.actor_kind` is ignored for external seats.",
            ],
        }

    @router.get("/{player_id}/status")
    async def status(player_id: str, request: Request) -> dict[str, Any]:
        agent = _require_seat(player_id, request)
        return _seat_status(agent)

    _peek_cache: dict[str, tuple[float, Any]] = {}

    def _peek_observation(agent: ExternalAgent):
        """Fog-safe read of the seat's OWN current Observation, any time.

        This is exactly `build_observation(universe, pid)` - the same object
        the scheduler would hand the seat on its turn - so it cannot reveal
        anything the seat is not entitled to. It is read-only: it does not
        touch `awaiting_input`, `turn_seq`, or the queue.
        """
        u = runner.state.universe
        if u is None:
            raise HTTPException(status_code=503, detail="match not running")
        now = time.time()
        hit = _peek_cache.get(agent.player_id)
        if hit is not None and (now - hit[0]) < PEEK_CACHE_S:
            return hit[1]
        obs = build_observation(u, agent.player_id)
        _peek_cache[agent.player_id] = (now, obs)
        return obs

    @router.get("/{player_id}/observation")
    async def observation(
        player_id: str,
        request: Request,
        wait_s: float = 0.0,
        format: str = "json",
        peek: bool = False,
    ) -> dict[str, Any]:
        """The seat's fogged Observation.

        * On your turn: the exact object the scheduler handed you (`turn_seq`
          bound); long-poll with `wait_s` while waiting.
        * `peek=1` (Parity S1): when it is NOT your turn, return a fresh
          read-only Observation for your seat instead of `null`, so a cockpit
          can show ship / port / map memory between turns. `awaiting_input`
          stays false and no action can be bound to a peeked observation.
        """
        agent = _require_seat(player_id, request)
        wait_s = max(0.0, min(float(wait_s), MAX_WAIT_S))
        if not agent.awaiting_input and wait_s > 0:
            await agent.wait_for_turn(wait_s)
            if agent.closed:
                raise HTTPException(status_code=503, detail="seat closed")
        body = _seat_status(agent)
        obs = agent.current_observation if agent.awaiting_input else None
        body["peek"] = False
        if obs is None and peek:
            obs = _peek_observation(agent)
            body["peek"] = True
        fmt = (format or "json").lower()
        body["observation"] = obs.model_dump(mode="json") if (obs is not None and fmt in ("json", "both")) else None
        if obs is not None and fmt in ("llm", "both"):
            body["llm_user_message"] = format_observation(obs)
        return body

    @router.get("/{player_id}/events")
    async def events(
        player_id: str,
        request: Request,
        since: int = 0,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Fogged event stream for this seat (Parity S1 / presentation boundary).

        Returns events with `seq > since`, in order, filtered by the same
        `_event_visible_to` rule the Observation uses, rendered as
        `event_view` (summary text always; `facts` = per-kind whitelist).
        `next_since` is the last seq returned (or `since` if none) so a client
        can page forward; `latest_seq` is the newest event in the match so a
        client knows whether it is caught up.
        """
        agent = _require_seat(player_id, request)
        u = runner.state.universe
        if u is None:
            raise HTTPException(status_code=503, detail="match not running")
        since = max(0, int(since))
        limit = max(1, min(int(limit), EVENTS_MAX_LIMIT))
        out: list[dict[str, Any]] = []
        for ev in u.events:
            if ev.seq <= since:
                continue
            if not _event_visible_to(ev, agent.player_id, u):
                continue
            out.append(event_view(ev))
            if len(out) >= limit:
                break
        latest = u.events[-1].seq if u.events else 0
        return {
            "player_id": agent.player_id,
            "events": out,
            "next_since": out[-1]["seq"] if out else since,
            "latest_seq": latest,
            "has_more": bool(out) and out[-1]["seq"] < latest,
        }

    @router.post("/{player_id}/action")
    async def submit(player_id: str, request: Request, body: ActionSubmission) -> dict[str, Any]:
        agent = _require_seat(player_id, request)
        raw = dict(body.action or {})
        raw.pop("actor_kind", None)
        try:
            action = Action.model_validate(raw)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"invalid action: {exc}") from exc
        try:
            bound = await agent.submit_action(action, turn_seq=body.turn_seq)
        except StaleTurnError as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "stale_turn", "submitted": exc.submitted, "current_turn_seq": exc.current},
            ) from exc
        except NotYourTurnError as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "not_awaiting", "current_turn_seq": agent.turn_seq, "message": str(exc)},
            ) from exc
        except QueueFullError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        # Yield once so the scheduler can pick the action up before we answer.
        await asyncio.sleep(0)
        return {"accepted": True, "player_id": player_id, "turn_seq": bound}

    return router
