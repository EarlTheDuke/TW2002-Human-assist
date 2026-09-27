"""Grokbot-player G7 — event-log dedupe, END SLOT styling, 401 stops the poller."""

from __future__ import annotations

import json
from pathlib import Path

from tests._cu_host import CuHost

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "bot.css").read_text(encoding="utf-8")
TOK = "g7-pilot-token-p2-000000000000"


def test_hold_buttons_use_the_primary_style() -> None:
    assert 'id="holdBtn" data-testid="hold-slot" class="primary"' in HTML
    assert 'id="cuHoldBtn" data-testid="cu-hold" class="primary"' in HTML
    assert "#cuHoldBtn.primary" in CSS and "#holdBtn.primary" in CSS
    assert "border: 2px solid var(--go)" in CSS


def test_duplicate_warp_seq_is_shown_once_and_401_stops(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    warp = {
        "seq": 7, "day": 1, "tick": 1, "kind": "warp", "actor_id": "P2",
        "sector_id": 2, "summary": "Commander warped 1 -> 2", "facts": {"from": 1, "to": 2},
    }
    body = json.dumps({"events": [warp, dict(warp)], "next_since": 7, "latest_seq": 7, "has_more": False})
    with CuHost(tmp_path, TOK, turns_per_day=40) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        def events(route):
            route.fulfill(status=200, content_type="application/json", body=body)

        page.route("**/harness/v1/P2/events**", events)
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("[data-testid=turn-banner]", timeout=20_000)
        hold = page.get_by_test_id("hold-slot")
        scan = page.get_by_test_id("action-scan")
        assert hold.is_visible()
        style = page.evaluate("""() => {
            const a = getComputedStyle(document.querySelector('[data-testid=hold-slot]'));
            const b = getComputedStyle(document.querySelector('[data-testid=action-scan]'));
            return { hold: a.borderTopStyle, scan: b.borderTopStyle, bg: a.backgroundColor, scanBg: b.backgroundColor };
        }""")
        assert style["hold"] == "solid" and style["scan"] == "solid"
        assert style["bg"] == style["scanBg"]

        page.wait_for_function("document.querySelectorAll('[data-testid=event-7]').length === 1", timeout=15_000)
        page.wait_for_timeout(1500)
        assert page.locator("[data-testid=event-7]").count() == 1
        page.close()

        cu = browser.new_page(viewport={"width": 1280, "height": 800})
        cu.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK}")
        cu.wait_for_selector("#cuTurn.turn", timeout=20_000)
        cu_style = cu.evaluate("""() => getComputedStyle(document.querySelector('[data-testid=cu-hold]')).borderTopStyle""")
        assert cu_style == "solid"
        hits = {"n": 0}

        def unauth(route):
            if "/events" not in route.request.url:
                route.fallback()
                return
            hits["n"] += 1
            route.fulfill(status=401, content_type="application/json", body='{"detail":"unauthorized"}')

        cu.route("**/harness/v1/**", unauth)
        cu.keyboard.press("r")
        cu.wait_for_selector("[data-testid=reconnect-banner]:not([hidden])", timeout=15_000)
        assert cu.locator("#reconnect").get_attribute("data-kind") == "auth"
        cu.wait_for_timeout(2000)
        stopped = hits["n"]
        cu.wait_for_timeout(3000)
        assert hits["n"] == stopped
        cu.close()
