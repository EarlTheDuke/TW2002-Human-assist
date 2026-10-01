"""The Computer page lists ports this seat has seen, and a best pair."""

from __future__ import annotations

from tests._cu_host import VIEW_H, CuHost
from tests.test_amz6_warp_codes import _replace_snapshot, _wait_parked

TOK = "known-ports-v1-token-p2-00000000000"
MAP_TOP = {1440: 714, 1920: 927}


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const body = document.querySelector('.mfd-body').getBoundingClientRect();
          const book = document.querySelector('[data-testid=known-port-book]');
          const box = book.getBoundingClientRect();
          const tabTop = Math.min(...tabs);
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: body.height,
            tabSpread: Math.max(...tabs) - tabTop,
            tabs: tabs.length,
            score: document.querySelector('#scoreboard').getBoundingClientRect().height,
            bookInside: book.hidden || (box.top >= body.top - 1 && box.bottom <= body.bottom + 1),
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
    assert lay["bookInside"]


def _stock(side: str, price: int) -> dict:
    return {"current": 10, "max": 20, "price": price, "side": side}


def _seed(universe, me) -> tuple[int, int]:
    here = me.sector_id
    buy = 44 if here != 44 else 45
    sell = 126 if here != 126 else 127
    mid = 80 if here not in (80, buy, sell) and 80 not in (buy, sell) else 81
    me.known_ports.clear()
    me.known_ports[buy] = {
        "class": "SBB",
        "stock": {
            "fuel_ore": _stock("sells_to_player", 21),
            "organics": _stock("buys_from_player", 40),
        },
        "last_seen_day": universe.day,
    }
    me.known_ports[sell] = {
        "class": "BSS",
        "stock": {
            "fuel_ore": _stock("buys_from_player", 34),
            "equipment": _stock("sells_to_player", 18),
        },
        "last_seen_day": universe.day - 2,
    }
    me.known_warps[buy] = [mid]
    me.known_warps[mid] = [sell]
    universe.players["P1"].known_ports[901] = {
        "class": "BBB",
        "stock": {"fuel_ore": _stock("sells_to_player", 424242)},
        "last_seen_day": universe.day,
    }
    return buy, sell


def test_known_port_book_is_this_seat_and_prices_the_best_pair(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        universe, me = _wait_parked(host)
        unknown = next(sid for sid in universe.sectors[me.sector_id].warps if sid not in (44, 45, 126, 127))
        me.known_ports.clear()
        _replace_snapshot(host, universe)

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.get_by_test_id("computer-toggle").click()
        page.wait_for_selector("[data-testid=known-port-empty]", timeout=10_000)
        assert page.get_by_test_id("known-port-empty").inner_text() == "no ports visited yet"
        assert page.get_by_test_id("known-port-pairs").inner_text() == "no pair yet"
        _assert_layout(page, 1440)

        buy, sell = _seed(universe, me)
        _replace_snapshot(host, universe)
        page.get_by_test_id("refresh").click()
        want = f"buy fuel_ore at sector {buy} @ 21, sell at sector {sell} @ 34, +13 per unit, 2 warps apart"
        page.wait_for_function(
            "(line) => document.querySelector('[data-testid=known-port-pairs]')?.textContent.includes(line)",
            arg=want,
            timeout=10_000,
        )
        assert page.get_by_test_id("known-port-pairs").inner_text() == want
        assert "424242" not in page.get_by_test_id("known-port-book").inner_text()
        assert page.locator(f"[data-testid=known-port-row-{unknown}]").count() == 0
        assert "seen today" in page.get_by_test_id(f"known-port-row-{buy}").inner_text()
        assert "seen 2d ago" in page.get_by_test_id(f"known-port-row-{sell}").inner_text()
        _assert_layout(page, 1440)

        posts: list[str] = []
        page.on("request", lambda r: posts.append(r.url) if r.method == "POST" and r.url.endswith("/action") else None)
        page.wait_for_selector("#verbPad button[data-verb=plot_course]:not([disabled])", timeout=15_000)
        page.get_by_test_id(f"known-port-row-{buy}").click()
        page.wait_for_selector("[data-testid=plot-target]", timeout=5_000)
        assert page.locator("[data-testid=plot-target]").input_value() == str(buy)
        assert page.locator("[data-testid=verb-form]").is_visible()
        assert posts == []
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        wide.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        wide.wait_for_selector("#turnBanner.turn", timeout=20_000)
        wide.get_by_test_id("computer-toggle").click()
        wide.wait_for_selector("[data-testid=known-port-pairs]", timeout=10_000)
        assert want in wide.get_by_test_id("known-port-pairs").inner_text()
        _assert_layout(wide, 1920)
        wide.close()

        cu = browser.new_page(viewport={"width": 1280, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')",
            timeout=20_000,
        )
        assert cu.evaluate("() => document.scrollingElement.scrollHeight") <= VIEW_H
        assert not cu.get_by_test_id("known-port-book").is_visible()
        cu.close()
