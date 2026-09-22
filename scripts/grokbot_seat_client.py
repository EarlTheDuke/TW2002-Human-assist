#!/usr/bin/env python3
"""Path-B seat runner: drive 1..N external seats against the TW2K harness.

One SeatClient + one brain per seat. No xAI, no LLM in this process.

  # scripted reference brain (test opponent) on one seat
  python scripts/grokbot_seat_client.py --seat P4 --policy heuristic

  # three seats, each handing decisions to its own Grok Bot session via files
  python scripts/grokbot_seat_client.py --seats P3,P4,P5 --policy mailbox --mailbox-dir .tw2k/mailbox

Env (all optional; flags win):
  TW2K_BASE_URL            default http://127.0.0.1:8031  (or contents of .tw2k/public_base_url.txt with --public)
  TW2K_SEAT / TW2K_SEATS   seat id(s)
  TW2K_TOKEN_<SEAT>        bearer token per seat; else read from --tokens-file (default .tw2k/external_tokens.json)
  TW2K_MAX_TURNS           stop after N turns per seat (0 = until the match ends)

Mailbox protocol (--policy mailbox): for each turn the runner writes
  <dir>/<SEAT>.pending.json   {turn_seq, deadline_at, seconds_left, observation, llm_user_message, rules (first time)}
and waits for the brain to write
  <dir>/<SEAT>.decision.json  {"turn_seq": N, "action": {"kind": "...", "args": {...}, "thought": "..."}}
If nothing arrives ~5 s before the deadline the runner submits `wait` so the match never stalls on us.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import httpx  # noqa: E402

from tw2k.agents.pathb_client import (  # noqa: E402
    MailboxPolicy,
    SeatClient,
    legal_heuristic_policy,
    run_seats,
)


def _token_for(seat: str, tokens_file: Path) -> str:
    env = (os.environ.get(f"TW2K_TOKEN_{seat}") or "").strip()
    if env:
        return env
    if tokens_file.exists():
        data = json.loads(tokens_file.read_text(encoding="utf-8"))
        tok = data.get(seat)
        if tok:
            return str(tok)
    raise SystemExit(f"no token for {seat}: set TW2K_TOKEN_{seat} or provide --tokens-file")


async def _main(args: argparse.Namespace) -> int:
    seats = [s.strip().upper() for s in (args.seats or args.seat or "").split(",") if s.strip()]
    if not seats:
        print("give --seat P3 or --seats P3,P4,P5", file=sys.stderr)
        return 2
    base = args.base_url
    if args.public:
        f = ROOT / ".tw2k" / "public_base_url.txt"
        if f.exists():
            base = f.read_text(encoding="utf-8").strip()
    tokens_file = Path(args.tokens_file)
    log = print if not args.quiet else (lambda _m: None)
    async with httpx.AsyncClient(base_url=base.rstrip("/"), timeout=httpx.Timeout(70.0, connect=15.0)) as http:
        clients: list[SeatClient] = []
        for seat in seats:
            if args.policy == "mailbox":
                policy = MailboxPolicy(args.mailbox_dir, margin_s=args.margin_s)  # one brain (mailbox) per seat
            else:
                policy = legal_heuristic_policy
            clients.append(SeatClient(http, seat, _token_for(seat, tokens_file), policy, wait_s=args.wait_s,
                                      safety_margin_s=args.margin_s, log=log))
        log(f"connecting {len(clients)} seat(s) to {base} policy={args.policy}")
        stats = await run_seats(clients, max_turns=args.max_turns)
    for seat, s in stats.items():
        print(f"{seat}: turns={s.turns} ok={s.ok} failed={s.failed} stale={s.stale} fallback_waits={s.fallback_waits} kinds={s.kinds}"
              + (f" last_error={s.last_error}" if s.last_error else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default=os.environ.get("TW2K_BASE_URL") or "http://127.0.0.1:8031")
    ap.add_argument("--public", action="store_true", help="use the tunnel URL from .tw2k/public_base_url.txt")
    ap.add_argument("--seat", default=os.environ.get("TW2K_SEAT"))
    ap.add_argument("--seats", default=os.environ.get("TW2K_SEATS"))
    ap.add_argument("--tokens-file", default=os.environ.get("TW2K_EXTERNAL_TOKENS_FILE") or str(ROOT / ".tw2k" / "external_tokens.json"))
    ap.add_argument("--policy", choices=["heuristic", "mailbox"], default="heuristic")
    ap.add_argument("--mailbox-dir", default=str(ROOT / ".tw2k" / "mailbox"))
    ap.add_argument("--max-turns", type=int, default=int(os.environ.get("TW2K_MAX_TURNS") or "0"))
    ap.add_argument("--wait-s", type=float, default=30.0, help="long-poll wait per request (max 60)")
    ap.add_argument("--margin-s", type=float, default=5.0, help="submit a safe wait this many seconds before the deadline")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    try:
        return asyncio.run(_main(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
