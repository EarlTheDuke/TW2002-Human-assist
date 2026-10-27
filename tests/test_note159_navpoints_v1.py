"""NOTE 159. NavPoints stay off until the switch or V311_PROFILE=v311.

Off, the computer menu has no NavPoint command. On, set, list, plot, and clear
work, and the points are still there after a save and resume.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import FighterDeployment, GameConfig, Player, Universe
from tw2k.engine.navpoints import menu_rows, resolve_navpoint
from tw2k.engine.runner import apply_action, query_route
from tw2k.engine.universe import generate_universe
from tw2k.public.manual import render

pytestmark = pytest.mark.legacy_profile

_BOT = Path(__file__).resolve().parents[1] / "web" / "bot.html"


def _seat():
    universe = generate_universe(GameConfig(seed=159, universe_size=40, max_days=2, enable_ferrengi=False))
    player = Player(id="P1", name="Tester", sector_id=1)
    universe.players["P1"] = player
    universe.sectors[1].occupant_ids.append("P1")
    return universe, player


def _kinds(universe) -> set[str]:
    return {row.kind for row in legal_actions(universe, "P1")}


def test_off_has_no_menu_and_profile_turns_it_on(monkeypatch) -> None:
    assert K.NAVPOINT_MODE == "legacy"
    assert K.navpoint_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.navpoint_live() is False
    universe, _player = _seat()
    assert "navpoint" not in _kinds(universe)
    assert "navpoints" not in universe.players["P1"].model_dump()
    refused = apply_action(universe, "P1", Action(kind=ActionKind.NAVPOINT, args={"op": "list"}))
    assert refused.ok is False
    assert refused.error == "unsupported action"
    assert "NavPoints" not in _BOT.read_text(encoding="utf-8")

    page = render("Galaxy War Command")
    assert "NAVPOINT_MODE" in page
    assert "there is no NavPoints menu." in page

    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "NAVPOINT_MODE", "v311")
    assert "navpoint" in _kinds(universe)
    monkeypatch.setattr(K, "NAVPOINT_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.NAVPOINT_MODE == "legacy"
    assert K.navpoint_live() is True
    assert "navpoint" in _kinds(universe)
    live = render("Galaxy War Command")
    assert "the computer menu sets, lists, and clears 4 named NavPoints." in live


def test_set_list_plot_clear_and_save(monkeypatch) -> None:
    monkeypatch.setattr(K, "NAVPOINT_MODE", "v311")
    universe, player = _seat()
    universe.sectors[1].warps = [11]
    universe.sectors[11].warps = [20]
    deep = 20
    listed = apply_action(universe, "P1", Action(kind=ActionKind.NAVPOINT, args={"op": "list"}))
    assert listed.ok is True
    rows = menu_rows(universe, player)
    by_slot = {row["slot"]: row for row in rows}
    assert by_slot["terra"]["sector"] == 1
    assert by_slot["stardock"]["sector"] == K.STARDOCK_SECTOR
    assert by_slot[1]["sector"] is None

    logged = apply_action(
        universe, "P1",
        Action(kind=ActionKind.NAVPOINT, args={"op": "set", "slot": 1, "name": "Home", "sector": deep}),
    )
    assert logged.ok is True
    assert menu_rows(universe, player)[0]["scan"] == "No Scan"
    fed = apply_action(
        universe, "P1",
        Action(kind=ActionKind.NAVPOINT, args={"op": "set", "slot": 2, "name": "Dockside", "sector": 2}),
    )
    assert fed.ok is True
    assert menu_rows(universe, player)[1]["scan"] != "No Scan"
    universe.sectors[deep].fighters = FighterDeployment(owner_id="P1", count=1)
    assert menu_rows(universe, player)[0]["scan"] != "No Scan"

    extra = apply_action(
        universe, "P1",
        Action(kind=ActionKind.NAVPOINT, args={"op": "set", "slot": 5, "name": "Far", "sector": 11}),
    )
    assert extra.ok is False

    plotted = apply_action(
        universe, "P1", Action(kind=ActionKind.PLOT_COURSE, args={"navpoint": "Home"}),
    )
    assert plotted.ok is True
    assert universe.events[-1].payload["path"] == [11, deep]
    asked = query_route(universe, "P1", "Home")
    assert asked["ok"] is True and asked["target"] == deep and asked["path"] == [11, deep]
    terra = query_route(universe, "P1", "Terra")
    assert terra["ok"] is True and terra["target"] == 1

    raw = universe.model_dump_json()
    resumed = Universe.model_validate_json(raw)
    assert resolve_navpoint(resumed.players["P1"], "home") == deep
    assert resolve_navpoint(resumed.players["P1"], "1") == deep

    cleared = apply_action(universe, "P1", Action(kind=ActionKind.NAVPOINT, args={"op": "clear", "slot": 1}))
    assert cleared.ok is True
    assert resolve_navpoint(player, "Home") is None
    gone = apply_action(universe, "P1", Action(kind=ActionKind.PLOT_COURSE, args={"navpoint": "Home"}))
    assert gone.ok is False and gone.error == "no such NavPoint"
    apply_action(universe, "P1", Action(kind=ActionKind.NAVPOINT, args={"op": "clear", "slot": 0}))
    assert player.navpoints == []
    assert "navpoints" not in player.model_dump()


def test_cockpit_sets_lists_plots_and_clears(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    from tests._cu_host import CuHost

    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.setattr(K, "NAVPOINT_MODE", "v311")
    tok = "note159-cockpit-token-p2-00000000"
    with CuHost(tmp_path, tok, turns_per_day=400) as host, sync_playwright() as pw:
        deadline = time.time() + 20
        me = None
        while time.time() < deadline:
            universe = host.runner.state.universe
            agent = next((row for row in host.runner.state.agents if row.player_id == "P2"), None)
            if host.parked and universe is not None and agent is not None and agent.awaiting_input and "P2" in universe.players:
                me = universe.players["P2"]
                break
            time.sleep(0.05)
        assert me is not None
        assert "navpoint" in _kinds(universe)
        dest = int(universe.sectors[me.sector_id].warps[0])
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={tok}")
            page.keyboard.press("c")
            page.wait_for_selector("#menu[data-screen=computer]", timeout=20_000)
            assert "NavPoints" in page.locator("#menu").inner_text()
            page.keyboard.press("n")
            page.wait_for_selector("#menu[data-screen=navpoints] [data-nav='1']", timeout=10_000)
            assert page.locator("[data-nav]").count() == 4
            assert "log important sectors" in page.locator("#menu").inner_text()
            assert "Terra" in page.locator("#menu").inner_text()
            page.locator("[data-nav-name='1']").fill("Home")
            page.locator("[data-nav-sector='1']").fill(str(dest))
            with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/action")):
                page.locator("[data-nav-set='1']").click()
            page.wait_for_function(
                "() => /logged at sector/.test((document.querySelector('#lastResult') || {}).textContent || '')",
                timeout=10_000,
            )
            page.evaluate("() => { const a = document.activeElement; if (a && a.blur) a.blur(); }")
            page.keyboard.press("Escape")
            page.keyboard.press("c")
            page.wait_for_selector("#menu[data-screen=computer]", timeout=10_000)
            page.keyboard.press("n")
            page.wait_for_selector("#menu[data-screen=navpoints] [data-nav-name='1']", timeout=10_000)
            assert page.locator("[data-nav-name='1']").input_value() == "Home"
            assert page.locator("[data-nav-scan='1']").inner_text() != ""
            with page.expect_response(lambda r: "/route?target=" in r.url):
                page.locator("[data-nav-plot='1']").click()
            page.wait_for_selector("[data-testid=course-line]", timeout=10_000)
            assert str(dest) in page.locator("[data-testid=course-line]").inner_text()
            page.evaluate("() => { const a = document.activeElement; if (a && a.blur) a.blur(); }")
            page.keyboard.press("Escape")
            page.keyboard.press("c")
            page.wait_for_selector("#menu[data-screen=computer]", timeout=10_000)
            page.keyboard.press("n")
            page.wait_for_selector("[data-nav-clear='1']", timeout=10_000)
            with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/action")):
                page.locator("[data-nav-clear='1']").click()
            page.wait_for_function(
                "() => /cleared/.test((document.querySelector('#lastResult') || {}).textContent || '')",
                timeout=10_000,
            )
            page.evaluate("() => { const a = document.activeElement; if (a && a.blur) a.blur(); }")
            page.keyboard.press("Escape")
            page.keyboard.press("c")
            page.wait_for_selector("#menu[data-screen=computer]", timeout=10_000)
            page.keyboard.press("n")
            page.wait_for_selector("[data-nav-name='1']", timeout=10_000)
            assert page.locator("[data-nav-name='1']").input_value() == ""
            page.close()
        finally:
            browser.close()
