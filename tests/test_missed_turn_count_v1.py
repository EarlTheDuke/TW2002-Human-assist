"""The away line can name turns the seat did not answer."""

from __future__ import annotations

from tests._cu_host import CuHost

TOK = "missed-turn-v1-token-p2-0000000000000"


def test_missed_turns_count_timeouts_and_auto_waits(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        n = page.evaluate(
            """() => window.TW2KParity.missedTurnCount([
              {kind: "agent_error", payload: {external_timeout: true}},
              {kind: "agent_thought", payload: {auto_wait: true}},
              {kind: "warp", payload: {}},
            ])"""
        )
        assert n == 2
        page.close()
