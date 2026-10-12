"""CONFIRM with Execute unchecked plots the route and does not fly it.

The shortest known path was already the one drawn. A hop with no remembered
return is marked on the warp button and on the route.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from tests._cu_host import CuHost

TOK = "plot-execute-v2-token-p2-000000000000"
SHOT = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-play-fixes" / "plan-only.png"
COPY = Path(r"C:\Users\sugar\tw2002_reference\cockpit_assets\screens\plan-only.png")


def _action(request) -> dict:
    return json.loads(request.post_data or "{}").get("action") or {}


def test_unchecked_confirm_plots_and_stays(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector("#warpBtns button:not([disabled])", timeout=20_000)
        with page.expect_request(
            lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000,
        ) as warp:
            page.keyboard.press("1")
        assert _action(warp.value)["kind"] == "warp"
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector("#warpBtns button[data-oneway='1']", timeout=10_000)
        target = page.locator("#warpBtns button").first.get_attribute("data-target")
        before = page.locator("#sbSector").inner_text()
        page.locator(f"[data-testid=map-sector-{target}]").click()
        page.wait_for_selector("[data-testid=verb-preview]", timeout=10_000)
        preview = page.locator("[data-testid=verb-preview]").inner_text()
        assert "plan only" in preview
        assert "one-way" in preview
        assert page.locator("[data-testid=plot-execute]").is_checked() is False
        page.wait_for_function(
            "() => Number(document.querySelector('[data-testid=route-line]')?.getAttribute('data-oneway-hops') || 0) > 0",
            timeout=5_000,
        )
        SHOT.parent.mkdir(parents=True, exist_ok=True)
        page.locator("[data-testid=verb-form], #verbForm").scroll_into_view_if_needed()
        page.screenshot(path=str(SHOT))
        COPY.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SHOT, COPY)
        with page.expect_request(
            lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000,
        ) as posted:
            page.locator("[data-testid=verb-submit]").click()
        action = _action(posted.value)
        assert action["kind"] == "plot_course"
        assert action["args"]["execute"] is False
        page.wait_for_function(
            "(prev) => (document.querySelector('#lastResult')?.textContent || '') !== prev",
            arg=page.locator("#lastResult").inner_text(),
            timeout=20_000,
        )
        assert page.locator("#sbSector").inner_text() == before
        page.close()
