"""NOTE 129. A total unknown is offered a new identity for 100 credits.

docs/playtests/twgs-live/name-change.txt. The deal was declined, so a No
pays nothing. A higher experience was not measured and is not given a price.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tw2k.engine.constants as K
from tw2k.agents.prompts import get_system_prompt
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship
from tw2k.engine.observation import build_observation
from tw2k.public.manual import render

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = (ROOT / "docs/playtests/twgs-live/name-change.txt").read_text(encoding="utf-8")


def _world():
    universe = generate_universe(
        GameConfig(seed=9, universe_size=20, max_days=5, enable_planets=False, enable_ferrengi=False)
    )
    for pid, name in (("P1", "N129Cur"), ("P2", "Bo")):
        player = Player(id=pid, name=name, ship=Ship(name="Ship"), credits=140, alignment=0, experience=1)
        player.sector_id = 1
        player.ug_entered_day = int(universe.day)
        player.ug_password_known = True
        universe.players[pid] = player
        if pid not in universe.sectors[1].occupant_ids:
            universe.sectors[1].occupant_ids.append(pid)
    return universe


def _on(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    monkeypatch.setattr(K, "UG_NAME_MODE", "v311")


def test_capture_lines_are_the_measured_offer() -> None:
    assert K.UG_NAME_CHANGE is False
    assert K.UG_NAME_MODE == "legacy"
    assert K.UG_NAME_UNKNOWN_COST == 100
    lines = K.ug_name_unknown_lines()
    assert len(lines) == 4
    for line in lines:
        assert line in CAPTURE
    assert "247" not in "\n".join(lines)
    assert "100 credits" in lines[2]


def test_stored_game_stays_off(monkeypatch) -> None:
    monkeypatch.setattr(K, "UG_NAME_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    universe = _world()
    player = universe.players["P1"]
    assert "underground_rename" not in {row.kind for row in legal_actions(universe, "P1")}
    refused = apply_action(
        universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"deal": True, "name": "Nyx"})
    )
    assert refused.ok is False
    assert player.name == "N129Cur"
    assert player.credits == 140
    monkeypatch.setattr(K, "UG_NAME_MODE", "1")
    assert K.ug_name_live() is False
    monkeypatch.setattr(K, "UG_NAME_MODE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.ug_name_live() is False
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.UG_NAME_MODE == "legacy"
    assert K.ug_name_live() is True


def test_offer_decline_and_accept_for_a_total_unknown(monkeypatch) -> None:
    _on(monkeypatch)
    universe = _world()
    player = universe.players["P1"]
    row = next(la for la in legal_actions(universe, "P1") if la.kind == "underground_rename")
    assert row.legal is True
    assert row.params["cost"] == 100
    assert row.params["lines"] == list(K.ug_name_unknown_lines())

    offered = apply_action(universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={}))
    assert offered.ok is True
    assert offered.turns_spent == 0
    assert player.name == "N129Cur"
    assert player.credits == 140
    assert universe.events[-1].payload["deal"] == "open"
    assert "this'll be cheap." in universe.events[-1].summary
    assert "100 credits." in universe.events[-1].summary
    assert "Well, is it a deal?" in universe.events[-1].summary
    rival = build_observation(universe, "P2")
    assert "total unknown" not in str(rival.recent_events)
    mine = build_observation(universe, "P1")
    assert "total unknown" in str(mine.recent_events)

    declined = apply_action(
        universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"deal": False, "name": "Nyx"})
    )
    assert declined.ok is True
    assert player.name == "N129Cur"
    assert player.credits == 140
    assert universe.events[-1].payload["deal"] == "no"
    assert "old_name" not in universe.events[-1].payload

    worded = apply_action(universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"deal": "no"}))
    assert worded.ok is True
    assert player.credits == 140

    accepted = apply_action(
        universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"deal": True, "name": "Nyx"})
    )
    assert accepted.ok is True
    assert player.name == "Nyx"
    assert player.credits == 40
    assert universe.events[-1].payload["deal"] == "yes"
    assert universe.events[-1].payload["cost"] == 100
    assert universe.events[-1].summary.startswith("N129Cur is now Nyx")
    assert "this'll be cheap" in universe.events[-1].summary
    assert "new identity for 100 credits" in universe.events[-1].summary


def test_a_name_without_a_deal_still_buys_it(monkeypatch) -> None:
    _on(monkeypatch)
    universe = _world()
    player = universe.players["P1"]
    result = apply_action(universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"name": "Nyx"}))
    assert result.ok is True
    assert player.name == "Nyx"
    assert player.credits == 40


def test_experience_zero_stays_on_the_existing_unknown_band(monkeypatch) -> None:
    """Experience 0 was not a separate measurement. The hook already prices at most 1."""
    _on(monkeypatch)
    universe = _world()
    universe.players["P1"].experience = 0
    row = next(la for la in legal_actions(universe, "P1") if la.kind == "underground_rename")
    assert row.legal is True
    assert row.params["cost"] == 100
    assert "100 credits." in row.params["lines"][2]


def test_higher_experience_is_not_priced(monkeypatch) -> None:
    _on(monkeypatch)
    universe = _world()
    player = universe.players["P1"]
    player.experience = 2
    player.credits = 5_000
    row = next(la for la in legal_actions(universe, "P1") if la.kind == "underground_rename")
    assert row.legal is False
    assert "not priced" in (row.reason or "")
    assert "lines" not in row.params
    assert "cost" not in row.params
    before = len(universe.events)
    refused = apply_action(
        universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"deal": True, "name": "Hex"})
    )
    assert refused.ok is False
    assert refused.error == "the Underground has not priced this trader"
    assert player.name == "N129Cur"
    assert player.credits == 5_000
    assert len(universe.events) == before


def test_a_short_purse_can_decline_and_cannot_accept(monkeypatch) -> None:
    _on(monkeypatch)
    universe = _world()
    player = universe.players["P1"]
    player.credits = 40
    declined = apply_action(universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"deal": False}))
    assert declined.ok is True
    assert player.credits == 40
    assert player.name == "N129Cur"
    accepted = apply_action(
        universe, "P1", Action(kind=ActionKind.UNDERGROUND_RENAME, args={"deal": True, "name": "Nyx"})
    )
    assert accepted.ok is False
    assert accepted.error == "not enough credits"
    assert player.name == "N129Cur"
    assert player.credits == 40


def test_prompt_and_manual_follow_the_switch(monkeypatch) -> None:
    monkeypatch.setattr(K, "UG_NAME_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    quiet = get_system_prompt()
    assert "Decline and the credits stay." not in quiet
    legacy = render("Galaxy War Command")
    assert "the Underground does not sell a new name." in legacy
    _on(monkeypatch)
    live_prompt = get_system_prompt()
    assert "100 credits" in live_prompt
    assert "Decline and the credits stay." in live_prompt
    assert "A higher experience is not priced." in live_prompt
    page = render("Galaxy War Command")
    assert "this'll be cheap." in page
    assert "Well, is it a deal?" in page


def test_cockpit_declines_then_accepts_the_measured_offer(monkeypatch, tmp_path) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests._cu_host import CuHost

    monkeypatch.setattr(K, "UG_NAME_MODE", "v311")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    token = "ug-name-token-p2-000000000000000000"
    pw = sync_api.sync_playwright().start()
    try:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:
            pytest.skip(f"chromium not available: {exc}")
        host = CuHost(tmp_path, token)
        host.__enter__()
        try:
            universe = host.runner.state.universe
            me = universe.players["P2"]
            origin = universe.sectors[me.sector_id]
            if "P2" in origin.occupant_ids:
                origin.occupant_ids.remove("P2")
            me.sector_id = 1
            me.planet_landed = None
            me.credits = 140
            me.alignment = 0
            me.experience = 1
            me.ug_password_known = True
            me.ug_entered_day = int(universe.day)
            if "P2" not in universe.sectors[1].occupant_ids:
                universe.sectors[1].occupant_ids.append("P2")
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={token}")
            page.wait_for_selector("#waitchip", timeout=20_000)
            page.keyboard.press(".")
            page.wait_for_function(
                "() => document.querySelector('#waitchip').textContent === 'YOUR MOVE'",
                timeout=20_000,
            )
            page.get_by_role("button", name="Get your Name Changed", exact=True).click()
            offer = page.locator("[data-ug-name=offer]")
            offer.wait_for(timeout=10_000)
            text = offer.inner_text()
            assert "Seems you're a total unknown, this'll be cheap." in text
            assert "We can give you a new identity for 100 credits." in text
            assert "Well, is it a deal?" in text
            assert "Kal Durak" in text
            page.evaluate("() => { document.querySelector('#lastResult').textContent = ''; }")
            with page.expect_request(
                lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000
            ) as caught:
                page.locator("#dangerNo").click()
            body = caught.value.post_data_json
            if callable(body):
                body = body()
            assert body["action"]["kind"] == "underground_rename"
            assert body["action"]["args"]["deal"] is False
            page.wait_for_function(
                """() => {
                  const chip = document.querySelector('#waitchip').textContent;
                  const line = document.querySelector('#lastResult').textContent || '';
                  return chip === 'YOUR MOVE' && line.indexOf('Credits') >= 0;
                }""",
                timeout=20_000,
            )
            assert me.credits == 140
            assert me.name == "Commander"
            result = page.locator("#lastResult").inner_text()
            assert "100 credits" in result
            assert "Credits +0" in result or "Credits 0" in result

            page.get_by_role("button", name="Get your Name Changed", exact=True).click()
            page.locator("#dangerOk").wait_for(timeout=10_000)
            page.locator("#dangerOk").click()
            page.wait_for_selector(".frm [data-n=name]", timeout=10_000)
            page.locator(".frm [data-n=name]").fill("Nyx")
            page.evaluate("() => { document.querySelector('#lastResult').textContent = ''; }")
            with page.expect_request(
                lambda r: r.method == "POST" and r.url.endswith("/action"), timeout=10_000
            ) as bought:
                page.locator(".frm button.verb", has_text="CONFIRM").click()
            bought_body = bought.value.post_data_json
            if callable(bought_body):
                bought_body = bought_body()
            assert bought_body["action"]["args"]["deal"] is True
            assert bought_body["action"]["args"]["name"] == "Nyx"
            page.wait_for_function(
                """() => (document.querySelector('#lastResult').textContent || '').indexOf('Nyx') >= 0""",
                timeout=20_000,
            )
            assert me.name == "Nyx"
            assert me.credits == 40
        finally:
            browser.close()
            host.__exit__(None, None, None)
    finally:
        pw.stop()
