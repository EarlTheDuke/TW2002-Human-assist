"""Offline fixtures for the parity prompt. No paid API.

Prints sizes and a contradiction checklist. Exit 0 when every parity check is green
and the matching legacy check is red.
"""

from __future__ import annotations

import os
import sys

from tw2k.agents.prompts import format_observation, get_system_prompt
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.models import (
    AlienTrader,
    Commodity,
    Planet,
    PlanetClass,
    Player,
    Port,
    PortClass,
    PortStock,
    Ship,
    ShipClass,
)
from tw2k.engine.observation import build_observation

FUEL, ORG, EQ = Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT
CONTRADICTIONS = ("500k cr at StarDock", "corp_deposit", "corp_withdraw", "shared treasury")


def _world():
    return generate_universe(GameConfig(
        seed=60, universe_size=500, max_days=3, enable_planets=False, enable_ferrengi=False,
    ))


def _hops_away(universe, hops: int) -> int:
    start = int(K.STARDOCK_SECTOR)
    seen = {start}
    layer = [start]
    for _ in range(hops):
        nxt: list[int] = []
        for sid in layer:
            for dest in universe.sectors[sid].warps:
                if dest not in seen:
                    seen.add(dest)
                    nxt.append(dest)
        if not nxt:
            raise RuntimeError(f"galaxy has no sector {hops} hops from StarDock")
        layer = nxt
    for sid in layer:
        if sid not in K.FEDSPACE_SECTORS:
            return int(sid)
    return int(layer[0])


def _seat(universe, pid: str, name: str, sector: int, credits: int, alignment: int = 200) -> Player:
    player = Player(
        id=pid, name=name, sector_id=sector, credits=credits, alignment=alignment,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER),
    )
    universe.players[pid] = player
    occupants = universe.sectors[sector].occupant_ids
    if pid not in occupants:
        occupants.append(pid)
    return player


def _act(universe, pid: str, kind: ActionKind, args: dict) -> None:
    result = apply_action(universe, pid, Action(kind=kind, args=args))
    if not result.ok:
        raise RuntimeError(f"{kind.value} for {pid} failed: {result.error}")


def _trading_port(universe, sector: int) -> None:
    universe.sectors[sector].port = Port(
        class_id=PortClass.CLASS_6_BBS,
        name="Lab",
        stock={
            FUEL: PortStock(current=1000, maximum=3000),
            ORG: PortStock(current=1000, maximum=3000),
            EQ: PortStock(current=1000, maximum=3000),
        },
        productivity={FUEL: 100, ORG: 100, EQ: 100},
        mcic={FUEL: -60, ORG: -60, EQ: 50},
    )


def fixtures() -> dict[str, tuple]:
    """name -> (universe, player id). Built once; rendered under both modes."""
    f1 = _world()
    _seat(f1, "P1", "P1", _hops_away(f1, 10), 250_000)

    f2 = _world()
    _seat(f2, "P1", "P1", int(K.STARDOCK_SECTOR), 300_000)

    f3 = _world()
    _seat(f3, "P1", "P1", int(K.STARDOCK_SECTOR), int(K.TAX_THRESHOLD) + 80_000, alignment=500)

    f4 = _world()
    home = _hops_away(f4, 2)
    _seat(f4, "P1", "P1", home, 50_000)
    _seat(f4, "P2", "P2", home, 10_000)
    _act(f4, "P1", ActionKind.CORP_CREATE, {"ticker": "ABC", "name": "Abe"})
    _act(f4, "P1", ActionKind.CORP_SET_PASSWORD, {"password": "secret1"})
    _act(f4, "P1", ActionKind.CORP_INVITE, {"target": "P2"})

    f5 = _world()
    home = _hops_away(f5, 2)
    _seat(f5, "P1", "P1", home, 80_000)
    _seat(f5, "P2", "P2", home, 5_000)
    _act(f5, "P1", ActionKind.CORP_CREATE, {"ticker": "ABC", "name": "Abe"})
    _act(f5, "P1", ActionKind.CORP_SET_PASSWORD, {"password": "secret1"})
    _act(f5, "P1", ActionKind.CORP_INVITE, {"target": "P2"})
    _act(f5, "P2", ActionKind.CORP_JOIN, {"ticker": "ABC", "password": "secret1"})

    f6 = _world()
    sector = _hops_away(f6, 3)
    _seat(f6, "P1", "P1", sector, 100_000)
    _trading_port(f6, sector)
    planet = Planet(
        id=7, sector_id=sector, name="Home", class_id=PlanetClass.M, owner_id="P1",
        stockpile={FUEL: 500, ORG: 500, EQ: 500},
    )
    f6.planets[7] = planet
    f6.sectors[sector].planet_ids.append(7)

    f7 = _world()
    sector = _hops_away(f7, 4)
    _seat(f7, "P1", "P1", sector, 20_000)
    f7.aliens["alien:1"] = AlienTrader(
        id="alien:1", name="Vorn", ship_name="Vorn's cruiser", sector_id=sector,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=20, shields=0),
        experience=100, alignment=-80, credits=1000,
    )

    return {
        "f1": (f1, "P1"),
        "f2": (f2, "P1"),
        "f3": (f3, "P1"),
        "f4": (f4, "P2"),
        "f5": (f5, "P1"),
        "f6": (f6, "P1"),
        "f7": (f7, "P1"),
        "f8": (f1, "P1"),
    }


