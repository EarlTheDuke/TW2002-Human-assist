#!/usr/bin/env python3
"""Commander decision helper — polls commander_pending.json and writes commander_action.json.

This is Commander's play policy (not the generic heuristic driver): prioritize
sell → buy toward routes → scan unknowns → warp toward StarDock when rich.
Tagged thoughts as Commander.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "docs" / "playtests"
PENDING = PLAY / "commander_pending.json"
ACTION = PLAY / "commander_action.json"


def decide(obs: dict) -> dict:
    sector = obs.get("sector") or {}
    ship = obs.get("ship") or {}
    cargo = ship.get("cargo") or {}
    port = sector.get("port") or {}
    buys = list(port.get("buys") or [])
    sells = list(port.get("sells") or [])
    warps = list(sector.get("warps_out") or [])
    free = int(ship.get("cargo_free") or 0)
    credits = int(obs.get("credits") or 0)
    fails = obs.get("recent_failures") or []
    adj = obs.get("adjacent") or []

    # Sell first
    for c in buys:
        qty = int(cargo.get(c) or 0)
        if qty > 0:
            return {
                "kind": "trade",
                "args": {"commodity": c, "qty": qty, "side": "sell"},
                "thought": "Commander: dump cargo the port buys — lock profit before moving.",
                "goal_short": "sell then reposition",
                "scratchpad_update": f"sold intent {c}x{qty} at {sector.get('id')}",
            }
    # Buy if empty holds
    if free > 0 and sells and credits > 2000:
        c = sells[0]
        qty = min(free, 20)
        return {
            "kind": "trade",
            "args": {"commodity": c, "qty": qty, "side": "buy"},
            "thought": f"Commander: load {qty} {c} for the next sell port.",
            "goal_short": "fill holds for arbitrage",
            "scratchpad_update": f"buying {c} at {sector.get('id')}",
        }
    # Scan unknown adjacent
    unknown = [a for a in adj if a.get("known") is False]
    if unknown and int(obs.get("turns_remaining") or 0) > 2:
        return {
            "kind": "scan",
            "args": {},
            "thought": "Commander: chart unknown neighbors before warping blind.",
            "goal_short": "map local space",
        }
    # Toward sector 1 if rich enough for upgrades
    if credits >= 200000 and warps:
        # prefer lower id warp as crude pull to fedspace
        target = sorted(warps)[0]
        return {
            "kind": "warp",
            "args": {"target": int(target)},
            "thought": "Commander: cash-heavy — bias toward StarDock / denser space for upgrades.",
            "goal_short": "reach StarDock for ship",
        }
    if warps:
        # prefer unknown adj warp
        unk_ids = {int(a["id"]) for a in unknown if "id" in a}
        for w in warps:
            if int(w) in unk_ids:
                return {
                    "kind": "warp",
                    "args": {"target": int(w)},
                    "thought": "Commander: push into unmapped warp.",
                    "goal_short": "explore",
                }
        return {
            "kind": "warp",
            "args": {"target": int(warps[0])},
            "thought": "Commander: reposition via first legal warp.",
            "goal_short": "keep tempo",
        }
    return {"kind": "wait", "args": {}, "thought": "Commander: no legal moves — wait."}


def main() -> None:
    print("Commander helper watching", PENDING)
    seen = None
    while True:
        if PENDING.exists():
            try:
                data = json.loads(PENDING.read_text(encoding="utf-8"))
            except Exception:
                time.sleep(0.3)
                continue
            key = (data.get("pid"), data.get("turn_seq"))
            if key != seen and data.get("observation"):
                act = decide(data["observation"])
                ACTION.write_text(
                    json.dumps({"turn_seq": data["turn_seq"], "action": act}, indent=2),
                    encoding="utf-8",
                )
                print("wrote", key, act.get("kind"), act.get("thought", "")[:80])
                seen = key
        time.sleep(0.25)


if __name__ == "__main__":
    main()
