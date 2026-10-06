#!/usr/bin/env python3
"""Focused port-upgrade / construction lab. No server, no LLM, no ports.

Prints one line per check from STAGED_port-upgrade-build-v1 section 13(d).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tw2k.engine import (  # noqa: E402
    Action,
    ActionKind,
    GameConfig,
    apply_action,
    generate_universe,
    tick_day,
)
from tw2k.engine.models import (  # noqa: E402
    Commodity,
    Planet,
    PlanetClass,
    Player,
    Port,
    PortClass,
    PortStock,
    Ship,
)
from tw2k.engine.port_build import port_count  # noqa: E402

FUEL, ORG, EQ = Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT


def _fail(msg: str) -> None:
    print(f"FAIL {msg}")
    raise SystemExit(1)


def _sit(u, sector_id: int) -> None:
    player = u.players["A"]
    old = u.sectors.get(player.sector_id)
    if old is not None and "A" in old.occupant_ids:
        old.occupant_ids.remove("A")
    player.sector_id = sector_id
    player.planet_landed = None
    sec = u.sectors[sector_id]
    if "A" not in sec.occupant_ids:
        sec.occupant_ids.append("A")


def _planet(u, pid: int, sector: int, ore: int, org: int, eq: int) -> Planet:
    pl = Planet(
        id=pid, sector_id=sector, name=f"P{pid}", class_id=PlanetClass.M,
        owner_id="A", stockpile={FUEL: ore, ORG: org, EQ: eq},
    )
    u.planets[pid] = pl
    if pid not in u.sectors[sector].planet_ids:
        u.sectors[sector].planet_ids.append(pid)
    return pl


def main() -> None:
    u = generate_universe(GameConfig(
        seed=8, universe_size=20, max_days=20, enable_planets=False, enable_ferrengi=False,
    ))
    player = Player(id="A", name="Ada", ship=Ship(), credits=5_000_000, experience=0, alignment=0)
    u.players["A"] = player
    _sit(u, 12)
    u.sectors[12].port = Port(
        class_id=PortClass.CLASS_4_SSB,  # sells fuel and organics, buys equipment
        name="BuyEQ",
        stock={
            FUEL: PortStock(current=0, maximum=3000),
            ORG: PortStock(current=0, maximum=3000),
            EQ: PortStock(current=0, maximum=3000),
        },
        productivity={FUEL: 100, ORG: 100, EQ: 100},
        mcic={FUEL: 50, ORG: 50, EQ: -60},
    )
    home = _planet(u, 7, 12, 0, 0, 6000)
    turns0 = player.turns_today
    res = apply_action(u, "A", Action(
        kind=ActionKind.PORT_UPGRADE, args={"commodity": "equipment", "units": 300},
    ))
    if not res.ok:
        _fail(f"upgrade: {res.error}")
    port = u.sectors[12].port
    if player.credits != 5_000_000 - 270_000:
        _fail(f"credits {player.credits}")
    if player.experience != 90 or player.alignment != 45:
        _fail(f"award exp={player.experience} align={player.alignment}")
    if port.stock[EQ].maximum != 6000:
        _fail(f"capacity {port.stock[EQ].maximum}")
    if player.turns_today != turns0 + 1:
        _fail(f"upgrade turns {player.turns_today}")
    print("upgrade 300 equipment: 270000cr +90exp +45align capacity 6000 turns 1")
    res = apply_action(u, "A", Action(
        kind=ActionKind.PLANET_TRADE,
        args={"planet_id": 7, "commodity": "equipment", "qty": 6000},
    ))
    if not res.ok:
        _fail(f"planet_trade: {res.error}")
    if home.stockpile[EQ] != 0:
        _fail(f"lot left {home.stockpile[EQ]}")
    if player.turns_today != turns0 + 1:
        _fail(f"planet_trade spent a second turn ({player.turns_today})")
    print(f"planet_trade 6000 equipment: credits {player.credits} turns still {player.turns_today}")

    _sit(u, 13)
    u.sectors[13].port = None
    yard = _planet(u, 8, 13, 60, 60, 60)
    res = apply_action(u, "A", Action(
        kind=ActionKind.PORT_BUILD, args={"port_class": "SSS", "planet_id": 8},
    ))
    if not res.ok:
        _fail(f"order SSS: {res.error}")
    print(f"ordered SSS on day {u.day}; days_left {u.sectors[13].port.construction['days_left']}")
    tick_day(u)
    cons = u.sectors[13].port.construction
    if cons is None or int(cons["days_left"]) != 1:
        _fail(f"tick 1 did not progress: {cons}")
    if yard.stockpile[FUEL] != 40:
        _fail(f"tick 1 stock {yard.stockpile[FUEL]}")
    print(f"tick day {u.day}: progress, fuel left {yard.stockpile[FUEL]}")
    yard.stockpile[FUEL] = 0
    stalled_fuel = 0
    tick_day(u)
    cons = u.sectors[13].port.construction
    if cons is None or int(cons["days_left"]) != 1 or yard.stockpile[FUEL] != stalled_fuel:
        _fail(f"stall failed days={None if cons is None else cons['days_left']} fuel={yard.stockpile[FUEL]}")
    print(f"tick day {u.day}: stalled, fuel still {yard.stockpile[FUEL]}")
    yard.stockpile = {FUEL: 20, ORG: 20, EQ: 20}
    exp_before = player.experience
    align_before = player.alignment
    tick_day(u)
    opened = u.sectors[13].port
    if opened is None or opened.construction is not None:
        _fail("SSS did not open")
    if int(opened.productivity[EQ]) != 10 or int(opened.stock[EQ].maximum) != 100:
        _fail(f"open prod {opened.productivity[EQ]} max {opened.stock[EQ].maximum}")
    built = [ev for ev in u.events if getattr(ev.kind, "value", ev.kind) == "port_built"]
    if not built or built[-1].payload.get("exp") != 7 or built[-1].payload.get("align") != 4:
        _fail(f"reward {built[-1].payload if built else None}")
    # tick_day also grants +1 exp and +1 align at midnight, on top of the completion reward.
    if player.experience != exp_before + 7 + 1 or player.alignment != align_before + 4 + 1:
        _fail(f"completion exp {player.experience} align {player.alignment} (before {exp_before}/{align_before})")
    print(f"tick day {u.day}: SSS open productivity 10, reward +7/+4 plus midnight +1/+1")

    _sit(u, 14)
    u.sectors[14].port = None
    u.port_cap = port_count(u)
    _planet(u, 9, 14, 500, 500, 500)
    res = apply_action(u, "A", Action(
        kind=ActionKind.PORT_BUILD, args={"port_class": "BBS", "planet_id": 9},
    ))
    if res.ok or "cannot support another port" not in (res.error or ""):
        _fail(f"cap: {res.error}")
    print(f"cap refuse: {res.error}")

    sec = u.sectors[16]
    sec.port = None
    sec.port_destroyed_day = u.day
    _sit(u, 16)
    _planet(u, 10, 16, 500, 500, 500)
    res = apply_action(u, "A", Action(
        kind=ActionKind.PORT_BUILD, args={"port_class": "BSS", "planet_id": 10},
    ))
    if res.ok or "radiating" not in (res.error or ""):
        _fail(f"radiation: {res.error}")
    print(f"radiation refuse on day {u.day}: {res.error}")
    u.port_cap = port_count(u) + 5
    tick_day(u)
    res = apply_action(u, "A", Action(
        kind=ActionKind.PORT_BUILD, args={"port_class": "BSS", "planet_id": 10},
    ))
    if not res.ok:
        _fail(f"after 1 day: {res.error}")
    print(f"radiation clear on day {u.day}: BSS ordered")
    print("port_upgrade_scenario_lab: PASS")


if __name__ == "__main__":
    main()
