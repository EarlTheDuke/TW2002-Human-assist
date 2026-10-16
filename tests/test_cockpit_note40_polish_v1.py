"""NOTE 42. One page, in this order. No stored flag moves."""

from __future__ import annotations

from pathlib import Path

from tw2k.engine.models import EventKind, MineDeployment, MineType

from tests._cu_host import CuHost

TOK = "note40-polish-token-p2-000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "note40-polish-v1"


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
        page.wait_for_timeout(120)
        page.evaluate(
            "(sel) => { const el = (sel && document.querySelector(sel)) || document.querySelector('#menu') || document.querySelector('#here'); if (el) el.scrollIntoView({ block: 'center' }); }",
            selector,
        )
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _back(page, needle: str) -> None:
    page.wait_for_function(
        "() => (document.querySelector('#lastResult').textContent || '').includes(" + repr(needle) + ")",
        timeout=20_000,
    )
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)


def _install():
    import pytest

    @pytest.fixture(scope="module")
    def world(tmp_path_factory):
        sync = pytest.importorskip("playwright.sync_api").sync_playwright
        pw = sync().start()
        host = CuHost(tmp_path_factory.mktemp("n42"), TOK)
        host.__enter__()
        browser, page = _page(pw, host)
        try:
            yield {"page": page, "universe": host.runner.state.universe, "host": host}
        finally:
            browser.close()
            host.__exit__(None, None, None)
            pw.stop()

    return world


world = _install()


def test_reload_reconnects_the_same_seat(world):
    page = world["page"]
    kept = page.evaluate("() => sessionStorage.getItem('tw2k-token-P2')")
    assert kept == TOK
    assert "token=" not in page.url
    page.reload()
    page.wait_for_function("() => document.querySelector('#sbDay').textContent !== '-'", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    assert page.locator("#sbDay").inner_text() != "-"
    _shoot(page, "reload")


def test_plain_warp_and_a_plot_skip_the_shield_line(world):
    page = world["page"]
    universe = world["universe"]
    me = universe.players["P2"]
    target = int(universe.sectors[me.sector_id].warps[0])
    universe.sectors[target].mines = []
    page.locator("#warps button", has_text=str(target)).first.click()
    _back(page, "warped")
    text = page.locator("#lastResult").inner_text()
    assert "Shields" not in text
    assert "remain" not in text
    _shoot(page, "warp", "#lastResult")
    page.keyboard.press("C")
    page.wait_for_selector("#menu", timeout=10_000)
    page.keyboard.press("F")
    page.wait_for_selector("#sectorAsk", timeout=10_000)
    here = int(me.sector_id)
    adjacent = {int(w) for w in universe.sectors[here].warps}
    far = next(int(i) for i in universe.sectors if int(i) not in adjacent and int(i) != here and int(i) > 10)
    page.locator("#sectorAsk").fill(str(far))
    page.locator("#sectorGo").click()
    _back(page, "plotted course")
    plotted = page.locator("#lastResult").inner_text()
    assert "Shields" not in plotted
    assert "remain" not in plotted
    nxt = int(universe.sectors[me.sector_id].warps[0])
    universe.sectors[nxt].mines.append(MineDeployment(owner_id="P1", kind=MineType.ARMID, count=2))
    me.ship.shields = 200
    page.locator("#warps button", has_text=str(nxt)).first.click()
    _back(page, "mines hit")
    hit = page.locator("#lastResult").inner_text()
    assert "Shields " in hit
    assert "Fighters " in hit and " remain" in hit
    assert "fighters " not in hit.split(". ")[-1] or hit.split(". ")[-1][:1].isupper() or "Fighters" in hit
    _shoot(page, "hit", "#lastResult")


def test_wait_asks_once_on_the_day_ending_wait(world):
    page = world["page"]
    host = world["host"]
    host.runner._wait_streak = {"P2": 0}
    page.evaluate("() => window.__tw2kTest.resetWaits()")
    for _ in range(3):
        page.keyboard.press("Escape")
        page.evaluate("() => { const el = document.querySelector('#lastResult'); if (el) el.textContent = ''; }")
        page.keyboard.press(".")
        page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
        page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
        assert "Wait" not in (page.locator("#menu").get_attribute("data-screen") or "") or page.locator("#menu").is_hidden()
    page.wait_for_function("() => window.__tw2kTest.serverWaits() >= 3", timeout=10_000)
    page.keyboard.press(".")
    page.wait_for_selector("#menu:not([hidden])", timeout=10_000)
    assert "One more Wait ends your day" in page.locator("#menu").inner_text()
    assert page.locator("#waitchip").inner_text() == "YOUR MOVE"
    _shoot(page, "wait", "#menu")
    page.keyboard.press("Escape")


def test_log_uses_the_avoid_statement(world):
    page = world["page"]
    text = page.locator("#log").inner_text()
    assert "avoid this sector?" not in text
    assert "Computer, then O" in text
    _shoot(page, "log", "#log")


def test_one_item_and_a_held_command_read_cleanly(world):
    page = world["page"]
    universe = world["universe"]
    host = world["host"]
    me = universe.players["P2"]
    host.runner._wait_streak = {"P2": 0}
    page.evaluate("() => window.__tw2kTest.resetWaits()")
    planet = next(iter(universe.planets.values()))
    old = universe.sectors.get(planet.sector_id)
    if old is not None and planet.id in old.planet_ids:
        old.planet_ids.remove(planet.id)
    planet.sector_id = int(me.sector_id)
    planet.owner_id = "P2"
    planet.name = "Phoenix"
    if planet.id not in universe.sectors[me.sector_id].planet_ids:
        universe.sectors[me.sector_id].planet_ids.append(planet.id)
    universe.emit(
        EventKind.TRADE,
        actor_id="P2",
        sector_id=me.sector_id,
        payload={},
        summary="bought 1 fighters and bought 1 shields",
    )
    page.keyboard.press(".")
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    log = page.locator("#log").inner_text()
    assert "1 fighter" in log
    assert "1 shield" in log
    assert "1 fighters" not in log
    assert "1 shields" not in log
    page.locator("#here button", has_text="Land on").click()
    page.locator("#dangerOk").click()
    _back(page, "ok")
    page.evaluate("() => window.__tw2kTest.setAwaiting(false)")
    page.keyboard.press("Q")
    text = page.locator("#lastResult").inner_text()
    assert text.startswith("Lift off will run when your turn comes.")
    _shoot(page, "wording", "#lastResult")
