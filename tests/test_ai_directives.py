from __future__ import annotations

import httpx
import pytest

from tw2k.agents.prompts import format_observation
from tw2k.engine import EventKind, GameConfig, Player, build_observation, generate_universe
from tw2k.engine import constants as K
from tw2k.server.app import create_app


def _directive_universe():
    cfg = GameConfig(
        seed=404,
        universe_size=40,
        max_days=1,
        enable_ferrengi=False,
        enable_planets=False,
        action_delay_s=0.0,
    )
    u = generate_universe(cfg)
    p1 = Player(id="P1", name="Tiny Box", agent_kind="llm", sector_id=1)
    p2 = Player(id="P2", name="Bot", agent_kind="heuristic", sector_id=1)
    u.players[p1.id] = p1
    u.players[p2.id] = p2
    u.sectors[1].occupant_ids.extend([p1.id, p2.id])
    p1.known_sectors.add(1)
    p2.known_sectors.add(1)
    return u, p1, p2


def test_empty_directive_is_absent_from_formatted_observation() -> None:
    u, p1, _ = _directive_universe()
    obs = build_observation(u, p1.id)

    assert obs.operator_directive == ""
    rendered = format_observation(obs)
    assert '"operator_directive":""' in rendered
    assert "OPERATOR DIRECTIVE ACTIVE" not in obs.action_hint


def test_active_directive_reaches_observation_and_prompt() -> None:
    u, p1, _ = _directive_universe()
    p1.set_operator_directive("Prioritize getting back to StarDock and buying fighters.", day=2, tick=7)
    p1.append_operator_dialogue(role="operator", message="Explain risk if you ignore this.", day=2, tick=8)

    obs = build_observation(u, p1.id)
    rendered = format_observation(obs, compact=False)

    assert obs.operator_directive.startswith("Prioritize getting back")
    assert obs.operator_dialogue[-1]["message"] == "Explain risk if you ignore this."
    assert "OPERATOR DIRECTIVE ACTIVE" in obs.action_hint
    assert "operator_dialogue" in rendered
    assert "buying fighters" in rendered


@pytest.mark.asyncio
async def test_ai_directive_api_set_chat_clear_mutates_only_target(tmp_path) -> None:
    app = create_app(auto_start=False)
    app.state.runner._saves_root = tmp_path / "saves"  # type: ignore[attr-defined]
    u, p1, p2 = _directive_universe()
    app.state.runner.state.universe = u

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/ai-directives",
            json={"player_id": p1.id, "directive": "Build credits, then buy a CargoTran."},
        )
        assert r.status_code == 200, r.text
        assert r.json()["operator_directive"] == "Build credits, then buy a CargoTran."
        assert p2.operator_directive == ""

        r = await client.post(
            "/api/ai-directives/chat",
            json={"player_id": p1.id, "message": "What is your next safe step?"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["operator_dialogue"][-1]["message"] == "What is your next safe step?"

        r = await client.delete(f"/api/ai-directives?player_id={p1.id}")
        assert r.status_code == 200, r.text
        assert r.json()["operator_directive"] == ""

    kinds = [e.kind for e in u.events]
    assert EventKind.OPERATOR_DIRECTIVE_SET in kinds
    assert EventKind.OPERATOR_MESSAGE in kinds
    assert EventKind.OPERATOR_DIRECTIVE_CLEARED in kinds


def test_directive_state_appears_in_snapshot_and_patch() -> None:
    app = create_app(auto_start=False)
    u, p1, _ = _directive_universe()
    app.state.runner.state.universe = u
    p1.set_operator_directive("Avoid combat until re-armed.", day=u.day, tick=u.tick)

    snap = app.state.runner.snapshot()
    row = next(p for p in snap["players"] if p["id"] == p1.id)
    assert row["operator_directive"] == "Avoid combat until re-armed."

    ev = u.emit(
        EventKind.OPERATOR_DIRECTIVE_SET,
        actor_id=p1.id,
        actor_kind="operator",
        payload={"player_id": p1.id, "directive": p1.operator_directive},
        summary="test directive",
    )
    patch = app.state.runner._state_patch_for(ev)
    assert patch["player"]["operator_directive"] == "Avoid combat until re-armed."


def test_directive_and_dialogue_caps_are_enforced() -> None:
    _, p1, _ = _directive_universe()
    p1.set_operator_directive("x" * (K.OPERATOR_DIRECTIVE_MAX_CHARS + 200), day=1, tick=1)
    for i in range(K.OPERATOR_DIALOGUE_MAX_MESSAGES + 5):
        p1.append_operator_dialogue(
            role="operator",
            message=f"{i}-" + ("y" * (K.OPERATOR_DIALOGUE_MESSAGE_MAX_CHARS + 50)),
            day=1,
            tick=i,
        )

    assert len(p1.operator_directive) <= K.OPERATOR_DIRECTIVE_MAX_CHARS
    assert len(p1.operator_dialogue) == K.OPERATOR_DIALOGUE_MAX_MESSAGES
    assert p1.operator_dialogue[0]["tick"] == 5
    assert all(len(m["message"]) <= K.OPERATOR_DIALOGUE_MESSAGE_MAX_CHARS for m in p1.operator_dialogue)
