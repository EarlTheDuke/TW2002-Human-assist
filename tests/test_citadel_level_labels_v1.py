"""Citadel names match one list. Costs, the garrison gift, and siege math stay."""

from __future__ import annotations

import re
from pathlib import Path

from tw2k.agents.prompts import _MATCH_PROMPT_FULL
from tw2k.engine.constants import CITADEL_PERK, CITADEL_TIER_COST

ROOT = Path(__file__).resolve().parents[1]
NAMES = [
    "Treasury",
    "Combat Control Computer",
    "Quasar cannon",
    "Planet TransWarp",
    "Planetary shields",
    "Interdictor",
]


def test_perk_list_is_the_original_order() -> None:
    assert [level for level, _, _ in CITADEL_PERK] == [1, 2, 3, 4, 5, 6]
    assert [name for _, name, _ in CITADEL_PERK] == NAMES
    assert "deposit and withdraw" in CITADEL_PERK[0][2]
    assert "2% daily interest" in CITADEL_PERK[0][2]
    assert "hostile warp" in CITADEL_PERK[2][2]
    for i, (_, _, perk) in enumerate(CITADEL_PERK):
        if i in (0, 2):
            assert "not yet in this game" not in perk
        else:
            assert "not yet in this game" in perk
    garrison = CITADEL_PERK[1][2]
    assert "garrison of 1000 fighters and 250 shields per level" in garrison
    assert CITADEL_TIER_COST == [
        (5_000, 1_000, 1),
        (10_000, 2_000, 1),
        (20_000, 4_000, 2),
        (40_000, 8_000, 2),
        (80_000, 16_000, 3),
        (160_000, 32_000, 4),
    ]


def test_js_titles_match_the_constants_list() -> None:
    text = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    start = text.index("const CITADEL_TIERS = [")
    block = text[start:text.index("];", start)]
    perks = re.findall(r'perk: "([^"]*)"', block)
    costs = re.findall(r"cr:\s*(\d+),\s*col:\s*(\d+),\s*days:\s*(\d+)", block)
    assert perks == [perk for _, _, perk in CITADEL_PERK]
    assert [(int(cr), int(col), int(days)) for cr, col, days in costs] == list(CITADEL_TIER_COST)
    assert "unlocks Genesis + interdictor" not in text
    assert "Basic fortifications" not in text


def test_prompt_and_design_match_the_constants_list() -> None:
    design = (ROOT / "docs" / "DESIGN.md").read_text(encoding="utf-8")
    planets = (ROOT / "src" / "tw2k" / "engine" / "planets.py").read_text(encoding="utf-8")
    for _, name, perk in CITADEL_PERK:
        assert perk in _MATCH_PROMPT_FULL
        assert perk in design
        assert name in design
    assert "sector-wide weapon" not in _MATCH_PROMPT_FULL
    assert "only Citadel L4 transwarp" not in _MATCH_PROMPT_FULL
    assert "L2 = Quasar" not in planets
    assert "if planet.citadel_level >= 2:" in planets
    assert "planet.fighters = max(planet.fighters, 1000 * planet.citadel_level)" in planets
    assert "planet.shields = max(planet.shields, 250 * planet.citadel_level)" in planets
