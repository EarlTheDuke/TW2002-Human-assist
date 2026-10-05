"""QC follow-ups for ship-hardware-v1."""

from __future__ import annotations

import json

import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, build_observation, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import (
    Corporation,
    MineDeployment,
    MineType,
    Player,
    Ship,
    ShipClass,
)
from tw2k.engine.runner import tick_day


def _world(seed: int = 5201):
    u = generate_universe(
        GameConfig(seed=seed, universe_size=80, enable_ferrengi=False, enable_planets=False)
    )
    sid = next(s for s in sorted(u.sectors) if s > 10 and len(u.sectors[s].warps) >= 1)
    adj = u.sectors[sid].warps[0]
    u.players["A"] = Player(
        id="A",
        name="Alpha",
        ship=Ship(holds=40, fighters=200, shields=100),
        sector_id=sid,
        credits=500_000,
    )
    u.players["B"] = Player(
        id="B",
        name="Bravo",
        ship=Ship(holds=40, fighters=50, shields=20),
        sector_id=sid,
        credits=50_000,
    )
    u.sectors[sid].occupant_ids.extend(["A", "B"])
    u.players["A"].known_sectors.update([sid, adj])
    u.players["B"].known_sectors.update([sid, adj])
    return u, sid, adj


@pytest.fixture
def tw(monkeypatch):
    monkeypatch.setattr(K, "HARDWARE_MODE", "tw2002")


def test_cloaked_ship_omitted_from_sector_occupants(tw) -> None:
    u, sid, adj = _world()
    u.players["B"].ship.cloaks = 1
    assert apply_action(u, "B", Action(kind=ActionKind.CLOAK, args={})).ok
    obs = build_observation(u, "A").model_dump(mode="json")
    assert "B" not in (obs.get("sector") or {}).get("occupants", [])
    assert "A" in (obs.get("sector") or {}).get("occupants", [])


def test_corp_other_players_no_cloaked_flag_or_sector(tw) -> None:
    u, sid, adj = _world()
    u.corporations["ZZ"] = Corporation(
        ticker="ZZ",
        name="Z",
        member_ids=["A", "B"],
        founder_id="A",
        ceo_id="A",
    )
    u.players["A"].corp_ticker = "ZZ"
    u.players["B"].corp_ticker = "ZZ"
    u.players["B"].ship.cloaks = 1
    assert apply_action(u, "B", Action(kind=ActionKind.CLOAK, args={})).ok
    obs = build_observation(u, "A").model_dump(mode="json")
    others = {p["id"]: p for p in (obs.get("other_players") or [])}
    assert "B" in others
    assert "sector_id" not in others["B"]
    assert "cloaked" not in others["B"]


def test_cloak_on_does_not_seed_rivals_last_seen(tw) -> None:
    u, sid, adj = _world()
    u.players["B"].ship.cloaks = 1
    assert apply_action(u, "B", Action(kind=ActionKind.CLOAK, args={})).ok
    obs = build_observation(u, "A").model_dump(mode="json")
    rivals = {r["id"]: r for r in (obs.get("rivals") or [])}
    assert "B" in rivals
    assert "last_seen_sector" not in rivals["B"]
    blob = json.dumps(obs.get("recent_events") or [])
    assert "cloak_on" not in blob


def test_photon_wave_expires_after_day_tick(tw) -> None:
    u, sid, adj = _world()
    u.players["A"].ship.ship_class = ShipClass.MISSILE_FRIGATE
    u.players["A"].ship.photon_missiles = 1
    assert apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": adj})).ok
    assert u.sectors[adj].photon_wave_remaining == 1
    tick_day(u)
    assert u.sectors[adj].photon_wave_remaining == 0


def test_tw2002_photon_adjacent_equivalent_to_phase_abc_b2(tw) -> None:
    """phase_abc b2 pins legacy same-sector photon; tw2002 needs adjacent-sector wave."""
    u, sid, adj = _world()
    u.players["A"].ship.ship_class = ShipClass.MISSILE_FRIGATE
    u.players["A"].ship.photon_missiles = 1
    # same-sector player target refused
    r = apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": "B"}))
    assert r.ok is False
    assert u.players["A"].ship.photon_missiles == 1
    r2 = apply_action(u, "A", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": adj}))
    assert r2.ok
    assert u.players["A"].ship.photon_missiles == 0
    assert u.sectors[adj].photon_wave_remaining == K.PHOTON_WAVE_DURATION


def test_lone_armid_does_not_detonate_tw2002(tw) -> None:
    from tw2k.engine.hardware import armid_detonation_hits

    hits, dmg = armid_detonation_hits(1, __import__("random").Random(0))
    assert hits == 0 and dmg == 20


def test_legacy_harness_hides_hardware_verbs() -> None:
    from pathlib import Path

    text = (
        Path(__file__).resolve().parents[1].joinpath("src/tw2k/server/harness.py").read_text(encoding="utf-8")
    )
    assert "if not K.hardware_tw2002():" in text
    assert "cloak" in text and "fire_disruptor" in text and "remove_limpet" in text


def test_carried_photon_into_hostile_armids(tw) -> None:
    u, sid, adj = _world()
    u.players["A"].ship.ship_class = ShipClass.MISSILE_FRIGATE
    u.players["A"].ship.photon_missiles = 2
    u.sectors[adj].fighters = None
    u.sectors[adj].mines = [MineDeployment(owner_id="B", kind=MineType.ARMID, count=4)]
    # Move B out so only mines remain
    u.sectors[sid].occupant_ids = [x for x in u.sectors[sid].occupant_ids if x != "B"]
    u.players["B"].sector_id = adj
    if "B" not in u.sectors[adj].occupant_ids:
        u.sectors[adj].occupant_ids.append("B")
    u.players["A"].turns_today = 5
    u.players["A"].turns_per_day = 40
    apply_action(u, "A", Action(kind=ActionKind.WARP, args={"target": adj}))
    assert u.players["A"].ship.photon_missiles == 0
    assert u.players["A"].turns_today == 40


def test_disruptor_legal_matches_handler_adjacency(tw) -> None:
    u, sid, adj = _world()
    u.players["A"].ship.mine_disruptors = 1
    far = next(s for s in sorted(u.sectors) if s not in (sid, adj) and s not in u.sectors[sid].warps)
    las = {a.kind: a for a in legal_actions(u, "A")}
    choices = (las["fire_disruptor"].params.get("target") or {}).get("choices") or []
    assert adj in choices and far not in choices
