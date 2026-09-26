"""Seat-only acceptance harness for seat brains (seat-bot S4).

docs/plans/2026-09-24-seat-bot-competitive.md. Everything here works on the
seat's own fogged observation - the dict the harness mailbox hands a brain -
and never touches the engine, `/state`, or another seat:

* `validate_action(obs, action)`: is the action legal *according to that
  observation's own `legal_actions` envelope*, with every required argument
  present and inside its advertised choices / caps?
* `MilestoneTracker`: did the brain walk genesis -> land -> build_citadel ->
  colonist ferry, in order, judged only from (observation, action) pairs?
* `replay(brain, payloads)`: feed recorded mailbox payloads (JSONL of
  `{seat, turn_seq, observation, ...}`, exactly what `MailboxPolicy` writes)
  to a brain and collect a report.
* `synthetic_obs(...)` + `STORYBOARD`: hand-built fogged observations for the
  empire loop, so a brain can be checked with no engine at all.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from typing import Any

# Arguments the seat contract REQUIRES, even where the engine would default one
# (the Kimi3 Path-B loops were exactly "engine defaulted qty=0 / planet_id=None").
REQUIRED_ARGS: dict[str, tuple[str, ...]] = {
    "warp": ("target",),
    "plot_course": ("target", "execute"),
    "trade": ("commodity", "qty", "side"),
    "probe": ("target",),
    "land_planet": ("planet_id",),
    "build_citadel": ("planet_id",),
    "assign_colonists": ("planet_id", "from", "to", "qty"),
    "load_planet_cargo": ("planet_id", "commodity", "qty"),
    "dump_planet_cargo": ("planet_id", "commodity", "qty"),
    "buy_equip": ("item", "qty"),
    "buy_ship": ("ship_class",),
    "deploy_fighters": ("qty", "mode"),
    "deploy_mines": ("kind", "qty"),
    "attack": ("target",),
    "photon_missile": ("target",),
    "hail": ("target", "message"),
    "broadcast": ("message",),
    "corp_create": ("ticker",),
    "corp_invite": ("target",),
    "corp_join": ("ticker",),
    "corp_deposit": ("amount",),
    "corp_withdraw": ("amount",),
    "corp_memo": ("message",),
    "propose_alliance": ("target",),
    "accept_alliance": ("alliance_id",),
    "break_alliance": ("alliance_id",),
}

# Which argument keys a `qty.max_by` table for each verb.
_QTY_KEY: dict[str, Callable[[dict[str, Any]], Any]] = {
    "assign_colonists": lambda a: a.get("from"),
    "buy_equip": lambda a: a.get("item"),
    "load_planet_cargo": lambda a: a.get("commodity"),
    "dump_planet_cargo": lambda a: a.get("commodity"),
    "deploy_mines": lambda a: a.get("kind"),
}


def _legal_map(obs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {la.get("kind"): la for la in (obs.get("legal_actions") or [])}


def _same(a: Any, b: Any) -> bool:
    return a == b or str(a) == str(b)


def validate_action(obs: dict[str, Any], action: dict[str, Any]) -> list[str]:
    """Problems with `action` judged ONLY from `obs` (empty list = acceptable)."""
    errors: list[str] = []
    kind = action.get("kind")
    args = action.get("args") or {}
    la = _legal_map(obs).get(kind)
    if la is None:
        return [f"{kind}: not a verb in legal_actions"]
    if not la.get("legal"):
        errors.append(f"{kind}: illegal here ({la.get('reason') or 'no reason'})")
    for name in REQUIRED_ARGS.get(kind, ()):
        if args.get(name) in (None, ""):
            errors.append(f"{kind}: missing required arg '{name}'")
    if kind == "plot_course" and "execute" in args and args["execute"] is not True:
        errors.append("plot_course: execute must be true (plan-only plots cost nothing and change nothing)")
    params = la.get("params") or {}
    for name, env in params.items():
        if not isinstance(env, dict) or name not in args:
            continue
        choices = env.get("choices")
        if choices and not any(_same(args[name], c) for c in choices):
            errors.append(f"{kind}: {name}={args[name]!r} not in choices {choices}")
    if "qty" in args:
        qty = args["qty"]
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            errors.append(f"{kind}: qty must be a positive int (got {qty!r})")
        else:
            env = params.get("qty") if isinstance(params.get("qty"), dict) else {}
            cap = None
            if kind == "trade":
                cap = ((env.get("max_by") or {}).get(args.get("commodity")) or {}).get(args.get("side"))
            elif kind in _QTY_KEY and env.get("max_by") is not None:
                cap = (env.get("max_by") or {}).get(_QTY_KEY[kind](args))
            elif env.get("max") is not None:
                cap = env.get("max")
            if cap is not None and qty > int(cap):
                errors.append(f"{kind}: qty {qty} exceeds envelope cap {cap}")
    return errors


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------

MILESTONES = ("genesis_bought", "genesis_deployed", "landed_genesis", "citadel_started",
              "colonists_bought", "ferry_home", "colonists_assigned")


@dataclass
class Report:
    turns: int = 0
    errors: list[tuple[int, str]] = field(default_factory=list)
    first: dict[str, int] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    ferry_trips: int = 0  # buy colonists -> ... -> assign from ship, completed
    kinds: dict[str, int] = field(default_factory=dict)

    @property
    def empire_loop_ok(self) -> bool:
        f = self.first
        if any(m not in f for m in MILESTONES):
            return False
        core = [f[m] for m in MILESTONES[:4]]
        return core == sorted(core) and f["colonists_bought"] < f["colonists_assigned"] and self.ferry_trips >= 1

    def missing(self) -> list[str]:
        return [m for m in MILESTONES if m not in self.first]

    def summary(self) -> str:
        return (f"turns={self.turns} errors={len(self.errors)} empire_loop_ok={self.empire_loop_ok} "
                f"ferry_trips={self.ferry_trips} milestones={self.first} missing={self.missing()}")


class MilestoneTracker:
    def __init__(self) -> None:
        self.report = Report()
        self._loaded = False

    def _hit(self, name: str, i: int) -> None:
        self.report.first.setdefault(name, i)
        self.report.counts[name] = self.report.counts.get(name, 0) + 1

    def observe(self, i: int, obs: dict[str, Any], action: dict[str, Any]) -> None:
        r = self.report
        r.turns += 1
        kind = action.get("kind")
        args = action.get("args") or {}
        r.kinds[kind] = r.kinds.get(kind, 0) + 1
        for e in validate_action(obs, action):
            r.errors.append((i, e))
        genesis_worlds = {p.get("id"): p for p in (obs.get("owned_planets") or []) if p.get("origin") == "genesis"}
        cargo = ((obs.get("ship") or {}).get("cargo") or {})
        if kind == "buy_equip" and args.get("item") == "genesis":
            self._hit("genesis_bought", i)
        elif kind == "deploy_genesis":
            self._hit("genesis_deployed", i)
        elif kind == "land_planet" and args.get("planet_id") in genesis_worlds:
            self._hit("landed_genesis", i)
        elif kind == "build_citadel" and args.get("planet_id") in genesis_worlds:
            self._hit("citadel_started", i)
        elif kind == "buy_equip" and args.get("item") == "colonists":
            self._hit("colonists_bought", i)
            self._loaded = True
        elif (kind == "plot_course" and int(cargo.get("colonists") or 0) > 0
              and any(_same(args.get("target"), p.get("sector_id")) for p in genesis_worlds.values())):
            self._hit("ferry_home", i)
        elif kind == "assign_colonists" and args.get("from") == "ship" and args.get("planet_id") in genesis_worlds:
            self._hit("colonists_assigned", i)
            if self._loaded:
                r.ferry_trips += 1
                self._loaded = False


def replay(brain: Any, payloads: Iterable[dict[str, Any]]) -> tuple[Report, list[dict[str, Any]]]:
    """Feed recorded mailbox payloads to `brain.decide`; open loop (actions are not applied)."""
    tracker = MilestoneTracker()
    actions: list[dict[str, Any]] = []
    for i, payload in enumerate(payloads):
        obs = payload.get("observation") if "observation" in payload else payload
        action = brain.decide(obs)
        tracker.observe(i, obs, action)
        actions.append(action)
    return tracker.report, actions


def count_aba(sectors: list[Any]) -> int:
    """A -> B -> A bounces in a per-decision sector trail (the qwen2-kimi3 report metric)."""
    return sum(1 for i in range(2, len(sectors))
               if sectors[i] is not None and sectors[i] == sectors[i - 2] and sectors[i] != sectors[i - 1])


def _game_turns(obs_list: list[dict[str, Any]]) -> int:
    """Game turns consumed across a decision sequence, from the seat's own turns_remaining."""
    total = 0
    for a, b in pairwise(obs_list):
        ta, tb = a.get("turns_remaining"), b.get("turns_remaining")
        if not isinstance(ta, int) or not isinstance(tb, int):
            continue
        total += (ta - tb) if a.get("day") == b.get("day") else ta  # rest of the day was used/forfeited
    return total


