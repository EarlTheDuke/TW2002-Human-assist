"""Docking costs one turn. Later trades in the visit cost none. Ports refill from productivity."""

from __future__ import annotations

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe, tick_day
from tw2k.engine import constants as K
from tw2k.engine.economy import regenerate_ports
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, Player, Port, PortClass, PortStock, Ship

FUEL = Commodity.FUEL_ORE


def _seat():
    universe = generate_universe(
        GameConfig(seed=8, universe_size=20, max_days=5, enable_planets=False, enable_ferrengi=False)
    )
    player = Player(id="P1", name="Trader", ship=Ship(), credits=500_000, experience=0)
    player.sector_id = 11
    player.ship.cargo[FUEL] = 30
    universe.players["P1"] = player
    universe.sectors[11].occupant_ids.append("P1")
    port = Port(
        class_id=PortClass.CLASS_1_BSS,
        stock={FUEL: PortStock(current=0, maximum=3000)},
        mcic={FUEL: -60},
        productivity={FUEL: 100},
    )
    universe.sectors[11].port = port
    return universe, player, port


def _sell(universe, qty: int = 1):
    return apply_action(
        universe,
        "P1",
        Action(kind=ActionKind.TRADE, args={"side": "sell", "commodity": "fuel_ore", "qty": qty}),
    )


def _trade_cost(universe) -> int:
    for entry in legal_actions(universe, "P1"):
        if entry.kind == ActionKind.TRADE.value:
            return int(entry.turn_cost)
    raise AssertionError("no trade action")


def test_first_trade_of_a_visit_costs_one_and_later_ones_cost_none() -> None:
    universe, player, _port = _seat()
    assert _trade_cost(universe) == K.PORT_DOCK_TURN_COST
    first = _sell(universe)
    assert first.ok, first.error
    assert player.turns_today == 1
    assert _trade_cost(universe) == 0
    second = _sell(universe)
    assert second.ok, second.error
    assert player.turns_today == 1


def test_leaving_and_coming_back_costs_one_again() -> None:
    universe, player, _port = _seat()
    assert _sell(universe).ok
    dest = universe.sectors[11].warps[0]
    left = apply_action(universe, "P1", Action(kind=ActionKind.WARP, args={"target": dest}))
    assert left.ok, left.error
    assert player.port_visit_sector_id is None
    path = _way_back(universe, player.sector_id, 11)
    assert path
    for nxt in path:
        hop = apply_action(universe, "P1", Action(kind=ActionKind.WARP, args={"target": nxt}))
        assert hop.ok, hop.error
    assert player.sector_id == 11
    turns = player.turns_today
    again = _sell(universe)
    assert again.ok, again.error
    assert player.turns_today == turns + 1


def _way_back(universe, start: int, goal: int) -> list[int]:
    seen = {start}
    queue: list[tuple[int, list[int]]] = [(start, [])]
    while queue:
        here, path = queue.pop(0)
        for nxt in universe.sectors[here].warps:
            if nxt in seen:
                continue
            step = path + [nxt]
            if nxt == goal:
                return step
            seen.add(nxt)
            queue.append((nxt, step))
    return []


def test_a_failed_trade_spends_no_turn_and_does_not_open_the_visit() -> None:
    universe, player, port = _seat()
    failed = _sell(universe, qty=5000)
    assert failed.ok is False
    assert player.turns_today == 0
    assert player.port_visit_sector_id is None
    assert port.stock[FUEL].current == 0
    opened = _sell(universe)
    assert opened.ok, opened.error
    assert player.turns_today == 1


def test_regen_follows_productivity_and_stays_inside_the_max() -> None:
    universe, _player, port = _seat()
    regenerate_ports(universe)
    assert port.stock[FUEL].current == round(100 * K.PORT_REGEN_PER_DAY)
    port.stock[FUEL].current = port.stock[FUEL].maximum - 1
    regenerate_ports(universe)
    assert port.stock[FUEL].current == port.stock[FUEL].maximum
    port.productivity[FUEL] = 0
    port.stock[FUEL].current = 0
    regenerate_ports(universe)
    assert port.stock[FUEL].current == 0


def test_same_seed_regens_the_same_way() -> None:
    def after(seed: int) -> list[tuple]:
        universe = generate_universe(
            GameConfig(seed=seed, universe_size=25, enable_planets=False, enable_ferrengi=False)
        )
        tick_day(universe)
        rows = []
        for sector_id in sorted(universe.sectors):
            port = universe.sectors[sector_id].port
            if port is None:
                continue
            for commodity, stock in port.stock.items():
                rows.append((sector_id, commodity.value, stock.current, stock.maximum))
        return rows

    assert after(31) == after(31)
    assert after(31) != after(32)


def test_new_ports_open_empty_and_an_old_save_loads() -> None:
    universe = generate_universe(
        GameConfig(seed=6, universe_size=20, enable_planets=False, enable_ferrengi=False)
    )
    for sector in universe.sectors.values():
        if sector.port is None:
            continue
        for stock in sector.port.stock.values():
            assert stock.current == 0
    old = Player.model_validate({"id": "P9", "name": "Old"})
    assert old.port_visit_sector_id is None
    bare = Port.model_validate(
        {"class_id": 1, "stock": {"fuel_ore": {"current": 10, "maximum": 80}}}
    )
    universe.sectors[11].port = bare
    regenerate_ports(universe)
    assert bare.stock[FUEL].current == 10
