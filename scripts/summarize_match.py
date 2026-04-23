#!/usr/bin/env python3
"""Print Tier-0 match metrics from saves/<run>/events.jsonl (or any events.jsonl path).

If the log ends with a ``match_metrics`` event, its payload is printed verbatim.
Otherwise metrics are recomputed with ``build_match_metrics_payload``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize TW2K match events.jsonl")
    parser.add_argument(
        "events_file",
        nargs="?",
        default=None,
        help="Path to events.jsonl (default: latest saves/*/events.jsonl)",
    )
    args = parser.parse_args()

    if args.events_file:
        path = Path(args.events_file)
    else:
        saves = REPO / "saves"
        if not saves.is_dir():
            print("No saves/ dir and no path given.", file=sys.stderr)
            sys.exit(1)
        candidates = sorted(
            saves.glob("*/events.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            print("No saves/*/events.jsonl found.", file=sys.stderr)
            sys.exit(1)
        path = candidates[0]
        print(f"# using {path}\n", file=sys.stderr)

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        print("empty log", file=sys.stderr)
        sys.exit(1)

    last = json.loads(lines[-1])
    if last.get("kind") == "match_metrics" and isinstance(last.get("payload"), dict):
        print(json.dumps(last["payload"], indent=2))
        return

    sys.path.insert(0, str(REPO / "src"))
    from tw2k.engine.match_metrics import build_match_metrics_payload  # noqa: E402
    from tw2k.engine.models import Event, EventKind  # noqa: E402

    events: list[Event] = []
    for line in lines:
        row = json.loads(line)
        row["kind"] = EventKind(row["kind"])
        events.append(Event.model_validate(row))

    payload = build_match_metrics_payload(events)
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
