"""Holds bar lists this seat's cargo on hover, without moving the ship bar."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "cargo-tip-v1-token-p2-000000000000000"
MAP_TOP = {1440: 714, 1920: 927}
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-polish-v1"
KNOWN = "Fuel ore 10, Organics 0, Equipment 4, empty 6 of 20"


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_selector("[data-testid=hull-holds] .n", timeout=15_000)


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const tabTop = Math.min(...tabs);
          const bar = document.querySelector('#scoreboard').getBoundingClientRect();
          const holds = document.querySelector('[data-testid=hull-holds]').getBoundingClientRect();
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            tabSpread: Math.max(...tabs) - tabTop,
            barH: bar.height,
            holdsH: holds.height,
          };
        }"""
    )


def _assert_layout(page, width: int, holds_h: float) -> None:
    lay = _layout(page)
    assert abs(lay["mapY"] - MAP_TOP[width]) < 4, lay["mapY"]
    assert abs(lay["mfd"] - 420) < 1
    assert lay["tabSpread"] < 2
    assert abs(lay["barH"] - 88) < 1
    assert abs(lay["holdsH"] - holds_h) < 1


def _action(request) -> dict:
    return json.loads(request.post_data or "{}").get("action") or {}


def _install(page, mode: dict) -> None:
    def handle(route) -> None:
        if not mode["kind"]:
            route.continue_()
            return
        response = route.fetch()
        data = response.json()
        obs = data.get("observation")
        ship = obs.get("ship") if isinstance(obs, dict) else None
        if isinstance(ship, dict):
            cargo = dict(ship.get("cargo") or {})
            if mode["kind"] == "known":
                cargo.update({"fuel_ore": 10, "organics": 0, "equipment": 4})
                ship["holds"] = 20
                ship["cargo_free"] = 6
            else:
                for name in ("fuel_ore", "organics", "equipment", "colonists"):
                    cargo[name] = 0
                ship["cargo_free"] = ship.get("holds")
            ship["cargo"] = cargo
            obs["ship"] = ship
            data["observation"] = obs
        route.fulfill(response=response, json=data)

    page.route("**/observation**", handle)


def _show(page, text: str) -> None:
    page.get_by_test_id("hull-holds").hover()
    page.wait_for_function(
        """(want) => {
          const tip = document.querySelector('[data-testid=cargo-tip]');
          if (!tip) return false;
          const shown = getComputedStyle(tip).display !== 'none';
          return shown && tip.textContent === want;
        }""",
        arg=text,
        timeout=10_000,
    )


def test_cargo_tip_lists_holds_without_growing_the_bar(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        posts: list[str] = []
        page.on(
            "request",
            lambda r: posts.append(r.url) if r.method == "POST" and r.url.endswith("/action") else None,
        )
        mode = {"kind": "known"}
        _install(page, mode)
        _open(page, host)
        holds_h = _layout(page)["holdsH"]
        _assert_layout(page, 1440, holds_h)
        assert page.get_by_test_id("cargo-tip").is_hidden()
        assert posts == []

        _show(page, KNOWN)
        _assert_layout(page, 1440, holds_h)
        page.screenshot(path=str(SHOTS / "after-1440x900-cargo.png"))
        page.mouse.move(0, 0)
        page.wait_for_function(
            "() => getComputedStyle(document.querySelector('[data-testid=cargo-tip]')).display === 'none'",
            timeout=5_000,
        )
        page.get_by_test_id("hull-holds").focus()
        page.wait_for_function(
            """(want) => {
              const tip = document.querySelector('[data-testid=cargo-tip]');
              return tip && getComputedStyle(tip).display !== 'none' && tip.textContent === want;
            }""",
            arg=KNOWN,
            timeout=5_000,
        )

        mode["kind"] = "empty"
        with page.expect_response(lambda r: "/observation" in r.url and r.ok, timeout=15_000):
            page.get_by_test_id("refresh").click()
        _show(page, "empty")
        _assert_layout(page, 1440, holds_h)
        assert posts == []

        page.wait_for_selector("[data-testid=action-scan]:not([disabled])", timeout=15_000)
        with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as scan:
            page.keyboard.press("s")
        assert _action(scan.value)["kind"] == "scan"
        page.wait_for_selector("#turnBanner:not(.turn)", timeout=15_000)
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector("#warpBtns button:not([disabled])", timeout=20_000)
        target = page.locator("#warpBtns button").first.get_attribute("data-target")
        with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as warp:
            page.keyboard.press("1")
        got = _action(warp.value)
        assert got["kind"] == "warp" and str(got["args"]["target"]) == target
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        wide_mode = {"kind": "known"}
        _install(wide, wide_mode)
        _open(wide, host)
        holds_w = _layout(wide)["holdsH"]
        _show(wide, KNOWN)
        _assert_layout(wide, 1920, holds_w)
        wide.screenshot(path=str(SHOTS / "after-1920x1080-cargo.png"))
        wide.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert not cu.get_by_test_id("cargo-tip").is_visible()
        assert cu.locator("#cuScreen [data-testid=cargo-tip]").count() == 0
        cu.close()


def test_cargo_tip_holds_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        browser = p.firefox.launch()
        for width, height in ((1440, 900), (1920, 1080)):
            page = browser.new_page(viewport={"width": width, "height": height})
            _install(page, {"kind": "known"})
            _open(page, host)
            holds_h = _layout(page)["holdsH"]
            _show(page, KNOWN)
            _assert_layout(page, width, holds_h)
            page.close()
        browser.close()
