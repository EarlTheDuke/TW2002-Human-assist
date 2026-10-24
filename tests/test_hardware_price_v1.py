"""Live shop prices for armid, limpet, genesis, and the ether probe.

A TWGS v3.34b card priced an armid at 1,000 with up to 30 points of damage,
a limpet at 10,000, a genesis at 20,000, and an ether probe at 3,000.
This copy charges 100, 250, 25,000, and 5,000. The armid hit is 20 under
the hardware switch and 100 on the older path. Combat was not played, so
30 is the shop ceiling, not a measured hit.

HARDWARE_PRICE_MODE defaults to legacy, so today's digests stay put.

Plants:
  pb1 — live shop prices stay at the old numbers.
  pb2 — a live armid hit stays at the old damage.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.hardware import armid_detonation_hits
from tw2k.engine.models import GameConfig, Player, Ship
from tw2k.engine.runner import apply_action
from tw2k.engine.universe import generate_universe


def test_default_keeps_todays_prices_and_hit():
    _prior_hardware_mode = K.HARDWARE_MODE
    try:
        assert K.HARDWARE_PRICE_MODE == "legacy"
        assert K.armid_mine_cost() == 100
        assert K.limpet_mine_cost() == 250
        assert K.genesis_torpedo_cost() == 25_000
        assert K.ether_probe_cost() == 5_000
        assert K.ship_tw_type1_cost() == 12_500
        assert K.ship_tw_type2_cost() == 20_000
        assert K.ship_tw_upgrade_cost() == 9_000
        assert K.SHIP_TW_TYPE1_COST == 12_500
        assert K.SHIP_TW_TYPE2_COST == 20_000
        assert K.SHIP_TW_UPGRADE_COST == 9_000
        assert K.armid_hit_damage() == K.ARMID_DAMAGE_TW2002
        old = K.HARDWARE_MODE
        try:
            K.HARDWARE_MODE = "legacy"
            assert K.armid_hit_damage() == 100
        finally:
            K.HARDWARE_MODE = old
    finally:
        K.HARDWARE_MODE = _prior_hardware_mode


def test_live_shop_charges_the_card_and_the_hit_is_30():
    _prior_hardware_price_mode = K.HARDWARE_PRICE_MODE
    try:
        try:
            K.HARDWARE_PRICE_MODE = "live"
            assert K.armid_mine_cost() == 1_000
            assert K.limpet_mine_cost() == 10_000
            assert K.genesis_torpedo_cost() == 20_000
            assert K.ether_probe_cost() == 3_000
            assert K.ship_tw_type1_cost() == 50_000
            assert K.ship_tw_type2_cost() == 80_000
            assert K.ship_tw_upgrade_cost() == 10_000
            assert K.SHIP_TW_TYPE1_COST == 12_500
            assert K.SHIP_TW_TYPE2_COST == 20_000
            assert K.SHIP_TW_UPGRADE_COST == 9_000
            assert K.SHIP_TW_MODE == "tw2002"
            assert K.armid_hit_damage() == 30
            hits, damage = armid_detonation_hits(4, None)
            assert hits == 2
            assert damage == 30

            universe = generate_universe(
                GameConfig(seed=4, universe_size=20, max_days=3, enable_planets=False, enable_ferrengi=False)
            )
            player = Player(id="P1", name="Trader", ship=Ship(), credits=50_000, experience=0)
            player.sector_id = K.STARDOCK_SECTOR
            universe.players["P1"] = player
            universe.sectors[K.STARDOCK_SECTOR].occupant_ids.append("P1")
            bought = apply_action(
                universe,
                "P1",
                Action(kind=ActionKind.BUY_EQUIP, args={"item": "armid_mines", "qty": 1}),
            )
            assert bought.ok, bought.error
            assert player.credits == 50_000 - 1_000
        finally:
            K.HARDWARE_PRICE_MODE = "legacy"
    finally:
        K.HARDWARE_PRICE_MODE = _prior_hardware_price_mode
