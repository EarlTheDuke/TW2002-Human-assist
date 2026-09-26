"""Seat-bot S3 - goal-driven SeatBrain, fogged observation only.

Offline proof: the real engine runs, but the brain sees nothing except
`build_observation(universe, seat)` - the exact object the harness mailbox
hands a seat. It must get from StarDock to a genesis world with a citadel
and run the colonist ferry, always passing required args and never
submitting an action the engine rejects on a precondition.
"""

from __future__ import annotations

import json
from pathlib import Path

from tw2k.agents.seat_brain import SeatBrain, SeatMemory
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.actions import Action
from tw2k.engine.models import Player
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action, tick_day

ROOT = Path(__file__).resolve().parents[1]


def _universe(seed: int = 230923, credits: int = 120_000):
    u = generate_universe(GameConfig(seed=seed, universe_size=150, max_days=12, turns_per_day=250,
                                     starting_credits=credits, enable_ferrengi=False, enable_planets=True))
    for pid, name in (("P1", "Seat"), ("P2", "Idle")):
        p = Player(id=pid, name=name, agent_kind="external", sector_id=1, credits=credits)
        u.players[pid] = p
        u.sectors[1].occupant_ids.append(pid)
    return u


def _play(u, brain: SeatBrain, *, max_actions: int = 2500, max_days: int = 6):
    log = []
    for _ in range(max_actions):
        p = u.players["P1"]
        if p.turns_today >= p.turns_per_day:
            if u.day >= max_days:
                break
            tick_day(u)
            continue
        obs = build_observation(u, "P1")
        action = brain.decide(obs)
        res = apply_action(u, "P1", Action(**action))
        log.append({"day": obs.day, "sector": obs.sector.get("id"), "action": action, "ok": res.ok, "error": res.error})
        if action["kind"] == "query_limpets":  # free no-op only chosen when out of turns
            tick_day(u)
    return log


def _ok(log, kind, **match):
    for i, rec in enumerate(log):
        a = rec["action"]
        if rec["ok"] and a["kind"] == kind and all(a["args"].get(k) == v for k, v in match.items()):
            return i
    return None


def test_offline_genesis_citadel_ferry_from_observation_only() -> None:
    u = _universe()
    brain = SeatBrain()
    log = _play(u, brain)

    failures = [r for r in log if not r["ok"]]
    assert not failures, failures[:5]

    i_ship = _ok(log, "buy_ship", ship_class="cargotran")
    i_gen = _ok(log, "buy_equip", item="genesis")
    i_dep = _ok(log, "deploy_genesis")
    i_land = _ok(log, "land_planet")
    i_build = _ok(log, "build_citadel")
    i_buy_col = _ok(log, "buy_equip", item="colonists")
    i_assign = _ok(log, "assign_colonists", **{"from": "ship"})
    order = [i_ship, i_gen, i_dep, i_land, i_build, i_buy_col, i_assign]
    assert None not in order, dict(zip(["ship", "genesis", "deploy", "land", "build", "buy_col", "assign"], order, strict=True))
    assert order[:5] == sorted(order[:5])          # upgrade -> genesis -> deploy -> land -> build
    assert i_buy_col < i_assign                    # ferry: buy at StarDock, unload at home

    # Genesis world with a working citadel and ferried colonists, seen through the seat's own observation.
    obs = build_observation(u, "P1")
    gworlds = [p for p in obs.owned_planets if p["origin"] == "genesis"]
    home = next(p for p in gworlds if p["id"] == brain.mem.home_planet)
    assert home["citadel_level"] >= 2           # Kimi3 winners were at L2 on day 8; this is day 6
    assert brain.mem.deploy_sector in {p["sector_id"] for p in gworlds}
    assert all(p["citadel_level"] >= 1 for p in gworlds)  # every genesis world got its citadel started

    # Required args every time; never landed on a non-genesis world.
    for rec in log:
        a = rec["action"]
        if a["kind"] == "assign_colonists":
            assert {"planet_id", "qty", "from", "to"} <= set(a["args"]) and a["args"]["qty"] > 0
        if a["kind"] in ("land_planet", "build_citadel"):
            assert "planet_id" in a["args"]
            assert u.planets[a["args"]["planet_id"]].origin == "genesis"
        if a["kind"] == "plot_course":
            assert "target" in a["args"] and a["args"]["execute"] is True

    # More than one ferry trip completed (StarDock <-> home alternation is not treated as a loop).
    assigns = [r for r in log if r["ok"] and r["action"]["kind"] == "assign_colonists"]
    assert len(assigns) >= 2
    assert brain.mem.stall_breaks <= 2, brain.mem.stall_breaks


def test_goals_and_scratchpad_writeback_resume_memory() -> None:
    u = _universe()
    brain = SeatBrain()
    log = _play(u, brain, max_actions=400, max_days=2)
    last = log[-1]["action"]
    assert last["goal_short"] and last["goal_medium"] and last["goal_long"]
    # Harness persists scratchpad_update; a fresh brain resumes the same home from it.
    scratch = build_observation(u, "P1").scratchpad
    mem = SeatMemory.load(scratch)
    assert mem.home_planet == brain.mem.home_planet and mem.deploy_sector == brain.mem.deploy_sector
    assert SeatBrain().decide(build_observation(u, "P1"))["scratchpad_update"].startswith("SEATBRAIN ")


