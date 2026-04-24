"""Match runner — owns the game loop and streams events to subscribers.

Also owns the per-match save writer (Phase 6). Every live match persists:

    saves/<run-id>/meta.json     — seed, config, agent specs, start time
    saves/<run-id>/actions.jsonl — every submitted Action + day_tick markers
    saves/<run-id>/events.jsonl  — every emitted Event (analysis/debug)

The actions log is authoritative for `tw2k replay` — because the engine is
deterministic given (seed, action sequence), re-executing actions.jsonl
on a fresh Universe reconstructs state bit-for-bit. The events log is
kept alongside for offline analysis and because it's free once we're
flushing events through the broadcaster anyway.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..agents.base import BaseAgent
from ..engine import (
    Action,
    ActionKind,
    EventKind,
    GameConfig,
    Universe,
    actor_kind_override,
    apply_action,
    build_observation,
    generate_universe,
    is_finished,
    tick_day,
)
from ..engine.llm_pricing import MatchCostTracker
from ..engine.match_metrics import build_match_metrics_payload
from ..engine.models import Player, Ship
from .broadcaster import Broadcaster


def _default_saves_root() -> Path:
    """Where `tw2k serve` drops saves/<run-id>/ dirs.

    Defaults to `<repo-root>/saves` so `tw2k replay saves/<id>` just works
    from the project checkout. Can be overridden with the TW2K_SAVES_DIR
    env var (absolute or relative; relative resolves against CWD).
    """
    import os

    override = os.environ.get("TW2K_SAVES_DIR")
    if override:
        return Path(override).expanduser().resolve()
    # Repo-root heuristic: src/tw2k/server/runner.py → up 4 = repo root.
    return Path(__file__).resolve().parents[3] / "saves"

# Distinct colors for players on the map
AGENT_COLORS = [
    "#6ee7ff",  # cyan
    "#ff9f6e",  # orange
    "#e2ff6e",  # lime
    "#ff6ee8",  # magenta
    "#6effa8",  # mint
    "#ffee6e",  # yellow
    "#a56eff",  # purple
    "#ff6e6e",  # red
]


def _is_day_done(player) -> bool:
    """Player has no meaningful actions left for the day.

    Classic TW2002 deducts 3 turns per warp for most ships. If a player has
    `turns_remaining < ship.turns_per_warp` AND can't afford a trade (cost=3),
    they can only wait/scan — treat as day-done so the server doesn't burn
    LLM calls on an agent that can't usefully move. This is the safety net
    that prevents an infinite out-of-turns loop (bug: D1·56..D1·91 flooding).
    """
    from ..engine import constants as K

    remaining = player.turns_per_day - player.turns_today
    if remaining <= 0:
        return True
    ship = getattr(player, "ship", None)
    warp_cost = K.TURN_COST["warp"]
    if ship is not None:
        spec = K.SHIP_SPECS.get(ship.ship_class.value)
        if spec and "turns_per_warp" in spec:
            warp_cost = int(spec["turns_per_warp"])
    trade_cost = K.TURN_COST["trade"]
    # If the agent can't warp AND can't trade, everything it could do is a
    # stall (wait/scan/transmit). Shut the day down so we tick forward.
    return remaining < warp_cost and remaining < trade_cost


@dataclass
class AgentSpec:
    player_id: str
    name: str
    kind: str  # "llm" | "heuristic" | "human"
    provider: str | None = None
    model: str | None = None


@dataclass
class MatchSpec:
    config: GameConfig
    agents: list[AgentSpec]
    action_delay_s: float = 0.6
    paused: bool = False
    # Per-turn deadline for HUMAN slots. None (default) = wait forever;
    # a float = force-submit a WAIT action on behalf of the human if
    # nothing arrives in that many seconds. Added Phase H1 so the match
    # doesn't grind to a permanent halt if the human closes the tab or
    # steps away. AI slots are unaffected — they already have
    # GameConfig.llm_think_cap_s as their provider-call budget.
    human_deadline_s: float | None = None


@dataclass
class RunnerState:
    universe: Universe | None = None
    agents: list[BaseAgent] = field(default_factory=list)
    current_player_idx: int = 0
    started_at: float = 0.0
    status: str = "idle"  # idle, running, paused, finished, error, replaying
    last_error: str = ""
    speed_multiplier: float = 1.0
    # Save sink — set by MatchRunner.start() for live matches. Unset (None)
    # for ReplayRunner and for any future headless runner that doesn't want
    # a save trail. The replay CLI uses this same directory layout in reverse.
    save_dir: Path | None = None
    run_id: str = ""
    # Per-player LLM cost tracker. One MatchCostTracker per match,
    # accumulated across every `agent.act()` call that returns usage.
    # Surfaced live via /api/cost, frozen into the final match_metrics
    # event, and re-derivable offline via scripts/cost_report.py.
    cost_tracker: MatchCostTracker = field(default_factory=MatchCostTracker)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class MatchRunner:
    """Owns the game loop. Safe to start/stop/pause from the server app."""

    # How many history samples to keep per player (Phase 4). Sampled once per
    # round-robin pass through all agents, so ~2 actions per sample with 2
    # agents; 240 samples covers the last several in-game days.
    HISTORY_MAX_SAMPLES = 240

    def __init__(self, broadcaster: Broadcaster, saves_root: Path | None = None):
        self.broadcaster = broadcaster
        self.state = RunnerState()
        self._spec: MatchSpec | None = None
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._pause = asyncio.Event()
        self._pause.set()  # starts un-paused
        # Phase 4: per-player ring buffer of (seq, day, credits, net_worth,
        # fighters, experience, alignment, sector_id). Populated by
        # _record_history_sample() on every round-robin rollover.
        self._history: dict[str, deque] = {}
        # Phase 6: save sink wiring. `saves_root` is the parent dir; each
        # match gets its own run-id subdir written there. `_actions_fp`
        # and `_events_fp` are opened/closed in start()/stop() respectively.
        self._saves_root: Path = saves_root or _default_saves_root()
        self._actions_fp = None  # type: ignore[assignment]
        self._events_fp = None  # type: ignore[assignment]

    # ---------------- lifecycle ---------------- #

    async def start(self, spec: MatchSpec) -> None:
        if self._task is not None and not self._task.done():
            await self.stop()
        self._spec = spec
        self._stop.clear()
        self._pause.set()
        self.state = RunnerState()
        self._last_published_seq = 0
        self._history = {}
        self.broadcaster.reset_history()
        self._open_save_sink(spec)
        self._task = asyncio.create_task(self._run(), name="tw2k-match")

    async def stop(self) -> None:
        if self._task is None:
            self._close_save_sink()
            return
        self._stop.set()
        self._pause.set()
        try:
            await asyncio.wait_for(self._task, timeout=5)
        except TimeoutError:
            self._task.cancel()
        # Close agents
        for agent in self.state.agents:
            try:
                await agent.close()
            except Exception:
                pass
        self._task = None
        self._close_save_sink()

    # ---------------- save sink (Phase 6) ---------------- #

    def _open_save_sink(self, spec: MatchSpec) -> None:
        """Create saves/<run-id>/ and open append-mode writers.

        Run-id is `YYYYMMDD-HHMMSS-seed<N>` which sorts well and encodes
        both when and what. Meta.json is written eagerly so a crash before
        any action still leaves enough to re-open the run manifest.
        """
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_id = f"{ts}-seed{spec.config.seed}"
        save_dir = self._saves_root / run_id
        try:
            save_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            # Disk full / permission denied shouldn't kill the match.
            # Fall through to no-save mode.
            self.state.last_error = f"save dir create failed: {exc}"
            return
        meta = {
            "run_id": run_id,
            "started_at": time.time(),
            "started_at_iso": datetime.now().isoformat(timespec="seconds"),
            "config": spec.config.model_dump(),
            "agents": [
                {
                    "player_id": a.player_id,
                    "name": a.name,
                    "kind": a.kind,
                    "provider": a.provider,
                    "model": a.model,
                }
                for a in spec.agents
            ],
            "action_delay_s": spec.action_delay_s,
            "schema_version": 1,
        }
        try:
            (save_dir / "meta.json").write_text(
                json.dumps(meta, indent=2, default=str), encoding="utf-8"
            )
            self._actions_fp = (save_dir / "actions.jsonl").open(
                "a", encoding="utf-8", buffering=1  # line-buffered
            )
            self._events_fp = (save_dir / "events.jsonl").open(
                "a", encoding="utf-8", buffering=1
            )
            self.state.save_dir = save_dir
            self.state.run_id = run_id
        except OSError as exc:
            self.state.last_error = f"save file open failed: {exc}"
            self._close_save_sink()

    def _close_save_sink(self) -> None:
        for fp in (self._actions_fp, self._events_fp):
            if fp is not None:
                try:
                    fp.flush()
                    fp.close()
                except OSError:
                    pass
        self._actions_fp = None
        self._events_fp = None

    def _record_action(self, player_id: str, action, ok: bool, error: str) -> None:
        """Append one line to actions.jsonl. No-op if save sink is absent."""
        if self._actions_fp is None:
            return
        u = self.state.universe
        rec = {
            "kind": "action",
            "t": time.time() - self.state.started_at,
            "day": u.day if u is not None else 0,
            "tick": u.tick if u is not None else 0,
            "seq_before": getattr(self, "_last_published_seq", 0),
            "player_id": player_id,
            "action": action.model_dump(mode="json"),
            "ok": ok,
            "error": error,
        }
        try:
            self._actions_fp.write(json.dumps(rec, default=str) + "\n")
        except OSError:
            pass

    def _record_llm_usage(self, agent: BaseAgent, sector_id: int, player_name: str) -> None:
        """Emit an LLM_USAGE event + update the cost tracker after agent.act().

        Looks at ``agent._last_usage`` (populated by `LLMAgent._call_*`).
        Heuristic / human agents never set it — we silently skip them.
        Each successful LLM call contributes one event + one tally
        bump so the spectator UI, /api/cost, and the final
        match_metrics payload stay in sync.
        """
        universe = self.state.universe
        if universe is None:
            return
        usage = getattr(agent, "_last_usage", None)
        if usage is None:
            return
        provider = str(getattr(agent, "provider", "") or "")
        model = str(getattr(agent, "model", "") or "")
        tracker = self.state.cost_tracker
        inc_cost, tally = tracker.record_call(
            agent.player_id,
            provider=provider,
            model=model,
            input_tokens=usage.input_tokens,
            cached_input_tokens=usage.cached_input_tokens,
            cache_write_tokens=usage.cache_write_tokens,
            output_tokens=usage.output_tokens,
        )
        universe.emit(
            EventKind.LLM_USAGE,
            actor_id=agent.player_id,
            sector_id=sector_id,
            payload={
                "provider": provider,
                "model": model,
                "usage": usage.to_payload(),
                "cost_usd": round(float(inc_cost), 6),
                "running_total_usd": round(float(tally.cost_usd), 6),
                "running_calls": int(tally.calls),
                "price_is_fallback": bool(tally.price_is_fallback),
            },
            summary=(
                f"[{player_name}] {provider}/{model} "
                f"+{usage.input_tokens}in/{usage.output_tokens}out "
                f"(cache:{usage.cached_input_tokens}) ${inc_cost:.4f} "
                f"run=${tally.cost_usd:.3f}"
            ),
        )
        # Don't clear _last_usage here — LLMAgent.act() resets it on the
        # next turn, and leaving it set lets late observers (debug probes)
        # inspect the last call.

    def _record_agent_fallback(
        self, agent: BaseAgent, sector_id: int, player_name: str
    ) -> None:
        """Emit a one-shot AGENT_FALLBACK event when an LLMAgent gives up.

        The flag is set by `LLMAgent._mark_fallback()` on the turn where
        consecutive-failure count hits 5. We consume-and-clear it here so
        the event fires exactly once per fallback transition. Agents that
        aren't LLMAgent (heuristic, human) lack the method and are skipped.
        """
        universe = self.state.universe
        if universe is None:
            return
        consume = getattr(agent, "consume_fallback_reason", None)
        if not callable(consume):
            return
        reason = consume()
        if reason is None:
            return
        provider = str(getattr(agent, "provider", "") or "")
        model = str(getattr(agent, "model", "") or "")
        universe.emit(
            EventKind.AGENT_FALLBACK,
            actor_id=agent.player_id,
            sector_id=sector_id,
            payload={
                "provider": provider,
                "model": model,
                "reason": reason,
            },
            summary=(
                f"*** [{player_name}] {provider}/{model} fell back to heuristic "
                f"(reason: {reason}) ***"
            ),
        )

    def _record_day_tick(self) -> None:
        """Append a day_tick marker so replay knows when to call tick_day."""
        if self._actions_fp is None:
            return
        u = self.state.universe
        rec = {
            "kind": "day_tick",
            "t": time.time() - self.state.started_at,
            "day": u.day if u is not None else 0,
            "tick": u.tick if u is not None else 0,
        }
        try:
            self._actions_fp.write(json.dumps(rec, default=str) + "\n")
        except OSError:
            pass

    def pause(self) -> None:
        self._pause.clear()
        self.state.status = "paused"

    def resume(self) -> None:
        self._pause.set()
        if self.state.status == "paused":
            self.state.status = "running"

    def set_speed(self, multiplier: float) -> None:
        self.state.speed_multiplier = max(0.1, min(10.0, multiplier))

    # ---------------- main loop ---------------- #

    async def _run(self) -> None:
        assert self._spec is not None
        try:
            self.state.status = "running"
            self.state.started_at = time.time()

            universe = generate_universe(self._spec.config)
            self.state.universe = universe

            agents = self._build_agents(self._spec, universe)
            self.state.agents = agents

            await self._emit_init()

            # Warm up any LLM agents in parallel BEFORE the game loop starts.
            # For large local models (e.g. qwen3.5:122b at 81GB) this can take
            # several minutes on cold load; we surface it as system events so
            # spectators see what's happening.
            await self._warmup_llm_agents(agents)

            universe.emit(
                EventKind.GAME_START,
                payload={
                    "players": [
                        {"id": a.player_id, "name": a.name, "kind": a.kind}
                        for a in agents
                    ],
                    "config": universe.config.model_dump(),
                },
                summary=f"Match begins — {len(agents)} players in a {universe.config.universe_size}-sector galaxy.",
            )
            await self._flush_events()

            # Turn loop: round-robin agents, day advances when all have exhausted turns.
            while not is_finished(universe) and not self._stop.is_set():
                await self._pause.wait()
                if self._stop.is_set():
                    break

                agent = agents[self.state.current_player_idx]
                player = universe.players[agent.player_id]

                if not player.alive:
                    self.state.current_player_idx = (self.state.current_player_idx + 1) % len(agents)
                    continue

                if _is_day_done(player):
                    # This player is done for the day. Advance to next; if all are done, tick day.
                    all_done = all(
                        _is_day_done(universe.players[a.player_id])
                        or not universe.players[a.player_id].alive
                        for a in agents
                    )
                    if all_done:
                        tick_day(universe)
                        self._record_day_tick()
                        await self._flush_events()
                        # brief pause between days for spectators
                        await self._sleep_scaled(1.0)
                    self.state.current_player_idx = (self.state.current_player_idx + 1) % len(agents)
                    continue

                try:
                    obs = build_observation(universe, agent.player_id)
                    # Human slots: emit HUMAN_TURN_START so the /play UI
                    # knows "it's your move" before the scheduler blocks
                    # inside agent.act(). The scheduler main loop stays
                    # serial so all other players naturally pause. A
                    # run-level stop (runner.stop) cancels the enclosing
                    # task and CancelledError propagates out of queue.get
                    # cleanly — no sentinel needed.
                    is_human = getattr(agent, "kind", None) == "human"
                    if is_human:
                        universe.emit(
                            EventKind.HUMAN_TURN_START,
                            actor_id=agent.player_id,
                            sector_id=player.sector_id,
                            payload={
                                "turns_today": player.turns_today,
                                "turns_per_day": player.turns_per_day,
                                "turns_remaining": player.turns_per_day - player.turns_today,
                                "deadline_s": self._spec.human_deadline_s,
                            },
                            summary=f"[{player.name}] human turn — awaiting input.",
                        )
                        await self._flush_events()
                    # Phase H1: honor --human-deadline-s if set, so a
                    # match with a human slot doesn't hang forever when
                    # the player steps away. On timeout we synthesize a
                    # WAIT action and emit an AGENT_THOUGHT event so the
                    # replay / spectator can tell "this was an idle
                    # auto-WAIT" from "this was a human-chosen WAIT".
                    deadline = self._spec.human_deadline_s if is_human else None
                    if deadline is not None and deadline > 0:
                        try:
                            action = await asyncio.wait_for(
                                agent.act(obs), timeout=deadline
                            )
                        except TimeoutError:
                            action = Action(
                                kind=ActionKind.WAIT,
                                thought=(
                                    f"auto-WAIT: no human input within "
                                    f"{deadline:.0f}s"
                                ),
                            )
                            universe.emit(
                                EventKind.AGENT_THOUGHT,
                                actor_id=agent.player_id,
                                sector_id=player.sector_id,
                                payload={
                                    "thought": (
                                        f"No action from {agent.player_id} in "
                                        f"{deadline:.0f}s — auto-WAIT."
                                    ),
                                    "auto_wait": True,
                                },
                                summary=f"[{player.name}] idle — auto-WAIT.",
                            )
                    else:
                        action = await agent.act(obs)
                except asyncio.CancelledError:
                    # Clean shutdown (runner.stop). Don't emit an error —
                    # just exit the loop.
                    raise
                except Exception as exc:
                    universe.emit(
                        EventKind.AGENT_ERROR,
                        actor_id=agent.player_id,
                        sector_id=player.sector_id,
                        payload={"error": str(exc)},
                        summary=f"[{player.name}] agent error: {exc}",
                    )
                    await self._flush_events()
                    self.state.current_player_idx = (self.state.current_player_idx + 1) % len(agents)
                    await self._sleep_scaled(self._spec.action_delay_s)
                    continue

                # Capture per-call LLM usage + cost if the agent exposes
                # it. LLMAgent populates ``_last_usage`` in each _call_*
                # path (anthropic/openai/xai/deepseek/custom/cursor).
                # Heuristic / human agents never set it, so this block
                # is a no-op for them. We emit BEFORE apply_action so
                # the usage event precedes the resulting game-state
                # events (warps, trades, ...) in the feed — makes replay
                # easy to audit turn-by-turn.
                self._record_llm_usage(agent, player.sector_id, player.name)

                # If the LLMAgent just switched to its heuristic fallback
                # (5 consecutive failures), surface a one-shot event so the
                # spectator / operator sees which slot went dark and why.
                # Otherwise the heuristic's coherent-looking thoughts make
                # the failure invisible mid-match.
                self._record_agent_fallback(agent, player.sector_id, player.name)

                # If the submitted Action carries an actor_kind override
                # (e.g. the copilot dispatched this on behalf of a human),
                # scope it onto the contextvar Universe.emit checks so every
                # event emitted during apply_action inherits the tag. Keeps
                # replay / spectator UI honest about who actually pulled
                # the trigger. Default None means we use the player's
                # agent_kind (unchanged behaviour for heuristic / llm /
                # manual-human submissions).
                override = getattr(action, "actor_kind", None)
                if override:
                    with actor_kind_override(override):
                        result = apply_action(universe, agent.player_id, action)
                else:
                    result = apply_action(universe, agent.player_id, action)
                # Record the action (success or failure) to actions.jsonl so
                # replay can re-execute the exact same submission sequence,
                # including invalid ones the engine rejected. Invalid actions
                # mutate alignment / trigger FED_RESPONSE on replay, so we
                # MUST include them to stay bit-for-bit faithful.
                self._record_action(agent.player_id, action, result.ok, result.error or "")

                # Phase D.2 — track LLM-timeout WAITs so the NEXT observation
                # can nudge the agent to re-read its scratchpad. A timeout
                # silently wastes a tick and often breaks a multi-step plan
                # (observed: day-1 "create corp THEN buy ship" sequences
                # where the timeout landed between steps 1 and 2). See
                # observation._action_hint for the hint rendering.
                thought_text = getattr(action, "thought", "") or ""
                is_timeout_wait = (
                    action.kind == ActionKind.WAIT
                    and isinstance(thought_text, str)
                    and thought_text.startswith("[LLM timeout")
                )
                player.last_action_was_timeout = bool(is_timeout_wait)
                # Match 13 — track consecutive timeouts per-player so
                # build_observation can shrink the observation payload
                # once the model is demonstrably struggling. Reset on
                # any non-timeout action (including non-LLM heuristics).
                if is_timeout_wait:
                    player.recent_timeouts = int(
                        getattr(player, "recent_timeouts", 0) or 0
                    ) + 1
                else:
                    player.recent_timeouts = 0
                if not result.ok:
                    # Avoid duplicating detailed failure events. The engine already
                    # emits TRADE_FAILED for bad trades and WARP_BLOCKED for bad
                    # warps; emitting AGENT_ERROR too would double-spam the feed.
                    handler_already_explained = False
                    for seq in result.event_seqs:
                        ev = next((e for e in universe.events if e.seq == seq), None)
                        if ev is None:
                            continue
                        if ev.kind in (EventKind.TRADE_FAILED, EventKind.WARP_BLOCKED, EventKind.FED_RESPONSE):
                            handler_already_explained = True
                            break
                    if not handler_already_explained:
                        universe.emit(
                            EventKind.AGENT_ERROR,
                            actor_id=agent.player_id,
                            sector_id=player.sector_id,
                            payload={"error": result.error, "action": action.model_dump()},
                            summary=f"[{player.name}] invalid action: {result.error}",
                        )

                # WAIT-loop guard: if an agent WAITs several times in a row while it
                # still has turns, skip the rest of its day so we don't flood the feed.
                waits = getattr(self, "_wait_streak", {})
                if action.kind == ActionKind.WAIT and result.ok:
                    waits[agent.player_id] = waits.get(agent.player_id, 0) + 1
                else:
                    waits[agent.player_id] = 0
                self._wait_streak = waits
                if waits.get(agent.player_id, 0) >= 4:
                    remaining = player.turns_per_day - player.turns_today
                    if remaining > 0:
                        player.turns_today = player.turns_per_day
                        # M2-7 fix: drop any leading WAIT actions from a
                        # HumanAgent's queue so queued productive actions
                        # (scan, warp, attack, build_citadel, ...) don't
                        # sit behind a wait streak and get re-triggered
                        # by this same guard tomorrow, stalling for days.
                        flushed = 0
                        drop_fn = getattr(agent, "drop_leading_waits", None)
                        if callable(drop_fn):
                            try:
                                flushed = int(drop_fn())
                            except Exception:
                                flushed = 0
                        thought = (
                            f"Standing down for the day ({remaining} turns skipped)."
                        )
                        summary = (
                            f"{player.name} ends the day early ({remaining} turns skipped)."
                        )
                        if flushed:
                            thought += f" Flushed {flushed} queued WAIT(s)."
                            summary += f" flushed {flushed} queued WAIT(s)."
                        universe.emit(
                            EventKind.AGENT_THOUGHT,
                            actor_id=agent.player_id,
                            sector_id=player.sector_id,
                            payload={
                                "thought": thought,
                                "turns_skipped": remaining,
                                "waits_flushed": flushed,
                            },
                            summary=summary,
                        )
                        waits[agent.player_id] = 0

                # OUT-OF-TURNS streak guard: if the agent repeatedly submits
                # actions that cost more turns than it has left, force-end its
                # day. Without this the server would loop forever asking Grok
                # to try again, burning LLM budget and flooding the feed
                # (observed bug: 36 straight "out of turns" errors on one day).
                oot_streak = getattr(self, "_oot_streak", {})
                failed_oot = (
                    not result.ok
                    and isinstance(result.error, str)
                    and "out of turns" in result.error.lower()
                )
                if failed_oot:
                    oot_streak[agent.player_id] = oot_streak.get(agent.player_id, 0) + 1
                else:
                    oot_streak[agent.player_id] = 0
                self._oot_streak = oot_streak
                if oot_streak.get(agent.player_id, 0) >= 2:
                    remaining = player.turns_per_day - player.turns_today
                    if remaining > 0:
                        player.turns_today = player.turns_per_day
                        universe.emit(
                            EventKind.AGENT_THOUGHT,
                            actor_id=agent.player_id,
                            sector_id=player.sector_id,
                            payload={
                                "thought": (
                                    f"Out of turns ({remaining} left, but needed more) — "
                                    f"ending day to avoid stall."
                                )
                            },
                            summary=f"{player.name} ends the day (insufficient turns for next action).",
                        )
                    oot_streak[agent.player_id] = 0

                await self._flush_events()
                self.state.current_player_idx = (self.state.current_player_idx + 1) % len(agents)
                # Sample history once per full round-robin pass.
                if self.state.current_player_idx == 0:
                    self._record_history_sample()
                await self._sleep_scaled(self._spec.action_delay_s)

            u = self.state.universe
            if u is not None and u.events:
                payload = build_match_metrics_payload(
                    u.events,
                    winner_id=u.winner_id,
                    win_reason=u.win_reason or "",
                )
                u.emit(
                    EventKind.MATCH_METRICS,
                    payload=payload,
                    summary=(
                        f"Match metrics — {payload['event_count']} events, "
                        f"{payload['llm_health']['parse_error_thoughts']} parse errors, "
                        f"hint_level={payload['hint_level']!r}"
                    ),
                )
                await self._flush_events()

            self.state.status = "finished"
        except Exception as exc:
            import traceback

            self.state.status = "error"
            self.state.last_error = f"{exc}\n{traceback.format_exc()}"
            await self.broadcaster.publish(
                {"type": "error", "message": self.state.last_error}
            )
        finally:
            for agent in self.state.agents:
                try:
                    await agent.close()
                except Exception:
                    pass

    # ---------------- helpers ---------------- #

    def _build_agents(self, spec: MatchSpec, universe: Universe) -> list[BaseAgent]:
        from ..agents import HeuristicAgent, LLMAgent
        from ..engine import constants as K

        # Distribute starting sectors across FedSpace so agents don't mirror each
        # other in the opening. Sector 1 (StarDock) is the canonical start; the
        # rest of FedSpace (2..10) sees Federal ports at ~60% spawn rate and is
        # safe from PvP. If we run out of FedSpace slots (>=10 agents) we cycle.
        # Optional: `GameConfig.all_start_stardock` places everyone at sector 1
        # so StarDock verbs are legal on turn 1 for every slot.
        fed_sectors = sorted(K.FEDSPACE_SECTORS)
        start_order = [fed_sectors[0]] + [s for s in fed_sectors if s != fed_sectors[0]]

        agents: list[BaseAgent] = []
        for i, ag in enumerate(spec.agents):
            color = AGENT_COLORS[i % len(AGENT_COLORS)]
            if bool(getattr(spec.config, "all_start_stardock", False)):
                start_sid = K.STARDOCK_SECTOR
            else:
                start_sid = start_order[i % len(start_order)]
            # Tiny deterministic loadout variance per player slot so two
            # otherwise-identical LLMs don't produce bit-for-bit identical plays.
            credit_skew = (i * 317) % 2001 - 1000  # ±1000 cr
            ship = Ship()
            # Respect the per-match starting_credits override from GameConfig
            # so `tw2k serve --starting-credits 75000` actually changes the
            # opening bankroll. Defaults to the canonical K.STARTING_CREDITS.
            base_credits = getattr(spec.config, "starting_credits", K.STARTING_CREDITS)
            # Likewise honor the per-match turns_per_day override. Without this,
            # `--turns-per-day 80` silently had no effect because Player() fell
            # back to K.STARTING_TURNS_PER_DAY = 1000, which meant day 1 never
            # actually ended in watchable sanity runs.
            base_tpd = getattr(spec.config, "turns_per_day", K.STARTING_TURNS_PER_DAY)
            player = Player(
                id=ag.player_id,
                name=ag.name,
                credits=base_credits + credit_skew,
                turns_per_day=base_tpd,
                ship=ship,
                sector_id=start_sid,
                agent_kind=ag.kind,
                color=color,
            )
            universe.players[ag.player_id] = player
            universe.sectors[start_sid].occupant_ids.append(ag.player_id)
            # Agents start knowing their immediate neighborhood (current sector
            # + adjacent warps and any ports there), not just "sector 1". This
            # removes the awkward "scan FedSpace first" opening move.
            player.known_sectors.add(start_sid)
            sector = universe.sectors[start_sid]
            # Seed the warp graph for the start sector so the LLM has
            # navigational memory from turn 1 without having to scan.
            player.known_warps[start_sid] = list(sector.warps)
            if sector.port is not None:
                player.known_ports[start_sid] = {
                    "class": sector.port.code,
                    "stock": {
                        c.value: {"current": s.current, "max": s.maximum}
                        for c, s in sector.port.stock.items()
                    },
                    "last_seen_day": universe.day,
                }
            for wid in sector.warps:
                player.known_sectors.add(wid)
                w = universe.sectors[wid]
                if w.port is not None:
                    player.known_ports[wid] = {
                        "class": w.port.code,
                        "stock": {
                            c.value: {"current": s.current, "max": s.maximum}
                            for c, s in w.port.stock.items()
                        },
                        "last_seen_day": universe.day,
                    }

            if ag.kind == "llm":
                agents.append(
                    LLMAgent(
                        player_id=ag.player_id,
                        name=ag.name,
                        provider=ag.provider,
                        model=ag.model,
                        think_cap_s=universe.config.llm_think_cap_s,
                    )
                )
            elif ag.kind == "human":
                from ..agents.human import HumanAgent

                agents.append(HumanAgent(player_id=ag.player_id, name=ag.name))
            else:
                agents.append(HeuristicAgent(player_id=ag.player_id, name=ag.name))
        return agents

    async def _warmup_llm_agents(self, agents: list[BaseAgent]) -> None:
        """Fire off a warmup call to every LLM agent in parallel so the backing
        model is resident before the first real turn. Publishes status events.
        """
        from ..agents.llm import LLMAgent

        llm_agents = [a for a in agents if isinstance(a, LLMAgent) and a.provider != "none"]
        if not llm_agents:
            return

        # Dedupe by (provider, model) — no need to warm the same model twice if
        # multiple agents share it.
        seen: dict[tuple[str, str], LLMAgent] = {}
        for a in llm_agents:
            seen.setdefault((a.provider, a.model), a)

        u = self.state.universe
        assert u is not None

        for (prov, mdl), agent in seen.items():
            u.emit(
                EventKind.AGENT_THOUGHT,
                actor_id=agent.player_id,
                sector_id=1,
                payload={"thought": f"Warming up {prov}/{mdl} — this can take a few minutes for large local models."},
                summary=f"Loading model {mdl} ({prov})… please wait.",
            )
        await self._flush_events()

        async def _warm(agent: LLMAgent) -> tuple[str, bool, str, float]:
            t0 = time.time()
            ok, msg = await agent.warmup()
            return (agent.model, ok, msg, time.time() - t0)

        # Run all warmups in parallel; Ollama will serialize same-model calls internally.
        results = await asyncio.gather(*[_warm(a) for a in seen.values()], return_exceptions=True)

        for res in results:
            if isinstance(res, Exception):
                u.emit(
                    EventKind.AGENT_ERROR,
                    payload={"error": str(res)},
                    summary=f"Warmup crashed: {type(res).__name__}: {res}",
                )
                continue
            model, ok, msg, elapsed = res  # type: ignore[misc]
            if ok:
                u.emit(
                    EventKind.AGENT_THOUGHT,
                    sector_id=1,
                    payload={"thought": f"Model {model} ready in {elapsed:.1f}s — {msg}"},
                    summary=f"Model {model} ready ({elapsed:.1f}s).",
                )
            else:
                u.emit(
                    EventKind.AGENT_ERROR,
                    payload={"error": msg, "model": model, "elapsed": elapsed},
                    summary=f"Model {model} warmup FAILED after {elapsed:.1f}s: {msg}",
                )

        # Mark non-representative LLMAgents (ones that share a model with a warmed
        # agent) as warm too, so they skip the extra-long first-call timeout.
        warmed_models: set[str] = set()
        for res in results:
            if isinstance(res, Exception):
                continue
            model, ok, _msg, _elapsed = res  # type: ignore[misc]
            if ok:
                warmed_models.add(model)
        for a in llm_agents:
            if a.model in warmed_models:
                a._warmed = True  # type: ignore[attr-defined]

        await self._flush_events()

    async def _emit_init(self) -> None:
        assert self.state.universe is not None
        u = self.state.universe
        # Pre-compute reciprocal sets so the UI can draw one-way warp arrows.
        warp_set: dict[int, set[int]] = {sid: set(s.warps) for sid, s in u.sectors.items()}
        sectors_payload = []
        for s in u.sectors.values():
            warps_with_dir = []
            for w in s.warps:
                # If the destination warps back to us, it's two-way.
                two_way = s.id in warp_set.get(w, set())
                warps_with_dir.append({"to": w, "two_way": two_way})
            sectors_payload.append({
                "id": s.id,
                "warps": s.warps,
                "warps_dir": warps_with_dir,
                "x": s.x,
                "y": s.y,
                "port": s.port.code if s.port else None,
                "port_name": s.port.name if s.port else None,
                "has_planets": bool(s.planet_ids),
                "is_fedspace": s.id in range(1, 11),
            })
        players_payload = [
            {
                "id": p.id,
                "name": p.name,
                "color": p.color,
                "kind": p.agent_kind,
                "sector_id": p.sector_id,
                "credits": p.credits,
                "ship": p.ship.ship_class.value,
                "alive": p.alive,
            }
            for p in u.players.values()
        ]
        await self.broadcaster.publish({
            "type": "init",
            "seed": u.config.seed,
            "universe_size": u.config.universe_size,
            "max_days": u.config.max_days,
            "sectors": sectors_payload,
            "players": players_payload,
        })

    async def _flush_events(self) -> None:
        """Publish any Events appended to the universe since last flush.

        Also mirrors each event to `events.jsonl` so the saves dir doubles as
        an offline feed/log viewer target. Writing here (not inside apply_action)
        keeps the engine pure and lets ReplayRunner reuse the same flush path.
        """
        assert self.state.universe is not None
        u = self.state.universe
        last_published = getattr(self, "_last_published_seq", 0)
        pending = [e for e in u.events if e.seq > last_published]
        if not pending:
            return
        for ev in pending:
            await self.broadcaster.publish({
                "type": "event",
                "event": ev.model_dump(),
                "state_patch": self._state_patch_for(ev),
            })
            self._last_published_seq = ev.seq
            if self._events_fp is not None:
                try:
                    self._events_fp.write(
                        json.dumps(ev.model_dump(mode="json"), default=str) + "\n"
                    )
                except OSError:
                    pass

    def _state_patch_for(self, ev) -> dict:
        """Produce a minimal state delta hint so the UI can update without rebuilding."""
        u = self.state.universe
        if u is None:
            return {}
        from ..engine.runner import alignment_label, full_net_worth, rank_for
        patch: dict = {}
        if ev.actor_id and ev.actor_id in u.players:
            p = u.players[ev.actor_id]
            patch["player"] = {
                "id": p.id,
                "sector_id": p.sector_id,
                "credits": p.credits,
                "alignment": p.alignment,
                "alignment_label": alignment_label(p.alignment),
                "experience": p.experience,
                "rank": rank_for(p.experience),
                "deaths": p.deaths,
                "max_deaths": 3,
                "ship": p.ship.ship_class.value,
                "fighters": p.ship.fighters,
                "shields": p.ship.shields,
                "cargo": {c.value: p.ship.cargo.get(c, 0) for c in p.ship.cargo},
                "holds": p.ship.holds,
                "cargo_free": p.ship.cargo_free,
                "photon_disabled_ticks": p.ship.photon_disabled_ticks,
                "photon_missiles": p.ship.photon_missiles,
                "ether_probes": p.ship.ether_probes,
                "genesis": p.ship.genesis,
                "corp_ticker": p.corp_ticker,
                "alive": p.alive,
                "turns_today": p.turns_today,
                "turns_per_day": p.turns_per_day,
                "scratchpad": p.scratchpad,
                "net_worth": full_net_worth(u, p),
                "alliances": list(p.alliances),
            }
        if ev.sector_id is not None and ev.sector_id in u.sectors:
            s = u.sectors[ev.sector_id]
            patch["sector"] = {
                "id": s.id,
                "occupants": list(s.occupant_ids),
                "fighters": (
                    {"owner_id": s.fighters.owner_id, "count": s.fighters.count, "mode": s.fighters.mode.value}
                    if s.fighters else None
                ),
                "mines": sum(m.count for m in s.mines),
            }
        if ev.kind == EventKind.DAY_TICK:
            patch["day"] = u.day
        if ev.kind == EventKind.GAME_OVER:
            patch["finished"] = True
            patch["winner_id"] = u.winner_id
            patch["win_reason"] = u.win_reason
        # Planet delta: any event that creates / mutates a planet needs to
        # ship the latest planet snapshot so the client Map stays fresh
        # WITHOUT a page reload. Previously the client only populated
        # state.planets from the initial snapshot, so newly-Genesised
        # planets never appeared on commander cards until refresh.
        planet_events = {
            EventKind.GENESIS_DEPLOYED,
            EventKind.ASSIGN_COLONISTS,
            EventKind.BUILD_CITADEL,
            EventKind.CITADEL_COMPLETE,
            EventKind.PLANET_ORPHANED,
        }
        if ev.kind in planet_events:
            planet_id = (ev.payload or {}).get("planet_id")
            if planet_id is not None and planet_id in u.planets:
                pl = u.planets[planet_id]
                patch["planet"] = {
                    "id": pl.id,
                    "name": pl.name,
                    "sector_id": pl.sector_id,
                    "owner_id": pl.owner_id,
                    "corp_ticker": pl.corp_ticker,
                    "class": pl.class_id.value,
                    "citadel_level": pl.citadel_level,
                    "citadel_target": pl.citadel_target,
                    "citadel_complete_day": pl.citadel_complete_day,
                    "fighters": pl.fighters,
                    "shields": pl.shields,
                    "treasury": pl.treasury,
                    "colonists": {c.value: pl.colonists.get(c, 0) for c in pl.colonists},
                    "stockpile": {c.value: pl.stockpile.get(c, 0) for c in pl.stockpile},
                }
        return patch

    async def _sleep_scaled(self, base: float) -> None:
        mult = max(0.01, self.state.speed_multiplier)
        await asyncio.sleep(base / mult)

    # ---------------- snapshot ---------------- #

    # ---------------- history (Phase 4) ---------------- #

    def _record_history_sample(self) -> None:
        """Append one sample per living player to the ring buffer.

        Called by the game loop once per round-robin pass (i.e. after every
        agent has been given a chance to act). Keeping a small per-player
        deque makes the /history endpoint O(samples) and stable.
        """
        u = self.state.universe
        if u is None:
            return
        from ..engine.runner import full_net_worth
        seq = int(getattr(u, "seq", u.tick))
        for p in u.players.values():
            buf = self._history.get(p.id)
            if buf is None:
                buf = deque(maxlen=self.HISTORY_MAX_SAMPLES)
                self._history[p.id] = buf
            buf.append(
                {
                    "seq": seq,
                    "day": u.day,
                    "tick": u.tick,
                    "credits": int(p.credits),
                    "net_worth": int(full_net_worth(u, p)),
                    "fighters": int(p.ship.fighters),
                    "shields": int(p.ship.shields),
                    "experience": int(p.experience),
                    "alignment": int(p.alignment),
                    "sector_id": int(p.sector_id) if p.sector_id else 0,
                    "alive": bool(p.alive),
                }
            )

    def history_snapshot(self, limit: int | None = None) -> dict:
        """Return the per-player history buffer for the /history endpoint."""
        out: dict[str, list] = {}
        for pid, buf in self._history.items():
            samples = list(buf)
            if limit is not None and limit > 0:
                samples = samples[-limit:]
            out[pid] = samples
        return {"samples": out, "max_samples": self.HISTORY_MAX_SAMPLES}

    def recent_events(self, since: int = 0, limit: int = 200) -> list[dict]:
        """Return event-log entries with seq > since, newest last."""
        u = self.state.universe
        if u is None:
            return []
        events = [e for e in u.events if e.seq > since]
        if len(events) > limit:
            events = events[-limit:]
        return [e.model_dump() for e in events]

    def snapshot(self) -> dict:
        u = self.state.universe
        if u is None:
            return {"status": self.state.status}
        from ..agents.llm import LLMAgent
        from ..engine.runner import alignment_label, full_net_worth, rank_for
        # Pull {player_id: (provider, model)} from the live agent instances so
        # the UI can render a "running model" badge per commander. Heuristic
        # agents get (None, None) and the UI can fall back to the kind label.
        agent_model: dict[str, tuple[str | None, str | None]] = {}
        for ag in self.state.agents:
            if isinstance(ag, LLMAgent):
                agent_model[ag.player_id] = (ag.provider, ag.model)
        return {
            "status": self.state.status,
            "speed": self.state.speed_multiplier,
            "day": u.day,
            "tick": u.tick,
            "finished": u.finished,
            "winner_id": u.winner_id,
            "win_reason": u.win_reason,
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "color": p.color,
                    "kind": p.agent_kind,
                    "sector_id": p.sector_id,
                    "credits": p.credits,
                    "alignment": p.alignment,
                    "alignment_label": alignment_label(p.alignment),
                    "experience": p.experience,
                    "rank": rank_for(p.experience),
                    "deaths": p.deaths,
                    "max_deaths": 3,
                    "ship": p.ship.ship_class.value,
                    "fighters": p.ship.fighters,
                    "shields": p.ship.shields,
                    "cargo": {c.value: p.ship.cargo.get(c, 0) for c in p.ship.cargo},
                    # Per-commodity weighted-avg cost basis (ints rounded).
                    # The UI shows this next to the cargo count so spectators
                    # can see each commander's unrealized P&L in real time.
                    "cargo_cost_avg": {
                        c.value: round(float(p.ship.cargo_cost.get(c, 0.0) or 0.0))
                        for c in p.ship.cargo
                        if p.ship.cargo.get(c, 0) > 0
                    },
                    "holds": p.ship.holds,
                    "cargo_free": p.ship.cargo_free,
                    "photon_disabled_ticks": p.ship.photon_disabled_ticks,
                    "photon_missiles": p.ship.photon_missiles,
                    "ether_probes": p.ship.ether_probes,
                    "genesis": p.ship.genesis,
                    # C3 — atomic_mines count so the "☠ atomic" equip chip
                    # actually fires. Previously the UI read p.atomic_mines
                    # but the snapshot never populated it.
                    "atomic_mines": sum(
                        v for k, v in p.ship.mines.items()
                        if getattr(k, "value", str(k)) == "atomic"
                    ),
                    "corp_ticker": p.corp_ticker,
                    "alive": p.alive,
                    "turns_today": p.turns_today,
                    "turns_per_day": p.turns_per_day,
                    "scratchpad": p.scratchpad,
                    "goal_short": getattr(p, "goal_short", "") or "",
                    "goal_medium": getattr(p, "goal_medium", "") or "",
                    "goal_long": getattr(p, "goal_long", "") or "",
                    "recent_trades": list(getattr(p, "trade_log", []) or [])[-3:],
                    # Full net worth — ship assets + every owned planet.
                    # `net_worth_ship` is broken out so the UI can show
                    # "30k ship + 15k planets" and spectators understand
                    # why Citadel-investor commanders are climbing.
                    "net_worth": full_net_worth(u, p),
                    "net_worth_ship": p.net_worth,
                    "alliances": list(p.alliances),
                    # Intel footprint: how many sectors / ports this
                    # commander has physically visited. Lets spectators
                    # see "explorer vs. grinder" at a glance without
                    # dumping the full known_ports dict over the wire.
                    "known_sectors_count": len(p.known_sectors),
                    "known_ports_count": len(p.known_ports),
                    # Which LLM is piloting this commander — lets the UI show
                    # a model badge ("Grok" vs "Sonnet") so head-to-head
                    # matches are legible at a glance. None for heuristic.
                    "provider": agent_model.get(p.id, (None, None))[0],
                    "model": agent_model.get(p.id, (None, None))[1],
                }
                for p in u.players.values()
            ],
            "corporations": [c.model_dump() for c in u.corporations.values()],
            "alliances": [a.model_dump() for a in u.alliances.values()],
            "planets": [
                {
                    "id": pl.id,
                    "name": pl.name,
                    "sector_id": pl.sector_id,
                    "owner_id": pl.owner_id,
                    "corp_ticker": pl.corp_ticker,
                    "class": pl.class_id.value,
                    "citadel_level": pl.citadel_level,
                    "citadel_target": pl.citadel_target,
                    "citadel_complete_day": pl.citadel_complete_day,
                    "fighters": pl.fighters,
                    "shields": pl.shields,
                    "treasury": pl.treasury,
                    # Idle-colonist pool + per-commodity productive pools.
                    # Spectators need this to see a commander's Citadel-L2
                    # progress (needs 2k idle + 10k cr) without parsing the
                    # event feed. Keys are commodity enum strings.
                    "colonists": {c.value: pl.colonists.get(c, 0) for c in pl.colonists},
                    # Commodity stockpile produced on-planet. Separate from
                    # colonists; these are surplus for trade or build-out.
                    "stockpile": {c.value: pl.stockpile.get(c, 0) for c in pl.stockpile},
                }
                for pl in u.planets.values()
            ],
            # Living Ferrengi raiders so spectators can see the threat layer
            # (dead ones are filtered). Includes sector, aggression, and
            # fighter count so the UI can render them on the map and in the
            # event ticker.
            "ferrengi": [
                {
                    "id": f.id,
                    "name": f.name,
                    "sector_id": f.sector_id,
                    "aggression": f.aggression,
                    "fighters": f.fighters,
                    "shields": f.shields,
                    "ship_class": f.ship_class.value if hasattr(f.ship_class, "value") else str(f.ship_class),
                }
                for f in u.ferrengi.values()
                if f.alive
            ],
            "last_error": self.state.last_error,
        }
