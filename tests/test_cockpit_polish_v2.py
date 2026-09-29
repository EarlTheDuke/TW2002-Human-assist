"""Polish nits: one tab row, a whole ship name, a clip from Moments, no guessed route point.

The map stays under the video. mode=cu stays one screen.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost

ROOT = Path(__file__).resolve().parents[1]
TOK = "polish-v2-token-p2-00000000000000"

TABS = """() => [...document.querySelectorAll('#mfd [role=tab]')].map(t => {
  const r = t.getBoundingClientRect();
  return {y: Math.round(r.y), h: r.height};
})"""

READOUTS = """() => {
  const box = (el) => el ? {text: (el.textContent || '').trim(), clipped: el.scrollWidth > el.clientWidth + 1} : null;
  const turns = document.getElementById('sbTurns') && document.getElementById('sbTurns').parentElement;
  const align = document.getElementById('sbAlignLabel') && document.getElementById('sbAlignLabel').parentElement;
  return {
    ship: box(document.getElementById('sbShip')),
    name: box(document.getElementById('sbName')),
    stage: box(document.getElementById('sbStage')),
    credits: box(document.getElementById('sbCredits')),
    day: box(document.getElementById('sbDay') && document.getElementById('sbDay').parentElement),
    sector: box(document.getElementById('sbSector')),
    turns: box(turns),
    align: box(align),
  };
}"""


def _manifest() -> dict:
    data = json.loads((ROOT / "web" / "media" / "manifest.json").read_text(encoding="utf-8"))
    data["clips"]["v2.play"] = {
        "caption": "Play clip",
        "fallback_still": "stills/system_scan.png",
        "variants": [{
            "id": "v2play",
            "webm": "clips/placeholder/ph_warp_out_a.webm",
            "mp4": "clips/placeholder/ph_warp_out_a.mp4",
            "poster": "stills/system_scan.png",
            "duration_ms": 2000,
            "provenance": {"approved_by": None},
        }],
    }
    data["clips"]["v2.still"] = {
        "caption": "Still only",
        "fallback_still": "stills/trade_port.png",
        "variants": [{}],
    }
    data["clips"]["v2.miss"] = {
        "caption": "Missing clip",
        "fallback_still": "stills/move_blocked.png",
        "variants": [{
            "id": "v2miss",
            "webm": "clips/placeholder/missing-v2.webm",
            "mp4": "clips/placeholder/missing-v2.mp4",
            "poster": "stills/move_blocked.png",
            "duration_ms": 2000,
            "provenance": {"approved_by": None},
        }],
    }
    return data


def _open(page, host, manifest: dict) -> None:
    page.route("**/manifest.json", lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps(manifest)))
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_function("() => window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
    page.wait_for_function("() => document.querySelector('#sbShip')?.textContent === 'merchant_cruiser'", timeout=15_000)


def _assert_row(page) -> None:
    tabs = page.evaluate(TABS)
    assert len(tabs) == 5
    assert len({t["y"] for t in tabs}) == 1
    assert all(t["h"] >= 32 for t in tabs)
    body = page.evaluate("() => document.querySelector('.mfd-body').getBoundingClientRect().height")
    assert body == 420 or abs(body - 420) < 1


def _assert_readouts(page) -> None:
    got = page.evaluate(READOUTS)
    assert got["ship"]["text"] == "merchant_cruiser" and not got["ship"]["clipped"]
    assert not got["credits"]["clipped"]
    assert not got["day"]["clipped"]
    assert not got["sector"]["clipped"]
    assert not got["turns"]["clipped"]
    assert not got["align"]["clipped"]
    assert not got["name"]["clipped"]
    assert not got["stage"]["clipped"]
    assert "Commander" in got["name"]["text"]
    assert "Opening" in got["stage"]["text"]


def test_tabs_and_ship_name_fit_at_both_sizes(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    manifest = _manifest()
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.add_init_script(
            "window.__cls = 0;"
            "new PerformanceObserver((list) => {"
            "  for (const e of list.getEntries()) if (!e.hadRecentInput) window.__cls += e.value;"
            "}).observe({type: 'layout-shift', buffered: true});"
        )
        _open(page, host, manifest)
        _assert_row(page)
        _assert_readouts(page)
        assert page.locator("#viewport + #mapCard").count() == 1
        assert page.evaluate("() => window.__cls") < 0.1
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        _open(wide, host, manifest)
        _assert_row(wide)
        _assert_readouts(wide)
        wide.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H


def test_five_tabs_share_one_row_in_firefox(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    manifest = _manifest()
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        browser = p.firefox.launch()
        for width, height in ((1440, 900), (1920, 1080)):
            page = browser.new_page(viewport={"width": width, "height": height})
            _open(page, host, manifest)
            _assert_row(page)
            _assert_readouts(page)
            page.close()
        browser.close()


def _moment(page, caption: str, digest: str) -> None:
    page.evaluate(
        """([caption, digest]) => window.TW2KMedia.keepMoment({hash: digest, trust: 'auto', caption})""",
        [caption, digest],
    )


def test_moment_play_uses_the_clip_or_the_poster(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    manifest = _manifest()
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        _open(page, host, manifest)
        _moment(page, "v2.play", "hash-play")
        page.locator("#mediaMoments li[data-hash=hash-play] button").click()
        page.wait_for_function(
            """() => {
              const s = document.querySelector('#vpClip video source');
              return s && s.src.includes('ph_warp_out_a');
            }""",
            timeout=8_000,
        )
        page.close()

        still = browser.new_page(viewport={"width": 1440, "height": 900})
        _open(still, host, manifest)
        _moment(still, "v2.still", "hash-still")
        still.locator("#mediaMoments li[data-hash=hash-still] button").click()
        still.wait_for_function(
            """() => {
              const img = document.querySelector('#vpClip img');
              const vid = document.querySelector('#vpClip video');
              return img && !img.hidden && img.src.includes('trade_port') && (!vid || vid.hidden);
            }""",
            timeout=8_000,
        )
        still.close()

        miss = browser.new_page(viewport={"width": 1440, "height": 900})
        _open(miss, host, manifest)
        _moment(miss, "v2.miss", "hash-miss")
        miss.locator("#mediaMoments li[data-hash=hash-miss] button").click()
        miss.wait_for_function(
            """() => {
              const img = document.querySelector('#vpClip img');
              const vid = document.querySelector('#vpClip video');
              return img && !img.hidden && img.src.includes('move_blocked') && vid && vid.hidden;
            }""",
            timeout=8_000,
        )
        miss.close()

        quiet = browser.new_page(viewport={"width": 1440, "height": 900})
        quiet.emulate_media(reduced_motion="reduce")
        _open(quiet, host, manifest)
        _moment(quiet, "v2.play", "hash-quiet")
        quiet.locator("#mediaMoments li[data-hash=hash-quiet] button").click()
        quiet.wait_for_function(
            """() => {
              const img = document.querySelector('#vpClip img');
              const vid = document.querySelector('#vpClip video');
              return img && !img.hidden && (!vid || vid.hidden);
            }""",
            timeout=8_000,
        )
