"""hold-endpoint-rules-v1. The hold note stays out until the switch is live."""

from __future__ import annotations

from tw2k.agents.prompts import get_system_prompt
from tw2k.engine import GameConfig, Player, build_observation, generate_universe
from tw2k.engine import constants as K


def _hint() -> str:
    cfg = GameConfig(
        seed=404,
        universe_size=40,
        max_days=1,
        enable_ferrengi=False,
        enable_planets=False,
        action_delay_s=0.0,
    )
    universe = generate_universe(cfg)
    player = Player(id="P1", name="Tiny Box", agent_kind="llm", sector_id=1)
    universe.players[player.id] = player
    universe.sectors[1].occupant_ids.append(player.id)
    player.known_sectors.add(1)
    return build_observation(universe, player.id).action_hint


def test_legacy_omits_the_hold_rule() -> None:
    assert K.HOLD_RULES_MODE == "legacy"
    assert "POST /hold" not in get_system_prompt()
    assert "POST /hold" not in _hint()


def test_live_names_hold_and_ok_versus_rejected() -> None:
    prior = K.HOLD_RULES_MODE
    K.HOLD_RULES_MODE = "live"
    try:
        prompt = get_system_prompt()
        hint = _hint()
    finally:
        K.HOLD_RULES_MODE = prior
    for text in (prompt, hint):
        assert "POST /hold {hold:true}" in text
        assert "POST /hold {hold:false} ends the slot and spends no turn." in text
        assert "ok means the engine applied it" in text
        assert "rejected means the engine refused it" in text
        assert "A 0-turn ok still ends the slot." in text
