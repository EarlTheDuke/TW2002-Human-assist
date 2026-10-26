"""The redesigned helm is /bot2. /bot stays the page it already is."""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

import pytest

from tests._cu_host import CuHost

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "cockpit-redesign-cur-v1"
TOK = "bot2-e2e-token-p2-0000000000000"


def test_bot_stays_and_bot2_is_open(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.setenv("TW2K_SPECTATOR_TOKEN", "not-the-seat-token")
    with CuHost(tmp_path, TOK) as host:
        bot = urlopen(host.base + "/bot", timeout=10).read().decode("utf-8")
        bot2 = urlopen(host.base + "/bot2", timeout=10).read().decode("utf-8")
    assert "Grok Bot Cockpit" in bot
    assert "ship-board" not in bot
    assert 'data-testid="ship-board"' in bot2
    # #432 retired the viewport still; the ship stage plays effects on #stageFx.
    assert 'data-testid="scene-still"' not in bot2
    assert 'data-testid="stage-fx"' in bot2
    assert 'data-testid="command-keys"' in bot2


def test_screens_at_three_widths(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    SHOTS.mkdir(parents=True, exist_ok=True)
    sizes = ((1920, 1080), (1440, 900), (390, 844))
    with CuHost(tmp_path, TOK) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for width, height in sizes:
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(f"{host.base}/bot2?seat=P2&token={TOK}")
                page.wait_for_function(
                    "() => { const el = document.querySelector('[data-testid=ship-class]'); return el && el.textContent && !el.textContent.includes('\\u2014'); }",
                    timeout=20_000,
                )
                assert page.locator("[data-testid=scene-still]").count() == 0
                assert page.locator("[data-testid=stage-fx]").count() == 1
                assert page.locator("[data-testid=fighter-row]").count() == 1
                assert page.locator("[data-testid=ship-cargo] .hold").count() == 4
                page.screenshot(path=str(SHOTS / f"{width}.png"), full_page=True)
                page.close()
        finally:
            browser.close()
