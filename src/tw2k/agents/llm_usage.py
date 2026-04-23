"""Per-call token usage extraction for every TW2K LLM backend.

Each provider returns a slightly different usage shape:

* **OpenAI / xAI / DeepSeek / custom (Ollama-compat)** — a
  ``response.usage`` object with ``prompt_tokens``, ``completion_tokens``,
  ``total_tokens`` and optionally ``prompt_tokens_details.cached_tokens``.
* **Anthropic** — ``msg.usage`` with ``input_tokens``, ``output_tokens``,
  ``cache_read_input_tokens``, ``cache_creation_input_tokens``.
* **Cursor Agent CLI** — the outer ``agent -p --output-format json``
  envelope carries a ``usage`` dict with ``inputTokens``, ``outputTokens``,
  ``cacheReadTokens``, ``cacheWriteTokens``.

This module normalizes all three shapes into a single ``LLMUsage``
dataclass so the runner can emit one consistent ``llm_usage`` event
regardless of backend.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMUsage:
    """Normalized token-usage reading for one LLM call.

    ``input_tokens`` is **fresh** input only (cached portion is
    *subtracted* off). This mirrors how Anthropic and Cursor already
    bill cache-reads separately, and matches how
    ``TokenPrices.cost_usd`` expects the inputs.
    """

    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    # Raw pre-split totals, preserved so downstream tooling (cost
    # reports, dashboards) can reconstruct whichever view it prefers.
    total_input_tokens: int = 0
    source: str = ""  # provider name that filled this struct
    raw: dict[str, Any] | None = None

    def to_payload(self) -> dict:
        return {
            "input_tokens": int(self.input_tokens),
            "cached_input_tokens": int(self.cached_input_tokens),
            "cache_write_tokens": int(self.cache_write_tokens),
            "output_tokens": int(self.output_tokens),
            "total_input_tokens": int(self.total_input_tokens),
            "source": self.source or "",
        }


def _as_int(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def from_openai_like(resp: Any, provider: str = "") -> LLMUsage | None:
    """Extract usage from an OpenAI-SDK ``ChatCompletion`` (or compat)."""
    usage = getattr(resp, "usage", None)
    if usage is None:
        return None
    prompt = _as_int(getattr(usage, "prompt_tokens", 0))
    completion = _as_int(getattr(usage, "completion_tokens", 0))
    cached = 0
    details = getattr(usage, "prompt_tokens_details", None)
    if details is not None:
        cached = _as_int(getattr(details, "cached_tokens", 0))
    # Some self-hosted OpenAI-compat servers stash cached counts at the
    # top level instead of inside prompt_tokens_details — belt & braces.
    if not cached:
        cached = _as_int(getattr(usage, "cached_tokens", 0))
    fresh = max(0, prompt - cached)
    return LLMUsage(
        input_tokens=fresh,
        cached_input_tokens=cached,
        cache_write_tokens=0,
        output_tokens=completion,
        total_input_tokens=prompt,
        source=provider or "openai_like",
        raw={
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "cached_tokens": cached,
        },
    )


def from_anthropic(msg: Any) -> LLMUsage | None:
    """Extract usage from an Anthropic ``Message`` response."""
    usage = getattr(msg, "usage", None)
    if usage is None:
        return None
    input_total = _as_int(getattr(usage, "input_tokens", 0))
    output = _as_int(getattr(usage, "output_tokens", 0))
    cache_read = _as_int(getattr(usage, "cache_read_input_tokens", 0))
    cache_create = _as_int(getattr(usage, "cache_creation_input_tokens", 0))
    # Anthropic already returns ``input_tokens`` as the *fresh* count
    # (cache reads/creates are reported as siblings, not inside it).
    return LLMUsage(
        input_tokens=input_total,
        cached_input_tokens=cache_read,
        cache_write_tokens=cache_create,
        output_tokens=output,
        total_input_tokens=input_total + cache_read + cache_create,
        source="anthropic",
        raw={
            "input_tokens": input_total,
            "output_tokens": output,
            "cache_read_input_tokens": cache_read,
            "cache_creation_input_tokens": cache_create,
        },
    )


def from_cursor_outer_json(outer: Any) -> LLMUsage | None:
    """Extract usage from the outer envelope of ``agent -p --output-format json``.

    ``outer`` may be the parsed dict or the raw JSON string. Unknown
    shapes return None (caller keeps going without cost tracking for
    that turn).
    """
    data = outer
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict):
        return None
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None
    prompt = _as_int(usage.get("inputTokens"))
    completion = _as_int(usage.get("outputTokens"))
    cache_read = _as_int(usage.get("cacheReadTokens"))
    cache_write = _as_int(usage.get("cacheWriteTokens"))
    # Cursor's ``inputTokens`` bundles the cached portion (observed
    # 2026-04: inputTokens=6094, cacheReadTokens=2112 on a trivial
    # call). Subtract so the "fresh" figure matches the price table.
    fresh = max(0, prompt - cache_read - cache_write)
    return LLMUsage(
        input_tokens=fresh,
        cached_input_tokens=cache_read,
        cache_write_tokens=cache_write,
        output_tokens=completion,
        total_input_tokens=prompt,
        source="cursor",
        raw=dict(usage),
    )
