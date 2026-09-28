"""Skip during death ends only the death clip. The escape pod still plays.

A second Skip ends the pod. Skip on any other clip clears the queue.
Each Skip increments the counter. Stills in reduced motion and mode=cu
do not start a video.
"""

from __future__ import annotations

import pytest

from tests._cu_host import CuHost

TOK = "v5p-skip-pod-token-p2-00000000"

OBS = {"self_id": "P2", "sector": {"id": 19}}
DEATH = {
    "seq": 1, "kind": "ship_destroyed", "actor_id": "P3", "sector_id": 19,
    "summary": "destroyed", "facts": {"victim": "P2"},
}
TRADE = {
    "seq": 2, "kind": "trade", "actor_id": "P2", "sector_id": 19,
    "summary": "trade", "facts": {"commodity": "fuel_ore"},
}
WARP = {
    "seq": 3, "kind": "warp", "actor_id": "P2", "sector_id": 20,
    "summary": "warp", "facts": {"from": 19, "to": 20},
}


def _arm(page) -> None:
    page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
    page.evaluate("""(pack) => {
        sessionStorage.removeItem('tw2k.media.counters');
        if (window.TW2KViewport) TW2KViewport.setMode(pack.mode);
        TW2KMedia._prime({ lastSeq: 0, visit_sector: 19, docked_in_visit: false });
        TW2KMedia.onEvents([pack.death], pack.obs);
    }""", {"mode": "live", "death": DEATH, "obs": OBS})


def _snap(page) -> dict:
    return page.evaluate("""() => ({
        playing: TW2KMedia._state().playing,
        waiting: TW2KMedia._state().waiting,
        counters: document.getElementById('mediaCounters').textContent,
        video: [...document.querySelectorAll('#vpClip video, #mediaHudVideo')].some((v) => !v.paused && !v.hidden && v.currentTime > 0),
    })""")


def test_skip_during_death_plays_the_pod_then_a_second_skip_ends_it(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}&viewport=live")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        _arm(page)
        assert _snap(page)["playing"] == "self.ship_destroyed"
        assert _snap(page)["waiting"] == "self.escape_pod"

        page.get_by_test_id("viewport-skip").click()
        mid = _snap(page)
        assert mid["playing"] == "self.escape_pod" and mid["waiting"] is None
        assert "skips 1" in mid["counters"]

        page.keyboard.press("Escape")
        done = _snap(page)
        assert done["playing"] is None and done["waiting"] is None
        assert "skips 2" in done["counters"]

        page.evaluate("""(pack) => { TW2KMedia.onEvents([pack.trade, pack.warp], pack.obs); }""",
                      {"trade": TRADE, "warp": WARP, "obs": OBS})
        queued = _snap(page)
        assert queued["playing"] == "dock.port" and queued["waiting"] == "warp.out"
        page.locator("#vpScreen").click()
        cleared = _snap(page)
        assert cleared["playing"] is None and cleared["waiting"] is None
        assert "skips 3" in cleared["counters"]
        page.close()

        cu = browser.new_page(viewport={"width": 1280, "height": 800})
        cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}")
        cu.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        cu.evaluate("""(pack) => {
            sessionStorage.removeItem('tw2k.media.counters');
            if (window.TW2KViewport) TW2KViewport.setMode('stills');
            TW2KMedia._prime({ lastSeq: 0, visit_sector: 19, docked_in_visit: false });
            TW2KMedia.onEvents([pack.death], pack.obs);
        }""", {"death": DEATH, "obs": OBS})
        assert _snap(cu)["playing"] == "self.ship_destroyed"
        cu.keyboard.press("Escape")
        still = _snap(cu)
        assert still["playing"] == "self.escape_pod" and still["video"] is False
        assert "skips 1" in still["counters"]
        cu.close()

        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        quiet = ctx.new_page()
        quiet.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        quiet.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        quiet.evaluate("""(pack) => {
            sessionStorage.removeItem('tw2k.media.counters');
            TW2KMedia._prime({ lastSeq: 0, visit_sector: 19, docked_in_visit: false });
            TW2KMedia.onEvents([pack.death], pack.obs);
            TW2KMedia.skipClip();
        }""", {"death": DEATH, "obs": OBS})
        reduced = _snap(quiet)
        assert reduced["playing"] == "self.escape_pod" and reduced["video"] is False
        quiet.close()
        ctx.close()


