"""NOTE 103 cockpit. Mail, NavPoints, find route, and a fighter line on the daily log."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests._cu_host import CuHost
from tw2k.engine import Action, ActionKind
from tw2k.engine.models import EventKind
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import _handle_hail

pytestmark = pytest.mark.legacy_profile

TOK = "note103-cockpit-token-p2-00000000"
SHOTS = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "note103-v1"


def _ready(host: CuHost):
    deadline = time.time() + 20
    while time.time() < deadline:
        universe = host.runner.state.universe
        agent = next((row for row in host.runner.state.agents if row.player_id == "P2"), None)
        if host.parked and universe is not None and agent is not None and agent.awaiting_input and "P2" in universe.players:
            return universe, universe.players["P2"], agent
        time.sleep(0.05)
    raise AssertionError("seat did not become ready")


def _shot(page, name: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.locator("#menu").screenshot(path=str(SHOTS / name))


def test_mail_helpers_and_fighter_line(tmp_path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    monkeypatch.setattr(K, "MAIL_MODE", "live")
    monkeypatch.setattr(K, "OWNER_HAZARD_NOTICE_MODE", "tw2002")
    with CuHost(tmp_path, TOK, turns_per_day=400) as host, sync_playwright() as pw:
        universe, me, agent = _ready(host)
        quiet = _handle_hail(universe, "P1", Action(kind=ActionKind.HAIL, args={"target": "P2", "message": "Left this for you"}))
        assert quiet.ok, quiet.error
        assert universe.players["P2"].inbox[-1]["kind"] == "mail"
        universe.emit(
            EventKind.COMBAT,
            actor_id="P1",
            sector_id=me.sector_id,
            payload={
                "vs": "fighter_sector",
                "defender_owner": "P2",
                "defender_losses": 4,
                "attacker_losses": 1,
            },
            summary="Ann hit fighters",
        )
        agent.current_observation = build_observation(universe, "P2")
        browser = pw.chromium.launch()
        try:
            for width, height in ((1366, 900), (390, 844)):
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
                page.wait_for_selector("[data-mail=new]", timeout=20_000)
                assert page.locator("[data-mail=new]").inner_text() == "New Mail"
                page.keyboard.press("c")
                page.wait_for_selector("#menu[data-screen=computer]", timeout=10_000)
                page.keyboard.press("m")
                page.wait_for_selector("#menu[data-screen=mail] [data-mail=letter]", timeout=10_000)
                assert "Left this for you" in page.locator("#menu").inner_text()
                _shot(page, f"{width}-mail.png")
                page.keyboard.press("Escape")
                page.keyboard.press("c")
                page.wait_for_selector("#menu[data-screen=computer]", timeout=10_000)
                assert "NavPoints" not in page.locator("#menu").inner_text()
                page.keyboard.press("n")
                page.wait_for_function(
                    "() => (document.querySelector('#lastResult') || {}).textContent.includes('not a computer command')",
                    timeout=10_000,
                )
                assert page.locator("#menu[data-screen=navpoints]").count() == 0
                page.keyboard.press("Escape")
                page.keyboard.press("c")
                page.keyboard.press("e")
                page.wait_for_selector("#menu[data-screen=find-route]", timeout=10_000)
                here = str(me.sector_id)
                page.locator("[data-route=from]").fill(here)
                page.locator("[data-route=to]").fill(here)
                page.locator("[data-route=go]").click()
                assert "0 hops" in page.locator("[data-route=path]").inner_text()
                page.keyboard.press("Escape")
                page.keyboard.press("c")
                page.keyboard.press("s")
                page.wait_for_selector("#menu[data-screen=quick-stats] [data-stat=line]", timeout=10_000)
                assert "Turns" in page.locator("#menu").inner_text()
                page.keyboard.press("Escape")
                page.keyboard.press("c")
                page.keyboard.press("d")
                page.wait_for_selector("#menu[data-screen=daily-log] [data-hit=fighters]", timeout=10_000)
                hit = page.locator("[data-hit=fighters]").inner_text()
                assert "sector" in hit
                assert "your losses 4" in hit
                assert "their losses 1" in hit
                page.close()
        finally:
            browser.close()
