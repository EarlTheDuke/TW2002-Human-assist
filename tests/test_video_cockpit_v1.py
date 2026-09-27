"""Video cockpit V1 - viewport shell, procedural starfield ambient, per-hull cockpit frame.

Done when (phase plan V1): the default /bot at 1440x900 shows the viewport and every
pre-existing data-testid is still visible (baseline captured before the change in
tests/fixtures/bot_default_visible_testids.json); mode=cu shows no viewport and the G2
test passes unchanged; reduced motion = no animation, no <video>; click-to-result timing
with the viewport live stays within ~5% of viewport off.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import statistics
from pathlib import Path

from tests._cu_host import CuHost

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")
JS = (ROOT / "web" / "viewport.js").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "bot.css").read_text(encoding="utf-8")
BASELINE = json.loads((ROOT / "tests" / "fixtures" / "bot_default_visible_testids.json").read_text(encoding="utf-8"))
TOK = "v1-viewport-token-p2-00000000000"


def test_viewport_markup_is_default_layout_only_and_decoration_only() -> None:
    main = HTML.split('id="main"')[1]
    assert 'id="viewport"' in main and 'data-testid="viewport"' in main, "viewport lives in #main (hidden in mode=cu)"
    assert 'id="viewport"' not in HTML.split('id="cuScreen"')[1].split("</section>\n\n  <!-- Scoreboard")[0]
    for tid in ("viewport-stars", "viewport-frame", "viewport-caption", "viewport-skip", "viewport-mode-live",
                "viewport-mode-stills", "viewport-mode-off", "viewport-sound"):
        assert f'data-testid="{tid}"' in HTML, tid
    assert "<video" not in HTML.split('id="viewport"')[1].split("</section>")[0], "V1 has no video"
    assert HTML.index("/static/viewport.js") < HTML.index("/static/bot.js")
    block = "/* ---- V1 video cockpit" + CSS.split("/* ---- V1 video cockpit")[1].split("/* ---- G6: game over")[0]
    block = re.sub(r"/\*.*?\*/", "", block, flags=re.S)
    assert not re.search(r"\b(animation|transition)[\w-]*\s*:", block), "no CSS motion; the canvas is the only motion"
    # Fog / decoration: the viewport reads only the Observation it is handed; no network, no spectator state.
    assert "fetch(" not in JS and "/state" not in JS and "XMLHttpRequest" not in JS
    assert 'params.get("mode") === "cu"' in JS and "if (CU)" in JS and "cu: true" in JS
    assert JS.index("if (CU)") < JS.index("getContext"), "the starfield canvas starts only after the CU return"


def _goto(browser, host, extra: str = "", **ctx):
    context = browser.new_context(viewport={"width": 1440, "height": 900}, **ctx)
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{host.base}/bot?seat=P2&token={TOK}{extra}")
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_function("window.TW2KViewport && window.TW2KViewport.state().sector !== null", timeout=20_000)
    return context, page, errors


def test_default_bot_shows_viewport_and_keeps_every_baseline_testid(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        ctx, page, errors = _goto(browser, host)
        vp = page.get_by_test_id("viewport")
        box = vp.bounding_box()
        assert vp.is_visible() and box and box["y"] + box["height"] <= 900, box
        st = page.evaluate("TW2KViewport.state()")
        me = host.runner.state.universe.players["P2"]
        assert st["mode"] == "live" and st["animating"] is True and st["hull"] == "hauler"
        assert st["caption"].startswith("Sector ") and page.get_by_test_id("viewport-caption").is_visible()
        shot = tmp_path / "viewport-default-1440x900.png"
        page.screenshot(path=str(shot))
        if os.environ.get("TW2K_SHOT_DIR"):
            shutil.copy(shot, Path(os.environ["TW2K_SHOT_DIR"]) / shot.name)
        visible = set(page.evaluate("""() => [...document.querySelectorAll('[data-testid]')]
            .filter(e => { const r = e.getBoundingClientRect(); return e.offsetParent !== null && r.width > 0 && r.height > 0; })
            .map(e => e.getAttribute('data-testid'))"""))
        missing = [t for t in BASELINE["testids"] if t not in visible]
        assert not missing, f"pre-existing data-testids no longer visible: {missing}"
        assert me.sector_id is not None and not errors, errors
        ctx.close()


def test_modes_hull_skip_and_focus(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        ctx, page, errors = _goto(browser, host)
        page.get_by_test_id("viewport-mode-stills").click()
        st = page.evaluate("TW2KViewport.state()")
        assert st["mode"] == "stills" and st["animating"] is False
        assert page.get_by_test_id("viewport-mode-stills").get_attribute("aria-pressed") == "true"
        page.get_by_test_id("viewport-mode-off").click()
        assert not page.locator("#vpScreen").is_visible() and page.get_by_test_id("viewport-caption").is_visible()
        page.reload()
        page.wait_for_function("window.TW2KViewport && window.TW2KViewport.state().sector !== null", timeout=20_000)
        assert page.evaluate("TW2KViewport.state().mode") == "off", "mode persists"
        page.get_by_test_id("viewport-mode-live").click()
        assert page.evaluate("TW2KViewport.state().animating") is True
        # per-hull frame follows the seat's own ship class
        page.evaluate("TW2KViewport.update({sector:{id:77,port:null}, ship:{class:'battleship'}})")
        assert page.get_by_test_id("viewport").get_attribute("data-hull") == "heavy"
        page.evaluate("TW2KViewport.update({sector:{id:77,port:null}, ship:{class:'imperial_starship'}})")
        assert page.get_by_test_id("viewport").get_attribute("data-hull") == "capital"
        # Skip never steals focus from the verb pad
        page.get_by_test_id("viewport-skip").click()
        assert page.evaluate("document.activeElement === document.querySelector('[data-testid=viewport-skip]')") is False
        assert page.evaluate("TW2KViewport.state().caption") == "Sector 77 · deep space"
        ctx.close()
        ctx2, page2, _ = _goto(browser, host, "&viewport=stills")
        assert page2.evaluate("TW2KViewport.state()")["mode"] == "stills", "?viewport= overrides the saved mode"
        ctx2.close()
        assert not errors, errors


def test_reduced_motion_means_no_animation_and_no_video(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        ctx, page, errors = _goto(browser, host, reduced_motion="reduce")
        st = page.evaluate("TW2KViewport.state()")
        assert st["reducedMotion"] is True and st["mode"] == "stills" and st["animating"] is False
        page.get_by_test_id("viewport-mode-live").click()
        assert page.evaluate("TW2KViewport.state().animating") is False, "Live is refused under reduced motion"
        styles = page.evaluate("""() => ['#viewport', '#vpScreen', '#vpStars', '.vp-frame'].map(s => {
            const cs = getComputedStyle(document.querySelector(s)); return [cs.animationName, cs.transitionDuration]; })""")
        assert all(a == "none" and t in ("0s", "") for a, t in styles), styles
        assert page.evaluate("document.querySelectorAll('#viewport video').length") == 0
        assert not errors, errors
        ctx.close()


def test_cu_mode_has_no_viewport(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK}")
        page.wait_for_selector("#cuTurn.turn", timeout=20_000)
        assert not page.get_by_test_id("viewport").is_visible()
        st = page.evaluate("TW2KViewport.state()")
        assert st["cu"] is True and st["animating"] is False
        assert page.evaluate("document.scrollingElement.scrollHeight") <= 800


def _round_trip_ms(page) -> float:
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    page.wait_for_timeout(100)
    return page.evaluate("""async () => {
        const last = document.querySelector('#lastResult');
        const before = last.textContent;
        const t0 = performance.now();
        document.querySelector('[data-testid=action-scan]').click();
        while (last.textContent === before) await new Promise((r) => setTimeout(r, 2));
        return performance.now() - t0;
    }""")


def test_click_to_result_timing_live_vs_off(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        results = {}
        for mode in ("off", "live", "off", "live"):
            ctx, page, _ = _goto(browser, host, f"&viewport={mode}")
            assert page.evaluate("TW2KViewport.state().mode") == mode
            samples = [_round_trip_ms(page) for _ in range(8)]
            results.setdefault(mode, []).extend(samples)
            ctx.close()
        off, live = statistics.median(results["off"]), statistics.median(results["live"])
        print(f"[v1 timing] click->result median: off {off:.0f} ms, live {live:.0f} ms ({(live / off - 1) * 100:+.1f}%)")
        if os.environ.get("TW2K_SHOT_DIR"):
            (Path(os.environ["TW2K_SHOT_DIR"]) / "viewport-timing.json").write_text(json.dumps(
                {"off_ms": results["off"], "live_ms": results["live"], "off_median": off, "live_median": live}), encoding="utf-8")
        assert live <= off * 1.05 + 25, (off, live)  # ~5% budget plus 25 ms timer noise
