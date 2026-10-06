"""Pins for the eight scale and empty-port bugs the earlier tests let through."""

from __future__ import annotations

import math

from tw2k.agents.seat_brain import SeatBrain, View
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, Player, Ship, ShipClass
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import _record_port_intel

# 200 + sin(day / 87 * 2 * pi) * 40, rounded. These days stay inside 160..239,
# so the 160 and 239 clamps do not change them. Day 22 is not in this set:
# the sine rounds to 240 and the clamp is what returns 239.
_FIGHTER_DAYS = {
    0: 200,
    10: 226,
    30: 233,
    44: 199,
    65: 160,
    87: 200,
    100: 232,
}


def _hand_hold(base: int, qty: int, held: int) -> int:
    return base * qty + 20 * (qty * held + qty * (qty - 1) // 2)


def _seat(universe, player_id: str, *, sector_id: int, credits: int, ship: Ship) -> Player:
    player = Player(id=player_id, name=player_id, ship=ship, credits=credits)
    player.sector_id = sector_id
    player.turns_per_day = 1000
    player.turns_today = 0
    universe.players[player_id] = player
    universe.sectors[sector_id].occupant_ids.append(player_id)
    sector = universe.sectors[sector_id]
    player.known_sectors.add(sector_id)
    player.known_warps[sector_id] = list(sector.warps)
    return player


def _selling_sector(universe):
    """A port that sells fuel and buys organics. Stock is still the opening 0."""
    for sector in universe.sectors.values():
        port = sector.port
        if port is None or int(port.class_id) not in (3, 5):
            continue
        if sector.id == K.STARDOCK_SECTOR:
            continue
        return sector
    raise AssertionError("no fuel-selling port")


def test_five_holds_on_top_of_twenty_keep_the_owned_term() -> None:
    """Buying 5 holds when 20 are already owned. Two days, hand formula."""
    for day, base in ((0, 151), (9, 249)):
        universe = generate_universe(
            GameConfig(seed=11, universe_size=25, enable_planets=False, enable_ferrengi=False)
        )
        universe.day = day
        ship = Ship(holds=20)
        player = _seat(universe, "P9", sector_id=1, credits=500_000, ship=ship)
        expect = _hand_hold(base, 5, 20)
        assert K.hold_day_base(day) == base
        assert K.hold_total_price("merchant_cruiser", 20, 5, day) == expect
        before = player.credits
        result = apply_action(
            universe, "P9", Action(kind=ActionKind.BUY_EQUIP, args={"item": "holds", "qty": 5})
        )
        assert result.ok, result.error
        assert player.ship.holds == 25
        assert before - player.credits == expect


def test_fighter_wave_matches_the_hand_sine_and_the_clamp_is_idle() -> None:
    for day, want in _FIGHTER_DAYS.items():
        raw = round(200 + math.sin(day / 87 * 2 * math.pi) * 40)
        assert raw == want
        assert 160 <= raw <= 239
        assert K.fighter_unit_price(day) == want
    raw_22 = round(200 + math.sin(22 / 87 * 2 * math.pi) * 40)
    assert raw_22 == 240
    assert K.fighter_unit_price(22) == 239


def test_buy_ship_charges_ship_cost_trade_in_and_shows_that_net() -> None:
    """Merchant Cruiser to Battle Ship, and Scout to CargoTran."""
    pairs = (
        ("merchant_cruiser", "battleship", ShipClass.MERCHANT_CRUISER),
        ("scout_marauder", "cargotran", ShipClass.SCOUT_MARAUDER),
    )
    for old, new, cls in pairs:
        universe = generate_universe(
            GameConfig(seed=11, universe_size=25, enable_planets=False, enable_ferrengi=False)
        )
        ship = Ship(ship_class=cls, holds=20, fighters=0)
        player = _seat(universe, "P9", sector_id=1, credits=500_000, ship=ship)
        trade_in = int(K.ship_cost(old) * 0.25)
        net = K.ship_cost(new) - trade_in
        rows = legal_actions(universe, "P9")
        ships = next(row for row in rows if row.kind == "buy_ship")
        params = ships.params["ship_class"]
        assert params["trade_in"] == trade_in
        assert params["net_cost_by"][new] == net
        before = player.credits
        result = apply_action(
            universe, "P9", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": new})
        )
        assert result.ok, result.error
        assert player.ship.ship_class.value == new
        assert before - player.credits == net
        assert before - player.credits == params["net_cost_by"][new]


def test_fresh_ship_net_worth_uses_ship_cost() -> None:
    universe = generate_universe(
        GameConfig(seed=11, universe_size=25, enable_planets=False, enable_ferrengi=False)
    )
    ship = Ship(ship_class=ShipClass.SCOUT_MARAUDER, holds=25, fighters=20, shields=0)
    player = _seat(universe, "P9", sector_id=1, credits=10_000, ship=ship)
    hull = int(K.ship_cost("scout_marauder") * 0.5)
    fighters = 20 * K.nw_fighter_value()  # NET_WORTH_MODE tw2002: half the wave midpoint
    assert K.nw_fighter_value() == 100
    shields = 0
    assert player.net_worth == player.credits + hull + fighters + shields


def _empty_obs(universe, player, sector, *, remember: bool):
    if remember:
        _record_port_intel(player, sector.id, sector.port, universe=universe)
    else:
        player.known_ports.pop(sector.id, None)
    obs = build_observation(universe, player.id).model_dump(mode="json")
    trade = next(row for row in obs["legal_actions"] if row["kind"] == "trade")
    qty = ((trade["params"].get("qty") or {}).get("max_by") or {}).get("fuel_ore") or {}
    assert int(qty.get("buy") or 0) == 0
    return obs


def test_empty_shelf_and_unseen_port_are_not_bought() -> None:
    universe = generate_universe(
        GameConfig(seed=17, universe_size=40, enable_planets=False, enable_ferrengi=False)
    )
    sector = _selling_sector(universe)
    ship = Ship(holds=20, fighters=0)
    ship.cargo[Commodity.ORGANICS] = 12
    player = _seat(universe, "P9", sector_id=sector.id, credits=20_000, ship=ship)
    brain = SeatBrain()
    buy = {"kind": "trade", "args": {"commodity": "fuel_ore", "qty": 0, "side": "buy"}}

    seen = _empty_obs(universe, player, sector, remember=True)
    stock = next(kp for kp in seen["known_ports"] if int(kp["sector_id"]) == sector.id)
    assert int(stock["stock"]["fuel_ore"]["current"]) == 0
    assert brain._empty_shelf_buy(View(seen), buy) is True
    action = brain.decide(seen)
    assert not (action["kind"] == "trade" and action.get("args", {}).get("side") == "buy")
    if action["kind"] == "trade":
        assert action["args"]["side"] == "sell"
    else:
        assert action["kind"] in ("warp", "plot_course")

    unseen = _empty_obs(universe, player, sector, remember=False)
    assert all(int(kp.get("sector_id") or -1) != sector.id for kp in unseen["known_ports"])
    assert brain._empty_shelf_buy(View(unseen), buy) is True
    action = brain.decide(unseen)
    assert not (action["kind"] == "trade" and action.get("args", {}).get("side") == "buy")


def test_stardock_does_not_buy_a_hull_the_list_prices_above_credits() -> None:
    """The upgrade guard, reached with a list net the computed net does not show."""
    universe = generate_universe(
        GameConfig(seed=11, universe_size=25, enable_planets=False, enable_ferrengi=False)
    )
    net = K.ship_cost("cargotran") - int(K.ship_cost("merchant_cruiser") * 0.25)
    ship = Ship(holds=20, fighters=0)
    player = _seat(universe, "P9", sector_id=1, credits=net - 1, ship=ship)
    obs = build_observation(universe, "P9").model_dump(mode="json")
    assert SeatBrain().decide(obs)["kind"] != "buy_ship"

    rich = _seat(universe, "P8", sector_id=1, credits=net + 2_000, ship=Ship(holds=20, fighters=0))
    listed = build_observation(universe, "P8").model_dump(mode="json")
    listed["owned_planets"] = [{
        "id": 1, "origin": "genesis", "citadel_level": 1, "colonists_total": 0, "sector_id": 1,
    }]
    for row in listed["legal_actions"]:
        if row["kind"] != "buy_ship":
            continue
        ship_params = row["params"]["ship_class"]
        ship_params["net_cost_by"]["cargotran"] = rich.credits + 5_000
        choices = list(ship_params.get("choices") or [])
        if "cargotran" not in choices:
            choices.append("cargotran")
        ship_params["choices"] = choices
        row["legal"] = True
    brain = SeatBrain()
    offered = brain._opt_upgrade(View(listed))
    assert offered is None or offered[1]["kind"] != "buy_ship"
    assert brain.decide(listed)["kind"] != "buy_ship"
