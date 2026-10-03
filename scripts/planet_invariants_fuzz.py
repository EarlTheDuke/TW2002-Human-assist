#!/usr/bin/env python3
"""Random planet actions against a scratch universe. No server, no ports.

Each seed is fixed. Each of 3 players takes 200 legal planet actions.
A day tick runs every 25 actions. The first broken rule exits 1 and
prints the seed, the actions so far, and the rule.
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
    Corporation,
    EventKind,
    FighterDeployment,
    GameConfig,
    Planet,
    PlanetClass,
    Player,
    Ship,
)
from tw2k.engine.runner import _bfs_path, apply_action, tick_day  # noqa: E402
from tw2k.engine.universe import generate_universe  # noqa: E402

# Forty fixed seeds. --seeds N uses the first N. A seed listed in XFAIL is a
# known engine bug: the script still runs it, prints xfail, and does not
# exit 1. Do not add a seed here to hide a new failure.
FIXED_SEEDS: tuple[int, ...] = tuple(range(91001, 91041))
XFAIL: frozenset[int] = frozenset()
ACTIONS_PER_PLAYER = 200
DAY_EVERY = 25
PLAYERS = ("A", "B", "C")
PLANET_KINDS = frozenset({
    ActionKind.DEPOSIT_PLANET_DEFENSE.value,
    ActionKind.WITHDRAW_PLANET_DEFENSE.value,
    ActionKind.DEPOSIT_TREASURY.value,
    ActionKind.WITHDRAW_TREASURY.value,
    ActionKind.LAND_PLANET.value,
    ActionKind.LIFTOFF.value,
    ActionKind.SET_QUASAR_SECTOR.value,
    ActionKind.SET_QUASAR_ATM.value,
    ActionKind.SET_MILITARY_REACTION.value,
    ActionKind.PLANET_TRANSWARP.value,
    ActionKind.PLANET_BUY_TRANSPORTER.value,
    ActionKind.PLANET_TRANSPORT.value,
    ActionKind.PLANET_DESTROY.value,
    ActionKind.CORP_JOIN.value,
    ActionKind.CORP_LEAVE.value,
    ActionKind.BUILD_CITADEL.value,
    ActionKind.ASSIGN_COLONISTS.value,
    ActionKind.LOAD_PLANET_CARGO.value,
    ActionKind.DUMP_PLANET_CARGO.value,
    ActionKind.ATTACK.value,
})
# These two failures still spend the turn and may change the fight.
CHARGED_FAIL = frozenset({
    "planetary defenses repelled landing",
    "interdicted by a planet",
})


def _credits(universe) -> dict[str, int]:
    return {pid: int(player.credits) for pid, player in universe.players.items()}


def _explained_total(before: dict[str, int], events, universe) -> int:
    """Player-credit total after applying the figures the new events carry."""
    credits = dict(before)
    for ev in events:
        payload = ev.payload or {}
        actor = ev.actor_id
        if ev.kind is EventKind.PLANET_TREASURY and actor in credits:
            amount = int(payload.get("amount") or 0)
            sign = -1 if payload.get("direction") == "deposit" else 1
            credits[actor] += sign * amount
        elif ev.kind is EventKind.BUILD_CITADEL and payload.get("paid_from") == "personal":
            if actor in credits:
                credits[actor] -= int(payload.get("cost_cr") or 0)
        elif ev.kind is EventKind.PLANET_TRANSPORTER_BOUGHT and actor in credits:
            credits[actor] -= int(K.PLANET_TRANSPORTER_COST_FIRST)
        elif ev.kind is EventKind.PLANET_TRANSPORT and actor in credits:
            hops = len(_bfs_path(universe, int(payload["from_sector"]), int(payload["to_sector"])))
            if hops > 0:
                credits[actor] -= (
                    K.PLANET_TRANSPORTER_COST_FIRST + K.PLANET_TRANSPORTER_COST_EXTRA * (hops - 1)
                )
        elif ev.kind is EventKind.PLANET_TAX_PAYOUT and actor in credits:
            credits[actor] += int(payload.get("payout") or 0)
        elif ev.kind is EventKind.SHIP_DESTROYED:
            victim = payload.get("victim")
            if payload.get("kind") == "ferrengi" and actor in credits:
                credits[actor] += int(payload.get("bounty") or 0)
            elif victim in credits:
                credits[victim] = int(credits[victim] * 0.75)
    return sum(credits.values())


def _fingerprint(universe, pid: str) -> tuple:
    player = universe.players[pid]
    cargo = tuple(sorted((c.value, int(n)) for c, n in (player.ship.cargo or {}).items()))
    return (
        player.credits,
        player.alive,
        player.sector_id,
        player.planet_landed,
        player.corp_ticker,
        player.alignment,
        player.ship.fighters,
        player.ship.shields,
        cargo,
        universe.day,
    )


def _world(universe) -> tuple:
    planets = []
    for planet in sorted(universe.planets.values(), key=lambda item: item.id):
        cols = tuple(sorted((c.value, int(n)) for c, n in planet.colonists.items()))
        stock = tuple(sorted((c.value, int(n)) for c, n in planet.stockpile.items()))
        planets.append((
            planet.id, planet.sector_id, planet.owner_id, planet.corp_ticker,
            planet.fighters, planet.shields, planet.treasury, planet.citadel_level,
            planet.citadel_target, planet.has_transporter, cols, stock,
            planet.quasar_sector_pct, planet.quasar_atm_pct, planet.military_reaction_pct,
        ))
    sectors = tuple(sorted(
        (sector.id, tuple(sector.planet_ids), tuple(sector.occupant_ids))
        for sector in universe.sectors.values()
    ))
    corps = tuple(sorted(
        (corp.ticker, tuple(corp.member_ids), corp.treasury)
        for corp in universe.corporations.values()
    ))
    ships = tuple(_fingerprint(universe, pid) for pid in PLAYERS if pid in universe.players)
    return (universe.day, ships, tuple(planets), sectors, corps)


def _negatives(universe) -> str | None:
    for player in universe.players.values():
        if player.credits < 0:
            return f"{player.id} credits {player.credits}"
        if player.ship.fighters < 0 or player.ship.shields < 0:
            return f"{player.id} ship fighters/shields"
        for _name, count in (player.ship.cargo or {}).items():
            if int(count) < 0:
                return f"{player.id} cargo"
    for planet in universe.planets.values():
        if planet.fighters < 0 or planet.shields < 0 or planet.treasury < 0:
            return f"planet {planet.id} fighters/shields/treasury"
        for count in planet.colonists.values():
            if int(count) < 0:
                return f"planet {planet.id} colonists"
        for count in planet.stockpile.values():
            if int(count) < 0:
                return f"planet {planet.id} stockpile"
    for corp in universe.corporations.values():
        if corp.treasury < 0:
            return f"corp {corp.ticker} treasury"
    for sector in universe.sectors.values():
        if sector.fighters is not None and sector.fighters.count < 0:
            return f"sector {sector.id} fighters"
    return None


def _structure(universe) -> str | None:
    for sector in universe.sectors.values():
        for planet_id in sector.planet_ids:
            planet = universe.planets.get(int(planet_id))
            if planet is None:
                return f"sector {sector.id} lists missing planet {planet_id}"
            if planet.sector_id != sector.id:
                return f"planet {planet.id} is listed in {sector.id} but sits in {planet.sector_id}"
    for planet in universe.planets.values():
        if planet.owner_id is not None and planet.owner_id not in universe.players:
            return f"planet {planet.id} owner {planet.owner_id} is not a player"
        if planet.corp_ticker is not None and planet.corp_ticker not in universe.corporations:
            return f"planet {planet.id} ticker {planet.corp_ticker} is not a corp"
    for player in universe.players.values():
        if player.planet_landed is None:
            continue
        planet = universe.planets.get(int(player.planet_landed))
        if planet is None:
            return f"{player.id} planet_landed {player.planet_landed} is missing"
        if planet.sector_id != player.sector_id:
            return f"{player.id} is landed on planet {planet.id} in sector {planet.sector_id}"
    return None


def _check(universe) -> str | None:
    return _negatives(universe) or _structure(universe)


def _sample(rng: random.Random, universe, spec) -> dict | None:
    args: dict = {}
    params = spec.params or {}
    for name, spec_item in params.items():
        if not isinstance(spec_item, dict):
            continue
        if "choices" in spec_item:
            choices = list(spec_item["choices"])
            if spec_item.get("required") and not choices:
                return None
            if choices:
                args[name] = rng.choice(choices)
        elif name == "dest_sector":
            args[name] = rng.choice(list(universe.sectors))
        elif "min" in spec_item and "max" in spec_item and "max_by" not in spec_item:
            lo = int(spec_item["min"])
            hi = int(spec_item["max"])
            if hi < lo:
                return None
            args[name] = rng.randint(lo, hi)
    for name, spec_item in params.items():
        if not isinstance(spec_item, dict) or "max_by" not in spec_item:
            continue
        key = args.get("kind") or args.get("commodity") or args.get("from")
        table = spec_item["max_by"]
        if key not in table:
            return None
        hi = int(table[key])
        lo = int(spec_item.get("min", 1))
        if hi < lo:
            return None
        args[name] = rng.randint(lo, hi)
    return args


def _build(seed: int):
    universe = generate_universe(GameConfig(
        seed=seed,
        universe_size=36,
        max_days=80,
        turns_per_day=1000,
        starting_credits=250_000,
        enable_ferrengi=False,
        enable_planets=False,
        enable_corps=True,
        planet_spawn_probability=0,
    ))
    deep = [sid for sid in sorted(universe.sectors) if sid > 10]
    homes = deep[:4]
    for index, pid in enumerate(PLAYERS):
        player = Player(
            id=pid, name=pid, ship=Ship(), sector_id=homes[index], credits=250_000,
            turns_per_day=1000,
        )
        player.ship.fighters = 80
        player.ship.shields = 40
        player.ship.cargo[Commodity.COLONISTS] = 400
        player.ship.cargo[Commodity.FUEL_ORE] = 20
        universe.players[pid] = player
        universe.sectors[homes[index]].occupant_ids.append(pid)
    universe.corporations["ZZ"] = Corporation(
        ticker="ZZ", name="ZZ", ceo_id="A", member_ids=["A", "B"], invited_ids=["C"],
    )
    universe.corporations["YY"] = Corporation(
        ticker="YY", name="YY", ceo_id="C", member_ids=["C"], invited_ids=["A"],
    )
    universe.players["A"].corp_ticker = "ZZ"
    universe.players["B"].corp_ticker = "ZZ"
    universe.players["C"].corp_ticker = "YY"
    classes = (PlanetClass.M, PlanetClass.K, PlanetClass.O, PlanetClass.H)
    levels = (0, 2, 4, 6)
    owners = ("A", "B", "C", "A")
    tickers = ("ZZ", "ZZ", "YY", "ZZ")
    for index, sid in enumerate(homes):
        level = levels[index]
        planet = Planet(
            id=88101 + index, sector_id=sid, name=f"Fuzz{index}", class_id=classes[index],
            owner_id=owners[index], corp_ticker=tickers[index],
            citadel_level=level, citadel_target=level,
            fighters=0 if level == 0 else 12, shields=0 if level < 2 else 8,
            treasury=0 if level == 0 else 4000, has_transporter=level == 4,
        )
        planet.colonists[Commodity.FUEL_ORE] = 2000
        planet.colonists[Commodity.ORGANICS] = 800
        planet.colonists[Commodity.EQUIPMENT] = 800
        planet.stockpile[Commodity.FUEL_ORE] = 30000
        planet.stockpile[Commodity.ORGANICS] = 4000
        planet.stockpile[Commodity.EQUIPMENT] = 2000
        universe.planets[planet.id] = planet
        universe.sectors[sid].planet_ids.append(planet.id)
        if index < 3:
            universe.players[PLAYERS[index]].planet_landed = planet.id
    spare = next(sid for sid in deep if sid not in homes)
    universe.sectors[spare].fighters = FighterDeployment(owner_id="A", count=5)
    return universe


def _fail(seed: int, log: list[str], rule: str) -> int:
    print(f"seed {seed}")
    print(f"invariant: {rule}")
    print("actions:")
    for line in log:
        print(line)
    return 1


def run_seed(seed: int) -> tuple[int, str]:
    rng = random.Random(seed)
    universe = _build(seed)
    log: list[str] = []
    ok_n = 0
    fail_n = 0
    days = 0
    broken = _check(universe)
    if broken:
        return _fail(seed, log, f"setup: {broken}"), ""
    action_n = 0
    for _step in range(ACTIONS_PER_PLAYER):
        for pid in PLAYERS:
            if not universe.players[pid].alive:
                log.append(f"{pid} skip dead")
                action_n += 1
            else:
                choices = [
                    item for item in legal_actions(universe, pid)
                    if item.legal and item.kind in PLANET_KINDS
                ]
                if not choices:
                    log.append(f"{pid} skip none legal")
                    action_n += 1
                else:
                    spec = rng.choice(choices)
                    args = _sample(rng, universe, spec)
                    if args is None:
                        log.append(f"{pid} skip {spec.kind} no args")
                        action_n += 1
                    else:
                        before_credits = _credits(universe)
                        before_turns = universe.players[pid].turns_today
                        before_world = _world(universe)
                        before_seq = universe.seq
                        result = apply_action(
                            universe, pid, Action(kind=ActionKind(spec.kind), args=args),
                        )
                        new_events = [ev for ev in universe.events if ev.seq > before_seq]
                        line = (
                            f"{pid} {spec.kind} {args} -> "
                            f"{'ok' if result.ok else 'no'} {result.error or ''} "
                            f"turns {result.turns_spent}"
                        )
                        log.append(line)
                        action_n += 1
                        if result.ok:
                            ok_n += 1
                        else:
                            fail_n += 1
                        rule = _check(universe)
                        if rule:
                            return _fail(seed, log, rule), ""
                        spent = universe.players[pid].turns_today - before_turns
                        if result.ok:
                            if spent != result.turns_spent:
                                return _fail(seed, log, f"ok action spent {spent} not {result.turns_spent}"), ""
                        elif result.error in CHARGED_FAIL:
                            if spent != result.turns_spent:
                                return _fail(
                                    seed, log, f"charged fail spent {spent} not {result.turns_spent}",
                                ), ""
                        else:
                            if spent != 0:
                                return _fail(seed, log, f"failed action spent {spent} turns"), ""
                            if _world(universe) != before_world:
                                return _fail(seed, log, "failed action changed the world"), ""
                        actual = sum(_credits(universe).values())
                        explained = _explained_total(before_credits, new_events, universe)
                        if actual != explained:
                            return _fail(
                                seed, log,
                                f"credits {sum(before_credits.values())} -> {actual}, events explain {explained}",
                            ), ""
            if action_n % DAY_EVERY == 0:
                before_credits = _credits(universe)
                before_seq = universe.seq
                tick_day(universe)
                days += 1
                new_events = [ev for ev in universe.events if ev.seq > before_seq]
                log.append(f"day {universe.day}")
                rule = _check(universe)
                if rule:
                    return _fail(seed, log, f"day tick: {rule}"), ""
                actual = sum(_credits(universe).values())
                explained = _explained_total(before_credits, new_events, universe)
                if actual != explained:
                    return _fail(
                        seed, log,
                        f"day tick credits {sum(before_credits.values())} -> {actual}, "
                        f"events explain {explained}",
                    ), ""
    row = f"| {seed} | {action_n} | {ok_n} | {fail_n} | {days} | pass |"
    return 0, row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Planet invariant fuzz")
    parser.add_argument("--seeds", type=int, default=len(FIXED_SEEDS))
    args = parser.parse_args(argv)
    if args.seeds < 1 or args.seeds > len(FIXED_SEEDS):
        print(f"seeds must be 1..{len(FIXED_SEEDS)}")
        return 2
    print("| Seed | Actions | Ok | Fail | Days | Result |")
    print("|---|---:|---:|---:|---:|---|")
    failed = 0
    for seed in FIXED_SEEDS[: args.seeds]:
        code, row = run_seed(seed)
        if code != 0:
            if seed in XFAIL:
                print(f"| {seed} |  |  |  |  | xfail |")
                continue
            failed += 1
            break
        print(row)
    print(f"planet_invariants_fuzz: {'PASS' if failed == 0 else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
