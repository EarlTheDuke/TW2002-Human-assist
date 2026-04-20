"""Phase H3 smoke tests — browser Web Speech API push-to-talk wiring.

These don't launch a browser. They parse `web/play.html`, `web/play.css`,
and `web/play.js` as text and assert the PTT contract is intact:

* The PTT button + status readout exist in the markup.
* CSS ships the listening/unsupported/error states.
* JS wires Web Speech API init, start/stop, normalization, and the
  global Space-hold behaviour.
* The shortcuts toast documents the new Space binding.
* The PTT path reuses the H2 `/api/copilot/chat` endpoint — no new
  server code required for H3, which is the point.

Phase H3 scope (docs/HUMAN_COPILOT_PLAN.md §12):
  - [x] Copilot service stays text-only; voice channel layered on top.
  - [x] Browser Web Speech API integration.
  - [x] Push-to-talk (hold Space) in /play.
  - [x] Transcript panel renders what was heard *before* the copilot acts.
  - [x] Voice grammar hints for sector numbers and commodity names.

Server-side STT via Pipecat / Deepgram is deferred (H5 polish).
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


@pytest.fixture(scope="module")
def play_html() -> str:
    return (WEB / "play.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def play_css() -> str:
    return (WEB / "play.css").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def play_js() -> str:
    return (WEB / "play.js").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Markup
# ---------------------------------------------------------------------------


def test_ptt_button_and_status_in_html(play_html: str) -> None:
    assert 'id="pttBtn"' in play_html
    assert 'id="pttStatus"' in play_html
    assert 'id="pttState"' in play_html
    assert 'id="pttPartial"' in play_html
    # Accessibility: aria-pressed toggles the listening state.
    assert 'aria-pressed="false"' in play_html
    # Accessibility: aria-live on the chat panel still present (H2 carryover).
    assert 'aria-live="polite"' in play_html


def test_shortcuts_toast_documents_space_hold(play_html: str) -> None:
    """Space = PTT-hold must be discoverable through the `?` overlay."""
    assert "<kbd>Space</kbd>" in play_html
    assert "push-to-talk" in play_html.lower()


def test_tagline_mentions_voice_phase(play_html: str) -> None:
    # Sanity: the tagline advertises the current phase so contributors
    # can quickly eyeball what's shipped.
    assert "H3" in play_html or "voice" in play_html.lower()


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------


def test_css_has_ptt_states(play_css: str) -> None:
    assert ".ptt-btn" in play_css
    assert ".ptt-btn.is-listening" in play_css
    assert ".ptt-btn.is-unsupported" in play_css
    assert "ptt-pulse" in play_css
    assert ".ptt-status" in play_css


# ---------------------------------------------------------------------------
# JS wiring
# ---------------------------------------------------------------------------


def test_js_uses_web_speech_api_with_fallback(play_js: str) -> None:
    # Feature detection covers both vendor-prefixed and unprefixed names.
    assert "SpeechRecognition" in play_js
    assert "webkitSpeechRecognition" in play_js
    # Graceful degradation — the unsupported branch must label the button.
    assert "is-unsupported" in play_js


def test_js_has_start_stop_toggle_fns(play_js: str) -> None:
    for name in ("startListening", "stopListening", "toggleListening", "initVoice"):
        assert name in play_js, f"{name} missing from play.js"


def test_js_has_global_space_ptt_hold(play_js: str) -> None:
    # The document-level keydown/keyup pair that implements hold-Space.
    assert "keydown" in play_js
    assert "keyup" in play_js
    assert 'ev.code === "Space"' in play_js
    # Guard: ignore Space while typing in a field.
    assert 'tag === "INPUT"' in play_js


def test_js_submits_final_transcript_to_chat(play_js: str) -> None:
    # On recognition.onend, the normalized transcript flows through the
    # existing H2 sendChat() helper — no new endpoint is introduced.
    assert "rec.onend" in play_js
    assert "sendChat(combined)" in play_js


def test_js_transcript_normalizer_handles_sectors_and_commodities(
    play_js: str,
) -> None:
    # Grammar hints live in the normalizeVoiceTranscript function.
    assert "normalizeVoiceTranscript" in play_js
    assert "fuel_ore" in play_js
    assert "hundred" in play_js  # number-word expansion for sectors
    assert "seventy" in play_js  # two-word compound for sector numbers


def test_js_exposes_voice_api_for_console(play_js: str) -> None:
    # We expose window.__tw2kVoice for console debugging + future
    # e2e tests (Playwright can drive normalize() directly).
    assert "window.__tw2kVoice" in play_js
