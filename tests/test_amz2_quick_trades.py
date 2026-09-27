"""One-click trades on the default layout, plus the manifest-queue nit.

Default `/bot`: a port that buys fuel, with fuel aboard, shows
`quick-sell-fuel_ore`. One click posts the trade. An empty hold hides that
button. Off a port, or while a trade is not allowed, the row is empty.
`mode=cu` keeps `cu-quick-*` and still fits 1280x800.
"""

from __future__ import annotations

import time
from pathlib import Path

from tests._cu_host import CuHost

TOK = "amz2-quick-trade-token-p2-000000"


def test_default_layout_sells_in_one_click_and_hides_when_it_cannot(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        sell = page.get_by_test_id("quick-sell-fuel_ore")
        sell.wait_for(state="visible", timeout=10_000)
        assert page.get_by_test_id("action-sell").is_visible()
        sell.click()
        page.wait_for_function(
            "() => { const t = document.querySelector('#lastResult').textContent || '';"
            "return t.indexOf('SELL') !== -1 && t.indexOf('ok') !== -1; }",
            timeout=15_000,
        )
        page.wait_for_function("() => !document.querySelector('[data-testid=quick-sell-fuel_ore]')", timeout=15_000)

        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        choices = page.evaluate("() => [...document.querySelectorAll('[data-testid^=warp-]')].map(b => Number(b.getAttribute('data-target')))")
        u = host.runner.state.universe
        bare = next((dest for dest in choices if not u.sectors[dest].port), None)
        assert bare is not None, choices
        page.get_by_test_id(f"warp-{bare}").click()
        page.wait_for_function(
            "() => (document.querySelector('#lastResult').textContent || '').indexOf('WARP') !== -1",
            timeout=15_000,
        )
        page.wait_for_function("() => document.querySelectorAll('#quickTrades button').length === 0", timeout=10_000)
        page.close()

        cu = browser.new_page(viewport={"width": 1280, "height": 800})
        cu.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK}")
        cu.wait_for_selector("#cuTurn.turn", timeout=20_000)
        assert cu.evaluate("document.scrollingElement.scrollHeight") <= 800
        assert cu.locator("#cuScreen [data-testid^=quick-]").count() == 0
        assert "cu-quick-" in (Path(__file__).resolve().parents[1] / "web" / "bot.js").read_text(encoding="utf-8")
        cu.close()


def test_events_wait_for_the_manifest_and_a_failed_fetch_clears_the_queue(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK + "-m", turns_per_day=40) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.route("**/media/manifest.json", lambda route: route.abort())
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}-m")
        page.wait_for_function("window.TW2KMedia", timeout=20_000)
        quiet = page.evaluate("""() => {
            const obs = { self_id: 'P2', sector: { id: 19 } };
            TW2KMedia.onEvents([{ seq: 1, kind: 'warp', actor_id: 'P2', sector_id: 8, summary: 'warp', facts: { from: 4, to: 8 } }], obs, { history: true });
            TW2KMedia.onEvents([{ seq: 2, kind: 'trade', actor_id: 'P2', sector_id: 19, summary: 'trade', facts: { commodity: 'fuel_ore', qty: 1, side: 'sell' } }], obs);
            return TW2KMedia._state();
        }""")
        assert quiet["playedKeys"] == [], quiet
        deadline = time.time() + 8
        pending = quiet.get("pending")
        while time.time() < deadline and pending != 0:
            time.sleep(0.1)
            pending = page.evaluate("TW2KMedia._state().pending")
        assert pending == 0
        assert page.evaluate("TW2KMedia._state().playedKeys") == []
        page.close()


def test_a_404_manifest_clears_the_pending_queue(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK + "-404", turns_per_day=40) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.route("**/media/manifest.json", lambda route: route.fulfill(status=404, body="missing"))
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}-404")
        page.wait_for_function("window.TW2KMedia", timeout=20_000)
        page.evaluate("""() => {
            const obs = { self_id: 'P2', sector: { id: 19 } };
            TW2KMedia.onEvents([{ seq: 1, kind: 'warp', actor_id: 'P2', sector_id: 8, summary: 'warp', facts: { from: 4, to: 8 } }], obs, { history: true });
            TW2KMedia.onEvents([{ seq: 2, kind: 'trade', actor_id: 'P2', sector_id: 19, summary: 'trade', facts: { commodity: 'fuel_ore', qty: 1, side: 'sell' } }], obs);
        }""")
        deadline = time.time() + 8
        pending = 1
        while time.time() < deadline and pending != 0:
            time.sleep(0.1)
            pending = page.evaluate("TW2KMedia._state().pending")
        assert pending == 0
        assert page.evaluate("TW2KMedia._state().playedKeys") == []
        page.close()
