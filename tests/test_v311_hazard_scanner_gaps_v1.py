"""NOTE 85 (v311-hazard-scanner-gaps-v1): probe owner, Ferrengi rewards, Ferrengal quasar.

SD-p and FIG-l are already the stored rule, so rows 100 and 103 add no switch.
"""

from __future__ import annotations

import tw2k.engine.constants as K
from tw2k.engine import Action, ActionKind, GameConfig, apply_action, build_observation, generate_universe
from tw2k.engine.combat import _resolve_ship_combat_attacker_npc
from tw2k.engine.corp import _controls, deploy_friend
from tw2k.engine.models import (
    FerrengiShip,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Player,
    Ship,
)
from tw2k.engine.observation import _ferrengi_check
from tw2k.engine.runner import _apply_sector_hazards, _quasar_shot


def _world(seed: int = 8501):
    return generate_universe(
        GameConfig(
            seed=seed,
            universe_size=80,
            max_days=5,
            enable_ferrengi=False,
            enable_planets=False,
            planet_spawn_probability=0,
        )
    )


def _lane(u):
    fed = set(K.FEDSPACE_SECTORS)
    for sid, sector in u.sectors.items():
        if int(sid) in fed:
            continue
        for dest in sector.warps:
            dest = int(dest)
            if dest not in fed:
                return int(sid), dest
    raise AssertionError("no lane outside FedSpace")


def _seat(u, pid, name, sector_id, **raw):
    ship = Ship(
        holds=20,
        fighters=int(raw.get("fighters", 50)),
        shields=int(raw.get("shields", 0)),
        ether_probes=int(raw.get("probes", 0)),
    )
    if "scanner" in raw:
        ship.scanner = raw["scanner"]
    player = Player(
        id=pid,
        name=name,
        ship=ship,
        sector_id=int(sector_id),
        credits=int(raw.get("credits", 1_000)),
        turns_today=0,
        turns_per_day=1_000,
        alignment=int(raw.get("alignment", 0)),
        experience=int(raw.get("experience", 100)),
    )
    u.players[pid] = player
    sector = u.sectors[int(sector_id)]
    if pid not in sector.occupant_ids:
        sector.occupant_ids.append(pid)
    player.known_sectors.add(int(sector_id))
    return player


def _clear(sector):
    sector.mines = []
    sector.fighters = None
    sector.nav_hazard = 0
    sector.planet_ids = []


def _probe(u, pid, target):
    return apply_action(u, pid, Action(kind=ActionKind.PROBE, args={"target": target}))


def _attack(u, pid, target):
    return apply_action(u, pid, Action(kind=ActionKind.ATTACK, args={"target": target, "qty": 100}))


def _ferrengi(fid, sid, aggression, hull, credits=100):
    return FerrengiShip(
        id=fid,
        name=f"Ferrengi {fid}",
        sector_id=sid,
        aggression=aggression,
        fighters=1,
        shields=0,
        hull=hull,
        credits=credits,
    )


def test_stored_switches_stay_legacy():
    assert K.PROBE_SHOOTDOWN_MODE == "legacy"
    assert K.FERRENGI_REWARD_MODE == "legacy"
    assert K.FERRENGAL_QUASAR_MODE == "legacy"
    assert K.probe_shootdown_live() is False
    assert K.ferrengi_reward_live() is False
    assert K.ferrengal_quasar_live() is False
    assert not hasattr(K, "SCANNER_DEVICE_MODE")
    assert not hasattr(K, "CORP_DEPLOY_MODE")


def test_v311_profile_turns_the_three_helpers_on(monkeypatch):
    monkeypatch.setattr(K, "V311_PROFILE", "v311")
    assert K.probe_shootdown_live() is True
    assert K.ferrengi_reward_live() is True
    assert K.ferrengal_quasar_live() is True
    assert K.PROBE_SHOOTDOWN_MODE == "legacy"
    assert K.FERRENGI_REWARD_MODE == "legacy"
    assert K.FERRENGAL_QUASAR_MODE == "legacy"


