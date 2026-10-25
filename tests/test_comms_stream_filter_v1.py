"""COMMS stays player channels. Trade failures stay on the verdict.

Ben saw "Guest 1 trade failed: You only have 15 empty holds." under the COMMS
header. That line is TRADE_FAILED (NOTE 71 hold check) from recent_events,
painted by the redesign activity log. The verdict and lastResult already say
the same refusal. Fed, radio, private, and corporation lines stay in the stream.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, generate_universe
from tw2k.engine.models import Commodity, EventKind, Player, Ship, ShipClass
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import apply_action
from tw2k.server.cockpit_fields import after_action

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "web" / "comms-stream.js"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node not installed")


def _filter(events: list) -> list:
    script = (
        f"const F = require({json.dumps(str(HELPER))});"
        "let raw = '';"
        "process.stdin.on('data', (chunk) => { raw += chunk; });"
        "process.stdin.on('end', () => {"
        "  const rows = JSON.parse(raw);"
        "  const before = JSON.stringify(rows);"
        "  const kept = F.forCommsActivity(rows);"
        "  process.stdout.write(JSON.stringify({kept, same: JSON.stringify(rows) === before}));"
        "});"
    )
    proc = subprocess.run(
        [NODE, "-e", script],
        input=json.dumps(events),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=30,
    )
    body = json.loads(proc.stdout)
    assert body["same"] is True
    return body["kept"]


def _universe():
    return generate_universe(GameConfig(
        seed=631, universe_size=80, max_days=3, turns_per_day=40,
        starting_credits=50_000, enable_ferrengi=False, enable_planets=False,
    ))


def _selling_port(universe, commodity: Commodity):
    for sector in universe.sectors.values():
        port = sector.port
        if port is not None and port.sells(commodity) and sector.id not in K.FEDSPACE_SECTORS:
            return sector
    raise AssertionError(f"no port sells {commodity}")


def _park(universe, player, sector_id: int) -> None:
    here = universe.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = sector_id
    dest = universe.sectors[sector_id]
    if player.id not in dest.occupant_ids:
        dest.occupant_ids.append(player.id)


@needs_node
def test_empty_hold_refusal_stays_on_the_verdict_and_leaves_comms(monkeypatch) -> None:
    monkeypatch.setattr(K, "HAGGLE_COUNTER_MODE", "live")
    universe = _universe()
    port = _selling_port(universe, Commodity.EQUIPMENT)
    player = Player(
        id="P1", name="Guest 1",
        ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, holds=15),
        sector_id=1, credits=50_000, alignment=100, experience=0, turns_per_day=40,
    )
    universe.players[player.id] = player
    _park(universe, player, port.id)
    assert int(player.ship.cargo_free) == 15

    result = apply_action(universe, player.id, Action(
        kind=ActionKind.TRADE, args={"side": "buy", "commodity": "equipment", "qty": 20},
    ))
    assert result.ok is False
    assert result.error == "You only have 15 empty holds."

    failed = next(ev for ev in reversed(universe.events) if ev.kind == EventKind.TRADE_FAILED)
    assert failed.summary == "Guest 1 trade failed: You only have 15 empty holds."

    agent = SimpleNamespace()
    after_action(
        agent, universe, player,
        SimpleNamespace(kind="trade", args={"side": "buy", "commodity": "equipment", "qty": 20}),
        SimpleNamespace(ok=False, error=result.error),
        {"credits": int(player.credits), "turns_today": int(player.turns_today)},
    )
    verdict = agent.cockpit_verdict
    assert verdict["ok"] is False
    assert verdict["reason"] == "You only have 15 empty holds."
    assert verdict["kind"] == "trade"

    obs = build_observation(universe, player.id)
    seen = [row for row in obs.recent_events if row.get("kind") == "trade_failed"]
    assert seen and seen[-1]["summary"] == failed.summary

    fed = {
        "seq": 9001, "kind": "broadcast",
        "summary": "Federation comm-link, HBot: ore is cheap at 12",
        "facts": {"link": "fed", "message": "ore is cheap at 12"},
    }
    hail = {
        "seq": 9002, "kind": "hail",
        "summary": "Other hails you: trade failed, try sector 4",
        "facts": {"message": "trade failed, try sector 4"},
    }
    kept = _filter([*seen, fed, hail])
    summaries = [row.get("summary") for row in kept]
    assert failed.summary not in summaries
    assert fed["summary"] in summaries
    assert hail["summary"] in summaries


@needs_node
def test_filter_drops_refusal_twins_and_keeps_channels_and_world_lines() -> None:
    rows = [
        {"seq": 1, "kind": "trade_failed", "summary": "Guest 1 trade failed: You only have 15 empty holds."},
        {"seq": 2, "kind": "trade_failed", "summary": "Guest 1 port countered at 105"},
        {"seq": 3, "kind": "trade_failed", "summary": "Guest 1 planetary trade refused: We're not interested."},
        {"seq": 4, "kind": "warp_blocked", "summary": "Guest 1 tried to warp to 712 (no warp)"},
        {"seq": 5, "kind": "agent_error", "summary": "[Guest 1] invalid action: lift off first"},
        {"seq": 6, "kind": "system", "summary": "[Guest 1] agent error: out of turns"},
        {"seq": 7, "kind": "broadcast", "summary": "Federation comm-link, HBot: hold the lane", "facts": {"link": "fed"}},
        {"seq": 8, "kind": "broadcast", "summary": "Sub-space radio [4] HBot: quiet", "payload": {"link": "radio"}},
        {"seq": 9, "kind": "hail", "summary": "HBot hails you: meet me in 8"},
        {"seq": 10, "kind": "corp_memo", "summary": "Corporate memo (ABC) HBot: dump ore"},
        {"seq": 11, "kind": "combat", "summary": "Guest 1 lost 2 shields and 4 fighters"},
        {"seq": 12, "kind": "ferrengi_encounter", "summary": "** Ferrengi Fighter Attack! **"},
        {"seq": 13, "kind": "warp", "summary": "Guest 1 warped to 12"},
        {"seq": 14, "kind": "trade", "summary": "Guest 1 bought 10 equipment"},
        {"seq": 15, "kind": "mine_detonated", "summary": "Mines hit Guest 1 for 30 damage"},
        {"seq": 16, "kind": "cockpit_note", "summary": "Sector 9 is now on your avoid list."},
        {"seq": 17, "kind": "fed_response", "summary": "Federation warns Guest 1 — no combat in FedSpace!"},
        {"seq": 18, "summary": "Guest 1 trade failed: not enough credits"},
    ]
    kept = _filter(rows)
    kinds = [row.get("kind") for row in kept]
    summaries = [row.get("summary") for row in kept]
    assert "trade_failed" not in kinds
    assert "warp_blocked" not in kinds
    assert "agent_error" not in kinds
    assert "Guest 1 trade failed: not enough credits" not in summaries
    assert "[Guest 1] agent error: out of turns" not in summaries
    for seq in (7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17):
        assert any(row.get("seq") == seq for row in kept)
    assert [row.get("seq") for row in kept] == [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]


def test_redesign_log_filters_comms_and_the_other_pages_do_not_paint_it() -> None:
    """The activity stream under COMMS is redesign #log. Verdict text is separate.

    /bot Comms reads the inbox. Its event chip groups trade_failed with trades,
    not with comms. /play does not paint recent_events under a COMMS header.
    """
    redesign = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")
    paint = redesign.split("function paintLog()", 1)[1].split("function rememberLine", 1)[0]
    assert "TW2KCommsStream.forCommsActivity" in paint
    assert "streamLog.push" not in paint
    comms = redesign.split("function paintComms()", 1)[1].split("function syncCommsFields", 1)[0]
    assert "forCommsActivity" not in comms
    assert "recent_events" not in comms
    assert "turn_log" in comms
    verdict = redesign.split("function paintVerdict()", 1)[1].split("function releaseTradeFocus", 1)[0]
    assert "CK.verdict" in verdict or "CK && CK.verdict" in verdict
    assert "Last action:" in verdict
    act = redesign.split("const bad = ", 1)[1].split("if (bad)", 1)[0]
    assert "trade failed" in act
    assert "setResult" in redesign.split("if (bad)", 1)[1][:500]

    page = (ROOT / "web" / "redesign.html").read_text(encoding="utf-8")
    assert page.index("/static/comms-stream.js") < page.index("/static/redesign.js")
    assert 'id="log"' in page and 'id="verdict"' in page and 'id="lastResult"' in page
    panel = page.split('data-testid="comms-panel"', 1)[1].split("</section>", 1)[0]
    assert 'id="log"' in panel and 'id="turnLog"' in panel

    bot = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")
    rendered = bot.split("function renderComms(", 1)[1].split("function renderIntel", 1)[0]
    assert "inbox" in rendered
    assert "recent_events" not in rendered
    assert 'trade_failed: "trade"' in bot
    assert 'hail: "comms"' in bot

    play = (ROOT / "web" / "play.js").read_text(encoding="utf-8")
    assert "recent_events" not in play
    assert "streamLog" not in play


def test_redesign_page_cache_busts_the_comms_helper() -> None:
    from tw2k.server.app import _redesign_page, _web_root

    body = _redesign_page(_web_root()).body.decode("utf-8")
    assert "/static/comms-stream.js?v=" in body
    assert body.index("comms-stream.js") < body.index("redesign.js")
