"""Port upgrade and construction. docs/playtests/ports/PORT_UPGRADE_BUILD.md."""

from __future__ import annotations

import random

import pytest

from tw2k.agents.prompts import get_system_prompt
from tw2k.agents.seat_brain import SeatBrain
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe, tick_day
from tw2k.engine import constants as K
from tw2k.engine.economy import regenerate_ports
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Commodity,
    Planet,
    PlanetClass,
    Player,
    Port,
    PortClass,
    PortStock,
    Ship,
    ShipClass,
)
from tw2k.engine.observation import build_observation
from tw2k.engine.port_build import upgrade_legal_spec

FUEL, ORG, EQ = Commodity.FUEL_ORE, Commodity.ORGANICS, Commodity.EQUIPMENT


def _world():
    u = generate_universe(GameConfig(
        seed=8, universe_size=20, max_days=12, enable_planets=False, enable_ferrengi=False,
    ))
    player = Player(id="A", name="Ada", ship=Ship(), credits=5_000_000, experience=0, alignment=-40)
    player.sector_id = 12
    u.players["A"] = player
    u.sectors[12].occupant_ids.append("A")
    u.sectors[12].port = None
    return u, player


def _port(u, cls=PortClass.CLASS_6_BBS, maximum=3000, current=1000, prod=100):
    """BBS buys fuel and organics, sells equipment."""
    port = Port(
        class_id=cls,
        name="Test",
        stock={
            FUEL: PortStock(current=current, maximum=maximum),
            ORG: PortStock(current=current, maximum=maximum),
            EQ: PortStock(current=current, maximum=maximum),
        },
        productivity={FUEL: prod, ORG: prod, EQ: prod},
        mcic={FUEL: -60, ORG: -60, EQ: 50},
    )
    u.sectors[12].port = port
    return port


def _planet(u, owner="A", ticker=None, ore=0, org=0, eq=0, sector=12):
    pl = Planet(
        id=7, sector_id=sector, name="Home", class_id=PlanetClass.M,
        owner_id=owner, corp_ticker=ticker,
        stockpile={FUEL: ore, ORG: org, EQ: eq},
    )
    u.planets[7] = pl
    u.sectors[sector].planet_ids.append(7)
    return pl


def _up(u, commodity="equipment", units=1):
    return apply_action(u, "A", Action(kind=ActionKind.PORT_UPGRADE, args={"commodity": commodity, "units": units}))


def _build(u, code="SSS", planet=7, name=None):
    args = {"port_class": code, "planet_id": planet}
    if name is not None:
        args["name"] = name
    return apply_action(u, "A", Action(kind=ActionKind.PORT_BUILD, args=args))


def _kinds(u, pid="A"):
    return {row.kind: row for row in legal_actions(u, pid)}


def test_pu1_offered_only_at_a_port():
    u, _ = _world()
    assert not _kinds(u)["port_upgrade"].legal
    assert not _up(u).ok
    _port(u)
    assert _kinds(u)["port_upgrade"].legal


def test_pu2_specials_refused():
    u, _ = _world()
    for cls in (PortClass.STARDOCK, PortClass.FEDERAL):
        _port(u, cls)
        assert not _up(u).ok
        assert "cannot be upgraded" in (_up(u).error or "")


def test_pu4_pu5_cost_holds_and_productivity():
    u, player = _world()
    port = _port(u)
    before = port.stock[EQ].current
    res = _up(u, "equipment", 10)
    assert res.ok, res.error
    assert player.credits == 5_000_000 - 9000
    assert port.stock[EQ].maximum == 3100
    assert port.productivity[EQ] == 110
    assert port.stock[EQ].current == before
    assert port.credits == 0


def test_pu6_cap_and_over_room_is_refused():
    u, _ = _world()
    port = _port(u, maximum=32750, prod=100)
    assert _up(u, "equipment", 1).ok
    assert port.stock[EQ].maximum == 32760
    refused = _up(u, "equipment", 1)
    assert not refused.ok and "at most 0" in (refused.error or "")
    port.productivity[EQ] = K.PORT_PRODUCTIVITY_MAX
    port.stock[EQ].maximum = 1000
    assert not _up(u, "equipment", 1).ok


def test_pu6_gold_cap_is_a_constant(monkeypatch):
    monkeypatch.setattr(K, "PORT_UPGRADE_MAX_HOLDS", 65530)
    monkeypatch.setattr(K, "PORT_PRODUCTIVITY_MAX", 6553)
    u, _ = _world()
    port = _port(u, maximum=32760, prod=100)
    assert _up(u, "equipment", 1).ok
    assert port.stock[EQ].maximum == 32770


