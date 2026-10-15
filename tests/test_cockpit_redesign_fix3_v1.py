"""Landed planet screen, a command that waits its turn, a map that is not one line, phone warps."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._cu_host import CuHost

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "cockpit-redesign-fix3-v1"
TOK = "fix3-e2e-token-p2-00000000000000"


def _park_on_planet(host: CuHost) -> None:
    universe = host.runner.state.universe
    me = universe.players["P2"]
    dest = next(sector for sector in universe.sectors.values() if sector.planet_ids and sector.id > 10)
    universe.sectors[me.sector_id].occupant_ids.remove("P2")
    me.sector_id = dest.id
    if "P2" not in dest.occupant_ids:
        dest.occupant_ids.append("P2")
    me.known_sectors.add(dest.id)


def test_landed_screen_map_phone_and_wording(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as pw:
        _park_on_planet(host)
        browser = pw.chromium.launch()
        try:
            wide = browser.new_page(viewport={"width": 1920, "height": 1080})
            wide.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            wide.wait_for_selector("#warps button", timeout=20_000)
            wide.screenshot(path=str(SHOTS / "1920.png"))
            wide.close()

            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            page.wait_for_selector("#warps button", timeout=20_000)
            spread = page.evaluate(
                """() => {
                  const nodes = [...document.querySelectorAll("#map .node")];
                  const here = document.querySelector("#map .node.here circle");
                  const xs = nodes.filter((n) => !n.classList.contains("here")).map((n) => Number(n.querySelector("circle").getAttribute("cx")));
                  const same = xs.length > 1 && xs.every((x) => Math.abs(x - xs[0]) < 1);
                  return here && here.getAttribute("cx") === "0" && here.getAttribute("cy") === "0" && !same;
                }"""
            )
            assert spread
            far = page.evaluate(
                """() => {
                  const here = Number(document.querySelector("#pSector").textContent);
                  const warps = [...document.querySelectorAll("#warps button")].map((b) => parseInt(b.textContent.split(":")[1], 10));
                  const pick = [1, 2, 3, 4, 5, 50, 100].find((n) => n !== here && !warps.includes(n));
                  return String(pick || (here === 1 ? 2 : 1));
                }"""
            )
            page.keyboard.press("C")
            page.keyboard.press("F")
            page.wait_for_selector("#sectorAsk", timeout=5_000)
            page.locator("#sectorAsk").fill(far)
            page.locator("#sectorGo").click()
            page.wait_for_function(
                "() => /hops/.test(document.querySelector('#lastResult').textContent || '')",
                timeout=20_000,
            )
            said = page.locator("#lastResult").inner_text()
            assert " > " in said and "[" not in said and ".." not in said
            page.screenshot(path=str(SHOTS / "1440.png"))
            page.locator("#keys button", has_text="Land").click()
            page.wait_for_selector(".planet", timeout=20_000)
            panel = page.locator("#here").inner_text()
            for word in ("Class", "Colonists", "Citadel", "Lift off", "Take product", "Build citadel"):
                assert word in panel
            assert "off" in (page.locator("#keys button[data-key=L]").get_attribute("class") or "")
            page.screenshot(path=str(SHOTS / "1440-landed.png"))
            page.keyboard.press("Q")
            page.wait_for_function(
                "() => !document.querySelector('.planet')",
                timeout=20_000,
            )
            page.locator("#warps button").first.click()
            page.keyboard.press("A")
            page.wait_for_function(
                """() => {
                  const chip = document.querySelector("#waitchip").textContent || "";
                  const line = document.querySelector("#lastResult").textContent || "";
                  return chip === "YOUR MOVE" && line.length > 3 && !/Waiting for your turn/.test(line);
                }""",
                timeout=20_000,
            )
            page.screenshot(path=str(SHOTS / "1440-waiting.png"))
            page.close()

            mid = browser.new_page(viewport={"width": 1366, "height": 768})
            mid.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            mid.wait_for_selector("#warps button", timeout=20_000)
            inside = mid.evaluate(
                """() => {
                  const a = document.querySelector("#warps").getBoundingClientRect();
                  const b = document.querySelector("#nav").getBoundingClientRect();
                  return a.height > 16 && a.bottom <= b.bottom + 1 && a.top >= b.top - 1;
                }"""
            )
            assert inside
            mid.screenshot(path=str(SHOTS / "1366.png"))
            mid.close()

            phone = browser.new_page(viewport={"width": 390, "height": 844})
            phone.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            phone.wait_for_selector("#warps button", timeout=20_000)
            above = phone.evaluate(
                """() => {
                  const warps = document.querySelector("#warps").getBoundingClientRect();
                  const keys = document.querySelector("#keys").getBoundingClientRect();
                  return warps.height > 16 && warps.bottom <= keys.top + 1 && warps.top < window.innerHeight;
                }"""
            )
            assert above
            phone.screenshot(path=str(SHOTS / "390.png"))
            phone.close()
        finally:
            browser.close()
