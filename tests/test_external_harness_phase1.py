"""Phase 1 tests — external (Grok Bot) seats.

Plan: docs/plans/2026-09-20-external-harness.md §5. Numbering below follows
the plan so Commander can tick acceptance criteria against it.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from tw2k.agents.external import (
    ExternalAgent,
    NotYourTurnError,
    QueueFullError,
    StaleTurnError,
)
from tw2k.engine import ActionKind, GameConfig, PlayerKind, generate_universe
from tw2k.engine.actions import Action
from tw2k.engine.models import EventKind as EK
from tw2k.engine.models import Player
from tw2k.server import harness_tokens as ht
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec


def _fake_obs():
    """Minimal duck-typed observation; ExternalAgent only stores it."""

    class _Obs:
        seq = 0

    return _Obs()


# ---------------------------------------------------------------------------
# 1. PlayerKind + actor_kind
# ---------------------------------------------------------------------------


def test_01_player_kind_external_round_trips_and_tags_events() -> None:
    assert PlayerKind("external") is PlayerKind.EXTERNAL
    cfg = GameConfig(seed=1, universe_size=40, max_days=2, turns_per_day=10)
    u = generate_universe(cfg)
    u.players["P3"] = Player(id="P3", name="GrokBot", agent_kind="external")
    ev = u.emit(EK.AGENT_THOUGHT, actor_id="P3", payload={"thought": "hi"})
    assert ev.actor_kind == "external"


# ---------------------------------------------------------------------------
# 2–5. ExternalAgent turn protocol
# ---------------------------------------------------------------------------


def test_02_act_blocks_until_submit_and_turn_seq_increments() -> None:
    async def _go() -> None:
        agent = ExternalAgent("P3", "GrokBot", token="t")
        assert agent.turn_seq == 0 and not agent.awaiting_input

        task = asyncio.create_task(agent.act(_fake_obs()))
        await asyncio.sleep(0.02)
        assert not task.done()
        assert agent.awaiting_input and agent.turn_seq == 1

        bound = await agent.submit_action(Action(kind=ActionKind.SCAN), turn_seq=1)
        assert bound == 1
        got = await asyncio.wait_for(task, timeout=1.0)
        assert got.kind == ActionKind.SCAN
        assert not agent.awaiting_input

        task2 = asyncio.create_task(agent.act(_fake_obs()))
        await asyncio.sleep(0.02)
        assert agent.turn_seq == 2
        await agent.submit_action(Action(kind=ActionKind.WAIT))  # turn_seq omitted is OK
        await asyncio.wait_for(task2, timeout=1.0)

    asyncio.run(_go())


def test_03_stale_not_your_turn_and_queue_full() -> None:
    async def _go() -> None:
        agent = ExternalAgent("P3", "GrokBot")
        with pytest.raises(NotYourTurnError):
            await agent.submit_action(Action(kind=ActionKind.WAIT))

        task = asyncio.create_task(agent.act(_fake_obs()))
        await asyncio.sleep(0.02)
        with pytest.raises(StaleTurnError) as ei:
            await agent.submit_action(Action(kind=ActionKind.WAIT), turn_seq=0)
        assert ei.value.current == 1 and ei.value.submitted == 0

        # First accepted, second for the same turn is rejected. Hold the
        # scheduler side so the queue stays full.
        agent._queue = asyncio.Queue(maxsize=1)  # fresh queue not yet awaited
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        # Re-enter a turn, then fill it without draining.
        agent.awaiting_input = True
        agent.turn_seq = 5
        await agent.submit_action(Action(kind=ActionKind.WAIT), turn_seq=5)
        with pytest.raises(QueueFullError):
            await agent.submit_action(Action(kind=ActionKind.WAIT), turn_seq=5)

    asyncio.run(_go())


def test_04_wait_for_turn_long_poll() -> None:
    async def _go() -> None:
        agent = ExternalAgent("P3", "GrokBot")
        assert await agent.wait_for_turn(0.05) is False

        waiter = asyncio.create_task(agent.wait_for_turn(2.0))
        await asyncio.sleep(0.02)
        act_task = asyncio.create_task(agent.act(_fake_obs()))
        assert await asyncio.wait_for(waiter, timeout=1.0) is True
        await agent.submit_action(Action(kind=ActionKind.WAIT))
        await act_task

    asyncio.run(_go())


def test_05_record_result_and_actor_kind_stripped() -> None:
    async def _go() -> None:
        agent = ExternalAgent("P3", "GrokBot")
        task = asyncio.create_task(agent.act(_fake_obs()))
        await asyncio.sleep(0.02)
        a = Action(kind=ActionKind.WAIT, actor_kind="copilot")
        await agent.submit_action(a)
        got = await task
        assert got.actor_kind is None
        agent.record_result(False, "out of turns", [7, 8])
        st = agent.status()
        assert st["last_result"]["ok"] is False
        assert st["last_result"]["error"] == "out of turns"
        assert st["last_result"]["event_seqs"] == [7, 8]
        assert st["last_result"]["turn_seq"] == 1

    asyncio.run(_go())


# ---------------------------------------------------------------------------
# 6. Token resolution
# ---------------------------------------------------------------------------


def test_06_token_resolution_order_and_persistence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tokens_file = tmp_path / "tok.json"
    tokens_file.write_text(json.dumps({"P4": "file-token-4444444444"}), encoding="utf-8")
    monkeypatch.setenv("TW2K_EXTERNAL_TOKEN_P5", "env-token-5555555555")
    monkeypatch.delenv("TW2K_EXTERNAL_TOKEN_P3", raising=False)

    out = ht.resolve_seat_tokens(
        {"P3": "explicit-333333333333", "P4": None, "P5": None, "P6": None},
        tokens_file=tokens_file,
    )
    assert out["P3"] == "explicit-333333333333"
    assert out["P4"] == "file-token-4444444444"
    assert out["P5"] == "env-token-5555555555"
    assert len(out["P6"]) >= 32  # generated

    on_disk = json.loads(tokens_file.read_text(encoding="utf-8"))
    # Only the generated one is persisted; explicit/env never leak into the file.
    assert set(on_disk) == {"P4", "P6"}
    assert on_disk["P6"] == out["P6"]

    # Second resolve reuses the persisted token (stable across restarts).
    again = ht.resolve_seat_tokens({"P6": None}, tokens_file=tokens_file)
    assert again["P6"] == out["P6"]

    m = ht.mask(out["P6"])
    assert "..." in m and len(m) == 11
    assert out["P6"] not in m
    assert ht.verify(out["P6"], out["P6"]) and not ht.verify("x", out["P6"]) and not ht.verify("", "")


def test_06b_gitignore_covers_tokens() -> None:
    gi = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert ".tw2k/" in gi
    assert "*external_tokens*.json" in gi


# ---------------------------------------------------------------------------
# 7–9. Runner integration
# ---------------------------------------------------------------------------


def _tiny_spec(*, external_timeout_s: float = 30.0, seed: int = 42) -> MatchSpec:
    cfg = GameConfig(
        seed=seed,
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
            AgentSpec(
                player_id="P2", name="GrokBot", kind="external", external_token="secret-token-2222222222"
            ),
        ],
        action_delay_s=0.0,
        external_timeout_s=external_timeout_s,
    )


async def _wait_until(pred, *, tries: int = 150, dt: float = 0.02) -> bool:
    for _ in range(tries):
        if pred():
            return True
        await asyncio.sleep(dt)
    return pred()


def test_07_scheduler_blocks_on_external_seat_and_applies_submitted_warp(tmp_path: Path) -> None:
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")

    async def _go() -> None:
        await runner.start(_tiny_spec())
        ext = None

        def _ready() -> bool:
            nonlocal ext
            if not runner.state.agents:
                return False
            ext = next(a for a in runner.state.agents if a.player_id == "P2")
            return bool(getattr(ext, "awaiting_input", False))

        assert await _wait_until(_ready), "scheduler never reached the external seat"
        assert isinstance(ext, ExternalAgent)
        assert ext.token == "secret-token-2222222222"
        u = runner.state.universe
        assert u is not None
        p2 = u.players["P2"]
        assert p2.agent_kind == "external"
        start_sector = p2.sector_id
        obs = ext.current_observation
        assert obs is not None and obs.self_id == "P2"
        target = obs.sector["warps_out"][0]

        await ext.submit_action(Action(kind=ActionKind.WARP, args={"target": target}), turn_seq=ext.turn_seq)
        assert await _wait_until(lambda: p2.sector_id == target), "warp not applied"
        assert p2.sector_id != start_sector
        assert await _wait_until(lambda: ext.last_result is not None and ext.last_result["ok"])
        warp_events = [e for e in u.events if e.kind == EK.WARP and e.actor_id == "P2"]
        assert warp_events and warp_events[0].actor_kind == "external"
        await runner.stop()

    asyncio.run(_go())


def test_08_timeout_applies_wait_emits_agent_error_and_streak_ends_day(tmp_path: Path) -> None:
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")

    async def _go() -> None:
        await runner.start(_tiny_spec(external_timeout_s=0.15))
        u = None

        def _errors() -> list:
            nonlocal u
            u = runner.state.universe
            if u is None:
                return []
            return [
                e
                for e in u.events
                if e.kind == EK.AGENT_ERROR and e.actor_id == "P2" and e.payload.get("external_timeout")
            ]

        assert await _wait_until(lambda: len(_errors()) >= 4, tries=400, dt=0.03)
        assert u is not None

        # Four consecutive timeout-WAITs trip the streak guard -> "ends the
        # day early" thought with turns_skipped. (turns_today itself resets
        # as soon as the day ticks, so assert on the event, not the counter.)
        def _day_ended() -> bool:
            return any(
                e.kind == EK.AGENT_THOUGHT
                and e.actor_id == "P2"
                and e.payload.get("turns_skipped") is not None
                for e in u.events
            )

        assert await _wait_until(_day_ended, tries=300, dt=0.03)
        ext = next(a for a in runner.state.agents if a.player_id == "P2")
        assert isinstance(ext, ExternalAgent)
        assert ext.last_result is not None and ext.last_result["ok"] is True  # WAIT applied fine
        await runner.stop()

    asyncio.run(_go())


def test_09_meta_json_records_kind_but_never_token(tmp_path: Path) -> None:
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")

    async def _go() -> None:
        await runner.start(_tiny_spec())
        assert await _wait_until(lambda: runner.state.save_dir is not None and runner.state.universe is not None)
        await runner.stop()

    asyncio.run(_go())
    save_dir = runner.state.save_dir
    assert save_dir is not None
    meta_text = (save_dir / "meta.json").read_text(encoding="utf-8")
    meta = json.loads(meta_text)
    kinds = {a["player_id"]: a["kind"] for a in meta["agents"]}
    assert kinds["P2"] == "external"
    assert "secret-token-2222222222" not in meta_text
    assert not any("token" in k.lower() for a in meta["agents"] for k in a)


# ---------------------------------------------------------------------------
# 10–14, 16. HTTP surface
# ---------------------------------------------------------------------------

TOK2 = "secret-token-2222222222"
TOK3 = "secret-token-3333333333"


def _http_spec(external_timeout_s: float = 30.0) -> MatchSpec:
    cfg = GameConfig(
        seed=42,
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
            AgentSpec(player_id="P2", name="GrokBot2", kind="external", external_token=TOK2),
            AgentSpec(player_id="P3", name="GrokBot3", kind="external", external_token=TOK3),
        ],
        action_delay_s=0.0,
        external_timeout_s=external_timeout_s,
    )


def _app_and_client(tmp_path: Path, *, client_host: str = "127.0.0.1"):
    import httpx

    from tw2k.server.app import create_app

    app = create_app(auto_start=False)
    app.state.runner._saves_root = tmp_path / "saves"
    transport = httpx.ASGITransport(app=app, client=(client_host, 5555))
    client = httpx.AsyncClient(transport=transport, base_url="http://harness.test")
    return app, client


def _auth(tok: str) -> dict[str, str]:
    return {"authorization": f"Bearer {tok}"}


def test_10_auth_matrix(tmp_path: Path) -> None:
    app, client = _app_and_client(tmp_path)
    runner = app.state.runner

    async def _go() -> None:
        # Before any match: 503 even with a token-looking header.
        r = await client.get("/harness/v1/P2/status", headers=_auth(TOK2))
        assert r.status_code == 503

        await runner.start(_http_spec())
        assert await _wait_until(lambda: bool(runner.state.agents) and runner.state.universe is not None)

        r = await client.get("/harness/v1/P2/status")
        assert r.status_code == 401
        r = await client.get("/harness/v1/P2/status", headers=_auth("nope-nope-nope-nope"))
        assert r.status_code == 401
        r = await client.get("/harness/v1/P3/status", headers=_auth(TOK2))
        assert r.status_code == 403
        r = await client.get("/harness/v1/P1/status", headers=_auth(TOK2))
        assert r.status_code == 409 and r.json()["detail"] == "not_external"
        r = await client.get("/harness/v1/P9/status", headers=_auth(TOK2))
        assert r.status_code == 404
        r = await client.get("/harness/v1/P2/status", headers=_auth(TOK2))
        assert r.status_code == 200
        body = r.json()
        assert body["player_id"] == "P2" and body["match_status"] == "running"
        assert "token" not in json.dumps(body).lower() or TOK2 not in json.dumps(body)

        r = await client.get("/harness/v1/seats", headers=_auth(TOK3))
        assert r.status_code == 200
        assert {s["player_id"] for s in r.json()["seats"]} == {"P2", "P3"}
        await runner.stop()
        await client.aclose()

    asyncio.run(_go())


def test_11_12_13_long_poll_observation_then_post_action(tmp_path: Path) -> None:
    app, client = _app_and_client(tmp_path)
    runner = app.state.runner

    async def _go() -> None:
        await runner.start(_http_spec())
        assert await _wait_until(lambda: bool(runner.state.agents) and runner.state.universe is not None)
        u = runner.state.universe
        assert u is not None

        # 11. long-poll until P2's turn
        r = await client.get(
            "/harness/v1/P2/observation", params={"wait_s": 5, "format": "both"}, headers=_auth(TOK2)
        )
        assert r.status_code == 200
        body = r.json()
        assert body["awaiting_input"] is True
        assert body["turn_seq"] == 1
        assert body["deadline_at"] is not None
        obs = body["observation"]
        assert obs["self_id"] == "P2"
        assert isinstance(body["llm_user_message"], str) and '"self"' in body["llm_user_message"]
        target = obs["sector"]["warps_out"][0]

        # 12a. stale turn_seq → 409 stale_turn with current_turn_seq
        r = await client.post(
            "/harness/v1/P2/action",
            json={"turn_seq": 0, "action": {"kind": "warp", "args": {"target": target}}},
            headers=_auth(TOK2),
        )
        assert r.status_code == 409
        assert r.json()["detail"]["code"] == "stale_turn"
        assert r.json()["detail"]["current_turn_seq"] == 1

        # 12b/13. valid post with actor_kind smuggled in → accepted, stripped
        r = await client.post(
            "/harness/v1/P2/action",
            json={
                "turn_seq": 1,
                "action": {"kind": "warp", "args": {"target": target}, "actor_kind": "copilot", "thought": "go"},
            },
            headers=_auth(TOK2),
        )
        assert r.status_code == 200 and r.json()["accepted"] is True
        p2 = u.players["P2"]
        assert await _wait_until(lambda: p2.sector_id == target)
        warp = next(e for e in u.events if e.kind == EK.WARP and e.actor_id == "P2")
        assert warp.actor_kind == "external"

        # status now shows last_result ok
        assert await _wait_until(
            lambda: (runner.state.agents[1].last_result or {}).get("ok") is True  # type: ignore[attr-defined]
        )
        r = await client.get("/harness/v1/P2/status", headers=_auth(TOK2))
        assert r.json()["last_result"]["ok"] is True

        # 12c. posting when not awaiting → 409 not_awaiting (P2 just acted;
        # scheduler is on P3 or P1 now)
        if not runner.state.agents[1].awaiting_input:  # type: ignore[attr-defined]
            r = await client.post(
                "/harness/v1/P2/action", json={"action": {"kind": "wait"}}, headers=_auth(TOK2)
            )
            assert r.status_code == 409 and r.json()["detail"]["code"] == "not_awaiting"

        # 422 on garbage
        r = await client.get("/harness/v1/P3/observation", params={"wait_s": 5}, headers=_auth(TOK3))
        assert r.json()["awaiting_input"] is True
        r = await client.post(
            "/harness/v1/P3/action", json={"action": {"kind": "teleport"}}, headers=_auth(TOK3)
        )
        assert r.status_code == 422

        await runner.stop()
        await client.aclose()

    asyncio.run(_go())


def test_14_rules_endpoint(tmp_path: Path) -> None:
    app, client = _app_and_client(tmp_path)
    runner = app.state.runner

    async def _go() -> None:
        await runner.start(_http_spec())
        assert await _wait_until(lambda: bool(runner.state.agents) and runner.state.universe is not None)
        r = await client.get("/harness/v1/rules", headers=_auth(TOK2))
        assert r.status_code == 200
        body = r.json()
        from tw2k.agents.prompts import get_system_prompt

        assert body["system_prompt"] == get_system_prompt()
        assert set(body["verbs"]) == {k.value for k in ActionKind}
        assert body["action_schema"]["title"] == "Action"
        await runner.stop()
        await client.aclose()

    asyncio.run(_go())


def test_15_build_default_spec_and_cli_external_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tw2k.server.app import _build_default_spec

    tokens_file = tmp_path / "tok.json"
    monkeypatch.setenv("TW2K_EXTERNAL_TOKENS_FILE", str(tokens_file))
    monkeypatch.delenv("TW2K_EXTERNAL_TIMEOUT_S", raising=False)

    spec = _build_default_spec(
        seed=1,
        universe_size=40,
        max_days=2,
        agent_names=None,
        agent_kind="heuristic",
        provider=None,
        model=None,
        num_agents=6,
        agent_overrides=[
            {"provider": "custom", "model": "qwen3.8:latest", "kind": "llm"},
            {"provider": "custom", "model": "qwen3.8:latest", "kind": "llm"},
            {"kind": "external", "token": "explicit-token-333333333"},
            {"kind": "external"},
            {"kind": "external"},
            {"kind": "external"},
        ],
        external_timeout_s=45,
    )
    kinds = [a.kind for a in spec.agents]
    assert kinds == ["llm", "llm", "external", "external", "external", "external"]
    assert spec.agents[0].provider == "custom" and spec.agents[0].model == "qwen3.8:latest"
    assert spec.agents[2].external_token == "explicit-token-333333333"
    gen = {a.player_id: a.external_token for a in spec.agents[3:]}
    assert all(t and len(t) >= 32 for t in gen.values())
    assert len(set(gen.values())) == 3
    assert spec.external_timeout_s == 45.0
    on_disk = json.loads(tokens_file.read_text(encoding="utf-8"))
    assert set(on_disk) == {"P4", "P5", "P6"}  # explicit P3 never persisted

    # Heuristic-only spec must not touch the tokens file.
    tokens_file.unlink()
    _build_default_spec(
        seed=1, universe_size=40, max_days=2, agent_names=None, agent_kind="heuristic",
        provider=None, model=None, num_agents=2,
    )
    assert not tokens_file.exists()

    # CLI: --external P3,P4 -> kind=external overrides without provider/model.
    captured: dict = {}

    def _fake_create_app(**kw):
        captured.update(kw)

        class _App:  # minimal stand-in for uvicorn.run
            pass

        return _App()

    import tw2k.cli as cli_mod
    import tw2k.server.app as app_mod

    monkeypatch.setattr(app_mod, "create_app", _fake_create_app)
    monkeypatch.setattr(cli_mod.uvicorn, "run", lambda *a, **k: None)
    from typer.testing import CliRunner

    res = CliRunner().invoke(
        cli_mod.app,
        ["serve", "--agent-kind", "heuristic", "--num-agents", "4", "--external", "P3,P4",
         "--external-timeout-s", "33", "--no-auto-start"],
    )
    assert res.exit_code == 0, res.output
    ov = captured["agent_overrides"]
    assert [o.get("kind") for o in ov] == [None, None, "external", "external"]
    assert "provider" not in ov[2] and "model" not in ov[2]
    assert captured["external_timeout_s"] == 33.0
    assert "EXTERNAL" in res.output and "token=" in res.output  # masked token in banner
    for tok in json.loads(tokens_file.read_text(encoding="utf-8")).values():
        assert tok not in res.output  # never printed unmasked


def test_16_loopback_only_unless_allowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TW2K_HARNESS_ALLOW_REMOTE", raising=False)
    app, client = _app_and_client(tmp_path, client_host="10.0.0.5")
    runner = app.state.runner

    async def _go() -> None:
        await runner.start(_http_spec())
        assert await _wait_until(lambda: bool(runner.state.agents) and runner.state.universe is not None)
        r = await client.get("/harness/v1/P2/status", headers=_auth(TOK2))
        assert r.status_code == 403
        monkeypatch.setenv("TW2K_HARNESS_ALLOW_REMOTE", "1")
        r = await client.get("/harness/v1/P2/status", headers=_auth(TOK2))
        assert r.status_code == 200
        await runner.stop()
        await client.aclose()

    asyncio.run(_go())
