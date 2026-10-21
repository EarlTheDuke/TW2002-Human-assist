"""Drive one cockpit seat in a real browser.

Each step saves the screenshot and the visible text, asks the provider for one
action, and performs it. The loop stops when the game is over, the stop file
appears, or the action limit is reached. A dropped page is opened again from
the original seat link.
"""

from __future__ import annotations

import atexit
import ctypes
import json
import os
import re
import signal
import subprocess
import sys
import threading
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
  const counter = document.querySelector('[data-haggle="counter"]');
  const quote = document.querySelector('[data-haggle="quote"]');
  const lineOf = (el) => (el && visible(el) ? (el.innerText || '').replace(/\s+/g, ' ').trim() : '');
  const haggle = lineOf(counter) || lineOf(quote);
  const gear = document.querySelector('[data-gear="price"]');
  return {
    sector: text('#pSector'),
    turns: text('#tl'),
    turnsFace: text('#turns'),
    turnsLeft: text('#turnsLeftToday'),
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
    haggle,
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


_CLEANUP_READY = False
_STOPPING = False
_PLAYER_MARK = "ai_cockpit_player.py"
# Windows-only. Held here so a POSIX test can still build the flag word.
_CREATE_NEW_PROCESS_GROUP = 0x00000200
_CREATE_NO_WINDOW = 0x08000000


def popen_kwargs() -> dict:
    """Isolate the player so a tree kill cannot reach whoever started it.

    Windows pairs the new process group with the windowless flag. POSIX starts
    a new session, the same setsid the cleanup tries again in-process.
    """
    if os.name == "nt":
        group = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", _CREATE_NEW_PROCESS_GROUP)
        hidden = getattr(subprocess, "CREATE_NO_WINDOW", _CREATE_NO_WINDOW)
        return {"creationflags": int(group) | int(hidden)}
    return {"start_new_session": True}


def engine_modules() -> list[str]:
    return sorted(name for name in sys.modules if name == "tw2k" or name.startswith("tw2k."))


def install_process_cleanup() -> None:
    """Kill child processes on exit, on SIGTERM or SIGINT, and if the parent dies.

    A new session keeps a later group signal from reaching the process that
    launched the player. When this process is already a session leader the
    extra setsid is skipped.
    """
    global _CLEANUP_READY
    if _CLEANUP_READY:
        return
    _CLEANUP_READY = True
    if os.name == "nt":
        _arm_parent_death()
    elif os.name == "posix":
        try:
            os.setsid()
        except OSError:
            pass
        _arm_parent_death()
        signal.signal(signal.SIGTERM, _on_stop_signal)
        signal.signal(signal.SIGINT, _on_stop_signal)
    atexit.register(kill_own_children)


def kill_own_children() -> None:
    """SIGTERM, then SIGKILL, every process this player started."""
    global _STOPPING
    if _STOPPING:
        return
    _STOPPING = True
    try:
        kill_process_tree(os.getpid())
    finally:
        _STOPPING = False


def kill_process_tree(pid: int, *, group: bool | None = None) -> None:
    """Stop `pid` and every descendant.

    SIGTERM goes out first. Anything still alive after a short wait is
    SIGKILL'd, and the walk is repeated so a child started during the
    first signal is included. A process-group leader other than this
    process also has its group signaled. Pass group=True when the caller
    started `pid` as a session leader and the process may already be
    gone: the group id is still that pid. This process does not signal
    its own group, because that group may belong to the caller.
    """
    if pid <= 1:
        return
    if os.name == "nt":
        _kill_windows_tree(pid)
        return
    own = pid == os.getpid()
    leader = _signal_group(pid, own, group)
    _signal_tree(pid, signal.SIGTERM, own=own, leader=leader)
    if _wait_until_dead(_targets(pid, own, leader=leader), 0.5):
        return
    _signal_tree(pid, signal.SIGKILL, own=own, leader=leader)
    _wait_until_dead(_targets(pid, own, leader=leader), 0.5)


def running_player_pids() -> list[int]:
    """Live processes whose command line names the cockpit player."""
    found: list[int] = []
    me = os.getpid()
    proc = Path("/proc")
    if not proc.is_dir():
        return found
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == me or not _alive(pid):
            continue
        if _PLAYER_MARK in _cmdline(pid):
            found.append(pid)
    return sorted(found)


def _on_stop_signal(signum: int, _frame) -> None:
    if _STOPPING:
        return
    kill_own_children()
    raise SystemExit(128 + int(signum))


def _arm_parent_death() -> None:
    """End this process when its parent is gone.

    POSIX asks the kernel for SIGTERM via prctl. Windows has no prctl, so a
    daemon thread polls the parent pid. A parent of pid 1 at startup means
    the parent already exited.
    """
    if os.name == "nt":
        _arm_parent_poll()
        return
    if os.name == "posix":
        _arm_parent_prctl()


def _arm_parent_prctl() -> None:
    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        libc.prctl.argtypes = [
            ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong,
        ]
        libc.prctl.restype = ctypes.c_int
        if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
            return
    except (OSError, AttributeError):
        return
    if os.getppid() == 1:
        kill_own_children()
        raise SystemExit(1)


def _arm_parent_poll() -> None:
    parent = os.getppid()
    if parent <= 1:
        kill_own_children()
        raise SystemExit(1)
    threading.Thread(
        target=_watch_parent, args=(parent,), name="ai-cockpit-parent", daemon=True,
    ).start()


def _watch_parent(parent: int) -> None:
    while _process_alive(parent):
        time.sleep(0.2)
    kill_own_children()
    os._exit(1)


def _kill_windows_tree(pid: int) -> None:
    """taskkill /T walks children. Killing our own pid would take the interpreter too."""
    if pid == os.getpid():
        for child in _windows_children(pid):
            _taskkill_tree(child)
        return
    _taskkill_tree(pid)


def _taskkill_tree(pid: int) -> None:
    if pid <= 1:
        return
    flags = 0
    if os.name == "nt":
        flags = int(getattr(subprocess, "CREATE_NO_WINDOW", _CREATE_NO_WINDOW))
    subprocess.run(
        ["taskkill", "/T", "/F", "/PID", str(int(pid))],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        creationflags=flags,
    )


def _windows_children(pid: int) -> list[int]:
    """Direct child pids. An empty list on POSIX, where /proc is the source."""
    try:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    except (OSError, AttributeError):
        return []
    snapshot = 0x00000002
    kernel.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    kernel.CreateToolhelp32Snapshot.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
    kernel.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    kernel.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.CreateToolhelp32Snapshot(snapshot, 0)
    if not handle or handle == ctypes.c_void_p(-1).value:
        return []
    entry = _ProcessEntry()
    entry.dwSize = ctypes.sizeof(entry)
    found: list[int] = []
    try:
        if not kernel.Process32FirstW(handle, ctypes.byref(entry)):
            return found
        while True:
            if int(entry.th32ParentProcessID) == pid:
                found.append(int(entry.th32ProcessID))
            if not kernel.Process32NextW(handle, ctypes.byref(entry)):
                break
    finally:
        kernel.CloseHandle(handle)
    return found


class _ProcessEntry(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_ulong),
        ("cntUsage", ctypes.c_ulong),
        ("th32ProcessID", ctypes.c_ulong),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", ctypes.c_ulong),
        ("cntThreads", ctypes.c_ulong),
        ("th32ParentProcessID", ctypes.c_ulong),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.c_ulong),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def _windows_alive(pid: int) -> bool:
    """True while Windows still reports the process as running."""
    if pid <= 0:
        return False
    try:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    except (OSError, AttributeError):
        return False
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x1000, 0, int(pid))
    if not handle:
        return False
    code = ctypes.c_ulong()
    try:
        ok = kernel.GetExitCodeProcess(handle, ctypes.byref(code))
    finally:
        kernel.CloseHandle(handle)
    return bool(ok) and int(code.value) == 259


