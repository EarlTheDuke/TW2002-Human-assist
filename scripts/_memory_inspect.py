"""Snapshot what ONE agent sees on a given turn vs. what the UI shows.

Connects to the running server (port 8001), grabs the universe state,
rebuilds Grok-Alpha's observation the same way the LLM does, then prints
the size and content of every memory field. The point: demonstrate how
much more the agent reads than the scratchpad string the user sees.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.request

WS = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS / "src"))

from tw2k.agents.prompts import format_observation  # noqa: E402


def _safe(s: str, limit: int = 200) -> str:
    enc = sys.stdout.encoding or "utf-8"
    s = s.encode(enc, "replace").decode(enc, "replace")
    return s if len(s) <= limit else s[:limit] + " …[truncated]"


def _roughly(chars: int) -> int:
    return int(chars * 0.27)


def main() -> None:
    # Hit /state for the live public snapshot (what the UI uses)
    with urllib.request.urlopen("http://127.0.0.1:8001/state", timeout=5) as r:
        state = json.loads(r.read().decode("utf-8-sig"))

    # Find P1
    players = state.get("players", {})
    if isinstance(players, dict):
        p1 = players.get("P1", {})
    else:
        p1 = next((p for p in players if p.get("id") == "P1"), {})

    print("=" * 78)
    print("WHAT THE UI SHOWS (scratchpad only)")
    print("=" * 78)
    scratch = p1.get("scratchpad") or ""
    print(f"scratchpad ({len(scratch)} chars, ~{_roughly(len(scratch))} tok):")
    print(f"  '{_safe(scratch, 400)}'")
    print()

    # Now rebuild the full observation by loading the save file
    saves_root = WS / "saves"
    run_dirs = sorted(saves_root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    latest = run_dirs[0]
    print(f"(reconstructing observation for P1 from latest match {latest.name})")
    print()

    # Simpler: build a fresh universe with same seed, give P1 the same
    # known_warps/scratchpad/trade_log from /state, and render the obs.
    from tw2k.engine import GameConfig, build_observation, generate_universe
    from tw2k.engine.models import EventKind, Player, Ship

    meta = json.loads((latest / "meta.json").read_text(encoding="utf-8-sig"))
    seed = int(meta.get("seed", 42))

    cfg = GameConfig(
        seed=seed,
        universe_size=int(meta.get("universe_size", 1000)),
        max_days=int(meta.get("max_days", 120)),
    )
    u = generate_universe(cfg)

    # Rebuild each player's live state from /state projection
    all_players = players if isinstance(players, list) else list(players.values())
    for pd in all_players:
        pid = pd.get("id")
        if not pid:
            continue
        p = Player(
            id=pid,
            name=pd.get("name") or pid,
            ship=Ship(holds=int(pd.get("holds", 20))),
            sector_id=int(pd.get("sector_id", 1)),
        )
        u.players[pid] = p
        u.sectors[p.sector_id].occupant_ids.append(pid)
        p.credits = int(pd.get("credits", 20000))
        p.scratchpad = pd.get("scratchpad") or ""
        p.goal_short = pd.get("goal_short") or ""
        p.goal_medium = pd.get("goal_medium") or ""
        p.goal_long = pd.get("goal_long") or ""
        p.known_sectors.add(p.sector_id)
        p.known_warps[p.sector_id] = list(u.sectors[p.sector_id].warps)

    # Replay actions from saved jsonl so known_warps/trade_log are real
    actions_fp = latest / "actions.jsonl"
    from tw2k.engine import Action, ActionKind, apply_action
    if actions_fp.exists():
        count = 0
        with actions_fp.open(encoding="utf-8") as f:
            for line in f:
                if count >= 300:  # limit replay depth for speed
                    break
                rec = json.loads(line)
                pid = rec.get("player_id")
                a = rec.get("action") or {}
                kind_str = a.get("kind")
                if pid not in u.players or not kind_str:
                    continue
                try:
                    kind = ActionKind(kind_str)
                except Exception:
                    continue
                apply_action(u, pid, Action(kind=kind, args=a.get("args") or {}))
                count += 1

    obs = build_observation(u, "P1")
    rendered = format_observation(obs)
    payload = json.loads(rendered)

    print("=" * 78)
    print("WHAT THE AGENT ACTUALLY READS EACH TURN (full observation)")
    print("=" * 78)
    total = 0
    rows = []
    for k, v in payload.items():
        s = json.dumps(v, separators=(",", ":"), ensure_ascii=False)
        rows.append((k, len(s), _roughly(len(s))))
        total += len(s)

    rows.sort(key=lambda r: -r[1])
    pad_k = max(len(r[0]) for r in rows)
    print(f"  {'field':<{pad_k}}  {'chars':>8}  {'~tok':>6}  {'pct':>5}")
    print(f"  {'-'*pad_k}  {'-'*8}  {'-'*6}  {'-'*5}")
    for k, chars, tok in rows:
        pct = 100 * chars / total if total else 0
        print(f"  {k:<{pad_k}}  {chars:>8,}  {tok:>6,}  {pct:>4.1f}%")
    print(f"  {'-'*pad_k}  {'-'*8}  {'-'*6}  {'-'*5}")
    print(f"  {'TOTAL':<{pad_k}}  {total:>8,}  {_roughly(total):>6,}")

    print()
    print("Key fields the SPECTATOR UI hides:")
    print("  - known_warps      (the full warp graph you've discovered)")
    print("  - trade_log        (your last 25 trades with realized_profit)")
    print("  - trade_summary    (aggregate P&L, haggle rate, best/worst pair)")
    print("  - recent_failures  (grouped repeated failures)")
    print("  - action_hint      (legal verbs + repeated-failure flags + P&L)")
    print("  - known_ports_top  (live port prices + stock, sorted)")
    print("  - recent_events    (last 30 fog-of-war filtered events)")
    print("  - sector + adjacent (current sector full detail)")


if __name__ == "__main__":
    main()
