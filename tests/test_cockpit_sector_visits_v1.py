"""Visited sectors get a ring. The sector you are in stays as it was."""

from __future__ import annotations

import json
from pathlib import Path

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "sector-visits-v1-token-p2-00000000000"
MAP_TOP = {1440: 714, 1920: 927}
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-polish-v1"


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


def test_left_sector_is_marked_visited(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
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
        here = page.locator("#knownMap .node.here").get_attribute("data-sector")
        assert page.locator("#knownMap .node.here[data-visited]").count() == 0

        page.wait_for_selector("#warpBtns button:not([disabled])", timeout=20_000)
        target = page.locator("#warpBtns button").first.get_attribute("data-target")
        plain = page.evaluate(
            """(skip) => {
              const nodes = [...document.querySelectorAll('#knownMap .node:not(.stub):not(.here)')];
              const hit = nodes.find((n) => n.getAttribute('data-visited') !== '1'
                && n.getAttribute('data-sector') !== String(skip));
              return hit ? hit.getAttribute('data-sector') : '';
            }""",
            target,
        )
        assert plain, "expected a known neighbor that has not been visited"

        with page.expect_request(
            lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000,
        ) as warp:
            page.keyboard.press("1")
        got = _action(warp.value)
        assert got["kind"] == "warp" and str(got["args"]["target"]) == str(target)
        page.wait_for_selector("#turnBanner:not(.turn)", timeout=15_000)
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector(f"[data-testid=map-sector-{here}][data-visited='1']", timeout=10_000)
        assert page.locator("#knownMap .node.here[data-visited]").count() == 0
        assert page.locator(f"[data-testid=map-sector-{plain}][data-visited]").count() == 0
        assert page.locator(f"[data-testid=map-sector-{here}] .visit-mark").count() == 1
        _assert_layout(page, 1440)

        with page.expect_request(
            lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000,
        ) as scan:
            page.keyboard.press("s")
        assert _action(scan.value)["kind"] == "scan"
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        assert [p["kind"] for p in posts] == ["warp", "scan"]
        assert page.locator(f"[data-testid=map-sector-{here}] .visit-mark").count() == 1
        page.screenshot(path=str(SHOTS / "after-1440x900-visits.png"))
        page.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.body.classList.contains('mode-cu') && document.body.scrollHeight <= 800",
            timeout=20_000,
        )
        assert cu.locator("[data-visited]").count() == 0
        assert cu.locator(".visit-mark").count() == 0
        cu.close()
