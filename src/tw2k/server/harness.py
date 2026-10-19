"""``/harness/v1`` — REST surface for external (Grok Bot) seats.

Plan: docs/plans/2026-09-20-external-harness.md §3.

A bot **pulls** its observation and **pushes** one Action per turn. The
server never calls out. Every route (except nothing — all of them) needs
``Authorization: Bearer <seat token>``; the token must belong to the seat
named in the path, so one bot can never move another bot's ship. A browser
that opened its seat claim link (G3, ``server/seat_links.py``) may send the
``tw2k_seat_<SEAT>`` cookie instead; cookie-authenticated writes must also
send ``X-TW2K-Seat: <SEAT>``.

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
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, Field

from ..agents.external import (
    ExternalAgent,
    NotYourTurnError,
    QueueFullError,
    StaleTurnError,
)
from ..agents.prompts import format_observation, get_system_prompt
from ..engine import build_observation
from ..engine import constants as K
from ..engine.actions import Action, ActionKind
from ..engine.observation import _event_visible_to, event_view, status_fields
from ..engine.runner import full_net_worth, query_route
from . import harness_tokens as ht
from . import seat_links

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
    # G4: set/clear hold-my-slot together with the action (applies after it).
    hold: bool | None = None


class HoldRequest(BaseModel):
    hold: bool


class MacroRequest(BaseModel):
    """G6 `run_route`: trade a port pair for N cycles inside one held slot."""

    kind: str = "run_route"
    a: int
    b: int
    buy_at_a: str
    buy_at_b: str
    cycles: int = 3
    turn_seq: int | None = None


def _allow_remote() -> bool:
    return (os.environ.get(ENV_ALLOW_REMOTE) or "").strip().lower() in ("1", "true", "yes")


def _bearer(request: Request) -> str:
    raw = request.headers.get("authorization") or ""
    scheme, _, token = raw.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


def _credential(request: Request, player_id: str | None = None) -> str:
    """Bearer header, else the G3 claim cookie. Cookie writes need the CSRF header."""
    token = _bearer(request)
    if token:
        return token
    token = seat_links.cookie_token(request.cookies, player_id)
    if token and request.method not in ("GET", "HEAD"):
        claimed = (request.headers.get(seat_links.CSRF_HEADER) or "").strip().upper()
        if not claimed or (player_id and claimed != player_id.upper()):
            raise HTTPException(status_code=403, detail=f"cookie auth needs the {seat_links.CSRF_HEADER} header")
    return token


_BANK_KINDS = {ActionKind.BANK_DEPOSIT, ActionKind.BANK_WITHDRAW, ActionKind.BANK_TRANSFER}


def rewrite_api_args(action: Action) -> None:
    """Bank clients may send credits or qty. The engine reads amount."""
    if action.kind not in _BANK_KINDS:
        return
    args = dict(action.args or {})
    if "amount" not in args:
        for alias in ("credits", "qty"):
            if alias in args:
                args["amount"] = args.pop(alias)
                break
    action.args = args


def arg_error(action: Action, error: str | None) -> str | None:
    if action.kind in _BANK_KINDS and error == "amount must be a whole number":
        return "amount is required. Valid names: amount. Aliases: credits, qty."
    return None


def retry_blocked(agent) -> bool:
    now = time.time()
    stamps = getattr(agent, "_retry_stamps", None)
    if stamps is None:
        stamps = []
        agent._retry_stamps = stamps
    window = float(K.API_RETRY_WINDOW_S)
    stamps[:] = [t for t in stamps if now - t < window]
    if len(stamps) >= int(K.API_RETRY_LIMIT):
        return True
    stamps.append(now)
    return False


def legal_verb_hint(universe, pid: str) -> list[str]:
    from ..engine.legality import legal_actions

    return [la.kind for la in legal_actions(universe, pid) if la.legal][:8]


def final_standings(universe, seat: str | None = None) -> dict[str, Any]:
    """Public end-of-match table (G6). Net worth stays on every row."""
    rows = []
    for p in universe.players.values():
        row = {
            "seat": p.id,
            "name": p.name,
            "net_worth": full_net_worth(universe, p) if p.alive else 0,
            "alive": p.alive,
        }
        if K.exp_score_live():
            row["experience"] = int(p.experience)
        rows.append(row)
    if K.exp_score_live():
        rows.sort(key=lambda r: (r["experience"], r["net_worth"]), reverse=True)
    else:
        rows.sort(key=lambda r: r["net_worth"], reverse=True)
    mode = K.rank_display()
    if mode != "legacy":
        for row in rows:
            person = universe.players[row["seat"]]
            worth = full_net_worth(universe, person) if person.alive else 0
            row["experience"] = int(person.experience)
            row["planet_value"] = int(worth) - int(person.net_worth)
        if mode == "exp":
            rows.sort(key=lambda r: (r["experience"], r["net_worth"]), reverse=True)
        elif mode == "networth":
            rows.sort(key=lambda r: r["net_worth"], reverse=True)
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    if mode != "legacy":
        by_exp = sorted(rows, key=lambda r: (r["experience"], r["net_worth"]), reverse=True)
        by_worth = sorted(rows, key=lambda r: r["net_worth"], reverse=True)
        exp_place = {r["seat"]: i for i, r in enumerate(by_exp, start=1)}
        worth_place = {r["seat"]: i for i, r in enumerate(by_worth, start=1)}
        for row in rows:
            row["experience_rank"] = exp_place[row["seat"]]
            row["net_worth_rank"] = worth_place[row["seat"]]
    win = next((r for r in rows if r["seat"] == universe.winner_id), None)
    out: dict[str, Any] = {
        "winner": {"seat": win["seat"], "name": win["name"]} if win else None,
        "win_reason": universe.win_reason or "",
        "standings": rows,
    }
    if seat is not None:
        out["your_rank"] = next((r["rank"] for r in rows if r["seat"] == seat), None)
    return out


def _video_custom_flag() -> dict[str, Any]:
    """Omit the key entirely when the custom queue was never started."""
    from ..media.custom_queue import current as custom_current

    if custom_current() is None:
        return {}
    return {"video_custom": True}


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
        token = _credential(request)
        if not token:
            raise HTTPException(status_code=401, detail="missing bearer token")
        for a in _external_agents():
            if ht.verify(token, a.token):
                return a
        raise HTTPException(status_code=401, detail="invalid token")

    def _require_seat(player_id: str, request: Request) -> ExternalAgent:
        _check_loopback(request)
        _require_match()
        token = _credential(request, player_id)
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
        # G6: once the match is over every write is 409 game_over and reads keep
        # working (final standings), even before the runner has closed the seat.
        if _match_finished():
            if request.method in ("GET", "HEAD"):
                return owner
            raise HTTPException(status_code=409, detail="game_over")
        if owner.closed:
            raise HTTPException(status_code=503, detail="seat closed")
        # Mark the seat attended: the runner shortens the idle auto-WAIT for
        # seats nobody is polling (Phase D P0).
        owner.touch_client()
        return owner

    def _match_finished() -> bool:
        u = runner.state.universe
        return runner.state.status == "finished" or bool(u is not None and u.finished)

    def _timeout_for(agent: ExternalAgent) -> float:
        spec = runner._spec
        default = float(getattr(spec, "external_timeout_s", 0.0) or 0.0) if spec else 0.0
        return float(agent.timeout_s or default)

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
            timeout_s = _timeout_for(cur)
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
        timeout_s = _timeout_for(agent)
        # The runner's effective deadline (idle rule, held slot) when it set one.
        deadline_at = agent.turn_deadline_at if agent.awaiting_input else None
        if deadline_at is None and agent.awaiting_input and agent.turn_started_at and timeout_s > 0:
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
            "wait_streak": int(getattr(runner, "_wait_streak", {}).get(agent.player_id, 0) or 0),
            **_status_and_result(agent),
            **_video_custom_flag(),
        }

    def _status_and_result(agent: ExternalAgent) -> dict[str, Any]:
        """G6: the one status line + structured fields; after the match, the result."""
        u = runner.state.universe
        out: dict[str, Any] = {"game_over": _match_finished()}
        if u is None or agent.player_id not in u.players:
            return out
        obs = agent.current_observation if agent.awaiting_input and agent.current_observation else _peek_observation(agent)
        out.update(status_fields(obs))
        if out["game_over"]:
            out.update(final_standings(u, agent.player_id))
        return out

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

    @router.get("/{player_id}/reference")
    async def reference(player_id: str, request: Request) -> dict[str, Any]:
        _require_seat(player_id, request)
        from .reference import game_reference
        universe = runner.state.universe
        return game_reference(
            universe.players.get(player_id), int(universe.day), int(universe.config.max_days),
        )

    @router.get("/rules")
    async def rules(request: Request) -> dict[str, Any]:
        _authenticate_any(request)
        verbs = [k.value for k in ActionKind]
        if not K.rob_tw2002():
            verbs = [v for v in verbs if v not in ("rob", "steal")]
        if not K.hardware_tw2002():
            verbs = [v for v in verbs if v not in ("cloak", "fire_disruptor", "remove_limpet", "launch_beacon", "deploy_atomic")]
        if not K.class0_tw2002():
            verbs = [v for v in verbs if v != "terra_colonists"]
        if not K.planet_trade_on():  # planetary-trading-v1: legacy has no <N> verb
            verbs = [v for v in verbs if v != "planet_trade"]
        return {
            "system_prompt": get_system_prompt(),
            "verbs": verbs,
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
        runner.note_harness_poll(agent.player_id)
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
        runner.note_harness_poll(agent.player_id)
        wait_s = max(0.0, min(float(wait_s), MAX_WAIT_S))
        if not agent.awaiting_input and wait_s > 0:
            await agent.wait_for_turn(wait_s)
            if agent.closed and not _match_finished():
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
        if K.cockpit_fields_on() and runner.state.universe is not None:
            from .cockpit_fields import cockpit_block

            body["cockpit"] = cockpit_block(runner.state.universe, agent)
        if K.turn_regen_live() and runner.state.universe is not None:
            body["turn_clock"] = _turn_clock(agent.player_id)
        spec = getattr(runner, "_spec", None)
        override = getattr(getattr(spec, "config", None), "starting_credits_override", None)
        body["starting_credits_line"] = K.starting_credits_line(override, K.opening_original_credits())
        turns_override = getattr(getattr(spec, "config", None), "turns_per_day_override", None)
        player = runner.state.universe.players.get(agent.player_id) if runner.state.universe is not None else None
        original_turns = int(player.turns_per_day) if player is not None else K.opening_original_turns()
        body["turns_per_day_line"] = K.turns_per_day_line(turns_override, original_turns)
        return body

    @router.get("/{player_id}/route")
    async def route(player_id: str, request: Request, target: int) -> dict[str, Any]:
        """NOTE 65 item 2. Read-only course over the real warp graph.

        Same avoids as plot_course. No event, no turn, and it works when it
        is not this seat's turn. A lobby GET is a public-mode read: the action
        limiter stays on harness POSTs only.
        """
        agent = _require_seat(player_id, request)
        runner.note_harness_poll(agent.player_id)
        u = runner.state.universe
        if u is None:
            raise HTTPException(status_code=503, detail="match not running")
        if player_id not in u.players:
            raise HTTPException(status_code=404, detail=f"no such player {player_id}")
        return query_route(u, player_id, target)

    def _turn_clock(player_id: str) -> dict[str, Any] | None:
        """NOTE 60 item 4: when this seat's next turn comes back and when the next day starts.

        Server facts only (epoch seconds and seconds from now), so the cockpit never guesses."""
        import time as _time

        u = runner.state.universe
        player = u.players.get(player_id) if u is not None else None
        if player is None:
            return None
        now = _time.time()
        day_s = float(K.TURN_REGEN_DAY_SECONDS)
        cap = max(0, int(player.turns_per_day))
        used = max(0, int(player.turns_today))
        out: dict[str, Any] = {
            "server_now": now,
            "day_seconds": day_s,
            "turns_per_hour": round(cap * 3600.0 / day_s, 1) if day_s > 0 else 0.0,
            "seconds_per_turn": round(day_s / cap, 3) if cap else None,
            "next_turn_at": None,
            "next_turn_in_s": None,
            "next_day_at": None,
            "next_day_in_s": None,
        }
        if cap and used > 0:
            per_turn = day_s / cap
            last = player.turn_regen_at
            earned = float(player.turn_regen_frac)
            if last is not None:
                earned += max(0.0, now - float(last)) / per_turn
            wait = (1.0 - (earned % 1.0)) * per_turn
            out["next_turn_in_s"] = round(wait, 1)
            out["next_turn_at"] = now + wait
        clock = runner.day_clock()
        if clock is not None:
            out["next_day_at"] = clock["next_day_at"]
            out["next_day_in_s"] = round(max(0.0, clock["next_day_at"] - now), 1)
        return out

    @router.get("/{player_id}/events")
    async def events(
        player_id: str,
        request: Request,
        since: int = 0,
        limit: int = 200,
        course: int = 0,
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
            view = event_view(ev)
            # NOTE 105. Same viewer rule as Observation.recent_events. Absent
            # unless the capture-credit sentence is on, so a legacy stream is unchanged.
            if (ev.kind.value == "ship_captured" and "credits_lost" in (ev.payload or {})
                    and (ev.payload.get("victim") == agent.player_id or ev.actor_id == agent.player_id)):
                view = dict(view)
                facts = dict(view.get("facts") or {})
                facts["credits_lost"] = int(ev.payload["credits_lost"])
                view["facts"] = facts
            if course and ev.kind.value == "autopilot":
                path = (ev.payload or {}).get("path")
                if isinstance(path, list):
                    view = dict(view)
                    facts = dict(view.get("facts") or {})
                    facts["path"] = [int(hop) for hop in path]
                    view["facts"] = facts
            out.append(view)
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
        try:
            return await _submit(agent, player_id, body)
        except HTTPException as exc:
            code = exc.detail.get("code") if isinstance(exc.detail, dict) else str(exc.detail)[:80]
            agent.note_post(exc.status_code, code)  # G5 per-action log: rejected attempt
            raise

    async def _submit(agent: ExternalAgent, player_id: str, body: ActionSubmission) -> dict[str, Any]:
        raw = dict(body.action or {})
        raw.pop("actor_kind", None)
        try:
            action = Action.model_validate(raw)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"invalid action: {exc}") from exc
        if K.api_args_live():
            rewrite_api_args(action)
            if retry_blocked(agent):
                raise HTTPException(status_code=429, detail="too many retries")
        if body.hold is not None:
            if body.hold and agent.hold_max <= 0:
                raise HTTPException(status_code=409, detail="hold_disabled")
            agent.hold_slot = bool(body.hold)
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
        body: dict[str, Any] = {"accepted": True, "player_id": player_id, "turn_seq": bound}
        if K.action_result_report():
            # accepted stays "queued". result is what the engine then did.
            body["result"] = await agent.wait_result(bound)
        elif K.api_args_live():
            body["result"] = await agent.wait_result(bound)
        if K.api_args_live() and (body.get("result") or {}).get("rejected"):
            body["accepted"] = False
            named = arg_error(action, body["result"].get("error"))
            body["reason"] = named or body["result"].get("error")
            body["legal_verbs"] = legal_verb_hint(runner.state.universe, player_id)
        if K.hold_rules_live():
            body["wording"] = K.HOLD_RULES_NOTE
        return body

    @router.post("/{player_id}/hold")
    async def hold(player_id: str, request: Request, body: HoldRequest) -> dict[str, Any]:
        """G4 hold-my-slot. `hold: true` keeps the scheduler on this seat after
        each action (up to `max` extra actions); `hold: false` ends the slot -
        immediately, without spending a turn, if the seat is in a held turn."""
        agent = _require_seat(player_id, request)
        if body.hold and agent.hold_max <= 0:
            raise HTTPException(status_code=409, detail="hold_disabled")
        released = agent.set_hold(body.hold)
        answer = {"player_id": player_id, "hold": agent.hold_slot, "released": released,
                  "used": agent.hold_count, "max": agent.hold_max}
        if K.hold_rules_live():
            answer["wording"] = K.HOLD_RULES_NOTE
        return answer

    @router.post("/{player_id}/macro")
    async def macro(player_id: str, request: Request, body: MacroRequest) -> dict[str, Any]:
        """Start a route macro on this seat's turn. Each step is an ordinary
        action applied by the engine one turn at a time; the macro stops on an
        enemy, an empty port, low turns, a failed step, or a hold release."""
        from ..agents.route_macro import new_plan

        agent = _require_seat(player_id, request)
        if body.kind != "run_route":
            raise HTTPException(status_code=422, detail=f"unknown macro {body.kind!r}")
        if agent.hold_max <= 0:
            raise HTTPException(status_code=409, detail="hold_disabled")
        if not agent.awaiting_input:
            raise HTTPException(status_code=409, detail={"code": "not_awaiting", "current_turn_seq": agent.turn_seq})
        if body.turn_seq is not None and body.turn_seq != agent.turn_seq:
            raise HTTPException(status_code=409, detail={"code": "stale_turn", "current_turn_seq": agent.turn_seq})
        try:
            plan = new_plan(body.a, body.b, body.buy_at_a, body.buy_at_b, body.cycles)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        action, why = agent.start_macro(plan)
        if action is None:
            return {"started": False, "stopped": why}
        bound = await agent.submit_action(action, turn_seq=agent.turn_seq)
        await asyncio.sleep(0)
        return {"started": True, "turn_seq": bound, "first_step": {"kind": action.kind.value, "args": action.args},
                "plan": {k: plan[k] for k in ("a", "b", "buy_at_a", "buy_at_b", "cycles")}}

    @router.post("/{player_id}/webhook_test")
    async def webhook_test(player_id: str, request: Request) -> dict[str, Any]:
        """G5 dry run: send one `turn_due_test` ping through the real delivery
        path (retry + log) without a turn. 409 when no webhook URL is set."""
        agent = _require_seat(player_id, request)
        if not agent._webhook_urls():
            raise HTTPException(status_code=409, detail="no_webhook_url")
        u = runner.state.universe
        entries = await agent.test_webhook(build_observation(u, agent.player_id))
        return {"player_id": player_id, "deliveries": entries, "delivered": any(e["ok"] for e in entries)}

    @router.get("/{player_id}/media/custom/{prompt_hash}")
    async def custom_clip(player_id: str, prompt_hash: str, request: Request) -> Response:
        agent = _require_seat(player_id, request)
        from ..media.custom_queue import current as custom_current

        q = custom_current()
        if q is None:
            raise HTTPException(status_code=404, detail="custom queue off")
        body = q.clip_bytes(agent.player_id, prompt_hash)
        if body is None:
            raise HTTPException(status_code=404, detail="no such clip")
        return Response(content=body, media_type="video/webm", headers={"Cache-Control": "private"})

    @router.get("/{player_id}/media/moments")
    async def custom_moments(player_id: str, request: Request, since: int = 0) -> dict[str, Any]:
        agent = _require_seat(player_id, request)
        from ..media.custom_queue import current as custom_current

        q = custom_current()
        if q is None:
            raise HTTPException(status_code=404, detail="custom queue off")
        return {"player_id": agent.player_id, **q.feed_for(agent.player_id, since)}

    def _match_key() -> str:
        universe = runner.state.universe
        return f"{universe.config.seed}-{id(universe)}"

    def _bridge_seat(request: Request) -> str:
        from .spectator_gate import COOKIE_NAME

        if not _credential(request) and request.cookies.get(COOKIE_NAME):
            raise HTTPException(status_code=403, detail="spectator")
        agent = _authenticate_any(request)
        asked = (request.query_params.get("seat") or "").strip().upper()
        if asked and asked != agent.player_id:
            raise HTTPException(status_code=403, detail="other seat")
        return agent.player_id

    async def _bridge_body(request: Request, seat: str) -> dict[str, Any]:
        try:
            body = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="text") from exc
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="text")
        asked = str(body.get("seat") or "").strip().upper()
        if asked and asked != seat:
            raise HTTPException(status_code=403, detail="other seat")
        return body

    def _bridge_fail(exc: Exception) -> None:
        if isinstance(exc, ValueError):
            raise HTTPException(status_code=400, detail="text" if str(exc) == "text" else str(exc)) from exc
        if isinstance(exc, PermissionError):
            raise HTTPException(status_code=429, detail="rate") from exc
        if isinstance(exc, LookupError):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise exc

    @router.get("/bridge")
    async def bridge_since(request: Request, since: int = 0) -> dict[str, Any]:
        from . import bridge

        seat = _bridge_seat(request)
        return {"seat": seat, "messages": bridge.since(_match_key(), seat, since)}

    @router.get("/bridge/pending")
    async def bridge_pending(request: Request) -> dict[str, Any]:
        from . import bridge

        seat = _bridge_seat(request)
        return {"seat": seat, "orders": bridge.pending(_match_key(), seat)}

    @router.post("/bridge")
    async def bridge_post(request: Request) -> dict[str, Any]:
        from . import bridge

        seat = _bridge_seat(request)
        body = await _bridge_body(request, seat)
        try:
            return bridge.post(_match_key(), seat, "captain", str(body.get("text") or ""))
        except (ValueError, PermissionError, LookupError) as exc:
            _bridge_fail(exc)
            raise

    @router.post("/bridge/reply")
    async def bridge_reply(request: Request) -> dict[str, Any]:
        from . import bridge

        seat = _bridge_seat(request)
        body = await _bridge_body(request, seat)
        ack_of = body.get("ack_of")
        try:
            linked = None if ack_of in (None, "") else int(ack_of)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="ack_of") from exc
        try:
            return bridge.post(_match_key(), seat, "pilot", str(body.get("text") or ""), linked)
        except (ValueError, PermissionError, LookupError) as exc:
            _bridge_fail(exc)
            raise

    @router.post("/bridge/ack")
    async def bridge_ack(request: Request) -> dict[str, Any]:
        from . import bridge

        seat = _bridge_seat(request)
        body = await _bridge_body(request, seat)
        try:
            msg_id = int(body.get("id"))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="id") from exc
        try:
            return bridge.ack(_match_key(), seat, msg_id, str(body.get("status") or ""))
        except (ValueError, PermissionError, LookupError) as exc:
            _bridge_fail(exc)
            raise

    return router


def build_seat_claim_router(runner) -> APIRouter:
    """``GET /bot/claim?seat=P6&token=...`` -> HttpOnly seat cookie + redirect to the CU cockpit (G3).

    401 missing / unknown token, 403 token belongs to another seat (or
    non-loopback client without TW2K_HARNESS_ALLOW_REMOTE), 503 no match.
    """
    router = APIRouter(tags=["harness"])

    @router.get(seat_links.CLAIM_PATH)
    async def claim(request: Request, seat: str = "", token: str = "", mode: str = "cu") -> Response:
        host = (request.client.host if request.client else "") or ""
        if not _allow_remote() and host not in _LOOPBACK:
            raise HTTPException(status_code=403, detail="harness is loopback-only")
        if not runner.state.agents or runner.state.universe is None:
            raise HTTPException(status_code=503, detail="match not running")
        seat = seat.strip().upper()
        token = token.strip()
        if not seat or not token:
            raise HTTPException(status_code=401, detail="invalid seat link (missing seat or token)")
        owner = next((a for a in runner.state.agents if isinstance(a, ExternalAgent) and ht.verify(token, a.token)), None)
        if owner is None:
            raise HTTPException(status_code=401, detail="invalid seat link")
        if owner.player_id != seat:
            raise HTTPException(status_code=403, detail="this link belongs to a different seat")
        from urllib.parse import quote

        target = f"/bot?seat={seat}" + ("&mode=cu" if mode == "cu" else "")
        # The fragment is not sent back to the server, so a copied cockpit link
        # still carries the token and the access log does not.
        located = target + "#token=" + quote(token, safe="")
        secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https"
        resp = RedirectResponse(target, status_code=303)
        resp.headers["location"] = located
        resp.set_cookie(
            seat_links.cookie_name(seat), token, path=seat_links.COOKIE_PATH, httponly=True, samesite="lax",
            secure=secure, max_age=14 * 24 * 3600,
        )
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["Referrer-Policy"] = "no-referrer"
        return resp

    return router
