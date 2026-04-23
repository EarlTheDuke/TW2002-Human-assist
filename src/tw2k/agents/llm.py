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
import shutil
from dataclasses import dataclass, field
from typing import Any

from ..engine import Action, ActionKind, Observation
from .base import BaseAgent
from .heuristic import HeuristicAgent
from .prompts import format_observation, get_system_prompt

# ---------------------------------------------------------------------------
# Provider-response diagnostics (M3-1 proper fix)
# ---------------------------------------------------------------------------
#
# Reasoning models served through OpenWebUI + Ollama (e.g. qwen3.5:122b) often
# return an empty `choices[0].message.content` and place the actual answer
# in `choices[0].message.reasoning` — especially when upstream enforces
# `response_format=json_object`. A naive `.content or ''` read therefore
# silently dropped 335/1168 turns in Match 4 (~29% of all LLM calls).
#
# `_coalesce_message_text` falls back to `reasoning` when `content` is empty
# and returns a `_ResponseDiag` we surface in the parse-error thought, so
# spectators (and us) can see WHY a turn was wasted instead of just a bare
# "[parse error] couldn't parse:".


@dataclass
class _ResponseDiag:
    """Structured summary of one chat-completion response for error logs."""

    finish_reason: str = ""
    source: str = ""  # "content" | "reasoning" | "empty"
    content_len: int = 0
    reasoning_len: int = 0
    content_preview: str = ""
    reasoning_preview: str = ""
    extras: dict[str, Any] = field(default_factory=dict)

    def short(self) -> str:
        parts = [
            f"finish={self.finish_reason or '?'}",
            f"src={self.source or 'empty'}",
            f"content_len={self.content_len}",
            f"reasoning_len={self.reasoning_len}",
        ]
        if self.content_preview:
            parts.append(f'content="{self.content_preview}"')
        if self.reasoning_preview:
            parts.append(f'reasoning="{self.reasoning_preview}"')
        return " ".join(parts)


def _preview(s: str | None, limit: int = 180) -> str:
    if not s:
        return ""
    s = s.replace("\n", " ").replace("\r", " ").strip()
    if len(s) > limit:
        s = s[:limit] + "..."
    return s


def _coalesce_message_text(
    resp: Any, *, prefer: str = "content"
) -> tuple[str, _ResponseDiag]:
    """Return (text, diag) from a chat-completion response.

    Preference order (with prefer="content"):
      1. message.content
      2. message.reasoning   -- OWUI/Ollama reasoning models push JSON here
      3. ""                  -- diag.source == "empty"
    """
    diag = _ResponseDiag()
    try:
        choice = resp.choices[0]
    except (AttributeError, IndexError, TypeError):
        return "", diag
    msg = getattr(choice, "message", None)
    if msg is None:
        diag.finish_reason = str(getattr(choice, "finish_reason", "") or "")
        return "", diag

    content = getattr(msg, "content", None) or ""
    reasoning = getattr(msg, "reasoning", None) or ""
    if not reasoning:
        # OWUI variants nest reasoning in model_extra under various names.
        extra = getattr(msg, "model_extra", None)
        if isinstance(extra, dict):
            reasoning = str(
                extra.get("reasoning")
                or extra.get("reasoning_content")
                or extra.get("thinking")
                or ""
            )

    diag.finish_reason = str(getattr(choice, "finish_reason", "") or "")
    diag.content_len = len(content)
    diag.reasoning_len = len(reasoning)
    diag.content_preview = _preview(content)
    diag.reasoning_preview = _preview(reasoning)

    if prefer == "reasoning" and reasoning.strip():
        diag.source = "reasoning"
        return reasoning, diag
    if content.strip():
        diag.source = "content"
        return content, diag
    if reasoning.strip():
        diag.source = "reasoning"
        return reasoning, diag
    diag.source = "empty"
    return "", diag


def _cursor_cmdline_budget() -> int:
    try:
        return int(os.environ.get("TW2K_CURSOR_CMDLINE_BUDGET", "30000"))
    except ValueError:
        return 30000


