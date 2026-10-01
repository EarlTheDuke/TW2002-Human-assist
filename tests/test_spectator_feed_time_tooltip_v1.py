"""Spectator feed rows name their day and turn on hover."""

from __future__ import annotations

from tests._cu_host import CuHost

TOK = "feed-time-tooltip-v1-token-p2-000000"


def _height(page) -> int:
    return page.evaluate("() => document.documentElement.scrollHeight")


def _row(page) -> dict:
    return page.evaluate(
        """() => {
          const time = document.querySelector('#eventFeed li .time');
          const row = time && time.parentElement;
          return row ? { title: row.title, time: time.textContent } : null;
        }"""
    )


def test_feed_rows_title_the_day_and_turn(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/")
        page.wait_for_selector("#eventFeed li .time", timeout=20_000)
        quiet = _height(page)
        got = _row(page)
        assert got["title"].startswith("Day ")
        assert ", turn " in got["title"]
        day, turn = got["time"].removeprefix("D").split("·")
        assert got["title"] == f"Day {day}, turn {turn}"
        assert _height(page) == quiet
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        wide.goto(f"{host.base}/")
        wide.wait_for_selector("#eventFeed li .time", timeout=20_000)
        tall = _height(wide)
        got = _row(wide)
        day, turn = got["time"].removeprefix("D").split("·")
        assert got["title"] == f"Day {day}, turn {turn}"
        assert _height(wide) == tall
        wide.close()
