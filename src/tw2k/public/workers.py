"""One `tw2k serve` process per game, owned by the lobby (Windows Job Object; kill-on-close)."""

from __future__ import annotations

import asyncio
import ctypes
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from . import worker as W
from .config import LobbyConfig, assert_lobby_port

BOT_NAMES = ("Vega", "Orion", "Lyra", "Rigel", "Talon")
_STRIP_ENV_PREFIXES = ("TW2K_", "TW2002_")
_STRIP_ENV = {"COCKPIT_LAYOUT", "AI_COCKPIT_SEAT_MODE"}
LOG_ROTATE_BYTES = 5 * 1024 * 1024
LOG_KEEP = 3


# --------------------------------------------------------------------------- job object

class _IoCounters(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimits),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
_JOB_EXTENDED_LIMIT_INFO_CLASS = 9


class JobObject:
    """Every worker joins this job; when the lobby process ends, Windows ends them too."""

    def __init__(self) -> None:
        self.handle = None
        if os.name != "nt":
            return
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateJobObjectW.restype = ctypes.c_void_p
        k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
        k32.SetInformationJobObject.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
        k32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        handle = k32.CreateJobObjectW(None, None)
        if not handle:
            return
        info = _ExtendedLimits()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not k32.SetInformationJobObject(handle, _JOB_EXTENDED_LIMIT_INFO_CLASS, ctypes.byref(info),
                                           ctypes.sizeof(info)):
            return
        self._k32 = k32
        self.handle = handle

    def assign(self, proc: subprocess.Popen) -> bool:
        if self.handle is None:
            return False
        return bool(self._k32.AssignProcessToJobObject(self.handle, int(proc._handle)))  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- worker spec

def seat_ids(humans: int) -> list[str]:
    return [f"P{i + 1}" for i in range(humans)]


def switch_overlay(settings: dict[str, Any]) -> dict[str, str]:
    # NOTE 74: every self-hosted beta game rolls the day on the clock.
    out: dict[str, str] = {"DAY_ROLL_CLOCK_MODE": "live"}
    if settings.get("rules") == "v311":
        out["V311_PROFILE"] = "v311"
    elif settings.get("starting_package") == "v311":
        out["STARTING_PACKAGE_MODE"] = "live"
    return out


def serve_command(settings: dict[str, Any], port: int, game_dir: Path, *, python: str | None = None,
                  idle_wait_s: float = 3.0) -> list[str]:
    humans = int(settings["humans"])
    bots = int(settings["bots"])
    names = [f"Guest {i + 1}" for i in range(humans)] + list(BOT_NAMES[:bots])
    cmd = [
        python or sys.executable, "-m", "tw2k.cli", "serve",
        "--host", "127.0.0.1", "--port", str(port),
        "--seed", str(int(settings["seed"])),
        "--universe-size", str(int(settings["universe_size"])),
        "--max-days", str(int(settings["max_days"])),
        "--turns-per-day", str(int(settings["turns_per_day"])),
        "--num-agents", str(humans + bots),
        "--agent-kind", "heuristic",
        "--external", ",".join(seat_ids(humans)),
        "--external-tokens-file", str(game_dir / "tokens.json"),
        "--external-idle-wait-s", f"{idle_wait_s:g}",
        "--day-seconds", f"{float(settings['day_seconds']):g}",
        "--agent-names", ",".join(names),
    ]
    if not settings.get("ferrengi", True):
        cmd.append("--no-ferrengi")
    override = settings.get("starting_credits_override")
    if override is not None:
        cmd.extend(["--starting-credits-override", str(int(override))])
    home = settings.get("home_planet_name")
    if home:
        cmd.extend(["--home-planet-name", str(home)])
    turns_override = settings.get("turns_per_day_override")
    if turns_override is not None:
        cmd.extend(["--turns-per-day-override", str(int(turns_override))])
    if settings.get("hold_until_human"):
        cmd.append("--hold-until-human")
    return cmd


