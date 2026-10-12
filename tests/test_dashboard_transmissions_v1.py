"""An empty transmissions panel says so and stays out of the way."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "dashboard-transmissions-v1"
REF = Path(r"C:\Users\sugar\tw2002_reference\dashboard_test\qc\dashboard-transmissions-v1")


def test_empty_transmissions_collapse_and_say_so(browser, tmp_path, monkeypatch) -> None:
    from tests._cu_host import CuHost

    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, "dash-transmissions-v1-token-p2-000") as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/")
        page.wait_for_function(
            """() => {
              const empty = document.querySelector('[data-testid=transmissions-empty]');
              const msgs = document.querySelectorAll('#messageFeed .message');
              return Boolean(empty) || msgs.length > 0;
            }""",
            timeout=20_000,
        )
        panel = page.locator("#panelMessages")
        if "collapsed" in (panel.get_attribute("class") or ""):
            page.locator("[data-collapse=messages]").click()
            page.wait_for_selector("[data-testid=transmissions-empty]", state="visible")
            assert "No hails" in page.locator("[data-testid=transmissions-empty]").inner_text()
        else:
            assert page.locator("#messageFeed .message").count() > 0
        for width, height, name in ((1920, 1080, "1920"), (1440, 900, "1440"), (390, 844, "390")):
            page.set_viewport_size({"width": width, "height": height})
            for folder in (SHOTS, REF):
                folder.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(folder / f"spectate-{name}.png"), full_page=(width < 720))
        page.close()
