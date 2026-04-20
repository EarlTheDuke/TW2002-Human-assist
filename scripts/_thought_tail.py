"""Show the last N agent_thought events for each player — evidence that
the new observation fields (known_warps, trade_summary, recent_failures)
are landing in LLM reasoning."""
from __future__ import annotations

import json
import os
import pathlib
import sys


def _safe(s: str) -> str:
    enc = sys.stdout.encoding or "utf-8"
    return s.encode(enc, "replace").decode(enc, "replace")


def main() -> None:
    path = pathlib.Path(os.environ["TEMP"]) / "tw2k_evts.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    events = data.get("events", [])

    for pid, pname in [("P1", "Grok"), ("P2", "Claude")]:
        thoughts = [
            e for e in events
            if e.get("actor_id") == pid and e.get("kind") == "agent_thought"
        ]
        print(f"\n=== {pname} last 6 agent_thoughts ===")
        for t in thoughts[-6:]:
            s = (t.get("summary") or "")[:200]
            print(f"  [{t.get('seq'):>4}] {_safe(s)}")


if __name__ == "__main__":
    main()
