"""Video cockpit V3 — stand-ins, approved real clips, budgets, three-browser playback.

The live manifest plays an approved take. A stand-in (approved_by null) stays first
so unapproving a take falls back without removing fallback_still.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests._cu_host import CuHost

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import media_clip_tools as tools  # noqa: E402
import media_validate_manifest as mv  # noqa: E402

MEDIA = ROOT / "web" / "media"
FIXTURES = ROOT / "tests" / "fixtures" / "media_events"
LIVE = json.loads((MEDIA / "manifest.json").read_text(encoding="utf-8-sig"))
CATALOG = json.loads((MEDIA / "clips" / "v3-pilot" / "clips_manifest_v3.json").read_text(encoding="utf-8"))
TOK = "v3-e2e-token-p2-00000000000000"
PLAY = """async (clips) => {
  const bad = [];
  for (const c of clips) {
    const v = document.createElement("video");
    v.muted = true;
    v.playsInline = true;
    const webm = document.createElement("source");
    webm.src = c.webm;
    webm.type = "video/webm";
    const mp4 = document.createElement("source");
    mp4.src = c.mp4;
    mp4.type = "video/mp4";
    v.append(webm, mp4);
    document.body.appendChild(v);
    const start = performance.now();
    const played = await Promise.race([
      v.play().then(() => "ok").catch((err) => String(err)),
      new Promise((resolve) => setTimeout(() => resolve("play-timeout"), 4000)),
    ]);
    while (v.currentTime <= 0 && performance.now() - start < 6000) {
      await new Promise((r) => setTimeout(r, 40));
    }
    if (!(v.currentTime > 0)) bad.push(c.id + " " + played);
    v.pause();
    v.remove();
  }
  return bad;
}"""


def _errors(data: dict, root: Path = MEDIA) -> list[str]:
    return mv.validate(data, root)[0]


def _trade() -> dict:
    return json.loads((FIXTURES / "trade_burst.json").read_text(encoding="utf-8"))


def _prime(page, trade: dict) -> None:
    page.evaluate("""(fx) => {
        TW2KMedia._prime({ lastSeq: 0, visit_sector: fx.state_before.visit_sector, docked_in_visit: fx.state_before.docked_in_visit });
        TW2KMedia.onEvents(fx.batch, fx.obs);
    }""", trade)


def _selected_ids() -> dict[str, str]:
    out = {}
    for key, amb in LIVE["ambient"].items():
        chosen = next(v for v in amb["variants"] if (v.get("provenance") or {}).get("approved_by"))
        out["ambient." + key] = chosen["id"]
    for key, clip in LIVE["clips"].items():
        approved = [v for v in clip["variants"] if (v.get("provenance") or {}).get("approved_by")]
        if not approved:
            continue
        out[key] = approved[0]["id"]
    return out


def test_live_manifest_plays_approved_reals_and_keeps_standins() -> None:
    assert _errors(LIVE) == []
    assert _selected_ids()["dock.port"] == "dock_port_std_a"
    dock = LIVE["clips"]["dock.port"]
    assert dock["fallback_still"] == "stills/trade_port.png"
    assert dock["variants"][0]["id"].startswith("ph_")
    assert dock["variants"][0]["provenance"]["approved_by"] is None
    assert dock["variants"][0]["provenance"]["tool"] == "placeholder-ffmpeg-from-still"
    baked = {v["id"] for v in dock["variants"] if v.get("baked_frame")}
    assert baked == {"dock_port_std_b", "dock_port_std_c"}
    warp = {v["id"] for v in LIVE["clips"]["warp.out"]["variants"] if v.get("baked_frame")}
    assert warp == {"warp_out_c"}
    standins = list((MEDIA / "clips" / "placeholder").glob("ph_*.webm"))
    assert len(standins) == 14
    assert len(CATALOG["clips"]) == 14


def test_unapproved_reals_stay_inside_the_standin_budget() -> None:
    data = copy.deepcopy(LIVE)
    for variant in tools.iter_variants(data):
        if not tools.is_standin(variant):
            tools.set_approval(variant, None)
    assert _errors(data) == []


def test_oversized_selected_set_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "clips").mkdir()
    clips = {}
    for i in range(6):
        name = f"big{i}.webm"
        (tmp_path / "clips" / name).write_bytes(b"\0" * 590_000)
        clips[f"warp.o{i}"] = {"priority": 2, "caption": "Warp", "variants": [{"id": f"v{i}", "webm": f"clips/{name}"}]}
    data = {"version": 2, "defaults": {"duration_ms": 2400, "muted": True}, "clips": clips,
            "triggers": [{"kind": "warp", "rule": "self", "clip": "warp.o0"}]}
    errs = _errors(data, tmp_path)
    assert any("one-browser budget" in e for e in errs), errs
    assert not any("600000" in e for e in errs)

    both = {}
    for i in range(7):
        (tmp_path / "clips" / f"w{i}.webm").write_bytes(b"\0" * 400_000)
        (tmp_path / "clips" / f"w{i}.mp4").write_bytes(b"\0" * 500_000)
        both[f"warp.b{i}"] = {"priority": 2, "caption": "Warp", "variants": [{
            "id": f"b{i}", "webm": f"clips/w{i}.webm", "mp4": f"clips/w{i}.mp4"}]}
    data["clips"] = both
    data["triggers"][0]["clip"] = "warp.b0"
    errs = _errors(data, tmp_path)
    assert any("all-formats budget" in e for e in errs), errs


def test_unknown_review_code_is_rejected() -> None:
    bad = copy.deepcopy(LIVE)
    bad["clips"]["warp.out"]["variants"][0]["review"] = {"codes": ["NOT_A_CODE"]}
    errs = _errors(bad)
    assert any("schema" in e or "unknown review code" in e for e in errs), errs


def test_swap_changes_the_file_and_approve_roundtrips(tmp_path: Path) -> None:
    media = tmp_path / "media"
    webm = tmp_path / "incoming.webm"
    webm.write_bytes(b"\0" * 1500)
    data = {"clips": {"warp.out": {"variants": [
        {"id": "ph_warp_out_a", "webm": "clips/placeholder/ph_warp_out_a.webm",
         "provenance": {"tool": tools.STANDIN_TOOL, "approved_by": None}},
        {"id": "warp_out_a", "webm": "clips/v3-pilot/warp_out_a.webm",
         "provenance": {"tool": "xai grok-imagine-video", "approved_by": "ben"}},
    ]}}}
    assert tools.find_variant(data["clips"]["warp.out"], "1")["id"] == "warp_out_a"
    with pytest.raises(SystemExit, match="refusing ph_warp_out_a"):
        tools.find_variant(data["clips"]["warp.out"], "ph_warp_out_a")
    swapped = tools.swap_variant(data, "warp.out", "warp_out_a", webm=webm, media_root=media)
    assert swapped["webm"] == "clips/swapped/warp_out_a.webm"
    assert swapped["bytes"] == 1500
    assert (media / swapped["webm"]).is_file()
    tools.set_approval(swapped, None)
    assert swapped["provenance"]["approved_by"] is None
    assert tools.approve_pending(data, "ben") == 0
    assert data["clips"]["warp.out"]["variants"][0]["provenance"]["approved_by"] is None


def test_approve_refuses_standins_and_keeps_the_catalog(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    catalog_path = tmp_path / "clips_manifest_v3.json"
    manifest_path.write_text(json.dumps(LIVE), encoding="utf-8")
    catalog_path.write_text(json.dumps(CATALOG), encoding="utf-8")
    script = ROOT / "scripts" / "media_approve_clips.py"

    def run(*extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), "--manifest", str(manifest_path), "--catalog", str(catalog_path), *extra],
            capture_output=True, text=True, timeout=60,
        )

    cleared = run("--all-pending", "--clear")
    assert cleared.returncode == 0, cleared.stderr
    again = run("--all-pending", "--by", "qc")
    assert again.returncode == 0 and "14" in again.stdout, again.stdout + again.stderr
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    approved = [v["id"] for v in tools.iter_variants(data)
                if isinstance((v.get("provenance") or {}).get("approved_by"), str)
                and (v.get("provenance") or {})["approved_by"].strip()]
    assert len(approved) == 14
    assert "combat_witnessed_placeholder" not in approved
    assert not any(vid.startswith("ph_") for vid in approved)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert all(row.get("approved_by") == "qc" for row in catalog["clips"])
    refused = run("--key", "dock.port", "--variant", "ph_dock_port_std_a")
    assert refused.returncode != 0
    assert "refusing ph_dock_port_std_a" in (refused.stderr + refused.stdout)
    for row in catalog["clips"]:
        if row["variant"] == "dock_port_std_a":
            row["approved_by"] = None
    wired = copy.deepcopy(data)
    tools.wire_pilot(wired, catalog["clips"], MEDIA)
    take = next(v for v in wired["clips"]["dock.port"]["variants"] if v["id"] == "dock_port_std_a")
    assert take["provenance"]["approved_by"] is None
    standin = next(v for v in wired["clips"]["dock.port"]["variants"] if v["id"] == "ph_dock_port_std_a")
    assert standin["provenance"]["approved_by"] is None


def test_fourteen_clips_play_in_chromium_firefox_and_webkit(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    clips = [{"id": row["variant"],
              "webm": f"/static/media/clips/v3-pilot/{row['webm']}",
              "mp4": f"/static/media/clips/v3-pilot/{row['mp4']}"} for row in CATALOG["clips"]]
    assert len(clips) == 14
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        for name in ("chromium", "firefox", "webkit"):
            if name == "chromium":
                browser = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
            elif name == "firefox":
                browser = p.firefox.launch(firefox_user_prefs={"media.autoplay.default": 0})
            else:
                browser = p.webkit.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
            page.wait_for_selector("#viewport", timeout=20_000)
            page.mouse.click(8, 8)
            bad = page.evaluate(PLAY, clips)
            assert bad == [], (name, bad)
            browser.close()


def test_approved_clip_plays_and_a_missing_file_falls_back(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    trade = _trade()
    baked = copy.deepcopy(LIVE)
    for variant in baked["clips"]["dock.port"]["variants"]:
        who = "ben" if variant["id"] == "dock_port_std_b" else None
        variant.setdefault("provenance", {})["approved_by"] = who
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        _prime(page, trade)
        page.wait_for_function("""() => {
            const s = document.querySelector("#vpClip video source");
            return s && s.src.includes("dock_port_std_a") && s.type === "video/webm";
        }""", timeout=5_000)
        assert "placeholder" not in (page.locator("#vpClip video source").first.get_attribute("src") or "")
        assert page.locator("#viewport").evaluate("el => el.classList.contains('is-baked-frame')") is False
        mp4 = page.locator("#vpClip video source").nth(1)
        assert mp4.get_attribute("type") == "video/mp4"
        page.close()

        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        page.route("**/manifest.json", lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps(baked)))
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        _prime(page, trade)
        page.wait_for_function("""() => {
            const s = document.querySelector("#vpClip video source");
            return s && s.src.includes("dock_port_std_b");
        }""", timeout=5_000)
        hidden = page.locator("[data-testid=viewport-frame]").evaluate("el => getComputedStyle(el).visibility")
        assert hidden == "hidden"
        page.get_by_test_id("viewport-skip").click()
        assert page.locator("#viewport").evaluate("el => el.classList.contains('is-baked-frame')") is False
        ctx.close()

        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)

        def _missing(route):
            route.fulfill(status=404, body="missing")

        page.route("**/*.webm", _missing)
        page.route("**/*.mp4", _missing)
        _prime(page, trade)
        page.wait_for_function("""() => {
            const raw = sessionStorage.getItem("tw2k.media.counters");
            return raw && (JSON.parse(raw)["poster-fallbacks"] || 0) > 0;
        }""", timeout=5_000)
        assert "trade_port" in (page.locator("[data-testid=viewport-clip-still]").get_attribute("src") or "")
        assert page.locator("#vpClip video").first.is_hidden()
        page.close()

        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
        page = ctx.new_page()
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        _prime(page, trade)
        page.wait_for_selector("[data-testid=viewport-clip]:not([hidden])", timeout=5_000)
        assert page.evaluate("document.querySelectorAll('#viewport video').length") == 0
        assert "trade_port" in (page.locator("[data-testid=viewport-clip-still]").get_attribute("src") or "")
        ctx.close()

        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK}")
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        _prime(page, trade)
        page.wait_for_selector("[data-testid=media-hud]:not([hidden])", timeout=5_000)
        assert page.evaluate("document.querySelectorAll('#viewport video').length") == 0
        assert "trade_port" in (page.locator("#mediaHudStill").get_attribute("src") or "")
        browser.close()


def test_three_missing_clips_each_fall_back(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    events = [
        ({"seq": 1, "kind": "trade", "actor_id": "P2", "sector_id": 19, "summary": "trade",
          "facts": {"commodity": "fuel_ore", "qty": 1, "side": "buy"}}, "trade_port"),
        ({"seq": 2, "kind": "warp", "actor_id": "P2", "sector_id": 19, "summary": "warp",
          "facts": {"from": 18, "to": 19}}, "move_warp"),
        ({"seq": 3, "kind": "combat", "actor_id": "P2", "sector_id": 19, "summary": "combat",
          "facts": {"attacker": "P2", "defender": "P3", "outcome": "hit"}}, "combat_photon"),
    ]
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        page.route("**/*.webm", lambda route: route.fulfill(status=404, body="missing"))
        page.route("**/*.mp4", lambda route: route.fulfill(status=404, body="missing"))
        page.evaluate("""() => {
            sessionStorage.removeItem("tw2k.media.counters");
            TW2KMedia._prime({ lastSeq: 0, visit_sector: 19, docked_in_visit: false });
        }""")
        for n, (ev, still) in enumerate(events, start=1):
            page.evaluate("""(ev) => { TW2KMedia.onEvents([ev], { self_id: "P2", sector: { id: 19 } }); }""", ev)
            page.wait_for_function("""([n, still]) => {
                const raw = sessionStorage.getItem("tw2k.media.counters");
                const count = raw ? (JSON.parse(raw)["poster-fallbacks"] || 0) : 0;
                const video = document.querySelector("#vpClip video");
                const img = document.querySelector("[data-testid=viewport-clip-still]");
                return count === n && video && video.hidden && img && img.src.includes(still);
            }""", arg=[n, still], timeout=1_500)
            if n < len(events):
                page.get_by_test_id("viewport-skip").click()
        browser.close()


def test_a_failed_clip_does_not_hide_the_next_one(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    trade = _trade()
    with CuHost(tmp_path, TOK) as host, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_function("window.TW2KMedia && window.TW2KMedia.ready()", timeout=20_000)
        page.route("**/*dock_port*", lambda route: route.fulfill(status=404, body="missing"))
        page.evaluate("""() => { sessionStorage.removeItem("tw2k.media.counters"); }""")
        _prime(page, trade)
        page.evaluate("""(fx) => { TW2KMedia.onEvents(fx.batch, fx.obs); }""", trade)
        page.wait_for_function("""() => {
            const raw = sessionStorage.getItem("tw2k.media.counters");
            const count = raw ? (JSON.parse(raw)["poster-fallbacks"] || 0) : 0;
            const video = document.querySelector("#vpClip video");
            return count === 1 && video && video.hidden;
        }""", timeout=5_000)
        page.evaluate("""() => {
            TW2KMedia.onEvents([{
                seq: 90, kind: "combat", actor_id: "P1", sector_id: 19, summary: "combat",
                facts: { attacker: "P1", defender: "P2", outcome: "destroyed" }
            }], { self_id: "P1", sector: { id: 19 } });
        }""")
        page.wait_for_function("""() => {
            const video = document.querySelector("#vpClip video");
            const src = video && video.querySelector("source") ? video.querySelector("source").src : "";
            const raw = sessionStorage.getItem("tw2k.media.counters");
            const count = raw ? (JSON.parse(raw)["poster-fallbacks"] || 0) : 0;
            return video && !video.hidden && video.currentTime > 0 && src.includes("combat_hit") && count === 1;
        }""", timeout=5_000)
        page.get_by_test_id("viewport-skip").click()
        page.evaluate("""() => {
            TW2KMedia._prime({ lastSeq: 90, visit_sector: 19, docked_in_visit: false });
            TW2KMedia.onEvents([{
                seq: 91, kind: "trade", actor_id: "P1", sector_id: 19, summary: "trade",
                facts: { commodity: "fuel_ore", qty: 1, side: "buy" }
            }], { self_id: "P1", sector: { id: 19 } });
        }""")
        page.wait_for_function("""() => {
            const raw = sessionStorage.getItem("tw2k.media.counters");
            const count = raw ? (JSON.parse(raw)["poster-fallbacks"] || 0) : 0;
            const video = document.querySelector("#vpClip video");
            const img = document.querySelector("[data-testid=viewport-clip-still]");
            return count === 2 && video && video.hidden && img && img.src.includes("trade_port");
        }""", timeout=1_500)
        browser.close()


def test_catalog_defaults_beside_the_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(LIVE), encoding="utf-8")
    real = MEDIA / "clips" / "v3-pilot" / "clips_manifest_v3.json"
    before = real.read_bytes()
    script = ROOT / "scripts" / "media_approve_clips.py"

    def run(*extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), "--manifest", str(manifest_path), *extra],
            capture_output=True, text=True, timeout=60,
        )
    cleared = run("--all-pending", "--clear")
    assert cleared.returncode == 0, cleared.stderr
    assert real.read_bytes() == before
    local = tmp_path / "clips" / "v3-pilot" / "clips_manifest_v3.json"
    local.parent.mkdir(parents=True)
    local.write_text(json.dumps(CATALOG), encoding="utf-8")
    approved = run("--all-pending", "--by", "qc")
    assert approved.returncode == 0, approved.stderr
    assert real.read_bytes() == before
    saved = json.loads(local.read_text(encoding="utf-8"))
    assert all(row.get("approved_by") == "qc" and row.get("approved_at") for row in saved["clips"])
    wired = copy.deepcopy(LIVE)
    tools.wire_pilot(wired, saved["clips"], MEDIA)
    take = next(v for v in wired["clips"]["dock.port"]["variants"] if v["id"] == "dock_port_std_a")
    row = next(r for r in saved["clips"] if r["variant"] == "dock_port_std_a")
    assert take["provenance"]["approved_by"] == "qc"
    assert take["provenance"]["approved_at"] == row["approved_at"]
