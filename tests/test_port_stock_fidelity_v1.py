"""Selling ports open full. Buying ports open hungry. A quiet day gives room back.

PORT_STOCK_FIDELITY_MODE stays legacy, so the pin and the digests do not move.
PORT_OPEN_STOCK_MODE stays legacy too. Live is a separate switch.

Plants these tests re-break:
- pb1 live still opens a selling side at 0
- pb2 a quiet day still adds stock on a buying side
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine.actions import ActionKind
from tw2k.engine.economy import can_trade, port_buy_price, regenerate_ports
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, GameConfig, Player, PortClass
from tw2k.engine.universe import generate_universe

LUMPED = "nothing you can buy or sell here right now (cargo, credits, holds or port stock)"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "port-stock-and-trade-reason-v1"


def _world(seed: int = 4242):
    return generate_universe(
        GameConfig(seed=seed, universe_size=40, enable_ferrengi=False, enable_planets=False)
    )


def _rows(universe):
    found = []
    for sid in sorted(universe.sectors):
        port = universe.sectors[sid].port
        if port is None:
            continue
        for commodity, stock in port.stock.items():
            found.append((port, commodity, stock))
    return found


def _sbb(universe):
    for sector in universe.sectors.values():
        port = sector.port
        if port is not None and port.class_id == PortClass.CLASS_3_SBB:
            return sector
    raise AssertionError("expected an SBB port")


def _seat(universe, sector, *, credits: int = 0):
    player = Player(id="P1", name="Ben", credits=credits, sector_id=sector.id)
    universe.players["P1"] = player
    sector.occupant_ids.append("P1")
    return player


def _trade(universe):
    for action in legal_actions(universe, "P1"):
        if action.kind == ActionKind.TRADE.value:
            return action
    raise AssertionError("expected a trade action")


def test_default_stays_legacy():
    assert K.PORT_STOCK_FIDELITY_MODE == "legacy"
    assert K.port_stock_fidelity_live() is False
    assert K.PORT_OPEN_STOCK_MODE == "legacy"


def test_legacy_ports_still_open_empty():
    rows = _rows(_world())
    assert rows
    assert all(int(stock.current) == int(stock.maximum * K.PORT_START_STOCK_PERCENT) for _p, _c, stock in rows)


def test_live_sell_side_opens_full_and_buy_side_opens_hungry(monkeypatch):
    monkeypatch.setattr(K, "PORT_STOCK_FIDELITY_MODE", "live")
    rows = _rows(_world())
    assert rows
    for port, commodity, stock in rows:
        if port.sells(commodity):
            assert int(stock.current) == int(stock.maximum) > 0
        if port.buys(commodity):
            assert int(stock.current) == 0
            assert int(stock.maximum) - int(stock.current) == int(stock.maximum)


def test_quiet_day_gives_buy_room_back_and_refills_a_seller(monkeypatch):
    monkeypatch.setattr(K, "PORT_STOCK_FIDELITY_MODE", "live")
    universe = _world(seed=3)
    buy = sell = None
    for port, commodity, stock in _rows(universe):
        if buy is None and port.buys(commodity):
            buy = (stock, commodity)
        if sell is None and port.sells(commodity):
            sell = stock
        if buy and sell:
            break
    assert buy and sell
    buy_stock, _commodity = buy
    buy_stock.maximum = 1000
    buy_stock.current = 500
    sell.maximum = 1000
    sell.current = 100
    regenerate_ports(universe)
    assert int(buy_stock.current) == 450
    assert int(sell.current) == 150


def test_one_visit_cannot_move_more_than_the_max(monkeypatch):
    monkeypatch.setattr(K, "PORT_STOCK_FIDELITY_MODE", "live")
    universe = _world()
    port, commodity, stock = next((port, commodity, stock) for port, commodity, stock in _rows(universe) if port.sells(commodity))
    ok, message = can_trade(port, commodity, int(stock.maximum) + 1, "buy")
    assert ok is False
    assert "100%" in message


def test_live_reasons_name_the_commodity(monkeypatch):
    monkeypatch.setattr(K, "PORT_STOCK_FIDELITY_MODE", "live")
    universe = _world()
    sector = _sbb(universe)
    port = sector.port
    _seat(universe, sector, credits=0)
    fuel = port.stock[Commodity.FUEL_ORE]
    assert port.sells(Commodity.FUEL_ORE)
    assert int(fuel.current) == int(fuel.maximum)
    action = _trade(universe)
    why = action.params["why"]
    assert "not enough credits" in why["fuel_ore"]
    assert "holds have none" in why["organics"]
    assert "cargo, credits, holds or port stock" not in (action.reason or "")

    fuel.current = 0
    action = _trade(universe)
    assert "to sell today" in action.params["why"]["fuel_ore"]

    ore = port.stock[Commodity.ORGANICS]
    assert port.buys(Commodity.ORGANICS)
    price = port_buy_price(port, Commodity.ORGANICS, 0)
    assert price > 0
    ore.current = int(ore.maximum)
    player = universe.players["P1"]
    player.ship.cargo[Commodity.ORGANICS] = 5
    action = _trade(universe)
    assert "will not buy" in action.params["why"]["organics"] or "port is full" in action.params["why"]["organics"]


def test_legacy_keeps_the_lumped_sentence_and_no_why_key():
    universe = _world()
    sector = _sbb(universe)
    _seat(universe, sector, credits=0)
    action = _trade(universe)
    assert action.legal is False
    assert action.reason == LUMPED
    assert "why" not in action.params


def test_docked_reasons_at_1440_and_390(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    from tests._cu_host import CuHost

    SHOTS.mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    monkeypatch.delenv("TW2K_PORT_STOCK_FIDELITY", raising=False)

    def shoot(tag: str, token: str) -> str:
        root = tmp_path / tag
        root.mkdir()
        with CuHost(root, token) as host, sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={token}")
                page.wait_for_selector(".porttbl", timeout=20_000)
                text = page.locator(".porttbl").inner_text()
                dimmed = page.evaluate(
                    """() => [...document.querySelectorAll('.porttbl tr')].slice(1)
                      .filter((tr) => !tr.querySelector('button'))
                      .map((tr) => tr.children[3].className)"""
                )
                assert dimmed and all("dim" in name for name in dimmed)
                page.screenshot(path=str(SHOTS / f"1440-{tag}.png"))
                page.set_viewport_size({"width": 390, "height": 844})
                page.locator(".porttbl").scroll_into_view_if_needed()
                page.screenshot(path=str(SHOTS / f"390-{tag}.png"))
                return text
            finally:
                browser.close()

    off = shoot("off", "port-stock-off-token-p2-00000000000")
    assert LUMPED not in off
    assert "Selling 0/" in off or "to sell today" in off
    assert "on board" in off or "room " in off

    monkeypatch.setattr(K, "PORT_STOCK_FIDELITY_MODE", "live")
    on = shoot("on", "port-stock-on-token-p2-000000000000")
    assert LUMPED not in on
    pairs = re.findall(r"Selling ([0-9,]+)/([0-9,]+)", on)
    assert pairs
    assert any(left == right and left != "0" for left, right in pairs)
