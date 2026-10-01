"""A scanned sector gets a filled dot. A sector only passed through does not."""

from __future__ import annotations

import json

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "sector-scanned-v1-token-p2-00000000000"
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


def test_scanned_sector_gets_a_dot_beside_its_number(browser, tmp_path, monkeypatch) -> None:
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
        assert page.locator("[data-scanned]").count() == 0
        here = page.locator("#knownMap .node.here").get_attribute("data-sector")

        page.wait_for_selector("#warpBtns button:not([disabled])", timeout=20_000)
        with page.expect_request(
            lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000,
        ) as warp:
            page.keyboard.press("1")
        assert _action(warp.value)["kind"] == "warp"
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector(f"[data-testid=map-sector-{here}][data-visited='1']", timeout=10_000)
        assert page.locator(f"[data-testid=map-sector-{here}][data-scanned]").count() == 0
        assert page.locator(f"[data-testid=map-sector-{here}] .visit-mark").count() == 1
        assert page.locator(f"[data-testid=map-sector-{here}] .scan-mark").count() == 0
        assert page.locator("#knownMap .node.here[data-scanned]").count() == 0

        with page.expect_request(
            lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000,
        ) as scan:
            page.keyboard.press("s")
        assert _action(scan.value)["kind"] == "scan"
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector("#knownMap .node.here[data-scanned='1']", timeout=10_000)
        assert page.locator("#knownMap .node.here .scan-mark").count() == 1
        assert page.locator("#knownMap .node.here[data-visited]").count() == 0
        assert page.locator(f"[data-testid=map-sector-{here}][data-scanned]").count() == 0
        assert page.locator(f"[data-testid=map-sector-{here}] .visit-mark").count() == 1
        page.evaluate("() => window.scrollTo(0, 0)")
        _assert_layout(page, 1440)
        assert [p["kind"] for p in posts] == ["warp", "scan"]
        page.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.body.classList.contains('mode-cu') && document.body.scrollHeight <= 800",
            timeout=20_000,
        )
        assert cu.locator("[data-scanned]").count() == 0
        assert cu.locator(".scan-mark").count() == 0
        cu.close()
