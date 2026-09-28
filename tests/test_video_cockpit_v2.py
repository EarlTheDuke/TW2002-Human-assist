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
        "const stale=c.consider([], 9000);"
        "const d=R.createSession(manifest);"
        "d.consider([seen], 0); d.finish(1000);"
        "const cooled=d.consider([{...seen, seq:5}], 2000);"
        "const e=R.createSession(manifest);"
        "const hidden=e.consider([warp], 0, {hidden:true, maxSeq:9});"
        "const held=R.createSession(manifest);"
        "held.consider([{clip_key:'dock.port', priority:2, seq:1, sector_id:19}], 0);"
        "const replay=held.consider([], 50);"
        "held.stop();"
        "const stopped=held.consider([], 60);"
        "const promo=R.createSession(manifest);"
        "promo.consider([{clip_key:'warp.out', priority:2, seq:1, sector_id:11}], 0);"
        "promo.consider([{clip_key:'dock.port', priority:2, seq:2, sector_id:19}], 10);"
        "const promoted=promo.finish(100);"
        "const moved=R.createSession(manifest);"
        "moved.consider([{clip_key:'warp.out', priority:2, seq:1, sector_id:4}], 0);"
        "moved.consider([{clip_key:'dock.port', priority:2, seq:2, sector_id:8}], 10);"
        "const dropped=moved.consider([], 20, {postedSeq:9});"
        "const quiet=R.createSession(manifest);"
        "quiet.consider([{clip_key:'combat.witnessed', priority:3, seq:1}], 0, {recordCooldown:false});"
        "quiet.stop();"
        "const replayed=quiet.consider([{clip_key:'combat.witnessed', priority:3, seq:2}], 100);"
        "process.stdout.write(JSON.stringify({playDock, preempt, wait, stale, cooled, hidden, hiddenSeq:e.state().lastSeq, replay, stopped, promoted, dropped, replayed}));"
    )
    assert got["playDock"]["playing"] == "dock.port"
    assert got["preempt"]["playing"] == "combat.incoming" and got["preempt"]["preempted"] is True
    assert got["preempt"]["waiting"] is None
    assert got["wait"]["playing"] == "warp.out" and got["wait"]["waiting"] == "dock.port"
    assert got["stale"]["waiting"] is None and got["stale"]["playing"] == "warp.out"
    assert got["cooled"]["playing"] is None
    assert got["hidden"]["playing"] is None and got["hiddenSeq"] == 9
    assert got["playDock"]["started"] is True
    assert got["replay"]["started"] is False and got["replay"]["playing"] == "dock.port"
    assert got["stopped"]["playing"] is None and got["stopped"]["started"] is False
    assert got["promoted"]["clip_key"] == "dock.port" and got["promoted"]["sector_id"] == 19
    assert got["dropped"]["waiting"] is None
    assert got["replayed"]["started"] is True and got["replayed"]["playing"] == "combat.witnessed"


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_death_then_pod_is_not_replaced_by_a_lower_priority() -> None:
    script = (
        f"const R = require({json.dumps(str(ROOT / 'web' / 'media-resolver.js'))});"
        "const s = R.createSession({defaults:{stale_ms:8000}, clips:{"
        "'self.ship_destroyed':{priority:0}, 'self.escape_pod':{priority:0},"
        "'dock.port':{priority:2}, 'combat.hit':{priority:1}}});"
        "const started = s.consider(["
        "{clip_key:'self.ship_destroyed', priority:0, seq:1},"
        "{clip_key:'self.escape_pod', priority:0, seq:1, chain:true}"
        "], 0);"
        "const dock = s.consider([{clip_key:'dock.port', priority:2, seq:2}], 100);"
        "const hit = s.consider([{clip_key:'combat.hit', priority:1, seq:3}], 200);"
        "const newer = s.consider([], 400, {postedSeq: 9});"
        "const next = s.finish(3000);"
        "process.stdout.write(JSON.stringify({started, dock, hit, newer, next: next && next.clip_key}));"
    )
    got = json.loads(subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True, timeout=30).stdout)
    assert got["started"]["playing"] == "self.ship_destroyed" and got["started"]["waiting"] == "self.escape_pod"
    assert got["dock"]["waiting"] == "self.escape_pod" and got["dock"]["playing"] == "self.ship_destroyed"
    assert got["hit"]["waiting"] == "self.escape_pod"
    assert got["newer"]["waiting"] == "self.escape_pod" and got["newer"]["playing"] == "self.ship_destroyed"
    assert got["next"] == "self.escape_pod"


