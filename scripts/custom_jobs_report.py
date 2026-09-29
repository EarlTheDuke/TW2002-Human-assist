"""Print one line per custom video job. No prompt text and no key.

Usage: python scripts/custom_jobs_report.py <cache_dir>
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: custom_jobs_report.py <cache_dir>", file=sys.stderr)
        return 2
    db = Path(argv[1]) / "jobs.sqlite"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT clip_key, status, reason, cost_cents, started_at, finished_at FROM jobs ORDER BY id"
    )
    for row in rows:
        latency = ""
        if row["started_at"] is not None and row["finished_at"] is not None:
            latency = f"{row['finished_at'] - row['started_at']:.1f}"
        reason = row["reason"] or ""
        print(f"{row['clip_key']} {row['status']} {reason} {row['cost_cents']} {latency}".rstrip())
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
