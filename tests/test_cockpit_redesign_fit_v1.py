"""The winning cockpit fits one screen, and the key bar does not cover the panels."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._cu_host import CuHost

TOK = "fit-e2e-token-p2-000000000000000"

INSIDE = """
() => {
  const vh = window.innerHeight;
  const ids = ["viewport", "nav", "ship", "context", "term", "keys"];
  const boxes = {};
  for (const id of ids) {
    const r = document.getElementById(id).getBoundingClientRect();
    boxes[id] = { top: r.top, bottom: r.bottom, height: r.height };
    if (r.height < 24 || r.top < -1 || r.bottom > vh + 2) return { ok: false, id, boxes };
  }
  const keys = document.getElementById("keys").getBoundingClientRect();
  const here = document.getElementById("context").getBoundingClientRect();
  const overlap = !(keys.bottom <= here.top || keys.top >= here.bottom);
  return { ok: !overlap, boxes };
}
"""


def test_panels_fit_and_the_phone_bar_stays_small(tmp_path: Path, monkeypatch) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for width, height in ((1920, 1080), (1440, 900), (1366, 768)):
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
                page.wait_for_selector("[data-testid=ship-board]", timeout=20_000)
                page.wait_for_timeout(400)
                fit = page.evaluate(INSIDE)
                assert fit["ok"], (width, height, fit)
                page.close()
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={TOK}")
            page.wait_for_selector(".title-frame", timeout=20_000)
            share = page.evaluate(
                """() => {
                  const h = document.getElementById('cmdline').getBoundingClientRect().height;
                  const k = document.getElementById('keys').getBoundingClientRect().height;
                  return (h + k) / window.innerHeight;
                }"""
            )
            assert share < 0.25, share
            page.close()
        finally:
            browser.close()
