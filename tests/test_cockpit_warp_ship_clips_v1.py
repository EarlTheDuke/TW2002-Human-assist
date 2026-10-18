"""cockpit-warp-ship-clips-v1. The warp scene uses the hull you are flying.

A real move plays that hull's clip. A refused warp, a plot, and a fresh page
play nothing. A hull with no rows falls back to today's warp.out clip.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine.models import ShipClass

from tests._cu_host import CuHost

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "cockpit-warp-ship-clips-v1"
TOK = "warp-clips-v1-token-p2-0000000000"
HULLS = tuple(cls.value for cls in ShipClass)


def _set_ship(host: CuHost, cls: str) -> None:
    me = host.runner.state.universe.players["P2"]
    me.ship.ship_class = ShipClass(cls)


def _your_move(page) -> None:
    page.wait_for_function(
        "() => (document.querySelector('#waitchip') || {}).textContent === 'YOUR MOVE'",
        timeout=20_000,
    )


def _ready(page) -> None:
    page.wait_for_function("() => window.__tw2kWarp && window.__tw2kWarp.ready()", timeout=20_000)
    _your_move(page)


def _plays(page) -> str:
    return page.locator("#warpClip").get_attribute("data-plays") or "0"


def _sector(page) -> str:
    return page.locator("#pSector").inner_text().strip()


def _quiet(page, plays: str) -> None:
    assert page.locator("#warpClip").is_hidden()
    assert _plays(page) == plays


def _shot(page, name: str) -> None:
    page.locator("#viewport").evaluate("el => el.scrollIntoView({block: 'start', inline: 'nearest'})")
    path = SHOTS / name
    page.screenshot(path=str(path))
    assert path.stat().st_size > 5000, path


def _hold(page) -> None:
    page.wait_for_function(
        """() => {
          const root = document.querySelector('#warpClip');
          if (!root || root.hidden) return false;
          const n = window.__tw2kWarp.hold(450);
          return n >= 1 || root.getAttribute('data-motion') === 'still';
        }""",
        timeout=8_000,
    )


def _fly(page, hull: str) -> None:
    here = _sector(page)
    page.locator("#warps button").first.click()
    page.wait_for_function(
        """([here, hull]) => {
          const sec = (document.querySelector('#pSector').textContent || '').trim();
          const root = document.querySelector('#warpClip');
          return sec && sec !== here && root && !root.hidden
            && root.getAttribute('data-hull') === hull
            && root.getAttribute('data-clip') === hull + '.streak.01'
            && !!root.querySelector('[data-testid=warp-body]');
        }""",
        arg=[here, hull],
        timeout=20_000,
    )


def test_warp_clip_matches_the_hull(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    import tw2k.server.runner as server_runner

    monkeypatch.setattr(server_runner, "note_wait_streak", lambda *a, **k: 0)
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK, max_days=30, turns_per_day=400) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            legacy = browser.new_page(viewport={"width": 1280, "height": 800})
            legacy.goto(f"{host.base}/bot?seat=P2&token={TOK}")
            legacy.wait_for_selector("[data-testid=ship]", timeout=20_000)
            assert legacy.locator("[data-testid=warp-clip]").count() == 0
            legacy.close()

            wide = browser.new_page(viewport={"width": 1280, "height": 800})
            phone = browser.new_page(viewport={"width": 390, "height": 844})
            url = f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}"
            wide.goto(url)
            phone.goto(url)
            wide.wait_for_selector("#warps button", timeout=20_000)
            phone.wait_for_selector("#warps button", timeout=20_000)
            _ready(wide)
            _ready(phone)
            _quiet(wide, "0")
            _quiet(phone, "0")

            catalog = wide.evaluate(
                """() => {
                  const rows = window.__tw2kWarp.hulls().map((hull) => {
                    const clip = window.__tw2kWarp.pick(hull, () => 0);
                    return {hull, id: clip.id, fallback: clip.fallback, kind: clip.kind};
                  });
                  window.__tw2kWarp.setList('merchant_cruiser', [
                    {id: 'merchant_cruiser.streak.01', kind: 'svg', duration_ms: 2000},
                    {id: 'merchant_cruiser.streak.02', kind: 'svg', duration_ms: 2000},
                  ]);
                  const first = window.__tw2kWarp.pick('merchant_cruiser', () => 0);
                  const second = window.__tw2kWarp.pick('merchant_cruiser', () => 0.99);
                  window.__tw2kWarp.setList('merchant_cruiser', [
                    {id: 'merchant_cruiser.streak.01', kind: 'svg', duration_ms: 2000},
                  ]);
                  const missing = window.__tw2kWarp.pick('no_such_hull', () => 0);
                  return {rows, first: first.id, second: second.id, missing};
                }"""
            )
            assert {row["hull"] for row in catalog["rows"]} == set(HULLS)
            for row in catalog["rows"]:
                assert row["fallback"] is False
                assert row["kind"] == "svg"
                assert row["id"] == row["hull"] + ".streak.01"
            assert catalog["first"] == "merchant_cruiser.streak.01"
            assert catalog["second"] == "merchant_cruiser.streak.02"
            assert catalog["missing"]["fallback"] is True
            assert catalog["missing"]["id"] == "warp.out"
            _quiet(wide, "0")

            here = _sector(wide)
            target = 1 if here != "1" else 2
            before = wide.locator("#lastResult").inner_text()
            wide.evaluate("(t) => window.__tw2kTest.do('plot_course', {target: t, execute: false})", target)
            wide.wait_for_function(
                "(prev) => (document.querySelector('#lastResult').textContent || '') !== prev",
                arg=before,
                timeout=15_000,
            )
            assert _sector(wide) == here
            _quiet(wide, "0")

            before = wide.locator("#lastResult").inner_text()
            wide.evaluate("() => window.__tw2kTest.do('warp', {target: 999999})")
            wide.wait_for_function(
                "(prev) => (document.querySelector('#lastResult').textContent || '') !== prev",
                arg=before,
                timeout=15_000,
            )
            assert _sector(wide) == here
            _quiet(wide, "0")
            assert wide.evaluate(
                """() => {
                  const still = document.querySelector('[data-testid=viewport-clip-still]');
                  const src = (still && still.getAttribute('src')) || '';
                  const shown = document.querySelector('[data-testid=viewport-clip]:not([hidden])');
                  return !shown && !/move_warp|warp_out/.test(src);
                }"""
            )

            wide.evaluate("() => window.__tw2kWarp.setList('merchant_cruiser', [])")
            phone.evaluate("() => window.__tw2kWarp.setList('merchant_cruiser', [])")
            departed = _sector(wide)
            wide.locator("#warps button").first.click()
            wide.wait_for_function(
                """(here) => {
                  const sec = (document.querySelector('#pSector').textContent || '').trim();
                  const root = document.querySelector('#warpClip');
                  const still = document.querySelector('[data-testid=viewport-clip-still]');
                  const src = (still && still.getAttribute('src')) || '';
                  const shown = document.querySelector('[data-testid=viewport-clip]:not([hidden])');
                  return sec && sec !== here && root && root.hidden && root.getAttribute('data-plays') === '0'
                    && !!shown && /move_warp|warp_out/.test(src);
                }""",
                arg=departed,
                timeout=20_000,
            )
            landed = _sector(wide)
            phone.wait_for_function(
                """(sec) => (document.querySelector('#pSector').textContent || '').trim() === sec
                  && document.querySelector('#warpClip').hidden
                  && document.querySelector('#warpClip').getAttribute('data-plays') === '0'""",
                arg=landed,
                timeout=20_000,
            )
            one = [{"id": "merchant_cruiser.streak.01", "kind": "svg", "duration_ms": 2000}]
            wide.evaluate("(row) => window.__tw2kWarp.setList('merchant_cruiser', row)", one)
            phone.evaluate("(row) => window.__tw2kWarp.setList('merchant_cruiser', row)", one)

            _fly(wide, "merchant_cruiser")
            phone.wait_for_function(
                """() => {
                  const root = document.querySelector('#warpClip');
                  return root && !root.hidden && root.getAttribute('data-hull') === 'merchant_cruiser';
                }""",
                timeout=20_000,
            )
            _hold(wide)
            _hold(phone)
            assert wide.evaluate("() => getComputedStyle(document.querySelector('#warpClip .warp-ship')).animationName") == "warp-jump"
            assert wide.evaluate(
                """() => {
                  const anim = document.querySelector('#warpClip .warp-ship').getAnimations()[0];
                  return anim ? anim.effect.getTiming().duration : 0;
                }"""
            ) == 2000
            assert phone.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
            assert wide.evaluate(
                """() => {
                  const a = document.querySelector('#warpClip').getBoundingClientRect();
                  const b = document.querySelector('#viewport').getBoundingClientRect();
                  return a.width > 40 && a.top >= b.top - 1 && a.bottom <= b.bottom + 1
                    && a.left >= b.left - 1 && a.right <= b.right + 1;
                }"""
            )
            merchant = wide.locator("[data-testid=warp-body]").inner_html()
            _shot(wide, "merchant-cruiser-1280.png")
            _shot(phone, "merchant-cruiser-390.png")

            _your_move(wide)
            _set_ship(host, "scout_marauder")
            wide.keyboard.press(".")
            wide.wait_for_function(
                "() => document.querySelector('#shipSvg').getAttribute('data-hull') === 'scout_marauder'",
                timeout=20_000,
            )
            _fly(wide, "scout_marauder")
            phone.wait_for_function(
                """() => {
                  const root = document.querySelector('#warpClip');
                  return root && !root.hidden && root.getAttribute('data-hull') === 'scout_marauder';
                }""",
                timeout=20_000,
            )
            _hold(wide)
            _hold(phone)
            scout = wide.locator("[data-testid=warp-body]").inner_html()
            assert scout != merchant
            _shot(wide, "scout-marauder-1280.png")
            _shot(phone, "scout-marauder-390.png")

            _your_move(wide)
            _set_ship(host, "escape_pod")
            wide.keyboard.press(".")
            wide.wait_for_function(
                "() => document.querySelector('#shipSvg').getAttribute('data-hull') === 'escape_pod'",
                timeout=20_000,
            )
            _fly(wide, "escape_pod")
            phone.wait_for_function(
                """() => {
                  const root = document.querySelector('#warpClip');
                  return root && !root.hidden && root.getAttribute('data-hull') === 'escape_pod';
                }""",
                timeout=20_000,
            )
            _hold(wide)
            _hold(phone)
            pod = wide.locator("[data-testid=warp-body]").inner_html()
            assert pod != merchant and pod != scout
            _shot(wide, "escape-pod-1280.png")
            _shot(phone, "escape-pod-390.png")

            _your_move(wide)
            _set_ship(host, "merchant_cruiser")
            wide.keyboard.press(".")
            wide.wait_for_function(
                "() => document.querySelector('#shipSvg').getAttribute('data-hull') === 'merchant_cruiser'",
                timeout=20_000,
            )
            still = browser.new_page(viewport={"width": 1280, "height": 800})
            still.emulate_media(reduced_motion="reduce")
            still.goto(url)
            still.wait_for_selector("#warps button", timeout=20_000)
            _ready(still)
            _fly(still, "merchant_cruiser")
            _hold(still)
            assert still.locator("#warpClip").get_attribute("data-motion") == "still"
            assert still.evaluate("() => getComputedStyle(document.querySelector('#warpClip .warp-ship')).animationName") == "none"
            assert still.locator("[data-testid=warp-body]").count() == 1
            _shot(still, "merchant-cruiser-still-1280.png")
        finally:
            browser.close()
