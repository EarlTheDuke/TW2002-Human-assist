"""GAP 12.4. Printed Extern and midnight jobs, against runner.tick_day.

Cabal glossary, the docs-wiki Glossary, cabal twgs.html, the MBBS manual,
and Gypsy name the jobs. Each one already runs, or it stays behind a switch
that already exists. INACTIVE_USER_MODE and INACTIVITY_TIMEOUT_MODE stay off.
No new switch.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import tw2k.engine.constants as K
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.capture import _pods_used_today
from tw2k.engine.models import Player
from tw2k.engine.runner import apply_action, tick_day
from tw2k.engine.ship_exit import _colonist_alignment
from tw2k.engine.tavern import _bump_attempts

ROOT = Path(__file__).resolve().parents[1]

_TICK_HELPERS = (
    "_note_inactive_users",
    "extern_corp_step",
    "extern_sweep",
    "regen_terra",
    "extern_repossess",
    "run_tows",
    "regenerate_ports",
    "clear_all_busts",
    "tick_photon_waves",
    "tick_cloak_fails",
    "tick_navhaz",
    "alien_day_step",
    "_advance_planets",
    "_complete_citadels",
    "advance_construction",
    "_rebuild_special_ports",
    "_planet_collisions",
    "collect_daily_tax",
)

_QUOTES = {
    "docs/reference/tw2002/cabal_strategy_site/glossary.html": (
        "Empty ships in Fedspace are repo'd.",
        "Players and Corps timeout.",
        "day are allowed back in.",
        "Hold, Fig, and Shield prices change at Class 0 and Class 9 ports.",
    ),
    "docs/reference/tw2002/classictw_docs_wiki/Glossary.html": (
        "7) Reset Grimy Trader Curse.",
        "8) Recover deaths (2 pods).",
        "9) Reset Jettison Collies.",
        "10) Reset Alignment loss for breaking into another corp.",
        "13) Planets in overloaded sectors collide.  Only 2 planets collide per extern.",
        "5) Underground wrong passwords resets.",
    ),
    "docs/reference/tw2002/cabal_strategy_site/twgs.html": (
        "Days until an inactive user is deleted: 30",
        "Inactivity Timeout : 14400 Sec",
        "NavHaz Dispersion: 100%",
    ),
    "docs/reference/tw2002/stardock_manuals_and_text_docs/Someguy_MBBS_manual.txt": (
        "of 2 pods per day, after that, you are dead until tomorrow.",
        "the Feds during the nightly cleanup.",
    ),
    "docs/reference/tw2002/stardock_manuals_and_text_docs/Gypsy_Big_Dummies_Guide.html": (
        "Too many ships will get you towed when Extern runs",
    ),
}


def _world():
    universe = generate_universe(GameConfig(
        seed=124, universe_size=40, max_days=30, turns_per_day=40,
        starting_credits=50_000, enable_ferrengi=False, enable_planets=True,
    ))
    player = Player(id="P9", name="P9", sector_id=1, credits=50_000, alignment=20)
    player.turns_per_day = 1000
    player.turns_today = 0
    universe.players["P9"] = player
    universe.sectors[1].occupant_ids.append("P9")
    return universe, player


def test_printed_sources_still_name_these_jobs() -> None:
    for rel, quotes in _QUOTES.items():
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        for quote in quotes:
            assert quote in text, quote


def test_tick_day_calls_the_printed_jobs() -> None:
    source = inspect.getsource(tick_day)
    missing = [name for name in _TICK_HELPERS if name not in source]
    assert missing == []
    assert "universe.day += 1" in source


def test_day_stamp_resets_curse_jettison_password_pods_and_breakin() -> None:
    universe, player = _world()
    day = int(universe.day)
    player.grimy_curse_day = day
    player.jettison_day = day
    player.jettison_colonists = 250
    player.ug_attempts_day = day
    player.ug_attempts = 4
    player.pods_day = day
    player.pods_today = 2
    player.corp_breakins_today = 3
    refused = apply_action(universe, "P9", Action(kind=ActionKind.GRIMY_CURSE, args={}))
    assert refused.ok is False and refused.error == "you already cursed him today"

    tick_day(universe)
    assert int(universe.day) == day + 1
    assert player.corp_breakins_today == 0
    assert _pods_used_today(universe, player) == 0
    assert _bump_attempts(player, int(universe.day)) == 1
    before = int(player.alignment)
    _colonist_alignment(universe, player, 1)
    assert player.jettison_day == int(universe.day)
    assert player.jettison_colonists == 1
    assert int(player.alignment) == before - 1
    cursed = apply_action(universe, "P9", Action(kind=ActionKind.GRIMY_CURSE, args={}))
    assert cursed.ok is True


def test_inactive_switches_stay_off_and_a_quiet_trader_stays() -> None:
    assert K.INACTIVE_USER_MODE == "legacy"
    assert K.inactive_user_live() is False
    assert K.INACTIVITY_TIMEOUT_MODE == "legacy"
    assert K.inactivity_timeout_live() is False
    assert K.INACTIVE_USER_DAYS == 30
    assert K.INACTIVITY_TIMEOUT_S == 14_400
    assert K.CLASS0_EXTERN_PLANET_RULE == "keep"
    assert K.NAVHAZ_DISPERSION_PER_DAY == 3
    assert K.PODS_PER_DAY == 2
    universe, player = _world()
    player.last_action_at = 0.0
    player.alive = True
    tick_day(universe)
    assert player.alive is True
    assert player.inactive_deleted is False


def test_grade_is_match_behind_flag_and_partial_is_only_2_15() -> None:
    v6 = (ROOT / "docs/plans/gap-map-refresh-v6.md").read_text(encoding="utf-8")
    every = v6.split("## Every row", 1)[1]
    row = next(line for line in every.splitlines() if line.startswith("12.4 "))
    assert row.startswith("12.4 Match-behind-flag")
    assert "| Match-behind-flag | 17 | 94 |" in v6
    assert "| Partial | 53 | 1 |" in v6
    assert "12.4 Partial" not in every
    remaining = (ROOT / "docs/plans/V311_REMAINING.md").read_text(encoding="utf-8")
    assert "169 of 171" in remaining
    assert "2.15 is the only counted Partial." in remaining
    for rel in ("docs/plans/GAP_MAP.md", "docs/reference/tw2002/GAP_MAP.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        line = next(item for item in text.splitlines() if item.startswith("| 12.4 Nightly Extern"))
        assert "| Match-behind-flag |" in line
