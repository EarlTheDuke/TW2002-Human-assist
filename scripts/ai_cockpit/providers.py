"""Pluggable minds. Scripted play needs no key. Live minds read a key from the environment."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from ai_cockpit.actions import Action, ActionError, parse_action
from ai_cockpit.redact import redact

SYSTEM = (
    "You are a person playing Galaxy War Command at the cockpit. "
    "You see only the screenshot and the visible text. "
    "You have no map of the engine and no private data. "
    "On your first turn, open the header Manual link and read the player manual "
    "before you trade or move. "
    "Then play like a trader: sell cargo the port is buying when a SELL button is on screen, "
    "confirm a form that is already open, and otherwise press the wait key. "
    "Reply with one JSON object and nothing else. "
    'The object is {"op":"click"|"type"|"press"|"wait","label":"","selector":"","text":"","key":"","ms":0}. '
    "click uses the visible label or a CSS selector of something on the screen. "
    "type fills the focused field. press is one key such as \".\". wait pauses for ms."
)


class ProviderError(RuntimeError):
    """A live provider could not answer. The message never includes a key."""


@dataclass
class TurnView:
    visible_text: str
    labels: list[str]
    screenshot_png: bytes
    manual_read: bool
    manual_excerpt: str
    step: int


@dataclass
class ScriptedTrader:
    """A short offline trader. It reads the manual, sells once, then waits a turn."""

    sold: bool = False
    looks: int = 0

    def decide(self, view: TurnView) -> Action:
        labels = [row.strip() for row in view.labels if row and row.strip()]
        upper = [row.upper() for row in labels]
        if not view.manual_read:
            return Action("click", label="Manual")
        if any(row == "CONFIRM" for row in upper):
            return Action("click", label="CONFIRM")
        if not self.sold:
            if any(row.startswith("SELL") for row in upper):
                self.sold = True
                return Action("click", label="SELL")
            self.looks += 1
            if self.looks < 8:
                return Action("wait", ms=400)
        return Action("press", key=".")


@dataclass
class _HTTPMind:
    name: str
    env_key: str
    url: str
    model_env: str
    default_model: str
    style: str
    extra_headers: dict[str, str] = field(default_factory=dict)

    def decide(self, view: TurnView) -> Action:
        key = (os.environ.get(self.env_key) or "").strip()
        if not key:
            raise ProviderError(f"{self.name} needs {self.env_key} in the environment")
        model = (os.environ.get(self.model_env) or self.default_model).strip()
        body = self._body(view, model)
        raw = _post_json(self.url, body, self._headers(key))
        text = _message_text(raw, self.style)
        try:
            return parse_action(text)
        except ActionError as exc:
            raise ProviderError(redact(f"{self.name} reply was not an action: {exc}")) from exc

    def _headers(self, key: str) -> dict[str, str]:
        headers = {"content-type": "application/json"}
        if self.style == "anthropic":
            headers["x-api-key"] = key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["authorization"] = f"Bearer {key}"
        headers.update(self.extra_headers)
        return headers

    def _body(self, view: TurnView, model: str) -> dict:
        prompt = _prompt(view)
        encoded = base64.standard_b64encode(view.screenshot_png).decode("ascii")
        if self.style == "anthropic":
            return {
                "model": model,
                "max_tokens": 300,
                "system": SYSTEM,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/png", "data": encoded},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }],
            }
        return {
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                    ],
                },
            ],
        }


def _prompt(view: TurnView) -> str:
    manual = "You have already read the player manual." if view.manual_read else (
        "You have not read the player manual yet. Open it before you trade."
    )
    excerpt = ""
    if view.manual_excerpt:
        excerpt = "\nManual excerpt:\n" + view.manual_excerpt[:4000]
    labels = "\n".join(f"- {row}" for row in view.labels[:80])
    return (
        f"Step {view.step}. {manual}\n"
        f"Visible controls:\n{labels}\n\n"
        f"Visible text:\n{view.visible_text[:8000]}"
        f"{excerpt}"
    )


def _post_json(url: str, body: dict, headers: dict[str, str]) -> dict:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ProviderError(f"model request failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"model request failed: {exc.__class__.__name__}") from exc
    except TimeoutError as exc:
        raise ProviderError("model request timed out") from exc


def _message_text(payload: dict, style: str) -> str:
    if style == "anthropic":
        blocks = payload.get("content") or []
        parts = [str(block.get("text") or "") for block in blocks if isinstance(block, dict)]
        return "\n".join(parts)
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    if isinstance(content, list):
        return "\n".join(str(part.get("text") or "") for part in content if isinstance(part, dict))
    return str(content)


def grok_provider() -> _HTTPMind:
    return _HTTPMind(
        name="grok",
        env_key="XAI_API_KEY",
        url="https://api.x.ai/v1/chat/completions",
        model_env="XAI_MODEL",
        default_model="grok-4",
        style="openai",
    )


def openai_provider() -> _HTTPMind:
    return _HTTPMind(
        name="openai",
        env_key="OPENAI_API_KEY",
        url="https://api.openai.com/v1/chat/completions",
        model_env="OPENAI_MODEL",
        default_model="gpt-4o",
        style="openai",
    )


def anthropic_provider() -> _HTTPMind:
    return _HTTPMind(
        name="anthropic",
        env_key="ANTHROPIC_API_KEY",
        url="https://api.anthropic.com/v1/messages",
        model_env="ANTHROPIC_MODEL",
        default_model="claude-sonnet-4-5",
        style="anthropic",
    )


def build_provider(name: str):
    key = (name or "scripted").strip().lower()
    if key == "scripted":
        return ScriptedTrader()
    if key in ("grok", "xai"):
        return grok_provider()
    if key == "openai":
        return openai_provider()
    if key == "anthropic":
        return anthropic_provider()
    raise ProviderError("provider must be scripted, grok, openai, or anthropic")