def worker_env(*, gid: str, settings: dict[str, Any], game_dir: Path, brand: str, lobby_secret: str,
               spectator_token: str, seat_tokens: dict[str, str], resume: Path | None,
               base: dict[str, str] | None = None) -> dict[str, str]:
    src = str(Path(__file__).resolve().parents[2])
    env = {k: v for k, v in (os.environ if base is None else base).items()
           if not k.startswith(_STRIP_ENV_PREFIXES) and k not in _STRIP_ENV}
    env["PYTHONPATH"] = os.pathsep.join([src] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["COCKPIT_LAYOUT"] = "redesign"
    env[W.ENV_PUBLIC_MODE] = "1"
    env[W.ENV_LOBBY_SECRET] = lobby_secret
    env["TW2K_SPECTATOR_TOKEN"] = spectator_token
    env[W.ENV_BASE_PATH] = f"/g/{gid}"
    env[W.ENV_BRAND] = brand
    env[W.ENV_SWITCH_OVERLAY] = json.dumps(switch_overlay(settings), sort_keys=True)
    env[W.ENV_SNAPSHOT_DIR] = str(game_dir / "snapshots")
    env["TW2K_SAVES_DIR"] = str(game_dir / "saves")
    for seat, tok in seat_tokens.items():
        env[f"TW2K_EXTERNAL_TOKEN_{seat}"] = tok
    if resume is not None:
        env[W.ENV_RESUME] = str(resume)
    return env


def _rotate_log(path: Path) -> None:
    try:
        if not path.exists() or path.stat().st_size < LOG_ROTATE_BYTES:
            return
        for i in range(LOG_KEEP - 1, 0, -1):
            older = path.with_name(f"{path.name}.{i}")
            if older.exists():
                older.replace(path.with_name(f"{path.name}.{i + 1}"))
        path.replace(path.with_name(f"{path.name}.1"))
    except OSError:
        pass


@dataclass
class Worker:
    gid: str
    port: int
    proc: subprocess.Popen
    log: Any
    started_at: float = field(default_factory=time.time)
    stopping: bool = False

    @property
    def pid(self) -> int:
        return self.proc.pid

    def alive(self) -> bool:
        return self.proc.poll() is None


class WorkerManager:
    def __init__(self, cfg: LobbyConfig, *, python: str | None = None) -> None:
        self.cfg = cfg
        self.python = python or sys.executable
        self.job = JobObject()
        self.workers: dict[str, Worker] = {}

    def game_dir(self, gid: str) -> Path:
        return self.cfg.games_dir / gid

    def ports_in_use(self) -> set[int]:
        return {w.port for w in self.workers.values() if w.alive()}

    def spawn(self, gid: str, settings: dict[str, Any], port: int, *, brand: str, lobby_secret: str,
              spectator_token: str, seat_tokens: dict[str, str], resume: Path | None) -> Worker:
        assert_lobby_port(self.cfg, port)
        gdir = self.game_dir(gid)
        (gdir / "snapshots").mkdir(parents=True, exist_ok=True)
        (gdir / "saves").mkdir(parents=True, exist_ok=True)
        self.cfg.logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.cfg.logs_dir / f"game-{gid}.log"
        _rotate_log(log_path)
        log = open(log_path, "ab", buffering=0)
        log.write(f"\n--- worker start {time.strftime('%Y-%m-%d %H:%M:%S')} port={port} "
                  f"resume={'yes' if resume else 'no'} ---\n".encode())
        env = worker_env(gid=gid, settings=settings, game_dir=gdir, brand=brand, lobby_secret=lobby_secret,
                         spectator_token=spectator_token, seat_tokens=seat_tokens, resume=resume)
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        proc = subprocess.Popen(
            serve_command(settings, port, gdir, python=self.python, idle_wait_s=self.cfg.external_idle_wait_s),
            cwd=str(gdir), env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            creationflags=flags, start_new_session=os.name != "nt",
        )
        self.job.assign(proc)
        w = Worker(gid=gid, port=port, proc=proc, log=log)
        self.workers[gid] = w
        return w

    async def wait_healthy(self, gid: str, timeout_s: float | None = None) -> bool:
        w = self.workers.get(gid)
        if w is None:
            return False
        deadline = time.monotonic() + (timeout_s or self.cfg.boot_timeout_s)
        async with httpx.AsyncClient(timeout=2.0) as client:
            while time.monotonic() < deadline:
                if not w.alive():
                    return False
                try:
                    r = await client.get(f"http://127.0.0.1:{w.port}/healthz")
                    if r.status_code == 200:
                        return True
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.4)
        return False

    async def stop(self, gid: str, *, lobby_secret: str, spectator_token: str, graceful: bool = True) -> None:
        w = self.workers.get(gid)
        if w is None:
            return
        w.stopping = True
        if w.alive() and graceful:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(f"http://127.0.0.1:{w.port}/control/shutdown",
                                      headers=admin_headers(lobby_secret, spectator_token))
            except httpx.HTTPError:
                pass
            deadline = time.monotonic() + self.cfg.stop_timeout_s
            while w.alive() and time.monotonic() < deadline:
                await asyncio.sleep(0.25)
        if w.alive():
            self._kill_tree(w)
        try:
            w.log.close()
        except OSError:
            pass
        self.workers.pop(gid, None)

    def _kill_tree(self, w: Worker) -> None:
        """Only ever called on a process this lobby started (its own Popen)."""
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(w.pid)], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False)
        else:
            w.proc.kill()
        try:
            w.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass

    def kill_all(self) -> None:
        for w in list(self.workers.values()):
            if w.alive():
                self._kill_tree(w)
            try:
                w.log.close()
            except OSError:
                pass
        self.workers.clear()


def admin_headers(lobby_secret: str, spectator_token: str) -> dict[str, str]:
    return {W.LOBBY_HEADER: lobby_secret, "authorization": f"Bearer {spectator_token}"}
