"""Unchecked spectator feed filters come back after a reload."""

from __future__ import annotations

from tests._cu_host import CuHost

TOK = "feed-filter-memory-v1-token-p2-00000000"
KEYS = ("combat", "trade", "move", "thought", "system", "diplomacy")


def _checked(page) -> dict:
    return {
        key: page.locator(f"[data-filter={key}]").is_checked()
        for key in KEYS
    }


def test_unchecked_feed_filters_survive_reload(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        posts: list[str] = []
        page.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
        page.goto(f"{host.base}/")
        page.wait_for_selector("[data-filter=combat]", timeout=20_000)
        assert page.locator("[data-testid=galaxy-toggle]").count() == 1
        assert _checked(page) == {key: True for key in KEYS}

        page.locator("[data-filter=combat]").uncheck()
        page.locator("[data-filter=diplomacy]").uncheck()
        assert posts == []
        page.reload()
        page.wait_for_selector("[data-filter=combat]", timeout=20_000)
        got = _checked(page)
        assert got["combat"] is False
        assert got["diplomacy"] is False
        assert got["trade"] is True
        assert got["move"] is True
        assert got["thought"] is True
        assert got["system"] is True
        stored = page.evaluate("() => localStorage.getItem('tw2k:eventFilters')")
        assert stored == '["combat","diplomacy"]'

        page.locator("[data-filter=combat]").check()
        page.reload()
        page.wait_for_selector("[data-filter=combat]", timeout=20_000)
        got = _checked(page)
        assert got["combat"] is True
        assert got["diplomacy"] is False
        page.close()
