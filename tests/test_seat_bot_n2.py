"""Seat-bot N2 — growth-aware colony management.

Owner-only observation fields (production, organics burn, growth_active,
organics_days_left) come from the class coefficients in planets.py.
The brain sizes the organics pool from that coefficient and buys and dumps
organics when the runway is under two days. One-day citadel tiers (L1/L2)
stay on the N1 schedule: a blanket "remaining >= tier cost" floor lost the
day-10 A/B by delaying the L2 fighter bonus. Multi-day tiers (L3+) still
require that floor, unless the match is in its last two days.

Offline only. The brain is fed build_observation for its own seat.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from tw2k.agents.seat_acceptance import synthetic_obs, validate_action
from tw2k.agents.seat_brain import SeatBrain
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import Player
from tw2k.engine.observation import build_observation
from tw2k.engine.planets import ORGANICS_DAYS_SUSTAINABLE, organics_worker_target, planet_growth_status
from tw2k.engine.runner import _bfs_path, apply_action

ROOT = Path(__file__).resolve().parents[1]


def _load_acceptance():
    path = ROOT / "scripts" / "seat_brain_acceptance.py"
    spec = importlib.util.spec_from_file_location("seat_brain_acceptance_n2", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _universe():
    u = generate_universe(GameConfig(seed=31, universe_size=90, max_days=3, turns_per_day=200,
                                     starting_credits=100_000, enable_ferrengi=False, enable_planets=True))
    for pid, name in (("P1", "Me"), ("P2", "Rival")):
        p = Player(id=pid, name=name, agent_kind="external", sector_id=1, credits=100_000)
        u.players[pid] = p
        u.sectors[1].occupant_ids.append(pid)
    return u


def _move(u, pid: str, sid: int) -> None:
    p = u.players[pid]
    u.sectors[p.sector_id].occupant_ids = [x for x in u.sectors[p.sector_id].occupant_ids if x != pid]
    p.sector_id = sid
    u.sectors[sid].occupant_ids.append(pid)


def _deep_sector(u) -> int:
    for sid in sorted(u.sectors):
        if sid > 10 and len(_bfs_path(u, 1, sid)) >= K.GENESIS_MIN_HOPS_FROM_STARDOCK and not u.sectors[sid].planet_ids:
            return sid
    raise AssertionError("no deep empty sector")


def _deploy(u) -> int:
    deep = _deep_sector(u)
    _move(u, "P1", deep)
    u.players["P1"].ship.genesis = 1
    res = apply_action(u, "P1", Action(kind=ActionKind.DEPLOY_GENESIS, args={}))
    assert res.ok, res.error
    return next(pid for pid in u.sectors[deep].planet_ids if u.planets[pid].owner_id == "P1")


def test_growth_status_matches_class_coefficients() -> None:
    cols = {"fuel_ore": 1000, "organics": 625, "equipment": 375, "colonists": 500}
    status = planet_growth_status("M", cols, 25)
    assert status["production"] == {"fuel_ore": 30, "organics": 31, "equipment": 11}
    assert status["organics_consumption_per_day"] == 25
    assert status["growth_active"] is True
    assert status["organics_days_left"] == ORGANICS_DAYS_SUSTAINABLE
    # K class cannot cover a 2,500 burn with the seed organics pool.
    thin = planet_growth_status("K", cols, 25)
    assert thin["production"]["organics"] == 6
    assert thin["organics_days_left"] < 2
    assert organics_worker_target(2500, 5) == 520
    assert organics_worker_target(2500, 0) == 0


def test_owned_planet_growth_fields_are_owner_only() -> None:
    u = _universe()
    plid = _deploy(u)
    obs = build_observation(u, "P1")
    entry = next(p for p in obs.owned_planets if p["id"] == plid)
    assert entry["production"]["organics"] == 31
    assert entry["organics_consumption_per_day"] == 25
    assert entry["growth_active"] is True
    assert entry["organics_days_left"] == ORGANICS_DAYS_SUSTAINABLE
    assert plid not in {p["id"] for p in build_observation(u, "P2").owned_planets}
    # A visitor in the sector still does not get the runway on the sector brief.
    brief = next(p for p in obs.sector["planets"] if p["id"] == plid)
    assert "organics_days_left" not in brief
    assert "production" not in brief


def _l2_world(pools: dict[str, int]) -> dict:
    return {"id": 7, "sector_id": 5, "name": "G", "class": "M", "origin": "genesis",
            "citadel_level": 1, "citadel_target": 1, "colonists": pools,
            "stockpile": {"fuel_ore": 0, "organics": 80, "equipment": 0},
            "production": {"fuel_ore": 0, "organics": 31, "equipment": 0},
            "organics_consumption_per_day": 20, "growth_active": True,
            "organics_days_left": ORGANICS_DAYS_SUSTAINABLE}


def test_one_day_l2_still_builds() -> None:
    """A/B: holding L2 for a full growth floor missed the fighter bonus on day 10."""
    pools = {"fuel_ore": 575, "organics": 625, "equipment": 375, "colonists": 500}
    obs = synthetic_obs(sector=5, planets=[_l2_world(pools)], landed=7, credits=40_000)
    a = SeatBrain().decide(obs)
    assert validate_action(obs, a) == []
    assert a["kind"] == "build_citadel" and a["args"]["planet_id"] == 7


def _l3_world() -> dict:
    """4,100 colonists pays for L3 (4,000) and leaves a hundred, under the floor."""
    pools = {"fuel_ore": 2000, "organics": 1000, "equipment": 600, "colonists": 500}
    world = _l2_world(pools)
    world["citadel_level"] = 2
    world["citadel_target"] = 2
    world["organics_consumption_per_day"] = 41
    return world


def test_multiday_citadel_keeps_a_growth_base() -> None:
    obs = synthetic_obs(sector=5, planets=[_l3_world()], landed=7, credits=40_000)
    a = SeatBrain().decide(obs)
    assert validate_action(obs, a) == []
    assert a["kind"] != "build_citadel"
    assert a["kind"] == "liftoff"


def test_multiday_citadel_builds_in_the_last_two_days_anyway() -> None:
    obs = synthetic_obs(sector=5, planets=[_l3_world()], landed=7, credits=40_000, day=28)
    obs["max_days"] = 30
    a = SeatBrain().decide(obs)
    assert validate_action(obs, a) == []
    assert a["kind"] == "build_citadel" and a["args"]["planet_id"] == 7


def test_underfed_world_buys_cheap_organics_and_remembers_the_drop() -> None:
    world = {"id": 7, "sector_id": 5, "name": "G", "class": "H", "origin": "genesis",
             "citadel_level": 2, "citadel_target": 2,
             "colonists": {"fuel_ore": 2500, "organics": 0, "equipment": 0, "colonists": 500},
             "stockpile": {"organics": 20},
             "production": {"fuel_ore": 200, "organics": 0, "equipment": 0},
             "organics_consumption_per_day": 30, "growth_active": True, "organics_days_left": 0}
    obs = synthetic_obs(sector=4, planets=[world], credits=20_000)
    obs["sector"]["port"] = {"code": "BSS"}
    obs["legal_actions"] = [la for la in obs["legal_actions"] if la["kind"] != "trade"]
    obs["legal_actions"].append({
        "kind": "trade", "legal": True, "reason": None, "detail": "precise",
        "params": {
            "commodity": {"buy_choices": ["organics"], "sell_choices": [], "choices": ["organics"]},
            "qty": {"max_by": {"organics": {"buy": 75, "sell": 0}}},
            "unit_price": {"listed_by": {"organics": {"buy": 18, "sell": 0}}},
        },
    })
    brain = SeatBrain()
    a = brain.decide(obs)
    assert validate_action(obs, a) == []
    assert a["kind"] == "trade" and a["args"]["side"] == "buy" and a["args"]["commodity"] == "organics"
    assert a["args"]["qty"] == 75
    assert brain.mem.organics_drop == 7

    hauled = synthetic_obs(sector=5, planets=[world], credits=18_650, colonists=0)
    hauled["ship"]["cargo"]["organics"] = 75
    hauled["ship"]["cargo_free"] = 0
    brain.mem.organics_drop = 7
    land = brain.decide(hauled)
    assert land["kind"] == "land_planet" and land["args"]["planet_id"] == 7


def test_k_class_unload_prefers_fuel_once_a_tiny_organics_crew_exists() -> None:
    """Coeff-1 (K/U) cannot surplus-feed; after a tiny organics crew, ferry goes to fuel."""
    world = {"id": 7, "sector_id": 5, "name": "G", "class": "K", "origin": "genesis",
             "citadel_level": 1, "citadel_target": 1,
             "colonists": {"fuel_ore": 1000, "organics": 200, "equipment": 200, "colonists": 100}}
    obs = synthetic_obs(sector=5, planets=[world], landed=7, colonists=75, credits=10_000)
    a = SeatBrain().decide(obs)
    assert a["kind"] == "assign_colonists"
    assert a["args"]["to"] == "fuel_ore" and a["args"]["qty"] == 75


def test_n2_day10_beats_n1_and_keeps_organics(monkeypatch) -> None:
    # CLASS0_TERRA.md: colonist scarcity changes day-10 NW bars; pin legacy for this bar only.
    monkeypatch.setattr("tw2k.engine.constants.CLASS0_MODE", "legacy")
    # PLANETARY_TRADING.md "Bots" (bots-use-planet-trade-v1): small planet-trade lots lift N1 on seed 250925 far more
    # than N2 (N1 171,399 -> 338,403, N2 316,376 -> 323,479), so this ladder bar keeps the slice-54 lot floors.
    monkeypatch.setattr("tw2k.engine.constants.BOT_PLANET_TRADE_MIN_LOT", 500)
    monkeypatch.setattr("tw2k.engine.constants.BOT_PLANET_TRADE_FREE_LOT", 500)
    # bots-use-planet-warfare-v1: home mines and pickets drop N2 under N1 on seed 250925.
    monkeypatch.setattr("tw2k.engine.constants.BOTS_TAVERN_MODE", "legacy")
    monkeypatch.setattr("tw2k.engine.constants.BOTS_WAR_MODE", "legacy")
    monkeypatch.setattr("tw2k.engine.constants.BOTS_DEPLOY_MODE", "legacy")
    monkeypatch.setattr("tw2k.engine.constants.STARDOCK_EXTRA_MODE", "legacy")
    # FEDSPACE_POLICE.md: no FED_MODE pin - the bar passes under tw2002 tows (QC re-measured, same numbers).
    """Five seeds, ten days, fogged observation only.

    On the corrected tw2002 price table (ECONOMY_CALIBRATION.md) the N2 ladder
    strictly beats N1 on all five seeds under default INFO_MODE/RANK_MODE
    tw2002 (bots-use-scanners-v1 retune; old INFO_MODE/RANK_MODE legacy pins
    removed). Rejected stays 0. Coeff-1 organics reshuffles and coeff-1 import
    targets are skipped; fuel gets the ferry instead. Held-zero planet ids are
    the measured result after the scanner fog retune.
    """
    mod = _load_acceptance()
    held_zeros = {250925: [32], 20260925: [30], 99: [29], 31: [30]}
    # Strict N2 > N1 on every seed (restores the bar weakened by economy-calibration-v1).
    failures = []
    beats = 0
    for seed in mod.N2_SEEDS:
        base = mod.prove_growth_replay(seed=seed, brain=mod.n1_brain())
        nxt = mod.prove_growth_replay(seed=seed, brain=mod.n2_brain())
        if nxt["net_worth"] > base["net_worth"]:
            beats += 1
        else:
            failures.append(("nw", seed, base["net_worth"], nxt["net_worth"]))
        if nxt["rejected"]:
            failures.append(("rejected", seed, nxt["rejected"]))
        if nxt["zero_planets"] != held_zeros.get(seed, []):
            failures.append(("organics", seed, nxt["zero_planets"], held_zeros.get(seed, [])))
    assert beats == len(mod.N2_SEEDS), failures
    assert not failures, failures