def test_probe_off_keeps_the_old_summary_and_payload():
    u = _world()
    home, busy = _lane(u)
    _clear(u.sectors[busy])
    u.sectors[busy].fighters = FighterDeployment(owner_id="B", count=20, mode=FighterMode.DEFENSIVE)
    _seat(u, "A", "Alice", home, probes=2)
    _seat(u, "B", "Bob", busy)
    res = _probe(u, "A", busy)
    assert res.ok
    ev = [e for e in u.events if e.kind.value == "probe"][-1]
    assert ev.payload["destroyed_at"] == busy
    assert "fighter_owner" not in ev.payload
    assert "fighter_owner_id" not in ev.payload
    assert ev.summary == (
        f"Alice's probe was destroyed by fighters in sector {busy} "
        f"({len(ev.payload['route']) + 1} sector{'s' if len(ev.payload['route']) + 1 != 1 else ''} out)"
    )
    assert "owned by" not in ev.summary
    assert busy not in u.players["A"].known_warps


def test_probe_live_names_the_fighter_owner_and_stops(monkeypatch):
    monkeypatch.setattr(K, "PROBE_SHOOTDOWN_MODE", "live")
    u = _world(8502)
    fed = set(K.FEDSPACE_SECTORS)
    home, busy, beyond = [int(s) for s in sorted(u.sectors) if int(s) not in fed][:3]
    u.sectors[home].warps = [busy]
    u.sectors[busy].warps = [home, beyond]
    _clear(u.sectors[busy])
    u.sectors[busy].fighters = FighterDeployment(owner_id="B", count=20, mode=FighterMode.OFFENSIVE)
    alice = _seat(u, "A", "Alice", home, probes=2)
    _seat(u, "B", "Bob", busy)
    assert _probe(u, "A", beyond).ok
    ev = [e for e in u.events if e.kind.value == "probe"][-1]
    assert ev.payload["destroyed_at"] == busy
    assert ev.payload["fighter_owner_id"] == "B"
    assert ev.payload["fighter_owner"] == "Bob"
    assert f"fighters owned by Bob in sector {busy}" in ev.summary
    assert beyond not in alice.probe_log
    assert busy not in alice.known_warps

    u.sectors[busy].fighters = FighterDeployment(
        owner_id=K.FERRENGI_OWNER_ID, count=5, mode=FighterMode.DEFENSIVE
    )
    assert _probe(u, "A", beyond).ok
    ev = [e for e in u.events if e.kind.value == "probe"][-1]
    assert ev.payload["fighter_owner"] == "the Ferrengi"

    alice.ship.ether_probes = 1
    u.sectors[busy].fighters = FighterDeployment(
        owner_id=K.ROGUE_OWNER_ID, count=5, mode=FighterMode.TOLL
    )
    assert _probe(u, "A", beyond).ok
    ev = [e for e in u.events if e.kind.value == "probe"][-1]
    assert ev.payload["fighter_owner"] == "rogue fighters"
    assert "owned by rogue fighters" in ev.summary


def test_scans_already_need_the_bought_device():
    """SD-p, row 100. INFO_MODE tw2002 already gates density and holo. No new switch."""
    assert K.INFO_MODE == "tw2002"
    assert K.DENSITY_SCANNER_COST == 2_000
    assert K.HOLO_SCANNER_COST == 25_000
    u = _world(8503)
    home, _ = _lane(u)
    alice = _seat(u, "A", "Alice", home)
    denied = apply_action(u, "A", Action(kind=ActionKind.SCAN, args={"tier": "density"}))
    assert not denied.ok
    assert denied.error == "no long range scanner (buy_equip density_scanner or holo_scanner at StarDock)"
    alice.ship.scanner = "density"
    assert apply_action(u, "A", Action(kind=ActionKind.SCAN, args={"tier": "density"})).ok
    holo = apply_action(u, "A", Action(kind=ActionKind.SCAN, args={"tier": "holo"}))
    assert not holo.ok and "holo" in holo.error
    alice.ship.scanner = "holo"
    assert apply_action(u, "A", Action(kind=ActionKind.SCAN, args={"tier": "density"})).ok
    assert apply_action(u, "A", Action(kind=ActionKind.SCAN, args={"tier": "holo"})).ok


def test_legacy_ferrengi_kill_pays_alignment_and_scaled_xp():
    u = _world(8504)
    home, _ = _lane(u)
    player = _seat(u, "A", "Alice", home, fighters=8_000, shields=500, credits=0, alignment=-20, experience=40)
    ferr = _ferrengi("e1", home, 3, K.FERRENGI_HULL_ASSAULT, credits=100)
    u.ferrengi = {"e1": ferr}
    assert _attack(u, "A", "e1").ok
    assert not ferr.alive
    assert player.alignment == -10
    assert player.experience == 40 + 20 * 3
    assert player.credits >= K.FERRENGI_BOUNTY_PER_AGG * 3


