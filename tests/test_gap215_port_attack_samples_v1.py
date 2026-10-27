"""GAP 2.15. Ven GameA port samples, behind PORT_ATTACK_MODE.

The class maps are measured fallbacks. Classes 2, 3, and 5 carry the
2026-10-25 lasers. A captured port name uses that port's own row, and a
variance row with no laser does not borrow another port's barrage.
Engine class 8 stays off the class maps.
"""
import pytest

import tw2k.engine.constants as K
from tests.test_phase_abc import _first_non_fed_sector, _make_universe
from tests.test_ship_combat_core_v1 import _act, _park
from tw2k.engine.actions import ActionKind
from tw2k.engine.models import EventKind, Port, PortClass, ShipClass

pytestmark = pytest.mark.legacy_profile


def _cruiser(seed: int, class_id: PortClass):
    u, (pilot, _other, _c) = _make_universe(seed=seed)
    sid = _first_non_fed_sector(u)
    _park(u, pilot, sid)
    sector = u.sectors[sid]
    if sector.port is None:
        sector.port = Port(class_id=class_id)
    sector.port.class_id = class_id
    sector.port.name = "generated-port"
    pilot.ship.fighters = 2500
    pilot.ship.shields = 400
    pilot.alignment = 0
    pilot.experience = 0
    pilot.deaths = 0
    return u, pilot


def _port_combat(u):
    return next(e for e in reversed(u.events) if e.kind is EventKind.COMBAT and e.payload.get("vs") == "port")


def test_samples_are_labeled() -> None:
    by_name = {row["name"]: row for row in K.PORT_ATTACK_GAMEA_SAMPLES}
    assert by_name["H'Catha"]["source"] == "Ven GameA 2026-10-24"
    assert by_name["Leipzig"]["source"] == "Ven GameA 2026-10-24"
    assert by_name["Mastro"]["status"] == "VARIANCE" and by_name["Mastro"]["laser"] is None
    assert by_name["Anaxagoras Primus"]["laser"] is None
    assert by_name["Mirador Outpost"]["laser"] is None
    for name in ("New Cesium", "Peleus", "Aesculapius", "Vergil Minor"):
        assert by_name[name]["source"] == "Ven GameA 2026-10-25"
        assert by_name[name]["status"] == "CONFIRMED"
    vergil = by_name["Vergil Minor"]
    assert vergil["class"] == 8 and vergil["def"] == 99 and vergil["laser"] == 954
    fed = next(row for row in K.PORT_ATTACK_GAMEA_SAMPLES if row["status"] == "FED_PRIOR")
    assert fed["def"] == 91 and fed["laser"] == 701 and fed["source"] == "REPORT.md"
    assert K.PORT_ATTACK_ALL_CLASSES_MODE == "legacy"
    assert K.PORT_LASER_BARRAGE[2] == 482
    assert K.PORT_LASER_BARRAGE[3] == 873
    assert K.PORT_LASER_BARRAGE[5] == 391
    assert 8 not in K.PORT_DEFENSE_RATING
    assert 8 not in K.PORT_LASER_BARRAGE


def test_class_fallbacks_are_primary_samples_and_a_generated_name_does_not_inherit_a_sector() -> None:
    assert K.port_attack_sample(1, None, "generated-port") == (46, 337)
    assert K.port_attack_sample(2, None, "generated-port") == (55, 482)
    assert K.port_attack_sample(3, None, "generated-port") == (86, 873)
    assert K.port_attack_sample(4, None, "generated-port") == (110, 1419)
    assert K.port_attack_sample(5, None, "generated-port") == (59, 391)
    assert K.port_attack_sample(6, None, "generated-port") == (98, 598)
    assert K.port_attack_sample(7, None, "generated-port") == (98, 1121)
    # Sector 913 is Anaxagoras Primus in the capture. A named generated port
    # there keeps the class fallback. An unnamed port may use the sector id.
    assert K.port_attack_sample(3, 913, "Terra-913") == (86, 873)
    assert K.port_attack_sample(3, 913, "") == (60, None)
    assert K.port_attack_sample(3, 436, "Peleus") == (86, 873)
    assert K.port_attack_sample(3, 100, "Anaxagoras Primus") == (60, None)
    assert K.port_attack_sample(2, 173, "Mastro") == (71, None)
    assert K.port_attack_sample(5, 121, "Mirador Outpost") == (44, None)
    assert K.port_attack_sample(1, 708, "Leipzig") == (49, None)
    assert K.port_attack_sample(8, 119, "Vergil Minor") == (None, None)
    assert K.port_attack_sample(8, 119, "") == (None, None)


