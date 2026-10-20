"""Drive one cockpit seat in a real browser.

Each step saves the screenshot and the visible text, asks the provider for one
action, and performs it. The loop stops when the game is over, the stop file
appears, or the action limit is reached. A dropped page is opened again from
the original seat link.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from ai_cockpit.actions import Action, ActionError, reject_reason
from ai_cockpit.providers import ProviderError, TurnView, resolve_provider
from ai_cockpit.redact import redact
from ai_cockpit.trader import guard_outgoing

_LABELS = r"""
() => Array.from(document.querySelectorAll('button, a')).filter((el) => {
  const style = getComputedStyle(el);
  if (style.display === 'none' || style.visibility === 'hidden') return false;
  if (el.disabled || el.classList.contains('dim')) return false;
  const box = el.getBoundingClientRect();
  return box.width > 0 && box.height > 0;
}).map((el) => (el.innerText || el.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim())
  .filter(Boolean)
"""

_SCREEN = r"""
() => {
  const text = (sel) => {
    const el = document.querySelector(sel);
    return el ? (el.innerText || '').replace(/\s+/g, ' ').trim() : '';
  };
  const visible = (el) => {
    const style = getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const box = el.getBoundingClientRect();
    return box.width > 0 && box.height > 0;
  };
  const buttons = Array.from(document.querySelectorAll('button, a')).filter((el) => visible(el) && !el.closest('[data-ai-send]'));
  const labels = buttons.filter((el) => !el.disabled && !el.classList.contains('dim')).map((el) =>
    (el.innerText || el.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim()
  ).filter(Boolean);
  const selectors = buttons.map((el) => {
    if (el.id) return '#' + el.id;
    if (el.dataset && el.dataset.n) return '[data-n="' + el.dataset.n + '"]';
    return '';
  }).filter(Boolean);
  const warps = Array.from(document.querySelectorAll('#warps button')).filter((el) =>
    visible(el) && !el.disabled && !el.classList.contains('dim')
  ).map((el) => (el.innerText || '').replace(/\s+/g, ' ').trim()).filter(Boolean);
  const rows = Array.from(document.querySelectorAll('#here tr')).map((tr) => {
    const cells = Array.from(tr.querySelectorAll('td')).map((td) =>
      (td.innerText || '').replace(/\s+/g, ' ').trim()
    );
    const btn = tr.querySelector('button');
    const open = btn && visible(btn) && !btn.disabled && !btn.classList.contains('dim');
    return { cells, button: open ? (btn.innerText || '').replace(/\s+/g, ' ').trim() : '' };
  }).filter((row) => row.cells.length);
  const fields = {};
  document.querySelectorAll('#formSlot [data-n]').forEach((el) => {
    const name = el.dataset.n;
    if (!name || !visible(el)) return;
    fields[name] = el.value || '';
    if (el.tagName === 'SELECT') {
      fields[name + 'Options'] = Array.from(el.options).filter((opt) => !opt.disabled).map((opt) => opt.value);
      selectors.push('[data-n="' + name + '"]');
    }
  });
  const ask = document.querySelector('#sectorAsk');
  if (ask && visible(ask)) selectors.push('#sectorAsk');
  const commsForm = document.querySelector('#commsForm');
  const commsOpen = !!(commsForm && !commsForm.hidden && visible(commsForm));
  const commsLines = Array.from(document.querySelectorAll('#turnLog > div[data-kind]')).map((el) => ({
    kind: el.dataset.kind || '',
    line: (el.textContent || '').replace(/\s+/g, ' ').trim(),
  })).filter((row) => row.line);
  const commsTargets = [];
  const corpOpt = document.querySelector('#commsKind option[value="corp"]');
  const commsCorp = !!(commsOpen && corpOpt && !corpOpt.disabled);
  if (commsOpen) {
    const addSel = (sel) => {
      const el = document.querySelector(sel);
      if (el && visible(el) && !el.disabled) selectors.push(sel);
    };
    const target = document.querySelector('#commsTarget');
    if (target) {
      Array.from(target.options).forEach((opt) => {
        if (!opt.disabled) commsTargets.push({
          id: opt.value,
          name: (opt.textContent || '').replace(/\s+/g, ' ').trim(),
        });
      });
    }
    addSel('#commsKind');
    addSel('#commsTarget');
    addSel('#commsMessage');
    addSel('#commsChannel');
    addSel('#commsSend');
    addSel('#commsTune');
    addSel('#commsFed');
    const kind = document.querySelector('#commsKind');
    if (kind && visible(kind)) {
      fields.commsKind = kind.value || '';
      fields.commsKindOptions = Array.from(kind.options).filter((opt) => !opt.disabled).map((opt) => opt.value);
    }
    const message = document.querySelector('#commsMessage');
    if (message && visible(message)) fields.commsMessage = message.value || '';
    if (target && visible(target)) {
      fields.commsTarget = target.value || '';
      fields.commsTargetOptions = Array.from(target.options).filter((opt) => !opt.disabled).map((opt) => opt.value);
    }
  }
  const form = document.querySelector('#formSlot');
  const formText = form ? (form.innerText || '').replace(/\s+/g, ' ').trim() : '';
  const menu = document.querySelector('#menu');
  const menuOpen = !!(menu && !menu.hidden && visible(menu));
  const haggle = document.querySelector('[data-haggle="counter"]');
  const gear = document.querySelector('[data-gear="price"]');
  return {
    sector: text('#pSector'),
    turns: text('#tl'),
    credits: text('#credits'),
    nw: text('#nw'),
    day: text('#sbDay'),
    maxDay: text('#maxDays'),
    chip: text('#waitchip'),
    port: text('[data-port="code"]'),
    here: text('#here'),
    holds: text('#holds'),
    ship: text('#shipStats'),
    last: text('#lastResult'),
    warps, rows, labels, selectors, fields,
    formOpen: !!formText,
    formText,
    haggle: haggle && visible(haggle) ? (haggle.innerText || '').replace(/\s+/g, ' ').trim() : '',
    gearNote: gear && visible(gear) ? (gear.innerText || '').replace(/\s+/g, ' ').trim() : '',
    threat: (() => {
      const box = document.querySelector('#sectorText');
      if (!box) return '';
      return (box.innerText || '').split('\n').map((line) => line.replace(/\s+/g, ' ').trim()).filter((line) => {
        if (/ferrengi|hostile fighters|\bmines\b|\balien\b/i.test(line)) return true;
        return /\boffensive\b/i.test(line) && !/yours/i.test(line);
      }).join(' | ');
    })(),
    menuOpen,
    menuText: menuOpen ? (menu.innerText || '').replace(/\s+/g, ' ').trim() : '',
    course: text('#course'),
    sectorAsk: ask && visible(ask) ? (ask.value || '') : '',
    comms: text('[data-testid=turn-log]'),
    commsOpen, commsLines, commsTargets, commsCorp,
  };
}
"""

_CHIP = """
() => {
  const chip = document.querySelector('#waitchip');
  return chip ? (chip.textContent || '') : '';
}
"""

_HISTORY = 8


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
    model: str = "",
    mock_script: str = "",
    level: str = "hard",
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

    provider, fallback = resolve_provider(provider_name, model, mock_script, level)
    if fallback:
        _write_log(log_path, fallback)
    gate = RateGate(min_interval)
    manual_read = False
    manual_excerpt = ""
    history: list[str] = []
    code = 0
    idle = 0
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            if not _open(page, url, log_path):
                _write_modules(run_dir)
                return 1
            _write_log(log_path, "seat page open " + redact(url))
            step = 1
            limit = max(0, int(max_turns))
            while step <= limit:
                if stop_file is not None and stop_file.is_file():
                    _write_log(log_path, f"stop file at step {step}")
                    break
                gate.wait()
                if not _ready(page, url, log_path):
                    code = 1
                    break
                _wait_chip(page)
                chip = _chip(page)
                if chip == "GAME OVER":
                    _capture(page, run_dir, step, "game over")
                    _write_log(log_path, "game over")
                    break
                if chip == "NO TURNS":
                    _write_log(log_path, "no turns, waiting for the next day")
                    _wait_until(page, ("YOUR MOVE", "GAME OVER"), 20_000)
                    chip = _chip(page)
                    if chip == "GAME OVER":
                        _capture(page, run_dir, step, "game over")
                        _write_log(log_path, "game over")
                        break
                    if chip == "NO TURNS":
                        idle += 1
                        if idle > 8:
                            _write_log(log_path, "the day did not roll")
                            code = 1
                            break
                        continue
                    idle = 0
                screen = _screen(page)
                _write_screen(log_path, step, screen)
                view = _view(page, run_dir, step, manual_read, manual_excerpt, screen, history)
                try:
                    action = provider.decide(view)
                except (ProviderError, ActionError) as exc:
                    _record(actions_path, step, Action("wait", ms=0), note=redact(str(exc)))
                    _write_log(log_path, redact(str(exc)))
                    code = 1
                    break
                usage = getattr(provider, "last_usage", None)
                if usage is not None:
                    _write_log(log_path, usage.line())
                reason = reject_reason(
                    action, list(view.labels),
                    selectors=list(screen.get("selectors") or []),
                    fields=list((screen.get("fields") or {}).keys()),
                )
                if reason and action.op == "click":
                    _write_log(log_path, f"step {step} skipped: {reason}")
                    action = Action("wait", ms=200)
                note = str(getattr(provider, "plan_note", "") or "")
                action = guard_outgoing(action)
                try:
                    opened = _act(page, action)
                    if opened is not None:
                        manual_excerpt = _read_manual(opened, run_dir)
                        manual_read = True
                        note = "read the player manual"
                        opened.close()
                except Exception as exc:
                    note = redact(exc.__class__.__name__)
                    _write_log(log_path, f"step {step} did not land: {note}")
                    _settle(page, url, log_path)
                _record(actions_path, step, action, note=note)
                shown = action.label or action.key or action.selector or action.text
                _write_log(log_path, f"step {step} {action.op} {redact(shown)}")
                history.append(_memory_line(step, screen, action))
                del history[:-_HISTORY]
                step += 1
            else:
                _write_log(log_path, "max turns reached")
        finally:
            browser.close()
    _write_modules(run_dir)
    return code


def _memory_line(step: int, screen: dict, action: Action) -> str:
    bits = [
        f"step {step}",
        f"sector {screen.get('sector') or '?'}",
        f"day {screen.get('day') or '?'}",
        f"turns {screen.get('turns') or '?'}",
        f"chip {screen.get('chip') or '?'}",
        action.op,
        action.label or action.key or action.text or action.selector,
    ]
    return " ".join(str(bit) for bit in bits if bit)


def _open(page, url: str, log_path: Path) -> bool:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_selector("#waitchip", timeout=20_000)
        return True
    except Exception as exc:
        _write_log(log_path, f"the seat page did not open: {exc.__class__.__name__}")
        return False


def _ready(page, url: str, log_path: Path) -> bool:
    """The chip is on the page. A closed or blank page is loaded again."""
    try:
        if _chip(page):
            return True
    except Exception:
        pass
    _write_log(log_path, "reloaded the seat page")
    return _open(page, url, log_path)


def _settle(page, url: str, log_path: Path) -> None:
    """Close a dialog that swallowed the click, then reload if the seat is gone."""
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
    except Exception:
        pass
    _ready(page, url, log_path)


def _chip(page) -> str:
    try:
        return str(page.evaluate(_CHIP) or "")
    except Exception:
        return ""


def _wait_chip(page) -> None:
    """Wait until the seat can act, or the game has stopped asking."""
    _wait_until(page, ("YOUR MOVE", "GAME OVER", "NO TURNS"), 20_000)


def _wait_until(page, chips: tuple[str, ...], timeout: int) -> None:
    wanted = json.dumps(list(chips))
    try:
        page.wait_for_function(
            "(names) => { const c = document.querySelector('#waitchip'); "
            "const t = c ? c.textContent : ''; return names.indexOf(t) >= 0; }",
            arg=json.loads(wanted),
            timeout=timeout,
        )
    except Exception:
        return


def _screen(page) -> dict:
    try:
        raw = page.evaluate(_SCREEN) or {}
    except Exception:
        raw = {}
    if not isinstance(raw, dict):
        return {}
    return raw


def _write_screen(log_path: Path, step: int, screen: dict) -> None:
    _write_log(
        log_path,
        "screen "
        f"day={screen.get('day') or '-'} "
        f"turns={screen.get('turns') or '-'} "
        f"credits={screen.get('credits') or '-'} "
        f"nw={screen.get('nw') or '-'} "
        f"chip={screen.get('chip') or '-'} "
        f"sector={screen.get('sector') or '-'}",
    )
    del step


def _view(page, run_dir: Path, step: int, manual_read: bool, manual_excerpt: str,
          screen: dict, history: list[str]) -> TurnView:
    try:
        text = page.locator("body").inner_text(timeout=10_000)
    except Exception:
        text = str(screen.get("here") or "")
    labels = list(screen.get("labels") or [])
    if not labels:
        try:
            labels = list(page.evaluate(_LABELS) or [])
        except Exception:
            labels = []
    shot_path = run_dir / f"screen-{step:03d}.png"
    try:
        png = page.screenshot(path=str(shot_path), type="png")
    except Exception:
        png = b""
    (run_dir / f"text-{step:03d}.txt").write_text(redact(text), encoding="utf-8")
    screen = dict(screen)
    screen["labels"] = labels
    return TurnView(
        visible_text=text,
        labels=labels,
        screenshot_png=png,
        manual_read=manual_read,
        manual_excerpt=manual_excerpt,
        step=step,
        screen=screen,
        history=list(history),
    )


def _capture(page, run_dir: Path, step: int, label: str) -> None:
    text = ""
    try:
        text = page.locator("body").inner_text(timeout=5_000)
    except Exception:
        text = label
    try:
        page.screenshot(path=str(run_dir / f"screen-{step:03d}.png"), type="png")
    except Exception:
        pass
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
        _type(page, action)
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


def _type(page, action: Action) -> None:
    target = page.locator(action.selector).first if action.selector else page.locator(":focus")
    tag = ""
    try:
        tag = str(target.evaluate("el => el.tagName") or "")
    except Exception:
        tag = ""
    if tag.upper() == "SELECT":
        try:
            target.select_option(value=action.text)
        except Exception:
            target.select_option(label=action.text)
        return
    target.click(timeout=3_000)
    target.fill(action.text)


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
    elif label.upper() == "BUY":
        pattern = re.compile(r"^BUY\b", re.I)
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
    return clean[:6000]


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
