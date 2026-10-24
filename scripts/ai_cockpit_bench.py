"""NOTE 172. A 10-day bench for the scripted AI cockpit seat. Test use only.

The app and one match run in this process on a port in 8020-8030. Three
heuristic code bots (H1, H2, H3) and one external seat, Commander, which is
played by scripts/ai_cockpit_player.py through the mode=cu seat link only.
V311_PROFILE is set only inside this process.

    python scripts/ai_cockpit_bench.py --seed 250925 --days 10 --out bench.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PLAYER = ROOT / "scripts" / "ai_cockpit_player.py"
# AI_BENCH_PORTS=8026-8030 keeps the bench off a lobby on the low ports.
_lo, _hi = (int(x) for x in os.environ.get("AI_BENCH_PORTS", "8020-8030").split("-"))
PORTS = range(_lo, _hi + 1)
TOKEN = "bench-cockpit-commander-token-0001"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def free_port() -> int:
    for port in PORTS:
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("no free port in 8020-8030")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=250925)
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--turns", type=int, default=40)
    ap.add_argument("--level", default="hard")
    ap.add_argument("--day-seconds", type=float, default=0.0,
                    help="one day of the v3.11 turn clock in seconds; 0 keeps the 40-turn test day")
    ap.add_argument("--out", default="")
    ap.add_argument("--work", default="", help="keep the saves and the player run here")
    ap.add_argument("--timeout", type=float, default=7200.0)
    args = ap.parse_args(argv)

    import tw2k.engine.constants as K

    K.V311_PROFILE = "v311"
    if not args.day_seconds:
        # The 40-turn test day: the day rolls when every seat is done, as in the
        # NOTE 152 and NOTE 171 benches. Only this process sees the change.
        K.live_pace = lambda: False
        K.turn_regen_live = lambda: False
        # NOTE 172d. With regen off but the v3.11 starting package on, tick_day
        # never refills a day, so every seat had one day of turns for the whole
        # bench. The test day hands the full day back at each roll.
        import tw2k.engine.runner as _er
        import tw2k.server.runner as _sr

        _tick = _er.tick_day

        def _tick_refill(universe) -> None:
            _tick(universe)
            for player in universe.players.values():
                player.turns_today = 0

        _er.tick_day = _tick_refill
        _sr.tick_day = _tick_refill
    import uvicorn

    from tw2k.engine import GameConfig
    from tw2k.engine.victory import full_net_worth
    from tw2k.server.app import create_app
    from tw2k.server.runner import AgentSpec, MatchSpec

    tmp = Path(args.work) if args.work else Path(tempfile.mkdtemp(prefix="cockpit-bench-"))
    tmp.mkdir(parents=True, exist_ok=True)
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp / "saves"
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    spec = MatchSpec(
        config=GameConfig(seed=args.seed, universe_size=200, max_days=args.days,
                          turns_per_day=args.turns, enable_ferrengi=True, action_delay_s=0.0,
                          turn_regen_day_seconds=args.day_seconds or None),
        agents=[
            AgentSpec(player_id="P1", name="H1", kind="heuristic"),
            AgentSpec(player_id="P2", name="H2", kind="heuristic"),
            AgentSpec(player_id="P3", name="H3", kind="heuristic"),
            AgentSpec(player_id="P4", name="Commander", kind="external", external_token=TOKEN),
        ],
        action_delay_s=0.0,
        external_timeout_s=900.0,
    )

    async def _main() -> None:
        async def start() -> None:
            while not server.started:
                await asyncio.sleep(0.05)
            await runner.start(spec)

        task = asyncio.create_task(start())
        await server.serve()
        task.cancel()
        await runner.stop()

    thread = threading.Thread(target=lambda: asyncio.run(_main()), daemon=True)
    thread.start()
    deadline = time.time() + 30
    while time.time() < deadline and runner.state.universe is None:
        time.sleep(0.1)
    run_dir = tmp / "run"
    url = f"http://127.0.0.1:{port}/bot?seat=P4&mode=cu&token={TOKEN}&layout=redesign"
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    for key in ("XAI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        env.pop(key, None)
    proc = subprocess.Popen(
        [sys.executable, str(PLAYER), "--url", url, "--provider", "scripted", "--level", args.level,
         "--max-turns", str(args.turns * args.days * 15), "--min-interval", "0", "--run-dir", str(run_dir)],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    t0 = time.time()
    try:
        while time.time() - t0 < args.timeout:
            if proc.poll() is not None:
                break
            if runner.state.status in ("finished", "error"):
                time.sleep(5)
                break
            time.sleep(2)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
    u = runner.state.universe
    seats = []
    for pid, p in u.players.items():
        seats.append({"id": pid, "name": p.name, "net_worth": int(full_net_worth(u, p)),
                      "credits": int(p.credits), "alive": bool(p.alive),
                      "holds": int(getattr(p.ship, "holds", 0) or 0),
                      "fighters": int(getattr(p.ship, "fighters", 0) or 0),
                      "shields": int(getattr(p.ship, "shields", 0) or 0),
                      "ship": str(getattr(p.ship, "ship_class", ""))})
    seats.sort(key=lambda r: -r["net_worth"])
    rank = next(i + 1 for i, r in enumerate(seats) if r["name"] == "Commander")
    report = {"seed": args.seed, "days": args.days, "day": int(getattr(u, "day", 0)),
              "rank": rank, "seats": seats, "elapsed_s": round(time.time() - t0)}
    labels = []
    actions = run_dir / "actions.jsonl"
    if actions.is_file():
        for line in actions.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            labels.append(str(row.get("note") or row.get("label") or ""))
    report["clicks"] = len(labels)
    report["plans"] = {k: labels.count(k) for k in sorted(set(labels)) if labels.count(k) >= 1}
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    server.should_exit = True
    thread.join(timeout=15)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