@needs_node
def test_ferrengi_plays_incoming_then_death_then_the_pod() -> None:
    got = _node(
        "const R=require(process.argv[1]); const fs=require('fs'); const path=require('path');"
        "const manifest=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));"
        "const fx=JSON.parse(fs.readFileSync(path.join(process.argv[3], 'ferrengi_attack.json'),'utf8'));"
        "const state=Object.assign({}, fx.state_before);"
        "const items=R.resolve(fx.batch, fx.obs, state, manifest);"
        "const s=R.createSession(manifest);"
        "const started=s.consider(items, 0);"
        "const death=s.finish(1000);"
        "const pod=s.finish(5000);"
        "process.stdout.write(JSON.stringify({"
        "keys:items.map(x=>x.clip_key), startedPlaying:started.playing, startedWaiting:started.waiting,"
        "death:death&&death.clip_key, pod:pod&&pod.clip_key, left:s.state().waiting}));"
    )
    assert got["keys"] == ["combat.incoming", "self.ship_destroyed", "self.escape_pod"]
    assert got["startedPlaying"] == "combat.incoming" and got["startedWaiting"] == "self.ship_destroyed"
    assert got["death"] == "self.ship_destroyed"
    assert got["pod"] == "self.escape_pod"
    assert got["left"] is None


@needs_node
def test_at_stardock_reads_the_manifest_sector() -> None:
    from tw2k.engine import constants as K

    live = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert live["defaults"]["stardock_sector"] == K.STARDOCK_SECTOR
    got = _node(
        "const R=require(process.argv[1]);"
        "const manifest={defaults:{stardock_sector:7}, clips:{'dock.stardock':{priority:2}},"
        "triggers:[{kind:'warp', rule:'self && at_stardock', clip:'dock.stardock'}]};"
        "const warp=(sector)=>R.resolve([{seq:1, kind:'warp', actor_id:'P1', sector_id:sector, facts:{to:sector}}],"
        "{self_id:'P1', sector:{id:sector}}, {}, manifest).map(x=>x.clip_key);"
        "process.stdout.write(JSON.stringify({match:warp(7), other:warp(1)}));"
    )
    assert got["match"] == ["dock.stardock"]
    assert got["other"] == []


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


def test_designed_stills_have_their_own_counter() -> None:
    html = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")
    player = (ROOT / "web" / "media-player.js").read_text(encoding="utf-8")
    assert "poster-fallbacks 0  stills 0" in html
    assert '"stills"' in player
    assert 'bump("stills")' in player
    assert 'bump("poster-fallbacks")' in player


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
        assert page.locator("[data-testid=media-hud]").is_hidden()
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
        page.close()


def _prime_trade(page, trade: dict) -> None:
    page.evaluate("""(fx) => {
        TW2KMedia._prime({ lastSeq: 0, visit_sector: fx.state_before.visit_sector, docked_in_visit: fx.state_before.docked_in_visit });
        TW2KMedia.onEvents(fx.batch, fx.obs);
    }""", trade)


def _scan_after(page, trade: dict) -> None:
    page.evaluate("""(fx) => {
        TW2KMedia.onEvents([{
            seq: 900000, day: 1, tick: 9, kind: "scan", actor_id: fx.obs.self_id,
            sector_id: fx.obs.sector.id, summary: "scan", facts: { tier: 1 }
        }], fx.obs);
    }""", trade)