def _cursor_system_prompt_for(observation_json: str) -> str:
    """Return the system prompt for a Cursor CLI turn.

    Windows `CreateProcess` command lines are capped (~32k chars). Full
    coaching prompt + observation can exceed that, so we temporarily
    switch to `TW2K_HINT_LEVEL=minimal` for this read only when needed.
    """
    full = get_system_prompt()
    overhead = 600  # delimiter text + safety margin
    if len(full) + len(observation_json) + overhead <= _cursor_cmdline_budget():
        return full
    old = os.environ.get("TW2K_HINT_LEVEL")
    os.environ["TW2K_HINT_LEVEL"] = "minimal"
    try:
        return get_system_prompt()
    finally:
        if old is None:
            os.environ.pop("TW2K_HINT_LEVEL", None)
        else:
            os.environ["TW2K_HINT_LEVEL"] = old


def _resolve_cursor_cli() -> tuple[str | None, str | None, str | None]:
    """Locate the Cursor Agent CLI entry points.

    Returns ``(node_exe, index_js, wrapper_cli)``. Prefer the first pair
    when non-None — invoking ``node.exe index.js ...`` bypasses the
    ``.cmd`` wrapper and its 8191-char `cmd.exe` command-line cap, which
    would otherwise break any real TW2K observation payload.
    """
    node = (os.environ.get("TW2K_CURSOR_NODE") or "").strip() or None
    js = (os.environ.get("TW2K_CURSOR_JS") or "").strip() or None
    if node and js and os.path.isfile(node) and os.path.isfile(js):
        return node, js, None

    cli = (os.environ.get("TW2K_CURSOR_CLI") or "").strip() or shutil.which("agent")
    if not cli:
        return None, None, None

    base = os.path.dirname(cli)
    versions_dir = os.path.join(base, "versions")
    if os.path.isdir(versions_dir):
        try:
            entries = [
                os.path.join(versions_dir, name)
                for name in os.listdir(versions_dir)
                if os.path.isdir(os.path.join(versions_dir, name))
            ]
            # Version dir names are YYYY.MM.DD-commit — lexicographic sort
            # correctly identifies the latest build.
            entries.sort(reverse=True)
            for ver in entries:
                cand_node = os.path.join(ver, "node.exe")
                cand_js = os.path.join(ver, "index.js")
                if os.path.isfile(cand_node) and os.path.isfile(cand_js):
                    return cand_node, cand_js, cli
        except OSError:
            pass
    return None, None, cli