def test_pu9_pu10_exp_align_carry_even_when_red():
    u, player = _world()
    _port(u)
    assert player.alignment < 0
    _up(u, "equipment", 1)
    assert player.experience == 0 and player.alignment == -40
    assert player.port_upgrade_carry["equipment"]["exp"] == pytest.approx(0.3)
    _up(u, "equipment", 9)  # 0.3 + 2.7 = 3.0 exp, 0.15 + 1.35 = 1.5 align
    assert player.experience == 3
    assert player.alignment == -40 + 1
    fresh, who = _world()
    _port(fresh)
    _up(fresh, "equipment", 2200)
    assert who.experience == 660
    assert who.alignment == -40 + 330


def test_pu11_sell_stock_unchanged_and_buy_room_grows():
    u, _ = _world()
    port = _port(u, current=500, maximum=1000)
    _up(u, "fuel_ore", 5)  # BBS buys fuel
    assert port.stock[FUEL].current == 500
    assert port.stock[FUEL].maximum - port.stock[FUEL].current == 550


def test_pu14_visit_turn():
    u, player = _world()
    _port(u)
    player.ship.cargo[EQ] = 1
    assert _up(u, "equipment", 1).ok
    assert player.turns_today == 1
    assert _up(u, "organics", 1).ok
    assert player.turns_today == 1


def test_pu15_guards():
    u, player = _world()
    _port(u)
    player.planet_landed = 1
    assert not _up(u).ok
    player.planet_landed = None
    player.ship.ship_class = ShipClass.ESCAPE_POD
    assert not _up(u).ok
    player.ship.ship_class = ShipClass.MERCHANT_CRUISER
    u.sectors[12].port.bust_player_id = "A"
    assert not _up(u).ok


def test_pu16_pu18_pu19_pu20_build_sss():
    u, player = _world()
    u.sectors[12].port = None
    assert not _kinds(u)["port_build"].legal
    pl = _planet(u, eq=100, org=100, ore=100)
    row = _kinds(u)["port_build"]
    assert row.legal, row.reason
    assert "SSS" in row.params["classes"]
    assert row.params["classes"]["SSS"]["cost"] == 30000
    assert row.params["classes"]["SSS"]["days"] == 2
    res = _build(u, "BBS")
    assert res.ok, res.error
    assert u.sectors[12].port.class_id == PortClass.CLASS_6_BBS
    assert player.credits == 5_000_000 - 39250
    assert pl.stockpile[EQ] == 100  # materials wait for the day tick


def test_pu17_rival_planet_reads_like_a_missing_one():
    u, _ = _world()
    u.sectors[12].port = None
    _planet(u, owner="B", eq=500, org=500, ore=500)
    missing = _build(u, "SSS", planet=99)
    rival = _build(u, "SSS", planet=7)
    assert missing.error == rival.error == "no such planet in this sector you can build from"


def test_pu21_pu22_pu24_pu25_construction_day_tick():
    u, player = _world()
    u.sectors[12].port = None
    pl = _planet(u, ore=40, org=40, eq=40)  # two SSS days are 20 each; a short day is staged below
    assert _build(u, "SSS").ok
    tick_day(u)
    assert pl.stockpile[EQ] == 20
    assert u.sectors[12].port.construction["days_left"] == 1
    pl.stockpile[EQ] = 0
    tick_day(u)
    assert pl.stockpile[ORG] == 20  # stall takes nothing
    assert u.sectors[12].port.construction["days_left"] == 1
    pl.stockpile[EQ] = 20
    tick_day(u)
    port = u.sectors[12].port
    assert port.construction is None
    assert port.productivity[EQ] == 10
    assert port.stock[EQ].maximum == 100
    assert port.mcic[EQ] == K.PORT_MCIC_DEFAULT_SELL
    # three midnights (+1 exp, +1 align) plus the completion reward
    assert player.experience == 3 + 7 and player.alignment == -40 + 3 + 4


def test_pu23_construction_docks_are_closed():
    u, player = _world()
    u.sectors[12].port = None
    _planet(u, ore=100, org=100, eq=100)
    assert _build(u).ok
    assert not _up(u).ok
    trade = apply_action(u, "A", Action(kind=ActionKind.TRADE, args={"side": "buy", "commodity": "equipment", "qty": 1}))
    assert not trade.ok
    assert not _kinds(u)["planet_trade"].legal


