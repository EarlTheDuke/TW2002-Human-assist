"""Playtest 3: the cockpit names the score that wins, the seat's place, and every rival."""
from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tests._cu_host import CuHost, allowed_test_port

pytestmark = pytest.mark.legacy_profile

TOK = "p3-score-token-p2-00000000000000001"


def _open(tmp_path: Path, pw):
    host = CuHost(tmp_path, TOK)
    host.__enter__()
    assert allowed_test_port(host.port)
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
    page.wait_for_function("() => document.querySelector('#xp').textContent !== '-'", timeout=20_000)
    return host, browser, page


@pytest.fixture()
def pw():
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    p = sync().start()
    yield p
    p.stop()


def test_experience_game_says_exp_wins_and_lists_everyone(tmp_path: Path, pw, monkeypatch) -> None:
    monkeypatch.setattr(K, "TRADER_RANK_LIST_MODE", "live")
    monkeypatch.setattr(K, "PLANET_VALUE_SCORE_MODE", "experience")
    host, browser, page = _open(tmp_path, pw)
    try:
        page.wait_for_function("() => /Score/.test(document.querySelector('#xpBtn').textContent)", timeout=20_000)
        assert "wins" in (page.locator("#xpStat").get_attribute("class") or "")
        assert " of " in page.locator("#place").inner_text()
        assert "most experience" in (page.locator("#xpStat").get_attribute("title") or "")
        page.locator("#xpBtn").click()
        page.wait_for_selector("#menu[data-screen='Standings']", timeout=10_000)
        text = page.locator("#menu").inner_text()
        assert "most experience" in text
        seats = len(host.runner.state.universe.players)
        assert page.locator("#menu [data-standing]").count() == seats + 1
        assert page.locator("#menu [data-me]").count() == 1
    finally:
        browser.close()
        host.__exit__(None, None, None)


def test_legacy_game_marks_net_worth_and_still_ranks(tmp_path: Path, pw) -> None:
    host, browser, page = _open(tmp_path, pw)
    try:
        assert page.locator("#xpBtn").inner_text() == "Exp"
        assert "wins" in (page.locator("#nwStat").get_attribute("class") or "")
        page.wait_for_function("() => / of /.test(document.querySelector('#place').textContent)", timeout=20_000)
    finally:
        browser.close()
        host.__exit__(None, None, None)
