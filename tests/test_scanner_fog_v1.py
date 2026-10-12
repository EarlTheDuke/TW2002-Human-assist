"""Planet owner and fighters stay hidden until a scan or a landing.

Off, the sector list still names the owner. On, owner, fighters, and
shields are hidden. A planet scanner reads owner and fighters only when
the planet has no shields. Landing reads all three.

Plants:
  pb1 — fog on, a stranger still sees the owner's name.
  pb2 — landing still hides the shields.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine.models import Planet, PlanetClass, Player, Ship
from tw2k.engine.observation import _planet_brief


def _pair(shields: int) -> tuple[Planet, Player]:
    planet = Planet(id=7, sector_id=20, name="Bare", class_id=PlanetClass.M,
                    owner_id="B", fighters=40, shields=shields)
    viewer = Player(id="A", name="Alpha", ship=Ship(), sector_id=20, credits=1_000)
    return planet, viewer


def test_switch_stays_off() -> None:
    assert K.SCANNER_FOG_MODE == "legacy"
    assert K.scanner_fog_live() is False


def test_off_still_names_the_owner() -> None:
    planet, viewer = _pair(0)
    brief = _planet_brief(planet, viewer)
    assert brief["owner_id"] == "B"
    assert "fighters" not in brief
    assert "shields" not in brief


def test_on_hides_until_scan_or_landing() -> None:
    planet, viewer = _pair(0)
    shielded, _viewer = _pair(25)
    K.SCANNER_FOG_MODE = "live"
    K.PLANET_SCANNER_MODE = "live"
    try:
        dark = _planet_brief(planet, viewer)
        assert "owner_id" not in dark
        assert "fighters" not in dark
        assert "shields" not in dark
        viewer.ship.planet_scanner = True
        seen = _planet_brief(planet, viewer)
        assert seen["owner_id"] == "B"
        assert seen["fighters"] == 40
        assert "shields" not in seen
        blocked = _planet_brief(shielded, viewer)
        assert "owner_id" not in blocked
        assert "fighters" not in blocked
        assert "shields" not in blocked
        viewer.ship.planet_scanner = False
        viewer.planet_landed = shielded.id
        landed = _planet_brief(shielded, viewer)
        assert landed["owner_id"] == "B"
        assert landed["fighters"] == 40
        assert landed["shields"] == 25
    finally:
        K.SCANNER_FOG_MODE = "legacy"
        K.PLANET_SCANNER_MODE = "legacy"
