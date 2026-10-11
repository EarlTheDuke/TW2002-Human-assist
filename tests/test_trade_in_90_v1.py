"""The yard can pay 90 percent of a hull and hand back the surplus.

Live TWGS itemized a trade-in at about 90 percent of each part. A Merchant
Cruiser with extra holds was quoted more than its sticker. This copy pays
25 percent of the sticker and keeps any surplus. Part prices (holds, drive,
computer, fighters, shields, scanner) were not published as a formula, so
this switch does not invent them.

TRADE_IN_MODE defaults to legacy, so today's digests stay put.

Plants:
  pb1 — live credit is still 25 percent.
  pb2 — live surplus is still kept by the yard.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import GameConfig, Player, ShipClass
from tw2k.engine.runner import apply_action
from tw2k.engine.universe import generate_universe


def _expensive_for_scout() -> str:
    scout = K.ship_cost("scout_marauder")
    best = None
    best_credit = 0
    for key in K.ship_specs():
        if key == "scout_marauder":
            continue
        credit = int(K.ship_cost(key) * K.TRADE_IN_FRACTION_LIVE)
        if credit > scout and credit > best_credit:
            best = key
            best_credit = credit
    assert best is not None, "expected a hull whose 90 percent exceeds a Scout"
    return best


def test_default_stays_a_quarter_and_keeps_the_surplus():
    assert K.TRADE_IN_MODE == "legacy"
    assert K.trade_in_live() is False
    assert K.trade_in_fraction() == 0.25
    assert K.trade_in_credit("merchant_cruiser") == int(K.ship_cost("merchant_cruiser") * 0.25)
    assert K.net_hull_cost(K.ESCAPE_POD, "scout_marauder") == 0
    old = _expensive_for_scout()
    assert K.net_hull_cost(old, "scout_marauder") == 0


def test_live_pays_ninety_percent_and_the_surplus(monkeypatch):
    monkeypatch.setattr(K, "TRADE_IN_MODE", "live")
    assert K.trade_in_fraction() == 0.90
    assert K.trade_in_credit("merchant_cruiser") == int(K.ship_cost("merchant_cruiser") * 0.90)
    old = _expensive_for_scout()
    surplus = K.ship_cost("scout_marauder") - int(K.ship_cost(old) * 0.90)
    assert surplus < 0
    assert K.net_hull_cost(old, "scout_marauder") == surplus
    pod_net = K.ship_cost("scout_marauder") - int(K.ship_cost("scout_marauder") * 0.90)
    assert K.net_hull_cost(K.ESCAPE_POD, "scout_marauder") == pod_net


def test_live_buy_hands_the_surplus_to_the_player(monkeypatch):
    monkeypatch.setattr(K, "TRADE_IN_MODE", "live")
    old = _expensive_for_scout()
    world = generate_universe(
        GameConfig(seed=21, universe_size=40, enable_ferrengi=False, enable_planets=False)
    )
    player = Player(
        id="P1", name="Seat", sector_id=K.STARDOCK_SECTOR, credits=0, turns_per_day=250,
    )
    player.ship.ship_class = ShipClass(old)
    world.players["P1"] = player
    world.sectors[K.STARDOCK_SECTOR].occupant_ids.append("P1")
    bought = apply_action(
        world, "P1",
        Action(kind=ActionKind.BUY_SHIP, args={"ship_class": "scout_marauder"}),
    )
    assert bought.ok is True
    assert player.ship.ship_class == ShipClass.SCOUT_MARAUDER
    assert player.credits > 0
    assert player.credits == -K.net_hull_cost(old, "scout_marauder")
