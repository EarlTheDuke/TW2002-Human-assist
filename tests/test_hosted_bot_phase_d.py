"""Phase D (computer-use playtest fixes) - see docs/playtests/COMPUTER_USE_INSIGHTS.md.

P0  unattended external seats auto-WAIT after `external_idle_wait_s`, attended ones
    keep the full `external_timeout_s`.
P2  harness status carries `current_turn` (who the scheduler is on, kind, deadline).
P1  /bot markup exposes stable data-testid hooks for computer-use clicks.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import httpx

from tw2k.agents.external import ExternalAgent
from tw2k.engine import GameConfig
from tw2k.engine.models import EventKind as EK
from tw2k.server.app import create_app
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec

TOK2 = "phase-d-token-p2-0000000000"
TOK3 = "phase-d-token-p3-0000000000"


def _spec(*, idle_wait_s: float, timeout_s: float = 30.0) -> MatchSpec:
    cfg = GameConfig(
        seed=11,
        universe_size=60,
        max_days=2,
        turns_per_day=12,
        starting_credits=25_000,
        enable_ferrengi=False,
        enable_planets=False,
        action_delay_s=0.0,
    )
    return MatchSpec(
        config=cfg,
        agents=[
            AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
            AgentSpec(player_id="P2", name="Attended", kind="external", external_token=TOK2),
            AgentSpec(player_id="P3", name="Unattended", kind="external", external_token=TOK3),
        ],
        action_delay_s=0.0,
        external_timeout_s=timeout_s,
        external_idle_wait_s=idle_wait_s,
        external_attend_window_s=45.0,
    )


async def _until(pred, *, tries: int = 300, dt: float = 0.02) -> bool:
    for _ in range(tries):
        if pred():
            return True
        await asyncio.sleep(dt)
    return pred()


def test_attendance_helpers() -> None:
    a = ExternalAgent("P9", "X")
    assert a.is_attended(45.0) is False
    a.touch_client()
    assert a.is_attended(45.0) is True
    assert a.is_attended(0.0) is False
    assert a.status()["last_client_seen_at"] is not None


def test_p0_unattended_seat_auto_waits_quickly_but_attended_seat_keeps_full_timeout(tmp_path: Path) -> None:
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")

    async def _go() -> None:
        await runner.start(_spec(idle_wait_s=0.2, timeout_s=30.0))
        assert await _until(lambda: bool(runner.state.agents) and runner.state.universe is not None)
        u = runner.state.universe
        assert u is not None
        p2 = next(a for a in runner.state.agents if a.player_id == "P2")
        assert isinstance(p2, ExternalAgent)
        # A "bot" is polling P2: mark attended before the scheduler reaches it.
        p2.touch_client()

        def _idle_waits(pid: str) -> int:
            return sum(
                1
                for e in u.events
                if e.kind == EK.AGENT_THOUGHT and e.actor_id == pid and e.payload.get("external_idle")
            )

        # Unattended P3 must produce idle auto-WAITs fast (0.2s each), even though the
        # nominal timeout is 30s. Scheduler order is P1 -> P2 -> P3, so P2 must be
        # blocking first; we release P2 with a WAIT once it is awaiting.
        assert await _until(lambda: p2.awaiting_input, tries=200)
        t0 = asyncio.get_event_loop().time()
        # Attended seat: no idle WAIT should fire for P2 within 1.0s.
        await asyncio.sleep(1.0)
        assert p2.awaiting_input, "attended seat was cut short by idle-wait"
        assert _idle_waits("P2") == 0
        from tw2k.engine.actions import Action, ActionKind

        await p2.submit_action(Action(kind=ActionKind.WAIT), turn_seq=p2.turn_seq)
        assert await _until(lambda: _idle_waits("P3") >= 1, tries=200, dt=0.02)
        elapsed = asyncio.get_event_loop().time() - t0
        assert elapsed < 8.0, f"unattended idle-wait took {elapsed:.1f}s"
        # No AGENT_ERROR for the idle case - it's a quiet WAIT.
        assert not any(
            e.kind == EK.AGENT_ERROR and e.actor_id == "P3" and e.payload.get("external_timeout")
            for e in u.events
        )
        await runner.stop()

    asyncio.run(_go())


def test_p2_status_exposes_current_turn_and_touch_marks_attended(tmp_path: Path) -> None:
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 5555))
    client = httpx.AsyncClient(transport=transport, base_url="http://phase-d.test")

    async def _go() -> None:
        # idle_wait disabled here so the seats block deterministically.
        await runner.start(_spec(idle_wait_s=0.0, timeout_s=30.0))
        assert await _until(lambda: bool(runner.state.agents) and runner.state.universe is not None)
        p2 = next(a for a in runner.state.agents if a.player_id == "P2")
        assert isinstance(p2, ExternalAgent)
        assert await _until(lambda: p2.awaiting_input, tries=200)

        # P3 asks "whose turn?" -> it's P2's.
        r = await client.get("/harness/v1/P3/status", headers={"authorization": f"Bearer {TOK3}"})
        assert r.status_code == 200
        body = r.json()
        ct = body["current_turn"]
        assert ct["player_id"] == "P2" and ct["kind"] == "external" and ct["name"] == "Attended"
        assert ct["awaiting_input"] is True
        assert ct["deadline_at"] is not None and ct["deadline_at"] > ct["started_at"]
        # P2 has not polled -> reported unattended; P3 just did -> attended.
        assert ct["attended"] is False
        p3 = next(a for a in runner.state.agents if a.player_id == "P3")
        assert isinstance(p3, ExternalAgent) and p3.is_attended(45.0)

        # Now P2 polls: attendance flips.
        r = await client.get("/harness/v1/P2/status", headers={"authorization": f"Bearer {TOK2}"})
        assert r.json()["current_turn"]["attended"] is True
        assert r.json()["awaiting_input"] is True
        await runner.stop()
        await client.aclose()

    asyncio.run(_go())


def test_p1_bot_page_has_testids_and_large_targets() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "web" / "bot.html").read_text(encoding="utf-8")
    js = (root / "web" / "bot.js").read_text(encoding="utf-8")
    css = (root / "web" / "bot.css").read_text(encoding="utf-8")
    for tid in ("connect", "refresh", "action-scan", "action-wait", "action-sell", "action-buy", "seat", "token"):
        assert f'data-testid="{tid}"' in html, tid
    assert 'data-testid", `warp-${' in js or "data-testid\", `warp-" in js
    # >=56px buttons everywhere clickable
    m = re.search(r"\.auth-bar button, \.actions button, \.warps button \{[^}]*min-height:\s*(\d+)px", css)
    assert m and int(m.group(1)) >= 56
