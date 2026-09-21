#!/usr/bin/env python3
"""Grok Bot bridge — Commander watch/act without xAI.

  python scripts/grokbot_bridge.py watch --base-url http://127.0.0.1:8031 --seat P3
  python scripts/grokbot_bridge.py act --seat P3 --turn-seq N --kind warp --arg target=8 --thought "..."
  python scripts/grokbot_bridge.py brief --seat P3   # one-shot status/obs dump
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / ".tw2k" / "external_tokens.json"
BRIEF = ROOT / "docs" / "playtests" / "grokbot_brief.json"
LOG = ROOT / "docs" / "playtests" / "GROKBOT_CONNECTOR_LOG.md"


def load_token(pid: str) -> str:
    data = json.loads(TOKENS.read_text(encoding="utf-8"))
    if pid not in data:
        raise SystemExit(f"no token for {pid}")
    return str(data[pid])


def client(base: str, token: str) -> httpx.Client:
    return httpx.Client(
        base_url=base.rstrip("/"),
        headers={"Authorization": f"Bearer {token}"},
        timeout=70.0,
    )


def compact(obs: dict) -> dict:
    sector = obs.get("sector") or {}
    ship = obs.get("ship") or {}
    port = sector.get("port") or {}
    return {
        "day": obs.get("day"),
        "tick": obs.get("tick"),
        "credits": obs.get("credits"),
        "net_worth": obs.get("net_worth"),
        "turns_remaining": obs.get("turns_remaining"),
        "sector_id": sector.get("id"),
        "warps_out": sector.get("warps_out"),
        "port_buys": port.get("buys"),
        "port_sells": port.get("sells"),
        "cargo": ship.get("cargo"),
        "cargo_free": ship.get("cargo_free"),
        "ship_class": ship.get("class"),
        "adjacent": [
            {"id": a.get("id"), "known": a.get("known"), "port": a.get("port")}
            for a in (obs.get("adjacent") or [])[:8]
        ],
        "recent_failures": obs.get("recent_failures"),
        "action_hint": (obs.get("action_hint") or "")[:500],
        "goals": obs.get("goals"),
        "scratchpad": obs.get("scratchpad"),
        "rivals": [
            {"id": r.get("id"), "name": r.get("name"), "net_worth": r.get("net_worth"), "ship": r.get("ship_class")}
            for r in (obs.get("rivals") or [])
        ],
    }


def cmd_brief(args: argparse.Namespace) -> int:
    token = load_token(args.seat)
    with client(args.base_url, token) as c:
        st = c.get(f"/harness/v1/{args.seat}/status").json()
        print(json.dumps(st, indent=2))
        if st.get("awaiting_input"):
            r = c.get(
                f"/harness/v1/{args.seat}/observation",
                params={"wait_s": 5, "format": "json"},
            ).json()
            brief = {
                "turn_seq": r.get("turn_seq"),
                "deadline_at": r.get("deadline_at"),
                "compact": compact(r.get("observation") or {}),
            }
            BRIEF.parent.mkdir(parents=True, exist_ok=True)
            BRIEF.write_text(json.dumps(brief, indent=2), encoding="utf-8")
            print("wrote", BRIEF)
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    token = load_token(args.seat)
    BRIEF.parent.mkdir(parents=True, exist_ok=True)
    LOG.touch(exist_ok=True)
    print(f"watching {args.seat} on {args.base_url} — Ctrl+C to stop")
    with client(args.base_url, token) as c:
        while True:
            r = c.get(
                f"/harness/v1/{args.seat}/observation",
                params={"wait_s": 30, "format": "json"},
            ).json()
            if r.get("match_status") in ("finished", "error"):
                print("match ended", r.get("match_status"))
                return 0
            if not r.get("awaiting_input"):
                continue
            brief = {
                "ts": time.time(),
                "player_id": args.seat,
                "turn_seq": r.get("turn_seq"),
                "deadline_at": r.get("deadline_at"),
                "compact": compact(r.get("observation") or {}),
            }
            BRIEF.write_text(json.dumps(brief, indent=2), encoding="utf-8")
            print(
                f"TURN {brief['turn_seq']} day={brief['compact'].get('day')} "
                f"sec={brief['compact'].get('sector_id')} cr={brief['compact'].get('credits')} "
                f"— wrote {BRIEF.name}; Commander should act"
            )
            # wait until turn advances or action file
            action_path = BRIEF.with_name("grokbot_action.json")
            deadline = float(r.get("deadline_at") or (time.time() + 120))
            while time.time() < deadline - 5:
                if action_path.exists():
                    raw = json.loads(action_path.read_text(encoding="utf-8"))
                    if int(raw.get("turn_seq", -1)) == int(brief["turn_seq"]):
                        action_path.unlink(missing_ok=True)
                        post = c.post(
                            f"/harness/v1/{args.seat}/action",
                            json={"turn_seq": brief["turn_seq"], "action": raw["action"]},
                        )
                        print("posted", post.status_code, post.text[:200])
                        last = c.get(f"/harness/v1/{args.seat}/status").json().get("last_result")
                        with LOG.open("a", encoding="utf-8") as f:
                            f.write(
                                f"- {time.strftime('%Y-%m-%dT%H:%M:%S')} {args.seat} "
                                f"{raw['action'].get('kind')} ok={last and last.get('ok')} "
                                f"thought={str(raw['action'].get('thought'))[:100]}\n"
                            )
                        break
                time.sleep(0.3)
            else:
                print("no Commander action before deadline — server will WAIT")
    return 0


def cmd_act(args: argparse.Namespace) -> int:
    token = load_token(args.seat)
    action_args: dict = {}
    for item in args.arg or []:
        k, _, v = item.partition("=")
        if v.isdigit() or (v.startswith("-") and v[1:].isdigit()):
            action_args[k] = int(v)
        else:
            try:
                action_args[k] = float(v)
            except ValueError:
                action_args[k] = v
    action = {
        "kind": args.kind,
        "args": action_args,
        "thought": args.thought or "Commander decision",
        "goal_short": args.goal or "",
        "scratchpad_update": args.scratch or "",
    }
    with client(args.base_url, token) as c:
        if args.turn_seq is None:
            st = c.get(f"/harness/v1/{args.seat}/status").json()
            if not st.get("awaiting_input"):
                print("not awaiting", st)
                return 1
            seq = st["turn_seq"]
        else:
            seq = args.turn_seq
        post = c.post(
            f"/harness/v1/{args.seat}/action",
            json={"turn_seq": seq, "action": action},
        )
        print(post.status_code, post.text[:300])
        print(c.get(f"/harness/v1/{args.seat}/status").json().get("last_result"))
    return 0 if post.is_success else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("TW2K_HARNESS_URL", "http://127.0.0.1:8031"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("watch")
    w.add_argument("--seat", default="P3")
    w.set_defaults(func=cmd_watch)
    b = sub.add_parser("brief")
    b.add_argument("--seat", default="P3")
    b.set_defaults(func=cmd_brief)
    a = sub.add_parser("act")
    a.add_argument("--seat", default="P3")
    a.add_argument("--turn-seq", type=int, default=None)
    a.add_argument("--kind", required=True)
    a.add_argument("--arg", action="append", default=[])
    a.add_argument("--thought", default="")
    a.add_argument("--goal", default="")
    a.add_argument("--scratch", default="")
    a.set_defaults(func=cmd_act)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
