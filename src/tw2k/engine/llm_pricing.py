"""Per-token pricing for the LLM providers TW2K talks to.

This module turns raw `LLMUsage` readings into dollar figures so the
runner can emit real-time cost-per-turn events and the final
`match_metrics` event can show a per-player budget impact.

### Data model

Prices are stored as **USD per 1,000,000 tokens**, split into four
channels that providers typically bill on:

* ``input``        — fresh input / prompt tokens
* ``cached_input`` — cached-prompt reads (cheaper than fresh input)
* ``output``       — generated / completion tokens
* ``cache_write``  — cache-creation writes (Anthropic-only; most
  providers charge the same as a fresh input token for these)

### Lookups

Because different providers report the same model by different slugs,
and because the user can point the ``custom`` provider at any local
server, we do a **provider → substring** match against ``MODELS``.
The first entry whose ``match`` substring appears in the requested
model name wins. A provider's ``"default"`` entry is the fallback.

### Overrides

Set ``TW2K_COST_OVERRIDES_PATH`` to a JSON file shaped like:

```json
{
  "xai": {
    "grok-4-1-fast-reasoning": {"input": 0.2, "output": 0.5}
  },
  "custom": {
    "default": {"input": 0.0, "output": 0.0}
  }
}
```

Missing channels fall back to the baked-in default. Unknown providers
are simply treated as free (``$0``) so cost tracking never crashes the
match — it just under-counts until the user adds a price.

Prices last curated: **2026-04-22**. They're best-effort estimates
sourced from each vendor's pricing page and may drift; operators
should refresh the JSON override to pin exact figures.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from threading import Lock
from typing import Iterable

# USD per 1M tokens.
_M = 1_000_000.0

# Default price tables per provider. Ordering matters for the
# substring match — put more-specific model slugs *before* broader
# ones, and keep "default" last so it only fires on miss.
DEFAULT_PRICES: dict[str, list[tuple[str, dict[str, float]]]] = {
    # xAI Grok. Prices from https://x.ai/api (fast-reasoning tier,
    # 2026-04). JSON mode adds no surcharge.
    "xai": [
        ("grok-4-1-fast-reasoning", {"input": 0.20, "output": 0.50}),
        ("grok-4-1-fast", {"input": 0.20, "output": 0.50}),
        ("grok-4", {"input": 3.00, "output": 15.00}),
        ("grok-3", {"input": 3.00, "output": 15.00}),
        ("default", {"input": 0.20, "output": 0.50}),
    ],
    # Anthropic — cache_read_input_tokens billed at ~10% of fresh
    # input, cache_creation billed at ~125% (the write premium).
    "anthropic": [
        (
            "claude-sonnet-4-5",
            {"input": 3.00, "cached_input": 0.30, "cache_write": 3.75, "output": 15.00},
        ),
        (
            "claude-sonnet-4",
            {"input": 3.00, "cached_input": 0.30, "cache_write": 3.75, "output": 15.00},
        ),
        (
            "claude-opus-4",
            {"input": 15.00, "cached_input": 1.50, "cache_write": 18.75, "output": 75.00},
        ),
        (
            "claude-haiku-4",
            {"input": 1.00, "cached_input": 0.10, "cache_write": 1.25, "output": 5.00},
        ),
        (
            "default",
            {"input": 3.00, "cached_input": 0.30, "cache_write": 3.75, "output": 15.00},
        ),
    ],
    # OpenAI — cached inputs at 50% of fresh.
    "openai": [
        ("gpt-5", {"input": 2.50, "cached_input": 1.25, "output": 10.00}),
        ("gpt-4.1", {"input": 2.00, "cached_input": 0.50, "output": 8.00}),
        ("gpt-4o-mini", {"input": 0.15, "cached_input": 0.075, "output": 0.60}),
        ("gpt-4o", {"input": 2.50, "cached_input": 1.25, "output": 10.00}),
        ("default", {"input": 2.50, "cached_input": 1.25, "output": 10.00}),
    ],
    # DeepSeek — cheapest of the bunch; cached at 10%.
    "deepseek": [
        ("deepseek-reasoner", {"input": 0.55, "cached_input": 0.14, "output": 2.19}),
        ("deepseek-chat", {"input": 0.27, "cached_input": 0.07, "output": 1.10}),
        ("default", {"input": 0.27, "cached_input": 0.07, "output": 1.10}),
    ],
    # Cursor Agent CLI (Composer family) — from cursor.com/docs/models-and-pricing
    # (2026-04). Composer 2 Fast is the default user experience.
    "cursor": [
        ("composer-2-fast", {"input": 1.50, "cached_input": 0.35, "output": 7.50}),
        ("composer-2", {"input": 0.50, "cached_input": 0.20, "output": 2.50}),
        ("default", {"input": 1.50, "cached_input": 0.35, "output": 7.50}),
    ],
    # Self-hosted / custom endpoints (tinybox, Ollama, vLLM, LiteLLM).
    # User pays in GPU-hours, not tokens, so TW2K accounts them as $0.
    # Override via TW2K_COST_OVERRIDES_PATH if you want to attribute
    # an internal chargeback rate.
    "custom": [
        ("default", {"input": 0.0, "cached_input": 0.0, "output": 0.0}),
    ],
    # Heuristic agents never call the LLM — always $0, but we keep
    # the entry so cost reports render them in the same columns.
    "heuristic": [
        ("default", {"input": 0.0, "cached_input": 0.0, "output": 0.0}),
    ],
    "none": [
        ("default", {"input": 0.0, "cached_input": 0.0, "output": 0.0}),
    ],
}


@dataclass(frozen=True)
class TokenPrices:
    """USD per 1M tokens for a (provider, model) pair."""

    input: float = 0.0
    cached_input: float = 0.0
    cache_write: float = 0.0
    output: float = 0.0
    provider: str = ""
    model: str = ""
    # True when we hit the provider's "default" catch-all rather than a
    # specific model entry. Tools can surface this so users know the
    # number is an estimate for an unrecognized slug.
    is_fallback: bool = False

    def cost_usd(
        self,
        *,
        input_tokens: int = 0,
        cached_input_tokens: int = 0,
        cache_write_tokens: int = 0,
        output_tokens: int = 0,
    ) -> float:
        """USD cost for one LLM call's token counts.

        ``input_tokens`` is treated as the *fresh* prompt tokens —
        callers should subtract ``cached_input_tokens`` (and
        ``cache_write_tokens`` on Anthropic) before passing in to
        avoid double-counting.
        """
        return (
            max(0, int(input_tokens)) * self.input / _M
            + max(0, int(cached_input_tokens)) * self.cached_input / _M
            + max(0, int(cache_write_tokens)) * self.cache_write / _M
            + max(0, int(output_tokens)) * self.output / _M
        )


# ---------------------------------------------------------------------------
# Override loading
# ---------------------------------------------------------------------------

_OVERRIDE_LOCK = Lock()
_OVERRIDES: dict[str, list[tuple[str, dict[str, float]]]] | None = None
_OVERRIDES_PATH: str | None = None


def _load_overrides_from_env() -> None:
    """(Re)load the optional price override JSON pointed at by env."""
    global _OVERRIDES, _OVERRIDES_PATH
    path = (os.environ.get("TW2K_COST_OVERRIDES_PATH") or "").strip() or None
    if path == _OVERRIDES_PATH and _OVERRIDES is not None:
        return
    _OVERRIDES_PATH = path
    _OVERRIDES = None
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception:
        # Any problem with the file means we silently stick with
        # defaults — cost tracking is observational, not critical.
        return
    parsed: dict[str, list[tuple[str, dict[str, float]]]] = {}
    if isinstance(raw, dict):
        for prov, models in raw.items():
            if not isinstance(models, dict):
                continue
            entries: list[tuple[str, dict[str, float]]] = []
            for slug, rates in models.items():
                if isinstance(slug, str) and isinstance(rates, dict):
                    clean = {
                        k: float(v)
                        for k, v in rates.items()
                        if k in ("input", "cached_input", "cache_write", "output")
                        and isinstance(v, (int, float))
                    }
                    if clean:
                        entries.append((slug.lower(), clean))
            if entries:
                parsed[prov.lower()] = entries
    _OVERRIDES = parsed


def _match_entries(
    entries: Iterable[tuple[str, dict[str, float]]], model: str
) -> tuple[dict[str, float], bool] | None:
    """First entry whose substring appears in ``model`` wins.

    ``default`` is the catch-all. Returns ``(rates, is_fallback)`` or
    None if no match at all.
    """
    lowered = (model or "").lower()
    default_rates: dict[str, float] | None = None
    for slug, rates in entries:
        if slug == "default":
            default_rates = rates
            continue
        if slug and slug in lowered:
            return rates, False
    if default_rates is not None:
        return default_rates, True
    return None


def lookup_prices(provider: str, model: str) -> TokenPrices:
    """Return ``TokenPrices`` for the given (provider, model) pair.

    Falls back through override → default → $0.
    """
    with _OVERRIDE_LOCK:
        _load_overrides_from_env()
        overrides = _OVERRIDES

    prov_key = (provider or "").lower()

    if overrides is not None and prov_key in overrides:
        match = _match_entries(overrides[prov_key], model or "")
        if match is not None:
            rates, is_fallback = match
            return _prices_from_rates(rates, provider, model, is_fallback)

    if prov_key in DEFAULT_PRICES:
        match = _match_entries(DEFAULT_PRICES[prov_key], model or "")
        if match is not None:
            rates, is_fallback = match
            return _prices_from_rates(rates, provider, model, is_fallback)

    return TokenPrices(provider=provider or "", model=model or "", is_fallback=True)


def _prices_from_rates(
    rates: dict[str, float], provider: str, model: str, is_fallback: bool
) -> TokenPrices:
    return TokenPrices(
        input=float(rates.get("input", 0.0)),
        cached_input=float(rates.get("cached_input", 0.0)),
        cache_write=float(rates.get("cache_write", 0.0)),
        output=float(rates.get("output", 0.0)),
        provider=provider or "",
        model=model or "",
        is_fallback=is_fallback,
    )


# ---------------------------------------------------------------------------
# Usage accumulator
# ---------------------------------------------------------------------------


@dataclass
class CostTally:
    """Rolling per-(provider,model) token + dollar totals for one player."""

    provider: str = ""
    model: str = ""
    calls: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    # Mirrored is_fallback status from the last price lookup — lets
    # the final report tell the operator that Composer's numbers are
    # from the real table but custom/tinybox is hand-waved $0.
    price_is_fallback: bool = False

    def add(
        self,
        *,
        provider: str,
        model: str,
        input_tokens: int = 0,
        cached_input_tokens: int = 0,
        cache_write_tokens: int = 0,
        output_tokens: int = 0,
    ) -> float:
        """Record one LLM call and return its incremental USD cost."""
        # If this tally is new, stamp provider/model once. When the
        # agent switches models mid-match (unlikely but possible via
        # env tweaks + restart) we keep the most recent slug.
        if not self.provider:
            self.provider = provider
        if not self.model:
            self.model = model
        prices = lookup_prices(provider, model)
        # Anthropic / OpenAI count cached tokens INSIDE the total input
        # figure they return. Callers pass the already-split values
        # (fresh=input-cached) so we don't double-count here.
        inc = prices.cost_usd(
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            cache_write_tokens=cache_write_tokens,
            output_tokens=output_tokens,
        )
        self.calls += 1
        self.input_tokens += max(0, int(input_tokens))
        self.cached_input_tokens += max(0, int(cached_input_tokens))
        self.cache_write_tokens += max(0, int(cache_write_tokens))
        self.output_tokens += max(0, int(output_tokens))
        self.cost_usd += inc
        self.price_is_fallback = prices.is_fallback
        return inc

    def to_payload(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "price_is_fallback": bool(self.price_is_fallback),
        }


@dataclass
class MatchCostTracker:
    """Per-match, per-player cost ledger.

    Kept on the runner so ``/api/cost`` and the final ``match_metrics``
    payload can surface it without re-scanning the event log.
    """

    per_player: dict[str, CostTally] = field(default_factory=dict)

    def record_call(
        self,
        player_id: str,
        *,
        provider: str,
        model: str,
        input_tokens: int = 0,
        cached_input_tokens: int = 0,
        cache_write_tokens: int = 0,
        output_tokens: int = 0,
    ) -> tuple[float, CostTally]:
        """Attribute one LLM call to ``player_id``; return (incremental_usd, updated_tally)."""
        tally = self.per_player.get(player_id)
        if tally is None:
            tally = CostTally()
            self.per_player[player_id] = tally
        inc = tally.add(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            cache_write_tokens=cache_write_tokens,
            output_tokens=output_tokens,
        )
        return inc, tally

    def totals(self) -> dict:
        """Snapshot payload for `/api/cost` and `match_metrics`."""
        grand_calls = 0
        grand_input = 0
        grand_cached = 0
        grand_cwrite = 0
        grand_output = 0
        grand_cost = 0.0
        rows: dict[str, dict] = {}
        for pid, tally in self.per_player.items():
            rows[pid] = tally.to_payload()
            grand_calls += tally.calls
            grand_input += tally.input_tokens
            grand_cached += tally.cached_input_tokens
            grand_cwrite += tally.cache_write_tokens
            grand_output += tally.output_tokens
            grand_cost += tally.cost_usd
        return {
            "per_player": rows,
            "total": {
                "calls": grand_calls,
                "input_tokens": grand_input,
                "cached_input_tokens": grand_cached,
                "cache_write_tokens": grand_cwrite,
                "output_tokens": grand_output,
                "cost_usd": round(grand_cost, 6),
            },
        }
