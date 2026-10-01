"""Enter in the trade quantity box presses Confirm."""

from __future__ import annotations

import json

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "enter-trade-v1-token-p2-000000000000"
MAP_TOP = {1440: 714, 1920: 927}


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const tabTop = Math.min(...tabs);
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            tabSpread: Math.max(...tabs) - tabTop,
            barH: document.querySelector('#scoreboard').getBoundingClientRect().height,
          };
        }"""
    )


def _assert_layout(page, width: int) -> None:
    lay = _layout(page)
    assert abs(lay["mapY"] - MAP_TOP[width]) < 4, lay["mapY"]
    assert abs(lay["mfd"] - 420) < 1
    assert lay["tabSpread"] < 2
    assert abs(lay["barH"] - 88) < 1, lay["barH"]


def _action(request) -> dict:
    return json.loads(request.post_data or "{}").get("action") or {}


def test_enter_in_quantity_presses_confirm(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        posts: list[dict] = []
        page.on(
            "request",
            lambda r: posts.append(_action(r)) if r.method == "POST" and r.url.endswith("/action") else None,
        )
        _open(page, host)
        _assert_layout(page, 1440)
        page.wait_for_selector("[data-testid=action-trade]:not([disabled])", timeout=20_000)
        page.get_by_test_id("action-trade").click()
        page.wait_for_selector("[data-testid=trade-qty]", timeout=5_000)
        qty = int(page.locator("[data-testid=trade-qty]").input_value())
        assert qty > 0

        page.locator("[data-testid=verb-submit]").evaluate("el => { el.disabled = true }")
        page.locator("[data-testid=trade-qty]").focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)
        assert posts == []
        assert page.locator("[data-testid=verb-form]").is_visible()

        page.locator("[data-testid=verb-submit]").evaluate("el => { el.disabled = false }")
        page.locator("[data-testid=trade-qty]").focus()
        with page.expect_request(
            lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000,
        ) as trade:
            page.keyboard.press("Enter")
        got = _action(trade.value)
        assert got["kind"] == "trade"
        assert got["args"]["qty"] == qty
        assert [p["kind"] for p in posts] == ["trade"]
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.evaluate("() => window.scrollTo(0, 0)")
        _assert_layout(page, 1440)
        page.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.body.classList.contains('mode-cu') && document.body.scrollHeight <= 800",
            timeout=20_000,
        )
        cu.close()
