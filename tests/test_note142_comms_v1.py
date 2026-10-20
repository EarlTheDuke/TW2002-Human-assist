"""NOTE 142. v3.11 player communications on the redesign Comms panel.

Sub-space radio, Fed Comm, a same-sector hail, and a corporation memo share one
line length, one pause between sends, and a turn log. The switch defaults to
legacy. "1" does not turn it on. V311_PROFILE "v311" does. Two browsers, one
process each, exchange a Fed Comm line and a hail.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

if __name__ == "__main__":
    _root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(_root), str(_root / "src")]

import pytest

import tests._cu_host as cu
import tw2k.engine.constants as K
from tests._cu_host import CuHost
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Corporation, Player, Ship
from tw2k.engine.observation import build_observation
from tw2k.engine.presence import note_poll
from tw2k.public.manual import render

ROOT = Path(__file__).resolve().parents[1]
SHOTS = Path("/opt/cursor/artifacts/note142")
FED_TEXT = "Hello <b>there</b> & friends"
HAIL_TEXT = "same sector"


def _world():
    universe = generate_universe(
        GameConfig(seed=4, universe_size=20, max_days=5, enable_planets=False, enable_ferrengi=False)
    )
    for pid, name, kind in (("P1", "Ann", "heuristic"), ("P2", "Bo", "external"), ("P3", "Cy", "heuristic")):
        player = Player(id=pid, name=name, ship=Ship(name="Ship"), credits=1_000, agent_kind=kind)
        player.sector_id = 1
        universe.players[pid] = player
        if pid not in universe.sectors[1].occupant_ids:
            universe.sectors[1].occupant_ids.append(pid)
    return universe


def _move(universe, pid: str, sector_id: int) -> None:
    player = universe.players[pid]
    home = universe.sectors[player.sector_id]
    if pid in home.occupant_ids:
        home.occupant_ids.remove(pid)
    player.sector_id = sector_id
    dest = universe.sectors[sector_id]
    if pid not in dest.occupant_ids:
        dest.occupant_ids.append(pid)


def _on(monkeypatch) -> None:
    monkeypatch.setattr(K, "COMMS_V311_MODE", "v311")


def test_switch_defaults_legacy_and_one_does_not_flip(monkeypatch) -> None:
    assert K.COMMS_V311_MODE == "legacy"
    assert K.comms_v311_live() is False
    assert K.COMMS_LINE_MAX == 155
    assert K.COMMS_MIN_GAP_S == 2.0
    monkeypatch.setattr(K, "COMMS_V311_MODE", "1")
    assert K.comms_v311_live() is False


def test_v311_profile_turns_comms_on_without_moving_the_flag(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.comms_v311_live() is True
    assert K.COMMS_V311_MODE == "legacy"


def test_legacy_hail_stays_in_the_inbox_and_dumps_omit_the_log() -> None:
    universe = _world()
    done = apply_action(universe, "P1", Action(kind=ActionKind.HAIL, args={"target": "P2", "message": "Ahoy"}))
    assert done.ok, done.error
    letter = universe.players["P2"].inbox[-1]
    assert letter["kind"] == "hail"
    assert letter["message"] == "Ahoy"
    assert universe.players["P2"].turn_log == []
    obs = build_observation(universe, "P2").model_dump()
    assert "turn_log" not in obs
    assert "comms" not in obs
    dumped = universe.players["P1"].model_dump()
    assert "turn_log" not in dumped
    assert "comms_sent_at" not in dumped
    assert "fedcomm_mute" not in dumped
    assert "hail_mute" not in dumped
    kinds = {row.kind for row in legal_actions(universe, "P1")}
    assert "radio" not in kinds
    refused = apply_action(universe, "P1", Action(kind=ActionKind.RADIO, args={"channel": 4, "message": "no"}))
    assert refused.ok is False
    assert refused.error == "unsupported action"


def test_radio_is_a_shared_channel_and_zero_is_off(monkeypatch) -> None:
    _on(monkeypatch)
    universe = _world()
    universe.players["P2"].radio_channel = 12
    universe.players["P3"].radio_channel = 9
    off = apply_action(
        universe, "P1", Action(kind=ActionKind.RADIO, args={"channel": 0, "message": "quiet"}),
    )
    assert off.ok is False
    assert off.error == "the radio is off. Pick a channel from 1 to 60000"
    assert universe.players["P2"].turn_log == []
    bad = apply_action(universe, "P1", Action(kind=ActionKind.RADIO, args={"channel": 60001}))
    assert bad.error == "radio channel must be 0 to 60000"
    done = apply_action(
        universe, "P1",
        Action(kind=ActionKind.RADIO, args={"channel": 12, "message": "Hello <b>deck</b>"}),
    )
    assert done.ok, done.error
    heard = universe.players["P2"].turn_log[-1]
    assert heard["line"] == "Sub-space radio [12] Ann: Hello <b>deck</b>"
    assert heard["message"] == "Hello <b>deck</b>"
    assert universe.players["P3"].turn_log == []
    assert universe.players["P2"].inbox == []
    kinds = {row.kind: row for row in legal_actions(universe, "P1")}
    assert kinds["radio"].legal is True
    assert universe.players["P1"].corp_ticker is None
    quiet = build_observation(universe, "P3")
    assert all("Hello" not in (row.get("summary") or "") for row in quiet.recent_events)
    loud = build_observation(universe, "P2")
    assert any("Sub-space radio [12] Ann" in (row.get("summary") or "") for row in loud.recent_events)


def test_line_length_rate_limit_and_a_bad_line_does_not_burn_the_gap(monkeypatch) -> None:
    _on(monkeypatch)
    universe = _world()
    universe.players["P2"].radio_channel = 4
    long = apply_action(
        universe, "P1",
        Action(kind=ActionKind.RADIO, args={"channel": 4, "message": "x" * 156}),
    )
    assert long.ok is False
    assert long.error == "a message line is 155 characters or less"
    blank = apply_action(
        universe, "P1",
        Action(kind=ActionKind.BROADCAST, args={"link": "fed", "message": "   \n  "}),
    )
    assert blank.error == "type a message"
    first = apply_action(
        universe, "P1",
        Action(kind=ActionKind.BROADCAST, args={"link": "fed", "message": "one"}),
    )
    assert first.ok, first.error
    second = apply_action(
        universe, "P1",
        Action(kind=ActionKind.BROADCAST, args={"link": "fed", "message": "two"}),
    )
    assert second.ok is False
    assert second.error == "wait a moment before the next message"
    universe.players["P1"].comms_sent_at = 0
    third = apply_action(
        universe, "P1",
        Action(kind=ActionKind.BROADCAST, args={"link": "fed", "message": "three"}),
    )
    assert third.ok, third.error
    tune = apply_action(universe, "P1", Action(kind=ActionKind.RADIO, args={"channel": 8}))
    assert tune.ok, tune.error
    assert universe.players["P1"].radio_channel == 8


def test_fed_comm_reaches_listeners_and_a_plain_broadcast_stays_mail(monkeypatch) -> None:
    _on(monkeypatch)
    universe = _world()
    universe.players["P3"].fedcomm_mute = True
    listen = apply_action(
        universe, "P1", Action(kind=ActionKind.BROADCAST, args={"link": "fed", "listen": False}),
    )
    assert listen.ok, listen.error
    assert universe.players["P1"].fedcomm_mute is True
    universe.players["P1"].fedcomm_mute = False
    done = apply_action(
        universe, "P1",
        Action(kind=ActionKind.BROADCAST, args={"link": "fed", "message": "all hands"}),
    )
    assert done.ok, done.error
    assert universe.players["P2"].turn_log[-1]["line"] == "Federation comm-link, Ann: all hands"
    assert universe.players["P3"].turn_log == []
    assert universe.players["P2"].inbox == []
    universe.players["P1"].comms_sent_at = 0
    plain = apply_action(
        universe, "P1", Action(kind=ActionKind.BROADCAST, args={"message": "old board"}),
    )
    assert plain.ok, plain.error
    assert universe.players["P2"].inbox[-1]["kind"] == "broadcast"
    assert universe.players["P2"].inbox[-1]["message"] == "old board"


def test_hail_is_same_sector_and_not_mail(monkeypatch) -> None:
    _on(monkeypatch)
    universe = _world()
    _move(universe, "P2", 2)
    away = apply_action(
        universe, "P1", Action(kind=ActionKind.HAIL, args={"target": "P2", "message": "far"}),
    )
    assert away.error == "that trader is not in this sector"
    missing = apply_action(
        universe, "P1", Action(kind=ActionKind.HAIL, args={"target": "P9", "message": "who"}),
    )
    assert missing.error == "unknown target"
    _move(universe, "P2", 1)
    note_poll(universe, "P2")
    done = apply_action(
        universe, "P1", Action(kind=ActionKind.HAIL, args={"target": "P2", "message": "near"}),
    )
    assert done.ok, done.error
    assert universe.players["P2"].inbox == []
    assert universe.players["P2"].turn_log[-1]["line"] == "Ann hails you: near"
    choices = {row.kind: row for row in legal_actions(universe, "P1")}["hail"]
    assert choices.params["target"]["choices"] == ["P2", "P3"]


def test_an_offline_or_muted_hail_falls_on_deaf_ears(monkeypatch) -> None:
    _on(monkeypatch)
    universe = _world()
    universe.players["P2"].agent_kind = "external"
    lost = apply_action(
        universe, "P1", Action(kind=ActionKind.HAIL, args={"target": "P2", "message": "anyone"}),
    )
    assert lost.ok, lost.error
    assert universe.players["P2"].inbox == []
    assert universe.players["P2"].turn_log == []
    assert universe.players["P1"].turn_log[-1]["line"] == "Your hail to Bo fell on deaf ears."
    assert universe.events[-1].summary == "Your hail to Bo fell on deaf ears."
    missed = build_observation(universe, "P2")
    assert all("anyone" not in (row.get("summary") or "") for row in missed.recent_events)
    note_poll(universe, "P2")
    universe.players["P2"].hail_mute = True
    universe.players["P1"].comms_sent_at = 0
    muted = apply_action(
        universe, "P1", Action(kind=ActionKind.HAIL, args={"target": "P2", "message": "still"}),
    )
    assert muted.ok, muted.error
    assert universe.players["P2"].turn_log == []
    assert "deaf ears" in universe.players["P1"].turn_log[-1]["line"]


def test_a_corporation_memo_stays_inside_the_corp(monkeypatch) -> None:
    _on(monkeypatch)
    universe = _world()
    universe.players["P1"].corp_ticker = "ZZ"
    universe.players["P2"].corp_ticker = "ZZ"
    universe.corporations["ZZ"] = Corporation(
        ticker="ZZ", name="Zed", ceo_id="P1", member_ids=["P1", "P2"],
    )
    alone = apply_action(
        universe, "P3", Action(kind=ActionKind.CORP_MEMO, args={"message": "nope"}),
    )
    assert alone.error == "not in a corporation"
    done = apply_action(
        universe, "P1", Action(kind=ActionKind.CORP_MEMO, args={"message": "members"}),
    )
    assert done.ok, done.error
    assert universe.players["P2"].turn_log[-1]["line"] == "Corporate memo (ZZ) Ann: members"
    assert universe.players["P3"].turn_log == []
    assert universe.players["P2"].inbox == []
    monkeypatch.setattr(K, "CORP_MODE", "tw2002")
    monkeypatch.setattr(K, "CORP_MEMO_SENDERS", "ceo")
    universe.players["P2"].comms_sent_at = 0
    blocked = apply_action(
        universe, "P2", Action(kind=ActionKind.CORP_MEMO, args={"message": "from the mate"}),
    )
    assert blocked.error == "only the C.E.O. may send a memo"


def test_the_turn_log_drops_a_line_after_ten_seconds(monkeypatch) -> None:
    _on(monkeypatch)
    universe = _world()
    from tw2k.engine.comms import seat_view

    universe.players["P2"].turn_log = [{
        "kind": "fedcomm", "from": "P1", "from_name": "Ann", "message": "old",
        "line": "Federation comm-link, Ann: old", "at": time.time() - 11,
    }]
    public, meta = seat_view(universe, universe.players["P2"])
    assert public == []
    assert meta["line_max"] == 155
    assert meta["show_s"] == 10
    assert meta["here"] == [{"id": "P1", "name": "Ann"}, {"id": "P3", "name": "Cy"}]
    fresh = build_observation(universe, "P2").model_dump()
    assert fresh["turn_log"] == []
    assert fresh["comms"]["fedcomm"] is True
    assert fresh["comms"]["hails"] is True
    assert fresh["comms"]["corp"] == ""


def test_manual_names_the_v311_comms_panel(monkeypatch) -> None:
    monkeypatch.setattr(K, "V311_PROFILE", "legacy")
    monkeypatch.setattr(K, "COMMS_V311_MODE", "legacy")
    legacy = render("Galaxy War Command")
    assert "The Comms panel sits on the deck" not in legacy
    assert "In legacy games, a hail is delivered into the other trader's mail either way." in legacy
    monkeypatch.setattr(K, "COMMS_V311_MODE", "v311")
    switched = render("Galaxy War Command")
    assert "The Comms panel sits on the deck" in switched
    assert "In this game, sub-space radio uses a channel from 1 to 60,000." in switched
    assert "An AI cockpit seat reads those lines on this same panel and answers a hail or a memo with Send." in switched
    assert "You wait 2 seconds between messages." in switched
    monkeypatch.setattr(K, "COMMS_V311_MODE", "legacy")
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    live = render("Galaxy War Command")
    assert "in v3.11 games, sub-space radio uses a channel from 1 to 60,000." in live
    assert "In legacy games" not in live


def test_the_ai_screen_reads_the_log_and_the_bot_page_is_unchanged() -> None:
    screen = (ROOT / "scripts" / "ai_cockpit" / "runner.py").read_text(encoding="utf-8")
    assert "data-ai-send" in screen
    assert "comms: text('[data-testid=turn-log]')" in screen
    html = (ROOT / "web" / "redesign.html").read_text(encoding="utf-8")
    assert 'data-testid="comms-panel"' in html
    assert 'data-ai-send' in html
    assert 'id="commsForm"' in html and "hidden" in html
    layout = (ROOT / "web" / "layout.js").read_text(encoding="utf-8")
    assert '["term", "Comms"]' in layout
    assert layout.count('["') >= 5
    for name in ("bot.html", "bot.js", "bot-parity.js"):
        body = (ROOT / "web" / name).read_text(encoding="utf-8")
        assert "comms-form" not in body, name
        assert "turn-log" not in body, name
        assert "paintComms" not in body, name


def test_two_seats_exchange_messages_in_separate_browsers(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api")
    assert sync_playwright
    _on(monkeypatch)
    job = Path(tempfile.mkdtemp(prefix="note142-comms-", dir=str(tmp_path)))
    p1 = "note142-comms-p1-token-0001"
    p2 = "note142-comms-p2-token-0002"
    with CuHost(job, p2, p1_token=p1, max_days=5, turns_per_day=80, seed=142) as host:
        assert host.port != 8099
        assert cu.allowed_test_port(host.port)
        universe = host.runner.state.universe
        _move(universe, "P1", universe.players["P2"].sector_id)
        (job / "job.json").write_text(json.dumps({
            "base": host.base,
            "p1": p1,
            "p2": p2,
        }), encoding="utf-8")
        env = os.environ.copy()
        env.pop("COCKPIT_LAYOUT", None)
        env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT)
        env["PYTHONIOENCODING"] = "utf-8"
        script = str(Path(__file__).resolve())
        procs = []
        for seat in ("p1", "p2"):
            procs.append(subprocess.Popen(
                [sys.executable, script, seat, str(job)],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            ))
        failed = []
        for seat, proc in zip(("p1", "p2"), procs, strict=True):
            try:
                out, err = proc.communicate(timeout=150)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = proc.communicate()
                failed.append(seat + " timed out\n" + (out or "")[-2000:] + (err or "")[-2000:])
                continue
            if proc.returncode != 0 or "BROWSER_OK " + seat not in (out or ""):
                failed.append(seat + "\n" + (out or "")[-2500:] + (err or "")[-2500:])
        assert failed == []


def _job(path: Path) -> dict:
    return json.loads(path.joinpath("job.json").read_text(encoding="utf-8"))


def _flag(path: Path, name: str) -> None:
    path.joinpath(name).write_text("ok", encoding="utf-8")


def _shot(page, name: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    height = page.evaluate("() => document.getElementById('deck').getBoundingClientRect().height")
    assert height > 400, height
    clear = page.evaluate(
        """() => {
          const send = document.querySelector('[data-testid=comms-send]').getBoundingClientRect();
          const hud = document.querySelector('.media-hud-inner');
          if (!hud || (hud.closest('[hidden]'))) return true;
          const box = hud.getBoundingClientRect();
          if (box.width < 2 || box.height < 2) return true;
          return send.right < box.left || send.left > box.right || send.bottom < box.top || send.top > box.bottom;
        }"""
    )
    assert clear, "the media still covers Send"
    page.screenshot(path=str(SHOTS / name))


def _chip(page) -> str:
    return (page.locator("#waitchip").inner_text() or "").strip()


def _tune(page) -> None:
    page.evaluate(
        """() => {
          const kind = document.querySelector('[data-testid=comms-kind]');
          kind.value = 'radio';
          kind.dispatchEvent(new Event('change'));
          const channel = document.querySelector('[data-testid=comms-channel]');
          channel.value = '4';
          document.querySelector('[data-testid=comms-tune]').click();
        }"""
    )


def _leave_turn(page) -> None:
    try:
        page.wait_for_function(
            "() => (document.querySelector('#waitchip') || {}).textContent !== 'YOUR MOVE'",
            timeout=15_000,
        )
    except Exception:
        page.wait_for_timeout(400)


def _yield_while(page, pending, timeout: float = 50) -> None:
    """Give the turn back while `pending` is still true, so the other seat can act."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not pending():
            return
        if _chip(page) == "YOUR MOVE":
            _tune(page)
            _leave_turn(page)
        else:
            page.wait_for_timeout(250)
    raise TimeoutError("the other seat did not finish")


