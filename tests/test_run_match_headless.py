"""Tests for scripts/run_match_headless.py.

Covers artifact writing, gate logic, stuck-day detection, and end-to-end
heuristic matches (fast, no LLM).
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load_runner_module():
    """Import scripts/run_match_headless.py as a module ('run_match_headless').

    We go through importlib because `scripts` is not a package. We also prime
    sys.path so the script's own imports of `watch_match` and `tw2k.*` work."""
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "run_match_headless", ROOT / "scripts" / "run_match_headless.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def runner_mod():
    return _load_runner_module()


# ---------------------------------------------------------------------------
# gate_passed
# ---------------------------------------------------------------------------


def test_gate_passed_with_on_arc_player(runner_mod):
    summary = {
        "final_day": 3,
        "players": [
            {"days_on_arc": 0},
            {"days_on_arc": 2},
        ],
    }
    assert runner_mod.gate_passed(summary) is True


def test_gate_passed_all_failed(runner_mod):
    summary = {
        "final_day": 3,
        "players": [{"days_on_arc": 0}, {"days_on_arc": 0}],
    }
    assert runner_mod.gate_passed(summary) is False


def test_gate_passed_no_final_day(runner_mod):
    assert runner_mod.gate_passed({"final_day": 0, "players": []}) is False


def test_gate_passed_one_day_match_lowers_bar(runner_mod):
    # 1-day match with on_arc=1 should pass even if we asked for 5 days.
    summary = {
        "final_day": 1,
        "players": [{"days_on_arc": 1}],
    }
    assert runner_mod.gate_passed(summary, min_days_on_arc=5) is True


# ---------------------------------------------------------------------------
# event_to_dict + snapshot_state
# ---------------------------------------------------------------------------


def test_event_to_dict_normalises_enum_kind(runner_mod):
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.models import EventKind

    u = generate_universe(GameConfig(seed=7, universe_size=64, max_days=1))
    ev = u.emit(EventKind.GAME_START, summary="test")
    d = runner_mod.event_to_dict(ev)
    assert d["kind"] == "game_start"
    assert d["seq"] == ev.seq


def test_snapshot_state_shape(runner_mod):
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.models import Player, Ship

    u = generate_universe(GameConfig(seed=7, universe_size=64, max_days=1))
    u.players["P1"] = Player(id="P1", name="Alice", ship=Ship())
    u.players["P2"] = Player(id="P2", name="Bob", ship=Ship())

    s = runner_mod.snapshot_state(u)
    assert set(s.keys()) == {"players", "planets"}
    assert {p["id"] for p in s["players"]} == {"P1", "P2"}
    for p in s["players"]:
        assert "net_worth" in p and "credits" in p and "name" in p


# ---------------------------------------------------------------------------
# End-to-end headless heuristic match
# ---------------------------------------------------------------------------


def test_headless_heuristic_match_runs(runner_mod, tmp_path):
    out_dir = tmp_path / "run"
    runner = runner_mod.HeadlessRunner(
        seed=13,
        universe_size=100,
        max_days=2,
        num_agents=2,
        out_dir=out_dir,
        verbose=False,
    )
    summary = asyncio.run(runner.run())

    assert summary["finished"] is False or summary["winner_id"]  # may or may not finish
    assert summary["final_day"] >= 1
    assert summary["num_events"] > 0
    assert len(summary["players"]) == 2
    for p in summary["players"]:
        assert {"id", "name", "credits", "net_worth", "days_on_arc", "days_scored"} <= p.keys()

    for name in ("events.jsonl", "scorecards.txt", "summary.json", "run.log"):
        assert (out_dir / name).exists(), f"missing artifact {name}"

    # events.jsonl: each line is a valid JSON dict with a seq + kind
    lines = [line for line in (out_dir / "events.jsonl").read_text().splitlines() if line.strip()]
    assert lines, "no events written"
    for line in lines[:20]:
        e = json.loads(line)
        assert "seq" in e and "kind" in e

    # summary.json round-trips
    reloaded = json.loads((out_dir / "summary.json").read_text())
    assert reloaded["final_day"] == summary["final_day"]


def test_headless_scores_day_1_rubric(runner_mod):
    """After day 1, heuristic agents should have been evaluated against the
    rubric (arc.days_scored should advance)."""
    runner = runner_mod.HeadlessRunner(
        seed=13,
        universe_size=80,
        max_days=1,
        num_agents=2,
        out_dir=None,
        verbose=False,
    )
    asyncio.run(runner.run())
    # Each arc scores day 1 at minimum.
    for arc in runner.arcs.values():
        assert arc.days_scored >= 1


def test_headless_non_rubric_days_do_not_increment_days_scored(runner_mod):
    """Days past the rubric (>5) should not inflate days_scored."""
    runner = runner_mod.HeadlessRunner(
        seed=13,
        universe_size=60,
        max_days=7,  # two days past the rubric
        num_agents=2,
        out_dir=None,
        verbose=False,
    )
    asyncio.run(runner.run())
    for arc in runner.arcs.values():
        # Rubric only covers days 1-5, so no arc should have more than 5 scored days.
        assert arc.days_scored <= 5


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_no_artifacts_exits_cleanly(runner_mod):
    rc = runner_mod.main([
        "--days", "1",
        "--agents", "2",
        "--universe-size", "60",
        "--no-artifacts",
        "--no-gate",
        "--quiet",
    ])
    assert rc == 0
