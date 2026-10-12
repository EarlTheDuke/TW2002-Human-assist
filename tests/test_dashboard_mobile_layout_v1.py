"""A phone can scroll the map and the feed. A wide screen stays side by side."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "dashboard-mobile-layout-v1"
REF = Path(r"C:\Users\sugar\tw2002_reference\dashboard_test\qc\dashboard-mobile-layout-v1")


def test_phone_stacks_and_scrolls_and_a_wide_screen_stays_side_by_side(browser, tmp_path, monkeypatch) -> None:
    from tests._cu_host import CuHost

    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, "dash-mobile-layout-v1-token-p2-000") as host:
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(f"{host.base}/")
        page.wait_for_function(
            "() => /^Day [1-9]/.test(document.getElementById('dayLabel').textContent)",
            timeout=20_000,
        )
        page.wait_for_function(
            """() => {
              const doc = document.documentElement;
              const map = document.getElementById('panelMap').getBoundingClientRect();
              const feed = document.getElementById('panelEvents').getBoundingClientRect();
              const bar = document.querySelector('.topbar').getBoundingClientRect();
              return map.height > 100 && feed.height > 100
                && map.width > 200 && feed.width > 200
                && doc.scrollHeight > doc.clientHeight + 40
                && doc.scrollWidth <= doc.clientWidth + 1
                && bar.width <= doc.clientWidth + 1;
            }""",
            timeout=10_000,
        )
        for width, height, name in ((390, 844, "390"), (1440, 900, "1440"), (1920, 1080, "1920")):
            page.set_viewport_size({"width": width, "height": height})
            if width >= 1440:
                page.wait_for_function(
                    """() => {
                      const left = document.getElementById('colLeft').getBoundingClientRect();
                      const right = document.getElementById('colRight').getBoundingClientRect();
                      return right.x > left.x + 80;
                    }""",
                    timeout=5_000,
                )
            for folder in (SHOTS, REF):
                folder.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(folder / f"spectate-{name}.png"), full_page=(width < 720))
        page.close()
