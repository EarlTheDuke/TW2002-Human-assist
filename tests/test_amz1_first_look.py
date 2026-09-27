"""First look: history does not play, the HUD does not cover the ship or eat a click,
and the stage detail sits under the stage value.

Accept (default /bot, 1440x900, host >= 8033):
1. After the turn banner, the ship does not intersect a visible media HUD.
2. Events already in the log at connect leave playedKeys empty.
3. One click on SCAN performs the scan.
4. A trade after connect plays dock.port in the viewport and leaves last-result uncovered.
5. mode=cu still docks a still with no video and fits 1280x800. CU viewport=off
   does not play a scan into the hidden slot.
6. #sbStage and the stage detail are both visible, do not intersect, the detail
   stays inside its card, and that card does not cover Credits.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from tests._cu_host import CuHost

TOK = "amz1-first-look-token-p2-00000000"
TRADE = json.loads(
    (Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "media_events" / "trade_burst.json").read_text(encoding="utf-8")
)


def _api(base: str, method: str, path: str, body: dict | None = None, token: str = TOK) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        base + path, data=data, method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _overlaps(a: dict | None, b: dict | None) -> bool:
    if not a or not b or a["width"] <= 0 or b["width"] <= 0 or a["height"] <= 0 or b["height"] <= 0:
        return False
    return a["x"] < b["x"] + b["width"] and a["x"] + a["width"] > b["x"] and a["y"] < b["y"] + b["height"] and a["y"] + a["height"] > b["y"]


def _inside(inner: dict, outer: dict) -> bool:
    return (inner["x"] >= outer["x"] - 1 and inner["y"] >= outer["y"] - 1
            and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + 1
            and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + 1)


def test_history_does_not_cover_the_ship_and_a_later_trade_still_plays(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        deadline = time.time() + 20
        status = {}
        while time.time() < deadline:
            status = _api(host.base, "GET", "/harness/v1/P2/status")
            if status.get("awaiting_input"):
                break
            time.sleep(0.1)
        assert status.get("awaiting_input"), status
        obs = _api(host.base, "GET", "/harness/v1/P2/observation?wait_s=0&peek=1")
        posted = _api(host.base, "POST", "/harness/v1/P2/action", {
            "turn_seq": obs["turn_seq"], "action": {"kind": "scan", "args": {}, "thought": "history"},
        })
        assert posted.get("accepted") is True, posted
        deadline = time.time() + 15
        prior = []
        while time.time() < deadline:
            prior = _api(host.base, "GET", "/harness/v1/P2/events?since=0&limit=50").get("events") or []
            if any(ev.get("kind") == "scan" for ev in prior):
                break
            time.sleep(0.1)
        assert any(ev.get("kind") == "scan" for ev in prior), prior

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_function("window.TW2KMedia && TW2KMedia.ready()", timeout=20_000)
        page.wait_for_function("() => (TW2KMedia._state().lastSeq || 0) > 0", timeout=10_000)
        quiet = page.evaluate("""() => {
            const hud = document.querySelector('[data-testid=media-hud]');
            const ship = document.querySelector('[data-testid=ship]');
            const vis = (el) => !!(el && !el.hidden && el.getClientRects().length);
            return { played: TW2KMedia._state().playedKeys, hud: vis(hud), ship: vis(ship),
                     shipBox: ship ? ship.getBoundingClientRect().toJSON() : null,
                     hudBox: vis(hud) ? hud.getBoundingClientRect().toJSON() : null };
        }""")
        assert quiet["played"] == [], quiet
        assert quiet["ship"] is True
        assert not _overlaps(quiet["shipBox"], quiet["hudBox"]), quiet

        overlap = page.evaluate("""async () => {
            const btn = document.querySelector('[data-testid=action-scan]');
            btn.click();
            const deadline = performance.now() + 3000;
            let hit = false;
            while (performance.now() < deadline) {
                const ship = document.querySelector('[data-testid=ship]');
                const hud = document.querySelector('[data-testid=media-hud]');
                const card = document.querySelector('.media-hud-inner');
                const vis = hud && !hud.hidden && hud.classList.contains('show') && card;
                if (vis && ship) {
                    const a = ship.getBoundingClientRect();
                    const b = card.getBoundingClientRect();
                    if (a.width > 0 && b.width > 0 && a.x < b.right && a.right > b.x && a.y < b.bottom && a.bottom > b.y) hit = true;
                }
                await new Promise((r) => setTimeout(r, 40));
            }
            return hit;
        }""")
        assert overlap is False
        page.wait_for_function(
            "() => { const t = document.querySelector('#lastResult').textContent || ''; return t.indexOf('SCAN') !== -1 && t.indexOf('ok') !== -1; }",
            timeout=15_000,
        )

        page.get_by_test_id("action-sell").click()
        page.locator("[data-testid=trade-qty]").fill("1")
        page.get_by_test_id("verb-submit").click()
        page.wait_for_selector("[data-testid=viewport-clip]:not([hidden])", timeout=8_000)
        assert "trade_port" in (page.locator("[data-testid=viewport-clip-still]").get_attribute("src") or "")
        dock = page.evaluate("""() => {
            const last = document.querySelector('#lastResult');
            const hud = document.querySelector('[data-testid=media-hud]');
            const vis = (el) => !!(el && !el.hidden && el.getClientRects().length);
            return { last: vis(last), lastBox: last.getBoundingClientRect().toJSON(),
                     hud: vis(hud), hudBox: vis(hud) ? hud.getBoundingClientRect().toJSON() : null,
                     played: TW2KMedia._state().playedKeys };
        }""")
        assert "dock.port" in dock["played"], dock
        assert dock["last"] is True
        assert not _overlaps(dock["lastBox"], dock["hudBox"]), dock

        stage = page.evaluate("""() => {
            const name = document.getElementById('sbStage');
            const detail = document.querySelector('[data-testid=stage-hint-detail]');
            const card = document.querySelector('[data-testid=stage-hint]');
            const credits = document.querySelector('[data-testid=credits]');
            const box = (el) => el.getBoundingClientRect().toJSON();
            return { name: name.textContent, detail: detail.textContent,
                     nameBox: box(name), detailBox: box(detail), cardBox: box(card),
                     creditsBox: credits.getBoundingClientRect().toJSON() };
        }""")
        assert stage["detail"].strip(), stage
        assert stage["nameBox"]["height"] > 0 and stage["detailBox"]["height"] > 0
        assert not _overlaps(stage["nameBox"], stage["detailBox"]), stage
        assert _inside(stage["detailBox"], stage["cardBox"]), stage
        assert not _overlaps(stage["cardBox"], stage["creditsBox"]), stage
        page.close()

        cu = browser.new_page(viewport={"width": 1280, "height": 800})
        cu.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK}")
        cu.wait_for_selector("#cuTurn.turn", timeout=20_000)
        cu.wait_for_function("window.TW2KMedia && TW2KMedia.ready()", timeout=20_000)
        cu.evaluate("""(fx) => {
            TW2KMedia._prime({ lastSeq: 0, visit_sector: fx.state_before.visit_sector, docked_in_visit: fx.state_before.docked_in_visit });
            TW2KMedia.onEvents(fx.batch, fx.obs);
        }""", TRADE)
        cu.wait_for_selector("#cuMediaSlot [data-testid=media-hud]:not([hidden])", timeout=5_000)
        assert cu.evaluate("document.querySelectorAll('video').length") == 0
        assert cu.evaluate("document.scrollingElement.scrollHeight") <= 800
        cu.close()

        off = browser.new_page(viewport={"width": 1280, "height": 800})
        off.goto(f"{host.base}/bot?seat=P2&mode=cu&viewport=off&token={TOK}")
        off.wait_for_function("window.TW2KMedia && TW2KMedia.ready()", timeout=20_000)
        quiet_off = off.evaluate("""() => {
            TW2KMedia._prime({ lastSeq: 0, visit_sector: 19, docked_in_visit: false });
            const obs = { self_id: 'P2', sector: { id: 19 } };
            TW2KMedia.onEvents([{ seq: 4, kind: 'scan', actor_id: 'P2', sector_id: 19, summary: 'scan', facts: {} }], obs);
            const hud = document.getElementById('mediaHud');
            return { hidden: !hud || hud.hidden === true, played: TW2KMedia._state().playedKeys };
        }""")
        assert quiet_off["hidden"] is True
        assert quiet_off["played"] == [], quiet_off
        off.close()


def _scans(host, n: int) -> None:
    for i in range(n):
        deadline = time.time() + 30
        status: dict = {}
        while time.time() < deadline:
            status = _api(host.base, "GET", "/harness/v1/P2/status", token=host.token)
            if status.get("awaiting_input"):
                break
            time.sleep(0.05)
        assert status.get("awaiting_input"), (i, status)
        obs = _api(host.base, "GET", "/harness/v1/P2/observation?wait_s=0&peek=1", token=host.token)
        posted = _api(host.base, "POST", "/harness/v1/P2/action", {
            "turn_seq": obs["turn_seq"], "action": {"kind": "scan", "args": {}, "thought": "backlog"},
        }, token=host.token)
        assert posted.get("accepted") is True, (i, posted)


def test_a_long_backlog_does_not_replay_on_connect(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK + "-b", turns_per_day=500) as host:
        _scans(host, 310)
        visible = _api(host.base, "GET", "/harness/v1/P2/events?since=0&limit=500", token=host.token).get("events") or []
        assert len(visible) >= 310, len(visible)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}-b")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_function(
            "() => { const t = document.getElementById('eventsMeta').textContent || ''; const n = parseInt(t, 10); return n >= 310; }",
            timeout=20_000,
        )
        quiet = page.evaluate("""() => {
            const hud = document.querySelector('[data-testid=media-hud]');
            const clip = document.querySelector('[data-testid=viewport-clip]');
            const vis = (el) => !!(el && !el.hidden && el.getClientRects().length);
            return { played: TW2KMedia._state().playedKeys, hud: vis(hud), clip: vis(clip),
                     n: parseInt(document.getElementById('eventsMeta').textContent, 10) };
        }""")
        assert quiet["n"] >= 310, quiet
        assert quiet["played"] == [], quiet
        assert quiet["hud"] is False and quiet["clip"] is False, quiet
        page.close()


def test_history_records_a_warp_before_the_manifest_is_loaded() -> None:
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        return
    root = Path(__file__).resolve().parents[1]
    script = (
        "const R=require(process.argv[1]);"
        "const st={visit_sector:null,docked_in_visit:false};"
        "R.resolve([{seq:1,kind:'warp',actor_id:'P2',sector_id:8,facts:{from:4,to:8}}],"
        "{self_id:'P2',sector:{id:4}}, st, null);"
        "if(st.visit_sector!==8) throw new Error(JSON.stringify(st));"
        "process.stdout.write('ok');"
    )
    out = subprocess.run([node, "-e", script, str(root / "web" / "media-resolver.js")],
                         capture_output=True, text=True, encoding="utf-8", check=True, timeout=20)
    assert out.stdout.strip() == "ok"
    js = (root / "web" / "media-player.js").read_text(encoding="utf-8")
    assert "pendingEvents" in js and "manifestFailed" in js and "length > 400" in js
    assert "R.resolve(fresh, state.obs || { self_id: null, sector: {} }, state, null)" in js
