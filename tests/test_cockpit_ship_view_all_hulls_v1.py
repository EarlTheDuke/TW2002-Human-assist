"""ship-view-all-hulls-v1. Every hull, clusters survive hide and resize, warp uses the mesh.

Each viewport runs in its own Python process so the browsers do not share one.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from tests._cu_host import CuHost
from tw2k.engine.models import ShipClass

ROOT = Path(__file__).resolve().parents[1]
SHOTS = Path("/opt/cursor/artifacts/note118")
JS = ROOT / "web" / "redesign.js"
VIEWPORTS = ("1280x720", "1600x1000", "390x844")
LABELS = ("Fighters", "Shields", "Holds", "armid mines", "limpet mines", "Cloaks", "Disruptors", "Towing nothing")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_every_hull_is_ours_and_bot_stays_plain() -> None:
    js = _text(JS)
    meshes = _text(ROOT / "web" / "hull-meshes.js")
    assert "const PROTOTYPE_HULLS" not in js
    assert "shipViewHull" in js
    assert "buildHullFaces" in js
    assert "TW2KHullMeshes" in meshes
    assert "function buildHullFaces" in meshes
    plan = _text(ROOT / "docs" / "plans" / "cockpit-ship-view-v1.md")
    assert "NOTE 118" in plan
    assert "Drew Markham" in plan
    loft = meshes.split("var LOFT = ", 1)[1][:2200]
    for cls in ShipClass:
        assert cls.value + ":" in loft
    for name in ("bot.html", "bot.js", "bot-parity.js"):
        body = _text(ROOT / "web" / name)
        assert "ship-view-plan" not in body, name
        assert "fighterClusters" not in body, name
        assert "data-mesh" not in body, name


def test_viewports_run_in_their_own_processes() -> None:
    script = str(Path(__file__).resolve())
    for spec in VIEWPORTS:
        env = os.environ.copy()
        # src before the repo root, or the child imports a stale tw2k that has no INFO_MODE.
        env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT)
        proc = subprocess.run(
            [sys.executable, script, spec],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=180,
        )
        tail = (proc.stdout or "")[-2500:] + (proc.stderr or "")[-2500:]
        assert proc.returncode == 0, spec + "\n" + tail
        assert "VIEWPORT_OK " + spec in (proc.stdout or ""), tail


def _browser(width: int, height: int) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    import tempfile

    os.environ.pop("COCKPIT_LAYOUT", None)
    os.environ.pop("TW2K_SPECTATOR_TOKEN", None)
    import tw2k.server.runner as server_runner

    server_runner.note_wait_streak = lambda *a, **k: 0
    SHOTS.mkdir(parents=True, exist_ok=True)
    tok = f"ship-view-all-v1-{width}x{height}-p2-0000"
    tmp = Path(tempfile.mkdtemp(prefix="ship-view-all-"))
    with CuHost(tmp, tok, max_days=30, turns_per_day=500) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            if width == 1280:
                legacy = browser.new_page(viewport={"width": width, "height": height})
                legacy.goto(f"{host.base}/bot?seat=P2&token={tok}")
                legacy.wait_for_selector("[data-testid=ship]", timeout=20_000)
                assert legacy.locator("#shipSvg").count() == 0
                assert "ship-view-plan" not in legacy.content()
                assert "warp-variants" not in legacy.content()
                legacy.close()

            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={tok}")
            page.wait_for_selector("#shipSvg [data-testid=ship-hull]", timeout=20_000)
            page.wait_for_function("() => window.__tw2kWarp && window.__tw2kWarp.ready()", timeout=20_000)
            bodies = {}
            for cls in ShipClass:
                fighters = 0 if cls is ShipClass.ESCAPE_POD else 4
                _show(host, page, cls.value, fighters)
                bodies[cls.value] = page.locator("[data-testid=ship-body]").inner_html()
                assert page.locator("#shipSvg").get_attribute("data-prototype") == "1"
                assert page.locator("#shipSvg").get_attribute("data-clusters") == "0"
            assert len(set(bodies.values())) == len(bodies)

            _show(host, page, "imperial_starship", 2000)
            _clusters_tidy(page, 2000)
            _stats(page, 2000)
            _shot(page, f"imperial-starship-2000-{width}x{height}.png")
            _show(host, page, "scout_marauder", 40)
            assert page.locator("[data-testid=fighter-cluster]").count() == 0
            assert page.locator("[data-testid=fighter-triangle]").count() == 40
            _shot(page, f"scout-marauder-40-{width}x{height}.png")

            _show(host, page, "battleship", 5000)
            _clusters_tidy(page, 5000)
            page.locator("[data-testid=layout-open]").click()
            page.locator("[data-testid=hide-ship]").click()
            page.wait_for_function(
                "() => document.querySelector('#ship').hidden === true",
                timeout=10_000,
            )
            assert page.locator("[data-testid=fighter-cluster]").count() == 4
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

            page.locator("[data-testid=layout-open]").click()
            for _ in range(4):
                page.locator("[data-testid=map-larger]").click()
            page.locator("[data-testid=layout-close]").click()
            splitter = page.locator("[data-testid=splitter-col-1]")
            if splitter.is_visible():
                splitter.focus()
                for _ in range(6):
                    splitter.press("Shift+ArrowRight")
            _clusters_tidy(page, 5000)
            _stats(page, 5000)
            _shot(page, f"battleship-5000-resized-{width}x{height}.png")

            mesh = page.evaluate(
                """() => {
                  const warp = window.__tw2kWarp;
                  const ship = window.__tw2kShip;
                  const hulls = ['merchant_cruiser', 'imperial_starship', 'escape_pod'];
                  const rows = hulls.map((hull) => {
                    const id = hull + '.streak.01';
                    warp.paint(hull, id);
                    const root = document.querySelector('#warpClip');
                    return {
                      hull,
                      ship: root.getAttribute('data-ship'),
                      mesh: root.getAttribute('data-mesh'),
                      faces: Number(root.getAttribute('data-faces')),
                      known: ship.faces(hull),
                      same: warp.panelMesh(hull) === ship.markup(hull),
                      polygons: (document.querySelector('[data-testid=warp-body]') || {}).innerHTML || '',
                    };
                  });
                  return rows;
                }"""
            )
            faces = set()
            for row in mesh:
                assert row["ship"] == row["hull"], row
                assert row["mesh"] in ("panel", "outline"), row
                assert row["faces"] == row["known"] and row["faces"] > 8, row
                assert row["same"] is True, row
                assert "polygon" in row["polygons"] or "<path" in row["polygons"] or "<ellipse" in row["polygons"], row["hull"]
                faces.add(row["faces"])
            assert len(faces) == 3, mesh
            page.close()
        finally:
            browser.close()


def _your_move(page) -> None:
    page.wait_for_function(
        "() => (document.querySelector('#waitchip') || {}).textContent === 'YOUR MOVE'",
        timeout=20_000,
    )


def _show(host: CuHost, page, cls: str, fighters: int) -> None:
    _your_move(page)
    me = host.runner.state.universe.players["P2"]
    me.ship.ship_class = ShipClass(cls)
    me.ship.fighters = int(fighters)
    page.keyboard.press(".")
    page.wait_for_function(
        """([cls, fighters]) => {
          const svg = document.querySelector('#shipSvg');
          return svg && svg.getAttribute('data-hull') === cls
            && svg.getAttribute('data-fighters') === String(fighters)
            && svg.querySelector('[data-testid=ship-body]');
        }""",
        arg=[cls, fighters],
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
          const ship = document.querySelector('#ship').getBoundingClientRect();
          const box = svg.getBoundingClientRect();
          const nodes = [...svg.querySelectorAll('[data-testid=fighter-cluster]')];
          const counts = nodes.map((el) => Number(el.getAttribute('data-count')));
          const labels = [...svg.querySelectorAll('[data-testid=fighter-cluster-count]')].map((el) => el.getBoundingClientRect());
          const inside = labels.every((r) => r.width > 2 && r.height > 2
            && r.left >= box.left - 4 && r.right <= box.right + 4
            && r.top >= box.top - 4 && r.bottom <= box.bottom + 4
            && r.left >= ship.left - 4 && r.right <= ship.right + 4);
          const centers = labels.map((r) => [(r.left + r.right) / 2, (r.top + r.bottom) / 2]);
          let separated = centers.length >= 2;
          for (let i = 0; i < centers.length; i++) {
            for (let j = i + 1; j < centers.length; j++) {
              const d = Math.hypot(centers[i][0] - centers[j][0], centers[i][1] - centers[j][1]);
              if (d < 10) separated = false;
            }
          }
          const body = svg.querySelector('[data-testid=ship-body]').getBoundingClientRect();
          const panel = document.querySelector('#ship');
          return {
            ok: nodes.length === 4 && counts.reduce((a, b) => a + b, 0) === fighters
              && inside && separated && body.width > 8 && body.height > 8
              && !panel.hidden && svg.getAttribute('data-panel') !== 'hidden',
            counts, inside, separated, panel: svg.getAttribute('data-panel'),
            shipHidden: panel.hidden,
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
    assert f"{int(fighters):,}" in bar


def _shot(page, name: str) -> None:
    _freeze(page)
    page.locator("#shipSvg").evaluate("el => el.scrollIntoView({block: 'center', inline: 'nearest'})")
    path = SHOTS / name
    page.screenshot(path=str(path))
    assert path.stat().st_size > 5000, path


if __name__ == "__main__":
    spec = sys.argv[1]
    w, h = spec.split("x", 1)
    _browser(int(w), int(h))
    print("VIEWPORT_OK " + spec, flush=True)
