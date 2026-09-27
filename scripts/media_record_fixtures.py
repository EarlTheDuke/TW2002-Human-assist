"""Record viewport event fixtures from a real engine match (video cockpit V0).

Drives seed 250925 (200 sectors, the CU pilot galaxy) through the scenarios
the viewport must handle and writes, per scenario, exactly what `/events`
would hand the viewing seat: rows rendered by `event_view()` and filtered by
`_event_visible_to()` (the same two calls the harness endpoint makes), plus a
minimal viewer observation and the resolver state before the batch.

    python scripts/media_record_fixtures.py            # writes tests/fixtures/media_events/*.json

Expected resolver outputs live in each fixture (`expected`) and in
docs/plans/2026-09-26-video-cockpit-v0-fixtures.md. Nothing here is runtime code.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tw2k.engine import GameConfig, generate_universe  # noqa: E402
from tw2k.engine import constants as K  # noqa: E402
from tw2k.engine.actions import Action, ActionKind  # noqa: E402
from tw2k.engine.models import Commodity, FerrengiShip, MineType, Player  # noqa: E402
from tw2k.engine.observation import _event_visible_to, build_observation, event_view  # noqa: E402
from tw2k.engine.runner import _bfs_path, apply_action  # noqa: E402

OUT = ROOT / "tests" / "fixtures" / "media_events"
SEED = 250925
VIEWER = "P1"


def _universe():
    u = generate_universe(GameConfig(seed=SEED, universe_size=200, max_days=3, turns_per_day=500,
                                     starting_credits=100_000, enable_ferrengi=False, enable_planets=False))
    for pid in ("P1", "P2", "P3"):
        u.players[pid] = Player(id=pid, name={"P1": "Commander", "P2": "Rival", "P3": "Bystander"}[pid],
                                agent_kind="external", sector_id=1, credits=100_000, turns_per_day=500)
        u.sectors[1].occupant_ids.append(pid)
    return u


def _move(u, pid: str, sid: int) -> None:
    p = u.players[pid]
    u.sectors[p.sector_id].occupant_ids = [x for x in u.sectors[p.sector_id].occupant_ids if x != pid]
    p.sector_id = sid
    u.sectors[sid].occupant_ids.append(pid)
    p.known_sectors.add(sid)


def _act(u, pid: str, verb: ActionKind, **args) -> None:
    res = apply_action(u, pid, Action(kind=verb, args=args))
    assert res.ok, (verb, args, res.error)


def _deep(u, exclude: set[int] = frozenset()) -> list[int]:
    return [s for s in sorted(u.sectors) if s not in K.FEDSPACE_SECTORS and s not in exclude]


def _port_sector(u, *, sells: str | None = None, exclude: set[int] = frozenset()) -> int:
    idx = {"fuel_ore": 0, "organics": 1, "equipment": 2}
    for s in _deep(u, exclude):
        port = u.sectors[s].port
        if port and port.code and len(port.code) == 3 and (sells is None or port.code[idx[sells]] == "S"):
            return s
    raise AssertionError("no port")


def _obs(u, viewer: str = VIEWER) -> dict:
    o = build_observation(u, viewer)
    port = (o.sector or {}).get("port")
    return {"self_id": o.self_id, "day": o.day, "tick": o.tick,
            "sector": {"id": o.sector["id"], "is_fedspace": o.sector.get("is_fedspace"),
                       "port": {"code": port.get("code"), "class_id": port.get("class_id")} if port else None},
            "ship": {"class": o.ship["class"]}}


def _batch(u, mark: int, viewer: str = VIEWER) -> list[dict]:
    return [event_view(e) for e in u.events[mark:] if _event_visible_to(e, viewer, u)]


def _write(name: str, description: str, u, mark: int, state: dict, expected: list[dict], notes: str = "") -> dict:
    fx = {"name": name, "description": description, "seed": SEED, "viewer": VIEWER, "state_before": state,
          "obs": _obs(u), "batch": _batch(u, mark), "expected": expected, "notes": notes}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(fx, indent=2) + "\n", encoding="utf-8")
    print(f"{name:28s} rows={len(fx['batch']):2d} kinds={[r['kind'] for r in fx['batch']]}")
    return fx


def clip(key: str, priority: int) -> dict:
    return {"clip_key": key, "priority": priority}


def main(argv: list[str] | None = None) -> int:
    import argparse

    global OUT
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(OUT), help="fixture directory (default tests/fixtures/media_events)")
    OUT = Path(ap.parse_args(argv).out)
    # 1. single warp
    u = _universe()
    start = _deep(u)[0]
    _move(u, "P1", start)
    to = u.sectors[start].warps[0]
    m = len(u.events)
    _act(u, "P1", ActionKind.WARP, target=to)
    _write("single_warp", "Viewer warps one hop.", u, m, {"visit_sector": start, "docked_in_visit": False},
           [clip("warp.out", 2)])

    # 2. autopilot burst (plot_course execute, several hops in one action)
    u = _universe()
    _move(u, "P1", start)
    far = next(s for s in _deep(u) if len(_bfs_path(u, start, s)) >= 5)
    m = len(u.events)
    _act(u, "P1", ActionKind.PLOT_COURSE, target=far, execute=True)
    _write("autopilot_burst", "Viewer autopilots several hops in one action.", u, m,
           {"visit_sector": start, "docked_in_visit": False}, [clip("warp.out", 2)],
           "Coalesce: all hop warps + the autopilot row become ONE warp.out; the last hop sets the arrival ambient.")

    # 3. trade burst at one port (first trades of the visit) + 3b. another trade later in the same visit
    u = _universe()
    port = _port_sector(u, sells="fuel_ore")
    _move(u, "P1", port)
    m = len(u.events)
    for _ in range(3):
        _act(u, "P1", ActionKind.TRADE, commodity="fuel_ore", qty=5, side="buy")
    _write("trade_burst", "Viewer's first three trades after arriving at a port.", u, m,
           {"visit_sector": port, "docked_in_visit": False}, [clip("dock.port", 2)],
           "Coalesce: several trades at one port in one batch = one dock.port.")
    m = len(u.events)
    _act(u, "P1", ActionKind.TRADE, commodity="fuel_ore", qty=5, side="buy")
    _write("trade_same_visit", "One more trade later in the same visit.", u, m,
           {"visit_sector": port, "docked_in_visit": True}, [],
           "first_in_visit is false: already docked this visit, so no clip (log + toast still update).")

    # 4. trade_failed (first trade attempt of the visit fails)
    u = _universe()
    _move(u, "P1", port)
    u.players["P1"].ship.cargo[Commodity.FUEL_ORE] = 0
    m = len(u.events)
    res = apply_action(u, "P1", Action(kind=ActionKind.TRADE, args={"commodity": "fuel_ore", "qty": 10, "side": "sell"}))
    assert not res.ok
    _write("trade_failed", "Viewer's first trade attempt at a port is rejected.", u, m,
           {"visit_sector": port, "docked_in_visit": False}, [clip("dock.port", 2)],
           "trade_failed also counts as docking (the ship still pulled up to the port).")

    # 5/6. self attack: win and lose (deep space, not FedSpace)
    for name, mine, theirs, exp, note in (
        ("self_attack_win", 3000, 40, [clip("combat.hit", 1)],
         "outcome_hit: the defender lost more. Until the V2 `outcome` fact lands, unknown outcome also maps to combat.hit."),
        ("self_attack_lose", 30, 3000, [clip("combat.miss", 1)],
         "Needs the V2 `outcome`/losses fact to tell miss from hit (pre-V2 fallback: combat.hit). If the viewer's ship is "
         "destroyed, ship_destroyed(victim=self) is the V7 key self.ship_destroyed (P0), not part of the V2 set."),
    ):
        u = _universe()
        arena = _deep(u)[3]
        for pid in ("P1", "P2"):
            _move(u, pid, arena)
        u.players["P1"].ship.fighters, u.players["P2"].ship.fighters = mine, theirs
        m = len(u.events)
        _act(u, "P1", ActionKind.ATTACK, target="P2")
        _write(name, f"Viewer attacks a rival ({mine} vs {theirs} fighters).", u, m,
               {"visit_sector": arena, "docked_in_visit": False}, exp, note)

    # 7. attacked by a Ferrengi (the NPC hunt pass, pinned so it attacks instead of wandering off)
    from tw2k.engine import ferrengi as ferr_mod

    u = _universe()
    lair = _deep(u)[5]
    _move(u, "P1", lair)
    u.players["P1"].ship.fighters = 5
    u.ferrengi["F1"] = FerrengiShip(id="F1", name="Grakk", sector_id=lair, aggression=10, fighters=400, shields=100)
    saved = K.FERRENGI_MOVE_PROB
    K.FERRENGI_MOVE_PROB = 0.0
    try:
        m = len(u.events)
        ferr_mod._ferrengi_roam_and_hunt(u)
    finally:
        K.FERRENGI_MOVE_PROB = saved
    _write("ferrengi_attack", "A Ferrengi attacks the viewer.", u, m, {"visit_sector": lair, "docked_in_visit": False},
           [clip("combat.incoming", 0)], "ferrengi_attack + the combat row (defender=self) coalesce into one P0 combat.incoming.")

    # 8. witnessed combat in the viewer's sector
    u = _universe()
    arena = _deep(u)[3]
    for pid in ("P1", "P2", "P3"):
        _move(u, pid, arena)
    u.players["P2"].ship.fighters, u.players["P3"].ship.fighters = 900, 300
    m = len(u.events)
    _act(u, "P2", ActionKind.ATTACK, target="P3")
    _write("witnessed_combat", "Two rivals fight in the viewer's sector.", u, m,
           {"visit_sector": arena, "docked_in_visit": False}, [clip("combat.witnessed", 3)],
           "witnessed_in_my_sector: actor != self and event sector == viewer's sector.")

    # 9. public, far-away port destroyed
    u = _universe()
    _move(u, "P1", start)
    target = _port_sector(u, exclude={start, *u.sectors[start].warps})
    _move(u, "P2", target)
    u.players["P2"].ship.mines[MineType.ATOMIC] = 5
    for c in u.sectors[target].port.stock.values():
        c.current = 0
    m = len(u.events)
    _act(u, "P2", ActionKind.DEPLOY_MINES, kind="atomic", qty=3)
    _write("far_port_destroyed", "A rival nukes a port far from the viewer (public event).", u, m,
           {"visit_sector": start, "docked_in_visit": False}, [],
           "Public events elsewhere never get a first-person clip (caption on the ticker at most).")

    # 10. another seat trades in the viewer's sector
    u = _universe()
    for pid in ("P1", "P2"):
        _move(u, pid, port)
    m = len(u.events)
    _act(u, "P2", ActionKind.TRADE, commodity="fuel_ore", qty=5, side="buy")
    _write("other_trade_in_sector", "A rival trades at the port the viewer is at.", u, m,
           {"visit_sector": port, "docked_in_visit": False}, [],
           "Not self: no dock clip for someone else's trade.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
