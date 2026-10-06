"""QC slice 55: the legacy digest pins cannot be moved by the caller's environment or global state.

TW2K_HINT_LEVEL=minimal in the parent shell moved the port-upgrade pin from 9be95517 to 924564e9
before the pins got a scrubbed environment (tests/_pin_env.py) and legacy_run_digest became hermetic.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import tw2k.engine.constants as K
from tests import fed_legacy_digest as FLD
from tests._pin_env import pin_env, scrubbed_environ
from tests.test_port_upgrade_legacy_pin import PIN_FLIPS, PORT_UPGRADE_LEGACY_GOLDEN

ROOT = Path(__file__).resolve().parents[1]


def test_pin_env_drops_every_tw2k_variable(monkeypatch):
    monkeypatch.setenv("TW2K_HINT_LEVEL", "minimal")
    monkeypatch.setenv("TW2K_PORT_MATCH", "1")
    monkeypatch.setenv("tw2k_lower", "x")
    monkeypatch.setenv("PYTHONHASHSEED", "123")
    env = pin_env(EXTRA="1")
    assert not any(k.upper().startswith("TW2K_") for k in env)
    assert env["PYTHONHASHSEED"] == "0" and env["EXTRA"] == "1"
    assert "PATH" in env or "Path" in env
    assert scrubbed_environ({"TW2K_A": "1", "B": "2"}) == {"B": "2"}


def test_no_pin_subprocess_inherits_the_raw_environment():
    offenders = []
    for path in sorted((ROOT / "tests").glob("*.py")):
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8")
        if "PYTHONHASHSEED" in text and "dict(os.environ" in text:
            offenders.append(path.name)
    assert offenders == []


def test_legacy_run_digest_hides_tw2k_vars_and_restores_modes(monkeypatch):
    monkeypatch.setenv("TW2K_HINT_LEVEL", "minimal")
    seen = {}

    def fake(root, seats, days, seed, flip):
        import os
        seen["env"] = sorted(k for k in os.environ if k.startswith("TW2K_"))
        K.PORT_UPGRADE_MODE = "legacy"
        K.FED_OUTPOST_MODE = "legacy"
        return "digest"

    monkeypatch.setattr(FLD, "_legacy_run_digest", fake)
    before = (K.PORT_UPGRADE_MODE, K.FED_OUTPOST_MODE)
    assert FLD.legacy_run_digest(ROOT, flip=("PORT_UPGRADE_MODE",)) == "digest"
    assert seen["env"] == []
    assert before == (K.PORT_UPGRADE_MODE, K.FED_OUTPOST_MODE)
    import os
    assert os.environ.get("TW2K_HINT_LEVEL") == "minimal"


def test_port_upgrade_pin_holds_with_a_hint_level_in_the_shell():
    """End to end: the raw digest call, run with TW2K_HINT_LEVEL=minimal set, still gives the golden."""
    code = (
        "import sys; sys.path.insert(0, 'tests'); sys.path.insert(0, 'src');"
        "from pathlib import Path; from fed_legacy_digest import legacy_run_digest;"
        f"print(legacy_run_digest(Path('.'), 'N3,N2,N1,H', 3, 250925, flip={PIN_FLIPS!r}))"
    )
    env = pin_env(TW2K_HINT_LEVEL="minimal", TW2K_PORT_MATCH="1")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True,
                         timeout=900, check=True)
    assert out.stdout.strip().splitlines()[-1] == PORT_UPGRADE_LEGACY_GOLDEN
