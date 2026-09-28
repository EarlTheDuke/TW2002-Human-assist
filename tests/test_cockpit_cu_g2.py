"""Grokbot-player G2 - one-screen turn layout for computer use (/bot?mode=cu).

Done when (docs/plans/2026-09-26-grokbot-plays-by-screen.md, G2): a
Playwright smoke test screenshots at 1280x800 and asserts every decision
field is inside the viewport; the default /bot layout is unchanged.

The browser test needs `pip install playwright` + `python -m playwright
install chromium`; it skips cleanly when either is missing. It hosts its own
match on a free local port >= 8033 (never the live :8031 match).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests._cu_host import VIEW_H, VIEW_W, CuHost, inside
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.models import Player
from tw2k.engine.observation import build_observation

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")
JS = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "bot.css").read_text(encoding="utf-8")
PARITY_PATH = ROOT / "web" / "bot-parity.js"
NODE = shutil.which("node")
TOK = "g2-cu-token-p2-0000000000000000"

# Every decision field the G2 spec lists, by the testid that renders it.
DECISION_FIELDS = (
    "cu-turn",        # whose turn + deadline countdown
    "cu-credits", "cu-networth", "cu-status-line",   # G6: day / turns left / rank in one line
    "cu-ship",        # ship / cargo
    "cu-sector", "cu-warps", "cu-port",   # sector + warps + port prices
    "cu-map",         # known-space mini map
    "cu-goal",        # goal / stage hint
    "cu-events",      # last 5 events
    "cu-toast",       # last action result
    "cu-turn-card",   # plain-text summary
    "cu-shortcuts",   # keyboard legend
    "cu-actions",     # big action buttons
)


# ------------------------------------------------------------------ static contract (no browser)
def test_cu_mode_is_opt_in_and_scoped() -> None:
    assert 'id="cuScreen"' in HTML and 'data-testid="cu-screen" hidden' in HTML
    for tid in DECISION_FIELDS:
        assert f'data-testid="{tid}"' in HTML, tid
    assert 'get("mode") === "cu"' in JS and "if (CU) setupCu();" in JS
    # Every G2 CSS rule is scoped to mode-cu (or to cu-only classes), so the default page cannot change.
    block = CSS.split("/* ---- G2:")[1].split("/* ---- media HUD")[0]
    for line in block.splitlines():
        if "{" not in line or line.lstrip().startswith("/*"):
            continue
        for sel in line.split("{")[0].split(","):
            sel = sel.strip()
            assert "mode-cu" in sel or sel.startswith((".cu-", "#cu")), f"unscoped G2 rule: {sel}"
    # Keyboard legend and handler share one keymap.
    assert "P.CU_KEYS" in JS and "CU_KEYS" in PARITY_PATH.read_text(encoding="utf-8")


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_turn_card_summarises_decision_state() -> None:
    u = generate_universe(GameConfig(seed=31, universe_size=90, max_days=3, turns_per_day=200,
                                     starting_credits=100_000, enable_ferrengi=False, enable_planets=True))
    u.players["P1"] = Player(id="P1", name="Me", agent_kind="external", sector_id=1, credits=100_000)
    u.sectors[1].occupant_ids.append("P1")
    obs = build_observation(u, "P1").model_dump(mode="json")
    ctx = {"statusLine": "Day 1 of 3 - 200 turns left today - Rank 1 of 1", "turn": "YOUR TURN",
           "stage": {"stage": "S3", "label": "Establish a Home", "next_milestone": "Finish L1"},
           "last": "turn 3: SCAN - ok", "events": [{"day": 1, "tick": i, "summary": f"ev {i}"} for i in range(8)]}
    script = (f"const P = require({json.dumps(str(PARITY_PATH))});"
              "const d = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
              "process.stdout.write(JSON.stringify(P.turnCard(d.obs, d.ctx)));")
    card = json.loads(subprocess.run([NODE, "-e", script], input=json.dumps({"obs": obs, "ctx": ctx}), capture_output=True,
                                     text=True, encoding="utf-8", check=True, timeout=30).stdout)
    s = obs["sector"]
    assert card.splitlines()[:2] == ["Day 1 of 3 - 200 turns left today - Rank 1 of 1", "TURN   YOUR TURN"]
    assert f"{obs['credits']:,} cr" in card and f"net worth {obs['net_worth']:,}" in card
    assert f"sector {s['id']}" in card and all(f"] {w}" in card for w in s["warps_out"][:9])
    assert "S3 Establish a Home - next: Finish L1" in card and "LAST   turn 3: SCAN - ok" in card
    assert "ev 7" in card and "ev 2" not in card  # last five only


# ------------------------------------------------------------------ browser smoke (Playwright, 1280x800)
def test_cu_layout_fits_1280x800_and_keys_work(browser, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        requests: list[str] = []
        page.on("request", lambda r: requests.append(r.url.replace(host.base, "")))
        page.goto(f"{host.base}/bot?seat=P2&mode=cu&token={TOK}")
        page.wait_for_selector("#cuTurn.turn", timeout=20_000)
        page.wait_for_function("document.querySelector('#cuTurnCard').textContent.startsWith('Day ')", timeout=10_000)

        assert page.evaluate("document.body.classList.contains('mode-cu')")
        assert page.evaluate("document.scrollingElement.scrollHeight") <= VIEW_H, "page scrolls at 1280x800"
        outside = [tid for tid in DECISION_FIELDS
                   if not page.get_by_test_id(tid).is_visible() or not inside(page.get_by_test_id(tid).bounding_box())]
        shot = tmp_path / "cu-1280x800.png"
        page.screenshot(path=str(shot))
        if os.environ.get("TW2K_SHOT_DIR"):
            shutil.copy(shot, Path(os.environ["TW2K_SHOT_DIR"]) / shot.name)
        assert not outside, f"decision fields outside the 1280x800 viewport: {outside}"
        # The clip HUD docks into leftover space and never covers a decision field.
        covered = page.evaluate("""(ids) => {
            const h = document.getElementById('mediaHud');
            if (!h) return [];
            if (h.parentElement.id !== 'cuMediaSlot') return ['not docked'];
            if (h.hidden) return [];
            const r = h.getBoundingClientRect();
            return ids.filter((id) => {
              const e = document.querySelector(`[data-testid="${id}"]`).getBoundingClientRect();
              return !(r.right <= e.left || r.left >= e.right || r.bottom <= e.top || r.top >= e.bottom);
            });
        }""", [t for t in DECISION_FIELDS if t != "cu-actions"])
        assert not covered, covered

        # Keyboard: S scans, toast reports the engine result and stays.
        assert "YOUR TURN" in page.get_by_test_id("cu-turn").inner_text()
        page.keyboard.press("s")
        page.wait_for_function("/SCAN .*ok/.test(document.querySelector('#cuToast').textContent)", timeout=15_000)
        assert "good" in page.get_by_test_id("cu-toast").get_attribute("class")
        page.wait_for_selector("#cuTurn.turn", timeout=20_000)
        page.wait_for_timeout(300)

        # Content is the seat's own state (fresh observation after one action).
        u = host.runner.state.universe
        me = u.players["P2"]
        assert page.locator("#cuCredits").inner_text() == f"{me.credits:,}"
        warps = page.locator("#cuWarpSlot [data-testid^=warp-]")
        assert warps.count() == len(u.sectors[me.sector_id].warps) and warps.first.is_visible()
        assert f"sector {me.sector_id}" in page.locator("#cuTurnCard").inner_text()
        assert page.locator("#cuPortSlot [data-testid=port-row-fuel_ore]").is_visible(), "port prices on screen"

        # Every visible actionable control carries a testid and a visible text label.
        unlabeled = page.evaluate("""() => [...document.querySelectorAll('#cuScreen button')]
            .filter(b => b.offsetParent !== null)
            .filter(b => !b.getAttribute('data-testid') || !b.innerText.trim())
            .map(b => b.outerHTML.slice(0, 80))""")
        assert not unlabeled, unlabeled

        # H toggles hold-my-slot (G4) and says so; H again turns it off.
        page.keyboard.press("h")
        page.wait_for_function("document.querySelector('#cuToast').textContent.startsWith('HOLDING SLOT')", timeout=5_000)
        assert page.get_by_test_id("cu-hold").get_attribute("aria-pressed") == "true"
        page.keyboard.press("h")
        page.wait_for_function("document.querySelector('[data-testid=cu-hold]').getAttribute('aria-pressed') === 'false'", timeout=5_000)

        # X opens the quick SELL form; its CONFIRM stays on screen.
        page.keyboard.press("x")
        page.wait_for_selector("#cuFormSlot #verbForm[data-verb=trade]:not([hidden])", timeout=5_000)
        submit_btn = page.get_by_test_id("verb-submit")
        assert submit_btn.is_visible() and inside(submit_btn.bounding_box()), submit_btn.bounding_box()
        page.screenshot(path=str(tmp_path / "cu-sell-form.png"))
        if os.environ.get("TW2K_SHOT_DIR"):
            shutil.copy(tmp_path / "cu-sell-form.png", Path(os.environ["TW2K_SHOT_DIR"]) / "cu-sell-form.png")
        page.keyboard.press("Escape")
        page.wait_for_selector("#verbForm", state="hidden", timeout=5_000)

        # An unavailable verb explains why instead of silently doing nothing.
        page.keyboard.press("9")
        toast = page.get_by_test_id("cu-toast")
        assert "bad" in toast.get_attribute("class") and ("#9" in toast.inner_text() or "not available" in toast.inner_text())
        page.keyboard.press("p")
        page.wait_for_selector("#cuFormSlot #verbForm[data-verb=plot_course]:not([hidden])", timeout=5_000)
        assert page.evaluate("document.activeElement.name") == "target"
        page.keyboard.press("Escape")
        page.wait_for_selector("#verbForm", state="hidden", timeout=5_000)
        page.keyboard.press("m")
        page.get_by_test_id("cu-more-panel").wait_for(state="visible", timeout=5_000)
        page.keyboard.press("Escape")
        page.get_by_test_id("cu-more-panel").wait_for(state="hidden", timeout=5_000)

        # Fog: the cockpit only ever talks to this seat's harness endpoints.
        api = [r for r in requests if not r.startswith(("/static/", "/bot"))]
        assert api and all(r.startswith(("/harness/v1/P2/", "/harness/v1/rules", "/harness/v1/seats")) for r in api), api

        # Default layout unchanged: no mode-cu, CU screen hidden, controls in their original columns.
        page2 = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        page2.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page2.wait_for_selector("#main:not([hidden])", timeout=20_000)
        assert not page2.evaluate("document.body.classList.contains('mode-cu')")
        assert not page2.get_by_test_id("cu-screen").is_visible()
        assert page2.evaluate("!!document.querySelector('#colAct #warpBtns') && !!document.querySelector('#colAct #verbPad')"
                              " && !!document.querySelector('#colWhere #knownMap') && !!document.querySelector('#portCard #portTape')")
        page2.wait_for_selector("#turnBanner.turn", timeout=20_000)
        with page2.expect_request(lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000) as posted:
            page2.keyboard.press("s")
        assert '"scan"' in (posted.value.post_data or "")
