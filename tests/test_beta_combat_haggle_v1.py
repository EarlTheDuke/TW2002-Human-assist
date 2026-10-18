"""NOTE 71 beta-combat-haggle-v1. Engine items 1, 2, 3 and 8.

Cockpit items are in test_cockpit_beta_combat_haggle_v1.py. With the new
switches left at legacy, the old formulas and the old turn advance stay.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import tw2k.engine.constants as K
from tw2k.agents.heuristic import HeuristicAgent
from tw2k.engine import Action, ActionKind, GameConfig, generate_universe
from tw2k.engine.combat import _resolve_ship_attack_tw2002
from tw2k.engine.economy import port_buy_price
from tw2k.engine.models import Commodity, EventKind, Player, Ship, ShipClass
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action
from tw2k.server.broadcaster import Broadcaster
from tw2k.server.runner import AgentSpec, MatchRunner, MatchSpec


def _universe(seed: int = 71):
    return generate_universe(GameConfig(
        seed=seed, universe_size=80, max_days=3, turns_per_day=40,
        starting_credits=50_000, enable_ferrengi=False, enable_planets=False,
    ))


def _seat(u, pid="P1", name="Guest 1", sector=1, fighters=100, shields=0, credits=50_000, holds=20):
    player = Player(
        id=pid, name=name,
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=fighters, shields=shields, holds=holds),
        sector_id=sector, credits=credits, alignment=100, experience=0,
        turns_per_day=40,
    )
    u.players[pid] = player
    sector_row = u.sectors[sector]
    if pid not in sector_row.occupant_ids:
        sector_row.occupant_ids.append(pid)
    return player


def _buying_port(u, commodity: Commodity):
    for sector in u.sectors.values():
        port = sector.port
        if port is not None and port.buys(commodity) and sector.id not in K.FEDSPACE_SECTORS:
            return sector
    raise AssertionError(f"no port buys {commodity}")


def _selling_port(u, commodity: Commodity):
    for sector in u.sectors.values():
        port = sector.port
        if port is not None and port.sells(commodity) and sector.id not in K.FEDSPACE_SECTORS:
            return sector
    raise AssertionError(f"no port sells {commodity}")


def _move(u, player, sector_id: int) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = sector_id
    dest = u.sectors[sector_id]
    if player.id not in dest.occupant_ids:
        dest.occupant_ids.append(player.id)


def _alien_exchange(u, shields: int, fighters: int, sent: int = 30):
    alien = next(iter(u.aliens.values()))
    alien.ship.ship_class = ShipClass.CARGOTRAN
    alien.ship.fighters = fighters
    alien.ship.shields = shields
    alien.ship.corbomite = 0
    player = _seat(u, fighters=200)
    _move(u, player, alien.sector_id)
    before = len(u.events)
    _resolve_ship_attack_tw2002(u, player.id, alien, sent)
    ev = next(e for e in u.events[before:] if e.kind == EventKind.COMBAT)
    rnd = ev.payload["rounds"][0]
    return alien, ev, rnd


def test_legacy_alien_odds_can_absorb_more_than_the_volley_and_shields_still_drop():
    """The recorded exchange is the odds formula, not a missed shield update.

    CargoTran odds 0.8 turn a volley of 30 into floor(30/0.8) = 37. Shields
    of 47 absorb 37 and finish at 10. The summary uses those same numbers.
    """
    assert K.ALIEN_COMBAT_FIX_MODE == "legacy" and not K.alien_combat_fix_live()
    u = _universe(7101)
    _alien, ev, rnd = _alien_exchange(u, shields=47, fighters=275)
    assert rnd["attacker_volley"] == 30
    assert rnd["defender_volley"] == 0
    assert rnd["defender_shield_absorbed"] == 37
    assert rnd["defender_shield_absorbed"] > rnd["attacker_volley"]
    assert rnd["defender_fighters_lost"] == 0
    assert rnd["defender_s_after"] == 10
    assert rnd["attacker_fighters_lost"] == 30
    assert "lost 30" in ev.summary
    assert "lost 37 shields and 0 fighters" in ev.summary


def test_live_alien_trade_is_one_to_one_and_the_summary_matches(monkeypatch):
    monkeypatch.setattr(K, "ALIEN_COMBAT_FIX_MODE", "live")
    u = _universe(7102)
    alien, ev, rnd = _alien_exchange(u, shields=10, fighters=275)
    assert rnd["attacker_volley"] == 30
    assert rnd["defender_shield_absorbed"] == 10
    assert rnd["defender_shield_absorbed"] <= min(rnd["attacker_volley"], 10)
    assert rnd["defender_s_after"] == 0
    assert rnd["defender_fighters_lost"] == 20
    assert rnd["attacker_fighters_lost"] == 30
    assert int(alien.ship.shields) == 0
    assert int(alien.ship.fighters) == 255
    assert "sent 30 fighters, lost 30" in ev.summary
    assert "lost 10 shields and 20 fighters" in ev.summary

    u = _universe(7103)
    _alien, ev, rnd = _alien_exchange(u, shields=47, fighters=275)
    assert rnd["defender_shield_absorbed"] == 30
    assert rnd["defender_shield_absorbed"] <= min(rnd["attacker_volley"], 47)
    assert rnd["defender_s_after"] == 17
    assert rnd["defender_fighters_lost"] == 0
    assert "lost 30 shields and 0 fighters" in ev.summary


def test_live_alien_fix_does_not_change_a_player_exchange(monkeypatch):
    monkeypatch.setattr(K, "ALIEN_COMBAT_FIX_MODE", "live")
    u = _universe(7104)
    attacker = _seat(u, pid="P1", name="Guest 1", fighters=200)
    defender = _seat(u, pid="P2", name="Other", fighters=275, shields=47)
    defender.ship.ship_class = ShipClass.CARGOTRAN
    _move(u, defender, attacker.sector_id)
    _resolve_ship_attack_tw2002(u, attacker.id, defender, 30)
    ev = next(e for e in u.events if e.kind == EventKind.COMBAT)
    rnd = ev.payload["rounds"][0]
    assert ev.payload["exchange_kind"] == "ship_vs_ship"
    assert rnd["defender_shield_absorbed"] == 37
    assert rnd["defender_s_after"] == 10
    assert rnd["attacker_fighters_lost"] == 30


def test_a_counter_stays_open_and_an_offer_past_it_can_still_be_taken(monkeypatch):
    monkeypatch.setattr(K, "HAGGLE_LIVE_MODE", "live")
    monkeypatch.setattr(K, "HAGGLE_COUNTER_MODE", "live")
    u = _universe(7105)
    sector = _buying_port(u, Commodity.FUEL_ORE)
    player = _seat(u, credits=5_000, holds=40)
    _move(u, player, sector.id)
    player.ship.cargo[Commodity.FUEL_ORE] = 30
    listed = port_buy_price(sector.port, Commodity.FUEL_ORE, 0)
    ask = max(listed + 1, int(listed * 1.08))
    assert listed * 1.03 < ask <= listed * 1.12
    spent = player.turns_today
    res = apply_action(u, player.id, Action(
        kind=ActionKind.TRADE, args={"side": "sell", "commodity": "fuel_ore", "qty": 10, "unit_price": ask},
    ))
    assert not res.ok and str(res.error).startswith("counter ")
    assert player.turns_today == spent
    assert player.haggle_counter and int(player.haggle_counter["counter"]) > 0
    failed = next(e for e in reversed(u.events) if e.kind == EventKind.TRADE_FAILED)
    price = int(player.haggle_counter["counter"])
    assert failed.summary == f"{player.name} port countered at {price}"
    assert "trade failed" not in failed.summary

    # Past the counter, still inside the measured 12% band: the port takes it.
    higher = min(int(listed * 1.12), max(price + 1, int(listed * 1.10)))
    assert higher > price
    taken = apply_action(u, player.id, Action(
        kind=ActionKind.TRADE, args={"side": "sell", "commodity": "fuel_ore", "qty": 10, "unit_price": higher},
    ))
    assert taken.ok, taken.error
    assert player.haggle_counter is None


def test_only_the_final_refusal_ends_the_trade(monkeypatch):
    monkeypatch.setattr(K, "HAGGLE_LIVE_MODE", "live")
    monkeypatch.setattr(K, "HAGGLE_COUNTER_MODE", "live")
    u = _universe(7106)
    sector = _buying_port(u, Commodity.FUEL_ORE)
    player = _seat(u, holds=40)
    _move(u, player, sector.id)
    player.ship.cargo[Commodity.FUEL_ORE] = 10
    listed = port_buy_price(sector.port, Commodity.FUEL_ORE, 0)
    spent = player.turns_today
    res = apply_action(u, player.id, Action(
        kind=ActionKind.TRADE,
        args={"side": "sell", "commodity": "fuel_ore", "qty": 10, "unit_price": listed * 3},
    ))
    assert not res.ok
    assert res.error in ("Get lost creep", "Swine, go peddle your wares")
    assert player.turns_today == spent + 1
    assert player.haggle_counter is None
    assert player.port_visit_sector_id is None


def test_holds_and_cargo_are_named_before_credits(monkeypatch):
    monkeypatch.setattr(K, "HAGGLE_COUNTER_MODE", "live")
    u = _universe(7107)
    sell_at = _selling_port(u, Commodity.EQUIPMENT)
    buyer = _seat(u, pid="P9", name="Buyer", credits=300, holds=20)
    _move(u, buyer, sell_at.id)
    res = apply_action(u, buyer.id, Action(
        kind=ActionKind.TRADE, args={"side": "buy", "commodity": "equipment", "qty": 2010},
    ))
    assert res.error == "You only have 20 empty holds."
    assert "Insufficient credits" not in (res.error or "")

    buy_at = _buying_port(u, Commodity.EQUIPMENT)
    seller = _seat(u, pid="P8", name="Seller", credits=1_000_000, holds=100)
    _move(u, seller, buy_at.id)
    seller.ship.cargo[Commodity.EQUIPMENT] = 83
    res = apply_action(u, seller.id, Action(
        kind=ActionKind.TRADE, args={"side": "sell", "commodity": "equipment", "qty": 8383},
    ))
    assert res.error == "You only have 83 Equipment in your holds."
    assert "100%" not in (res.error or "")


def test_legacy_haggle_still_names_credits_first():
    assert not K.haggle_counter_live()
    u = _universe(7108)
    sell_at = _selling_port(u, Commodity.EQUIPMENT)
    stock = sell_at.port.stock[Commodity.EQUIPMENT]
    stock.current = max(int(stock.current), 5000)
    stock.maximum = max(int(stock.maximum), 5000)
    buyer = _seat(u, credits=300, holds=20)
    _move(u, buyer, sell_at.id)
    res = apply_action(u, buyer.id, Action(
        kind=ActionKind.TRADE, args={"side": "buy", "commodity": "equipment", "qty": 2010},
    ))
    assert res.error is not None and res.error.startswith("Insufficient credits")


def test_a_counter_keeps_the_same_seat_in_the_scheduler(monkeypatch, tmp_path):
    monkeypatch.setattr(K, "HAGGLE_LIVE_MODE", "live")
    monkeypatch.setattr(K, "HAGGLE_COUNTER_MODE", "live")
    runner = MatchRunner(Broadcaster(), saves_root=tmp_path / "saves")
    spec = MatchSpec(
        config=GameConfig(
            seed=7109, universe_size=60, max_days=2, turns_per_day=30,
            starting_credits=20_000, enable_ferrengi=False, enable_planets=False,
            action_delay_s=0.0,
        ),
        agents=[
            AgentSpec(player_id="P1", name="Ben", kind="human"),
            AgentSpec(player_id="P2", name="Vega", kind="human"),
        ],
        action_delay_s=0.0,
    )

    async def go() -> None:
        await runner.start(spec)
        try:
            for _ in range(200):
                u = runner.state.universe
                if u is not None and any(e.kind == EventKind.HUMAN_TURN_START and e.actor_id == "P1" for e in u.events):
                    break
                await asyncio.sleep(0.02)
            u = runner.state.universe
            assert u is not None
            sector = _buying_port(u, Commodity.FUEL_ORE)
            player = u.players["P1"]
            _move(u, player, sector.id)
            player.ship.cargo[Commodity.FUEL_ORE] = 20
            listed = port_buy_price(sector.port, Commodity.FUEL_ORE, int(player.experience))
            ask = max(listed + 1, int(listed * 1.08))
            agent = next(a for a in runner.state.agents if a.player_id == "P1")
            agent.submit_action_nowait(Action(
                kind=ActionKind.TRADE,
                args={"side": "sell", "commodity": "fuel_ore", "qty": 10, "unit_price": ask},
            ))
            for _ in range(200):
                if any("port countered at" in (e.summary or "") for e in u.events):
                    break
                await asyncio.sleep(0.02)
            assert any("port countered at" in (e.summary or "") for e in u.events)
            starts = [e.actor_id for e in u.events if e.kind == EventKind.HUMAN_TURN_START]
            assert starts.count("P1") >= 2
            assert "P2" not in starts
            assert runner.state.current_player_idx == 0
        finally:
            await runner.stop()

    asyncio.run(go())


def _flee_obs(events=None, ferrengal=77):
    return SimpleNamespace(
        adjacent=[{"id": 77, "navhaz": 0}, {"id": 39, "navhaz": 0}],
        turns_remaining=10,
        sector={"id": 119},
        _ferrengal_sector=ferrengal,
        recent_events=events or [],
        day=7,
        self_id="P2",
        legal_actions=[],
        ship={"fighters": 10, "cargo": {}},
    )


def test_a_bot_fleeing_ferrengi_picks_the_safe_warp_not_ferrengal(monkeypatch):
    monkeypatch.setattr(K, "BOT_HAZARD_MEMORY_MODE", "live")
    bot = HeuristicAgent("P2", "Vega", seed=1)
    bot._visit_counts[39] = 5  # legacy would prefer the unvisited Ferrengal warp
    action = bot._flee(_flee_obs(), "Ferrengi aggression 9 - bail.")
    assert action.kind == ActionKind.WARP
    assert action.args["target"] == 39
    assert "Warping to 39." in (action.thought or "")


def test_switch_off_a_bot_still_flees_into_the_unvisited_warp():
    assert not K.bot_hazard_memory_live()
    bot = HeuristicAgent("P2", "Vega", seed=1)
    bot._visit_counts[39] = 5
    action = bot._flee(_flee_obs(), "Ferrengi aggression 9 - bail.")
    assert action.kind == ActionKind.WARP
    assert action.args["target"] == 77


def test_a_bot_does_not_reenter_a_sector_that_mined_it_today(monkeypatch):
    monkeypatch.setattr(K, "BOT_HAZARD_MEMORY_MODE", "live")
    bot = HeuristicAgent("P2", "Vega", seed=1)
    mined = [{
        "kind": "mine_detonated",
        "day": 7,
        "sector_id": 77,
        "actor_id": "P9",
        "facts": {"victim": "P2", "hits": 1, "damage": 40},
    }]
    action = bot._flee(_flee_obs(mined, ferrengal=None), "Ferrengi aggression 9 - bail.")
    assert action.args["target"] == 39

    only = SimpleNamespace(
        adjacent=[{"id": 77, "navhaz": 0}],
        turns_remaining=10,
        sector={"id": 119},
        _ferrengal_sector=None,
        recent_events=mined,
        day=7,
        self_id="P2",
        legal_actions=[{"kind": "pay_toll", "legal": True}],
        ship={"fighters": 10, "cargo": {}},
    )
    stayed = bot._flee(only, "Ferrengi aggression 9 - bail.")
    assert stayed.kind == ActionKind.PAY_TOLL
    assert stayed.kind != ActionKind.WARP


def test_ferrengal_is_omitted_from_the_observation_while_the_switch_is_off():
    u = _universe(7110)
    u.ferrengal_sector = 77
    player = _seat(u)
    dumped = build_observation(u, player.id).model_dump()
    assert "ferrengal_sector" not in dumped


def test_ferrengal_is_on_the_observation_when_the_switch_is_on(monkeypatch):
    monkeypatch.setattr(K, "BOT_HAZARD_MEMORY_MODE", "live")
    u = _universe(7111)
    u.ferrengal_sector = 77
    player = _seat(u)
    obs = build_observation(u, player.id)
    assert obs._ferrengal_sector == 77
