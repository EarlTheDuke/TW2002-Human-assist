#!/usr/bin/env python3
"""NOTE 160. Ten days with every v3.11 switch on, in this process only.

Lineup, in seat order:

* AI cockpit and AI cockpit 2, decided by the cockpit scripted trader
  (``tw2k.agents.cockpit_seat.SeatBrain``). No model key. AI cockpit also
  sets NavPoint "Lane" on a neighboring sector and plots that name once.
* Code bots N3, N2, N1, and the heuristic H.

``V311_PROFILE`` is set to ``v311`` here and is not written back. The stored
default stays legacy. ``AI_COCKPIT_SEAT_MODE`` is set to ``tw2002`` in this
process so the two cockpit seats are the ones a form would launch. The
profile does not turn that switch on, and this script does not change the
stored value.

    PYTHONHASHSEED=0 python3 scripts/v311_note160_soak.py --seed 250925
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
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Code bots first in the report's words, then the two scripted cockpit seats.
# Spawn order matches the lobby: cockpit seats, then code bots.
LINEUP = (
    ("scripted", "AI cockpit"),
    ("scripted", "AI cockpit 2"),
    ("N3", "N3"),
    ("N2", "N2"),
    ("N1", "N1"),
    ("H", "H"),
)
STUCK_ZERO = 200
PRICE_CEILING = 100_000


def _acceptance():
    spec = importlib.util.spec_from_file_location(
        "seat_brain_acceptance_note160", ROOT / "scripts" / "seat_brain_acceptance.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _player_bits(universe, player, day: int, pid: str) -> list[dict[str, Any]]:
    """Cheap checks after one action. The day-end audit repeats the full board."""
    del universe
    from tw2k.engine import constants as K

    rows: list[dict[str, Any]] = []

    def add(what: str) -> None:
        rows.append({"day": day, "what": what, "where": pid})

    ship = player.ship
    if int(player.credits) < 0:
        add(f"negative credits {player.credits}")
    if int(player.bank_balance) < 0:
        add(f"negative bank {player.bank_balance}")
    if int(ship.fighters) < 0:
        add(f"negative fighters {ship.fighters}")
    if int(ship.shields) < 0:
        add(f"negative shields {ship.shields}")
    if int(ship.cargo_used) > int(ship.holds):
        add(f"cargo uses {ship.cargo_used} holds but the ship has {ship.holds}")
    spec = K.hull_spec(ship.ship_class.value) or {}
    room = spec.get("max_fighters")
    if room is not None and int(ship.fighters) > int(room):
        add(f"fighters {ship.fighters} exceed {ship.ship_class.value} room {room}")
    return rows


def _audit(universe, day: int) -> list[dict[str, Any]]:
    """Negatives, impossible prices, and stock that cannot exist."""
    from tw2k.engine import constants as K
    from tw2k.engine.victory import full_net_worth

    rows: list[dict[str, Any]] = []

    def add(what: str, where: str) -> None:
        rows.append({"day": day, "what": what, "where": where})

    for pid, player in universe.players.items():
        ship = player.ship
        if int(player.credits) < 0:
            add(f"negative credits {player.credits}", pid)
        if int(player.experience) < 0:
            add(f"negative experience {player.experience}", pid)
        if int(player.alignment) < -1_000_000 or int(player.alignment) > 1_000_000:
            add(f"alignment outlier {player.alignment}", pid)
        if int(player.bank_balance) < 0:
            add(f"negative bank {player.bank_balance}", pid)
        if int(ship.fighters) < 0:
            add(f"negative fighters {ship.fighters}", pid)
        if int(ship.shields) < 0:
            add(f"negative shields {ship.shields}", pid)
        if int(ship.holds) < 0:
            add(f"negative holds {ship.holds}", pid)
        for key, qty in (ship.cargo or {}).items():
            if int(qty or 0) < 0:
                add(f"negative cargo {key} {qty}", pid)
        used = int(ship.cargo_used)
        if used > int(ship.holds):
            add(f"cargo uses {used} holds but the ship has {ship.holds}", pid)
        spec = K.hull_spec(ship.ship_class.value) or {}
        room = spec.get("max_fighters")
        if room is not None and int(ship.fighters) > int(room):
            add(f"fighters {ship.fighters} exceed {ship.ship_class.value} room {room}", pid)
        try:
            worth = int(full_net_worth(universe, player))
        except Exception as exc:
            add(f"net worth crashed: {exc.__class__.__name__}", pid)
            worth = 0
        if worth < 0:
            add(f"negative net worth {worth}", pid)
        for row in player.trade_log or []:
            price = row.get("price")
            qty = int(row.get("qty") or 0)
            if price is None:
                continue
            try:
                unit = int(price)
            except (TypeError, ValueError):
                add(f"non-numeric trade price {price!r}", pid)
                continue
            if unit <= 0 or unit > PRICE_CEILING:
                add(f"impossible trade price {unit} qty {qty} {row.get('commodity')}", pid)
        for row in player.trade_log or []:
            unit = row.get("unit")
            if unit is None:
                continue
            try:
                unit = int(unit)
            except (TypeError, ValueError):
                add(f"non-numeric trade unit {row.get('unit')!r}", pid)
                continue
            if unit <= 0 or unit > PRICE_CEILING:
                add(f"impossible trade unit {unit} qty {row.get('qty')} {row.get('commodity')}", pid)
            if int(row.get("qty") or 0) < 0:
                add(f"negative trade qty {row.get('qty')}", pid)
    for sid, sector in universe.sectors.items():
        port = sector.port
        if port is not None:
            if int(getattr(port, "credits", 0) or 0) < 0:
                add(f"negative port credits {port.credits}", f"sector {sid}")
            for key, stock in (port.stock or {}).items():
                current = int(stock.current)
                maximum = int(stock.maximum)
                if current < 0 or maximum < 0:
                    add(f"negative port stock {key} {current}/{maximum}", f"sector {sid}")
                elif current > maximum:
                    add(f"port stock over max {key} {current}/{maximum}", f"sector {sid}")
        group = getattr(sector, "fighters", None)
        if group is not None and int(getattr(group, "count", 0) or 0) < 0:
            add(f"negative sector fighters {group.count}", f"sector {sid}")
        for mine in sector.mines or []:
            if int(getattr(mine, "count", 0) or 0) < 0:
                add(f"negative mines {mine.count}", f"sector {sid}")
    from tw2k.engine.economy import port_buy_price, port_sell_price
    from tw2k.engine.models import Commodity

    for sid, sector in universe.sectors.items():
        port = sector.port
        if port is None:
            continue
        for commodity in (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT):
            if commodity not in (port.stock or {}):
                continue
            try:
                if port.buys(commodity):
                    price = int(port_buy_price(port, commodity, 0))
                elif port.sells(commodity):
                    price = int(port_sell_price(port, commodity, 0))
                else:
                    continue
            except Exception as exc:
                add(f"price crashed {commodity.value}: {exc.__class__.__name__}", f"sector {sid}")
                continue
            if price <= 0 or price > PRICE_CEILING:
                add(f"impossible {commodity.value} price {price}", f"sector {sid}")
    for pid, planet in universe.planets.items():
        for key, qty in (planet.colonists or {}).items():
            if int(qty or 0) < 0:
                add(f"negative colonists {key} {qty}", f"planet {pid}")
        if int(getattr(planet, "treasury", 0) or 0) < 0:
            add(f"negative treasury {planet.treasury}", f"planet {pid}")
        fighters = int(getattr(planet, "fighters", 0) or 0)
        if fighters < 0:
            add(f"negative planet fighters {fighters}", f"planet {pid}")
    return rows


def run_soak(seed: int, days: int, universe_size: int) -> dict[str, Any]:
    from tw2k.agents.cockpit_seat import SeatBrain as ScriptedTrader
    from tw2k.engine import Action, GameConfig, apply_action, build_observation, generate_universe, is_finished, tick_day
    from tw2k.engine import constants as K
    from tw2k.engine.models import Player, Ship
    from tw2k.engine.presence import mark_ai_cockpit
    from tw2k.engine.runner import grant_starting_planet, inactive_clock
    from tw2k.engine.victory import full_net_worth

    K.V311_PROFILE = "v311"
    K.AI_COCKPIT_SEAT_MODE = "tw2002"
    assert K.v311_profile() is True
    assert K.TW2002_LIVE_PROFILE == "legacy"

    sba = _acceptance()
    makers = {"N1": sba.n1_brain, "N2": sba.n2_brain, "N3": sba.SeatBrain}
    universe = generate_universe(GameConfig(
        seed=seed, universe_size=universe_size, max_days=max(30, days + 2),
        turns_per_day=K.STARTING_TURNS_PER_DAY, starting_credits=K.STARTING_CREDITS,
        enable_ferrengi=True, enable_planets=True,
    ))
    fed = sorted(K.FEDSPACE_SECTORS)
    start_order = [fed[0]] + [s for s in fed if s != fed[0]]
    state: dict[str, dict[str, Any]] = {}
    for i, (kind, name) in enumerate(LINEUP):
        pid = f"P{i + 1}"
        start_sid = start_order[i % len(start_order)]
        credits, turns, fighters = K.opening_loadout(
            K.STARTING_CREDITS, K.STARTING_TURNS_PER_DAY, i, None, None)
        ship = Ship()
        ship.fighters = fighters
        player = Player(
            id=pid, name=name, credits=credits, turns_per_day=turns, ship=ship,
            sector_id=start_sid, agent_kind="external" if kind == "scripted" else "heuristic",
        )
        universe.players[pid] = player
        universe.sectors[start_sid].occupant_ids.append(pid)
        mark_ai_cockpit(player)
        if getattr(universe, "inactive_users_armed", False):
            player.last_action_at = float(inactive_clock())
        if K.starting_package_live():
            grant_starting_planet(universe, player)
        player.known_sectors.add(int(player.sector_id))
        sector = universe.sectors[player.sector_id]
        player.known_warps[int(player.sector_id)] = list(sector.warps)
        if sector.port is not None:
            player.known_ports[int(player.sector_id)] = {
                "class": sector.port.code,
                "stock": {c.value: {"current": s.current, "max": s.maximum} for c, s in sector.port.stock.items()},
                "last_seen_day": universe.day,
            }
        brain = None
        agent = None
        if kind == "scripted":
            brain = ScriptedTrader(days)
        elif kind in makers:
            brain = makers[kind]()
        else:
            from tw2k.agents import HeuristicAgent
            import zlib
            agent = HeuristicAgent(pid, name, seed=zlib.crc32(f"{seed}:{pid}".encode()))
        state[pid] = {
            "kind": kind, "name": name, "brain": brain, "agent": agent,
            "actions": 0, "ok": 0, "rejected": 0, "exceptions": 0,
            "rej_top": collections.Counter(), "samples": [],
            "forced_done": 0, "idle_done": False, "zero_streak": 0,
            "trace": [], "kinds": collections.Counter(),
        }

    findings = _audit(universe, int(universe.day))
    day_rows: list[dict[str, Any]] = []
    # AI cockpit sets one NavPoint and lays in a course to it. The other
    # cockpit seat keeps trading. A failed try is retried on a later turn.
    nav = {"set": False, "used": False, "sector": None, "set_day": None, "use_day": None, "errors": []}

    def cockpit_nav(pid: str, player, obs: dict) -> dict[str, Any] | None:
        if player.name != "AI cockpit":
            return None
        if nav["used"] or len(nav["errors"]) >= 8:
            return None
        if player.planet_landed or obs.get("fighter_challenge") or obs.get("ferrengi_encounter"):
            return None
        here = int(player.sector_id)
        if not nav["set"]:
            hops = [int(w) for w in universe.sectors[here].warps if int(w) in universe.sectors]
            if not hops:
                return None
            nav["sector"] = hops[0]
            return {
                "kind": "navpoint",
                "args": {"op": "set", "slot": 1, "name": "Lane", "sector": hops[0]},
                "thought": "log NavPoint Lane",
            }
        return {
            "kind": "plot_course",
            "args": {"navpoint": "Lane", "execute": True},
            "thought": "lay in NavPoint Lane",
        }
    order = list(state)
    steps = 0
    max_steps = 400_000

    def done(pid: str) -> bool:
        player = universe.players[pid]
        row = state[pid]
        return (not player.alive) or row["idle_done"] or int(player.turns_today) >= int(player.turns_per_day)

    def snap(why: str) -> None:
        seats = {}
        for pid in order:
            player = universe.players[pid]
            seats[pid] = {
                "name": player.name,
                "kind": state[pid]["kind"],
                "credits": int(player.credits),
                "net_worth": int(full_net_worth(universe, player)),
                "fighters": int(player.ship.fighters),
                "sector": int(player.sector_id),
                "landed": player.planet_landed,
                "turns_used": int(player.turns_today),
                "ship": player.ship.ship_class.value,
                "alive": bool(player.alive),
                "ok": state[pid]["ok"],
                "rejected": state[pid]["rejected"],
                "exceptions": state[pid]["exceptions"],
                "kinds": dict(state[pid]["kinds"]),
            }
        day_rows.append({"day": int(universe.day), "why": why, "seats": seats})
        print(
            f"day {universe.day} {why} " + " ".join(
                f"{pid}:{seats[pid]['credits']}/{seats[pid]['net_worth']}@{seats[pid]['sector']}"
                f" r{seats[pid]['rejected']}" for pid in order),
            flush=True)

    async def play() -> None:
        nonlocal steps
        idx = 0
        while steps < max_steps:
            if is_finished(universe) or getattr(universe, "game_over", False):
                snap("finished")
                return
            if all(done(pid) for pid in order):
                snap("day-end")
                fresh = _audit(universe, int(universe.day))
                findings.extend(fresh)
                if int(universe.day) >= days:
                    return
                tick_day(universe)
                if K.starting_package_live() or K.turn_regen_live():
                    for pid in order:
                        if universe.players[pid].alive:
                            universe.players[pid].turns_today = 0
                for row in state.values():
                    row["idle_done"] = False
                    row["zero_streak"] = 0
                continue
            pid = order[idx % len(order)]
            idx += 1
            if done(pid):
                continue
            row = state[pid]
            player = universe.players[pid]
            steps += 1
            obs_model = build_observation(universe, pid)
            obs = obs_model.model_dump(mode="json")
            try:
                steered = cockpit_nav(pid, player, obs) if row["kind"] == "scripted" else None
                if steered is not None:
                    act = steered
                elif row["kind"] == "scripted":
                    kind, args, thought = row["brain"].decide(obs)
                    act = {"kind": kind, "args": args, "thought": thought}
                elif row["brain"] is not None:
                    act = row["brain"].decide(obs)
                else:
                    action = await row["agent"].act(obs_model)
                    act = {
                        "kind": getattr(action.kind, "value", str(action.kind)),
                        "args": dict(action.args or {}),
                        "thought": action.thought or "",
                    }
            except Exception:
                row["exceptions"] += 1
                if len(row["trace"]) < 4:
                    row["trace"].append(traceback.format_exc()[-800:])
                findings.append({
                    "day": int(universe.day),
                    "what": f"{row['name']} decide crashed",
                    "where": pid,
                })
                act = {"kind": "wait", "args": {}, "thought": "exception fallback"}
            kind = str(act.get("kind") or "wait")
            turns_before = int(player.turns_today)
            day_before = int(universe.day)
            try:
                res = apply_action(universe, pid, Action(
                    kind=kind, args=dict(act.get("args") or {}), thought=str(act.get("thought") or "")))
                ok, err = bool(res.ok), str(res.error or "")
            except Exception:
                row["exceptions"] += 1
                ok, err = False, "engine exception"
                if len(row["trace"]) < 4:
                    row["trace"].append(traceback.format_exc()[-800:])
                findings.append({
                    "day": int(universe.day),
                    "what": f"{row['name']} apply {kind} crashed",
                    "where": pid,
                })
            spent = max(0, int(player.turns_today) - turns_before) if int(universe.day) == day_before else 0
            row["actions"] += 1
            row["kinds"][kind] += 1
            if player.name == "AI cockpit" and act.get("thought") in ("log NavPoint Lane", "lay in NavPoint Lane"):
                if ok and kind == "navpoint":
                    nav["set"] = True
                    nav["set_day"] = int(universe.day)
                elif ok and kind == "plot_course":
                    nav["used"] = True
                    nav["use_day"] = int(universe.day)
                elif not ok and len(nav["errors"]) < 8:
                    nav["errors"].append(f"d{universe.day} {kind}: {err[:120]}")
                    if kind == "navpoint":
                        nav["set"] = False
            seen = {(item["where"], item["what"]) for item in findings}
            for item in _player_bits(universe, universe.players[pid], int(universe.day), pid):
                if (item["where"], item["what"]) not in seen:
                    findings.append(item)
            if ok:
                row["ok"] += 1
            else:
                row["rejected"] += 1
                row["rej_top"][f"{kind}: {err[:90]}"] += 1
                if len(row["samples"]) < 8:
                    row["samples"].append(f"d{universe.day} {kind}: {err[:120]}")
                if "out of turns" in err:
                    row["idle_done"] = True
            row["zero_streak"] = row["zero_streak"] + 1 if spent == 0 else 0
            if row["zero_streak"] >= STUCK_ZERO and not row["idle_done"]:
                row["idle_done"] = True
                row["forced_done"] += 1
                findings.append({
                    "day": int(universe.day),
                    "what": f"{row['name']} stuck after {STUCK_ZERO} zero-turn actions (last {kind})",
                    "where": pid,
                })
        findings.append({"day": int(universe.day), "what": "step budget exhausted before the day cap", "where": "match"})
        snap("budget")

    prior = K.regen_now
    K.regen_now = lambda: 0.0
    try:
        asyncio.run(play())
    finally:
        K.regen_now = prior

    if not nav["set"] or not nav["used"]:
        findings.append({
            "day": int(nav["use_day"] or nav["set_day"] or universe.day),
            "what": (
                f"AI cockpit did not set and use a NavPoint "
                f"(set={nav['set']} used={nav['used']} {nav['errors']})"
            ),
            "where": "P1",
        })

    # Worth path: a seat that ends more than 20x its day-1 worth, and grew
    # by at least a million, is an outlier. Day 1 includes the home planet.
    if day_rows:
        opened = day_rows[0]["seats"]
        closed = day_rows[-1]["seats"]
        for pid, end in closed.items():
            start = int(opened.get(pid, {}).get("net_worth") or 0)
            if start > 0 and int(end["net_worth"]) > max(start * 20, start + 1_000_000):
                findings.append({
                    "day": int(end and day_rows[-1]["day"]),
                    "what": f"net worth {start:,} -> {int(end['net_worth']):,}",
                    "where": pid,
                })
    seats = {}
    for pid, row in state.items():
        player = universe.players[pid]
        seats[pid] = {
            "name": player.name, "kind": row["kind"],
            "credits": int(player.credits),
            "net_worth": int(full_net_worth(universe, player)),
            "fighters": int(player.ship.fighters),
            "ship": player.ship.ship_class.value,
            "alive": bool(player.alive),
            "sector": int(player.sector_id),
            "actions": row["actions"], "ok": row["ok"], "rejected": row["rejected"],
            "exceptions": row["exceptions"], "forced_done": row["forced_done"],
            "rejected_top": [[k, v] for k, v in row["rej_top"].most_common(6)],
            "samples": row["samples"], "trace": row["trace"],
        }
    return {
        "seed": seed, "days_asked": days, "day_reached": int(universe.day),
        "status": "finished" if (is_finished(universe) or int(universe.day) >= days) else "stopped",
        "game_over": bool(getattr(universe, "game_over", False)),
        "win_reason": universe.win_reason, "steps": steps,
        "profile": K.V311_PROFILE, "helpers_on": sum(1 for name in K.V311_PROFILE_HELPERS if getattr(K, name)()),
        "findings": findings, "days": day_rows, "seats": seats,
        "navpoint": nav,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--size", type=int, default=1000)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    result = run_soak(args.seed, args.days, args.size)
    text = json.dumps(result, indent=1, default=str)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    point = result.get("navpoint") or {}
    print(f"SOAK seed {result['seed']} day {result['day_reached']} steps {result['steps']} "
          f"findings {len(result['findings'])} game_over {result['game_over']} "
          f"nav set={point.get('set')} d{point.get('set_day')} sector {point.get('sector')} "
          f"used={point.get('used')} d{point.get('use_day')}")
    for row in result["findings"][:40]:
        print(f"FIND d{row['day']} {row['where']}: {row['what']}")
    return 0


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":
        env = dict(os.environ, PYTHONHASHSEED="0")
        raise SystemExit(subprocess.call([sys.executable, *sys.argv], env=env))
    raise SystemExit(main())
