"""cockpit-ship-view-plan-v1. Three hulls, counted fighter clusters, stats stay put."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from tests._cu_host import CuHost
from tw2k.engine.models import ShipClass

ROOT = Path(__file__).resolve().parents[1]
SHOTS = Path("/opt/cursor/artifacts/note116")
JS = ROOT / "web" / "redesign.js"
PLAN = ROOT / "docs" / "plans" / "cockpit-ship-view-v1.md"
TOK = "ship-view-plan-v1-token-p2-0000"
CAP = 200
CLUSTER_MAX = 4
LABELS = ("Fighters", "Shields", "Holds", "armid mines", "limpet mines", "Cloaks", "Disruptors", "Towing nothing")
VIEWPORTS = ((1280, 720), (1600, 1000), (390, 844))
PROTO = ("merchant_cruiser", "scout_marauder", "escape_pod")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _plan(fighters: int) -> tuple[int, int]:
    count = max(0, int(fighters))
    if count <= CAP:
        return count, 1
    scale = math.ceil(count / CAP)
    return math.ceil(count / scale), scale


def _clusters(cls: str, fighters: int) -> list[tuple[int, int]]:
    if cls not in PROTO:
        return []
    triangles, scale = _plan(fighters)
    if scale <= 1 or triangles < 1:
        return []
    groups = min(CLUSTER_MAX, triangles)
    base, extra = divmod(triangles, groups)
    sizes = [base + (1 if i < extra else 0) for i in range(groups)]
    last = fighters - scale * (triangles - 1)
    out: list[tuple[int, int]] = []
    idx = 0
    for use in sizes:
        count = 0
        for _ in range(use):
            count += last if idx == triangles - 1 else scale
            idx += 1
        out.append((use, count))
    return out


def test_plan_names_the_art_and_bot_stays_plain() -> None:
    plan = _text(PLAN)
    assert "NOTE 116" in plan
    assert "Recommendation" in plan
    assert "Option 2" in plan
    assert "Attribution-NonCommercial-NoDerivs" in plan
    assert "Drew Markham" in plan
    js = _text(JS)
    block = js.split("const PROTOTYPE_HULLS = ", 1)[1][:180]
    for hull in PROTO:
        assert hull in block
    assert "fighterClusters" in js
    css = _text(ROOT / "web" / "ship-view-plan.css")
    assert "fighter-cluster-count" in css
    for name in ("bot.html", "bot.js", "bot-parity.js", "layout.js", "redesign.html", "redesign.css"):
        body = _text(ROOT / "web" / name)
        assert "ship-view-plan" not in body, name
        assert "fighterClusters" not in body, name
        assert "PROTOTYPE_HULLS" not in body, name
    assert ShipClass.MERCHANT_CRUISER.value == "merchant_cruiser"


def _set_ship(host: CuHost, cls: str, fighters: int) -> None:
    me = host.runner.state.universe.players["P2"]
    me.ship.ship_class = ShipClass(cls)
    me.ship.fighters = int(fighters)


def _your_move(page) -> None:
    page.wait_for_function(
        "() => (document.querySelector('#waitchip') || {}).textContent === 'YOUR MOVE'",
        timeout=20_000,
    )


def _wait_view(page, cls: str, fighters: int) -> None:
    triangles, scale = _plan(fighters)
    clusters = _clusters(cls, fighters)
    page.wait_for_function(
        """([cls, fighters, triangles, scale, clusters, proto]) => {
          const svg = document.querySelector("#shipSvg");
          if (!svg) return false;
          const n = svg.querySelectorAll("[data-testid=fighter-triangle]").length;
          const legend = document.querySelector("[data-testid=fighter-legend]");
          const legendOk = scale > 1
            ? !!legend && legend.textContent === ("each triangle = " + scale + " fighters")
            : !legend;
          const nodes = [...svg.querySelectorAll("[data-testid=fighter-cluster]")];
          const got = nodes.map((el) => [Number(el.getAttribute("data-triangles")), Number(el.getAttribute("data-count"))]);
          const labels = nodes.map((el) => (el.querySelector("[data-testid=fighter-cluster-count]") || {}).textContent || "");
          const glow = !!svg.querySelector("[data-testid=space-glow]");
          return svg.getAttribute("data-hull") === cls
            && svg.getAttribute("data-fighters") === String(fighters)
            && svg.getAttribute("data-triangles") === String(triangles)
            && svg.getAttribute("data-scale") === String(scale)
            && svg.getAttribute("data-prototype") === (proto ? "1" : "0")
            && svg.getAttribute("data-clusters") === String(clusters.length)
            && n === triangles
            && !!svg.querySelector("[data-testid=ship-body]")
            && legendOk
            && JSON.stringify(got) === JSON.stringify(clusters)
            && JSON.stringify(labels) === JSON.stringify(clusters.map((row) => String(row[1])))
            && glow === proto;
        }""",
        arg=[cls, fighters, triangles, scale, _clusters(cls, fighters), cls in PROTO],
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
    page.evaluate("() => window.__tw2kShip.hold()")
    report = page.evaluate(
        """() => {
          const doc = document.documentElement;
          const ship = document.querySelector("#ship").getBoundingClientRect();
          const svg = document.querySelector("#shipSvg").getBoundingClientRect();
          const stats = document.querySelector("#shipStats").getBoundingClientRect();
          const holds = [...document.querySelectorAll("#holds .hold")].map((h) => h.getBoundingClientRect());
          const labels = [...document.querySelectorAll("[data-testid=fighter-cluster-count]")].map((el) => el.getBoundingClientRect());
          const holdsOk = holds.length === 4 && holds.every((r) => r.width > 24 && r.height > 12
            && r.top >= ship.top - 1 && r.bottom <= ship.bottom + 1
            && r.left >= ship.left - 1 && r.right <= ship.right + 1);
          const labelsOk = labels.every((r) => r.width > 2 && r.height > 2
            && r.left >= svg.left - 2 && r.right <= svg.right + 2
            && r.top >= svg.top - 2 && r.bottom <= svg.bottom + 2);
          const svgOk = svg.width > 40 && svg.left >= ship.left - 1 && svg.right <= ship.right + 1;
          const statsOk = stats.top >= svg.bottom - 2 && stats.height > 16
            && stats.left >= ship.left - 1 && stats.right <= ship.right + 1
            && stats.bottom <= ship.bottom + 1;
          return {
            ok: doc.scrollWidth <= doc.clientWidth + 1 && svgOk && statsOk && holdsOk && labelsOk,
            overflow: doc.scrollWidth - doc.clientWidth,
            svgOk, statsOk, holdsOk, labelsOk,
            svg: {w: Math.round(svg.width), h: Math.round(svg.height)},
            ship: {h: Math.round(ship.height)},
            stats: {h: Math.round(stats.height), bottom: Math.round(stats.bottom - ship.bottom)},
            holds: holds.map((r) => ({w: Math.round(r.width), h: Math.round(r.height),
              top: Math.round(r.top - ship.top), bottom: Math.round(r.bottom - ship.bottom),
              left: Math.round(r.left - ship.left), right: Math.round(r.right - ship.right)})),
            labelEdges: labels.map((r) => ({
              l: Math.round(r.left - svg.left), r: Math.round(r.right - svg.right),
              t: Math.round(r.top - svg.top), b: Math.round(r.bottom - svg.bottom),
            })),
          };
        }"""
    )
    assert report["ok"], json.dumps(report)


def _shot(page, name: str) -> None:
    page.evaluate("() => window.__tw2kShip.hold()")
    page.locator("#shipSvg").evaluate("el => el.scrollIntoView({block: 'center', inline: 'nearest'})")
    path = SHOTS / name
    page.screenshot(path=str(path))
    assert path.stat().st_size > 5000, path


def test_prototype_hulls_match_fighters_at_three_sizes(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    import tw2k.server.runner as server_runner

    monkeypatch.setattr(server_runner, "note_wait_streak", lambda *a, **k: 0)
    SHOTS.mkdir(parents=True, exist_ok=True)
    samples = [
        ("merchant_cruiser", 30, True),
        ("merchant_cruiser", 201, False),
        ("merchant_cruiser", 2000, True),
        ("scout_marauder", 150, True),
        ("escape_pod", 0, True),
        ("battleship", 2000, False),
    ]
    with CuHost(tmp_path, TOK, max_days=30, turns_per_day=400) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            legacy = browser.new_page(viewport={"width": 1280, "height": 720})
            legacy.goto(f"{host.base}/bot?seat=P2&token={TOK}")
            legacy.wait_for_selector("[data-testid=ship]", timeout=20_000)
            assert legacy.locator("#shipSvg").count() == 0
            assert legacy.locator("[data-testid=fighter-cluster]").count() == 0
            assert "ship-view-plan" not in legacy.content()
            legacy.close()

            url = f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}"
            pages = []
            for width, height in VIEWPORTS:
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(url)
                page.wait_for_selector("#shipSvg [data-testid=ship-hull]", timeout=20_000)
                link = page.locator("#ship-view-plan-css")
                assert link.count() == 1
                assert link.get_attribute("href") == "/static/ship-view-plan.css"
                pages.append(page)
            wide, tall, phone = pages
            assert wide.evaluate("() => window.__tw2kShip.motion()") == "drift"
            assert tall.evaluate("() => window.__tw2kShip.motion()") == "drift"
            assert phone.evaluate("() => window.__tw2kShip.motion()") == "static"
            assert phone.evaluate("() => window.__tw2kShip.fit()") == 0.72
            assert phone.evaluate(
                "() => getComputedStyle(document.querySelector('#shipSvg .hull-float')).animationName"
            ) == "none"

            driver = wide
            for cls, fighters, shoot in samples:
                _your_move(driver)
                _set_ship(host, cls, fighters)
                driver.keyboard.press(".")
                for page in pages:
                    _wait_view(page, cls, fighters)
                    _stats_keep_the_count(page, fighters)
                    _fitted(page)
                if shoot:
                    for page, (width, height) in zip(pages, VIEWPORTS, strict=True):
                        _shot(page, f"{cls}-{fighters}-{width}x{height}.png")
            wide.close()
            tall.close()
            phone.close()
        finally:
            browser.close()
