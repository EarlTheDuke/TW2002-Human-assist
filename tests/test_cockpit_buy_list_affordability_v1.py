"""Unaffordable gear stays on the list, and a cut order says what it was cut from."""

from __future__ import annotations

import shutil
from pathlib import Path

from tests._cu_host import CuHost

TOK = "buy-list-v1-token-p2-000000000000000"
SHOT = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-buy-list" / "order-cut.png"
COPY = Path(r"C:\Users\sugar\tw2002_reference\cockpit_assets\screens\order-cut.png")


def test_a_cut_order_names_both_numbers(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        words = page.evaluate(
            """() => {
              const P = window.TW2KParity;
              return {
                cut: P.clampNote(270, 269),
                same: P.clampNote(10, 10),
                credits: P.affordReason(0, 0),
                room: P.affordReason(0, 4),
                ok: P.affordReason(3, 4),
              };
            }"""
        )
        assert words["cut"] == "cut from 270 to 269"
        assert words["same"] == ""
        assert words["credits"] == "not enough credits"
        assert words["room"] == "no room on the ship"
        assert words["ok"] == ""
        page.locator("[data-testid=action-trade]").click()
        page.locator("[data-testid=trade-side-sell]").click()
        page.locator("[data-testid=trade-qty]").fill("270")
        preview = page.locator("[data-testid=verb-preview]").inner_text()
        assert "cut from 270 to" in preview
        page.locator("#verbForm").scroll_into_view_if_needed()
        SHOT.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOT))
        COPY.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SHOT, COPY)
        page.close()
