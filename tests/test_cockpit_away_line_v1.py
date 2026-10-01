"""A quiet line counts events that happened before this page loaded."""

from __future__ import annotations

import json

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "away-line-v1-token-p2-00000000000000"
MAP_TOP = {1440: 714, 1920: 927}


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const tabTop = Math.min(...tabs);
          const banner = document.querySelector('#turnBanner').getBoundingClientRect();
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            tabSpread: Math.max(...tabs) - tabTop,
            barH: document.querySelector('#scoreboard').getBoundingClientRect().height,
            bannerH: banner.height,
          };
        }"""
    )


def _assert_layout(page, width: int) -> None:
    lay = _layout(page)
    assert abs(lay["mapY"] - MAP_TOP[width]) < 4, lay["mapY"]
    assert abs(lay["mfd"] - 420) < 1
    assert lay["tabSpread"] < 2
    assert abs(lay["barH"] - 88) < 1, lay["barH"]
    assert abs(lay["bannerH"] - 92) < 1, lay["bannerH"]


def _action(request) -> dict:
    return json.loads(request.post_data or "{}").get("action") or {}


def _hits(a: dict | None, b: dict | None) -> bool:
    if not a or not b or a["w"] <= 0 or b["w"] <= 0 or a["h"] <= 0 or b["h"] <= 0:
        return False
    return a["x"] < b["right"] and b["x"] < a["right"] and a["y"] < b["bottom"] and b["y"] < a["bottom"]


def _assert_clear(page) -> None:
    boxes = page.evaluate(
        """() => {
          const box = (el) => {
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return {x: r.x, y: r.y, right: r.right, bottom: r.bottom, w: r.width, h: r.height};
          };
          return {
            away: box(document.querySelector('[data-testid=away-line]')),
            who: box(document.querySelector('#turnBanner .who')),
            timer: box(document.querySelector('[data-testid=turn-timer]')),
          };
        }"""
    )
    assert boxes["away"] and boxes["who"] and boxes["timer"], boxes
    assert not _hits(boxes["away"], boxes["who"]), boxes
    assert not _hits(boxes["away"], boxes["timer"]), boxes


def test_away_line_counts_events_from_before_the_load(browser, tmp_path, monkeypatch) -> None:
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
        page.wait_for_timeout(500)
        assert page.locator("[data-testid=away-line]").count() == 0

        page.wait_for_selector("#warpBtns button:not([disabled])", timeout=20_000)
        with page.expect_request(
            lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000,
        ) as warp:
            page.keyboard.press("1")
        assert _action(warp.value)["kind"] == "warp"
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        assert page.locator("[data-testid=away-line]").count() == 0

        _open(page, host)
        page.wait_for_selector("[data-testid=away-line]", timeout=15_000)
        text = page.locator("[data-testid=away-line]").inner_text()
        assert text.startswith("While you were away:")
        assert "warp" in text
        _assert_layout(page, 1440)
        _assert_clear(page)
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.evaluate("() => window.scrollTo(0, 0)")
        _assert_layout(page, 1920)
        _assert_clear(page)
        page.set_viewport_size({"width": 1440, "height": 900})

        with page.expect_request(
            lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000,
        ) as scan:
            page.keyboard.press("s")
        assert _action(scan.value)["kind"] == "scan"
        page.wait_for_function(
            "() => !document.querySelector('[data-testid=away-line]')",
            timeout=5_000,
        )
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        _assert_layout(page, 1440)
        assert [p["kind"] for p in posts] == ["warp", "scan"]
        page.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.body.classList.contains('mode-cu') && document.body.scrollHeight <= 800",
            timeout=20_000,
        )
        assert cu.locator("[data-testid=away-line]").count() == 0
        cu.close()
