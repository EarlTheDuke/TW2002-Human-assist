"""The winning cockpit is off unless COCKPIT_LAYOUT=redesign or ?layout=redesign."""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

import pytest

from tests._cu_host import CuHost

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "cockpit-redesign-wire-v1"
TOK = "wire-e2e-token-p2-00000000000000"


def test_default_bot_is_the_old_page(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.setenv("TW2K_SPECTATOR_TOKEN", "not-the-seat-token")
    with CuHost(tmp_path, TOK) as host:
        old = urlopen(host.base + "/bot", timeout=10).read().decode("utf-8")
        asked = urlopen(host.base + "/bot?layout=redesign", timeout=10).read().decode("utf-8")
        bot2 = urlopen(host.base + "/bot2", timeout=10).read().decode("utf-8")
    assert "Grok Bot Cockpit" in old
    assert "NAV COMPUTER" not in old
    assert "ship-board" not in old
    assert "NAV COMPUTER" in asked
    assert 'data-testid="scene-still"' in asked
    assert 'data-testid="ship-board"' in bot2
    assert 'data-testid="command-keys"' in bot2
    assert "onclick=\"form(" not in asked


def test_env_flag_serves_the_redesign(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("COCKPIT_LAYOUT", "redesign")
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = urlopen(host.base + "/bot", timeout=10).read().decode("utf-8")
        forced = urlopen(host.base + "/bot?layout=legacy", timeout=10).read().decode("utf-8")
    assert "NAV COMPUTER" in page
    assert "Grok Bot Cockpit" in forced


def test_screens_and_a_wait(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for width, height in ((1920, 1080), (1440, 900), (390, 844)):
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
                page.wait_for_function(
                    "() => { const el = document.querySelector('[data-testid=ship-class]'); return el && el.textContent && !el.textContent.includes('\\u2014'); }",
                    timeout=20_000,
                )
                assert page.locator("[data-testid=scene-still]").count() == 1
                assert page.locator("[data-testid=fighter-row]").count() == 1
                assert page.locator("[data-testid=ship-cargo] .hold").count() == 4
                page.screenshot(path=str(SHOTS / f"{width}.png"), full_page=True)
                page.close()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"{host.base}/bot2?seat=P2&token={TOK}")
            page.wait_for_selector("[data-testid=action-wait]:not([disabled])", timeout=20_000)
            page.get_by_test_id("action-wait").click()
            page.wait_for_function(
                "() => (document.querySelector('#lastResult').textContent || '').includes('You wait')",
                timeout=20_000,
            )
            page.close()
        finally:
            browser.close()
