"""llm-rules-parity-v1. The mode is on, and legacy reads it as off."""

from __future__ import annotations

import tw2k.engine.constants as K


def test_lp1_mode(monkeypatch):
    assert K.llm_parity_on()
    monkeypatch.setattr(K, "LLM_PARITY_MODE", "legacy")
    assert not K.llm_parity_on()