def _process_alive(pid: int) -> bool:
    if os.name == "nt":
        return _windows_alive(pid)
    return _alive(pid)


def _signal_group(pid: int, own: bool, group: bool | None) -> bool:
    if own:
        return False
    if group is None:
        return _group_leader(pid)
    return bool(group)


def _targets(pid: int, own: bool, *, leader: bool) -> list[int]:
    found = _descendants(pid)
    if leader:
        for member in _group_members(pid):
            if member not in found:
                found.append(member)
    if not own and pid not in found:
        found.append(pid)
    return found


def _signal_tree(pid: int, sig: int, *, own: bool, leader: bool) -> None:
    _signal_many(_targets(pid, own, leader=leader), sig)
    if leader and os.name == "posix":
        try:
            os.killpg(pid, sig)
        except (OSError, AttributeError):
            pass


def _group_members(pid: int) -> list[int]:
    members: list[int] = []
    proc = Path("/proc")
    if not proc.is_dir():
        return members
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        one = int(entry.name)
        fields = _stat_fields(one)
        if len(fields) < 3:
            continue
        try:
            pgrp = int(fields[2])
        except ValueError:
            continue
        if pgrp == pid and _alive(one):
            members.append(one)
    return members


def _signal_many(pids: list[int], sig: int) -> None:
    for one in pids:
        if one <= 1:
            continue
        try:
            os.kill(one, sig)
        except OSError:
            pass


