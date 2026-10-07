"""planetary-trading-v1: PLANET_TRADE_MODE legacy is byte-identical to the commit before the slice.

Recorded with tests/fed_legacy_digest.py on origin a54fa5b (slice 51 + bots rob-steal-hardware QC fixes, no
PLANET_TRADE_MODE): scripted match N3,N2,N1,H, seed 250925, 3 days, every switch at its default (= this slice with only
PLANET_TRADE_MODE flipped). The digest hashes every observation + prompt text, every action + result, every event
and the end-of-day universe state (PLANETARY_TRADING.md "PLANET_TRADE_MODE pin").
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tests._pin_env import pin_env

ROOT = Path(__file__).resolve().parents[1]
PLANET_TRADE_LEGACY_GOLDEN = "77c7d444a0965a2c40cffcca"  # recorded on 3b8f8e5 (origin; PLANET_TRADE_MODE absent)
# fullgame-fixes-v2 switches and CORPSHIP_MODE are flipped too: their tw2002 defaults change the N3 game.
PIN_FLIPS = ("BOTS_BANK_MODE", "LLM_PLANET_NUDGE_MODE", "LLM_PARITY_MODE", "PLANET_TRADE_MODE", "CORPSHIP_MODE", "PORT_UPGRADE_MODE", "PLANET_DIVIDEND_MODE", "HUNT_MODE",
             "COMBAT_FRAMING_MODE", "SLOW_HULL_HINT_MODE", "COMBAT_SCANNER_MODE", "GENESIS_HULL_MODE",
             "MINE_OVERFLOW_MODE", "FED_OUTPOST_MODE", "BANK_MODE", "CORP_MODE", "ALIEN_MODE",
             "CORP_BOTS_MODE")


def test_planet_trade_legacy_is_unchanged():
    code = (
        "import sys; sys.path.insert(0, 'tests'); sys.path.insert(0, 'src');"
        "from pathlib import Path; from fed_legacy_digest import legacy_run_digest;"
        f"print(legacy_run_digest(Path('.'), 'N3,N2,N1,H', 3, 250925, flip={PIN_FLIPS!r}))"
    )
    env = pin_env()
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True,
                         timeout=900, check=True)
    assert out.stdout.strip().splitlines()[-1] == PLANET_TRADE_LEGACY_GOLDEN
