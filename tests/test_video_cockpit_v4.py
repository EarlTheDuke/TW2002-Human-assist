"""Video cockpit V4-lite: cache headers, idle poster preload, session counters, CU stills.

No generated video and no paid API. The browser half uses a test host on a
free port >= 8033.
"""

from __future__ import annotations

import json
import shutil
import statistics
import subprocess
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests._cu_host import VIEW_H, VIEW_W, CuHost, inside
from tests.test_cockpit_cu_g2 import DECISION_FIELDS
from tw2k.server.media_cache import IMMUTABLE, REVALIDATE, MediaStaticFiles, media_cache_control

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
TOK = "v4-lite-token-p2-00000000000000"
GUIDE = (ROOT / "docs" / "GROK_BOT_PLAYER_GUIDE.md").read_text(encoding="utf-8")


def test_hashed_media_is_immutable_and_other_media_revalidates(tmp_path: Path) -> None:
    assert media_cache_control("media/posters/dock.a1b2c3d4.png") == IMMUTABLE
    assert media_cache_control("media/manifest.json") == REVALIDATE
    assert media_cache_control("media/stills/trade_port.png") == REVALIDATE
    assert media_cache_control("app.js") is None

    root = tmp_path / "web"
    (root / "media" / "posters").mkdir(parents=True)
    (root / "media" / "stills").mkdir()
    (root / "media" / "manifest.json").write_text("{}", encoding="utf-8")
    (root / "media" / "stills" / "trade_port.png").write_bytes(b"png")
    (root / "media" / "posters" / "dock.a1b2c3d4.png").write_bytes(b"png")
    (root / "bot.js").write_text("/*js*/", encoding="utf-8")
    app = FastAPI()
    app.mount("/static", MediaStaticFiles(directory=str(root)), name="static")
    client = TestClient(app)
    hashed = client.get("/static/media/posters/dock.a1b2c3d4.png")
    still = client.get("/static/media/stills/trade_port.png")
    manifest = client.get("/static/media/manifest.json")
    script = client.get("/static/bot.js")
    assert hashed.status_code == still.status_code == manifest.status_code == script.status_code == 200
    assert hashed.headers["cache-control"] == IMMUTABLE
    assert still.headers["cache-control"] == REVALIDATE
    assert manifest.headers["cache-control"] == REVALIDATE
    assert "immutable" not in script.headers.get("cache-control", "")
    assert media_cache_control("media/clips/v3-pilot/dock_port_std_a.8d5213fb.webm") == IMMUTABLE


def test_default_hold_key_ignores_repeat_and_editable() -> None:
    js = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")
    assert "if (ev.repeat" in js
    assert "isContentEditable" in js
    assert '(ev.key || "").toLowerCase()' in js


def test_guide_labels_cu_live_as_not_for_scored_play() -> None:
    assert "not for scored CU play" in GUIDE
    assert "?viewport=off" in GUIDE
    assert "H (hold / end slot) works on the default layout and in `mode=cu`" in GUIDE


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_stale_waiting_clip_is_counted_once() -> None:
    script = (
        f"const R = require({json.dumps(str(ROOT / 'web' / 'media-resolver.js'))});"
        "const s = R.createSession({defaults:{stale_ms:4000}, clips:{}});"
        "s.consider([{clip_key:'warp.out', priority:2, seq:1, sector_id:4}], 0);"
        "s.consider([{clip_key:'dock.port', priority:2, seq:2, sector_id:8}], 10);"
        "const late = s.consider([], 5000);"
        "const posted = R.createSession({defaults:{stale_ms:4000}, clips:{}});"
        "posted.consider([{clip_key:'warp.out', priority:2, seq:1}], 0);"
        "posted.consider([{clip_key:'dock.port', priority:2, seq:2}], 10);"
        "const dropped = posted.consider([], 20, {postedSeq:9});"
        "process.stdout.write(JSON.stringify({late, drops:s.state().staleDrops, posted:dropped.staleDropped}));"
    )
    got = json.loads(subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True, timeout=30).stdout)
    assert got["late"]["staleDropped"] == 1 and got["late"]["waiting"] is None
    assert got["drops"] == 1
    assert got["posted"] == 0, "a newer self action is not a stale drop"


