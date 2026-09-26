"""Seat-bot S4 - seat-only acceptance harness for the S3 SeatBrain.

* Synthetic storyboards (no engine): the brain walks genesis -> deploy ->
  land -> build_citadel -> colonist ferry, each action valid per that
  observation's own legal_actions envelope.
* Validator negatives: missing planet_id / qty, execute=false, qty over cap,
  arg outside choices, illegal verb.
* Grid sweep: across synthetic states the brain never emits an action the
  envelope rejects.
* Record -> replay: an offline engine run records the seat's OWN observations
  (mailbox payload format); a fresh brain replays the trace to the same
  milestones with zero validation errors.
* End-to-end over the real HTTP harness: the brain plays a seat through
  /harness/v1 only; every request path is recorded and must stay inside that
  seat's endpoints (no /state, no other seat).
"""

from __future__ import annotations

import asyncio
import importlib.util
import itertools
from pathlib import Path

import httpx
import pytest

from tw2k.agents.pathb_client import SeatClient
from tw2k.agents.seat_acceptance import (
    MILESTONES,
    STORYBOARD,
    MilestoneTracker,
    ferry_storyboard,
    load_jsonl,
    replay,
    synthetic_obs,
    validate_action,
)
from tw2k.agents.seat_brain import SeatBrain
from tw2k.engine import GameConfig
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

ROOT = Path(__file__).resolve().parents[1]


def _script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Synthetic storyboards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("board_name,board", [("genesis", STORYBOARD), ("citadel_ferry", ferry_storyboard())])
def test_storyboard_brain_emits_expected_valid_actions(board_name, board) -> None:
    brain = SeatBrain()
    for label, obs, kind, args in board:
        action = brain.decide(obs)
        assert validate_action(obs, action) == [], (label, action)
        assert action["kind"] == kind, (label, action["kind"], action["thought"])
        for k, v in args.items():
            assert action["args"].get(k) == v, (label, k, action["args"])


def test_storyboards_reach_every_milestone_in_order() -> None:
    tracker = MilestoneTracker()
    i = 0
    for board in (STORYBOARD, ferry_storyboard()):
        brain = SeatBrain()
        for _label, obs, _kind, _args in board:
            tracker.observe(i, obs, brain.decide(obs))
            i += 1
    r = tracker.report
    assert r.errors == []
    assert r.missing() == [] and r.empire_loop_ok, r.summary()


def test_synthetic_cli_passes() -> None:
    assert _script("seat_brain_acceptance").run_synthetic() == 0


# ---------------------------------------------------------------------------
# Validator negatives
# ---------------------------------------------------------------------------


def _landed_obs():
    planet = {"id": 7, "sector_id": 5, "name": "G", "class": "M", "origin": "genesis", "citadel_level": 0,
              "citadel_target": 0, "colonists": {"fuel_ore": 1000, "organics": 600, "equipment": 300, "colonists": 600}}
    return synthetic_obs(sector=5, planets=[planet], landed=7, colonists=75)


def test_validator_flags_missing_planet_id_and_qty() -> None:
    obs = _landed_obs()
    errs = validate_action(obs, {"kind": "assign_colonists", "args": {"from": "ship", "to": "organics"}})
    assert any("planet_id" in e for e in errs) and any("'qty'" in e for e in errs)
    assert any("planet_id" in e for e in validate_action(obs, {"kind": "build_citadel", "args": {}}))
    ok = {"kind": "assign_colonists", "args": {"planet_id": 7, "from": "ship", "to": "organics", "qty": 75}}
    assert validate_action(obs, ok) == []


def test_validator_flags_bad_qty_choices_execute_and_illegal() -> None:
    obs = _landed_obs()
    over = {"kind": "assign_colonists", "args": {"planet_id": 7, "from": "ship", "to": "organics", "qty": 76}}
    assert any("exceeds" in e for e in validate_action(obs, over))
    zero = {"kind": "assign_colonists", "args": {"planet_id": 7, "from": "ship", "to": "organics", "qty": 0}}
    assert any("positive" in e for e in validate_action(obs, zero))
    wrong_planet = {"kind": "build_citadel", "args": {"planet_id": 99}}
    assert any("not in choices" in e for e in validate_action(obs, wrong_planet))
    space = synthetic_obs(sector=5)
    assert any("execute" in e for e in validate_action(space, {"kind": "plot_course", "args": {"target": 1}}))
    assert any("execute must be true" in e
               for e in validate_action(space, {"kind": "plot_course", "args": {"target": 1, "execute": False}}))
    assert any("illegal" in e for e in validate_action(space, {"kind": "deploy_genesis", "args": {}}))
    assert any("not in choices" in e for e in validate_action(space, {"kind": "warp", "args": {"target": 3}}))


# ---------------------------------------------------------------------------
# Grid sweep: brain never violates the envelope
# ---------------------------------------------------------------------------


