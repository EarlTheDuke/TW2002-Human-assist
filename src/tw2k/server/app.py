"""FastAPI application wiring."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from ..agents.human import HumanAgent
from ..agents.llm import default_provider
from ..copilot import CopilotMode
from ..copilot.dashboards import build_price_table, build_route_table
from ..copilot.registry import CopilotRegistry
from ..copilot.standing_orders import StandingOrder
from ..copilot.ui_agent import button_hints, suggest_next_move
from ..engine import GameConfig, build_observation
from ..engine.actions import Action
from .broadcaster import Broadcaster
from .replay import ReplayRunner
from .runner import AgentSpec, MatchRunner, MatchSpec



# Phase C.2 — kinds that end up in the /highlights feed. Mirrors
# web/app.js BIG_MOMENT_KINDS so the two stay in lockstep. These are
# the match-shaping events the UI highlight reel surfaces above the
# normal filter buckets.
_HIGHLIGHT_EVENT_KINDS = {
    "player_eliminated",
    "ship_destroyed",
    "port_destroyed",
    "atomic_detonation",
    "citadel_complete",
    "alliance_formed",
    "genesis_deployed",
    "corp_create",
    "game_over",
    "game_start",
}


def _collect_highlights(runner, limit: int) -> list[dict]:
    u = runner.state.universe
    if u is None:
        return []
    out: list[dict] = []
    for e in u.events:
        kv = e.kind.value if hasattr(e.kind, "value") else str(e.kind)
        if kv in _HIGHLIGHT_EVENT_KINDS:
            out.append(e.model_dump())
    if limit and len(out) > limit:
        out = out[-limit:]
    return out


def _web_root() -> Path:
    """Locate the shipped web/ directory regardless of install layout."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "web",  # repo checkout
        Path(__file__).resolve().parent.parent / "web",                # inside the package
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f"Couldn't locate web/ assets. Tried: {candidates}")


