"""cockpit-warp-video-clips-v1. A real move plays a captured webm for this hull.

The file comes from window.TW2KWarpClipSource.resolve. A missing file, a
still, and reduced motion keep the live scene. Skip hides the picture.
/bot does not load the video catalog.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests._cu_host import CuHost
from tw2k.engine.models import ShipClass

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "web" / "warp-video" / "manifest.json"
HULLS = tuple(cls.value for cls in ShipClass)
MAX_BYTES = 300 * 1024


def _duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        text=True,
    ).strip()
    return float(out)


def test_manifest_lists_captured_clips_and_a_generated_slot() -> None:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert doc["version"] == 1
    about = doc["generated"]["about"]
    assert "generated (AI)" in about
    assert "webm" in about
    assert doc["generated"]["clips"] == []
    assert set(doc["hulls"]) == set(HULLS)
    for hull, rows in doc["hulls"].items():
        assert len(rows) == 10, hull
        assert [row["n"] for row in rows] == [f"{n:02d}" for n in range(1, 11)]
        for row in rows:
            assert row["id"].startswith(hull + ".")
            assert row["webm"] == f"{hull}/{row['n']}.webm"
            assert 1500 <= row["duration_ms"] <= 3000
            path = ROOT / "web" / "warp-video" / row["webm"]
            assert path.is_file(), path
            assert path.stat().st_size == row["bytes"]
            assert path.stat().st_size <= MAX_BYTES
            assert abs(_duration(path) - row["duration_ms"] / 1000) <= 0.2
    page = (ROOT / "web" / "redesign.html").read_text(encoding="utf-8")
    assert "/static/warp-video.js" in page
    script = (ROOT / "web" / "warp-video.js").read_text(encoding="utf-8")
    assert 'playback !== "move"' in script
    assert "generated" in script
    for name in ("bot.html", "bot.js", "bot-parity.js"):
        text = (ROOT / "web" / name).read_text(encoding="utf-8")
        assert "warp-video" not in text, name


def _host(tmp_path: Path, monkeypatch, token: str):
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    import tw2k.server.runner as server_runner

    monkeypatch.setattr(server_runner, "note_wait_streak", lambda *a, **k: 0)
    return CuHost(tmp_path, token, max_days=30, turns_per_day=400)


def _ready(page) -> None:
    page.wait_for_function(
        "() => window.__tw2kWarp && window.__tw2kWarp.ready() && window.TW2KWarpClipSource && window.TW2KWarpClipSource.ready",
        timeout=20_000,
    )
    page.wait_for_function(
        "() => (document.querySelector('#waitchip') || {}).textContent === 'YOUR MOVE'",
        timeout=20_000,
    )
    page.evaluate("() => window.TW2KWarpClipSource.ready")


def _sector(page) -> str:
    return page.locator("#pSector").inner_text().strip()


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


def test_video_plays_only_on_a_real_move(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    token = "warp-video-move-p2-00000000000000"
    with _host(tmp_path, monkeypatch, token) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            legacy = browser.new_page(viewport={"width": 1280, "height": 800})
            legacy.goto(f"{host.base}/bot?seat=P2&token={token}")
            legacy.wait_for_selector("[data-testid=ship]", timeout=20_000)
            assert legacy.locator("[data-testid=warp-clip]").count() == 0
            assert legacy.locator("script[src*='warp-video']").count() == 0
            legacy.close()

            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={token}")
            page.wait_for_selector("#warps button", timeout=20_000)
            _ready(page)
            assert page.locator("#warpClip").get_attribute("data-plays") == "0"
            catalog = page.evaluate(
                """async () => {
                  await window.TW2KWarpClipSource.ready;
                  const cat = window.TW2KWarpClipSource.catalog();
                  const hull = document.querySelector('#shipSvg').getAttribute('data-hull');
                  const idle = window.TW2KWarpClipSource.resolve({
                    id: hull + '.streak.01', hull: hull, playback: 'paint', duration_ms: 1600
                  });
                  const live = window.TW2KWarpClipSource.resolve({
                    id: hull + '.streak.01', hull: hull, playback: 'move', duration_ms: 1600
                  });
                  cat.generated.clips.push({
                    id: hull + '.streak.01',
                    webm: 'generated/' + hull + '/01.webm',
                    duration_ms: 2200
                  });
                  const gen = window.TW2KWarpClipSource.resolve({
                    id: hull + '.streak.01', hull: hull, playback: 'move', duration_ms: 1600
                  });
                  cat.generated.clips.length = 0;
                  return {
                    idle: idle,
                    live: live && live.webm,
                    gen: gen && gen.webm,
                    genMs: gen && gen.duration_ms,
                    about: cat.generated.about
                  };
                }"""
            )
            assert catalog["idle"] is None
            assert catalog["live"].startswith("/static/warp-video/")
            assert catalog["live"].endswith("/01.webm")
            assert "/generated/" in catalog["gen"]
            assert catalog["genMs"] == 2200
            assert "generated (AI)" in catalog["about"]

            here = _sector(page)
            before = page.locator("#lastResult").inner_text()
            page.evaluate("(t) => window.__tw2kTest.do('plot_course', {target: t, execute: false})", 1 if here != "1" else 2)
            page.wait_for_function(
                "(prev) => (document.querySelector('#lastResult').textContent || '') !== prev",
                arg=before,
                timeout=15_000,
            )
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

            first = _warp(page)
            hull = page.locator("#shipSvg").get_attribute("data-hull")
            page.wait_for_function(
                """() => {
                  const root = document.querySelector('#warpClip');
                  const video = document.querySelector('#warpVideo');
                  return root && root.getAttribute('data-kind') === 'file'
                    && video && !video.hidden && video.readyState >= 2
                    && /\\.webm($|\\?)/.test(video.currentSrc);
                }""",
                timeout=8_000,
            )
            assert first.startswith(hull + ".")
            assert page.locator("#warpClip").get_attribute("data-hull") == hull
            assert page.locator("#warpClip").get_attribute("data-clip-source") == "hook"
            assert page.locator("[data-testid=warp-body]").count() == 1
            held = page.evaluate("() => window.__tw2kWarp.hold(450)")
            assert held >= 1
            src = page.evaluate("() => document.querySelector('#warpVideo').currentSrc")
            assert src.endswith(".webm")
            assert f"/warp-video/{hull}/" in src

            second = _warp(page)
            assert second != first
            assert second.startswith(hull + ".")
            page.wait_for_function(
                "(prev) => { const v = document.querySelector('#warpVideo'); return v && !v.hidden && v.currentSrc && v.currentSrc !== prev; }",
                arg=src,
                timeout=8_000,
            )

            plays = page.locator("#warpClip").get_attribute("data-plays")
            page.locator("[data-testid=warp-skip]").click()
            page.wait_for_function("() => document.querySelector('#warpClip').hidden", timeout=2_000)
            assert page.locator("#warpClip").get_attribute("data-plays") == plays
            assert page.evaluate("() => document.querySelector('#warpVideo').paused") is True

            page.evaluate(
                """() => {
                  window.TW2KWarpClipSource = {
                    resolve() { return {kind: 'file', webm: '/static/warp-video/missing/no-such.webm'}; }
                  };
                }"""
            )
            _warp(page)
            page.wait_for_function(
                """() => {
                  const root = document.querySelector('#warpClip');
                  const video = document.querySelector('#warpVideo');
                  return root && !root.hidden && root.getAttribute('data-kind') === 'svg'
                    && video && video.hidden
                    && !!root.querySelector('[data-testid=warp-body]');
                }""",
                timeout=8_000,
            )
        finally:
            browser.close()


def test_reduced_motion_keeps_the_live_scene(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    token = "warp-video-still-p2-0000000000000"
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
            assert page.locator("#warpClip").get_attribute("data-kind") == "svg"
            assert page.evaluate("() => getComputedStyle(document.querySelector('#warpClip .warp-ship')).animationName") == "none"
            assert page.locator("[data-testid=warp-body]").count() == 1
            video = page.evaluate(
                """() => {
                  const v = document.querySelector('#warpVideo');
                  return {hidden: !v || v.hidden, paused: !v || v.paused, src: v ? (v.currentSrc || '') : ''};
                }"""
            )
            assert video["hidden"] is True
            assert video["paused"] is True
            assert video["src"] == ""
            page.locator("[data-testid=warp-skip]").click()
            page.wait_for_function("() => document.querySelector('#warpClip').hidden", timeout=2_000)
        finally:
            browser.close()
