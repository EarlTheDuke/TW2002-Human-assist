"""NOTE 124. After the game ends, the day countdown stops.

The end panel already says the game is over. The turns line must not keep
counting a later day.
"""

from __future__ import annotations

import pytest

from tests._cu_host import CuHost

TOK = "note124-preflight-token-p2-0000000000"


def test_the_day_clock_stops_when_the_game_is_over(tmp_path, monkeypatch) -> None:
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    with CuHost(tmp_path, TOK) as host, sync() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            page.wait_for_selector("#waitchip", timeout=20_000)
            page.wait_for_function(
                "() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'",
                timeout=20_000,
            )
            shown = page.evaluate(
                """() => {
                  window.__tw2kTest.setTurnClock({
                    server_now: Date.now() / 1000,
                    day_seconds: 90,
                    next_day_in_s: 20,
                    next_day_at: Date.now() / 1000 + 20
                  });
                  const line = document.getElementById('dayEnds').textContent;
                  const clock = document.getElementById('dayClock').textContent;
                  window.__tw2kTest.setGameOver(true);
                  return {
                    line: line,
                    hidden: document.getElementById('dayEnds').hidden,
                    clock: document.getElementById('dayClock').textContent,
                    beforeClock: clock
                  };
                }"""
            )
            assert "ends in" in shown["line"]
            assert "next day in" in shown["beforeClock"]
            assert shown["hidden"] is True
            assert shown["clock"] == ""
        finally:
            browser.close()
