"""Combat and defense controls the cockpit can reach, and the action each one posts."""

from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine.models import FighterDeployment, FighterMode, ShipClass

from tests._cu_host import CuHost

PORT_TOK = "combat-port-token-p2-000000000000"
DOCK_TOK = "combat-dock-token-p2-000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-gameplay-reach-combat-v1"
WIDTHS = ((1920, 1080, "1920"), (390, 844, "390"))


def _page(pw, host, token):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={token}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    return browser, page


def _quiet(page) -> None:
    page.keyboard.press("Escape")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)


def _shoot(page, stem: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, height, name in WIDTHS:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(150)
        page.evaluate("() => { const el = document.querySelector('[data-screen=defense]'); if (el) el.scrollIntoView({ block: 'center' }); }")
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _action(request) -> dict:
    body = request.post_data_json
    if callable(body):
        body = body()
    return body["action"]


def _post(page, kind: str) -> dict:
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        page.locator(f"[data-kind={kind}]").click()
    return _action(caught.value)


@pytest.fixture(scope="module")
def seats(tmp_path_factory):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    port_host = CuHost(tmp_path_factory.mktemp("combat-port"), PORT_TOK)
    port_host.__enter__()
    dock_host = CuHost(tmp_path_factory.mktemp("combat-dock"), DOCK_TOK, park_at=1)
    dock_host.__enter__()
    dock_u = dock_host.runner.state.universe
    dock_me = dock_u.players["P2"]
    dock_me.ship.ship_class = ShipClass.IMPERIAL_STARSHIP
    here = dock_u.sectors[dock_me.sector_id]
    lock_id = next(int(w) for w in here.warps)
    lock = dock_u.sectors[lock_id]
    if lock.fighters is None:
        lock.fighters = FighterDeployment(owner_id="P2", count=5, mode=FighterMode.DEFENSIVE)
    dock_me.known_sectors.add(lock_id)
    port_browser, port_page = _page(pw, port_host, PORT_TOK)
    dock_browser, dock_page = _page(pw, dock_host, DOCK_TOK)
    try:
        yield {"port": port_page, "dock": dock_page}
    finally:
        port_browser.close()
        dock_browser.close()
        port_host.__exit__(None, None, None)
        dock_host.__exit__(None, None, None)
        pw.stop()


def test_encounter_buttons_say_why_when_nobody_challenges(seats) -> None:
    port = seats["port"]
    _quiet(port)
    text = port.locator("[data-fighters=here]").inner_text()
    assert "No fighters" in text or "Your fighters" in text
    for kind in ("pay_toll", "retreat", "surrender"):
        port.locator(f"[data-kind={kind}]").click()
        port.wait_for_function(
            "(kind) => (document.querySelector('#lastResult').textContent || '').length > 0",
            arg=kind,
            timeout=10_000,
        )
        assert "ok —" not in port.locator("#lastResult").inner_text()
    _shoot(port, "encounter")


def test_deployed_mode_shows_and_reaction_waits_for_a_planet(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("f")
    port.wait_for_selector(".frm [data-n=leave]", timeout=10_000)
    port.locator(".frm [data-n=leave]").fill("4")
    port.locator(".frm [data-n=mode]").select_option("toll")
    port.keyboard.press("Enter")
    port.wait_for_function("() => /^ok —/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    port.wait_for_function("() => /toll/.test(document.querySelector('[data-fighters=here]').textContent || '')", timeout=10_000)
    port.keyboard.press("g")
    port.wait_for_selector("#menu[data-screen='Deployed Fighters']", timeout=10_000)
    assert "toll" in port.locator("#menu").inner_text().lower()
    port.keyboard.press("Escape")
    _quiet(port)
    port.locator("[data-kind=set_military_reaction]").click()
    port.wait_for_function("() => /planet|landed|citadel/i.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)


def test_cloak_posts_after_it_is_bought(seats) -> None:
    dock = seats["dock"]
    _quiet(dock)
    assert dock.locator("[data-gear=cloaks]").inner_text().endswith("0")
    dock.locator("[data-kind=cloak]").click()
    dock.wait_for_function("() => /cloak/i.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)
    dock.get_by_role("button", name="StarDock: buy gear").click()
    dock.locator(".frm [data-n=item]").select_option("cloak")
    dock.locator(".frm [data-n=qty]").fill("1")
    dock.keyboard.press("Enter")
    dock.wait_for_function("() => document.querySelector('[data-gear=cloaks]').textContent.trim().endsWith('1')", timeout=20_000)
    action = _post(dock, "cloak")
    assert action["kind"] == "cloak"
    dock.wait_for_function("() => /^ok —/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)


def test_disruptor_shows_the_count_and_the_reason(seats) -> None:
    port = seats["port"]
    _quiet(port)
    assert port.locator("[data-gear=disruptors]").inner_text().endswith("0")
    port.locator("[data-kind=fire_disruptor]").click()
    port.wait_for_function("() => /disruptor/i.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)


def test_limpet_query_posts_and_removal_says_why(seats) -> None:
    dock = seats["dock"]
    _quiet(dock)
    assert dock.locator("[data-gear=limpet]").is_hidden()
    action = _post(dock, "query_limpets")
    assert action["kind"] == "query_limpets"
    dock.wait_for_function("() => /^ok —/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    dock.locator("[data-kind=remove_limpet]").click()
    dock.wait_for_function("() => /limpet/i.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)
    assert "ok —" not in dock.locator("#lastResult").inner_text()


def test_tow_line_and_release_say_when_nothing_is_locked(seats) -> None:
    port = seats["port"]
    _quiet(port)
    assert "Towing nothing" in port.locator("[data-gear=tow]").inner_text()
    port.locator("[data-kind=tow_release]").click()
    port.wait_for_function("() => /tow/i.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)
    assert "ok —" not in port.locator("#lastResult").inner_text()


def test_transwarp_shows_the_fuel_cost_once_a_lock_exists(seats) -> None:
    dock = seats["dock"]
    _quiet(dock)
    dock.locator("[data-kind=ship_transwarp]").click()
    dock.wait_for_function("() => /transwarp/i.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)
    dock.get_by_role("button", name="StarDock: buy gear").click()
    dock.locator(".frm [data-n=item]").select_option("transwarp_drive")
    dock.locator(".frm [data-n=qty]").fill("1")
    dock.keyboard.press("Enter")
    dock.wait_for_function("() => /^ok —/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    dock.locator("[data-kind=ship_transwarp]").click()
    dock.wait_for_selector("[data-ore=cost]", timeout=10_000)
    cost = dock.locator("[data-ore=cost]").inner_text()
    assert "Fuel cost" in cost and "ore" in cost
    with dock.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        dock.get_by_role("button", name="CONFIRM").click()
    action = _action(caught.value)
    assert action["kind"] == "ship_transwarp"
    assert isinstance(action["args"]["sector_id"], int)
    _shoot(dock, "defense")
