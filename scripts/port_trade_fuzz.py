#!/usr/bin/env python3
"""Random legal port trades against a scratch universe. No server, no paid call.

The expected unit quote is recomputed here from the stock factor, the MCIC
point, and the experience span. It does not call the engine price functions.
Day regen may change how much goods exist. A trade may not.
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
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
from tw2k.engine.runner import apply_action, tick_day  # noqa: E402
from tw2k.engine.universe import generate_universe  # noqa: E402

FIXED_SEEDS: tuple[int, ...] = tuple(range(93001, 93041))
ACTIONS = 300
MIN_OK = 12
PLAYERS = ("P1", "P2", "P3")
START_XP = (0, 400, 1200)
SECTORS = tuple(range(11, 19))
CLASS_NUMS = (1, 2, 3, 4, 5, 6, 7, 8)
COMMODITIES = (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT)
COVERAGE = (
    *(f"class {n}" for n in range(1, 8)),
    *(f"{c.value} buy" for c in COMMODITIES),
    *(f"{c.value} sell" for c in COMMODITIES),
    "haggle_accepted",
    "haggle_rejected",
    "oversize_rejected",
)


def _die(seed: int, step: int, pid: str, message: str) -> None:
    print(f"seed {seed} step {step} {pid}: {message}")
    print("port_trade_fuzz: FAIL")
    raise SystemExit(1)


def _span(experience: int) -> float:
    if experience <= 0:
        return 0.0
    return min(1.0, experience / K.PORT_PRICE_EXPERIENCE_CAP)


def _clamp(base: int, raw: float) -> int:
    cap = base * K.PORT_UNIT_PRICE_MAX_MULT
    price = round(raw)
    if price < 1:
        return 1
    if price > cap:
        return cap
    return price


def _fraction(port: Port, commodity: Commodity) -> float:
    stock = port.stock.get(commodity)
    if stock is None or stock.maximum == 0:
        return 0.0
    return max(0.0, min(1.0, stock.current / stock.maximum))


def _mcic(port: Port, commodity: Commodity) -> int:
    stored = port.mcic.get(commodity)
    if stored is not None:
        return int(stored)
    if port.buys(commodity):
        return K.PORT_MCIC_DEFAULT_BUY
    return K.PORT_MCIC_DEFAULT_SELL


def formula_sell(port: Port, commodity: Commodity, experience: int) -> int:
    """Player pays this. Mirrors PRICE_MODEL.md without calling the engine."""
    base = K.COMMODITY_BASE_PRICE[commodity.value]
    if port.class_id == PortClass.FEDERAL:
        return base
    stock_mult = 1.25 - 0.65 * _fraction(port, commodity)
    mcic_mult = max(0.05, 1.0 + (_mcic(port, commodity) - K.PORT_MCIC_DEFAULT_SELL) * K.PORT_MCIC_POINT)
    exp_mult = 1.0 - K.PORT_EXPERIENCE_BUY_DISCOUNT * _span(experience)
    return _clamp(base, base * stock_mult * mcic_mult * exp_mult)


def formula_buy(port: Port, commodity: Commodity, experience: int) -> int:
    """Port pays this. Mirrors PRICE_MODEL.md without calling the engine."""
    base = K.COMMODITY_BASE_PRICE[commodity.value]
    if port.class_id == PortClass.FEDERAL:
        return base
    stock_mult = 1.45 - 0.70 * _fraction(port, commodity)
    mcic_mult = max(0.05, 1.0 + (K.PORT_MCIC_DEFAULT_BUY - _mcic(port, commodity)) * K.PORT_MCIC_POINT)
    exp_mult = 1.0 + K.PORT_EXPERIENCE_SELL_BONUS * _span(experience)
    return _clamp(base, base * stock_mult * mcic_mult * exp_mult)


def formula_price(port: Port, commodity: Commodity, experience: int, side: str) -> int:
    if side == "buy":
        return formula_sell(port, commodity, experience)
    return formula_buy(port, commodity, experience)


def _goods(universe) -> dict[Commodity, int]:
    totals = {c: 0 for c in COMMODITIES}
    for sector in universe.sectors.values():
        port = sector.port
        if port is None:
            continue
        for commodity, stock in port.stock.items():
            if commodity in totals:
                totals[commodity] += stock.current
    for player in universe.players.values():
        for commodity in totals:
            totals[commodity] += int(player.ship.cargo.get(commodity, 0))
    return totals


def _bounds(universe, seed: int, step: int, pid: str) -> None:
    for player in universe.players.values():
        if player.credits < 0:
            _die(seed, step, pid, f"{player.id} negative credits {player.credits}")
        if player.ship.cargo_free < 0:
            _die(seed, step, pid, f"{player.id} negative holds {player.ship.cargo_free}")
        for commodity in COMMODITIES:
            if int(player.ship.cargo.get(commodity, 0)) < 0:
                _die(seed, step, pid, f"{player.id} negative {commodity.value}")
    for sector in universe.sectors.values():
        port = sector.port
        if port is None:
            continue
        for commodity, stock in port.stock.items():
            if stock.current < 0 or stock.current > stock.maximum:
                _die(seed, step, pid, f"sector {sector.id} {commodity.value} stock {stock.current}")


def _move(universe, pid: str, sector_id: int) -> None:
    player = universe.players[pid]
    old = universe.sectors[player.sector_id]
    if pid in old.occupant_ids:
        old.occupant_ids.remove(pid)
    player.sector_id = sector_id
    if pid not in universe.sectors[sector_id].occupant_ids:
        universe.sectors[sector_id].occupant_ids.append(pid)


def _world(seed: int):
    rng = random.Random(seed + 17)
    universe = generate_universe(
        GameConfig(
            seed=seed,
            universe_size=40,
            max_days=40,
            turns_per_day=8000,
            enable_planets=False,
            enable_ferrengi=False,
        )
    )
    for sector_id, class_num in zip(SECTORS, CLASS_NUMS, strict=True):
        if class_num == 8:
            universe.sectors[sector_id].port = Port(class_id=PortClass.STARDOCK, name="StarDock")
            continue
        trades = K.PORT_CLASS_TRADES[class_num]
        stock: dict[Commodity, PortStock] = {}
        mcic: dict[Commodity, int] = {}
        productivity: dict[Commodity, int] = {}
        for idx, deal in enumerate(trades):
            if deal is None:
                continue
            commodity = COMMODITIES[idx]
            maximum = rng.randint(800, 3200)
            current = rng.randint(0, maximum)
            stock[commodity] = PortStock(current=current, maximum=maximum)
            if deal:
                mcic[commodity] = -rng.randint(300, 800) if rng.random() < 0.2 else -rng.randint(1, 100)
            else:
                mcic[commodity] = rng.randint(300, 800) if rng.random() < 0.2 else rng.randint(1, 100)
            productivity[commodity] = rng.randint(1, K.PORT_PRODUCTIVITY_MAX)
        universe.sectors[sector_id].port = Port(
            class_id=PortClass(class_num),
            name=f"Class{class_num}",
            stock=stock,
            mcic=mcic,
            productivity=productivity,
        )
    for pid, xp, sector_id in zip(PLAYERS, START_XP, SECTORS[:3], strict=True):
        ship = Ship(holds=200)
        for commodity in COMMODITIES:
            ship.cargo[commodity] = 40
        player = Player(
            id=pid,
            name=pid,
            ship=ship,
            credits=5_000_000,
            turns_per_day=8000,
            experience=xp,
            sector_id=sector_id,
        )
        universe.players[pid] = player
        universe.sectors[sector_id].occupant_ids.append(pid)
    return universe


def _options(universe, pid: str) -> list[tuple[str, str, int, int]]:
    for entry in legal_actions(universe, pid):
        if entry.kind != ActionKind.TRADE.value or not entry.legal:
            continue
        max_by = entry.params.get("qty", {}).get("max_by", {})
        listed = entry.params.get("unit_price", {}).get("listed_by", {})
        found = []
        for commodity, sides in max_by.items():
            for side, mx in sides.items():
                if int(mx) < 1:
                    continue
                price = listed.get(commodity, {}).get(side)
                if price is None:
                    continue
                found.append((commodity, side, int(mx), int(price)))
        return found
    return []


def _check_lists(universe, pid: str, seed: int, step: int, options) -> None:
    player = universe.players[pid]
    port = universe.sectors[player.sector_id].port
    for commodity_name, side, _mx, listed in options:
        commodity = Commodity(commodity_name)
        expect = formula_price(port, commodity, int(player.experience), side)
        if listed != expect:
            _die(seed, step, pid, f"engine quote {listed} != formula {expect} for {side} {commodity_name}")


def _act(universe, pid: str, side: str, commodity: str, qty: int, offer: int | None):
    args: dict = {"side": side, "commodity": commodity, "qty": qty}
    if offer is not None:
        args["unit_price"] = offer
    return apply_action(universe, pid, Action(kind=ActionKind.TRADE, args=args))


def _one(universe, rng: random.Random, pid: str, seed: int, step: int, counts: Counter) -> None:
    if rng.random() < 0.4:
        _move(universe, pid, rng.choice(SECTORS))
    options = _options(universe, pid)
    if not options:
        return
    _check_lists(universe, pid, seed, step, options)
    commodity_name, side, mx, listed = rng.choice(options)
    commodity = Commodity(commodity_name)
    roll = rng.random()
    offer: int | None = None
    qty = rng.randint(1, mx)
    kind = "fair"
    if roll < 0.18:
        kind = "oversize"
        qty = mx + rng.randint(1, 40)
    elif roll < 0.40 and listed > 1:
        kind = "modest"
        offer = listed - 1 if side == "buy" else listed + 1
    elif roll < 0.62:
        kind = "wild"
        offer = max(1, listed // 2) if side == "buy" else listed * 2
        if offer == listed:
            kind = "fair"
            offer = None
    player = universe.players[pid]
    port = universe.sectors[player.sector_id].port
    class_num = int(port.class_id)
    before_goods = _goods(universe)
    before_credits = player.credits
    before_turns = player.turns_today
    before_cargo = int(player.ship.cargo.get(commodity, 0))
    result = _act(universe, pid, side, commodity_name, qty, offer)
    if kind == "oversize":
        if result.ok:
            _die(seed, step, pid, "oversize trade was accepted")
        if player.credits != before_credits or player.turns_today != before_turns:
            _die(seed, step, pid, "failed trade changed credits or spent a turn")
        if _goods(universe) != before_goods:
            _die(seed, step, pid, "failed trade created or destroyed goods")
        counts["oversize_rejected"] += 1
        _bounds(universe, seed, step, pid)
        return
    if not result.ok:
        _die(seed, step, pid, f"{side} {commodity_name} x{qty} failed: {result.error}")
    delta = before_credits - player.credits if side == "buy" else player.credits - before_credits
    if qty <= 0 or delta % qty != 0:
        _die(seed, step, pid, f"credits moved {delta} for qty {qty}")
    paid = delta // qty
    base = K.COMMODITY_BASE_PRICE[commodity_name]
    cap = base * K.PORT_UNIT_PRICE_MAX_MULT
    # The cap binds the list quote. An accepted haggle settles at the player's
    # offer, which may sit one credit past that cap.
    if paid < 1 or (offer is None and paid > cap):
        _die(seed, step, pid, f"paid {paid} outside 1..{cap}")
    if side == "buy" and paid > listed:
        _die(seed, step, pid, f"buy paid {paid} above list {listed}")
    if side == "sell" and paid < listed:
        _die(seed, step, pid, f"sell paid {paid} below list {listed}")
    if offer is None:
        if paid != listed:
            _die(seed, step, pid, f"fair trade paid {paid}, list {listed}")
    elif paid != offer and paid != listed:
        _die(seed, step, pid, f"haggle paid {paid}, offer {offer}, list {listed}")
    if _goods(universe) != before_goods:
        _die(seed, step, pid, "trade created or destroyed goods")
    _bounds(universe, seed, step, pid)
    if class_num != 8:
        counts[f"class {class_num}"] += 1
    counts[f"{commodity_name} {side}"] += 1
    if offer is not None and paid == offer and offer != listed:
        counts["haggle_accepted"] += 1
    elif offer is not None and paid == listed:
        counts["haggle_rejected"] += 1
    player.experience = int(player.experience) + 5
    if side == "buy" and step % 7 == 0:
        _sell_back(universe, pid, commodity, commodity_name, qty, before_credits, before_cargo, seed, step, counts)


def _sell_back(universe, pid, commodity, commodity_name, qty, credits_before, cargo_before, seed, step, counts) -> None:
    """A buy then a sell at this same port must not raise credits if cargo returns."""
    player = universe.players[pid]
    after_buy = player.credits
    turns = player.turns_today
    goods = _goods(universe)
    result = _act(universe, pid, "sell", commodity_name, qty, None)
    if not result.ok:
        if player.credits != after_buy or player.turns_today != turns or _goods(universe) != goods:
            _die(seed, step, pid, "failed sell-back changed the world")
        counts["oversize_rejected"] += 0
        return
    if _goods(universe) != goods:
        _die(seed, step, pid, "sell-back created or destroyed goods")
    if int(player.ship.cargo.get(commodity, 0)) == cargo_before and player.credits > credits_before:
        _die(seed, step, pid, f"same-port round trip grew credits {credits_before} -> {player.credits}")
    _bounds(universe, seed, step, pid)


def _run_seed(seed: int, counts: Counter) -> None:
    rng = random.Random(seed)
    universe = _world(seed)
    baseline = _goods(universe)
    for step in range(ACTIONS):
        if rng.random() < 0.05:
            tick_day(universe)
            baseline = _goods(universe)
        for pid in PLAYERS:
            _one(universe, rng, pid, seed, step, counts)
        if _goods(universe) != baseline:
            _die(seed, step, "-", "goods changed outside a trade")
    print(f"| {seed} | pass |")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=len(FIXED_SEEDS))
    parser.add_argument("--force-zero", choices=COVERAGE, default=None)
    args = parser.parse_args()
    counts: Counter = Counter()
    print("| Seed | Result |")
    for seed in FIXED_SEEDS[: args.seeds]:
        _run_seed(seed, counts)
    if args.force_zero:
        counts[args.force_zero] = 0
    print("| Kind | Count |")
    for kind in COVERAGE:
        print(f"| {kind} | {counts[kind]} |")
    for kind in COVERAGE:
        if counts[kind] == 0:
            print(f"coverage: {kind} never succeeded")
            print("port_trade_fuzz: FAIL")
            raise SystemExit(1)
        if counts[kind] < MIN_OK:
            print(f"coverage: {kind} below {MIN_OK}")
            print("port_trade_fuzz: FAIL")
            raise SystemExit(1)
    print("port_trade_fuzz: PASS")


if __name__ == "__main__":
    main()
