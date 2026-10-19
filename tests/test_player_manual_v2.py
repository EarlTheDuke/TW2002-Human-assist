"""NOTE 109: the player manual names every action and every profile switch.

Numbers are read from the engine at render time. The page says "in v3.11 games"
only while V311_PROFILE is the string the engine actually checks, which is "v311".
The string "1" does not turn that profile on.
"""
from __future__ import annotations

import re

import tw2k.engine.constants as K
from tw2k.engine.actions import ActionKind
from tw2k.public.manual import EXEMPT, MANUAL_COVERAGE, SECTIONS, render

NEW_SECTIONS = (
    "hardware",
    "stardock-services",
    "communications",
    "computer-reports",
    "death-and-pods",
    "feds-and-ferrengi-v311",
    "towing-and-transwarp",
)


def _needed() -> set[str]:
    modes = {
        switch
        for _helper, (switch, _why) in K.V311_PROFILE_HELPERS.items()
        if switch.endswith("_MODE")
    }
    return {kind.value for kind in ActionKind} | modes


def test_every_action_and_profile_switch_is_mapped_or_exempt() -> None:
    exempt = dict(EXEMPT)
    section_ids = {sid for sid, _title in SECTIONS}
    for name, reason in exempt.items():
        assert reason.strip()
        assert name not in MANUAL_COVERAGE
    missing = []
    for name in sorted(_needed()):
        if name in MANUAL_COVERAGE:
            assert MANUAL_COVERAGE[name] in section_ids, name
        elif name not in exempt:
            missing.append(name)
    assert missing == []


def test_new_sections_are_in_the_contents_and_v311_wording_follows_the_profile(monkeypatch) -> None:
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    legacy = render("Galaxy War Command")
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    untouched = render("Galaxy War Command")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    live = render("Galaxy War Command")

    assert "in v3.11 games" not in legacy
    assert "in v3.11 games" not in untouched
    assert "in v3.11 games" in live
    assert "In legacy games" not in live
    assert "in v3.11 games, destroying an alien does not start a race grudge." in live
    assert "Rules in this game" in legacy
    assert "Rules in this game" in live
    assert f"{K.PLANET_SCANNER_COST:,}" in live
    assert f"{K.RADIO_CHANNEL_MAX:,}" in live
    assert f"{K.SHIP_RENAME_COST:,}" in live
    assert "not sold" in legacy

    ids = set(re.findall(r'id="([a-z0-9-]+)"', live))
    hrefs = re.findall(r'href="#([a-z0-9-]+)"', live)
    for sid in NEW_SECTIONS:
        assert sid in ids
        assert sid in hrefs
        assert f'id="{sid}"' in live
    assert "rules-in-this-game" in ids
