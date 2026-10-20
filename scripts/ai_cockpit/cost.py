"""Token prices for the cockpit player.

The figures are the same USD-per-million rates as
``src/tw2k/engine/llm_pricing.py`` (curated 2026-04-22). This copy lives here
so the player process does not import the engine. Unknown models use the
provider default. A missing provider costs nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

# USD per 1,000,000 tokens. More specific model names come first.
_PRICES: dict[str, list[tuple[str, dict[str, float]]]] = {
    "xai": [
        ("grok-4.3", {"input": 1.25, "cached_input": 0.20, "output": 2.50}),
        ("grok-4-1-fast-reasoning", {"input": 0.20, "output": 0.50}),
        ("grok-4-1-fast", {"input": 0.20, "output": 0.50}),
        ("grok-4", {"input": 3.00, "output": 15.00}),
        ("grok-3", {"input": 3.00, "output": 15.00}),
        ("default", {"input": 0.20, "output": 0.50}),
    ],
    "anthropic": [
        ("claude-sonnet-4-5", {"input": 3.00, "cached_input": 0.30, "cache_write": 3.75, "output": 15.00}),
        ("claude-sonnet-4", {"input": 3.00, "cached_input": 0.30, "cache_write": 3.75, "output": 15.00}),
        ("claude-opus-4", {"input": 15.00, "cached_input": 1.50, "cache_write": 18.75, "output": 75.00}),
        ("claude-haiku-4", {"input": 1.00, "cached_input": 0.10, "cache_write": 1.25, "output": 5.00}),
        ("default", {"input": 3.00, "cached_input": 0.30, "cache_write": 3.75, "output": 15.00}),
    ],
    "openai": [
        ("gpt-5", {"input": 2.50, "cached_input": 1.25, "output": 10.00}),
        ("gpt-4.1", {"input": 2.00, "cached_input": 0.50, "output": 8.00}),
        ("gpt-4o-mini", {"input": 0.15, "cached_input": 0.075, "output": 0.60}),
        ("gpt-4o", {"input": 2.50, "cached_input": 1.25, "output": 10.00}),
        ("default", {"input": 2.50, "cached_input": 1.25, "output": 10.00}),
    ],
}

_ALIASES = {"grok": "xai", "xai": "xai", "openai": "openai", "anthropic": "anthropic"}


@dataclass
class Usage:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    usd: float = 0.0

    def add(self, other: Usage) -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cached_tokens += other.cached_tokens
        self.cache_write_tokens += other.cache_write_tokens
        self.usd += other.usd

    def line(self) -> str:
        return (
            f"cost provider={self.provider} model={self.model} "
            f"input_tokens={self.input_tokens} output_tokens={self.output_tokens} "
            f"usd={self.usd:.6f}"
        )


def _rates(provider: str, model: str) -> dict[str, float]:
    table = _PRICES.get(_ALIASES.get(provider, provider), [])
    name = (model or "").lower()
    chosen: dict[str, float] = {}
    for needle, rates in table:
        if needle == "default":
            chosen = rates
            break
        if needle in name:
            return rates
    return chosen


def price_usage(provider: str, model: str, *, input_tokens: int, output_tokens: int,
                cached_tokens: int = 0, cache_write_tokens: int = 0) -> Usage:
    """Dollar cost for one reply. Fresh input is billed apart from cached reads."""
    rates = _rates(provider, model)
    fresh = max(0, int(input_tokens) - int(cached_tokens))
    cached = max(0, int(cached_tokens))
    write = max(0, int(cache_write_tokens))
    output = max(0, int(output_tokens))
    million = 1_000_000.0
    usd = (
        fresh * float(rates.get("input", 0.0))
        + cached * float(rates.get("cached_input", rates.get("input", 0.0)))
        + write * float(rates.get("cache_write", rates.get("input", 0.0)))
        + output * float(rates.get("output", 0.0))
    ) / million
    return Usage(
        provider=provider,
        model=model,
        input_tokens=int(input_tokens),
        output_tokens=output,
        cached_tokens=cached,
        cache_write_tokens=write,
        usd=usd,
    )