def test_skip_and_cu_timer_do_not_replay_a_stale_dock(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    trade = json.loads((FIXTURES / "trade_burst.json").read_text(encoding="utf-8"))
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        _prime_trade(page, trade)
        page.wait_for_selector("[data-testid=viewport-clip]:not([hidden])", timeout=5_000)
        assert page.locator("[data-testid=viewport-caption]").inner_text() == "Docking at 19"
        page.get_by_test_id("viewport-skip").click()
        assert page.locator("[data-testid=viewport-clip]").is_hidden()
        _scan_after(page, trade)
        page.wait_for_timeout(400)
        assert "Docking" not in page.locator("[data-testid=viewport-caption]").inner_text()
        assert "trade_port" not in (page.locator("[data-testid=viewport-clip-still]").get_attribute("src") or "")
        assert page.locator("[data-testid=media-hud]").is_hidden()
        ctx.close()

        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK}")
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        _prime_trade(page, trade)
        page.wait_for_selector("[data-testid=media-hud]:not([hidden])", timeout=5_000)
        assert "docking" in page.locator("#mediaHudCaption").inner_text().casefold()
        assert "trade_port" in (page.locator("#mediaHudStill").get_attribute("src") or "")
        page.wait_for_timeout(3200)
        assert page.locator("[data-testid=media-hud]").is_hidden()
        _scan_after(page, trade)
        page.wait_for_timeout(300)
        hud = page.locator("[data-testid=media-hud]")
        if hud.is_visible():
            assert "docking" not in page.locator("#mediaHudCaption").inner_text().casefold()
            assert "trade_port" not in (page.locator("#mediaHudStill").get_attribute("src") or "")
        page.close()


