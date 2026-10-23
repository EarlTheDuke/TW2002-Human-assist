"""Playtest 3 leftovers (a): v3.11 autopilot asks at each port, and <E> Express flies non-stop.

TWINSTR AUTOPILOT MENU (docs/reference/tw2002/stardock_manuals_and_text_docs/Someguy_TWINSTR.txt,
"<E> Express Non-stop ... without pausing to ask if you want to stop in the sectors with planets
or ports"). The engine side (no stop_at_ports flies through) is pinned in
tests/test_v311_live_rulings_v2.py::test_express_stops_at_a_port_only_when_the_cockpit_asks.
"""
from __future__ import annotations

from pathlib import Path

from tw2k.public import manual

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")


def _fn(name: str) -> str:
    start = JS.index(f"function {name}(")
    return JS[start:JS.index("\n  }\n", start)]


def test_engage_express_drops_the_port_stop() -> None:
    body = _fn("engage")
    assert body.startswith("function engage(express)")
    assert "if (!express && (((LA(\"plot_course\")" in body
    assert "args.stop_at_ports = true" in body


def test_course_row_and_port_stop_offer_express() -> None:
    assert JS.count("engage(true)") == 3
    assert 'addEventListener("click", engage)' not in JS, "a click event must not read as express"
    assert "Engage (stops at ports)" in JS and "Express non-stop</button>" in JS
    assert 'ex.textContent = "EXPRESS"' in JS
    assert 'ex.textContent = "Express"' in JS
    stop = JS[JS.index('bar.id = "portStop"'):]
    stop = stop[:stop.index('insertAdjacentElement("afterend", bar)')]
    assert stop.index("bar.appendChild(go)") < stop.index("bar.appendChild(ex)") < stop.index("bar.appendChild(stay)")


def test_manual_names_express() -> None:
    assert "choose Express to fly non-stop" in manual._SWITCH_PLAIN["AUTOPILOT_PORT_STOP_MODE"]
