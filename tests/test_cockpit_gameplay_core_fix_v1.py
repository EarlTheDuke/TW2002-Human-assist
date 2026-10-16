"""Terra colonists, the wait warning, the shipyard, the attack prompt, and mine pickup."""

from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine.models import EventKind, FerrengiShip, MineDeployment, MineType

from tests._cu_host import CuHost

DOCK_TOK = "core-dock-token-p2-000000000000"
PORT_TOK = "core-port-token-p2-000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-gameplay-core-fix-v1"


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


def _action(request) -> dict:
    body = request.post_data_json
    if callable(body):
        body = body()
    return body["action"]


def _shoot(page, stem: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, height, name in ((1920, 1080, "1920"), (390, 844, "390")):
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(150)
        page.evaluate("() => { const el = document.querySelector('.frm') || document.querySelector('#menu') || document.querySelector('#here'); if (el) el.scrollIntoView({ block: 'center' }); }")
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


@pytest.fixture(scope="module")
def seats(tmp_path_factory):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    dock_host = CuHost(tmp_path_factory.mktemp("core-dock"), DOCK_TOK, park_at=1)
    dock_host.__enter__()
    port_host = CuHost(tmp_path_factory.mktemp("core-port"), PORT_TOK)
    port_host.__enter__()
    universe = port_host.runner.state.universe
    me = universe.players["P2"]
    sector = universe.sectors[me.sector_id]
    sector.mines.append(MineDeployment(owner_id="P2", kind=MineType.ARMID, count=3))
    universe.ferrengi["ferr_core"] = FerrengiShip(
        id="ferr_core", name="Ferrengi Assault Trader", sector_id=me.sector_id,
        aggression=4, fighters=40, shields=10,
    )
    universe.emit(
        EventKind.COMBAT, actor_id="P1", sector_id=me.sector_id,
        payload={"defender": "P2", "attacker": "Raider", "defender_losses": 4, "attacker_losses": 1},
        summary="Raider attacked Commander",
    )
    dock_browser, dock_page = _page(pw, dock_host, DOCK_TOK)
    port_browser, port_page = _page(pw, port_host, PORT_TOK)
    try:
        yield {"dock": dock_page, "port": port_page}
    finally:
        dock_browser.close()
        port_browser.close()
        dock_host.__exit__(None, None, None)
        port_host.__exit__(None, None, None)
        pw.stop()


def test_terra_form_shows_the_pool_and_posts_the_move(seats) -> None:
    dock = seats["dock"]
    _quiet(dock)
    dock.get_by_role("button", name="Load colonists (Terra)").click()
    dock.wait_for_selector("[data-terra=pool]", timeout=10_000)
    assert "Terra holds" in dock.locator("[data-terra=pool]").inner_text()
    dock.locator(".frm [data-n=qty]").fill("1")
    _shoot(dock, "terra")
    with dock.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        dock.locator(".frm button.verb", has_text="CONFIRM").click()
    action = _action(caught.value)
    assert action["kind"] == "terra_colonists"
    assert action["args"]["qty"] == 1


def test_third_wait_asks_before_it_ends_the_day(seats) -> None:
    dock = seats["dock"]
    _quiet(dock)
    for _ in range(2):
        dock.keyboard.press(".")
        dock.wait_for_function("() => /You wait/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
        _quiet(dock)
    dock.keyboard.press(".")
    dock.wait_for_selector("#menu[data-screen=Wait]", timeout=10_000)
    assert "One more Wait ends your day" in dock.locator("#menu").inner_text()
    assert "turns left" in dock.locator("#menu").inner_text()
    _shoot(dock, "wait")
    dock.keyboard.press("Escape")


def test_shipyard_shows_the_trade_and_the_hull(seats) -> None:
    dock = seats["dock"]
    _quiet(dock)
    dock.get_by_role("button", name="Shipyards").click()
    dock.wait_for_selector("[data-yard=deal]", timeout=10_000)
    deal = dock.locator("[data-yard=deal]").inner_text()
    assert "Holds" in deal and "fighters" in deal and "turns per warp" in deal
    assert "fly the new one" in deal
    dock.locator(".frm [data-n=trade_in]").uncheck()
    stayed = dock.locator("[data-yard=deal]").inner_text()
    assert "stay aboard" in stayed
    _shoot(dock, "yard")


def test_attack_always_asks_how_many_fighters(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("a")
    port.wait_for_selector(".frm [data-n=qty]", timeout=10_000)
    assert "Ferrengi Assault Trader" in port.locator(".frm [data-n=target] option").first.inner_text()
    assert port.locator(".frm [data-n=qty]").input_value() == "20"
    assert port.locator(".frm [data-n=qty]").get_attribute("data-cap") == "20"
    _shoot(port, "attack")


def test_a_hit_on_you_shows_a_red_line(seats) -> None:
    port = seats["port"]
    port.wait_for_function("() => /You were attacked by Raider/.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)
    assert "lost 4" in port.locator("#lastResult").inner_text()


def test_h_picks_mines_back_up(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("h")
    port.wait_for_selector(".frm [data-n=pickup]", timeout=10_000)
    assert "In this sector: armid 3" in port.locator("[data-mines=form]").inner_text()
    _shoot(port, "mines")
    with port.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000) as caught:
        port.get_by_role("button", name="PICK UP").click()
    action = _action(caught.value)
    assert action["kind"] == "recall_deployed"
    assert action["args"]["what"] == "mines"
    assert action["args"]["kind"] == "armid"
    assert action["args"]["qty"] >= 1