def test_live_ferrengi_kill_alignment_only_for_a_good_trader_and_xp_by_hull(monkeypatch):
    monkeypatch.setattr(K, "FERRENGI_REWARD_MODE", "live")
    cases = (
        (0, 0, K.FERRENGI_HULL_ASSAULT, 50),
        (12, 12 + K.FERRENGI_ALIGN_ON_KILL, K.FERRENGI_HULL_CRUISER, 100),
        (-8, -8, K.FERRENGI_HULL_DREAD, 150),
    )
    for start, expect_align, hull, xp in cases:
        u = _world(8505 + start)
        home, _ = _lane(u)
        player = _seat(
            u, "A", "Alice", home, fighters=8_000, shields=500, credits=0, alignment=start, experience=10,
        )
        ferr = _ferrengi("e1", home, 4, hull, credits=25)
        u.ferrengi = {"e1": ferr}
        assert _attack(u, "A", "e1").ok, start
        assert player.alignment == expect_align
        assert player.experience == 10 + xp
        assert player.credits >= K.FERRENGI_BOUNTY_PER_AGG * 4

    u = _world(8519)
    home, _ = _lane(u)
    player = _seat(u, "A", "Alice", home, fighters=8_000, shields=500, credits=0, alignment=4, experience=7)
    ferr = _ferrengi("e1", home, 2, "", credits=0)
    u.ferrengi = {"e1": ferr}
    assert _attack(u, "A", "e1").ok
    assert player.experience == 7 + 20 * 2


def test_live_reward_when_the_ferrengi_dies_on_its_own_attack(monkeypatch):
    u = _world(8520)
    home, _ = _lane(u)
    player = _seat(u, "A", "Alice", home, fighters=5_000, shields=400, credits=10, alignment=0, experience=80)
    ferr = _ferrengi("e1", home, 4, K.FERRENGI_HULL_DREAD, credits=999)
    deaths = player.deaths
    _resolve_ship_combat_attacker_npc(u, ferr, player)
    assert not ferr.alive and player.alive and player.deaths == deaths
    assert player.credits == 10
    assert player.alignment == 0
    assert player.experience == 80

    monkeypatch.setattr(K, "FERRENGI_REWARD_MODE", "live")
    player.alignment = 6
    player.ship.fighters = 5_000
    player.ship.shields = 400
    ferr = _ferrengi("e2", home, 4, K.FERRENGI_HULL_ASSAULT, credits=999)
    _resolve_ship_combat_attacker_npc(u, ferr, player)
    assert not ferr.alive and player.deaths == deaths
    assert player.credits == 10 + K.FERRENGI_BOUNTY_PER_AGG * 4
    assert player.alignment == 6 + K.FERRENGI_ALIGN_ON_KILL
    assert player.experience == 80 + K.FERRENGI_XP_BY_HULL[K.FERRENGI_HULL_ASSAULT]
    assert all(int(qty or 0) == 0 for qty in player.ship.cargo.values())


def test_ferrengi_hint_stays_put_until_the_reward_switch(monkeypatch):
    u = _world(8521)
    home, _ = _lane(u)
    player = _seat(u, "A", "Alice", home, fighters=100)
    row = {"id": "e1", "aggression": 3, "fighters": 1, "shields": 0, "hull": "assault_trader"}
    off = _ferrengi_check(player, {"ferrengi": [row]})
    assert "3,000 cr bounty + salvage, 60 exp, +10 alignment;" in off
    monkeypatch.setattr(K, "FERRENGI_REWARD_MODE", "live")
    live = _ferrengi_check(player, {"ferrengi": [row]})
    assert "50 exp by hull" in live
    assert "alignment if you are a good trader" in live


def test_ferrengal_quasar_off_does_nothing():
    burned, damage = _quasar_shot(K.FERRENGAL_QUASAR_FUEL, K.FERRENGAL_QUASAR_PCT)
    assert (burned, damage) == (1_000, 333)
    u = _world(8522)
    home, there = _lane(u)
    _clear(u.sectors[there])
    u.ferrengal_sector = there
    player = _seat(u, "A", "Alice", home, fighters=40, shields=400)
    _apply_sector_hazards(u, "A", u.sectors[there], entry_verb="entering")
    assert player.ship.shields == 400 and player.ship.fighters == 40
    assert not any(e.kind.value == "quasar_fire" for e in u.events)


