"""Remembered port letters are tinted; an unrecalled neighbor stays a bare number."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost
from tests.test_amz6_warp_codes import _replace_snapshot, _wait_parked

TOK = "port-color-v1-token-p2-0000000000000"
MAP_TOP = {1440: 714, 1920: 927}
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-polish-v1"
BUY = "rgb(125, 206, 160)"
SELL = "rgb(158, 201, 239)"


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


def _assert_layout(page, width: int) -> None:
    lay = _layout(page)
    assert abs(lay["mapY"] - MAP_TOP[width]) < 4, lay["mapY"]
    assert abs(lay["mfd"] - 420) < 1
    assert lay["tabSpread"] < 2


def _letters(page, selector: str) -> dict:
    return page.evaluate(
        """(sel) => {
          const root = document.querySelector(sel);
          if (!root) return null;
          const nodes = [...root.querySelectorAll('span, tspan')];
          return {
            text: root.textContent,
            letters: nodes.map((s) => ({
              t: s.textContent,
              c: s.getAttribute('class'),
              color: getComputedStyle(s).color,
              fill: getComputedStyle(s).fill,
              style: getComputedStyle(s).fontStyle,
              weight: String(getComputedStyle(s).fontWeight),
            })),
          };
        }""",
        selector,
    )


def _action(request) -> dict:
    return json.loads(request.post_data or "{}").get("action") or {}


def _remember(host, universe, me, unknown) -> None:
    me.known_ports[unknown] = {"class": "BSS", "stock": {}, "last_seen_day": universe.day}
    me.known_sectors.add(unknown)
    _replace_snapshot(host, universe)


def _assert_bss(info: dict) -> None:
    got = [(row["t"], row["c"], row["style"], row["weight"]) for row in info["letters"]]
    assert got == [("B", "pc-b", "normal", "800"), ("S", "pc-s", "italic", "600"), ("S", "pc-s", "italic", "600")], info
    for row in info["letters"]:
        paint = row["color"] if row["c"] else ""
        if row["fill"] not in ("", "none", "rgb(0, 0, 0)", "rgba(0, 0, 0, 0)"):
            paint = row["fill"]
        want = BUY if row["t"] == "B" else SELL
        assert paint == want, row


def test_remembered_bss_letters_are_tinted(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK) as host:
        universe, me = _wait_parked(host)
        other = universe.players["P1"]
        here = universe.sectors[me.sector_id]
        unknown = next(sid for sid in here.warps if sid not in me.known_ports and universe.sectors[sid].port)
        me.known_ports.pop(unknown, None)
        other.known_ports[unknown] = {"class": "BSS", "stock": {}, "last_seen_day": universe.day}
        _replace_snapshot(host, universe)

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        posts: list[str] = []
        page.on(
            "request",
            lambda r: posts.append(r.url) if r.method == "POST" and r.url.endswith("/action") else None,
        )
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector(f"[data-testid=warp-{unknown}]", timeout=20_000)
        bare = page.locator(f"[data-testid=warp-{unknown}]")
        assert bare.inner_text().strip() == f"WARP {unknown}"
        assert bare.locator("span").count() == 0
        _assert_layout(page, 1440)
        assert posts == []

        _remember(host, universe, me, unknown)
        page.get_by_test_id("refresh").click()
        page.wait_for_function(
            f"() => document.querySelector('[data-testid=warp-{unknown}] .pc-b')",
            timeout=10_000,
        )
        button = _letters(page, f"[data-testid=warp-{unknown}]")
        assert button["text"] == f"WARP {unknown} BSS"
        _assert_bss(button)
        chip = _letters(page, f"[data-testid=exit-ring-{unknown}]")
        assert chip["text"].endswith("BSS")
        _assert_bss(chip)
        label = _letters(page, f"[data-testid=map-sector-{unknown}] text.code")
        assert label["text"] == "BSS"
        _assert_bss(label)
        bare_id = next((sid for sid in here.warps if sid != unknown and sid not in me.known_ports), None)
        if bare_id is not None:
            other_btn = page.locator(f"[data-testid=warp-{bare_id}]")
            assert other_btn.inner_text().strip() == f"WARP {bare_id}"
            assert other_btn.locator(".pc-b, .pc-s").count() == 0
        _assert_layout(page, 1440)
        page.screenshot(path=str(SHOTS / "after-1440x900-portcolor.png"))
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        wide.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        wide.wait_for_selector("#turnBanner.turn", timeout=20_000)
        wide.wait_for_selector(f"[data-testid=warp-{unknown}] .pc-b", timeout=15_000)
        wide_btn = _letters(wide, f"[data-testid=warp-{unknown}]")
        assert wide_btn["text"] == f"WARP {unknown} BSS"
        _assert_bss(wide_btn)
        _assert_layout(wide, 1920)
        wide.screenshot(path=str(SHOTS / "after-1920x1080-portcolor.png"))

        wide.wait_for_selector("[data-testid=action-scan]:not([disabled])", timeout=15_000)
        with wide.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as scan:
            wide.keyboard.press("s")
        assert _action(scan.value)["kind"] == "scan"
        wide.wait_for_selector("#turnBanner:not(.turn)", timeout=15_000)
        wide.wait_for_selector("#turnBanner.turn", timeout=20_000)
        wide.wait_for_selector("#warpBtns button:not([disabled])", timeout=20_000)
        target = wide.locator("#warpBtns button").first.get_attribute("data-target")
        with wide.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as warp:
            wide.keyboard.press("1")
        got = _action(warp.value)
        assert got["kind"] == "warp" and str(got["args"]["target"]) == target
        wide.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert cu.locator(".pc-b, .pc-s").count() == 0
        cu.close()


def test_port_code_letters_hold_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        browser = p.firefox.launch()
        universe, me = _wait_parked(host)
        here = universe.sectors[me.sector_id]
        unknown = next(sid for sid in here.warps if sid not in me.known_ports and universe.sectors[sid].port)
        me.known_ports.pop(unknown, None)
        _replace_snapshot(host, universe)
        for width, height in ((1440, 900), (1920, 1080)):
            me.known_ports.pop(unknown, None)
            me.known_sectors.discard(unknown)
            _replace_snapshot(host, universe)
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
            page.wait_for_selector("#turnBanner.turn", timeout=20_000)
            page.wait_for_selector(f"[data-testid=warp-{unknown}]", timeout=20_000)
            assert page.locator(f"[data-testid=warp-{unknown}]").inner_text().strip() == f"WARP {unknown}"
            assert page.locator(f"[data-testid=warp-{unknown}] span").count() == 0
            _remember(host, universe, me, unknown)
            page.get_by_test_id("refresh").click()
            page.wait_for_function(
                f"() => document.querySelector('[data-testid=warp-{unknown}] .pc-b')",
                timeout=10_000,
            )
            info = _letters(page, f"[data-testid=warp-{unknown}]")
            assert info["text"] == f"WARP {unknown} BSS"
            _assert_bss(info)
            _assert_layout(page, width)
            page.close()
        browser.close()
