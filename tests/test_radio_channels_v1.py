"""Corp subspace radio exists only when that switch is on.

Off, the action is refused and the legal list does not offer it.
On, channel 0 to 60000. Only corp mates tuned to that channel hear it.

Plants:
  pb1 — a mate on the same channel still hears nothing.
  pb2 — the action succeeds while the switch is off.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship

pytestmark = pytest.mark.legacy_profile


def _world():
    u = generate_universe(GameConfig(seed=3, universe_size=30, enable_ferrengi=False, enable_planets=False))
    for pid, name in (("A", "Alpha"), ("B", "Bravo"), ("C", "Cee")):
        u.players[pid] = Player(id=pid, name=name, ship=Ship(), sector_id=1, credits=1000)
        u.sectors[1].occupant_ids.append(pid)
    u.players["A"].corp_ticker = "ACME"
    u.players["B"].corp_ticker = "ACME"
    return u


def test_switch_stays_off() -> None:
    assert K.RADIO_CHANNEL_MODE == "legacy"
    assert K.radio_channel_live() is False
    assert K.RADIO_CHANNEL_MAX == 60_000


def test_off_is_not_offered() -> None:
    u = _world()
    kinds = {a.kind for a in legal_actions(u, "A")}
    assert "radio" not in kinds
    heard = apply_action(u, "A", Action(kind=ActionKind.RADIO, args={"channel": 12, "message": "hi"}))
    assert heard.ok is False
    assert "radio_channel" not in u.players["A"].model_dump()


def test_on_reaches_only_the_tuned_mate() -> None:
    _prior_radio_channel_mode = K.RADIO_CHANNEL_MODE
    try:
        u = _world()
        try:
            K.RADIO_CHANNEL_MODE = "live"
            kinds = {a.kind for a in legal_actions(u, "A")}
            assert "radio" in kinds
            bad = apply_action(u, "A", Action(kind=ActionKind.RADIO, args={"channel": 60001}))
            assert bad.ok is False
            assert apply_action(u, "A", Action(kind=ActionKind.RADIO, args={"channel": 12})).ok
            assert apply_action(u, "B", Action(kind=ActionKind.RADIO, args={"channel": 12})).ok
            assert apply_action(u, "C", Action(kind=ActionKind.RADIO, args={"channel": 12})).ok is False
            sent = apply_action(u, "A", Action(kind=ActionKind.RADIO, args={"message": "hold"}))
            assert sent.ok is True
            assert u.players["B"].inbox[-1]["message"] == "hold"
            assert u.players["B"].inbox[-1]["channel"] == 12
            assert u.players["C"].inbox == []
        finally:
            K.RADIO_CHANNEL_MODE = "legacy"
    finally:
        K.RADIO_CHANNEL_MODE = _prior_radio_channel_mode
