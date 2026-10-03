"""Port quotes follow stock, MCIC, and experience."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, build_observation, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.economy import port_buy_price, port_sell_price
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, Player, Port, PortClass, PortStock, Ship

ROOT = Path(__file__).resolve().parents[1]
FUZZ = ROOT / "scripts" / "port_trade_fuzz.py"
FUEL = Commodity.FUEL_ORE
EQ = Commodity.EQUIPMENT


def _sell_port(mcic: int, current: int, maximum: int = 3000) -> Port:
    return Port(
        class_id=PortClass.CLASS_5_SBS,
        stock={EQ: PortStock(current=current, maximum=maximum)},
        mcic={EQ: mcic},
    )


def _buy_port(mcic: int, current: int, maximum: int = 3000) -> Port:
    return Port(
        class_id=PortClass.CLASS_1_BSS,
        stock={FUEL: PortStock(current=current, maximum=maximum)},
        mcic={FUEL: mcic},
    )


def test_price_falls_as_stock_rises_on_both_sides() -> None:
    sell = [_sell_port(50, current) for current in (0, 1000, 2000, 3000)]
    sell_prices = [port_sell_price(port, EQ) for port in sell]
    assert sell_prices == sorted(sell_prices, reverse=True)
    assert sell_prices[0] > sell_prices[-1]
    buy = [_buy_port(-60, current) for current in (0, 1000, 2000, 3000)]
    buy_prices = [port_buy_price(port, FUEL) for port in buy]
    assert buy_prices == sorted(buy_prices, reverse=True)
    assert buy_prices[0] > buy_prices[-1]


def test_experience_never_worsens_a_deal_and_stops_at_the_cap() -> None:
    sell = _sell_port(50, 1500)
    buy = _buy_port(-60, 500)
    steps = (0, 100, 500, 1000, 1001, 50_000)
    paid = [port_sell_price(sell, EQ, xp) for xp in steps]
    received = [port_buy_price(buy, FUEL, xp) for xp in steps]
    assert paid == sorted(paid, reverse=True)
    assert received == sorted(received)
    assert paid[3] == paid[4] == paid[5]
    assert received[3] == received[4] == received[5]
    assert paid[0] > paid[3]
    assert received[0] < received[3]


def test_different_mcic_quotes_a_different_price() -> None:
    cheap = port_sell_price(_sell_port(20, 1500), EQ)
    dear = port_sell_price(_sell_port(90, 1500), EQ)
    assert dear > cheap
    low = port_buy_price(_buy_port(-20, 500), FUEL)
    high = port_buy_price(_buy_port(-90, 500), FUEL)
    assert high > low


def test_same_seed_rolls_the_same_hidden_values() -> None:
    config = GameConfig(seed=4242, universe_size=40, enable_planets=False, enable_ferrengi=False)
    first = generate_universe(config)
    second = generate_universe(config)
    seen: set[int] = set()
    for sid, sector in first.sectors.items():
        other = second.sectors[sid].port
        port = sector.port
        if port is None:
            assert other is None
            continue
        assert port.mcic == other.mcic
        assert port.productivity == other.productivity
        for commodity, mcic in port.mcic.items():
            seen.add(mcic)
            assert K.PORT_MCIC_MIN <= mcic <= K.PORT_MCIC_MAX
            assert 1 <= port.productivity[commodity] <= K.PORT_PRODUCTIVITY_MAX
            if port.sells(commodity):
                assert mcic > 0
            if port.buys(commodity):
                assert mcic < 0
    assert len(seen) > 1


def test_old_save_loads_without_hidden_fields() -> None:
    raw = {
        "class_id": int(PortClass.CLASS_6_BBS),
        "stock": {"fuel_ore": {"current": 0, "maximum": 1000}},
        "name": "Old",
    }
    loaded = Port.model_validate(raw)
    assert loaded.mcic == {}
    assert loaded.productivity == {}
    fresh = Port(
        class_id=PortClass.CLASS_6_BBS,
        stock={FUEL: PortStock(current=0, maximum=1000)},
    )
    assert port_buy_price(loaded, FUEL) == port_buy_price(fresh, FUEL)


def test_same_port_buy_then_sell_does_not_profit() -> None:
    universe = generate_universe(
        GameConfig(seed=7, universe_size=20, enable_planets=False, enable_ferrengi=False)
    )
    port = Port(
        class_id=PortClass.CLASS_4_SSB,
        stock={FUEL: PortStock(current=500, maximum=1000)},
        mcic={FUEL: 40},
        productivity={FUEL: 10},
    )
    universe.sectors[12].port = port
    player = Player(id="P1", name="Trader", ship=Ship(), credits=50_000, turns_per_day=100)
    player.sector_id = 12
    universe.players["P1"] = player
    before = player.credits
    bought = apply_action(
        universe,
        "P1",
        Action(kind=ActionKind.TRADE, args={"side": "buy", "commodity": "fuel_ore", "qty": 3}),
    )
    assert bought.ok
    sold = apply_action(
        universe,
        "P1",
        Action(kind=ActionKind.TRADE, args={"side": "sell", "commodity": "fuel_ore", "qty": 3}),
    )
    assert sold.ok is False
    assert player.credits <= before


def test_hidden_fields_stay_out_of_the_brief_and_legal_actions() -> None:
    universe = generate_universe(
        GameConfig(seed=11, universe_size=25, enable_planets=False, enable_ferrengi=False)
    )
    player = Player(id="P1", name="Trader", ship=Ship(), credits=50_000)
    player.sector_id = 12
    universe.players["P1"] = player
    universe.sectors[12].occupant_ids.append("P1")
    brief = json.dumps(build_observation(universe, "P1").model_dump())
    actions = json.dumps([row.model_dump() for row in legal_actions(universe, "P1")])
    blob = (brief + actions).lower()
    assert "mcic" not in blob
    assert "productivity" not in blob


def _fuzz(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(FUZZ), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_port_trade_fuzz_passes() -> None:
    proc = _fuzz("--seeds", "2")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "port_trade_fuzz: PASS" in proc.stdout
    assert "coverage:" not in proc.stdout
    assert proc.stdout.count("| pass |") == 2


def test_port_trade_fuzz_fails_when_a_side_is_zero() -> None:
    proc = _fuzz("--seeds", "1", "--force-zero", "sell")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "coverage: sell never succeeded" in proc.stdout
    assert "port_trade_fuzz: FAIL" in proc.stdout
