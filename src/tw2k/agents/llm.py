"""LLM-driven agent. Supports Anthropic (Claude) and OpenAI backends.

Falls back to HeuristicAgent behavior if:
- No API key is configured
- The LLM call errors repeatedly
- The response can't be parsed

Emits an AGENT_ERROR event via its action (as a WAIT with a thought describing the problem)
so spectators see when the LLM misbehaves rather than silently failing.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

from ..engine import Action, ActionKind, Observation
from .base import BaseAgent
from .heuristic import HeuristicAgent
from .prompts import SYSTEM_PROMPT, format_observation

# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------


def default_provider() -> str:
    # Explicit custom endpoint takes precedence — lets users point at self-hosted
    # OpenAI-compatible servers (LiteLLM, vLLM, Ollama, OpenWebUI, tinybox, etc.).
    if os.environ.get("TW2K_CUSTOM_BASE_URL"):
        return "custom"
    if os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY"):
        return "xai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek"
    return "none"


DEFAULT_ANTHROPIC_MODEL = os.environ.get("TW2K_ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
DEFAULT_OPENAI_MODEL = os.environ.get("TW2K_OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_DEEPSEEK_MODEL = os.environ.get("TW2K_DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.environ.get("TW2K_DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEFAULT_CUSTOM_MODEL = os.environ.get("TW2K_CUSTOM_MODEL", "gpt-4o-mini")
CUSTOM_BASE_URL = os.environ.get("TW2K_CUSTOM_BASE_URL", "")
DEFAULT_XAI_MODEL = os.environ.get("TW2K_XAI_MODEL", "grok-4-1-fast-reasoning")
XAI_BASE_URL = os.environ.get("TW2K_XAI_BASE_URL", "https://api.x.ai/v1")
# Keep Ollama-resident models from unloading between turns. Ollama's native arg
# is passed via `extra_body` since the OpenAI-compat endpoint accepts it.
CUSTOM_KEEP_ALIVE = os.environ.get("TW2K_CUSTOM_KEEP_ALIVE", "30m")


# ---------------------------------------------------------------------------
# LLM agent
# ---------------------------------------------------------------------------


class LLMAgent(BaseAgent):
    kind = "llm"

    def __init__(
        self,
        player_id: str,
        name: str,
        provider: str | None = None,
        model: str | None = None,
        think_cap_s: float | None = None,
    ):
        super().__init__(player_id, name)
        self.provider = provider or default_provider()
        self.model = model or self._default_model()
        # Per-turn timeout. Cold-load is handled separately by warmup(); this budget
        # covers steady-state generation once the model is resident.
        default_timeout = 20.0
        if self.provider == "custom":
            default_timeout = 300.0  # local 30–120B models can be slow per-token
        if self.provider == "xai":
            default_timeout = 120.0  # reasoning models think before replying
        try:
            env_cap = float(os.environ.get("TW2K_THINK_CAP_S", ""))
        except ValueError:
            env_cap = 0.0
        self.think_cap_s = think_cap_s if think_cap_s is not None else (env_cap or default_timeout)
        # Warmup timeout — how long we'll wait for a cold model to first respond.
        try:
            self.warmup_timeout_s = float(os.environ.get("TW2K_WARMUP_TIMEOUT_S", "900"))
        except ValueError:
            self.warmup_timeout_s = 900.0
        self._fallback = HeuristicAgent(player_id, name + " (heuristic fallback)")
        self._client = None
        self._consecutive_failures = 0
        self._warmed = False

    def _default_model(self) -> str:
        if self.provider == "anthropic":
            return DEFAULT_ANTHROPIC_MODEL
        if self.provider == "openai":
            return DEFAULT_OPENAI_MODEL
        if self.provider == "deepseek":
            return DEFAULT_DEEPSEEK_MODEL
        if self.provider == "custom":
            return DEFAULT_CUSTOM_MODEL
        if self.provider == "xai":
            return DEFAULT_XAI_MODEL
        return ""

    # ---------- lifecycle ---------- #

    async def close(self) -> None:
        client = self._client
        if client is not None and hasattr(client, "close"):
            try:
                await client.close()  # type: ignore[misc]
            except Exception:
                pass

    async def warmup(self) -> tuple[bool, str]:
        """Force the backend to load the model into memory.

        Returns (ok, message). Safe to call multiple times — only the first
        actual backend call does the cold load; subsequent calls are fast
        no-ops as long as the provider keeps the model resident.

        For `custom` (Ollama-compatible) providers, uses Ollama's `keep_alive`
        so the model stays resident for TW2K_CUSTOM_KEEP_ALIVE (default 30m).
        """
        if self.provider in ("none",) or self._warmed:
            self._warmed = True
            return (True, "already warm")
        try:
            raw = await asyncio.wait_for(
                self._call_warmup(), timeout=self.warmup_timeout_s
            )
            self._warmed = True
            return (True, (raw or "").strip()[:80] or "ok")
        except TimeoutError:
            return (False, f"warmup timed out after {self.warmup_timeout_s:.0f}s")
        except Exception as exc:
            return (False, f"{type(exc).__name__}: {exc}")

    async def _call_warmup(self) -> str:
        """Tiny prompt just to trigger model loading. Minimal token budget."""
        messages = [{"role": "user", "content": "Reply with just: ok"}]
        if self.provider == "anthropic":
            if self._client is None:
                import anthropic
                self._client = anthropic.AsyncAnthropic()
            msg = await self._client.messages.create(  # type: ignore[union-attr]
                model=self.model,
                max_tokens=8,
                messages=messages,
            )
            return "".join(
                b.text for b in msg.content if getattr(b, "type", None) == "text"
            )
        # All OpenAI-compatible backends
        client = await self._ensure_openai_client()
        # Reasoning models spend most of their budget on hidden thinking tokens,
        # so we need a bigger warmup cap for them to actually emit any text.
        warmup_tokens = 64 if self.provider == "xai" else 8
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": warmup_tokens,
            "temperature": 0.0,
            "messages": messages,
        }
        if self.provider == "custom":
            kwargs["extra_body"] = {"keep_alive": CUSTOM_KEEP_ALIVE}
        resp = await client.chat.completions.create(**kwargs)  # type: ignore[union-attr]
        return resp.choices[0].message.content or ""

    async def _ensure_openai_client(self):
        """Lazily build the right AsyncOpenAI client for current provider."""
        if self._client is not None:
            return self._client
        import openai

        if self.provider == "openai":
            self._client = openai.AsyncOpenAI()
        elif self.provider == "deepseek":
            api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
            self._client = openai.AsyncOpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
        elif self.provider == "xai":
            api_key = (
                os.environ.get("XAI_API_KEY")
                or os.environ.get("GROK_API_KEY")
                or os.environ.get("OPENAI_API_KEY")
            )
            if not api_key:
                raise RuntimeError(
                    "No xAI API key — set XAI_API_KEY (or GROK_API_KEY). "
                    "Get one at https://console.x.ai/."
                )
            self._client = openai.AsyncOpenAI(api_key=api_key, base_url=XAI_BASE_URL)
        elif self.provider == "custom":
            base_url = os.environ.get("TW2K_CUSTOM_BASE_URL", CUSTOM_BASE_URL)
            if not base_url:
                raise RuntimeError("TW2K_CUSTOM_BASE_URL is not set")
            api_key = (
                os.environ.get("TW2K_CUSTOM_API_KEY")
                or os.environ.get("OPENAI_API_KEY")
                or os.environ.get("DEEPSEEK_API_KEY")
                or "sk-placeholder"
            )
            self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            raise RuntimeError(f"no OpenAI-compat client for provider {self.provider}")
        return self._client

    # ---------- act ---------- #

    async def act(self, obs: Observation) -> Action:
        if self.provider == "none":
            return await self._fallback.act(obs)

        prompt = format_observation(obs)
        # First call on a cold model gets extra grace so we don't punish warmup.
        timeout = self.warmup_timeout_s if not self._warmed else self.think_cap_s
        try:
            raw = await asyncio.wait_for(self._call(prompt), timeout=timeout)
            self._warmed = True
        except TimeoutError:
            self._consecutive_failures += 1
            if self._consecutive_failures >= 5:
                return await self._fallback.act(obs)
            return Action(kind=ActionKind.WAIT, thought=f"[LLM timeout after {timeout:.0f}s] resting a tick.")
        except Exception as exc:
            self._consecutive_failures += 1
            if self._consecutive_failures >= 5:
                return await self._fallback.act(obs)
            return Action(kind=ActionKind.WAIT, thought=f"[LLM error] {type(exc).__name__}: {exc}")

        self._consecutive_failures = 0

        parsed = _parse_response(raw)
        if parsed is None:
            return Action(kind=ActionKind.WAIT, thought=f"[parse error] couldn't parse: {raw[:200]}")

        return parsed

    # ---------- provider-specific calls ---------- #

    async def _call(self, observation_json: str) -> str:
        if self.provider == "anthropic":
            return await self._call_anthropic(observation_json)
        if self.provider == "openai":
            return await self._call_openai(observation_json)
        if self.provider == "deepseek":
            return await self._call_deepseek(observation_json)
        if self.provider == "custom":
            return await self._call_custom(observation_json)
        if self.provider == "xai":
            return await self._call_xai(observation_json)
        raise RuntimeError(f"Unknown provider {self.provider}")

    async def _call_anthropic(self, observation_json: str) -> str:
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic()
        msg = await self._client.messages.create(  # type: ignore[union-attr]
            model=self.model,
            max_tokens=900,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": observation_json}],
        )
        parts = []
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "".join(parts)

    async def _call_openai(self, observation_json: str) -> str:
        client = await self._ensure_openai_client()
        resp = await client.chat.completions.create(  # type: ignore[union-attr]
            model=self.model,
            max_tokens=900,
            temperature=0.6,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": observation_json},
            ],
        )
        return resp.choices[0].message.content or ""

    async def _call_custom(self, observation_json: str) -> str:
        """Self-hosted OpenAI-compatible endpoint.

        Configured via env:
          TW2K_CUSTOM_BASE_URL    — e.g. https://tinybox.silverstarindustries.com/ollama/v1
          TW2K_CUSTOM_API_KEY     — bearer token (falls back to OPENAI_API_KEY)
          TW2K_CUSTOM_MODEL       — model name to request
          TW2K_CUSTOM_KEEP_ALIVE  — Ollama keep_alive duration (default 30m)
          TW2K_CUSTOM_JSON_MODE   — "1" to request JSON response_format (default off —
                                    many self-hosted servers reject unknown fields)
          TW2K_CUSTOM_MAX_TOKENS  — output token budget per turn (default 700)
        """
        client = await self._ensure_openai_client()
        try:
            max_tokens = int(os.environ.get("TW2K_CUSTOM_MAX_TOKENS", "700"))
        except ValueError:
            max_tokens = 700
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": 0.6,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": observation_json},
            ],
            # Keep Ollama-resident models pinned between turns so we don't pay
            # the cold-load tax on every call.
            "extra_body": {"keep_alive": CUSTOM_KEEP_ALIVE},
        }
        if os.environ.get("TW2K_CUSTOM_JSON_MODE", "").strip() in ("1", "true", "yes"):
            kwargs["response_format"] = {"type": "json_object"}
        resp = await client.chat.completions.create(**kwargs)  # type: ignore[union-attr]
        return resp.choices[0].message.content or ""

    async def _call_deepseek(self, observation_json: str) -> str:
        """DeepSeek is OpenAI-API-compatible — same SDK, different base_url."""
        client = await self._ensure_openai_client()
        resp = await client.chat.completions.create(  # type: ignore[union-attr]
            model=self.model,
            max_tokens=900,
            temperature=0.6,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": observation_json},
            ],
        )
        return resp.choices[0].message.content or ""

    async def _call_xai(self, observation_json: str) -> str:
        """xAI Grok is OpenAI-API-compatible at https://api.x.ai/v1.

        Reasoning models (like grok-4-1-fast-reasoning) produce tokens after a
        hidden thinking phase, so we give them a generous output budget and
        skip `response_format` (xAI JSON-mode support varies by model).
        """
        client = await self._ensure_openai_client()
        try:
            max_tokens = int(os.environ.get("TW2K_XAI_MAX_TOKENS", "1200"))
        except ValueError:
            max_tokens = 1200
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": 0.6,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": observation_json},
            ],
        }
        if os.environ.get("TW2K_XAI_JSON_MODE", "").strip() in ("1", "true", "yes"):
            kwargs["response_format"] = {"type": "json_object"}
        resp = await client.chat.completions.create(**kwargs)  # type: ignore[union-attr]
        return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}\s*$")


def _parse_response(raw: str) -> Action | None:
    raw = raw.strip()
    if not raw:
        return None

    # Strip ```json fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)

    # Fallback: find the last top-level { ... } block
    data: dict[str, Any] | None = None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_BLOCK_RE.search(raw)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    if not isinstance(data, dict):
        return None

    action_obj = data.get("action")
    if not isinstance(action_obj, dict):
        return None
    kind_raw = action_obj.get("kind", "")
    args = action_obj.get("args") or {}
    if not isinstance(args, dict):
        args = {}

    try:
        kind = ActionKind(kind_raw)
    except ValueError:
        # Normalize common mistakes
        aliases = {
            "move": ActionKind.WARP,
            "buy": ActionKind.TRADE,
            "sell": ActionKind.TRADE,
            "message": ActionKind.HAIL,
            "send": ActionKind.HAIL,
            "idle": ActionKind.WAIT,
            "pass": ActionKind.WAIT,
            "noop": ActionKind.WAIT,
        }
        kind = aliases.get(kind_raw)
        if kind is None:
            return None
        # If the alias is buy/sell, infer side
        if kind_raw == "buy":
            args.setdefault("side", "buy")
        elif kind_raw == "sell":
            args.setdefault("side", "sell")

    return Action(
        kind=kind,
        args=args,
        thought=str(data.get("thought") or "")[:1500],
        scratchpad_update=(
            str(data["scratchpad_update"])[:8000]
            if "scratchpad_update" in data and data["scratchpad_update"] is not None
            else None
        ),
    )
