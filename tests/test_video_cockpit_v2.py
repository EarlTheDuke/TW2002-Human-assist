"""Video cockpit V2 — event-to-clip resolver, placeholder stills, combat outcome.

Resolver (Node) must match every V0 fixture row. The queue covers preemption,
equal-priority wait, stale drop, cooldown, and tab-hidden. Playwright checks the
placeholder still in the viewport, reduced motion, and that mode=cu stays a still
with no viewport video. Click-to-result timing stays in test_video_cockpit_v1.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tests._cu_host import CuHost

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "web" / "media-resolver.js"
MANIFEST = ROOT / "web" / "media" / "manifest.json"
FIXTURES = ROOT / "tests" / "fixtures" / "media_events"
NODE = shutil.which("node")
TOK = "v2-viewport-token-p2-00000000000"

needs_node = pytest.mark.skipif(NODE is None, reason="node not installed")


def _node(script: str) -> object:
    out = subprocess.run([NODE, "-e", script, str(RESOLVER), str(MANIFEST), str(FIXTURES)],
                         capture_output=True, text=True, encoding="utf-8", check=True, timeout=30)
    return json.loads(out.stdout)


@needs_node
def test_resolver_matches_every_v0_fixture() -> None:
    got = _node(
        "const R=require(process.argv[1]); const fs=require('fs'); const path=require('path');"
        "const manifest=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));"
        "const out={};"
        "for (const name of fs.readdirSync(process.argv[3]).filter(f=>f.endsWith('.json'))) {"
        "  const fx=JSON.parse(fs.readFileSync(path.join(process.argv[3], name),'utf8'));"
        "  const state=Object.assign({}, fx.state_before);"
        "  out[fx.name]=R.resolve(fx.batch, fx.obs, state, manifest).map(x=>({clip_key:x.clip_key, priority:x.priority}));"
        "}"
        "process.stdout.write(JSON.stringify(out));"
    )
    for path in sorted(FIXTURES.glob("*.json")):
        fx = json.loads(path.read_text(encoding="utf-8"))
        assert got[fx["name"]] == fx["expected"], fx["name"]


@needs_node
def test_queue_preempts_waits_drops_stale_and_respects_cooldown_and_hidden() -> None:
    got = _node(
        "const R=require(process.argv[1]); const fs=require('fs');"
        "const manifest=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));"
        "const dock={clip_key:'dock.port', priority:2, seq:1};"
        "const warp={clip_key:'warp.out', priority:2, seq:2};"
        "const incoming={clip_key:'combat.incoming', priority:0, seq:3};"
        "const seen={clip_key:'combat.witnessed', priority:3, seq:4};"
        "const a=R.createSession(manifest);"
        "const playDock=a.consider([dock], 0);"
        "const preempt=a.consider([incoming], 100);"
        "const b=R.createSession(manifest);"
        "b.consider([warp], 0);"
        "const wait=b.consider([dock], 50);"
        "const c=R.createSession(manifest);"
        "c.consider([warp], 0); c.consider([dock], 10);"
        "const stale=c.consider([], 5000);"
        "const d=R.createSession(manifest);"
        "d.consider([seen], 0); d.finish(1000);"
        "const cooled=d.consider([{...seen, seq:5}], 2000);"
        "const e=R.createSession(manifest);"
        "const hidden=e.consider([warp], 0, {hidden:true, maxSeq:9});"
        "process.stdout.write(JSON.stringify({playDock, preempt, wait, stale, cooled, hidden, hiddenSeq:e.state().lastSeq}));"
    )
    assert got["playDock"]["playing"] == "dock.port"
    assert got["preempt"]["playing"] == "combat.incoming" and got["preempt"]["preempted"] is True
    assert got["preempt"]["waiting"] is None
    assert got["wait"]["playing"] == "warp.out" and got["wait"]["waiting"] == "dock.port"
    assert got["stale"]["waiting"] is None and got["stale"]["playing"] == "warp.out"
    assert got["cooled"]["playing"] is None
    assert got["hidden"]["playing"] is None and got["hiddenSeq"] == 9


def test_ship_combat_outcome_and_own_death_are_in_the_fixtures() -> None:
    lose = json.loads((FIXTURES / "self_attack_lose.json").read_text(encoding="utf-8"))
    win = json.loads((FIXTURES / "self_attack_win.json").read_text(encoding="utf-8"))
    ferr = json.loads((FIXTURES / "ferrengi_attack.json").read_text(encoding="utf-8"))
    lose_c = next(r for r in lose["batch"] if r["kind"] == "combat")["facts"]
    win_c = next(r for r in win["batch"] if r["kind"] == "combat")["facts"]
    assert lose_c["outcome"] == "miss" and win_c["outcome"] == "destroyed"
    assert {"attacker_losses", "defender_losses", "outcome"} <= set(lose_c) <= set(win_c) | set(lose_c)
    for fx in (lose, ferr):
        assert fx["obs"]["sector"]["id"] == 1
        assert any(r["kind"] == "ship_destroyed" and r["facts"].get("victim") == "P1" for r in fx["batch"])


def test_placeholder_manifest_points_at_existing_stills() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["version"] == 2
    stills = {
        "dock.port": "stills/trade_port.png",
        "warp.out": "stills/move_warp.png",
        "combat.hit": "stills/combat_photon.png",
        "combat.miss": "stills/combat_alert.png",
        "combat.incoming": "stills/combat_alert.png",
        "combat.witnessed": "stills/combat_alert.png",
    }
    for key, still in stills.items():
        clip = m["clips"][key]
        assert clip["fallback_still"] == still or clip["variants"][0]["poster"] == still
        assert (ROOT / "web" / "media" / clip["variants"][0]["poster"]).is_file()
    js = (ROOT / "web" / "media-player.js").read_text(encoding="utf-8")
    assert "onEvents" in js and "playEntry" in js and "skipClip" in js
    assert "vp-video-a" in js and "vp-video-b" in js


def test_browser_placeholder_clip_reduced_motion_and_cu(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    trade = json.loads((FIXTURES / "trade_burst.json").read_text(encoding="utf-8"))
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        page.evaluate("""(fx) => {
            TW2KMedia._prime({ lastSeq: 0, visit_sector: fx.state_before.visit_sector, docked_in_visit: fx.state_before.docked_in_visit });
            TW2KMedia.onEvents(fx.batch, fx.obs);
        }""", trade)
        page.wait_for_selector("[data-testid=viewport-clip]:not([hidden])", timeout=5_000)
        assert "trade_port" in page.locator("[data-testid=viewport-clip-still]").get_attribute("src")
        assert page.locator("[data-testid=viewport-caption]").inner_text().startswith("Docking")
        page.get_by_test_id("viewport-skip").click()
        assert page.locator("[data-testid=viewport-clip]").is_hidden()
        ctx.close()

        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        page = ctx.new_page()
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        page.evaluate("""(fx) => {
            TW2KMedia._prime({ lastSeq: 0, visit_sector: fx.state_before.visit_sector, docked_in_visit: fx.state_before.docked_in_visit });
            TW2KMedia.onEvents(fx.batch, fx.obs);
        }""", trade)
        page.wait_for_selector("[data-testid=viewport-clip]:not([hidden])", timeout=5_000)
        anim = page.evaluate("""() => {
            const img = document.querySelector('[data-testid=viewport-clip-still]');
            return getComputedStyle(img).animationName;
        }""")
        assert anim == "none"
        assert page.evaluate("document.querySelectorAll('#viewport video').length") == 0
        ctx.close()

        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK}")
        page.wait_for_selector("#cuTurn.turn", timeout=20_000)
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        page.evaluate("""(fx) => {
            TW2KMedia._prime({ lastSeq: 0, visit_sector: fx.state_before.visit_sector, docked_in_visit: fx.state_before.docked_in_visit });
            TW2KMedia.onEvents(fx.batch, fx.obs);
        }""", trade)
        page.wait_for_selector("[data-testid=media-hud]:not([hidden])", timeout=5_000)
        assert not page.get_by_test_id("viewport").is_visible()
        assert page.evaluate("document.querySelectorAll('#viewport video').length") == 0
        assert page.evaluate("document.scrollingElement.scrollHeight") <= 800
