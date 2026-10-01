"""The spectator browser tab follows the match day and pause state."""

from __future__ import annotations

from tests._cu_host import CuHost

TOK = "spectator-tab-title-v1-token-p2-000000"
PLAIN = "TW2K-AI — Spectator"


def test_spectator_tab_title_follows_day_and_pause(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/")
        page.wait_for_function(
            """() => {
              const day = document.getElementById('dayLabel').textContent;
              return document.title === `TW2K - ${day} - live` && /^Day [1-9]/.test(day);
            }""",
            timeout=20_000,
        )
        day = page.locator("#dayLabel").inner_text()
        assert page.title() == f"TW2K - {day} - live"
        assert page.title() != PLAIN

        assert page.request.post(f"{host.base}/control/pause").ok
        page.wait_for_function(
            """(day) => document.title === `TW2K - ${day} - paused`""",
            arg=day,
            timeout=10_000,
        )

        assert page.request.post(f"{host.base}/control/resume").ok
        page.wait_for_function(
            """(day) => document.title === `TW2K - ${day} - live`""",
            arg=day,
            timeout=10_000,
        )
        page.close()
