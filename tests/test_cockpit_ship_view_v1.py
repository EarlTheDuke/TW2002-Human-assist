"""cockpit-ship-view-v1. Every hull draws, and the red triangles match the fighters."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from tw2k.engine.models import ShipClass

from tests._cu_host import CuHost

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "cockpit-ship-view-v1"
TOK = "ship-view-v1-token-p2-00000000000"
CAP = 200
LABELS = ("Fighters", "Shields", "Holds", "armid mines", "limpet mines", "Cloaks", "Disruptors", "Towing nothing")


def _plan(fighters: int) -> tuple[int, int]:
    count = max(0, int(fighters))
    if count <= CAP:
        return count, 1
    scale = math.ceil(count / CAP)
    return math.ceil(count / scale), scale


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
    """The turn's observation is fixed until the seat acts, so wait once after the edit."""
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
            ? !!legend && legend.textContent === ("each triangle = " + scale + " fighters")
            : !legend;
          return svg.getAttribute("data-hull") === cls
            && svg.getAttribute("data-fighters") === String(fighters)
            && svg.getAttribute("data-triangles") === String(triangles)
            && svg.getAttribute("data-scale") === String(scale)
            && n === triangles
            && !!svg.querySelector("[data-testid=ship-body]")
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
    assert page.locator("[data-testid=fighter-row]").count() == 1


def _shot(page, name: str) -> None:
    page.locator("#shipSvg").evaluate("el => el.scrollIntoView({block: 'center', inline: 'nearest'})")
    path = SHOTS / name
    page.screenshot(path=str(path))
    assert path.stat().st_size > 5000, path


def test_ship_view_hulls_and_fighters(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    import tw2k.server.runner as server_runner

    # A run of waits would stand the seat down for the day. The view only needs a new observation.
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

            wide = browser.new_page(viewport={"width": 1280, "height": 800})
            phone = browser.new_page(viewport={"width": 390, "height": 844})
            url = f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}"
            wide.goto(url)
            phone.goto(url)
            wide.wait_for_selector("#shipSvg [data-testid=ship-hull]", timeout=20_000)
            phone.wait_for_selector("#shipSvg [data-testid=ship-hull]", timeout=20_000)
            assert wide.evaluate(
                "() => getComputedStyle(document.querySelector('#shipSvg .hull-float')).animationName"
            ) == "ship-float"

            bodies = {}
            samples = [(cls.value, 8 + (i % 5)) for i, cls in enumerate(ShipClass)]
            samples.extend([
                ("merchant_cruiser", 30),
                ("merchant_cruiser", 200),
                ("merchant_cruiser", 201),
                ("merchant_cruiser", 2000),
                ("escape_pod", 0),
            ])
            shot = {
                ("merchant_cruiser", 30): "merchant-cruiser-30",
                ("merchant_cruiser", 2000): "fleet-2000",
                ("escape_pod", 0): "escape-pod",
            }
            for cls, fighters in samples:
                _show(host, wide, cls, fighters)
                _wait_view(phone, cls, fighters)
                _stats_keep_the_count(wide, fighters)
                _stats_keep_the_count(phone, fighters)
                if fighters == 8 + (list(ShipClass).index(ShipClass(cls)) % 5):
                    bodies[cls] = wide.locator("[data-testid=ship-body]").inner_html()
                name = shot.get((cls, fighters))
                if name:
                    fitted = phone.evaluate(
                        """() => {
                          const doc = document.documentElement;
                          const ship = document.querySelector("#ship").getBoundingClientRect();
                          const svg = document.querySelector("#shipSvg").getBoundingClientRect();
                          const stats = document.querySelector("#shipStats").getBoundingClientRect();
                          return doc.scrollWidth <= doc.clientWidth + 1
                            && svg.width > 40
                            && svg.left >= ship.left - 1 && svg.right <= ship.right + 1
                            && stats.left >= ship.left - 1 && stats.right <= ship.right + 1
                            && stats.top >= svg.bottom - 2
                            && stats.height > 16;
                        }"""
                    )
                    assert fitted, (name, phone.viewport_size)
                    for shot_page in (wide, phone):
                        cargo_in = shot_page.evaluate(
                            """() => {
                              const ship = document.querySelector("#ship").getBoundingClientRect();
                              const holds = [...document.querySelectorAll("#holds .hold")].map((h) => {
                                const r = h.getBoundingClientRect();
                                return {t: h.innerText.replace(/\\s+/g, " "), w: Math.round(r.width), h: Math.round(r.height),
                                  top: Math.round(r.top - ship.top), bottom: Math.round(r.bottom - ship.bottom),
                                  left: Math.round(r.left - ship.left), right: Math.round(r.right - ship.right)};
                              });
                              const ok = holds.length === 4 && holds.every((r) => r.w > 24 && r.h > 12 && r.top >= -1 && r.bottom <= 1 && r.left >= -1 && r.right <= 1);
                              return ok ? "ok" : JSON.stringify({shipH: Math.round(ship.height), holds: holds});
                            }"""
                        )
                        assert cargo_in == "ok", (name, shot_page.viewport_size, cargo_in)
                    _shot(wide, f"{name}-1280.png")
                    _shot(phone, f"{name}-390.png")
            assert len(bodies) == len(ShipClass)
            assert len(set(bodies.values())) == len(bodies)

            still = browser.new_page(viewport={"width": 1280, "height": 800})
            still.emulate_media(reduced_motion="reduce")
            still.goto(url)
            still.wait_for_selector("#shipSvg .hull-float", timeout=20_000)
            assert still.evaluate(
                "() => getComputedStyle(document.querySelector('#shipSvg .hull-float')).animationName"
            ) == "none"
            still.close()
            wide.close()
            phone.close()
        finally:
            browser.close()
