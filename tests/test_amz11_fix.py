"""Quick-trade labels stay whole, and plot preview rejects a bad target.

A short name such as SELL Fuel is never ellipsized. The credit total stays
inside the button. Buttons wrap onto another row instead of shrinking.
"""

from __future__ import annotations

import time

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost
from tw2k.engine.models import Commodity
from tw2k.engine.observation import build_observation

TOK = "amz11fix-labels-token-p2-000000"


def _wait_parked(host: CuHost):
    deadline = time.time() + 15
    universe = host.runner.state.universe
    me = universe.players["P2"]
    while time.time() < deadline:
        port = universe.sectors[me.sector_id].port
        if me.ship.cargo.get(Commodity.FUEL_ORE, 0) >= 10 and port is not None and (port.code or "").startswith("B"):
            return universe, me
        time.sleep(0.05)
    raise AssertionError("seat did not park")


def _move(universe, me, dest: int) -> None:
    universe.sectors[me.sector_id].occupant_ids.remove("P2")
    me.sector_id = dest
    universe.sectors[dest].occupant_ids.append("P2")


def _room(port, commodity, qty: int) -> None:
    stock = port.stock[commodity]
    if stock.maximum - stock.current < qty:
        stock.maximum = stock.current + qty


def _stock(port, commodity, qty: int) -> None:
    stock = port.stock[commodity]
    if stock.current < qty:
        stock.current = qty
    if stock.maximum < stock.current:
        stock.maximum = stock.current


def _load(me, port, fuel: int, organics: int) -> None:
    me.ship.holds = max(me.ship.holds, fuel + organics + 500)
    me.ship.cargo[Commodity.FUEL_ORE] = fuel
    me.ship.cargo[Commodity.ORGANICS] = organics
    me.ship.cargo[Commodity.EQUIPMENT] = 0
    me.credits = max(me.credits, 1_000_000)
    _room(port, Commodity.FUEL_ORE, fuel)
    _room(port, Commodity.ORGANICS, organics)
    _stock(port, Commodity.EQUIPMENT, 10)


def _snapshot(host: CuHost, universe) -> None:
    agent = next(a for a in host.runner.state.agents if a.player_id == "P2")
    agent.current_observation = build_observation(universe, "P2")


def _fit(page, cu: bool) -> dict:
    if cu:
        page.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
    else:
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_function(
        "() => document.querySelectorAll('#quickTrades button, #cuQuickTrades button').length >= 3",
        timeout=15_000,
    )
    return page.evaluate("""() => {
        const buttons = [...document.querySelectorAll('#quickTrades button, #cuQuickTrades button')]
            .filter((b) => b.offsetParent !== null);
        const bad = [];
        for (const b of buttons) {
            const label = b.querySelector('.qlabel');
            const num = b.querySelector('.qnum');
            const br = b.getBoundingClientRect();
            const nr = num.getBoundingClientRect();
            const labelCut = label.scrollWidth > label.clientWidth + 1;
            const numCut = num.scrollWidth > num.clientWidth + 1
                || nr.left < br.left - 1 || nr.right > br.right + 1 || nr.bottom > br.bottom + 1;
            const lr = label.getBoundingClientRect();
            const gap = nr.top >= lr.bottom - 1 ? nr.top - lr.bottom : nr.left - lr.right;
            if (labelCut || numCut || gap <= 0) bad.push(b.textContent);
        }
        return {
            n: buttons.length,
            texts: buttons.map((b) => b.textContent),
            bad,
            scroll: document.scrollingElement.scrollHeight,
            wide: document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
        };
    }""")


def _expect(fit: dict, parts: tuple[str, ...], *, cu: bool) -> None:
    assert fit["n"] >= 3, fit
    assert not fit["bad"], fit
    assert fit["wide"], fit
    blob = " ".join(fit["texts"]).replace(",", "")
    for digits in parts:
        assert digits in blob, fit["texts"]
    assert all("…" not in t and "..." not in t for t in fit["texts"]), fit["texts"]
    if cu:
        assert fit["scroll"] <= VIEW_H, fit


def test_quick_labels_stay_whole_for_small_and_large_totals(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    sync_api = pytest.importorskip("playwright.sync_api")
    with CuHost(tmp_path, TOK) as host:
        universe, me = _wait_parked(host)
        dest = next(s for s in universe.sectors.values() if s.port and s.port.code == "BBS")
        _move(universe, me, dest.id)
        _load(me, dest.port, 10, 10)
        _snapshot(host, universe)
        with sync_api.sync_playwright() as pw:
            launched = []
            for name in ("chromium", "firefox"):
                try:
                    launched.append((name, getattr(pw, name).launch()))
                except Exception as exc:
                    pytest.fail(f"{name} did not launch: {exc}")
            try:
                for name, browser in launched:
                    _check_browser(browser, host, ("x10",))
                _load(me, dest.port, 1000, 250)
                _snapshot(host, universe)
                for name, browser in launched:
                    _check_browser(browser, host, ("x1000", "x250"))
            finally:
                for name, browser in launched:
                    browser.close()


def _check_browser(browser, host: CuHost, parts: tuple[str, ...]) -> None:
    default = browser.new_page(viewport={"width": 1440, "height": 900})
    default.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    _expect(_fit(default, False), parts, cu=False)
    default.set_viewport_size({"width": VIEW_W, "height": VIEW_H})
    _expect(_fit(default, False), parts, cu=False)
    default.close()
    cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
    cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
    _expect(_fit(cu, True), parts, cu=True)
    cu.close()


def test_plot_preview_says_already_here_and_rejects_a_bad_target(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK + "-plot") as host:
        page = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}-plot")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        here = page.get_by_test_id("sector").inner_text().strip()
        page.get_by_test_id("action-plot-course").click()
        page.wait_for_selector("[data-testid=plot-target]", timeout=5_000)
        target = page.locator("[data-testid=plot-target]")
        target.fill(here)
        page.wait_for_function(
            "() => document.querySelector('[data-testid=verb-preview]').textContent === 'you are already here'",
            timeout=5_000,
        )
        target.fill("-1")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=verb-preview]').textContent === 'enter a valid sector'",
            timeout=5_000,
        )
        target.fill("0")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=verb-preview]').textContent === 'enter a valid sector'",
            timeout=5_000,
        )
        page.close()
