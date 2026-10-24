"""GameA TWSTATS [Settings] photon and cloak card.

Capture: docs/playtests/twgs-live/twstats-costs-ven.txt (Ven GameA, PR #157).
The five confirmed lines:

    Photon Missile Duration=20 Sec
    FedSpace Photons=False
    Photons Disable Players=True
    Cloak Fail Percent=3%
    Multiple Photons=False

FedSpace, player disable, and one photon per wave are PHOTON_CLOAK_SETTINGS_MODE
row 230. The 3% cloak fail is already stored. The 20-second duration stays
1 day-tick. A stored game (the card off) does not move.
"""

from __future__ import annotations

from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, Ship, ShipClass
from tw2k.engine.runner import tick_day

CAPTURE = (
    "Photon Missile Duration=20 Sec",
    "FedSpace Photons=False",
    "Photons Disable Players=True",
    "Cloak Fail Percent=3%",
    "Multiple Photons=False",
)
CAPTURE_PATH = Path("docs/playtests/twgs-live/twstats-costs-ven.txt")


def test_capture_lines_are_cited() -> None:
    profile = Path("docs/plans/v311-profile-v1.md").read_text(encoding="utf-8")
    queue = Path("docs/plans/live-twgs-test-queue-v1.md").read_text(encoding="utf-8")
    conflicts = Path("docs/plans/V311_SOURCE_CONFLICTS.md").read_text(encoding="utf-8")
    for line in CAPTURE:
        assert line in profile, line
        assert line in queue, line
    assert "Photon Missile Duration=20 Sec" in conflicts
    assert "DIFFERENT and deferred" in conflicts
    # The tip file is the [Costs] stub until PR #157 lands the full capture.
    text = CAPTURE_PATH.read_text(encoding="utf-8") if CAPTURE_PATH.exists() else ""
    if "[Settings]" in text:
        for line in CAPTURE:
            assert line in text, line


