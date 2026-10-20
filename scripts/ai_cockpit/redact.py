"""Strip API keys and seat tokens from anything the player writes down."""

from __future__ import annotations

import os
import re

# Names only. Values are read at redact time so a key set later is still covered.
KEY_ENVS = (
    "XAI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "TW2K_COCKPIT_LLM_KEY",
)

_BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{8,}")
_SK = re.compile(r"(?i)\bsk-[A-Za-z0-9_\-]{8,}")
_XAI = re.compile(r"(?i)\bxai-[A-Za-z0-9_\-]{8,}")
_TOKEN_QUERY = re.compile(r"(?i)(token=)[^&\s\"']+")


def secret_values() -> list[str]:
    """Key values currently in the environment. Short values are ignored."""
    found: list[str] = []
    for name in KEY_ENVS:
        value = os.environ.get(name) or ""
        if len(value) >= 6:
            found.append(value)
    return found


def redact(text: str) -> str:
    """Replace keys and seat tokens with a fixed marker."""
    if not text:
        return text
    for value in secret_values():
        text = text.replace(value, "[redacted]")
    text = _BEARER.sub("Bearer [redacted]", text)
    text = _SK.sub("[redacted]", text)
    text = _XAI.sub("[redacted]", text)
    text = _TOKEN_QUERY.sub(r"\1[redacted]", text)
    return text
