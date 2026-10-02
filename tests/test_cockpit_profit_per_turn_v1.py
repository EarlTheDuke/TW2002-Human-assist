"""Moments shows this seat's realized trade profit, not the sliced log."""

from __future__ import annotations

from tests._cu_host import VIEW_H, CuHost
from tests.test_amz6_warp_codes import _replace_snapshot, _wait_parked

TOK = "profit-per-turn-v1-token-p2-00000000"
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


def _show(page) -> None:
    page.get_by_test_id("refresh").click()
    page.get_by_test_id("mfd-tab-moments").click()


def _expect_rate(universe, me) -> str:
    net = 4200
    used = max(0, (universe.day - 1) * me.turns_per_day + me.turns_today)
    per = round(net / used)
    return f"Trade profit +4,200 cr, {per:,} cr per turn"


def test_trade_profit_uses_the_summary_and_caps_the_rate(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        universe, me = _wait_parked(host)
        me.trade_log.clear()
        universe.players["P1"].trade_log.append(
            {"side": "sell", "total": 999999, "realized_profit": 999999, "commodity": "equipment"},
        )
        _replace_snapshot(host, universe)

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.get_by_test_id("mfd-tab-moments").click()
        assert page.get_by_test_id("trade-profit").is_hidden()

        me.turns_today = 50
        me.trade_log.extend([
            {"side": "buy", "total": 300, "commodity": "equipment", "qty": 10},
            {"side": "sell", "total": 4500, "realized_profit": 4200, "commodity": "equipment", "qty": 10},
        ])
        _replace_snapshot(host, universe)
        _show(page)
        want = _expect_rate(universe, me)
        page.wait_for_function(
            "(line) => document.querySelector('[data-testid=trade-profit]')?.textContent === line",
            arg=want,
            timeout=10_000,
        )
        assert "999999" not in page.get_by_test_id("trade-profit").inner_text()
        page.evaluate("() => window.scrollTo(0, 0)")
        _assert_layout(page, 1440)

        me.turns_per_day = 0
        me.turns_today = 0
        _replace_snapshot(host, universe)
        _show(page)
        page.wait_for_function(
            "() => document.querySelector('[data-testid=trade-profit]')?.textContent === 'Trade profit +4,200 cr'",
            timeout=10_000,
        )

        me.trade_log[:] = [
            {"side": "sell", "total": 10, "realized_profit": 10, "commodity": "fuel_ore"} for _ in range(50)
        ]
        _replace_snapshot(host, universe)
        _show(page)
        page.wait_for_function(
            "() => document.querySelector('[data-testid=trade-profit]')?.textContent === 'Trade profit, last 50 trades: +500 cr'",
            timeout=10_000,
        )
        assert "per turn" not in page.get_by_test_id("trade-profit").inner_text()

        me.trade_log[:] = [{"side": "buy", "total": 300, "commodity": "equipment"}]
        _replace_snapshot(host, universe)
        _show(page)
        page.wait_for_function(
            "() => document.querySelector('[data-testid=trade-profit]')?.textContent === 'Trade profit +0 cr'",
            timeout=10_000,
        )
        assert "999999" not in page.get_by_test_id("trade-profit").inner_text()

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
        assert not cu.get_by_test_id("trade-profit").is_visible()
        cu.close()
