"""Warp buttons show the turn cost, and the drawn course is the server path."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests._cu_host import CuHost
from tests._refresh import wait_refreshes

TOK = "nav-e2e-token-p2-0000000000000000"


def test_server_course_turn_cost_and_a_centred_map(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("COCKPIT_LAYOUT", raising=False)
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            page.wait_for_selector("#warps button", timeout=20_000)
            assert re.search(r"\(\d+t\)", page.locator("#warps button").first.inner_text())
            labels_ok = page.evaluate(
                """() => {
                  const texts = [...document.querySelectorAll('#map text')];
                  if (!texts.length || getComputedStyle(texts[0]).pointerEvents !== 'auto') return false;
                  const here = document.querySelector('#map .node.here circle');
                  if (!here || here.getAttribute('cx') !== '0' || here.getAttribute('cy') !== '0') return false;
                  for (let i = 0; i < texts.length; i++) {
                    const a = texts[i].getBoundingClientRect();
                    for (let j = i + 1; j < texts.length; j++) {
                      const b = texts[j].getBoundingClientRect();
                      const dx = (a.x + a.width / 2) - (b.x + b.width / 2);
                      const dy = (a.y + a.height / 2) - (b.y + b.height / 2);
                      if (Math.hypot(dx, dy) < 10) return false;
                    }
                  }
                  return true;
                }"""
            )
            assert labels_ok
            info = page.evaluate(
                """async (token) => {
                  const headers = {"Content-Type": "application/json", "X-TW2K-Seat": "P2", Authorization: "Bearer " + token};
                  const obs = await fetch("/harness/v1/P2/observation?wait_s=0&peek=1&format=both", {headers}).then((r) => r.json());
                  const here = Number(obs.observation.sector.id);
                  const target = here === 1 ? 2 : 1;
                  const posted = await fetch("/harness/v1/P2/action", {method: "POST", headers, body: JSON.stringify({turn_seq: obs.turn_seq, action: {kind: "plot_course", args: {target, execute: false}}})});
                  if (!posted.ok) throw new Error(await posted.text());
                  const events = await fetch("/harness/v1/P2/events?since=0&limit=100&course=1", {headers}).then((r) => r.json());
                  const plot = [...(events.events || [])].reverse().find((ev) => ev.kind === "autopilot" && ev.facts && ev.facts.path);
                  const warp = (obs.observation.legal_actions || []).find((a) => a.kind === "warp") || {};
                  return {path: plot.facts.path, cost: warp.turn_cost || 0, planets: (obs.observation.sector.planets || []).map((p) => p.id)};
                }""",
                TOK,
            )
            route = ",".join(str(n) for n in info["path"])
            page.wait_for_function(
                "(route) => document.querySelector('#map').getAttribute('data-route') === route",
                arg=route,
                timeout=20_000,
            )
            hops = len(info["path"])
            turns = hops * int(info["cost"])
            assert f"{hops} hops, {turns} turns" in page.locator("#warps .eng").inner_text()
            wait_refreshes(page, 1)
            assert page.locator("#map").get_attribute("data-route") == route
            if info["planets"]:
                page.evaluate(
                    """async (token) => {
                      const headers = {"Content-Type": "application/json", "X-TW2K-Seat": "P2", Authorization: "Bearer " + token};
                      const obs = await fetch("/harness/v1/P2/observation?wait_s=0&peek=1&format=both", {headers}).then((r) => r.json());
                      const planet = obs.observation.sector.planets[0].id;
                      const posted = await fetch("/harness/v1/P2/action", {method: "POST", headers, body: JSON.stringify({turn_seq: obs.turn_seq, action: {kind: "land_planet", args: {planet_id: planet}}})});
                      if (!posted.ok) throw new Error(await posted.text());
                    }""",
                    TOK,
                )
                page.wait_for_function(
                    "() => (document.querySelector('#sectorText').textContent || '').includes('LANDED')",
                    timeout=20_000,
                )
                page.locator("#warps .eng").click()
                page.wait_for_function(
                    "() => (document.querySelector('#lastResult').textContent || '').includes('Lift off first')",
                    timeout=10_000,
                )
                assert page.locator("#map").get_attribute("data-route") == route
        finally:
            browser.close()
