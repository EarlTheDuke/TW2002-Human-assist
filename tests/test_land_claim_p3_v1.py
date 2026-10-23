"""Playtest 3 leftovers (b): under V311_PROFILE=v311 landing does not claim an unowned planet.

v3.11 sets ownership with the planet menu's <O> Claim Ownership (Someguy_TWINSTR.txt
PLANET MENU; EIS PlanetMenu.html; MBBS war manual "you must Claim Ownership of it").
LAND_CLAIM_MODE stays legacy by default: landing claims an empty neutral planet.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player
from tw2k.engine.runner import apply_action
from tw2k.public import manual

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def profile():
    saved = K.V311_PROFILE
    yield
    K.V311_PROFILE = saved


def _setup():
    u = generate_universe(GameConfig(seed=31, universe_size=90, max_days=3, turns_per_day=200,
                                     starting_credits=100_000, enable_ferrengi=False, enable_planets=True))
    pl = next(p for p in u.planets.values() if p.owner_id is None)
    p = Player(id="P1", name="Me", agent_kind="external", sector_id=pl.sector_id, credits=100_000)
    u.players["P1"] = p
    u.sectors[pl.sector_id].occupant_ids.append("P1")
    return u, pl


def test_switch_is_registered_and_legacy_by_default() -> None:
    assert K.LAND_CLAIM_MODE == "legacy"
    assert K.V311_PROFILE_HELPERS["land_claim_explicit_live"][0] == "LAND_CLAIM_MODE"
    assert K.land_claim_explicit_live() is False


def test_legacy_landing_still_claims(profile) -> None:
    u, pl = _setup()
    assert apply_action(u, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": pl.id})).ok
    assert pl.owner_id == "P1"
    la = {x.kind: x for x in legal_actions(u, "P1")}[ActionKind.CLAIM_PLANET]
    assert "claims_neutral" not in (la.params or {})


def test_v311_landing_leaves_it_unowned_until_claim(profile) -> None:
    K.V311_PROFILE = "v311"
    u, pl = _setup()
    assert apply_action(u, "P1", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": pl.id})).ok
    assert u.players["P1"].planet_landed == pl.id
    assert pl.owner_id is None
    la = {x.kind: x for x in legal_actions(u, "P1")}[ActionKind.CLAIM_PLANET]
    assert la.legal, la.reason
    assert la.params["claims_neutral"]["default"] is True
    res = apply_action(u, "P1", Action(kind=ActionKind.CLAIM_PLANET, args={}))
    assert res.ok, res.error
    assert pl.owner_id == "P1" and pl.origin == "claim"


def test_manual_and_cockpit_say_landing_does_not_claim(profile) -> None:
    assert "LAND_CLAIM_MODE" in manual._SWITCH_PLAIN
    js = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")
    body = js[js.index("function landLine(p)"):]
    body = body[:body.index("\n  }\n")]
    assert "claims_neutral" in body and "Landing does not claim it" in body
