"""Quick forensic pass over the live event log to quantify memory-gap
symptoms: warp-block repeats, haggle-countered rate, redundant scans,
and Grok's deadloop length."""
from __future__ import annotations

import json
import os
import pathlib
import sys
from collections import Counter, defaultdict


def main() -> None:
    path = pathlib.Path(os.environ["TEMP"]) / "tw2k_evts.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    events = data.get("events", [])
    print(f"total events: {len(events)}")

    kinds = Counter(e.get("kind") for e in events)
    print("\n=== event-kind counts ===")
    for k, n in kinds.most_common(15):
        print(f"  {k:22s} {n}")

    # Warp-block repeats per player
    blocks_by_actor: dict[str, list[str]] = defaultdict(list)
    for e in events:
        if e.get("kind") == "warp_blocked":
            blocks_by_actor[e.get("actor_id", "?")].append(
                (e.get("summary") or "")[:80]
            )
    print("\n=== warp_blocked per actor ===")
    for pid, blocks in blocks_by_actor.items():
        print(f"  {pid}: {len(blocks)} blocks")
        for b in blocks[-6:]:
            s = b.encode(sys.stdout.encoding or "utf-8", "replace").decode(
                sys.stdout.encoding or "utf-8", "replace"
            )
            print(f"    - {s}")

    # Haggle countered rate
    trade_evts = [e for e in events if e.get("kind") == "trade"]
    haggle_countered = sum(
        1 for e in trade_evts if "haggle countered" in (e.get("summary") or "").lower()
    )
    print(f"\n=== trades: {len(trade_evts)} total, {haggle_countered} haggle-countered "
          f"({100*haggle_countered/max(1,len(trade_evts)):.0f}%) ===")

    # Consecutive-failure streaks per actor
    print("\n=== consecutive-failure streaks (any fail kind) ===")
    fail_kinds = {"warp_blocked", "trade_failed", "agent_error"}
    streaks_by_actor: dict[str, int] = defaultdict(int)
    current_by_actor: dict[str, int] = defaultdict(int)
    last_kind_by_actor: dict[str, str] = defaultdict(str)
    for e in events:
        actor = e.get("actor_id")
        if not actor:
            continue
        k = e.get("kind")
        if k == "agent_thought":
            continue  # pure narration, doesn't change streak
        if k in fail_kinds:
            current_by_actor[actor] += 1
            streaks_by_actor[actor] = max(streaks_by_actor[actor], current_by_actor[actor])
        else:
            current_by_actor[actor] = 0
        last_kind_by_actor[actor] = k
    for pid, mx in streaks_by_actor.items():
        print(f"  {pid}: longest consecutive-fail streak = {mx}")

    # Grok's last 20 non-thought events — visualize the deadloop
    print("\n=== Grok's last 20 non-thought events (deadloop visualization) ===")
    grok_evts = [e for e in events if e.get("actor_id") == "P1" and e.get("kind") != "agent_thought"]
    for e in grok_evts[-20:]:
        summ = (e.get("summary") or "")[:85]
        summ = summ.encode(sys.stdout.encoding or "utf-8", "replace").decode(
            sys.stdout.encoding or "utf-8", "replace"
        )
        print(f"  [{e.get('seq'):>3}] {e.get('kind'):14s} {summ}")


if __name__ == "__main__":
    main()
