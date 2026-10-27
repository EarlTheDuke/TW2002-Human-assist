"""Three-day smoke that plays the bot screen with the mouse. No action API call from this file."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests._cu_host import CuHost, free_port

pytestmark = pytest.mark.legacy_profile

TOK = "playthrough-p2-000000000000000000"
# Game 5 owns 8042. The shared scanner starts at 8040, so this smoke starts higher.
SMOKE_PORT = 8050


def test_three_day_smoke_uses_the_bot_screen_only(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    monkeypatch.setattr("tests._cu_host.free_port", lambda start=SMOKE_PORT: free_port(SMOKE_PORT))
    with CuHost(tmp_path, TOK, max_days=3, turns_per_day=3) as host:
        assert host.port >= SMOKE_PORT
        assert host.port not in range(8031, 8043)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("[data-testid=action-wait]", timeout=20_000)
        page.wait_for_function("document.querySelector('#sbDay').textContent !== '-'", timeout=15_000)
        shots = tmp_path / "shots"
        shots.mkdir()
        log: list[str] = []
        seen = ""
        for _ in range(24):
            day = page.locator("#sbDay").inner_text().strip()
            if day.isdigit() and int(day) >= 3 and log:
                break
            btn = page.get_by_test_id("action-wait")
            if not btn.is_enabled():
                page.wait_for_timeout(400)
                continue
            btn.click()
            page.wait_for_function(
                "(prev) => { const t = document.querySelector('#lastResult').textContent || ''; return t !== prev && t.includes('ok'); }",
                arg=seen,
                timeout=20_000,
            )
            seen = page.locator("#lastResult").inner_text()
            day = page.locator("#sbDay").inner_text().strip()
            log.append(f"day {day}: {seen}")
            page.screenshot(path=str(shots / f"day-{day}-wait-{len(log)}.png"))
        (tmp_path / "actions.log").write_text("\n".join(log) + "\n", encoding="utf-8")
        assert log, "the screen never accepted a wait"
        assert all("FAILED" not in line for line in log)
        assert list(shots.glob("*.png")), "no screenshot"
        assert page.locator("#sbDay").inner_text().strip() == "3" or any(line.startswith("day 3:") for line in log)
