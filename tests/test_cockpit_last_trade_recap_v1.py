"""The Moments tab recaps this seat's latest trade."""

from __future__ import annotations

import json

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "last-trade-recap-v1-token-p2-0000000"
MAP_TOP = {1440: 714}


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const tabTop = Math.min(...tabs);
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            tabSpread: Math.max(...tabs) - tabTop,
          };
        }"""
    )


def _action(request) -> dict:
    return json.loads(request.post_data or "{}").get("action") or {}


def test_moments_tab_recaps_this_seats_last_trade(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.get_by_test_id("mfd-tab-moments").click()
        assert not page.get_by_test_id("last-trade").is_visible()
        lay = _layout(page)
        assert abs(lay["mapY"] - MAP_TOP[1440]) < 4, lay["mapY"]
        assert abs(lay["mfd"] - 420) < 1
        assert lay["tabSpread"] < 2

        page.wait_for_selector("[data-testid=action-trade]:not([disabled])", timeout=20_000)
        page.get_by_test_id("action-trade").click()
        page.wait_for_selector("[data-testid=trade-qty]", timeout=5_000)
        with page.expect_request(
            lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000,
        ) as trade:
            page.get_by_test_id("verb-submit").click()
        got = _action(trade.value)
        assert got["kind"] == "trade"
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.evaluate("() => window.scrollTo(0, 0)")
        page.get_by_test_id("mfd-tab-moments").click()
        side = str(got["args"]["side"]).upper()
        needle = f"Last trade: {side} {got['args']['qty']} {got['args']['commodity']} @"
        page.wait_for_function(
            """(needle) => {
              const el = document.querySelector('[data-testid=last-trade]');
              return el && !el.hidden && el.textContent.startsWith(needle) && el.textContent.endsWith(' cr');
            }""",
            arg=needle,
            timeout=15_000,
        )
        text = page.get_by_test_id("last-trade").inner_text()
        assert " = " in text
        lay = _layout(page)
        assert abs(lay["mapY"] - MAP_TOP[1440]) < 4, lay["mapY"]
        assert abs(lay["mfd"] - 420) < 1
        page.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.body.classList.contains('mode-cu') && document.body.scrollHeight <= 800",
            timeout=20_000,
        )
        assert not cu.get_by_test_id("last-trade").is_visible()
        cu.close()
