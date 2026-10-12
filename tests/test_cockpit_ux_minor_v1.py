"""Small cockpit wording from the Game 8 play log.

A premium haggle is over the port price, not a percent off list. The port
column says how much is for sale, or how much room a buying port has left.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from tests._cu_host import CuHost

TOK = "ux-minor-v1-token-p2-00000000000000"
SHOT = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-play-fixes" / "haggle-preview.png"
COPY = Path(r"C:\Users\sugar\tw2002_reference\cockpit_assets\screens\haggle-preview.png")


def test_stock_room_and_haggle_wording(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        holds = []
        page.on("request", lambda r: holds.append(r.url) if r.method == "POST" and r.url.endswith("/hold") else None)
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.locator("[data-testid=mfd-tab-port]").click()
        page.wait_for_selector("[data-testid=port-row-fuel_ore]", state="visible", timeout=20_000)
        assert "STOCK / ROOM" in page.locator("#portTape thead").inner_text()
        fuel = page.locator("[data-testid=port-row-fuel_ore]").inner_text()
        assert " / " in fuel and "room" in fuel
        card = page.locator("[data-testid=compare-panel]").text_content() or ""
        assert "genesis" in card
        page.evaluate(
            "sessionStorage.setItem('tw2k_hold_P2', JSON.stringify({on:true,used:1,max:5}))"
        )
        page.reload()
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        assert holds == []
        page.locator("[data-testid=action-trade]").click()
        page.locator("[data-testid=trade-side-sell]").click()
        page.locator("[data-testid=trade-price]").fill("99999")
        preview = page.locator("[data-testid=verb-preview]").inner_text()
        assert "over the port price" in preview
        assert "off list" not in preview
        assert "settle at list" not in preview
        assert "costs the turn" in preview
        page.locator("#verbForm").scroll_into_view_if_needed()
        SHOT.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOT))
        COPY.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SHOT, COPY)
        page.close()