def _arm_death(page) -> None:
    page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
    page.evaluate(
        """(pack) => {
            sessionStorage.removeItem('tw2k.media.counters');
            TW2KMedia._prime({ lastSeq: 0, visit_sector: 19, docked_in_visit: false });
            TW2KMedia.onEvents([pack.death], pack.obs);
        }""",
        {"death": DEATH, "obs": OBS},
    )


def _click_dismiss_twice(page) -> None:
    page.wait_for_selector("[data-testid=media-hud-dismiss]", state="visible", timeout=10_000)
    page.get_by_test_id("media-hud-dismiss").click()
    mid = _snap(page)
    assert mid["playing"] == "self.escape_pod" and mid["waiting"] is None, mid
    assert "skips 1" in mid["counters"]
    page.get_by_test_id("media-hud-dismiss").click()
    done = _snap(page)
    assert done["playing"] is None and done["waiting"] is None, done
    assert "skips 2" in done["counters"]


def test_death_card_dismiss_keeps_the_pod(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    sync_api = pytest.importorskip("playwright.sync_api")
    with CuHost(tmp_path, TOK + "-x", turns_per_day=500) as host, sync_api.sync_playwright() as pw:
        launched = []
        for name in ("chromium", "firefox"):
            try:
                launched.append(getattr(pw, name).launch())
            except Exception as exc:
                pytest.fail(f"{name} did not launch: {exc}")
        try:
            chromium = launched[0]
            cu = chromium.new_page(viewport={"width": 1280, "height": 800})
            cu.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}-x")
            _arm_death(cu)
            _click_dismiss_twice(cu)
            cu.evaluate(
                """(pack) => {
                    sessionStorage.removeItem('tw2k.media.counters');
                    TW2KMedia._prime({ lastSeq: 0, visit_sector: 19, docked_in_visit: false });
                    TW2KMedia.onEvents([pack.death], pack.obs);
                    TW2KMedia.skipClip();
                    TW2KMedia.skipClip();
                    TW2KMedia.onEvents([pack.trade], pack.obs);
                }""",
                {"death": DEATH, "obs": OBS, "trade": TRADE},
            )
            fast = _snap(cu)
            assert fast["playing"] == "dock.port" and fast["waiting"] is None, fast
            assert "skips 2" in fast["counters"]
            cu.close()

            default = chromium.new_page(viewport={"width": 1440, "height": 900})
            default.goto(f"{host.base}/bot?seat=P2&token={TOK}-x&viewport=live")
            default.wait_for_selector("#turnBanner.turn", timeout=20_000)
            _arm_death(default)
            default.evaluate(
                """() => TW2KMedia.playEntry(
                    { still: 'stills/combat_alert.png', caption: 'Ship destroyed' },
                    'self.ship_destroyed')"""
            )
            default.wait_for_selector("[data-testid=media-hud-dismiss]", state="visible", timeout=10_000)
            default.get_by_test_id("media-hud-dismiss").click()
            shown = _snap(default)
            assert shown["playing"] == "self.escape_pod" and shown["waiting"] is None, shown
            assert "skips 1" in shown["counters"]
            default.close()

            fox = launched[1].new_page(viewport={"width": 1280, "height": 800})
            fox.goto(f"{host.base}/bot?mode=cu&seat=P2&token={TOK}-x")
            _arm_death(fox)
            _click_dismiss_twice(fox)
            fox.close()
        finally:
            for browser in launched:
                browser.close()

