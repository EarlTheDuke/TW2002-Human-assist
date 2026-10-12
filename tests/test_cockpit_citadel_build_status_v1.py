"""An in-progress citadel names the level being built and the day it finishes.

The finished level stays at L0 until that day. The planet row and the stage
line must not call that an L0 build.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from tests._cu_host import CuHost

TOK = "citadel-build-v1-token-p2-000000000000"
SHOT = Path(__file__).resolve().parents[1] / "docs" / "playtests" / "cockpit-citadel-build" / "citadel-building.png"
COPY = Path(r"C:\Users\sugar\tw2002_reference\cockpit_assets\screens\citadel-building.png")


def _paint_build(route) -> None:
    response = route.fetch()
    try:
        data = response.json()
    except Exception:
        route.fulfill(response=response)
        return
    obs = data.get("observation")
    if isinstance(obs, dict):
        obs["owned_planets"] = [{
            "id": 32,
            "name": "Eden",
            "class": "M",
            "sector_id": 12,
            "origin": "genesis",
            "citadel_level": 0,
            "citadel_target": 1,
            "citadel_complete_day": 8,
            "colonists": {"fuel_ore": 1000},
            "colonists_total": 1000,
            "stockpile": {},
            "fighters": 0,
            "shields": 0,
            "growth_active": True,
        }]
    route.fulfill(response=response, json=data)


def test_l1_build_shows_level_and_completion_day(browser, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TW2K_SPECTATOR_TOKEN", raising=False)
    with CuHost(tmp_path, TOK) as host:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.route("**/observation**", _paint_build)
        page.goto(f"{host.base}/bot?seat=P2&token={TOK}")
        page.wait_for_selector("#turnBanner.turn", timeout=20_000)
        words = page.evaluate(
            """() => {
              const P = window.TW2KParity;
              const building = {citadel_level: 0, citadel_target: 1, citadel_complete_day: 8};
              const idle = {citadel_level: 0, citadel_target: 0};
              const higher = {citadel_level: 1, citadel_target: 2, citadel_complete_day: 4};
              return {
                row: P.planetRow(building).metas.find((m) => m.startsWith("citadel")),
                idle: P.citadelStatus(idle),
                higher: P.citadelStatus(higher),
                noday: P.citadelStatus({citadel_level: 0, citadel_target: 1}),
                quiet: P.stageBuildDetail("You own 1 planet(s); citadel L0 in progress", [idle]),
                live: P.stageBuildDetail("You own 1 planet(s); citadel L0 in progress", [building]),
              };
            }"""
        )
        assert words["row"] == "citadel L1 building, done day 8"
        assert words["idle"] == "citadel L0"
        assert words["higher"] == "citadel L2 building, done day 4"
        assert words["noday"] == "citadel L1 building"
        assert words["quiet"] == "You own 1 planet(s); no citadel started"
        assert words["live"] == "You own 1 planet(s); citadel L1 building, done day 8"
        page.locator("[data-testid=mfd-tab-planets]").click()
        row = page.locator("[data-testid=owned-planet-32]")
        row.wait_for(timeout=20_000)
        text = row.inner_text()
        assert "citadel L1 building, done day 8" in text
        assert "citadel L0" not in text
        detail = page.locator("[data-testid=stage-hint-detail]").inner_text()
        assert "citadel L1 building, done day 8" in detail
        assert "citadel L0 in progress" not in detail
        page.locator("[data-testid=stage-hint]").scroll_into_view_if_needed()
        SHOT.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOT))
        COPY.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SHOT, COPY)
        page.close()
