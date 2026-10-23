"""Playtest 3: the reconnect line floats and waits, and buttons survive polls."""
from __future__ import annotations

from pathlib import Path

import pytest

import tests._cu_host as cu

ROOT = Path(__file__).resolve().parents[1]


def test_the_error_line_is_an_overlay() -> None:
    css = (ROOT / "web" / "redesign.css").read_text(encoding="utf-8")
    assert "#err{position:fixed" in css
    js = (ROOT / "web" / "redesign.js").read_text(encoding="utf-8")
    assert "DROP_SHOW_MS = 3000" in js
    assert "keepIfSame(liveBox, box)" in js and "keepIfSame(liveRow, row)" in js


@pytest.fixture()
def page(tmp_path: Path):
    sync = pytest.importorskip("playwright.sync_api").sync_playwright
    token = "p3-stable-seat-token-p2-00000000001"
    host = cu.CuHost(tmp_path, token)
    host.__enter__()
    assert host.port != 8099 and cu.allowed_test_port(host.port)
    pw = sync().start()
    browser = pw.chromium.launch()
    try:
        pg = browser.new_page(viewport={"width": 1280, "height": 800})
        pg.goto(f"{host.base}/bot?layout=redesign&seat=P2&token={token}")
        pg.wait_for_function("() => document.querySelector('#pSector').textContent !== '-'", timeout=20_000)
        yield pg
    finally:
        browser.close()
        pw.stop()
        host.__exit__(None, None, None)


def test_buttons_are_the_same_nodes_after_idle_polls(page) -> None:
    page.evaluate(
        """() => {
          window.__p3 = Array.from(document.querySelectorAll('#warps button, #here button'));
          window.__p3.forEach(b => { b.__p3mark = 1; });
        }"""
    )
    assert page.evaluate("() => window.__p3.length") > 0
    page.wait_for_timeout(5_000)
    kept = page.evaluate("() => window.__p3.filter(b => b.isConnected && b.__p3mark).length")
    total = page.evaluate("() => window.__p3.length")
    assert kept == total


def test_banner_waits_overlays_and_clears(page) -> None:
    before = page.evaluate("() => JSON.stringify(document.querySelector('#deck').getBoundingClientRect())")
    page.evaluate(
        """() => {
          window.__realFetch = window.fetch;
          window.fetch = () => Promise.reject(new Error('host down'));
          window.__tw2kLink.noteDrop(new Error('host down'));
        }"""
    )
    page.wait_for_timeout(1_000)
    assert page.evaluate("() => { const e = document.querySelector('#err'); return !e.hidden && e.dataset.kind === 'reconnect'; }") is False
    page.wait_for_function(
        "() => { const e = document.querySelector('#err'); return !e.hidden && e.dataset.kind === 'reconnect'; }",
        timeout=8_000,
    )
    assert page.evaluate("() => getComputedStyle(document.querySelector('#err')).position") == "fixed"
    after = page.evaluate("() => JSON.stringify(document.querySelector('#deck').getBoundingClientRect())")
    assert after == before
    page.evaluate("() => { window.fetch = window.__realFetch; }")
    page.wait_for_function(
        "() => { const e = document.querySelector('#err'); return e.hidden || e.dataset.kind !== 'reconnect'; }",
        timeout=8_000,
    )
