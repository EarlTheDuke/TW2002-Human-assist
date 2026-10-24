"""Re-export the cockpit directive helpers.

The implementation lives in ``scripts/ai_cockpit/directives.py`` so the
rendered cockpit player can import it without loading the engine. This
module does not add a route and does not read another seat's files.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PATH = Path(__file__).resolve().parents[3] / "scripts" / "ai_cockpit" / "directives.py"
_SPEC = importlib.util.spec_from_file_location("cockpit_directive_impl", _PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"cockpit directive helpers not found at {_PATH}")
_mod = importlib.util.module_from_spec(_SPEC)
sys.modules["cockpit_directive_impl"] = _mod
_SPEC.loader.exec_module(_mod)

Directive = _mod.Directive
DirectiveError = _mod.DirectiveError
DirectiveHarness = _mod.DirectiveHarness
RetryableHTTPError = _mod.RetryableHTTPError
StuckWatch = _mod.StuckWatch
clean_seat = _mod.clean_seat
directive_step = _mod.directive_step
drop_file = _mod.drop_file
load_active = _mod.load_active
observation_fingerprint = _mod.observation_fingerprint
prompt_block = _mod.prompt_block
redact_text = _mod.redact_text
retryable_error = _mod.retryable_error
screen_fingerprint = _mod.screen_fingerprint
seat_from_url = _mod.seat_from_url
token_from_url = _mod.token_from_url
turn_prompt = _mod.turn_prompt
validate_proposal = _mod.validate_proposal
with_reconnect = _mod.with_reconnect

__all__ = [
    "Directive",
    "DirectiveError",
    "DirectiveHarness",
    "RetryableHTTPError",
    "StuckWatch",
    "clean_seat",
    "directive_step",
    "drop_file",
    "load_active",
    "observation_fingerprint",
    "prompt_block",
    "redact_text",
    "retryable_error",
    "screen_fingerprint",
    "seat_from_url",
    "token_from_url",
    "turn_prompt",
    "validate_proposal",
    "with_reconnect",
]
