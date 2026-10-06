"""PORT_UPGRADE_MODE legacy matches the engine before this slice.

Recorded on the rules-doc commit before the engine change, then rebased onto the
class0-outpost-label tip. Scripted N3,N2,N1,H, seed 250925, 3 days. FED_OUTPOST_MODE
is flipped too: it landed on origin after that recording and must not move the digest.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tests._pin_env import pin_env

ROOT = Path(__file__).resolve().parents[1]
PORT_UPGRADE_LEGACY_GOLDEN = "9be955176171eb289630b373"
PIN_FLIPS = ("PORT_UPGRADE_MODE", "FED_OUTPOST_MODE", "BANK_MODE", "CORP_MODE")


def test_port_upgrade_legacy_is_unchanged():
    code = (
        "import sys; sys.path.insert(0, 'tests'); sys.path.insert(0, 'src');"
        "from pathlib import Path; from fed_legacy_digest import legacy_run_digest;"
        f"print(legacy_run_digest(Path('.'), 'N3,N2,N1,H', 3, 250925, flip={PIN_FLIPS!r}))"
    )
    env = pin_env()
    out = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=900, check=True,
    )
    assert out.stdout.strip().splitlines()[-1] == PORT_UPGRADE_LEGACY_GOLDEN
