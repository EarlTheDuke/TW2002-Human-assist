"""scripts/run_scripted_match.py: a short mixed match is deterministic."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _runner():
    spec = importlib.util.spec_from_file_location("run_scripted_match", ROOT / "scripts" / "run_scripted_match.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_two_day_three_seat_match_is_the_same_twice(tmp_path: Path) -> None:
    mod = _runner()
    args = ["--seats", "N3,N2,H", "--seed", "250925", "--days", "2", "--size", "300"]
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    assert mod.main([*args, "--json", str(first), "--md", str(tmp_path / "a.md")]) == 0
    assert mod.main([*args, "--json", str(second)]) == 0
    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")
    result = json.loads(first.read_text(encoding="utf-8"))
    assert result["days_played"] == 2
    assert [result["players"][p]["seat"] for p in ("P1", "P2", "P3")] == ["N3", "N2", "H"]
    assert sorted(result["ranking"]) == ["P1", "P2", "P3"]
    for row in result["players"].values():
        assert row["exceptions"] == 0
        assert len(row["daily"]) == 2
        assert row["actions"] > 0
    md = (tmp_path / "a.md").read_text(encoding="utf-8")
    assert md.count("\n| ") >= 4 and "N3-P1" in md and "H-P3" in md


def test_seat_list_rejects_unknown_kinds() -> None:
    mod = _runner()
    assert mod.parse_seats("n3, heuristic ,N1") == ["N3", "H", "N1"]
    with pytest.raises(ValueError):
        mod.parse_seats("N4")
