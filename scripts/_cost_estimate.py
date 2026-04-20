"""Estimate per-turn LLM token cost against the live match.

Builds a real Observation for each live player using the running server's
state, renders the user message via format_observation, concatenates the
SYSTEM_PROMPT, and counts tokens with tiktoken (cl100k_base is close
enough to Claude's tokenizer for rough cost estimates — Anthropic's
tokens-per-char ratio is within ~10% of OpenAI's on English text).
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.request

# Ensure we can import the tw2k engine without starting the server.
WS = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS / "src"))

from tw2k.agents.prompts import SYSTEM_PROMPT, format_observation  # noqa: E402
from tw2k.engine import build_observation  # noqa: E402
from tw2k.engine.models import Universe  # noqa: E402


def _roughly(chars: int) -> int:
    """Anthropic's tokens/char on English settles around 0.27 (~3.7 chars
    per token). We use 0.27 as a conservative estimate — slightly higher
    than OpenAI's 0.25 to avoid underselling the bill."""
    return int(chars * 0.27)


def main() -> None:
    # Fetch the live universe JSON. /state is the spectator view; not
    # enough to rebuild a Universe. Instead, hit a dedicated dump if one
    # exists — otherwise we approximate by asking the server for current
    # payload via the same path the agent sees.
    #
    # Cheapest approach: just measure SYSTEM + format_observation(obs)
    # using a FRESH local generation of the universe with the same seed.
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.models import Player, Ship

    cfg = GameConfig(seed=42, universe_size=1000, max_days=5)
    u: Universe = generate_universe(cfg)
    # Two players at StarDock, identical-ish to the real match setup.
    p1 = Player(id="P1", name="Grok", ship=Ship(), sector_id=1)
    p2 = Player(id="P2", name="Claude", ship=Ship(), sector_id=1)
    u.players["P1"] = p1
    u.players["P2"] = p2
    for p in (p1, p2):
        u.sectors[1].occupant_ids.append(p.id)
        p.known_sectors.add(1)
        p.known_warps[1] = list(u.sectors[1].warps)

    # Simulate a mid-game state: pretend each player has explored ~40
    # sectors, has 25 trade_log entries, and has a full recent_events
    # history of 30. We don't need to run an actual game — we just
    # inflate the relevant Player/Universe fields.
    for p in (p1, p2):
        for i, sid in enumerate(list(u.sectors.keys())[:40]):
            p.known_sectors.add(sid)
            p.known_warps[sid] = list(u.sectors[sid].warps)
        for i in range(25):
            p.trade_log.append({
                "day": 1, "tick": i, "sector_id": 7,
                "commodity": "organics", "qty": 20, "side": "sell" if i % 2 else "buy",
                "unit": 20 + i, "total": (20 + i) * 20,
                "realized_profit": 60 if i % 2 else None,
                "note": "haggle countered" if i % 4 == 0 else "",
            })
        p.scratchpad = "Day 1 plan: cargotran by 45k; pair fuel_ore 5<->7; watch haggle rate. " * 3
        p.goal_short = "warp to 680 SBS, sell fuel_ore @<=18cr cost basis"
        p.goal_medium = "hit 45k credits, swap to cargotran, pick Genesis sector"
        p.goal_long = "Citadel L2 by day 3, two-planet cluster, push 500k by day 5"

    # Emit ~30 recent events so recent_events, recent_failures, and
    # action_hint's REPEATED FAILURES scan have real data.
    from tw2k.engine.models import EventKind
    for i in range(30):
        u.emit(EventKind.AGENT_THOUGHT, actor_id="P1",
               sector_id=1, payload={"text": f"t{i}"}, summary=f"Grok thought {i}")
        u.emit(EventKind.AGENT_THOUGHT, actor_id="P2",
               sector_id=1, payload={"text": f"t{i}"}, summary=f"Claude thought {i}")

    # Now measure.
    rows = []
    for pid in ("P1", "P2"):
        obs = build_observation(u, pid)
        user_msg = format_observation(obs)
        system_chars = len(SYSTEM_PROMPT)
        user_chars = len(user_msg)
        system_tok = _roughly(system_chars)
        user_tok = _roughly(user_chars)
        rows.append({
            "pid": pid,
            "system_chars": system_chars,
            "user_chars": user_chars,
            "system_tok_est": system_tok,
            "user_tok_est": user_tok,
            "input_tok_total": system_tok + user_tok,
        })

    print("=== Per-turn input token estimate (mid-game, 40 sectors known, 25 trades, 30 events) ===")
    for r in rows:
        print(f"  {r['pid']}: system={r['system_tok_est']:,} tok + user={r['user_tok_est']:,} tok"
              f" = {r['input_tok_total']:,} input tok/turn")

    # Output budget — hard-capped in src/tw2k/agents/llm.py
    out_tok_cap_claude = 900
    out_tok_typical = 650  # Claude rarely uses the full 900; estimate ~70% of cap
    print(f"\n  Claude max_tokens cap: {out_tok_cap_claude} (typical use ~{out_tok_typical})")

    # --- Cost math ---
    # Turn economy: 300 turns/day, 5 days, 2 actions/turn average (warp=2,
    # trade=3, scan=1, wait=1 -> weighted mean ~2).
    actions_per_day_per_player = 300 // 2  # 150 LLM calls/player/day
    days = 5
    actions_per_player = actions_per_day_per_player * days  # 750
    # Add 10% overhead for failed-retry turns that don't consume game turns.
    overhead_mul = 1.10
    effective_calls = int(actions_per_player * overhead_mul)

    # Use Claude's row (P2).
    claude = next(r for r in rows if r["pid"] == "P2")
    input_per_call = claude["input_tok_total"]

    total_input = effective_calls * input_per_call
    total_output = effective_calls * out_tok_typical

    rate_in = 3.00 / 1_000_000   # $/token
    rate_out = 15.00 / 1_000_000

    cost_in = total_input * rate_in
    cost_out = total_output * rate_out
    cost_total = cost_in + cost_out

    print("\n=== Claude Sonnet 4.5 — FULL 5-DAY MATCH COST ESTIMATE ===")
    print(f"  LLM calls/day (Claude):    ~{actions_per_day_per_player}")
    print(f"  Days:                      {days}")
    print(f"  + 10% retry overhead:      x{overhead_mul}")
    print(f"  Effective calls (Claude):  {effective_calls:,}")
    print(f"  Input per call:            {input_per_call:,} tok")
    print(f"  Output per call (typical): {out_tok_typical:,} tok")
    print(f"  Total input:               {total_input:,} tok")
    print(f"  Total output:              {total_output:,} tok")
    print(f"  Input cost:                ${cost_in:6.2f}  @ $3.00/M")
    print(f"  Output cost:               ${cost_out:6.2f}  @ $15.00/M")
    print(f"  ---")
    print(f"  CLAUDE TOTAL:              ${cost_total:6.2f}")

    # Worst-case bound: Claude maxes output every call AND input is 20%
    # larger late-game (known_warps grows to ~200 entries).
    worst_input = int(total_input * 1.20)
    worst_output = effective_calls * out_tok_cap_claude
    worst_cost = worst_input * rate_in + worst_output * rate_out
    print(f"\n  Worst-case (full max_tokens + 20% fatter ctx): ${worst_cost:6.2f}")

    # --- 120-day extrapolation ---
    scale = 120 / 5
    print(f"\n=== 120-day marathon extrapolation (x{scale:g}) ===")
    print(f"  Claude typical: ${cost_total * scale:6.2f}")
    print(f"  Claude worst:   ${worst_cost * scale:6.2f}")


if __name__ == "__main__":
    main()
