"""Summarise a pilot run's per-action log for the computer-use seat (grokbot-player G5 -> G6).

Reads ``saves/<run>/external_actions.jsonl`` (written for every external seat)
and ``webhook_deliveries.jsonl`` and prints a Markdown table per seat: wall
time per action, illegal attempts, rejected posts, retries, auto-WAITs, held
actions and webhook delivery health. Paste it into
``docs/playtests/cu-pilot-*/INSIGHTS.md``.

    python scripts/cu_pilot_report.py saves/<run-id>            # a run dir
    python scripts/cu_pilot_report.py --latest                   # newest run under saves/ (or TW2K_SAVES_DIR)
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, round(q * (len(s) - 1)))]


def summarise(run_dir: Path) -> dict[str, dict]:
    per: dict[str, dict] = defaultdict(lambda: {"results": [], "posts": [], "released": 0, "hooks": []})
    for r in _rows(run_dir / "external_actions.jsonl"):
        seat = per[r["seat"]]
        if r["event"] == "result":
            seat["results"].append(r)
        elif r["event"] == "post":
            seat["posts"].append(r)
        elif r["event"] == "slot_released":
            seat["released"] += 1
    for r in _rows(run_dir / "webhook_deliveries.jsonl"):
        per[r["seat"]]["hooks"].append(r)
    out: dict[str, dict] = {}
    for seat, d in sorted(per.items()):
        res = d["results"]
        played = [r for r in res if not r.get("auto")]
        think = [r["think_s"] for r in played if r.get("think_s") is not None]
        rejected = Counter(p["status"] for p in d["posts"] if p["status"] != 200)
        hooks_ok = sum(1 for h in d["hooks"] if h.get("ok"))
        out[seat] = {
            "actions": len(played),
            "ok": sum(1 for r in played if r.get("ok")),
            "illegal": sum(1 for r in played if not r.get("ok")),
            "auto_waits": sum(1 for r in res if r.get("auto")),
            "rejected_posts": dict(sorted(rejected.items())),
            "retries": sum(1 for r in played if (r.get("posts") or 1) > 1),
            "held_actions": sum(1 for r in played if r.get("held")),
            "slots_released": d["released"],
            "think_median_s": round(statistics.median(think), 1) if think else None,
            "think_p90_s": round(_pct(think, 0.9), 1) if think else None,
            "think_max_s": round(max(think), 1) if think else None,
            "kinds": dict(Counter(r.get("kind") for r in played).most_common()),
            "webhook_ok": hooks_ok,
            "webhook_failed_attempts": len(d["hooks"]) - hooks_ok,
        }
    return out


def to_markdown(run_dir: Path, summary: dict[str, dict]) -> str:
    lines = [f"### Pilot per-action summary - `{run_dir.name}`", "",
             "| Seat | Actions | OK | Illegal | Auto-WAIT | Rejected posts | Retries | Held | Think median / p90 / max (s) | Webhook ok / failed |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for seat, s in summary.items():
        rej = ", ".join(f"{k}x{v}" for k, v in s["rejected_posts"].items()) or "0"
        think = " / ".join("-" if s[k] is None else str(s[k]) for k in ("think_median_s", "think_p90_s", "think_max_s"))
        lines.append(f"| {seat} | {s['actions']} | {s['ok']} | {s['illegal']} | {s['auto_waits']} | {rej} | {s['retries']} | "
                     f"{s['held_actions']} (+{s['slots_released']} released) | {think} | {s['webhook_ok']} / {s['webhook_failed_attempts']} |")
    lines += ["", "Verbs per seat: " + "; ".join(f"{seat}: {s['kinds']}" for seat, s in summary.items())]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", nargs="?", help="saves/<run-id> directory")
    ap.add_argument("--latest", action="store_true", help="use the newest run dir under the saves root")
    ap.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    args = ap.parse_args(argv)
    if args.latest:
        root = Path(os.environ.get("TW2K_SAVES_DIR") or ROOT / "saves")
        runs = sorted((p for p in root.iterdir() if (p / "meta.json").is_file()), key=lambda p: p.stat().st_mtime) if root.is_dir() else []
        if not runs:
            print(f"no runs under {root}", file=sys.stderr)
            return 1
        run_dir = runs[-1]
    elif args.run_dir:
        run_dir = Path(args.run_dir)
    else:
        ap.error("give a run dir or --latest")
    summary = summarise(run_dir)
    print(json.dumps(summary, indent=2) if args.json else to_markdown(run_dir, summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
