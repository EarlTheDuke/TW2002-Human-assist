"""NOTE 103. From the command prompt, > opens quick stats and < backtracks.

/ is the documented quick-stats key and stays unbound. A one-way return refuses.
"""

from __future__ import annotations

import re
from collections import deque
from pathlib import Path

import pytest

from tw2k.public.manual import render

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "web" / "redesign.js"
TOK = "note103-keys-token-p2-0000000000"
PROMPT_STATS = "Quick stats from the command prompt"
PROMPT_BACK = "Backtrack to the previous sector when that lane is still open"


def _key_body() -> str:
    js = JS.read_text(encoding="utf-8")
    start = js.index("  function key(k) {")
    end = js.index("  function flushPending()", start)
    return js[start:end]


def _listener() -> str:
    js = JS.read_text(encoding="utf-8")
    start = js.index('document.addEventListener("keydown", (ev) => {\n    const tag')
    end = js.index("  window.__tw2kTest", start)
    return js[start:end]


def test_prompt_keys_are_named_before_the_computer_menu() -> None:
    body = _key_body()
    stats = body.index('if (k === ">") { quickStats(); return; }')
    back = body.index('if (k === "<") { backtrack(); return; }')
    menu = body.index("if (inComputer)", stats)
    assert stats < back < menu
    assert 'if (k === "S") return quickStats();' in body
    assert 'if (k === "B") return selfDestructInGame() ? beginSelfDestruct() : backtrack();' in body
    assert 'k === "/"' not in body
    assert 'k === ","' not in body
    listener = _listener()
    code = "\n".join(line for line in listener.splitlines() if not line.strip().startswith("//"))
    assert 'if (ev.key === ">" || ev.key === "<")' in code
    assert code.index('ev.key === ">"') < code.index("toUpperCase()")


def test_the_manual_names_the_prompt_keys() -> None:
    page = render("Galaxy War Command")
    assert PROMPT_STATS in page
    assert PROMPT_BACK in page


def _lanes(universe, sid: int) -> list[int]:
    return [int(w) for w in universe.sectors[int(sid)].warps]


def _two_way(universe, src: int, dst: int) -> bool:
    return dst in _lanes(universe, src) and src in _lanes(universe, dst)


def _find_hop(universe, start: int, want_two_way: bool, limit: int = 6) -> list[int] | None:
    """Hops from start whose last step matches the lane direction."""
    start = int(start)
    queue: deque[tuple[int, list[int]]] = deque([(start, [])])
    seen = {start}
    while queue:
        at, path = queue.popleft()
        if len(path) >= limit:
            continue
        for nxt in _lanes(universe, at):
            hop = path + [nxt]
            if _two_way(universe, at, nxt) == want_two_way:
                return hop
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, hop))
    return None


def _action(request) -> dict:
    body = request.post_data_json
    if callable(body):
        body = body()
    return body["action"]


def _sector(page) -> str:
    return page.locator("#pSector").inner_text().strip()


def _your_move(page) -> None:
    page.wait_for_function(
        "() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'",
        timeout=20_000,
    )


def _hop(page, dest: int) -> None:
    page.wait_for_selector("#warps button", timeout=20_000)
    page.locator("#warps button").filter(has_text=re.compile(rf":{dest}(?:\s|\(|$)")).first.click()
    page.wait_for_function(
        "() => document.querySelector('#pSector').textContent.trim() === " + repr(str(dest)),
        timeout=20_000,
    )
    _your_move(page)


def _walk(page, hops: list[int]) -> None:
    for dest in hops:
        _hop(page, dest)


def test_prompt_keys_open_quick_stats_and_backtrack(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    from tests._cu_host import CuHost

    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as pw:
        universe = host.runner.state.universe
        start = int(universe.players["P2"].sector_id)
        two = _find_hop(universe, start, True)
        one = _find_hop(universe, start, False)
        assert two, "seed has no two-way lane within 6 hops"
        assert one, "seed has no one-way lane within 6 hops"
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            page.wait_for_selector("#waitchip", timeout=20_000)
            _your_move(page)
            assert _sector(page) == str(start)

            quiet: list = []
            page.on(
                "request",
                lambda request: quiet.append(request)
                if request.method == "POST" and request.url.endswith("/action")
                else None,
            )
            page.keyboard.press("<")
            page.wait_for_function(
                "() => /No previous sector/.test(document.querySelector('#lastResult').textContent || '')",
                timeout=10_000,
            )
            page.keyboard.press(">")
            page.wait_for_selector("#menu[data-screen=quick-stats] [data-stat=line]", timeout=10_000)
            screen = page.locator("#menu").inner_text()
            assert "Quick stats" in screen
            assert "Turns" in screen and "credits" in screen
            assert "Fighters" in screen
            assert page.locator("[data-stat=line]").count() >= 3
            page.keyboard.press("Escape")
            page.wait_for_function("() => document.querySelector('#menu').hidden", timeout=10_000)
            page.keyboard.press("/")
            page.wait_for_timeout(300)
            assert page.locator("#menu").is_hidden()
            assert _sector(page) == str(start)
            assert quiet == []

            before = start if len(two) == 1 else two[-2]
            _walk(page, two)
            assert _sector(page) == str(two[-1])
            with page.expect_request(
                lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=15_000,
            ) as caught:
                page.keyboard.press("<")
            action = _action(caught.value)
            assert action["kind"] == "warp"
            assert int(action["args"]["target"]) == before
            page.wait_for_function(
                "() => document.querySelector('#pSector').textContent.trim() === " + repr(str(before)),
                timeout=20_000,
            )
            _your_move(page)
            assert "cannot backtrack" not in page.locator("#lastResult").inner_text()

            here = int(_sector(page))
            away = _find_hop(universe, here, False)
            assert away, "no one-way lane from the sector < returned to"
            _walk(page, away)
            landed = str(away[-1])
            assert _sector(page) == landed
            page.keyboard.press("<")
            page.wait_for_function(
                "() => /cannot backtrack/.test(document.querySelector('#lastResult').textContent || '')",
                timeout=10_000,
            )
            page.wait_for_timeout(400)
            assert _sector(page) == landed
            _your_move(page)
        finally:
            browser.close()
