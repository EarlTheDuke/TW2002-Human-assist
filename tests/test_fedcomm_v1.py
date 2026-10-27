"""The Federation lane note is sent only when that switch is on.

Off, a swept stack still gets the old Extern line and no inbox note.
On, the owner is told not to deploy fighters in the lanes, with the sector.

Plants:
  pb1 — the live note is skipped, so the inbox stays empty.
  pb2 — the switch off still sends the note.
"""

from __future__ import annotations

import pytest

import tw2k.engine.constants as K
from tw2k.engine.class0 import extern_sweep
from tw2k.engine.models import FighterDeployment, FighterMode, GameConfig, Player, Ship, ShipClass
from tw2k.engine.universe import generate_universe

pytestmark = pytest.mark.legacy_profile


def _world():
    u = generate_universe(GameConfig(seed=4501, universe_size=80, enable_ferrengi=False, enable_planets=True))
    u.players["A"] = Player(
        id="A", name="Alpha",
        ship=Ship(holds=20, fighters=10, ship_class=ShipClass.MERCHANT_CRUISER),
        sector_id=1, credits=1000,
    )
    lane = next(s for s in u.msl_sectors if s not in (1,) and s not in K.FEDSPACE_SECTORS)
    u.sectors[lane].fighters = FighterDeployment(owner_id="A", count=12, mode=FighterMode.DEFENSIVE)
    return u, lane


def test_switch_stays_off() -> None:
    assert K.FEDCOMM_MODE == "legacy"
    assert K.fedcomm_live() is False


def test_off_keeps_the_old_note() -> None:
    u, lane = _world()
    extern_sweep(u)
    assert u.sectors[lane].fighters is None
    assert u.players["A"].inbox == []


def test_on_sends_the_lane_note() -> None:
    _prior_fedcomm_mode = K.FEDCOMM_MODE
    try:
        u, lane = _world()
        try:
            K.FEDCOMM_MODE = "live"
            extern_sweep(u)
            note = u.players["A"].inbox[-1]
            assert note["from"] == "FedComm"
            assert note["message"] == "Don't deploy fighters in the MSL's."
            assert note["sector_id"] == lane
        finally:
            K.FEDCOMM_MODE = "legacy"
    finally:
        K.FEDCOMM_MODE = _prior_fedcomm_mode
