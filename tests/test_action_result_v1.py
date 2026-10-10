"""The action API should say whether the game actually did the move.

Game 5: POST /action returned accepted:true, then the engine rejected the
move. The real answer was only in the event feed. A plotted route flew every
hop and then reported 0 turns.

ACTION_RESULT_MODE defaults to legacy, so the POST body and the route
accounting stay as they are. report waits for the engine and adds
result {ok, rejected, error, turns_spent}. The route result names the hops.

Plants:
  pb1 — report mode still omits result on the POST body.
  pb2 — report mode still returns turns_spent 0 after a two-hop route.
"""

from __future__ import annotations

import asyncio

import tw2k.engine.constants as K
from tw2k.agents.external import ExternalAgent
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import EventKind, Player
from tw2k.engine.runner import _warp_cost_for, apply_action
from tests.test_external_harness_phase1 import (
    TOK2,
    _app_and_client,
    _auth,
    _http_spec,
    _wait_until,
)


def _universe():
    cfg = GameConfig(
        seed=21, universe_size=40, max_days=3, turns_per_day=1000,
        starting_credits=20_000, enable_ferrengi=False, enable_planets=False,
    )
    u = generate_universe(cfg)
    p = Player(id="P1", name="Seat", agent_kind="external", sector_id=1, credits=20_000)
    u.players["P1"] = p
    u.sectors[1].occupant_ids.append("P1")
    p.known_sectors.add(1)
    p.known_warps[1] = list(u.sectors[1].warps)
    return u


def _two_hop_target(u) -> int:
    start = u.players["P1"].sector_id
    here = set(u.sectors[start].warps)
    for mid in u.sectors[start].warps:
        for nxt in u.sectors[mid].warps:
            if nxt != start and nxt not in here:
                return int(nxt)
    raise AssertionError("seed 21 has no two-hop target")


def _plot(u, target: int):
    return apply_action(u, "P1", Action(
        kind=ActionKind.PLOT_COURSE, args={"target": target, "execute": True},
    ))


def test_default_stays_legacy():
    assert K.ACTION_RESULT_MODE == "legacy"
    assert K.action_result_report() is False


def test_legacy_route_spends_the_hops_and_reports_zero():
    u = _universe()
    p = u.players["P1"]
    hop = _warp_cost_for(p)
    target = _two_hop_target(u)
    before = p.turns_today
    res = _plot(u, target)
    assert res.ok, res.error
    assert res.turns_spent == 0
    assert p.turns_today - before == 2 * hop
    done = next(e for e in reversed(u.events) if e.kind == EventKind.AUTOPILOT)
    assert "turns_spent" not in done.payload


def test_report_route_names_the_turns_it_spent(monkeypatch):
    monkeypatch.setattr(K, "ACTION_RESULT_MODE", "report")
    u = _universe()
    p = u.players["P1"]
    hop = _warp_cost_for(p)
    target = _two_hop_target(u)
    before = p.turns_today
    res = _plot(u, target)
    assert res.ok, res.error
    assert res.turns_spent == 2 * hop
    assert p.turns_today - before == 2 * hop
    done = next(e for e in reversed(u.events) if e.kind == EventKind.AUTOPILOT)
    assert done.payload["turns_spent"] == 2 * hop
    assert done.payload["hops_done"] == 2


def test_legacy_post_has_no_result_field(tmp_path):
    app, client = _app_and_client(tmp_path)
    runner = app.state.runner

    async def _go() -> None:
        await runner.start(_http_spec())
        assert await _wait_until(lambda: runner.state.universe is not None)
        r = await client.get(
            "/harness/v1/P2/observation", params={"wait_s": 5}, headers=_auth(TOK2),
        )
        assert r.status_code == 200
        turn = r.json()["turn_seq"]
        target = r.json()["observation"]["sector"]["warps_out"][0]
        posted = await client.post(
            "/harness/v1/P2/action",
            json={"turn_seq": turn, "action": {"kind": "warp", "args": {"target": target}}},
            headers=_auth(TOK2),
        )
        assert posted.status_code == 200
        body = posted.json()
        assert body["accepted"] is True
        assert "result" not in body
        await runner.stop()
        await client.aclose()

    asyncio.run(_go())


def test_report_post_says_rejected_when_the_engine_says_no(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "ACTION_RESULT_MODE", "report")
    app, client = _app_and_client(tmp_path)
    runner = app.state.runner

    async def _go() -> None:
        await runner.start(_http_spec())
        assert await _wait_until(lambda: runner.state.universe is not None)
        r = await client.get(
            "/harness/v1/P2/observation", params={"wait_s": 5}, headers=_auth(TOK2),
        )
        assert r.status_code == 200
        turn = r.json()["turn_seq"]
        posted = await client.post(
            "/harness/v1/P2/action",
            json={"turn_seq": turn, "action": {"kind": "warp", "args": {"target": 999999}}},
            headers=_auth(TOK2),
        )
        assert posted.status_code == 200
        body = posted.json()
        assert body["accepted"] is True
        assert body["result"]["ok"] is False
        assert body["result"]["rejected"] is True
        assert body["result"]["error"]
        seat = next(a for a in runner.state.agents if getattr(a, "player_id", None) == "P2")
        assert isinstance(seat, ExternalAgent)
        assert seat.last_result is not None
        assert seat.last_result["rejected"] is True
        await runner.stop()
        await client.aclose()

    asyncio.run(_go())
