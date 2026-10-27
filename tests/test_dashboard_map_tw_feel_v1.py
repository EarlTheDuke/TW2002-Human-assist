"""The map opens wide enough to read, with sector numbers and ship names."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "dashboard-map-tw-feel-v1"
REF = Path(r"C:\Users\sugar\tw2002_reference\dashboard_test\qc\dashboard-map-tw-feel-v1")


def test_map_shows_sector_numbers_and_ship_names(browser, tmp_path, monkeypatch) -> None:
    from tests._cu_host import CuHost

    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, "dash-map-feel-v1-token-p2-0000000") as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/")
        page.wait_for_selector(".sector-label", timeout=20_000)
        page.wait_for_selector("[data-testid=ship-name]", timeout=20_000)
        zoom = page.locator("#mapZoomReadout").inner_text().strip().rstrip("%")
        assert int(zoom) <= 200
        assert page.locator(".sector-label").first.text_content().strip().isdigit()
        assert page.locator("[data-testid=ship-name]").first.text_content().strip()
        chips = page.locator(".ferr-chip")
        if chips.count():
            text = chips.first.text_content()
            assert "sector " in text
            assert "fighters" in text
        for width, height, name in ((1920, 1080, "1920"), (1440, 900, "1440"), (390, 844, "390")):
            page.set_viewport_size({"width": width, "height": height})
            for folder in (SHOTS, REF):
                folder.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(folder / f"spectate-{name}.png"), full_page=(width < 720))
        page.close()
