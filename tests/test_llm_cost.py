"""Tests for LLM cost tracking (pricing table + usage extraction + tally)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from tw2k.agents.llm_usage import (
    LLMUsage,
    from_anthropic,
    from_cursor_outer_json,
    from_openai_like,
)
from tw2k.engine.llm_pricing import (
    MatchCostTracker,
    TokenPrices,
    lookup_prices,
)


# ---------------------------------------------------------------------------
# Pricing lookup
# ---------------------------------------------------------------------------


def test_lookup_known_cursor_composer() -> None:
    """Exact model match returns the baked-in composer-2-fast rates."""
    p = lookup_prices("cursor", "composer-2-fast")
    assert p.provider == "cursor"
    assert p.model == "composer-2-fast"
    assert p.input == pytest.approx(1.50)
    assert p.cached_input == pytest.approx(0.35)
    assert p.output == pytest.approx(7.50)
    assert p.is_fallback is False


def test_lookup_unknown_provider_returns_zeros() -> None:
    """Unknown provider falls through to a zero-rate table."""
    p = lookup_prices("no-such-provider", "model-x")
    assert p.input == 0.0
    assert p.output == 0.0
    assert p.is_fallback is True


def test_lookup_custom_is_free_by_default() -> None:
    """Self-hosted `custom` provider bills $0 out of the box."""
    p = lookup_prices("custom", "qwen3.5:122b")
    assert p.input == 0.0
    assert p.output == 0.0


def test_lookup_provider_default_fallback() -> None:
    """Unknown model inside a known provider hits the 'default' row."""
    p = lookup_prices("xai", "grok-999-unreleased")
    assert p.is_fallback is True
    # xAI default uses the fast-reasoning tier rates.
    assert p.input > 0.0


def test_tokenprices_cost_math() -> None:
    """cost_usd treats each bucket independently and clamps negatives."""
    prices = TokenPrices(input=1.50, cached_input=0.35, output=7.50)
    cost = prices.cost_usd(
        input_tokens=1000,
        cached_input_tokens=2000,
        output_tokens=500,
    )
    # 1000*1.50/1e6 + 2000*0.35/1e6 + 500*7.50/1e6
    expected = (1000 * 1.50 + 2000 * 0.35 + 500 * 7.50) / 1_000_000
    assert cost == pytest.approx(expected)


def test_tokenprices_clamps_negative_counts() -> None:
    prices = TokenPrices(input=1.0, output=2.0)
    assert prices.cost_usd(input_tokens=-500, output_tokens=10) == pytest.approx(
        10 * 2.0 / 1_000_000
    )


# ---------------------------------------------------------------------------
# Price override loading
# ---------------------------------------------------------------------------


def test_price_overrides_via_env(tmp_path, monkeypatch) -> None:
    """User-supplied JSON can shadow the default rates per (provider, model)."""
    override = tmp_path / "rates.json"
    override.write_text(
        json.dumps(
            {
                "custom": {
                    "default": {"input": 0.50, "output": 2.00},
                    "qwen3.5": {"input": 0.10, "output": 0.40},
                }
            }
        )
    )
    monkeypatch.setenv("TW2K_COST_OVERRIDES_PATH", str(override))
    # Force the module to re-read on the next lookup.
    import tw2k.engine.llm_pricing as lp

    lp._OVERRIDES = None
    lp._OVERRIDES_PATH = None

    specific = lookup_prices("custom", "qwen3.5:122b")
    assert specific.input == pytest.approx(0.10)
    assert specific.output == pytest.approx(0.40)
    assert specific.is_fallback is False

    fallback = lookup_prices("custom", "some-other-model")
    assert fallback.input == pytest.approx(0.50)
    assert fallback.output == pytest.approx(2.00)
    assert fallback.is_fallback is True

    monkeypatch.delenv("TW2K_COST_OVERRIDES_PATH")
    lp._OVERRIDES = None
    lp._OVERRIDES_PATH = None


# ---------------------------------------------------------------------------
# Usage extraction — OpenAI-shape
# ---------------------------------------------------------------------------


def _mk_openai_resp(
    prompt: int = 0,
    completion: int = 0,
    cached: int = 0,
    *,
    via_details: bool = True,
):
    """Build a fake openai.ChatCompletion-ish object with the given counts."""
    if via_details:
        usage = SimpleNamespace(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=prompt + completion,
            prompt_tokens_details=SimpleNamespace(cached_tokens=cached),
        )
    else:
        usage = SimpleNamespace(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=prompt + completion,
            cached_tokens=cached,
        )
    return SimpleNamespace(usage=usage)


def test_from_openai_like_splits_cached_from_fresh() -> None:
    """cached_tokens is subtracted from prompt_tokens to get fresh input."""
    resp = _mk_openai_resp(prompt=10_000, completion=500, cached=3_000)
    u = from_openai_like(resp, provider="openai")
    assert u is not None
    assert u.input_tokens == 7_000
    assert u.cached_input_tokens == 3_000
    assert u.output_tokens == 500
    assert u.total_input_tokens == 10_000
    assert u.source == "openai"


def test_from_openai_like_top_level_cached_fallback() -> None:
    """Some self-hosted servers expose cached_tokens at the top level."""
    resp = _mk_openai_resp(prompt=8_000, completion=200, cached=1_500, via_details=False)
    # Scrub prompt_tokens_details so only the top-level field remains.
    resp.usage.prompt_tokens_details = SimpleNamespace(cached_tokens=0)
    u = from_openai_like(resp, provider="custom")
    assert u is not None
    assert u.cached_input_tokens == 1_500
    assert u.input_tokens == 6_500


def test_from_openai_like_missing_usage() -> None:
    """Missing usage block returns None, not a crash."""
    resp = SimpleNamespace(usage=None)
    assert from_openai_like(resp, provider="xai") is None


# ---------------------------------------------------------------------------
# Usage extraction — Anthropic shape
# ---------------------------------------------------------------------------


def test_from_anthropic_preserves_cache_read_and_create() -> None:
    """Anthropic input_tokens is already 'fresh' — we just copy it across."""
    msg = SimpleNamespace(
        usage=SimpleNamespace(
            input_tokens=500,
            output_tokens=300,
            cache_read_input_tokens=2_000,
            cache_creation_input_tokens=100,
        )
    )
    u = from_anthropic(msg)
    assert u is not None
    assert u.input_tokens == 500
    assert u.cached_input_tokens == 2_000
    assert u.cache_write_tokens == 100
    assert u.output_tokens == 300
    assert u.total_input_tokens == 500 + 2_000 + 100
    assert u.source == "anthropic"


# ---------------------------------------------------------------------------
# Usage extraction — Cursor CLI envelope
# ---------------------------------------------------------------------------


def test_from_cursor_outer_json_parses_envelope() -> None:
    """Outer JSON with usage block → split cached/write off the fresh input."""
    outer = {
        "text": "...reply...",
        "usage": {
            "inputTokens": 10_000,
            "outputTokens": 400,
            "cacheReadTokens": 8_000,
            "cacheWriteTokens": 200,
        },
    }
    u = from_cursor_outer_json(outer)
    assert u is not None
    assert u.input_tokens == 10_000 - 8_000 - 200
    assert u.cached_input_tokens == 8_000
    assert u.cache_write_tokens == 200
    assert u.output_tokens == 400
    assert u.source == "cursor"


def test_from_cursor_outer_json_accepts_string() -> None:
    raw = json.dumps(
        {"usage": {"inputTokens": 5, "outputTokens": 1, "cacheReadTokens": 0}}
    )
    u = from_cursor_outer_json(raw)
    assert u is not None
    assert u.input_tokens == 5
    assert u.output_tokens == 1


def test_from_cursor_outer_json_missing_usage_returns_none() -> None:
    assert from_cursor_outer_json({"text": "hi"}) is None
    assert from_cursor_outer_json("not json") is None
    assert from_cursor_outer_json(42) is None


# ---------------------------------------------------------------------------
# MatchCostTracker end-to-end
# ---------------------------------------------------------------------------


def test_match_cost_tracker_accumulates_across_calls() -> None:
    tracker = MatchCostTracker()
    # Composer 2 Fast: 1.50/0.35/7.50 per 1M.
    inc1, tally = tracker.record_call(
        "p1",
        provider="cursor",
        model="composer-2-fast",
        input_tokens=1_000,
        cached_input_tokens=2_000,
        output_tokens=500,
    )
    expected = (1_000 * 1.50 + 2_000 * 0.35 + 500 * 7.50) / 1_000_000
    assert inc1 == pytest.approx(expected)
    assert tally.calls == 1

    inc2, tally = tracker.record_call(
        "p1",
        provider="cursor",
        model="composer-2-fast",
        input_tokens=500,
        output_tokens=100,
    )
    assert tally.calls == 2
    assert tally.cost_usd == pytest.approx(inc1 + inc2)

    # Second player — separate bucket.
    tracker.record_call(
        "p2",
        provider="custom",
        model="qwen3.5:122b",
        input_tokens=1_000_000,
        output_tokens=500_000,
    )
    totals = tracker.totals()
    assert set(totals["per_player"]) == {"p1", "p2"}
    # Custom is $0 out of the box → only p1 contributes to grand total.
    assert totals["total"]["cost_usd"] == pytest.approx(inc1 + inc2)
    assert totals["total"]["calls"] == 3


def test_tracker_records_fallback_flag_for_unknown_model() -> None:
    tracker = MatchCostTracker()
    tracker.record_call(
        "p1",
        provider="anthropic",
        model="claude-future-11",
        input_tokens=100,
        output_tokens=100,
    )
    tally = tracker.per_player["p1"]
    # claude-future-11 isn't a known slug → default row.
    assert tally.price_is_fallback is True
    assert tally.cost_usd > 0.0  # we still priced it against the default row
