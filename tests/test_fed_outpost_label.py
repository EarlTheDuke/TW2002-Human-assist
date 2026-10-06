"""class0-outpost-label: FedSpace "Federal" ports (sectors 2-10) are not Class 0 ports.

Original TW2002 has exactly three Class 0 ports (Sol, Alpha Centauri, Rylos) and each sells fighters,
shields and holds (cabal glossary "Class 0 Ports", EIS TradeWars.html, Iago_War_Manual.txt). Our ours-only
FedSpace ports are stored as class 0 but trade and sell nothing; a live LLM seat starting beside one read
"class_id 0" and had buy_equip refused twice. Rules: docs/playtests/ports/CLASS0_TERRA.md row t25.
"""

from __future__ import annotations

import json

import pytest

import tw2k.engine.constants as K
from tw2k.agents.prompts import format_observation
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.class0 import fed_outpost_here, is_fed_outpost, special_port_at
from tw2k.engine.legality import legal_actions
from tw2k.engine.models import Player, PortClass, Ship, ShipClass
from tw2k.engine.observation import build_observation
from tw2k.engine.scanners import sector_view


def _world(seed: int = 4501, size: int = 80):
    u = generate_universe(GameConfig(seed=seed, universe_size=size, enable_ferrengi=False, enable_planets=True))
    u.players["A"] = Player(
        id="A", name="Alpha",
        ship=Ship(holds=50, fighters=100, shields=50, ship_class=ShipClass.MERCHANT_CRUISER),
        sector_id=K.STARDOCK_SECTOR, credits=500_000, turns_today=0,
    )
    u.sectors[K.STARDOCK_SECTOR].occupant_ids.append("A")
    return u


def _move(u, pid: str, dest: int) -> None:
    p = u.players[pid]
    if pid in u.sectors[p.sector_id].occupant_ids:
        u.sectors[p.sector_id].occupant_ids.remove(pid)
    p.sector_id = dest
    u.sectors[dest].occupant_ids.append(pid)
    p.known_sectors.add(dest)


def _outpost_sector(u) -> int:
    for sid in sorted(K.FEDSPACE_SECTORS):
        s = u.sectors[sid]
        if s.port is not None and is_fed_outpost(s.port, sid):
            return sid
    raise AssertionError("seed has no FedSpace outpost")


def _buy_equip(u, pid: str) -> dict:
    return next(a for a in legal_actions(u, pid) if a.kind == "buy_equip").model_dump()


@pytest.fixture
def tw(monkeypatch):
    monkeypatch.setattr(K, "CLASS0_MODE", "tw2002")
    monkeypatch.setattr(K, "FED_OUTPOST_MODE", "tw2002")


@pytest.fixture
def legacy(monkeypatch):
    monkeypatch.setattr(K, "FED_OUTPOST_MODE", "legacy")


def test_defaults() -> None:
    assert K.FED_OUTPOST_MODE == "tw2002"
    assert K.fed_outpost_tw2002()


def test_fedspace_outposts_exist_and_trade_nothing(tw) -> None:
    """The ours-only ports are still generated (generation unchanged) and still trade nothing."""
    u = _world()
    sid = _outpost_sector(u)
    port = u.sectors[sid].port
    assert sid != K.STARDOCK_SECTOR and port.class_id == PortClass.FEDERAL and port.special is None
    assert special_port_at(u, sid) is None
    assert fed_outpost_here(u, sid)
    assert not fed_outpost_here(u, K.STARDOCK_SECTOR)


def test_observation_labels_outpost_not_class0(tw) -> None:
    u = _world()
    sid = _outpost_sector(u)
    _move(u, "A", sid)
    port = build_observation(u, "A").sector["port"]
    assert port["class_id"] is None
    assert port["class_display"] == K.FED_OUTPOST_CLASS_DISPLAY
    assert port["note"] == K.FED_OUTPOST_NOTE
    assert "Alpha Centauri" in port["note"] and "sector 1" in port["note"]
    assert port["buys"] == [] and port["sells"] == []
    assert all(s["side"] == "not_traded" for s in port["stock"].values())


def test_llm_prompt_has_no_class0_for_outpost(tw) -> None:
    """What the LLM reads: no `class_id:0` on the outpost, the note is there."""
    u = _world()
    sid = _outpost_sector(u)
    _move(u, "A", sid)
    payload = json.loads(format_observation(build_observation(u, "A")))
    port = payload["sector"]["port"]
    assert port["class_id"] is None
    assert "not a Class 0 port" in port["note"]
    assert "buy_equip" not in payload["legal_actions"]["legal"]
    assert "not a Class 0 port" in payload["legal_actions"]["blocked"]["buy_equip"]
    assert '"class_id":0' not in json.dumps(payload["sector"], separators=(",", ":"))


