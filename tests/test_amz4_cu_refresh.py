"""Refresh is visible on the mode=cu top bar and only refetches."""

from __future__ import annotations

import time
from pathlib import Path

from tests._cu_host import VIEW_H, VIEW_W, CuHost, inside

TOK = "amz4-refresh-token-p2-000000000"


def test_cu_refresh_is_visible_and_does_not_spend_a_turn(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK, turns_per_day=40) as host:
        page = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        page.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK}")
        page.wait_for_selector("#cuTurn.turn", timeout=20_000)
        refresh = page.get_by_test_id("refresh")
        assert refresh.is_visible()
        box = refresh.bounding_box()
        assert inside(box), box
        assert page.evaluate("document.getElementById('pollBtn').closest('#cuScreen') !== null")
        assert page.evaluate("document.scrollingElement.scrollHeight") <= VIEW_H
        before = page.evaluate("() => ({ played: TW2KMedia._state().playedKeys, hud: !!document.querySelector('[data-testid=media-hud]:not([hidden])') })")
        hits = {"obs": 0, "post": 0}

        def count(route) -> None:
            if route.request.method == "POST":
                hits["post"] += 1
            if "/observation" in route.request.url:
                hits["obs"] += 1
            route.continue_()

        page.route("**/harness/v1/**", count)
        refresh.click()
        deadline = time.time() + 8
        while time.time() < deadline and hits["obs"] < 1:
            time.sleep(0.05)
        assert hits["obs"] >= 1 and hits["post"] == 0, hits
        after = page.evaluate("() => ({ played: TW2KMedia._state().playedKeys, hud: !!document.querySelector('[data-testid=media-hud]:not([hidden])') })")
        assert after["played"] == before["played"], after
        assert after["hud"] is False
        page.close()

        default = browser.new_page(viewport={"width": 1440, "height": 900})
        default.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        default.wait_for_selector("#turnBanner.turn", timeout=20_000)
        assert default.get_by_test_id("refresh").is_visible()
        assert default.evaluate("document.getElementById('pollBtn').closest('#authBar') !== null")
        default.close()
