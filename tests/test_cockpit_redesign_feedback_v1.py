"""Results, trade reasons, and turns left stay in plain words."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._cu_host import CuHost

TOK = "feedback-e2e-token-p2-000000000000"


def test_turns_reasons_and_a_result_line(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            page.wait_for_function("() => document.querySelector('#tl').textContent === '60'", timeout=20_000)
            assert "D" not in page.locator("#tl").inner_text()
            table = page.locator(".porttbl").inner_text()
            assert "to sell" in table or "not buying" in table or "on board" in table or "room " in table
            assert "cargo, credits, holds or port stock" not in table
            page.locator("#keys button", has_text="Attack").click()
            reason = page.locator("#lastResult").inner_text()
            assert "buy_equip" not in reason
            assert "_" not in reason
            page.wait_for_selector("[data-testid=action-wait]:not([disabled])", timeout=20_000)
            page.get_by_test_id("action-wait").click()
            page.wait_for_function(
                "() => /ok/.test(document.querySelector('#lastResult').textContent || '') && /Turns spent/.test(document.querySelector('#lastResult').textContent || '')",
                timeout=20_000,
            )
        finally:
            browser.close()