def test_preload_counters_cu_slot_and_timing(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_function("window.TW2KMedia && TW2KMedia.preloadState().done === true", timeout=20_000)
        pre = page.evaluate("TW2KMedia.preloadState()")
        assert pre["skipped"] == "" and pre["urls"] >= 1
        assert 0 < pre["bytes"] <= 12 * 1024 * 1024
        assert pre["beforeInteractive"] <= 150 * 1024
        bench = page.evaluate("TW2KMedia.benchSwap(40)")
        print(f"[v4 bench] resolve+swap p95 {bench['p95']:.2f} ms max {bench['max']:.2f} ms n={bench['n']}")
        assert bench["n"] == 40 and bench["p95"] <= 4.0, bench

        counters = page.evaluate("""() => {
            sessionStorage.removeItem('tw2k.media.counters');
            TW2KMedia._prime({ lastSeq: 0, visit_sector: 19, docked_in_visit: false });
            const obs = { self_id: 'P2', sector: { id: 19 } };
            TW2KMedia.onEvents([{ seq: 1, kind: 'warp', actor_id: 'P2', sector_id: 19, summary: 'warp', facts: { from: 18, to: 19 } }], obs);
            TW2KMedia.onEvents([{ seq: 2, kind: 'combat', actor_id: 'P3', sector_id: 19, summary: 'combat', facts: { attacker: 'P3', defender: 'P2', outcome: 'hit' } }], obs);
            TW2KMedia.skipClip();
            return document.getElementById('mediaCounters').textContent;
        }""")
        assert "plays 2" in counters and "skips 1" in counters
        assert "preemptions 1" in counters and "poster-fallbacks 0" in counters
        assert "stale-drops 0" in counters
        page.keyboard.press("h")
        page.wait_for_function("document.querySelector('[data-testid=hold-slot]').getAttribute('aria-pressed') === 'true'", timeout=5_000)
        assert "(H)" in page.get_by_test_id("hold-slot").inner_text()
        page.keyboard.press("h")
        page.wait_for_function("document.querySelector('[data-testid=hold-slot]').getAttribute('aria-pressed') === 'false'", timeout=5_000)
        page.close()

        saved = browser.new_page(viewport={"width": 1440, "height": 900})
        saved.add_init_script("Object.defineProperty(navigator, 'connection', { configurable: true, get: () => ({ saveData: true }) });")
        saved.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        saved.wait_for_function("window.TW2KMedia && TW2KMedia.preloadState().done === true", timeout=20_000)
        assert saved.evaluate("TW2KMedia.preloadState()")["skipped"] == "saveData"
        assert saved.evaluate("TW2KMedia.preloadState()")["bytes"] == 0
        saved.close()

        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        quiet = ctx.new_page()
        quiet.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        quiet.wait_for_function("window.TW2KMedia && TW2KMedia.preloadState().done === true", timeout=20_000)
        assert quiet.evaluate("TW2KMedia.preloadState()")["skipped"] == "reduce"
        ctx.close()

        def open_cu(query: str):
            p = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
            p.goto(f"{host.base}/bot?seat=P2&mode=cu{query}&token={TOK}")
            p.wait_for_selector("#cuTurn.turn", timeout=20_000)
            return p

        stills = open_cu("")
        stills.wait_for_function("window.TW2KMedia && TW2KMedia.preloadState().done === true", timeout=20_000)
        assert stills.evaluate("TW2KViewport.state()") == {"mode": "stills", "animating": False, "cu": True}
        assert stills.evaluate("TW2KMedia.preloadState().skipped") == "cu"
        assert stills.evaluate("document.querySelectorAll('video').length") == 0
        outside = [tid for tid in DECISION_FIELDS
                   if not stills.get_by_test_id(tid).is_visible() or not inside(stills.get_by_test_id(tid).bounding_box())]
        assert not outside, outside
        assert stills.evaluate("document.scrollingElement.scrollHeight") <= VIEW_H
        stills.evaluate("TW2KMedia.ensureHud()")
        style = stills.evaluate("""() => {
            const inner = document.querySelector('#cuMediaSlot .media-hud-inner');
            const cs = getComputedStyle(inner);
            return { opacity: cs.opacity, transition: cs.transitionDuration, animation: cs.animationName,
                     parent: inner.closest('#cuMediaSlot') ? 'slot' : '' };
        }""")
        assert style["parent"] == "slot"
        assert style["opacity"] == "1" and style["animation"] == "none"
        assert style["transition"] in ("0s", "")
        h_stills = stills.evaluate("document.getElementById('cuMediaSlot').getBoundingClientRect().height")
        stills.close()

        off = open_cu("&viewport=off")
        box = off.evaluate("""() => {
            const s = document.getElementById('cuMediaSlot');
            return { h: s.getBoundingClientRect().height, vis: getComputedStyle(s).visibility,
                     off: s.classList.contains('is-off'), mode: TW2KViewport.state().mode };
        }""")
        assert box["mode"] == "off" and box["off"] is True and box["vis"] == "hidden"
        assert box["h"] > 0 and abs(box["h"] - h_stills) <= 2, (box["h"], h_stills)
        off.wait_for_function("window.TW2KMedia && TW2KMedia.ready()", timeout=10_000)
        assert off.evaluate("document.querySelectorAll('video').length") == 0
        quiet = off.evaluate("""() => {
            TW2KMedia._prime({ lastSeq: 0, visit_sector: 19, docked_in_visit: false });
            const obs = { self_id: 'P2', sector: { id: 19 } };
            TW2KMedia.onEvents([{ seq: 3, kind: 'combat', actor_id: 'P3', sector_id: 19, summary: 'fight',
              facts: { attacker: 'P3', defender: 'P9' } }], obs);
            const hud = document.getElementById('mediaHud');
            return { hidden: !hud || hud.hidden === true, played: TW2KMedia._state().playedKeys };
        }""")
        assert quiet["hidden"] is True
        assert "combat.witnessed" not in quiet["played"], quiet
        off.close()

        live = open_cu("&viewport=live")
        assert live.evaluate("TW2KViewport.state().mode") == "live"
        assert live.evaluate("document.querySelectorAll('video').length") == 0
        live.close()

        def samples(query: str) -> list[float]:
            p = open_cu(query)
            out = []
            for _ in range(10):
                p.wait_for_selector("#cuTurn.turn", timeout=20_000)
                sample = p.evaluate("""async () => {
                    const toast = document.querySelector('#cuToast');
                    const btn = document.querySelector('[data-testid=action-scan]');
                    const t0 = performance.now();
                    btn.click();
                    const deadline = t0 + 8000;
                    while (performance.now() < deadline) {
                        const text = toast.textContent || "";
                        const cls = toast.className || "";
                        if (cls.indexOf("busy") === -1 && text.indexOf("SUBMITTING") === -1
                            && (cls.indexOf("good") !== -1 || cls.indexOf("bad") !== -1)) {
                            return { ms: performance.now() - t0, text, cls,
                                     ok: cls.indexOf("good") !== -1 && text.indexOf("SCAN") !== -1 };
                        }
                        await new Promise((r) => setTimeout(r, 5));
                    }
                    return { ms: -1, text: toast.textContent, cls: toast.className, ok: false, disabled: btn.disabled };
                }""")
                assert sample["ok"], sample
                out.append(sample["ms"])
            p.close()
            return out

        off_ms = samples("&viewport=off")
        still_ms = samples("")
        off_med, still_med = statistics.median(off_ms), statistics.median(still_ms)
        print(f"[v4 cu timing] scan->toast median: off {off_med:.0f} ms, stills {still_med:.0f} ms ({(still_med / off_med - 1) * 100:+.1f}%)")
        assert still_med <= off_med * 1.05 + 25, (off_med, still_med)


def _approved_webm(key: str) -> str:
    manifest = json.loads((ROOT / "web" / "media" / "manifest.json").read_text(encoding="utf-8"))
    for variant in manifest["clips"][key]["variants"]:
        who = (variant.get("provenance") or {}).get("approved_by")
        webm = variant.get("webm") or ""
        if isinstance(who, str) and who.strip() and webm:
            return webm
    raise AssertionError(key)


def _clip_transfers(page) -> list[dict]:
    return page.evaluate("""() => performance.getEntriesByType('resource')
        .filter((e) => /\\/clips\\/.+\\.(webm|mp4)(?:\\?|$)/.test(e.name))
        .map((e) => ({ name: e.name, transfer: e.transferSize, encoded: e.encodedBodySize }))""")


def _round_trip_ms(page) -> float:
    page.wait_for_selector("#turnBanner.turn", timeout=20_000)
    return page.evaluate("""async () => {
        const last = document.querySelector('#lastResult');
        const before = last.textContent;
        const t0 = performance.now();
        document.querySelector('[data-testid=action-scan]').click();
        const deadline = t0 + 8000;
        while (performance.now() < deadline && last.textContent === before) {
            await new Promise((r) => setTimeout(r, 5));
        }
        if (last.textContent === before) return -1;
        return performance.now() - t0;
    }""")


def test_hashed_clips_cache_preload_cap_and_live_timing(browser, tmp_path: Path, monkeypatch) -> None:
    """Second load plays hashed clips from cache. Preload stops at a tiny cap.

    A 4x CPU throttle still meets the 4 ms resolve budget, and 10 scans with
    the viewport live stay within 5% of viewport off.
    """
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    dock = _approved_webm("dock.port")
    assert media_cache_control("media/" + dock) == IMMUTABLE
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&viewport=live&token={TOK}")
        page.wait_for_function("window.TW2KMedia && TW2KMedia.preloadState().done === true", timeout=20_000)
        pre = page.evaluate("TW2KMedia.preloadState()")
        assert pre["skipped"] == "" and pre["capped"] is False
        assert 0 < pre["clipBytes"] <= 3_500_000, pre
        assert pre["bytes"] <= 12 * 1024 * 1024
        assert pre["beforeInteractive"] <= 150 * 1024
        assert page.evaluate("document.querySelectorAll('#viewport video').length") <= 2
        header = page.evaluate(
            """async (path) => (await fetch('/static/media/' + path)).headers.get('cache-control')""",
            dock,
        )
        assert header == IMMUTABLE, header
        page.evaluate("""() => {
            TW2KMedia._prime({ lastSeq: 0, visit_sector: 19, docked_in_visit: false });
            TW2KMedia.onEvents([{
                seq: 1, kind: 'trade', actor_id: 'P2', sector_id: 19, summary: 'trade',
                facts: { commodity: 'fuel_ore', qty: 1, side: 'buy' }
            }], { self_id: 'P2', sector: { id: 19 } });
        }""")
        page.wait_for_function("""() => {
            const video = document.querySelector('#vpClip video');
            const src = video && video.querySelector('source') ? video.querySelector('source').src : '';
            return video && !video.hidden && video.currentTime > 0 && src.includes('.webm');
        }""", timeout=8_000)
        page.wait_for_function(
            """() => performance.getEntriesByType('resource')
                .some((e) => /\\/clips\\/.+\\.webm(?:\\?|$)/.test(e.name) && e.transferSize > 0)""",
            timeout=8_000,
        )
        first = _clip_transfers(page)
        assert any(row["transfer"] > 0 and row["encoded"] > 0 for row in first), first
        page.reload()
        page.wait_for_function("window.TW2KMedia && TW2KMedia.preloadState().done === true", timeout=20_000)
        page.evaluate("""() => {
            TW2KMedia._prime({ lastSeq: 0, visit_sector: 19, docked_in_visit: false });
            TW2KMedia.onEvents([{
                seq: 1, kind: 'trade', actor_id: 'P2', sector_id: 19, summary: 'trade',
                facts: { commodity: 'fuel_ore', qty: 1, side: 'buy' }
            }], { self_id: 'P2', sector: { id: 19 } });
        }""")
        page.wait_for_function("""() => {
            const video = document.querySelector('#vpClip video');
            const src = video && video.querySelector('source') ? video.querySelector('source').src : '';
            return video && !video.hidden && video.currentTime > 0 && src.includes('.webm');
        }""", timeout=8_000)
        page.wait_for_function(
            """() => {
                const rows = performance.getEntriesByType('resource')
                    .filter((e) => /\\/clips\\/.+\\.(webm|mp4)(?:\\?|$)/.test(e.name));
                return rows.length > 0 && rows.every((e) => e.transferSize === 0 && e.encodedBodySize > 0);
            }""",
            timeout=8_000,
        )
        second = _clip_transfers(page)
        assert second and all(row["transfer"] == 0 and row["encoded"] > 0 for row in second), second
        client = page.context.new_cdp_session(page)
        client.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        bench = page.evaluate("TW2KMedia.benchSwap(40)")
        client.send("Emulation.setCPUThrottlingRate", {"rate": 1})
        print(f"[v4 throttle] resolve+swap p95 {bench['p95']:.2f} ms")
        assert bench["n"] == 40 and bench["p95"] <= 4.0, bench
        page.close()

        results: dict[str, list[float]] = {}
        for mode in ("off", "live", "off", "live"):
            p = browser.new_page(viewport={"width": 1440, "height": 900})
            p.goto(f"{host.base}/bot?seat=P2&viewport={mode}&token={TOK}")
            assert p.evaluate("TW2KViewport.state().mode") == mode
            if mode == "live":
                p.wait_for_function("window.TW2KMedia && TW2KMedia.ready()", timeout=20_000)
                p.evaluate("""() => {
                    TW2KMedia._prime({ lastSeq: 0, visit_sector: 19, docked_in_visit: false });
                    TW2KMedia.onEvents([{
                        seq: 1, kind: 'warp', actor_id: 'P2', sector_id: 19, summary: 'warp',
                        facts: { from: 18, to: 19 }
                    }], { self_id: 'P2', sector: { id: 19 } });
                }""")
            samples = [_round_trip_ms(p) for _ in range(5)]
            assert all(ms >= 0 for ms in samples), samples
            results.setdefault(mode, []).extend(samples)
            p.close()
        off_med, live_med = statistics.median(results["off"]), statistics.median(results["live"])
        print(f"[v4 live timing] scan->result median: off {off_med:.0f} ms, live {live_med:.0f} ms")
        assert len(results["off"]) == len(results["live"]) == 10
        assert live_med <= off_med * 1.05 + 25, (off_med, live_med)

        capped = browser.new_page(viewport={"width": 1440, "height": 900})
        capped.add_init_script("window.__TW2K_PRELOAD_CAP = 1024;")
        capped.goto(f"{host.base}/bot?seat=P2&viewport=live&token={TOK}")
        capped.wait_for_function("window.TW2KMedia && TW2KMedia.preloadState().done === true", timeout=20_000)
        small = capped.evaluate("TW2KMedia.preloadState()")
        assert small["capped"] is True, small
        assert small["bytes"] <= 1024 and small["clipBytes"] == 0, small
        capped.close()
