"""Warp exits as a numbered ring on the video, same order as the warp buttons."""

from __future__ import annotations

import time

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost
from tw2k.engine.observation import build_observation

TOK = "exit-ring-v1-token-p2-00000000000"
MAP_TOP = {1440: 714, 1920: 927}


def _wait_parked(host: CuHost):
    deadline = time.time() + 15
    universe = host.runner.state.universe
    me = universe.players["P2"]
    while time.time() < deadline:
        if me.sector_id > 10 and me.turns_per_day - me.turns_today >= 2 and universe.sectors[me.sector_id].warps:
            return universe, me
        time.sleep(0.05)
    raise AssertionError("seat did not park")


def _serve(host, universe):
    agent = next(a for a in host.runner.state.agents if a.player_id == "P2")
    agent.current_observation = build_observation(universe, "P2")


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_selector("#warpBtns button", timeout=15_000)
    page.wait_for_selector("[data-testid=exit-ring] button", timeout=15_000)


def _targets(page, selector: str) -> list[str]:
    return page.locator(selector).evaluate_all("els => els.map(e => e.getAttribute('data-target'))")


def _assert_ring(page, width: int) -> None:
    buttons = _targets(page, "#warpBtns button")
    chips = _targets(page, "[data-testid=exit-ring] button")
    assert chips == buttons and chips, (chips, buttons)
    labels = page.locator("[data-testid=exit-ring] button").all_inner_texts()
    button_labels = page.locator("#warpBtns button").all_inner_texts()
    for i, (chip, button) in enumerate(zip(labels, button_labels, strict=True), start=1):
        assert chip.startswith(f"{i} ")
        target = chips[i - 1]
        assert target in chip
        code = button.replace(f"WARP {target}", "").strip()
        if code:
            assert code in chip
        else:
            assert chip.strip() == f"{i} {target}"
    lay = page.evaluate(
        """() => {
          const box = (el) => {
            const r = el.getBoundingClientRect();
            return {top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width, height: r.height};
          };
          const scr = box(document.querySelector('#vpScreen'));
          const cap = box(document.querySelector('#vpCaption'));
          const chips = [...document.querySelectorAll('[data-testid=exit-ring] button')].map(box);
          const cx = scr.left + scr.width / 2, cy = scr.top + scr.height / 2;
          const hit = document.elementFromPoint(cx, cy);
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            scr, cap, chips,
            centreClear: !(hit && hit.closest && hit.closest('#warpRing')),
          };
        }"""
    )
    assert abs(lay["mapY"] - MAP_TOP[width]) < 4, lay["mapY"]
    assert abs(lay["mfd"] - 420) < 1
    assert lay["centreClear"]
    for chip in lay["chips"]:
        assert chip["bottom"] <= lay["cap"]["top"] + 1, (chip, lay["cap"])
        assert chip["top"] >= lay["scr"]["top"] - 1 and chip["bottom"] <= lay["scr"]["bottom"] + 1


def _warp_posts(posts: list[str]) -> list[str]:
    return [body for body in posts if '"warp"' in body or '"kind":"warp"' in body]


def _assert_one_warp(page, posts: list[str], fire) -> None:
    before = len(_warp_posts(posts))
    fire()
    deadline = time.time() + 10
    while time.time() < deadline and len(_warp_posts(posts)) < before + 1:
        page.wait_for_timeout(100)
    page.wait_for_timeout(400)
    assert len(_warp_posts(posts)) == before + 1, _warp_posts(posts)


def test_ring_matches_buttons_and_posts_once(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        universe, me = _wait_parked(host)
        other = universe.players["P1"]
        here = universe.sectors[me.sector_id]
        unknown = next(sid for sid in here.warps if universe.sectors[sid].port)
        me.known_ports.pop(unknown, None)
        other.known_ports[unknown] = {"class": "BBS", "stock": {}, "last_seen_day": universe.day}
        _serve(host, universe)

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.add_init_script(
            "window.__cls = 0; window.__warpPosts = [];"
            "new PerformanceObserver((list) => {"
            "  for (const e of list.getEntries()) if (!e.hadRecentInput) window.__cls += e.value;"
            "}).observe({type: 'layout-shift', buffered: true});"
        )
        posts: list[str] = []
        page.on("request", lambda r: posts.append(r.post_data or "") if r.method == "POST" else None)
        _open(page, host)
        bare = page.locator(f"[data-testid=exit-ring-{unknown}]")
        assert "BBS" not in (bare.inner_text() or "")
        assert "tint-" not in (bare.get_attribute("class") or "")
        _assert_ring(page, 1440)
        assert page.evaluate("() => window.__cls") < 0.1

        page.evaluate("() => window.TW2KViewport.setEventCaption('Warping out')")
        centre = page.evaluate(
            """() => {
              const r = document.querySelector('#vpScreen').getBoundingClientRect();
              return {x: r.left + r.width / 2, y: r.top + r.height / 2};
            }"""
        )
        page.mouse.click(centre["x"], centre["y"])
        assert "Warping" not in page.get_by_test_id("viewport-caption").inner_text()
        assert _warp_posts(posts) == []

        _assert_one_warp(page, posts, lambda: page.keyboard.press("1"))
        page.wait_for_function(
            "() => { const b = document.querySelector('#warpBtns button'); return b && !b.disabled; }",
            timeout=10_000,
        )
        _assert_one_warp(page, posts, lambda: page.locator("[data-testid=exit-ring] button").first.click())

        me.turns_today = me.turns_per_day
        _serve(host, universe)
        page.get_by_test_id("refresh").click()
        page.wait_for_function(
            "() => document.querySelector('[data-testid=exit-ring]')?.querySelector('button') == null",
            timeout=10_000,
        )
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        me.turns_today = 0
        _serve(host, universe)
        _open(wide, host)
        _assert_ring(wide, 1920)
        wide.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert not cu.get_by_test_id("exit-ring").is_visible()
        assert cu.locator("#cuScreen [data-testid=exit-ring]").count() == 0


def test_warp_ring_holds_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        _wait_parked(host)
        browser = p.firefox.launch()
        for width, height in ((1440, 900), (1920, 1080)):
            page = browser.new_page(viewport={"width": width, "height": height})
            _open(page, host)
            _assert_ring(page, width)
            page.close()
        browser.close()
