"""Rival strength, a kill-cash switch, and the combat lines on the redesign cockpit.

The browser tests share one page and run in this order. Rival strength and
federal ships are on only here. Kill cash stays the old payment unless the
test turns that switch on.
"""

from __future__ import annotations

from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine.bank import on_ship_lost
from tw2k.engine.models import EventKind, ShipClass

from tests._cu_host import CuHost

TOK = "combat-token-p2-000000000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-combat-clarity-v1"


def _page(pw, host):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=20_000)
    return browser, page


def _shoot(page, stem: str, selector: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, name in ((1920, "1920"), (390, "390")):
        page.set_viewport_size({"width": width, "height": 1080 if width == 1920 else 844})
        page.wait_for_timeout(150)
        page.evaluate("(sel) => { const el = document.querySelector(sel); if (el) el.scrollIntoView({ block: 'center' }); }", selector)
        page.screenshot(path=str(SHOTS / f"{name}-{stem}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def _next(page, mutate=None) -> None:
    page.keyboard.press("Escape")
    page.evaluate("() => { const el = document.querySelector('#lastResult'); if (el) el.textContent = ''; }")
    page.keyboard.press(".")
    confirm = page.locator("#dangerOk")
    if confirm.count() and confirm.is_visible():
        confirm.click()
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    if mutate:
        mutate()
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=30_000)


def _sit(universe, pid: str, sector_id: int) -> None:
    player = universe.players[pid]
    origin = universe.sectors[player.sector_id]
    if pid in origin.occupant_ids:
        origin.occupant_ids.remove(pid)
    player.sector_id = int(sector_id)
    player.planet_landed = None
    dest = universe.sectors[player.sector_id]
    if pid not in dest.occupant_ids:
        dest.occupant_ids.append(pid)
    if pid != "P2":
        player.turns_today = int(player.turns_per_day)


def _install():
    import pytest

    @pytest.fixture(scope="module")
    def world(tmp_path_factory):
        _prior_rival_strength_mode = K.RIVAL_STRENGTH_MODE
        try:
            sync = pytest.importorskip("playwright.sync_api").sync_playwright
            saved = K.RIVAL_STRENGTH_MODE
            K.RIVAL_STRENGTH_MODE = "live"
            pw = sync().start()
            host = CuHost(tmp_path_factory.mktemp("combat"), TOK)
            host.__enter__()
            universe = host.runner.state.universe
            me = universe.players["P2"]
            browser, page = _page(pw, host)
            try:
                yield {"page": page, "universe": universe, "me": me}
            finally:
                browser.close()
                host.__exit__(None, None, None)
                pw.stop()
                K.RIVAL_STRENGTH_MODE = saved
        finally:
            K.RIVAL_STRENGTH_MODE = _prior_rival_strength_mode

    return world


world = _install()


def test_kill_cash_stays_until_the_switch(world, monkeypatch) -> None:
    universe = world["universe"]
    killer = universe.players["P2"]
    victim = universe.players["P1"]
    victim.credits = 1_000
    before = int(killer.credits)
    assert K.KILL_CASH_MODE == "legacy"
    assert K.kill_cash_held() is False
    monkeypatch.setattr(K, "KILL_CASH_MODE", "tw2002")
    lost = on_ship_lost(universe, victim, "P2", True, "merchant_cruiser")
    assert lost == 1_000
    assert killer.credits == before
    assert victim.credits == 0


def test_rival_fighters_and_shields_show_before_the_attack(world) -> None:
    page = world["page"]
    universe = world["universe"]
    home = int(world["me"].sector_id)
    def plant() -> None:
        rival = universe.players["P1"]
        _sit(universe, "P1", home)
        rival.ship.ship_class = ShipClass.MERCHANT_CRUISER
        rival.ship.fighters = 40
        rival.ship.shields = 15

    _next(page, plant)
    page.wait_for_function("() => /40 fighters/.test(document.body.innerText) && /15 shields/.test(document.body.innerText)", timeout=10_000)
    assert "a Merchant Cruiser" in page.locator("#sectorText").inner_text()
    _shoot(page, "rival", "#here")
    page.keyboard.press("a")
    page.wait_for_selector(".frm")
    text = page.locator(".frm").inner_text()
    assert "40 fighters" in text
    assert "15 shields" in text
    assert "1 to" in text
    _shoot(page, "attack", ".frm")
    page.keyboard.press("Escape")


def test_escape_pod_reads_as_an_escape_pod(world) -> None:
    page = world["page"]

    def pod() -> None:
        world["universe"].players["P1"].ship.ship_class = ShipClass.ESCAPE_POD

    _next(page, pod)
    page.wait_for_function("() => /an Escape Pod/.test(document.body.innerText)", timeout=10_000)
    _shoot(page, "pod", "#here")
    world["universe"].players["P1"].ship.ship_class = ShipClass.MERCHANT_CRUISER


def test_a_finished_citadel_names_its_level(world) -> None:
    page = world["page"]
    universe = world["universe"]
    planet = next(iter(universe.planets.values()))

    def land() -> None:
        origin = universe.sectors[planet.sector_id]
        origin.planet_ids = [pid for pid in origin.planet_ids if pid != planet.id]
        planet.sector_id = int(world["me"].sector_id)
        planet.owner_id = "P2"
        planet.citadel_level = 1
        planet.citadel_target = 1
        planet.citadel_complete_day = None
        if planet.id not in universe.sectors[planet.sector_id].planet_ids:
            universe.sectors[planet.sector_id].planet_ids.append(planet.id)
        _sit(universe, "P2", planet.sector_id)
        world["me"].planet_landed = int(planet.id)

    _next(page, land)
    page.wait_for_function("() => /Citadel/.test(document.body.innerText) && /level 1/.test(document.body.innerText)", timeout=10_000)
    assert "building toward" not in page.locator("body").inner_text()
    _shoot(page, "citadel", ".planet")

    def build() -> None:
        planet.citadel_target = 2
        planet.citadel_complete_day = int(universe.day) + 3

    _next(page, build)
    page.wait_for_function("() => /building toward 2/.test(document.body.innerText) && /ready day/.test(document.body.innerText)", timeout=10_000)


def test_unaffordable_warps_and_engage_stay_grey(world) -> None:
    page = world["page"]

    def short() -> None:
        me = world["me"]
        me.planet_landed = None
        me.turns_today = int(me.turns_per_day) - 2

    _next(page, short)
    page.wait_for_selector("#warps button.dim")
    page.locator("#warps button.dim").first.click()
    page.wait_for_function("() => /out of turns/.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)
    _shoot(page, "warps", "#warps")
    page.keyboard.press("c")
    page.keyboard.press("f")
    page.wait_for_selector("#sectorAsk")
    here = int(world["me"].sector_id)
    adjacent = {int(w) for w in world["universe"].sectors[here].warps}
    far = next(sid for sid in world["universe"].sectors if int(sid) != here and int(sid) not in adjacent)
    page.locator("#sectorAsk").fill(str(far))
    page.locator("#sectorAsk").press("Enter")
    page.wait_for_selector("button.eng", timeout=20_000)
    assert "dim" in (page.locator("button.eng").get_attribute("class") or "")
    page.locator("button.eng").click()
    page.wait_for_function("() => /unaffordable/.test(document.querySelector('#lastResult').textContent || '')", timeout=10_000)


def test_stardock_gear_uses_the_original_names(world) -> None:
    page = world["page"]

    def dock() -> None:
        me = world["me"]
        me.turns_today = 0
        me.planet_landed = None
        me.credits = 5_000_000
        _sit(world["universe"], "P2", 1)

    _next(page, dock)
    clicked = False
    for _ in range(4):
        button = page.locator("#here button", has_text="buy gear")
        try:
            button.wait_for(state="visible", timeout=5_000)
            button.click(timeout=5_000)
            clicked = True
            break
        except Exception:
            page.wait_for_timeout(400)
    assert clicked, "buy gear was not clickable"
    page.wait_for_selector(".frm")
    names = page.locator(".frm option").evaluate_all("els => els.map((el) => el.textContent)")
    assert "Armid Mines" in names
    assert "Atomic Detonator" in names
    assert "armid_mines" not in names
    _shoot(page, "gear", ".frm")
    page.keyboard.press("Escape")


def test_a_federal_target_warns_before_the_attack(world) -> None:
    page = world["page"]
    universe = world["universe"]
    assert universe.federals

    def park() -> None:
        me = world["me"]
        me.planet_landed = None
        me.turns_today = 0
        dest = next(
            int(sid) for sid, sec in universe.sectors.items()
            if not getattr(sec, "is_fedspace", False) and int(sid) > 10
        )
        _sit(universe, "P2", dest)
        universe.federals[0].sector_id = dest

    _next(page, park)
    page.keyboard.press("a")
    page.wait_for_selector("[data-fed=warn]")
    assert "podded" in page.locator("[data-fed=warn]").inner_text()
    _shoot(page, "federal", ".frm")
    page.keyboard.press("Escape")


def test_a_closed_command_says_ok(world) -> None:
    page = world["page"]
    page.keyboard.press("Escape")
    page.keyboard.press("j")
    page.wait_for_selector("#dangerOk")
    assert page.locator("#dangerOk").inner_text() == "OK"
    assert "not in this game" in page.locator("#menu").inner_text()
    _shoot(page, "closed", "#menu")
    page.keyboard.press("Escape")


def test_an_attack_result_names_the_fighters_you_lost(world) -> None:
    page = world["page"]
    universe = world["universe"]
    home = int(world["me"].sector_id)

    def arm() -> None:
        world["me"].planet_landed = None
        world["me"].turns_today = 0
        world["me"].ship.fighters = 20
        rival = universe.players["P1"]
        _sit(universe, "P1", home)
        _sit(universe, "P2", home)
        rival.ship.ship_class = ShipClass.MERCHANT_CRUISER
        rival.ship.fighters = 5
        rival.ship.shields = 0
        universe.federals[0].sector_id = 1

    _next(page, arm)
    page.keyboard.press("a")
    page.wait_for_selector(".frm")
    page.locator(".frm input[type=number]").fill("1")
    page.evaluate("() => { document.querySelector('#lastResult').textContent = ''; }")
    page.locator(".frm button.verb", has_text="CONFIRM").click()
    page.wait_for_function("() => /You lost/.test(document.querySelector('#lastResult').textContent || '') && /remain/.test(document.querySelector('#lastResult').textContent || '')", timeout=20_000)
    _shoot(page, "losses", "#lastResult")


def test_tax_shows_until_an_action_and_a_new_day_replaces_the_line(world) -> None:
    page = world["page"]

    def roll() -> None:
        me = world["me"]
        # Dawn tax is stamped on the new day (collect_daily_tax runs after day += 1).
        world["universe"].day += 1
        world["universe"].emit(
            EventKind.TAX_COLLECTED, actor_id="P2", sector_id=me.sector_id,
            payload={"credits_before": 1000, "tax": 50, "align_gain": 1, "new_alignment": 1},
            summary="The Federation collected 50 credits in taxes (+1 alignment)",
        )

    _next(page, roll)
    page.wait_for_selector("[data-tax=overnight]", timeout=10_000)
    assert "50" in page.locator("[data-tax=overnight]").inner_text()
    page.wait_for_function(
        "() => /You wait/.test(document.querySelector('#lastResult').textContent || '') && /Day \\d+/.test(document.querySelector('#lastResult').textContent || '')",
        timeout=10_000,
    )
    rolled = page.locator("#lastResult").inner_text()
    assert rolled.index("You wait") < rolled.index("Day ")
    _shoot(page, "tax", "[data-tax=overnight]")
    _shoot(page, "day", "#lastResult")
    page.keyboard.press(".")
    confirm = page.locator("#dangerOk")
    if confirm.count() and confirm.is_visible():
        confirm.click()
    page.wait_for_function("() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'", timeout=30_000)
    assert page.locator("[data-tax=overnight]").count() == 0