# ---------------------------------------------------------------------------
# Synthetic observations for specific rungs
# ---------------------------------------------------------------------------


def _obs(**over):
    base = {
        "day": 1, "credits": 50_000, "sector": {"id": 40, "warps_out": [41, 42]}, "planet_landed": None,
        "ship": {"class": "cargotran", "cargo": {"colonists": 0}, "cargo_free": 75, "genesis": 0},
        "known_warps": {"1": [2], "2": [1, 40], "40": [2, 41, 42]},
        "known_sectors": [{"id": s} for s in (1, 2, 40, 41, 42)],
        "owned_planets": [], "scratchpad": "",
        "legal_actions": [
            {"kind": "warp", "legal": True, "params": {"target": {"choices": [41, 42]}}},
            {"kind": "scan", "legal": True},
            {"kind": "wait", "legal": True},
            {"kind": "plot_course", "legal": True},
            {"kind": "liftoff", "legal": False, "reason": "not landed on a planet"},
        ],
    }
    base.update(over)
    return base


def _legal(obs, kind, legal=True, reason=None, params=None):
    obs["legal_actions"] = [la for la in obs["legal_actions"] if la["kind"] != kind]
    obs["legal_actions"].append({"kind": kind, "legal": legal, "reason": reason, "params": params or {}})
    return obs


def test_landed_on_claimed_neutral_lifts_off_instead_of_unloading() -> None:
    o = _obs(planet_landed=20, ship={"class": "cargotran", "cargo": {"colonists": 75}, "cargo_free": 0, "genesis": 0},
             owned_planets=[{"id": 20, "sector_id": 40, "origin": "claim", "citadel_level": 0, "citadel_target": 0,
                             "colonists_total": 0, "colonists": {}}])
    _legal(o, "assign_colonists", True, params={"planet_id": {"choices": [20]}, "qty": {"max_by": {"ship": 75}}})
    _legal(o, "liftoff", True)
    a = SeatBrain().decide(o)
    assert a["kind"] == "liftoff"


def test_deploy_illegal_too_close_carries_genesis_deeper() -> None:
    o = _obs(ship={"class": "cargotran", "cargo": {}, "cargo_free": 75, "genesis": 1},
             sector={"id": 2, "warps_out": [1, 40]},
             known_warps={"1": [2], "2": [1, 40], "40": [2, 41]})
    _legal(o, "deploy_genesis", False, reason="too close to StarDock (1 hops, need >=3); warp deeper")
    _legal(o, "warp", True, params={"target": {"choices": [1, 40]}})
    a = SeatBrain().decide(o)
    assert a["kind"] == "warp" and a["args"]["target"] == 40


def test_assign_uses_landed_genesis_planet_and_full_load() -> None:
    o = _obs(planet_landed=38, ship={"class": "cargotran", "cargo": {"colonists": 75}, "cargo_free": 0, "genesis": 0},
             owned_planets=[{"id": 38, "sector_id": 40, "origin": "genesis", "citadel_level": 1, "citadel_target": 1,
                             "colonists_total": 1800, "colonists": {"organics": 600, "fuel_ore": 700,
                                                                    "equipment": 300, "colonists": 200}}])
    _legal(o, "assign_colonists", True, params={"planet_id": {"choices": [38]}, "qty": {"max_by": {"ship": 75}}})
    a = SeatBrain().decide(o)
    assert a["kind"] == "assign_colonists"
    assert a["args"]["planet_id"] == 38 and a["args"]["qty"] == 75 and a["args"]["from"] == "ship"


def test_ferry_plots_home_with_execute_even_after_previous_stardock_plot() -> None:
    brain = SeatBrain()
    planets = [{"id": 38, "sector_id": 40, "origin": "genesis", "citadel_level": 1, "citadel_target": 1,
                "colonists_total": 1500, "colonists": {}}]
    brain.decide(_obs(owned_planets=planets))  # establishes home = sector 40
    o = _obs(sector={"id": 1, "warps_out": [2]}, owned_planets=planets,
             ship={"class": "cargotran", "cargo": {"colonists": 75}, "cargo_free": 0, "genesis": 0})
    a = brain.decide(o)
    assert a["kind"] == "plot_course" and a["args"] == {"target": 40, "execute": True}


def test_stall_triggers_exploration_break() -> None:
    brain = SeatBrain(stall_window=3)
    o = _obs(credits=100)  # broke, nothing to buy; earn policy has no port -> explores, but pin sector
    kinds = []
    for _ in range(8):
        kinds.append(brain.decide(o)["kind"])
    assert brain.mem.stall_breaks >= 1


def test_brain_is_seat_only() -> None:
    src = (ROOT / "src" / "tw2k" / "agents" / "seat_brain.py").read_text(encoding="utf-8")
    runner = (ROOT / "scripts" / "seat_brain_v2.py").read_text(encoding="utf-8")
    for bad in ('"/state', "'/state", "universe", "players[", "_RECENT_PLOTS", "ping_pong"):
        assert bad not in src, bad
        assert bad not in runner, bad
    assert "StallDetector" in src
    json.dumps(SeatMemory().dump())