@pytest.mark.parametrize(
    ("class_id", "rating", "barrage", "shields", "dies"),
    [
        (PortClass.CLASS_1_BSS, 46, 337, 400, False),
        (PortClass.CLASS_1_BSS, 46, 337, 336, True),
        (PortClass.CLASS_2_BSB, 55, 482, 400, True),
        (PortClass.CLASS_3_SBB, 86, 873, 400, True),
        (PortClass.CLASS_4_SSB, 110, 1419, 400, True),
        (PortClass.CLASS_5_SBS, 59, 391, 400, False),
        (PortClass.CLASS_6_BBS, 98, 598, 400, True),
        (PortClass.CLASS_7_BBB, 98, 1121, 400, True),
    ],
)
def test_confirmed_pairs_fire_when_the_attack_flag_is_on(
    monkeypatch, class_id, rating, barrage, shields, dies,
) -> None:
    u, pilot = _cruiser(21501 + int(class_id) + shields, class_id)
    pilot.ship.shields = shields
    before = pilot.ship.fighters
    res = _act(u, pilot.id, ActionKind.ATTACK, target="port", confirm=True, qty=30)
    assert res.ok is True
    assert pilot.alignment == -5
    assert pilot.deaths == (1 if dies else 0)
    if not dies:
        assert pilot.ship.fighters == before - 30
    ev = _port_combat(u)
    assert ev.payload["defensive_rating"] == rating
    assert ev.payload["barrage"] == barrage
    assert ev.payload["outcome"] == ("destroyed" if dies else "survived")


def test_zero_fighters_abort_before_combat(monkeypatch) -> None:
    u, pilot = _cruiser(21541, PortClass.CLASS_4_SSB)
    res = _act(u, pilot.id, ActionKind.ATTACK, target="port", confirm=True, qty=0)
    assert res.ok is False
    assert "1 to" in (res.error or "")
    assert pilot.alignment == 0 and pilot.ship.fighters == 2500 and pilot.deaths == 0
    assert not any(e.kind is EventKind.COMBAT and e.payload.get("vs") == "port" for e in u.events)


def test_named_variance_port_does_not_borrow_a_laser(monkeypatch) -> None:
    u, pilot = _cruiser(21542, PortClass.CLASS_1_BSS)
    u.sectors[pilot.sector_id].port.name = "Leipzig"
    pilot.ship.shields = 100
    res = _act(u, pilot.id, ActionKind.ATTACK, target="port", confirm=True, qty=1)
    assert res.ok is True
    assert pilot.deaths == 0 and pilot.alignment == -5
    ev = _port_combat(u)
    assert ev.payload["defensive_rating"] == 49
    assert ev.payload["barrage"] is None
    assert ev.payload["outcome"] == "survived"


def test_variance_sample_can_blow_the_port_without_borrowing_a_laser(monkeypatch) -> None:
    monkeypatch.setattr(K, "PORT_ATTACK_ALL_CLASSES_MODE", "live")
    u, pilot = _cruiser(21543, PortClass.CLASS_3_SBB)
    u.sectors[pilot.sector_id].port.name = "Anaxagoras Primus"
    pilot.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
    odds = K.combat_hull(pilot.ship.ship_class.value)[0]
    qty = K.port_figs_to_blow(60, odds)
    pilot.ship.fighters = qty
    res = _act(u, pilot.id, ActionKind.ATTACK, target="port", confirm=True, qty=qty)
    assert res.ok is True
    assert pilot.deaths == 0 and pilot.alignment == -55 and pilot.experience == 50
    assert u.sectors[pilot.sector_id].port_destroyed_day == u.day
    ev = _port_combat(u)
    assert ev.payload["defensive_rating"] == 60
    assert ev.payload["barrage"] is None
    assert ev.payload["port_destroyed"] is True


def test_anaxagoras_def_is_not_the_peleus_fallback(monkeypatch) -> None:
    monkeypatch.setattr(K, "PORT_ATTACK_ALL_CLASSES_MODE", "live")
    u, pilot = _cruiser(21544, PortClass.CLASS_3_SBB)
    pilot.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
    u.sectors[pilot.sector_id].port.name = "Anaxagoras Primus"
    odds = K.combat_hull(pilot.ship.ship_class.value)[0]
    short = K.port_figs_to_blow(60, odds) - 1
    pilot.ship.fighters = short
    res = _act(u, pilot.id, ActionKind.ATTACK, target="port", confirm=True, qty=short)
    assert res.ok is True and pilot.deaths == 0 and pilot.experience == 0
    assert u.sectors[pilot.sector_id].port_destroyed_day is None
    ev = _port_combat(u)
    assert ev.payload["defensive_rating"] == 60 and ev.payload["barrage"] is None
    assert ev.payload["port_destroyed"] is False
