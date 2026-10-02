"""The Bridge tab summarizes what changed for this seat since last turn."""

from __future__ import annotations

from tests._cu_host import VIEW_H, CuHost
from tests.test_amz6_warp_codes import _replace_snapshot, _wait_parked

TOK = "what-changed-v1-token-p2-0000000000"
MAP_TOP = {1440: 714, 1920: 927}


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const tabTop = Math.min(...tabs);
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            tabSpread: Math.max(...tabs) - tabTop,
            tabs: tabs.length,
            score: document.querySelector('#scoreboard').getBoundingClientRect().height,
          };
        }"""
    )


def _assert_layout(page, width: int) -> None:
    lay = _layout(page)
    assert abs(lay["mapY"] - MAP_TOP[width]) < 4, lay["mapY"]
    assert abs(lay["mfd"] - 420) < 1
    assert lay["tabSpread"] < 2
    assert lay["tabs"] == 5
    assert abs(lay["score"] - 88) < 1


def test_since_turn_is_this_seat_and_hidden_at_first(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        universe, me = _wait_parked(host)
        origin = me.sector_id
        dest = next(sid for sid in universe.sectors[origin].warps)
        port_id = next(sid for sid in range(1, 180) if sid not in me.known_ports and sid not in (origin, dest))
        universe.players["P1"].credits = 424242
        _replace_snapshot(host, universe)

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.get_by_test_id("mfd-tab-bridge").click()
        assert page.get_by_test_id("since-turn").is_hidden()

        universe.tick += 100
        _replace_snapshot(host, universe)
        page.get_by_test_id("refresh").click()
        page.get_by_test_id("mfd-tab-bridge").click()
        page.wait_for_timeout(400)
        assert page.get_by_test_id("since-turn").is_hidden()

        me.credits += 500
        me.sector_id = dest
        me.trade_log.extend([
            {"side": "buy", "total": 100, "commodity": "equipment"},
            {"side": "sell", "total": 300, "commodity": "equipment"},
        ])
        me.known_ports[port_id] = {"class": "BSS", "stock": {}, "last_seen_day": universe.day}
        universe.tick += 100
        _replace_snapshot(host, universe)
        page.get_by_test_id("refresh").click()
        page.get_by_test_id("mfd-tab-bridge").click()
        page.wait_for_function(
            """(parts) => {
              const el = document.querySelector('[data-testid=since-turn]');
              if (!el || el.hidden) return false;
              return parts.every((part) => el.textContent.includes(part));
            }""",
            arg=[
                "Credits +500 cr",
                f"Moved from {origin} to {dest}",
                "Trades 2, net +200 cr",
                f"New ports {port_id}",
            ],
            timeout=10_000,
        )
        text = page.get_by_test_id("since-turn").inner_text()
        assert "424242" not in text
        assert len(text.splitlines()) <= 6
        page.evaluate("() => window.scrollTo(0, 0)")
        _assert_layout(page, 1440)
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.evaluate("() => window.scrollTo(0, 0)")
        _assert_layout(page, 1920)
        page.close()

        cu = browser.new_page(viewport={"width": 1280, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert not cu.get_by_test_id("since-turn").is_visible()
        cu.close()
