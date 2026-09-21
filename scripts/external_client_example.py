"""Reference external-seat client for the TW2K harness (Grok Bot template).

Copy this file, replace `decide()` with your own brain (an LLM call, a
rules engine, anything). Everything else is protocol plumbing.

Env:
  TW2K_HARNESS_URL     default http://127.0.0.1:8000
  TW2K_HARNESS_PLAYER  e.g. P3
  TW2K_HARNESS_TOKEN   the seat's bearer token (from .tw2k/external_tokens.json)
  TW2K_HARNESS_TURNS   optional: stop after N turns (default: run until match ends)

Protocol (docs/plans/2026-09-20-external-harness.md §3):
  1. GET  /harness/v1/{pid}/observation?wait_s=30   long-polls until it's our turn
  2. decide an Action from observation JSON
  3. POST /harness/v1/{pid}/action {turn_seq, action}
  4. GET  /harness/v1/{pid}/status                  -> last_result (ok / error)

Requires: pip install httpx
"""

from __future__ import annotations

import os
import random
import sys
import time
from typing import Any

import httpx

BASE = (os.environ.get("TW2K_HARNESS_URL") or "http://127.0.0.1:8000").rstrip("/")
PID = (os.environ.get("TW2K_HARNESS_PLAYER") or "").strip()
TOKEN = (os.environ.get("TW2K_HARNESS_TOKEN") or "").strip()
MAX_TURNS = int(os.environ.get("TW2K_HARNESS_TURNS") or "0")


def decide(obs: dict[str, Any]) -> dict[str, Any]:
    """Toy policy: sell what the port buys, buy what it sells, else move."""
    sector = obs.get("sector") or {}
    ship = obs.get("ship") or {}
    cargo = ship.get("cargo") or {}
    port = sector.get("port") or {}
    turns_left = int(obs.get("turns_remaining") or 0)

    if turns_left < 3:
        return {"kind": "wait", "thought": "out of turns for today"}

    if port:
        for commodity in port.get("buys") or []:
            qty = int(cargo.get(commodity) or 0)
            if qty > 0:
                return {
                    "kind": "trade",
                    "args": {"commodity": commodity, "qty": qty, "side": "sell"},
                    "thought": f"sell {qty} {commodity}",
                }
        free = int(ship.get("cargo_free") or 0)
        sells = port.get("sells") or []
        if free > 0 and sells and int(obs.get("credits") or 0) > 500:
            commodity = sells[0]
            price = int(((port.get("stock") or {}).get(commodity) or {}).get("price") or 0) or 30
            qty = max(1, min(free, int(obs["credits"]) // max(1, price) // 2))
            return {
                "kind": "trade",
                "args": {"commodity": commodity, "qty": qty, "side": "buy"},
                "thought": f"buy {qty} {commodity}",
            }

    warps = list(sector.get("warps_out") or [])
    if warps:
        return {"kind": "warp", "args": {"target": random.choice(warps)}, "thought": "explore"}
    return {"kind": "scan", "thought": "nothing else to do"}


def main() -> int:
    if not PID or not TOKEN:
        print("set TW2K_HARNESS_PLAYER and TW2K_HARNESS_TOKEN", file=sys.stderr)
        return 2
    headers = {"authorization": f"Bearer {TOKEN}"}
    turns = 0
    with httpx.Client(base_url=BASE, headers=headers, timeout=70.0) as c:
        r = c.get(f"/harness/v1/{PID}/status")
        if r.status_code != 200:
            print(f"status {r.status_code}: {r.text}", file=sys.stderr)
            return 1
        print(f"[{PID}] connected — match {r.json().get('match_status')}")
        while True:
            r = c.get(f"/harness/v1/{PID}/observation", params={"wait_s": 30})
            if r.status_code == 503:
                print(f"[{PID}] match over / seat closed")
                return 0
            r.raise_for_status()
            body = r.json()
            if body.get("match_status") in ("finished", "error"):
                print(f"[{PID}] match {body['match_status']}")
                return 0
            if not body.get("awaiting_input"):
                continue
            obs = body["observation"]
            turn_seq = body["turn_seq"]
            action = decide(obs)
            t0 = time.time()
            r = c.post(f"/harness/v1/{PID}/action", json={"turn_seq": turn_seq, "action": action})
            if r.status_code == 409:
                print(f"[{PID}] turn {turn_seq} rejected: {r.json().get('detail')}")
                continue
            r.raise_for_status()
            time.sleep(0.05)
            st = c.get(f"/harness/v1/{PID}/status").json()
            res = st.get("last_result") or {}
            verdict = "ok" if res.get("ok") else f"FAIL {res.get('error')}"
            print(
                f"[{PID}] D{st.get('day')} turn {turn_seq}: {action['kind']} {action.get('args', {})} "
                f"-> {verdict} ({time.time() - t0:.2f}s)"
            )
            turns += 1
            if MAX_TURNS and turns >= MAX_TURNS:
                return 0


if __name__ == "__main__":
    raise SystemExit(main())
