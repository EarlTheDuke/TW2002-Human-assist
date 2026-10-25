"""ship-view-full-v1. Every hull turns in space from the shared mesh module.

Each viewport runs in its own Python process. The leak guard is fail mode
when this file is collected by pytest.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if __name__ == "__main__":
    _root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(_root))
    sys.path.insert(0, str(_root / "src"))

import pytest

from tests._cu_host import CuHost
from tests._screenshot import force_blocking_stdio, save_screenshot
from tw2k.engine.models import ShipClass

ROOT = Path(__file__).resolve().parents[1]
SHOTS = Path("/opt/cursor/artifacts/note126")
JS = ROOT / "web" / "redesign.js"
MESHES = ROOT / "web" / "hull-meshes.js"
VIEWPORTS = ("1280x720", "1600x1000", "390x844")
LABELS = ("Fighters", "Shields", "Holds", "armid mines", "limpet mines", "Cloaks", "Disruptors", "Towing nothing")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_meshes_are_shared_and_bot_stays_plain() -> None:
    js = _text(JS)
    meshes = _text(MESHES)
    export = _text(ROOT / "web" / "hull-meshes.mjs")
    html = _text(ROOT / "web" / "redesign.html")
    assert "window.TW2KHullMeshes" in meshes or "root.TW2KHullMeshes" in meshes
    assert "function buildHullFaces" in meshes
    assert "export const buildHullFaces" in export
    assert "Drew Markham" not in meshes
    assert "/static/hull-meshes.js" in html
    assert "TW2KHullMeshes" in js
    loft = meshes.split("var LOFT = ", 1)[1][:2200]
    for cls in ShipClass:
        assert cls.value + ":" in loft
    for name in ("bot.html", "bot.js", "bot-parity.js"):
        body = _text(ROOT / "web" / name)
        assert "hull-meshes" not in body, name
        assert "fighterClusters" not in body, name
        assert "ship-view-plan" not in body, name


def test_viewports_run_in_their_own_processes() -> None:
    script = str(Path(__file__).resolve())
    # A captured pipe fills during a long run and the next screenshot raises
    # BlockingIOError. Write the child log to a file the parent reads after.
    with tempfile.TemporaryDirectory(prefix="viewports-full-") as tmp:
        folder = Path(tmp)
        for spec in VIEWPORTS:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT)
            env["TW2K_LEAK_GUARD"] = "fail"
            out = folder / f"{spec}.out"
            err = folder / f"{spec}.err"
            with out.open("w", encoding="utf-8") as stdout, err.open("w", encoding="utf-8") as stderr:
                proc = subprocess.run(
                    [sys.executable, script, spec],
                    cwd=str(ROOT),
                    check=False,
                    stdout=stdout,
                    stderr=stderr,
                    env=env,
                    timeout=600,
                )
            text = out.read_text(encoding="utf-8", errors="replace")
            tail = (text + err.read_text(encoding="utf-8", errors="replace"))[-4000:]
            assert proc.returncode == 0, spec + "\n" + tail
            assert "VIEWPORT_OK " + spec in text, tail


def _browser(width: int, height: int) -> None:
    force_blocking_stdio()
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    import tempfile

    os.environ.pop("COCKPIT_LAYOUT", None)
    os.environ.pop("TW2K_SPECTATOR_TOKEN", None)
    os.environ.pop("V311_PROFILE", None)
    import tw2k.server.runner as server_runner

    server_runner.note_wait_streak = lambda *a, **k: 0
    SHOTS.mkdir(parents=True, exist_ok=True)
    tok = f"ship-view-full-v1-{width}x{height}-p2-0000"
    tmp = Path(tempfile.mkdtemp(prefix="ship-view-full-"))
    with CuHost(tmp, tok, max_days=30, turns_per_day=500) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            if width == 1280:
                legacy = browser.new_page(viewport={"width": width, "height": height})
                legacy.goto(f"{host.base}/bot?seat=P2&token={tok}")
                legacy.wait_for_selector("[data-testid=ship]", timeout=20_000)
                assert legacy.locator("#shipSvg").count() == 0
                assert "hull-meshes" not in legacy.content()
                assert "ship-view-plan" not in legacy.content()
                legacy.close()

            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={tok}")
            page.wait_for_selector("#shipSvg [data-testid=ship-hull]", timeout=20_000)
            page.wait_for_function("() => window.__tw2kWarp && window.__tw2kWarp.ready()", timeout=20_000)
            assert page.evaluate("() => window.__tw2kShip.meshes()") == "ship-view-full-v1"
            assert page.evaluate("() => window.TW2KHullMeshes.ids().length") == len(list(ShipClass))
            bodies = {}
            for cls in ShipClass:
                fighters = 0 if cls is ShipClass.ESCAPE_POD else 4
                shields = 0 if cls is ShipClass.ESCAPE_POD else 5000
                _show(host, page, cls.value, fighters, shields)
                svg = page.locator("#shipSvg")
                assert svg.get_attribute("data-view") == "solid"
                assert svg.get_attribute("data-meshes") == "ship-view-full-v1"
                assert svg.get_attribute("data-clusters") == "0"
                assert page.locator("[data-testid=starfield-far]").count() == 1
                assert page.locator("[data-testid=starfield-near]").count() == 1
                assert page.locator("[data-testid=space-glow]").count() == 1
                plate = page.locator("[data-testid=hull-plate-name]").inner_text().strip()
                kind = page.locator("[data-testid=hull-plate-class]").inner_text().strip().replace(" ", "_")
                assert plate
                assert kind == cls.value
                bodies[cls.value] = page.locator("[data-testid=ship-body]").inner_html()
                _shot(page, f"{cls.value}-{width}x{height}.png")
            assert len(set(bodies.values())) == len(bodies)

            _show(host, page, "scout_marauder", 40, 5000)
            assert page.locator("[data-testid=fighter-cluster]").count() == 0
            assert page.locator("[data-testid=fighter-triangle]").count() == 1
            _stats(page, 40)

            _show(host, page, "imperial_starship", 2000, 5000, "ok")
            _clusters_tidy(page, 2000)
            _stats(page, 2000)
            glow_high = float(page.locator("[data-testid=shield-glow]").get_attribute("opacity") or "0")
            assert page.locator("#shipSvg").get_attribute("data-damage") == "ok"
            assert glow_high > 0.2

            _show(host, page, "imperial_starship", 2000, 1, "low")
            assert page.locator("#shipSvg").get_attribute("data-damage") == "low"
            assert page.locator("[data-testid=hull-damage]").evaluate("el => el.style.display") != "none"
            glow_low = float(page.locator("[data-testid=shield-glow]").get_attribute("opacity") or "0")
            assert glow_low < glow_high
            _shot(page, f"imperial-starship-low-shield-{width}x{height}.png")

            if width >= 1100:
                _show(host, page, "battleship", 12, 5000)
                page.evaluate("() => window.__tw2kShip.release()")
                page.locator("[data-testid=ship-pause]").click()
                page.wait_for_function(
                    "() => document.querySelector('#shipSvg').getAttribute('data-paused') === '1'",
                    timeout=10_000,
                )
                yaw = page.locator("#shipSvg").get_attribute("data-yaw")
                page.wait_for_timeout(350)
                assert page.locator("#shipSvg").get_attribute("data-yaw") == yaw
                box = page.locator("#shipSvg").bounding_box()
                assert box and box["width"] > 40
                before = page.locator("#shipSvg").get_attribute("data-yaw")
                page.mouse.move(box["x"] + 30, box["y"] + box["height"] / 2)
                page.mouse.down()
                page.mouse.move(box["x"] + min(box["width"] - 8, 160), box["y"] + box["height"] / 2)
                page.mouse.up()
                after = page.locator("#shipSvg").get_attribute("data-yaw")
                assert before != after, (before, after)
                near = page.locator("[data-testid=starfield-near]").get_attribute("transform") or ""
                assert "translate" in near
                page.locator("[data-testid=ship-pause]").click()
                page.wait_for_function(
                    "() => document.querySelector('#shipSvg').getAttribute('data-paused') === '0'",
                    timeout=10_000,
                )

            _show(host, page, "battleship", 5000, 5000)
            _clusters_tidy(page, 5000)
            page.locator("[data-testid=layout-open]").click()
            page.locator("[data-testid=hide-ship]").click()
            page.wait_for_function("() => document.querySelector('#ship').hidden === true", timeout=10_000)
            assert page.locator("[data-testid=fighter-cluster]").count() == 0
            assert page.locator("[data-testid=fighter-triangle]").count() == 50
            page.locator("[data-testid=show-panel-ship]").click()
            page.wait_for_function(
                """() => {
                  const ship = document.querySelector('#ship');
                  const svg = document.querySelector('#shipSvg');
                  return ship && !ship.hidden && svg && svg.getAttribute('data-panel') === 'shown';
                }""",
                timeout=10_000,
            )
            page.locator("[data-testid=layout-close]").click()
            _clusters_tidy(page, 5000)
            _stats(page, 5000)

            same = page.evaluate(
                """() => {
                  const hull = 'merchant_cruiser';
                  const id = hull + '.streak.01';
                  window.__tw2kWarp.paint(hull, id);
                  const root = document.querySelector('#warpClip');
                  return {
                    ship: root.getAttribute('data-ship'),
                    faces: Number(root.getAttribute('data-faces')),
                    known: window.__tw2kShip.faces(hull),
                    module: window.TW2KHullMeshes.buildHullFaces(
                      {class: hull, transwarp: {}},
                      {accent: '#7aa2ff', detail: 'pods bridge', engines: 2, name: 'Merchant Cruiser'}
                    ).length,
                    same: window.__tw2kWarp.panelMesh(hull) === window.__tw2kShip.markup(hull),
                  };
                }"""
            )
            assert same["ship"] == "merchant_cruiser", same
            assert same["faces"] == same["known"] == same["module"], same
            assert same["faces"] > 8, same
            assert same["same"] is True, same
            page.close()

            if width == 1280:
                for cls in ShipClass:
                    _record(browser, host, tok, cls.value, 0 if cls is ShipClass.ESCAPE_POD else 4)
        finally:
            browser.close()


def _record(browser, host: CuHost, tok: str, cls: str, fighters: int) -> None:
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        record_video_dir=str(SHOTS),
        record_video_size={"width": 1280, "height": 720},
    )
    page = context.new_page()
    try:
        page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={tok}")
        page.wait_for_selector("#shipSvg [data-testid=ship-hull]", timeout=20_000)
        _show(host, page, cls, fighters, 0 if fighters == 0 else 5000)
        page.wait_for_timeout(700)
    finally:
        page.close()
        context.close()
    video = page.video
    assert video is not None
    src = Path(video.path())
    dest = SHOTS / f"{cls}.webm"
    shutil.move(str(src), dest)
    assert dest.stat().st_size > 1000, dest


def _your_move(page) -> None:
    page.wait_for_function(
        "() => (document.querySelector('#waitchip') || {}).textContent === 'YOUR MOVE'",
        timeout=20_000,
    )


def _show(host: CuHost, page, cls: str, fighters: int, shields: int | None = None, damage: str = "") -> None:
    _your_move(page)
    me = host.runner.state.universe.players["P2"]
    me.ship.ship_class = ShipClass(cls)
    me.ship.fighters = int(fighters)
    if shields is not None:
        me.ship.shields = int(shields)
    page.keyboard.press(".")
    page.wait_for_function(
        """([cls, fighters, damage]) => {
          const svg = document.querySelector('#shipSvg');
          const plate = document.querySelector('[data-testid=hull-plate-class]');
          const damageOk = !damage || svg.getAttribute('data-damage') === damage;
          return svg && svg.getAttribute('data-hull') === cls
            && svg.getAttribute('data-fighters') === String(fighters)
            && svg.querySelector('[data-testid=ship-body]')
            && plate && plate.textContent.trim().replace(/ /g, '_') === cls
            && damageOk;
        }""",
        arg=[cls, fighters, damage],
        timeout=20_000,
    )


def _freeze(page) -> None:
    page.evaluate(
        """() => {
          window.__tw2kShip.hold();
          const group = document.querySelector('#shipSvg .hull-float');
          if (group) group.style.animation = 'none';
        }"""
    )


def _clusters_tidy(page, fighters: int) -> None:
    _freeze(page)
    report = page.evaluate(
        """(fighters) => {
          const svg = document.querySelector('#shipSvg');
          const box = svg.getBoundingClientRect();
          const clusters = svg.querySelectorAll('[data-testid=fighter-cluster]').length;
          const darts = [...svg.querySelectorAll('[data-testid=fighter-triangle]')];
          const markers = fighters < 1 ? 0 : Math.max(1, Math.ceil(fighters / 100));
          const legend = document.querySelector('[data-testid=fighter-legend]');
          const legendText = legend ? legend.textContent.trim() : '';
          const legendOk = markers > 0 ? legendText === 'each marker = 100 fighters' : !legend;
          const body = svg.querySelector('[data-testid=ship-body]').getBoundingClientRect();
          let inside = true;
          darts.forEach((el) => {
            const r = el.getBoundingClientRect();
            if (r.width < 0.2 || r.height < 0.2) return;
            if (r.right < box.left - 2 || r.left > box.right + 2 || r.bottom < box.top - 2 || r.top > box.bottom + 2) inside = false;
          });
          const panel = document.querySelector('#ship');
          return {
            ok: clusters === 0 && darts.length === markers && legendOk && inside
              && body.width > 4 && body.height > 4
              && !panel.hidden && svg.getAttribute('data-panel') !== 'hidden'
              && svg.getAttribute('data-clusters') === '0',
            clusters, markers: darts.length, expect: markers, legendText, inside,
            panel: svg.getAttribute('data-panel'),
            svg: {w: Math.round(box.width), h: Math.round(box.height)},
            body: {w: Math.round(body.width), h: Math.round(body.height)},
          };
        }""",
        fighters,
    )
    assert report["ok"], report


def _stats(page, fighters: int) -> None:
    text = page.locator("#shipStats").inner_text()
    pos = -1
    for label in LABELS:
        found = text.find(label)
        assert found > pos, (label, text)
        pos = found
    bar = page.locator("#shipStats .bar").first.inner_text().replace("\n", " ")
    assert bar.startswith("Fighters")
    assert f"{int(fighters):,}" in bar or str(int(fighters)) in bar


def _shot(page, name: str) -> None:
    _freeze(page)
    page.locator("#shipSvg").evaluate("el => el.scrollIntoView({block: 'center', inline: 'nearest'})")
    path = SHOTS / name
    save_screenshot(page, path)
    assert path.stat().st_size > 5000, path


if __name__ == "__main__":
    spec = sys.argv[1]
    w, h = spec.split("x", 1)
    _browser(int(w), int(h))
    print("VIEWPORT_OK " + spec, flush=True)
