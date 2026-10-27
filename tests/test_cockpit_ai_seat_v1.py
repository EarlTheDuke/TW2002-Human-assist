"""NOTE 54. The cockpit seat stays off unless the new switch is on.

Flag off: the client posts nothing, and a default match grows no new seat.
Flag on: one seat leaves StarDock, warps one hop, then docks or waits,
reading only the harness.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
from pathlib import Path

import pytest

import tw2k.agents.cockpit_seat as seat
import tw2k.engine.constants as K
from tests.test_external_harness_phase1 import TOK2, _app_and_client, _auth, _http_spec, _wait_until

pytestmark = pytest.mark.legacy_profile

LOG = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-ai-seat-v1"
ARTIFACT_ENV = "TW2K_SEAT_ARTIFACTS"


def artifact_dir(tmp_path: Path) -> Path:
    """The committed log folder only when TW2K_SEAT_ARTIFACTS=1 asks for it."""
    return LOG if os.environ.get(ARTIFACT_ENV) == "1" else tmp_path / "cockpit-ai-seat-v1"


def _stardock_spec():
    """The day-1 loop starts where a human starts: sector 1."""
    spec = _http_spec()
    spec.config.all_start_stardock = True
    return spec


def test_flag_off_wires_no_seat(tmp_path) -> None:
    assert K.AI_COCKPIT_SEAT_MODE == "legacy"
    assert K.ai_cockpit_seat_on() is False
    source = inspect.getsource(seat)
    for banned in ("build_observation", "generate_universe", "MatchRunner", "Universe"):
        assert banned not in source
    runner = Path(inspect.getfile(K)).resolve().parents[1] / "server" / "runner.py"
    app = runner.with_name("app.py")
    assert "cockpit_seat" not in runner.read_text(encoding="utf-8")
    assert "cockpit_seat" not in app.read_text(encoding="utf-8")

    called = {"n": 0}

    async def _refuse(*_a, **_k):
        called["n"] += 1
        raise AssertionError("flag off must not read the harness")

    client = seat.CockpitSeat("P2", _refuse, _refuse)

    async def _off() -> None:
        try:
            await client.run_day1()
        except seat.CockpitSeatOff:
            return
        raise AssertionError("legacy mode ran the seat")

    asyncio.run(_off())
    assert called["n"] == 0

    app_obj, http = _app_and_client(tmp_path)
    runner_obj = app_obj.state.runner

    async def _match() -> None:
        await runner_obj.start(_http_spec())
        assert await _wait_until(lambda: runner_obj.state.universe is not None)
        kinds = [spec.kind for spec in runner_obj._spec.agents]
        assert kinds == ["heuristic", "external", "external"]
        assert len(runner_obj.state.agents) == 3
        await runner_obj.stop()
        await http.aclose()

    asyncio.run(_match())


def test_flag_on_leaves_stardock_then_docks_or_waits(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "tw2002")
    assert K.ai_cockpit_seat_on() is True
    app, http = _app_and_client(tmp_path)
    runner = app.state.runner
    headers = _auth(TOK2)

    async def get(path, params=None):
        leaf = path.rstrip("/").rsplit("/", 1)[-1]
        assert leaf in seat.READS
        got = await http.get(path, params=params, headers=headers)
        assert got.status_code == 200, got.text
        return got.json()

    async def post(path, body):
        assert path.endswith("/action")
        got = await http.post(path, json=body, headers=headers)
        assert got.status_code == 200, got.text
        return got.json()

    async def _go() -> list[dict]:
        await runner.start(_stardock_spec())
        assert await _wait_until(lambda: runner.state.universe is not None)
        try:
            return await seat.CockpitSeat("P2", get, post).run_day1()
        finally:
            await runner.stop()
            await http.aclose()

    log = asyncio.run(_go())
    # NOTE 97 kept the first six and added the computer tables after prices.
    assert log[0]["sections"] == [
        "rules_in_force", "rules", "scoring", "ranks", "ships", "prices",
        "planet_classes", "citadel_tables", "combat_odds", "flee_rule",
        "haggle_bands", "exp_alignment",
    ]
    warp = log[2]
    dock = log[3]
    assert warp["from_sector"] == 1
    assert warp["kind"] == "warp"
    assert warp["accepted"] is True
    assert dock["from_sector"] != 1
    assert dock["kind"] in ("trade", "wait")
    assert dock["accepted"] is True
    if dock["port"] and dock["kind"] == "trade":
        assert dock["args"]["qty"] == 1
        assert dock["args"]["side"] in ("buy", "sell")
    out = artifact_dir(tmp_path)
    out.mkdir(parents=True, exist_ok=True)
    (out / "day1.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    lines = [
        "P2 day 1, cockpit reads only.",
        f"reference sections: {', '.join(log[0]['sections'])}",
        f"warp {warp['from_sector']} -> {warp['args']['target']}",
        f"then {dock['kind']} in sector {dock['from_sector']}"
        + ("" if dock["kind"] == "trade" else f" ({dock.get('trade_reason') or 'no port'})"),
    ]
    (out / "day1.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
