"""Run a TW2K-AI match headlessly and emit scorecards.

This script drives the engine directly (no FastAPI server, no WebSocket) so it
can be called in tight iteration loops without polluting a long-lived server.

Artifacts land under ``artifacts/run-<UTC timestamp>-<suffix>/``:

    events.jsonl     - full event stream, one JSON per line
    scorecards.txt   - per-day scorecards + end-of-game arc report
    summary.json     - machine-readable final summary
    run.log          - stdout mirror

Exit codes:
    0 - match completed, rubric thresholds met (or --no-gate)
    1 - match completed but rubric regression detected
    2 - runtime error

Usage:
    python scripts/run_match_headless.py                         # heuristic, 2 agents, 10 days
    python scripts/run_match_headless.py --days 5 --agents 3
    python scripts/run_match_headless.py --kind llm              # requires provider env vars
    python scripts/run_match_headless.py --no-gate               # never fail on rubric
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import traceback
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from watch_match import (  # noqa: E402
    RUBRIC,
    PlayerArc,
    evaluate,
    render_arc_report,
    render_scorecard,
    resolve_actor,
    update_from_event,
)

from tw2k.agents import BaseAgent, HeuristicAgent  # noqa: E402
from tw2k.engine import (  # noqa: E402
    Action,
    ActionKind,
    GameConfig,
    apply_action,
    build_observation,
    generate_universe,
    is_finished,
    tick_day,
)
from tw2k.engine.models import Player, Ship  # noqa: E402

# ---------------------------------------------------------------------------
# Event → dict helper
# ---------------------------------------------------------------------------


def event_to_dict(event) -> dict:
    """Convert an engine Event (pydantic BaseModel) to a plain dict the
    watcher helpers understand. The engine stores EventKind as an enum; we
    normalise to the string value so downstream code matches on ``"warp"``
    etc."""
    d = event.model_dump(mode="json")
    # pydantic serialises the str-enum to its value already when mode="json",
    # but we defend against future changes.
    kind = d.get("kind")
    if hasattr(kind, "value"):
        d["kind"] = kind.value
    return d


# ---------------------------------------------------------------------------
# State snapshot (matches the shape watch_match.close_day() expects)
# ---------------------------------------------------------------------------


def snapshot_state(universe) -> dict:
    """Build a lightweight state dict in the shape the watcher's close_day
    helpers expect: ``{"players": [...], "planets": [...]}``. We only include
    the fields that the scorecard actually reads."""
    players = []
    for pid, p in universe.players.items():
        players.append(
            {
                "id": pid,
                "name": p.name,
                "net_worth": p.net_worth,
                "credits": p.credits,
                "planets": [
                    {"id": pl.id, "citadel_level": getattr(pl, "citadel_level", 0)}
                    for pl in universe.planets.values()
                    if pl.owner_id == pid
                ],
            }
        )
    planets = [
        {
            "id": pl.id,
            "owner_id": pl.owner_id,
            "citadel_level": getattr(pl, "citadel_level", 0),
        }
        for pl in universe.planets.values()
    ]
    return {"players": players, "planets": planets}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class HeadlessRunner:
    def __init__(
        self,
        *,
        seed: int = 42,
        universe_size: int = 1000,
        max_days: int = 10,
        num_agents: int = 2,
        agent_factory=None,
        out_dir: Path | None = None,
        gate: bool = True,
        verbose: bool = True,
        turns_per_day: int | None = None,
    ):
        self.turns_per_day_override = turns_per_day
        cfg_kwargs = {"seed": seed, "universe_size": universe_size, "max_days": max_days}
        if turns_per_day is not None:
            cfg_kwargs["turns_per_day"] = turns_per_day
        self.config = GameConfig(**cfg_kwargs)
        self.universe = generate_universe(self.config)
        self.num_agents = num_agents
        self.agent_factory = agent_factory or (
            lambda i, pid, name: HeuristicAgent(pid, name)
        )
        self.out_dir = out_dir
        self.gate = gate
        self.verbose = verbose

        self._log_lines: list[str] = []
        self._scorecard_lines: list[str] = []
        self._events_jsonl: list[str] = []

        # Scorecard bookkeeping (mirrors watch_match.main)
        self.arcs: dict[str, PlayerArc] = {}
        self.current_day = 1
        self._events_seen_seq = 0

    # -------- logging helpers --------

    def log(self, line: str) -> None:
        self._log_lines.append(line)
        if self.verbose:
            print(line, flush=True)

    def score(self, line: str) -> None:
        self._scorecard_lines.append(line)
        self.log(line)

    # -------- setup --------

    def build_agents(self) -> list[BaseAgent]:
        agents: list[BaseAgent] = []
        for i in range(self.num_agents):
            pid = f"P{i+1}"
            name = f"Agent-{i+1}"
            player = Player(id=pid, name=name, ship=Ship())
            if self.turns_per_day_override is not None:
                player.turns_per_day = self.turns_per_day_override
            self.universe.players[pid] = player
            self.universe.sectors[1].occupant_ids.append(pid)
            player.known_sectors.add(1)
            # Seed arc and starting net worth for day 1
            self.arcs[pid] = PlayerArc(name=name)
            self.arcs[pid].stats_for(1).nw_start = player.net_worth
            agents.append(self.agent_factory(i, pid, name))
        return agents

    # -------- event handling --------

    def drain_events(self) -> list[dict]:
        """Return all events emitted since the last call, as dicts."""
        new = [event_to_dict(e) for e in self.universe.events if e.seq > self._events_seen_seq]
        if new:
            self._events_seen_seq = new[-1]["seq"]
        return new

    def handle_events(self, events: list[dict]) -> None:
        state_players = {p["id"]: p for p in snapshot_state(self.universe)["players"]}
        for ev in events:
            self._events_jsonl.append(json.dumps(ev, separators=(",", ":")))
            actor = resolve_actor(ev, state_players)
            day = ev.get("day") or self.current_day
            if actor and actor in self.arcs:
                update_from_event(self.arcs[actor], day, ev)

    def close_day(self, day_no: int) -> None:
        """Finalise the day: set nw_end, emit per-player scorecards.

        Days outside the rubric (>5) only record nw_end for arc accounting
        but do not emit a scorecard header."""
        state = snapshot_state(self.universe)
        has_rubric = day_no in RUBRIC
        planet_level_by_owner: dict[str, int] = {}
        for pl in state["planets"]:
            owner = pl.get("owner_id")
            lvl = int(pl.get("citadel_level") or 0)
            if owner:
                planet_level_by_owner[owner] = max(planet_level_by_owner.get(owner, 0), lvl)

        if has_rubric:
            self.score("")
            self.score(f"======= Day {day_no} Scorecard =======")
        for p in state["players"]:
            pid = p["id"]
            if pid not in self.arcs:
                self.arcs[pid] = PlayerArc(name=p["name"])
            arc = self.arcs[pid]
            st = arc.stats_for(day_no)
            st.nw_end = int(p.get("net_worth") or 0)
            st.citadel_level_reached = max(
                st.citadel_level_reached, planet_level_by_owner.get(pid, 0)
            )
            if has_rubric:
                checks = evaluate(st, day_no)
                arc.days_scored += 1
                passed = sum(1 for _, ok, _ in checks if ok)
                if checks and passed >= len(checks) - 1:
                    arc.days_on_arc += 1
                for line in render_scorecard(p["name"], day_no, checks):
                    self.score(line)
            arc.stats_for(day_no + 1).nw_start = int(p.get("net_worth") or 0)

    # -------- main loop --------

    async def run(self) -> dict:
        agents = self.build_agents()
        self.log(f"=== headless match · seed={self.config.seed} · "
                 f"agents={self.num_agents} · max_days={self.config.max_days} ===")

        idx = 0
        # Cap total iterations generously; real exit is via is_finished() or
        # reaching max_days. Allow ~2000 actions per agent per day since some
        # actions (port trades) cost zero turns.
        max_steps = self.config.max_days * 2000 * self.num_agents + 1000
        steps = 0
        last_day = self.universe.day
        # Progress heartbeat so long-running (LLM) matches show liveness.
        heartbeat_every = 5  # steps
        t_start = time.time()

        # Two-layer day-length cap. Port trades cost zero turns so agents can
        # take many more actions than `turns_per_day` per day; we still need
        # bounded days.
        #   (a) turns-progress stall: if turns_today doesn't advance for
        #       `stuck_limit` iterations, force a tick.
        #   (b) hard per-day iteration cap: no day may take more than
        #       `max_iters_per_day` total actions.
        # Stall guards scale with day length so short LLM sanity matches
        # (turns_per_day=20) don't wait 400 failing actions before forcing
        # rollover. 6x per-agent per-day is enough headroom for zero-cost
        # verbs (scan, trade haggles, hails) while still cutting off genuine
        # stuck-LLM loops in reasonable wall time.
        stuck_limit = max(20, self.config.turns_per_day * self.num_agents // 2)
        stuck_counter = 0
        last_total_turns = 0
        max_iters_per_day = max(40, self.config.turns_per_day * self.num_agents * 6)
        day_iters = 0
        # Per-player consecutive-failure counter. If an agent issues N failing
        # actions in a row we force-WAIT one of their turns to unstick the
        # player without letting them spin forever at ~10s/call.
        fail_streak: dict[str, int] = {a.player_id: 0 for a in agents}
        fail_streak_limit = 4

        def total_turns_today() -> int:
            return sum(
                self.universe.players[a.player_id].turns_today for a in agents
            )

        def roll_day() -> None:
            nonlocal last_day, day_iters, stuck_counter, last_total_turns
            self.handle_events(self.drain_events())
            self.close_day(self.universe.day)
            tick_day(self.universe)
            self.handle_events(self.drain_events())
            last_day = self.universe.day
            day_iters = 0
            stuck_counter = 0
            last_total_turns = 0

        while (
            not is_finished(self.universe)
            and steps < max_steps
            and self.universe.day <= self.config.max_days
        ):
            steps += 1
            agent = agents[idx]
            player = self.universe.players[agent.player_id]

            if player.turns_today >= player.turns_per_day:
                if all(
                    self.universe.players[a.player_id].turns_today
                    >= self.universe.players[a.player_id].turns_per_day
                    for a in agents
                ):
                    roll_day()
                idx = (idx + 1) % len(agents)
                continue

            obs = build_observation(self.universe, agent.player_id)
            t_act = time.time()
            try:
                action = await agent.act(obs)
            except Exception as e:
                action = Action(kind=ActionKind.END_TURN, thought=f"agent error: {e}")
            act_dt = time.time() - t_act
            result = apply_action(self.universe, agent.player_id, action)
            self.handle_events(self.drain_events())

            # Track consecutive failures per-player so a flailing LLM doesn't
            # burn 10 minutes of wall time re-issuing the same invalid verb.
            action_kind = getattr(action.kind, "value", str(action.kind))
            if not result.ok:
                fail_streak[agent.player_id] = fail_streak.get(agent.player_id, 0) + 1
                # Surface failures to the progress stream immediately — crucial
                # for diagnosing "why is the LLM not making money?" without
                # waiting for the full events.jsonl dump at match end.
                self.log(
                    f"[fail] step={steps} {agent.player_id} {action_kind} "
                    f"-> {result.error} (streak={fail_streak[agent.player_id]})"
                )
                if fail_streak[agent.player_id] >= fail_streak_limit:
                    p = self.universe.players[agent.player_id]
                    forced_wait = Action(kind=ActionKind.WAIT)
                    wait_res = apply_action(self.universe, agent.player_id, forced_wait)
                    self.handle_events(self.drain_events())
                    self.log(
                        f"[unstick] step={steps} {agent.player_id} had "
                        f"{fail_streak_limit} consecutive failures; forced WAIT "
                        f"(ok={wait_res.ok}, turns={p.turns_today}/{p.turns_per_day})"
                    )
                    fail_streak[agent.player_id] = 0
            else:
                fail_streak[agent.player_id] = 0

            if steps % heartbeat_every == 0:
                elapsed = time.time() - t_start
                p = self.universe.players[agent.player_id]
                ok_tag = "ok" if result.ok else f"FAIL:{result.error}"
                self.log(
                    f"[progress] step={steps} day={self.universe.day} "
                    f"{agent.player_id}@sector{p.sector_id} "
                    f"credits={p.credits} turns={p.turns_today}/{p.turns_per_day} "
                    f"act={action_kind}({ok_tag}) "
                    f"dt={act_dt:.1f}s elapsed={elapsed:.0f}s"
                )

            # Incrementally checkpoint events / log every 25 steps so the
            # artifacts/<run>/events.jsonl is inspectable mid-match (helpful
            # for long LLM runs where the final dump might be an hour away).
            if steps % 25 == 0:
                self._write_artifacts(summary=None)

            day_iters += 1
            now_total = total_turns_today()
            if now_total == last_total_turns:
                stuck_counter += 1
            else:
                stuck_counter = 0
                last_total_turns = now_total

            if stuck_counter >= stuck_limit:
                self.log(
                    f"[stuck-day] day {self.universe.day}: no turn-progress "
                    f"in {stuck_limit} iterations, forcing tick"
                )
                roll_day()
            elif day_iters >= max_iters_per_day:
                self.log(
                    f"[day-cap] day {self.universe.day}: hit iteration cap "
                    f"{max_iters_per_day}, forcing tick"
                )
                roll_day()

            if self.universe.day != last_day:
                self.close_day(last_day)
                last_day = self.universe.day

            idx = (idx + 1) % len(agents)

        # Final close-out
        self.handle_events(self.drain_events())
        self.close_day(self.universe.day)

        # Arc report
        for line in render_arc_report(self.arcs, self.universe.day):
            self.score(line)

        for agent in agents:
            await agent.close()

        summary = self._build_summary(agents)
        self._write_artifacts(summary)

        return summary

    # -------- summary / artifacts --------

    def _build_summary(self, agents: list[BaseAgent]) -> dict:
        players = []
        for agent in agents:
            p = self.universe.players[agent.player_id]
            arc = self.arcs.get(agent.player_id)
            players.append({
                "id": agent.player_id,
                "name": p.name,
                "alive": p.alive,
                "credits": p.credits,
                "net_worth": p.net_worth,
                "sector_id": p.sector_id,
                "ship_class": p.ship.ship_class.value,
                "fighters": p.ship.fighters,
                "days_on_arc": arc.days_on_arc if arc else 0,
                "days_scored": arc.days_scored if arc else 0,
            })
        return {
            "seed": self.config.seed,
            "universe_size": self.config.universe_size,
            "max_days": self.config.max_days,
            "final_day": self.universe.day,
            "finished": self.universe.finished,
            "winner_id": self.universe.winner_id,
            "win_reason": self.universe.win_reason,
            "num_events": self.universe.seq,
            "players": players,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def _write_artifacts(self, summary: dict | None = None) -> None:
        if self.out_dir is None:
            return
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / "events.jsonl").write_text(
            "\n".join(self._events_jsonl) + ("\n" if self._events_jsonl else ""),
            encoding="utf-8",
        )
        (self.out_dir / "scorecards.txt").write_text(
            "\n".join(self._scorecard_lines) + "\n", encoding="utf-8"
        )
        if summary is not None:
            (self.out_dir / "summary.json").write_text(
                json.dumps(summary, indent=2, default=_json_default), encoding="utf-8"
            )
        (self.out_dir / "run.log").write_text(
            "\n".join(self._log_lines) + "\n", encoding="utf-8"
        )


def _json_default(o):
    if is_dataclass(o):
        return asdict(o)
    if hasattr(o, "model_dump"):
        return o.model_dump(mode="json")
    return str(o)


# ---------------------------------------------------------------------------
# Gate: has the match met a minimum rubric bar?
# ---------------------------------------------------------------------------


def gate_passed(summary: dict, min_days_on_arc: int = 1) -> bool:
    """The bar: at least one player has ≥ min_days_on_arc days on-arc.

    The rubric only scores days 1-5. If the match ran fewer days than that,
    we accept any player with ≥ (final_day - 1) on-arc, i.e. all scored days
    passed except possibly the first.
    """
    final_day = summary.get("final_day", 0)
    if final_day < 1:
        return False
    required = min(min_days_on_arc, max(1, final_day - 1))
    return any(p.get("days_on_arc", 0) >= required for p in summary.get("players", []))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s).strip("-")


def _make_out_dir(suffix: str) -> Path:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    name = f"run-{ts}" + (f"-{_slug(suffix)}" if suffix else "")
    return ROOT / "artifacts" / name


def _build_agent_factory(kind: str):
    kind = (kind or "heuristic").lower()
    if kind == "heuristic":
        return lambda i, pid, name: HeuristicAgent(pid, name)
    if kind == "llm":
        from tw2k.agents import LLMAgent  # lazy import
        return lambda i, pid, name: LLMAgent(pid, name)
    raise ValueError(f"unknown agent kind: {kind}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--universe-size", type=int, default=1000)
    ap.add_argument("--days", type=int, default=10, help="Max days (time victory cap).")
    ap.add_argument("--agents", type=int, default=2, help="Number of agents.")
    ap.add_argument("--kind", default="heuristic", choices=["heuristic", "llm"])
    ap.add_argument("--suffix", default="", help="Suffix added to artifact folder name.")
    ap.add_argument("--no-artifacts", action="store_true", help="Skip writing artifacts.")
    ap.add_argument("--no-gate", action="store_true", help="Don't exit 1 on rubric miss.")
    ap.add_argument("--quiet", action="store_true", help="Suppress live stdout.")
    ap.add_argument(
        "--turns-per-day",
        type=int,
        default=None,
        help=(
            "Override the per-player turns_per_day. Lower values (e.g. 40) make "
            "LLM sanity matches finish in minutes instead of hours by forcing "
            "end-of-day rollover after fewer actions."
        ),
    )
    args = ap.parse_args(argv)

    try:
        out_dir = None if args.no_artifacts else _make_out_dir(args.suffix or args.kind)
        runner = HeadlessRunner(
            seed=args.seed,
            universe_size=args.universe_size,
            max_days=args.days,
            num_agents=args.agents,
            agent_factory=_build_agent_factory(args.kind),
            out_dir=out_dir,
            gate=not args.no_gate,
            verbose=not args.quiet,
            turns_per_day=args.turns_per_day,
        )
        t0 = time.time()
        summary = asyncio.run(runner.run())
        elapsed = time.time() - t0
        runner.log(f"=== match done in {elapsed:.1f}s · "
                   f"day={summary['final_day']} · events={summary['num_events']} ===")
        if out_dir is not None:
            runner.log(f"=== artifacts: {out_dir} ===")

        if args.no_gate:
            return 0
        return 0 if gate_passed(summary) else 1
    except Exception:
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
