"""R-4 v3.11 pins: two scripted matches on the stored defaults (V311_PROFILE "v311").

Every legacy-removal batch must leave both digests byte-identical: a v3.11 game never ran
the deleted path. A digest that moves means the batch changed v3.11 play, which is a bug
unless the batch says why and re-pins on purpose. See tests/v311_digest.py.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests._pin_env import pin_env

ROOT = Path(__file__).resolve().parents[1]

# Recorded on phase2-v311-default (R-4 flip, parent 9dfe6487).
V311_GOLDENS = {
    ("N3,N2,N1,H", 3, 250925): "e9bfe5c4a5f9b16f17898b04",
    ("H,N1,N3,H", 3, 4242): "928c35e031322bbc82c65bf7",
}


@pytest.mark.parametrize(("seats", "days", "seed"), sorted(V311_GOLDENS))
def test_v311_scripted_match_is_unchanged(seats: str, days: int, seed: int) -> None:
    code = (
        "import sys; sys.path[:0] = ['tests', 'src'];"
        "from pathlib import Path; from v311_digest import v311_run_digest;"
        f"print(v311_run_digest(Path('.'), {seats!r}, {days}, {seed}))"
    )
    env = pin_env(PYTHONPATH=str(ROOT / "src"))
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True,
                         timeout=900, check=True)
    assert out.stdout.strip().splitlines()[-1] == V311_GOLDENS[(seats, days, seed)]
