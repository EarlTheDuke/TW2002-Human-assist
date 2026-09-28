"""Refresh is visible on the mode=cu top bar and only refetches.

The WAITING banner keeps its countdown whole: the actor phrase ellipsizes,
the seconds do not.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from tests._cu_host import VIEW_H, VIEW_W, CuHost, inside

TOK = "amz4-refresh-token-p2-000000000"
REAL_NAME = "Other"
LONG_NAME = "Other " + ("Longname " * 16)


def _banner(page) -> dict:
    return page.evaluate("""() => {
        const banner = document.getElementById('cuTurn');
        const main = banner.querySelector('.main');
        const cd = banner.querySelector('.cd');
        const cs = main ? getComputedStyle(main) : null;
        const cdBox = cd ? cd.getBoundingClientRect() : null;
        const bannerBox = banner.getBoundingClientRect();
        return {
            text: (main ? main.textContent : '') + (cd ? cd.textContent : ''),
            main_text: main ? main.textContent : '',
            ellipsis: !!(cs && cs.textOverflow === 'ellipsis' && cs.overflowX === 'hidden'
                && cs.whiteSpace === 'nowrap' && cs.display === 'block' && cs.minWidth === '0px'),
            main_over: !!(main && main.scrollWidth > main.clientWidth + 1),
            cd_text: cd ? cd.textContent : '',
            cd_scroll: cd ? cd.scrollWidth : -1,
            cd_client: cd ? cd.clientWidth : -1,
            cd_right: cdBox ? cdBox.right : -1,
            banner_right: bannerBox.right,
        };
    }""")


def _assert_waiting(info: dict, name: str) -> None:
    """The phrase fits or ellipsizes. The countdown element is fully inside the banner."""
    assert info["ellipsis"], info
    assert re.fullmatch(rf"WAITING · {re.escape(name)} \(remote seat\) is acting · \d{{2,}}s", info["text"]), info
    assert re.fullmatch(r" · \d{2,}s", info["cd_text"]), info
    assert info["main_text"] + info["cd_text"] == info["text"]
    assert info["cd_scroll"] <= info["cd_client"], info
    assert info["cd_right"] <= info["banner_right"] + 1, info
    if info["main_over"]:
        assert info["ellipsis"]


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

        scripted = {"name": REAL_NAME, "ago": 12}

        def scripted_turn(route) -> None:
            path = route.request.url.split("?", 1)[0]
            if route.request.method == "GET" and (path.endswith("/status") or path.endswith("/observation")):
                now = time.time()
                route.fulfill(status=200, content_type="application/json", body=json.dumps({
                    "server_time": now, "match_status": "running", "day": 1, "tick": 4,
                    "awaiting_input": False, "turn_seq": 3,
                    "status_line": "Day 1 of 3 - 40 turns left today - Rank 2 of 2",
                    "current_turn": {
                        "player_id": "P1", "name": scripted["name"], "kind": "external",
                        "started_at": now - scripted["ago"], "deadline_at": now + 40, "attended": True,
                    },
                }))
                return
            route.continue_()

        def wait_phrase(fragment: str) -> None:
            page.wait_for_function(
                """(frag) => {
                    const m = document.querySelector('#cuTurn .main');
                    return !!(m && m.textContent.includes(frag));
                }""",
                arg=fragment, timeout=10_000,
            )

        page.route("**/harness/v1/**", scripted_turn)
        wait_phrase(f"WAITING · {REAL_NAME} (remote seat)")
        time.sleep(0.6)
        wait_phrase(f"WAITING · {REAL_NAME} (remote seat)")
        real = _banner(page)
        _assert_waiting(real, REAL_NAME)

        scripted["name"] = LONG_NAME
        scripted["ago"] = 88
        page.get_by_test_id("refresh").click()
        wait_phrase("Longname Longname")
        time.sleep(0.3)
        wait_phrase("Longname Longname")
        long = _banner(page)
        _assert_waiting(long, LONG_NAME)
        assert long["main_over"], long

        fit = page.evaluate("""() => {
            document.getElementById('cuStatusLine').textContent = 'Day 12 of 30 - 1,000 turns left today - Rank 10 of 12';
            document.getElementById('cuSeat').textContent = 'P2 Commander';
            const nodes = [...document.querySelectorAll('.cu-top .cu-stat .v'), document.querySelector('.cu-statusline')];
            return nodes.map(el => ({ id: el.id || el.getAttribute('data-testid'), scroll: el.scrollWidth, client: el.clientWidth }));
        }""")
        overflow = [row for row in fit if row["scroll"] > row["client"] + 1]
        assert not overflow, overflow
        assert page.evaluate("document.scrollingElement.scrollHeight") <= VIEW_H
        still = _banner(page)
        _assert_waiting(still, LONG_NAME)
        page.unroute("**/harness/v1/**", scripted_turn)
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
