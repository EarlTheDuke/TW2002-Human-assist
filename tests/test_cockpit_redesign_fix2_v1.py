"""The second cockpit fix list: forms stay open, warps stay on screen, names and a course prompt."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._cu_host import CuHost

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "cockpit-redesign-fix2-v1"
TOK = "fix2-e2e-token-p2-00000000000000"


def _inside(page, child: str, parent: str) -> bool:
    return page.evaluate(
        """([child, parent]) => {
          const a = document.querySelector(child).getBoundingClientRect();
          const b = document.querySelector(parent).getBoundingClientRect();
          return a.height > 16 && a.top >= b.top - 1 && a.bottom <= b.bottom + 1 && a.left >= b.left - 1 && a.right <= b.right + 1;
        }""",
        [child, parent],
    )


def test_fix_list(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            wide = browser.new_page(viewport={"width": 1920, "height": 1080})
            wide.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            wide.wait_for_selector(".porttbl", timeout=20_000)
            assert wide.locator("#waitchip").inner_text() == "YOUR MOVE"
            wide.screenshot(path=str(SHOTS / "1920.png"))
            wide.close()

            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            page.wait_for_selector("#warps button", timeout=20_000)
            assert _inside(page, "#warps", "#nav")
            assert _inside(page, "#shipStats", "#ship")
            assert _inside(page, "#holds", "#ship")
            names = page.evaluate(
                """async (token) => {
                  const headers = {"Content-Type": "application/json", "X-TW2K-Seat": "P2", Authorization: "Bearer " + token};
                  const obs = await fetch("/harness/v1/P2/observation?wait_s=0&peek=1&format=both", {headers}).then((r) => r.json());
                  const here = obs.observation.sector || {};
                  const roster = obs.observation.other_players || [];
                  return (here.occupants || []).map((id) => {
                    const row = roster.find((r) => r.id === id);
                    return row && row.name ? row.name : "";
                  }).filter(Boolean);
                }""",
                TOK,
            )
            sector = page.locator("#sectorText").inner_text()
            for name in names:
                assert name in sector
            assert "Traders : P" not in sector
            warps_drawn = page.evaluate(
                """() => {
                  const want = [...document.querySelectorAll("#warps button")].map((b) => b.textContent.split(":")[1].split(" ")[0]);
                  const have = [...document.querySelectorAll("#map .node")].map((n) => n.dataset.id);
                  return want.every((id) => have.includes(id));
                }"""
            )
            assert warps_drawn
            page.screenshot(path=str(SHOTS / "1440.png"))
            page.keyboard.press("P")
            page.wait_for_selector(".frm", timeout=10_000)
            qty = page.locator(".frm input[data-n=qty]")
            qty.fill("7")
            page.wait_for_timeout(3200)
            assert page.locator(".frm").count() == 1
            assert qty.input_value() == "7"
            page.screenshot(path=str(SHOTS / "1440-form.png"))
            page.keyboard.press("Escape")
            page.keyboard.press("C")
            page.keyboard.press("F")
            page.wait_for_selector("#menu[data-screen=ask-sector]", timeout=5_000)
            assert "What is the destination sector?" in page.locator("#menu").inner_text()
            page.screenshot(path=str(SHOTS / "1440-course.png"))
            page.keyboard.press("Escape")
            page.locator("#keys button", has_text="Long Range").click()
            reason = page.locator("#lastResult").inner_text()
            assert "buy_equip" not in reason
            assert "_" not in reason
            page.locator("#warps button").first.click()
            page.wait_for_function(
                "() => /Turns spent/.test(document.querySelector('#lastResult').textContent || '')",
                timeout=20_000,
            )
            done = page.locator("#lastResult").inner_text()
            assert "M —" not in done and "C.F" not in done
            page.close()

            mid = browser.new_page(viewport={"width": 1366, "height": 768})
            mid.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            mid.wait_for_selector("#warps button", timeout=20_000)
            assert _inside(mid, "#warps", "#nav")
            assert _inside(mid, "#shipStats", "#ship")
            assert _inside(mid, "#holds", "#ship")
            mid.screenshot(path=str(SHOTS / "1366.png"))
            mid.close()

            phone = browser.new_page(viewport={"width": 390, "height": 844})
            phone.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            phone.wait_for_selector("#keys button", timeout=20_000)
            phone.locator("#keys button", has_text="Attack").click()
            phone.wait_for_function(
                "() => (document.querySelector('#lastResult').textContent || '').length > 3",
                timeout=10_000,
            )
            visible = phone.evaluate(
                """() => {
                  const keys = document.querySelector("#keys").getBoundingClientRect();
                  const last = document.querySelector("#lastResult").getBoundingClientRect();
                  const h = window.innerHeight;
                  return keys.height > 24 && last.top < h && last.bottom <= h + 1 && keys.top < h;
                }"""
            )
            assert visible
            phone.screenshot(path=str(SHOTS / "390.png"))
            phone.close()
        finally:
            browser.close()
