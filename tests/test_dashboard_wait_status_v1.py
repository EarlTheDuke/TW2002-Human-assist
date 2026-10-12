"""A seat that holds the tick is named. A moving match still says live."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "dashboard-wait-status-v1"
REF = Path(r"C:\Users\sugar\tw2002_reference\dashboard_test\qc\dashboard-wait-status-v1")


def test_a_held_seat_replaces_the_live_label(browser, tmp_path, monkeypatch) -> None:
    from tests._cu_host import CuHost

    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, "dash-wait-status-v1-token-p2-00000") as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/")
        page.wait_for_function(
            """() => {
              const text = document.getElementById('statusLabel').textContent || '';
              return /^Waiting for Commander \\(day-done \\d+\\/\\d+\\)$/.test(text);
            }""",
            timeout=40_000,
        )
        assert "paused" in page.locator("#statusDot").get_attribute("class")
        assert "waiting" in page.title()
        for width, height, name in ((1920, 1080, "1920"), (1440, 900, "1440"), (390, 844, "390")):
            page.set_viewport_size({"width": width, "height": height})
            for folder in (SHOTS, REF):
                folder.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(folder / f"spectate-{name}.png"))
        page.close()
