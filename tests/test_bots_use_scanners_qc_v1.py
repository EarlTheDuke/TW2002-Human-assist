"""QC follow-ups for bots-use-scanners-v1."""

from __future__ import annotations

import asyncio

from tw2k.agents.heuristic import HeuristicAgent
from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View
from tw2k.engine import ActionKind, GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.models import Player, Ship
from tw2k.engine.observation import build_observation


def _open(u, pid, sector=1, credits=30_000, ship=None):
    p = Player(id=pid, name=pid, credits=credits, ship=ship or Ship(), sector_id=sector)
    u.players[pid] = p
    if pid not in u.sectors[sector].occupant_ids:
        u.sectors[sector].occupant_ids.append(pid)
    p.known_sectors.add(sector)
    return p


def test_holo_upgrade_keep_matches_choice() -> None:
    """Density->holo upgrade: choice and buy share working_capital keep (no mismatch)."""
    u = generate_universe(GameConfig(
        seed=43, universe_size=40, enable_ferrengi=False, enable_planets=False,
    ))
    # 30k is enough for holo+cash_buffer but not holo+working_capital — must not choose.
    p = _open(u, "A", credits=30_000)
    p.ship.scanner = K.SCANNER_DENSITY
    obs = build_observation(u, "A").model_dump(mode="json")
    brain = SeatBrain(cash_buffer=2_000, working_capital=8_000)
    brain.mem = SeatMemory()
    v = View(obs)
    choice = brain._scanner_item_choice(v)
    buy = brain._buy_scanner(v)
    assert choice is None or choice[0] != "holo_scanner", choice
    assert buy is None, buy
    # Above working_capital keep, both sides agree on the upgrade.
    p.credits = 40_000
    obs = build_observation(u, "A").model_dump(mode="json")
    v = View(obs)
    choice = brain._scanner_item_choice(v)
    buy = brain._buy_scanner(v)
    assert choice is not None and choice[0] == "holo_scanner", choice
    assert buy is not None and buy["args"]["item"] == "holo_scanner", buy


def test_heuristic_prefers_density_port_over_empty(monkeypatch) -> None:
    monkeypatch.setattr(K, "BOTS_TAVERN_MODE", "legacy")
    monkeypatch.setattr(K, "H_RECOVERY_MODE", "legacy")
    u = generate_universe(GameConfig(seed=44, universe_size=40, enable_ferrengi=False, enable_planets=False))
    p = _open(u, "H1", sector=2, credits=20_000)
    p.ship.scanner = K.SCANNER_DENSITY
    if 2 not in u.sectors:
        p.sector_id = 1
        u.sectors[1].occupant_ids.append("H1")
    real = build_observation(u, "H1")
    real.adjacent = [
        {"id": 10, "known": True, "port": None, "density": 0, "scan_day": 1},
        {"id": 11, "known": True, "port": None, "density": 100, "scan_day": 1},
    ]
    las = []
    for la in real.legal_actions:
        d = la if isinstance(la, dict) else (la.model_dump() if hasattr(la, "model_dump") else dict(la))
        if d.get("kind") == "warp":
            params = dict(d.get("params") or {})
            tgt = dict(params.get("target") or {})
            tgt["choices"] = [10, 11]
            params["target"] = tgt
            d = {**d, "legal": True, "reason": None, "params": params}
        las.append(d)
    real.legal_actions = las
    agent = HeuristicAgent("H1", "Heur", seed=1)
    act = asyncio.run(agent.act(real))
    assert act.kind is ActionKind.WARP
    assert int(act.args["target"]) == 11, act


def test_maybe_scan_requires_fitted_device() -> None:
    """_maybe_scan must refuse when the ship has no scanner under tw2002."""
    u = generate_universe(GameConfig(seed=45, universe_size=40, enable_ferrengi=False, enable_planets=False))
    p = _open(u, "A", credits=50_000)
    assert p.ship.scanner is None
    obs = build_observation(u, "A").model_dump(mode="json")
    brain = SeatBrain()
    brain.mem = SeatMemory()
    assert brain._maybe_scan(View(obs), force=True) is None


def test_heuristic_keeps_buffer_on_density_buy() -> None:
    """Heuristic must not spend the last credits on a density scanner."""
    u = generate_universe(GameConfig(seed=46, universe_size=40, enable_ferrengi=False, enable_planets=False))
    p = _open(u, "H1", credits=2_500)  # density 2000 would leave 500 < 2k buffer
    obs = build_observation(u, "H1")
    agent = HeuristicAgent("H1", "Heur", seed=1)
    act = asyncio.run(agent.act(obs))
    if act.kind is ActionKind.BUY_EQUIP:
        assert act.args.get("item") not in ("density_scanner", "holo_scanner"), act


def test_heuristic_density_tie_break_survives_rng() -> None:
    """Equal visits, no port/dense_port: higher density wins; rng only breaks exact ties."""
    for seed in range(1, 9):
        u = generate_universe(GameConfig(seed=47, universe_size=40, enable_ferrengi=False, enable_planets=False))
        p = _open(u, "H1", sector=1, credits=20_000)
        p.ship.scanner = K.SCANNER_DENSITY
        real = build_observation(u, "H1")
        real.adjacent = [
            {"id": 10, "known": True, "port": None, "density": 0, "scan_day": 1},
            {"id": 11, "known": True, "port": None, "density": 40, "scan_day": 1},
            {"id": 12, "known": True, "port": None, "density": 0, "scan_day": 1},
        ]
        las = []
        for la in real.legal_actions:
            d = la if isinstance(la, dict) else (la.model_dump() if hasattr(la, "model_dump") else dict(la))
            if d.get("kind") == "warp":
                params = dict(d.get("params") or {})
                tgt = dict(params.get("target") or {})
                tgt["choices"] = [10, 11, 12]
                params["target"] = tgt
                d = {**d, "legal": True, "reason": None, "params": params}
            las.append(d)
        real.legal_actions = las
        agent = HeuristicAgent("H1", "Heur", seed=seed)
        act = asyncio.run(agent.act(real))
        if act.kind is not ActionKind.WARP:
            continue
        assert int(act.args["target"]) == 11, (seed, act)
