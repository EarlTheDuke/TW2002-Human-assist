#!/usr/bin/env python3
"""Drop one directive file into a seat's inbox.

The inbox is a directory on disk. This does not call the game server and
does not read another seat's file. Ben keeps the example, edits the goal,
and points the cockpit player or the grokbot seat client at the same inbox.

    python3 scripts/drop_directive.py \
        --inbox runs/directives \
        --seat P3 \
        --file examples/directives/citadel-quasars.json

That writes runs/directives/P3.json. The seat P3 reads it on its next turn.
P4 does not. Remove the file, or set expires / expires_day, to retire it.

A recovery file written by the harness (runs/directives/P3/recovery.json)
is separate. Priority 100 on Ben's directive stays above that recovery.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _import_root() -> None:
    root = Path(__file__).resolve().parent
    text = str(root)
    if text not in sys.path:
        sys.path.insert(0, text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--inbox", required=True, help="directory that holds <SEAT>.json files")
    parser.add_argument("--seat", required=True, help="seat id, for example P3")
    parser.add_argument("--file", required=True, help="directive JSON to copy in")
    args = parser.parse_args(argv)
    _import_root()
    from ai_cockpit.directives import DirectiveError, drop_file

    try:
        dest = drop_file(args.inbox, args.seat, args.file)
    except DirectiveError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
