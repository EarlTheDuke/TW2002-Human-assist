"""Outsiders in a sector do not read another planet's garrison numbers."""

from __future__ import annotations

from pathlib import Path

from tests.test_phase_abc import _make_universe
from tw2k.agents.prompts import SYSTEM_PROMPT, get_system_prompt
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Commodity, Planet, PlanetClass
from tw2k.engine.observation import build_observation

SECTOR = 120
HIDDEN = ("fighters", "shields", "treasury", "stockpile")
KEPT = ("id", "name", "class", "owner_id", "corp_ticker", "citadel_level")
CONTESTED_GATE = "(p.planet_id.contested || []).includes(Number(vals.planet_id))"
WARNING = 'txt += " · WARNING: defended hostile planet - landing means citadel combat";'


def _stand(u, player) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = SECTOR
    player.planet_landed = None
    if player.id not in u.sectors[SECTOR].occupant_ids:
        u.sectors[SECTOR].occupant_ids.append(player.id)


def _plant(u, *, owner: str | None, corp: str | None, fighters: int, shields: int = 87) -> Planet:
    planet = Planet(
        id=77021, sector_id=SECTOR, name="FogHold",
        class_id=PlanetClass.M, owner_id=owner, corp_ticker=corp,
        fighters=fighters, shields=shields,
        citadel_level=2, citadel_target=2, treasury=6543,
    )
    planet.stockpile[Commodity.FUEL_ORE] = 19
    planet.colonists[Commodity.ORGANICS] = 40
    u.planets[planet.id] = planet
    u.sectors[SECTOR].planet_ids.append(planet.id)
    return planet


def _brief(u, pid: str) -> dict:
    obs = build_observation(u, pid)
    return next(p for p in obs.sector["planets"] if p["id"] == 77021)


def _contested(u, pid: str) -> list[int]:
    land = next(la for la in legal_actions(u, pid) if la.kind == "land_planet")
    return list(land.params["planet_id"]["contested"])


def test_outsider_loses_garrison_numbers_and_keeps_the_contested_flag() -> None:
    u, (outsider, owner, mate) = _make_universe(seed=77021)
    planet = _plant(u, owner=owner.id, corp="QQ", fighters=4321)
    _stand(u, outsider)
    _stand(u, owner)
    mate.corp_ticker = "QQ"
    _stand(u, mate)

    hidden = _brief(u, outsider.id)
    for key in HIDDEN:
        assert key not in hidden, key
    for key in KEPT:
        assert key in hidden, key
    assert hidden["owner_id"] == owner.id
    assert hidden["corp_ticker"] == "QQ"
    assert hidden["citadel_level"] == 2
    assert hidden["colonists_total"] == 40
    assert 4321 not in hidden.values()
    assert _contested(u, outsider.id) == [planet.id]

    shown = _brief(u, owner.id)
    assert shown["fighters"] == 4321
    assert shown["military_reaction_pct"] == 0
    assert shown["shields"] == 87
    assert shown["treasury"] == 6543
    assert shown["stockpile"]["fuel_ore"] == 19

    shared = _brief(u, mate.id)
    assert shared["fighters"] == 4321
    assert shared["treasury"] == 6543
    assert _contested(u, mate.id) == []


def test_shields_only_is_contested_without_showing_the_numbers() -> None:
    u, (outsider, *_) = _make_universe(seed=77022)
    planet = _plant(u, owner="B", corp="QQ", fighters=0, shields=87)
    _stand(u, outsider)
    hidden = _brief(u, outsider.id)
    assert "shields" not in hidden and "fighters" not in hidden
    assert "military_reaction_pct" not in hidden
    assert _contested(u, outsider.id) == [planet.id]


def test_empty_hostile_planet_is_not_contested() -> None:
    u, (outsider, *_) = _make_universe(seed=77023)
    _plant(u, owner="B", corp="QQ", fighters=0, shields=0)
    _stand(u, outsider)
    hidden = _brief(u, outsider.id)
    assert "military_reaction_pct" not in hidden
    assert _contested(u, outsider.id) == []


def test_prompts_and_cockpit_warning_use_the_contested_flag() -> None:
    assert "only for a planet you own or share a corp with" in SYSTEM_PROMPT
    js = (Path(__file__).resolve().parents[1] / "web" / "bot.js").read_text(encoding="utf-8")
    assert CONTESTED_GATE in js
    assert WARNING in js


def test_minimal_prompt_names_the_same_omission(monkeypatch) -> None:
    monkeypatch.setenv("TW2K_HINT_LEVEL", "minimal")
    text = get_system_prompt()
    assert "only for a planet you own or share a corp with" in text
    assert "land_planet contested" in text
