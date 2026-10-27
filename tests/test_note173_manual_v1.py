"""NOTE 173. The player manual lists every v3.11 switch in plain words.

The lobby Rules line shows the profile for the game being created. It is a
display. It does not add a field, and it does not change a stored default.
"""
from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.public import pages
from tw2k.public import workers as WM
from tw2k.public.manual import _SWITCH_PLAIN, SECTIONS, render
from tw2k.public.security import parse_game_form

pytestmark = pytest.mark.legacy_profile


def test_v311_mode_lists_every_switch(monkeypatch) -> None:
    assert K.V311_PROFILE == "legacy"
    assert ("v311-mode", "v3.11 mode") in SECTIONS
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    legacy = render("Galaxy War Command")
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    untouched = render("Galaxy War Command")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    live = render("Galaxy War Command")

    assert "in v3.11 games" not in legacy
    assert "in v3.11 games" not in untouched
    assert "In legacy games" not in live
    assert 'id="v311-mode"' in legacy
    assert "V311_PROFILE" in legacy
    assert "does not change the stored defaults" in legacy
    listed = {row[0] for row in K.V311_PROFILE_HELPERS.values()}
    assert set(_SWITCH_PLAIN) == listed
    for switch in listed:
        assert f"<td>{switch}</td>" in legacy
        assert f"<td>{switch}</td>" in live
    assert "<td>NAVPOINT_MODE</td>" in legacy
    assert "there is no NavPoints menu." in legacy
    assert "the computer menu sets, lists, and clears 4 named NavPoints." in live
    assert "CIM is not on the computer." in legacy
    assert "Federation Hall lists each corporation" in legacy
    assert "A total unknown can buy a new name from the Underground." in legacy
    assert "A bounty on a good trader costs alignment and no experience." in legacy
    assert "Each player gets one seat link." in legacy


def test_rules_profile_is_a_display_and_defaults_stay() -> None:
    assert K.V311_PROFILE == "legacy"
    html = pages.new_game("Galaxy War Command")
    assert 'id="rulesProfile"' in html
    assert 'data-profile="v311"' in html
    assert "Profile: v3.11" in html
    assert 'name="rules"' in html
    assert 'name="profile"' not in html
    assert "Ports open full and restock 5% of max each dawn." in html
    legacy_form = pages.new_game("Galaxy War Command", values={"name": "Alpha", "rules": "legacy"})
    assert 'data-profile="legacy"' in legacy_form
    assert "Profile: legacy" in legacy_form
    made = pages.created(
        "Galaxy War Command",
        game={"id": "ab12", "name": "Alpha", "settings": {"rules": "legacy", "day_seconds": 1800}},
        join_links=[("P1", "http://lobby/join/ab12/P1?k=token")],
        watch_link="http://lobby/g/ab12/watch",
    )
    assert 'id="rulesProfile"' in made
    assert 'data-profile="legacy"' in made
    assert "Profile: legacy" in made
    v311 = pages.created(
        "Galaxy War Command",
        game={"id": "ab12", "name": "Alpha", "settings": {"rules": "v311", "day_seconds": 1800}},
        join_links=[],
        watch_link="http://lobby/g/ab12/watch",
    )
    assert 'data-profile="v311"' in v311
    assert "Profile: v3.11" in v311
    parsed = parse_game_form({"name": "Alpha", "rules": "legacy", "starting_package": "classic"})
    assert "profile" not in parsed.settings()
    assert WM.switch_overlay(parsed.settings())["V311_PROFILE"] == "legacy"  # R-4: the default is v311
    v311_settings = parse_game_form({"name": "Alpha", "rules": "v311"}).settings()
    assert WM.switch_overlay(v311_settings)["V311_PROFILE"] == "v311"
    assert K.V311_PROFILE == "legacy"


def test_rules_profile_follows_the_select() -> None:
    html = pages.new_game("Galaxy War Command")
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    with sync() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        shown = page.locator("#rulesProfile")
        assert shown.get_attribute("data-profile") == "v311"
        assert shown.inner_text().startswith("Profile: v3.11")
        page.select_option("#rules", "legacy")
        assert shown.get_attribute("data-profile") == "legacy"
        assert shown.inner_text().startswith("Profile: legacy")
        page.select_option("#rules", "v311")
        assert shown.get_attribute("data-profile") == "v311"
        assert shown.inner_text().startswith("Profile: v3.11")
        browser.close()
