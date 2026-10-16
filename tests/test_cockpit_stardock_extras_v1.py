"""StarDock tavern, police, ship, and bank controls on the redesign cockpit."""

from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine.models import ParkedShip, Ship, ShipClass
from tw2k.engine.tavern import password_for

from tests._cu_host import CuHost

TOK = "dock-token-p2-00000000000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-stardock-extras-v1"
WORD = password_for(250925)


def _page(pw, host):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    return browser, page


def _shoot(page, stem: str, selector: str = "") -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, height, name in ((1920, 1080, "1920"), (390, 844, "390")):
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(150)
        page.evaluate(
            "(sel) => { const el = (sel && document.querySelector(sel)) || document.querySelector('.frm') || document.querySelector('#menu') || document.querySelector('[data-screen=stardock]'); if (el) el.scrollIntoView({ block: 'center' }); }",
            selector,
        )
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _action(request) -> dict:
    body = request.post_data_json
    if callable(body):
        body = body()
    return body["action"]


def _ready(page) -> None:
    page.keyboard.press("Escape")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)


def _posted(page) -> None:
    page.wait_for_function(
        """() => {
          const chip = document.querySelector('#waitchip').textContent;
          const line = document.querySelector('#lastResult').textContent || '';
          return chip === 'YOUR MOVE' && /^(ok|REFUSED|FAILED)/.test(line);
        }""",
        timeout=20_000,
    )


def _confirm(page) -> dict:
    page.evaluate("() => { document.querySelector('#lastResult').textContent = ''; }")
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        page.locator("#dangerOk").click()
    _posted(page)
    return _action(caught.value)


def _form_post(page) -> dict:
    page.evaluate("() => { document.querySelector('#lastResult').textContent = ''; }")
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        page.locator(".frm button.verb", has_text="CONFIRM").click()
    _posted(page)
    return _action(caught.value)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    host = CuHost(tmp_path_factory.mktemp("dock"), TOK)
    host.__enter__()
    universe = host.runner.state.universe
    me = universe.players["P2"]
    origin = universe.sectors[me.sector_id]
    if "P2" in origin.occupant_ids:
        origin.occupant_ids.remove("P2")
    me.sector_id = 1
    me.planet_landed = None
    me.credits = 50_000
    me.alignment = 100
    me.ug_password_known = True
    me.ug_entered_day = int(universe.day)
    if "P2" not in universe.sectors[1].occupant_ids:
        universe.sectors[1].occupant_ids.append("P2")
    universe.players["P1"].alignment = -200
    universe.tavern = {
        "announcement": None, "conversation": [], "wall": [],
        "ug_contracts": {}, "ug_pending": {"P2": 250},
    }
    ship = Ship(ship_class=ShipClass.MERCHANT_FREIGHTER, name="spare", holds=65)
    universe.parked_ships[9001] = ParkedShip(
        id=9001, owner_id="P2", sector_id=1, ship=ship, parked_day=int(universe.day),
    )
    browser, page = _page(pw, host)
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    try:
        yield {"page": page, "me": me}
    finally:
        browser.close()
        host.__exit__(None, None, None)
        pw.stop()


def test_order_shows_the_price_and_posts(world) -> None:
    page = world["page"]
    _ready(page)
    _shoot(page, "dock", "[data-screen=stardock]")
    page.get_by_role("button", name="Order", exact=True).click()
    page.wait_for_selector("[data-price=dock]", timeout=10_000)
    assert "20" in page.locator("[data-price=dock]").inner_text()
    _shoot(page, "order")
    action = _form_post(page)
    assert action["kind"] == "tavern_order"
    assert action["args"]["item"] == "drink"


