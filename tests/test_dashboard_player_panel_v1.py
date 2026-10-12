"""A leaderboard row follows that ship, and Details opens the drawer."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "dashboard-player-panel-v1"
REF = Path(r"C:\Users\sugar\tw2002_reference\dashboard_test\qc\dashboard-player-panel-v1")


def test_row_follows_the_ship_and_details_opens(browser, tmp_path, monkeypatch) -> None:
    from tests._cu_host import CuHost

    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, "dash-player-panel-v1-token-p2-0000") as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/")
        page.wait_for_selector("[data-lb-player]", timeout=20_000)
        row = page.locator("[data-lb-player]").first
        pid = row.get_attribute("data-lb-player")
        row.click()
        page.wait_for_function(
            "(pid) => document.getElementById('mapFollowWho').value === pid",
            arg=pid,
            timeout=10_000,
        )
        assert page.locator("#detailDrawer").is_visible()
        page.locator(".player-card[open] [data-testid=player-details]").click()
        assert page.locator("#detailDrawer").is_visible()
        card = page.locator(".player-card[open]").first
        assert card.locator(".player-name").count() == 0
        assert card.locator(".pc-sum-name").count() == 1
        vitals = page.locator("#detailDrawer").inner_text()
        assert "0/0" not in vitals
        assert "still flying" in page.locator("#playerCountLabel").inner_text().lower()
        legend = page.locator(".lb-legend").inner_text()
        assert "planets" in legend and "kills" in legend
        assert page.locator(".lb-stat").nth(0).get_attribute("title")
        for width, height, name in ((1920, 1080, "1920"), (1440, 900, "1440"), (390, 844, "390")):
            page.set_viewport_size({"width": width, "height": height})
            for folder in (SHOTS, REF):
                folder.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(folder / f"spectate-{name}.png"), full_page=(width < 720))
        page.close()
