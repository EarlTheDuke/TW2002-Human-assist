"""NOTE 97. The reference reads the engine tables, and the two unsettled switches stay put.

No new helper row. Haggle stays +1/+2. A rename stays 5,000 credits and 30 characters.
Turns on a rename were not measured. The handler stays credit-only.
StarDock is labelled Class 9 only while the live class map is on. Its stored id stays 8.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.models import Player, PortClass, Ship
from tw2k.public.manual import render
from tw2k.server.reference import game_reference, stardock_class_label

pytestmark = pytest.mark.legacy_profile

ROOT = Path(__file__).resolve().parents[1]


def _section(ref: dict, sid: str) -> dict:
    return next(row for row in ref["sections"] if row["id"] == sid)


def test_note97_adds_no_helper_row() -> None:
    """Planet classes and the StarDock label do not add a profile helper.

    Later notes may extend the table. This slice does not own a row, so the
    test does not pin the last row number.
    """
    text = (ROOT / "docs/plans/v311-profile-v1.md").read_text()
    rows = re.findall(r"^\| (\d+) \| `([^`]+)` \| `([^`]+)` \| ([^|]+)\|", text, re.M)
    assert rows
    owned = [switch for _num, switch, _helper, why in rows if re.search(r"NOTE 97\b", why)]
    assert owned == []
    switches = {switch for _helper, (switch, _why) in K.V311_PROFILE_HELPERS.items()}
    assert "COMPUTER_HELPERS_MODE" not in switches


def test_planet_catalog_and_citadel_rows_read_the_engine() -> None:
    assert K.CITADEL_CLASS_COSTS["M"][0] == (1000, 300, 200, 250, 4)
    ref = game_reference()
    classes = _section(ref, "planet_classes")["rows"]
    assert [row["letter"] for row in classes] == list(K.PLANET_CLASS_NAMES)
    for row in classes:
        letter = row["letter"]
        ratio = K.PLANET_PROD_PER_UNIT[letter]
        assert row["name"] == K.PLANET_CLASS_NAMES[letter]
        assert row["per_unit"] == {
            "fuel_ore": int(ratio[0]),
            "organics": int(ratio[1]),
            "equipment": int(ratio[2]),
        }
        assert row["max_colonists"] == int(K.PLANET_MAX_COLONISTS[letter])
        assert len(row["citadel"]) == int(K.CITADEL_LEVELS)
        for level in row["citadel"]:
            colonists, fuel, organics, equipment, days = K.citadel_class_cost(letter, level["level"])
            assert (level["colonists"], level["fuel_ore"], level["organics"], level["equipment"], level["days"]) == (
                int(colonists), int(fuel), int(organics), int(equipment), int(days),
            )
    citadel = _section(ref, "citadel_tables")["rows"]
    expect = []
    for letter in K.PLANET_CLASS_NAMES:
        for level in range(1, int(K.CITADEL_LEVELS) + 1):
            colonists, fuel, organics, equipment, days = K.citadel_class_cost(letter, level)
            expect.append(
                f"colonists {int(colonists)}, fuel {int(fuel)}, organics {int(organics)}, "
                f"equipment {int(equipment)}, days {int(days)}"
            )
    assert [row["value"] for row in citadel] == expect


def test_combat_flee_haggle_and_experience_read_the_engine() -> None:
    ref = game_reference()
    combat = {row["name"]: row["value"] for row in _section(ref, "combat_odds")["rows"]}
    assert combat["Planet offense"] == f"{int(K.PLANET_OFFENSE_ODDS)} to 1"
    assert combat["Planet defense"] == f"{int(K.PLANET_DEFENSE_ODDS)} attacker fighters per planet fighter"
    assert combat["Planet shields"] == f"{int(K.PLANET_SHIELD_ODDS)} attacker fighters per shield"
    for spec in K.ship_specs().values():
        odds = spec.get("offensive_odds")
        if odds is None:
            continue
        name = spec.get("display_name")
        assert combat[name] == f"{odds} to 1, {int(spec.get('fighters_per_attack') or 0)} fighters per attack"
    flee = {row["name"]: row["value"] for row in _section(ref, "flee_rule")["rows"]}
    assert flee["Flee ratio"] == K.COMBAT_FLEE_RATIO
    assert flee["Flee penalty"] == int(K.FLEE_PENALTY_TURNS)
    bands = {row["name"]: row["value"] for row in _section(ref, "haggle_bands")["rows"]}
    assert bands["Good haggle"] == K.HAGGLE_EXP_GOOD == 1
    assert bands["Great haggle"] == K.HAGGLE_EXP_GREAT == 2
    awards = {row["name"]: row["value"] for row in _section(ref, "exp_alignment")["rows"]}
    assert awards["trade"] == int(K.xp_award("trade"))
    assert awards["deploy_genesis"] == int(K.xp_award("deploy_genesis"))
    assert awards["destroy_port"] == int(K.xp_award("destroy_port"))
    assert awards["Kill experience share"] == K.KILL_EXP_SHARE
    assert awards["Kill alignment share"] == K.KILL_ALIGN_SHARE
    assert awards["Daily alignment"] == int(K.DAILY_ALIGNMENT)
    assert awards["Genesis alignment"] == int(K.GENESIS_ALIGNMENT)
    assert awards["Combat experience divisor"] == ", ".join(
        f"{name} {int(num)}" for name, num in K.COMBAT_EXP_DIVISOR.items()
    )


def test_stardock_label_is_9_only_on_the_live_map(monkeypatch) -> None:
    assert K.PORT_CLASS_MAP_MODE == "legacy"
    assert int(PortClass.STARDOCK) == 8
    assert stardock_class_label() == 8
    legacy_ref = game_reference()
    assert legacy_ref["stardock_class"] == 8
    legacy_rules = next(row["body"] for row in legacy_ref["sections"] if row["id"] == "rules")
    assert "StarDock is shown as Class 8." in legacy_rules
    assert "Its stored id stays 8." in legacy_rules
    legacy = render("Trade Wars")
    assert "Its stored class id is 8." in legacy
    assert "shown as Class 9" not in legacy
    monkeypatch.setattr(K, "PORT_CLASS_MAP_MODE", "live")
    assert int(PortClass.STARDOCK) == 8
    assert stardock_class_label() == 9
    live_ref = game_reference()
    assert live_ref["stardock_class"] == 9
    live_rules = next(row["body"] for row in live_ref["sections"] if row["id"] == "rules")
    assert "StarDock is shown as Class 9." in live_rules
    assert "Its stored id stays 8." in live_rules
    live = render("Trade Wars")
    assert "shown as Class 9" in live
    assert "stored id stays 8" in live
    assert "Class 9 in the trade book is still the built SSS port" in live


def test_haggle_amounts_and_rename_cost_stay(monkeypatch) -> None:
    assert K.HAGGLE_EXP_MODE == "legacy"
    assert K.HAGGLE_EXP_GOOD == 1
    assert K.HAGGLE_EXP_GREAT == 2
    assert K.SHIP_RENAME_MODE == "legacy"
    assert K.SHIP_RENAME_COST == 5_000
    assert K.SHIP_RENAME_NAME_MAX == 30
    monkeypatch.setattr(K, "SHIP_RENAME_MODE", "live")
    universe = generate_universe(
        GameConfig(seed=4, universe_size=20, max_days=5, enable_planets=False, enable_ferrengi=False)
    )
    player = Player(id="P1", name="Trader", ship=Ship(name="Unnamed"), credits=20_000, experience=0)
    player.sector_id = K.STARDOCK_SECTOR
    universe.players["P1"] = player
    universe.sectors[K.STARDOCK_SECTOR].occupant_ids.append("P1")
    long_name = "A" * 31
    refused = apply_action(universe, "P1", Action(kind=ActionKind.SHIP_RENAME, args={"name": long_name}))
    assert refused.ok is False
    assert "30" in (refused.error or "")
    assert player.credits == 20_000
    done = apply_action(universe, "P1", Action(kind=ActionKind.SHIP_RENAME, args={"name": "A" * 30}))
    assert done.ok, done.error
    assert done.turns_spent == 0
    assert player.ship.name == "A" * 30
    assert player.credits == 20_000 - 5_000
