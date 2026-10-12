"""cockpit-scene-image-v1. A still stays in the 16:9 window, from the fogged view only."""
from __future__ import annotations

from tests._cu_host import CuHost

TOK = "scene-image-v1-token-p2-0000000000"


def test_scene_still_loads_and_visuals_off_hides_it(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        page.wait_for_selector("[data-testid=scene-still]:not([hidden])", timeout=15_000)
        still = page.get_by_test_id("scene-still")
        src = still.get_attribute("src") or ""
        assert "/static/media/stills/" in src and src.endswith(".webp"), src
        assert still.get_attribute("alt")
        box = page.evaluate(
            """() => {
              const s = document.querySelector('#vpScreen').getBoundingClientRect();
              const i = document.querySelector('#sceneStill').getBoundingClientRect();
              return { sw: s.width, sh: s.height, iw: i.width, ih: i.height };
            }"""
        )
        assert abs(box["sw"] / box["sh"] - 16 / 9) < 0.04, box
        assert abs(box["iw"] - box["sw"]) < 2 and abs(box["ih"] - box["sh"]) < 2, box
        page.close()

        off = browser.new_page(viewport={"width": 1440, "height": 900})
        off.goto(f"{host.base}/bot?seat=P2&token={TOK}&visuals=0")
        off.wait_for_selector("#turnBanner.turn", timeout=20_000)
        off.wait_for_timeout(500)
        assert off.get_by_test_id("scene-still").is_hidden()
        off.close()
