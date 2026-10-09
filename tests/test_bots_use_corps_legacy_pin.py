"""CORP_BOTS_MODE legacy matches the engine before this slice.

Recorded with tests/fed_legacy_digest.py on 423d502 (no CORP_BOTS_MODE): scripted
N3,N2,N1,H, seed 250925, 3 days. CORP_BOTS_MODE is named so the pin still matches
after the mode exists. LLM_ROUTE_NOTICE and LLM_NEW_DAY_GOAL_NOTICE are bools,
not modes, so this pin sets both False before the digest.
The 10-day N3,N3,N2,N2,N1,H seed 250925 digest with the same flips, outside the
suite, is 221826d9bd9a6a6c85668224.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tests._pin_env import pin_env

ROOT = Path(__file__).resolve().parents[1]
BOTS_USE_CORPS_LEGACY_GOLDEN = "9b607d3dae940c0b1a69f6d7"
PIN_FLIPS = (
    "BOTS_TAVERN_MODE", "H_RECOVERY_MODE", "CORP_FIX_MODE", "BOTS_WAR_MODE", "TAVERN_MODE", "BOTS_BANK_MODE", "LLM_PLANET_NUDGE_MODE",
    "LLM_PARITY_MODE",
    "CORP_BOTS_MODE",
    "ALIEN_MODE",
    "CORP_MODE",
    "BANK_MODE",
    "PORT_UPGRADE_MODE",
    "FED_OUTPOST_MODE",
    "CORPSHIP_MODE",
    "PLANET_TRADE_MODE",
    "CAPTURE_MODE",
    "PLANET_DIVIDEND_MODE",
    "HUNT_MODE",
    "COMBAT_FRAMING_MODE",
    "SLOW_HULL_HINT_MODE",
    "COMBAT_SCANNER_MODE",
    "GENESIS_HULL_MODE",
    "MINE_OVERFLOW_MODE",
)


def test_bots_use_corps_legacy_is_unchanged():
    code = (
        "import sys; sys.path.insert(0, 'tests'); sys.path.insert(0, 'src');"
        "import tw2k.engine.constants as K;"
        "K.LLM_ROUTE_NOTICE = False; K.LLM_NEW_DAY_GOAL_NOTICE = False;"
        "from pathlib import Path; from fed_legacy_digest import legacy_run_digest;"
        f"print(legacy_run_digest(Path('.'), 'N3,N2,N1,H', 3, 250925, flip={PIN_FLIPS!r}))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=pin_env(),
        capture_output=True, text=True, timeout=900, check=True,
    )
    assert out.stdout.strip().splitlines()[-1] == BOTS_USE_CORPS_LEGACY_GOLDEN
