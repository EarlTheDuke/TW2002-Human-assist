"""A counter at the hidden limit trades. One credit past it does not."""

from __future__ import annotations

import json
from pathlib import Path

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, build_observation, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.economy import haggle_bound, haggle_room_pct, port_buy_price, port_sell_price
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, Player, Port, PortClass, PortStock, Ship

FUEL = Commodity.FUEL_ORE
EQ = Commodity.EQUIPMENT
ROOT = Path(__file__).resolve().parents[1]


def _seat() -> tuple:
    universe = generate_universe(
        GameConfig(seed=4, universe_size=20, max_days=5, enable_planets=False, enable_ferrengi=False)
    )
    player = Player(id="P1", name="Trader", ship=Ship(), credits=500_000, experience=0)
    player.sector_id = 11
    player.ship.cargo[FUEL] = 20
    universe.players["P1"] = player
    universe.sectors[11].occupant_ids.append("P1")
    return universe, player


def _port(universe, class_id: PortClass, commodity: Commodity, mcic: int, current: int) -> Port:
    port = Port(
        class_id=class_id,
        stock={commodity: PortStock(current=current, maximum=3000)},
        mcic={commodity: mcic},
    )
    universe.sectors[11].port = port
    return port


def _trade(universe, side: str, commodity: str, qty: int = 1, unit_price: int | None = None):
    args: dict = {"side": side, "commodity": commodity, "qty": qty}
    if unit_price is not None:
        args["unit_price"] = unit_price
    return apply_action(universe, "P1", Action(kind=ActionKind.TRADE, args=args))


def test_room_runs_from_110_to_149_and_stops() -> None:
    assert haggle_room_pct(0) == K.PORT_HAGGLE_MIN_PCT
    assert haggle_room_pct(-100) == K.PORT_HAGGLE_MAX_PCT
    assert haggle_room_pct(100) == K.PORT_HAGGLE_MAX_PCT
    assert haggle_room_pct(-800) == K.PORT_HAGGLE_MAX_PCT
    assert haggle_room_pct(800) == K.PORT_HAGGLE_MAX_PCT


def test_counter_at_the_limit_is_accepted_and_one_past_it_spends_a_turn() -> None:
    universe, player = _seat()
    port = _port(universe, PortClass.CLASS_1_BSS, FUEL, -100, 0)
    listed = port_buy_price(port, FUEL, 0)
    bound = haggle_bound(listed, -100, "sell")
    assert bound > listed
    credits = player.credits
    stock = port.stock[FUEL].current
    held = player.ship.cargo[FUEL]
    won = _trade(universe, "sell", "fuel_ore", unit_price=bound)
    assert won.ok, won.error
    assert player.credits == credits + bound
    assert port.stock[FUEL].current == stock + 1
    assert player.ship.cargo[FUEL] == held - 1

    universe, player = _seat()
    port = _port(universe, PortClass.CLASS_1_BSS, FUEL, -100, 0)
    listed = port_buy_price(port, FUEL, 0)
    bound = haggle_bound(listed, -100, "sell")
    credits = player.credits
    stock = port.stock[FUEL].current
    held = player.ship.cargo[FUEL]
    lost = _trade(universe, "sell", "fuel_ore", unit_price=bound + 1)
    assert lost.ok is False
    assert lost.error == "the port lost patience"
    assert player.credits == credits
    assert port.stock[FUEL].current == stock
    assert player.ship.cargo[FUEL] == held
    assert player.turns_today == K.PORT_HAGGLE_FAIL_TURNS
    assert player.experience == 0


def test_buy_counter_at_the_floor_is_accepted() -> None:
    universe, player = _seat()
    player.ship.cargo[FUEL] = 0
    port = _port(universe, PortClass.CLASS_5_SBS, EQ, 100, 3000)
    listed = port_sell_price(port, EQ, 0)
    floor = haggle_bound(listed, 100, "buy")
    assert floor < listed
    credits = player.credits
    won = _trade(universe, "buy", "equipment", unit_price=floor)
    assert won.ok, won.error
    assert player.credits == credits - floor
    lost = _trade(universe, "buy", "equipment", unit_price=floor - 1)
    assert lost.ok is False
    assert lost.error == "the port lost patience"


def test_no_haggle_trade_still_takes_the_first_offer() -> None:
    universe, player = _seat()
    port = _port(universe, PortClass.CLASS_1_BSS, FUEL, -60, 500)
    listed = port_buy_price(port, FUEL, 0)
    credits = player.credits
    result = _trade(universe, "sell", "fuel_ore")
    assert result.ok, result.error
    assert player.credits == credits + listed
    # first_dock +1 under RANK_MODE tw2002 (EXPERIENCE_ALIGNMENT.md x2); 0 under legacy.
    assert player.experience == K.xp_award("trade") + K.xp_award("first_dock")


def test_same_seed_gives_the_same_limits() -> None:
    def limits(seed: int) -> list[tuple]:
        universe = generate_universe(
            GameConfig(seed=seed, universe_size=30, enable_planets=False, enable_ferrengi=False)
        )
        rows = []
        for sector_id in sorted(universe.sectors):
            port = universe.sectors[sector_id].port
            if port is None:
                continue
            for commodity, _stock in port.stock.items():
                mcic = int(port.mcic.get(commodity, 0))
                if port.buys(commodity):
                    listed = port_buy_price(port, commodity, 0)
                    rows.append((sector_id, commodity.value, haggle_bound(listed, mcic, "sell")))
                elif port.sells(commodity):
                    listed = port_sell_price(port, commodity, 0)
                    rows.append((sector_id, commodity.value, haggle_bound(listed, mcic, "buy")))
        return rows

    assert limits(21) == limits(21)
    assert limits(21) != limits(22)


def test_experience_from_a_good_deal_is_capped() -> None:
    universe, player = _seat()
    port = _port(universe, PortClass.CLASS_1_BSS, FUEL, -100, 0)
    listed = port_buy_price(port, FUEL, 0)
    bound = haggle_bound(listed, -100, "sell")
    assert bound - listed > K.PORT_HAGGLE_XP_CAP
    result = _trade(universe, "sell", "fuel_ore", unit_price=bound)
    assert result.ok, result.error
    assert player.experience == K.xp_award("trade") + K.xp_award("first_dock") + K.PORT_HAGGLE_XP_CAP


def test_hidden_limit_stays_out_of_payloads() -> None:
    universe, _player = _seat()
    port = _port(universe, PortClass.CLASS_1_BSS, FUEL, -100, 0)
    listed = port_buy_price(port, FUEL, 0)
    bound = haggle_bound(listed, -100, "sell")
    lost = _trade(universe, "sell", "fuel_ore", unit_price=bound + 1)
    assert lost.error == "the port lost patience"
    brief = json.dumps(build_observation(universe, "P1").model_dump())
    actions = json.dumps([row.model_dump() for row in legal_actions(universe, "P1")])
    events = json.dumps([event.model_dump() for event in universe.events])
    blob = (brief + actions + events).lower()
    for word in ("mcic", "productivity", "haggle_limit", "haggle_bound", "counter_pct"):
        assert word not in blob
    server = (ROOT / "src" / "tw2k" / "server" / "runner.py").read_text(encoding="utf-8")
    assert "haggle_bound" not in server
    assert "haggle_limit" not in server
