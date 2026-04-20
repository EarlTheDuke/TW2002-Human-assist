"""Phase H1 tests — human cockpit UI + observation/humans endpoints + deadline.

What H1 promises (from docs/HUMAN_COPILOT_PLAN.md §12):
  1. /play serves a cockpit HTML page (and gracefully renders when no
     human slot exists or when the player needs to pick a slot).
  2. GET /api/match/humans enumerates HUMAN slots in the current match.
  3. GET /api/human/observation returns the full Observation the
     scheduler would give that human player RIGHT NOW — same object
     the LLM path consumes — exposed via HTTP so the cockpit can
     render "Copilot's view" and drive the action forms.
  4. --human-deadline-s forces an auto-WAIT when a human doesn't
     submit within the budget, so a match with a human slot cannot
     grind to a permanent halt if the player closes the tab.
  5. Pure-AI matches are totally unaffected by any H1 code path.

We drive the FastAPI app via httpx.ASGITransport — no uvicorn / real
port — so tests stay fast and deterministic on Windows.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from tw2k.agents.human import HumanAgent
from tw2k.engine import ActionKind, EventKind, GameConfig
from tw2k.engine.actions import Action
from tw2k.server.app import create_app
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec

# ---------------------------------------------------------------------------
# Static asset check — play.html / play.js / play.css exist
# ---------------------------------------------------------------------------


def test_play_assets_shipped() -> None:
    """The cockpit is three plain files in web/ — if any is missing,
    /play has nothing to serve. Lightweight sanity guard so accidental
    rename/delete blows up in CI before it hits a demo."""
    web_root = Path(__file__).resolve().parent.parent / "web"
    for fname in ("play.html", "play.js", "play.css"):
        p = web_root / fname
        assert p.is_file(), f"missing cockpit asset web/{fname}"
        assert p.stat().st_size > 100, f"suspiciously small web/{fname}"


# ---------------------------------------------------------------------------
# App fixtures — one app with a human slot, one without
# ---------------------------------------------------------------------------


def _app_with_human(tmp_path: Path) -> FastAPI:
    """Server with P1=heuristic, P2=HUMAN, no auto-start.

    Tests then kick a match by hand via the runner attached in
    app.state, which lets us control timing. We don't want auto-start
    because the lifespan handler would race with our test fixtures.
    """
    app = create_app(
        seed=101,
        universe_size=40,
        max_days=1,
        num_agents=2,
        agent_kind="heuristic",
        auto_start=False,
        turns_per_day=6,
        starting_credits=20_000,
        agent_overrides=[{}, {"kind": "human"}],
        action_delay_s=0.0,
    )
    return app


async def _start_match(app: FastAPI, tmp_path: Path) -> MatchRunner:
    """Boot a match through the app's runner so /api routes see the
    same universe. Returns the runner for direct manipulation."""
    runner: MatchRunner = app.state.runner
    runner._saves_root = tmp_path / "saves"  # type: ignore[attr-defined]
    spec = MatchSpec(
        config=GameConfig(
            seed=101,
            universe_size=40,
            max_days=1,
            turns_per_day=6,
            starting_credits=20_000,
            enable_ferrengi=False,
            enable_planets=False,
            action_delay_s=0.0,
        ),
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="You", kind="human"),
        ],
        action_delay_s=0.0,
    )
    await runner.start(spec)
    # Let the scheduler boot up + reach the human's first turn.
    for _ in range(120):
        await asyncio.sleep(0.02)
        u = runner.state.universe
        if u is None:
            continue
        if any(e.kind == EventKind.HUMAN_TURN_START for e in u.events):
            break
    return runner


@pytest.fixture
def app_with_human(tmp_path: Path) -> FastAPI:
    """Build a test app with one HUMAN slot (P2). The runner is
    pre-exposed on app.state.runner by create_app, so tests drive
    it directly without needing to introspect a closure."""
    return _app_with_human(tmp_path)


# ---------------------------------------------------------------------------
# /play static route
# ---------------------------------------------------------------------------


def test_play_route_serves_html(app_with_human: FastAPI) -> None:
    async def _go() -> None:
        transport = httpx.ASGITransport(app=app_with_human)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/play")
            assert r.status_code == 200
            assert "text/html" in r.headers["content-type"]
            body = r.text
            assert "TW2K-AI" in body
            assert "cockpit" in body.lower()
            # Should have cache-busted asset URLs
            assert "/static/play.js?v=" in body
            assert "/static/play.css?v=" in body

    asyncio.run(_go())


def test_play_route_also_works_without_humans(tmp_path: Path) -> None:
    """Even if a match has zero human slots, /play still returns 200 —
    the page itself renders a helpful "no human slot" view. This means
    the user can navigate to /play on any running match without a 404."""
    app = create_app(
        seed=42,
        universe_size=40,
        max_days=1,
        num_agents=2,
        agent_kind="heuristic",
        auto_start=False,
        turns_per_day=4,
        action_delay_s=0.0,
    )

    async def _go() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/play")
            assert r.status_code == 200
            assert "No human slot" in r.text or "noHuman" in r.text

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# /api/match/humans
# ---------------------------------------------------------------------------


def test_match_humans_lists_only_human_slots(
    app_with_human: FastAPI, tmp_path: Path
) -> None:
    async def _go() -> None:
        await _start_match(app_with_human, tmp_path)
        transport = httpx.ASGITransport(app=app_with_human)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/match/humans")
            assert r.status_code == 200
            body = r.json()
            ids = [h["player_id"] for h in body["humans"]]
            assert ids == ["P2"]
            only = body["humans"][0]
            assert only["name"] == "You"
            assert only["alive"] is True
            assert "sector_id" in only
            assert "turns_today" in only
        await app_with_human.state.runner.stop()

    asyncio.run(_go())


def test_match_humans_empty_when_no_human(tmp_path: Path) -> None:
    app = create_app(
        seed=42,
        universe_size=40,
        max_days=1,
        num_agents=2,
        agent_kind="heuristic",
        auto_start=False,
        action_delay_s=0.0,
    )

    async def _go() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/match/humans")
            assert r.status_code == 200
            assert r.json()["humans"] == []

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# /api/human/observation
# ---------------------------------------------------------------------------


def test_human_observation_returns_full_observation(
    app_with_human: FastAPI, tmp_path: Path
) -> None:
    """Exit-critical: the cockpit is driven by this endpoint. It must
    return every field the autonomous LLM path sees (self, ship,
    sector, adjacent, known_ports, known_warps, recent_failures,
    action_hint). If any goes missing the UI breaks silently."""

    async def _go() -> None:
        await _start_match(app_with_human, tmp_path)
        transport = httpx.ASGITransport(app=app_with_human)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/human/observation?player_id=P2")
            assert r.status_code == 200, r.text
            obs = r.json()
            for key in (
                "day",
                "tick",
                "self_id",
                "self_name",
                "credits",
                "turns_remaining",
                "turns_per_day",
                "ship",
                "sector",
                "adjacent",
                "known_ports",
                "known_warps",
                "recent_failures",
                "action_hint",
            ):
                assert key in obs, f"observation missing {key!r}"
            assert obs["self_id"] == "P2"
            assert obs["self_name"] == "You"
        await app_with_human.state.runner.stop()

    asyncio.run(_go())


def test_human_observation_rejects_non_human_slot(
    app_with_human: FastAPI, tmp_path: Path
) -> None:
    async def _go() -> None:
        await _start_match(app_with_human, tmp_path)
        transport = httpx.ASGITransport(app=app_with_human)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/human/observation?player_id=P1")
            assert r.status_code == 409
            assert "not a human" in r.json()["detail"].lower()
        await app_with_human.state.runner.stop()

    asyncio.run(_go())


def test_human_observation_404_on_unknown_player(
    app_with_human: FastAPI, tmp_path: Path
) -> None:
    async def _go() -> None:
        await _start_match(app_with_human, tmp_path)
        transport = httpx.ASGITransport(app=app_with_human)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/human/observation?player_id=P99")
            assert r.status_code == 404
        await app_with_human.state.runner.stop()

    asyncio.run(_go())


def test_human_observation_503_when_no_match(tmp_path: Path) -> None:
    app = create_app(
        seed=42,
        universe_size=40,
        max_days=1,
        num_agents=2,
        agent_kind="heuristic",
        auto_start=False,
        action_delay_s=0.0,
    )

    async def _go() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/human/observation?player_id=P1")
            assert r.status_code == 503

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# --human-deadline-s → auto-WAIT
# ---------------------------------------------------------------------------


def test_human_deadline_forces_auto_wait(tmp_path: Path) -> None:
    """With a short deadline set, the scheduler must force a WAIT on
    behalf of the human after the deadline elapses — otherwise a
    closed tab would halt the match forever. Emits an AGENT_THOUGHT
    event tagged auto_wait=True for forensics."""
    broadcaster = Broadcaster()
    runner = MatchRunner(broadcaster, saves_root=tmp_path / "saves")
    spec = MatchSpec(
        config=GameConfig(
            seed=55,
            universe_size=40,
            max_days=1,
            turns_per_day=4,
            starting_credits=15_000,
            enable_ferrengi=False,
            enable_planets=False,
            action_delay_s=0.0,
        ),
        agents=[
            AgentSpec(player_id="P1", name="Bot", kind="heuristic"),
            AgentSpec(player_id="P2", name="Idle", kind="human"),
        ],
        action_delay_s=0.0,
        # Very short deadline so the test finishes quickly.
        human_deadline_s=0.25,
    )

    async def _go() -> None:
        await runner.start(spec)
        # Never feed the human anything. Scheduler should auto-WAIT at
        # least once before the match ends. (tick_day resets
        # turns_today across day boundaries, so we check the monotonic
        # event log, not the live player counter.)
        for _ in range(60):
            await asyncio.sleep(0.05)
            u = runner.state.universe
            if u is None:
                continue
            auto_waits = [
                e
                for e in u.events
                if e.kind == EventKind.AGENT_THOUGHT
                and (e.payload or {}).get("auto_wait")
            ]
            if len(auto_waits) >= 1:
                break
            if runner.state.status in ("finished", "error"):
                break
        u = runner.state.universe
        assert u is not None
        auto_waits = [
            e
            for e in u.events
            if e.kind == EventKind.AGENT_THOUGHT
            and (e.payload or {}).get("auto_wait")
        ]
        assert auto_waits, "no auto_wait AGENT_THOUGHT emitted"
        assert auto_waits[0].actor_id == "P2"
        assert auto_waits[0].actor_kind == "human"
        await runner.stop()

    asyncio.run(_go())


def test_human_deadline_none_blocks_indefinitely(tmp_path: Path) -> None:
    """Backwards compat: deadline=None means "wait forever" — the
    existing H0 behavior. Critical guard so the default doesn't
    change under anyone's feet."""
    broadcaster = Broadcaster()
    runner = MatchRunner(broadcaster, saves_root=tmp_path / "saves")
    spec = MatchSpec(
        config=GameConfig(
            seed=56,
            universe_size=40,
            max_days=1,
            turns_per_day=4,
            starting_credits=15_000,
            enable_ferrengi=False,
            enable_planets=False,
            action_delay_s=0.0,
        ),
        agents=[
            AgentSpec(player_id="P1", name="Bot", kind="heuristic"),
            AgentSpec(player_id="P2", name="Idle", kind="human"),
        ],
        action_delay_s=0.0,
        human_deadline_s=None,
    )

    async def _go() -> None:
        await runner.start(spec)
        # Wait longer than any plausible human-turn-budget. Without a
        # deadline P2 must NOT auto-WAIT.
        await asyncio.sleep(0.5)
        u = runner.state.universe
        assert u is not None
        p2 = u.players["P2"]
        assert p2.turns_today == 0, "human advanced without a deadline set"
        # Prove it unblocks with an explicit action.
        hum = next(
            a for a in runner.state.agents
            if a.player_id == "P2" and isinstance(a, HumanAgent)
        )
        await hum.submit_action(Action(kind=ActionKind.WAIT))
        for _ in range(40):
            await asyncio.sleep(0.02)
            if p2.turns_today >= 1:
                break
        assert p2.turns_today >= 1
        await runner.stop()

    asyncio.run(_go())
