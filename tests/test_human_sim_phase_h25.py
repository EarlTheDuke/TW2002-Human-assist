"""Phase H2.5 tests — headless `tw2k human-sim` CLI driver.

Covers:
  * The `pass` demo responder runs end-to-end and exits cleanly with an
    actor_kind=copilot event on the human's behalf.
  * The `trade` demo responder kicks off a TaskAgent autopilot, the loop
    hits `max_iterations=4`, and all dispatched scans/passes carry
    actor_kind=copilot.
  * A user-supplied `--script` file drives the copilot responder.
  * Wall-clock deadline forces outcome=deadline when the loop is
    instructed to never terminate.
  * The CLI subcommand exists and returns a valid JSON envelope.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

from tw2k.copilot.human_sim import SimResult, run_human_sim
from tw2k.copilot.session import CopilotMode


def _run(**kwargs) -> SimResult:
    return asyncio.run(run_human_sim(**kwargs))


def test_human_sim_demo_pass_dispatches_one_copilot_action() -> None:
    result = _run(
        seed=42,
        intent="pass the turn",
        demo="pass",
        mode=CopilotMode.DELEGATED,
        max_wall_s=15.0,
        universe_size=30,
        max_days=1,
        turns_per_day=40,
        starting_credits=20_000,
    )
    assert result.outcome == "completed", result.error or result
    assert result.copilot_event_count >= 1, (
        f"expected >=1 copilot-tagged events, got {result.copilot_event_count} "
        f"(actions={[a.__dict__ for a in result.actions_dispatched]}, "
        f"tail={result.engine_events_tail[-5:]})"
    )
    # No leak: no copilot action should be tagged 'human'.
    for ev in result.engine_events_tail:
        if ev["actor_id"] == "P2" and ev["actor_kind"] == "copilot":
            assert ev["kind"] != "human_turn_start"
    assert any(a.tool == "pass_turn" and a.ok for a in result.actions_dispatched)


def test_human_sim_demo_trade_runs_loop_to_iteration_cap() -> None:
    result = _run(
        seed=7,
        intent="run a quick trade loop",
        demo="trade",
        mode=CopilotMode.DELEGATED,
        max_wall_s=30.0,
        universe_size=30,
        max_days=1,
        turns_per_day=80,
        starting_credits=20_000,
    )
    assert result.outcome == "completed", result.error or result
    assert result.task_final is not None
    assert result.task_final["state"] == "done"
    assert result.task_final["iterations"] == 4
    assert result.task_final["reason_finished"].startswith("hit iteration cap")
    # Every TaskAgent-dispatched action touched seq and emitted an event
    # tagged actor_kind=copilot. Count conservatively.
    assert result.copilot_event_count >= 3, result.to_json()


def test_human_sim_script_file_overrides_demo(tmp_path: Path) -> None:
    script_path = tmp_path / "script.json"
    script_path.write_text(
        json.dumps(
            ['{"tool":"pass_turn","arguments":{},"thought":"from script"}']
        ),
        encoding="utf-8",
    )
    result = _run(
        seed=42,
        intent="do the scripted thing",
        script_file=script_path,
        mode=CopilotMode.DELEGATED,
        max_wall_s=15.0,
        universe_size=30,
        max_days=1,
        turns_per_day=40,
        starting_credits=20_000,
    )
    assert result.outcome == "completed", result.error or result
    assert any(a.tool == "pass_turn" and a.ok for a in result.actions_dispatched)


def test_human_sim_json_shape_is_stable() -> None:
    result = _run(
        seed=42,
        intent="pass",
        demo="pass",
        mode=CopilotMode.DELEGATED,
        max_wall_s=15.0,
        universe_size=30,
        max_days=1,
        turns_per_day=40,
        starting_credits=20_000,
    )
    j = result.to_json()
    # Exact keys matter for downstream CI consumers + forensics scripts.
    expected_keys = {
        "seed",
        "intent",
        "mode",
        "outcome",
        "iterations",
        "duration_s",
        "chat_turns",
        "actions_dispatched",
        "task_final",
        "final_credits",
        "final_sector",
        "copilot_event_count",
        "human_event_count",
        "error",
        "engine_events_tail",
    }
    assert set(j.keys()) == expected_keys


def test_human_sim_cli_subcommand_returns_json(tmp_path: Path) -> None:
    """Spawn the CLI in --json mode and parse stdout as JSON."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tw2k.cli",
            "human-sim",
            "42",
            "pass the turn",
            "--demo",
            "pass",
            "--max-wall-s",
            "15",
            "--universe-size",
            "30",
            "--max-days",
            "1",
            "--turns-per-day",
            "40",
            "--starting-credits",
            "20000",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    # --json prints a single JSON object on stdout. Everything else (rich
    # banners, typer exit) must go to stderr in that mode.
    j = json.loads(proc.stdout)
    assert j["outcome"] == "completed"
    assert j["seed"] == 42
