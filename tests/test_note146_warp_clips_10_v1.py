"""NOTE 146. Ten distinct warp pictures per ship, picked so none repeats next.

Each hull lists at least ten clips. A clip changes the camera, the star
streaks, the engine plume, and the exit flash. A plot and a refused warp
do not play one. Fifty picks in a row never repeat the same clip twice.
Stills holds a frame, Off stays dark, and Skip hides the picture.
The redesign layout is the only page that has this. /bot is unchanged.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tests._cu_host import CuHost, allowed_test_port
from tw2k.engine.models import ShipClass

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "web" / "media" / "warp-clips.json"
VARIANTS = ROOT / "web" / "warp-variants.js"
HULLS = tuple(cls.value for cls in ShipClass)


def _styles() -> list[dict]:
    text = VARIANTS.read_text(encoding="utf-8")
    rows = []
    for block in re.findall(r"\{[^{}]*duration_ms:[^{}]*\}", text):
        row = {}
        for key in ("n", "style", "camera", "stars", "exit", "glow", "flash"):
            found = re.search(rf'{key}:\s*"([^"]+)"', block)
            assert found, key
            row[key] = found.group(1)
        for key in ("plume", "streak", "duration_ms"):
            found = re.search(rf"{key}:\s*(-?\d+)", block)
            assert found, key
            row[key] = int(found.group(1))
        rows.append(row)
    return rows


def test_each_ship_has_ten_distinct_clips() -> None:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert set(doc["hulls"]) == set(HULLS)
    styles = _styles()
    assert len(styles) == 10
    assert len({row["glow"] for row in styles}) == 10
    assert len({row["plume"] for row in styles}) == 10
    assert len({row["streak"] for row in styles}) == 10
    assert len({row["flash"] for row in styles}) == 10
    assert len({(row["camera"], row["stars"], row["exit"], row["glow"], row["plume"]) for row in styles}) == 10
    for hull, clips in doc["hulls"].items():
        assert len(clips) >= 10, hull
        assert len({row["id"] for row in clips}) >= 10
        assert all(row["kind"] == "svg" for row in clips)
    assert MANIFEST.stat().st_size < 60 * 1024
    assert VARIANTS.stat().st_size < 60 * 1024
    for name in ("bot.html", "bot.js", "bot-parity.js"):
        text = (ROOT / "web" / name).read_text(encoding="utf-8")
        assert "warp-variants" not in text
        assert "warp-clips.json" not in text
        assert "data-plume" not in text


def test_no_clip_on_a_still_ship_and_no_repeat_over_fifty(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("V311_PROFILE", raising=False)
    token = "note146-warp-p2-token-0000000001"
    with CuHost(tmp_path, token, max_days=5, turns_per_day=80) as host, sync_playwright() as pw:
        assert host.port != 8099
        assert allowed_test_port(host.port)
        browser = pw.chromium.launch()
        try:
            legacy = browser.new_page(viewport={"width": 1280, "height": 800})
            legacy.goto(f"{host.base}/bot?seat=P2&token={token}")
            legacy.wait_for_selector("[data-testid=ship]", timeout=20_000)
            assert legacy.locator("[data-testid=warp-clip]").count() == 0
            legacy.close()

            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={token}")
            page.wait_for_selector("#warps button", timeout=20_000)
            page.wait_for_function("() => window.__tw2kWarp && window.__tw2kWarp.ready()", timeout=20_000)
            page.wait_for_function(
                "() => (document.querySelector('#waitchip') || {}).textContent === 'YOUR MOVE'",
                timeout=20_000,
            )
            assert page.locator("#warpClip").get_attribute("data-plays") == "0"

            here = page.locator("#pSector").inner_text().strip()
            before = page.locator("#lastResult").inner_text()
            page.evaluate("(t) => window.__tw2kTest.do('plot_course', {target: t, execute: false})", 1 if here != "1" else 2)
            page.wait_for_function(
                "(prev) => (document.querySelector('#lastResult').textContent || '') !== prev",
                arg=before,
                timeout=15_000,
            )
            assert page.locator("#pSector").inner_text().strip() == here
            assert page.locator("#warpClip").get_attribute("data-plays") == "0"

            before = page.locator("#lastResult").inner_text()
            page.evaluate("() => window.__tw2kTest.do('warp', {target: 999999})")
            page.wait_for_function(
                "(prev) => (document.querySelector('#lastResult').textContent || '') !== prev",
                arg=before,
                timeout=15_000,
            )
            assert page.locator("#pSector").inner_text().strip() == here
            assert page.locator("#warpClip").get_attribute("data-plays") == "0"

            varied = page.evaluate(
                """() => {
                  const hull = document.querySelector('#shipSvg').getAttribute('data-hull');
                  const api = window.TW2KWarpVariants;
                  const seen = [];
                  api.styles.forEach((style) => {
                    const id = hull + '.' + style.style + '.' + style.n;
                    window.__tw2kWarp.paint(hull, id);
                    const root = document.querySelector('#warpClip');
                    const body = document.querySelector('[data-testid=warp-body]');
                    seen.push({
                      glow: root.getAttribute('data-glow'),
                      plume: root.getAttribute('data-plume'),
                      streak: root.getAttribute('data-streak'),
                      flash: root.getAttribute('data-flash'),
                      exit: root.getAttribute('data-exit'),
                      camera: root.getAttribute('data-camera'),
                      html: body ? body.innerHTML : ''
                    });
                  });
                  const ids = [];
                  for (let i = 0; i < 50; i++) ids.push(window.__tw2kWarp.pick(hull).id);
                  return {hull, seen, ids};
                }"""
            )
            seen = varied["seen"]
            assert len(seen) == 10
            assert len({row["glow"] for row in seen}) == 10
            assert len({row["plume"] for row in seen}) == 10
            assert len({row["html"] for row in seen}) >= 8
            assert all(row["html"] and "polygon" in row["html"] for row in seen)
            flashes = [row for row in seen if row["exit"] == "flash"]
            assert len(flashes) >= 2
            assert len({row["flash"] for row in flashes}) == len(flashes)
            ids = varied["ids"]
            assert len(ids) == 50
            assert all(item.startswith(varied["hull"] + ".") for item in ids)
            assert all(ids[i] != ids[i + 1] for i in range(len(ids) - 1)), ids
            assert len(set(ids)) >= 10

            def warp() -> str:
                page.wait_for_function(
                    """() => {
                      const chip = document.querySelector('#waitchip');
                      const btn = document.querySelector('#warps button');
                      return chip && chip.textContent === 'YOUR MOVE' && btn && !btn.disabled;
                    }""",
                    timeout=20_000,
                )
                sector = page.locator("#pSector").inner_text().strip()
                plays = page.locator("#warpClip").get_attribute("data-plays") or "0"
                page.locator("#warps button").first.click()
                page.wait_for_function(
                    """([sector, plays]) => {
                      const sec = (document.querySelector('#pSector').textContent || '').trim();
                      const root = document.querySelector('#warpClip');
                      return sec && sec !== sector && root && !root.hidden
                        && root.getAttribute('data-plays') === String(Number(plays) + 1);
                    }""",
                    arg=[sector, plays],
                    timeout=20_000,
                )
                return page.locator("#warpClip").get_attribute("data-clip") or ""

            first = warp()
            page.locator("[data-testid=warp-skip]").click()
            page.wait_for_function("() => document.querySelector('#warpClip').hidden", timeout=2_000)
            second = warp()
            assert first != second
            assert first.startswith(varied["hull"] + ".")
            held = page.evaluate("() => window.__tw2kWarp.hold(400)")
            assert held >= 1

            page.locator("[data-testid=viewport-mode-stills]").click()
            third = warp()
            assert third != second
            assert page.locator("#warpClip").get_attribute("data-motion") == "still"
            assert page.evaluate(
                "() => getComputedStyle(document.querySelector('#warpClip .warp-ship')).animationName"
            ) == "none"
            page.locator("[data-testid=warp-skip]").click()
            page.wait_for_function("() => document.querySelector('#warpClip').hidden", timeout=2_000)

            page.locator("[data-testid=viewport-mode-off]").click()
            page.wait_for_function(
                """() => {
                  const chip = document.querySelector('#waitchip');
                  const btn = document.querySelector('#warps button');
                  return chip && chip.textContent === 'YOUR MOVE' && btn && !btn.disabled;
                }""",
                timeout=20_000,
            )
            sector = page.locator("#pSector").inner_text().strip()
            plays = page.locator("#warpClip").get_attribute("data-plays")
            page.locator("#warps button").first.click()
            page.wait_for_function(
                "(sector) => (document.querySelector('#pSector').textContent || '').trim() !== sector",
                arg=sector,
                timeout=20_000,
            )
            assert page.locator("#warpClip").get_attribute("data-plays") == plays
            assert page.locator("#warpClip").is_hidden()
        finally:
            browser.close()
