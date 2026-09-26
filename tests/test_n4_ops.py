"""N4 ops hygiene: plot_course execute first-hop turn cost, and brain run logs.

Unaffordable first hop (turns left < one warp) must not be a free success.
The seat-brain runner stamps git SHA + module mtime at start and on every
turns.jsonl row, and rewrites live_summary.json each decision.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.constants import SHIP_SPECS
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player
from tw2k.engine.runner import _warp_cost_for, apply_action

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "seat_brain_v2.py"


def _universe():
    cfg = GameConfig(seed=21, universe_size=40, max_days=3, turns_per_day=1000, starting_credits=20_000,
                     enable_ferrengi=False, enable_planets=False)
    u = generate_universe(cfg)
    p = Player(id="P1", name="Seat", agent_kind="external", sector_id=1, credits=20_000)
    u.players["P1"] = p
    u.sectors[1].occupant_ids.append("P1")
    p.known_sectors.add(1)
    p.known_warps[1] = list(u.sectors[1].warps)
    return u


def _neighbor(u) -> int:
    return next(iter(u.sectors[u.players["P1"].sector_id].warps))


def _plot(u, *, execute: bool):
    return apply_action(u, "P1", Action(
        kind=ActionKind.PLOT_COURSE, args={"target": _neighbor(u), "execute": execute},
    ))


def test_unaffordable_first_hop_plot_course_not_legal_and_rejected() -> None:
    u = _universe()
    p = u.players["P1"]
    hop = _warp_cost_for(p)
    assert hop == int(SHIP_SPECS["merchant_cruiser"]["turns_per_warp"])
    p.turns_today = p.turns_per_day - (hop - 1)
    here = p.sector_id
    turns = p.turns_today

    la = next(x for x in legal_actions(u, "P1") if x.kind == "plot_course")
    execute = la.params["execute"]
    assert execute["legal"] is False
    assert execute["reason"] and "first hop unaffordable" in execute["reason"]
    assert execute["first_hop_turns"] == hop
    # A plan still costs nothing; only execute is gated.
    assert la.legal is True

    preview = _plot(u, execute=False)
    assert preview.ok, preview.error
    assert p.sector_id == here and p.turns_today == turns

    res = _plot(u, execute=True)
    assert res.ok is False
    assert res.error and "first hop unaffordable" in res.error
    assert p.sector_id == here
    assert p.turns_today == turns


def test_affordable_first_hop_plot_course_executes() -> None:
    u = _universe()
    p = u.players["P1"]
    hop = _warp_cost_for(p)
    target = _neighbor(u)
    p.turns_today = p.turns_per_day - hop
    la = next(x for x in legal_actions(u, "P1") if x.kind == "plot_course")
    assert la.params["execute"]["legal"] is True
    res = apply_action(u, "P1", Action(
        kind=ActionKind.PLOT_COURSE, args={"target": target, "execute": True},
    ))
    assert res.ok, res.error
    assert p.sector_id == target
    assert p.turns_today == p.turns_per_day


def _obs(**over) -> dict:
    base = {
        "day": 1, "credits": 20_000, "net_worth": 48_000,
        "sector": {"id": 12},
        "owned_planets": [{
            "id": 7, "sector_id": 40, "origin": "genesis", "citadel_level": 1,
            "citadel_target": 1, "colonists_total": 1000,
        }],
        "ship": {"class": "merchant_cruiser", "cargo": {}, "cargo_free": 20, "genesis": 0},
        "legal_actions": [
            {"kind": "wait", "legal": True},
            {"kind": "query_limpets", "legal": True},
        ],
        "scratchpad": "",
    }
    base.update(over)
    return base


def _write_pending(path: Path, seq: int, obs: dict) -> None:
    payload = json.dumps({"turn_seq": seq, "observation": obs})
    tmp = path.with_suffix(".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def _wait_lines(path: Path, n: int, proc: subprocess.Popen, timeout: float = 15.0) -> list[str]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() not in (None, 0):
            err = proc.stderr.read() if proc.stderr else ""
            out = proc.stdout.read() if proc.stdout else ""
            raise AssertionError(f"runner exited {proc.returncode}\n{out}\n{err}")
        if path.exists():
            lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if len(lines) >= n:
                return lines
        time.sleep(0.05)
    have = path.read_text(encoding="utf-8") if path.exists() else ""
    raise AssertionError(f"timed out waiting for {n} jsonl rows, have {have!r}")


def test_runner_smoke_stamps_sha_and_updates_live_summary(tmp_path: Path) -> None:
    mailbox = tmp_path / "mailbox"
    log_dir = tmp_path / "logs"
    mailbox.mkdir()
    pending = mailbox / "P4.pending.json"
    _write_pending(pending, 1, _obs())
    proc = subprocess.Popen(
        [sys.executable, str(RUNNER), "--seat", "P4", "--mailbox-dir", str(mailbox),
         "--log-dir", str(log_dir), "--max-turns", "2"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        rows = _wait_lines(log_dir / "turns.jsonl", 1, proc)
        first = json.loads(rows[0])
        summary_path = log_dir / "live_summary.json"
        snap1 = json.loads(summary_path.read_text(encoding="utf-8"))
        _write_pending(pending, 2, _obs(day=2, credits=12_500, net_worth=51_000, sector={"id": 40}))
        rows = _wait_lines(log_dir / "turns.jsonl", 2, proc)
    finally:
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    stdout = proc.stdout.read() if proc.stdout else ""
    stderr = proc.stderr.read() if proc.stderr else ""
    assert proc.returncode == 0, stderr or stdout

    assert "SHA=" in stdout, stdout
    sha = stdout.split("SHA=", 1)[1].split()[0]
    mtime = stdout.split("module_mtime=", 1)[1].split()[0]
    assert sha and sha != "unknown"
    assert mtime

    for line in rows:
        rec = json.loads(line)
        assert rec["git_sha"] == sha
        assert rec["module_mtime"] == mtime

    snap2 = json.loads(summary_path.read_text(encoding="utf-8"))
    assert snap1["turn_seq"] == 1 and snap1["day"] == 1 and snap1["sector"] == 12
    assert snap1["credits"] == 20_000 and snap1["net_worth"] == 48_000
    assert snap1["planets"][0]["id"] == 7
    assert snap1["goals"]["short"] and snap1["goals"]["medium"] and snap1["goals"]["long"]
    assert snap1["last_action"]["kind"]
    assert snap1["stall_breaks"] == 0 and snap1["replans"] == 0
    assert snap1["git_sha"] == sha and snap1["module_mtime"] == mtime
    assert first["git_sha"] == sha

    assert snap2["turn_seq"] == 2 and snap2["day"] == 2 and snap2["sector"] == 40
    assert snap2["credits"] == 12_500 and snap2["net_worth"] == 51_000
    assert snap2["last_action"]["kind"]
    assert snap2["git_sha"] == sha and snap2["module_mtime"] == mtime
    assert snap2["ts"] != snap1["ts"] or snap2["turn_seq"] != snap1["turn_seq"]