def test_promoted_waiting_clip_keeps_its_sector(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        page.evaluate("""() => {
            TW2KMedia._prime({ lastSeq: 0, visit_sector: 4, docked_in_visit: false });
            TW2KMedia.onEvents([
                { seq: 1, day: 1, tick: 1, kind: "warp", actor_id: "P1", sector_id: 11,
                  summary: "warp", facts: { from: 4, to: 19 } },
                { seq: 2, day: 1, tick: 2, kind: "trade", actor_id: "P1", sector_id: 19,
                  summary: "trade", facts: { commodity: "fuel_ore", qty: 1, side: "buy" } }
            ], { self_id: "P1", sector: { id: 19 } });
        }""")
        page.wait_for_selector("[data-testid=viewport-clip]:not([hidden])", timeout=5_000)
        assert page.locator("[data-testid=viewport-caption]").inner_text() == "Warping out"
        page.wait_for_function(
            "() => document.querySelector('[data-testid=viewport-caption]').textContent === 'Docking at 19'",
            timeout=6_000,
        )
        page.close()


def test_live_stills_and_off_change_a_resolved_clip(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    trade = json.loads((FIXTURES / "trade_burst.json").read_text(encoding="utf-8"))
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)

        page.locator("[data-vp-mode=stills]").click()
        _prime_trade(page, trade)
        page.wait_for_selector("[data-testid=viewport-clip]:not([hidden])", timeout=5_000)
        anim = page.evaluate("() => getComputedStyle(document.querySelector('[data-testid=viewport-clip-still]')).animationName")
        assert anim == "none"
        assert page.evaluate("() => document.querySelectorAll('#vpClip video').length") == 0
        assert "trade_port" in (page.locator("[data-testid=viewport-clip-still]").get_attribute("src") or "")

        page.locator("[data-vp-mode=live]").click()
        _prime_trade(page, trade)
        page.wait_for_selector("[data-testid=viewport-clip].is-live", timeout=5_000)
        src = page.locator("#vpClip video source").first.get_attribute("src") or ""
        assert "dock_port_std_a" in src and src.endswith(".webm")
        assert page.locator("#vpClip video source").nth(1).get_attribute("type") == "video/mp4"

        page.locator("[data-vp-mode=off]").click()
        _prime_trade(page, trade)
        page.wait_for_timeout(300)
        assert page.locator("[data-testid=viewport-clip]").is_hidden()
        assert "Docking" not in page.locator("[data-testid=viewport-caption]").inner_text()
        assert page.locator("[data-testid=media-hud]").is_hidden()
        page.close()


def test_exchange_outcome_hit_miss_destroyed_and_ferrengi_path() -> None:
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.combat import _exchange_outcome, _resolve_ship_combat_attacker_npc
    from tw2k.engine.models import EventKind, FerrengiShip, Player, ShipClass

    hit = _exchange_outcome(
        [{"attacker_fighters_lost": 2, "defender_fighters_lost": 5}], attacker_f=10, defender_f=8,
    )
    assert hit == {"attacker_losses": 2, "defender_losses": 5, "outcome": "hit"}
    miss = _exchange_outcome(
        [{"attacker_fighters_lost": 1, "defender_fighters_lost": 0}], attacker_f=10, defender_f=8,
    )
    assert miss["outcome"] == "miss" and miss["defender_losses"] == 0
    destroyed = _exchange_outcome(
        [{"attacker_fighters_lost": 1, "defender_fighters_lost": 4}], attacker_f=10, defender_f=0,
    )
    assert destroyed["outcome"] == "destroyed"
    attacker_down = _exchange_outcome(
        [{"attacker_fighters_lost": 3, "defender_fighters_lost": 2}], attacker_f=0, defender_f=8,
    )
    assert attacker_down["outcome"] == "miss"
    both = _exchange_outcome(
        [{"attacker_fighters_lost": 1, "defender_fighters_lost": 1}], attacker_f=0, defender_f=0,
    )
    assert both["outcome"] == "destroyed"
    summed = _exchange_outcome(
        [
            {"attacker_fighters_lost": 1, "defender_fighters_lost": 2},
            {"attacker_fighters_lost": 3, "defender_fighters_lost": 4},
        ],
        attacker_f=9, defender_f=7,
    )
    assert summed == {"attacker_losses": 4, "defender_losses": 6, "outcome": "hit"}

    universe = generate_universe(GameConfig(seed=1, universe_size=40, max_days=2))
    player = Player(id="P1", name="Commander", agent_kind="external", sector_id=1, credits=1000, turns_per_day=40)
    player.ship.fighters = 500
    player.ship.shields = 100
    universe.players["P1"] = player
    universe.sectors[1].occupant_ids.append("P1")
    ferr = FerrengiShip(
        id="F1", name="Raider", sector_id=1, aggression=1, fighters=40, shields=0,
        ship_class=ShipClass.MERCHANT_CRUISER,
    )
    universe.ferrengi[ferr.id] = ferr
    _resolve_ship_combat_attacker_npc(universe, ferr, player)
    combat = next(ev for ev in reversed(universe.events) if ev.kind == EventKind.COMBAT)
    payload = combat.payload
    expect = _exchange_outcome(payload["rounds"], payload["attacker_f"], payload["defender_f"])
    assert payload["exchange_kind"] == "ferrengi_vs_ship"
    assert payload["outcome"] == expect["outcome"]
    assert payload["attacker_losses"] == expect["attacker_losses"]
    assert payload["defender_losses"] == expect["defender_losses"]


def test_hail_plays_in_the_hud_not_the_viewport(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK, turns_per_day=500) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&viewport=live&token={TOK}")
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        page.evaluate("""() => {
            TW2KMedia._prime({ lastSeq: 0, visit_sector: 19, docked_in_visit: false });
            TW2KMedia.onEvents([{
                seq: 1, kind: "hail", actor_id: "P2", sector_id: 19, summary: "hail",
                facts: { target: "P3", message: "hold fire" }
            }], { self_id: "P2", sector: { id: 19 } });
        }""")
        page.wait_for_function("""() => {
            const hud = document.getElementById("mediaHud");
            const clip = document.getElementById("vpClip");
            const still = document.getElementById("mediaHudStill");
            return hud && hud.hidden === false && (!clip || clip.hidden) && still && still.src.includes("comms_hail");
        }""", timeout=5_000)
        page.close()
