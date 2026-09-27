"""`run_route` macro for external (computer-use) seats - grokbot-player G6.

One CU click covers many game turns: trade a port pair A <-> B for N cycles.
The planner is pure and fog-safe: it reads only the seat's own Observation
(sector, ship, legal_actions envelope) and returns ONE ordinary action for the
current turn, or a stop reason. The runner applies each step with the normal
engine rules, one real turn at a time inside the seat's held slot, so a step
can never skip a rule; if the engine rejects a step the macro stops.

Cycle: at A sell what B sold us, buy `buy_at_a`, travel to B; at B sell it,
buy `buy_at_b`, travel back to A. Arriving at A again completes a cycle.
Trades are at list price (auto-accept, no haggle).
"""

from __future__ import annotations

from typing import Any

COMMODITIES = ("fuel_ore", "organics", "equipment")
MAX_CYCLES = 10
MAX_STEPS = 80


def new_plan(a: int, b: int, buy_at_a: str, buy_at_b: str, cycles: int) -> dict[str, Any]:
    if a == b:
        raise ValueError("a and b must differ")
    for c in (buy_at_a, buy_at_b):
        if c not in COMMODITIES:
            raise ValueError(f"unknown commodity {c!r}")
    if buy_at_a == buy_at_b:
        raise ValueError("buy_at_a and buy_at_b must differ")
    if not 1 <= int(cycles) <= MAX_CYCLES:
        raise ValueError(f"cycles must be 1..{MAX_CYCLES}")
    return {"kind": "run_route", "a": int(a), "b": int(b), "buy_at_a": buy_at_a, "buy_at_b": buy_at_b,
            "cycles": int(cycles), "cycles_done": 0, "steps": 0, "bought_here": None, "visited_b": False,
            "started_at_route": False}


def _legal(obs: dict, kind: str) -> dict:
    for la in obs.get("legal_actions") or []:
        if la.get("kind") == kind:
            return la
    return {"kind": kind, "legal": False, "reason": "no legality data", "params": {}}


def _enemy_here(obs: dict) -> str | None:
    s = obs.get("sector") or {}
    me = obs.get("self_id")
    mates = {o.get("id") for o in obs.get("other_players") or [] if o.get("is_corpmate")}
    others = [o for o in s.get("occupants") or [] if o != me and o not in mates]
    if others:
        return f"another commander in sector ({', '.join(others)})"
    fg = s.get("fighter_group") or {}
    if fg.get("count") and fg.get("owner_id") not in (me, None) and fg.get("owner_id") not in mates:
        return f"hostile fighters in sector (owner {fg.get('owner_id')})"
    if s.get("ferrengi"):
        return "Ferrengi in sector"
    return None


def _affordable(obs: dict, la: dict) -> str | None:
    if not la.get("legal"):
        return la.get("reason") or "not legal now"
    cost = int(la.get("turn_cost") or 0)
    if cost > int(obs.get("turns_remaining") or 0):
        return f"low turns ({obs.get('turns_remaining')} left, next step needs {cost})"
    return None


def _travel(obs: dict, target: int) -> tuple[dict | None, str | None]:
    warps = (obs.get("sector") or {}).get("warps_out") or []
    if target in warps:
        la = _legal(obs, "warp")
        why = _affordable(obs, la)
        return (None, why) if why else ({"kind": "warp", "args": {"target": target}}, None)
    la = _legal(obs, "plot_course")
    why = _affordable(obs, la)
    if why:
        return None, f"cannot plot to {target}: {why}"
    return {"kind": "plot_course", "args": {"target": target, "execute": True}}, None


def _trade(obs: dict, side: str, commodity: str) -> tuple[dict | None, str | None]:
    la = _legal(obs, "trade")
    why = _affordable(obs, la)
    if why:
        return None, why
    p = la.get("params") or {}
    choices = (p.get("commodity") or {}).get(f"{side}_choices") or []
    if commodity not in choices:
        return None, f"port does not {'sell' if side == 'buy' else 'buy'} {commodity} now"
    qty = int((((p.get("qty") or {}).get("max_by") or {}).get(commodity) or {}).get(side) or 0)
    if qty <= 0:
        return None, f"{commodity}: port out of stock or no credits / holds" if side == "buy" else f"cannot sell {commodity}"
    return {"kind": "trade", "args": {"commodity": commodity, "qty": qty, "side": side}}, None


def next_step(obs: dict, plan: dict) -> tuple[dict | None, str | None]:
    """Return (action, None) for this turn, or (None, stop_reason)."""
    if plan["steps"] >= MAX_STEPS:
        return None, f"step limit ({MAX_STEPS}) reached"
    enemy = _enemy_here(obs)
    if enemy:
        return None, enemy
    here = (obs.get("sector") or {}).get("id")
    a, b = plan["a"], plan["b"]
    if here not in (a, b):
        if plan["steps"] == 0:
            return _travel(obs, a)  # walk onto the route first
        return None, f"left the route (now in sector {here})"
    cargo = (obs.get("ship") or {}).get("cargo") or {}
    at_a = here == a
    if at_a and plan["visited_b"]:
        plan["cycles_done"] += 1
        plan["visited_b"] = False
    if not at_a:
        plan["visited_b"] = True
    sell_c = plan["buy_at_b"] if at_a else plan["buy_at_a"]
    buy_c = plan["buy_at_a"] if at_a else plan["buy_at_b"]
    if int(cargo.get(sell_c) or 0) > 0:
        return _trade(obs, "sell", sell_c)
    if at_a and plan["cycles_done"] >= plan["cycles"]:
        return None, f"route complete ({plan['cycles_done']} cycles)"
    if plan["bought_here"] != here:
        step, why = _trade(obs, "buy", buy_c)
        if step is None:
            return None, why
        plan["bought_here"] = here
        return step, None
    plan["bought_here"] = None
    return _travel(obs, b if at_a else a)
