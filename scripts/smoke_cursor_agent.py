"""Cursor provider smoke test.

Builds a tiny synthetic Universe, creates an LLMAgent(provider="cursor"),
warms it up, and runs a single act() — prints the resulting Action + the
parsed LLMUsage so we can verify both the CLI path AND the cost-tracking
path work end-to-end BEFORE we fire off a full 3-agent match.

Invoke from the repo root:

    $env:CURSOR_API_KEY = "crsr_..."
    python scripts/smoke_cursor_agent.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from tw2k.agents.llm import LLMAgent, _resolve_cursor_cli
from tw2k.engine import GameConfig, build_observation, generate_universe


async def main() -> int:
    node, js, cli = _resolve_cursor_cli()
    print(f"[smoke] resolved cursor CLI: node={node} js={js} wrapper={cli}")
    if not ((node and js) or cli):
        print("[smoke] FAIL: no cursor CLI found on disk", file=sys.stderr)
        return 2
    if not os.environ.get("CURSOR_API_KEY"):
        print("[smoke] WARNING: CURSOR_API_KEY not set — may fall back to 'agent login'")

    cfg = GameConfig(
        seed=42,
        universe_size=30,
        max_days=1,
        turns_per_day=5,
        starting_credits=20_000,
        all_start_stardock=True,
        enable_ferrengi=False,
        enable_planets=False,
        enable_corps=False,
    )
    universe = generate_universe(cfg)
    from tw2k.engine.models import Player

    p1 = Player(id="P1", name="SmokeTest")
    universe.players["P1"] = p1
    universe.sectors[p1.sector_id].occupant_ids.append("P1")

    agent = LLMAgent(
        player_id="P1",
        name="SmokeTest",
        provider="cursor",
        model=os.environ.get("TW2K_CURSOR_MODEL", "composer-2-fast"),
        think_cap_s=180.0,
    )

    print("[smoke] calling warmup() ...")
    ok, note = await agent.warmup()
    print(f"[smoke] warmup => ok={ok} note={note[:160]!r}")
    if not ok:
        print("[smoke] FAIL: warmup failed", file=sys.stderr)
        return 3

    obs = build_observation(universe, "P1")
    print("[smoke] calling act() ...")
    action = await agent.act(obs)
    print(f"[smoke] action => kind={action.kind} args={action.args}")
    print(f"[smoke] thought => {action.thought[:300]!r}")
    usage = getattr(agent, "_last_usage", None)
    if usage is not None:
        print(
            f"[smoke] usage => in={usage.input_tokens} "
            f"cache_r={usage.cached_input_tokens} "
            f"cache_w={usage.cache_write_tokens} "
            f"out={usage.output_tokens} source={usage.source}"
        )
    else:
        print("[smoke] usage => None (no outer envelope parsed)")

    await agent.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
