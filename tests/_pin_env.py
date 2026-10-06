"""Hermetic environment for the legacy digest pins (QC slice 55).

A pin subprocess used to inherit the whole parent environment. TW2K_HINT_LEVEL=minimal
in the shell that runs pytest moves the 9be95517 pin to 924564e9 (agency.is_minimal
changes every observation), so any TW2K_* variable left over from a match or a server
run could fail the pins for a reason that has nothing to do with the engine.
"""

from __future__ import annotations

import os

PIN_ENV_PREFIXES = ("TW2K_",)


def scrubbed_environ(environ: dict[str, str] | None = None) -> dict[str, str]:
    """`environ` (default os.environ) without any TW2K_* variable."""
    src = os.environ if environ is None else environ
    return {k: v for k, v in src.items() if not k.upper().startswith(PIN_ENV_PREFIXES)}


def pin_env(**extra: str) -> dict[str, str]:
    """Environment for a pin subprocess: no TW2K_* variables, PYTHONHASHSEED=0, plus `extra`."""
    env = scrubbed_environ()
    env["PYTHONHASHSEED"] = "0"
    env.update(extra)
    return env
