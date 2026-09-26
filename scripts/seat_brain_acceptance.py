#!/usr/bin/env python3
"""Seat-only acceptance harness for the S3 SeatBrain (seat-bot S4).

  # 1. engine-free: hand-built fogged observations for the empire loop
  python scripts/seat_brain_acceptance.py synthetic

  # 2. record a trace of the seat's OWN observations from an offline engine run
  #    (mailbox payload format - identical to what a live seat receives)
  python scripts/seat_brain_acceptance.py record --out docs/playtests/seat_trace.jsonl --days 4

  # 3. replay any trace (offline recording, or a live one from seat_brain_v2.py --record)
  #    through a FRESH brain; validate every action against that observation's legal_actions
  python scripts/seat_brain_acceptance.py replay docs/playtests/seat_trace.jsonl

  # 4. N1 offline proof (no live match): seed 250925, spawn sector 6, day-1 StarDock
  python scripts/seat_brain_acceptance.py n1

  # 5. N2 offline proof: 10-day growth A/B vs the N1 brain, five seeds
  python scripts/seat_brain_acceptance.py n2

  # 6. N3 offline proof: value-per-turn vs the N2 ladder. Ferry turns < 40%,
  #    day-10 net worth >= 400k on seed 250925, organics never 0.
  python scripts/seat_brain_acceptance.py n3

Exit code 0 = every action valid and the genesis -> land -> citadel -> ferry loop completed.
Replay and synthetic modes never touch the engine state, /state, or another seat.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tw2k.agents.seat_acceptance import (  # noqa: E402
    STORYBOARD,
    MilestoneTracker,
    aba_bounces,
    ferry_storyboard,
    load_jsonl,
    replay,
    validate_action,
)
from tw2k.agents.seat_brain import SeatBrain  # noqa: E402


def run_synthetic() -> int:
    failures = 0
    for board_name, board in (("genesis", STORYBOARD), ("citadel+ferry", ferry_storyboard())):
        brain = SeatBrain()
        for label, obs, kind, args in board:
            action = brain.decide(obs)
            problems = validate_action(obs, action)
            match = action["kind"] == kind and all(action["args"].get(k) == v for k, v in args.items())
            ok = match and not problems
            failures += not ok
            print(f"{'OK ' if ok else 'FAIL'} [{board_name}] {label}: {action['kind']} {action['args']}"
                  + ("" if match else f"  (expected {kind} {args})") + (f"  {problems}" if problems else ""))
    print(f"synthetic: {'PASS' if failures == 0 else f'{failures} FAIL'}")
    return 0 if failures == 0 else 1


def record_offline(out: Path, *, seed: int = 230923, credits: int = 120_000, days: int = 4,
                   max_actions: int = 4000, seat: str = "P1") -> dict:
    """Offline engine run. The brain only sees build_observation(u, seat); every payload is recorded."""
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.actions import Action
    from tw2k.engine.models import Player
    from tw2k.engine.observation import build_observation
    from tw2k.engine.runner import apply_action, tick_day

    u = generate_universe(GameConfig(seed=seed, universe_size=150, max_days=days + 2, turns_per_day=250,
                                     starting_credits=credits, enable_ferrengi=False, enable_planets=True))
    for pid, name in ((seat, "Seat"), ("P9", "Idle")):
        p = Player(id=pid, name=name, agent_kind="external", sector_id=1, credits=credits)
        u.players[pid] = p
        u.sectors[1].occupant_ids.append(pid)
    brain = SeatBrain()
    tracker = MilestoneTracker()
    out.parent.mkdir(parents=True, exist_ok=True)
    rejected = 0
    with out.open("w", encoding="utf-8") as f:
        for seq in range(max_actions):
            p = u.players[seat]
            if p.turns_today >= p.turns_per_day:
                if u.day >= days:
                    break
                tick_day(u)
                continue
            obs = build_observation(u, seat).model_dump(mode="json")
            f.write(json.dumps({"seat": seat, "turn_seq": seq, "observation": obs}) + "\n")
            action = brain.decide(obs)
            tracker.observe(seq, obs, action)
            rejected += not apply_action(u, seat, Action(**action)).ok
            if action["kind"] == "query_limpets":
                tick_day(u)
    return {"report": tracker.report, "rejected": rejected}


def _open_seat(u, seat: str, sector: int, credits: int):
    """Place a seat the way the live server does: FedSpace spawn knowledge, no god view.

    Neighbour ports are remembered as class + stock only (no prices) until visited.
    """
    from tw2k.engine.models import Player

    p = Player(id=seat, name="Seat", agent_kind="external", sector_id=sector, credits=credits,
               turns_per_day=u.config.turns_per_day)
    u.players[seat] = p
    u.sectors[sector].occupant_ids.append(seat)
    p.known_sectors.add(sector)
    sec = u.sectors[sector]
    p.known_warps[sector] = list(sec.warps)
    if sec.port is not None:
        p.known_ports[sector] = {
            "class": sec.port.code,
            "stock": {c.value: {"current": s.current, "max": s.maximum} for c, s in sec.port.stock.items()},
            "last_seen_day": u.day,
        }
    for wid in sec.warps:
        p.known_sectors.add(wid)
        w = u.sectors[wid]
        if w.port is not None:
            p.known_ports[wid] = {
                "class": w.port.code,
                "stock": {c.value: {"current": s.current, "max": s.maximum} for c, s in w.port.stock.items()},
                "last_seen_day": u.day,
            }
    return p


def prove_n1_day(*, seed: int = 250925, credits: int = 20_000, spawn: int = 6,
                 universe_size: int = 1000, turns_per_day: int = 1000) -> dict:
    """One fogged day from ``spawn``. The brain never sees ``/state``."""
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.actions import Action
    from tw2k.engine.observation import build_observation
    from tw2k.engine.runner import apply_action

    u = generate_universe(GameConfig(
        seed=seed, universe_size=universe_size, max_days=3, turns_per_day=turns_per_day,
        starting_credits=credits, enable_ferrengi=False, enable_planets=True,
    ))
    p = _open_seat(u, "P1", spawn, credits)
    brain = SeatBrain()
    rows: list[tuple] = []
    rejected = 0
    peak = credits
    trade_profit = 0
    reached_day = None
    reached_turns = None
    for _ in range(2500):
        if p.turns_today >= p.turns_per_day:
            break
        day = u.day
        sector = p.sector_id
        if sector == 1 and reached_day is None:
            reached_day, reached_turns = day, p.turns_today
        obs = build_observation(u, "P1").model_dump(mode="json")
        action = brain.decide(obs)
        problems = validate_action(obs, action)
        if problems:
            rejected += 1
        res = apply_action(u, "P1", Action(**action))
        if not res.ok:
            rejected += 1
        kind = action.get("kind")
        target = (action.get("args") or {}).get("target")
        rows.append((sector, kind, target))
        if kind == "trade" and (action.get("args") or {}).get("side") == "sell":
            # realized profit is on the player's own trade log (seat-visible ledger).
            entry = p.trade_log[-1] if p.trade_log else None
            if entry and entry.get("day") == day and isinstance(entry.get("realized_profit"), int):
                trade_profit += int(entry["realized_profit"])
        peak = max(peak, p.credits)
        if p.sector_id == 1 and reached_day is None:
            reached_day, reached_turns = u.day, p.turns_today
    bounces = aba_bounces(rows)
    per_100 = (100.0 * bounces / len(rows)) if rows else 0.0
    return {
        "seed": seed, "credits": credits, "spawn": spawn, "day_end_sector": p.sector_id,
        "end_credits": p.credits, "peak_credits": peak, "trade_profit": trade_profit,
        "reached_stardock_day": reached_day, "reached_turns": reached_turns,
        "decisions": len(rows), "aba_bounces": bounces, "aba_per_100": per_100,
        "rejected": rejected,
    }


def run_n1(seeds: list[int], credits_list: list[int]) -> int:
    """N1 done-when: StarDock on day 1 at 100k and 20k; 20k trades a profit; ABA <= 2/100."""
    failures = 0
    for seed in seeds:
        for credits in credits_list:
            row = prove_n1_day(seed=seed, credits=credits)
            ok_sd = row["reached_stardock_day"] == 1
            ok_aba = row["aba_per_100"] <= 2.0
            ok_rej = row["rejected"] == 0
            ok_profit = True if credits >= 50_000 else row["trade_profit"] > 0
            ok = ok_sd and ok_aba and ok_rej and ok_profit
            failures += not ok
            print(
                f"{'OK ' if ok else 'FAIL'} seed={seed} start={credits} "
                f"stardock_day={row['reached_stardock_day']} turns={row['reached_turns']} "
                f"peak={row['peak_credits']} trade_profit={row['trade_profit']} "
                f"aba={row['aba_bounces']}/{row['decisions']} ({row['aba_per_100']:.2f}/100) "
                f"rejected={row['rejected']} end_sector={row['day_end_sector']}"
            )
    print(f"n1: {'PASS' if failures == 0 else f'{failures} FAIL'}")
    return 0 if failures == 0 else 1


N2_SEEDS = (250925, 20260925, 230923, 99, 31)


def n1_brain():
    """SeatBrain with the N1 citadel and organics policy (no N2 growth rules, no N3 allocator)."""
    return SeatBrain(feed_organics=False, citadel_floor_ratio=None, citadel_fuel_shield=False,
                     citadel_multiday_floor=False, value_allocator=False)


def n2_brain():
    """N2 growth policy on the fixed ladder. ``value_allocator`` off is the pre-N3 brain."""
    return SeatBrain(value_allocator=False)


_FERRY_MOVE = frozenset({"plot_course", "warp", "land_planet", "assign_colonists", "liftoff"})


def _is_ferry_action(action: dict, colonists_aboard: int) -> bool:
    """Colonist purchase, a thought that says ferry, or a move while colonists are aboard.

    ``plot_course execute`` spends warp turns inside the handler and reports
    ``turns_spent=0``. Callers must weight this by the ``turns_today`` delta.
    """
    kind = action.get("kind")
    args = action.get("args") or {}
    thought = str(action.get("thought") or "").lower()
    if "ferry" in thought:
        return True
    if kind == "buy_equip" and args.get("item") == "colonists":
        return True
    return colonists_aboard > 0 and kind in _FERRY_MOVE


def prove_growth_replay(*, seed: int, brain: SeatBrain | None = None, days: int = 10,
                        credits: int = 20_000, spawn: int = 6, universe_size: int = 1000,
                        turns_per_day: int = 1000, max_actions: int = 20_000) -> dict:
    """Fogged replay. The brain sees only ``build_observation`` for its seat.

    ``max_days`` stays at the default match length so the last-two-days citadel
    exception does not fire inside a day-10 window.
    """
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.actions import Action
    from tw2k.engine.models import Commodity
    from tw2k.engine.observation import build_observation
    from tw2k.engine.runner import apply_action, tick_day
    from tw2k.engine.victory import full_net_worth

    u = generate_universe(GameConfig(
        seed=seed, universe_size=universe_size, max_days=30, turns_per_day=turns_per_day,
        starting_credits=credits, enable_ferrengi=False, enable_planets=True,
    ))
    p = _open_seat(u, "P1", spawn, credits)
    brain = brain or SeatBrain()
    rejected = 0
    min_organics: int | None = None
    zero_planets: set[int] = set()
    samples = 0
    ferry_turns = 0
    total_turns = 0

    def sample() -> None:
        nonlocal min_organics, samples
        for pl in u.planets.values():
            if pl.owner_id != "P1":
                continue
            colonists = sum(int(n) for n in pl.colonists.values())
            if pl.origin != "genesis" and colonists <= 0:
                continue
            stock = int(pl.stockpile.get(Commodity.ORGANICS, 0))
            samples += 1
            min_organics = stock if min_organics is None else min(min_organics, stock)
            if stock <= 0:
                zero_planets.add(pl.id)

    for _ in range(max_actions):
        if p.turns_today >= p.turns_per_day:
            if u.day >= days:
                break
            tick_day(u)
            sample()
            continue
        obs = build_observation(u, "P1").model_dump(mode="json")
        turns_before = p.turns_today
        day_before = u.day
        colonists_aboard = int(p.ship.cargo.get(Commodity.COLONISTS, 0))
        action = brain.decide(obs)
        if validate_action(obs, action):
            rejected += 1
        res = apply_action(u, "P1", Action(**action))
        if not res.ok:
            rejected += 1
        if u.day == day_before:
            spent = max(0, p.turns_today - turns_before)
            total_turns += spent
            if _is_ferry_action(action, colonists_aboard):
                ferry_turns += spent
        sample()
        if action["kind"] == "query_limpets":
            tick_day(u)
            sample()
            if u.day >= days:
                break
    sample()
    worlds = [pl for pl in u.planets.values() if pl.owner_id == "P1" and pl.origin == "genesis"]
    return {
        "seed": seed,
        "day": u.day,
        "net_worth": full_net_worth(u, p),
        "credits": p.credits,
        "min_organics": min_organics,
        "zero_planets": sorted(zero_planets),
        "organics_samples": samples,
        "genesis_worlds": len(worlds),
        "citadels": sorted(int(pl.citadel_level) for pl in worlds),
        "colonists": [sum(int(n) for n in pl.colonists.values()) for pl in worlds],
        "rejected": rejected,
        "ferry_turns": ferry_turns,
        "total_turns": total_turns,
        "ferry_pct": (100.0 * ferry_turns / total_turns) if total_turns else 0.0,
    }


def run_n2(seeds: list[int]) -> int:
    """N2 done-when: no genesis world organics at 0, and day-10 NW beats N1 on >= 4/5 seeds."""
    failures = 0
    beats = 0
    print(f"{'seed':>8} {'N1 NW':>10} {'N2 NW':>10} {'delta':>10} {'N2 min org':>10} {'zeros':>8} {'citadels'}")
    for seed in seeds:
        base = prove_growth_replay(seed=seed, brain=n1_brain())
        nxt = prove_growth_replay(seed=seed, brain=n2_brain())
        beat = nxt["net_worth"] > base["net_worth"]
        beats += beat
        clean = not nxt["zero_planets"] and nxt["rejected"] == 0
        ok = beat and clean
        failures += not clean
        print(
            f"{seed:>8} {base['net_worth']:>10} {nxt['net_worth']:>10} {nxt['net_worth'] - base['net_worth']:>10} "
            f"{nxt['min_organics']!s:>10} {(nxt['zero_planets'] or '-')!s:>8} {nxt['citadels']} "
            f"col={nxt['colonists']} {'OK' if ok else 'FAIL'}"
        )
    need = 4 if len(seeds) >= 5 else len(seeds)
    score_ok = beats >= need
    print(f"n2: beats {beats}/{len(seeds)} (need {need}); organics {'clean' if failures == 0 else f'{failures} seeds hit 0 or rejected'}")
    return 0 if score_ok and failures == 0 else 1


# Kimi3 winner on this seed was ~427k. The bar is the round number under that.
N3_BENCH_SEED = 250925
N3_MIN_NET_WORTH = 400_000
N3_MAX_FERRY_PCT = 40.0
# A seed "tanks" when N3 finishes under 85% of the N2 ladder on the same map.
N3_N2_FLOOR = 0.85


def run_n3(seeds: list[int]) -> int:
    """N3 done-when: ferry < 40%, seed 250925 day-10 NW >= 400k, organics never 0.

    The N2 column is the fixed ladder (``value_allocator`` off) on the same seeds.
    """
    failures = 0
    print(
        f"{'seed':>8} {'N2 NW':>10} {'N3 NW':>10} {'delta':>9} "
        f"{'N3 ferry':>9} {'N2 ferry':>9} {'org':>6} {'cit':>12} {'worlds':>6}"
    )
    for seed in seeds:
        base = prove_growth_replay(seed=seed, brain=n2_brain())
        nxt = prove_growth_replay(seed=seed, brain=SeatBrain())
        nw_ok = nxt["net_worth"] >= N3_MIN_NET_WORTH if seed == N3_BENCH_SEED else True
        ferry_ok = nxt["ferry_pct"] < N3_MAX_FERRY_PCT
        org_ok = not nxt["zero_planets"] and nxt["rejected"] == 0 and nxt["min_organics"] not in (None, 0)
        floor = int(base["net_worth"] * N3_N2_FLOOR)
        kept = nxt["net_worth"] >= floor
        ok = nw_ok and ferry_ok and org_ok and kept
        failures += not ok
        flag = "OK" if ok else "FAIL"
        print(
            f"{seed:>8} {base['net_worth']:>10} {nxt['net_worth']:>10} "
            f"{nxt['net_worth'] - base['net_worth']:>9} "
            f"{nxt['ferry_pct']:>8.1f}% {base['ferry_pct']:>8.1f}% "
            f"{nxt['min_organics']!s:>6} {nxt['citadels']!s:>12} {nxt['genesis_worlds']:>6} {flag}"
        )
        if not ok:
            print(
                f"         nw_ok={nw_ok} ferry_ok={ferry_ok} org_ok={org_ok} "
                f"kept_vs_n2={kept} (floor {floor}) zeros={nxt['zero_planets'] or '-'} "
                f"rejected={nxt['rejected']} col={nxt['colonists']}"
            )
    if N3_BENCH_SEED not in seeds:
        failures += 1
        print(f"FAIL seed {N3_BENCH_SEED} missing from the N3 set")
    print(
        f"n3: {'PASS' if failures == 0 else f'{failures} FAIL'} "
        f"(ferry < {N3_MAX_FERRY_PCT:.0f}%, seed {N3_BENCH_SEED} NW >= {N3_MIN_NET_WORTH}, organics != 0)"
    )
    return 0 if failures == 0 else 1


def run_replay(path: Path, *, show_errors: int = 10) -> int:
    payloads = load_jsonl(path)
    report, _ = replay(SeatBrain(), payloads)
    print(report.summary())
    for i, e in report.errors[:show_errors]:
        print(f"  #{i}: {e}")
    ok = not report.errors and report.empire_loop_ok
    print(f"replay: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("synthetic")
    rec = sub.add_parser("record")
    rec.add_argument("--out", required=True)
    rec.add_argument("--seed", type=int, default=230923)
    rec.add_argument("--credits", type=int, default=120_000)
    rec.add_argument("--days", type=int, default=4)
    rep = sub.add_parser("replay")
    rep.add_argument("trace")
    n1 = sub.add_parser("n1", help="offline N1 proof: route to StarDock, earn first, frontier explore")
    n1.add_argument("--seeds", default="250925,20260925", help="comma-separated universe seeds")
    n1.add_argument("--credits", default="100000,20000", help="comma-separated starting credits")
    n2 = sub.add_parser("n2", help="offline N2 proof: 10-day organics + net worth vs the N1 brain")
    n2.add_argument("--seeds", default=",".join(str(s) for s in N2_SEEDS), help="comma-separated universe seeds")
    n3 = sub.add_parser("n3", help="offline N3 proof: ferry share, day-10 net worth, organics vs the N2 ladder")
    n3.add_argument("--seeds", default=",".join(str(s) for s in N2_SEEDS), help="comma-separated universe seeds")
    args = ap.parse_args()
    if args.cmd == "synthetic":
        return run_synthetic()
    if args.cmd == "record":
        res = record_offline(Path(args.out), seed=args.seed, credits=args.credits, days=args.days)
        print(res["report"].summary(), f"engine_rejections={res['rejected']}")
        print(f"wrote {args.out}")
        return 0 if res["rejected"] == 0 and res["report"].empire_loop_ok else 1
    if args.cmd == "n1":
        seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
        credits = [int(s) for s in args.credits.split(",") if s.strip()]
        return run_n1(seeds, credits)
    if args.cmd == "n2":
        seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
        return run_n2(seeds)
    if args.cmd == "n3":
        seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
        return run_n3(seeds)
    return run_replay(Path(args.trace))


if __name__ == "__main__":
    raise SystemExit(main())
