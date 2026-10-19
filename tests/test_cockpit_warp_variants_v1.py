"""cockpit-warp-variants-v1. Ten seeded pictures per hull, one at random per jump.

A real move picks a clip in the page. The pick is not sent to the server.
Reduced motion and Stills hold one frame. Viewport Off stays dark.
/bot does not load the variants.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._cu_host import CuHost
from tw2k.engine.models import ShipClass

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "web" / "media" / "warp-clips.json"
VARIANTS = ROOT / "web" / "warp-variants.js"
TOK = "warp-variants-v1-token-p2-00000000"
HULLS = tuple(cls.value for cls in ShipClass)
SHEET_HULLS = ("merchant_cruiser", "escape_pod")
SIZES = ((1280, 720), (1600, 1000), (390, 844))


def test_manifest_lists_ten_svg_variants_and_stays_small() -> None:
    doc = json.loads(MANIFEST.read_text())
    assert doc["fallback_clip"] == "warp.out"
    assert set(doc["hulls"]) == set(HULLS)
    cameras = set()
    stars = set()
    exits = set()
    for hull, rows in doc["hulls"].items():
        assert len(rows) == 10, hull
        numbers = []
        for row in rows:
            assert row["kind"] == "svg"
            assert row["duration_ms"] == 2000
            head, style, number = row["id"].rsplit(".", 2)
            assert head == hull
            assert style == row["style"]
            assert number == f"{int(number):02d}"
            numbers.append(number)
            cameras.add(row["camera"])
            stars.add(row["stars"])
            exits.add(row["exit"])
        assert numbers == [f"{n:02d}" for n in range(1, 11)]
    assert {"side", "chase", "headon", "top"} <= cameras
    assert {"streaks", "tunnel", "nebula", "sparse"} <= stars
    assert {"flash", "fold", "fade"} <= exits
    assert MANIFEST.stat().st_size < 60 * 1024
    assert VARIANTS.stat().st_size < 60 * 1024
    bot = (ROOT / "web" / "bot.html").read_text()
    assert "warp-variants" not in bot
    assert "warp-clips.json" not in (ROOT / "web" / "bot.js").read_text()


def _ready(page) -> None:
    page.wait_for_function("() => window.__tw2kWarp && window.__tw2kWarp.ready()", timeout=20_000)
    page.wait_for_function(
        "() => (document.querySelector('#waitchip') || {}).textContent === 'YOUR MOVE'",
        timeout=20_000,
    )


def _sector(page) -> str:
    return page.locator("#pSector").inner_text().strip()


def _warp_once(page) -> str:
    page.wait_for_function(
        """() => {
          const chip = document.querySelector('#waitchip');
          const btn = document.querySelector('#warps button');
          return chip && chip.textContent === 'YOUR MOVE' && btn && !btn.disabled;
        }""",
        timeout=20_000,
    )
    here = _sector(page)
    plays = page.locator("#warpClip").get_attribute("data-plays") or "0"
    page.locator("#warps button").first.click()
    page.wait_for_function(
        """([here, plays]) => {
          const sec = (document.querySelector('#pSector').textContent || '').trim();
          const root = document.querySelector('#warpClip');
          return sec && sec !== here && root && root.getAttribute('data-plays') === String(Number(plays) + 1);
        }""",
        arg=[here, plays],
        timeout=20_000,
    )
    return page.locator("#warpClip").get_attribute("data-clip") or ""


def test_variants_play_on_a_real_move_only(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    import tw2k.server.runner as server_runner

    monkeypatch.setattr(server_runner, "note_wait_streak", lambda *a, **k: 0)
    shots = tmp_path / "sheets"
    shots.mkdir()
    with CuHost(tmp_path, TOK, max_days=30, turns_per_day=800) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            legacy = browser.new_page(viewport={"width": 1280, "height": 720})
            legacy.goto(f"{host.base}/bot?seat=P2&token={TOK}")
            legacy.wait_for_selector("[data-testid=ship]", timeout=20_000)
            assert legacy.locator("[data-testid=warp-clip]").count() == 0
            assert legacy.locator("script[src*='warp-variants']").count() == 0
            legacy.close()

            wide = browser.new_page(viewport={"width": 1280, "height": 720})
            wide.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            wide.wait_for_selector("#warps button", timeout=20_000)
            _ready(wide)
            assert wide.locator("#warpClip").get_attribute("data-plays") == "0"

            same = wide.evaluate(
                """() => {
                  const api = window.TW2KWarpVariants;
                  const warp = window.__tw2kWarp;
                  const hulls = warp.hulls();
                  const rows = [];
                  let paint = 0;
                  hulls.forEach((hull) => {
                    if (warp.panelMesh(hull) !== window.__tw2kShip.markup(hull)) rows.push(hull + ' mesh');
                    const ids = [];
                    api.styles.forEach((style) => {
                      const id = hull + '.' + style.style + '.' + style.n;
                      warp.paint(hull, id);
                      const root = document.querySelector('#warpClip');
                      const body = document.querySelector('[data-testid=warp-body]');
                      const html = body ? body.innerHTML : '';
                      paint = Math.max(paint, Number(root.getAttribute('data-paint-ms')) || 0);
                      if (root.getAttribute('data-clip') !== id) rows.push(id + ' clip');
                      if (root.getAttribute('data-ship') !== hull) rows.push(id + ' ship');
                      if (root.getAttribute('data-camera') !== style.camera) rows.push(id + ' camera');
                      if (!html || (html.indexOf('polygon') < 0 && html.indexOf('<path') < 0)) rows.push(id + ' empty');
                      warp.paint(hull, id);
                      const again = document.querySelector('[data-testid=warp-body]').innerHTML;
                      if (again !== html) rows.push(id + ' unstable');
                      ids.push(html);
                    });
                    if (new Set(ids).size < 6) rows.push(hull + ' variants look alike');
                  });
                  const hull = document.querySelector('#shipSvg').getAttribute('data-hull');
                  return {rows, paint, hull};
                }"""
            )
            assert same["rows"] == [], same["rows"][:12]
            assert same["paint"] < 16, same["paint"]

            for hull in SHEET_HULLS:
                for n in range(1, 11):
                    wide.evaluate(
                        """([hull, n]) => {
                          const style = window.TW2KWarpVariants.styles[n - 1];
                          window.__tw2kWarp.paint(hull, hull + '.' + style.style + '.' + style.n);
                        }""",
                        [hull, n],
                    )
                    wide.locator("#warpSvg").screenshot(path=str(shots / f"{hull}-{n:02d}.png"))

            frame = wide.evaluate(
                """() => new Promise((resolve) => {
                  const costs = [];
                  let n = 0;
                  const step = () => {
                    const t0 = performance.now();
                    document.querySelector('#warpSvg').getBoundingClientRect();
                    costs.push(performance.now() - t0);
                    if (++n < 12) requestAnimationFrame(step);
                    else resolve(Math.max.apply(null, costs));
                  };
                  requestAnimationFrame(step);
                })"""
            )
            assert frame < 16, frame

            here = _sector(wide)
            before_plays = wide.locator("#warpClip").get_attribute("data-plays")
            before_result = wide.locator("#lastResult").inner_text()
            wide.evaluate("(t) => window.__tw2kTest.do('plot_course', {target: t, execute: false})", 1 if here != "1" else 2)
            wide.wait_for_function(
                "(prev) => (document.querySelector('#lastResult').textContent || '') !== prev",
                arg=before_result,
                timeout=15_000,
            )
            assert _sector(wide) == here
            assert wide.locator("#warpClip").get_attribute("data-plays") == before_plays
            before_result = wide.locator("#lastResult").inner_text()
            wide.evaluate("() => window.__tw2kTest.do('warp', {target: 999999})")
            wide.wait_for_function(
                "(prev) => (document.querySelector('#lastResult').textContent || '') !== prev",
                arg=before_result,
                timeout=15_000,
            )
            assert _sector(wide) == here
            assert wide.locator("#warpClip").get_attribute("data-plays") == before_plays

            seen = []
            paints = []
            for _ in range(20):
                clip = _warp_once(wide)
                seen.append(clip)
                paints.append(float(wide.locator("#warpClip").get_attribute("data-paint-ms") or "99"))
                hull_now = wide.locator("#shipSvg").get_attribute("data-hull") or ""
                assert wide.locator("#warpClip").get_attribute("data-ship") == hull_now
                assert clip.startswith(hull_now + ".")
            assert len(set(seen)) >= 6, seen
            assert all(seen[i] != seen[i + 1] for i in range(19)), seen
            assert max(paints) < 16, paints
            (shots / "frame-ms.txt").write_text(
                f"preview {same['paint']}\njump {max(paints)}\nframe {frame}\n"
            )

            wide.locator("[data-testid=viewport-mode-stills]").click()
            wide.wait_for_function(
                "() => document.querySelector('#viewport').getAttribute('data-mode') === 'stills'",
                timeout=10_000,
            )
            still_id = _warp_once(wide)
            assert wide.locator("#warpClip").get_attribute("data-motion") == "still"
            assert wide.evaluate("() => getComputedStyle(document.querySelector('#warpClip .warp-ship')).animationName") == "none"
            assert still_id

            wide.locator("[data-testid=viewport-mode-off]").click()
            wide.wait_for_function(
                "() => document.querySelector('#viewport').getAttribute('data-mode') === 'off'",
                timeout=10_000,
            )
            off_here = _sector(wide)
            off_plays = wide.locator("#warpClip").get_attribute("data-plays")
            wide.locator("#warps button").first.click()
            wide.wait_for_function(
                "(here) => (document.querySelector('#pSector').textContent || '').trim() !== here",
                arg=off_here,
                timeout=20_000,
            )
            assert wide.locator("#warpClip").is_hidden()
            assert wide.evaluate(
                """() => {
                  const shown = document.querySelector('[data-testid=viewport-clip]:not([hidden])');
                  return !shown;
                }"""
            )
            assert wide.locator("#warpClip").get_attribute("data-plays") == off_plays

            reduce = browser.new_page(viewport={"width": 1280, "height": 720})
            reduce.emulate_media(reduced_motion="reduce")
            reduce.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            reduce.wait_for_selector("#warps button", timeout=20_000)
            _ready(reduce)
            _warp_once(reduce)
            assert reduce.locator("#warpClip").get_attribute("data-motion") == "still"
            assert reduce.evaluate("() => getComputedStyle(document.querySelector('#warpClip .warp-ship')).animationName") == "none"
            assert reduce.locator("[data-testid=warp-body]").count() == 1

            for width, height in SIZES[1:]:
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
                page.wait_for_selector("#warps button", timeout=20_000)
                _ready(page)
                _warp_once(page)
                assert page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
                assert page.evaluate(
                    """() => {
                      const a = document.querySelector('#warpClip').getBoundingClientRect();
                      const b = document.querySelector('#viewport').getBoundingClientRect();
                      return a.width > 40 && a.top >= b.top - 1 && a.bottom <= b.bottom + 1
                        && a.left >= b.left - 1 && a.right <= b.right + 1;
                    }"""
                )
                page.close()
        finally:
            browser.close()

    paint_note = shots / "frame-ms.txt"
    assert paint_note.is_file()
    art = Path("/opt/cursor/artifacts/note111-warp")
    art.mkdir(parents=True, exist_ok=True)
    for png in shots.glob("*.png"):
        (art / png.name).write_bytes(png.read_bytes())
    (art / "frame-ms.txt").write_text(paint_note.read_text())
    _contact_sheet(shots, art)


def _contact_sheet(shots: Path, art: Path) -> None:
    from PIL import Image, ImageDraw

    tiles = []
    for hull in SHEET_HULLS:
        row = []
        for n in range(1, 11):
            img = Image.open(shots / f"{hull}-{n:02d}.png").convert("RGB")
            img.thumbnail((180, 120))
            row.append(img)
        tiles.append(row)
    width = max(img.width for row in tiles for img in row)
    height = max(img.height for row in tiles for img in row)
    sheet = Image.new("RGB", (width * 10, height * 2 + 28), (0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    for r, hull in enumerate(SHEET_HULLS):
        draw.text((4, r * height), hull, fill=(180, 220, 255))
        for c, img in enumerate(tiles[r]):
            sheet.paste(img, (c * width, 16 + r * height))
    sheet.save(art / "contact-sheet.png")