def create_app(
    *,
    seed: int = 42,
    universe_size: int = 1000,
    max_days: int = 15,
    agent_names: list[str] | None = None,
    agent_kind: str = "auto",  # "llm" | "heuristic" | "auto"
    provider: str | None = None,
    model: str | None = None,
    num_agents: int = 2,
    auto_start: bool = True,
    turns_per_day: int | None = None,
    starting_credits: int | None = None,
    all_start_stardock: bool = False,
    one_way_fraction: float | None = None,
    agent_overrides: list[dict] | None = None,
    action_delay_s: float | None = None,
    human_deadline_s: float | None = None,
    play_to_day_cap: bool = False,
) -> FastAPI:
    from .runner import _default_saves_root

    broadcaster = Broadcaster()
    runner = MatchRunner(broadcaster)
    # H5.1/H5.2 — per-player memory + decision traces live alongside
    # match saves so cleaning `saves/` wipes everything in one shot.
    _saves_root = _default_saves_root()
    copilot_registry = CopilotRegistry(
        memory_dir=_saves_root / "copilot_memory",
        trace_dir=_saves_root / "copilot_traces",
    )

    web_root = _web_root()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if auto_start:
            spec = _build_default_spec(
                seed=seed,
                universe_size=universe_size,
                max_days=max_days,
                agent_names=agent_names,
                agent_kind=agent_kind,
                provider=provider,
                model=model,
                num_agents=num_agents,
                turns_per_day=turns_per_day,
                starting_credits=starting_credits,
                all_start_stardock=all_start_stardock,
                one_way_fraction=one_way_fraction,
                agent_overrides=agent_overrides,
                action_delay_s=action_delay_s,
                human_deadline_s=human_deadline_s,
                play_to_day_cap=play_to_day_cap,
            )
            await runner.start(spec)
            # runner.start kicks off the scheduler loop in a background
            # task; `runner.state.agents` isn't populated synchronously.
            # Poll briefly so the copilot registry has human sessions
            # wired up before any API request (and the UI) arrives. A
            # live server happily reaches this point within a few ticks
            # so the wait is invisible in practice; tests exercising the
            # lifespan see deterministic readiness here.
            import asyncio as _asyncio

            for _ in range(200):
                if runner.state.agents and runner.state.universe is not None:
                    break
                await _asyncio.sleep(0.02)
            copilot_registry.rebuild(runner=runner, broadcaster=broadcaster)
        yield
        await runner.stop()
        copilot_registry.clear()

    app = FastAPI(title="TW2K-AI", version="0.1.0", lifespan=lifespan)
    # Expose the runner on app.state so tests (and potentially future
    # admin endpoints) can reach it without grabbing closure handles.
    # In production nothing reads this attribute; the endpoints all
    # close over `runner` directly.
    app.state.runner = runner
    app.state.broadcaster = broadcaster
    app.state.copilot_registry = copilot_registry

    # Static files
    app.mount("/static", StaticFiles(directory=str(web_root)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        html = (web_root / "index.html").read_text(encoding="utf-8")
        # Bust browser caches whenever app.js or style.css changes.
        try:
            js_v = int((web_root / "app.js").stat().st_mtime)
            css_v = int((web_root / "style.css").stat().st_mtime)
        except OSError:
            js_v = css_v = 0
        html = html.replace("/static/app.js", f"/static/app.js?v={js_v}")
        html = html.replace("/static/style.css", f"/static/style.css?v={css_v}")
        return HTMLResponse(
            html,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @app.get("/state")
    async def state() -> dict[str, Any]:
        return runner.snapshot()

    @app.get("/events")
    async def events(since: int = 0, limit: int = 200) -> dict[str, Any]:
        return {"events": runner.recent_events(since=since, limit=limit)}

    @app.get("/highlights")
    async def highlights(limit: int = 200) -> dict[str, Any]:
        """Phase C.2 — BIG_MOMENT_KINDS subset for the highlight reel.

        The spectator UI already filters the full event stream client
        side; this endpoint exists so a fresh browser connection can
        back-fill the reel without replaying all of /events and then
        discarding 90%.
        """
        return {"highlights": _collect_highlights(runner, max(1, min(1000, limit)))}

    @app.get("/history")
    async def history(limit: int = 120) -> dict[str, Any]:
        """Per-player sparkline data.

        Phase 4 of the UI overhaul. Each sample carries credits / net_worth /
        fighters / shields / experience / alignment / sector_id so the client
        can render inline SVG sparklines on player cards and in the drawer.
        """
        return runner.history_snapshot(limit=limit)

    @app.post("/control/pause")
    async def pause() -> dict[str, Any]:
        runner.pause()
        return {"status": runner.state.status}

    @app.post("/control/resume")
    async def resume() -> dict[str, Any]:
        runner.resume()
        return {"status": runner.state.status}

    @app.post("/control/speed")
    async def speed(body: dict[str, Any]) -> dict[str, Any]:
        runner.set_speed(float(body.get("multiplier", 1.0)))
        return {"speed": runner.state.speed_multiplier}

    @app.post("/api/human/action")
    async def submit_human_action(body: dict[str, Any]) -> dict[str, Any]:
        """Queue an Action for a HUMAN-kind player.

        Phase H0 contract:
          body = {"player_id": "P3", "action": {...Action JSON...}}

        The scheduler is already sitting on `await agent.act(obs)` for
        a human slot on its turn; pushing an Action here unblocks that
        call. Off-turn submissions are also accepted — they queue up
        and are consumed on the next time it becomes that player's
        turn. This keeps the endpoint idempotent and lets the /play
        UI stay ahead of the round-robin without racing the scheduler.

        Returns on success:
          {"queued": true, "player_id": "...", "pending": N,
           "observation_seq": K}
        Raises HTTPException on:
          * 404 — no such player_id in the live match
          * 409 — that player is not a HUMAN slot
          * 503 — match isn't running / no agents yet
          * 422 — action body failed Action.model_validate
          * 429 — agent's queue is full
        """
        player_id = body.get("player_id")
        raw_action = body.get("action")
        if not isinstance(player_id, str) or not player_id:
            raise HTTPException(status_code=400, detail="missing player_id")
        if not isinstance(raw_action, dict):
            raise HTTPException(status_code=400, detail="missing action body")

        agents_list = runner.state.agents
        if not agents_list:
            raise HTTPException(status_code=503, detail="match not running")

        agent: HumanAgent | None = None
        for a in agents_list:
            if a.player_id == player_id and isinstance(a, HumanAgent):
                agent = a
                break
        if agent is None:
            # Distinguish "no such player" from "player exists but isn't
            # a human" so the UI can show the right error.
            exists = any(a.player_id == player_id for a in agents_list)
            if not exists:
                raise HTTPException(status_code=404, detail=f"no such player {player_id}")
            raise HTTPException(status_code=409, detail=f"player {player_id} is not a human slot")

        try:
            action = Action.model_validate(raw_action)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"invalid action: {exc}") from exc

        try:
            await agent.submit_action(action)
        except RuntimeError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc

        return {
            "queued": True,
            "player_id": player_id,
            "pending": agent.pending,
            "observation_seq": agent.last_observation_seq,
        }

    @app.delete("/api/human/queue")
    async def flush_human_queue(player_id: str) -> dict[str, Any]:
        """Drop every pending action for a HUMAN slot.

        Phase H6 addition (M2-8 fix). Recovers a stuck human queue without
        restarting the server — e.g., when an external driver agent has
        jammed the queue with waits it can no longer clear, or the /play UI
        got out of sync with the scheduler.

        Response:
          {"player_id": "P1", "dropped": N, "pending": 0}
        Raises HTTPException on:
          * 400 — missing/empty player_id
          * 404 — no such player_id
          * 409 — player exists but isn't a HUMAN slot
          * 503 — match isn't running

        Safe to call while the scheduler is blocked on the agent's turn:
        ``await queue.get()`` just keeps waiting for the next push after
        the flush.
        """
        if not player_id:
            raise HTTPException(status_code=400, detail="missing player_id")
        agents_list = runner.state.agents
        if not agents_list:
            raise HTTPException(status_code=503, detail="match not running")
        agent: HumanAgent | None = None
        for a in agents_list:
            if a.player_id == player_id and isinstance(a, HumanAgent):
                agent = a
                break
        if agent is None:
            exists = any(a.player_id == player_id for a in agents_list)
            if not exists:
                raise HTTPException(status_code=404, detail=f"no such player {player_id}")
            raise HTTPException(status_code=409, detail=f"player {player_id} is not a human slot")
        dropped = agent.clear_queue()
        return {"player_id": player_id, "dropped": dropped, "pending": agent.pending}

    @app.get("/api/match/humans")
    async def list_humans() -> dict[str, Any]:
        """Enumerate HUMAN slots in the current match.

        Used by the /play cockpit to decide which player the user is
        flying. If no ?player= query-param is passed and exactly one
        human slot exists, the cockpit auto-binds to it. Multiple
        humans or zero humans both result in a chooser page.

        Each entry also carries `awaiting_input: bool`. This is the
        scheduler's ground truth for "it's this player's turn right
        now" — true iff the scheduler's current_player_idx points at
        this slot, the slot's action queue is empty, and the match is
        running. The /play page uses it to enable the action buttons
        on initial load (a HUMAN_TURN_START event fired before the WS
        connected is otherwise lost).
        """
        u = runner.state.universe
        if u is None:
            return {"humans": [], "status": runner.state.status}
        idx = runner.state.current_player_idx
        cur_player_id = (
            runner.state.agents[idx].player_id
            if 0 <= idx < len(runner.state.agents)
            else None
        )
        out: list[dict[str, Any]] = []
        for ag in runner.state.agents:
            if not isinstance(ag, HumanAgent):
                continue
            p = u.players.get(ag.player_id)
            if p is None:
                continue
            awaiting = (
                runner.state.status == "running"
                and cur_player_id == ag.player_id
                and ag.pending == 0
                and p.alive
            )
            out.append(
                {
                    "player_id": ag.player_id,
                    "name": ag.name,
                    "color": p.color,
                    "alive": p.alive,
                    "sector_id": p.sector_id,
                    "turns_today": p.turns_today,
                    "turns_per_day": p.turns_per_day,
                    "pending_actions": ag.pending,
                    "awaiting_input": awaiting,
                }
            )
        return {"humans": out, "status": runner.state.status, "day": u.day, "tick": u.tick}

    @app.get("/api/human/observation")
    async def human_observation(player_id: str) -> dict[str, Any]:
        """Full Observation for a human slot.

        Returns what `build_observation(universe, player_id)` would give
        the scheduler — same fields, same fog-of-war filtering, same
        action_hint. The /play cockpit renders a human-friendly subset
        (sector, ship, cargo, known ports, recent failures) AND lets
        the power user expand a "Copilot's view" panel to see the raw
        JSON exactly as an LLM agent would. That transparency is core
        to making the human/copilot split legible later on.

        Returns 404 if player_id doesn't exist, 409 if the player is
        not a HUMAN slot, 503 if no match is running.
        """
        u = runner.state.universe
        if u is None:
            raise HTTPException(status_code=503, detail="match not running")
        if player_id not in u.players:
            raise HTTPException(status_code=404, detail=f"no such player {player_id}")
        if u.players[player_id].agent_kind != "human":
            raise HTTPException(
                status_code=409, detail=f"player {player_id} is not a human slot"
            )
        try:
            obs = build_observation(u, player_id)
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"failed to build observation: {exc}"
            ) from exc
        return obs.model_dump(mode="json")

    # ------------------------------------------------------------------
    # Copilot endpoints (Phase H2 — text-only)
    # ------------------------------------------------------------------

    def _get_session(player_id: str):
        sess = copilot_registry.get(player_id)
        if sess is None:
            # Distinguish "no such player" from "not a human slot"
            # mirroring the /api/human/action error model.
            agents_list = runner.state.agents
            if not agents_list:
                raise HTTPException(status_code=503, detail="match not running")
            if not any(a.player_id == player_id for a in agents_list):
                raise HTTPException(
                    status_code=404, detail=f"no such player {player_id}"
                )
            raise HTTPException(
                status_code=409,
                detail=f"player {player_id} has no copilot session (not a human slot)",
            )
        return sess

    @app.get("/api/copilot/state")
    async def copilot_state(player_id: str) -> dict[str, Any]:
        """Full session snapshot for the cockpit chat panel."""
        sess = _get_session(player_id)
        return sess.state_snapshot()

    @app.post("/api/copilot/chat")
    async def copilot_chat(body: dict[str, Any]) -> dict[str, Any]:
        player_id = body.get("player_id")
        message = body.get("message")
        if not isinstance(player_id, str) or not isinstance(message, str):
            raise HTTPException(
                status_code=400, detail="body requires player_id + message strings"
            )
        sess = _get_session(player_id)
        resp = await sess.handle_chat(message)
        return {"ok": True, "response": resp.model_dump()}

    @app.post("/api/copilot/mode")
    async def copilot_mode(body: dict[str, Any]) -> dict[str, Any]:
        player_id = body.get("player_id")
        mode = body.get("mode")
        if not isinstance(player_id, str) or not isinstance(mode, str):
            raise HTTPException(status_code=400, detail="body requires player_id + mode")
        try:
            mode_enum = CopilotMode(mode)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"unknown mode {mode!r} (expected one of "
                + ", ".join(m.value for m in CopilotMode)
                + ")",
            ) from exc
        sess = _get_session(player_id)
        await sess.set_mode(mode_enum)
        return {"ok": True, "mode": sess.mode.value}

    @app.post("/api/copilot/confirm")
    async def copilot_confirm(body: dict[str, Any]) -> dict[str, Any]:
        player_id = body.get("player_id")
        plan_id = body.get("plan_id")
        if not isinstance(player_id, str) or not isinstance(plan_id, str):
            raise HTTPException(
                status_code=400, detail="body requires player_id + plan_id"
            )
        sess = _get_session(player_id)
        ok = await sess.confirm_pending(plan_id)
        if not ok:
            raise HTTPException(status_code=404, detail="no matching pending plan")
        return {"ok": True}

    @app.post("/api/copilot/cancel")
    async def copilot_cancel(body: dict[str, Any]) -> dict[str, Any]:
        """Cancel the pending plan OR the active autopilot task — whichever
        is live. If both are live, cancels both (Esc in the UI maps here).
        """
        player_id = body.get("player_id")
        plan_id = body.get("plan_id")
        if not isinstance(player_id, str):
            raise HTTPException(status_code=400, detail="body requires player_id")
        sess = _get_session(player_id)
        cancelled_plan = await sess.cancel_pending(
            plan_id if isinstance(plan_id, str) else None
        )
        cancelled_task = await sess.cancel_active_task(
            reason=str(body.get("reason") or "human_cancel")
        )
        return {"ok": True, "cancelled_plan": cancelled_plan, "cancelled_task": cancelled_task}

    @app.post("/api/copilot/standing-orders")
    async def copilot_add_order(body: dict[str, Any]) -> dict[str, Any]:
        player_id = body.get("player_id")
        order_raw = body.get("order")
        if not isinstance(player_id, str) or not isinstance(order_raw, dict):
            raise HTTPException(
                status_code=400, detail="body requires player_id + order object"
            )
        sess = _get_session(player_id)
        try:
            order = StandingOrder.model_validate(order_raw)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"invalid order: {exc}") from exc
        await sess.add_standing_order(order)
        return {"ok": True, "orders": [o.model_dump() for o in sess.standing_orders]}

    @app.delete("/api/copilot/standing-orders")
    async def copilot_remove_order(player_id: str, order_id: str) -> dict[str, Any]:
        sess = _get_session(player_id)
        ok = await sess.remove_standing_order(order_id)
        if not ok:
            raise HTTPException(status_code=404, detail="no such order")
        return {"ok": True, "orders": [o.model_dump() for o in sess.standing_orders]}

    @app.get("/api/copilot/safety")
    async def copilot_safety(player_id: str) -> dict[str, Any]:
        """H4: one-shot safety evaluation for the named human player.

        The `/play` cockpit polls this on mode change and uses the
        returned level to render an escalation banner before any
        autopilot actions fire.
        """
        registry = getattr(app.state, "copilot_registry", None)
        if registry is None:
            raise HTTPException(status_code=503, detail="copilot not ready")
        sess = registry.get(player_id)
        if sess is None:
            raise HTTPException(
                status_code=404, detail=f"no copilot session for {player_id}"
            )
        return sess.safety_snapshot()

    @app.get("/api/copilot/memory")
    async def copilot_memory(player_id: str) -> dict[str, Any]:
        """H5.1: per-player long-term memory snapshot."""
        sess = _get_session(player_id)
        return sess.memory_snapshot()

    @app.post("/api/copilot/memory/remember")
    async def copilot_memory_remember(body: dict[str, Any]) -> dict[str, Any]:
        player_id = body.get("player_id")
        key = body.get("key")
        value = body.get("value")
        if not isinstance(player_id, str) or not isinstance(key, str) or not isinstance(
            value, str
        ):
            raise HTTPException(
                status_code=400,
                detail="body requires player_id + key + value strings",
            )
        sess = _get_session(player_id)
        ok = await sess.remember(key, value)
        if not ok:
            raise HTTPException(status_code=422, detail="empty key or value")
        return {"ok": True, "memory": sess.memory_snapshot()}

    @app.post("/api/copilot/memory/forget")
    async def copilot_memory_forget(body: dict[str, Any]) -> dict[str, Any]:
        player_id = body.get("player_id")
        key = body.get("key")
        if not isinstance(player_id, str) or not isinstance(key, str):
            raise HTTPException(
                status_code=400, detail="body requires player_id + key strings"
            )
        sess = _get_session(player_id)
        had = await sess.forget(key)
        return {"ok": True, "existed": had, "memory": sess.memory_snapshot()}

    @app.get("/api/copilot/whatif")
    async def copilot_whatif(player_id: str) -> dict[str, Any]:
        """H5.4: predicted outcome for the player's current pending plan.

        Returns ``{pending: false}`` when there's nothing to preview —
        the cockpit renders nothing in that case.
        """
        sess = _get_session(player_id)
        snap = sess.whatif_snapshot()
        if snap is None:
            return {"pending": False}
        return {"pending": True, **snap}

    @app.get("/api/economy/prices")
    async def economy_prices(player_id: str) -> dict[str, Any]:
        """H6.4: per-port live prices + stock for every port the player has scouted.

        Returns 404 if the player doesn't exist, 503 if no match is
        running. Respects fog-of-war (only ports in ``known_ports``
        appear). Prices are recomputed from current universe state so
        the UI matches what a trade would actually execute at.
        """
        u = runner.state.universe
        if u is None:
            raise HTTPException(status_code=503, detail="match not running")
        if player_id not in u.players:
            raise HTTPException(status_code=404, detail=f"no such player {player_id}")
        return build_price_table(u, player_id)

    @app.get("/api/economy/routes")
    async def economy_routes(
        player_id: str, max_routes: int = 10
    ) -> dict[str, Any]:
        """H6.4: top-N trade routes across the player's known ports.

        Computes credits-per-turn for every (port_A sells X → port_B
        buys X) pair the player has discovered, subject to the player's
        current cargo-hold capacity and BFS round-trip distance.
        Returns empty ``routes`` list when the player has seen fewer
        than 2 ports or no profitable pair exists yet.
        """
        u = runner.state.universe
        if u is None:
            raise HTTPException(status_code=503, detail="match not running")
        if player_id not in u.players:
            raise HTTPException(status_code=404, detail=f"no such player {player_id}")
        return build_route_table(u, player_id, max_routes=max(1, min(50, max_routes)))

    @app.get("/api/copilot/hints")
    async def copilot_hints(player_id: str) -> dict[str, Any]:
        """Rule-based UIAgent hints for the cockpit button row.

        Fast + no LLM call, so the UI can re-request this on every
        observation refresh without cost.
        """
        u = runner.state.universe
        if u is None:
            raise HTTPException(status_code=503, detail="match not running")
        if player_id not in u.players:
            raise HTTPException(status_code=404, detail=f"no such player {player_id}")
        if u.players[player_id].agent_kind != "human":
            raise HTTPException(
                status_code=409, detail=f"player {player_id} is not a human slot"
            )
        obs = build_observation(u, player_id)
        return {
            "hints": button_hints(obs),
            "suggest": suggest_next_move(obs),
        }

    @app.get("/play", response_class=HTMLResponse)
    async def play_page() -> HTMLResponse:
        """Human cockpit. One page for every human slot in the match.

        The page itself is stateless; all state comes from /api endpoints
        and the /ws event stream. Navigate with ?player=P2 to bind a
        browser session to a specific human slot; with no query param
        and exactly one human slot, the cockpit auto-binds.
        """
        play_path = web_root / "play.html"
        if not play_path.is_file():
            raise HTTPException(status_code=404, detail="play.html not found")
        html = play_path.read_text(encoding="utf-8")
        try:
            js_v = int((web_root / "play.js").stat().st_mtime)
            css_v = int((web_root / "play.css").stat().st_mtime)
            shared_css_v = int((web_root / "style.css").stat().st_mtime)
        except OSError:
            js_v = css_v = shared_css_v = 0
        html = html.replace("/static/play.js", f"/static/play.js?v={js_v}")
        html = html.replace("/static/play.css", f"/static/play.css?v={css_v}")
        html = html.replace("/static/style.css", f"/static/style.css?v={shared_css_v}")
        return HTMLResponse(
            html,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @app.post("/control/restart")
    async def restart(body: dict[str, Any] | None = None) -> dict[str, Any]:
        body = body or {}
        spec = _build_default_spec(
            seed=int(body.get("seed", seed)),
            universe_size=int(body.get("universe_size", universe_size)),
            max_days=int(body.get("max_days", max_days)),
            agent_names=body.get("agent_names", agent_names),
            agent_kind=body.get("agent_kind", agent_kind),
            provider=body.get("provider", provider),
            model=body.get("model", model),
            num_agents=int(body.get("num_agents", num_agents)),
            turns_per_day=(int(body["turns_per_day"]) if "turns_per_day" in body else turns_per_day),
            starting_credits=(int(body["starting_credits"]) if "starting_credits" in body else starting_credits),
            all_start_stardock=(
                bool(body["all_start_stardock"])
                if "all_start_stardock" in body
                else all_start_stardock
            ),
            # Per-agent overrides: a list of dicts, each with optional
            # `provider`, `model`, `name`, `kind`. Slot N in the list maps to
            # player PN+1. Missing slots fall back to the global provider/model.
            # This is the hook for multi-model matches (e.g., Grok vs Claude).
            agent_overrides=body.get("agents", agent_overrides),
            action_delay_s=(float(body["action_delay_s"]) if "action_delay_s" in body else action_delay_s),
            play_to_day_cap=(
                bool(body["play_to_day_cap"])
                if "play_to_day_cap" in body
                else play_to_day_cap
            ),
        )
        await runner.start(spec)
        # Rebuild copilot sessions — old ones held references to the
        # previous match's HumanAgent queues which are now garbage. Chat
        # history from the prior match is intentionally wiped; if we
        # ever want persistence across restarts, that's a future knob.
        copilot_registry.rebuild(runner=runner, broadcaster=broadcaster)
        return {"status": runner.state.status}

    @app.websocket("/ws")
    async def ws(sock: WebSocket) -> None:
        await sock.accept()
        queue = await broadcaster.subscribe()
        # Initial snapshot
        try:
            await sock.send_text(json.dumps({"type": "snapshot", "snapshot": runner.snapshot()}, default=str))
        except Exception:
            await broadcaster.unsubscribe(queue)
            return

        async def pump() -> None:
            try:
                while True:
                    msg = await queue.get()
                    await sock.send_text(msg)
            except (WebSocketDisconnect, asyncio.CancelledError):
                pass
            except Exception:
                pass

        task = asyncio.create_task(pump())
        try:
            while True:
                # Keep the connection alive; accept any client pings
                try:
                    msg = await sock.receive_text()
                    if msg == "ping":
                        await sock.send_text("pong")
                except WebSocketDisconnect:
                    break
        finally:
            task.cancel()
            await broadcaster.unsubscribe(queue)

    return app


def _build_default_spec(
    *,
    seed: int,
    universe_size: int,
    max_days: int,
    agent_names: list[str] | None,
    agent_kind: str,
    provider: str | None,
    model: str | None,
    num_agents: int,
    turns_per_day: int | None = None,
    starting_credits: int | None = None,
    all_start_stardock: bool = False,
    one_way_fraction: float | None = None,
    agent_overrides: list[dict] | None = None,
    action_delay_s: float | None = None,
    human_deadline_s: float | None = None,
    play_to_day_cap: bool = False,
) -> MatchSpec:
    names = agent_names or _default_agent_names(num_agents)
    if len(names) < num_agents:
        names = names + _default_agent_names(num_agents)[len(names):num_agents]
    names = names[:num_agents]

    resolved_kind = agent_kind
    if resolved_kind == "auto":
        resolved_kind = "llm" if default_provider() != "none" else "heuristic"

    cfg_kwargs: dict = dict(
        seed=seed,
        universe_size=universe_size,
        max_days=max_days,
        corp_max_members=max(2, num_agents),
    )
    if turns_per_day is not None:
        cfg_kwargs["turns_per_day"] = turns_per_day
    if starting_credits is not None:
        cfg_kwargs["starting_credits"] = starting_credits
    if all_start_stardock:
        cfg_kwargs["all_start_stardock"] = True
    if one_way_fraction is not None:
        # Clamp to [0.0, 1.0] — universe.py expects a probability.
        cfg_kwargs["one_way_fraction"] = max(0.0, min(1.0, float(one_way_fraction)))
    if action_delay_s is not None:
        cfg_kwargs["action_delay_s"] = action_delay_s
    if play_to_day_cap:
        cfg_kwargs["play_to_day_cap"] = True
    cfg = GameConfig(**cfg_kwargs)

    # Per-agent overrides — slot N of the list maps to player P(N+1). Each
    # entry may specify any of: provider, model, name, kind. Missing fields
    # fall back to the global values. Missing slots use globals entirely.
    # Enables matches like "P1 = Grok, P2 = Claude Sonnet 4.5".
    overrides = list(agent_overrides or [])

    agents: list[AgentSpec] = []
    for i in range(num_agents):
        ov = overrides[i] if i < len(overrides) else {}
        if not isinstance(ov, dict):
            ov = {}
        agents.append(
            AgentSpec(
                player_id=f"P{i+1}",
                name=str(ov.get("name") or names[i]),
                kind=str(ov.get("kind") or resolved_kind),
                provider=ov.get("provider", provider),
                model=ov.get("model", model),
            )
        )
    return MatchSpec(
        config=cfg,
        agents=agents,
        action_delay_s=cfg.action_delay_s,
        human_deadline_s=human_deadline_s,
    )


def _default_agent_names(n: int) -> list[str]:
    pool = [
        "Captain Reyes", "Admiral Vex", "Commodore Blake", "Warlord Kaine",
        "Baron Solari", "Lady Ferrix", "Ace Thorne", "Orion Duskwright",
    ]
    return pool[:max(n, 2)]


def create_replay_app(replay_dir: Path, *, speed: float = 1.0) -> FastAPI:
    """Return a spectator-UI app wired to replay a saved run-dir.

    The UI is byte-identical to the live spectator; only the runner
    differs. `/control/restart` is disabled in replay mode because
    there's nothing to start — you'd want `tw2k replay <other-dir>` for
    a different match.
    """
    broadcaster = Broadcaster()
    runner = ReplayRunner(broadcaster, replay_dir)
    runner.set_speed(speed)

    web_root = _web_root()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await runner.start()
        yield
        await runner.stop()

    app = FastAPI(title=f"TW2K-AI Replay · {replay_dir.name}", version="0.1.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(web_root)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        html = (web_root / "index.html").read_text(encoding="utf-8")
        try:
            js_v = int((web_root / "app.js").stat().st_mtime)
            css_v = int((web_root / "style.css").stat().st_mtime)
        except OSError:
            js_v = css_v = 0
        html = html.replace("/static/app.js", f"/static/app.js?v={js_v}")
        html = html.replace("/static/style.css", f"/static/style.css?v={css_v}")
        return HTMLResponse(
            html,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @app.get("/state")
    async def state() -> dict[str, Any]:
        snap = runner.snapshot()
        snap["mode"] = "replay"
        snap["run_id"] = runner.state.run_id
        return snap

    @app.get("/events")
    async def events(since: int = 0, limit: int = 200) -> dict[str, Any]:
        return {"events": runner.recent_events(since=since, limit=limit)}

    @app.get("/highlights")
    async def highlights(limit: int = 200) -> dict[str, Any]:
        return {"highlights": _collect_highlights(runner, max(1, min(1000, limit)))}

    @app.get("/history")
    async def history(limit: int = 120) -> dict[str, Any]:
        return runner.history_snapshot(limit=limit)

    @app.post("/control/pause")
    async def pause() -> dict[str, Any]:
        runner.pause()
        return {"status": runner.state.status}

    @app.post("/control/resume")
    async def resume() -> dict[str, Any]:
        runner.resume()
        return {"status": runner.state.status}

    @app.post("/control/speed")
    async def speed_route(body: dict[str, Any]) -> dict[str, Any]:
        runner.set_speed(float(body.get("multiplier", 1.0)))
        return {"speed": runner.state.speed_multiplier}

    @app.post("/control/restart")
    async def restart_disabled() -> dict[str, Any]:
        # Replay mode: restart would need a fresh match spec. Surface
        # a clear error instead of silently re-running the same log.
        return {
            "status": "unsupported",
            "error": "restart is disabled in replay mode — use `tw2k replay <dir>` for a different run",
        }

    @app.websocket("/ws")
    async def ws(sock: WebSocket) -> None:
        await sock.accept()
        queue = await broadcaster.subscribe()
        try:
            await sock.send_text(
                json.dumps({"type": "snapshot", "snapshot": runner.snapshot()}, default=str)
            )
        except Exception:
            await broadcaster.unsubscribe(queue)
            return

        async def pump() -> None:
            try:
                while True:
                    msg = await queue.get()
                    await sock.send_text(msg)
            except (WebSocketDisconnect, asyncio.CancelledError):
                pass
            except Exception:
                pass

        task = asyncio.create_task(pump())
        try:
            while True:
                try:
                    msg = await sock.receive_text()
                    if msg == "ping":
                        await sock.send_text("pong")
                except WebSocketDisconnect:
                    break
        finally:
            task.cancel()
            await broadcaster.unsubscribe(queue)

    return app
