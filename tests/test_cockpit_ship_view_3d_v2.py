"""cockpit-ship-view-3d-v2. A shaded model per hull, fighters orbit, stats stay put."""

from __future__ import annotations

import gzip
import math
from pathlib import Path

import pytest

from tw2k.engine.models import ShipClass

from tests._cu_host import CuHost

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "cockpit-ship-view-3d-v2"
JS = ROOT / "web" / "redesign.js"
TOK = "ship-view-3d-v2-token-p2-0000000000"
LABELS = ("Fighters", "Shields", "Holds", "armid mines", "limpet mines", "Cloaks", "Disruptors", "Towing nothing")
SHOT = {
    ("merchant_cruiser", 30): "merchant-cruiser-30",
    ("merchant_freighter", 40): "merchant-freighter",
    ("scout_marauder", 12): "scout-marauder",
    ("imperial_starship", 2000): "imperial-starship-2000",
    ("escape_pod", 0): "escape-pod",
}


def _plan(fighters: int) -> tuple[int, int]:
    count = max(0, int(fighters))
    if count < 1:
        return 0, 1
    return max(1, math.ceil(count / 100)), 100


def _set_ship(host: CuHost, cls: str, fighters: int) -> None:
    me = host.runner.state.universe.players["P2"]
    me.ship.ship_class = ShipClass(cls)
    me.ship.fighters = int(fighters)


def _your_move(page) -> None:
    page.wait_for_function(
        "() => (document.querySelector('#waitchip') || {}).textContent === 'YOUR MOVE'",
        timeout=20_000,
    )


def _show(host: CuHost, page, cls: str, fighters: int) -> None:
    _your_move(page)
    _set_ship(host, cls, fighters)
    page.keyboard.press(".")
    _wait_view(page, cls, fighters)


def _wait_view(page, cls: str, fighters: int) -> None:
    triangles, scale = _plan(fighters)
    page.wait_for_function(
        """([cls, fighters, triangles, scale]) => {
          const svg = document.querySelector("#shipSvg");
          if (!svg) return false;
          const n = svg.querySelectorAll("[data-testid=fighter-triangle]").length;
          const legend = document.querySelector("[data-testid=fighter-legend]");
          const legendOk = scale > 1
            ? !!legend && legend.textContent === "each marker = 100 fighters"
            : !legend;
          const body = svg.querySelector("[data-testid=ship-body]");
          return svg.getAttribute("data-hull") === cls
            && svg.getAttribute("data-fighters") === String(fighters)
            && svg.getAttribute("data-triangles") === String(triangles)
            && svg.getAttribute("data-scale") === String(scale)
            && svg.getAttribute("data-view") === "solid"
            && body && body.getAttribute("data-model") === "solid"
            && n === triangles
            && legendOk;
        }""",
        arg=[cls, fighters, triangles, scale],
        timeout=20_000,
    )


def _stats_keep_the_count(page, fighters: int) -> None:
    text = page.locator("#shipStats").inner_text()
    pos = -1
    for label in LABELS:
        found = text.find(label)
        assert found > pos, (label, text)
        pos = found
    bar = page.locator("#shipStats .bar").first.inner_text().replace("\n", " ")
    assert bar.startswith("Fighters")
    assert f"{int(fighters):,}" in bar


def _fitted(page) -> None:
    fitted = page.evaluate(
        """() => {
          const doc = document.documentElement;
          const ship = document.querySelector("#ship").getBoundingClientRect();
          const svg = document.querySelector("#shipSvg").getBoundingClientRect();
          const stats = document.querySelector("#shipStats").getBoundingClientRect();
          const holds = [...document.querySelectorAll("#holds .hold")].map((h) => h.getBoundingClientRect());
          const holdsOk = holds.length === 4 && holds.every((r) => r.width > 24 && r.height > 12
            && r.top >= ship.top - 1 && r.bottom <= ship.bottom + 1
            && r.left >= ship.left - 1 && r.right <= ship.right + 1);
          return doc.scrollWidth <= doc.clientWidth + 1
            && svg.width > 40
            && svg.left >= ship.left - 1 && svg.right <= ship.right + 1
            && stats.top >= svg.bottom - 2
            && stats.height > 16
            && holdsOk;
        }"""
    )
    assert fitted, page.viewport_size


def _shot(page, name: str) -> None:
    page.evaluate("() => window.__tw2kShip.hold()")
    page.locator("#shipSvg").evaluate("el => el.scrollIntoView({block: 'center', inline: 'nearest'})")
    path = SHOTS / name
    page.screenshot(path=str(path))
    assert path.stat().st_size > 5000, path


def test_ship_view_bytes_stay_under_the_budget() -> None:
    js = JS.read_text(encoding="utf-8")
    start = js.index("/* ship3d-start */")
    end = js.index("/* ship3d-end */")
    zipped = len(gzip.compress(js[start:end].encode(), 9))
    assert zipped < 300_000, zipped


