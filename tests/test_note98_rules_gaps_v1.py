"""NOTE 98. Two new switches, and the three items already on this tip."""
import tw2k.engine.constants as K
from tests.test_phase_abc import _first_non_fed_sector, _make_universe
from tests.test_ship_combat_core_v1 import _act, _park
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import EventKind, GameConfig, Port, PortClass, ShipClass
from tw2k.engine.runner import apply_action
from tw2k.engine.universe import generate_universe


def _cruiser(seed: int, class_id: PortClass = PortClass.CLASS_6_BBS):
    u, (pilot, _other, _c) = _make_universe(seed=seed)
    sid = _first_non_fed_sector(u)
    _park(u, pilot, sid)
    sector = u.sectors[sid]
    if sector.port is None:
        sector.port = Port(class_id=class_id)
    sector.port.class_id = class_id
    pilot.ship.ship_class = ShipClass.INTERDICTOR_CRUISER
    pilot.ship.fighters = 20_000
    pilot.ship.shields = 700
    pilot.alignment = 0
    pilot.experience = 0
    return u, pilot


def test_attack_switch_stays_legacy() -> None:
    assert K.PORT_ATTACK_ALL_CLASSES_MODE == "legacy"
    assert K.port_attack_all_classes() is False
    assert K.port_figs_to_blow(98, 1.0) == 2156
    assert K.port_figs_to_blow(551, 1.5) == 8081


def test_off_a_shielded_class_6_does_not_blow_the_port(monkeypatch) -> None:
    monkeypatch.setattr(K, "PORT_ATTACK_MODE", "live")
    u, pilot = _cruiser(98011)
    res = _act(u, pilot.id, ActionKind.ATTACK, target="port", confirm=True, qty=1796)
    assert res.ok is True
    assert pilot.deaths == 0 and pilot.alignment == -5 and pilot.experience == 0
    assert u.sectors[pilot.sector_id].port is not None
    assert u.sectors[pilot.sector_id].port_destroyed_day is None


def test_on_class_6_blow_pays_and_a_later_dock_kills(monkeypatch) -> None:
    monkeypatch.setattr(K, "PORT_ATTACK_MODE", "live")
    monkeypatch.setattr(K, "PORT_ATTACK_ALL_CLASSES_MODE", "live")
    u, pilot = _cruiser(98012)
    res = _act(u, pilot.id, ActionKind.ATTACK, target="port", confirm=True, qty=1796)
    assert res.ok is True
    assert pilot.deaths == 0
    assert pilot.alignment == -55
    assert pilot.experience == 50
    assert u.sectors[pilot.sector_id].port is not None
    assert u.sectors[pilot.sector_id].port_destroyed_day == u.day
    blown = next(e for e in u.events if e.kind is EventKind.PORT_DESTROYED)
    assert blown.payload["defensive_rating"] == 98
    dock = apply_action(
        u, pilot.id,
        Action(kind=ActionKind.TRADE, args={"commodity": "equipment", "qty": 1, "side": "buy"}),
    )
    assert dock.ok is True and pilot.deaths == 1


def test_on_an_unmeasured_class_still_has_no_barrage(monkeypatch) -> None:
    monkeypatch.setattr(K, "PORT_ATTACK_MODE", "live")
    monkeypatch.setattr(K, "PORT_ATTACK_ALL_CLASSES_MODE", "live")
    u, pilot = _cruiser(98013, PortClass.CLASS_1_BSS)
    res = _act(u, pilot.id, ActionKind.ATTACK, target="port", confirm=True, qty=1796)
    assert res.ok is True
    assert pilot.deaths == 0 and pilot.alignment == -5 and pilot.experience == 0
    assert u.sectors[pilot.sector_id].port_destroyed_day is None
    ev = next(e for e in reversed(u.events) if e.kind is EventKind.COMBAT and e.payload.get("vs") == "port")
    assert ev.payload["barrage"] is None and ev.payload["defensive_rating"] is None
    assert ev.payload["port_destroyed"] is False


