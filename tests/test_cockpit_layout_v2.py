"""cockpit-layout-v2. The map fills the center column and can be moved."""
from __future__ import annotations

from tests._cu_host import CuHost

TOK = "layout-v2-token-p2-000000000000"


def _open(page, host) -> None:
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_selector("#knownMap .node.here", timeout=15_000)


def test_center_column_and_map_controls(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        _open(page, host)
        share = page.evaluate(
            """() => {
              const cols = [...document.querySelectorAll('#main > .col')].map((c) => c.getBoundingClientRect().width);
              const map = document.querySelector('#knownMap').getBoundingClientRect().width;
              return { cols, map, page: window.innerWidth };
            }"""
        )
        total = sum(share["cols"])
        assert abs(share["cols"][1] / total - 0.6) < 0.05, share
        assert share["map"] > share["page"] * 0.45, share
        assert page.locator("#knownMap .node.stub[data-x]").count() == 0
        page.get_by_test_id("map-zoom-in").click()
        zoomed = page.locator("#knownMap").get_attribute("viewBox")
        assert zoomed != "0 0 100 100"
        page.keyboard.press("c")
        assert page.locator("#knownMap").get_attribute("viewBox") == "0 0 100 100"
        page.get_by_test_id("map-recenter").click()
        assert page.locator("#knownMap").get_attribute("viewBox") == "0 0 100 100"
        page.close()