def _server_channel(spec: dict, seat: str) -> int:
    who = "P1" if seat == "p1" else "P2"
    req = urllib.request.Request(
        f"{spec['base']}/harness/v1/{who}/observation?peek=1",
        headers={"Authorization": "Bearer " + spec[seat], "X-TW2K-Seat": who},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    comms = (body.get("observation") or {}).get("comms") or {}
    return int(comms.get("radio_channel") or 0)


def _browser(seat: str, jobdir: str) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    job = Path(jobdir)
    spec = _job(job)
    token = spec[seat]
    who = "P1" if seat == "p1" else "P2"
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            page.goto(f"{spec['base']}/bot?layout=redesign&seat={who}&token={token}")
            page.wait_for_selector("[data-testid=comms-form]:not([hidden])", timeout=25_000)
            deadline = time.time() + 40
            while time.time() < deadline and _server_channel(spec, seat) != 4:
                if _chip(page) == "YOUR MOVE":
                    _tune(page)
                    _leave_turn(page)
                else:
                    page.wait_for_timeout(250)
            if _server_channel(spec, seat) != 4:
                raise TimeoutError("radio did not tune to 4")
            _flag(job, seat + "-tuned")
            _yield_while(page, lambda: not (job.joinpath("p1-tuned").is_file() and job.joinpath("p2-tuned").is_file()))
            if seat == "p1":
                _send_when_ready(page, "fed", FED_TEXT, "")
                _flag(job, "p1-sent")
                _see(page, "Commander hails you: " + HAIL_TEXT)
            else:
                _yield_while(page, lambda: not job.joinpath("p1-sent").is_file())
                _see(page, "Federation comm-link, HBot: " + FED_TEXT)
                _shot(page, "p2-comms.png")
                _send_when_ready(page, "hail", HAIL_TEXT, "P1")
                page.click("[data-testid=layout-open]")
                page.wait_for_selector("#layoutList .layout-row")
                labels = page.locator("#layoutList .layout-row").all_inner_texts()
                assert len(labels) == 5
                assert any("Comms" in label for label in labels)
            if seat == "p1":
                _shot(page, "p1-comms.png")
            log = page.locator("[data-testid=turn-log]")
            assert log.locator("b").count() == 0
            if seat == "p2":
                assert "<b>" in log.inner_text()
                assert "&" in log.inner_text()
        except Exception:
            try:
                _shot(page, seat + "-failed.png")
            except Exception:
                pass
            raise
        finally:
            browser.close()
    print("BROWSER_OK " + seat)


def _send_when_ready(page, kind: str, message: str, target: str) -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        if _chip(page) != "YOUR MOVE":
            page.wait_for_timeout(200)
            continue
        outcome = page.evaluate(
            """([kind, message, target]) => {
              const pick = document.querySelector('[data-testid=comms-kind]');
              pick.value = kind;
              pick.dispatchEvent(new Event('change'));
              if (kind === 'hail') {
                const who = document.querySelector('[data-testid=comms-target]');
                const opt = who && Array.from(who.options).find((row) => row.value === target);
                if (!opt) return 'missing';
                who.value = target;
              }
              document.querySelector('[data-testid=comms-message]').value = message;
              document.querySelector('[data-testid=comms-send]').click();
              return 'sent';
            }""",
            [kind, message, target],
        )
        if outcome == "missing":
            _tune(page)
            _leave_turn(page)
            continue
        _leave_turn(page)
        err = page.locator("#err")
        if err.count() and err.is_visible():
            raise AssertionError(err.inner_text())
        return
    raise TimeoutError("could not send " + kind)


def _see(page, needle: str) -> None:
    deadline = time.time() + 40
    while time.time() < deadline:
        text = page.locator("[data-testid=turn-log]").inner_text()
        head = ""
        head_node = page.locator("[data-testid=turn-log-head]")
        if head_node.count():
            head = head_node.inner_text().strip()
        if needle in text and _chip(page) == "YOUR MOVE" and head == "At the start of your turn":
            assert page.locator("[data-testid=turn-log] b").count() == 0
            return
        if _chip(page) == "YOUR MOVE":
            _tune(page)
            _leave_turn(page)
        else:
            page.wait_for_timeout(300)
    raise AssertionError(needle + " | " + page.locator("[data-testid=turn-log]").inner_text())


if __name__ == "__main__":
    _browser(sys.argv[1], sys.argv[2])
