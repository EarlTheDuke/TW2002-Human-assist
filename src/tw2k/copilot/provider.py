"""Thin LLM facade for the copilot.

H2 intentionally keeps this simple: one call in, one JSON string out,
parsed into a `ToolCall` (or list of them). Real native tool-use (with
multi-turn tool_result loops) arrives in H3+ alongside Pipecat.

Why not reuse `LLMAgent._call_*` directly? Those methods are tightly
coupled to the autonomous-agent system prompt + observation-json user
message. The copilot needs a different system prompt (tool-centric)
and a different user message (human utterance + observation snippet),
so a tiny parallel implementation is cleaner than adding a branch to
the existing agent code.

If `provider="mock"` is used, `call_llm` dispatches to a `MockProvider`
registry — this is how the tests run without any real API key and is
how the scripted exit-criterion integration test drives a trade loop.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import Awaitable, Callable
from typing import Any

from ..agents.llm import (
    CUSTOM_BASE_URL,
    CUSTOM_KEEP_ALIVE,
    DEEPSEEK_BASE_URL,
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_CUSTOM_MODEL,
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_XAI_MODEL,
    XAI_BASE_URL,
    default_provider,
)
from .tools import ToolCall

# ---------------------------------------------------------------------------
# Mock provider hook — used by tests and the H2 scripted demo.
# ---------------------------------------------------------------------------

MockResponder = Callable[[str, str, dict[str, Any]], Awaitable[str]]
"""(system_prompt, user_prompt, context) -> raw JSON string."""

_mock_responders: dict[str, MockResponder] = {}


def register_mock_responder(tag: str, fn: MockResponder) -> None:
    """Install a mock responder under `tag`. Call `call_llm(..., provider="mock:"+tag)`."""
    _mock_responders[tag] = fn


def clear_mock_responders() -> None:
    _mock_responders.clear()


# ---------------------------------------------------------------------------
# Model defaults
# ---------------------------------------------------------------------------


def default_model(provider: str) -> str:
    if provider == "anthropic":
        return DEFAULT_ANTHROPIC_MODEL
    if provider == "openai":
        return DEFAULT_OPENAI_MODEL
    if provider == "deepseek":
        return DEFAULT_DEEPSEEK_MODEL
    if provider == "custom":
        return DEFAULT_CUSTOM_MODEL
    if provider == "xai":
        return DEFAULT_XAI_MODEL
    return ""


def resolve_provider(explicit: str | None = None) -> str:
    """Same resolution rules as the autonomous `LLMAgent` — keeps
    `tw2k serve --provider foo` working identically for the copilot."""
    if explicit:
        return explicit
    env = os.environ.get("TW2K_COPILOT_PROVIDER")
    if env:
        return env
    return default_provider()


# ---------------------------------------------------------------------------
# call_llm
# ---------------------------------------------------------------------------


async def call_llm(
    *,
    system: str,
    user: str,
    provider: str | None = None,
    model: str | None = None,
    timeout_s: float = 30.0,
    context: dict[str, Any] | None = None,
) -> str:
    """Run a single-shot LLM call, return raw text.

    `provider="mock:<tag>"` routes to a registered mock responder.
    `provider="none"` raises (caller should guard on that case).
    """
    provider = resolve_provider(provider)
    context = context or {}

    if provider.startswith("mock:"):
        tag = provider.split(":", 1)[1]
        fn = _mock_responders.get(tag)
        if fn is None:
            raise RuntimeError(f"no mock responder registered for tag {tag!r}")
        return await fn(system, user, context)

    if provider == "none":
        raise RuntimeError(
            "no LLM provider configured — set XAI_API_KEY / ANTHROPIC_API_KEY / "
            "OPENAI_API_KEY / TW2K_CUSTOM_BASE_URL, or pass provider='mock:...' "
            "for scripted dev."
        )

    model = model or default_model(provider)
    if provider == "anthropic":
        return await asyncio.wait_for(
            _call_anthropic(system, user, model), timeout=timeout_s
        )
    # All others are OpenAI-API-compatible.
    return await asyncio.wait_for(
        _call_openai_compatible(system, user, model, provider), timeout=timeout_s
    )


async def _call_anthropic(system: str, user: str, model: str) -> str:
    import anthropic

    client = anthropic.AsyncAnthropic()
    try:
        msg = await client.messages.create(
            model=model,
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    finally:
        # Anthropic client reuses internal http client; closing here keeps our
        # lifecycle simple (one-shot call per copilot turn).
        close = getattr(client, "close", None)
        if callable(close):
            try:
                await close()
            except Exception:
                pass
    return "".join(
        b.text for b in msg.content if getattr(b, "type", None) == "text"
    )


async def _call_openai_compatible(
    system: str, user: str, model: str, provider: str
) -> str:
    import openai

    if provider == "openai":
        client = openai.AsyncOpenAI()
    elif provider == "deepseek":
        client = openai.AsyncOpenAI(
            api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url=DEEPSEEK_BASE_URL
        )
    elif provider == "xai":
        client = openai.AsyncOpenAI(
            api_key=(
                os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")
            ),
            base_url=XAI_BASE_URL,
        )
    elif provider == "custom":
        base_url = os.environ.get("TW2K_CUSTOM_BASE_URL", CUSTOM_BASE_URL)
        if not base_url:
            raise RuntimeError("TW2K_CUSTOM_BASE_URL is not set")
        api_key = (
            os.environ.get("TW2K_CUSTOM_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or "sk-placeholder"
        )
        client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
    else:
        raise RuntimeError(f"unknown OpenAI-compatible provider {provider!r}")

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": 800,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    # The copilot emits strict JSON — request JSON mode where the provider
    # supports it. xAI/Custom vary by model, so those remain opt-in via env.
    if provider in ("openai", "deepseek"):
        kwargs["response_format"] = {"type": "json_object"}
    if provider == "custom":
        kwargs["extra_body"] = {"keep_alive": CUSTOM_KEEP_ALIVE}

    try:
        resp = await client.chat.completions.create(**kwargs)
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            try:
                await close()
            except Exception:
                pass
    return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

_JSON_OBJ_RE = re.compile(r"\{[\s\S]*\}\s*$")


def parse_tool_response(raw: str) -> list[ToolCall]:
    """Parse our copilot JSON envelope into an ordered list of ToolCalls.

    Expected envelopes (either accepted):

        {"tool": "warp", "arguments": {"target": 874}, "thought": "..."}

    or a multi-step plan:

        {"plan": [
           {"tool": "warp", "arguments": {"target": 874}},
           {"tool": "sell", "arguments": {"commodity": "fuel_ore", "qty": 50}},
         ], "thought": "..."}

    The function is forgiving: it strips markdown code fences, pulls the
    last JSON object out of mixed prose, and accepts `tool`/`name`,
    `arguments`/`args`. On any unrecoverable parse failure returns `[]`
    (the caller treats that as "ask the human to retry").
    """
    if not raw:
        return []
    s = raw.strip()
    # Strip ```json ... ``` fences anywhere in the text by cutting between
    # the first ``` and the last ``` that surround our JSON.
    if "```" in s:
        # Replace fence markers with nothing; the JSON object is the only
        # thing we care about and _JSON_OBJ_RE below still finds it.
        s = s.replace("```json", "```")
        parts = s.split("```")
        # Prefer the biggest `{...}` chunk inside fences, else the whole text.
        best = max(parts, key=len) if parts else s
        s = best
    # Extract from first "{" to matching last "}" — handles cases where the
    # LLM prefixed the JSON with prose ("Here's what I'd do:\n{...}").
    first = s.find("{")
    last = s.rfind("}")
    if first != -1 and last != -1 and last > first:
        s = s[first : last + 1]
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return []
    if not isinstance(obj, dict):
        return []

    # Shared thought (outer envelope) applies to any tool that doesn't set
    # its own — useful when the LLM writes "here's my plan and why" up top.
    outer_thought = obj.get("thought") or obj.get("rationale") or ""

    def _one(d: dict[str, Any]) -> ToolCall | None:
        name = d.get("tool") or d.get("name")
        if not isinstance(name, str):
            return None
        args = d.get("arguments") or d.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        thought = d.get("thought") or outer_thought or ""
        return ToolCall(name=name, arguments=args, thought=str(thought))

    if "plan" in obj and isinstance(obj["plan"], list):
        out: list[ToolCall] = []
        for item in obj["plan"]:
            if isinstance(item, dict):
                tc = _one(item)
                if tc is not None:
                    out.append(tc)
        return out

    # Single tool call envelope.
    tc = _one(obj)
    return [tc] if tc is not None else []
