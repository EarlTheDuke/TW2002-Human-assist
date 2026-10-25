"""Fleet-glass ship view. Our own meshes, readable stats, fighter counts stay real."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tw2k.engine.models import ShipClass

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "plans" / "ship-view-visual-research-v1.md"
JS = ROOT / "web" / "redesign.js"
MESHES = ROOT / "web" / "hull-meshes.js"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_research_recommends_our_own_art() -> None:
    doc = _text(DOC)
    assert "Recommendation" in doc
    assert "B. Our own look." in doc
    assert "Attribution-NonCommercial-NoDerivs" in doc
    assert "No ANSI file" in doc
    assert "scale = ceil(fighters / 200)" in doc
    assert "at most four corner clusters" in doc
    assert "add up to the real total" in doc
    assert "not copied" in doc.lower() or "not a copy" in doc.lower() or "No ANSI file" in doc


def test_panel_states_the_marker_rule_and_keeps_the_legend() -> None:
    js = _text(JS)
    assert "FIGHTER_EXACT_CAP" not in js
    assert "each marker = 100 fighters" in js
    assert "Math.ceil(count / 100)" in js
    assert "data-marker-rule" in js
    assert "ceil(fighters / 200)" not in js
    assert "fleet-glass" in _text(MESHES) or 'look: "fleet-glass-v1"' in _text(MESHES)
    assert "Drew Markham" not in _text(MESHES)
    for name in ("bot.html", "bot.js", "bot-parity.js"):
        body = _text(ROOT / "web" / name)
        assert "hull-meshes" not in body, name
        assert "fighterClusters" not in body, name


def test_every_hull_mesh_is_distinct() -> None:
    classes = [cls.value for cls in ShipClass]
    script = """
import { buildHullFaces, hullMarkup } from "./web/hull-meshes.mjs";
const hulls = __HULLS__;
const seen = new Set();
for (const hull of hulls) {
  const ship = {class: hull, transwarp: {}};
  const def = {accent: "#7aa2ff", detail: "bridge", engines: 2, name: hull};
  const faces = buildHullFaces(ship, def);
  if (faces.length < 12) throw new Error(hull + " faces " + faces.length);
  const svg = hullMarkup(ship, def, 0.82, 0.5, 1, 200, 124);
  const polys = (svg.match(/<polygon/g) || []).length;
  if (polys < 8) throw new Error(hull + " polys " + polys);
  if (seen.has(svg)) throw new Error("duplicate " + hull);
  seen.add(svg);
}
if (seen.size !== hulls.length) throw new Error("unique " + seen.size);
""".replace("__HULLS__", json.dumps(classes))
    subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
