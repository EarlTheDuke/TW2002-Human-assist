"""Starport upgrade and construction. docs/playtests/ports/PORT_UPGRADE_BUILD.md.

`port_upgrade` raises one commodity's productivity and capacity. `port_build` orders a new
port that finishes over several days, drawing materials from the trader's planet. Both are
absent when PORT_UPGRADE_MODE is legacy. Neither draws from universe.rng.
"""

from __future__ import annotations

import math
import random
from typing import Any

from . import constants as K
from .actions import Action, ActionResult
from .economy import begin_port_visit, trade_turn_cost
from .models import (
    TRADE_COMMODITIES,
    Commodity,
    EventKind,
    Planet,
    Player,
    Port,
    PortClass,
    PortStock,
    ShipClass,
    Universe,
)

NO_PLANET = "no such planet in this sector you can build from"
CAP_FULL = "the universe cannot support another port"
_COMMODITY_ORDER = (Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT)

# Letter code -> repo PortClass. Never the other way: repo 1 is BSS, TW class 1 is BBS.
CODE_TO_CLASS: dict[str, PortClass] = {
    "BSS": PortClass.CLASS_1_BSS,
    "BSB": PortClass.CLASS_2_BSB,
    "SBB": PortClass.CLASS_3_SBB,
    "SSB": PortClass.CLASS_4_SSB,
    "SBS": PortClass.CLASS_5_SBS,
    "BBS": PortClass.CLASS_6_BBS,
    "BBB": PortClass.CLASS_7_BBB,
    "SSS": PortClass.CLASS_9_SSS,
}
BUILD_CODES = ("BBS", "BSB", "SBB", "SSB", "SBS", "BSS", "SSS", "BBB")


def on() -> bool:
    return K.port_upgrade_on()


def under_construction(port: Port | None) -> bool:
    return bool(port is not None and getattr(port, "construction", None))


def docks_closed(port: Port | None) -> bool:
    """pu23: a port under construction does not trade, rob, steal, planet-trade, or upgrade."""
    if not on() or not under_construction(port):
        return False
    return K.PORT_BUILD_DOCKS_OPEN is False


def _body(player: Player) -> str | None:
    if not player.alive:
        return "player is destroyed"
    if player.planet_landed is not None:
        return "lift off first"
    if player.ship.ship_class == ShipClass.ESCAPE_POD:
        return "an escape pod cannot trade at a port"
    return None


def _out_of_turns(player: Player, cost: int) -> str | None:
    if player.turns_today + cost > player.turns_per_day:
        return "out of turns for this day"
    return None


def _upgrade_turn_cost(player: Player) -> int:
    if K.PORT_UPGRADE_TURN_COST == "visit":
        return trade_turn_cost(player)
    return int(K.PORT_UPGRADE_TURN_COST)


def _special(port: Port) -> bool:
    if port.class_id in (PortClass.STARDOCK, PortClass.FEDERAL):
        return True
    return bool(getattr(port, "special", None)) and not K.PORT_UPGRADE_SPECIAL


def _trades(port: Port, commodity: Commodity) -> bool:
    trades = K.PORT_CLASS_TRADES.get(int(port.class_id))
    if not trades:
        return False
    idx = {Commodity.FUEL_ORE: 0, Commodity.ORGANICS: 1, Commodity.EQUIPMENT: 2}[commodity]
    return trades[idx] is not None


def upgrade_block(universe: Universe, player: Player) -> str | None:
    """None when this trader may open the upgrade menu here."""
    why = _body(player)
    if why:
        return why
    port = universe.sectors[player.sector_id].port
    if port is None:
        return "no trading port in this sector"
    if _special(port) or (not K.PORT_UPGRADE_SPECIAL and port.class_id in (PortClass.STARDOCK, PortClass.FEDERAL)):
        return "this port cannot be upgraded"
    if docks_closed(port) or under_construction(port):
        return "this port is under construction"
    if K.PORT_UPGRADE_BUST_BLOCKS and K.rob_tw2002() and getattr(port, "bust_player_id", None) == player.id:
        return "you are busted at this port until it clears"
    return None


