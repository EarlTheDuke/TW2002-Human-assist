"""The Credits box turns amber under 1,000 credits and back at 1,000."""

from __future__ import annotations

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "low-credits-v1-token-p2-0000000000000"
MAP_TOP = {1440: 714, 1920: 927}
AMBER = "rgb(245, 165, 36)"


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_function(
        "() => document.querySelector('[data-testid=credits]')?.textContent !== '-'",
        timeout=15_000,
    )


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const tabTop = Math.min(...tabs);
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            tabSpread: Math.max(...tabs) - tabTop,
            barH: document.querySelector('#scoreboard').getBoundingClientRect().height,
            cellW: document.querySelector('#sbCredits').closest('.score').getBoundingClientRect().width,
          };
        }"""
    )


def _assert_layout(page, width: int) -> None:
    lay = _layout(page)
    assert abs(lay["mapY"] - MAP_TOP[width]) < 4, lay["mapY"]
    assert abs(lay["mfd"] - 420) < 1
    assert lay["tabSpread"] < 2
    assert abs(lay["barH"] - 88) < 1, lay["barH"]
    assert abs(lay["cellW"] - 156) < 2, lay["cellW"]


def _install(page, credits: dict) -> None:
    def handle(route) -> None:
        if credits["n"] is None:
            route.continue_()
            return
        response = route.fetch()
        data = response.json()
        obs = data.get("observation")
        if isinstance(obs, dict):
            obs["credits"] = int(credits["n"])
            data["observation"] = obs
        route.fulfill(response=response, json=data)

    page.route("**/observation**", handle)


def _set_credits(page, credits: dict, n: int) -> None:
    credits["n"] = n
    with page.expect_response(lambda r: "/observation" in r.url and r.ok, timeout=15_000):
        page.get_by_test_id("refresh").click()
    page.wait_for_function(
        """(want) => {
          const el = document.querySelector('[data-testid=credits]');
          return !!el && el.textContent === Number(want).toLocaleString();
        }""",
        arg=n,
        timeout=10_000,
    )


def _mark(page) -> dict:
    return page.evaluate(
        """() => {
          const el = document.querySelector('[data-testid=credits]');
          const cell = el.closest('.score');
          const delta = document.querySelector('[data-testid=credits-delta]');
          return {
            text: el.textContent,
            level: el.getAttribute('data-level'),
            color: getComputedStyle(el).color,
            border: getComputedStyle(cell).borderTopColor,
            deltaText: delta.textContent,
          };
        }"""
    )


def test_credits_box_goes_amber_under_one_thousand(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        _open(page, host)
        _assert_layout(page, 1440)
        start = _mark(page)
        assert start["level"] is None
        assert start["color"] != AMBER
        assert start["deltaText"] == ""

        credits = {"n": None}
        _install(page, credits)
        _set_credits(page, credits, 999)
        low = _mark(page)
        assert low["text"] == "999"
        assert low["level"] == "low"
        assert low["color"] == AMBER
        assert low["border"] == AMBER
        _assert_layout(page, 1440)

        _set_credits(page, credits, 1000)
        plain = _mark(page)
        assert plain["text"] == "1,000"
        assert plain["level"] is None
        assert plain["color"] != AMBER
        assert plain["border"] != AMBER
        _assert_layout(page, 1440)

        page.set_viewport_size({"width": 1920, "height": 1080})
        page.evaluate("() => window.scrollTo(0, 0)")
        _assert_layout(page, 1920)
        page.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.body.classList.contains('mode-cu') && document.body.scrollHeight <= 800",
            timeout=20_000,
        )
        assert cu.locator("[data-testid=credits][data-level]").count() == 0
        cu.close()
