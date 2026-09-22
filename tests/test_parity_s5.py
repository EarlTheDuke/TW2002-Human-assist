"""Parity S5 - known-space map: fog-safe coordinates + click-to-plot.

* Observation.known_sectors lists ONLY sectors the player knows (visited /
  scanned / probed / current) with the universe layout coords for those ids;
  unknown sectors never appear, and remembered port codes come from the
  player's own known_ports (never a live peek).
* format_observation (the LLM message) does not ship coordinates.
* The copilot route table walks the player's known_warps, not the true graph.
* /bot draws the map from known_sectors and gates click-to-plot on
  legal_actions.plot_course.
"""

from __future__ import annotations

import json
from pathlib import Path

from tw2k.agents.prompts import format_observation
from tw2k.copilot.dashboards import _bfs_hops
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.models import Player
from tw2k.engine.observation import build_observation
from tw2k.engine.runner import _record_port_intel

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")
JS = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "bot.css").read_text(encoding="utf-8")


def _u():
    u = generate_universe(GameConfig(seed=77, universe_size=120, max_days=3, turns_per_day=30))
    p = Player(id="P1", name="Me", agent_kind="external", sector_id=1)
    u.players["P1"] = p
    u.sectors[1].occupant_ids.append("P1")
    return u, p


def test_known_sectors_is_fog_safe_and_uses_layout_coords() -> None:
    u, p = _u()
    # Player knows: current sector 1 (implicit), scanned 1 (warps known), visited neighbour n1, probed far sector.
    n1 = sorted(u.sectors[1].warps)[0]
    far = max(u.sectors)  # certainly not adjacent to 1 in a 120-sector map... verify below
    assert far not in u.sectors[1].warps
    p.known_sectors.update({1, n1, far})
    p.known_warps[1] = list(u.sectors[1].warps)
    p.known_warps[n1] = list(u.sectors[n1].warps)
    # Remember a port only for n1 (if it has one) via the real intel path.
    if u.sectors[n1].port is not None:
        _record_port_intel(p, n1, u.sectors[n1].port, universe=u)

    obs = build_observation(u, "P1")
    ids = [n["id"] for n in obs.known_sectors]
    assert ids == sorted(set(ids))
    assert set(ids) == {1, n1, far}, ids
    # Nothing else leaks - in particular no neighbour-of-neighbour and none of the other ~117 sectors.
    assert not (set(ids) - {1, n1, far})
    by_id = {n["id"]: n for n in obs.known_sectors}
    for sid in ids:
        assert by_id[sid]["x"] == round(u.sectors[sid].x, 4) and by_id[sid]["y"] == round(u.sectors[sid].y, 4)
    # Port code is the REMEMBERED one; the far probed-but-unscouted sector shows none even if it has a live port.
    assert by_id[far]["port"] is None
    if u.sectors[n1].port is not None:
        assert by_id[n1]["port"] == u.sectors[n1].port.code
    # Current sector shows its live code (you can see it).
    assert by_id[1]["port"] == (u.sectors[1].port.code if u.sectors[1].port else None)
    assert by_id[1]["is_fedspace"] is True and by_id[1]["warps_known"] is True and by_id[far]["warps_known"] is False

    # LLM message: no coordinates shipped (known_warps is their map).
    msg = json.loads(format_observation(obs))
    assert "known_sectors" not in msg
    assert "x" not in json.dumps(msg.get("known_warps", {}))


def test_fresh_player_knows_only_where_they_stand() -> None:
    u, p = _u()
    obs = build_observation(u, "P1")
    assert [n["id"] for n in obs.known_sectors] == [1]


def test_route_bfs_uses_player_memory_not_true_graph() -> None:
    u, p = _u()
    src = 1
    dst = sorted(u.sectors[1].warps)[0]
    # True graph has a 1-hop path; the player remembers nothing -> no route.
    assert _bfs_hops({}, src, dst) is None
    assert _bfs_hops({src: [dst]}, src, dst) == 1
    # String keys (as stored on some observations) work too.
    assert _bfs_hops({str(src): [dst]}, src, dst) == 1


def test_bot_map_contract() -> None:
    assert 'data-obs="known_sectors"' in HTML and 'data-testid="known-map-svg"' in HTML
    assert 'data-testid="known-warps"' in HTML and 'data-obs="known_warps"' in HTML  # text twin kept
    assert "map-sector-" in JS and 'openVerb("plot_course", { target: id })' in JS
    assert 'canUse("plot_course")' in JS  # gate is the engine's legality, not a JS rule
    assert "known_sectors" in JS and "stubs" in JS  # unknown neighbours drawn without server coords
    assert "prefers-reduced-motion" in CSS
    # Stub placement is derived from the SOURCE node's screen position only (no server coords for unknowns).
    stub_block = JS[JS.index("// Stubs:"):JS.index("// Edges")]
    assert "pos[Number(src)]" in stub_block and "n.x" not in stub_block and "n.y" not in stub_block
