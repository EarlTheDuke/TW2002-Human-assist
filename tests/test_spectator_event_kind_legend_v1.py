"""Spectator feed category boxes name what they show on hover."""

from __future__ import annotations

from tests._cu_host import CuHost

TOK = "event-kind-legend-v1-token-p2-00000"

TITLES = {
    "combat": "Combat: fights, shots, mines, and ships lost",
    "trade": "Trade: buys and sells at ports",
    "move": "Movement: warps, scans, and landings",
    "thought": "Thoughts: what a commander is thinking",
    "system": "System: day changes, errors, and operator notes",
    "diplomacy": "Diplomacy: hails, corporations, alliances, and planets",
}


def _height(page) -> int:
    return page.evaluate("() => document.documentElement.scrollHeight")


def _titles(page) -> dict:
    return page.evaluate(
        """() => {
          const out = {};
          document.querySelectorAll(".filter-group input[data-filter]").forEach((el) => {
            const label = el.closest("label");
            out[el.dataset.filter] = label ? label.title : "";
          });
          return out;
        }"""
    )


def test_category_labels_title_what_they_show(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/")
        page.wait_for_selector(".filter-group input[data-filter=trade]", timeout=20_000)
        quiet = _height(page)
        assert _titles(page) == TITLES
        assert _height(page) == quiet
        page.close()

        wide = browser.new_page(viewport={"width": 1920, "height": 1080})
        wide.goto(f"{host.base}/")
        wide.wait_for_selector(".filter-group input[data-filter=trade]", timeout=20_000)
        tall = _height(wide)
        assert _titles(wide) == TITLES
        assert _height(wide) == tall
        wide.close()
