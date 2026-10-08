#!/usr/bin/env python3
"""Scripted bot match: code-only seats in one shared universe, in-process.

    python scripts/run_scripted_match.py --seats N3,N2,N1,H --seed 250925 --days 10 \
        --json match.json --md match.md

Seats are any comma-separated mix of N1, N2, N3 (SeatBrain variants from
scripts/seat_brain_acceptance.py) and H (the rule-based HeuristicAgent).
Seat i is player P{i+1} and spawns in FedSpace sector i+1 (wrapping). Every
seat starts with --credits and --turns-per-day.

No web server, no ports, no network, no API keys: the engine is imported and
driven directly (build_observation -> decide -> apply_action -> tick_day).

Deterministic: the universe, the engine RNG and each Heuristic seat's RNG are
seeded from --seed, and seats act in a fixed round-robin. The script re-runs
itself with PYTHONHASHSEED=0 when that variable is not already "0", so set
iteration order is pinned too. The JSON holds no wall-clock values, so two
runs with the same arguments write the same file.
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import importlib.util
import json
import os
import subprocess
import sys
import zlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SEAT_KINDS = ("N1", "N2", "N3", "H", "R")


def fold_bank_events(events, pids: list[str]) -> dict[str, dict[str, int]]:
    """Count bank, tax, death, and citadel-treasury events for --bank-report."""
    rows = {
        pid: {"deposits": 0, "deposited": 0, "withdrawals": 0, "withdrawn": 0,
              "tax": 0, "tax_align": 0, "credits_lost": 0, "credits_lost_count": 0,
              "credits_lost_largest": 0, "credits_recovered": 0,
              "treasury_deposits": 0, "treasury_deposited": 0,
              "treasury_withdrawals": 0, "treasury_withdrawn": 0}
        for pid in pids
    }
    for ev in events:
        kind = getattr(ev.kind, "value", str(ev.kind))
        pid = str(ev.actor_id or "")
        payload = ev.payload or {}
        if kind == "bank_deposit" and pid in rows:
            rows[pid]["deposits"] += 1
            rows[pid]["deposited"] += int(payload.get("amount") or 0)
        elif kind == "bank_withdraw" and pid in rows:
            rows[pid]["withdrawals"] += 1
            rows[pid]["withdrawn"] += int(payload.get("amount") or 0)
        elif kind == "tax_collected" and pid in rows:
            rows[pid]["tax"] += int(payload.get("tax") or 0)
            rows[pid]["tax_align"] += int(payload.get("align_gain") or 0)
        elif kind == "ship_destroyed":
            victim = str(payload.get("victim") or "")
            lost = int(payload.get("credits_lost") or 0)
            if victim in rows:
                rows[victim]["credits_lost"] += lost
                rows[victim]["credits_lost_count"] += 1
                rows[victim]["credits_lost_largest"] = max(rows[victim]["credits_lost_largest"], lost)
        elif kind == "credits_recovered" and pid in rows:
            rows[pid]["credits_recovered"] += int(payload.get("credits_recovered") or 0)
        elif kind == "planet_treasury" and pid in rows:
            amount = int(payload.get("amount") or 0)
            if payload.get("direction") == "deposit":
                rows[pid]["treasury_deposits"] += 1
                rows[pid]["treasury_deposited"] += amount
            elif payload.get("direction") == "withdraw":
                rows[pid]["treasury_withdrawals"] += 1
                rows[pid]["treasury_withdrawn"] += amount
    return rows
# A seat that sends this many zero-turn actions in a row is done for the day.
STUCK_ZERO_TURN_ACTIONS = 200


def _acceptance():
    spec = importlib.util.spec_from_file_location(
        "seat_brain_acceptance_for_match", ROOT / "scripts" / "seat_brain_acceptance.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _seat_agent(kind: str, pid: str, name: str, seed: int):
    """H is the heuristic. R is the offline text reader. Code seats have no agent."""
    if kind == "H":
        from tw2k.agents import HeuristicAgent
        return HeuristicAgent(pid, name, seed=zlib.crc32(f"{seed}:{pid}".encode()))
    if kind == "R":
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from tests.llm_text_reader import TextReaderAgent
        return TextReaderAgent(pid, name)
    return None


def parse_seats(text: str) -> list[str]:
    seats = [s.strip().upper() for s in text.split(",") if s.strip()]
    seats = ["H" if s in ("HEUR", "HEURISTIC") else s for s in seats]
    bad = [s for s in seats if s not in SEAT_KINDS]
    if bad or not seats:
        raise ValueError(f"seats must be a comma list of {', '.join(SEAT_KINDS)}; got {text!r}")
    return seats


def _place_reader_f1(universe, pid: str) -> None:
    """The fixture-lab f1 start: 10 hops from StarDock, outside FedSpace, 250000 credits."""
    from tw2k.engine import constants as K

    start = int(K.STARDOCK_SECTOR)
    seen = {start}
    layer = [start]
    for _ in range(10):
        nxt: list[int] = []
        for sid in layer:
            for dest in universe.sectors[sid].warps:
                if dest not in seen:
                    seen.add(dest)
                    nxt.append(dest)
        if not nxt:
            raise RuntimeError("galaxy has no sector 10 hops from StarDock")
        layer = nxt
    dest = next((int(sid) for sid in layer if sid not in K.FEDSPACE_SECTORS), int(layer[0]))
    player = universe.players[pid]
    old = universe.sectors[player.sector_id].occupant_ids
    if pid in old:
        old.remove(pid)
    player.sector_id = dest
    player.credits = 250_000
    occupants = universe.sectors[dest].occupant_ids
    if pid not in occupants:
        occupants.append(pid)


def run_match(seats: list[str], *, seed: int, days: int, universe_size: int = 1000,
              turns_per_day: int = 1000, credits: int = 20_000, ferrengi: bool = True,
              max_steps: int = 2_000_000, port_report: bool = False,
              bank_report: bool = False, corp_report: bool = False,
              corp_policy: str | None = None,
              corp_pairs: list[tuple[str, str]] | None = None,
              action_digest: bool = False, reader_start: str | None = None,
              war_report: bool = False) -> dict[str, Any]:
    """Play the match and return a JSON-ready summary."""
    from tw2k.agents.seat_acceptance import aba_bounces, validate_action
    from tw2k.agents.seat_brain import SeatBrain
    from tw2k.engine import (
        Action,
        GameConfig,
        apply_action,
        build_observation,
        generate_universe,
        is_finished,
        tick_day,
    )
    from tw2k.engine import constants as K
    from tw2k.engine.victory import full_net_worth

    sba = _acceptance()
    makers = {"N1": sba.n1_brain, "N2": sba.n2_brain, "N3": SeatBrain}
    u = generate_universe(GameConfig(seed=seed, universe_size=universe_size, max_days=max(30, days + 2),
                                     turns_per_day=turns_per_day, starting_credits=credits,
                                     enable_ferrengi=ferrengi, enable_planets=True))
    fed = sorted(K.FEDSPACE_SECTORS)
    st: dict[str, dict[str, Any]] = {}
    for i, kind in enumerate(seats):
        pid = f"P{i + 1}"
        p = sba._open_seat(u, pid, fed[i % len(fed)], credits)
        p.name = f"{kind}-{pid}"
        st[pid] = {
            "kind": kind,
            "brain": makers[kind]() if kind in makers else None,
            "agent": _seat_agent(kind, pid, p.name, seed),
            "actions": 0, "kinds": collections.Counter(), "features": collections.Counter(),
            "rej_validate": 0, "rej_engine": 0,
            "rej_top": collections.Counter(), "exceptions": 0, "buys": 0, "sells": 0, "units_sold": 0,
            "realized": 0, "idle_done": False, "zero_streak": 0, "forced_done": 0, "wasted_turns": 0,
            "rows": [], "daily": [], "start_sector": p.sector_id,
            "exp0": int(p.experience), "align0": int(p.alignment),
            "bank_carry": 0, "bank_detours": 0, "broke_days": 0,
        }
    if reader_start == "f1":
        for pid, row in st.items():
            if row["kind"] == "R":
                _place_reader_f1(u, pid)
                row["start_sector"] = u.players[pid].sector_id
    from tw2k.agents import corp_brain
    saved_policy = K.BOT_CORP_POLICY
    if corp_policy:
        K.BOT_CORP_POLICY = corp_policy
    elif K.corp_bots_on() and K.BOT_CORP_POLICY == "off":
        K.BOT_CORP_POLICY = "pair"
    if K.bot_corp_policy() in ("pair", "team"):
        code_ids = [f"P{i + 1}" for i, kind in enumerate(seats) if kind not in ("H", "R")]
        corp_brain.configure(code_ids, seed, explicit=corp_pairs)

    def done(pid: str) -> bool:
        p = u.players[pid]
        return (not p.alive) or st[pid]["idle_done"] or p.turns_today >= p.turns_per_day

    def snap() -> None:
        for pid, s in st.items():
            p = u.players[pid]
            ship = p.ship.ship_class.value
            s["daily"].append({"day": u.day, "net_worth": full_net_worth(u, p), "credits": p.credits,
                               "ship": ship, "alive": p.alive})
            if bank_report and ship in ("escape_pod", "scout_marauder"):
                if int(p.credits) + int(p.bank_balance) < int(K.BOT_BANK_BROKE_LINE):
                    s["broke_days"] += 1

    order = list(st)
    steps = 0
    save_load_day15 = None

    async def play() -> None:
        nonlocal steps, save_load_day15
        idx = 0
        while steps < max_steps:
            if is_finished(u):
                return
            if all(done(pid) for pid in order):
                for pid in order:
                    p = u.players[pid]
                    if p.alive:
                        st[pid]["wasted_turns"] += max(0, p.turns_per_day - p.turns_today)
                snap()
                if corp_report and u.day == 15 and save_load_day15 is None:
                    from tw2k.engine.models import Universe
                    blob = u.model_dump_json()
                    again = Universe.model_validate_json(blob)
                    save_load_day15 = "identical" if again.model_dump_json() == blob else "diff"
                if u.day >= days:
                    return
                tick_day(u)
                for s in st.values():
                    s["idle_done"] = False
                    s["zero_streak"] = 0
                continue
            pid = order[idx % len(order)]
            idx += 1
            if done(pid):
                continue
            s = st[pid]
            p = u.players[pid]
            steps += 1
            obs_model = build_observation(u, pid)
            obs = obs_model.model_dump(mode="json")
            try:
                if s["brain"] is not None:
                    act = s["brain"].decide(obs)
                else:
                    a = await s["agent"].act(obs_model)
                    act = {"kind": getattr(a.kind, "value", str(a.kind)), "args": dict(a.args or {}),
                           "thought": a.thought or ""}
            except Exception:
                s["exceptions"] += 1
                act = {"kind": "wait", "args": {}, "thought": "exception fallback"}
            kind = act["kind"]
            args = act.get("args") or {}
            thought = str(act.get("thought") or "")
            if s["brain"] is not None and validate_action(obs, act):
                s["rej_validate"] += 1
            turns_before = p.turns_today
            sector_before = p.sector_id
            day_before = u.day
            try:
                res = apply_action(u, pid, Action(**{k: act[k] for k in ("kind", "args", "thought") if k in act}))
                ok, err = res.ok, str(res.error or "")
            except Exception:
                s["exceptions"] += 1
                ok, err = False, "engine exception"
            spent = max(0, p.turns_today - turns_before) if u.day == day_before else 0
            s["actions"] += 1
            s["kinds"][kind] += 1
            if kind == "buy_equip" and args.get("item"):
                s["features"][f"buy_equip:{args.get('item')}"] += 1
            elif kind in ("rob", "steal", "terra_colonists", "cloak", "photon_missile",
                          "fire_disruptor", "launch_beacon", "deploy_atomic", "remove_limpet",
                          "deploy_mines"):
                s["features"][kind] += 1
            if not ok:
                s["rej_engine"] += 1
                s["rej_top"][f"{kind}: {err[:80]}"] += 1
                if "out of turns" in err:
                    s["idle_done"] = True
            elif kind == "trade":
                if args.get("side") == "sell":
                    s["sells"] += 1
                    sold = p.trade_log[-1] if p.trade_log else {}
                    s["realized"] += int(sold.get("realized_profit") or 0)
                    s["units_sold"] += int(sold.get("qty") or 0)
                else:
                    s["buys"] += 1
            if ok and bank_report:
                if (int(sector_before) == int(K.STARDOCK_SECTOR)
                        and int(p.sector_id) != int(K.STARDOCK_SECTOR)
                        and kind in ("warp", "plot_course", "ship_transwarp")):
                    s["bank_carry"] = max(int(s["bank_carry"]), int(p.credits))
                if "bank the spare cash on the way" in thought:
                    s["bank_detours"] += 1
            s["rows"].append((sector_before, kind, args.get("target") or args.get("planet_id")))
            if kind == "query_limpets":
                s["idle_done"] = True
            s["zero_streak"] = s["zero_streak"] + 1 if spent == 0 else 0
            if s["zero_streak"] >= STUCK_ZERO_TURN_ACTIONS and not s["idle_done"]:
                s["idle_done"] = True
                s["forced_done"] += 1

    asyncio.run(play())

    players = {}
    for pid, s in st.items():
        p = u.players[pid]
        planets = sorted(pl.id for pl in u.planets.values() if pl.owner_id == pid)
        players[pid] = {
            "seat": s["kind"], "name": p.name, "start_sector": s["start_sector"],
            "net_worth": full_net_worth(u, p), "public_net_worth": p.net_worth, "credits": p.credits,
            "ship": p.ship.ship_class.value, "holds": p.ship.holds, "fighters": p.ship.fighters,
            "planets": planets, "alive": p.alive, "deaths": int(p.deaths),
            "actions": s["actions"], "kinds": dict(sorted(s["kinds"].items())),
            "buys": s["buys"], "sells": s["sells"], "units_sold": s["units_sold"],
            "realized_profit": s["realized"],
            "profit_per_unit": round(s["realized"] / s["units_sold"], 1) if s["units_sold"] else 0.0,
            "rejected_validate": s["rej_validate"], "rejected_engine": s["rej_engine"],
            "rejected_top": [[k, v] for k, v in sorted(s["rej_top"].items(), key=lambda kv: (-kv[1], kv[0]))[:5]],
            "exceptions": s["exceptions"], "forced_done": s["forced_done"], "wasted_turns": s["wasted_turns"],
            "aba_bounces": aba_bounces(s["rows"]), "daily": s["daily"],
        }
        # An all-legacy digest hashes this dict. The key appears only while a tw2002
        # switch that this slice teaches is on, so the legacy golden stays put.
        if K.rob_tw2002() or K.hardware_tw2002() or K.class0_tw2002():
            players[pid]["features"] = dict(sorted(s["features"].items()))
    # Slice 55 match table only. Absent unless asked, so the legacy digest JSON stays put.
    if port_report:
        upgrades: dict[str, dict[str, int]] = {
            pid: {"count": 0, "units": 0, "credits": 0, "exp": 0, "align": 0} for pid in players
        }
        planet_trades: dict[str, dict[str, int]] = {
            pid: {"count": 0, "credits": 0, "qty": 0} for pid in players
        }
        for ev in u.events:
            kind = getattr(ev.kind, "value", str(ev.kind))
            pid = str(ev.actor_id or "")
            payload = ev.payload or {}
            if kind == "port_upgraded" and pid in upgrades:
                upgrades[pid]["count"] += 1
                upgrades[pid]["units"] += int(payload.get("units") or 0)
                upgrades[pid]["credits"] += int(payload.get("cost") or 0)
                upgrades[pid]["exp"] += int(payload.get("exp") or 0)
                upgrades[pid]["align"] += int(payload.get("align") or 0)
            elif kind == "planet_trade" and pid in planet_trades:
                planet_trades[pid]["count"] += 1
                planet_trades[pid]["credits"] += int(payload.get("price") or 0)
                planet_trades[pid]["qty"] += int(payload.get("qty") or 0)
        violations = 0
        for sector in u.sectors.values():
            port = sector.port
            if port is None:
                continue
            for row in getattr(port, "stock", {}).values():
                if hasattr(K, "PORT_UPGRADE_MAX_HOLDS") and int(row.maximum) > int(K.PORT_UPGRADE_MAX_HOLDS):
                    violations += 1
            cons = getattr(port, "construction", None)
            if cons and int(cons.get("days_left") or 0) < 0:
                violations += 1
        for pid, row in players.items():
            p = u.players[pid]
            row["experience"] = int(p.experience)
            row["alignment"] = int(p.alignment)
            row["exp_delta"] = int(p.experience) - int(st[pid]["exp0"])
            row["align_delta"] = int(p.alignment) - int(st[pid]["align0"])
            row["port_upgraded"] = upgrades[pid]
            row["planet_trade"] = planet_trades[pid]
    else:
        violations = None
    bank_rows = None
    if bank_report:
        from tw2k.agents.bank_brain import nest_egg
        bank_rows = fold_bank_events(u.events, list(players))
        for pid, row in players.items():
            balance = int(u.players[pid].bank_balance)
            egg = nest_egg(int(row.get("net_worth") or 0))
            bank_rows[pid]["nest_egg"] = egg
            bank_rows[pid]["max_carry"] = int(st[pid]["bank_carry"])
            bank_rows[pid]["detours"] = int(st[pid]["bank_detours"])
            bank_rows[pid]["broke_days"] = int(st[pid]["broke_days"])
            row["bank_balance"] = balance
            row["bank"] = bank_rows[pid]
    corp_summary = None
    if corp_report:  # CORP_RULES.md match check (c)/(d)/(f) counters (QC 57); not part of any digest
        counts: dict[str, int] = {}
        corporate_deploys = {pid: 0 for pid in players}
        hostile_between_members = 0
        mate_tolls = 0
        attacks = {"combat", "fighter_challenge", "ship_destroyed", "mine_detonated", "photon_hit"}
        for ev in u.events:
            kind = getattr(ev.kind, "value", str(ev.kind))
            payload = ev.payload or {}
            if kind.startswith("corp_"):
                counts[kind] = counts.get(kind, 0) + 1
            pid = str(ev.actor_id or "")
            if kind in ("deploy_fighters", "deploy_mines") and payload.get("ownership") == "corporate" and pid in players:
                corporate_deploys[pid] += 1
            if kind in attacks or kind == "toll":
                if pid in u.players and u.players[pid].corp_ticker:
                    blob = json.dumps(payload, sort_keys=True, default=str)
                    mates = set(u.corporations.get(u.players[pid].corp_ticker).member_ids
                                if u.players[pid].corp_ticker in u.corporations else ()) - {pid}
                    if any(f'"{m}"' in blob for m in mates):
                        if kind == "toll":
                            mate_tolls += 1
                        else:
                            hostile_between_members += 1
        rogue_groups = 0
        corporate_groups = 0
        for sec in u.sectors.values():
            groups = ([sec.fighters] if sec.fighters is not None else []) + list(sec.mines or [])
            for g in groups:
                if g.owner_id == K.ROGUE_OWNER_ID:
                    rogue_groups += 1
                elif getattr(g, "corp_ticker", None):
                    corporate_groups += 1
        corp_summary = {
            "corps": {t: sorted(c.member_ids) for t, c in sorted(u.corporations.items())},
            "events": dict(sorted(counts.items())), "corporate_deploys": corporate_deploys,
            "hostile_between_members": hostile_between_members, "mate_tolls": mate_tolls,
            "save_load_day15": save_load_day15, "rogue_groups": rogue_groups,
            "corporate_groups": corporate_groups, "policy": K.BOT_CORP_POLICY, "mode": K.CORP_MODE,
        }
        for pid, row in players.items():
            row["corp_ticker"] = u.players[pid].corp_ticker
    ranking = sorted(players, key=lambda q: (-players[q]["net_worth"], q))
    result = {
        "seed": seed, "days": days, "days_played": u.day, "seats": seats, "universe_size": universe_size,
        "turns_per_day": turns_per_day, "start_credits": credits, "ferrengi": ferrengi,
        "economy_mode": K.ECONOMY_SCALE_MODE, "commodity_base": dict(K.COMMODITY_BASE_PRICE.items()),
        "steps": steps, "finished": bool(u.finished), "winner": u.winner_id, "win_reason": u.win_reason,
        "ranking": ranking, "players": players,
    }
    if violations is not None:
        result["invariant_violations"] = violations
    if action_digest:
        blob = [[pid, st[pid]["rows"]] for pid in sorted(st)]
        result["action_digest"] = format(zlib.crc32(json.dumps(blob).encode()), "08x")
    if corp_summary is not None:
        result["corp"] = corp_summary
    if war_report:
        from tw2k.agents.war_report import counts_from_events
        result["war"] = counts_from_events(list(u.events))
    if bank_rows is not None:
        result["bank_rejected"] = sum(int(row["rejected_engine"]) for row in players.values())
        result["bank_exceptions"] = sum(int(row["exceptions"]) for row in players.values())
        result["ferrengi_credits"] = sum(int(ship.credits) for ship in (getattr(u, "ferrengi", None) or {}).values())
        from tw2k.engine.models import Universe
        again = Universe.model_validate_json(u.model_dump_json())
        result["bank_save_load"] = "identical" if again.model_dump_json() == u.model_dump_json() else "diff"
    K.BOT_CORP_POLICY = saved_policy
    corp_brain.clear()
    return result


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# Scripted match: seed {result['seed']}, {result['days_played']} of {result['days']} days",
        "",
        f"Seats {','.join(result['seats'])}; universe {result['universe_size']}; "
        f"{result['turns_per_day']} turns/day; start {result['start_credits']:,} credits; "
        f"Ferrengi {'on' if result['ferrengi'] else 'off'}; economy {result['economy_mode']} "
        f"(bases {', '.join(f'{k} {v}' for k, v in result['commodity_base'].items())}).",
        "",
        "| # | Seat | Net worth | Credits | Ship | Planets | Alive | Deaths | Sells | Profit/unit | Rejected (check/engine) | Exceptions |",
        "|---|------|-----------|---------|------|---------|-------|--------|-------|-------------|-------------------------|------------|",
    ]
    for rank, pid in enumerate(result["ranking"], 1):
        r = result["players"][pid]
        lines.append(
            f"| {rank} | {r['name']} | {r['net_worth']:,} | {r['credits']:,} | {r['ship']} | {len(r['planets'])} | "
            f"{'yes' if r['alive'] else 'no'} | {r['deaths']} | {r['sells']} | {r['profit_per_unit']} | "
            f"{r['rejected_validate']}/{r['rejected_engine']} | {r['exceptions']} |"
        )
    lines += ["", "Net worth by day:", ""]
    for pid in result["ranking"]:
        r = result["players"][pid]
        lines.append(f"- {r['name']}: " + ", ".join(f"d{d['day']} {d['net_worth']:,}" for d in r["daily"]))
    if result["finished"]:
        lines += ["", f"Finished early: winner {result['winner']} ({result['win_reason']})."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seats", default="N3,N2,N1,H", help="comma list of N1, N2, N3, H")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--size", type=int, default=1000, help="universe size (sectors)")
    ap.add_argument("--turns-per-day", type=int, default=1000)
    ap.add_argument("--credits", type=int, default=20_000)
    ap.add_argument("--no-ferrengi", action="store_true")
    ap.add_argument("--port-report", action="store_true",
                    help="add port-upgrade and planet-trade totals (not part of the legacy digest)")
    ap.add_argument("--bank-report", action="store_true",
                    help="add bank, tax, and death-credit totals (not part of the legacy digest)")
    ap.add_argument("--bank-legacy", action="store_true",
                    help="run with BANK_MODE legacy (the before column)")
    ap.add_argument("--treasury-policy", choices=("overflow", "spare", "off"),
                    help="set BOT_TREASURY_POLICY for this run")
    ap.add_argument("--detour-hops", type=int,
                    help="set BOT_BANK_DETOUR_HOPS_ON for this run (0 turns the detour off)")
    ap.add_argument("--corp-policy", choices=("off", "pair", "team"),
                    help="override K.BOT_CORP_POLICY (default pair while CORP_BOTS_MODE is tw2002)")
    ap.add_argument("--bot-corp-pairs", default="",
                    help="explicit pairs, P1:P3,P2:P4. Empty uses consecutive code seats")
    ap.add_argument("--corp-report", action="store_true",
                    help="add corp counters (corps, members, corp events, rogue groups; not part of the legacy digest)")
    ap.add_argument("--llm-parity", choices=("tw2002", "legacy"),
                    help="set LLM_PARITY_MODE for this run (bots ignore the prompt; the action digest must match)")
    ap.add_argument("--tavern", choices=("tw2002", "legacy"),
                    help="set TAVERN_MODE for this run (code bots do not use the Tavern)")
    ap.add_argument("--reader-start", choices=("f1",),
                    help="move an R seat 10 hops from StarDock with 250000 credits")
    ap.add_argument("--action-digest", action="store_true",
                    help="add a checksum of each seat's action rows (not part of the legacy digest)")
    ap.add_argument("--bots-war", choices=("tw2002", "legacy"),
                    help="set BOTS_WAR_MODE for this run")
    ap.add_argument("--corp-fix", choices=("tw2002", "legacy"),
                    help="set CORP_FIX_MODE for this run")
    ap.add_argument("--h-recovery", choices=("tw2002", "legacy"),
                    help="set H_RECOVERY_MODE for this run")
    ap.add_argument("--war-policy", choices=("full", "defend", "off"),
                    help="set BOT_WAR_POLICY for this run")
    ap.add_argument("--war-report", action="store_true",
                    help="print war verb counts (not part of the legacy digest)")
    ap.add_argument("--json", dest="json_out", help="write the JSON summary here")
    ap.add_argument("--md", dest="md_out", help="write the markdown summary here")
    a = ap.parse_args(argv)
    if a.bank_legacy or a.llm_parity or a.treasury_policy or a.detour_hops is not None or a.tavern or a.bots_war or a.war_policy or a.corp_fix or a.h_recovery:
        from tw2k.engine import constants as K
        if a.bank_legacy:
            K.BANK_MODE = "legacy"
        if a.llm_parity:
            K.LLM_PARITY_MODE = a.llm_parity
        if a.tavern:
            K.TAVERN_MODE = a.tavern
        if a.bots_war:
            K.BOTS_WAR_MODE = a.bots_war
        if a.war_policy:
            K.BOT_WAR_POLICY = a.war_policy
        if a.corp_fix:
            K.CORP_FIX_MODE = a.corp_fix
        if a.h_recovery:
            K.H_RECOVERY_MODE = a.h_recovery
        if a.treasury_policy:
            K.BOT_TREASURY_POLICY = a.treasury_policy
        if a.detour_hops is not None:
            K.BOT_BANK_DETOUR_HOPS_ON = int(a.detour_hops)
    pairs = None
    if a.bot_corp_pairs.strip():
        pairs = []
        for item in a.bot_corp_pairs.split(","):
            left, right = item.split(":")
            pairs.append((left.strip(), right.strip()))
    result = run_match(parse_seats(a.seats), seed=a.seed, days=a.days, universe_size=a.size,
                       turns_per_day=a.turns_per_day, credits=a.credits, ferrengi=not a.no_ferrengi,
                       port_report=a.port_report, bank_report=a.bank_report,
                       corp_report=a.corp_report, corp_policy=a.corp_policy, corp_pairs=pairs,
                       action_digest=a.action_digest, reader_start=a.reader_start,
                       war_report=a.war_report)
    text = json.dumps(result, indent=1, sort_keys=True)
    md = render_markdown(result)
    if a.json_out:
        Path(a.json_out).write_text(text + "\n", encoding="utf-8")
    if a.md_out:
        Path(a.md_out).write_text(md, encoding="utf-8")
    print(md)
    if a.action_digest:
        print(f"ACTION_DIGEST {result['action_digest']}")
    if a.bank_report:
        print(f"BANK rejected {result['bank_rejected']} exceptions {result['bank_exceptions']} "
              f"ferrengi_credits {result['ferrengi_credits']} save {result['bank_save_load']}")
        for pid in result["ranking"]:
            row = result["players"][pid]
            b = row.get("bank") or {}
            print(f"BANK {pid} {row['seat']} nw {row['net_worth']} cash {row['credits']} "
                  f"balance {row.get('bank_balance')} dep {b.get('deposited')} wd {b.get('withdrawn')} "
                  f"tax {b.get('tax')} align {b.get('tax_align')} lost {b.get('credits_lost')} "
                  f"lost_n {b.get('credits_lost_count')} lost_max {b.get('credits_lost_largest')} "
                  f"recovered {b.get('credits_recovered')} treas {b.get('treasury_deposited')} "
                  f"treas_wd {b.get('treasury_withdrawn')} egg {b.get('nest_egg')} "
                  f"carry {b.get('max_carry')} detour {b.get('detours')} broke {b.get('broke_days')} "
                  f"rej {row['rejected_engine']}")
    if a.corp_report:
        print("CORP " + json.dumps(result["corp"], sort_keys=True))
    if a.war_report:
        print("WAR_REPORT " + json.dumps(result.get("war") or {}, sort_keys=True))
    return 0


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        env = dict(os.environ, PYTHONHASHSEED="0")
        sys.exit(subprocess.call([sys.executable, *sys.argv], env=env))
    sys.exit(main())
