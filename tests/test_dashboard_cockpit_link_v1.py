"""The dashboard Cockpit link opens /bot. /play stays behind the spectator token."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "dashboard-cockpit-link-v1"
REF = Path(r"C:\Users\sugar\tw2002_reference\dashboard_test\qc\dashboard-cockpit-link-v1")
SPEC = "dash-cockpit-link-v1-secret"


def test_cockpit_link_opens_bot_and_play_stays_gated(browser, tmp_path, monkeypatch) -> None:
    from tests._cu_host import CuHost

    monkeypatch.setenv("TW2K_SPECTATOR_TOKEN", SPEC)
    with CuHost(tmp_path, "dash-cockpit-link-seat-p2-000000") as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/spectate?token={SPEC}")
        page.wait_for_function(
            "() => /^Day [1-9]/.test(document.getElementById('dayLabel').textContent)",
            timeout=20_000,
        )
        href = page.locator("#cockpitLink").get_attribute("href")
        assert href == "/bot"
        import httpx
        assert httpx.get(f"{host.base}/bot").status_code == 200
        assert httpx.get(f"{host.base}/play").status_code == 401
        for width, height, name in ((1920, 1080, "1920"), (1440, 900, "1440"), (390, 844, "390")):
            page.set_viewport_size({"width": width, "height": height})
            for folder in (SHOTS, REF):
                folder.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(folder / f"spectate-{name}.png"))
        page.close()
