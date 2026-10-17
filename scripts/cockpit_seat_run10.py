"""NOTE 55 run10. Ten days of the cockpit-only seat on its own local server.

Test use only. The server runs in this process on a free port in 8020-8030
with port stock and haggle live. P1 is the heuristic bot and P2 is an
external seat. The seat runs in a subprocess through
scripts/run_cockpit_seat.py over real HTTP, with AI_COCKPIT_SEAT_MODE=tw2002
set only in that subprocess. Halfway through each day this driver pauses
the match, takes one screenshot of the redesign cockpit for P2, compares
the cockpit credits and sector with the seat's own observation, and
resumes. The token lives in a temp file and is never printed or saved.

    python scripts/cockpit_seat_run10.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "playtests" / "cockpit-ai-seat-v2"
V2 = OUT
# NOTE 56: --v3 turns the cockpit block on in the server and writes cockpit-ai-seat-v3.
V3 = "--v3" in sys.argv[1:]
if V3:
    OUT = ROOT / "docs" / "playtests" / "cockpit-ai-seat-v3"
TAG = "v3" if V3 else "v2"
PORTS = range(8020, 8031)
SEED, DAYS, TURNS, CREDITS, SECTORS = 250925, 10, 100, 20_000, 200
VIEW = {"width": 1440, "height": 900}


def free_port() -> int:
    for port in PORTS:
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit("no free port in 8020-8030")


class Host:
    """The real app and one match on a background thread."""

    def __init__(self, tmp: Path, token: str) -> None:
        import uvicorn

        import tw2k.engine.constants as K
        from tw2k.server.app import create_app

        K.PORT_STOCK_FIDELITY_MODE = "live"
        K.HAGGLE_LIVE_MODE = "live"
        if V3:
            K.COCKPIT_FIELDS_MODE = "tw2002"
        self.token = token
        self.port = free_port()
        self.app = create_app(auto_start=False)
        self.runner = self.app.state.runner
        self.runner._saves_root = tmp / "saves"
        self.server = uvicorn.Server(uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="warning"))
        self.thread = threading.Thread(target=lambda: asyncio.run(self._main()), daemon=True)

    async def _main(self) -> None:
        from tw2k.engine import GameConfig
        from tw2k.server.runner import AgentSpec, MatchSpec

        async def start() -> None:
            while not self.server.started:
                await asyncio.sleep(0.05)
            await self.runner.start(MatchSpec(
                config=GameConfig(seed=SEED, universe_size=SECTORS, max_days=DAYS, turns_per_day=TURNS,
                                  starting_credits=CREDITS, enable_ferrengi=True, enable_planets=True,
                                  action_delay_s=0.0, all_start_stardock=True),
                agents=[
                    AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
                    AgentSpec(player_id="P2", name="CockpitSeat", kind="external", external_token=self.token),
                ],
                action_delay_s=0.03,
                external_timeout_s=600.0,
            ))

        task = asyncio.create_task(start())
        await self.server.serve()
        task.cancel()
        await self.runner.stop()

    def __enter__(self) -> Host:
        self.thread.start()
        deadline = time.time() + 30
        while time.time() < deadline and not (self.server.started and self.runner.state.universe is not None):
            time.sleep(0.1)
        if not self.server.started or self.runner.state.universe is None:
            raise SystemExit("the local server did not start")
        return self

    def __exit__(self, *exc) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=20)

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def seat_day(self) -> tuple[int, int, bool]:
        u = self.runner.state.universe
        me = u.players.get("P2") if u is not None else None
        over = bool(getattr(u, "game_over", False)) or self.runner.state.status in ("finished", "stopped")
        return int(getattr(u, "day", 0) or 0), int(getattr(me, "turns_today", 0) or 0), over


def _digits(text: str) -> int | None:
    found = re.sub(r"[^0-9-]", "", text or "")
    return int(found) if found not in ("", "-") else None


def shoot(page, http: httpx.Client, host: Host, name: str) -> dict:
    """Screenshot the cockpit while paused and compare it with the seat."""
    peek = http.get("/harness/v1/P2/observation", params={"wait_s": 0, "peek": 1}).json()
    obs = peek.get("observation") or {}
    seat_credits = int(obs.get("credits") or 0)
    seat_sector = int((obs.get("sector") or {}).get("id") or 0)
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={host.token}")
    cockpit_credits = cockpit_sector = None
    deadline = time.time() + 15
    while time.time() < deadline:
        cockpit_credits = _digits(page.locator("#credits").inner_text())
        cockpit_sector = _digits(page.locator("#pSector").inner_text())
        if cockpit_credits == seat_credits and cockpit_sector == seat_sector:
            break
        page.wait_for_timeout(300)
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path))
    return {
        "shot": f"docs/playtests/cockpit-ai-seat-{TAG}/{name}.png",
        "day": int(obs.get("day") or 0),
        "turns_remaining": int(obs.get("turns_remaining") or 0),
        "seat_credits": seat_credits, "cockpit_credits": cockpit_credits,
        "seat_sector": seat_sector, "cockpit_sector": cockpit_sector,
        "match": cockpit_credits == seat_credits and cockpit_sector == seat_sector,
    }


def gaps_md(report: dict) -> str:
    from tw2k.agents.cockpit_seat import GAP_TEXT

    lines = [
        "# Cockpit seat v2: gaps found in the 10-day run",
        "",
        "Each row is one decision the cockpit-only seat made during run10, and what it",
        "needed that a human at the original TW2002 screen would have had. The count is",
        "the number of turns where the seat needed it. Rows come from the run report",
        "(`run10.json`, `gaps`), written while the seat played.",
        "",
        "| Decision | Turns | What the seat needed | Where the cockpit has it | Original TW2002 screen |",
        "| --- | ---: | --- | --- | --- |",
    ]
    seen = set()
    for row in report.get("gaps") or []:
        seen.add(row["id"])
        lines.append(f"| {row['decision']} | {row['count']} | {row['needed']} | {row['cockpit']} | {row['original']} |")
    unused = [gid for gid in GAP_TEXT if gid not in seen]
    if unused:
        lines += ["", "These listed gaps did not come up in this run: " + ", ".join(f"`{gid}`" for gid in unused) + "."]
    return "\n".join(lines) + "\n"


def gaps_md_v3(report: dict) -> str:
    """NOTE 56: each v2 gap with its v2 count, its v3 count, and what closed it."""
    from tw2k.agents.cockpit_seat import GAP_FIELDS, GAP_TEXT

    before: dict[str, int] = {}
    try:
        v2 = json.loads((V2 / "run10.json").read_text(encoding="utf-8"))
        before = {row["id"]: int(row["count"]) for row in v2.get("gaps") or []}
    except (OSError, ValueError, KeyError):
        pass
    after = {row["id"]: int(row["count"]) for row in report.get("gaps") or []}
    lines = [
        "# Cockpit seat v3: the gaps after cockpit-gaps-v1",
        "",
        "Each row is one gap the cockpit-only seat found in the v2 run10. \"v2\" is the",
        "number of turns it needed the missing piece then (cockpit-ai-seat-v2/run10.json);",
        "\"v3\" is the count in this run, with the cockpit block on (COCKPIT_FIELDS_MODE=tw2002).",
        "A gap marked \"not in original\" is one the original TW2002 never prints either, so the",
        "cockpit adds no hint and the seat keeps its guess there.",
        "",
        "| Decision | v2 | v3 | Status | Where the cockpit has it now | Original TW2002 screen |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for gid, (decision, _needed, _cockpit, original) in GAP_TEXT.items():
        status, where = GAP_FIELDS[gid]
        lines.append(f"| {decision} | {before.get(gid, 0)} | {after.get(gid, 0)} | {status} | {where} | {original} |")
    return "\n".join(lines) + "\n"


def run10_txt(report: dict, replay: list[dict], port: int, seat_out: str) -> str:
    days = report["days"]
    first, last = days[0], days[-1]
    lines = [
        "Cockpit seat v3, run10 (NOTE 56, the seat reads the cockpit block)." if V3 else "Cockpit seat v2, run10 (NOTE 55).",
        f"Local server on port {port}. Seed {SEED}, {SECTORS} sectors, {DAYS} days, {TURNS} turns a day,"
        f" {CREDITS:,} starting credits, all seats start at StarDock, Ferrengi on.",
        "Port stock live and haggle live. P1 heuristic, P2 the cockpit-only seat over HTTP.",
        "",
        "day  credits start -> end      net worth start -> end    turns  trades  buys  sells  holds+  refused",
    ]
    for row in days:
        lines.append(
            f"{row['day']:>3}  {row['credits_start']:>10,} -> {row['credits_end']:>10,}"
            f"  {row['net_worth_start']:>10,} -> {row['net_worth_end']:>10,}"
            f"  {row['turns_used']:>5}  {row['trades']:>6}  {row['buys']:>4}  {row['sells']:>5}"
            f"  {row['holds_bought']:>6}  {row['refused']:>7}"
        )
    lines += [
        "",
        f"Credits {first['credits_start']:,} -> {last['credits_end']:,}."
        f" Net worth {first['net_worth_start']:,} -> {last['net_worth_end']:,}.",
        f"Posts {report['posts']}, refused {len(report['refused'])}. Kinds: "
        + ", ".join(f"{k} {v}" for k, v in sorted(report["kinds"].items())) + ".",
        f"Final (after the last day): day {report['final'].get('day')}, credits {report['final'].get('credits'):,},"
        f" sector {report['final'].get('sector')}, holds {report['final'].get('holds')}.",
        "",
        "Replay check (cockpit vs seat, while paused):",
    ]
    for row in replay:
        lines.append(
            f"  {Path(row['shot']).name}: day {row['day']}, seat {row['seat_credits']:,} cr in {row['seat_sector']},"
            f" cockpit {row['cockpit_credits']} cr in {row['cockpit_sector']}, {'match' if row['match'] else 'MISMATCH'}"
        )
    lines += ["", "Seat runner output:", *("  " + line for line in seat_out.strip().splitlines())]
    return "\n".join(lines) + "\n"


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="cockpit-seat-run10-"))
    token = secrets.token_urlsafe(24)
    tokens = tmp / "tokens.json"
    tokens.write_text(json.dumps({"P2": token}), encoding="utf-8")
    report_path = tmp / "report.json"
    replay: list[dict] = []
    with Host(tmp, token) as host:
        env = {**os.environ, "AI_COCKPIT_SEAT_MODE": "tw2002", "PYTHONUNBUFFERED": "1"}
        env["PYTHONPATH"] = str(ROOT / "src")
        child = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts" / "run_cockpit_seat.py"), "--base-url", host.base,
             "--seat", "P2", "--tokens-file", str(tokens), "--days", str(DAYS), "--out", str(report_path)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        headers = {"authorization": f"Bearer {token}"}
        with httpx.Client(base_url=host.base, headers=headers, timeout=30) as http, sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport=VIEW)
            shot_days: set[int] = set()
            while child.poll() is None:
                day, used, over = host.seat_day()
                if over:
                    break
                if 1 <= day <= DAYS and day not in shot_days and used >= TURNS // 2:
                    http.post("/control/pause")
                    time.sleep(0.5)
                    replay.append(shoot(page, http, host, f"day{day:02d}"))
                    shot_days.add(day)
                    http.post("/control/resume")
                time.sleep(0.01)
            seat_out, _ = child.communicate(timeout=900)
            replay.append(shoot(page, http, host, "final"))
            browser.close()
        code = child.returncode
    if code != 0:
        print(seat_out)
        raise SystemExit(f"the seat runner exited with {code}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    final = report.get("final") or {}
    last = replay[-1]
    report_final_match = last["seat_credits"] == final.get("credits") and last["seat_sector"] == final.get("sector")
    run = {
        "note": "NOTE 56 cockpit-ai-seat-v3 run10" if V3 else "NOTE 55 cockpit-ai-seat-v2 run10",
        "settings": {
            "port": host.port, "seed": SEED, "universe_size": SECTORS, "max_days": DAYS, "turns_per_day": TURNS,
            "starting_credits": CREDITS, "all_start_stardock": True, "enable_ferrengi": True,
            "port_stock_fidelity": "live", "haggle_live": "live",
            "cockpit_fields": "tw2002" if V3 else "legacy", "seats": {"P1": "heuristic", "P2": "cockpit seat"},
        },
        "days": report["days"],
        "posts": report["posts"],
        "refused": report["refused"],
        "kinds": report["kinds"],
        "gaps": report["gaps"],
        "day_end_source": report.get("day_end_source"),
        "start_day": report.get("start_day"),
        "end_day": report.get("end_day"),
        "final": final,
        "replay": replay,
        "replay_all_match": all(row["match"] for row in replay),
        "final_matches_seat_report": report_final_match,
        "log_tail": report.get("log", [])[-40:],
    }
    text = json.dumps(run, indent=2, default=str) + "\n"
    if token in text or token in seat_out:
        raise SystemExit("the token leaked into the output; nothing written")
    (OUT / "run10.json").write_text(text, encoding="utf-8")
    (OUT / "run10.txt").write_text(run10_txt(report, replay, host.port, seat_out), encoding="utf-8")
    (OUT / "gaps.md").write_text(gaps_md_v3(report) if V3 else gaps_md(report), encoding="utf-8")
    days = report["days"]
    print(f"port {host.port}: credits {days[0]['credits_start']:,} -> {days[-1]['credits_end']:,},"
          f" net worth {days[0]['net_worth_start']:,} -> {days[-1]['net_worth_end']:,},"
          f" posts {report['posts']}, refused {len(report['refused'])},"
          f" replay match {run['replay_all_match']}, shots {len(replay)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
