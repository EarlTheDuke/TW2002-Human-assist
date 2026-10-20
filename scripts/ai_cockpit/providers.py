"""Pluggable minds. Scripted play needs no key. Live minds read a key from the environment."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from ai_cockpit.actions import Action, ActionError, parse_action, reject_reason
from ai_cockpit.cost import Usage, price_usage
from ai_cockpit.redact import redact
from ai_cockpit.trader import ScriptedTrader

PLAYBOOK = (
    "You are a person playing Galaxy War Command at the cockpit. "
    "You see only the screenshot, the visible text, and the notes below. "
    "You have no map of the engine and no private data. "
    "On your first turn, open the header Manual link and read the player manual "
    "before you trade or move. "
    "Then play a trader: sell cargo where the port is buying, and buy where the port "
    "is selling when you already know a port that pays more for that good. "
    "When a trade form shows a port counter, confirm that price. "
    "At StarDock, buy one hold and then fighters when you can pay. "
    "Do not warp into a sector whose screen showed Ferrengi, mines, or hostile fighters. "
    "Use every turn. When the chip says NO TURNS, wait for the next day. "
    "When the chip says GAME OVER, stop. "
    "Reply with one JSON object and nothing else. "
    'The object is {"op":"click"|"type"|"press"|"wait","label":"","selector":"","text":"","key":"","ms":0}. '
    "click uses a label that is on the screen now. "
    "type fills a visible field. press is one key such as \".\" or \"Escape\". wait pauses for ms."
)

_ATTEMPTS = 3


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
    screen: dict = field(default_factory=dict)
    history: list = field(default_factory=list)


def system_prompt(manual_excerpt: str) -> str:
    """The standing instructions, plus the manual text the seat page showed."""
    excerpt = (manual_excerpt or "").strip()
    if not excerpt:
        return PLAYBOOK + "\n\nThe player manual is not in memory yet. Open it before you trade."
    return PLAYBOOK + "\n\nPlayer manual, as shown on the seat page:\n" + excerpt[:6000]


def _usage_from_payload(payload: dict, style: str, provider: str, model: str) -> Usage:
    usage = payload.get("usage") or {}
    if not isinstance(usage, dict):
        usage = {}
    if style == "anthropic":
        return price_usage(
            provider, model,
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            cached_tokens=int(usage.get("cache_read_input_tokens") or 0),
            cache_write_tokens=int(usage.get("cache_creation_input_tokens") or 0),
        )
    details = usage.get("prompt_tokens_details") or {}
    if not isinstance(details, dict):
        details = {}
    return price_usage(
        provider, model,
        input_tokens=int(usage.get("prompt_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or 0),
        cached_tokens=int(details.get("cached_tokens") or 0),
    )


@dataclass
class _HTTPMind:
    name: str
    env_key: str
    url: str
    model_env: str
    default_model: str
    style: str
    extra_headers: dict[str, str] = field(default_factory=dict)
    model_override: str = ""
    last_usage: Usage | None = None
    plan_note: str = ""

    def decide(self, view: TurnView) -> Action:
        key = (os.environ.get(self.env_key) or "").strip()
        if not key:
            raise ProviderError(f"{self.name} needs {self.env_key} in the environment")
        model = (self.model_override or os.environ.get(self.model_env) or self.default_model).strip()
        errors: list[str] = []
        total = Usage(provider=self.name, model=model)
        action = Action("wait", ms=400)
        for _attempt in range(_ATTEMPTS):
            body = self._body(view, model, errors)
            raw = _post_json(self.url, body, self._headers(key))
            total.add(_usage_from_payload(raw, self.style, self.name, model))
            text = _message_text(raw, self.style)
            try:
                parsed = parse_action(text)
            except ActionError as exc:
                errors.append(redact(str(exc)))
                continue
            reason = reject_reason(
                parsed,
                list(view.labels),
                selectors=list((view.screen or {}).get("selectors") or []),
                fields=list(((view.screen or {}).get("fields") or {}).keys()),
            )
            if reason:
                errors.append(reason)
                continue
            action = parsed
            errors.clear()
            break
        self.last_usage = total
        if errors:
            self.plan_note = "invalid action, waiting"
            return Action("wait", ms=400)
        self.plan_note = ""
        return action

    def _headers(self, key: str) -> dict[str, str]:
        headers = {"content-type": "application/json"}
        if self.style == "anthropic":
            headers["x-api-key"] = key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["authorization"] = f"Bearer {key}"
        headers.update(self.extra_headers)
        return headers

    def _body(self, view: TurnView, model: str, errors: list[str]) -> dict:
        prompt = _prompt(view, errors)
        system = system_prompt(view.manual_excerpt if view.manual_read else "")
        encoded = base64.standard_b64encode(view.screenshot_png).decode("ascii")
        if self.style == "anthropic":
            return {
                "model": model,
                "max_tokens": 300,
                "system": system,
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
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                    ],
                },
            ],
        }


def _prompt(view: TurnView, errors: list[str] | None = None) -> str:
    manual = "You have already read the player manual." if view.manual_read else (
        "You have not read the player manual yet. Open it before you trade."
    )
    labels = "\n".join(f"- {row}" for row in view.labels[:80])
    history = "\n".join(f"- {row}" for row in (view.history or [])[-8:])
    recent = f"\nRecent screens and actions:\n{history}\n" if history else ""
    complaint = ""
    if errors:
        complaint = "\nThe last reply was not a visible action: " + "; ".join(errors[-3:]) + "\nChoose a label from the list.\n"
    return (
        f"Step {view.step}. {manual}\n"
        f"{recent}"
        f"{complaint}"
        f"Visible controls:\n{labels}\n\n"
        f"Visible text:\n{view.visible_text[:8000]}"
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


def build_provider(name: str, model: str = ""):
    key = (name or "scripted").strip().lower()
    if key == "scripted":
        return ScriptedTrader()
    if key in ("grok", "xai"):
        mind = grok_provider()
    elif key == "openai":
        mind = openai_provider()
    elif key == "anthropic":
        mind = anthropic_provider()
    else:
        raise ProviderError("provider must be scripted, grok, openai, or anthropic")
    mind.model_override = (model or "").strip()
    return mind
