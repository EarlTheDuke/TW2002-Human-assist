"""NOTE 60 v311-daylen-and-yard-v1 on the redesign cockpit (items 3-7), with the screens.

One page per roster. The v3.11 page runs a 600 s day with 60 turns (a turn every 10 s):
the shipyard on day 1, out of turns, the day-2 roll on the clock, a Citadel L1 built on
day 2 and finished on day 6. The legacy page shows the old roster and the old lines.
Screens: docs/playtests/v311-daylen-and-yard-v1/{1920,390}-*.png.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine.models import Commodity, Planet, PlanetClass

from tests._cu_host import CuHost

TOK = "daylen-token-p2-0000000000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "v311-daylen-and-yard-v1"
DAY_S = 600.0


def _page(browser, host):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    _my_move(page)
    return page


def _my_move(page, timeout=30_000) -> None:
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=timeout)


def _shoot(page, stem: str, selector: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, name in ((1920, "1920"), (390, "390")):
        page.set_viewport_size({"width": width, "height": 1080 if width == 1920 else 844})
        page.wait_for_timeout(200)
        page.evaluate("(sel) => { const el = document.querySelector(sel); if (el) el.scrollIntoView({ block: 'center' }); }", selector)
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _wait_then(page, mutate) -> None:
    """Spend one WAIT, then change the world before the seat's next observation."""
    page.keyboard.press("Escape")
    page.keyboard.press(".")
    confirm = page.locator("#dangerOk")
    if confirm.count() and confirm.is_visible():
        confirm.click()
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    mutate()


def _out_of_turns(u) -> None:
    p2 = u.players["P2"]
    p2.turns_today = p2.turns_per_day
    p2.turn_regen_at, p2.turn_regen_frac = time.time(), 0.0


def _roll(host, day: int) -> None:
    """Move the server's day mark back one day length: the loop rolls on its clock."""
    u = host.runner.state.universe
    _out_of_turns(u)  # a resting seat; the roll does not wait for anyone
    host.runner._live_day_mark -= DAY_S
    deadline = time.time() + 15
    while u.day < day and time.time() < deadline:
        time.sleep(0.05)
    assert u.day == day, (u.day, day)


def _open_yard(page) -> str:
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Shipyards").first.click()
    sel = page.locator('#formSlot select[data-n="ship_class"]')
    sel.wait_for(timeout=10_000)
    sel.select_option("scout_marauder")
    page.wait_for_timeout(150)
    return page.locator('[data-yard="deal"]').inner_text()


def _to_stardock(u) -> None:
    """Move P2 onto the universe's StarDock: v3.11 draws its sector, so it is not always 1."""
    p2, sid = u.players["P2"], K.stardock_sector_of(u)
    u.sectors[p2.sector_id].occupant_ids.remove("P2")
    p2.sector_id = sid
    u.sectors[sid].occupant_ids.append("P2")
    p2.known_sectors.add(sid)


def _list_box(page) -> list[dict]:
    # A native drop-down does not show in a screenshot, so the shot opens it as a list.
    page.evaluate("""() => { const s = document.querySelector('#formSlot select[data-n="ship_class"]');
        s.size = s.options.length; }""")
    return page.evaluate("""() => [...document.querySelectorAll('#formSlot select[data-n="ship_class"] option')]
        .map((o) => ({ value: o.value, text: o.textContent, disabled: o.disabled }))""")


@pytest.fixture(scope="module")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception as exc:
            pytest.skip(f"chromium not available: {exc}")
        yield b
        b.close()


