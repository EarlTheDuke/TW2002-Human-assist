"""cockpit-warp-clips-per-hull-v1. Ten short clips per hull, the ship you fly.

A real move plays one. A refused warp, a plot, and another seat's warp do not.
The next clip is a different picture. prefers-reduced-motion holds a still,
and Skip hides the picture. /bot without the redesign layout has none of this.
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
MESH = ROOT / "web" / "hull-mesh.js"
WARP_HULL = ROOT / "web" / "warp-hull.mjs"
ART = Path("/opt/cursor/artifacts/note127-warp")
HULLS = tuple(cls.value for cls in ShipClass)
SHEET = ("merchant_cruiser", "scout_marauder")
SCENES = (
    ("streak", "side", "streaks", "jump", 1600),
    ("chase", "chase", "streaks", "fade", 1800),
    ("headon", "headon", "tunnel", "flash", 2100),
    ("top", "top", "sparse", "fade", 2400),
    ("side", "side", "nebula", "fold", 2700),
    ("gate", "gate", "gate", "gate", 1500),
    ("headon", "headon", "sparse", "fade", 1900),
    ("top", "top", "streaks", "flash", 2300),
    ("side", "side", "tunnel", "fade", 2600),
    ("chase", "chase", "nebula", "flash", 3000),
)


def _host(tmp_path: Path, monkeypatch, token: str):
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    import tw2k.server.runner as server_runner

    monkeypatch.setattr(server_runner, "note_wait_streak", lambda *a, **k: 0)
    return CuHost(tmp_path, token, max_days=30, turns_per_day=400)


def _ready(page) -> None:
    page.wait_for_function(
        "() => window.__tw2kWarp && window.__tw2kWarp.ready() && window.TW2KWarpHull && window.TW2KWarpHull.source === 'note126'",
        timeout=20_000,
    )
    page.wait_for_function(
        "() => (document.querySelector('#waitchip') || {}).textContent === 'YOUR MOVE'",
        timeout=20_000,
    )


def _sector(page) -> str:
    return page.locator("#pSector").inner_text().strip()


def _open(browser, base: str, token: str, **kwargs):
    page = browser.new_page(viewport={"width": 1280, "height": 800}, **kwargs)
    page.goto(f"{base}/bot?layout=redesign&seat=P2&token={token}")
    page.wait_for_selector("#warps button", timeout=20_000)
    _ready(page)
    return page


def _warp(page) -> str:
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
          return sec && sec !== here && root && !root.hidden
            && root.getAttribute('data-plays') === String(Number(plays) + 1);
        }""",
        arg=[here, plays],
        timeout=20_000,
    )
    return page.locator("#warpClip").get_attribute("data-clip") or ""


def test_ten_variants_per_hull_and_bot_stays_plain() -> None:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert doc["version"] == 3
    assert doc["fallback_clip"] == "warp.out"
    assert set(doc["hulls"]) == set(HULLS)
    cameras, stars, exits = set(), set(), set()
    for hull, rows in doc["hulls"].items():
        assert len(rows) == 10, hull
        assert len({row["id"] for row in rows}) == 10
        for n, (row, scene) in enumerate(zip(rows, SCENES), start=1):
            style, camera, field, exit_, ms = scene
            assert row["id"] == f"{hull}.{style}.{n:02d}"
            assert row["kind"] == "svg"
            assert row["style"] == style
            assert row["camera"] == camera
            assert row["stars"] == field
            assert row["exit"] == exit_
            assert row["duration_ms"] == ms
            assert 1500 <= ms <= 3000
            cameras.add(camera)
            stars.add(field)
            exits.add(exit_)
    assert {"side", "chase", "headon", "top", "gate"} <= cameras
    assert {"streaks", "tunnel", "nebula", "sparse", "gate"} <= stars
    assert {"jump", "flash", "fold", "fade", "gate"} <= exits
    script = VARIANTS.read_text(encoding="utf-8")
    assert "TW2KWarpClipSource" in script
    assert "resolve(chosen)" in script
    for _style, _camera, _field, _exit, ms in SCENES:
        assert f"duration_ms: {ms}" in script
    mesh = MESH.read_text(encoding="utf-8")
    assert 'source: "note118"' in mesh
    loader = WARP_HULL.read_text(encoding="utf-8")
    assert 'from "/static/hull-meshes.mjs"' in loader
    assert "buildHullFaces" in loader and "projectFace" in loader and "hullMarkup" in loader
    assert "note118" in loader
    page = (ROOT / "web" / "redesign.html").read_text(encoding="utf-8")
    assert "warp-hull.mjs" in page and "/static/hull-meshes.js" in page and "warp-skip" in page
    assert 'src="/static/hull-mesh.js"' not in page
    bot = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")
    assert "hull-mesh" not in bot and "warp-variants" not in bot and "warp-skip" not in bot
    assert "warp-clips.json" not in (ROOT / "web" / "bot.js").read_text(encoding="utf-8")


