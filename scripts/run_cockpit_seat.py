"""Drive one external seat from the cockpit harness over HTTP. Test use only.

NOTE 55. The seat reads its own observation, reference, events and status,
and posts actions the redesign cockpit can send, with the seat's bearer
token from a tokens file. It refuses to start unless AI_COCKPIT_SEAT_MODE is
tw2002 in this process (set the environment variable of the same name).

    AI_COCKPIT_SEAT_MODE=tw2002 python scripts/run_cockpit_seat.py \
        --base-url http://127.0.0.1:8027 --seat P2 --tokens-file tokens.json --days 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ENV_MODE = "AI_COCKPIT_SEAT_MODE"


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--seat", required=True)
    parser.add_argument("--tokens-file", required=True)
    parser.add_argument("--days", type=int, default=10,
                        help="game days to play, counted from the day the seat starts on")
    parser.add_argument("--out", default="", help="write the run report JSON here")
    parser.add_argument("--idle-s", type=float, default=600.0)
    parser.add_argument("--directives", default="",
                        help="per-seat directive inbox, for example runs/directives with P3.json inside")
    parser.add_argument("--stuck-after", type=int, default=6,
                        help="acted turns with no progress before a recovery directive")
    return parser.parse_args(argv)


def switch_on() -> bool:
    import tw2k.engine.constants as K

    mode = (os.environ.get(ENV_MODE) or "").strip().lower()
    if mode:
        K.AI_COCKPIT_SEAT_MODE = mode
    return K.ai_cockpit_seat_on()


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    if not switch_on():
        print(f"refusing to start: {ENV_MODE} is legacy in this process", file=sys.stderr)
        return 2
    try:
        tokens = json.loads(Path(args.tokens_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read the tokens file: {exc}", file=sys.stderr)
        return 2
    seat = str(args.seat).upper()
    token = str((tokens or {}).get(seat) or "")
    if not token:
        print(f"the tokens file has no token for {seat}", file=sys.stderr)
        return 2

    import httpx

    from tw2k.agents.cockpit_seat import run_http

    async def _go() -> dict:
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(base_url=args.base_url.rstrip("/"), timeout=timeout) as client:
            return await run_http(
                client, seat, token, int(args.days), idle_s=float(args.idle_s),
                directives=str(args.directives or "") or None,
                stuck_after=int(args.stuck_after),
            )

    report = asyncio.run(_go())
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    for row in report["days"]:
        print(f"day {row['day']}: credits {row['credits_start']:,} -> {row['credits_end']:,}, "
              f"net worth {row['net_worth_start']:,} -> {row['net_worth_end']:,}, "
              f"turns {row['turns_used']}, trades {row['trades']}, refused {row['refused']}")
    print(f"posts {report['posts']}, refused {len(report['refused'])}")
    if report["posts"] == 0:
        print(f"the seat made 0 posts: started on day {report.get('start_day')}, asked for {args.days} day(s)"
              f" through day {report.get('end_day')}, and no turn of its own opened", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
