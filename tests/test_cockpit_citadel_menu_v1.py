"""Citadel treasury, quasar, planet jump, transporter, claim, and destroy."""

from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine.models import Commodity

from tests._cu_host import CuHost

TOK = "citadel-token-p2-000000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-citadel-menu-v1"


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
            "(sel) => { const el = (sel && document.querySelector(sel)) || document.querySelector('.frm') || document.querySelector('#menu') || document.querySelector('.planet'); if (el) el.scrollIntoView({ block: 'center' }); }",
            selector,
        )
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _action(request) -> dict:
    body = request.post_data_json
    if callable(body):
        body = body()
    return body["action"]


def _post(page, button, fill):
    page.get_by_role("button", name=button, exact=True).click()
    page.wait_for_selector(".frm", timeout=10_000)
    if fill:
        fill(page)
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        page.locator(".frm button.verb", has_text="CONFIRM").click()
    return _action(caught.value)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    host = CuHost(tmp_path_factory.mktemp("citadel"), TOK)
    host.__enter__()
    universe = host.runner.state.universe
    me = universe.players["P2"]
    planet = next(p for p in universe.planets.values() if p.sector_id > 10)
    origin = universe.sectors[me.sector_id]
    origin.occupant_ids.remove("P2")
    me.sector_id = planet.sector_id
    universe.sectors[planet.sector_id].occupant_ids.append("P2")
    me.planet_landed = planet.id
    me.credits = 60_000
    planet.owner_id = "P2"
    planet.citadel_level = 4
    planet.treasury = 1000
    planet.quasar_sector_pct = 10
    planet.quasar_atm_pct = 20
    planet.fighters = 0
    planet.shields = 0
    planet.has_transporter = False
    planet.stockpile[Commodity.FUEL_ORE] = 5000
    browser, page = _page(pw, host)
    try:
        yield {"page": page, "planet": planet, "universe": universe}
    finally:
        browser.close()
        host.__exit__(None, None, None)
        pw.stop()


def test_planet_card_shows_quasar_treasury_and_range(world) -> None:
    page = world["page"]
    card = page.locator(".planet").inner_text()
    assert "Quasar sector 10%" in card and "atmosphere 20%" in card
    assert "Treasury" in page.locator("[data-treasury=balance]").inner_text()
    assert "500" in page.locator("[data-range=transporter]").inner_text()
    _shoot(page, "planet")
    _shoot(page, "commands", "[data-kind=planet_transwarp]")


def test_treasury_deposit_posts_the_amount(world) -> None:
    page = world["page"]

    def fill(p):
        p.locator(".frm [data-n=amount]").fill("25")
        _shoot(p, "treasury")

    action = _post(page, "Treasury deposit", fill)
    assert action["kind"] == "deposit_treasury"
    assert action["args"]["amount"] == 25


def test_treasury_withdraw_posts_the_amount(world) -> None:
    page = world["page"]
    page.get_by_role("button", name="Treasury withdraw", exact=True).click()
    page.wait_for_selector(".frm [data-n=side]", timeout=10_000)
    page.locator(".frm [data-n=side]").select_option("withdraw")
    page.locator(".frm [data-n=amount]").fill("10")
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        page.locator(".frm button.verb", has_text="CONFIRM").click()
    action = _action(caught.value)
    assert action["kind"] == "withdraw_treasury"
    assert action["args"]["amount"] == 10


def test_quasar_sector_posts_the_percent(world) -> None:
    page = world["page"]
    action = _post(page, "Quasar sector", lambda p: p.locator(".frm [data-n=pct]").fill("15"))
    assert action["kind"] == "set_quasar_sector"
    assert action["args"]["pct"] == 15


def test_quasar_atmosphere_posts_the_percent(world) -> None:
    page = world["page"]
    page.get_by_role("button", name="Quasar atmosphere", exact=True).click()
    page.wait_for_selector(".frm [data-n=kind]", timeout=10_000)
    page.locator(".frm [data-n=kind]").select_option("set_quasar_atm")
    page.locator(".frm [data-n=pct]").fill("25")
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        page.locator(".frm button.verb", has_text="CONFIRM").click()
    action = _action(caught.value)
    assert action["kind"] == "set_quasar_atm"
    assert action["args"]["pct"] == 25


def test_planet_transwarp_shows_the_fuel_cost(world) -> None:
    page = world["page"]
    page.get_by_role("button", name="Planet TransWarp", exact=True).click()
    page.wait_for_selector("[data-fuel=jump]", timeout=10_000)
    assert "400" in page.locator("[data-fuel=jump]").inner_text()
    _shoot(page, "jump")
    page.locator(".frm [data-n=dest]").fill("20")
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        page.locator(".frm button.verb", has_text="CONFIRM").click()
    action = _action(caught.value)
    assert action["kind"] == "planet_transwarp"
    assert action["args"]["dest_sector"] == 20


def test_claim_says_why_when_the_planet_is_yours(world) -> None:
    page = world["page"]
    page.keyboard.press("Escape")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    page.get_by_role("button", name="Claim planet", exact=True).click()
    page.wait_for_function("() => /already owned/.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)


def test_buy_transporter_shows_the_price(world) -> None:
    page = world["page"]
    page.get_by_role("button", name="Buy transporter", exact=True).click()
    page.wait_for_selector("#menu", timeout=10_000)
    assert "50,000" in page.locator("#menu").inner_text()
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        page.locator("#dangerOk").click()
    assert _action(caught.value)["kind"] == "planet_buy_transporter"


def test_use_transporter_shows_the_range(world) -> None:
    page = world["page"]
    page.wait_for_function(
        "() => { const b = document.querySelector('[data-kind=planet_transport]'); return b && !b.classList.contains('dim'); }",
        timeout=10_000,
    )
    page.get_by_role("button", name="Use transporter", exact=True).click()
    page.wait_for_selector("[data-fuel=jump]", timeout=10_000)
    text = page.locator("[data-fuel=jump]").inner_text()
    assert "10 fuel" in text and "Range" in text
    page.keyboard.press("Escape")


def test_destroy_asks_before_it_posts(world) -> None:
    page = world["page"]
    planet = world["planet"]
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    planet.owner_id = "P1"
    planet.fighters = 0
    planet.shields = 0
    planet.colonists[Commodity.FUEL_ORE] = 100
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    page.wait_for_function(
        "() => { const b = document.querySelector('[data-kind=planet_destroy]'); return b && !b.classList.contains('dim'); }",
        timeout=15_000,
    )
    page.get_by_role("button", name="Destroy planet", exact=True).click()
    page.wait_for_selector("#menu[data-screen='Destroy planet']", timeout=10_000)
    assert "cannot be undone" in page.locator("#menu").inner_text()
    _shoot(page, "destroy")
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        page.locator("#dangerOk").click()
    assert _action(caught.value)["kind"] == "planet_destroy"