def test_brain_actions_always_valid_across_synthetic_grid() -> None:
    worlds = [
        [],
        [{"id": 7, "sector_id": 5, "name": "G", "class": "M", "origin": "genesis", "citadel_level": 0, "citadel_target": 0,
          "colonists": {"fuel_ore": 1000, "organics": 600, "equipment": 300, "colonists": 600}}],
        [{"id": 7, "sector_id": 5, "name": "G", "class": "M", "origin": "genesis", "citadel_level": 1, "citadel_target": 2,
          "colonists": {"fuel_ore": 100, "organics": 50, "equipment": 0, "colonists": 0}}],
        [{"id": 8, "sector_id": 4, "name": "N", "class": "K", "origin": "claim", "citadel_level": 0, "citadel_target": 0,
          "colonists": {}}],
    ]
    checked = 0
    for sector, planets, colonists, genesis, credits in itertools.product(
            (1, 2, 3, 4, 5), worlds, (0, 75), (0, 1), (500, 35_000, 120_000)):
        landed_opts = [None] + [p["id"] for p in planets if p["sector_id"] == sector]
        for landed in landed_opts:
            obs = synthetic_obs(sector=sector, planets=planets, colonists=colonists, genesis=genesis,
                                credits=credits, landed=landed)
            action = SeatBrain().decide(obs)
            assert validate_action(obs, action) == [], (sector, planets, colonists, genesis, credits, landed, action)
            if landed is not None and planets and next(p for p in planets if p["id"] == landed)["origin"] == "claim":
                assert action["kind"] != "assign_colonists"  # never invest colonists in a claimed neutral
            checked += 1
    assert checked > 200


# ---------------------------------------------------------------------------
# Record -> replay (recorded fogged observations, fresh brain)
# ---------------------------------------------------------------------------


def test_record_then_replay_with_fresh_brain(tmp_path: Path) -> None:
    acc = _script("seat_brain_acceptance")
    trace = tmp_path / "seat_trace.jsonl"
    rec = acc.record_offline(trace, days=2)
    assert rec["rejected"] == 0
    assert rec["report"].empire_loop_ok, rec["report"].summary()
    payloads = load_jsonl(trace)
    assert payloads and set(payloads[0]) == {"seat", "turn_seq", "observation"}
    assert "legal_actions" in payloads[0]["observation"] and "owned_planets" in payloads[0]["observation"]
    report, actions = replay(SeatBrain(), payloads)
    assert report.errors == [], report.errors[:5]
    assert report.empire_loop_ok, report.summary()
    # The brain's decisions are a function of the observation stream alone.
    assert report.first == rec["report"].first and report.ferry_trips == rec["report"].ferry_trips
    assert acc.run_replay(trace) == 0


# ---------------------------------------------------------------------------
# End-to-end over the real harness, with request-path audit
# ---------------------------------------------------------------------------


def test_brain_over_http_harness_touches_only_its_own_seat(tmp_path: Path) -> None:
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"
    seen: list[str] = []

    async def spy(scope, receive, send):
        if scope["type"] == "http":
            seen.append(scope["path"])
        await app(scope, receive, send)

    token = "s4-token-p1-00000000000000000"
    spec = MatchSpec(
        config=GameConfig(seed=230923, universe_size=150, max_days=6, turns_per_day=250, starting_credits=120_000,
                          enable_ferrengi=False, enable_planets=True, action_delay_s=0.0),
        agents=[AgentSpec(player_id="P1", name="Seat", kind="external", external_token=token),
                AgentSpec(player_id="P2", name="HBot", kind="heuristic")],
        action_delay_s=0.0, external_timeout_s=30.0,
    )
    tracker = MilestoneTracker()
    brain = SeatBrain()
    stop = asyncio.Event()
    n = {"i": 0}

    def policy(ctx):
        action = brain.decide(ctx.observation)
        tracker.observe(n["i"], ctx.observation, action)
        n["i"] += 1
        if "colonists_assigned" in tracker.report.first and tracker.report.ferry_trips >= 2:
            stop.set()
        return action

    async def _go():
        await runner.start(spec)
        for _ in range(300):
            if runner.state.universe is not None and runner.state.agents:
                break
            await asyncio.sleep(0.02)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=spy, client=("127.0.0.1", 5555)),
                                     base_url="http://s4.test") as http:
            client = SeatClient(http, "P1", token, policy, wait_s=5.0, safety_margin_s=1.0)
            stats = await asyncio.wait_for(client.run(max_turns=600, stop=stop), timeout=240)
        await runner.stop()
        return stats

    stats = asyncio.run(_go())
    r = tracker.report
    assert r.errors == [], r.errors[:5]
    assert stats.failed == 0 and stats.stale == 0, stats
    assert all(m in r.first for m in MILESTONES), r.summary()
    assert r.empire_loop_ok and r.ferry_trips >= 2, r.summary()
    # Fog audit: the brain's only traffic is its own seat's harness endpoints.
    allowed = {"/harness/v1/rules", "/harness/v1/P1/observation", "/harness/v1/P1/action", "/harness/v1/P1/status"}
    assert seen and set(seen) <= allowed, sorted(set(seen) - allowed)
    assert not any("/state" in p or "/P2/" in p or p == "/harness/v1/seats" for p in seen)