def test_talk_posts_the_text(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Talk", exact=True).click()
    page.wait_for_selector(".frm [data-n=text]", timeout=10_000)
    assert "free" in page.locator("[data-price=dock]").inner_text()
    page.locator(".frm [data-n=text]").fill("Anyone selling fuel?")
    action = _form_post(page)
    assert action["kind"] == "tavern_talk"
    assert action["args"]["text"] == "Anyone selling fuel?"


def test_announce_shows_the_price(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Announce", exact=True).click()
    page.wait_for_selector(".frm [data-n=text]", timeout=10_000)
    assert "100" in page.locator("[data-price=dock]").inner_text()
    page.locator(".frm [data-n=text]").fill("Buying organics")
    action = _form_post(page)
    assert action["kind"] == "tavern_announce"


def test_graffiti_posts_the_text(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Graffiti", exact=True).click()
    page.wait_for_selector(".frm [data-n=text]", timeout=10_000)
    page.locator(".frm [data-n=text]").fill("Terra was here")
    action = _form_post(page)
    assert action["kind"] == "tavern_graffiti"


def test_grimy_ask_shows_the_trace_price(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Ask Grimy", exact=True).click()
    page.wait_for_selector(".frm [data-n=topic]", timeout=10_000)
    assert "3,000" in page.locator("[data-price=dock]").inner_text()
    page.locator(".frm [data-n=topic]").select_option("tricron")
    action = _form_post(page)
    assert action["kind"] == "grimy_ask"
    assert action["args"]["topic"] == "tricron"


def test_curse_shows_the_turn_cost(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Curse", exact=True).click()
    page.wait_for_selector("#dangerOk", timeout=10_000)
    assert "turn" in page.locator("#menu").inner_text()
    action = _confirm(page)
    assert action["kind"] == "grimy_curse"


def test_underground_enter_posts_the_password(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Enter underground", exact=True).click()
    page.wait_for_selector(".frm [data-n=password]", timeout=10_000)
    assert "password" in page.locator("[data-price=dock]").inner_text().lower()
    page.locator(".frm [data-n=password]").fill(WORD)
    action = _form_post(page)
    assert action["kind"] == "underground_enter"


def test_underground_claim_shows_the_pending_credits(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Claim underground", exact=True).click()
    page.wait_for_selector("#dangerOk", timeout=10_000)
    assert "250" in page.locator("#menu").inner_text()
    page.keyboard.press("Escape")


def test_cineplex_says_the_picture_is_free(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Cineplex", exact=True).click()
    page.wait_for_selector("#dangerOk", timeout=10_000)
    assert "free" in page.locator("#menu").inner_text()
    page.keyboard.press("Escape")


def test_tricron_shows_the_ante(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Tri-Cron", exact=True).click()
    page.wait_for_selector("#dangerOk", timeout=10_000)
    assert "100" in page.locator("#menu").inner_text()
    _shoot(page, "tricron", "#menu")
    page.keyboard.press("Escape")


def test_reward_shows_the_minimum_and_posts(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Post a reward", exact=True).click()
    page.wait_for_selector(".frm [data-n=amount]", timeout=10_000)
    assert "1,000" in page.locator("[data-price=dock]").inner_text()
    page.locator(".frm [data-n=amount]").fill("1000")
    action = _form_post(page)
    assert action["kind"] == "post_reward"
    assert action["args"]["target_id"] == "P1"
    assert action["args"]["amount"] == 1000


def test_claim_reward_says_why_there_is_nothing(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Claim a reward", exact=True).click()
    assert "no pending reward" in page.locator("#lastResult").inner_text()


def test_ship_password_posts_the_word(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Ship password", exact=True).click()
    page.wait_for_selector(".frm [data-n=password]", timeout=10_000)
    page.locator(".frm [data-n=password]").fill("harbor")
    action = _form_post(page)
    assert action["kind"] == "ship_set_password"


def test_sell_spare_shows_the_credit(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Sell a spare ship", exact=True).click()
    page.wait_for_selector("[data-price=dock]", timeout=10_000)
    assert "cr" in page.locator("[data-price=dock]").inner_text()
    action = _form_post(page)
    assert action["kind"] == "sell_ship"
    assert action["args"]["ship_id"] == 9001


def test_bank_transfer_shows_the_cap(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Transfer credits", exact=True).click()
    page.wait_for_selector(".frm [data-n=amount]", timeout=10_000)
    assert "HBot" in page.locator(".frm").inner_text()
    _shoot(page, "transfer")
    page.locator(".frm [data-n=amount]").fill("25")
    action = _form_post(page)
    assert action["kind"] == "bank_transfer"
    assert action["args"]["to_player"] == "P1"
    assert action["args"]["amount"] == 25


def test_commission_asks_before_it_posts(world) -> None:
    page = world["page"]
    me = world["me"]
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    me.alignment = 600
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    page.wait_for_function(
        "() => { const b = document.querySelector('[data-kind=apply_commission]'); return b && !b.classList.contains('dim'); }",
        timeout=20_000,
    )
    page.get_by_role("button", name="Federal commission", exact=True).click()
    page.wait_for_selector("#dangerOk", timeout=10_000)
    assert "once" in page.locator("#menu").inner_text()
    action = _confirm(page)
    assert action["kind"] == "apply_commission"


def test_contract_shows_the_minimum(world) -> None:
    page = world["page"]
    _ready(page)
    page.get_by_role("button", name="Contract", exact=True).click()
    page.wait_for_selector(".frm [data-n=amount]", timeout=10_000)
    assert "1,000" in page.locator("[data-price=dock]").inner_text()
    page.locator(".frm [data-n=amount]").fill("1000")
    action = _form_post(page)
    assert action["kind"] == "underground_contract"
    assert action["args"]["amount"] == 1000
