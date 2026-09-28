"""Default /bot keys: S scans, 1-9 warps, same gates as mode=cu.

Keys do nothing inside a form, on key-repeat, or when the verb is not legal.
The CU keymap (X, P, M, and the rest) stays on mode=cu only.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests._cu_host import CuHost
from tw2k.engine.observation import build_observation

TOK = "amz5-keys-token-p2-000000000000"


def _action(request) -> dict:
    return json.loads(request.post_data or "{}").get("action") or {}


def test_default_s_scans_and_1_warps_without_firing_inside_a_form(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector("[data-testid=action-scan]:not([disabled])", timeout=20_000)
        page.wait_for_selector("#warpBtns button", timeout=20_000)
        hints = page.evaluate("""() => ({
            scan: getComputedStyle(document.querySelector('[data-testid=action-scan]'), '::after').content,
            warp: getComputedStyle(document.querySelector('#warpBtns button'), '::before').content,
        })""")
        assert "S" in hints["scan"] and "counter(warpkey)" in hints["warp"]

        def wait_turn() -> None:
            page.wait_for_selector("#turnBanner:not(.turn)", timeout=15_000)
            page.wait_for_selector("#turnBanner.turn", timeout=20_000)

        with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as scan:
            page.keyboard.press("s")
        assert _action(scan.value)["kind"] == "scan"
        wait_turn()
        page.wait_for_selector("#warpBtns button:not([disabled])", timeout=20_000)
        target = page.locator("#warpBtns button").first.get_attribute("data-target")

        with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as warp:
            page.keyboard.press("1")
        got = _action(warp.value)
        assert got["kind"] == "warp" and str(got["args"]["target"]) == target

        wait_turn()
        page.wait_for_selector("[data-testid=action-trade]:not([disabled])", timeout=20_000)
        page.get_by_test_id("action-trade").click()
        page.wait_for_selector("#verbForm:not([hidden]) input", timeout=5_000)
        page.locator("#verbForm input").first.focus()
        posted = []
        page.on("request", lambda r: posted.append(r.url) if r.method == "POST" and r.url.endswith("/action") else None)
        page.keyboard.type("s1")
        page.wait_for_timeout(400)
        assert posted == []
        page.get_by_test_id("verb-cancel").click()
        page.wait_for_function("document.getElementById('verbForm').hidden === true", timeout=5_000)

        page.keyboard.down("s")
        page.wait_for_timeout(700)
        page.keyboard.up("s")
        page.wait_for_timeout(400)
        assert len(posted) == 1
        page.close()


def test_s_does_nothing_when_scan_is_not_legal(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        u = host.runner.state.universe
        me = u.players["P2"]
        me.turns_today = me.turns_per_day
        agent = next(a for a in host.runner.state.agents if a.player_id == "P2")
        # The open turn keeps the observation it was handed. Replace that snapshot
        # with one built after the turns ran out, then let Refresh draw it.
        agent.current_observation = build_observation(u, "P2")
        page.get_by_test_id("refresh").click()
        page.wait_for_function("document.querySelector('[data-testid=action-scan]').disabled === true", timeout=10_000)
        posted = []
        page.on("request", lambda r: posted.append(r.url) if r.method == "POST" and r.url.endswith("/action") else None)
        page.keyboard.press("s")
        page.wait_for_timeout(500)
        assert posted == []
        page.close()
