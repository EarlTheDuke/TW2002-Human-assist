"""Bot growth and fixes: rich upgrades, defence, Ferrengi avoid, heuristic, 6th planet."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import tw2k.engine.constants as K
from tw2k.agents.heuristic import HeuristicAgent
from tw2k.agents.seat_acceptance import synthetic_obs, validate_action
from tw2k.agents.seat_brain import (
    DEFENSE_CASH_GATE,
    RICH_CREDITS,
    SeatBrain,
    SeatMemory,
    View,
)
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.actions import ActionKind
from tw2k.engine.combat import _destroy_ship
from tw2k.engine.constants import FEDSPACE_SECTORS, STARDOCK_SECTOR
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import EventKind, Planet, PlanetClass, Player, Ship, ShipClass
from tw2k.engine.observation import build_observation

ROOT = Path(__file__).resolve().parents[1]


def _load_acceptance():
    path = ROOT / "scripts" / "seat_brain_acceptance.py"
    spec = importlib.util.spec_from_file_location("seat_brain_acceptance_bg", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _rich_stardock_obs(*, credits: int, ship_class: str = "cargotran",
                       fighters: int = 20, shields: int = 0) -> dict:
    obs = synthetic_obs(sector=STARDOCK_SECTOR, credits=credits, ship_class=ship_class)
    obs["ship"]["fighters"] = fighters
    obs["ship"]["shields"] = shields
    obs["ship"]["fighter_cap"] = 400 if ship_class == "cargotran" else 10000
    obs["ship"]["shield_cap"] = 1000
    las = []
    for la in obs["legal_actions"]:
        if la["kind"] == "buy_equip":
            params = dict(la.get("params") or {})
            item = dict(params.get("item") or {})
            item["choices"] = list(dict.fromkeys(list(item.get("choices") or []) + ["fighters", "shields", "genesis"]))
            item["unit_price_by"] = {
                **(item.get("unit_price_by") or {}),
                "fighters": 200, "shields": 10, "genesis": 10000, "colonists": 10,
            }
            params["item"] = item
            qty = dict(params.get("qty") or {})
            max_by = dict(qty.get("max_by") or {})
            max_by.update({"fighters": 380, "shields": 1000, "genesis": 5, "colonists": 75})
            qty["max_by"] = max_by
            params["qty"] = qty
            la = {**la, "legal": True, "reason": None, "params": params}
        if la["kind"] == "buy_ship":
            params = dict(la.get("params") or {})
            sc = dict(params.get("ship_class") or {})
            sc["choices"] = list(dict.fromkeys(
                list(sc.get("choices") or []) + ["cargotran", "battleship", "havoc_gunstar", "imperial_starship"]
            ))
            sc["net_cost_by"] = {
                **(sc.get("net_cost_by") or {}),
                "cargotran": 40000, "battleship": 80000, "havoc_gunstar": 70000, "imperial_starship": 300000,
            }
            params["ship_class"] = sc
            la = {**la, "legal": True, "reason": None, "params": params}
        las.append(la)
    obs["legal_actions"] = las
    obs["owned_planets"] = [{
        "id": 7, "sector_id": 40, "name": "Home", "class": "M", "origin": "genesis",
        "citadel_level": 1, "citadel_target": 1,
        "colonists": {"fuel_ore": 1000, "organics": 500, "equipment": 200, "colonists": 200},
        "colonists_total": 1900,
        "stockpile": {"fuel_ore": 100, "organics": 200, "equipment": 50},
        "production": {"fuel_ore": 30, "organics": 25, "equipment": 11},
        "organics_consumption_per_day": 19, "growth_active": True, "organics_days_left": 9999,
    }]
    return obs


def test_rich_n3_buys_tougher_hull() -> None:
    brain = SeatBrain()
    brain.mem = SeatMemory()
    brain.mem.hot_sectors.add(187)
    obs = _rich_stardock_obs(credits=RICH_CREDITS + 50_000, fighters=10, shields=0)
    a = brain.decide(obs)
    assert validate_action(obs, a) == []
    assert a["kind"] == "buy_ship", a
    assert a["args"]["ship_class"] in (
        "battleship", "havoc_gunstar", "imperial_starship", "star_master", "constellation", "missile_frigate"
    )


def test_rich_n3_buys_shields_when_hull_is_already_tough() -> None:
    brain = SeatBrain()
    brain.mem = SeatMemory()
    brain.mem.hot_sectors.add(187)  # defence only after Ferrengi are fogged
    obs = _rich_stardock_obs(credits=DEFENSE_CASH_GATE + 20_000, ship_class="havoc_gunstar",
                             fighters=10, shields=0)
    las = []
    for la in obs["legal_actions"]:
        if la["kind"] == "buy_ship":
            la = {**la, "legal": False, "reason": "no ship you can buy right now",
                  "params": {"ship_class": {"choices": [], "net_cost_by": {}}}}
        las.append(la)
    obs["legal_actions"] = las
    a = brain.decide(obs)
    assert validate_action(obs, a) == []
    assert a["kind"] == "buy_equip", a
    assert a["args"]["item"] in ("shields", "fighters")


def test_rich_n2_raises_target_planets_above_two() -> None:
    mod = _load_acceptance()
    brain = mod.n2_brain()
    obs = _rich_stardock_obs(credits=500_000)
    obs["owned_planets"].append({
        "id": 8, "sector_id": 41, "name": "Two", "class": "K", "origin": "genesis",
        "citadel_level": 1, "citadel_target": 1,
        "colonists": {"fuel_ore": 800, "organics": 400, "equipment": 100, "colonists": 100},
        "colonists_total": 1400,
        "stockpile": {"fuel_ore": 50, "organics": 80, "equipment": 10},
        "production": {"fuel_ore": 40, "organics": 5, "equipment": 5},
        "organics_consumption_per_day": 14, "growth_active": True, "organics_days_left": 9999,
    })
    brain.decide(obs)
    assert brain.target_planets > 2


def test_hot_ferrengi_sector_is_avoided_when_naked() -> None:
    brain = SeatBrain()
    mem = SeatMemory()
    mem.hot_sectors.add(187)
    brain.mem = mem
    obs = synthetic_obs(sector=4, credits=50_000, ship_class="cargotran")
    obs["ship"]["fighters"] = 5
    obs["ship"]["shields"] = 0
    obs["sector"] = {"id": 4, "warps_out": [187, 5], "port": None, "is_fedspace": False}
    obs["known_warps"] = {"4": [187, 5], "5": [4, 13], "13": [5], "187": [4]}
    obs["known_sectors"] = [{"id": s} for s in (4, 5)]
    las = []
    for la in obs["legal_actions"]:
        if la["kind"] == "warp":
            la = {**la, "legal": True, "reason": None,
                  "params": {"target": {"type": "int", "required": True, "choices": [187, 5]}}}
        if la["kind"] == "plot_course":
            la = {**la, "legal": False, "reason": "disabled for this test"}
        las.append(la)
    obs["legal_actions"] = las
    assert 187 not in brain._legal_warps(View(obs))
    a = brain.decide(obs)
    assert validate_action(obs, a) == []
    assert a["kind"] == "warp", a
    assert a["args"]["target"] == 5


def test_sixth_planet_refused_warps_away() -> None:
    u = generate_universe(GameConfig(seed=34321, universe_size=80, enable_ferrengi=False, enable_planets=True))
    sid = next(s for s in u.sectors if s >= 30 and s not in FEDSPACE_SECTORS)
    sec = u.sectors[sid]
    for old in list(sec.planet_ids):
        sec.planet_ids.remove(old)
    for i in range(5):
        pid = 88000 + i
        u.planets[pid] = Planet(id=pid, sector_id=sid, name=f"Fill{i}", class_id=PlanetClass.M)
        sec.planet_ids.append(pid)
    p = Player(id="A", name="A", credits=50_000, ship=Ship(holds=75, fighters=50, shields=0, genesis=1),
               sector_id=sid, turns_today=0)
    u.players["A"] = p
    sec.occupant_ids.append("A")
    p.known_sectors.add(sid)
    p.known_warps[sid] = list(sec.warps)
    listed = {la.kind: la for la in legal_actions(u, "A")}["deploy_genesis"]
    assert not listed.legal
    assert "5 planets" in (listed.reason or "")
    obs = build_observation(u, "A").model_dump(mode="json")
    for label, brain in (("n3", SeatBrain()), ("n2", _load_acceptance().n2_brain()), ("n1", _load_acceptance().n1_brain())):
        a = brain.decide(obs)
        assert validate_action(obs, a) == [], a
        assert a["kind"] == "warp", (label, a)
        assert a["args"]["target"] in sec.warps
        thought = a.get("thought", "").lower()
        assert "elsewhere" in thought or "5 planets" in thought or "genesis" in thought, (label, a)


def test_coeff1_organics_rebalance_is_skipped() -> None:
    brain = SeatBrain(value_allocator=False)
    planet = {
        "id": 7, "sector_id": 5, "name": "Uworld", "class": "U", "origin": "genesis",
        "citadel_level": 2, "citadel_target": 2,
        "colonists": {"fuel_ore": 2000, "organics": 100, "equipment": 200, "colonists": 200},
        "colonists_total": 2500,
        "stockpile": {"fuel_ore": 50, "organics": 5, "equipment": 10},
        "production": {"fuel_ore": 20, "organics": 1, "equipment": 12},
        "organics_consumption_per_day": 25, "growth_active": False, "organics_days_left": 0,
    }
    obs = synthetic_obs(sector=5, credits=30_000, ship_class="cargotran", landed=7, planets=[planet])
    obs["owned_planets"] = [planet]
    las = []
    for la in obs["legal_actions"]:
        if la["kind"] == "assign_colonists":
            la = {**la, "legal": True, "reason": None, "params": {
                "planet_id": {"type": "int", "required": True, "choices": [7]},
                "from": {"type": "str", "required": True, "choices": ["fuel_ore", "colonists", "equipment"]},
                "to": {"type": "str", "required": True, "choices": ["organics", "fuel_ore"]},
                "qty": {"type": "int", "required": True, "min": 1,
                         "max_by": {"fuel_ore": 2000, "colonists": 200, "equipment": 200}},
            }}
        if la["kind"] == "build_citadel":
            la = {**la, "legal": False, "reason": "already at tier"}
        if la["kind"] == "liftoff":
            la = {**la, "legal": True, "reason": None}
        las.append(la)
    # Ensure assign_colonists is present even if synthetic omitted it.
    if not any(la["kind"] == "assign_colonists" for la in las):
        las.append({"kind": "assign_colonists", "legal": True, "reason": None, "params": {
            "planet_id": {"type": "int", "required": True, "choices": [7]},
            "from": {"type": "str", "required": True, "choices": ["fuel_ore", "colonists", "equipment"]},
            "to": {"type": "str", "required": True, "choices": ["organics", "fuel_ore"]},
            "qty": {"type": "int", "required": True, "min": 1,
                     "max_by": {"fuel_ore": 2000, "colonists": 200, "equipment": 200}},
        }})
    obs["legal_actions"] = las
    # Direct unit check of the helper: coeff-1 must refuse the reshuffle.
    assert brain._rebalance_organics(View(obs), planet) is None
    a = brain.decide(obs)
    assert validate_action(obs, a) == []
    if a["kind"] == "assign_colonists":
        assert a["args"].get("to") != "organics", a


def test_heuristic_avoids_reverse_and_out_of_turns() -> None:
    agent = HeuristicAgent("P6", "Heur", seed=42)

    class _Obs:
        def __init__(self, sector_id, adj, turns_remaining, credits=1000):
            self.sector = {"id": sector_id, "ferrengi": [], "port": None}
            self.adjacent = adj
            self.turns_remaining = turns_remaining
            self.turns_per_day = 1000
            self.credits = credits
            self.ship = {"fighters": 50, "cargo": {}, "cargo_free": 20}

    adj_a = [{"id": 270, "known": True, "port": "BSB"}, {"id": 100, "known": True, "port": None}]
    adj_b = [{"id": 203, "known": True, "port": "BSB"}, {"id": 101, "known": True, "port": None}]
    a1 = asyncio.run(agent.act(_Obs(203, adj_a, 10)))
    assert a1.kind is ActionKind.WARP
    first = int(a1.args["target"])
    a2 = asyncio.run(agent.act(_Obs(first, adj_b if first == 270 else adj_a, 10)))
    assert a2.kind is ActionKind.WARP
    if first == 270:
        assert int(a2.args["target"]) != 203
    dead = asyncio.run(agent.act(_Obs(203, adj_a, 0)))
    assert dead.kind is ActionKind.WAIT


def test_heuristic_seed_is_deterministic() -> None:
    async def one(seed: int) -> list[int]:
        agent = HeuristicAgent("P6", "Heur", seed=seed)
        targets = []

        class _Obs:
            def __init__(self, sector_id: int = 10):
                self.sector = {"id": sector_id, "ferrengi": [], "port": None}
                self.adjacent = [{"id": i, "known": True, "port": None} for i in (20, 21, 22)]
                self.turns_remaining = 50
                self.credits = 1000
                self.ship = {"fighters": 10, "cargo": {}, "cargo_free": 20}

        here = 10
        for _ in range(5):
            act = await agent.act(_Obs(here))
            targets.append(int(act.args["target"]))
            here = targets[-1]
        return targets

    assert asyncio.run(one(99)) == asyncio.run(one(99))


def test_third_loss_in_a_day_is_ship_destroyed() -> None:
    """tw2002: two pods a day; the third loss is Ship Destroyed (not elimination)."""
    assert K.DEATH_MODE == "tw2002"
    assert K.PODS_PER_DAY == 2
    u = generate_universe(GameConfig(seed=7, universe_size=40, enable_ferrengi=False, enable_planets=False))
    p = Player(id="A", name="A", credits=10_000, ship=Ship(fighters=10), sector_id=1)
    p.ship.ship_class = ShipClass.BATTLESHIP
    u.players["A"] = p
    u.sectors[1].occupant_ids.append("A")
    outcomes = []
    for _ in range(3):
        p.ship.ship_class = ShipClass.BATTLESHIP
        p.sector_id = 1
        if "A" not in u.sectors[1].occupant_ids:
            u.sectors[1].occupant_ids.append("A")
        _destroy_ship(u, "A", reason="mines")
        ev = next(e for e in reversed(u.events) if e.kind == EventKind.SHIP_DESTROYED)
        outcomes.append(ev.payload["outcome"])
    assert outcomes == ["escape_pod", "escape_pod", "ship_destroyed"]
    assert p.alive is True
    assert p.deaths == 3


def test_n1_ferry_still_meets_acceptance_bar() -> None:
    mod = _load_acceptance()
    row = mod.prove_n1_day(seed=250925, credits=100_000)
    assert row["rejected"] == 0
    assert row["reached_stardock_day"] == 1
    assert row["aba_per_100"] <= 2.0
