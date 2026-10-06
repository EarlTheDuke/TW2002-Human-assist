"""PORT_UPGRADE_MODE legacy matches the engine before this slice.

Recorded with tests/fed_legacy_digest.py on e6c7e60 (rules doc on origin 086972d, no engine
change): scripted N3,N2,N1,H, seed 250925, 3 days. flip is only PORT_UPGRADE_MODE.
The same digest on this tree with that flip is 9be955176171eb289630b373.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT_UPGRADE_LEGACY_GOLDEN = "9be955176171eb289630b373"
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
