"""The feed hides model usage and says tool calls in plain words."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "playtests" / "dashboard-feed-plain-language-v1"
REF = Path(r"C:\Users\sugar\tw2002_reference\dashboard_test\qc\dashboard-feed-plain-language-v1")


def test_model_usage_stays_off_and_tool_calls_read_as_sentences(browser, tmp_path, monkeypatch) -> None:
    from tests._cu_host import CuHost

    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, "dash-feed-plain-v1-token-p2-000000") as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/")
        page.wait_for_function(
            "() => /^Day [1-9]/.test(document.getElementById('dayLabel').textContent)",
            timeout=20_000,
        )
        box = page.get_by_test_id("feed-model-usage")
        assert box.is_visible()
        assert not box.is_checked()
        label = page.locator("#statusLabel").inner_text()
        assert "thinking" not in label
        assert "kimi" not in label.lower()
        lines = page.evaluate(
            """() => ({
              land: window.tw2kFeedPlain('agent_thought', 'Grok Bot: land_planet {"planet_id":38}'),
              load: window.tw2kFeedPlain('agent_thought', 'load_planet_cargo {"pool":"fuel_ore","amount":12}'),
              plain: window.tw2kFeedPlain('warp', 'Commander warped to sector 12'),
            })"""
        )
        assert lines["land"] == "Grok Bot lands on planet 38"
        assert lines["load"] == "loads 12 fuel ore from the planet"
        assert lines["plain"] == "Commander warped to sector 12"
        for width, height, name in ((1920, 1080, "1920"), (1440, 900, "1440"), (390, 844, "390")):
            page.set_viewport_size({"width": width, "height": height})
            for folder in (SHOTS, REF):
                folder.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(folder / f"spectate-{name}.png"), full_page=(width < 720))
        page.close()
