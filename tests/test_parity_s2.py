"""Parity S2 - read-only cockpit tapes on /bot (peek-powered).

The UI is plain JS we cannot execute under pytest, so these tests pin the
contract the JS relies on:

* every Observation top-level key has a `data-obs` home in bot.html,
* the S2 panels and CU affordances exist with stable data-testid hooks,
* bot.js uses peek + /events (no hard-coded game truth, no 2.5 s poller),
* the /bot route still serves the page and assets through the app (gate off),
* and the harness responses the JS consumes carry the fields the panels read.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import httpx

from tw2k.engine import GameConfig
from tw2k.engine.observation import Observation
from tw2k.server.app import create_app
from tw2k.server.runner import AgentSpec, MatchSpec

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")
JS = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "bot.css").read_text(encoding="utf-8")
TOK2 = "s2-token-p2-00000000000000"


def test_every_observation_key_has_a_data_obs_home() -> None:
    keys = list(Observation.model_fields)
    missing = [k for k in keys if f'data-obs="{k}"' not in HTML]
    assert not missing, f"Observation keys without a data-obs home in bot.html: {missing}"
    # No data-obs points at a key that does not exist (typo guard).
    used = set(re.findall(r'data-obs="([a-z_.]+)"', HTML))
    for u in used:
        top = u.split(".")[0]
        assert top in keys, f"data-obs={u!r} is not an Observation field"


def test_s2_panels_and_cu_hooks_exist() -> None:
    for tid in (
        "scoreboard", "col-where", "col-act", "col-know", "here", "sector", "port", "port-tape", "adjacent",
        "known-warps", "ship", "cargo", "known-ports", "trade", "rivals", "planets", "comms", "intel",
        "last-result", "last-result-json", "recent-failures", "action-hint", "raw-obs-drawer",
        "events", "event-log", "filter-all", "filter-trade", "filter-move", "filter-combat", "filter-comms",
        "connect", "refresh", "action-scan", "action-wait", "action-sell", "action-buy", "turn-banner", "whose-turn",
    ):
        assert f'data-testid="{tid}"' in HTML, tid
    # English-first result with the JSON in a drawer, aria-live for screen readers / CU.
    assert 'id="lastResult"' in HTML and 'aria-live="polite"' in HTML
    assert "<details" in HTML and 'id="lastResultJson"' in HTML
    # Port tape shows side + price + stock per commodity (done-when #2).
    assert "<th>Price</th>" in HTML and "<th>Stock</th>" in HTML
    # Known ports table has per-commodity price columns (which known port buys it).
    assert "<th>Fuel</th>" in HTML and "<th>Org</th>" in HTML and "<th>Equip</th>" in HTML


def test_bot_js_is_peek_and_events_driven() -> None:
    assert "peek=1" in JS, "cockpit must peek between turns"
    assert "/events?since=" in JS, "cockpit must read the fogged event stream"
    assert "setInterval(refresh" not in JS, "no blind status poller"
    assert "watchLoop" in JS
    # Renders straight from Observation keys the server owns.
    for key in ("known_ports", "known_warps", "trade_summary", "trade_log", "recent_failures", "cargo_cost_avg",
                "cargo_value_at_cost", "fighter_cap", "orphaned_planets", "limpets_owned", "probe_log", "alliances"):
        assert key in JS, key
    # No client-side rule constants: prices/turn costs come only from the Observation.
    for forbidden in ("TURN_COST", "COMMODITY_BASE_PRICE", "SHIP_SPECS", "CITADEL_TIER_COST"):
        assert forbidden not in JS, forbidden
    # Stable warp DOM (Phase D fix) still in place.
    assert "data-warp-key" in JS
    # Reduced-motion respected.
    assert "prefers-reduced-motion" in CSS


def test_bot_route_serves_new_markup_and_harness_carries_panel_fields(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    app = create_app(auto_start=False)
    runner = app.state.runner
    runner._saves_root = tmp_path / "saves"
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5555)), base_url="http://s2.test")

    async def _until(pred, tries=300, dt=0.02):
        for _ in range(tries):
            if pred():
                return True
            await asyncio.sleep(dt)
        return pred()

    async def _go() -> None:
        r = await client.get("/bot")
        assert r.status_code == 200 and 'data-testid="col-know"' in r.text and "/static/bot.js?v=" in r.text
        for asset in ("/static/bot.js", "/static/bot.css"):
            assert (await client.get(asset)).status_code == 200

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
        assert await _until(lambda: bool(runner.state.agents) and runner.state.universe is not None)
        # The one call the cockpit makes on Connect: peek observation, wait 0.
        r = await client.get("/harness/v1/P2/observation", params={"wait_s": 0, "peek": 1, "format": "json"},
                             headers={"authorization": f"Bearer {TOK2}"})
        assert r.status_code == 200
        body = r.json()
        assert body["observation"] is not None
        obs = body["observation"]
        # Fields every S2 panel reads must be present (the JS treats them as authoritative).
        for k in ("sector", "adjacent", "ship", "known_ports", "known_warps", "trade_summary", "trade_log",
                  "recent_failures", "rivals", "other_players", "owned_planets", "orphaned_planets", "inbox",
                  "alliances", "limpets_owned", "probe_log", "action_hint", "goals", "scratchpad",
                  "net_worth", "rank", "alignment_label", "deaths", "max_deaths"):
            assert k in obs, k
        assert "current_turn" in body and "server_time" in body
        # Port tape needs stock rows with side/price when a port exists.
        port = obs["sector"].get("port")
        if port and port.get("stock"):
            row = next(iter(port["stock"].values()))
            assert {"current", "max", "price", "side"} <= set(row)
        r = await client.get("/harness/v1/P2/events", params={"since": 0}, headers={"authorization": f"Bearer {TOK2}"})
        assert r.status_code == 200 and "events" in r.json()
        await runner.stop()
        await client.aclose()

    asyncio.run(_go())
