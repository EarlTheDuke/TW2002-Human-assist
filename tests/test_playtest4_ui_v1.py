"""Playtest 4 (game 668cbeaf at 5b73cb5): engine side of the cockpit fixes.

* CIM R lists each known port's goods (buying/selling, amount, percent) from the
  trader's own last look, so the computer screen has data to show.
* The yard's net-worth line is the engine's figure after the swap
  (ship_class.net_worth_delta_by), and a trade-in that pays you says so.
* The citadel Terra-trips sentence uses the viewer's holds, not a fixed 30.
"""
from __future__ import annotations

import tw2k.engine.constants as K
from tests.test_colonist_units_v1 import _land, _world as _col_world
from tests.test_note162_buildable_v1 import _world as _cim_world
from tests.test_note73_beta_addendum_v1 import _seat, _world as _yard_world
from tw2k.engine import Action, ActionKind, apply_action
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, EventKind, PlanetClass
from tw2k.engine.observation import build_observation


def test_cim_r_lists_known_port_goods(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    universe = _cim_world()
    player = universe.players["P1"]
    player.known_ports[2] = {
        "class": "2", "last_seen_day": 1,
        "stock": {
            "fuel_ore": {"current": 1200, "max": 2000, "price": 30, "side": "buys_from_player"},
            "organics": {"current": 500, "max": 1000, "price": 40, "side": "sells_to_player"},
        },
    }
    assert apply_action(universe, "P1", Action(kind=ActionKind.CIM, args={"query": "R"})).ok
    row = universe.events[-1].payload["ports"][0]
    assert row["sector_id"] == 2 and row["class"] == "2" and row["last_seen_day"] == 1
    assert row["goods"] == {
        "fuel_ore": {"side": "buying", "qty": 1200, "pct": 60},
        "organics": {"side": "selling", "qty": 500, "pct": 50},
    }
    assert "price" not in row["goods"]["fuel_ore"]


def test_yard_net_worth_preview_matches_the_buy(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    world = _yard_world(75)
    player = _seat(world, "P1", name="Yard", credits=500_000)
    player.ship.fighters = 30
    player.ship.shields = 10
    player.ship.cargo[Commodity.FUEL_ORE] = 5
    for target in ("scout_marauder", "colonial_transport"):
        shown = next(la for la in legal_actions(world, "P1") if la.kind == ActionKind.BUY_SHIP)
        delta = shown.params["ship_class"]["net_worth_delta_by"][target]
        before = player.net_worth
        res = apply_action(world, "P1", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": target}))
        assert res.ok, res.error
        assert player.net_worth - before == delta, target


def test_trade_in_that_pays_you_says_so(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    world = _yard_world(76)
    player = _seat(world, "P1", name="Down", credits=1_000)
    player.ship.holds = 40
    target = "scout_marauder"
    net = K.net_hull_cost(player.ship.ship_class.value, target, ship=player.ship)
    assert net < 0, net
    res = apply_action(world, "P1", Action(kind=ActionKind.BUY_SHIP, args={"ship_class": target}))
    assert res.ok, res.error
    ev = [e for e in world.events if e.kind == EventKind.BUY_SHIP][-1]
    assert ev.summary.endswith(f"(trade-in paid {-net} cr back)"), ev.summary
    assert f"({net} cr)" not in ev.summary


def test_citadel_trips_use_the_ships_holds(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    u = _col_world()
    planet = _land(u, PlanetClass.M)
    planet.colonists[Commodity.FUEL_ORE] = 221_000
    u.players["P1"].ship.holds = 70
    quote = build_observation(u, "P1").citadel_next_build
    assert quote["haul_holds"] == 70
    assert quote["plain"].endswith("about 12 more Terra trips with 70 holds")
    listed = {la.kind: la for la in legal_actions(u, "P1")}
    assert listed["build_citadel"].params["next"]["plain"] == quote["plain"]