def test_buy_equip_reason_names_outpost_legal_equals_handler(tw) -> None:
    u = _world()
    sid = _outpost_sector(u)
    _move(u, "A", sid)
    la = _buy_equip(u, "A")
    assert la["legal"] is False
    assert K.FED_OUTPOST_BUY_REASON in la["reason"]
    assert la["reason"].startswith("must be at StarDock (sector 1) or a Class 0 port")
    before = (u.players["A"].credits, u.players["A"].ship.fighters, u.players["A"].turns_today)
    r = apply_action(u, "A", Action(kind=ActionKind.BUY_EQUIP, args={"item": "fighters", "qty": 1}))
    assert r.ok is False
    assert r.error == la["reason"]
    assert (u.players["A"].credits, u.players["A"].ship.fighters, u.players["A"].turns_today) == before


def test_sol_sector1_still_sells_class0_items(tw) -> None:
    """Sol (sector 1, merged with StarDock) is a Class 0: fighters, shields, holds on the legal list."""
    u = _world()
    la = _buy_equip(u, "A")
    assert la["legal"] is True
    choices = set(la["params"]["item"]["choices"])
    assert {"fighters", "shields", "holds"} <= choices
    port = build_observation(u, "A").sector["port"]
    assert port["class_id"] == int(PortClass.STARDOCK) and "note" not in port


def test_alpha_rylos_still_class0(tw) -> None:
    u = _world()
    for key, sid in sorted((u.class0_sectors or {}).items()):
        _move(u, "A", int(sid))
        obs = build_observation(u, "A")
        assert obs.sector["port"]["class_id"] == 0 and "note" not in obs.sector["port"], key
        assert obs.sector["class0_port"]["sells"] == ["fighters", "shields", "holds"]
        assert _buy_equip(u, "A")["legal"] is True


def test_holo_probe_view_labels_outpost(tw) -> None:
    u = _world()
    sid = _outpost_sector(u)
    view = sector_view(u, "A", sid)
    assert view["port"]["class_id"] is None
    assert view["port"]["note"] == K.FED_OUTPOST_NOTE
    ac = int((u.class0_sectors or {})["alpha_centauri"])
    assert sector_view(u, "A", ac)["port"]["class_id"] == 0


def test_class0_legacy_note_points_at_stardock(monkeypatch) -> None:
    """CLASS0_MODE legacy has no Alpha Centauri / Rylos: the note and reason only name StarDock."""
    monkeypatch.setattr(K, "CLASS0_MODE", "legacy")
    monkeypatch.setattr(K, "FED_OUTPOST_MODE", "tw2002")
    u = _world()
    sid = _outpost_sector(u)
    _move(u, "A", sid)
    port = build_observation(u, "A").sector["port"]
    assert port["note"] == K.FED_OUTPOST_NOTE_NO_CLASS0 and "Alpha" not in port["note"]
    la = _buy_equip(u, "A")
    assert la["reason"] == f"must be at StarDock (sector 1); {K.FED_OUTPOST_BUY_REASON}"
    r = apply_action(u, "A", Action(kind=ActionKind.BUY_EQUIP, args={"item": "fighters", "qty": 1}))
    assert r.ok is False and K.FED_OUTPOST_BUY_REASON in r.error


def test_legacy_shows_class0_and_old_reason(legacy) -> None:
    u = _world()
    sid = _outpost_sector(u)
    _move(u, "A", sid)
    port = build_observation(u, "A").sector["port"]
    assert port["class_id"] == 0 and port["code"] == "FED"
    assert "note" not in port and "class_display" not in port
    assert sector_view(u, "A", sid)["port"]["class_id"] == 0
    la = _buy_equip(u, "A")
    assert la["reason"] == "must be at StarDock (sector 1) or a Class 0 port"
    r = apply_action(u, "A", Action(kind=ActionKind.BUY_EQUIP, args={"item": "fighters", "qty": 1}))
    assert r.error == "must be at StarDock (sector 1) or a Class 0 port"


def test_legacy_observation_byte_identical_off_outposts(monkeypatch) -> None:
    """Away from an outpost the mode changes nothing; generation is the same in both modes."""
    dumps = {}
    for mode in ("legacy", "tw2002"):
        monkeypatch.setattr(K, "FED_OUTPOST_MODE", mode)
        u = _world()
        dumps[mode] = (u.model_dump_json(), format_observation(build_observation(u, "A")))
    assert dumps["legacy"] == dumps["tw2002"]


def test_outpost_trade_still_refused(tw) -> None:
    """Engine identity unchanged: trading at the outpost is refused exactly as before."""
    u = _world()
    sid = _outpost_sector(u)
    _move(u, "A", sid)
    trade = next(a for a in legal_actions(u, "A") if a.kind == "trade").model_dump()
    assert trade["legal"] is False
