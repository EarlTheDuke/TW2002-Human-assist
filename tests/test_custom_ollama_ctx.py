"""TW2K_CUSTOM_NUM_CTX / localhost defaults for Ollama OpenAI-compat."""

from __future__ import annotations

import pytest

from tw2k.agents.llm import _custom_ollama_context_options


@pytest.fixture(autouse=True)
def _clear_custom_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TW2K_CUSTOM_BASE_URL", raising=False)
    monkeypatch.delenv("TW2K_CUSTOM_NUM_CTX", raising=False)


def test_localhost_defaults_to_32768(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TW2K_CUSTOM_BASE_URL", "http://127.0.0.1:11434/v1")
    assert _custom_ollama_context_options() == {"num_ctx": 32768}


def test_localhost_ipv6_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TW2K_CUSTOM_BASE_URL", "http://[::1]:11434/v1")
    assert _custom_ollama_context_options() == {"num_ctx": 32768}


def test_remote_url_skips_without_explicit_ctx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TW2K_CUSTOM_BASE_URL", "https://tinybox.example/ollama/v1")
    assert _custom_ollama_context_options() is None


def test_explicit_num_ctx_for_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TW2K_CUSTOM_BASE_URL", "https://tinybox.example/ollama/v1")
    monkeypatch.setenv("TW2K_CUSTOM_NUM_CTX", "65536")
    assert _custom_ollama_context_options() == {"num_ctx": 65536}


def test_zero_disables_even_on_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TW2K_CUSTOM_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv("TW2K_CUSTOM_NUM_CTX", "0")
    assert _custom_ollama_context_options() is None


def test_effective_base_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TW2K_CUSTOM_BASE_URL", "https://tinybox.example/ollama/v1")
    assert _custom_ollama_context_options("http://127.0.0.1:11434/v1") == {"num_ctx": 32768}