def test_pu26_cap_frees_when_a_port_is_cleared():
    u, _ = _world()
    u.sectors[12].port = None
    _planet(u, ore=500, org=500, eq=500)
    from tw2k.engine.port_build import port_count
    u.port_cap = port_count(u)
    assert not _build(u).ok
    u.port_cap = port_count(u) + 1
    assert _build(u, "BSS").ok
    assert not _build(u, "SSS").ok


def test_pu27_radiation_and_fedspace():
    u, player = _world()
    u.sectors[12].port = None
    _planet(u, ore=100, org=100, eq=100)
    u.sectors[12].port_destroyed_day = u.day
    assert not _build(u).ok
    u.sectors[12].port_destroyed_day = u.day - 1
    assert _build(u, "SSS").ok
    player.sector_id = 1
    u.sectors[1].occupant_ids.append("A")
    u.sectors[1].port = None
    assert not _kinds(u)["port_build"].legal


def test_pu28_bot_upgrades_a_buying_port_only(monkeypatch):
    u, player = _world()
    _port(u, current=0, maximum=100)  # BBS buys organics
    _planet(u, org=6000)
    player.credits = 200_000
    obs = build_observation(u, "A").model_dump(mode="json")
    act = SeatBrain().decide(obs)
    assert act["kind"] == "port_upgrade"
    assert act["args"]["commodity"] == "organics"
    assert 1 <= act["args"]["units"] <= K.BOT_PORT_UPGRADE_MAX_UNITS
    monkeypatch.setattr(K, "BOT_PORT_UPGRADE_POLICY", "off")
    again = SeatBrain().decide(obs)
    assert again["kind"] != "port_upgrade"


def test_pu29_bot_does_not_build():
    u, _ = _world()
    u.sectors[12].port = None
    _planet(u, eq=5000, org=5000, ore=5000)
    obs = build_observation(u, "A").model_dump(mode="json")
    assert SeatBrain().decide(obs)["kind"] != "port_build"


def test_pu30_prompt_line_only_when_on(monkeypatch):
    line = "Upgrading a port raises how much it can buy or sell"
    assert line in get_system_prompt()
    monkeypatch.setattr(K, "PORT_UPGRADE_MODE", "legacy")
    assert line not in get_system_prompt()


def test_legacy_handlers_are_unsupported(monkeypatch):
    monkeypatch.setattr(K, "PORT_UPGRADE_MODE", "legacy")
    u, _ = _world()
    _port(u)
    assert _up(u).error == "unsupported action"
    assert "port_upgrade" not in _kinds(u)


def test_rng_is_untouched_by_upgrade_build_and_the_tick():
    u, _ = _world()
    _port(u)
    state = u.rng.getstate()
    assert _up(u, "equipment", 2).ok
    assert u.rng.getstate() == state
    u.sectors[12].port = None
    _planet(u, ore=80, org=80, eq=80)
    assert _build(u).ok
    assert u.rng.getstate() == state
    tick_day(u)
    assert u.rng.getstate() == state


def test_legal_max_units_matches_the_handler():
    rng = random.Random(4)
    u, player = _world()
    port = _port(u, maximum=rng.randint(100, 5000), current=10, prod=rng.randint(1, 400))
    player.credits = rng.randint(0, 80_000)
    _ok, _why, _cost, params = upgrade_legal_spec(u, "A")
    for commodity, row in params["commodities"].items():
        mx = int(row["max_units"])
        refused = _up(u, commodity, mx + 1)
        assert not refused.ok and f"at most {mx}" in (refused.error or "")
        if mx >= 1:
            assert _up(u, commodity, mx).ok
        port.stock[Commodity(commodity)].maximum -= K.PORT_UPGRADE_HOLDS_PER_UNIT * mx if mx else 0
        if mx:
            port.productivity[Commodity(commodity)] -= mx
            player.credits += int(row["unit_cost"]) * mx


def test_regen_follows_the_new_productivity():
    u, _ = _world()
    port = _port(u, current=0, maximum=5000, prod=10)
    _up(u, "equipment", 250)
    assert port.productivity[EQ] == 260
    before = port.stock[EQ].current
    regenerate_ports(u)
    assert port.stock[EQ].current - before == round(260 * K.PORT_REGEN_PER_DAY)
