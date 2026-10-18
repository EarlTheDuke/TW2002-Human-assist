"""NOTE 63 combat-message-clarity-v1: the boarding prompt, the attacker's kill line and a replaced queued action say what really happens."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine.ferrengi import _make_ferrengi, apply_ferrengi_tribute, open_ferrengi_encounter
from tw2k.engine.models import Commodity

from tests._cu_host import CuHost

TOK = "note63-clarity-token-p2-0000000000"
TOK1 = "note63-clarity-token-p1-0000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "combat-message-clarity-v1"
PROMPT = "surrender costs 5 cargo holds and all your cargo; with empty holds, 5 cargo holds and 10% of the credits on board"


def _open(browser, host, token, seat):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat={seat}&token={token}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    return page


def _shoot(page, stem: str, selector: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, name in ((1920, "1920"), (390, "390")):
        page.set_viewport_size({"width": width, "height": 844 if width == 390 else 1080})
        page.wait_for_timeout(80)
        page.evaluate(
            "(sel) => { const el = document.querySelector(sel); if (el) el.scrollIntoView({ block: 'center' }); }",
            selector,
        )
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _mine(page) -> bool:
    return page.locator("#waitchip").inner_text() == "YOUR MOVE"


def _your_move(page) -> None:
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=25_000)


def _wait(page, host, pid: str) -> None:
    streak = getattr(host.runner, "_wait_streak", None)
    if isinstance(streak, dict):
        streak[pid] = 0
    page.evaluate("() => { if (window.__tw2kTest) window.__tw2kTest.resetWaits(); }")
    page.keyboard.press("Escape")
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)


def _move(universe, pid: str, sector_id: int) -> None:
    player = universe.players[pid]
    origin = universe.sectors[player.sector_id]
    if pid in origin.occupant_ids:
        origin.occupant_ids.remove(pid)
    player.sector_id = int(sector_id)
    player.planet_landed = None
    dest = universe.sectors[player.sector_id]
    if pid not in dest.occupant_ids:
        dest.occupant_ids.append(pid)


def _plant(universe, pid: str = "P2", fid: str = "note63a"):
    me = universe.players[pid]
    ferr = _make_ferrengi(universe, fid=fid, sid=int(me.sector_id), aggression=8)
    ferr.name = "Ferrengi Battle Cruiser " + fid
    ferr.fighters = 300
    universe.ferrengi[ferr.id] = ferr
    open_ferrengi_encounter(universe, ferr, me)
    return ferr


def _turn_to(pages, host, want: str) -> None:
    other = "P1" if want == "P2" else "P2"
    for _ in range(80):
        if _mine(pages[want]):
            return
        if _mine(pages[other]):
            _wait(pages[other], host, other)
            continue
        pages[want].wait_for_timeout(250)
    raise AssertionError(f"{want} never reached YOUR MOVE")


@pytest.fixture
def duel(tmp_path):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    host = CuHost(tmp_path, TOK, p1_token=TOK1, max_days=6, turns_per_day=30)
    host.__enter__()
    browser = pw.chromium.launch()
    pages = {"P1": _open(browser, host, TOK1, "P1"), "P2": _open(browser, host, TOK, "P2")}
    universe = host.runner.state.universe
    sector = universe.sectors[40]
    sector.fighters = None
    sector.mines = []
    for pid in ("P1", "P2"):
        _move(universe, pid, 40)
        ship = universe.players[pid].ship
        for good in list(ship.cargo):
            ship.cargo[good] = 0
        ship.shields = 0
        universe.players[pid].credits = 300
    try:
        yield {"pages": pages, "universe": universe, "host": host}
    finally:
        browser.close()
        host.__exit__(None, None, None)
        pw.stop()


def test_the_boarding_prompt_matches_what_the_tribute_takes(duel):
    """D15 P2-1: 'surrender costs 5 cargo holds, or 10% of the credits on board', then ignoring it took 5 holds and 30 cr."""
    pages, universe, host = duel["pages"], duel["universe"], duel["host"]
    assert K.FERRENGI_ENGAGE_MODE == "legacy"
    _turn_to(pages, host, "P2")
    page = pages["P2"]
    me = universe.players["P2"]
    holds = int(me.ship.holds)
    _plant(universe)
    page.wait_for_function("(want) => (document.querySelector('#log').textContent || '').includes(want)", arg=PROMPT, timeout=15_000)
    log = page.locator("#log").inner_text()
    assert "5 cargo holds, or 10%" not in log
    _shoot(page, "board", "#log")
    _wait(page, host, "P2")
    _turn_to(pages, host, "P2")
    page.wait_for_function(
        "() => /You ignored the Ferrengi Battle Cruiser note63a/.test(document.querySelector('#lastResult').textContent || '')",
        timeout=20_000,
    )
    text = page.locator("#lastResult").inner_text()
    assert "it took 5 cargo holds and 30 cr" in text, text
    assert int(me.ship.holds) == holds - 5 and int(me.credits) == 270
    _shoot(page, "ignored", "#lastResult")
    me.ship.cargo[Commodity.FUEL_ORE] = 7
    _plant(universe, fid="note63b")
    took = apply_ferrengi_tribute(universe, "P2", ignored=True)
    assert took["cargo"] == {"fuel_ore": 7} and took["holds_stolen"] == 5 and took["credits"] == 0
    assert int(me.credits) == 270


def test_the_attacker_line_shows_the_tribute_once(duel):
    """D15 P3-2: the killer's line ended 'it took 5 cargo holds and 30 cr. Credits on board lost: 30 cr.'; the killer lost no ship."""
    pages, universe, host = duel["pages"], duel["universe"], duel["host"]
    me, rival = universe.players["P2"], universe.players["P1"]
    me.ship.fighters, rival.ship.fighters = 40, 1
    _turn_to(pages, host, "P2")
    page = pages["P2"]
    _plant(universe)
    page.wait_for_function("() => /Ferrengi Fighter Attack/.test(document.querySelector('#log').textContent || '')", timeout=15_000)
    page.wait_for_timeout(2_500)
    previous = page.locator("#lastResult").inner_text()
    page.keyboard.press("Escape")
    page.locator("[data-key=A]").click()
    page.wait_for_selector(".frm", timeout=8_000)
    page.locator(".frm select").evaluate(
        """(el, name) => {
          const hit = [...el.options].find((o) => new RegExp(name, 'i').test(o.textContent || ''));
          el.value = hit ? hit.value : el.options[0].value;
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        rival.name,
    )
    page.locator(".frm input[type=number]").evaluate("(el) => { el.value = '40'; }")
    page.locator(".frm button", has_text="CONFIRM").click()
    page.wait_for_function(
        "(old) => { const t = document.querySelector('#lastResult').textContent || ''; return t !== old && /ship destroyed/i.test(t) && /You ignored/.test(t); }",
        arg=previous,
        timeout=20_000,
    )
    text = page.locator("#lastResult").inner_text()
    assert "it took 5 cargo holds and 30 cr" in text, text
    assert "Credits on board lost" not in text, text
    assert text.count("30 cr") == 1, text
    _shoot(page, "killer", "#lastResult")
    victim = pages["P1"]
    _turn_to(pages, host, "P1")
    victim.wait_for_function(
        "() => { const t = document.querySelector('#lastResult').textContent || ''; return /attacked you in 40/.test(t) && /ship destroyed/i.test(t); }",
        timeout=20_000,
    )
    heard = victim.locator("#lastResult").inner_text()
    assert "Credits on board lost: 300 cr" in heard, heard
    _shoot(victim, "victim", "#lastResult")


def test_a_new_queued_action_says_it_replaces_the_old_one(duel):
    """D15 P3-3: a queued attack, then a queued warp; the attack never ran and nothing said it was dropped."""
    pages, universe, host = duel["pages"], duel["universe"], duel["host"]
    me, rival = universe.players["P2"], universe.players["P1"]
    me.ship.fighters, rival.ship.fighters = 20, 5
    _turn_to(pages, host, "P2")
    page = pages["P2"]
    page.wait_for_timeout(2_500)
    _wait(page, host, "P2")
    _your_move(pages["P1"])
    page.locator("[data-key=A]").click()
    page.wait_for_selector(".frm", timeout=8_000)
    page.locator(".frm select").evaluate(
        """(el, name) => {
          const hit = [...el.options].find((o) => new RegExp(name, 'i').test(o.textContent || ''));
          el.value = hit ? hit.value : el.options[0].value;
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        rival.name,
    )
    page.locator(".frm input[type=number]").evaluate("(el) => { el.value = '1'; }")
    page.locator(".frm button", has_text="CONFIRM").click()
    page.wait_for_function("() => /^Attack will run when your turn comes\\.$/.test((document.querySelector('#lastResult').textContent || '').trim())", timeout=8_000)
    warps = page.locator("#warps button")
    assert warps.count() >= 2
    first = warps.nth(0)
    first_id = re.match(r"\d+:(\d+)", first.inner_text().strip()).group(1)
    first.click()
    text = page.locator("#lastResult").inner_text()
    assert text == f"Warp to {first_id} will run when your turn comes. This replaces your queued attack.", text
    _shoot(page, "replaced", "#lastResult")
    first.click()
    assert page.locator("#lastResult").inner_text() == f"Warp to {first_id} will run when your turn comes."
    second = warps.nth(1)
    second_id = re.match(r"\d+:(\d+)", second.inner_text().strip()).group(1)
    second.click()
    text = page.locator("#lastResult").inner_text()
    assert text == f"Warp to {second_id} will run when your turn comes. This replaces your queued warp to {first_id}.", text
    _wait(pages["P1"], host, "P1")
    page.wait_for_function(
        "(want) => (document.querySelector('#lastResult').textContent || '').startsWith('ok') && (document.querySelector('#lastResult').textContent || '').includes(want)",
        arg=second_id,
        timeout=20_000,
    )
    assert int(me.sector_id) == int(second_id)
    assert int(rival.ship.fighters) == 5 and int(me.ship.fighters) == 20
    assert "will run" not in page.locator("#lastResult").inner_text()
