"""port-attack-defense-v1. Off, a port is not a target. On, the one measured case applies."""
import tw2k.engine.constants as K
from tests.test_phase_abc import _first_non_fed_sector, _make_universe
from tests.test_ship_combat_core_v1 import _act, _park
from tw2k.engine.actions import ActionKind
from tw2k.engine.models import EventKind, Port, PortClass


def _cruiser(seed: int):
    u, (pilot, _other, _c) = _make_universe(seed=seed)
    sid = _first_non_fed_sector(u)
    _park(u, pilot, sid)
    sector = u.sectors[sid]
    if sector.port is None:
        sector.port = Port(class_id=PortClass.CLASS_6_BBS)
    sector.port.class_id = PortClass.CLASS_6_BBS
    pilot.ship.fighters = 57
    pilot.ship.shields = 400
    pilot.alignment = 0
    return u, pilot


def test_flag_stays_legacy() -> None:
    assert K.PORT_ATTACK_MODE == "legacy"
    assert K.port_attack_live() is False


def test_off_a_port_is_not_a_target() -> None:
    u, pilot = _cruiser(61001)
    res = _act(u, pilot.id, ActionKind.ATTACK, target="port", confirm=True, qty=30)
    assert res.ok is False and "not found" in (res.error or "")
    assert pilot.alignment == 0 and pilot.ship.fighters == 57 and pilot.deaths == 0


def test_on_asks_before_it_fires(monkeypatch) -> None:
    monkeypatch.setattr(K, "PORT_ATTACK_MODE", "live")
    u, pilot = _cruiser(61002)
    res = _act(u, pilot.id, ActionKind.ATTACK, target="port", qty=30)
    assert res.ok is False and res.error == K.PORT_ATTACK_CONFIRM
    assert pilot.alignment == 0 and pilot.ship.fighters == 57 and pilot.deaths == 0


def test_on_class_6_barrage_kills_the_cruiser(monkeypatch) -> None:
    monkeypatch.setattr(K, "PORT_ATTACK_MODE", "live")
    u, pilot = _cruiser(61003)
    res = _act(u, pilot.id, ActionKind.ATTACK, target="port", confirm=True, qty=30)
    assert res.ok is True
    assert pilot.alignment == -5
    assert pilot.deaths == 1
    ev = next(e for e in reversed(u.events) if e.kind is EventKind.COMBAT and e.payload.get("vs") == "port")
    assert ev.payload["defensive_rating"] == 98
    assert ev.payload["barrage"] == 598
    assert ev.payload["sent"] == 30
    assert ev.payload["outcome"] == "destroyed"


def test_on_an_unmeasured_class_does_not_invent_a_kill(monkeypatch) -> None:
    monkeypatch.setattr(K, "PORT_ATTACK_MODE", "live")
    u, pilot = _cruiser(61004)
    u.sectors[pilot.sector_id].port.class_id = PortClass.CLASS_1_BSS
    res = _act(u, pilot.id, ActionKind.ATTACK, target="port", confirm=True, qty=30)
    assert res.ok is True
    assert pilot.alignment == -5 and pilot.ship.fighters == 27 and pilot.deaths == 0
    ev = next(e for e in reversed(u.events) if e.kind is EventKind.COMBAT and e.payload.get("vs") == "port")
    assert ev.payload["barrage"] is None and ev.payload["outcome"] == "survived"
