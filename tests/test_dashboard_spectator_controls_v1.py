"""Spectators can watch. They cannot pause, change speed, or start a new match.

When TW2K_SPECTATOR_TOKEN is set, the page hides those controls and
/control/* answers 403. With the token unset, the controls stay and
pause still works.

Plants:
  pb1 — the page still shows the controls while the token is set.
  pb2 — a spectator token can still pause.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from tw2k.server.app import create_app

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "dashboard-spectator-controls-v1"
REF = Path(r"C:\Users\sugar\tw2002_reference\dashboard_test\qc\dashboard-spectator-controls-v1")
SPEC = "dash-spec-controls-v1-secret"


def test_spectator_token_rejects_control_and_marks_the_page(monkeypatch) -> None:
    monkeypatch.setenv("TW2K_SPECTATOR_TOKEN", SPEC)
    client = TestClient(create_app(auto_start=False))
    headers = {"authorization": f"Bearer {SPEC}"}
    for path in ("/control/pause", "/control/resume", "/control/restart"):
        got = client.post(path, headers=headers)
        assert got.status_code == 403, path
        assert "cannot control" in got.json()["detail"]
    got = client.post("/control/speed", headers=headers, json={"multiplier": 2})
    assert got.status_code == 403
    html = client.get("/", headers=headers).text
    assert 'data-spectator="1"' in html
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    assert "data-spectator" not in client.get("/").text


def test_spectator_page_hides_the_match_controls(browser, tmp_path, monkeypatch) -> None:
    from tests._cu_host import CuHost

    monkeypatch.setenv("TW2K_SPECTATOR_TOKEN", SPEC)
    with CuHost(tmp_path, "dash-spec-controls-seat-p2-0000") as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/spectate?token={SPEC}")
        page.wait_for_function(
            "() => /^Day [1-9]/.test(document.getElementById('dayLabel').textContent)",
            timeout=20_000,
        )
        assert page.locator("#pauseBtn").is_hidden()
        assert page.locator(".speed-group").is_hidden()
        assert page.locator("#restartBtn").is_hidden()
        assert page.locator("#cockpitLink").is_visible()
        assert page.locator("#helpBtn").is_visible()
        refused = page.request.post(
            f"{host.base}/control/pause",
            headers={"authorization": f"Bearer {SPEC}"},
        )
        assert refused.status == 403
        for width, height, name in ((1920, 1080, "1920"), (1440, 900, "1440"), (390, 844, "390")):
            page.set_viewport_size({"width": width, "height": height})
            for folder in (SHOTS, REF):
                folder.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(folder / f"spectate-{name}.png"))
        page.close()
