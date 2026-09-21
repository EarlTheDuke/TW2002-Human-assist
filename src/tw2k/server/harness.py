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
from ..engine.actions import Action, ActionKind
from . import harness_tokens as ht

ENV_ALLOW_REMOTE = "TW2K_HARNESS_ALLOW_REMOTE"
_LOOPBACK = {"127.0.0.1", "::1", "localhost", "testclient"}
MAX_WAIT_S = 60.0


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
        return owner

    def _seat_status(agent: ExternalAgent) -> dict[str, Any]:
        u = runner.state.universe
        p = u.players.get(agent.player_id) if u is not None else None
        deadline_at = None
        timeout_s = float(getattr(runner._spec, "external_timeout_s", 0.0) or 0.0) if runner._spec else 0.0
        if agent.awaiting_input and agent.turn_started_at and timeout_s > 0:
            deadline_at = agent.turn_started_at + timeout_s
        return {
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

    @router.get("/seats")
    async def seats(request: Request) -> dict[str, Any]:
        _authenticate_any(request)
        return {"seats": [_seat_status(a) for a in _external_agents()]}

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

    @router.get("/{player_id}/observation")
    async def observation(
        player_id: str,
        request: Request,
        wait_s: float = 0.0,
        format: str = "json",
    ) -> dict[str, Any]:
        agent = _require_seat(player_id, request)
        wait_s = max(0.0, min(float(wait_s), MAX_WAIT_S))
        if not agent.awaiting_input and wait_s > 0:
            await agent.wait_for_turn(wait_s)
            if agent.closed:
                raise HTTPException(status_code=503, detail="seat closed")
        body = _seat_status(agent)
        obs = agent.current_observation if agent.awaiting_input else None
        fmt = (format or "json").lower()
        body["observation"] = obs.model_dump(mode="json") if (obs is not None and fmt in ("json", "both")) else None
        if obs is not None and fmt in ("llm", "both"):
            body["llm_user_message"] = format_observation(obs)
        return body

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
