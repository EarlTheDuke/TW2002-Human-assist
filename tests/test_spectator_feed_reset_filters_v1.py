"""Reset re-checks every spectator feed category and forgets the saved choice."""

from __future__ import annotations

from tests._cu_host import CuHost

TOK = "feed-reset-filters-v1-token-p2-000000"
KEYS = ("combat", "trade", "move", "thought", "system", "diplomacy")


def _checked(page) -> dict:
    return {key: page.locator(f"[data-filter={key}]").is_checked() for key in KEYS}


def test_reset_rechecks_categories_and_clears_the_saved_choice(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        posts: list[str] = []
        page.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
        page.goto(f"{host.base}/")
        page.wait_for_selector("[data-filter=combat]", timeout=20_000)
        reset = page.get_by_test_id("feed-filter-reset")
        assert not reset.is_visible()
        assert _checked(page) == {key: True for key in KEYS}

        page.locator("[data-filter=combat]").uncheck()
        page.locator("[data-filter=trade]").uncheck()
        assert reset.is_visible()
        page.evaluate("() => localStorage.setItem('tw2k:actorFilter', 'players')")
        reset.click()
        assert _checked(page) == {key: True for key in KEYS}
        assert not reset.is_visible()
        assert page.evaluate("() => localStorage.getItem('tw2k:eventFilters')") is None
        assert page.evaluate("() => localStorage.getItem('tw2k:actorFilter')") == "players"
        assert posts == []

        page.reload()
        page.wait_for_selector("[data-filter=combat]", timeout=20_000)
        assert _checked(page) == {key: True for key in KEYS}
        assert not page.get_by_test_id("feed-filter-reset").is_visible()
        page.close()
