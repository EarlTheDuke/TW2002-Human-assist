#!/usr/bin/env python3
"""Random buy and sell against two scratch ports. No server, no paid call.

Each seed is fixed. The trader alternates a 1-unit buy at a sell port and
a 1-unit sell at a buy port. A bad quantity is tried on a regular cadence.
The first broken rule exits 1.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tw2k.engine import constants as K  # noqa: E402
from tw2k.engine.actions import Action, ActionKind  # noqa: E402
from tw2k.engine.legality import legal_actions  # noqa: E402
from tw2k.engine.models import (  # noqa: E402
    Commodity,
    GameConfig,
    Player,
    Port,
    PortClass,
    PortStock,
    Ship,
)
from tw2k.engine.runner import apply_action  # noqa: E402
from tw2k.engine.universe import generate_universe  # noqa: E402

FIXED_SEEDS: tuple[int, ...] = tuple(range(92001, 92011))
ACTIONS = 200
MIN_OK = 40
SELL_SECTOR = 15
BUY_SECTOR = 16
FUEL = Commodity.FUEL_ORE


def _die(seed: int, step: int, message: str) -> None:
    print(f"seed {seed} step {step}: {message}")
    print("port_trade_fuzz: FAIL")
    raise SystemExit(1)


def _listed(universe, pid: str, side: str) -> int | None:
    for entry in legal_actions(universe, pid):
        if entry.kind != ActionKind.TRADE.value or not entry.legal:
            continue
        cell = entry.params.get("unit_price", {}).get("listed_by", {}).get(FUEL.value, {})
        if side in cell:
            return int(cell[side])
    return None


def _snap(universe, pid: str) -> tuple:
    player = universe.players[pid]
    port = universe.sectors[player.sector_id].port
    stock = None if port is None else (port.stock[FUEL].current, port.stock[FUEL].maximum)
    return (
        player.credits,
        player.turns_today,
        player.ship.cargo.get(FUEL, 0),
        player.ship.cargo_free,
        stock,
    )


def _move(universe, pid: str, sector_id: int) -> None:
    player = universe.players[pid]
    old = universe.sectors[player.sector_id]
    if pid in old.occupant_ids:
        old.occupant_ids.remove(pid)
    player.sector_id = sector_id
    universe.sectors[sector_id].occupant_ids.append(pid)


def _world(seed: int):
    universe = generate_universe(
        GameConfig(
            seed=seed,
            universe_size=30,
            max_days=2,
            enable_planets=False,
            enable_ferrengi=False,
        )
    )
    rng = random.Random(seed)
    universe.sectors[SELL_SECTOR].port = Port(
        class_id=PortClass.CLASS_4_SSB,
        name="SellFuel",
        stock={FUEL: PortStock(current=2500, maximum=3000)},
        mcic={FUEL: rng.randint(1, K.PORT_MCIC_MAX)},
        productivity={FUEL: rng.randint(1, K.PORT_PRODUCTIVITY_MAX)},
    )
    universe.sectors[BUY_SECTOR].port = Port(
        class_id=PortClass.CLASS_1_BSS,
        name="BuyFuel",
        stock={FUEL: PortStock(current=200, maximum=3000)},
        mcic={FUEL: rng.randint(K.PORT_MCIC_MIN, -1)},
        productivity={FUEL: rng.randint(1, K.PORT_PRODUCTIVITY_MAX)},
    )
    player = Player(
        id="P1",
        name="Trader",
        ship=Ship(),
        credits=2_000_000,
        turns_per_day=8000,
        experience=900 if seed % 2 else 0,
    )
    player.ship.cargo[FUEL] = 8
    player.sector_id = SELL_SECTOR
    universe.players["P1"] = player
    universe.sectors[SELL_SECTOR].occupant_ids.append("P1")
    return universe


def _check_bounds(universe, pid: str, seed: int, step: int) -> None:
    player = universe.players[pid]
    if player.credits < 0:
        _die(seed, step, f"negative credits {player.credits}")
    if player.ship.cargo_free < 0:
        _die(seed, step, f"negative holds {player.ship.cargo_free}")
    if player.ship.cargo.get(FUEL, 0) < 0:
        _die(seed, step, "negative cargo")
    for sector in (SELL_SECTOR, BUY_SECTOR):
        stock = universe.sectors[sector].port.stock[FUEL]
        if stock.current < 0 or stock.current > stock.maximum:
            _die(seed, step, f"stock {stock.current} outside 0..{stock.maximum}")


def _run_seed(seed: int) -> tuple[int, int]:
    universe = _world(seed)
    buy_ok = 0
    sell_ok = 0
    for step in range(ACTIONS):
        if step % 11 == 10:
            before = _snap(universe, "P1")
            turns = universe.players["P1"].turns_today
            result = apply_action(
                universe,
                "P1",
                Action(kind=ActionKind.TRADE, args={"side": "buy", "commodity": FUEL.value, "qty": 10**9}),
            )
            if result.ok:
                _die(seed, step, "huge buy was accepted")
            if _snap(universe, "P1") != before:
                _die(seed, step, "failed buy changed credits, stock, or holds")
            if universe.players["P1"].turns_today != turns:
                _die(seed, step, "failed buy spent a turn")
            continue

        buying = step % 2 == 0
        _move(universe, "P1", SELL_SECTOR if buying else BUY_SECTOR)
        side = "buy" if buying else "sell"
        quote = _listed(universe, "P1", side)
        if quote is None:
            _die(seed, step, f"no listed {side} price")
        base = K.COMMODITY_BASE_PRICE[FUEL.value]
        cap = base * K.PORT_UNIT_PRICE_MAX_MULT
        if quote < 1 or quote > cap:
            _die(seed, step, f"price {quote} outside 1..{cap}")
        credits_before = universe.players["P1"].credits
        result = apply_action(
            universe,
            "P1",
            Action(kind=ActionKind.TRADE, args={"side": side, "commodity": FUEL.value, "qty": 1}),
        )
        if not result.ok:
            _die(seed, step, f"{side} failed: {result.error}")
        delta = credits_before - universe.players["P1"].credits
        expect = quote if buying else -quote
        if delta != expect:
            _die(seed, step, f"credits moved {delta}, quote {expect}")
        if buying:
            buy_ok += 1
            after_buy = universe.players["P1"].credits
            back = apply_action(
                universe,
                "P1",
                Action(kind=ActionKind.TRADE, args={"side": "sell", "commodity": FUEL.value, "qty": 1}),
            )
            if back.ok and universe.players["P1"].credits > credits_before:
                _die(seed, step, "buy-then-sell at one port made a profit")
            if not back.ok and universe.players["P1"].credits != after_buy:
                _die(seed, step, "failed sell-back changed credits")
        else:
            sell_ok += 1
        _check_bounds(universe, "P1", seed, step)
    return buy_ok, sell_ok


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=len(FIXED_SEEDS))
    parser.add_argument("--force-zero", choices=("buy", "sell"), default=None)
    args = parser.parse_args()
    seeds = FIXED_SEEDS[: args.seeds]
    total_buy = 0
    total_sell = 0
    print("| Seed | Buy ok | Sell ok |")
    for seed in seeds:
        buy_ok, sell_ok = _run_seed(seed)
        total_buy += buy_ok
        total_sell += sell_ok
        flag = "pass" if buy_ok >= 10 and sell_ok >= 10 else "fail"
        print(f"| {seed} | {buy_ok} | {sell_ok} | {flag} |")
        if flag == "fail":
            print("port_trade_fuzz: FAIL")
            raise SystemExit(1)
    if args.force_zero == "buy":
        total_buy = 0
    elif args.force_zero == "sell":
        total_sell = 0
    if total_buy == 0:
        print("coverage: buy never succeeded")
        print("port_trade_fuzz: FAIL")
        raise SystemExit(1)
    if total_sell == 0:
        print("coverage: sell never succeeded")
        print("port_trade_fuzz: FAIL")
        raise SystemExit(1)
    if total_buy < MIN_OK or total_sell < MIN_OK:
        kind = "buy" if total_buy < MIN_OK else "sell"
        print(f"coverage: {kind} below {MIN_OK}")
        print("port_trade_fuzz: FAIL")
        raise SystemExit(1)
    print("port_trade_fuzz: PASS")


if __name__ == "__main__":
    main()
