"""One-click trades show the list-price total. Plot previews from memory only.

The credit total is envelope price times quantity. The plot form names the
hop count and the first sector when this seat already knows a path, and
otherwise says the route is shown after plotting. Neither reads a new route
from the server.
"""

from __future__ import annotations

import json
import re
from urllib.request import Request, urlopen

from tests._cu_host import VIEW_H, VIEW_W, CuHost

TOK = "amz11-totals-token-p2-0000000000"


def _observation(host: CuHost, token: str) -> dict:
    req = Request(
        f"{host.base}/harness/v1/P2/observation?wait_s=0&peek=1",
        headers={"Authorization": f"Bearer {token}", "X-TW2K-Seat": "P2"},
    )
    with urlopen(req, timeout=15) as resp:
        return json.load(resp)


def _trade(obs: dict) -> dict:
    return next(la for la in obs["legal_actions"] if la["kind"] == "trade")


def test_quick_trade_buttons_show_list_price_times_qty(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        sell = page.get_by_test_id("quick-sell-fuel_ore")
        sell.wait_for(state="visible", timeout=15_000)
        obs = _observation(host, TOK)["observation"]
        params = _trade(obs)["params"]
        qty = params["qty"]["max_by"]["fuel_ore"]["sell"]
        unit = params["unit_price"]["listed_by"]["fuel_ore"]["sell"]
        text = sell.inner_text()
        match = re.search(r"x([\d,]+) - ([\d,]+) cr", text)
        assert match, text
        assert int(match.group(1).replace(",", "")) == qty
        assert int(match.group(2).replace(",", "")) == unit * qty
        assert "SELL Fuel" in text

        for width, height in ((1440, 900), (1280, 800)):
            page.set_viewport_size({"width": width, "height": height})
            wide = page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
            assert wide
        page.close()

        cu = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function("() => document.querySelector('[data-testid=cu-turn]')?.textContent.includes('YOUR TURN')", timeout=20_000)
        cu.wait_for_selector("[data-testid=cu-quick-sell-fuel_ore]", timeout=15_000)
        fit = cu.evaluate("""() => {
            const b = document.querySelector('[data-testid=cu-quick-sell-fuel_ore]');
            const num = b.querySelector('.qnum');
            const br = b.getBoundingClientRect();
            const nr = num.getBoundingClientRect();
            return {
                text: b.textContent,
                numberInside: nr.left >= br.left - 1 && nr.right <= br.right + 1 && num.scrollWidth <= num.clientWidth + 1,
                scroll: document.scrollingElement.scrollHeight,
                wide: document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
            };
        }""")
        match = re.search(r"x([\d,]+) - ([\d,]+) cr", fit["text"])
        assert match, fit["text"]
        assert int(match.group(1).replace(",", "")) == qty
        assert int(match.group(2).replace(",", "")) == unit * qty
        assert fit["numberInside"] and fit["scroll"] <= VIEW_H and fit["wide"], fit
        cu.close()


def test_plot_preview_uses_known_hops_or_says_after_plotting(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK + "-plot") as host:
        page = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}-plot")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector("#warpBtns button", timeout=15_000)
        neighbour = page.locator("#warpBtns button").first.get_attribute("data-target")
        calls = []
        page.on("request", lambda r: calls.append(r.url) if r.method == "POST" or "plot" in r.url else None)
        page.get_by_test_id("action-plot-course").click()
        page.wait_for_selector("#verbForm[data-verb=plot_course] [data-testid=plot-target]", timeout=5_000)
        page.locator("[data-testid=plot-target]").fill(str(neighbour))
        page.wait_for_function(
            f"() => {{ const t = document.querySelector('[data-testid=verb-preview]').textContent;"
            f" return t.includes('1 hop') && t.includes('first sector {neighbour}'); }}",
            timeout=5_000,
        )
        page.locator("[data-testid=plot-target]").fill("99999")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=verb-preview]').textContent === 'route shown after plotting'",
            timeout=5_000,
        )
        assert calls == []
        page.close()
