"""Dry-run checks for the computer-use pilot host (grokbot-player G5).

Run by ``scripts/run_cu_pilot.ps1 -DryRun`` against a host started with
``--start-paused`` (nobody takes a turn). Verifies:

1. host up (``/bot`` 200), spectator gate on (``/state`` 401 without the token);
2. lineup: P1 QwenA llm/custom, P2 SeatBrain external, P3 Commander external;
   seed / days / turns per day from the run's meta.json; match paused, 0 turns taken;
3. per-seat deadlines: P3 (computer use) 600 s, P2 (scripted bot) 60 s; hold enabled;
4. seat links: P3's claim link sets an HttpOnly cookie and lands on /bot?mode=cu;
5. turn_due webhook: a test ping for P3 is delivered; P2 has no webhook;
   with ``--receiver-port`` the payload is inspected (no observation, no token);
6. no seat token appears in the run's logs.

Prints PASS/FAIL per check; exit 0 only if all pass. Tokens are never printed.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
LINEUP = {"P1": ("QwenA", "llm"), "P2": ("SeatBrain", "external"), "P3": ("Commander", "external")}


class Receiver:
    """Tiny local webhook endpoint so the dry run can read the payload."""

    def __init__(self, port: int) -> None:
        self.payloads: list[dict] = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("content-length") or 0))
                try:
                    outer.payloads.append(json.loads(body or b"{}"))
                except json.JSONDecodeError:
                    outer.payloads.append({"raw": body.decode("utf-8", "replace")})
                self.send_response(200)
                self.end_headers()

            def log_message(self, *a):
                pass

        self.server = HTTPServer(("127.0.0.1", port), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="http://127.0.0.1:8032")
    ap.add_argument("--tokens-file", default=str(ROOT / ".tw2k" / "external_tokens.json"))
    ap.add_argument("--spectator-token-file", default=str(ROOT / ".tw2k" / "spectator_token.txt"))
    ap.add_argument("--links-dir", default=str(ROOT / ".tw2k" / "seat_links"))
    ap.add_argument("--saves-root", default=str(ROOT / "saves"))
    ap.add_argument("--log-dir", action="append", default=[], help="extra dirs to scan for leaked tokens")
    ap.add_argument("--receiver-port", type=int, default=0, help="host a local webhook receiver on this port")
    ap.add_argument("--seed", type=int, default=250925)
    ap.add_argument("--max-days", type=int, default=2)
    ap.add_argument("--turns-per-day", type=int, default=60)
    ap.add_argument("--cu-timeout", type=float, default=600.0)
    ap.add_argument("--bot-timeout", type=float, default=60.0)
    args = ap.parse_args(argv)

    results: list[tuple[bool, str]] = []

    def check(ok: bool, what: str) -> None:
        results.append((bool(ok), what))
        print(f"{'PASS' if ok else 'FAIL'}  {what}", flush=True)

    tokens = json.loads(Path(args.tokens_file).read_text(encoding="utf-8"))
    spec_tok = Path(args.spectator_token_file).read_text(encoding="utf-8").strip()
    receiver = Receiver(args.receiver_port) if args.receiver_port else None
    c = httpx.Client(base_url=args.base, timeout=30)
    seat = lambda pid: {"authorization": f"Bearer {tokens[pid]}"}  # noqa: E731

    # 1. host + gate
    check(c.get("/bot").status_code == 200, "host up: GET /bot 200")
    check(c.get("/state").status_code == 401, "spectator gate on: /state 401 without token")
    check(c.get("/harness/v1/P3/status").status_code == 401, "harness needs a seat credential (401 without)")

    # 2. lineup
    st = c.get("/state", headers={"authorization": f"Bearer {spec_tok}"}).json()
    players = {p["id"]: p for p in (st["players"] if isinstance(st["players"], list) else st["players"].values())}
    for pid, (name, kind) in LINEUP.items():
        p = players.get(pid, {})
        check(p.get("name") == name and p.get("kind") == kind, f"lineup {pid} = {name} ({kind}) [got {p.get('name')!r} {p.get('kind')!r}]")
    check(players.get("P1", {}).get("provider") == "custom", f"P1 provider custom (model {players.get('P1', {}).get('model')!r})")
    check(set(players) == set(LINEUP), f"exactly 3 seats {sorted(players)}")
    check(st.get("status") == "paused", f"match paused for the dry run (status {st.get('status')!r})")
    check(all(p.get("turns_today", 0) == 0 for p in players.values()), "no turns taken")
    check(all(p.get("turns_per_day") == args.turns_per_day for p in players.values()), f"{args.turns_per_day} turns/day")
    runs = sorted((p for p in Path(args.saves_root).iterdir() if (p / "meta.json").is_file()), key=lambda p: p.stat().st_mtime) \
        if Path(args.saves_root).is_dir() else []
    run_dir = runs[-1] if runs else None
    cfg = json.loads((run_dir / "meta.json").read_text(encoding="utf-8")).get("config", {}) if run_dir else {}
    check(cfg.get("seed") == args.seed and cfg.get("max_days") == args.max_days,
          f"seed {cfg.get('seed')} / {cfg.get('max_days')} days (meta.json in {run_dir.name if run_dir else '?'})")

    # 3. deadlines + hold
    s3 = c.get("/harness/v1/P3/status", headers=seat("P3")).json()
    s2 = c.get("/harness/v1/P2/status", headers=seat("P2")).json()
    check(s3.get("timeout_s") == args.cu_timeout, f"P3 computer-use deadline {s3.get('timeout_s')} s")
    check(s2.get("timeout_s") == args.bot_timeout, f"P2 scripted-bot deadline {s2.get('timeout_s')} s")
    check((s3.get("hold") or {}).get("max", 0) > 0, f"hold-my-slot enabled (max {(s3.get('hold') or {}).get('max')})")

    # 4. seat link
    link_file = Path(args.links_dir) / "P3.txt"
    link = link_file.read_text(encoding="utf-8").strip() if link_file.is_file() else ""
    check(bool(link), f"seat link written: {link_file}")
    if link:
        path = link[link.index("/bot/claim"):]
        r = c.get(path, follow_redirects=False)
        check(r.status_code == 303 and r.headers.get("location") == "/bot?seat=P3&mode=cu"
              and "HttpOnly" in r.headers.get("set-cookie", ""), "P3 seat link -> 303 /bot?seat=P3&mode=cu + HttpOnly cookie")

    # 5. webhook
    r = c.post("/harness/v1/P3/webhook_test", headers=seat("P3"))
    body = r.json() if r.status_code == 200 else {}
    check(r.status_code == 200 and body.get("delivered"), f"P3 turn_due test ping delivered ({[(d['attempt'], d['status']) for d in body.get('deliveries', [])]})")
    check(c.post("/harness/v1/P2/webhook_test", headers=seat("P2")).status_code == 409, "P2 (scripted bot) has no webhook")
    if receiver is not None:
        got = receiver.payloads[-1] if receiver.payloads else {}
        raw = json.dumps(got)
        check(got.get("event") == "turn_due_test" and got.get("seat") == "P3" and "turn_seq" in got and got.get("deadline_at"),
              "payload has seat / turn_seq / deadline_at")
        check(str(got.get("bot_url", "")).endswith("/bot?seat=P3&mode=cu"), f"payload bot_url {got.get('bot_url')}")
        check("observation" not in got and not any(t in raw for t in tokens.values()), "payload has no observation dump and no token")
        receiver.close()

    # 6. no token in logs
    scan = [run_dir] if run_dir else []
    scan += [Path(d) for d in args.log_dir]
    leaked = []
    for d in scan:
        for f in d.rglob("*"):
            if f.is_file() and f.stat().st_size < 50_000_000:
                text = f.read_text(encoding="utf-8", errors="ignore")
                if any(t in text for t in tokens.values()) or spec_tok in text:
                    leaked.append(str(f))
    check(not leaked, f"no seat/spectator token in {len(scan)} log dir(s)" + (f": {leaked}" if leaked else ""))

    failed = [w for ok, w in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed", flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
