"""Which test files the quick run takes.

The quick run is every unit file (no Chromium) except the slow ones listed
here. The legacy pins are slow too, about a minute each, but they stay in the
quick run: they are the check that default play did not change, and each is
one test, so xdist runs them side by side.

A file goes in SLOW_UNIT_FILES when it takes 15s or more on its own share of
a 12-worker run. Timings below are from the 2026-10-25 run on 6221838e.
The full suite (scripts/run_regression.py) still runs every file.
"""

from __future__ import annotations

from pathlib import Path

from tests._regression import split_files

SLOW_SECONDS = 15.0

SLOW_UNIT_FILES = frozenset({
    "test_beta_playtest2_day_v1.py",  # 58s
    "test_class0_terra_qc_v1.py",  # 50s
    "test_cockpit_ai_seat_v1.py",  # 35s
    "test_cockpit_ai_seat_v3.py",  # 124s
    "test_colonist_units_v1.py",  # 147s
    "test_copilot_phase_h2.py",  # 42s
    "test_copilot_phase_h5.py",  # 26s
    "test_copilot_phase_h6.py",  # 15s
    "test_corpships_v1.py",  # 418s
    "test_day_roll_on_clock_v1.py",  # 25s
    "test_economy_calibration_v1.py",  # 42s
    "test_external_harness_phase1.py",  # 32s
    "test_fidelity_profile_soak_v1.py",  # 262s
    "test_fullgame_fixes_v2.py",  # 67s
    "test_human_agent_phase_h0.py",  # 22s
    "test_human_queue_flush.py",  # 21s
    "test_human_sim_phase_h25.py",  # 27s
    "test_human_ui_phase_h1.py",  # 27s
    "test_leak_guard_v1.py",  # 15s
    "test_lobby_ai_opponents_v1.py",  # 60s
    "test_lobby_tinybox_seats_v1.py",  # 25s
    "test_parity_s1.py",  # 21s
    "test_port_buy_price_anchor_v1.py",  # 379s
    "test_repeatable_runs_v1.py",  # 52s
    "test_run_match_headless.py",  # 17s
    "test_run_scripted_match.py",  # 27s
    "test_seat_bot_n2.py",  # 277s
    "test_seat_bot_n3.py",  # 352s
    "test_seat_bot_s4.py",  # 46s
    "test_seat_drop_pause_v1.py",  # 19s
    "test_selfhost_beta_live_v1.py",  # 24s
    "test_ship_combat_core_v1.py",  # 15s
    "test_ship_fleet_v1.py",  # 52s
    "test_ship_tow_v1.py",  # 62s
    "test_ship_transwarp_v1.py",  # 38s
    "test_turn_cadence_g4.py",  # 29s
    "test_v311_daylen_and_yard_v1.py",  # 20s
})


def is_pin_file(path: Path) -> bool:
    return path.stem.endswith("_v311_pin")


def quick_files(tests_dir: Path) -> list[Path]:
    _browser, unit = split_files(tests_dir)
    return [path for path in unit if path.name not in SLOW_UNIT_FILES]
