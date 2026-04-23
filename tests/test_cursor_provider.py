"""Tests for the Cursor Agent CLI (`cursor`) LLM provider."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from tw2k.agents.llm import (
    LLMAgent,
    _cursor_system_prompt_for,
    _unwrap_agent_print_json,
)
def test_unwrap_agent_print_json_prefers_text_key() -> None:
    inner = '{"thought":"t","action":{"kind":"wait","args":{}}}'
    wrapped = json.dumps({"text": inner})
    assert _unwrap_agent_print_json(wrapped) == inner


@pytest.mark.asyncio
async def test_invoke_cursor_cli_success() -> None:
    raw_action = {
        "thought": "hi",
        "action": {"kind": "wait", "args": {}},
    }
    outer = json.dumps({"text": json.dumps(raw_action)})

    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(outer.encode("utf-8"), b""))
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_proc
        ag = LLMAgent("P1", "C", provider="cursor", model="composer-2-fast")
        out = await ag._invoke_cursor_cli("ping")
    assert "wait" in out
    mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_invoke_cursor_cli_nonzero_exit() -> None:
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"", b"auth failed"))
    mock_proc.returncode = 1

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_proc
        ag = LLMAgent("P1", "C", provider="cursor", model="m")
        with pytest.raises(RuntimeError, match="agent exited"):
            await ag._invoke_cursor_cli("ping")


@pytest.mark.asyncio
async def test_call_cursor_populates_last_diag() -> None:
    raw_action = {
        "thought": "t",
        "action": {"kind": "scan", "args": {}},
    }
    outer = json.dumps({"text": json.dumps(raw_action)})

    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(outer.encode("utf-8"), b""))
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_proc
        ag = LLMAgent("P1", "C", provider="cursor", model="composer-2-fast")
        text = await ag._call_cursor('{"obs":true}')
    assert "scan" in text
    assert ag._last_diag is not None
    assert ag._last_diag.content_len == len(text)


def test_cursor_system_prompt_shrinks_when_over_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TW2K_HINT_LEVEL", "full")
    monkeypatch.setenv("TW2K_CURSOR_CMDLINE_BUDGET", "8000")
    from tw2k.agents.prompts import get_system_prompt

    full_len = len(get_system_prompt())
    huge_obs = "x" * 50000
    shrunk = _cursor_system_prompt_for(huge_obs)
    assert len(shrunk) < full_len
