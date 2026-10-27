"""NOTE 87 (v311-exp-alignment-trade-gaps-v1). Rows 109, 110 and 112.

Row 111 (alignment sources) and row 113 (corp transfer and the mixed-corp
Extern loss) are already on this tip. Those tests live with the code that
already does the work.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.economy import haggle_bound, haggle_experience, port_buy_price
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, Player, Port, PortClass, PortStock, Ship

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]
FUEL = Commodity.FUEL_ORE


def _seat(sector: int = 11, credits: int = 500_000):
    universe = generate_universe(
        GameConfig(seed=4, universe_size=20, max_days=5, enable_planets=False, enable_ferrengi=False)
    )
    player = Player(id="P1", name="Trader", ship=Ship(name="Unnamed"), credits=credits, experience=0)
    player.sector_id = sector
    player.ship.cargo[FUEL] = 20
    universe.players["P1"] = player
    universe.sectors[sector].occupant_ids.append("P1")
    return universe, player


def test_cabal_hold_examples_match_the_written_total() -> None:
    """formulas.html: 100 holds at B=200 cost 119,000; 50 to 250 at B=164 costs 620,800."""

    def total(base: int, count: int, already: int = 0) -> int:
        return count * base + 20 * (count * already + count * (count - 1) // 2)

    assert total(200, 100) == 119_000
    # The page says 620,800 for 50 to 250. 663,500 minus 32,700 is 630,800.
    assert total(164, 50) == 32_700
    assert total(164, 250) == 663_500
    assert total(164, 200, 50) == 630_800


def test_shop_slope_stays_when_the_class0_switch_is_off(monkeypatch) -> None:
    monkeypatch.setattr(K, "SHOP_PRICE_MODE", "live")
    monkeypatch.setattr(K, "CLASS0_HOLD_FORMULA_MODE", "legacy")
    assert K.class0_hold_formula_live() is False
    assert K.hold_next_price("merchant_cruiser", 20, 1) == 550
    assert K.hold_total_price("merchant_cruiser", 20, 2, 1) == 1120


def test_class0_formula_replaces_the_shop_slope(monkeypatch) -> None:
    monkeypatch.setattr(K, "SHOP_PRICE_MODE", "live")
    monkeypatch.setattr(K, "CLASS0_HOLD_FORMULA_MODE", "live")
    day = 1
    base = K.hold_day_base(day)
    assert K.hold_next_price("merchant_cruiser", 20, day) == base + 20 * 20
    holds = 100
    assert K.hold_total_price("merchant_cruiser", 0, holds, day) == (
        base * holds + 20 * holds * (holds - 1) // 2
    )


def test_profile_uses_the_cabal_formula_and_leaves_the_stored_flag(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.shop_price_live() is True
    assert K.class0_hold_formula_live() is True
    assert K.CLASS0_HOLD_FORMULA_MODE == "legacy"
    day = 1
    base = K.hold_day_base(day)
    assert K.hold_next_price("merchant_cruiser", 0, day) == base
    assert K.hold_next_price("merchant_cruiser", 20, day) != 550


def test_haggle_experience_off_is_the_capped_gap() -> None:
    assert haggle_experience(3, 40) == 3
    assert haggle_experience(40, 40) == K.PORT_HAGGLE_XP_CAP
    assert haggle_experience(0, 40) == 0


def test_haggle_experience_on_is_one_or_two(monkeypatch) -> None:
    assert haggle_experience(1, 40) == K.HAGGLE_EXP_GOOD == 1
    assert haggle_experience(39, 40) == 1
    assert haggle_experience(40, 40) == K.HAGGLE_EXP_GREAT == 2
    assert haggle_experience(0, 10) == 0


def _fuel_port() -> Port:
    return Port(
        class_id=PortClass.CLASS_1_BSS,
        stock={FUEL: PortStock(current=0, maximum=3000)},
        mcic={FUEL: -100},
    )


def test_a_trade_awards_the_gap_until_the_switch_is_on(monkeypatch) -> None:
    universe, player = _seat()
    port = _fuel_port()
    universe.sectors[11].port = port
    listed = port_buy_price(port, FUEL, 0)
    bound = haggle_bound(listed, -100, "sell")
    assert bound - listed > K.PORT_HAGGLE_XP_CAP
    won = apply_action(
        universe, "P1",
        Action(kind=ActionKind.TRADE, args={"side": "sell", "commodity": "fuel_ore", "qty": 1, "unit_price": bound}),
    )
    assert won.ok, won.error
    base = K.xp_award("trade") + K.xp_award("first_dock")
    assert player.experience == base + K.PORT_HAGGLE_XP_CAP

    universe, player = _seat()
    universe.sectors[11].port = _fuel_port()
    modest = apply_action(
        universe, "P1",
        Action(kind=ActionKind.TRADE, args={
            "side": "sell", "commodity": "fuel_ore", "qty": 1, "unit_price": listed + 1,
        }),
    )
    assert modest.ok, modest.error
    assert player.experience == base + K.HAGGLE_EXP_GOOD

    universe, player = _seat()
    universe.sectors[11].port = _fuel_port()
    great = apply_action(
        universe, "P1",
        Action(kind=ActionKind.TRADE, args={
            "side": "sell", "commodity": "fuel_ore", "qty": 1, "unit_price": bound,
        }),
    )
    assert great.ok, great.error
    assert player.experience == base + K.HAGGLE_EXP_GREAT


def test_ship_rename_is_absent_until_the_switch_is_on(monkeypatch) -> None:
    universe, player = _seat(K.STARDOCK_SECTOR, credits=20_000)
    kinds = {row.kind for row in legal_actions(universe, "P1")}
    assert "ship_rename" not in kinds
    refused = apply_action(universe, "P1", Action(kind=ActionKind.SHIP_RENAME, args={"name": "Ghost"}))
    assert refused.ok is False and refused.error == "unsupported action"
    assert player.ship.name == "Unnamed"
    assert player.credits == 20_000

    monkeypatch.setattr(K, "SHIP_RENAME_MODE", "live")
    away, away_player = _seat(11, credits=20_000)
    row = next(item for item in legal_actions(away, "P1") if item.kind == "ship_rename")
    assert row.legal is False and "StarDock" in (row.reason or "")
    missed = apply_action(away, "P1", Action(kind=ActionKind.SHIP_RENAME, args={"name": "Ghost"}))
    assert missed.ok is False
    assert away_player.ship.name == "Unnamed"

    universe, player = _seat(K.STARDOCK_SECTOR, credits=20_000)
    row = next(item for item in legal_actions(universe, "P1") if item.kind == "ship_rename")
    assert row.legal is True
    assert row.params["cost"] == K.SHIP_RENAME_COST
    done = apply_action(universe, "P1", Action(kind=ActionKind.SHIP_RENAME, args={"name": "  Ghost   Runner "}))
    assert done.ok, done.error
    assert player.ship.name == "Ghost Runner"
    assert player.credits == 20_000 - K.SHIP_RENAME_COST
    same = apply_action(universe, "P1", Action(kind=ActionKind.SHIP_RENAME, args={"name": "Ghost Runner"}))
    assert same.ok is False and "already" in (same.error or "")
    assert player.credits == 20_000 - K.SHIP_RENAME_COST


def test_ship_rename_refuses_a_blank_name_and_a_short_purse(monkeypatch) -> None:
    monkeypatch.setattr(K, "SHIP_RENAME_MODE", "live")
    universe, player = _seat(K.STARDOCK_SECTOR, credits=K.SHIP_RENAME_COST - 1)
    row = next(item for item in legal_actions(universe, "P1") if item.kind == "ship_rename")
    assert row.legal is False and "credits" in (row.reason or "")
    broke = apply_action(universe, "P1", Action(kind=ActionKind.SHIP_RENAME, args={"name": "Ghost"}))
    assert broke.ok is False
    assert player.ship.name == "Unnamed"
    player.credits = K.SHIP_RENAME_COST
    blank = apply_action(universe, "P1", Action(kind=ActionKind.SHIP_RENAME, args={"name": "   "}))
    assert blank.ok is False
    assert player.credits == K.SHIP_RENAME_COST


def test_profile_turns_the_note_helpers_on_without_moving_the_flags(monkeypatch) -> None:
    assert K.class0_hold_formula_live() is False
    assert K.ship_rename_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.class0_hold_formula_live() is True
    assert K.ship_rename_live() is True
    assert K.CLASS0_HOLD_FORMULA_MODE == "legacy"
    assert K.SHIP_RENAME_MODE == "legacy"


def test_redesign_registration_form_renames_the_ship(tmp_path, monkeypatch) -> None:
    """The redesign yard form charges the fee and christens the ship."""
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    import tests._cu_host as hostmod

    monkeypatch.setattr(K, "SHIP_RENAME_MODE", "live")
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    token = "note87-rename-token-p2-000000000000"
    with hostmod.CuHost(tmp_path, token, park_at=1) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={token}")
            button = page.locator("#here button[data-kind=ship_rename]")
            button.wait_for(timeout=20_000)
            assert button.is_enabled()
            before = int(host.runner.state.universe.players["P2"].credits)
            button.click()
            page.wait_for_selector("#formSlot .frm", timeout=5_000)
            form = page.locator("#formSlot")
            text = form.inner_text()
            assert "CHANGE REGISTRATION" in text
            assert "5,000 cr" in text
            assert "registered as" in text
            page.locator("#formSlot input[data-n=name]").fill("Ghost Runner")
            page.locator("#formSlot button", has_text="CONFIRM").click()
            page.wait_for_function(
                "() => /Ghost Runner/.test(document.body.innerText)",
                timeout=20_000,
            )
            assert host.runner.state.universe.players["P2"].ship.name == "Ghost Runner"
            assert host.runner.state.universe.players["P2"].credits == before - K.SHIP_RENAME_COST
            page.goto(f"{host.base}/bot?seat=P2&token={token}")
            page.wait_for_selector("#sbCredits", timeout=20_000)
            assert page.locator("button[data-kind=ship_rename]").count() == 0
        finally:
            browser.close()


def test_redesign_has_the_registration_form_and_bot_does_not() -> None:
    redesign = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")
    assert 'reasonButton("ship_rename", "Change registration"' in redesign
    assert "CHANGE REGISTRATION" in redesign
    for name in ("bot.html", "bot.js", "bot-parity.js"):
        assert "ship_rename" not in (ROOT / "web" / name).read_text(encoding="utf-8")
