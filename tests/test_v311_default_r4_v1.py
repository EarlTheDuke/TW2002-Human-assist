"""R-4 (docs/plans/future-stages-v1.md): the stored V311_PROFILE default is v311.

A process that never sets the profile now plays the v3.11 rulings. Legacy is a choice:
the lobby's Legacy rule set names it in the switch overlay, and a test module that pins
the legacy numbers marks itself with pytest.mark.legacy_profile.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.public import security as S
from tw2k.public import workers as WM


def test_stored_default_is_v311() -> None:
    assert K.V311_PROFILE == "v311"
    assert K.v311_profile() is True


def test_lobby_names_the_profile_for_both_rule_sets() -> None:
    v311 = WM.switch_overlay(S.parse_game_form({"name": "A", "rules": "v311"}).settings())
    legacy = WM.switch_overlay(S.parse_game_form({"name": "B", "rules": "legacy"}).settings())
    assert v311["V311_PROFILE"] == "v311"
    assert legacy["V311_PROFILE"] == "legacy"