def _economy_moved(a: dict[str, Any], b: dict[str, Any]) -> bool:
    ca = (a.get("ship") or {}).get("cargo") or {}
    cb = (b.get("ship") or {}).get("cargo") or {}
    return a.get("credits") != b.get("credits") or ca != cb


def route_metrics(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    """N1 metrics from the seat's OWN observations only (mailbox payloads, in order).

    `aba` counts every A->B->A bounce in the per-decision sector trail; `idle_aba` only the
    bounces with no credit/cargo change around them (pure wandering, the qwen2-kimi3 P6
    failure) - a buy-at-A / sell-at-B trade loop is an ABA by design but not idle.
    Rates are per 100 GAME turns (a plot_course decision can spend many turns)."""
    obs_list = [p.get("observation") if "observation" in p else p for p in payloads]
    sectors: list[Any] = []
    stardock_day = None
    day1_profit = 0
    seen_trades: set[tuple] = set()
    for obs in obs_list:
        sid = (obs.get("sector") or {}).get("id")
        sectors.append(sid)
        if sid == 1 and stardock_day is None:
            stardock_day = obs.get("day")
        for t in obs.get("trade_log") or []:
            key = (t.get("day"), t.get("tick"), t.get("sector_id"), t.get("commodity"), t.get("side"))
            if key in seen_trades:
                continue
            seen_trades.add(key)
            if t.get("day") == 1 and isinstance(t.get("realized_profit"), int):
                day1_profit += t["realized_profit"]
    aba = count_aba(sectors)
    idle = sum(1 for i in range(2, len(sectors))
               if sectors[i] is not None and sectors[i] == sectors[i - 2] and sectors[i] != sectors[i - 1]
               and not _economy_moved(obs_list[i - 2], obs_list[i - 1])
               and not _economy_moved(obs_list[i - 1], obs_list[i]))
    turns = _game_turns(obs_list)
    return {
        "decisions": len(sectors),
        "game_turns": turns,
        "stardock_day": stardock_day,
        "day1_trade_profit": day1_profit,
        "aba": aba,
        "aba_per_100_turns": round(100.0 * aba / max(1, turns), 2),
        "idle_aba": idle,
        "idle_aba_per_100_turns": round(100.0 * idle / max(1, turns), 2),
        "unique_sectors": len({s for s in sectors if s is not None}),
    }


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


# ---------------------------------------------------------------------------
# Synthetic fogged observations (no engine)
# ---------------------------------------------------------------------------

# StarDock 1 - 2 - 3 - 4 - 5 (deep, home). 2/3 are within 3 hops of StarDock.
SYN_WARPS = {1: [2], 2: [1, 3], 3: [2, 4], 4: [3, 5], 5: [4]}


def _la(kind: str, legal: bool = True, reason: str | None = None, **params: Any) -> dict[str, Any]:
    return {"kind": kind, "legal": legal, "reason": None if legal else reason, "detail": "precise", "params": params}


def synthetic_obs(*, sector: int, credits: int = 90_000, ship_class: str = "cargotran", holds: int = 75,
                  colonists: int = 0, genesis: int = 0, landed: int | None = None,
                  planets: list[dict[str, Any]] | None = None, day: int = 1, turns: int = 200) -> dict[str, Any]:
    """A fog-shaped observation with a consistent legal_actions envelope for the empire loop."""
    planets = planets or []
    cargo = {"fuel_ore": 0, "organics": 0, "equipment": 0, "colonists": colonists}
    free = holds - colonists
    here_planets = [p["id"] for p in planets if p["sector_id"] == sector]
    landed_p = next((p for p in planets if p["id"] == landed), None)
    warps = SYN_WARPS[sector]
    las = [
        _la("warp", target={"type": "int", "required": True, "choices": warps}),
        _la("plot_course", target={"type": "int", "required": True, "suggested": sorted(SYN_WARPS)},
            execute={"type": "bool"}),
        _la("scan"), _la("wait"),
        _la("trade", False, "no trading port in this sector"),
        _la("liftoff", landed is not None, "not landed on a planet"),
        _la("land_planet", bool(here_planets), "no planet in this sector",
            planet_id={"type": "int", "required": True, "choices": here_planets, "contested": []}),
    ]
    far = sector >= 4
    if genesis <= 0:
        las.append(_la("deploy_genesis", False, "no genesis torpedoes loaded (buy_equip genesis at StarDock)"))
    elif sector == 1 or not far:
        las.append(_la("deploy_genesis", False,
                       "cannot deploy genesis in FedSpace" if sector == 1 else "too close to StarDock (2 hops, need >=3); warp deeper"))
    elif landed is not None:
        las.append(_la("deploy_genesis", False, "must be in space to deploy genesis (liftoff first)"))
    else:
        las.append(_la("deploy_genesis", hops_from_stardock=sector - 1, min_hops=3))
    if sector == 1:
        prices = {"genesis": 25_000, "colonists": 10, "fighters": 50}
        max_by = {"genesis": credits // 25_000, "colonists": min(free, credits // 10), "fighters": credits // 50}
        las.append(_la("buy_equip", item={"choices": [i for i, m in max_by.items() if m > 0], "unit_price_by": prices},
                       qty={"min": 1, "max_by": max_by}))
        las.append(_la("buy_ship", False, "no ship you can buy right now (credits / alignment / corp)",
                       ship_class={"choices": []}))
    else:
        las.append(_la("buy_equip", False, "must be at StarDock (sector 1)", item={"choices": []}, qty={"max_by": {}}))
        las.append(_la("buy_ship", False, "must be at StarDock (sector 1)"))
    if landed_p is not None and landed_p.get("origin") == "genesis":
        pools = landed_p.get("colonists") or {}
        from_choices = (["ship"] if colonists else []) + [k for k, n in pools.items() if n > 0]
        las.append(_la("assign_colonists", bool(from_choices), "no colonists aboard or on the planet",
                       planet_id={"choices": [landed]}, **{"from": {"choices": from_choices}},
                       to={"choices": ["fuel_ore", "organics", "equipment", "colonists"]},
                       qty={"min": 1, "max_by": {"ship": colonists, **{k: n for k, n in pools.items() if n > 0}}}))
        lvl, tgt = landed_p["citadel_level"], landed_p["citadel_target"]
        total = sum(pools.values())
        tiers = [(5000, 1000), (10000, 2000), (20000, 4000)]
        if tgt > lvl:
            las.append(_la("build_citadel", False, f"citadel L{tgt} already under construction", planet_id={"choices": [landed]}))
        elif total < tiers[lvl][1]:
            las.append(_la("build_citadel", False, f"need {tiers[lvl][1]} colonists on planet (have {total})",
                           planet_id={"choices": [landed]}))
        else:
            las.append(_la("build_citadel", planet_id={"choices": [landed]},
                           next={"level": lvl + 1, "credits": tiers[lvl][0], "colonists": tiers[lvl][1]}))
    else:
        las.append(_la("assign_colonists", False, "not landed on a planet"))
        las.append(_la("build_citadel", False, "not landed on a planet"))
    owned = []
    for p in planets:
        pools = p.get("colonists") or {}
        owned.append({**p, "colonists": pools, "colonists_total": sum(pools.values())})
    return {
        "day": day, "tick": 0, "credits": credits, "turns_remaining": turns, "planet_landed": landed,
        "sector": {"id": sector, "warps_out": warps, "port": None, "is_fedspace": sector == 1},
        "ship": {"class": ship_class, "holds": holds, "cargo": cargo, "cargo_free": free, "genesis": genesis},
        "known_warps": {str(k): v for k, v in SYN_WARPS.items()},
        "known_sectors": [{"id": k} for k in SYN_WARPS],
        "known_ports": [], "owned_planets": owned, "legal_actions": las, "scratchpad": "",
    }


def _genesis_world(level: int = 0, target: int = 0, pools: dict[str, int] | None = None) -> dict[str, Any]:
    return {"id": 7, "sector_id": 5, "name": "Genesis 5-7", "class": "M", "origin": "genesis",
            "citadel_level": level, "citadel_target": target,
            "colonists": pools if pools is not None else {"fuel_ore": 1000, "organics": 625, "equipment": 375, "colonists": 500}}


# (label, observation, expected action kind, expected args subset)
STORYBOARD: list[tuple[str, dict[str, Any], str, dict[str, Any]]] = [
    ("stardock: buy genesis", synthetic_obs(sector=1), "buy_equip", {"item": "genesis", "qty": 1}),
    ("carry genesis away from fedspace", synthetic_obs(sector=2, genesis=1, credits=65_000), "warp", {"target": 3}),
    ("still too close: deeper", synthetic_obs(sector=3, genesis=1, credits=65_000), "warp", {"target": 4}),
    ("deep enough: deploy", synthetic_obs(sector=4, genesis=1, credits=65_000), "deploy_genesis", {}),
]


def ferry_storyboard() -> list[tuple[str, dict[str, Any], str, dict[str, Any]]]:
    """The citadel + ferry half, around a genesis world (planet 7) in sector 5."""
    seed = _genesis_world()
    built = _genesis_world(0, 1, {"fuel_ore": 700, "organics": 400, "equipment": 200, "colonists": 200})
    after = _genesis_world(0, 1, {"fuel_ore": 775, "organics": 400, "equipment": 200, "colonists": 200})
    return [
        ("home in space: land to build", synthetic_obs(sector=5, planets=[seed]), "land_planet", {"planet_id": 7}),
        ("landed: build L1", synthetic_obs(sector=5, planets=[seed], landed=7), "build_citadel", {"planet_id": 7}),
        ("built: liftoff", synthetic_obs(sector=5, planets=[built], landed=7, credits=35_000), "liftoff", {}),
        ("need colonists: plot stardock", synthetic_obs(sector=5, planets=[built], credits=35_000),
         "plot_course", {"target": 1, "execute": True}),
        ("stardock: load colonists", synthetic_obs(sector=1, planets=[built], credits=35_000), "buy_equip",
         {"item": "colonists"}),
        ("loaded: plot home", synthetic_obs(sector=1, planets=[built], credits=34_250, colonists=75),
         "plot_course", {"target": 5, "execute": True}),
        ("home with colonists: land", synthetic_obs(sector=5, planets=[built], credits=34_250, colonists=75),
         "land_planet", {"planet_id": 7}),
        ("landed with colonists: assign all", synthetic_obs(sector=5, planets=[built], landed=7, credits=34_250,
                                                           colonists=75),
         "assign_colonists", {"planet_id": 7, "from": "ship", "qty": 75}),
        ("unloaded: liftoff", synthetic_obs(sector=5, planets=[after], landed=7, credits=34_250), "liftoff", {}),
        ("next trip: plot stardock", synthetic_obs(sector=5, planets=[after], credits=34_250),
         "plot_course", {"target": 1, "execute": True}),
        # Rich enough for a 2nd world while keeping the next tier (10k) + working capital funded.
        ("rich at stardock: genesis #2", synthetic_obs(sector=1, planets=[after], credits=60_000),
         "buy_equip", {"item": "genesis", "qty": 1}),
    ]


__all__ = [
    "MILESTONES", "REQUIRED_ARGS", "STORYBOARD", "MilestoneTracker", "Report", "count_aba", "ferry_storyboard",
    "load_jsonl", "replay", "route_metrics", "synthetic_obs", "validate_action",
]
