"""A plotted route shows its hop count and turn cost on the map."""

from __future__ import annotations

import json

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "route-cost-v1-token-p2-0000000000000"
MAP_TOP = {1440: 714, 1920: 927}


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_selector("#knownMap .node.here", timeout=15_000)


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


def test_plotted_route_shows_hops_and_turns(browser, tmp_path, monkeypatch) -> None:
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
        assert posts == []
        cost = page.locator("[data-testid=route-cost]")
        assert cost.is_hidden()

        page.wait_for_selector("#warpBtns button:not([disabled])", timeout=20_000)
        with page.expect_request(
            lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000,
        ) as warp:
            page.keyboard.press("1")
        assert _action(warp.value)["kind"] == "warp"
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector("#warpBtns button:not([disabled])", timeout=20_000)
        target = page.locator("#warpBtns button").first.get_attribute("data-target")
        page.locator(f"[data-testid=map-sector-{target}]").click()
        page.wait_for_selector("[data-testid=route-cost]:not([hidden])", timeout=10_000)
        assert cost.get_attribute("data-hops") == "1"
        assert cost.get_attribute("data-turns") == "3"
        assert cost.inner_text() == "1 hop · 3 turns"
        assert page.locator("[data-testid=route-line]").count() == 1
        assert [p["kind"] for p in posts] == ["warp"]

        page.locator("[data-testid=plot-execute]").uncheck()
        page.wait_for_function(
            "() => document.querySelector('[data-testid=route-cost]').getAttribute('data-turns') === '0'",
            timeout=5_000,
        )
        assert cost.inner_text() == "1 hop · 0 turns"
        page.locator("[data-testid=plot-execute]").check()
        page.wait_for_function(
            "() => document.querySelector('[data-testid=route-cost]').getAttribute('data-turns') === '3'",
            timeout=5_000,
        )

        page.locator("[data-testid=plot-target]").fill("")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=route-cost]').hidden",
            timeout=5_000,
        )
        assert cost.is_hidden()
        assert cost.inner_text() == ""
        assert page.locator("[data-testid=route-line]").count() == 0
        assert [p["kind"] for p in posts] == ["warp"]
        page.evaluate("() => window.scrollTo(0, 0)")
        _assert_layout(page, 1440)

        page.set_viewport_size({"width": 1920, "height": 1080})
        page.evaluate("() => window.scrollTo(0, 0)")
        _assert_layout(page, 1920)
        page.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.body.classList.contains('mode-cu') && document.body.scrollHeight <= 800",
            timeout=20_000,
        )
        assert cu.locator("[data-testid=route-cost]").is_hidden()
        cu.close()
