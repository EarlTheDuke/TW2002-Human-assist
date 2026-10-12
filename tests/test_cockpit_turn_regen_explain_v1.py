"""Turns that come back while you wait say so.

A new day still refills without that sentence. The number is the rise the
page just saw, and the rate is the day's turns spread across 24 hours.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from tests._cu_host import CuHost

TOK = "turn-regen-v1-token-p2-00000000000000"
SHOT = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-turn-regen" / "turns-back.png"
COPY = Path(r"C:\Users\sugar\tw2002_reference\cockpit_assets\screens\turns-back.png")


def test_a_same_day_rise_names_the_wait(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        hits = {"n": 0}

        def paint(route):
            response = route.fetch()
            try:
                data = response.json()
            except Exception:
                route.fulfill(response=response)
                return
            obs = data.get("observation")
            hits["n"] += 1
            if isinstance(obs, dict) and hits["n"] >= 2:
                obs["turns_remaining"] = int(obs.get("turns_remaining") or 0) + 2
            route.fulfill(response=response, json=data)

        page.route("**/observation**", paint)
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        words = page.evaluate(
            """() => {
              const P = window.TW2KParity;
              return {
                rise: P.turnRegenNote({day: 1, left: 7}, {day: 1, turns_remaining: 9, turns_per_day: 250}),
                down: P.turnRegenNote({day: 1, left: 9}, {day: 1, turns_remaining: 7, turns_per_day: 250}),
                newDay: P.turnRegenNote({day: 1, left: 2}, {day: 2, turns_remaining: 250, turns_per_day: 250}),
              };
            }"""
        )
        assert words["rise"] == "+2 while you waited. Spent turns come back as time passes, spread across 24 hours, and stop at 250."
        assert words["down"] == ""
        assert words["newDay"] == ""
        page.locator("[data-testid=refresh]").click()
        page.wait_for_function(
            "document.querySelector('[data-testid=turns-regen]').textContent.includes('while you waited')",
            timeout=20_000,
        )
        note = page.locator("[data-testid=turns-regen]").inner_text()
        assert "while you waited" in note
        assert "24 hours" in note
        assert "stop at" in note
        page.locator("[data-testid=turns-regen]").scroll_into_view_if_needed()
        SHOT.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOT))
        COPY.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SHOT, COPY)
        page.close()
