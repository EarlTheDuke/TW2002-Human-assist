"""Map room: caption on the video, controls under the map, map card higher.

Old map-card tops, with the brackets line, were 810 px at 1440x900 and
1023 px at 1920x1080. The card has to sit at least 90 px above those.
"""

from __future__ import annotations

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "map-room-v1-token-p2-000000000000"
OLD_MAP_TOP = {1440: 810, 1920: 1023}


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#sbSector')?.textContent !== '-'", timeout=15_000)


def _layout(page) -> dict:
    lay = page.evaluate(
        """() => {
          const box = (el) => {
            const r = el.getBoundingClientRect();
            return {top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width, height: r.height};
          };
          const scr = box(document.querySelector('#vpScreen'));
          const cap = box(document.querySelector('#vpCaption'));
          const map = box(document.querySelector('#mapCard'));
          const controls = box(document.querySelector('#vpControls'));
          const brackets = box(document.querySelector('#localBrackets'));
          const svg = box(document.querySelector('#knownMap'));
          const buttons = [...document.querySelectorAll('#vpControls button')].map((b) => {
            const r = b.getBoundingClientRect();
            return {id: b.getAttribute('data-testid'), h: r.height, w: r.width,
              top: r.top, bottom: r.bottom, left: r.left, right: r.right,
              sw: b.scrollWidth, cw: b.clientWidth};
          });
          const sound = document.querySelector('[data-testid=viewport-sound]');
          const vp = document.querySelector('#viewport').getBoundingClientRect();
          return {
            mapY: map.top, mapBottom: map.bottom, controlsTop: controls.top,
            scr, cap, brackets, svg, buttons,
            sound: sound.textContent, soundSw: sound.scrollWidth, soundCw: sound.clientWidth,
            mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            innerW: document.querySelector('#viewport').clientWidth - 20,
            vpW: vp.width,
            caption: document.querySelector('#vpCaption').textContent,
          };
        }"""
    )
    page.locator("#vpControls").scroll_into_view_if_needed()
    buttons = page.evaluate(
        """() => [...document.querySelectorAll('#vpControls button')].map((b) => {
          const r = b.getBoundingClientRect();
          return {id: b.getAttribute('data-testid'), h: r.height, w: r.width,
            top: r.top, bottom: r.bottom, left: r.left, right: r.right,
            sw: b.scrollWidth, cw: b.clientWidth};
        })"""
    )
    lay["buttons"] = buttons
    return lay


def _assert_room(page, width: int) -> None:
    lay = _layout(page)
    limit = OLD_MAP_TOP[width] - 90
    assert lay["mapY"] <= limit, f"map top {lay['mapY']:.1f} at {width}; need <= {limit} (was {OLD_MAP_TOP[width]})"
    scr, cap = lay["scr"], lay["cap"]
    assert cap["top"] >= scr["top"] - 1 and cap["bottom"] <= scr["bottom"] + 1, (cap, scr)
    assert cap["left"] >= scr["left"] - 1 and cap["right"] <= scr["right"] + 1, (cap, scr)
    assert cap["top"] >= scr["top"] + scr["height"] * 0.5, (cap, scr)
    assert lay["caption"].startswith("Sector ")
    assert lay["controlsTop"] >= lay["mapBottom"] - 1, lay
    assert abs(scr["width"] / scr["height"] - 16 / 9) < 0.03, scr
    cap_w = 604 if page.viewport_size["height"] <= 920 else lay["innerW"]
    assert abs(scr["width"] - min(lay["innerW"], cap_w)) < 3, (scr["width"], lay["innerW"], cap_w)
    assert abs(lay["svg"]["width"] / lay["svg"]["height"] - 1) < 0.03, lay["svg"]
    assert lay["svg"]["width"] >= min(400, lay["innerW"] - 8)
    assert 12 <= lay["brackets"]["height"] <= 28, lay["brackets"]
    assert abs(lay["mfd"] - 420) < 1, lay["mfd"]
    assert page.locator("#viewport + #mapCard").count() == 1
    assert page.locator("#mapCard + #vpControls").count() == 1
    ids = {b["id"] for b in lay["buttons"]}
    assert ids == {"viewport-skip", "viewport-mode-live", "viewport-mode-stills", "viewport-mode-off"}
    view_h = page.viewport_size["height"]
    view_w = page.viewport_size["width"]
    for b in lay["buttons"]:
        assert b["h"] >= 32 and b["w"] >= 32, b
        assert b["sw"] <= b["cw"] + 1, b
        assert b["top"] >= 0 and b["bottom"] <= view_h + 1 and b["left"] >= 0 and b["right"] <= view_w + 1, b
    assert lay["sound"].strip() == "Sound: off"
    assert lay["soundSw"] <= lay["soundCw"] + 1


def _click_controls(page) -> None:
    page.evaluate("() => window.TW2KViewport.setEventCaption('Warping out')")
    assert "Warping" in page.get_by_test_id("viewport-caption").inner_text()
    page.get_by_test_id("viewport-skip").click()
    assert "Warping" not in page.get_by_test_id("viewport-caption").inner_text()
    page.get_by_test_id("viewport-mode-stills").click()
    assert page.evaluate("() => window.TW2KViewport.state().mode") == "stills"
    assert page.get_by_test_id("viewport-mode-stills").get_attribute("aria-pressed") == "true"
    page.get_by_test_id("viewport-mode-off").click()
    assert not page.locator("#vpScreen").is_visible()
    assert page.get_by_test_id("viewport-caption").is_visible()
    page.get_by_test_id("viewport-mode-live").click()
    assert page.evaluate("() => window.TW2KViewport.state().mode") == "live"
    assert page.get_by_test_id("viewport-mode-live").get_attribute("aria-pressed") == "true"
    page.get_by_test_id("viewport").scroll_into_view_if_needed()
    page.wait_for_function("() => window.TW2KViewport.state().animating === true", timeout=3_000)


def test_map_card_rises_and_controls_work(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.add_init_script(
            "window.__cls = 0;"
            "new PerformanceObserver((list) => {"
            "  for (const e of list.getEntries()) if (!e.hadRecentInput) window.__cls += e.value;"
            "}).observe({type: 'layout-shift', buffered: true});"
        )
        _open(page, host)
        _assert_room(page, 1440)
        assert page.evaluate("() => window.__cls") < 0.1
        _click_controls(page)
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        _open(wide, host)
        _assert_room(wide, 1920)
        _click_controls(wide)
        wide.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert not cu.get_by_test_id("viewport").is_visible()
        assert cu.locator("#cuScreen [data-vp-mode], #cuScreen #vpSkip").count() == 0
        cu.close()


def test_map_room_holds_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        browser = p.firefox.launch()
        for width, height in ((1440, 900), (1920, 1080)):
            page = browser.new_page(viewport={"width": width, "height": height})
            _open(page, host)
            _assert_room(page, width)
            _click_controls(page)
            page.close()
        browser.close()
