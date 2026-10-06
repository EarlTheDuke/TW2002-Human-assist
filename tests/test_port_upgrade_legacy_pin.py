"""PORT_UPGRADE_MODE legacy matches the engine before this slice.

Recorded with tests/fed_legacy_digest.py on f769d39 (rules doc only, no engine change):
scripted N3,N2,N1,H, seed 250925, 3 days. flip is only PORT_UPGRADE_MODE: every other
mode already existed on that commit and stays at its default.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT_UPGRADE_LEGACY_GOLDEN = "2bfc607c3338e87690bcc253"
PIN_FLIPS = ("PORT_UPGRADE_MODE",)


def test_port_upgrade_legacy_is_unchanged():
    code = (
        "import sys; sys.path.insert(0, 'tests'); sys.path.insert(0, 'src');"
        "from pathlib import Path; from fed_legacy_digest import legacy_run_digest;"
        f"print(legacy_run_digest(Path('.'), 'N3,N2,N1,H', 3, 250925, flip={PIN_FLIPS!r}))"
    )
    env = dict(os.environ, PYTHONHASHSEED="0")
    out = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=900, check=True,
    )
    assert out.stdout.strip().splitlines()[-1] == PORT_UPGRADE_LEGACY_GOLDEN
