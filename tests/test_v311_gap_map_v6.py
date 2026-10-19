"""The v6 gap map is a complete regrade, and every switch it names is real.

Modelled on the v5 gap-map test file living beside this one. That file checks
engine behaviour for rows 145-149. This one checks the doc contract for the
refresh: 171 graded rows, a counts table that adds up, and cited switches.
"""
from __future__ import annotations

import re
from pathlib import Path

import tw2k.engine.constants as K

ROOT = Path(__file__).resolve().parents[1]
V6 = ROOT / "docs" / "plans" / "gap-map-refresh-v6.md"
V5 = ROOT / "docs" / "plans" / "gap-map-refresh-v5.md"

_GRADE = r"Match-behind-flag|Ben-decision|Match|Partial|Different|Missing"
_ROW = re.compile(rf"^(\d+\.\d+)\s+({_GRADE})\b", re.M)
_SWITCH = re.compile(r"\b([A-Z][A-Z0-9_]*_(?:MODE|RULE))\b")


def _grades(text: str) -> list[tuple[str, str]]:
    body = text.split("## Every row", 1)[1]
    return _ROW.findall(body)


def test_v5_points_at_v6() -> None:
    first = V5.read_text(encoding="utf-8").splitlines()[0]
    assert first == "Superseded by gap-map-refresh-v6.md"


def test_doc_has_171_graded_rows() -> None:
    rows = _grades(V6.read_text(encoding="utf-8"))
    ids = [row_id for row_id, _grade in rows]
    assert len(rows) == 171
    assert len(set(ids)) == 171
    assert "5.16" not in ids
    assert "7.1" not in ids
    assert "8.5" not in ids


def test_counts_table_sums_to_171() -> None:
    text = V6.read_text(encoding="utf-8")
    rows = _grades(text)
    counted: dict[str, int] = {}
    for _row_id, grade in rows:
        counted[grade] = counted.get(grade, 0) + 1
    table: dict[str, int] = {}
    for line in text.splitlines():
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) != 3 or parts[0] not in {
            "Match",
            "Match-behind-flag",
            "Partial",
            "Different",
            "Missing",
            "Ben-decision",
            "Total",
        }:
            continue
        table[parts[0]] = int(parts[2])
    assert sum(v for k, v in table.items() if k != "Total") == 171
    assert table["Total"] == 171
    for grade, n in counted.items():
        assert table[grade] == n, grade


def test_every_cited_switch_exists() -> None:
    text = V6.read_text(encoding="utf-8")
    names = sorted(set(_SWITCH.findall(text)))
    assert names, "the regrade should name the switches it found"
    missing = [name for name in names if not hasattr(K, name)]
    assert missing == []
