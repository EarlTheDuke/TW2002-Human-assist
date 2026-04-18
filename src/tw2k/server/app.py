"""FastAPI application wiring."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from ..agents.llm import default_provider
from ..engine import GameConfig
from .broadcaster import Broadcaster
from .runner import AgentSpec, MatchRunner, MatchSpec


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
    max_days: int = 10,
    agent_names: list[str] | None = None,
    agent_kind: str = "auto",  # "llm" | "heuristic" | "auto"
    provider: str | None = None,
    model: str | None = None,
    num_agents: int = 2,
    auto_start: bool = True,
) -> FastAPI:
    broadcaster = Broadcaster()
    runner = MatchRunner(broadcaster)

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
            )
            await runner.start(spec)
        yield
        await runner.stop()

    app = FastAPI(title="TW2K-AI", version="0.1.0", lifespan=lifespan)

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
        )
        await runner.start(spec)
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
) -> MatchSpec:
    names = agent_names or _default_agent_names(num_agents)
    if len(names) < num_agents:
        names = names + _default_agent_names(num_agents)[len(names):num_agents]
    names = names[:num_agents]

    resolved_kind = agent_kind
    if resolved_kind == "auto":
        resolved_kind = "llm" if default_provider() != "none" else "heuristic"

    cfg = GameConfig(
        seed=seed,
        universe_size=universe_size,
        max_days=max_days,
        corp_max_members=max(2, num_agents),
    )

    agents = [
        AgentSpec(
            player_id=f"P{i+1}",
            name=names[i],
            kind=resolved_kind,
            provider=provider,
            model=model,
        )
        for i in range(num_agents)
    ]
    return MatchSpec(config=cfg, agents=agents, action_delay_s=cfg.action_delay_s)


def _default_agent_names(n: int) -> list[str]:
    pool = [
        "Captain Reyes", "Admiral Vex", "Commodore Blake", "Warlord Kaine",
        "Baron Solari", "Lady Ferrix", "Ace Thorne", "Orion Duskwright",
    ]
    return pool[:max(n, 2)]
