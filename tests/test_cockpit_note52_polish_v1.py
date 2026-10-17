"""NOTE 53. Planet keys stay on the planet after a landing. One fighter stays singular."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tw2k.engine.ferrengi import _make_ferrengi, open_ferrengi_encounter
from tw2k.engine.models import Commodity

from tests._cu_host import CuHost

TOK = "note52-polish-token-p2-00000000000"
TOK1 = "note52-polish-token-p1-00000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "note52-polish-v1"


def _page(pw, host, token, seat):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat={seat}&token={token}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    return browser, page


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


def _your_move(page) -> None:
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=25_000)


def _next(page, host, mutate=None) -> None:
    streak = getattr(host.runner, "_wait_streak", None)
    if isinstance(streak, dict):
        streak["P2"] = 0
    page.evaluate("() => { if (window.__tw2kTest) window.__tw2kTest.resetWaits(); }")
    page.keyboard.press("Escape")
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    if mutate:
        mutate()
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=25_000)


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


@pytest.fixture
def world(tmp_path):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    host = CuHost(tmp_path, TOK, max_days=8)
    host.__enter__()
    browser, page = _page(pw, host, TOK, "P2")
    _your_move(page)
    try:
        yield {"page": page, "universe": host.runner.state.universe, "host": host}
    finally:
        browser.close()
        host.__exit__(None, None, None)
        pw.stop()


def test_f_after_an_ignored_boarding_opens_the_planet_form(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]

    def place() -> None:
        planet = next(iter(universe.planets.values()))
        old = universe.sectors.get(planet.sector_id)
        if old is not None and planet.id in getattr(old, "planet_ids", []):
            old.planet_ids.remove(planet.id)
        planet.sector_id = int(me.sector_id)
        planet.owner_id = "P2"
        planet.name = "Shield Rock"
        planet.fighters = 0
        planet.shields = 0
        if planet.id not in universe.sectors[me.sector_id].planet_ids:
            universe.sectors[me.sector_id].planet_ids.append(planet.id)

    _next(page, world["host"], place)
    me.ship.cargo[Commodity.FUEL_ORE] = 10
    ferr = _make_ferrengi(universe, fid="note53dread", sid=int(me.sector_id), aggression=8)
    ferr.name = "Dreadnought"
    ferr.fighters = 400
    universe.ferrengi[ferr.id] = ferr
    open_ferrengi_encounter(universe, ferr, me)
    page.locator("#here button", has_text="Shield Rock").click()
    page.locator("#dangerOk").click()
    page.wait_for_function(
        "() => /landed/i.test(document.querySelector('#lastResult').textContent || '') && /You ignored/.test(document.querySelector('#lastResult').textContent || '')",
        timeout=20_000,
    )
    page.keyboard.press("F")
    page.wait_for_selector(".frm [data-n=kind]", timeout=10_000)
    form = page.locator(".frm").inner_text()
    assert "In this sector" not in form
    _shoot(page, "planet", ".frm")


def test_one_fighter_stays_singular(tmp_path):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    host = CuHost(tmp_path, TOK, p1_token=TOK1, max_days=6, turns_per_day=30)
    host.__enter__()
    browser, first = _page(pw, host, TOK1, "P1")
    second = browser.new_page(viewport={"width": 1440, "height": 900})
    second.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    second.wait_for_selector("#waitchip", timeout=20_000)
    try:
        universe = host.runner.state.universe
        sector = universe.sectors[40]
        sector.fighters = None
        sector.mines = []
        for pid, fighters, shields in (("P1", 41, 0), ("P2", 1, 100)):
            _move(universe, pid, 40)
            universe.players[pid].ship.fighters = fighters
            universe.players[pid].ship.shields = shields
        pages = {"P1": first, "P2": second}

        def ready() -> str:
            for _ in range(40):
                for pid, pg in pages.items():
                    if pg.locator("#waitchip").inner_text() == "YOUR MOVE":
                        return pid
                first.wait_for_timeout(250)
            raise AssertionError("nobody reached YOUR MOVE")

        for _ in range(2):
            pid = ready()
            streak = getattr(host.runner, "_wait_streak", None)
            if isinstance(streak, dict):
                streak[pid] = 0
            pages[pid].evaluate("() => { if (window.__tw2kTest) window.__tw2kTest.resetWaits(); }")
            pages[pid].keyboard.press("Escape")
            pages[pid].keyboard.press(".")
            pages[pid].wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
        actor = ready()
        other = "P2" if actor == "P1" else "P1"
        page = pages[actor]
        previous = page.locator("#lastResult").inner_text()
        page.keyboard.press("Escape")
        page.locator("[data-key=A]").click()
        page.wait_for_selector(".frm", timeout=8_000)
        page.locator(".frm select").evaluate(
            """(el, name) => {
              const hit = [...el.options].find((o) => new RegExp(name, 'i').test(o.textContent || ''));
              el.value = hit ? hit.value : el.options[0].value;
            }""",
            universe.players[other].name,
        )
        page.locator(".frm input[type=number]").evaluate("(el) => { el.value = '40'; }")
        page.locator(".frm button", has_text="CONFIRM").click()
        page.wait_for_function(
            "() => { const now = document.querySelector('#lastResult').textContent || ''; return now !== "
            + json.dumps(previous)
            + " && /remain/.test(now); }",
            timeout=20_000,
        )
        text = page.locator("#lastResult").inner_text()
        log = page.locator("#log").inner_text()
        victim = pages[other]
        _your_move(victim)
        heard = victim.locator("#lastResult").inner_text()
        blob = text + "\n" + heard + "\n" + log
        assert not re.search(r"\b1 fighters\b", blob), blob
        assert not re.search(r"\b1 shields\b", blob), blob
        assert re.search(r"\b1 fighter\b", blob), blob
        _shoot(page, "one", "#lastResult")
        _shoot(victim, "singular", "#lastResult")
    finally:
        browser.close()
        host.__exit__(None, None, None)
        pw.stop()
