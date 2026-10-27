"""Screens of the wired cockpit, and the old page stays the default."""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

import pytest

from tests._cu_host import CuHost

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "cockpit-redesign-gate-v1"
TOK = "gate-e2e-token-p2-000000000000000"


def test_default_page_stays_the_old_cockpit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.setenv("TW2K_SPECTATOR_TOKEN", "not-the-seat-token")
    with CuHost(tmp_path, TOK) as host:
        old = urlopen(host.base + "/bot", timeout=10).read().decode("utf-8")
        new = urlopen(host.base + "/bot?layout=redesign", timeout=10).read().decode("utf-8")
    assert "Grok Bot Cockpit" in old and "NAV COMPUTER" not in old
    assert "NAV COMPUTER" in new and "onclick=\"form(" not in new


def test_play_screens(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for width, height, name in ((1920, 1080, "1920-port.png"), (1440, 900, "1440-port.png"), (390, 844, "390-phone.png")):
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
                page.wait_for_selector(".porttbl", timeout=20_000)
                page.screenshot(path=str(SHOTS / name))
                page.close()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            page.wait_for_selector(".porttbl", timeout=20_000)
            page.locator("#keys button", has_text="Attack").click()
            page.wait_for_function(
                "() => (document.querySelector('#lastResult').textContent || '').length > 3",
                timeout=10_000,
            )
            page.screenshot(path=str(SHOTS / "1440-refused.png"))
            page.locator("#keys button", has_text="Ship Info").click()
            page.wait_for_selector("#menu[data-screen=ship-info]", timeout=5_000)
            page.screenshot(path=str(SHOTS / "1440-ship.png"))
            page.keyboard.press("Escape")
            info = page.evaluate(
                """async (token) => {
                  const headers = {"Content-Type": "application/json", "X-TW2K-Seat": "P2", Authorization: "Bearer " + token};
                  const obs = await fetch("/harness/v1/P2/observation?wait_s=0&peek=1&format=both", {headers}).then((r) => r.json());
                  const here = Number(obs.observation.sector.id);
                  const target = here === 1 ? 2 : 1;
                  const posted = await fetch("/harness/v1/P2/action", {method: "POST", headers, body: JSON.stringify({turn_seq: obs.turn_seq, action: {kind: "plot_course", args: {target, execute: false}}})});
                  if (!posted.ok) throw new Error(await posted.text());
                  const events = await fetch("/harness/v1/P2/events?since=0&limit=100&course=1", {headers}).then((r) => r.json());
                  const plot = [...(events.events || [])].reverse().find((ev) => ev.kind === "autopilot" && ev.facts && ev.facts.path);
                  return {route: plot.facts.path.join(","), hops: plot.facts.path.length};
                }""",
                TOK,
            )
            page.wait_for_function(
                "(route) => document.querySelector('#map').getAttribute('data-route') === route",
                arg=info["route"],
                timeout=20_000,
            )
            assert f"{info['hops']} hops" in page.locator("#warps .eng").inner_text()
            page.screenshot(path=str(SHOTS / "1440-route.png"))
            page.locator("#warps .eng").click()
            page.wait_for_function(
                "() => document.querySelector('#pSector').textContent === '1'",
                timeout=30_000,
            )
            page.locator("button", has_text="buy gear").click()
            page.wait_for_selector(".frm", timeout=10_000)
            page.screenshot(path=str(SHOTS / "1440-stardock.png"))
            found = False
            for _ in range(4):
                before = page.locator("#pSector").inner_text()
                page.locator("#warps button").first.click()
                page.wait_for_function(
                    "(before) => document.querySelector('#pSector').textContent !== before",
                    arg=before,
                    timeout=20_000,
                )
                if "Ports" not in page.locator("#sectorText").inner_text():
                    found = True
                    break
            assert found
            page.screenshot(path=str(SHOTS / "1440-deep.png"))
            page.close()
        finally:
            browser.close()
