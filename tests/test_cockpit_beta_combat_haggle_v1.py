"""NOTE 71 cockpit items. Redesign only. /bot is not loaded.

Enter on a select does not POST /action. Typing into a prefilled amount
replaces it. A day-6 tax reads as last night's on day 7. StarDock keeps
its three buttons. The shipyard asks before it posts. The bank withdraw
box starts empty. A 3-seat alliance picker posts the second commander.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine.models import Corporation, EventKind, FighterDeployment, FighterMode, Player, Ship, ShipClass

from tests._cu_host import CuHost

TOK = "note71-haggle-token-p2-000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "beta-combat-haggle-v1"


def _open(browser, host):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    return page


def _shoot(page, stem: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / f"{stem}.png"))


def _show(page, host):
    """The cockpit paints the turn snapshot. Rebuild it from the live universe."""
    from tw2k.engine.observation import build_observation

    agent = next(a for a in host.runner.state.agents if a.player_id == "P2")
    agent.current_observation = build_observation(host.runner.state.universe, "P2")
    page.reload()
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function(
        "() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'",
        timeout=20_000,
    )
    page.keyboard.press("Escape")


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    import tw2k.engine.constants as K

    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    saved_info = K.INFO_MODE
    browser = None
    host = None
    page = None
    try:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium is not installed: {exc}")
        host = CuHost(tmp_path_factory.mktemp("note71"), TOK, seed=7112)
        host.__enter__()
        if host.port in range(8099, 8120) or host.port in range(8031, 8037):
            pytest.fail(f"host bound a protected port {host.port}")
        page = _open(browser, host)
        yield {"page": page, "host": host, "browser": browser}
    finally:
        if page is not None:
            page.close()
        if browser is not None:
            browser.close()
        if host is not None:
            host.__exit__(None, None, None)
        pw.stop()
        K.INFO_MODE = saved_info


def test_enter_on_a_select_does_not_post_and_typing_replaces_a_prefill(world):
    page, host = world["page"], world["host"]
    u = host.runner.state.universe
    me = u.players["P2"]
    u.sectors[me.sector_id].fighters = FighterDeployment(owner_id="P2", count=83, mode=FighterMode.DEFENSIVE)
    _show(page, host)
    posts = []
    page.on("request", lambda req: posts.append(req.url) if req.method == "POST" and req.url.endswith("/action") else None)
    page.keyboard.press("Escape")
    page.keyboard.press("F")
    page.wait_for_selector("#formSlot select", timeout=10_000)
    leave = page.locator("#formSlot [data-n=leave]")
    assert leave.input_value() == "83"
    leave.click()
    page.keyboard.type("83")
    assert leave.input_value() == "83"
    page.locator("#formSlot select").focus()
    page.keyboard.press("Enter")
    page.wait_for_timeout(400)
    assert posts == []
    _shoot(page, "fighter-select")


def test_day7_shows_last_night_no_tax_and_the_net_worth_line(world):
    page, host = world["page"], world["host"]
    u = host.runner.state.universe
    u.config.max_days = 30
    u.day = 6
    u.emit(
        EventKind.TAX_COLLECTED,
        actor_id="P2",
        sector_id=u.players["P2"].sector_id,
        payload={"credits_before": 100_000, "tax": 7826, "align_gain": 5, "new_alignment": 10},
        summary="Day 6 tax 7,826 cr",
    )
    u.day = 7
    _show(page, host)
    page.keyboard.press("V")
    page.wait_for_selector("#menu", timeout=10_000)
    text = page.locator("#menu").inner_text()
    assert "Last night: no tax" in text
    assert "Overnight Federation tax for the night before day 6: 7,826 cr, alignment +5." in text
    assert "Last night: 7,826" not in text
    assert "5% of the cash on your ship when it is over 100,000 at dawn; the bank is not taxed" in text
    assert "Under v3.11 rules you are ranked by experience" in text
    assert "Bought holds and fighters left in sectors are not counted." in text
    page.keyboard.press("Escape")
    assert page.locator("#nwBtn").inner_text() == "Net worth (estimate)"
    page.locator("#nwBtn").click()
    page.wait_for_selector("[data-worth=note]", timeout=10_000)
    _shoot(page, "net-worth")


def test_stardock_buttons_stay_put_and_the_yard_and_bank_ask_first(world):
    page, host = world["page"], world["host"]
    u = host.runner.state.universe
    me = u.players["P2"]
    if me.sector_id != 1:
        u.sectors[me.sector_id].occupant_ids.remove("P2")
        me.sector_id = 1
        if "P2" not in u.sectors[1].occupant_ids:
            u.sectors[1].occupant_ids.append("P2")
    me.credits = 0
    me.bank_balance = 311_008
    me.planet_landed = None
    _show(page, host)
    labels = page.locator("#here button").all_inner_texts()
    assert "StarDock: buy gear" in labels
    assert "Shipyards" in labels
    assert "Bank" in labels
    assert labels.index("StarDock: buy gear") < labels.index("Shipyards") < labels.index("Bank")
    gear = page.locator("#here button", has_text="StarDock: buy gear")
    assert "dim" in (gear.get_attribute("class") or "")
    assert gear.get_attribute("title")
    posts = []
    page.on("request", lambda req: posts.append(req.url) if req.method == "POST" and req.url.endswith("/action") else None)
    page.locator("#here button", has_text="Bank").click()
    page.wait_for_selector("#formSlot [data-n=amount]", timeout=10_000)
    assert page.locator("#formSlot [data-n=side]").input_value() == "withdraw"
    assert page.locator("#formSlot [data-n=amount]").input_value() == ""
    page.keyboard.press("Escape")

    me.credits = 500_000
    _show(page, host)
    page.locator("#here button", has_text="Shipyards").click()
    page.wait_for_selector("#formSlot select", timeout=10_000)
    page.locator("#formSlot select").focus()
    page.keyboard.press("Enter")
    page.wait_for_timeout(300)
    assert page.locator("[data-yard=confirm]").count() == 0
    page.locator("#formSlot button", has_text="CONFIRM").click()
    page.wait_for_selector("[data-yard=confirm]", timeout=10_000)
    assert "Want to buy it?" in page.locator("[data-yard=confirm]").inner_text()
    assert posts == []
    page.locator("#dangerNo").click()
    page.wait_for_timeout(300)
    assert posts == []
    _shoot(page, "stardock")


def test_alliance_picker_lists_both_commanders_and_posts_the_second(world):
    page, host = world["page"], world["host"]
    u = host.runner.state.universe
    if "P3" not in u.players:
        u.players["P3"] = Player(
            id="P3", name="Orion",
            ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER),
            sector_id=2, credits=1_000,
        )
    u.players["P1"].name = "Vega"
    u.corporations["ZZ"] = Corporation(ticker="ZZ", name="Zed", ceo_id="P2", member_ids=["P2"])
    u.players["P2"].corp_ticker = "ZZ"
    _show(page, host)
    page.keyboard.press("T")
    page.wait_for_selector("#corpBtns", timeout=10_000)
    page.locator("#corpBtns button", has_text="Propose alliance").click()
    page.wait_for_selector("#commanderPick", timeout=10_000)
    options = page.locator("#commanderPick option")
    assert options.count() == 2
    names = [options.nth(i).inner_text() for i in range(2)]
    assert names == ["Vega", "Orion"]
    assert options.nth(1).get_attribute("value") == "P3"
    posted = []
    page.on("request", lambda req: posted.append(req.post_data or "") if req.method == "POST" and req.url.endswith("/action") else None)
    page.locator("#commanderPick").select_option(index=1)
    page.locator("#dangerOk").click()
    page.locator("#menu button", has_text="CONFIRM").click()
    page.wait_for_timeout(800)
    blob = " ".join(posted)
    assert '"target": "P3"' in blob or '"target":"P3"' in blob
    _shoot(page, "alliance")
