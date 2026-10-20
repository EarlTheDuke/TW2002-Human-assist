"""NOTE 134 version-fixes-v1.

Computer B follows the profile. A v3.11 game, where self-destruct is already a
real command, asks before it destroys the ship. A legacy game still backtracks.
The old /bot page is unchanged. StarDock, quotes, the name change and the
Cineplex stay as they are.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

if __name__ == "__main__":
    _root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(_root))
    sys.path.insert(0, str(_root / "src"))

import pytest

import tests._cu_host as cu
import tw2k.engine.constants as K
from tw2k.engine.observation import build_observation
from tw2k.public.manual import render

ROOT = Path(__file__).resolve().parents[1]
CASES = ("v311", "legacy")
PROMPT = "ARE YOU SURE CAPTAIN? (Y/N) [N]"
ABORTED = "Self Destruct Aborted..."


def test_the_manual_computer_list_follows_the_profile(monkeypatch) -> None:
    legacy = render("Galaxy War Command")
    assert "Backtrack one sector" in legacy
    assert "Begin Self Destruct" not in legacy
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert "Backtrack one sector" in render("Galaxy War Command")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    live = render("Galaxy War Command")
    assert "Begin Self Destruct" in live
    assert PROMPT in live
    assert ABORTED in live
    assert "Backtrack one sector" not in live
    assert "returns to the previous sector." in live


def test_bot_pages_do_not_grow_a_self_destruct_computer_key() -> None:
    js = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")
    assert "Begin Self Destruct" in js
    assert PROMPT in js
    assert ABORTED in js
    for name in ("bot.html", "bot.js", "bot-parity.js"):
        body = (ROOT / "web" / name).read_text(encoding="utf-8")
        assert "Begin Self Destruct" not in body, name
        assert "ARE YOU SURE CAPTAIN" not in body, name


def test_browsers_run_in_their_own_processes() -> None:
    script = str(Path(__file__).resolve())
    for spec in CASES:
        env = os.environ.copy()
        env.pop("COCKPIT_LAYOUT", None)
        env.pop("V311_PROFILE", None)
        env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT)
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, script, spec],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=180,
        )
        tail = (proc.stdout or "")[-2500:] + (proc.stderr or "")[-2500:]
        assert proc.returncode == 0, spec + "\n" + tail
        assert "BROWSER_OK " + spec in (proc.stdout or ""), tail


def _seat(host) -> tuple:
    me = host.runner.state.universe.players["P2"]
    return (
        int(me.credits), int(me.experience), int(me.alignment),
        str(me.ship.ship_class.value if hasattr(me.ship.ship_class, "value") else me.ship.ship_class),
        int(me.sector_id), bool(me.alive),
    )


def _action(request) -> dict:
    body = request.post_data_json
    if callable(body):
        body = body()
    return body["action"]


def _open(pw, host, token: str):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={token}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    page.wait_for_function(
        "() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'",
        timeout=20_000,
    )
    return browser, page


def _computer(page) -> None:
    page.keyboard.press("Escape")
    page.keyboard.press("c")
    page.wait_for_selector("#menu[data-screen=computer]", timeout=10_000)


def _abort(page, host, key: str) -> None:
    before = _seat(host)
    posted: list = []

    def hear(request) -> None:
        if request.method == "POST" and request.url.endswith("/action"):
            posted.append(request)

    page.on("request", hear)
    _computer(page)
    page.keyboard.press("b")
    page.wait_for_selector("[data-ask=destruct]", timeout=10_000)
    assert PROMPT in page.locator("#menu").inner_text()
    page.keyboard.press(key)
    page.wait_for_function(
        "() => (document.querySelector('#lastResult').textContent || '').includes('Self Destruct Aborted')",
        timeout=10_000,
    )
    page.wait_for_timeout(400)
    page.remove_listener("request", hear)
    assert posted == []
    assert _seat(host) == before
    assert page.locator("#menu").is_hidden()


def _browser(kind: str) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    prior = K.V311_PROFILE
    K.V311_PROFILE = "v311" if kind == "v311" else "legacy"
    tok = "version-fixes-" + kind + "-p2-000000"
    tmp = Path(tempfile.mkdtemp(prefix="version-fixes-"))
    try:
        with cu.CuHost(tmp, tok) as host, sync_playwright() as pw:
            assert cu.allowed_test_port(host.port)
            assert host.port != 8099
            obs = build_observation(host.runner.state.universe, "P2")
            kinds = {row["kind"] for row in obs.legal_actions}
            if kind == "v311":
                assert "self_destruct" in kinds
            else:
                assert "self_destruct" not in kinds
            browser, page = _open(pw, host, tok)
            try:
                _computer(page)
                menu = page.locator("#menu").inner_text()
                if kind == "legacy":
                    assert "Backtrack" in menu
                    assert "Begin Self Destruct" not in menu
                    page.keyboard.press("b")
                    page.wait_for_function(
                        "() => /No previous sector/.test(document.querySelector('#lastResult').textContent || '')",
                        timeout=10_000,
                    )
                    assert page.locator("[data-ask=destruct]").is_hidden()
                else:
                    assert "Begin Self Destruct" in menu
                    assert "Backtrack" not in menu
                    _abort(page, host, "n")
                    _abort(page, host, "Enter")
                    page.keyboard.press("<")
                    page.wait_for_function(
                        "() => /No previous sector/.test(document.querySelector('#lastResult').textContent || '')",
                        timeout=10_000,
                    )
                    before = _seat(host)
                    _computer(page)
                    page.keyboard.press("b")
                    page.wait_for_selector("[data-ask=destruct]", timeout=10_000)
                    with page.expect_request(
                        lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000,
                    ) as caught:
                        page.keyboard.press("y")
                    assert _action(caught.value)["kind"] == "self_destruct"
                    assert _action(caught.value)["args"] == {}
                    page.wait_for_timeout(500)
                    assert _seat(host) != before
            finally:
                browser.close()
    finally:
        K.V311_PROFILE = prior
    print("BROWSER_OK " + kind)


if __name__ == "__main__":
    _browser(sys.argv[1])
