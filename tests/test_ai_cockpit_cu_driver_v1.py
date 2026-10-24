"""UI-only cockpit driver: a custom model endpoint and a stand-in page.

The loop under test never starts TinyBox and never opens a harness socket.
A live browser check at the bottom confirms mode=cu on the redesign seat.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
TOKEN = "cu-driver-seat-token-0001"


def _scripts() -> None:
    text = str(SCRIPTS)
    if text not in sys.path:
        sys.path.insert(0, text)


def _key(*parts: str) -> str:
    return "".join(parts)


CUSTOM_KEY = _key("sk-", "customdriver", "1234567890")


class _Locator:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    def inner_text(self, timeout: int | None = None) -> str:
        return self.page.visible

    def click(self, timeout: int | None = None) -> None:
        self.page.clicks.append("locator")


class _Keys:
    def __init__(self) -> None:
        self.pressed: list[str] = []

    def press(self, key: str) -> None:
        self.pressed.append(key)


class FakePage:
    """The slice of a Playwright page the turn loop actually touches."""

    def __init__(self, screen: dict, visible: str) -> None:
        self.screen = dict(screen)
        self.visible = visible
        self.chip = "YOUR MOVE"
        self.clicks: list[str] = []
        self.keyboard = _Keys()
        self.on_click = None

    def evaluate(self, script, arg=None):
        text = str(script)
        if arg is not None and "want" in text:
            self.clicks.append(str(arg))
            if self.on_click is not None:
                self.on_click(str(arg))
            return True
        if "turnsLeftToday" in text:
            return dict(self.screen)
        if "#waitchip" in text and "textContent" in text:
            return self.chip
        if "Array.from" in text:
            return list(self.screen.get("labels") or [])
        return ""

    def wait_for_function(self, script, arg=None, timeout: int | None = None) -> None:
        return None

    def wait_for_timeout(self, ms: int) -> None:
        return None

    def locator(self, selector: str) -> _Locator:
        return _Locator(self)

    def screenshot(self, path: str | None = None, type: str = "png") -> bytes:
        data = b"\x89PNG\r\n\x1a\nfake-screen"
        if path:
            Path(path).write_bytes(data)
        return data


class _Brain:
    def __init__(self, label: str) -> None:
        self.label = label
        self.views = []
        self.plan_note = ""
        self.last_usage = None

    def decide(self, view):
        self.views.append(view)
        return __import__("ai_cockpit.actions", fromlist=["Action"]).Action("click", label=self.label)


def _screen() -> dict:
    return {
        "sector": "12",
        "turns": "40",
        "turnsFace": "40",
        "turnsLeft": "40",
        "credits": "500 cr",
        "nw": "1000",
        "day": "1",
        "maxDay": "3",
        "chip": "YOUR MOVE",
        "labels": ["Warp 2", "Manual"],
        "selectors": [],
        "fields": {},
        "warps": ["Warp 2"],
        "rows": [],
        "here": "Sector 12 port BSS",
    }


def test_custom_endpoint_and_a_missing_key_do_not_call_out(monkeypatch) -> None:
    _scripts()
    from ai_cockpit.providers import chat_completions_url, resolve_provider
    from ai_cockpit.trader import ScriptedTrader

    assert chat_completions_url("https://models.example/v1") == "https://models.example/v1/chat/completions"
    assert chat_completions_url("https://models.example/api/") == "https://models.example/api/chat/completions"
    assert (
        chat_completions_url("https://models.example/v1/chat/completions")
        == "https://models.example/v1/chat/completions"
    )
    with pytest.raises(Exception) as bad:
        chat_completions_url("https://user:secret@models.example/v1")
    assert "secret" not in str(bad.value)
    assert "username" in str(bad.value)

    def explode(*_args, **_kwargs):
        raise AssertionError("the model endpoint was called")

    monkeypatch.setattr("urllib.request.urlopen", explode)
    for name in ("AI_COCKPIT_BASE_URL", "AI_COCKPIT_API_KEY", "AI_COCKPIT_MODEL",
                 "TW2K_CUSTOM_BASE_URL", "TW2K_CUSTOM_API_KEY", "TW2K_CUSTOM_MODEL",
                 "TW2K_TINYBOX_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    provider, note = resolve_provider("custom")
    assert isinstance(provider, ScriptedTrader)
    assert note == "no AI_COCKPIT_BASE_URL, scripted fallback"
    monkeypatch.setenv("TW2K_CUSTOM_BASE_URL", "https://models.example/api")
    provider, note = resolve_provider("custom")
    assert isinstance(provider, ScriptedTrader)
    assert note == "no AI_COCKPIT_API_KEY, scripted fallback"
    monkeypatch.setenv("TW2K_CUSTOM_API_KEY", CUSTOM_KEY)
    provider, note = resolve_provider("openai-compatible")
    assert isinstance(provider, ScriptedTrader)
    assert note == "no AI_COCKPIT_MODEL, scripted fallback"
    assert CUSTOM_KEY not in note


def test_custom_mind_posts_the_screen_and_not_a_harness_read(monkeypatch) -> None:
    _scripts()
    from ai_cockpit.providers import TurnView, build_provider
    from ai_cockpit.redact import redact

    captured: dict = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            payload = {
                "choices": [{"message": {"content": '{"op":"click","label":"Warp 2"}'}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 6},
            }
            return json.dumps(payload).encode()

    def urlopen(request, timeout=60):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode())
        captured["headers"] = {key.lower(): value for key, value in request.header_items()}
        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    for name in ("AI_COCKPIT_BASE_URL", "AI_COCKPIT_API_KEY", "AI_COCKPIT_MODEL",
                 "TW2K_CUSTOM_BASE_URL", "TW2K_CUSTOM_API_KEY", "TW2K_CUSTOM_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AI_COCKPIT_BASE_URL", "https://models.example/v1")
    monkeypatch.setenv("AI_COCKPIT_API_KEY", CUSTOM_KEY)
    monkeypatch.setenv("AI_COCKPIT_MODEL", "qwen-test")
    view = TurnView(
        "YOUR MOVE\nSector 12\ntoken=seat-secret",
        ["Warp 2", "Manual"],
        b"\x89PNG",
        True,
        "Getting started. Trade between ports.",
        2,
        screen={"selectors": [], "fields": {}},
        history=["step 1 click Manual"],
    )
    action = build_provider("custom").decide(view)
    assert action.op == "click" and action.label == "Warp 2"
    assert captured["url"] == "https://models.example/v1/chat/completions"
    body = json.dumps(captured["body"])
    assert "Sector 12" in body
    assert "Warp 2" in body
    assert "Getting started" in body
    assert "/harness/" not in body
    assert "legal_actions" not in body
    assert "observation" not in body
    assert CUSTOM_KEY not in body
    assert captured["headers"]["authorization"] == f"Bearer {CUSTOM_KEY}"
    assert CUSTOM_KEY not in redact(f"authorization {CUSTOM_KEY} token=seat-secret")
    assert "token=[redacted]" in redact("token=seat-secret")


def test_the_driver_clicks_the_page_and_stops_at_game_over(tmp_path: Path, monkeypatch) -> None:
    _scripts()
    from ai_cockpit.runner import run_turns

    monkeypatch.setenv("AI_COCKPIT_API_KEY", CUSTOM_KEY)
    page = FakePage(_screen(), f"YOUR MOVE Sector 12 token={TOKEN} key {CUSTOM_KEY}")
    brain = _Brain("Warp 2")

    def advance(_label: str) -> None:
        page.chip = "GAME OVER"

    page.on_click = advance
    run = tmp_path / "run"
    run.mkdir()
    code = run_turns(
        page,
        url=f"http://127.0.0.1:9/bot?seat=P2&mode=cu&token={TOKEN}&layout=redesign",
        provider=brain,
        run_dir=run,
        max_turns=4,
        min_interval=0,
    )
    assert code == 0
    assert page.clicks == ["Warp 2"]
    assert brain.views and "Sector 12" in brain.views[0].visible_text
    assert "/harness/" not in brain.views[0].visible_text
    assert "legal_actions" not in brain.views[0].visible_text
    actions = [json.loads(line) for line in (run / "actions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert actions[0]["op"] == "click" and actions[0]["label"] == "Warp 2"
    blob = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in run.iterdir())
    assert TOKEN not in blob
    assert CUSTOM_KEY not in blob
    assert "token=[redacted]" in blob
    assert (run / "screen-001.png").is_file()
    assert "game over" in (run / "player.log").read_text(encoding="utf-8")


def test_an_offscreen_click_waits_and_a_stop_file_ends_the_loop(tmp_path: Path) -> None:
    _scripts()
    from ai_cockpit.actions import Action
    from ai_cockpit.runner import run_turns

    page = FakePage(_screen(), "YOUR MOVE Sector 12")
    calls = {"n": 0}

    def decide(view):
        calls["n"] += 1
        if calls["n"] == 1:
            return Action("click", label="Not on screen")
        page.chip = "GAME OVER"
        return Action("wait", ms=10)

    class _Two:
        plan_note = ""
        last_usage = None

    brain = _Two()
    brain.decide = decide

    run = tmp_path / "off"
    run.mkdir()
    code = run_turns(
        page, url="http://127.0.0.1:9/bot?mode=cu&token=hidden", provider=brain,
        run_dir=run, max_turns=3, min_interval=0,
    )
    assert code == 0
    rows = [json.loads(line) for line in (run / "actions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows[0]["op"] == "wait"
    assert "not on screen" in (run / "player.log").read_text(encoding="utf-8")
    assert page.clicks == []

    stop = tmp_path / "STOP"
    stopped = tmp_path / "stop-run"
    stopped.mkdir()
    page.chip = "YOUR MOVE"
    brain = _Brain("Warp 2")

    def halt(label: str) -> None:
        stop.write_text("stop", encoding="utf-8")

    page.on_click = halt
    code = run_turns(
        page, url="http://127.0.0.1:9/bot?mode=cu", provider=brain, run_dir=stopped,
        max_turns=5, min_interval=0, stop_file=stop,
    )
    assert code == 0
    assert page.clicks == ["Warp 2"]
    assert "stop file at step 2" in (stopped / "player.log").read_text(encoding="utf-8")


def test_the_lobby_stores_custom_without_a_key(monkeypatch) -> None:
    import tw2k.engine.constants as K
    from tw2k.public import pages
    from tw2k.public import security as S

    monkeypatch.setattr(K, "AI_COCKPIT_SEAT_MODE", "tw2002")
    shown = pages.new_game("Galaxy War Command")
    assert "OpenAI-compatible (env)" in shown
    form = S.parse_game_form({
        "name": "Alpha", "humans": 1, "bots": 0, "ai_cockpit": "on",
        "ai_cockpit_provider": "custom", "ai_cockpit_model": "qwen-test",
    })
    settings = form.settings()
    assert settings["ai_cockpit_provider"] == "custom"
    assert settings["ai_cockpit_model"] == "qwen-test"
    assert "ai_key" not in settings
    assert CUSTOM_KEY not in str(settings)
    with pytest.raises(S.FormError):
        S.parse_game_form({
            "name": "Alpha", "humans": 1, "ai_cockpit": "on",
            "ai_cockpit_provider": "observation",
        })


def test_mode_cu_redesign_enlarges_targets_and_disables_a_grey_warp(tmp_path, browser) -> None:
    from tests._cu_host import CuHost, allowed_test_port

    with CuHost(tmp_path / "host", TOKEN, turns_per_day=60) as host:
        assert allowed_test_port(host.port)
        assert host.port not in range(8031, 8038)
        assert host.port != 8041
        me = host.runner.state.universe.players["P2"]
        me.turns_today = int(me.turns_per_day) - 1
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(
            f"{host.base}/bot?seat=P2&mode=cu&token={TOKEN}&layout=redesign",
            wait_until="domcontentloaded",
        )
        page.wait_for_function(
            "() => document.body.classList.contains('cu-seat')",
            timeout=10_000,
        )
        page.wait_for_function(
            """() => {
              const sector = document.querySelector('#pSector');
              const text = sector ? (sector.textContent || '').trim() : '';
              return !!text && text !== '-';
            }""",
            timeout=20_000,
        )
        chip = page.locator("#waitchip")
        assert chip.inner_text().strip() in {"YOUR MOVE", "WAITING", "NO TURNS", "GAME OVER"}
        assert chip.get_attribute("role") == "status"
        page.wait_for_selector("#warps button", timeout=10_000)
        box = page.locator("#warps button").first.bounding_box()
        assert box is not None and box["height"] >= 48 and box["width"] >= 48
        manual = page.locator("#manualLink").bounding_box()
        assert manual is not None and manual["height"] >= 48
        page.wait_for_selector("#warps button.dim", timeout=20_000)
        grey = page.locator("#warps button.dim").first
        assert grey.is_disabled()
        assert grey.get_attribute("aria-disabled") == "true"
        page.close()