def test_v311_cockpit_yard_turns_day_roll_and_citadel(browser, tmp_path) -> None:
    _prior_v311_profile = K.V311_PROFILE
    try:
        saved = K.V311_PROFILE
        try:
            K.V311_PROFILE = "v311"
            with CuHost(tmp_path, TOK, max_days=9, turns_per_day=60, park_at=K.STARDOCK_SECTOR,
                        day_seconds=DAY_S) as host:
                u = host.runner.state.universe
                assert float(K.TURN_REGEN_DAY_SECONDS) == DAY_S
                page = _page(browser, host)
                _wait_then(page, lambda: (_to_stardock(u), setattr(u.players["P2"], "credits", 40_000)))
                _my_move(page)

                # Items 5 and 6: the v3.11 roster from the server, every hull, the unaffordable grey.
                deal = _open_yard(page)
                assert "Scout Marauder" in deal and "Holds 10 of 25, fighters 250" in deal, deal
                _shoot(page, "scout-v311", '[data-yard="deal"]')
                options = _list_box(page)
                assert len(options) == len(K.ship_specs())  # every buyable hull of the roster
                assert all(re.search(r" - [\d,]+ cr", o["text"]) for o in options), options
                grey = [o for o in options if o["disabled"]]
                assert grey and all("(" in o["text"] for o in grey)
                assert not any(o["value"] == "scout_marauder" for o in grey)
                assert "Waiting for your turn" not in " ".join(o["text"] for o in options)
                _shoot(page, "yard-list-v311", '#formSlot select[data-n="ship_class"]')

                # Item 4: out of turns, with the server's next-turn ETA and next-day time.
                _wait_then(page, lambda: _out_of_turns(u))
                page.wait_for_function("() => document.querySelector('#tl').textContent === '0'", timeout=20_000)
                page.keyboard.press("M")
                line = page.locator("#lastResult").inner_text()
                assert re.search(r"No turns left\. Next turn in about \d+ s \([^)]+\)\. Day 2 starts at [^.]+\.", line), line
                _shoot(page, "no-turns-v311", "#lastResult")

                # Item 7 (and item 2): day 2 comes on the clock; turns come back hourly.
                _roll(host, 2)
                page.wait_for_function("() => /Day 2 dawns/.test(document.querySelector('#lastResult').textContent)",
                                       timeout=20_000)
                line = page.locator("#lastResult").inner_text()
                assert re.search(r"Day 2 dawns\. Turns come back a little at a time; you have \d+ of 60\.", line), line
                _shoot(page, "day-roll-v311", "#lastResult")

                # Item 3: Citadel L1 on a class M planet on day 2, ready day 6.
                p2 = u.players["P2"]
                planet = Planet(id=88602, sector_id=K.STARDOCK_SECTOR + 1, name="Yardstick", class_id=PlanetClass.M,
                                owner_id="P2", citadel_level=0, citadel_target=0)

                def land() -> None:
                    sid = next(s for s in sorted(u.sectors) if s > 10 and not u.sectors[s].planet_ids
                               and not u.sectors[s].port)
                    planet.sector_id = sid
                    u.planets[planet.id] = planet
                    u.sectors[sid].planet_ids.append(planet.id)
                    for pool in planet.colonists:
                        planet.colonists[pool] = 0
                    planet.colonists[Commodity.COLONISTS] = 1_000_000
                    planet.stockpile[Commodity.FUEL_ORE] = 300
                    planet.stockpile[Commodity.ORGANICS] = 200
                    planet.stockpile[Commodity.EQUIPMENT] = 250
                    u.sectors[p2.sector_id].occupant_ids.remove("P2")
                    p2.sector_id, p2.planet_landed = sid, planet.id
                    u.sectors[sid].occupant_ids.append("P2")
                    p2.known_sectors.add(sid)
                    p2.turns_today = 0

                land()  # the seat is resting, so it picks up the landing on its next slot
                _my_move(page, timeout=40_000)
                page.wait_for_selector('[data-citadel="level"]', timeout=20_000)
                page.keyboard.press("B")
                page.wait_for_selector("#dangerOk", state="visible", timeout=10_000)
                quote = page.locator("#menu").inner_text()
                assert "4 days. Ready day 6." in quote, quote
                _shoot(page, "citadel-quote-v311", "#dangerOk")
                page.locator("#dangerOk").click()
                deadline = time.time() + 15
                while planet.citadel_complete_day is None and time.time() < deadline:
                    time.sleep(0.05)
                assert planet.citadel_complete_day == 6 and u.day == 2
                for day in (3, 4, 5, 6):
                    _roll(host, day)
                    if day < 6:
                        assert planet.citadel_level == 0, day
                assert planet.citadel_level == 1
                page.wait_for_function("() => /level 1/.test((document.querySelector('[data-citadel=\"level\"]') || {}).textContent || '')",
                                       timeout=20_000)
                assert "Treasury" in page.locator('[data-perk="now"]').inner_text()
                _shoot(page, "citadel-l1-v311", '[data-citadel="level"]')
                page.close()
        finally:
            K.V311_PROFILE = saved
    finally:
        K.V311_PROFILE = _prior_v311_profile


def test_legacy_cockpit_keeps_the_legacy_roster_and_lines(browser, tmp_path) -> None:
    _prior_yard_stats_mode = K.YARD_STATS_MODE
    try:
        assert K.V311_PROFILE != "v311"
        with CuHost(tmp_path, TOK, max_days=3, turns_per_day=60, park_at=K.STARDOCK_SECTOR) as host:
            u = host.runner.state.universe
            page = _page(browser, host)
            _wait_then(page, lambda: setattr(u.players["P2"], "credits", 40_000))
            _my_move(page)
            # No server figures under legacy: the HULL table is the fallback, with the legacy numbers.
            deal = _open_yard(page)
            assert "Holds 25, fighters 150" in deal, deal
            assert page.evaluate("() => !!document.querySelector('#formSlot select[data-n=\"ship_class\"]')")
            options = _list_box(page)
            assert len(options) == len(K.ship_specs())
            _shoot(page, "yard-list-legacy", '#formSlot select[data-n="ship_class"]')
            # The legacy roster from the server's figures when the yard switch alone is on.
            saved = K.YARD_STATS_MODE
            try:
                K.YARD_STATS_MODE = "live"
                _wait_then(page, lambda: None)
                _my_move(page)
                deal = _open_yard(page)
                assert "Holds 25, fighters 150" in deal, deal
                _shoot(page, "scout-legacy", '[data-yard="deal"]')
            finally:
                K.YARD_STATS_MODE = saved
            # Legacy keeps the old out-of-turns line (no server clock in the observation).
            _wait_then(page, lambda: setattr(u.players["P2"], "turns_today", u.players["P2"].turns_per_day))
            page.wait_for_function("() => document.querySelector('#tl').textContent === '0'", timeout=20_000)
            page.keyboard.press("M")
            line = page.locator("#lastResult").inner_text()
            assert line.startswith("No turns left today. Day "), line
            _shoot(page, "no-turns-legacy", "#lastResult")
            page.close()
    finally:
        K.YARD_STATS_MODE = _prior_yard_stats_mode
