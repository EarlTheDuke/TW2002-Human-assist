"""NOTE 73 cockpit checks on the redesign page, at 1280x800 and 390 wide.

Terra's form opens in the viewport and CONFIRM posts terra_colonists. The
StarDock list keeps a Genesis row the seat cannot buy. Rankings, the end
panel, and a tokenless seat use the words from the engine. Ports stay at
8200 and above, clear of 8099-8119.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.engine.victory import check_victory

import tests._cu_host as cu
from tests._cu_host import CuHost

TOK = "note73-token-p2-00000000000000000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "beta-playtest-addendum-v1"
BLOCKED = set(range(8031, 8037)) | set(range(8099, 8120))


def _safe_port(start: int = 8200) -> int:
    from tests._port_lock import claim_ports

    begin = start if start >= 8200 else 8200
    return claim_ports(1, low=begin, high=begin + 200, avoid=set(BLOCKED), sequential=True)


def _box_in_view(page, selector: str) -> None:
    box = page.locator(selector).bounding_box()
    vp = page.viewport_size or {"width": 1280, "height": 800}
    assert box, selector
    assert box["width"] > 8 and box["height"] > 8
    assert 0 <= box["y"] < vp["height"], box
    assert box["x"] < vp["width"] and box["x"] + box["width"] > 0, box


def _shot(page, stem: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / f"{stem}.png"))


def _my_move(page, timeout=30_000) -> None:
    page.wait_for_function(
        "() => document.querySelector('#waitchip') && document.querySelector('#waitchip').textContent === 'YOUR MOVE'",
        timeout=timeout,
    )


def _open(page, host, width: int, height: int):
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2#token={TOK}")
    page.wait_for_selector("#waitchip", timeout=20_000)
    _my_move(page)
    assert "token=" not in page.url.split("#")[-1] or page.url.endswith(page.url.split("#")[0])
    return page


@pytest.fixture()
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as pw:
        try:
            launched = pw.chromium.launch()
        except Exception as exc:
            pytest.skip(f"chromium not available: {exc}")
        yield launched
        launched.close()


def test_terra_gear_rankings_and_a_tokenless_seat(browser, tmp_path, monkeypatch) -> None:
    _prior_v311_profile = K.V311_PROFILE
    try:
        monkeypatch.setattr(cu, "free_port", _safe_port)
        saved = K.V311_PROFILE
        try:
            K.V311_PROFILE = "v311"
            with CuHost(tmp_path, TOK, max_days=3, turns_per_day=40, park_at=K.STARDOCK_SECTOR, fuel=0) as host:
                assert host.port >= 8200 and host.port not in BLOCKED
                u = host.runner.state.universe
                assert u.terra_colonists and u.terra_colonists > 0
                ctx = browser.new_context()
                page = ctx.new_page()
                _open(page, host, 1280, 800)

                page.get_by_role("button", name="Shipyards").click()
                page.locator('[data-yard="receipt"]').wait_for(timeout=10_000)
                receipt = page.locator('[data-yard="receipt"]').inner_text()
                assert receipt.startswith("We'll give you ")
                assert "Holds " in receipt and "go with the old ship" in receipt
                page.keyboard.press("Escape")

                def _terra(width: int, height: int, stem: str) -> None:
                    page.set_viewport_size({"width": width, "height": height})
                    page.keyboard.press("Escape")
                    page.get_by_role("button", name="Load colonists (Terra)").click()
                    page.locator('[data-screen="terra"]').wait_for(timeout=10_000)
                    _box_in_view(page, '[data-screen="terra"]')
                    _shot(page, stem)

                _terra(1280, 800, "1280-terra")
                _terra(390, 844, "390-terra")
                before = int(u.terra_colonists)
                page.get_by_role("button", name="CONFIRM").click()
                for _ in range(50):
                    if int(u.terra_colonists) < before:
                        break
                    page.wait_for_timeout(100)
                assert int(u.terra_colonists) < before
                # No free holds and nothing to put back: the button greys instead of opening a dead form.
                from tw2k.engine.models import Commodity

                me = u.players["P2"]
                me.ship.cargo[Commodity.COLONISTS] = 0
                me.ship.cargo[Commodity.FUEL_ORE] = int(me.ship.holds)
                page.wait_for_function(
                    """() => {
                        const b = [...document.querySelectorAll('button')].find((el) => el.textContent.includes('Load colonists'));
                        return b && b.disabled;
                    }""",
                    timeout=8_000,
                )

                page.keyboard.press("Escape")
                page.keyboard.press(".")
                confirm = page.locator("#dangerOk")
                if confirm.count() and confirm.is_visible():
                    confirm.click()
                page.wait_for_function(
                    "() => document.querySelector('#waitchip').textContent !== 'YOUR MOVE'",
                    timeout=20_000,
                )
                u.players["P2"].credits = 300
                _my_move(page)
                page.set_viewport_size({"width": 1280, "height": 800})
                page.get_by_role("button", name="StarDock: buy gear").click()
                page.locator('#formSlot select[data-n="item"]').wait_for(timeout=10_000)
                page.evaluate("""() => { const s = document.querySelector('#formSlot select[data-n="item"]');
                    s.size = Math.min(s.options.length, 12); }""")
                options = page.evaluate("""() => [...document.querySelectorAll('#formSlot select[data-n="item"] option')]
                    .map((o) => ({ value: o.value, text: o.label || o.textContent, disabled: o.disabled }))""")
                genesis = next(row for row in options if row["value"] == "genesis")
                assert genesis["disabled"] is True
                assert "need " in genesis["text"] and "have 300" in genesis["text"]
                _box_in_view(page, "#formSlot")
                _shot(page, "1280-gear")
                page.set_viewport_size({"width": 390, "height": 844})
                page.locator("#formSlot").scroll_into_view_if_needed()
                _box_in_view(page, "#formSlot")
                _shot(page, "390-gear")
                page.keyboard.press("Escape")

                page.set_viewport_size({"width": 1280, "height": 800})
                page.keyboard.press("C")
                page.keyboard.press("L")
                page.locator("[data-screen=rankings]").wait_for(timeout=10_000)
                body = page.locator("#menu").inner_text()
                assert "Trader Rankings" in body and "Commander" in body
                page.locator("#rankToggle").click()
                assert "experience" in page.locator("#menu").inner_text()
                _shot(page, "1280-rankings")
                page.set_viewport_size({"width": 390, "height": 844})
                _shot(page, "390-rankings")
                page.keyboard.press("Escape")

                page.keyboard.press("Z")
                page.wait_for_function(
                    "() => /How this game ends/.test(document.querySelector('#menu').innerText)",
                    timeout=15_000,
                )
                help_text = page.locator("#menu").inner_text()
                assert f"{K.BANK_MAX_BALANCE:,}" in help_text or str(K.BANK_MAX_BALANCE) in help_text
                assert "corporation costs nothing" in help_text.lower() or "A corporation costs nothing" in help_text
                page.keyboard.press("Escape")

                u.day = u.config.max_days + 1
                check_victory(u)
                from tw2k.engine.observation import build_observation

                for agent in host.runner.state.agents:
                    if getattr(agent, "player_id", None) == "P2" and getattr(agent, "current_observation", None) is not None:
                        agent.current_observation = build_observation(u, "P2")
                page.wait_for_selector('[data-game-over="panel"]', timeout=15_000)
                panel = page.locator('[data-game-over="panel"]').inner_text()
                assert panel.startswith("GAME OVER - ")
                assert "experience" in panel.lower()
                assert "You finished" in panel
                _shot(page, "1280-game-over")
                page.set_viewport_size({"width": 390, "height": 844})
                _shot(page, "390-game-over")
                ctx.close()

                bare_ctx = browser.new_context()
                bare = bare_ctx.new_page()
                bare.set_viewport_size({"width": 1280, "height": 800})
                bare.goto(f"{host.base}/bot?layout=redesign&seat=P2")
                bare.click("#connectBtn")
                bare.wait_for_selector("#err", state="visible", timeout=10_000)
                err = bare.locator("#err").inner_text()
                assert "This seat needs its join link" in err
                assert "missing bearer token" not in err.lower()
                _shot(bare, "1280-tokenless")
                bare.set_viewport_size({"width": 390, "height": 844})
                _shot(bare, "390-tokenless")
                bare_ctx.close()
        finally:
            K.V311_PROFILE = saved
    finally:
        K.V311_PROFILE = _prior_v311_profile
