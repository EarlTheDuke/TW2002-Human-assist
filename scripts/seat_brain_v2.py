#!/usr/bin/env python3
"""Run the S3 goal-driven SeatBrain for one seat.

Reads ONLY that seat's own observation - never /state, never other seats.

Mailbox mode (default; same files as the old commander_p4_brain.py and
grokbot_seat_client.py --policy mailbox):
  python scripts/grokbot_seat_client.py --seat P4 --policy mailbox      # runner: harness <-> files
  python scripts/seat_brain_v2.py --seat P4                             # brain:  files -> decision

Direct harness mode (no mailbox; brain drives the seat itself):
  python scripts/seat_brain_v2.py --seat P4 --harness --base-url http://127.0.0.1:8031

Optional --log-dir writes one JSON line per decision (turns.jsonl).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tw2k.agents.seat_brain import SeatBrain  # noqa: E402


def _log(log_dir: Path | None, seq, obs: dict, action: dict, brain: SeatBrain) -> None:
    rep = brain.last_report
    line = (f"seq={seq} day={obs.get('day')} sector={(obs.get('sector') or {}).get('id')} "
            f"cr={obs.get('credits')} -> {action['kind']} {action.get('args')} | {action.get('thought')}")
    print(line, flush=True)
    if log_dir is None:
        return
    log_dir.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": datetime.now(UTC).isoformat(), "turn_seq": seq, "day": obs.get("day"),
        "sector": (obs.get("sector") or {}).get("id"), "credits": obs.get("credits"),
        "net_worth": obs.get("net_worth"), "action": {k: action[k] for k in ("kind", "args", "thought")},
        "progress": rep.summary() if rep else None,
        "owned_planets": [{k: p.get(k) for k in ("id", "origin", "citadel_level", "citadel_target", "colonists_total")}
                          for p in (obs.get("owned_planets") or [])],
    }
    with (log_dir / "turns.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def run_mailbox(seat: str, mailbox: Path, log_dir: Path | None, max_turns: int, record: Path | None = None) -> int:
    brain = SeatBrain()
    pending = mailbox / f"{seat}.pending.json"
    decision = mailbox / f"{seat}.decision.json"
    print(f"seat_brain_v2 {seat} watching {pending}", flush=True)
    last_seq = None
    played = 0
    while not max_turns or played < max_turns:
        try:
            data = json.loads(pending.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, OSError):
            time.sleep(0.3)
            continue
        seq = data.get("turn_seq")
        if seq == last_seq:
            time.sleep(0.3)
            continue
        obs = data.get("observation") or {}
        if record is not None:  # seat-only trace for scripts/seat_brain_acceptance.py replay
            record.parent.mkdir(parents=True, exist_ok=True)
            with record.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"seat": seat, "turn_seq": seq, "observation": obs}) + "\n")
        action = brain.decide(obs)
        tmp = decision.with_suffix(".tmp")
        tmp.write_text(json.dumps({"turn_seq": seq, "action": action}), encoding="utf-8")
        tmp.replace(decision)
        _log(log_dir, seq, obs, action, brain)
        last_seq = seq
        played += 1
    return 0


async def run_harness(seat: str, base_url: str, tokens_file: Path, log_dir: Path | None, max_turns: int) -> int:
    import httpx

    from tw2k.agents.pathb_client import SeatClient

    token = json.loads(tokens_file.read_text(encoding="utf-8"))[seat]
    brain = SeatBrain()

    def policy(ctx):
        action = brain.decide(ctx.observation)
        _log(log_dir, ctx.turn_seq, ctx.observation, action, brain)
        return action

    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=httpx.Timeout(70.0, connect=15.0)) as http:
        stats = await SeatClient(http, seat, token, policy).run(max_turns=max_turns)
    print(f"{seat}: turns={stats.turns} ok={stats.ok} failed={stats.failed} kinds={stats.kinds}", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seat", required=True)
    ap.add_argument("--mailbox-dir", default=str(ROOT / ".tw2k" / "mailbox"))
    ap.add_argument("--harness", action="store_true", help="drive the seat directly over /harness/v1 (no mailbox)")
    ap.add_argument("--base-url", default="http://127.0.0.1:8031")
    ap.add_argument("--tokens-file", default=str(ROOT / ".tw2k" / "external_tokens.json"))
    ap.add_argument("--log-dir", default=None)
    ap.add_argument("--max-turns", type=int, default=0)
    ap.add_argument("--record", default=None,
                    help="append each mailbox payload (seat's own observation) to this JSONL for offline replay")
    args = ap.parse_args()
    seat = args.seat.upper()
    log_dir = Path(args.log_dir) if args.log_dir else None
    try:
        if args.harness:
            return asyncio.run(run_harness(seat, args.base_url, Path(args.tokens_file), log_dir, args.max_turns))
        return run_mailbox(seat, Path(args.mailbox_dir), log_dir, args.max_turns,
                           Path(args.record) if args.record else None)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