def _unwrap_agent_print_json(stdout: str) -> str:
    """Extract assistant text from `agent --print --output-format json` stdout."""
    s = (stdout or "").strip()
    if not s:
        return ""
    try:
        outer = json.loads(s)
    except json.JSONDecodeError:
        return s
    if isinstance(outer, str):
        return outer
    if not isinstance(outer, dict):
        return s
    for key in ("text", "message", "content", "result", "output", "response", "answer"):
        v = outer.get(key)
        if isinstance(v, str) and v.strip():
            return v
    msg = outer.get("message")
    if isinstance(msg, dict):
        for key in ("content", "text"):
            v = msg.get(key)
            if isinstance(v, str) and v.strip():
                return v
    return s


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
# Cursor Agent CLI (`agent` from https://cursor.com/install) — subprocess provider.
DEFAULT_CURSOR_MODEL = os.environ.get("TW2K_CURSOR_MODEL", "composer-2-fast")


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
        if self.provider == "cursor":
            default_timeout = 120.0  # Cursor Agent CLI round-trip + cloud model
        try:
            env_cap = float(os.environ.get("TW2K_THINK_CAP_S", ""))
        except ValueError:
            env_cap = 0.0
        self.think_cap_s = think_cap_s if think_cap_s is not None else (env_cap or default_timeout)
        if self.provider == "cursor":
            try:
                ccap = float(os.environ.get("TW2K_CURSOR_THINK_CAP_S", ""))
            except ValueError:
                ccap = 0.0
            if ccap > 0:
                self.think_cap_s = ccap
        # Warmup timeout — how long we'll wait for a cold model to first respond.
        try:
            self.warmup_timeout_s = float(os.environ.get("TW2K_WARMUP_TIMEOUT_S", "900"))
        except ValueError:
            self.warmup_timeout_s = 900.0
        self._fallback = HeuristicAgent(player_id, name + " (heuristic fallback)")
        self._client = None
        self._consecutive_failures = 0
        self._warmed = False
        # Last provider-response diagnostics. Populated by every _call_* path
        # and consumed by act() when the parser fails so we can surface
        # finish_reason / content-vs-reasoning info in the agent thought
        # instead of a bare "[parse error] couldn't parse:" line.
        self._last_diag: _ResponseDiag | None = None

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
        if self.provider == "cursor":
            return DEFAULT_CURSOR_MODEL
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
        if self.provider == "cursor":
            return await self._invoke_cursor_cli(
                "Reply with the single word ok and nothing else."
            )
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
        text, _ = _coalesce_message_text(resp)
        return text

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
            # Match 13 — early-warning thought at exactly 3 consecutive
            # timeouts so the spectator feed surfaces the problem BEFORE
            # the silent heuristic fallback kicks in at 5. Without this,
            # operators only notice the fallback AFTER it's happened
            # (agent stops using LLM-grade reasoning, hard to diagnose
            # mid-match because the heuristic's thoughts look coherent).
            if self._consecutive_failures == 3:
                return Action(
                    kind=ActionKind.WAIT,
                    thought=(
                        f"[LLM timeout after {timeout:.0f}s] *** 3 consecutive "
                        f"timeouts — 2 more will trigger heuristic fallback. "
                        f"Operator: check model health. ***"
                    ),
                )
            return Action(kind=ActionKind.WAIT, thought=f"[LLM timeout after {timeout:.0f}s] resting a tick.")
        except Exception as exc:
            self._consecutive_failures += 1
            if self._consecutive_failures >= 5:
                return await self._fallback.act(obs)
            return Action(kind=ActionKind.WAIT, thought=f"[LLM error] {type(exc).__name__}: {exc}")

        self._consecutive_failures = 0

        parsed = _parse_response(raw)
        if parsed is None:
            # Enriched parse-error thought: surface finish_reason + which
            # channel (content vs reasoning) the text came from + a short
            # preview of each so we can diagnose M3-1-class issues directly
            # from the event feed. If no diag (e.g. Anthropic path that
            # doesn't populate one yet), fall back to the raw preview.
            diag = self._last_diag
            if diag is not None:
                return Action(
                    kind=ActionKind.WAIT,
                    thought=f"[parse error] {diag.short()}",
                )
            return Action(
                kind=ActionKind.WAIT,
                thought=f"[parse error] couldn't parse: {raw[:200]}",
            )

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
        if self.provider == "cursor":
            return await self._call_cursor(observation_json)
        raise RuntimeError(f"Unknown provider {self.provider}")

    async def _invoke_cursor_cli(self, prompt: str) -> str:
        """Run `agent -p` headlessly; return raw assistant text (may be JSON-wrapped).

        Windows `cmd.exe` caps command lines at ~8191 chars, and the
        `agent` entry point is a `.cmd` wrapper — so any non-trivial
        TW2K observation overflows it. We avoid that by locating the
        bundled ``node.exe`` + ``index.js`` next to the wrapper and
        invoking them directly via `CreateProcess` (32767-char limit).
        Override paths with ``TW2K_CURSOR_NODE`` / ``TW2K_CURSOR_JS``.
        """
        ws = (os.environ.get("TW2K_CURSOR_WORKSPACE") or "").strip() or os.getcwd()
        node_exe, index_js, cli_fallback = _resolve_cursor_cli()
        if not node_exe or not index_js:
            if not cli_fallback:
                raise RuntimeError(
                    "Cursor Agent CLI not found. Install: "
                    "irm 'https://cursor.com/install?win32=true' | iex "
                    "(PowerShell) — then `agent login` or set CURSOR_API_KEY."
                )
            argv_base: list[str] = [cli_fallback]
        else:
            argv_base = [node_exe, index_js]
        argv = argv_base + [
            "-p",
            "--output-format",
            "json",
            "--mode",
            "ask",
            "--model",
            self.model,
            "--trust",
            "--workspace",
            ws,
            prompt,
        ]
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
        )
        out_b, err_b = await proc.communicate()
        out = out_b.decode("utf-8", errors="replace")
        err = err_b.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            raise RuntimeError(
                f"agent exited {proc.returncode}"
                + (f": {err}" if err else "")
            )
        return _unwrap_agent_print_json(out)

    async def _call_cursor(self, observation_json: str) -> str:
        sys_prompt = _cursor_system_prompt_for(observation_json)
        body = (
            "=== TW2K system instructions ===\n"
            f"{sys_prompt}\n\n"
            "=== Current observation (JSON) ===\n"
            f"{observation_json}\n\n"
            "Respond with ONLY one JSON object matching the TW2K agent schema: "
            "`thought`, `scratchpad_update`, `goals` {short,medium,long}, and "
            "`action` {kind, args}. No markdown code fences, no prose before or after."
        )
        text = await self._invoke_cursor_cli(body)
        diag = _ResponseDiag(
            finish_reason="agent_cli",
            source="content" if text.strip() else "empty",
            content_len=len(text),
            content_preview=_preview(text),
        )
        self._last_diag = diag
        return text

    async def _call_anthropic(self, observation_json: str) -> str:
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic()
        msg = await self._client.messages.create(  # type: ignore[union-attr]
            model=self.model,
            max_tokens=900,
            system=get_system_prompt(),
            messages=[{"role": "user", "content": observation_json}],
        )
        parts = []
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        text = "".join(parts)
        # Mirror the OpenAI-shape diag so the parse-error path still has
        # something useful to print even on the Anthropic backend.
        diag = _ResponseDiag(
            finish_reason=str(getattr(msg, "stop_reason", "") or ""),
            source="content" if text.strip() else "empty",
            content_len=len(text),
            content_preview=_preview(text),
        )
        self._last_diag = diag
        return text

    async def _call_openai(self, observation_json: str) -> str:
        client = await self._ensure_openai_client()
        resp = await client.chat.completions.create(  # type: ignore[union-attr]
            model=self.model,
            max_tokens=900,
            temperature=0.6,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": observation_json},
            ],
        )
        text, diag = _coalesce_message_text(resp)
        self._last_diag = diag
        return text

    async def _call_custom(self, observation_json: str) -> str:
        """Self-hosted OpenAI-compatible endpoint.

        Configured via env:
          TW2K_CUSTOM_BASE_URL    — e.g. https://tinybox.silverstarindustries.com/ollama/v1
          TW2K_CUSTOM_API_KEY     — bearer token (falls back to OPENAI_API_KEY)
          TW2K_CUSTOM_MODEL       — model name to request
          TW2K_CUSTOM_KEEP_ALIVE  — Ollama keep_alive duration (default 30m)
          TW2K_CUSTOM_JSON_MODE   — "1" to request JSON response_format (default off —
                                    many self-hosted servers reject unknown fields)
          TW2K_CUSTOM_MAX_TOKENS  — output token budget per turn (default 4000).
                                    Reasoning models (qwen3.5:122b, DeepSeek-R1,
                                    QwQ) frequently spend 800-1500 tokens on a
                                    hidden reasoning pass BEFORE emitting the JSON
                                    action. Match 5 smoke at 1200 saw 12.5% of turns
                                    truncated with finish_reason=length; at 2000
                                    still ~10%. 4000 is safe on local GPUs (cost is
                                    wall-time, not $) and drives the rate toward 0.
        """
        client = await self._ensure_openai_client()
        try:
            max_tokens = int(os.environ.get("TW2K_CUSTOM_MAX_TOKENS", "4000"))
        except ValueError:
            max_tokens = 4000
        # Ollama native: num_predict caps output tokens below the server's
        # own default (often 128). Without this, OpenAI-compat `max_tokens`
        # is sometimes ignored by the Ollama backend and the model runs
        # out of budget mid-JSON.
        extra_body: dict[str, Any] = {
            "keep_alive": CUSTOM_KEEP_ALIVE,
            "num_predict": max_tokens,
        }
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": 0.6,
            "messages": [
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": observation_json},
            ],
            "extra_body": extra_body,
        }
        if os.environ.get("TW2K_CUSTOM_JSON_MODE", "").strip() in ("1", "true", "yes"):
            kwargs["response_format"] = {"type": "json_object"}
        resp = await client.chat.completions.create(**kwargs)  # type: ignore[union-attr]
        text, diag = _coalesce_message_text(resp)
        self._last_diag = diag
        return text

    async def _call_deepseek(self, observation_json: str) -> str:
        """DeepSeek is OpenAI-API-compatible — same SDK, different base_url."""
        client = await self._ensure_openai_client()
        resp = await client.chat.completions.create(  # type: ignore[union-attr]
            model=self.model,
            max_tokens=900,
            temperature=0.6,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": observation_json},
            ],
        )
        text, diag = _coalesce_message_text(resp)
        self._last_diag = diag
        return text

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
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": observation_json},
            ],
        }
        if os.environ.get("TW2K_XAI_JSON_MODE", "").strip() in ("1", "true", "yes"):
            kwargs["response_format"] = {"type": "json_object"}
        resp = await client.chat.completions.create(**kwargs)  # type: ignore[union-attr]
        text, diag = _coalesce_message_text(resp)
        self._last_diag = diag
        return text


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}\s*$")
# Reasoning models (Qwen3.5, QwQ, DeepSeek-R1, ...) often emit visible
# reasoning inside their `content` wrapped in <think>...</think> tags.
# We strip those before JSON parsing so the trailing action JSON can be
# located. Without this, ~50% of qwen3.5:122b turns failed strict parse
# and the agent fell back to WAIT (Match 3 / M3-1).
_THINK_BLOCK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)
_LEFTOVER_THINK_RE = re.compile(r"</?think>", re.IGNORECASE)