def test_every_hull_has_a_shaded_model_and_fighters_match(tmp_path: Path, monkeypatch) -> None:
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
            assert legacy.locator("[data-testid=ship-view]").count() == 0
            assert legacy.locator("#shipSvg").count() == 0
            legacy.close()

            wide = browser.new_page(viewport={"width": 1366, "height": 768})
            phone = browser.new_page(viewport={"width": 390, "height": 844})
            url = f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}"
            wide.goto(url)
            phone.goto(url)
            wide.wait_for_selector("#shipSvg [data-testid=ship-hull]", timeout=20_000)
            phone.wait_for_selector("#shipSvg [data-testid=ship-hull]", timeout=20_000)
            assert wide.evaluate("() => window.__tw2kShip.motion()") == "drift"
            assert wide.evaluate(
                "() => getComputedStyle(document.querySelector('#shipSvg .hull-float')).animationName"
            ) == "ship-float"
            assert phone.evaluate("() => window.__tw2kShip.motion()") == "static"
            assert phone.evaluate("() => window.__tw2kShip.fit()") == 0.72
            assert phone.evaluate(
                "() => getComputedStyle(document.querySelector('#shipSvg .hull-float')).animationName"
            ) == "none"

            catalog = wide.evaluate(
                """(hulls) => {
                  const rows = hulls.map((hull) => ({hull, model: window.__tw2kShip.hasModel(hull), markup: window.__tw2kShip.markup(hull)}));
                  return rows;
                }""",
                arg=[cls.value for cls in ShipClass],
            )
            assert {row["hull"] for row in catalog} == {cls.value for cls in ShipClass}
            markups = []
            for row in catalog:
                assert row["model"] is True, row["hull"]
                assert "<polygon" in row["markup"], row["hull"]
                markups.append(row["markup"])
            assert len(set(markups)) == len(markups)

            signatures = {}
            samples = [(cls.value, 4) for cls in ShipClass]
            samples.extend([
                ("merchant_cruiser", 0),
                ("merchant_cruiser", 1),
                ("merchant_cruiser", 30),
                ("merchant_cruiser", 200),
                ("merchant_cruiser", 201),
                ("merchant_cruiser", 2000),
                ("merchant_freighter", 40),
                ("scout_marauder", 12),
                ("imperial_starship", 2000),
                ("escape_pod", 0),
            ])
            seen = set()
            for cls, fighters in samples:
                key = (cls, fighters)
                if key in seen:
                    continue
                seen.add(key)
                _show(host, wide, cls, fighters)
                _wait_view(phone, cls, fighters)
                wide.evaluate("() => window.__tw2kShip.hold()")
                visible = wide.evaluate(
                    """() => [...document.querySelectorAll('#shipSvg [data-testid=ship-body] polygon')]
                      .filter((p) => p.style.display !== 'none').length"""
                )
                assert visible >= 8, (cls, visible)
                if fighters == 4:
                    signatures[cls] = wide.evaluate(
                        """() => [...document.querySelectorAll('#shipSvg [data-testid=ship-body] polygon')]
                          .filter((p) => p.style.display !== 'none').map((p) => p.getAttribute('points')).join('|')"""
                    )
                if key in SHOT or fighters in (0, 1, 30, 200, 201, 2000):
                    _stats_keep_the_count(wide, fighters)
                    _stats_keep_the_count(phone, fighters)
                if key in SHOT:
                    _fitted(wide)
                    _fitted(phone)
                    _shot(wide, f"{SHOT[key]}-1366.png")
                    _shot(phone, f"{SHOT[key]}-390.png")
            assert len(signatures) == len(ShipClass)
            assert len(set(signatures.values())) == len(signatures)

            wide.evaluate("() => window.__tw2kShip.forceOutline(true)")
            wide.wait_for_function(
                """() => {
                  const svg = document.querySelector('#shipSvg');
                  const body = svg && svg.querySelector('[data-testid=ship-body]');
                  return svg && svg.getAttribute('data-view') === 'outline'
                    && body && body.getAttribute('data-model') === 'outline'
                    && body.querySelector('polygon, ellipse, rect');
                }""",
                timeout=10_000,
            )
            wide.evaluate("() => window.__tw2kShip.forceOutline(false)")
            _wait_view(wide, "escape_pod", 0)

            still = browser.new_page(viewport={"width": 1366, "height": 768})
            still.emulate_media(reduced_motion="reduce")
            still.goto(url)
            still.wait_for_selector("#shipSvg .hull-float", timeout=20_000)
            assert still.evaluate("() => window.__tw2kShip.motion()") == "still"
            assert still.evaluate(
                "() => getComputedStyle(document.querySelector('#shipSvg .hull-float')).animationName"
            ) == "none"
            still.close()
            wide.close()
            phone.close()
        finally:
            browser.close()
