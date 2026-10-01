"""P opens the plot course form and focuses its target field."""

from __future__ import annotations

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "key-plot-port-v1-token-p2-000000000"
MAP_TOP = {1440: 714}


def _layout(page) -> dict:
    return page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('#mfd [role=tab]')].map((t) => t.getBoundingClientRect().top);
          const tabTop = Math.min(...tabs);
          return {
            mapY: document.querySelector('#mapCard').getBoundingClientRect().top,
            mfd: document.querySelector('.mfd-body').getBoundingClientRect().height,
            tabSpread: Math.max(...tabs) - tabTop,
          };
        }"""
    )


def test_p_opens_plot_course_and_focuses_the_target(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        posts: list[str] = []
        page.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector("[data-testid=action-plot-course]:not([disabled])", timeout=20_000)
        lay = _layout(page)
        assert abs(lay["mapY"] - MAP_TOP[1440]) < 4, lay["mapY"]
        assert abs(lay["mfd"] - 420) < 1
        assert lay["tabSpread"] < 2

        page.keyboard.press("p")
        page.wait_for_selector("[data-testid=plot-target]", timeout=5_000)
        focused = page.evaluate("() => document.activeElement.getAttribute('data-testid')")
        assert focused == "plot-target"
        assert posts == []
        page.evaluate("() => window.scrollTo(0, 0)")
        lay = _layout(page)
        assert abs(lay["mapY"] - MAP_TOP[1440]) < 4, lay["mapY"]
        assert abs(lay["mfd"] - 420) < 1

        page.keyboard.press("p")
        assert page.locator("[data-testid=verb-form]").is_visible()
        assert posts == []
        page.get_by_test_id("verb-cancel").click()
        page.wait_for_function(
            "() => document.querySelector('[data-testid=verb-form]').hidden",
            timeout=5_000,
        )

        page.get_by_test_id("keys-help").click()
        page.wait_for_selector("[data-testid=keys-help-overlay]:not([hidden])", timeout=5_000)
        assert page.locator("[data-hotkey=P]").inner_text() == "P Plot course"
        page.keyboard.press("p")
        assert page.evaluate("() => document.querySelector('[data-testid=verb-form]').hidden")
        assert page.evaluate("() => document.getElementById('keysHelp').hidden === false")
        assert page.get_by_test_id("keys-help-overlay").is_visible()
        page.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function(
            "() => document.body.classList.contains('mode-cu') && document.body.scrollHeight <= 800",
            timeout=20_000,
        )
        cu.close()
