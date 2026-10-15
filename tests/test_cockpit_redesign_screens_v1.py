"""Ship info is a screen, and the log is newest-first in plain words."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._cu_host import CuHost

TOK = "screens-e2e-token-p2-000000000000"


def test_ship_info_and_a_plain_log(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            page.wait_for_selector("#keys button", timeout=20_000)
            page.locator("#keys button", has_text="Ship Info").click()
            page.wait_for_selector("#menu[data-screen=ship-info]", timeout=5_000)
            info = page.locator("#menu").inner_text()
            for label in ("Name", "Class", "Holds", "Fighters", "Shields", "Turns per warp", "Gear"):
                assert label in info
            page.wait_for_selector("[data-testid=action-wait]:not([disabled])", timeout=20_000)
            page.get_by_test_id("action-wait").click()
            page.wait_for_function(
                "() => /You wait/.test(document.querySelector('#lastResult').textContent || '')",
                timeout=20_000,
            )
            page.wait_for_function("() => document.querySelectorAll('#log div').length > 0", timeout=10_000)
            text = page.locator("#log").inner_text()
            assert "AUTOPILO" not in text and "DEPLOY_F" not in text
            seqs = page.eval_on_selector_all("#log div", "els => els.map((el) => Number(el.dataset.seq))")
            assert seqs == sorted(seqs, reverse=True)
            assert seqs[0] == max(seqs)
        finally:
            browser.close()
