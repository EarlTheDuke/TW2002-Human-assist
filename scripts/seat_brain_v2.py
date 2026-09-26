#!/usr/bin/env python3
"""Run the S3 goal-driven SeatBrain for one seat.

Reads ONLY that seat's own observation - never /state, never other seats.

Mailbox mode (default; same files as the old commander_p4_brain.py and
grokbot_seat_client.py --policy mailbox):
  python scripts/grokbot_seat_client.py --seat P4 --policy mailbox      # runner: harness <-> files
  python scripts/seat_brain_v2.py --seat P4                             # brain:  files -> decision

Direct harness mode (no mailbox; brain drives the seat itself):
  python scripts/seat_brain_v2.py --seat P4 --harness --base-url http://127.0.0.1:8031

Optional --log-dir writes one JSON line per decision (turns.jsonl). Every
row carries the process git SHA and the seat_brain module mtime captured at
startup. live_summary.json is rewritten on every decision.

Ops
---
After any brain commit, restart the brain process only. Leave the match,
the harness, and the other seats running. Then confirm the startup line
contains the new commit (`seat_brain_v2 <SEAT> SHA=<commit> module_mtime=...`).
The same SHA and module mtime are copied onto every turns.jsonl row.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tw2k.agents import seat_brain as _seat_brain_mod  # noqa: E402
from tw2k.agents.seat_brain import SeatBrain  # noqa: E402

_PLANET_KEYS = ("id", "origin", "citadel_level", "citadel_target", "colonists_total")


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    sha = out.strip()
    return sha or "unknown"


def _module_mtime() -> str:
    """mtime of the decision module this process imported, in UTC."""
    path = Path(_seat_brain_mod.__file__).resolve()
    return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()


def runtime_identity() -> dict[str, str]:
    """Git SHA + seat_brain module mtime for this process. Captured once at start."""
    return {
        "git_sha": _git_sha(),
        "module_mtime": _module_mtime(),
        "module": "tw2k.agents.seat_brain",
    }


def _announce(seat: str, ident: dict[str, str], extra: str = "") -> None:
    tail = f" {extra}" if extra else ""
    print(
        f"seat_brain_v2 {seat} SHA={ident['git_sha']} module_mtime={ident['module_mtime']} "
        f"module={ident['module']}{tail}",
        flush=True,
    )


def _planets(obs: dict) -> list[dict]:
    return [{k: p.get(k) for k in _PLANET_KEYS} for p in (obs.get("owned_planets") or []) if isinstance(p, dict)]


def _goal_text(action: dict, prior: dict, action_key: str, prior_key: str) -> str:
    written = action.get(action_key)
    if written is not None:
        return str(written)
    return str(prior.get(prior_key) or "")


def _goals(obs: dict, action: dict) -> dict[str, str]:
    prior = obs.get("goals") if isinstance(obs.get("goals"), dict) else {}
    return {
        "short": _goal_text(action, prior, "goal_short", "short"),
        "medium": _goal_text(action, prior, "goal_medium", "medium"),
        "long": _goal_text(action, prior, "goal_long", "long"),
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _log(log_dir: Path | None, seq, obs: dict, action: dict, brain: SeatBrain, *,
         seat: str, ident: dict[str, str], summary_path: Path) -> None:
    rep = brain.last_report
    mem = brain.mem
    line = (f"seq={seq} day={obs.get('day')} sector={(obs.get('sector') or {}).get('id')} "
            f"cr={obs.get('credits')} -> {action['kind']} {action.get('args')} | {action.get('thought')}")
    print(line, flush=True)
    sector = (obs.get("sector") or {}).get("id")
    planets = _planets(obs)
    action_rec = {k: action[k] for k in ("kind", "args", "thought") if k in action}
    rec = {
        "ts": datetime.now(UTC).isoformat(), "turn_seq": seq, "day": obs.get("day"),
        "sector": sector, "credits": obs.get("credits"),
        "net_worth": obs.get("net_worth"), "action": action_rec,
        "git_sha": ident["git_sha"], "module_mtime": ident["module_mtime"],
        "progress": rep.summary() if rep else None,
        "owned_planets": planets,
    }
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "turns.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    summary = {
        "ts": rec["ts"], "seat": seat, "git_sha": ident["git_sha"], "module_mtime": ident["module_mtime"],
        "turn_seq": seq, "day": obs.get("day"), "sector": sector, "credits": obs.get("credits"),
        "net_worth": obs.get("net_worth"), "goals": _goals(obs, action), "planets": planets,
        "last_action": action_rec,
        "stall_breaks": int(mem.stall_breaks) if mem is not None else 0,
        "replans": int(mem.replans) if mem is not None else 0,
    }
    _write_json(summary_path, summary)


def run_mailbox(seat: str, mailbox: Path, log_dir: Path | None, max_turns: int, record: Path | None = None,
                *, ident: dict[str, str] | None = None, summary_path: Path | None = None) -> int:
    brain = SeatBrain()
    ident = ident or runtime_identity()
    if summary_path is None:
        summary_path = (log_dir / "live_summary.json") if log_dir else (mailbox / f"{seat}.live_summary.json")
    pending = mailbox / f"{seat}.pending.json"
    decision = mailbox / f"{seat}.decision.json"
    _announce(seat, ident, f"watching {pending}")
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
        _log(log_dir, seq, obs, action, brain, seat=seat, ident=ident, summary_path=summary_path)
        last_seq = seq
        played += 1
    return 0


async def run_harness(seat: str, base_url: str, tokens_file: Path, log_dir: Path | None, max_turns: int,
                       *, ident: dict[str, str] | None = None, summary_path: Path | None = None) -> int:
    import httpx

    from tw2k.agents.pathb_client import SeatClient

    token = json.loads(tokens_file.read_text(encoding="utf-8"))[seat]
    brain = SeatBrain()
    ident = ident or runtime_identity()
    summary_path = summary_path or (
        (log_dir / "live_summary.json") if log_dir else (ROOT / ".tw2k" / f"{seat}.live_summary.json")
    )
    _announce(seat, ident, f"harness {base_url}")

    def policy(ctx):
        action = brain.decide(ctx.observation)
        _log(log_dir, ctx.turn_seq, ctx.observation, action, brain, seat=seat, ident=ident, summary_path=summary_path)
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
    ident = runtime_identity()
    try:
        if args.harness:
            return asyncio.run(run_harness(seat, args.base_url, Path(args.tokens_file), log_dir, args.max_turns,
                                           ident=ident))
        return run_mailbox(seat, Path(args.mailbox_dir), log_dir, args.max_turns,
                           Path(args.record) if args.record else None, ident=ident)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
