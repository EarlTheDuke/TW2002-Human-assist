"""Replay runner — re-executes a recorded match from `saves/<run-id>/`.

Reads `meta.json` + `actions.jsonl` and drives the exact same engine
pipeline as a live match. Because the engine is deterministic in
`(seed, action sequence)` — `Universe.rng` is seeded from `config.seed`
and generation-time randomness has its own independent RNG — replaying
the recorded actions reconstructs every state mutation, every emitted
event, and (transitively) every UI update bit-for-bit.

This subclass reuses MatchRunner's state, broadcaster plumbing,
history ring-buffer, snapshot endpoints, and event fan-out. The only
override is `_run()`, which replaces the live agent round-robin loop
with a straightforward iteration over the recorded action log.

Honored controls during replay: `pause`, `resume`, `set_speed`, `stop`.
Speed is applied as a divisor on the recorded inter-action wall-time,
so `speed=2.0` plays back twice as fast as recorded, regardless of what
the live match's `action_delay_s` was.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from ..engine import (
    EventKind,
    GameConfig,
    Universe,
    apply_action,
    generate_universe,
    is_finished,
    tick_day,
)
from ..engine.actions import Action
from ..engine.models import Player, Ship
from .broadcaster import Broadcaster
from .runner import AGENT_COLORS, AgentSpec, MatchRunner, MatchSpec, RunnerState


class ReplayRunner(MatchRunner):
    """MatchRunner variant that plays back a recorded saves/<run-id>/ dir."""

    def __init__(self, broadcaster: Broadcaster, replay_dir: Path):
        # We still want a saves_root pointing *somewhere*, but we never
        # write during replay, so we route it to a throwaway path that
        # _open_save_sink() won't touch (because we override start()).
        super().__init__(broadcaster, saves_root=replay_dir.parent)
        self._replay_dir = replay_dir
        self._meta: dict[str, Any] | None = None
        self._log: list[dict[str, Any]] = []

    # ---------------- lifecycle ---------------- #

    async def start(self, spec: MatchSpec | None = None) -> None:  # type: ignore[override]
        """Begin replay. `spec` is ignored; the recorded meta is authoritative."""
        if self._task is not None and not self._task.done():
            await self.stop()
        self._load(self._replay_dir)
        # Reconstruct a MatchSpec from meta for snapshot/_build_agents compatibility.
        cfg = GameConfig(**self._meta["config"])  # type: ignore[index]
        agents: list[AgentSpec] = [
            AgentSpec(
                player_id=a["player_id"],
                name=a["name"],
                kind=a["kind"],
                provider=a.get("provider"),
                model=a.get("model"),
            )
            for a in self._meta["agents"]  # type: ignore[index]
        ]
        self._spec = MatchSpec(
            config=cfg,
            agents=agents,
            action_delay_s=float(self._meta.get("action_delay_s", 0.6)),  # type: ignore[union-attr]
        )
        self._stop.clear()
        self._pause.set()
        self.state = RunnerState()
        self.state.run_id = self._meta.get("run_id", self._replay_dir.name)  # type: ignore[union-attr]
        self.state.save_dir = self._replay_dir
        self._last_published_seq = 0
        self._history = {}
        self.broadcaster.reset_history()
        # NOTE: intentionally skip _open_save_sink — replay must NEVER
        # overwrite a recorded run. Our writer fps stay None.
        self._task = asyncio.create_task(self._run(), name="tw2k-replay")

    # ---------------- loader ---------------- #

    def _load(self, replay_dir: Path) -> None:
        meta_path = replay_dir / "meta.json"
        actions_path = replay_dir / "actions.jsonl"
        if not meta_path.is_file():
            raise FileNotFoundError(f"meta.json not found in {replay_dir}")
        if not actions_path.is_file():
            raise FileNotFoundError(f"actions.jsonl not found in {replay_dir}")
        self._meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self._log = []
        with actions_path.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    self._log.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip truncated last-line from a crashed writer
                    # rather than refuse to replay — partial runs are
                    # still useful to watch up to the cutoff.
                    continue

    # ---------------- main loop (override) ---------------- #

    async def _run(self) -> None:  # mirrors MatchRunner._run, but log-driven
        assert self._spec is not None
        try:
            self.state.status = "replaying"
            self.state.started_at = time.time()

            universe = generate_universe(self._spec.config)
            self.state.universe = universe

            # Recreate players exactly the way MatchRunner._build_agents did —
            # same start-sector rotation, same credit skew, same initial
            # known-sectors/known-ports seeding — so a replay reproduces the
            # live observation context too.
            self._place_players(universe)

            await self._emit_init()

            universe.emit(
                EventKind.GAME_START,
                payload={
                    "players": [
                        {"id": a.player_id, "name": a.name, "kind": a.kind}
                        for a in self._spec.agents
                    ],
                    "config": universe.config.model_dump(),
                    "replay": {"run_id": self.state.run_id, "total_log_entries": len(self._log)},
                },
                summary=(
                    f"[REPLAY] {self.state.run_id} begins — "
                    f"{len(self._spec.agents)} players, "
                    f"{len(self._log)} log entries."
                ),
            )
            await self._flush_events()

            prev_t = 0.0
            for idx, entry in enumerate(self._log):
                await self._pause.wait()
                if self._stop.is_set():
                    break
                if is_finished(universe):
                    break

                entry_t = float(entry.get("t", prev_t))
                # Replay honors the recorded inter-event wall time, scaled
                # by speed_multiplier so the user can scrub fast/slow
                # without losing the match's pacing.
                dt = max(0.0, entry_t - prev_t)
                if dt > 0:
                    await self._sleep_scaled(dt)
                prev_t = entry_t

                kind = entry.get("kind", "action")
                if kind == "day_tick":
                    tick_day(universe)
                    await self._flush_events()
                    # Sample history at day boundaries. In a live match we
                    # sample on round-robin rollover, which is a similar
                    # cadence for small matches. Keeps sparklines populated.
                    self._record_history_sample()
                    continue

                # action
                try:
                    action = Action.model_validate(entry["action"])
                except Exception as exc:
                    universe.emit(
                        EventKind.AGENT_ERROR,
                        payload={"error": f"replay decode failed: {exc}", "entry": idx},
                        summary=f"[REPLAY] entry {idx} decode failed: {exc}",
                    )
                    await self._flush_events()
                    continue

                player_id = str(entry.get("player_id", ""))
                apply_action(universe, player_id, action)
                await self._flush_events()

                # Periodic history sample — every ~8 actions keeps sparklines
                # updating without flooding the ring buffer.
                if idx % 8 == 0:
                    self._record_history_sample()

            # Final sample + a synthetic event so the UI shows we reached EOF.
            self._record_history_sample()
            if not is_finished(universe):
                universe.emit(
                    EventKind.GAME_OVER,
                    payload={"reason": "replay_eof", "run_id": self.state.run_id},
                    summary=f"[REPLAY] end of log reached ({len(self._log)} entries).",
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

    # ---------------- player placement ---------------- #

    def _place_players(self, universe: Universe) -> None:
        """Insert Player objects mirroring MatchRunner._build_agents layout.

        Replay doesn't build LLM/heuristic agent objects (no one would be
        driving them anyway), but we still need real Player models in
        `universe.players` so that apply_action works and snapshots render
        commander cards. This is the same placement logic as live.
        """
        from ..engine import constants as K

        assert self._spec is not None
        fed_sectors = sorted(K.FEDSPACE_SECTORS)
        start_order = [fed_sectors[0]] + [s for s in fed_sectors if s != fed_sectors[0]]

        for i, ag in enumerate(self._spec.agents):
            color = AGENT_COLORS[i % len(AGENT_COLORS)]
            start_sid = start_order[i % len(start_order)]
            credit_skew = (i * 317) % 2001 - 1000
            ship = Ship()
            base_credits = getattr(self._spec.config, "starting_credits", K.STARTING_CREDITS)
            base_tpd = getattr(self._spec.config, "turns_per_day", K.STARTING_TURNS_PER_DAY)
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
            player.known_sectors.add(start_sid)
            sector = universe.sectors[start_sid]
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
