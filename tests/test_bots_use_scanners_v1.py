"""Planted bugs for bots-use-scanners-v1: buy/use scanners under INFO_MODE tw2002."""

from __future__ import annotations

import asyncio

from tw2k.agents.heuristic import HeuristicAgent
from tw2k.agents.prompts import SYSTEM_PROMPT
from tw2k.agents.seat_acceptance import validate_action
from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View
from tw2k.engine import ActionKind, GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action
from tw2k.engine.models import Ship, ShipClass
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action


def _open(u, pid, sector=1, credits=20_000, ship=None):
    from tw2k.engine.models import Player
    p = Player(id=pid, name=pid, credits=credits, ship=ship or Ship(), sector_id=sector)
    u.players[pid] = p
    if pid not in u.sectors[sector].occupant_ids:
        u.sectors[sector].occupant_ids.append(pid)
    p.known_sectors.add(sector)
    return p


def test_brain_does_not_buy_scanner_past_credits() -> None:
    """Plant: buying a scanner when credits < list price."""
    u = generate_universe(GameConfig(seed=11, universe_size=40, enable_ferrengi=False, enable_planets=False))
    p = _open(u, "A", credits=500)  # below density 2000
    obs = build_observation(u, "A").model_dump(mode="json")
    a = SeatBrain().decide(obs)
    assert validate_action(obs, a) == []
    if a["kind"] == "buy_equip":
        assert a["args"].get("item") not in ("density_scanner", "holo_scanner"), a


def test_brain_does_not_buy_holo_on_density_only_hull() -> None:
    """Plant: holo on Scout (density-only)."""
    u = generate_universe(GameConfig(seed=12, universe_size=40, enable_ferrengi=False, enable_planets=False))
    ship = Ship(ship_class=ShipClass.SCOUT_MARAUDER, holds=12, fighters=0)
    p = _open(u, "A", credits=80_000, ship=ship)
    assert K.scanner_room("scout_marauder") == K.SCANNER_DENSITY
    obs = build_observation(u, "A").model_dump(mode="json")
    # Force legal list: holo must not be offered; brain must not invent it.
    a = SeatBrain().decide(obs)
    assert validate_action(obs, a) == []
    if a["kind"] == "buy_equip" and a["args"].get("item") == "holo_scanner":
        raise AssertionError(a)
    # Direct helper: item choice never returns holo for scout
    brain = SeatBrain()
    brain.mem = SeatMemory()
    choice = brain._scanner_item_choice(View(obs))
    assert choice is None or choice[0] == "density_scanner", choice


def test_brain_does_not_scan_without_a_device() -> None:
    """Plant: scan while ship.scanner is None under tw2002."""
    u = generate_universe(GameConfig(seed=13, universe_size=40, enable_ferrengi=False, enable_planets=False))
    p = _open(u, "A", credits=50_000)
    assert p.ship.scanner is None
    # Leave StarDock so buy_equip scanner is not the first priority distraction:
    # warp to a neighbor first via engine, then decide.
    warps = list(u.sectors[1].warps)
    assert warps
    apply_action(u, "A", Action(kind=ActionKind.WARP, args={"target": warps[0]}))
    obs = build_observation(u, "A").model_dump(mode="json")
    assert (obs.get("ship") or {}).get("scanner") is None
    a = SeatBrain().decide(obs)
    assert validate_action(obs, a) == []
    assert a["kind"] != "scan", a


def test_brain_uses_holo_scan_results_to_pick_a_port() -> None:
    """Plant: ignoring scan results (warp blind after a holo reveals a port)."""
    u = generate_universe(GameConfig(seed=14, universe_size=60, enable_ferrengi=False, enable_planets=False))
    p = _open(u, "A", credits=30_000)
    p.ship.scanner = K.SCANNER_HOLO
    obs = build_observation(u, "A").model_dump(mode="json")
    brain = SeatBrain()
    a = brain.decide(obs)
    assert validate_action(obs, a) == []
    # With a holo fitted at StarDock and blind neighbors, should scan (or buy already done).
    if a["kind"] == "scan":
        assert a["args"].get("tier") in (None, "holo", "density")
        apply_action(u, "A", Action(kind=ActionKind.SCAN, args=a.get("args") or {"tier": "holo"}))
        obs2 = build_observation(u, "A").model_dump(mode="json")
        a2 = brain.decide(obs2)
        assert validate_action(obs2, a2) == []
        # After scan, prefer warping to a neighbor that now shows a port when trading/exploring.
        ports = [adj for adj in (obs2.get("adjacent") or []) if adj.get("port")]
        if ports and a2["kind"] == "warp":
            assert a2["args"]["target"] in {int(x["id"]) for x in (obs2.get("adjacent") or [])}


def test_brain_does_not_rebuy_scanner_already_owned() -> None:
    """Plant: re-buying density when already fitted."""
    u = generate_universe(GameConfig(seed=15, universe_size=40, enable_ferrengi=False, enable_planets=False))
    p = _open(u, "A", credits=50_000)
    p.ship.scanner = K.SCANNER_DENSITY
    obs = build_observation(u, "A").model_dump(mode="json")
    brain = SeatBrain()
    brain.mem = SeatMemory()
    assert brain._buy_scanner(View(obs)) is None or brain._scanner_item_choice(View(obs)) is None or (
        brain._scanner_item_choice(View(obs))[0] == "holo_scanner"
    )
    # Density already owned: may upgrade to holo on merchant_cruiser, never density again.
    choice = brain._scanner_item_choice(View(obs))
    assert choice is None or choice[0] == "holo_scanner", choice
    a = brain.decide(obs)
    assert validate_action(obs, a) == []
    if a["kind"] == "buy_equip":
        assert a["args"].get("item") != "density_scanner", a


def test_prompt_turn1_requires_a_scanner_before_scan() -> None:
    """Plant: prompt nudge still says bare scan on turn 1 without buying hardware."""
    text = SYSTEM_PROMPT
    assert "density_scanner" in text or "holo_scanner" in text
    # The worked example must buy a scanner before teaching scan.
    buy_i = text.find('buy_equip')
    scan_example = text.find('"kind":"scan"')
    assert buy_i != -1 and scan_example != -1
    # First buy_equip for scanner appears before the post-buy scan example in the day-1 block.
    day1 = text.find("DAY-1 WORKED EXAMPLE")
    assert day1 != -1
    chunk = text[day1: day1 + 2500]
    assert "density_scanner" in chunk or "holo_scanner" in chunk
    assert chunk.find("density_scanner") < chunk.find('"kind":"scan"') or chunk.find("holo_scanner") < chunk.find('"kind":"scan"')


def test_heuristic_buys_density_at_stardock_when_naked() -> None:
    u = generate_universe(GameConfig(seed=16, universe_size=40, enable_ferrengi=False, enable_planets=False))
    p = _open(u, "H1", credits=20_000)
    obs = build_observation(u, "H1")
    agent = HeuristicAgent("H1", "Heur", seed=1)
    act = asyncio.run(agent.act(obs))
    assert act.kind is ActionKind.BUY_EQUIP
    assert act.args.get("item") in ("density_scanner", "holo_scanner")
