"""Corporation rules that are already on. The new switch stays off."""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine.corp import handle_corp_drop, handle_corp_transfer


def test_the_existing_rules_stay():
    _prior_corp_rules_v2_mode = K.CORP_RULES_V2_MODE
    try:
        for mode in ("legacy", "live"):
            K.CORP_RULES_V2_MODE = mode
            assert K.CORP_MAX_MEMBERS == 5
            assert K.corp_rules_on()
        K.CORP_RULES_V2_MODE = "legacy"
        assert handle_corp_drop is not None
        assert handle_corp_transfer is not None
    finally:
        K.CORP_RULES_V2_MODE = _prior_corp_rules_v2_mode
