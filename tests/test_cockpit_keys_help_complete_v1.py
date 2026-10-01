"""The keys overlay mentions Enter confirming a trade."""

from __future__ import annotations

from tests._cu_host import CuHost

TOK = "keys-help-complete-v1-token-p2-000000"


def test_keys_overlay_lists_enter_confirming_a_trade(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.get_by_test_id("keys-help").click()
        page.wait_for_selector("[data-testid=keys-help-overlay]:not([hidden])", timeout=5_000)
        line = page.locator("[data-testid=keys-help-overlay] [data-hotkey=Enter]")
        assert line.count() == 1
        assert line.inner_text() == "Enter Confirm trade"
        page.close()
