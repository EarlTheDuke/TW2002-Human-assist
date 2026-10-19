#!/usr/bin/env python3
"""Dry run only. Print proposed constant edits from a filled live-queue CSV.

Reads a copy of docs/plans/live-twgs-results-template-v1.csv. For each row
with an observed_value, prints the constant, the current value from
tw2k.engine.constants, the proposed new value, and the UNVERIFIED comment
to drop. Writes nothing and changes nothing.

    python3 scripts/live_queue_proposals.py filled.csv
"""

from __future__ import annotations

import argparse
import csv
import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import tw2k.engine.constants as K  # noqa: E402

COLUMNS = (
    "item_id",
    "constant",
    "current_value",
    "observed_text",
    "observed_value",
    "date",
    "tester",
    "notes",
)
_ASSIGN = re.compile(r"^[A-Z][A-Z0-9_]*\s*=")


def named_in(cell: str) -> list[str]:
    """Constants, GameConfig fields, and doc paths named in one CSV cell."""
    names: list[str] = []
    for match in re.finditer(r"\b([A-Z][A-Z0-9_]{2,})\b", cell):
        names.append(match.group(1))
    for match in re.finditer(r"\b(GameConfig\.[A-Za-z_][A-Za-z0-9_]*)\b", cell):
        names.append(match.group(1))
    for match in re.finditer(r"([\w./-]+\.md)\b", cell):
        names.append(match.group(1))
    for match in re.finditer(r"\b([a-z][a-z0-9_]+)\b", cell):
        obj = getattr(K, match.group(1), None)
        if inspect.isfunction(obj) and getattr(obj, "__module__", "") == K.__name__:
            names.append(match.group(1))
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def current_text(name: str) -> str:
    """Read a current value. Does not assign it."""
    if name.startswith("GameConfig."):
        field = name.split(".", 1)[1]
        from tw2k.engine.models import GameConfig

        spec = GameConfig.model_fields.get(field)
        if spec is None:
            return f"not on tw2k.engine.constants; {name} is not a GameConfig field"
        return f"not on tw2k.engine.constants; {name} default is {spec.default!r}"
    if name.endswith(".md"):
        return f"not on tw2k.engine.constants; doc path {name}"
    if not hasattr(K, name):
        return "not on tw2k.engine.constants"
    obj = getattr(K, name)
    if inspect.isfunction(obj):
        return f"function {name}{inspect.signature(obj)}"
    return repr(obj)


def unverified_comment(name: str) -> str:
    """Nearest UNVERIFIED comment above this constant. Empty-handed if none."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return f"(no UNVERIFIED comment attached to {name})"
    path = ROOT / "src" / "tw2k" / "engine" / "constants.py"
    lines = path.read_text(encoding="utf-8").splitlines()
    assign = re.compile(rf"^{re.escape(name)}\s*=")
    defn = re.compile(rf"^def {re.escape(name)}\b")
    idx = None
    for i, line in enumerate(lines):
        if assign.match(line) or defn.match(line):
            idx = i
            break
    if idx is None:
        return f"(no UNVERIFIED comment attached to {name})"
    inline = ""
    if "#" in lines[idx]:
        inline = lines[idx].split("#", 1)[1].strip()
    j = idx - 1
    skipped = 0
    while j >= 0 and skipped < 40:
        stripped = lines[j].strip()
        if stripped == "" or _ASSIGN.match(stripped):
            j -= 1
            skipped += 1
            continue
        if stripped.startswith("#"):
            block: list[str] = []
            while j >= 0 and lines[j].lstrip().startswith("#"):
                block.append(lines[j].lstrip()[1:].strip())
                j -= 1
            block.reverse()
            blob = "\n".join(block).strip()
            if inline:
                blob = f"{blob}\n{inline}".strip()
            if "UNVERIFIED" in blob:
                return blob
            skipped += 1
            continue
        break
    if inline and "UNVERIFIED" in inline:
        return inline
    return f"(no UNVERIFIED comment attached to {name})"


def propose(rows: list[dict[str, str]]) -> str:
    chunks = [
        "DRY RUN. This script writes nothing and changes nothing.",
        "",
    ]
    shown = 0
    for row in rows:
        observed = (row.get("observed_value") or "").strip()
        if not observed:
            continue
        shown += 1
        item = (row.get("item_id") or "").strip()
        cell = (row.get("constant") or "").strip()
        names = named_in(cell)
        chunks.append(f"item_id: {item}")
        if not names:
            chunks.append(f"constant cell: {cell}")
            chunks.append("not an engine constant; no value to change")
            chunks.append(f"proposed value: {observed}")
            chunks.append("")
            continue
        for name in names:
            chunks.append(f"constant: {name}")
            chunks.append(f"current value: {current_text(name)}")
            chunks.append(f"proposed value: {observed}")
            chunks.append("UNVERIFIED comment to drop:")
            chunks.append(unverified_comment(name))
            chunks.append("")
    if shown == 0:
        chunks.append("No row has an observed_value. Nothing to propose.")
        chunks.append("")
    return "\n".join(chunks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Dry run only. Read a filled live-queue CSV and print proposed "
            "constant values. Writes nothing and changes nothing."
        )
    )
    parser.add_argument(
        "csv_path",
        help="filled results CSV (a copy of the template). Not modified.",
    )
    args = parser.parse_args(argv)
    path = Path(args.csv_path)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            print(f"missing columns: {', '.join(missing)}", file=sys.stderr)
            return 2
        rows = list(reader)
    sys.stdout.write(propose(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