def test_ferrengal_quasar_live_uses_the_s1_shot(monkeypatch):
    monkeypatch.setattr(K, "FERRENGAL_QUASAR_MODE", "live")
    u = _world(8523)
    home, there = _lane(u)
    other = next(int(s) for s in u.sectors if int(s) not in (home, there))
    dest = u.sectors[there]
    _clear(dest)
    u.ferrengal_sector = there
    player = _seat(u, "A", "Alice", home, fighters=40, shields=400)
    _apply_sector_hazards(u, "A", dest, entry_verb="entering")
    assert player.ship.shields == 400 - 333
    assert player.ship.fighters == 40
    ev = [e for e in u.events if e.kind.value == "quasar_fire"][-1]
    assert ev.payload["damage"] == 333 and ev.payload["burned"] == 1_000
    assert ev.payload["victim"] == "A"
    assert ev.summary == "The Quasar Cannon on Ferrengal locks onto Alice and fires for 333"
    seen = [e.get("summary") or "" for e in build_observation(u, "A").recent_events]
    assert any("Quasar Cannon on Ferrengal" in line for line in seen)

    before = len([e for e in u.events if e.kind.value == "quasar_fire"])
    _apply_sector_hazards(u, "A", dest, entry_verb="landing")
    assert len([e for e in u.events if e.kind.value == "quasar_fire"]) == before

    u.ferrengal_sector = other
    shields = player.ship.shields
    _apply_sector_hazards(u, "A", dest, entry_verb="entering")
    assert player.ship.shields == shields

    u.ferrengal_sector = there
    player.ship.shields = 0
    player.ship.fighters = 100
    _apply_sector_hazards(u, "A", dest, entry_verb="entering")
    assert player.ship.ship_class.value == K.ESCAPE_POD
    assert any("locks onto Alice" in e.summary for e in u.events if e.kind.value == "quasar_fire")


def test_mines_kill_before_the_ferrengal_shot(monkeypatch):
    monkeypatch.setattr(K, "FERRENGAL_QUASAR_MODE", "live")
    u = _world(8524)
    home, there = _lane(u)
    dest = u.sectors[there]
    _clear(dest)
    dest.mines = [MineDeployment(owner_id=K.FERRENGI_OWNER_ID, kind=MineType.ARMID, count=2)]
    u.ferrengal_sector = there
    player = _seat(u, "A", "Alice", home, fighters=1, shields=0)
    _apply_sector_hazards(u, "A", dest, entry_verb="entering")
    assert player.deaths == 1
    assert not any(e.kind.value == "quasar_fire" for e in u.events)


def test_corporate_and_personal_deploy_already_differ():
    """FIG-l, row 103. CORP_MODE tw2002 already splits corporate and personal."""
    assert K.CORP_MODE == "tw2002"
    assert K.corp_rules_on()
    assert K.CORP_DEPLOY_DEFAULT == "corporate"
    assert K.CORP_RECLAIM_BY == "member"
    u = _world(8525)
    home, _ = _lane(u)
    owner = _seat(u, "A", "Alice", home)
    mate = _seat(u, "B", "Bob", home)
    owner.corp_ticker = "XYZ"
    mate.corp_ticker = "XYZ"
    personal = FighterDeployment(owner_id="A", count=5, mode=FighterMode.DEFENSIVE)
    corporate = FighterDeployment(owner_id="A", count=5, mode=FighterMode.OFFENSIVE, corp_ticker="XYZ")
    personal_mine = MineDeployment(owner_id="A", kind=MineType.ARMID, count=2)
    corporate_mine = MineDeployment(owner_id="A", kind=MineType.ARMID, count=2, corp_ticker="XYZ")
    assert deploy_friend(u, "A", personal) and not deploy_friend(u, "B", personal)
    assert deploy_friend(u, "B", corporate)
    assert deploy_friend(u, "A", personal_mine) and not deploy_friend(u, "B", personal_mine)
    assert deploy_friend(u, "B", corporate_mine)
    assert _controls(u, "A", personal) and not _controls(u, "B", personal)
    assert _controls(u, "B", corporate) and _controls(u, "B", corporate_mine)