def _stock(port: Port, commodity: Commodity) -> PortStock:
    row = port.stock.get(commodity)
    if row is None:
        row = PortStock(current=0, maximum=0)
        port.stock[commodity] = row
    return row


def _max_units(port: Port, commodity: Commodity, credits: int) -> int:
    row = port.stock.get(commodity)
    maximum = int(row.maximum) if row is not None else 0
    prod = int(port.productivity.get(commodity, 0) or 0)
    holds = int(K.PORT_UPGRADE_HOLDS_PER_UNIT)
    hold_room = max(0, (int(K.PORT_UPGRADE_MAX_HOLDS) - maximum) // holds) if holds else 0
    prod_room = max(0, int(K.PORT_PRODUCTIVITY_MAX) - prod)
    cost = int(K.PORT_UPGRADE_UNIT_COST[commodity.value])
    afford = credits // cost if cost > 0 else 0
    return max(0, min(hold_room, prod_room, afford))


def _commodity_row(port: Port, commodity: Commodity, credits: int) -> dict[str, Any]:
    row = port.stock.get(commodity)
    maximum = int(row.maximum) if row is not None else 0
    if port.buys(commodity):
        side = "buys_from_player"
    elif port.sells(commodity):
        side = "sells_to_player"
    else:
        side = "not_traded"
    return {
        "unit_cost": int(K.PORT_UPGRADE_UNIT_COST[commodity.value]),
        "holds_per_unit": int(K.PORT_UPGRADE_HOLDS_PER_UNIT),
        "capacity": maximum,
        "capacity_max": int(K.PORT_UPGRADE_MAX_HOLDS),
        "max_units": _max_units(port, commodity, credits),
        "side": side,
        "exp_per_unit": K.PORT_UPGRADE_EXP_PER_UNIT[commodity.value],
        "align_per_unit": K.PORT_UPGRADE_ALIGN_PER_UNIT[commodity.value],
    }


def upgrade_legal_spec(universe: Universe, pid: str) -> tuple[bool, str | None, int, dict[str, Any]]:
    if not on() or pid not in universe.players:
        return False, "unsupported action", 0, {}
    player = universe.players[pid]
    cost = _upgrade_turn_cost(player)
    why = upgrade_block(universe, player)
    port = universe.sectors[player.sector_id].port
    commodities: dict[str, Any] = {}
    if why is None and port is not None:
        for commodity in _COMMODITY_ORDER:
            if _trades(port, commodity):
                commodities[commodity.value] = _commodity_row(port, commodity, player.credits)
        if not any(int(row["max_units"]) >= 1 for row in commodities.values()):
            roomy = any(_max_units(port, Commodity(c), 10**12) >= 1 for c in commodities)
            why = "not enough credits for one upgrade unit" if roomy else "this port cannot take another upgrade unit"
    if why is None:
        why = _out_of_turns(player, cost)
    params = {"commodities": commodities, "turn_cost": cost}
    return why is None, why, cost, params


def _grant(player: Player, commodity: str, units: int) -> tuple[int, int]:
    """Whole experience and alignment from this upgrade. Fractions carry when the mode says so."""
    exp_rate = float(K.PORT_UPGRADE_EXP_PER_UNIT[commodity])
    align_rate = float(K.PORT_UPGRADE_ALIGN_PER_UNIT[commodity])
    if K.PORT_UPGRADE_FRACTION != "carry":
        return math.floor(units * exp_rate), math.floor(units * align_rate)
    bag = player.port_upgrade_carry.setdefault(commodity, {"exp": 0.0, "align": 0.0})
    exp_mille = round(float(bag.get("exp", 0.0)) * 1000) + units * round(exp_rate * 1000)
    align_mille = round(float(bag.get("align", 0.0)) * 1000) + units * round(align_rate * 1000)
    exp_whole, exp_rem = divmod(exp_mille, 1000)
    align_whole, align_rem = divmod(align_mille, 1000)
    if exp_rem or align_rem:
        bag["exp"] = exp_rem / 1000
        bag["align"] = align_rem / 1000
    else:
        player.port_upgrade_carry.pop(commodity, None)
    return exp_whole, align_whole


def _drop_tow(universe: Universe, player: Player) -> None:
    if not K.tow_on() or getattr(player.ship, "tow_lock", None) is None:
        return
    from .tow import release
    release(universe, player.ship, player.id, "port")


def handle_port_upgrade(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    why = upgrade_block(universe, player)
    if why:
        return ActionResult(ok=False, error=why)
    cost = _upgrade_turn_cost(player)
    turns = _out_of_turns(player, cost)
    if turns:
        return ActionResult(ok=False, error=turns)
    port = universe.sectors[player.sector_id].port
    assert port is not None
    raw = str((action.args or {}).get("commodity") or "").lower()
    try:
        commodity = Commodity(raw)
    except ValueError:
        return ActionResult(ok=False, error=f"invalid commodity {(action.args or {}).get('commodity')!r}")
    if commodity not in TRADE_COMMODITIES or not _trades(port, commodity):
        return ActionResult(ok=False, error=f"this port does not trade {raw or 'that commodity'}")
    units = (action.args or {}).get("units")
    if isinstance(units, bool) or (isinstance(units, float) and not units.is_integer()):
        return ActionResult(ok=False, error="units must be a whole number")  # pu7: never silently clipped
    try:
        units = int(units)
    except (TypeError, ValueError):
        return ActionResult(ok=False, error="units must be a whole number")
    room = _max_units(port, commodity, player.credits)
    if units < 1 or units > room:
        return ActionResult(ok=False, error=f"at most {room} units")
    unit_cost = int(K.PORT_UPGRADE_UNIT_COST[commodity.value])
    paid = unit_cost * units
    player.credits -= paid
    if K.PORT_UPGRADE_CREDITS_TO_PORT:
        port.credits = int(getattr(port, "credits", 0) or 0) + paid
    row = _stock(port, commodity)
    row.maximum += int(K.PORT_UPGRADE_HOLDS_PER_UNIT) * units
    port.productivity[commodity] = int(port.productivity.get(commodity, 0) or 0) + units
    exp_add, align_add = _grant(player, commodity.value, units)
    player.experience = int(player.experience) + exp_add
    player.alignment = int(player.alignment) + align_add
    begin_port_visit(player)
    _drop_tow(universe, player)
    universe.emit(
        EventKind.PORT_UPGRADED,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={
            "commodity": commodity.value,
            "units": units,
            "cost": paid,
            "capacity": int(row.maximum),
            "exp": exp_add,
            "align": align_add,
        },
        summary=(f"{player.name} upgraded {commodity.value} by {units} "
                 f"({row.maximum} holds) for {paid}cr"),
    )
    return ActionResult(ok=True, turns_spent=cost)


def class_buys(code: str) -> set[str]:
    pc = CODE_TO_CLASS.get(code)
    if pc is None:
        return set()
    trades = K.PORT_CLASS_TRADES.get(int(pc), (None, None, None))
    return {c.value for c, deal in zip(_COMMODITY_ORDER, trades, strict=True) if deal is True}


def _build_codes() -> tuple[str, ...]:
    if K.PORT_BUILD_ALLOW_SSS:
        return BUILD_CODES
    return tuple(code for code in BUILD_CODES if code != "SSS")


def port_count(universe: Universe) -> int:
    """Ports toward the cap. pu26: a destroyed port frees its slot once cleared (radiation over)."""
    return sum(
        1 for sector in universe.sectors.values()
        if sector.port is not None or (on() and radiating(universe, int(sector.id)))
    )


def stamp_port_cap(universe: Universe) -> int | None:
    return ensure_port_cap(universe)


def ensure_port_cap(universe: Universe) -> int | None:
    if not on():
        return None
    if universe.port_cap is not None:
        return int(universe.port_cap)
    n = port_count(universe)
    pct = int(K.PORT_BUILD_INITIAL_BUILT_PCT)
    universe.port_cap = math.ceil(n * 100 / pct) if n and pct else n
    return int(universe.port_cap)


def radiating(universe: Universe, sector_id: int) -> bool:
    sector = universe.sectors[sector_id]
    day = getattr(sector, "port_destroyed_day", None)
    if day is None:
        return False
    return int(universe.day) < int(day) + int(K.PORT_BUILD_RADIATION_DAYS)


def _owns_planet(player: Player, planet: Planet) -> bool:
    if planet.owner_id is not None and planet.owner_id == player.id:
        return True
    if K.PORT_BUILD_PLANET_WHO == "owner_or_corp":
        return bool(planet.corp_ticker and player.corp_ticker and planet.corp_ticker == player.corp_ticker)
    return False


def _planets_here(universe: Universe, player: Player) -> list[Planet]:
    sector = universe.sectors[player.sector_id]
    found = [universe.planets[pid] for pid in sector.planet_ids if pid in universe.planets]
    owned = [pl for pl in found if int(pl.sector_id) == int(player.sector_id) and _owns_planet(player, pl)]
    return sorted(owned, key=lambda pl: int(pl.id))


def _stock_days(planet: Planet, code: str) -> int:
    daily = K.PORT_BUILD_DAILY_MATERIALS[code]
    days = []
    for commodity, need in zip(_COMMODITY_ORDER, daily, strict=True):
        have = int(planet.stockpile.get(commodity, 0) or 0)
        if int(need) <= 0:
            continue
        days.append(have // int(need))
    return min(days) if days else 0


def build_block(universe: Universe, player: Player) -> str | None:
    why = _body(player)
    if why:
        return why
    sector = universe.sectors[player.sector_id]
    if player.sector_id in K.FEDSPACE_SECTORS and not K.PORT_BUILD_FEDSPACE:
        return "FedSpace cannot hold a built port"
    if player.sector_id == K.STARDOCK_SECTOR:
        return "FedSpace cannot hold a built port"
    if sector.port is not None:
        return "this sector already has a port"
    if radiating(universe, player.sector_id):
        return "this sector is still radiating"
    cap = ensure_port_cap(universe)
    if cap is not None and port_count(universe) >= cap:
        return CAP_FULL
    if K.PORT_BUILD_NEEDS_PLANET and not _planets_here(universe, player):
        return NO_PLANET
    return None


def _class_row(code: str, credits: int) -> dict[str, Any]:
    daily = K.PORT_BUILD_DAILY_MATERIALS[code]
    cost = int(K.PORT_BUILD_COST[code])
    return {
        "cost": cost,
        "days": int(K.PORT_BUILD_DAYS[code]),
        "daily": {
            "fuel_ore": int(daily[0]),
            "organics": int(daily[1]),
            "equipment": int(daily[2]),
        },
        "reward": list(K.PORT_BUILD_REWARD[code]),
        "affordable": credits >= cost,
    }


def build_legal_spec(universe: Universe, pid: str) -> tuple[bool, str | None, int, dict[str, Any]]:
    if not on() or pid not in universe.players:
        return False, "unsupported action", 0, {}
    player = universe.players[pid]
    cost = 1
    why = build_block(universe, player)
    if why is None:
        why = _out_of_turns(player, cost)
    classes = {code: _class_row(code, player.credits) for code in _build_codes()}
    planets = [
        {
            "planet_id": int(pl.id),
            "name": pl.name,
            "owner": "self" if pl.owner_id == player.id else "corp",
            "stock_days": {code: _stock_days(pl, code) for code in _build_codes()},
        }
        for pl in _planets_here(universe, player)
    ]
    cap = ensure_port_cap(universe)
    free = None if cap is None else max(0, int(cap) - port_count(universe))
    params = {"classes": classes, "planets": planets, "ports_free": free, "turn_cost": cost}
    return why is None, why, cost, params


def _valid_name(name: str) -> bool:
    return 1 <= len(name) <= int(K.PORT_BUILD_NAME_MAX) and all(32 <= ord(ch) <= 126 for ch in name)


def _generated_name(universe: Universe, sector_id: int) -> str:
    from .universe import _port_name
    side = random.Random(f"tw2k-port-build:{universe.config.seed}:{sector_id}")
    return _port_name(side, sector_id)


def _pay_reward(player: Player, code: str) -> tuple[int, int]:
    exp, align = K.PORT_BUILD_REWARD[code]
    player.experience = int(player.experience) + int(exp)
    player.alignment = int(player.alignment) + int(align)
    return int(exp), int(align)


def handle_port_build(universe: Universe, pid: str, action: Action) -> ActionResult:
    if not on():
        return ActionResult(ok=False, error="unsupported action")
    player = universe.players[pid]
    why = build_block(universe, player)
    if why:
        return ActionResult(ok=False, error=why)
    if _out_of_turns(player, 1):
        return ActionResult(ok=False, error="out of turns for this day")
    args = action.args or {}
    code = str(args.get("port_class") or "").upper()
    if code not in _build_codes():
        return ActionResult(ok=False, error=f"unknown port class {args.get('port_class')!r}")
    planet_id = args.get("planet_id")
    try:
        planet_id = int(planet_id)
    except (TypeError, ValueError):
        planet_id = None
    planet = next((pl for pl in _planets_here(universe, player) if planet_id is not None and int(pl.id) == planet_id), None)
    if planet is None:
        return ActionResult(ok=False, error=NO_PLANET)
    price = int(K.PORT_BUILD_COST[code])
    if player.credits < price:
        return ActionResult(ok=False, error="not enough credits")
    raw_name = args.get("name")
    if raw_name is None or raw_name == "":
        name = _generated_name(universe, player.sector_id)
    else:
        name = str(raw_name)
        if not _valid_name(name):
            return ActionResult(ok=False, error="port name must be 30 printable characters or fewer")
    player.credits -= price
    days = int(K.PORT_BUILD_DAYS[code])
    port = Port(
        class_id=CODE_TO_CLASS[code],
        name=name,
        construction={
            "code": code,
            "days_left": days,
            "days_total": days,
            "planet_id": int(planet.id),
            "owner_id": player.id,
            "name": name,
            "reward_paid": K.PORT_BUILD_REWARD_WHEN == "order",
        },
    )
    universe.sectors[player.sector_id].port = port
    rewarded = (0, 0)
    if K.PORT_BUILD_REWARD_WHEN == "order":
        rewarded = _pay_reward(player, code)
    begin_port_visit(player)
    _drop_tow(universe, player)
    universe.emit(
        EventKind.PORT_BUILD_ORDERED,
        actor_id=pid,
        sector_id=player.sector_id,
        payload={
            "port_class": code,
            "planet_id": int(planet.id),
            "days": days,
            "cost": price,
            "name": name,
            "exp": rewarded[0],
            "align": rewarded[1],
        },
        summary=f"{player.name} ordered a class {code} port ({days} days) for {price}cr",
    )
    return ActionResult(ok=True, turns_spent=1)


def _open_port(universe: Universe, sector_id: int, port: Port, cons: dict) -> None:
    code = str(cons.get("code"))
    prod = int(K.PORT_BUILD_START_PRODUCTIVITY)
    holds = prod * int(K.PORT_UPGRADE_HOLDS_PER_UNIT)
    pct = int(K.PORT_BUILD_START_STOCK_PCT)
    pc = CODE_TO_CLASS[code]
    port.class_id = pc
    port.construction = None
    port.credits = 0
    port.stock = {}
    port.productivity = {}
    port.mcic = {}
    trades = K.PORT_CLASS_TRADES[int(pc)]
    for commodity, deal in zip(_COMMODITY_ORDER, trades, strict=True):
        if deal is None:
            continue
        current = int(holds * pct / 100)
        if deal is True:
            current = 0  # buying port: full room
        port.stock[commodity] = PortStock(current=current, maximum=holds)
        port.productivity[commodity] = prod
        port.mcic[commodity] = K.PORT_MCIC_DEFAULT_BUY if deal is True else K.PORT_MCIC_DEFAULT_SELL
    if not cons.get("reward_paid"):
        owner = universe.players.get(str(cons.get("owner_id")))
        if owner is not None:
            exp, align = _pay_reward(owner, code)
        else:
            exp, align = (0, 0)
    else:
        exp, align = (0, 0)
    universe.emit(  # public and anonymous: no actor, so rivals learn neither the builder nor where he is (QC 55)
        EventKind.PORT_BUILT,
        sector_id=sector_id,
        payload={"port_class": code, "name": port.name, "exp": exp, "align": align},
        summary=f"A class {code} port opened in sector {sector_id}",
    )


def advance_construction(universe: Universe) -> None:
    """One day of port construction, after planet production. No universe.rng draws."""
    if not on():
        return
    for sector_id in sorted(universe.sectors):
        sector = universe.sectors[sector_id]
        port = sector.port
        cons = getattr(port, "construction", None) if port is not None else None
        if not cons:
            continue
        assert port is not None
        code = str(cons.get("code"))
        planet = universe.planets.get(int(cons.get("planet_id") or 0))
        daily = K.PORT_BUILD_DAILY_MATERIALS[code]
        ready = (
            planet is not None
            and int(planet.sector_id) == int(sector_id)
            and int(planet.id) in sector.planet_ids
            and all(int(planet.stockpile.get(c, 0) or 0) >= int(need) for c, need in zip(_COMMODITY_ORDER, daily, strict=True))
        )
        owner = str(cons.get("owner_id") or "")
        if not ready or K.PORT_BUILD_STALL != "pause":
            if not ready:
                universe.emit(
                    EventKind.PORT_BUILD_STALLED,
                    actor_id=owner,
                    sector_id=sector_id,
                    payload={"days_left": int(cons.get("days_left") or 0)},
                    summary=f"Port construction in {sector_id} paused for lack of materials",
                )
                continue
        for commodity, need in zip(_COMMODITY_ORDER, daily, strict=True):
            planet.stockpile[commodity] = int(planet.stockpile.get(commodity, 0) or 0) - int(need)
        cons["days_left"] = int(cons.get("days_left") or 0) - 1
        universe.emit(
            EventKind.PORT_BUILD_PROGRESS,
            actor_id=owner,
            sector_id=sector_id,
            payload={"days_left": int(cons["days_left"]), "days_total": int(cons.get("days_total") or 0)},
            summary=f"Port construction in {sector_id}: {cons['days_left']} days left",
        )
        if int(cons["days_left"]) <= 0:
            _open_port(universe, sector_id, port, cons)


def observation_extra(port: Port) -> dict[str, Any]:
    """Keys added to a sector port block only while the mode is on."""
    if not on():
        return {}
    cons = getattr(port, "construction", None)
    if cons:
        return {
            "under_construction": {
                "class": cons.get("code"),
                "days_left": int(cons.get("days_left") or 0),
                "days_total": int(cons.get("days_total") or 0),
            },
        }
    upgradable = port.class_id not in (PortClass.STARDOCK, PortClass.FEDERAL) and not getattr(port, "special", None)
    return {"upgradable": bool(upgradable)}