def test_on_class_0_does_not_use_the_blow_formula(monkeypatch) -> None:
    monkeypatch.setattr(K, "PORT_ATTACK_MODE", "live")
    monkeypatch.setattr(K, "PORT_ATTACK_ALL_CLASSES_MODE", "live")
    monkeypatch.setitem(K.PORT_DEFENSE_RATING, 0, 98)
    u, pilot = _cruiser(98014, PortClass.FEDERAL)
    res = _act(u, pilot.id, ActionKind.ATTACK, target="port", confirm=True, qty=1796)
    assert res.ok is True and pilot.deaths == 0 and pilot.experience == 0
    assert u.sectors[pilot.sector_id].port_destroyed_day is None


def test_class_fix_stays_off_and_live_map_keeps_class_7_bbb() -> None:
    assert K.PORT_CLASS_NUMBER_FIX_MODE == "legacy"
    assert K.port_class_number_fix() is False
    assert K.port_class_trades(7) == (True, True, True)
    assert PortClass.CLASS_7_BBB.code == "BBB"
    assert int(PortClass.STARDOCK) == 8


def test_class_fix_makes_class_7_sss_and_leaves_stardock_at_8(monkeypatch) -> None:
    monkeypatch.setattr(K, "PORT_CLASS_MAP_MODE", "live")
    monkeypatch.setattr(K, "PORT_CLASS_NUMBER_FIX_MODE", "live")
    assert K.port_class_trades(7) == (False, False, False)
    assert PortClass.CLASS_7_BBB.code == "SSS"
    assert int(PortClass.STARDOCK) == 8
    assert PortClass.STARDOCK.code == "STARDOCK"
    assert K.port_class_trades(8) == (True, True, True)
    assert K.port_class_trades(9) == (False, False, False)
    world = generate_universe(GameConfig(seed=250925, universe_size=80, enable_ferrengi=False, enable_planets=False))
    assert int(world.sectors[K.STARDOCK_SECTOR].port.class_id) == 8


def test_class_fix_alone_does_not_rewrite_legacy_letters(monkeypatch) -> None:
    monkeypatch.setattr(K, "PORT_CLASS_NUMBER_FIX_MODE", "live")
    assert K.port_class_trades(7) == (True, True, True)
    assert PortClass.CLASS_7_BBB.code == "BBB"


def test_genesis_experience_and_alignment_are_already_on() -> None:
    assert K.RANK_MODE == "tw2002"
    assert K.xp_award("deploy_genesis") == 25
    assert K.GENESIS_ALIGNMENT == 10
    u, (pilot, _b, _c) = _make_universe(seed=98021)
    pilot.ship.genesis = 1
    pilot.sector_id = _first_non_fed_sector(u)
    pilot.alignment = 40
    pilot.experience = 0
    res = apply_action(u, pilot.id, Action(kind=ActionKind.DEPLOY_GENESIS))
    assert res.ok, res.error
    assert pilot.experience == 25
    assert pilot.alignment == 50


def test_citadel_path_is_already_the_s1_table(monkeypatch) -> None:
    assert K.CITADEL_FIDELITY_MODE == "tw2002"
    assert K.CITADEL_COST_MODE == "credits"
    assert K.citadel_fidelity_rules() is True
    assert K.citadel_class_cost("K", 1)[:4] == (1000, 400, 300, 600)
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.CITADEL_COST_MODE == "credits"
    assert K.citadel_fidelity_rules() is True
    colonists, fuel, organics, equipment, days = K.citadel_class_cost("K", 1)
    assert (colonists, fuel, organics, equipment, days) == (1000, 400, 300, 600, 6)


def test_alien_experience_split_is_already_bible() -> None:
    assert K.ALIEN_KILL_EXP_RULE == "bible"
    assert K.ALIEN_KILL_ALIGN_SHARE == 0.5
