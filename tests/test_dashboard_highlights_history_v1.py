"""Highlights come from the whole match, and the feed can load older rows."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "dashboard-highlights-history-v1"
REF = Path(r"C:\Users\sugar\tw2002_reference\dashboard_test\qc\dashboard-highlights-history-v1")


def test_highlights_use_full_history_and_feed_loads_older(browser, tmp_path, monkeypatch) -> None:
    from tests._cu_host import CuHost

    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, "dash-highlights-v1-token-p2-00000") as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/")
        page.wait_for_function(
            "() => document.getElementById('highlightsReel').dataset.source === 'history'",
            timeout=20_000,
        )
        reel = page.locator("#highlightsList").inner_text()
        assert "MATCH START" in reel
        assert "PLANET TAX" not in reel
        assert "DIVIDEND" not in reel
        page.wait_for_function(
            "() => document.querySelectorAll('#eventFeed li').length > 5",
            timeout=20_000,
        )
        page.evaluate("() => window.tw2kDropEarlyEvents()")
        page.wait_for_selector("[data-testid=feed-load-older]:not([hidden])", timeout=5_000)
        before_seqs = page.eval_on_selector_all(
            "#eventFeed li",
            "els => els.map((el) => Number(el.dataset.seq)).filter((n) => n)",
        )
        before = page.locator("#eventFeed li").count()
        page.get_by_test_id("feed-load-older").click()
        page.wait_for_function(
            "(n) => document.querySelectorAll('#eventFeed li').length > n",
            arg=before,
            timeout=10_000,
        )
        seqs_on_page = page.eval_on_selector_all(
            "#eventFeed li",
            "els => els.map((el) => Number(el.dataset.seq)).filter((n) => n)",
        )
        assert before_seqs
        assert min(seqs_on_page) < min(before_seqs)
        older = page.request.get(f"{host.base}/events?before=30&limit=8").json()
        seqs = [row["seq"] for row in older["events"]]
        assert seqs
        assert all(seq < 30 for seq in seqs)
        assert seqs == sorted(seqs)
        highlights = page.request.get(f"{host.base}/highlights?limit=1000").json()["highlights"]
        assert any(row["kind"] == "game_start" for row in highlights)
        for width, height, name in ((1920, 1080, "1920"), (1440, 900, "1440"), (390, 844, "390")):
            page.set_viewport_size({"width": width, "height": height})
            for folder in (SHOTS, REF):
                folder.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(folder / f"spectate-{name}.png"), full_page=(width < 720))
        page.close()