def _wait_until_dead(pids: list[int], seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while True:
        if all(not _alive(one) for one in pids):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)


def _descendants(pid: int) -> list[int]:
    children = _children_by_parent()
    ordered: list[int] = []
    stack = list(children.get(pid, []))
    seen: set[int] = set()
    while stack:
        child = stack.pop()
        if child in seen or child <= 1:
            continue
        seen.add(child)
        ordered.append(child)
        stack.extend(children.get(child, []))
    return ordered


def _children_by_parent() -> dict[int, list[int]]:
    found: dict[int, list[int]] = {}
    proc = Path("/proc")
    if not proc.is_dir():
        return found
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        fields = _stat_fields(int(entry.name))
        if len(fields) < 2:
            continue
        try:
            ppid = int(fields[1])
        except ValueError:
            continue
        found.setdefault(ppid, []).append(int(entry.name))
    return found


def _group_leader(pid: int) -> bool:
    fields = _stat_fields(pid)
    if len(fields) < 3:
        return False
    try:
        return int(fields[2]) == pid
    except ValueError:
        return False


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    fields = _stat_fields(pid)
    if not fields:
        return False
    return fields[0] != "Z"


def _stat_fields(pid: int) -> list[str]:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError:
        return []
    cut = raw.rfind(")")
    if cut < 0:
        return []
    return raw[cut + 2:].split()


def _cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", "replace")


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
    install_process_cleanup()
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

    _write_log(log_path, "process started")
    provider, fallback = resolve_provider(provider_name, model, mock_script, level)
    if fallback:
        _write_log(log_path, fallback)
    gate = RateGate(min_interval)
    manual_read = False
    manual_excerpt = ""
    history: list[str] = []
    code = 0
    idle = 0
    try:
        with sync_playwright() as playwright:
            browser, page = _open_when_ready(playwright, url, log_path, headless)
            if browser is None or page is None:
                _write_modules(run_dir)
                return 1
            try:
                # "seat page is open" must not be a substring of the failure
                # line "the seat page did not open". A loaded Windows box writes
                # that failure while Chromium is still starting, and a check for
                # "seat page open" then treated the dead seat as ready.
                _write_log(log_path, "seat page is open " + redact(url))
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
                    if chip != "YOUR MOVE":
                        # The server is not offering a turn. A click from here never lands.
                        _write_log(log_path, "waiting for the turn")
                        idle += 1
                        if idle > 8:
                            _write_log(log_path, "the turn did not arrive")
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
    finally:
        kill_own_children()
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


def _open_when_ready(playwright, url: str, log_path: Path, headless: bool, timeout_s: float = 240):
    """Launch the browser and open the seat, retrying until the port is up.

    The first navigation used to fail once (the worker had answered /healthz
    but the seat page was not ready, or Chromium was not up yet) and the
    process exited. The game then waits on that seat until something connects,
    so the other seats never finish the day, and the only log line was missing
    because this process had already gone.

    90s was enough on an idle VM and not on the loaded Windows merge box:
    launching Chromium plus one slow page load used the whole budget, the
    process exited, and the scheduler sat on that seat.
    """
    deadline = time.monotonic() + timeout_s
    while True:
        browser = None
        try:
            browser = playwright.chromium.launch(headless=headless)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            if _open(page, url, log_path):
                return browser, page
            _write_log(log_path, "seat page was not ready; retrying")
        except Exception as exc:
            _write_log(log_path, f"browser did not start: {exc.__class__.__name__}")
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        if time.monotonic() >= deadline:
            return None, None
        time.sleep(1)


def _open(page, url: str, log_path: Path) -> bool:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_selector("#waitchip", timeout=45_000)
        # The header says YOUR MOVE before the seat connects. Wait for a sector.
        page.wait_for_function(
            """() => {
              const sector = document.querySelector('#pSector');
              const sign = document.querySelector('.sign-in');
              const text = sector ? (sector.textContent || '').trim() : '';
              const signedOut = !!(sign && !sign.hidden);
              return !!text && text !== '-' && !signedOut;
            }""",
            timeout=45_000,
        )
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
    # 20s missed the chip on the loaded Windows box. The seat stays attended
    # while this process is up, so giving up early left the scheduler on the
    # full external timeout instead of the action.
    _wait_until(page, ("YOUR MOVE", "GAME OVER", "NO TURNS"), 90_000)


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
        f"left={screen.get('turnsLeft') or '-'} "
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
