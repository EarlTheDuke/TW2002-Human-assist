"""Phase H4 UI smoke tests — TTS, interrupt listener, escalation banner.

Parses web/play.{html,css,js} as text and asserts the contract for the
H4 browser-side additions:

* A TTS toggle button + speaking indicator.
* An escalation banner that raises on critical safety signals.
* JS helpers for speechSynthesis wrapping, always-on interrupt
  listener, and safety polling on mode change.
* Interrupt-word list includes at least "stop"/"hold"/"pause" so the
  copilot can be halted by voice while autopilot is running.

Pipecat / server-side STT is still explicitly *not* in scope here —
H4 remains a browser-only feature layered on the H2 copilot pipeline.
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


def test_tts_toggle_button_in_html(play_html: str) -> None:
    assert 'id="ttsToggleBtn"' in play_html
    assert 'aria-pressed="false"' in play_html


def test_escalation_banner_present_in_html(play_html: str) -> None:
    for elem_id in (
        "copilotEscalation",
        "copilotEscalationTitle",
        "copilotEscalationReason",
        "copilotEscalationDismiss",
    ):
        assert f'id="{elem_id}"' in play_html, f"missing #{elem_id}"
    assert 'role="alert"' in play_html


def test_tagline_advertises_voice_in_out(play_html: str) -> None:
    lower = play_html.lower()
    assert "h4" in lower or "voice in + out" in lower or "voice out" in lower


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------


def test_css_has_tts_and_escalation_states(play_css: str) -> None:
    assert ".tts-toggle" in play_css
    assert ".tts-toggle.is-on" in play_css
    assert ".tts-toggle.is-speaking" in play_css
    assert ".copilot-escalation" in play_css
    assert ".ptt-btn.is-interrupt-listen" in play_css


def test_css_escalation_is_visually_loud(play_css: str) -> None:
    # Red/bad border + a flashing animation are part of the contract
    # — the banner must jump out.
    assert "var(--bad)" in play_css or "#ff" in play_css
    assert "esc-flash" in play_css


# ---------------------------------------------------------------------------
# JS wiring
# ---------------------------------------------------------------------------


def test_js_exposes_tts_helpers(play_js: str) -> None:
    for name in ("speakCopilot", "maybeSpeakMessage", "setTtsEnabled", "wireTts"):
        assert name in play_js, f"{name} missing"
    assert "speechSynthesis" in play_js
    assert "SpeechSynthesisUtterance" in play_js
    assert "window.__tw2kTts" in play_js


def test_js_persists_tts_preference(play_js: str) -> None:
    # We use localStorage so the user's voice-on/off choice survives
    # page reloads without a round-trip to the server.
    assert "tw2k.tts.enabled" in play_js
    assert "localStorage" in play_js


def test_js_has_interrupt_listener(play_js: str) -> None:
    for name in (
        "initInterruptListener",
        "startInterruptListening",
        "stopInterruptListening",
        "syncInterruptListenerToMode",
    ):
        assert name in play_js, f"{name} missing"
    # Must include the core interrupt vocabulary.
    for word in ("stop", "hold", "pause", "cancel", "abort"):
        assert f'"{word}"' in play_js, f"interrupt word {word!r} missing"
    assert "INTERRUPT_RE" in play_js
    assert "window.__tw2kInterrupt" in play_js


def test_js_interrupt_mode_sync_wires_to_setcopilotmode(play_js: str) -> None:
    # setCopilotMode must trigger the interrupt listener transition AND
    # a safety poll so the banner rises without a round-trip.
    assert "syncInterruptListenerToMode" in play_js
    assert "pollSafetyForMode" in play_js
    assert "/api/copilot/safety" in play_js


def test_js_escalation_message_handler_present(play_js: str) -> None:
    # When the server broadcasts a copilot_chat with kind=escalation, the
    # UI must surface the banner (and TTS should speak it).
    assert 'kind === "escalation"' in play_js
    assert "showEscalation" in play_js


def test_js_tts_debounces_duplicates(play_js: str) -> None:
    # Rapid-fire progress events shouldn't cause overlapping speech.
    # The debouncer lives in speakCopilot.
    assert "lastUtteranceTs" in play_js
    assert "lastText" in play_js
