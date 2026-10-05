#!/usr/bin/env python3
"""Run every planetary scenario lab. No server, no paid call, no ports.

Prints one row per scenario: pass or fail, and the key line from that table.
Exits 1 when any scenario fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from planetary_scenario_lab import (  # noqa: E402
    DEFAULT_ATTACKER_SHIELDS,
    DEFAULT_CITADEL_LEVEL,
    DEFAULT_SEEDS,
    format_atmosphere_table,
    format_corp_table,
    format_destroy_table,
    format_gift_table,
    format_hazard_table,
    format_interdict_table,
    format_markdown,
    format_photon_table,
    format_production_table,
    format_quasar_table,
    format_transporter_table,
    format_transwarp_table,
    run_grid,
)

import tw2k.engine.constants as K  # noqa: E402


def _siege() -> str:
    cells = run_grid(seeds=DEFAULT_SEEDS)
    return format_markdown(
        cells,
        seeds=DEFAULT_SEEDS,
        citadel_level=DEFAULT_CITADEL_LEVEL,
        attacker_shields=DEFAULT_ATTACKER_SHIELDS,
    )


# Each needle is one data line the lab already prints. A rules change that
# moves that line fails this script.
SCENARIOS: tuple[tuple[str, object, str], ...] = (
    ("siege", _siege, "| 0 | 0 | 100 | 100.0% | 0.0% | 0.0% | 100.0 |"),
    ("production", format_production_table, "| M | fuel_ore | 33 | 333 |"),
    ("hazards", format_hazard_table, "| 100 | 0 | 0 | 100.0% | 0.0% | 66.7% |"),
    ("quasar", format_quasar_table, "| 10% of 10000 | 3 | 10 | 10000 | 0 | 1000 | 333 | 9000 | 667 | 0 |"),
    (
        "atmosphere",
        format_atmosphere_table,
        "| both shots, shields already down | 0 | 10000 | 0 | 2 | 2000, 1800 | 8100 | no |",
    ),
    ("photon", format_photon_table, "| no photon | 3 | 0 | no | no | 333 | 9000 |"),
    ("interdict", format_interdict_table, "| 500 fuel | 6 | 500 | yes | 40 | 0 | 0 |"),
    ("transwarp", format_transwarp_table, "| 2 hops, 1000 fuel | 4 | 1000 | yes | yes | 42 | 200 |"),
    ("transporter", format_transporter_table, "| buy | 60000 | 0 | yes | 10000 | 0 | 40 |"),
    ("gift", format_gift_table, "| 2 | 0 | 0 | 0 | 0 | planet_id,from,to |"),
    # EXPERIENCE_ALIGNMENT.md x7: tw2002 charges -1 when the planet goes, nothing for the colonists.
    ("destroy", format_destroy_table,
     "| kill | yes | yes | yes | 0 | " + ("0" if K.rank_tw2002() else "-50") + " | 40 |"),
    ("corp", format_corp_table, "| leave planet_transwarp | D | ZZ | no | 0 | 0 |"),
)


def main() -> int:
    failed = 0
    print("| Scenario | Result | Key |")
    print("|---|---|---|")
    for name, fn, needle in SCENARIOS:
        try:
            text = fn()
        except Exception as exc:
            failed += 1
            print(f"| {name} | fail | {type(exc).__name__}: {exc} |")
            continue
        if needle in text:
            print(f"| {name} | pass | {needle} |")
        else:
            failed += 1
            print(f"| {name} | fail | missing {needle} |")
    print(f"planetary_lab_all: {'PASS' if failed == 0 else f'{failed} FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
