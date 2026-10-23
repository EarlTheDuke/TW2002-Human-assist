"""Playtest 3 leftovers (c): a port trade is not shown to rivals under v311."""
from __future__ import annotations

import json

import pytest

from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import Commodity, Player
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action


def _trade_and_look(monkeypatch, profile):
    monkeypatch.setattr(K, "V311_PROFILE", profile)
    u = generate_universe(GameConfig(seed=7, universe_size=80, max_days=3, turns_per_day=200, enable_ferrengi=False))
    sid = next(s for s, x in u.sectors.items() if x.port is not None and s > 10)
    for pid in ("P1", "P2"):
        p = Player(id=pid, name="Guest " + pid, agent_kind="external", sector_id=sid, credits=50000)
        u.players[pid] = p
        u.sectors[sid].occupant_ids.append(pid)
    for c in Commodity:
        u.players["P1"].ship.cargo[c] = 10
        for side in ("sell", "buy"):
            if apply_action(u, "P1", Action(kind=ActionKind.TRADE, args={"commodity": c.value, "qty": 5, "side": side})).ok:
                break
        else:
            continue
        break

    def trades(pid):
        o = json.loads(build_observation(u, pid).model_dump_json())
        return [e for e in o["recent_events"] if e.get("kind") == "trade"]

    return trades("P1"), trades("P2")


def test_legacy_rival_still_sees_trade(monkeypatch):
    mine, rival = _trade_and_look(monkeypatch, "legacy")
    assert mine and rival
    assert "@" in rival[0]["summary"]


def test_v311_rival_does_not_see_trade(monkeypatch):
    mine, rival = _trade_and_look(monkeypatch, "v311")
    assert mine and "@" in mine[0]["summary"]
    assert rival == []


def test_private_flag_never_reaches_view(monkeypatch):
    mine, _ = _trade_and_look(monkeypatch, "v311")
    assert "_private" not in json.dumps(mine)


def test_helper_registered_and_manual_line():
    assert K.TRADE_PRIVATE_MODE == "legacy"
    assert "trade_private_live" in K.V311_PROFILE_HELPERS
    from tw2k.public import manual
    assert "TRADE_PRIVATE_MODE" in manual._SWITCH_PLAIN
