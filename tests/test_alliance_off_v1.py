"""GAP 14.6: v3.11 has no enforced alliance.

Bible (S3), "Secret Alliances and Treaties": a corporation may offer not to
attack you; "These are by no means binding and are not enforced".
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship, ShipClass
from tw2k.engine.runner import apply_action


def _u():
    u = generate_universe(GameConfig(
        seed=146, universe_size=80, max_days=3, turns_per_day=40,
        starting_credits=50_000, enable_ferrengi=False, enable_planets=False,
    ))
    for pid in ("P1", "P2"):
        u.players[pid] = Player(
            id=pid, name=pid, ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=10, holds=20),
            sector_id=1, credits=1000, alignment=0, experience=0, turns_per_day=40,
        )
        u.sectors[1].occupant_ids.append(pid)
    return u


def _legal(u, pid, kind):
    return next(a for a in legal_actions(u, pid) if a.kind == kind)


def test_legacy_keeps_alliances(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    assert not K.alliance_off_live()
    u = _u()
    assert _legal(u, "P1", ActionKind.PROPOSE_ALLIANCE).legal
    r = apply_action(u, "P1", Action(kind=ActionKind.PROPOSE_ALLIANCE, args={"target": "P2"}))
    assert r.ok and u.alliances


def test_v311_refuses_propose_and_accept(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    u = _u()
    apply_action(u, "P1", Action(kind=ActionKind.PROPOSE_ALLIANCE, args={"target": "P2"}))
    aid = next(iter(u.alliances))
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.alliance_off_live()
    la = _legal(u, "P1", ActionKind.PROPOSE_ALLIANCE)
    assert not la.legal and la.reason == K.ALLIANCE_OFF_REASON
    assert not _legal(u, "P2", ActionKind.ACCEPT_ALLIANCE).legal
    r = apply_action(u, "P1", Action(kind=ActionKind.PROPOSE_ALLIANCE, args={"target": "P2"}))
    assert not r.ok
    r = apply_action(u, "P2", Action(kind=ActionKind.ACCEPT_ALLIANCE, args={"alliance_id": aid}))
    assert not r.ok and not u.alliances[aid].active
    assert _legal(u, "P1", ActionKind.BREAK_ALLIANCE).legal  # an old pact can still end


def test_switch_alone(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    monkeypatch.setattr(K, "ALLIANCE_OFF_MODE", "live")
    assert K.alliance_off_live()


def test_manual_line():
    from tw2k.public import manual
    assert "ALLIANCE_OFF_MODE" in manual._SWITCH_PLAIN
    assert "gentleman's agreement the game does not enforce" in open(manual.__file__).read()
