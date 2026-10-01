"""The spectator feed says how many events a filter is hiding."""

from __future__ import annotations

import re

from tests._cu_host import CuHost

TOK = "feed-count-v1-token-p2-000000000000"


def _height(page) -> int:
    return page.evaluate("() => document.documentElement.scrollHeight")


def _count(page) -> str:
    return page.get_by_test_id("feed-filter-count").inner_text()


def test_feed_count_appears_only_when_events_are_hidden(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/")
        page.wait_for_selector("#eventFeed li[data-kind=warp]", timeout=20_000)
        count = page.get_by_test_id("feed-filter-count")
        assert not count.is_visible()
        quiet = _height(page)

        page.locator("[data-filter=move]").uncheck()
        page.wait_for_function(
            """() => {
              const el = document.querySelector('[data-testid=feed-filter-count]');
              return el && !el.hidden && /^showing \\d+ of \\d+$/.test(el.textContent);
            }""",
            timeout=5_000,
        )
        shown, total = (int(n) for n in re.findall(r"\d+", _count(page)))
        assert shown < total
        assert _height(page) == quiet

        page.get_by_test_id("feed-filter-reset").click()
        page.wait_for_function(
            "() => document.querySelector('[data-testid=feed-filter-count]').hidden",
            timeout=5_000,
        )
        assert _height(page) == quiet

        page.locator("#eventActorFilter").select_option("players")
        page.wait_for_function(
            """() => {
              const el = document.querySelector('[data-testid=feed-filter-count]');
              return el && !el.hidden && el.textContent.startsWith('showing ');
            }""",
            timeout=5_000,
        )
        page.locator("#eventActorFilter").select_option("all")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=feed-filter-count]').hidden",
            timeout=5_000,
        )
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        wide.goto(f"{host.base}/")
        wide.wait_for_selector("#eventFeed li[data-kind=warp]", timeout=20_000)
        tall = _height(wide)
        wide.locator("[data-filter=move]").uncheck()
        wide.wait_for_selector("[data-testid=feed-filter-count]:not([hidden])", timeout=5_000)
        assert _height(wide) == tall
        wide.close()
