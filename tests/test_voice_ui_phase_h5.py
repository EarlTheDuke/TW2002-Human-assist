"""Phase H5 UI smoke tests — memory panel, what-if preview, i18n, mobile.

These asserts keep the cockpit HTML/CSS/JS honest without spinning up
a headless browser. Every H5 UI deliverable is represented here:

* **H5.1 Memory panel**: `<details class="copilot-memory">` section,
  `#copilotMemoryChip` summary, remember form, forget buttons, and the
  JS helpers (`memoryRemember`, `memoryForget`, `renderMemory`,
  `fetchMemorySnapshot`).
* **H5.3 i18n + mobile**: `<select id="voiceLangSelect">`, BCP-47
  options, `applyVoiceLang`, `VOICE_LANG_KEY` localStorage, and mobile
  media queries at 900px / 720px that stack the cockpit + enlarge
  touch targets.
* **H5.4 What-if preview**: `#copilotWhatIf` + `#copilotWhatIfOneLiner`
  markup, CSS classes for positive/negative deltas, and the JS
  `fetchWhatIf` / `renderWhatIf` helpers.
* Tagline advertises Phase H5 so we can eyeball which phase a running
  build is on.
* Debug hooks `window.__tw2kMem`, `window.__tw2kWhatIf`,
  `window.__tw2kVoiceLang` are exposed so Playwright / manual console
  can poke the new features without new endpoints.
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


def test_tagline_reads_phase_h5(play_html: str) -> None:
    lower = play_html.lower()
    assert "h5" in lower or "phase h5" in lower


def test_voice_lang_selector_present(play_html: str) -> None:
    assert 'id="voiceLangSelect"' in play_html
    # At least three BCP-47 options so translators / i18n QA can swap.
    for lang in ("en-US", "es-ES", "fr-FR", "de-DE", "ja-JP", "zh-CN"):
        assert f'value="{lang}"' in play_html


def test_memory_panel_markup_present(play_html: str) -> None:
    for elem_id in (
        "copilotMemoryChip",
        "copilotMemoryPrefs",
        "copilotMemoryRules",
        "copilotMemoryFavs",
        "copilotMemoryForm",
        "copilotMemoryKey",
        "copilotMemoryValue",
    ):
        assert f'id="{elem_id}"' in play_html, f"missing #{elem_id}"


def test_whatif_summary_markup_present(play_html: str) -> None:
    for elem_id in (
        "copilotWhatIf",
        "copilotWhatIfOneLiner",
        "copilotWhatIfWarnings",
    ):
        assert f'id="{elem_id}"' in play_html, f"missing #{elem_id}"


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------


def test_css_has_memory_styles(play_css: str) -> None:
    assert ".copilot-memory" in play_css
    assert ".memory-prefs" in play_css
    assert ".memory-rules" in play_css
    assert ".fav-chip" in play_css
    assert ".mem-forget" in play_css


def test_css_has_whatif_styles(play_css: str) -> None:
    assert ".whatif-summary" in play_css
    assert ".whatif-oneliner" in play_css
    assert ".whatif-oneliner.is-positive" in play_css
    assert ".whatif-oneliner.is-negative" in play_css


def test_css_has_voice_lang_selector(play_css: str) -> None:
    assert ".voice-lang" in play_css


def test_css_mobile_breakpoints_present(play_css: str) -> None:
    # The existing 1200px + 720px breakpoints remain, and H5 adds a
    # 900px "tablet" tier that stacks the cockpit and fattens touch
    # targets for voice/PTT.
    assert "@media (max-width: 900px)" in play_css
    assert "@media (max-width: 720px)" in play_css
    # 720px tier hides the ptt-label/tts-label so the buttons shrink
    # to icon-only on phones.
    assert ".tts-label, .ptt-label" in play_css or ".tts-label" in play_css


# ---------------------------------------------------------------------------
# JS wiring
# ---------------------------------------------------------------------------


def test_js_memory_helpers_present(play_js: str) -> None:
    for name in (
        "renderMemory",
        "memoryRemember",
        "memoryForget",
        "fetchMemorySnapshot",
    ):
        assert name in play_js, f"{name} missing"
    # API endpoints are wired.
    assert "/api/copilot/memory/remember" in play_js
    assert "/api/copilot/memory/forget" in play_js
    assert "/api/copilot/memory?player_id=" in play_js


def test_js_whatif_helpers_present(play_js: str) -> None:
    for name in ("renderWhatIf", "fetchWhatIf"):
        assert name in play_js, f"{name} missing"
    assert "/api/copilot/whatif?player_id=" in play_js


def test_js_voice_lang_helpers_present(play_js: str) -> None:
    for name in (
        "applyVoiceLang",
        "_loadVoiceLang",
        "_saveVoiceLang",
        "VOICE_LANG_KEY",
    ):
        assert name in play_js, f"{name} missing"
    assert "tw2k.voice.lang" in play_js
    # TTS utterance must honour the selected lang.
    assert "u.lang = ttsState.lang" in play_js or "if (ttsState.lang)" in play_js


def test_js_exposes_h5_debug_hooks(play_js: str) -> None:
    for hook in ("window.__tw2kMem", "window.__tw2kWhatIf", "window.__tw2kVoiceLang"):
        assert hook in play_js, f"{hook} missing"


def test_js_memory_update_ws_event_handled(play_js: str) -> None:
    # memory_update WS broadcasts trigger a cheap memory snapshot
    # re-fetch so the right-panel chip stays fresh.
    assert '"memory_update"' in play_js or "m.kind === \"memory_update\"" in play_js
    assert "fetchMemorySnapshot" in play_js


def test_js_state_snapshot_consumes_memory_and_whatif(play_js: str) -> None:
    # fetchCopilotState should render memory + whatif blocks if present.
    assert "s.memory" in play_js
    assert "s.whatif" in play_js
    assert "renderMemory(s.memory)" in play_js or "renderMemory(s.memory" in play_js


def test_js_render_pending_plan_triggers_whatif(play_js: str) -> None:
    # Every re-render of the pending plan should kick off a what-if
    # fetch so the human never sees stale predictions.
    assert "renderPendingPlan" in play_js
    # fetchWhatIf is called from inside renderPendingPlan's happy path.
    # We just require both names co-exist + that fetchWhatIf is
    # reachable from the main render flow.
    snippet = play_js.split("renderPendingPlan", 1)[1][:2000]
    assert "fetchWhatIf" in snippet
