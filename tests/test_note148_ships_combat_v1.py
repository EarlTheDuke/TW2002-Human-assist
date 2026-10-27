"""NOTE 148. Two ships-and-combat rows whose v3.11 numbers are known.

Each row stays on the legacy rule while its switch is off, including when
V311_PROFILE is "1". The switch, or V311_PROFILE "v311" alone, uses the
printed figure.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.combat import _resolve_ship_combat_attacker_npc
from tw2k.engine.models import (
    FerrengiShip,
    GameConfig,
    MineDeployment,
    MineType,
    Player,
    Sector,
    Ship,
    ShipClass,
    Universe,
)
from tw2k.engine.runner import apply_action
from tw2k.public.manual import render

pytestmark = pytest.mark.legacy_profile


def test_ferrengi_attack_fails_off_and_passes_on(monkeypatch) -> None:
    """GAP 8.1. FERRSPEC: an Assault Trader sends 1,000 of 3,000 at odds 1.0.

    20,000 defending fighters at 1.0 lose 1,000. The three-round roll spends
    the whole stack and the Ferrengi does not walk away with 2,000 fighters.
    """
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.ferrengi_attack_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    assert K.ferrengi_fighters_per_attack(K.FERRENGI_HULL_ASSAULT) == 1_000
    assert K.ferrengi_fighters_per_attack(K.FERRENGI_HULL_CRUISER) == 2_000
    assert K.ferrengi_fighters_per_attack(K.FERRENGI_HULL_DREAD) == 5_000

    def scene():
        universe = Universe(
            config=GameConfig(seed=14801, universe_size=2, enable_ferrengi=False),
            sectors={2: Sector(id=2, warps=[])},
        )
        victim = Player(
            id="V", name="Vera", sector_id=2, credits=0,
            ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=20_000, shields=0),
        )
        ferr = FerrengiShip(
            id="F1", name="Assault", sector_id=2, aggression=3,
            fighters=3_000, shields=200, hull=K.FERRENGI_HULL_ASSAULT,
        )
        universe.players["V"] = victim
        _resolve_ship_combat_attacker_npc(universe, ferr, victim)
        return ferr, victim

    ferr, victim = scene()
    assert ferr.alive is False
    assert ferr.fighters == 0
    assert victim.ship.fighters != 19_000

    monkeypatch.setattr(K, "FERRENGI_ATTACK_MODE", "v311")
    ferr, victim = scene()
    assert ferr.alive is True
    assert ferr.fighters == 2_000
    assert ferr.shields == 200
    assert victim.ship.fighters == 19_000
    assert victim.ship.shields == 0
    assert victim.deaths == 0

    monkeypatch.setattr(K, "FERRENGI_ATTACK_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.FERRENGI_ATTACK_MODE == "legacy"
    assert K.FERRENGI_ODDS_MODE == "legacy"
    # The profile also turns on Bible odds: 2,000 fighters at 1.2, so 1,000 remain.
    ferr, victim = scene()
    assert ferr.alive is True
    assert ferr.fighters == 1_000
    assert victim.ship.fighters == 17_600


def test_photon_limpet_fails_off_and_passes_on(monkeypatch) -> None:
    """GAP 4.10. S1 keeps a limpet on the wave. Armids stay quiet either way."""
    monkeypatch.setattr(K, "V311_PROFILE", "1")
    assert K.photon_limpet_live() is False
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")

    def scene():
        sectors = {
            11: Sector(id=11, warps=[12]),
            12: Sector(
                id=12, warps=[11], photon_wave_remaining=1,
                mines=[
                    MineDeployment(owner_id="O", kind=MineType.LIMPET, count=1),
                    MineDeployment(owner_id="O", kind=MineType.ARMID, count=2),
                ],
            ),
        }
        universe = Universe(
            config=GameConfig(seed=14802, universe_size=12, enable_ferrengi=False, enable_planets=False),
            sectors=sectors,
        )
        pilot = Player(
            id="A", name="Ada", sector_id=11, credits=0,
            ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=20, shields=500),
            turns_per_day=40,
        )
        universe.players["A"] = pilot
        universe.sectors[11].occupant_ids.append("A")
        result = apply_action(universe, "A", Action(kind=ActionKind.WARP, args={"target": 12}))
        return universe, pilot, result

    universe, pilot, result = scene()
    assert result.ok is True
    assert pilot.sector_id == 12
    assert universe.limpets == {}
    assert pilot.ship.shields == 500
    kinds = {mine.kind: mine.count for mine in universe.sectors[12].mines}
    assert kinds[MineType.LIMPET] == 1
    assert kinds[MineType.ARMID] == 2

    monkeypatch.setattr(K, "PHOTON_LIMPET_MODE", "v311")
    universe, pilot, result = scene()
    assert result.ok is True
    assert "O:A" in universe.limpets
    assert pilot.ship.shields == 500
    kinds = {mine.kind: mine.count for mine in universe.sectors[12].mines}
    assert MineType.LIMPET not in kinds
    assert kinds[MineType.ARMID] == 2

    monkeypatch.setattr(K, "PHOTON_LIMPET_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.PHOTON_LIMPET_MODE == "legacy"
    universe, pilot, result = scene()
    assert result.ok is True
    assert "O:A" in universe.limpets
    assert kinds_left(universe)[MineType.ARMID] == 2


def kinds_left(universe: Universe) -> dict:
    return {mine.kind: mine.count for mine in universe.sectors[12].mines}


def test_manual_names_the_two_switches() -> None:
    page = render("Galaxy War Command")
    assert "a Ferrengi attack uses three rolls and can send every fighter it has." in page
    assert "a limpet does not attach while that wave is up." in page
