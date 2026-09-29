"""Deck cockpit: instrument bar, fixed side screen, fog-safe port tint.

The map stays under the video. mode=cu stays one screen. Port color comes
from this seat's memory only.
"""

from __future__ import annotations

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "polish-v1-token-p2-00000000000000"


def test_deck_tabs_keep_their_height_and_keys_still_fire(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.add_init_script(
            "window.__cls = 0; window.__clsSources = [];"
            "new PerformanceObserver((list) => {"
            "  for (const e of list.getEntries()) if (!e.hadRecentInput) {"
            "    window.__cls += e.value;"
            "    window.__clsSources.push(e.value.toFixed(3) + ' ' + (e.sources || []).map(s => (s.node && s.node.id) || (s.node && s.node.className) || '').join(','));"
            "  }"
            "}).observe({type: 'layout-shift', buffered: true});"
        )
        posts: list[str] = []
        page.on("request", lambda r: posts.append(r.post_data or "") if r.method == "POST" else None)
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_function("() => document.querySelector('#sbSector')?.textContent !== '-'", timeout=15_000)
        assert page.locator("#viewport + #mapCard").count() == 1
        assert page.get_by_test_id("inst-ship").inner_text() != "-"
        assert page.get_by_test_id("alert-lamp").inner_text().strip() != ""
        assert page.get_by_test_id("mfd-tab-ship").get_attribute("aria-selected") == "true"
        before = page.evaluate("() => document.querySelector('.mfd-body').getBoundingClientRect().height")
        page.get_by_test_id("mfd-tab-port").click()
        after = page.evaluate("() => document.querySelector('.mfd-body').getBoundingClientRect().height")
        assert before == after and before >= 400
        assert page.get_by_test_id("port").is_visible()
        assert page.get_by_test_id("mfd-tab-port").get_attribute("aria-selected") == "true"
        page.get_by_test_id("mfd-tab-ship").focus()
        page.keyboard.press("s")
        page.wait_for_timeout(600)
        assert any('"scan"' in body or '"kind":"scan"' in body or "scan" in body for body in posts)
        cls = page.evaluate("() => ({value: window.__cls, sources: window.__clsSources})")
        assert cls["value"] < 0.1, cls
        page.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H


def test_port_tint_ignores_another_seat_and_a_route_line_uses_known_warps(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        universe = host.runner.state.universe
        me = universe.players["P2"]
        other = universe.players["P1"]
        here = universe.sectors[me.sector_id]
        unknown = next(sid for sid in here.warps if universe.sectors[sid].port)
        me.known_ports.pop(unknown, None)
        other.known_ports[unknown] = {"class": "BBS", "stock": {}, "last_seen_day": universe.day}
        from tests.test_amz6_warp_codes import _replace_snapshot
        _replace_snapshot(host, universe)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector(f"[data-testid=warp-{unknown}]", timeout=20_000)
        bare = page.locator(f"[data-testid=warp-{unknown}]")
        assert "BBS" not in (bare.inner_text() or "")
        assert "tint-" not in (bare.get_attribute("class") or "")
        me.known_ports[unknown] = {"class": "BBS", "stock": {}, "last_seen_day": universe.day}
        _replace_snapshot(host, universe)
        page.get_by_test_id("refresh").click()
        page.wait_for_function(
            f"() => (document.querySelector('[data-testid=warp-{unknown}]')?.className || '').includes('tint-mix')",
            timeout=10_000,
        )
        page.get_by_test_id("action-plot-course").click()
        page.get_by_test_id("plot-target").fill(str(unknown))
        page.wait_for_selector("[data-testid=route-line]", timeout=8_000)
        page.close()