def test_stored_game_keeps_today_and_the_duration_stays_one_tick(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.photon_cloak_settings_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    assert K.photon_cloak_settings_live() is False
    assert K.PHOTON_CLOAK_SETTINGS_MODE == "legacy"
    assert K.PHOTON_WAVE_DURATION == 1
    assert K.CLOAK_FAIL_RATE == 0.03
    u, sid, adj = _world()
    _arm(u)
    align = u.players["A"].alignment
    assert apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": adj})).ok
    assert u.players["B"].ship.photon_disabled_ticks == 0
    assert u.players["A"].ship.photon_refire_ticks == 0
    assert apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": adj})).ok
    assert u.players["A"].ship.photon_missiles == 1
    assert u.players["A"].alignment == align
    # Into FedSpace is still allowed while the card is off.
    _link_fed(u, sid)
    assert apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": 1})).ok
    assert u.players["A"].alignment == align


def test_card_honors_the_three_lines_and_leaves_duration_and_cloak(monkeypatch) -> None:
    monkeypatch.setattr(K, "PHOTON_CLOAK_SETTINGS_MODE", "live")
    assert K.photon_cloak_settings_live() is True
    assert K.PHOTON_WAVE_DURATION == 1
    assert K.CLOAK_FAIL_RATE == 0.03
    u, sid, adj = _world()
    _arm(u)
    _link_fed(u, sid)
    align = u.players["A"].alignment
    las = {a.kind: a for a in legal_actions(u, "A")}
    choices = (las["photon_missile"].params.get("target") or {}).get("choices", [])
    assert 1 not in choices
    assert all(int(c) not in K.FEDSPACE_SECTORS for c in choices)
    fed = apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": 1}))
    assert fed.ok is False and fed.error == "FedSpace photons are off"
    assert u.players["A"].alignment == align
    assert u.players["A"].ship.photon_missiles == 3
    assert apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": adj})).ok
    assert u.players["B"].ship.photon_disabled_ticks == K.PHOTON_WAVE_DURATION
    assert u.players["A"].ship.photon_disabled_ticks == 0
    assert u.players["A"].ship.photon_refire_ticks == 1
    assert u.players["A"].ship.photon_missiles == 2
    blocked = {a.kind: a for a in legal_actions(u, "A")}
    assert blocked["photon_missile"].legal is False
    assert blocked["photon_missile"].reason == "photon wave still up"
    again = apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": adj}))
    assert again.ok is False and again.error == "photon wave still up"
    assert u.players["A"].ship.photon_missiles == 2
    # A disabled player cannot fire back.
    if sid not in u.sectors[adj].warps:
        u.sectors[adj].warps.append(sid)
    u.players["B"].ship.ship_class = ShipClass.MISSILE_FRIGATE
    u.players["B"].ship.photon_missiles = 1
    u.players["B"].turns_per_day = 1000
    u.players["B"].turns_today = 0
    back = apply_action(u, "B", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": sid}))
    assert back.ok is False and back.error == "your fighters are offline (photon)"
    tick_day(u)
    assert u.players["A"].ship.photon_refire_ticks == 0
    assert u.players["B"].ship.photon_disabled_ticks == 0
    assert u.sectors[adj].photon_wave_remaining == 0
    assert apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": adj})).ok


def test_firing_from_fedspace_is_refused_without_an_alignment_dock(monkeypatch) -> None:
    monkeypatch.setattr(K, "PHOTON_CLOAK_SETTINGS_MODE", "live")
    u, sid, _adj = _world()
    _arm(u)
    _move(u, "A", 1)
    if sid not in u.sectors[1].warps:
        u.sectors[1].warps.append(sid)
    align = u.players["A"].alignment
    missiles = u.players["A"].ship.photon_missiles
    res = apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": sid}))
    assert res.ok is False and res.error == "FedSpace photons are off"
    assert u.players["A"].alignment == align
    assert u.players["A"].ship.photon_missiles == missiles
    las = {a.kind: a for a in legal_actions(u, "A")}
    assert las["photon_missile"].legal is False
    assert las["photon_missile"].reason == "FedSpace photons are off"


def test_v311_and_live_profile_turn_the_card_on_without_moving_the_stored_flag(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.PHOTON_CLOAK_SETTINGS_MODE == "legacy"
    assert K.photon_cloak_settings_live() is True
    assert K.PHOTON_WAVE_DURATION == 1
    assert K.CLOAK_FAIL_RATE == 0.03
    u, _sid, adj = _world()
    _arm(u)
    assert apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": adj})).ok
    second = apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": adj}))
    assert second.ok is False and second.error == "photon wave still up"
    assert u.players["B"].ship.photon_disabled_ticks == 1

    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.v311_profile() is False
    assert K.PHOTON_CLOAK_SETTINGS_MODE == "legacy"
    assert K.photon_cloak_settings_live() is True
    assert K.PHOTON_WAVE_DURATION == 1


def _world(seed: int = 22501):
    u = generate_universe(GameConfig(seed=seed, universe_size=80, enable_ferrengi=False, enable_planets=False))
    sid = next(s for s in sorted(u.sectors) if s > 10 and u.sectors[s].warps)
    adj = next(w for w in u.sectors[sid].warps if int(w) > 10)
    u.players["A"] = Player(
        id="A", name="Alpha", ship=Ship(holds=40, fighters=200, shields=100),
        sector_id=sid, credits=500_000, alignment=40,
    )
    u.players["B"] = Player(
        id="B", name="Bravo", ship=Ship(holds=40, fighters=50, shields=20),
        sector_id=adj, credits=50_000,
    )
    u.sectors[sid].occupant_ids.append("A")
    u.sectors[adj].occupant_ids.append("B")
    return u, sid, adj


def _arm(u) -> None:
    ship = u.players["A"]
    ship.ship.ship_class = ShipClass.MISSILE_FRIGATE
    ship.ship.photon_missiles = 3
    ship.turns_per_day = 1000
    ship.turns_today = 0


def _move(u, pid: str, dest: int) -> None:
    player = u.players[pid]
    here = u.sectors[player.sector_id]
    if pid in here.occupant_ids:
        here.occupant_ids.remove(pid)
    player.sector_id = int(dest)
    if pid not in u.sectors[dest].occupant_ids:
        u.sectors[dest].occupant_ids.append(pid)


def _link_fed(u, sid: int) -> None:
    if 1 not in u.sectors[sid].warps:
        u.sectors[sid].warps.append(1)
