"""NOTE 51. The growth switch is on only inside a test and put back."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine.models import Commodity, PlanetClass
from tw2k.engine.planets import _complete_citadels

from tests._cu_host import CuHost

TOK = "note50-polish-token-p2-00000000000"
TOK1 = "note50-polish-token-p1-00000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "note50-polish-v1"


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


def _next(page, host) -> None:
    host.runner._wait_streak = {"P2": 0}
    page.evaluate("() => { if (window.__tw2kTest) window.__tw2kTest.resetWaits(); }")
    page.keyboard.press("Escape")
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)


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


def _your_move(page) -> None:
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=25_000)


@pytest.fixture
def world(tmp_path):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    pw = sync().start()
    host = CuHost(tmp_path, TOK, max_days=12)
    host.__enter__()
    browser, page = _page(pw, host, TOK, "P2")
    _your_move(page)
    try:
        yield {"page": page, "universe": host.runner.state.universe, "host": host, "pw": pw}
    finally:
        K.PLANET_GROWTH_MODE = "legacy"
        browser.close()
        host.__exit__(None, None, None)
        pw.stop()


def test_the_half_cap_line_shows_only_when_the_switch_is_on(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    planet = next(iter(universe.planets.values()))
    old = universe.sectors.get(planet.sector_id)
    if old is not None and planet.id in getattr(old, "planet_ids", []):
        old.planet_ids.remove(planet.id)
    planet.sector_id = int(me.sector_id)
    planet.owner_id = "P2"
    planet.class_id = PlanetClass.M
    planet.fighters = 0
    planet.shields = 0
    planet.name = "Phoenix"
    planet.colonists[Commodity.ORGANICS] = 2500
    if planet.id not in universe.sectors[me.sector_id].planet_ids:
        universe.sectors[me.sector_id].planet_ids.append(planet.id)
    _next(page, world["host"])
    page.locator("#here button", has_text="Phoenix").click()
    page.locator("#dangerOk").click()
    page.wait_for_function(
        "() => (document.querySelector('#lastResult').textContent || '').toLowerCase().includes('land')",
        timeout=20_000,
    )
    assert page.locator("[data-colonists=trend]").count() == 0
    from tw2k.engine.observation import build_observation
    owned = build_observation(universe, "P2").owned_planets
    assert all("colonists_text" not in row for row in owned)
    K.PLANET_GROWTH_MODE = "tw2002"
    _next(page, world["host"])
    text = page.locator("[data-colonists=trend]").inner_text()
    assert text == "below half the class cap (30,000), about 5% more each day"
    _shoot(page, "below", "[data-colonists=trend]")
    planet.colonists[Commodity.ORGANICS] = 20_000
    _next(page, world["host"])
    above = page.locator("[data-colonists=trend]").inner_text()
    assert above == "above half the class cap (30,000), about 5% die off each day"
    _shoot(page, "above", "[data-colonists=trend]")


def _open_build(page) -> str:
    page.keyboard.press("Escape")
    page.locator("#here button", has_text="Build citadel").click()
    page.wait_for_selector("#menu", timeout=10_000)
    return page.locator("#menu").inner_text()


def _finish_build(universe, planet) -> None:
    universe.day = int(planet.citadel_complete_day)
    _complete_citadels(universe)


def test_a_citadel_climbs_from_level_1_to_level_3(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    planet = next(iter(universe.planets.values()))
    old = universe.sectors.get(planet.sector_id)
    if old is not None and planet.id in getattr(old, "planet_ids", []):
        old.planet_ids.remove(planet.id)
    planet.sector_id = int(me.sector_id)
    planet.owner_id = "P2"
    planet.class_id = PlanetClass.M
    planet.name = "Phoenix"
    planet.fighters = 0
    planet.shields = 0
    if planet.id not in universe.sectors[me.sector_id].planet_ids:
        universe.sectors[me.sector_id].planet_ids.append(planet.id)
    for mode in ("legacy", "tw2002"):
        K.PLANET_GROWTH_MODE = mode
        planet.citadel_level = 1
        planet.citadel_target = 0
        planet.citadel_complete_day = None
        planet.colonists[Commodity.ORGANICS] = 5000
        for level in (2, 3):
            cols, fuel, organics, equipment, days = K.citadel_class_cost("M", level)
            planet.stockpile[Commodity.FUEL_ORE] = 0
            planet.stockpile[Commodity.ORGANICS] = organics
            planet.stockpile[Commodity.EQUIPMENT] = equipment
            if me.planet_landed != planet.id:
                _next(page, world["host"])
                page.locator("#here button", has_text="Phoenix").click()
                page.locator("#dangerOk").click()
                page.wait_for_function(
                    "() => (document.querySelector('#lastResult').textContent || '').toLowerCase().includes('land')",
                    timeout=20_000,
                )
            else:
                _next(page, world["host"])
            short = _open_build(page)
            assert "Short: fuel ore" in short
            assert f"{fuel:,}" in short or str(fuel) in short
            page.locator("#dangerOk").click()
            assert int(planet.citadel_target or 0) <= int(planet.citadel_level)
            planet.stockpile[Commodity.FUEL_ORE] = fuel
            _next(page, world["host"])
            ready = _open_build(page)
            assert "Short:" not in ready
            assert f"{days} day" in ready
            assert "Ready day" in ready
            assert f"(have {fuel:,})" in ready or f"(have {fuel})" in ready
            if level == 2 and mode == "legacy":
                _shoot(page, "build", "#menu")
            page.locator("#dangerOk").click()
            page.wait_for_function(
                "() => /began|citadel/i.test(document.querySelector('#lastResult').textContent || '')",
                timeout=20_000,
            )
            page.wait_for_function(
                "() => ((document.querySelector('[data-citadel=level]') || {}).textContent || '').includes('building toward "
                + str(level)
                + "')",
                timeout=20_000,
            )
            card = page.locator("[data-citadel=level]").inner_text()
            assert f"building toward {level}" in card
            assert "ready day" in card.lower()
            _finish_build(universe, planet)
            _next(page, world["host"])
            done = page.locator("[data-citadel=level]").inner_text()
            assert f"level {level}" in done
            perk = page.locator("[data-perk=now]").inner_text()
            assert ("Combat Control Computer" if level == 2 else "Quasar cannon") in perk
            if level == 3 and mode == "tw2002":
                _shoot(page, "citadel", "[data-citadel=level]")


def test_two_cockpits_fight_outside_fedspace(tmp_path):
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
        for pid, fighters, shields in (("P1", 200, 0), ("P2", 200, 0)):
            _move(universe, pid, 40)
            ship = universe.players[pid].ship
            ship.fighters = fighters
            ship.shields = shields
            universe.players[pid].experience = 1000
            universe.players[pid].alignment = 100
        pages = {"P1": first, "P2": second}

        def ready() -> str:
            for _ in range(40):
                for pid, pg in pages.items():
                    if pg.locator("#waitchip").inner_text() == "YOUR MOVE":
                        return pid
                first.wait_for_timeout(250)
            raise AssertionError("nobody reached YOUR MOVE")

        def spend_wait(pid: str) -> None:
            streak = getattr(host.runner, "_wait_streak", None)
            if isinstance(streak, dict):
                streak[pid] = 0
            pages[pid].evaluate("() => { if (window.__tw2kTest) window.__tw2kTest.resetWaits(); }")
            pages[pid].keyboard.press("Escape")
            pages[pid].keyboard.press(".")
            pages[pid].wait_for_function(
                "() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'",
                timeout=20_000,
            )

        for _ in range(2):
            spend_wait(ready())
        for pid, fighters, shields in (("P1", 200, 0), ("P2", 200, 0)):
            universe.players[pid].ship.fighters = fighters
            universe.players[pid].ship.shields = shields
        for _ in range(2):
            spend_wait(ready())
        start = {pid: (int(universe.players[pid].experience), int(universe.players[pid].alignment)) for pid in ("P1", "P2")}
        lost = None
        traded = {"P1": False, "P2": False}
        for _ in range(6):
            actor = ready()
            other = "P2" if actor == "P1" else "P1"
            page = pages[actor]
            before = {
                actor: (int(universe.players[actor].ship.fighters), int(universe.players[actor].ship.shields)),
                other: (int(universe.players[other].ship.fighters), int(universe.players[other].ship.shields)),
            }
            df, ds = before[other]
            if traded["P1"] and traded["P2"] and before[actor][0] >= df + ds > 0:
                qty = df + ds
            else:
                qty = min(40, before[actor][0])
            page.keyboard.press("Escape")
            page.locator("[data-key=A]").click()
            try:
                page.wait_for_selector(".frm", timeout=8_000)
            except Exception as exc:
                raise AssertionError(page.locator("#lastResult").inner_text()) from exc
            page.locator(".frm select").evaluate(
                """(el, name) => {
                  const hit = [...el.options].find(o => new RegExp(name, 'i').test(o.textContent || ''));
                  el.value = hit ? hit.value : el.options[0].value;
                  el.dispatchEvent(new Event('change', { bubbles: true }));
                }""",
                universe.players[other].name,
            )
            page.locator(".frm input[type=number]").evaluate(
                "(el, n) => { el.value = String(n); }",
                qty,
            )
            previous = page.locator("#lastResult").inner_text()
            page.locator(".frm button", has_text="CONFIRM").click()
            page.wait_for_function(
                "() => { const now = document.querySelector('#lastResult').textContent || ''; return now !== " + json.dumps(previous) + " && /fighters and/.test(now); }",
                timeout=20_000,
            )
            text = page.locator("#lastResult").inner_text()
            pairs = [(int(a.replace(",", "")), int(b.replace(",", ""))) for a, b in re.findall(r"lost ([\d,]+) fighters and ([\d,]+) shields", text)]
            assert len(pairs) >= 2
            after = {
                actor: (int(universe.players[actor].ship.fighters), int(universe.players[actor].ship.shields)),
                other: (int(universe.players[other].ship.fighters), int(universe.players[other].ship.shields)),
            }
            gone = "ship destroyed" in text.lower()
            assert pairs[0] == (before[actor][0] - after[actor][0], before[actor][1] - after[actor][1]), text
            if gone:
                assert pairs[1] == before[other]
            else:
                assert pairs[1] == (before[other][0] - after[other][0], before[other][1] - after[other][1])
            traded[actor] = True
            log = page.locator("#log").inner_text()
            assert "fighters" in log and "shields" in log
            victim = pages[other]
            _your_move(victim)
            needle = json.dumps(f"lost {pairs[1][0]} fighters and {pairs[1][1]} shields")
            victim.wait_for_function(
                "() => (document.querySelector('#lastResult').textContent || '').includes(" + needle + ")",
                timeout=20_000,
            )
            heard = victim.locator("#lastResult").inner_text()
            assert "fighters and" in heard and "shields" in heard
            if "ship destroyed" in text or "ship destroyed" in heard:
                lost = other if "ship destroyed" in text else actor
                both = text + "\n" + heard
                assert "escaped in a pod" in both or "ship destroyed" in both
                assert "Credits on board lost" in both
                _shoot(page, "fight", "#lastResult")
                break
        assert lost is not None
        winner = "P2" if lost == "P1" else "P1"
        pages[winner].keyboard.press("v")
        pages[winner].wait_for_function(
            "() => /Experience/.test(document.body.innerText)",
            timeout=10_000,
        )
        panel = pages[winner].locator("body").inner_text()
        exp, align = universe.players[winner].experience, universe.players[winner].alignment
        assert f"{int(exp):,}" in panel or str(int(exp)) in panel
        assert f"{int(align):,}" in panel or str(int(align)) in panel
        assert (int(exp), int(align)) != start[winner]
    finally:
        browser.close()
        host.__exit__(None, None, None)
        pw.stop()
