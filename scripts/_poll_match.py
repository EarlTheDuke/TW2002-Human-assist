"""Tiny poll helper for the running match — used while sanity-checking
that both LLM providers are actually driving the agents. Keeps the
PowerShell / cmd quoting mess out of the shell call.

Prints to stdout in whatever encoding the console prefers; non-ASCII in
agent thoughts (LLM-emitted arrows, ellipses, smart-quotes) is replaced
rather than raising. Windows cp1252 console chokes on emoji/unicode
arrows otherwise.
"""
from __future__ import annotations

import json
import sys
import urllib.request


def _safe(s: str) -> str:
    enc = sys.stdout.encoding or "utf-8"
    return s.encode(enc, errors="replace").decode(enc, errors="replace")


def main(url: str = "http://127.0.0.1:8001") -> None:
    with urllib.request.urlopen(f"{url}/state", timeout=5) as r:
        state = json.loads(r.read().decode("utf-8-sig"))
    print(f"status={state.get('status')}  day={state.get('day')}  tick={state.get('tick')}  finished={state.get('finished')}")
    for p in state.get("players", []):
        print(
            f"  {p.get('name','?'):10s} kind={p.get('agent_kind','?'):10s} "
            f"turns={p.get('turns_today',0):4d}/{p.get('turns_per_day',0):4d}  "
            f"credits={p.get('credits',0):>7}  sector={p.get('sector_id','?'):>4}  "
            f"net_worth={p.get('net_worth',0):>7}  alive={p.get('alive','?')}"
        )

    with urllib.request.urlopen(f"{url}/events?limit=40", timeout=5) as r:
        evs = json.loads(r.read().decode("utf-8-sig")).get("events", [])
    print(f"--- last {min(len(evs), 10)} events (of {len(evs)}):")
    for e in evs[-10:]:
        summary = (e.get("summary") or "").replace("\n", " ")[:100]
        print(_safe(f"  [{e.get('seq')}] {e.get('kind','?'):18s} {summary}"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001")
