#!/usr/bin/env python3
"""Summarize per-player LLM cost from a match's events.jsonl.

Reads every ``llm_usage`` event in the log and prints a table of
per-player totals + a grand total. Works on live matches too — point
it at ``saves/<run>/events.jsonl`` while the match is running and it
just counts what's been flushed so far.

Usage:
    python scripts/cost_report.py                         # latest saves/*/events.jsonl
    python scripts/cost_report.py saves/<run>/events.jsonl
    python scripts/cost_report.py --json                  # machine-readable output
    python scripts/cost_report.py --by-day                # extra per-day breakdown

Costs are computed at emit time (by the runner) using the pricing
table in ``src/tw2k/engine/llm_pricing.py``. If you want to re-price
the same event log against a different rate sheet, set
``TW2K_COST_OVERRIDES_PATH`` before running — but note that the
rollup here uses the cost_usd field that was baked into the event,
so overrides only affect *future* emissions. A future version of
this script could re-derive from token counts if needed.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]


def _latest_events_log() -> Path | None:
    saves = REPO / "saves"
    if not saves.is_dir():
        return None
    candidates = sorted(
        saves.glob("*/events.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _aggregate(events_path: Path, *, by_day: bool) -> dict[str, Any]:
    """Walk the event log once and aggregate llm_usage rows."""
    per_player: dict[str, dict[str, Any]] = {}
    per_day: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    grand_calls = 0
    grand_cost = 0.0
    with events_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("kind") != "llm_usage":
                continue
            actor = ev.get("actor_id") or "_engine"
            pay = ev.get("payload") or {}
            usage = pay.get("usage") or {}
            row = per_player.setdefault(
                actor,
                {
                    "provider": "",
                    "model": "",
                    "calls": 0,
                    "input_tokens": 0,
                    "cached_input_tokens": 0,
                    "cache_write_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "price_is_fallback": False,
                },
            )
            if not row["provider"]:
                row["provider"] = str(pay.get("provider") or "")
            if not row["model"]:
                row["model"] = str(pay.get("model") or "")
            row["calls"] += 1
            row["input_tokens"] += int(usage.get("input_tokens") or 0)
            row["cached_input_tokens"] += int(usage.get("cached_input_tokens") or 0)
            row["cache_write_tokens"] += int(usage.get("cache_write_tokens") or 0)
            row["output_tokens"] += int(usage.get("output_tokens") or 0)
            row["cost_usd"] += float(pay.get("cost_usd") or 0.0)
            if pay.get("price_is_fallback"):
                row["price_is_fallback"] = True
            grand_calls += 1
            grand_cost += float(pay.get("cost_usd") or 0.0)
            if by_day:
                day = int(ev.get("day") or 0)
                per_day[day][actor] += float(pay.get("cost_usd") or 0.0)

    for row in per_player.values():
        row["cost_usd"] = round(row["cost_usd"], 6)

    return {
        "events_file": str(events_path),
        "per_player": per_player,
        "total": {
            "calls": grand_calls,
            "cost_usd": round(grand_cost, 6),
        },
        "per_day": (
            {
                str(d): {a: round(c, 6) for a, c in rows.items()}
                for d, rows in sorted(per_day.items())
            }
            if by_day
            else None
        ),
    }


def _human_table(agg: dict[str, Any]) -> str:
    """Return a plain-text, fixed-width summary table."""
    rows = agg.get("per_player") or {}
    total = agg.get("total") or {}
    lines: list[str] = []
    lines.append(f"events: {agg['events_file']}")
    lines.append(
        f"calls: {total.get('calls', 0)}    total cost: ${float(total.get('cost_usd') or 0):.4f}"
    )
    lines.append("")
    header = (
        f"{'player':<14} {'provider':<10} {'model':<28} {'calls':>6} "
        f"{'input':>9} {'cached':>8} {'output':>8} {'cost $':>10}  note"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for pid in sorted(rows):
        r = rows[pid]
        note = "~estimate" if r.get("price_is_fallback") else ""
        lines.append(
            f"{pid:<14.14} {str(r.get('provider') or ''):<10.10} "
            f"{str(r.get('model') or ''):<28.28} "
            f"{r.get('calls', 0):>6} "
            f"{r.get('input_tokens', 0):>9} "
            f"{r.get('cached_input_tokens', 0):>8} "
            f"{r.get('output_tokens', 0):>8} "
            f"${float(r.get('cost_usd') or 0):>9.4f}  {note}"
        )
    if agg.get("per_day"):
        lines.append("")
        lines.append("per-day USD:")
        for d, rows_d in agg["per_day"].items():
            lines.append(
                f"  day {d:>4}: "
                + ", ".join(f"{a}=${c:.4f}" for a, c in rows_d.items())
            )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize TW2K LLM cost from events.jsonl")
    parser.add_argument(
        "events_file",
        nargs="?",
        default=None,
        help="Path to events.jsonl (default: latest saves/*/events.jsonl)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the aggregate as JSON rather than a formatted table.",
    )
    parser.add_argument(
        "--by-day",
        action="store_true",
        help="Include a per-day per-player USD breakdown.",
    )
    args = parser.parse_args()

    path: Path | None = None
    if args.events_file:
        path = Path(args.events_file)
    else:
        path = _latest_events_log()
        if path is None:
            print("No saves/*/events.jsonl found and no path given.", file=sys.stderr)
            sys.exit(1)
        print(f"# using {path}", file=sys.stderr)

    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        sys.exit(1)

    agg = _aggregate(path, by_day=args.by_day)
    if args.json:
        print(json.dumps(agg, indent=2, sort_keys=True))
    else:
        print(_human_table(agg))


if __name__ == "__main__":
    main()
