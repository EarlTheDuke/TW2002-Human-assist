"""Drive one cockpit seat in a real browser.

Each step saves the screenshot and the visible text, asks the provider for one
action, and performs it. The loop stops when the game is over, the stop file
appears, or the action limit is reached.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from ai_cockpit.actions import Action, ActionError
from ai_cockpit.providers import ProviderError, TurnView, build_provider
from ai_cockpit.redact import redact

_LABELS = r"""
() => Array.from(document.querySelectorAll('button, a')).filter((el) => {
  const style = getComputedStyle(el);
  if (style.display === 'none' || style.visibility === 'hidden') return false;
  const box = el.getBoundingClientRect();
  return box.width > 0 && box.height > 0;
}).map((el) => (el.innerText || el.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim())
  .filter(Boolean)
"""

_CHIP = """
() => {
  const chip = document.querySelector('#waitchip');
  return chip ? (chip.textContent || '') : '';
}
"""


class RateGate:
    """Sleep so two actions cannot start closer than `interval` seconds."""

    def __init__(self, interval: float) -> None:
        self.interval = max(0.0, float(interval))
        self._last = 0.0

    def wait(self) -> None:
        if self.interval <= 0:
            self._last = time.monotonic()
            return
        now = time.monotonic()
        if self._last:
            remain = self.interval - (now - self._last)
            if remain > 0:
                time.sleep(remain)
        self._last = time.monotonic()


def engine_modules() -> list[str]:
    return sorted(name for name in sys.modules if name == "tw2k" or name.startswith("tw2k."))


def play(
    *,
    url: str,
    provider_name: str,
    run_dir: Path,
    max_turns: int,
    min_interval: float,
    stop_file: Path | None,
    headless: bool = True,
) -> int:
    """Play until the seat is done. Returns 0 on a clean stop."""
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "player.log"
    actions_path = run_dir / "actions.jsonl"
    if stop_file is not None and stop_file.is_file():
        _write_log(log_path, "stop file present before the browser opened")
        _write_modules(run_dir)
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _write_log(log_path, "Playwright is not installed")
        _write_modules(run_dir)
        return 1

    provider = build_provider(provider_name)
    gate = RateGate(min_interval)
    manual_read = False
    manual_excerpt = ""
    code = 0
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_selector("#waitchip", timeout=20_000)
        except Exception as exc:
            _write_log(log_path, f"the seat page did not open: {exc.__class__.__name__}")
            browser.close()
            _write_modules(run_dir)
            return 1
        # The page removes the token from the address. Log only the redacted form.
        _write_log(log_path, "seat page open " + redact(url))
        for step in range(1, max(0, int(max_turns)) + 1):
            if stop_file is not None and stop_file.is_file():
                _write_log(log_path, f"stop file at step {step}")
                break
            gate.wait()
            _wait_chip(page)
            chip = page.evaluate(_CHIP) or ""
            if chip == "GAME OVER":
                _capture(page, run_dir, step, "game over")
                _write_log(log_path, "game over")
                break
            view = _view(page, run_dir, step, manual_read, manual_excerpt)
            try:
                action = provider.decide(view)
            except (ProviderError, ActionError) as exc:
                _record(actions_path, step, Action("wait", ms=0), note=redact(str(exc)))
                _write_log(log_path, redact(str(exc)))
                code = 1
                break
            note = ""
            try:
                opened = _act(page, action)
                if opened is not None:
                    manual_excerpt = _read_manual(opened, run_dir)
                    manual_read = True
                    note = "read the player manual"
                    opened.close()
            except Exception as exc:
                note = redact(f"{exc.__class__.__name__}")
                _write_log(log_path, f"step {step} did not land: {note}")
            _record(actions_path, step, action, note=note)
            _write_log(log_path, f"step {step} {action.op} {redact(action.label or action.key or action.selector)}")
        else:
            _write_log(log_path, "max turns reached")
        browser.close()
    _write_modules(run_dir)
    return code


def _wait_chip(page) -> None:
    """Wait until the seat can act, or the game has stopped asking."""
    try:
        page.wait_for_function(
            "() => { const c = document.querySelector('#waitchip'); "
            "const t = c ? c.textContent : ''; "
            "return t === 'YOUR MOVE' || t === 'GAME OVER' || t === 'NO TURNS'; }",
            timeout=20_000,
        )
    except Exception:
        return


def _view(page, run_dir: Path, step: int, manual_read: bool, manual_excerpt: str) -> TurnView:
    text = page.locator("body").inner_text(timeout=10_000)
    labels = page.evaluate(_LABELS) or []
    shot_path = run_dir / f"screen-{step:03d}.png"
    png = page.screenshot(path=str(shot_path), type="png")
    (run_dir / f"text-{step:03d}.txt").write_text(redact(text), encoding="utf-8")
    return TurnView(
        visible_text=text,
        labels=list(labels),
        screenshot_png=png,
        manual_read=manual_read,
        manual_excerpt=manual_excerpt,
        step=step,
    )


def _capture(page, run_dir: Path, step: int, label: str) -> None:
    text = ""
    try:
        text = page.locator("body").inner_text(timeout=5_000)
    except Exception:
        text = label
    page.screenshot(path=str(run_dir / f"screen-{step:03d}.png"), type="png")
    (run_dir / f"text-{step:03d}.txt").write_text(redact(text), encoding="utf-8")


def _act(page, action: Action):
    if action.op == "wait":
        page.wait_for_timeout(action.ms or 200)
        return None
    if action.op == "press":
        page.keyboard.press(action.key or ".")
        page.wait_for_timeout(300)
        return None
    if action.op == "type":
        page.keyboard.type(action.text)
        return None
    target = _locator(page, action)
    if _opens_manual(action):
        with page.expect_popup(timeout=8_000) as popup:
            target.click(timeout=8_000)
        manual = popup.value
        manual.wait_for_load_state("domcontentloaded", timeout=15_000)
        return manual
    target.click(timeout=8_000)
    page.wait_for_timeout(300)
    return None


def _opens_manual(action: Action) -> bool:
    label = action.label.strip().lower()
    selector = action.selector.strip().lower()
    return label == "manual" or "manuallink" in selector or selector == "#manuallink"


def _locator(page, action: Action):
    if action.selector:
        return page.locator(action.selector).first
    label = action.label.strip()
    if not label:
        raise ActionError("click needs a label or a selector")
    if label.upper() == "SELL":
        pattern = re.compile(r"^SELL\b", re.I)
    else:
        pattern = re.compile("^" + re.escape(label) + "$", re.I)
    button = page.get_by_role("button", name=pattern)
    if button.count():
        return button.first
    link = page.get_by_role("link", name=pattern)
    if link.count():
        return link.first
    return page.get_by_text(pattern).first


def _read_manual(page, run_dir: Path) -> str:
    text = page.locator("body").inner_text(timeout=15_000)
    page.screenshot(path=str(run_dir / "screen-manual.png"), type="png")
    clean = redact(text)
    (run_dir / "text-manual.txt").write_text(clean, encoding="utf-8")
    return clean[:4000]


def _record(path: Path, step: int, action: Action, *, note: str) -> None:
    row = {"step": step, "at": time.time(), "note": redact(note)}
    row.update(action.as_dict())
    row["label"] = redact(str(row["label"]))
    row["text"] = redact(str(row["text"]))
    row["selector"] = redact(str(row["selector"]))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def _write_log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(redact(line) + "\n")


def _write_modules(run_dir: Path) -> None:
    names = engine_modules()
    (run_dir / "modules.txt").write_text("\n".join(names) + ("\n" if names else ""), encoding="utf-8")