def _extract_last_json_object(text: str) -> str | None:
    """Return the substring of `text` that is the last balanced `{...}`
    block, or None if none is found. Unlike a trailing-anchored regex
    this tolerates prose AFTER the JSON block (e.g. a reasoning model
    that forgot to stop after its answer)."""
    end = text.rfind("}")
    while end >= 0:
        depth = 0
        for i in range(end, -1, -1):
            ch = text[i]
            if ch == "}":
                depth += 1
            elif ch == "{":
                depth -= 1
                if depth == 0:
                    return text[i : end + 1]
        end = text.rfind("}", 0, end)
    return None


def _parse_response(raw: str) -> Action | None:
    raw = raw.strip()
    if not raw:
        return None

    # Strip reasoning-model <think>...</think> blocks before anything else.
    raw = _THINK_BLOCK_RE.sub("", raw)
    raw = _LEFTOVER_THINK_RE.sub("", raw).strip()
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
        candidate: str | None = m.group(0) if m else None
        if candidate is None:
            candidate = _extract_last_json_object(raw)
        if candidate:
            try:
                data = json.loads(candidate)
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

    # Structured 3-horizon goals. Accept either a top-level `goals` object or
    # per-field siblings so different LLMs' preferred shapes work. The engine
    # treats None as "don't change my prior goal", "" as "clear", otherwise replace.
    goals_obj = data.get("goals") if isinstance(data.get("goals"), dict) else {}

    def _goal(key: str) -> str | None:
        # Prefer the nested form `goals.short`, fall back to top-level
        # `goal_short`. If neither is supplied, leave the goal untouched.
        if key in goals_obj:
            v = goals_obj[key]
            return str(v)[:240] if v is not None else ""
        top = f"goal_{key}"
        if top in data:
            v = data[top]
            return str(v)[:240] if v is not None else ""
        return None

    return Action(
        kind=kind,
        args=args,
        thought=str(data.get("thought") or "")[:1500],
        scratchpad_update=(
            str(data["scratchpad_update"])[:8000]
            if "scratchpad_update" in data and data["scratchpad_update"] is not None
            else None
        ),
        goal_short=_goal("short"),
        goal_medium=_goal("medium"),
        goal_long=_goal("long"),
    )
