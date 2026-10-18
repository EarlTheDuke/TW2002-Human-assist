"""selfhost-beta-v1 smoke: a real lobby with 3 games, 1 guest seat each over HTTP through the proxy.

    python scripts/selfhost/smoke.py --lobby-port 8099 --game-ports 8100-8102

Each game: v3.11 rules, 2 code bots, 1 guest seat, a 120 s day, run to day 3. Along the way: a
spectator, the beta-full answer, cross-game token checks, one game put to sleep and woken by its
player, one graceful lobby restart, CPU/RAM samples, and screenshots (1920 and 390 wide).
Everything is stopped at the end. Nothing outside the given ports is touched.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from tw2k.public.config import parse_port_range, port_is_free  # noqa: E402


class Guest:
    def __init__(self, url: str, name: str) -> None:
        self.c = httpx.Client(base_url=url, timeout=60)
        self.name = name
        self.gid = ""
        self.stats = {"actions": 0, "accepted": 0, "rejected": 0, "polls": 0, "waking_503": 0, "resumed": 0,
                      "conn_errors": 0, "unauthorized": 0}
        self.tokens: list[str] = []
        self.first_obs_keys: list[str] = []

    def accept(self) -> None:
        self.c.post("/api/accept", json={})

    def claim(self, path: str) -> None:
        url = self.c.post(path, json={}).json()["claim_url"]
        self.tokens.append(url.split("token=")[1])
        self.c.get(url)

    def resume(self) -> bool:
        r = self.c.post(f"/api/games/{self.gid}/resume", json={})
        if r.status_code != 200:
            return False
        url = r.json()["claim_url"]
        self.tokens.append(url.split("token=")[1])
        self.c.get(url)
        self.stats["resumed"] += 1
        return True

    def play(self, stop: threading.Event) -> None:
        hdr = {"X-TW2K-Seat": "P1"}
        while not stop.is_set():
            try:
                r = self.c.get(f"/g/{self.gid}/harness/v1/P1/observation", params={"wait_s": 8}, headers=hdr)
            except httpx.HTTPError:
                self.stats["conn_errors"] += 1
                time.sleep(1.0)
                continue
            self.stats["polls"] += 1
            if r.status_code == 401:
                self.stats["unauthorized"] += 1
                if not self.resume():
                    time.sleep(1.0)
                continue
            if r.status_code in (502, 503):
                self.stats["waking_503"] += 1
                time.sleep(1.5)
                continue
            if r.status_code != 200:
                time.sleep(1.0)
                continue
            body = r.json()
            obs = body.get("observation")
            if not obs or not body.get("awaiting_input"):
                continue
            if not self.first_obs_keys:
                self.first_obs_keys = sorted(obs)[:12]
            adj = [a.get("sector_id", a.get("id")) for a in obs.get("adjacent") or []]
            adj = [a for a in adj if isinstance(a, int)]
            action = {"kind": "warp", "args": {"target": random.choice(adj)}} if adj else {"kind": "scan", "args": {}}
            try:
                a = self.c.post(f"/g/{self.gid}/harness/v1/P1/action", headers=hdr,
                                json={"action": action, "turn_seq": body.get("turn_seq")})
            except httpx.HTTPError:
                self.stats["conn_errors"] += 1
                continue
            self.stats["actions"] += 1
            if a.status_code == 200 and a.json().get("accepted", True):
                self.stats["accepted"] += 1
            else:
                self.stats["rejected"] += 1
            time.sleep(0.4)


def sample(lobby_pid: int) -> dict:
    import psutil

    try:
        root = psutil.Process(lobby_pid)
        procs = [root] + root.children(recursive=True)
    except psutil.Error:
        return {}
    for p in procs:
        try:
            p.cpu_percent(None)
        except psutil.Error:
            pass
    time.sleep(1.0)
    cpu = rss = 0.0
    n = 0
    rows = {}
    for p in procs:
        try:
            pc, mem = p.cpu_percent(None), p.memory_info().rss
            cmd = p.cmdline()
        except psutil.Error:
            continue
        cpu += pc
        rss += mem
        n += 1
        if p.pid == lobby_pid:
            rows["lobby"] = {"cpu_percent": round(pc, 1), "rss_mb": round(mem / 1e6)}
        elif "--port" in cmd:
            port = cmd[cmd.index("--port") + 1]
            rows[f"worker:{port}"] = {"cpu_percent": round(pc, 1), "rss_mb": round(mem / 1e6)}
    return {"t": round(time.time()), "processes": n, "cpu_percent": round(cpu, 1), "rss_mb": round(rss / 1e6),
            "per_process": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lobby-port", type=int, default=8099)
    ap.add_argument("--game-ports", default="8100-8102")
    ap.add_argument("--root", default=str(REPO / "saves" / "selfhost-smoke"))
    ap.add_argument("--shots", default=str(REPO / "docs" / "playtests" / "selfhost-beta-v1"))
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--max-minutes", type=float, default=16.0)
    args = ap.parse_args()

    ports = [args.lobby_port] + list(parse_port_range(args.game_ports))
    busy = [p for p in ports if not port_is_free(p)]
    if busy:
        print(f"ports busy, not starting: {busy}")
        return 2
    root = Path(args.root)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    shots = Path(args.shots)
    shots.mkdir(parents=True, exist_ok=True)
    url = f"http://127.0.0.1:{args.lobby_port}"
    env = {k: v for k, v in os.environ.items() if not k.startswith(("TW2K_", "TW2002_"))}
    env.update(TW2K_LOBBY_ROOT=str(root), TW2K_LOBBY_PORT=str(args.lobby_port), TW2K_GAME_PORTS=args.game_ports,
               TW2K_LOBBY_DAY_PRESETS="2m=120", TW2K_LOBBY_MAX_GAMES=str(len(ports) - 1),
               PYTHONPATH=str(REPO / "src"), PYTHONUNBUFFERED="1")
    report: dict = {"ports": ports, "timeline": [], "samples": []}
    t0 = time.time()

    def note(what: str, **kw) -> None:
        row = {"t_s": round(time.time() - t0, 1), "event": what, **kw}
        report["timeline"].append(row)
        print(json.dumps(row), flush=True)

    def start_lobby() -> subprocess.Popen:
        p = subprocess.Popen([sys.executable, "-m", "tw2k.cli", "lobby"], env=env, cwd=str(REPO),
                             stdout=open(root / "lobby.console.log", "ab"), stderr=subprocess.STDOUT)
        while True:
            if p.poll() is not None:
                raise SystemExit("lobby exited")
            try:
                if httpx.get(url + "/healthz", timeout=2).status_code == 200:
                    return p
            except httpx.HTTPError:
                time.sleep(0.3)

    def stop_lobby(p: subprocess.Popen) -> float:
        s = time.time()
        key = (root / "lobby.shutdown.key").read_text().strip()
        httpx.post(url + "/admin/shutdown", headers={"x-lobby-shutdown": key}, timeout=30)
        p.wait(90)
        return round(time.time() - s, 1)

    lobby = start_lobby()
    note("lobby up", pid=lobby.pid)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for tag, vp in {"1920": {"width": 1920, "height": 1080}, "390": {"width": 390, "height": 844}}.items():
            ctx = b.new_context(viewport=vp)
            pg = ctx.new_page()
            pg.goto(url + "/")
            pg.screenshot(path=str(shots / f"disclaimer-{tag}.png"))
            pg.click("text=I understand")
            pg.wait_for_selector("text=Closed beta lobby")
            pg.goto(url + "/new")
            pg.screenshot(path=str(shots / f"new-game-{tag}.png"), full_page=True)
            ctx.close()
        b.close()
    note("screenshots before games")
    guests = [Guest(url, f"guest{i + 1}") for i in range(3)]
    stop = threading.Event()
    threads: list[threading.Thread] = []
    try:
        for i, g in enumerate(guests):
            g.accept()
            s = time.time()
            r = g.c.post("/api/games", json={"name": f"Smoke {i + 1}", "rules": "v311", "bots": 2, "humans": 1,
                                             "day": "2m", "universe_size": 1000, "max_days": 10})
            assert r.status_code == 200, r.text
            g.gid = r.json()["id"]
            note("game created", game=g.gid, seconds=round(time.time() - s, 1))
            g.claim(f"/api/games/{g.gid}/join")
            th = threading.Thread(target=g.play, args=(stop,), daemon=True)
            th.start()
            threads.append(th)
        extra = Guest(url, "late")
        extra.accept()
        r = extra.c.post("/api/games", json={"name": "Fourth", "humans": 1})
        report["beta_full"] = {"status": r.status_code, "detail": r.json().get("detail")}
        note("fourth game", status=r.status_code, detail=r.json().get("detail"))

        leaks = []
        for g in guests:
            for other in guests:
                if other is g:
                    continue
                rr = httpx.get(f"{url}/g/{other.gid}/harness/v1/P1/observation?peek=1",
                               headers={"authorization": f"Bearer {g.tokens[-1]}"},
                               cookies={"gwc_guest": g.c.cookies.get("gwc_guest")})
                leaks.append(rr.status_code)
        report["cross_game_token_checks"] = leaks
        note("cross-game tokens", codes=sorted(set(leaks)), checks=len(leaks))

        watcher = Guest(url, "watcher")
        watcher.accept()

        async def frames(gid: str) -> int:
            from websockets.asyncio.client import connect

            cookie = "; ".join(f"{c.name}={c.value}" for c in watcher.c.cookies.jar
                               if c.path in ("/", f"/g/{gid}/"))
            n = 0
            async with connect(f"ws://127.0.0.1:{args.lobby_port}/g/{gid}/ws",
                               additional_headers={"cookie": cookie}) as ws:
                end = time.time() + 10
                while time.time() < end:
                    try:
                        await asyncio.wait_for(ws.recv(), max(0.1, end - time.time()))
                        n += 1
                    except asyncio.TimeoutError:
                        break
            return n

        report["spectator"] = {}
        for g in guests:
            watcher.c.get(f"/g/{g.gid}/watch")
            st = watcher.c.get(f"/g/{g.gid}/state")
            nframes = asyncio.run(frames(g.gid))
            hidden = watcher.c.post(f"/g/{g.gid}/control/pause")
            rival = watcher.c.get(f"/g/{g.gid}/harness/v1/P1/observation?peek=1")
            act = watcher.c.post(f"/g/{g.gid}/harness/v1/P1/action", json={"action": {"kind": "scan"}})
            report["spectator"][g.gid] = {"state": st.status_code, "ws_frames_10s": nframes,
                                          "control_pause": hidden.status_code, "seat_observation": rival.status_code,
                                          "seat_action": act.status_code}
            note("spectator", game=g.gid, **report["spectator"][g.gid])

        def days() -> dict:
            out = {}
            for g in guests:
                try:
                    out[g.gid] = g.c.get(f"/api/games/{g.gid}").json()
                except (httpx.HTTPError, ValueError):
                    out[g.gid] = {}
            return out

        shot_state = {"done": False}

        def screenshots() -> None:
            from playwright.sync_api import sync_playwright

            sizes = {"1920": {"width": 1920, "height": 1080}, "390": {"width": 390, "height": 844}}

            def cookies_of(cl: httpx.Client) -> list[dict]:
                return [{"name": c.name, "value": c.value, "domain": "127.0.0.1", "path": c.path or "/"}
                        for c in cl.cookies.jar]

            with sync_playwright() as pw:
                b = pw.chromium.launch()
                for tag, vp in sizes.items():
                    fresh = b.new_context(viewport=vp)
                    pg = fresh.new_page()
                    pg.goto(url + "/")
                    pg.click("text=I understand")
                    pg.wait_for_selector("text=Closed beta lobby")
                    pg.screenshot(path=str(shots / f"lobby-{tag}.png"), full_page=True)
                    fresh.close()
                    seat = b.new_context(viewport=vp)
                    seat.add_cookies(cookies_of(guests[0].c))
                    pg = seat.new_page()
                    pg.goto(f"{url}/g/{guests[0].gid}/bot?seat=P1&mode=cu")
                    pg.wait_for_function("document.querySelector('.sign-in') && document.querySelector('.sign-in').hidden",
                                         timeout=15000)
                    pg.wait_for_timeout(1500)
                    pg.screenshot(path=str(shots / f"cockpit-header-{tag}.png"))
                    seat.close()
                    spec = b.new_context(viewport=vp)
                    spec.add_cookies(cookies_of(watcher.c))
                    pg = spec.new_page()
                    pg.goto(f"{url}/g/{guests[0].gid}/")
                    pg.wait_for_timeout(4000)
                    pg.screenshot(path=str(shots / f"spectator-{tag}.png"))
                    spec.close()
                    full = b.new_context(viewport=vp)
                    full.add_cookies(cookies_of(extra.c))
                    pg = full.new_page()
                    pg.goto(url + "/new")
                    pg.screenshot(path=str(shots / f"beta-full-{tag}.png"))
                    full.close()
                b.close()
            shot_state["done"] = True

        report["samples"].append(sample(lobby.pid))
        slept = restarted = False
        deadline = t0 + args.max_minutes * 60
        while time.time() < deadline:
            time.sleep(10)
            report["samples"].append(sample(lobby.pid))
            info = days()
            ds = {k: v.get("day") for k, v in info.items()}
            note("days", days=ds, status={k: v.get("status") for k, v in info.items()})
            if not shot_state["done"] and time.time() - t0 > 40:
                try:
                    screenshots()
                    note("screenshots", folder=str(shots))
                except Exception as exc:  # report and keep going
                    note("screenshots failed", error=repr(exc)[:200])
                    shot_state["done"] = True
            if not slept and time.time() - t0 > 90:
                adm = httpx.get(url + "/admin").text
                csrf = re.search(r'name="csrf" value="([0-9a-f]+)"', adm).group(1)
                target = guests[2]
                s = time.time()
                httpx.post(f"{url}/admin/games/{target.gid}/sleep", data={"csrf": csrf}, timeout=60)
                st_sleep = target.c.get(f"/api/games/{target.gid}").json()["status"]
                note("admin sleep", game=target.gid, status=st_sleep, seconds=round(time.time() - s, 1))
                w0 = time.time()
                while time.time() - w0 < 60:
                    if target.c.get(f"/api/games/{target.gid}").json()["status"] == "running" and \
                            target.stats["resumed"] >= 1:
                        break
                    time.sleep(0.5)
                note("woken by its player", game=target.gid, seconds=round(time.time() - w0, 1),
                     resumed=target.stats["resumed"])
                slept = True
            if slept and not restarted and time.time() - t0 > 160:
                down = stop_lobby(lobby)
                s = time.time()
                lobby = start_lobby()
                note("lobby restarted", stop_seconds=down, start_seconds=round(time.time() - s, 1), pid=lobby.pid)
                restarted = True
            if restarted and all((d or 0) >= args.days for d in ds.values()):
                note("all games reached day", day=args.days)
                break
        report["guests"] = {g.gid: g.stats for g in guests}
        report["final"] = days()
    finally:
        stop.set()
        for th in threads:
            th.join(15)
        if lobby.poll() is None:
            report["final_stop_seconds"] = stop_lobby(lobby)
        logs = ""
        for p in (root / "logs").glob("*.log*"):
            logs += p.read_text(encoding="utf-8", errors="replace")
        secrets_seen = [t for g in guests for t in g.tokens if t in logs]
        secrets_seen += [c for c in (g.c.cookies.get("gwc_guest") for g in guests) if c and c in logs]
        report["log_secret_hits"] = len(secrets_seen)
        report["ports_free_after"] = all(port_is_free(p) for p in ports)
        report["elapsed_s"] = round(time.time() - t0, 1)
        per: dict = {}
        for smp in report["samples"]:
            for key, row in smp.get("per_process", {}).items():
                per.setdefault(key, []).append(row)
        report["per_process_summary"] = {
            key: {"samples": len(rows),
                  "cpu_avg": round(sum(r["cpu_percent"] for r in rows) / len(rows), 1),
                  "cpu_peak": max(r["cpu_percent"] for r in rows),
                  "rss_avg_mb": round(sum(r["rss_mb"] for r in rows) / len(rows)),
                  "rss_peak_mb": max(r["rss_mb"] for r in rows)}
            for key, rows in sorted(per.items())}
        (shots / "smoke.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({k: report.get(k) for k in ("guests", "log_secret_hits", "ports_free_after", "elapsed_s",
                                                     "per_process_summary", "spectator")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