def _render(universe, pid: str, *, parity: bool, minimal: bool) -> tuple[str, str, str]:
    K.LLM_PARITY_MODE = "tw2002" if parity else "legacy"
    if minimal:
        os.environ["TW2K_HINT_LEVEL"] = "minimal"
    else:
        os.environ.pop("TW2K_HINT_LEVEL", None)
    obs = build_observation(universe, pid)
    return get_system_prompt(), format_observation(obs), obs.action_hint or ""


def checklist() -> list[str]:
    """Empty when the lab's contradiction checks all hold."""
    fails: list[str] = []
    built = fixtures()
    rows: list[str] = []
    obs_growth: list[float] = []
    saved_mode = K.LLM_PARITY_MODE
    try:
        for name, (universe, pid) in built.items():
            minimal = name == "f8"
            par_prompt, par_obs, par_hint = _render(universe, pid, parity=True, minimal=minimal)
            leg_prompt, leg_obs, leg_hint = _render(universe, pid, parity=False, minimal=minimal)
            for bad in CONTRADICTIONS:
                if bad in par_prompt:
                    fails.append(f"{name} parity prompt still has {bad!r}")
                if name == "f1" and bad == "500k cr at StarDock" and bad not in leg_prompt:
                    fails.append("legacy prompt lost the 500k StarDock line")
            if minimal and len(par_prompt) >= len(_render(universe, pid, parity=True, minimal=False)[0]):
                fails.append("minimal parity prompt is not shorter than full")
            if name == "f1":
                if "warp back" in par_hint:
                    fails.append("f1 parity hint still says warp back")
                if '"execute":true' not in par_hint:
                    fails.append("f1 parity hint does not name plot_course execute")
                if "warp back" not in leg_hint:
                    fails.append("f1 legacy hint lost warp back")
            if name == "f4" and "secret1" in par_hint:
                fails.append("f4 parity hint copied the corp password")
            if name == "f5" and "corp_transfer" not in par_obs:
                fails.append("f5 observation does not list corp_transfer")
            if name == "f6" and "port_upgrade" not in par_obs:
                fails.append("f6 observation does not list port_upgrade")
            if name == "f7" and "alien:1" not in par_obs:
                fails.append("f7 observation does not show alien:1")
            if '"args":' not in par_obs:
                fails.append(f"{name} parity observation has no args hints")
            if '"args":' in leg_obs:
                fails.append(f"{name} legacy observation gained args hints")
            growth = 100.0 * (len(par_obs) - len(leg_obs)) / max(1, len(leg_obs))
            obs_growth.append(growth)
            rows.append(
                f"{name} prompt {len(leg_prompt)} -> {len(par_prompt)}  "
                f"obs {len(leg_obs)} -> {len(par_obs)} ({growth:.1f}%)"
            )
        obs_growth.sort()
        median = obs_growth[len(obs_growth) // 2]
        if median > float(K.LLM_OBS_GROWTH_MAX_PCT):
            fails.append(f"observation median growth {median:.1f}% exceeds {K.LLM_OBS_GROWTH_MAX_PCT}%")
        legacy_prompt = _render(built["f1"][0], "P1", parity=False, minimal=False)[0]
        parity_prompt = _render(built["f1"][0], "P1", parity=True, minimal=False)[0]
        prompt_growth = 100.0 * (len(parity_prompt) - len(legacy_prompt)) / max(1, len(legacy_prompt))
        if prompt_growth > float(K.LLM_PROMPT_GROWTH_MAX_PCT):
            fails.append(f"prompt growth {prompt_growth:.1f}% exceeds {K.LLM_PROMPT_GROWTH_MAX_PCT}%")
        print("llm_prompt_fixture_lab")
        for row in rows:
            print(row)
        print(f"obs median growth {median:.1f}%")
        print(f"full prompt growth {prompt_growth:.2f}%")
    finally:
        K.LLM_PARITY_MODE = saved_mode
        os.environ.pop("TW2K_HINT_LEVEL", None)
    return fails


def main() -> int:
    fails = checklist()
    if fails:
        print("checklist: FAIL")
        for item in fails:
            print(" -", item)
        return 1
    print("checklist: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
