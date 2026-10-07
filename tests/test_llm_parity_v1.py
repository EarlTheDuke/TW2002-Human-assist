"""llm-rules-parity-v1. The mode is on, and legacy reads it as off."""

from __future__ import annotations

import tw2k.engine.constants as K


def test_lp1_mode(monkeypatch):
    assert K.llm_parity_on()
    monkeypatch.setattr(K, "LLM_PARITY_MODE", "legacy")
    assert not K.llm_parity_on()


def test_lp3_parity_drops_the_500k_stardock_corp(monkeypatch):
    from tw2k.agents import prompts
    get_system_prompt = prompts.get_system_prompt
    monkeypatch.setattr(K, "LLM_PARITY_MODE", "legacy")
    legacy = get_system_prompt()
    monkeypatch.setattr(K, "LLM_PARITY_MODE", "tw2002")
    parity = get_system_prompt()
    assert "500k cr at StarDock" in legacy
    assert "500k cr at StarDock" not in parity
    assert "corp_deposit" not in parity.split("Corp:")[1].split("\n", 1)[0]
    assert "C.E.O. ONLY" in parity
    assert '"execute":true' in parity
    monkeypatch.setattr(prompts, "is_minimal", lambda: True)
    minimal = get_system_prompt()
    assert "500k cr at StarDock" not in minimal
    assert "free in any sector" in minimal


def test_lp5_a_rich_solo_hint_does_not_say_500k_at_stardock():
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.models import Player, Ship, ShipClass
    from tw2k.engine.observation import _action_hint
    universe = generate_universe(GameConfig(seed=60, universe_size=40, max_days=2, enable_ferrengi=False))
    player = Player(id="P1", name="P1", sector_id=1, credits=80_000, alignment=100, ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER))
    universe.players["P1"] = player
    hint = _action_hint({"id": 1, "is_stardock": True}, player, [{"id": 1}, {"id": 2}], universe)
    assert "500k" not in hint
    assert "free in any sector" in hint
    assert "<from the invite>" not in hint or "password" in hint
