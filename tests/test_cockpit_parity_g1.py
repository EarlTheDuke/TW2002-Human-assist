"""Grokbot-player G1 - cockpit information parity (CP1-CP5).

docs/plans/2026-09-26-cockpit-parity-plan.md: every field an API LLM seat
receives in `format_observation` must be visible on `/bot` without opening
Raw obs, and the cockpit must stay fogged (own Observation, own events).

The row/transcript text lives in web/bot-parity.js (pure functions, no DOM),
so these tests execute it under Node against observations built by the real
engine instead of only grepping markup.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path

import httpx
import pytest

from tw2k.agents.prompts import format_observation, stage_hint
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import Corporation, Player
from tw2k.engine.observation import Observation, build_observation
from tw2k.engine.runner import _bfs_path, apply_action
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")
JS = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")
PARITY_PATH = ROOT / "web" / "bot-parity.js"
PARITY = PARITY_PATH.read_text(encoding="utf-8")
NODE = shutil.which("node")
TOK2 = "g1-token-p2-000000000000000"


def _move(u, pid: str, sid: int) -> None:
    p = u.players[pid]
    u.sectors[p.sector_id].occupant_ids = [x for x in u.sectors[p.sector_id].occupant_ids if x != pid]
    p.sector_id = sid
    u.sectors[sid].occupant_ids.append(pid)


def _empire_universe():
    """P1 owns a genesis world, shares corp ACE with P2, has P3 in its
    sector and P4 far away, plus an operator directive and 10 dialogue lines."""
    u = generate_universe(GameConfig(seed=31, universe_size=90, max_days=3, turns_per_day=200,
                                     starting_credits=100_000, enable_ferrengi=False, enable_planets=True))
    for pid, name in (("P1", "Me"), ("P2", "Mate"), ("P3", "Neighbour"), ("P4", "Stranger")):
        u.players[pid] = Player(id=pid, name=name, agent_kind="external", sector_id=1, credits=100_000)
        u.sectors[1].occupant_ids.append(pid)
    deep = next(s for s in sorted(u.sectors) if s > 10 and not u.sectors[s].planet_ids
                and len(_bfs_path(u, 1, s)) >= K.GENESIS_MIN_HOPS_FROM_STARDOCK)
    _move(u, "P1", deep)
    u.players["P1"].ship.genesis = 1
    assert apply_action(u, "P1", Action(kind=ActionKind.DEPLOY_GENESIS, args={})).ok
    _move(u, "P3", deep)
    _move(u, "P4", next(s for s in sorted(u.sectors) if s not in (1, deep) and s > 20))
    u.corporations["ACE"] = Corporation(ticker="ACE", name="Aces", ceo_id="P1", member_ids=["P1", "P2"])
    u.players["P1"].corp_ticker = "ACE"
    u.players["P2"].corp_ticker = "ACE"
    me = u.players["P1"]
    me.set_operator_directive("Hold the home world, ferry colonists", day=1, tick=7)
    for i in range(10):
        me.append_operator_dialogue(role="operator" if i % 2 == 0 else "ai", message=f"line {i}", day=1, tick=i)
    return u


def _node(expr: str, obs: dict) -> object:
    """Evaluate `expr` with P = bot-parity.js exports and obs = the fixture."""
    script = (
        f"const P = require({json.dumps(str(PARITY_PATH))});"
        "const obs = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
        f"process.stdout.write(JSON.stringify({expr}));"
    )
    out = subprocess.run([NODE, "-e", script], input=json.dumps(obs), capture_output=True, text=True,
                         encoding="utf-8", check=True, timeout=30)
    return json.loads(out.stdout)


needs_node = pytest.mark.skipif(NODE is None, reason="node not installed")


# ------------------------------------------------------------------ acceptance: API prompt keys -> cockpit homes
def test_every_format_observation_key_is_rendered_on_bot() -> None:
    obs = build_observation(_empire_universe(), "P1")
    payload = json.loads(format_observation(obs))
    fields = set(Observation.model_fields)
    code = JS + PARITY
    missing = []
    for key, val in payload.items():
        if key == "self":
            for sub in val:
                if f'data-obs="{sub}"' not in HTML and f'data-obs="self_{sub}"' not in HTML:
                    missing.append(f"self.{sub}")
        elif key == "recent_events":
            # Rendered from /events (same _event_visible_to rule, longer tail), not obs.recent_events.
            if 'data-obs="recent_events"' not in HTML or "/events?since=" not in JS:
                missing.append(key)
        elif key in fields:
            if f'data-obs="{key}"' not in HTML or not re.search(rf"\bobs\.{key}\b", code):
                missing.append(key)
        elif f'data-llm="{key}"' not in HTML:
            missing.append(key)
    assert not missing, f"API prompt keys with no rendered /bot home: {missing}"


# ------------------------------------------------------------------ CP1 planet tape
@needs_node
def test_cp1_planet_row_carries_id_origin_colonists_stockpile_growth() -> None:
    obs = build_observation(_empire_universe(), "P1").model_dump(mode="json")
    p = obs["owned_planets"][0]
    r = _node("P.planetRow(obs.owned_planets[0])", obs)
    text = " | ".join([r["title"], *r["metas"]])
    assert f"id {p['id']}" in text
    assert f"origin {p['origin']}" in text and p["origin"] == "genesis"
    assert f"colonists {p['colonists_total']:,}" in text
    for pool, n in p["colonists"].items():
        assert f"{n:,}" in text, pool
    assert f"Org {p['stockpile']['organics']:,}" in text
    assert f"eats {p['organics_consumption_per_day']:,} Org/day" in text
    assert ("growing" in text) if p["growth_active"] else ("NOT growing" in text)
    assert f"organics last {p['organics_days_left']:,} day(s)" in text


# ------------------------------------------------------------------ CP2 other players
@needs_node
def test_cp2_every_other_player_rendered_and_fog_respected() -> None:
    obs = build_observation(_empire_universe(), "P1").model_dump(mode="json")
    here = obs["sector"]["id"]
    rows = _node("obs.other_players.map((o) => P.otherPlayerRow(o, obs.sector.id))", obs)
    by_id = {o["id"]: " | ".join([r["title"], *r["metas"]]) for o, r in zip(obs["other_players"], rows, strict=True)}
    assert set(by_id) == {"P2", "P3", "P4"}
    others = {o["id"]: o for o in obs["other_players"]}
    mate = others["P2"]
    assert "Corpmate Mate (P2)" in by_id["P2"]
    assert f"{mate['credits']:,} cr" in by_id["P2"] and f"alignment {mate['alignment']}" in by_id["P2"]
    assert f"sector {here} (here)" in by_id["P3"] and others["P3"]["ship_class"] in by_id["P3"]
    # Engine fog: a non-mate elsewhere has no sector/hull, and the row says so.
    assert "sector_id" not in others["P4"] and "ship_class" not in others["P4"]
    assert "location hidden" in by_id["P4"]
    assert _node("P.occupantLabel('P3', obs.other_players)", obs).startswith("P3 Neighbour")


# ------------------------------------------------------------------ CP3 operator dialogue + directive meta
@needs_node
def test_cp3_dialogue_is_the_same_tail_api_seats_get() -> None:
    o = build_observation(_empire_universe(), "P1")
    api_tail = json.loads(format_observation(o))["operator_dialogue"]
    lines = _node("P.dialogueLines(obs)", o.model_dump(mode="json"))
    assert [ln["text"] for ln in lines] == [m["message"] for m in api_tail] == [f"line {i}" for i in range(2, 10)]
    assert {ln["role"] for ln in lines} == {"Operator", "AI"}
    assert _node("P.directiveMeta(obs)", o.model_dump(mode="json")) == " (set day 1.7)"


# ------------------------------------------------------------------ CP4 prompt twin
@needs_node
def test_cp4_stage_hint_comes_from_the_api_twin() -> None:
    o = build_observation(_empire_universe(), "P1")
    sh = stage_hint(o)
    twin = format_observation(o)
    got = _node("[P.stageText(P.parseTwin(obs.twin).stage_hint), P.stageDetail(P.parseTwin(obs.twin).stage_hint)]",
                {"twin": twin})
    assert got[0] == f"{sh['stage']} {sh['label']}"
    assert sh["reason"] in got[1]
    assert _node("P.parseTwin('not json')", {}) is None


# ------------------------------------------------------------------ CP5 thought toggle
@needs_node
def test_cp5_thoughts_hidden_by_default_and_only_own() -> None:
    evs = {"mine": {"kind": "agent_thought", "actor_id": "P1"}, "theirs": {"kind": "agent_thought", "actor_id": "P2"},
           "usage": {"kind": "llm_usage", "actor_id": "P1"}, "warp": {"kind": "warp", "actor_id": "P2"}}
    got = _node(
        "Object.fromEntries(Object.entries(obs).map(([k, e]) => [k, ["
        "P.eventShown(e, {seat: 'P1'}), P.eventShown(e, {seat: 'P1', thoughts: true}),"
        "P.eventShown(e, {seat: 'P1', thoughts: true, usage: true})]]))", evs)
    assert got["mine"] == [False, True, True]
    assert got["theirs"] == [False, False, False]
    assert got["usage"] == [False, False, True]
    assert got["warp"] == [True, True, True]


# ------------------------------------------------------------------ UI contract
def test_bot_js_wiring_for_g1() -> None:
    polls = re.findall(r"/observation\?[^`]*", JS)
    assert len(polls) == 2 and all("format=both" in p for p in polls), polls
    assert 'api("/rules")' in JS and "rulesLoaded" in JS
    assert "is_corpmate)" not in JS.replace("!!a.is_corpmate)", "").replace("!!b.is_corpmate)", ""), "no corpmate-only filter"
    assert "window.TW2KParity" in JS and "P.planetRow" in JS and "P.otherPlayerRow" in JS and "P.dialogueLines" in JS
    assert "P.eventShown" in JS and "data-toggle" in JS
    for tid in ("stage-hint", "operator-dialogue", "operator-directive-updated", "other-players", "llm-twin",
                "llm-twin-drawer", "rules-drawer", "rules-prompt", "filter-thoughts", "filter-usage"):
        assert f'data-testid="{tid}"' in HTML, tid
    assert HTML.index("/static/bot-parity.js") < HTML.index("/static/bot.js")
    # No client-side rule constants, no spectator reads.
    for forbidden in ("TURN_COST", "COMMODITY_BASE_PRICE", "SHIP_SPECS", "CITADEL_TIER_COST", "/state"):
        assert forbidden not in PARITY, forbidden
    assert "fetch(\"/state" not in JS and "'/state'" not in JS
    # Mojibake guard (the old files shipped double-encoded UTF-8).
    for text in (HTML, JS, PARITY):
        assert "\u00e2\u20ac" not in text and "\u00c2\u00b7" not in text


# ------------------------------------------------------------------ live harness: twin, rules, own thoughts only
def test_harness_serves_twin_rules_and_only_own_thoughts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5555)), base_url="http://g1.test")
    auth = {"authorization": f"Bearer {TOK2}"}

    async def _until(pred, tries=400, dt=0.02):
        for _ in range(tries):
            if await pred():
                return True
            await asyncio.sleep(dt)
        return await pred()

    async def _go() -> None:
        page = (await client.get("/bot")).text
        assert "/static/bot-parity.js?v=" in page
        assert (await client.get("/static/bot-parity.js")).status_code == 200
        spec = MatchSpec(
            config=GameConfig(seed=9, universe_size=60, max_days=2, turns_per_day=12, starting_credits=25_000,
                              enable_ferrengi=False, enable_planets=False, action_delay_s=0.0),
            agents=[
                AgentSpec(player_id="P1", name="HBot", kind="heuristic"),
                AgentSpec(player_id="P2", name="Seat", kind="external", external_token=TOK2),
            ],
            action_delay_s=0.0,
            external_timeout_s=30.0,
        )
        await runner.start(spec)

        async def my_turn():
            r = await client.get("/harness/v1/P2/status", headers=auth)
            return r.status_code == 200 and r.json().get("awaiting_input")
        assert await _until(my_turn)

        r = await client.get("/harness/v1/P2/observation", params={"wait_s": 0, "peek": 1, "format": "both"}, headers=auth)
        body = r.json()
        assert body["observation"] is not None
        twin = json.loads(body["llm_user_message"])
        assert twin["stage_hint"]["stage"] and twin["self"]["id"] == "P2"

        rules = (await client.get("/harness/v1/rules", headers=auth)).json()
        assert rules["system_prompt"] and "warp" in rules["verbs"]

        post = await client.post("/harness/v1/P2/action", headers=auth, json={
            "turn_seq": body["turn_seq"], "action": {"kind": "scan", "args": {}, "thought": "g1 own thought marker"}})
        assert post.status_code == 200, post.text

        async def saw_own_thought():
            evs = (await client.get("/harness/v1/P2/events", params={"since": 0, "limit": 500}, headers=auth)).json()["events"]
            return any(e["kind"] == "agent_thought" and "g1 own thought marker" in (e.get("summary") or "") for e in evs)
        assert await _until(saw_own_thought)
        evs = (await client.get("/harness/v1/P2/events", params={"since": 0, "limit": 500}, headers=auth)).json()["events"]
        thoughts = [e for e in evs if e["kind"] in ("agent_thought", "llm_usage")]
        assert thoughts and all(e.get("actor_id") == "P2" for e in thoughts), "another seat's thoughts leaked"
        await runner.stop()
        await client.aclose()

    asyncio.run(_go())
