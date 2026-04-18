"""Dump the exact, live anatomy of one agent turn.

Generates a realistic mid-match state by running a small heuristic simulation,
then — for one player — captures every piece of information that participates
in the LLM pipeline for a single turn:

  1. The full Observation pydantic object (structured game state).
  2. The action_hint (prose strip injected into the observation).
  3. The stage_hint (auto-computed arc position).
  4. The exact USER MESSAGE payload that `format_observation` produces —
     this is the string that is sent verbatim to the LLM as `role: user`.
  5. The SYSTEM_PROMPT string (sent verbatim as `role: system`).

Also emits a simulated LLM response so the doc can show the round trip. The
goal is an artifact concrete enough that a new developer can read it and
confidently answer "what does the agent see, and when does it write its plan?"

Usage:
  python scripts/dump_turn_anatomy.py

Writes under docs/agent_turn/:
  system_prompt.md           — the literal SYSTEM_PROMPT
  observation_raw.json       — full Observation model (superset)
  user_message.json          — EXACT string sent to the LLM
  action_hint.txt            — just the hint strip, for readability
  stage_hint.json            — just the stage_hint block
  example_llm_response.json  — a plausible grok response with goals + action
  pipeline_trace.md          — human-narrated walk-through of turn N
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from tw2k.agents import HeuristicAgent  # noqa: E402
from tw2k.agents.prompts import SYSTEM_PROMPT, format_observation, stage_hint  # noqa: E402
from tw2k.engine import (  # noqa: E402
    GameConfig,
    apply_action,
    build_observation,
    generate_universe,
    is_finished,
    tick_day,
)
from tw2k.engine.models import Player, Ship  # noqa: E402

TARGET_TURNS = 40  # how many heuristic rounds before we snapshot
SEED = 42
UNIVERSE_SIZE = 1000
MAX_DAYS = 3
TURNS_PER_DAY = 80
STARTING_CREDITS = 75_000


async def _simulate_until_interesting() -> tuple[object, str]:
    """Run a universe forward until the target player has cargo + goals."""
    config = GameConfig(
        seed=SEED,
        universe_size=UNIVERSE_SIZE,
        max_days=MAX_DAYS,
        turns_per_day=TURNS_PER_DAY,
        starting_credits=STARTING_CREDITS,
    )
    universe = generate_universe(config)

    agents: list[HeuristicAgent] = []
    for i in range(2):
        pid = f"P{i+1}"
        name = ("Captain Reyes", "Admiral Vex")[i]
        p = Player(
            id=pid,
            name=name,
            ship=Ship(),
            credits=STARTING_CREDITS,
            turns_per_day=TURNS_PER_DAY,
        )
        universe.players[pid] = p
        universe.sectors[1].occupant_ids.append(pid)
        p.known_sectors.add(1)
        agents.append(HeuristicAgent(pid, name))

    target_pid = agents[0].player_id
    idx = 0
    loop_guard = 0
    while not is_finished(universe) and loop_guard < TARGET_TURNS * 4:
        loop_guard += 1
        agent = agents[idx]
        player = universe.players[agent.player_id]
        if player.turns_today >= player.turns_per_day:
            if all(
                universe.players[a.player_id].turns_today
                >= universe.players[a.player_id].turns_per_day
                for a in agents
            ):
                tick_day(universe)
            idx = (idx + 1) % len(agents)
            continue
        obs = build_observation(universe, agent.player_id)
        action = await agent.act(obs)
        apply_action(universe, agent.player_id, action)
        idx = (idx + 1) % len(agents)
        # Bail as soon as the target player has meaningful state to observe:
        # they have moved off sector 1, visited at least one port, and taken
        # actions. This keeps the captured observation rich without running
        # the whole game.
        tp = universe.players[target_pid]
        if (
            tp.sector_id != 1
            and len(tp.known_ports) >= 2
            and tp.turns_today >= 6
        ):
            break

    return universe, target_pid


def _inject_realistic_agent_memory(universe: object, target_pid: str) -> None:
    """Populate goals, scratchpad, and trade_log so the dump matches what a
    ~40-turn-in LLM run would actually look like. Heuristic agents don't
    write goals or scratchpads, so we stage those fields here to match the
    content that comes out of grok-4-fast in live matches."""
    p = universe.players[target_pid]  # type: ignore[attr-defined]
    p.scratchpad = (
        "sec 5(SBB fo@21, eq@40) <-> sec 7(BSB fo@27, eq@35) paired.\n"
        "CargoTran 43.5k @ sec 1 once cr>=45k. Genesis plan: any dead-end\n"
        "sector with 1 warp-out in the outer ring. Vex last seen sec 395."
    )
    p.goal_short = (
        "warp 7 -> sell 20 fuel_ore @>=26cr; warp 5 buy 20 fo @<=22cr; "
        "repeat until cr>=45k"
    )
    p.goal_medium = (
        "hit 45k cr, warp back to sector 1, buy_ship cargotran (43.5k), "
        "fill holds with colonists for Genesis run"
    )
    p.goal_long = (
        "CargoTran day 1, Genesis a dead-end sector day 2, Citadel L2 by "
        "day 3; ferry colonists to compound planet production."
    )
    # Ensure trade_log has at least a couple of entries even if heuristic
    # sim didn't produce them — they're the "recent trades" list the UI
    # and action_hint reference.
    if not getattr(p, "trade_log", None):
        p.trade_log = []
    if len(p.trade_log) < 2:
        universe_day = getattr(universe, "day", 1)  # type: ignore[attr-defined]
        p.trade_log.extend(
            [
                {
                    "day": universe_day,
                    "tick": 4,
                    "sector_id": 5,
                    "commodity": "fuel_ore",
                    "qty": 20,
                    "side": "buy",
                    "unit": 21,
                    "total": 420,
                    "realized_profit": None,
                },
                {
                    "day": universe_day,
                    "tick": 8,
                    "sector_id": 7,
                    "commodity": "fuel_ore",
                    "qty": 20,
                    "side": "sell",
                    "unit": 27,
                    "total": 540,
                    "realized_profit": 120,
                },
            ]
        )


def _example_llm_response() -> dict:
    """A plausible, well-formed response grok-4-fast would emit mid-day-1.

    Mirrors the JSON schema in the system prompt exactly. Used in the doc
    to show the 'Turn N+1' side of the handshake."""
    return {
        "thought": (
            "At sector 5 (SBB fuel_ore seller). My goal is to run 5<->7 "
            "until I hit 45k cr. Buying 20 holds of fuel_ore below list."
        ),
        "scratchpad_update": (
            "sec 5(SBB fo@21, eq@40) <-> sec 7(BSB fo@27, eq@35) paired.\n"
            "CargoTran 43.5k @ sec 1 once cr>=45k. Loop complete: 3 done, "
            "2 to go. Est cr after this round-trip: ~45.5k."
        ),
        "goals": {
            "short": (
                "buy 20 fo @<=19cr (haggle); warp 5 -> 7; sell @>=27cr; "
                "this is trip 4/5"
            ),
            "medium": (
                "hit 45k cr THIS DAY, warp 1, buy_ship cargotran, load "
                "colonists for Genesis"
            ),
            "long": (
                "CargoTran day 1, Genesis day 2, Citadel L2 day 3; "
                "out-produce Vex"
            ),
        },
        "action": {
            "kind": "trade",
            "args": {
                "commodity": "fuel_ore",
                "qty": 20,
                "side": "buy",
                "unit_price": 19,
            },
        },
    }


def main() -> None:
    out_dir = REPO / "docs" / "agent_turn"
    out_dir.mkdir(parents=True, exist_ok=True)

    universe, target_pid = asyncio.run(_simulate_until_interesting())
    _inject_realistic_agent_memory(universe, target_pid)

    obs = build_observation(universe, target_pid)
    user_message_str = format_observation(obs, compact=False)
    user_message_obj = json.loads(user_message_str)

    # -- System prompt (verbatim) --
    (out_dir / "system_prompt.md").write_text(
        "# SYSTEM PROMPT (verbatim string sent as `role: system`)\n\n"
        "This is the exact text of `tw2k.agents.prompts.SYSTEM_PROMPT` that\n"
        "is passed to the LLM on every single turn. It is static across\n"
        "turns — only the user message changes.\n\n"
        "```\n" + SYSTEM_PROMPT + "\n```\n",
        encoding="utf-8",
    )

    # -- Full Observation model (superset — not everything is sent to LLM!) --
    (out_dir / "observation_raw.json").write_text(
        obs.model_dump_json(indent=2),
        encoding="utf-8",
    )

    # -- Exact user message string (subset that actually reaches the LLM) --
    (out_dir / "user_message.json").write_text(
        json.dumps(user_message_obj, indent=2),
        encoding="utf-8",
    )

    (out_dir / "action_hint.txt").write_text(
        obs.action_hint + "\n",
        encoding="utf-8",
    )

    (out_dir / "stage_hint.json").write_text(
        json.dumps(stage_hint(obs), indent=2),
        encoding="utf-8",
    )

    (out_dir / "example_llm_response.json").write_text(
        json.dumps(_example_llm_response(), indent=2),
        encoding="utf-8",
    )

    sent_keys = sorted(user_message_obj.keys())
    obs_keys = sorted(obs.model_dump().keys())
    sent_self_keys = sorted((user_message_obj.get("self") or {}).keys())
    # Any Observation field whose NAME appears as a key in user_message OR
    # as a key nested under user_message.self is considered "sent". The
    # obs field `self_id` / `self_name` project to `self.id` / `self.name`.
    reachable = set(sent_keys) | set(sent_self_keys) | {"self_id", "self_name"}
    # `known_ports` ships as `known_ports_top` (a curated subset). That's
    # intentional — mark it reachable.
    if "known_ports_top" in sent_keys:
        reachable.add("known_ports")
    not_sent = sorted(k for k in obs_keys if k not in reachable)

    print(f"[ok] wrote artifacts to {out_dir}")
    print(f"[info] player: {target_pid} ({obs.self_name})")
    print(f"[info] universe day={obs.day} tick={obs.tick} sector={obs.sector['id']}")
    print(f"[info] user_message top-level keys: {sent_keys}")
    print(f"[info] self.* keys: {sent_self_keys}")
    print(f"[info] fields on Observation BUT NOT in user_message: {not_sent}")
    print(
        f"[info] user_message length: {len(user_message_str):,} chars "
        f"(~{len(user_message_str) // 4:,} tokens est)"
    )


if __name__ == "__main__":
    main()