def test_clip_plays_only_on_a_real_move(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    token = "warp-per-hull-move-p2-000000000000"
    with _host(tmp_path, monkeypatch, token) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            legacy = browser.new_page(viewport={"width": 1280, "height": 800})
            legacy.goto(f"{host.base}/bot?seat=P2&token={token}")
            legacy.wait_for_selector("[data-testid=ship]", timeout=20_000)
            assert legacy.locator("[data-testid=warp-clip]").count() == 0
            assert legacy.locator("script[src*='hull-mesh']").count() == 0
            legacy.close()

            page = _open(browser, host.base, token)
            assert page.locator("#warpClip").get_attribute("data-plays") == "0"
            here = _sector(page)
            before = page.locator("#lastResult").inner_text()
            page.evaluate("(t) => window.__tw2kTest.do('plot_course', {target: t, execute: false})", 1 if here != "1" else 2)
            page.wait_for_function(
                "(prev) => (document.querySelector('#lastResult').textContent || '') !== prev",
                arg=before,
                timeout=15_000,
            )
            assert _sector(page) == here
            assert page.locator("#warpClip").is_hidden()
            assert page.locator("#warpClip").get_attribute("data-plays") == "0"

            before = page.locator("#lastResult").inner_text()
            page.evaluate("() => window.__tw2kTest.do('warp', {target: 999999})")
            page.wait_for_function(
                "(prev) => (document.querySelector('#lastResult').textContent || '') !== prev",
                arg=before,
                timeout=15_000,
            )
            assert _sector(page) == here
            assert page.locator("#warpClip").get_attribute("data-plays") == "0"

            quiet = page.evaluate(
                """async () => {
                  const root = document.querySelector('#warpClip');
                  const before = root.getAttribute('data-plays');
                  const self = window.__tw2kWarp.selfId();
                  const other = await window.__tw2kWarp.consider([
                    {kind: 'warp', actor_id: 'P9', facts: {from: 1, to: 2}, sector_id: 1}
                  ]);
                  const same = await window.__tw2kWarp.consider([
                    {kind: 'warp', actor_id: self, facts: {from: 4, to: 4}, sector_id: 4}
                  ]);
                  return {before, after: root.getAttribute('data-plays'), other, same, self, hidden: root.hidden};
                }"""
            )
            assert quiet["self"] == "P2"
            assert quiet["other"] is False and quiet["same"] is False
            assert quiet["before"] == "0" and quiet["after"] == "0" and quiet["hidden"] is True

            clip = _warp(page)
            hull = page.locator("#shipSvg").get_attribute("data-hull")
            assert clip.startswith(hull + ".")
            assert page.locator("#warpClip").get_attribute("data-hull") == hull
            assert page.locator("#warpClip").get_attribute("data-ship") == hull
            assert page.locator("[data-testid=warp-body]").count() == 1
        finally:
            browser.close()


def test_random_clip_does_not_repeat(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    token = "warp-per-hull-bag-p2-0000000000000"
    with _host(tmp_path, monkeypatch, token) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = _open(browser, host.base, token)
            bag = page.evaluate(
                """() => {
                  const hull = document.querySelector('#shipSvg').getAttribute('data-hull');
                  const ids = [];
                  for (let i = 0; i < 20; i++) ids.push(window.__tw2kWarp.pick(hull).id);
                  return {hull, ids};
                }"""
            )
            ids = bag["ids"]
            assert len(ids) == 20
            assert all(item.startswith(bag["hull"] + ".") for item in ids)
            assert len(set(ids)) == 10
            assert all(ids[i] != ids[i + 1] for i in range(len(ids) - 1)), ids
            live = [_warp(page) for _ in range(6)]
            assert all(live[i] != live[i + 1] for i in range(5)), live
            assert all(item.startswith(bag["hull"] + ".") for item in live)
        finally:
            browser.close()


def test_clip_matches_the_flying_hull(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    token = "warp-per-hull-mesh-p2-000000000000"
    shots = tmp_path / "sheet"
    shots.mkdir()
    with _host(tmp_path, monkeypatch, token) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = _open(browser, host.base, token)
            drawn = page.evaluate(
                """() => {
                  const api = window.TW2KWarpVariants;
                  const warp = window.__tw2kWarp;
                  const mesh = window.TW2KWarpHull;
                  const problems = [];
                  const hulls = ['merchant_cruiser', 'scout_marauder'];
                  if (!mesh || mesh.source !== 'note126') problems.push('source ' + (mesh && mesh.source));
                  if (mesh.hullMarkup !== window.TW2KHullMeshes.markup) problems.push('not the panel markup');
                  hulls.forEach((hull) => {
                    const sample = {class: hull, fighters: 0, shields: 0, shield_cap: 0, transwarp: {}};
                    const def = {accent: '#7aa2ff', detail: 'bridge', engines: 2};
                    const faces = mesh.buildHullFaces(sample, def);
                    if (!faces || faces.length < 8) problems.push(hull + ' faces');
                    api.styles.forEach((style) => {
                      const id = hull + '.' + style.style + '.' + style.n;
                      warp.paint(hull, id);
                      const root = document.querySelector('#warpClip');
                      const body = document.querySelector('[data-testid=warp-body]');
                      const html = body ? body.innerHTML : '';
                      if (root.getAttribute('data-hull') !== hull) problems.push(id + ' hull');
                      if (root.getAttribute('data-ship') !== hull) problems.push(id + ' ship');
                      if (root.getAttribute('data-camera') !== style.camera) problems.push(id + ' camera');
                      if (root.getAttribute('data-stars') !== style.stars) problems.push(id + ' stars');
                      if (root.getAttribute('data-exit') !== style.exit) problems.push(id + ' exit');
                      if (Number(root.getAttribute('data-duration')) !== style.duration_ms) problems.push(id + ' duration');
                      if (root.getAttribute('data-mesh-source') !== 'note126') problems.push(id + ' mesh');
                      if (root.getAttribute('data-clip-source') !== 'procedural') problems.push(id + ' procedural');
                      const yaw0 = Number(root.getAttribute('data-yaw'));
                      warp.hold(1000);
                      const yaw1 = Number(root.getAttribute('data-yaw'));
                      const spun = document.querySelector('[data-testid=warp-body]').innerHTML;
                      if (Math.abs(yaw1 - yaw0 - 0.28) > 0.02) problems.push(id + ' spin ' + yaw0 + ' ' + yaw1);
                      if (spun === html) problems.push(id + ' did not rotate');
                      warp.hold(0);
                      const anim = document.querySelector('#warpClip .warp-ship');
                      const timing = anim && anim.getAnimations()[0];
                      const ms = timing ? timing.effect.getTiming().duration : 0;
                      if (ms !== style.duration_ms) problems.push(id + ' anim ' + ms);
                      if (!html || html.indexOf('polygon') < 0) problems.push(id + ' empty');
                    });
                  });
                  const merchant = (function () {
                    warp.paint('merchant_cruiser', 'merchant_cruiser.streak.01');
                    return document.querySelector('[data-testid=warp-body]').innerHTML;
                  })();
                  const scout = (function () {
                    warp.paint('scout_marauder', 'scout_marauder.streak.01');
                    return document.querySelector('[data-testid=warp-body]').innerHTML;
                  })();
                  if (merchant === scout) problems.push('same mesh');
                  window.TW2KWarpClipSource = {
                    resolve(chosen) {
                      if (chosen.id !== 'merchant_cruiser.gate.06') return null;
                      return {kind: 'file', webm: 'clips/merchant-gate.webm', duration_ms: 1500};
                    }
                  };
                  warp.paint('merchant_cruiser', 'merchant_cruiser.streak.01');
                  const kept = document.querySelector('#warpClip').getAttribute('data-clip-source');
                  warp.paint('merchant_cruiser', 'merchant_cruiser.gate.06');
                  const root = document.querySelector('#warpClip');
                  const video = document.querySelector('#warpVideo');
                  const hooked = {
                    kept: kept,
                    source: root.getAttribute('data-clip-source'),
                    kind: root.getAttribute('data-kind'),
                    src: video ? video.getAttribute('src') || video.src || '' : '',
                  };
                  delete window.TW2KWarpClipSource;
                  return {problems, hooked};
                }"""
            )
            assert drawn["problems"] == [], drawn["problems"][:16]
            assert drawn["hooked"]["kept"] == "procedural"
            assert drawn["hooked"]["source"] == "hook"
            assert drawn["hooked"]["kind"] == "file"
            assert drawn["hooked"]["src"].endswith("/static/media/clips/merchant-gate.webm")

            for hull in SHEET:
                for n in range(1, 11):
                    page.evaluate(
                        """([hull, n]) => {
                          const style = window.TW2KWarpVariants.styles[n - 1];
                          window.__tw2kWarp.paint(hull, hull + '.' + style.style + '.' + style.n);
                          window.__tw2kWarp.hold(400);
                        }""",
                        [hull, n],
                    )
                    page.locator("#warpSvg").screenshot(path=str(shots / f"{hull}-{n:02d}.png"))

            me = host.runner.state.universe.players["P2"]
            me.ship.ship_class = ShipClass.SCOUT_MARAUDER
            page.keyboard.press(".")
            page.wait_for_function(
                "() => document.querySelector('#shipSvg').getAttribute('data-hull') === 'scout_marauder'",
                timeout=20_000,
            )
            clip = _warp(page)
            assert clip.startswith("scout_marauder.")
            assert page.locator("#warpClip").get_attribute("data-hull") == "scout_marauder"
            assert page.locator("#warpClip").get_attribute("data-ship") == "scout_marauder"
            assert page.locator("#shipSvg").get_attribute("data-hull") == "scout_marauder"
        finally:
            browser.close()
    _contact_sheet(shots)


def test_skip_click_hides_the_clip(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    token = "warp-per-hull-skip-p2-000000000000"
    with _host(tmp_path, monkeypatch, token) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = _open(browser, host.base, token)
            _warp(page)
            assert page.locator("[data-testid=warp-skip]").is_visible()
            plays = page.locator("#warpClip").get_attribute("data-plays")
            page.locator("[data-testid=warp-skip]").click()
            page.wait_for_function("() => document.querySelector('#warpClip').hidden", timeout=2_000)
            assert page.locator("#warpClip").get_attribute("data-plays") == plays
        finally:
            browser.close()


def test_reduced_motion_holds_a_still(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    token = "warp-per-hull-still-p2-00000000000"
    with _host(tmp_path, monkeypatch, token) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.emulate_media(reduced_motion="reduce")
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={token}")
            page.wait_for_selector("#warps button", timeout=20_000)
            _ready(page)
            _warp(page)
            assert page.locator("#warpClip").get_attribute("data-motion") == "still"
            assert page.evaluate("() => getComputedStyle(document.querySelector('#warpClip .warp-ship')).animationName") == "none"
            assert page.locator("[data-testid=warp-body]").count() == 1
            assert page.locator("[data-testid=warp-skip]").is_visible()
            page.locator("[data-testid=warp-skip]").click()
            page.wait_for_function("() => document.querySelector('#warpClip').hidden", timeout=2_000)
        finally:
            browser.close()


def _contact_sheet(shots: Path) -> None:
    from PIL import Image, ImageDraw

    tiles = []
    for hull in SHEET:
        row = []
        for n in range(1, 11):
            img = Image.open(shots / f"{hull}-{n:02d}.png").convert("RGB")
            img.thumbnail((180, 120))
            row.append(img)
        tiles.append(row)
    width = max(img.width for row in tiles for img in row)
    height = max(img.height for row in tiles for img in row)
    sheet = Image.new("RGB", (width * 10, height * 2 + 36), (0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    for r, hull in enumerate(SHEET):
        draw.text((4, r * (height + 8)), hull, fill=(180, 220, 255))
        for c, img in enumerate(tiles[r]):
            sheet.paste(img, (c * width, 18 + r * (height + 8)))
    ART.mkdir(parents=True, exist_ok=True)
    sheet.save(ART / "contact-sheet.png")
