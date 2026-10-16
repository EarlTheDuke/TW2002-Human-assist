"""Deep-play cockpit fixes: ships you can see, names on the attack form, and the day-start lines."""

from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine.bank import collect_daily_tax
from tw2k.engine.models import FerrengiShip

from tests._cu_host import CuHost

PORT_TOK = "deep-port-token-p2-000000000000"
TURN_TOK = "deep-turn-token-p2-000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-deep-d1-fix-v1"
WIDTHS = ((1920, 1080, "1920"), (390, 844, "390"))


def _page(pw, host, token):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={token}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    return browser, page


def _quiet(page) -> None:
    page.keyboard.press("Escape")
    page.wait_for_function(
        "() => { const t = document.querySelector('#waitchip').textContent; return t === 'YOUR MOVE' || t === 'NO TURNS'; }",
        timeout=20_000,
    )


def _shoot(page, stem: str, selector: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, height, name in WIDTHS:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(150)
        page.evaluate(
            "(sel) => { const el = document.querySelector(sel); if (el) el.scrollIntoView({ block: 'center' }); }",
            selector,
        )
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


@pytest.fixture(scope="module")
def seats(tmp_path_factory):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    port_host = CuHost(tmp_path_factory.mktemp("deep-port"), PORT_TOK)
    port_host.__enter__()
    universe = port_host.runner.state.universe
    me = universe.players["P2"]
    planet = next(p for p in universe.planets.values() if p.sector_id > 10)
    origin = universe.sectors[me.sector_id]
    origin.occupant_ids.remove("P2")
    me.sector_id = planet.sector_id
    universe.sectors[planet.sector_id].occupant_ids.append("P2")
    me.known_sectors.add(planet.sector_id)
    planet.owner_id = "P2"
    planet.citadel_level = 0
    planet.citadel_target = 1
    planet.citadel_complete_day = int(universe.day) + 2
    universe.ferrengi["ferr_d1"] = FerrengiShip(
        id="ferr_d1", name="Ferrengi Assault Trader", sector_id=planet.sector_id,
        aggression=5, fighters=90, shields=40,
    )
    here = universe.sectors[planet.sector_id]
    beyond = None
    for hop in here.warps:
        for nxt in universe.sectors[int(hop)].warps:
            if int(nxt) not in (planet.sector_id, int(hop)):
                beyond = int(nxt)
                break
        if beyond is not None:
            break
    if beyond is None:
        raise RuntimeError("no two-hop course from the planet sector")
    turn_host = CuHost(tmp_path_factory.mktemp("deep-turn"), TURN_TOK)
    turn_host.__enter__()
    spent = turn_host.runner.state.universe.players["P2"]
    spent.turns_today = spent.turns_per_day
    port_browser, port_page = _page(pw, port_host, PORT_TOK)
    turn_browser, turn_page = _page(pw, turn_host, TURN_TOK)
    try:
        yield {
            "port": port_page, "turn": turn_page, "universe": universe,
            "origin": planet.sector_id, "beyond": beyond, "finish": planet.citadel_complete_day,
        }
    finally:
        port_browser.close()
        turn_browser.close()
        port_host.__exit__(None, None, None)
        turn_host.__exit__(None, None, None)
        pw.stop()


def test_enemy_ship_shows_in_the_sector_and_here(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.wait_for_function("() => /Ferrengi Assault Trader/.test(document.querySelector('#sectorText').textContent || '')", timeout=10_000)
    text = port.locator("#sectorText").inner_text()
    assert "Ferrengi Assault Trader" in text and "90" in text
    here = port.locator("[data-ships=here]").inner_text()
    assert "Ferrengi Assault Trader" in here and "90" in here
    _shoot(port, "ships", "[data-ships=here]")


def test_attack_form_names_the_ship_and_caps_the_fighters(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("a")
    port.wait_for_selector(".frm [data-n=target]", timeout=10_000)
    label = port.locator(".frm [data-n=target] option").first.inner_text()
    assert "Ferrengi Assault Trader" in label
    assert "ferr_d1" not in label
    assert "90" in label
    cap = port.locator(".frm [data-n=qty]").get_attribute("data-cap")
    aboard = port.locator("#shipStats").inner_text()
    assert cap == "20"
    assert "20" in aboard


def test_no_turns_left_is_not_waiting(seats) -> None:
    turn = seats["turn"]
    _quiet(turn)
    assert turn.locator("#waitchip").inner_text() == "NO TURNS"
    assert "off" in (turn.locator("#keys button[data-key=M]").get_attribute("class") or "")
    turn.keyboard.press("m")
    turn.wait_for_function("() => /No turns left today/.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)
    assert "Day" in turn.locator("#lastResult").inner_text()


def test_photon_refusal_names_the_hulls_that_can_carry_them(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("c")
    port.keyboard.press("p")
    port.wait_for_function("() => /cannot carry photon missiles/.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)
    text = port.locator("#lastResult").inner_text()
    assert "Missile Frigate" in text and "Imperial StarShip" in text


def test_citadel_card_shows_the_finish_day(seats) -> None:
    port = seats["port"]
    _quiet(port)
    port.keyboard.press("l")
    port.locator("#dangerOk").click()
    port.wait_for_function(
        "(day) => new RegExp('ready day ' + day).test(document.querySelector('#here').textContent || '')",
        arg=seats["finish"], timeout=20_000,
    )
    _shoot(port, "citadel", ".planet")
    port.keyboard.press("q")
    port.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)


def test_plotted_course_log_starts_at_the_origin(seats) -> None:
    port = seats["port"]
    _quiet(port)
    origin = seats["origin"]
    beyond = seats["beyond"]
    port.keyboard.press("c")
    port.keyboard.press("f")
    port.locator("#sectorAsk").fill(str(beyond))
    port.keyboard.press("Enter")
    port.wait_for_function(
        "(origin) => new RegExp('plotted course ' + origin + ' >').test(document.querySelector('#lastResult').textContent || '')",
        arg=origin, timeout=20_000,
    )
    port.locator("button.eng").click()
    port.wait_for_function("() => /^ok —/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    log = port.locator("#log").inner_text()
    assert f"plotted course {origin} >" in log
    assert f"plotted course {beyond} >" not in log


def test_overnight_tax_shows_on_the_status_screen(seats) -> None:
    port = seats["port"]
    me = seats["universe"].players["P2"]
    me.credits = 200_000
    collect_daily_tax(seats["universe"])
    port.wait_for_selector("[data-tax=overnight]", timeout=15_000)
    port.keyboard.press("v")
    port.wait_for_function("() => /Overnight Federation tax/.test(document.querySelector('#menu').textContent || '')", timeout=10_000)
    text = port.locator("#menu").inner_text()
    assert "alignment +" in text
    _shoot(port, "tax", "#menu")
