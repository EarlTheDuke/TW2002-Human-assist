"""Phase A/B/C smoke: drive the engine through every new code path with synthetic actions.

Run directly:  python scripts/smoke_phase_abc.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe, tick_day
from tw2k.engine import constants as K
from tw2k.engine.models import (
    Commodity,
    FerrengiShip,
    MineType,
    Player,
    Ship,
)

PASS = []
FAIL = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        PASS.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL.append((name, detail))
        print(f"  FAIL  {name}  ({detail})")


def main() -> int:
    cfg = GameConfig(seed=2026, universe_size=200, max_days=10, planet_spawn_probability=0.06)
    u = generate_universe(cfg)
    a = Player(id="A", name="Alice", ship=Ship(holds=40, fighters=200, shields=100), sector_id=1)
    b = Player(id="B", name="Bob",   ship=Ship(holds=40, fighters=200, shields=100), sector_id=1)
    c = Player(id="C", name="Carol", ship=Ship(holds=40, fighters=200, shields=100), sector_id=1)
    for p in (a, b, c):
        u.players[p.id] = p
        u.sectors[1].occupant_ids.append(p.id)
        p.known_sectors.add(1)

    print("\n[A.5] Per-ship turns_per_warp")
    nxt = u.sectors[1].warps[0]
    res = apply_action(u, "A", Action(kind=ActionKind.WARP, args={"target": nxt}))
    check("warp ok", res.ok, str(res.error))
    check("warp consumed 3 turns (Merchant Cruiser)", a.turns_today == 3, f"got {a.turns_today}")

    # --------- A.3 Genesis ----------
    print("\n[A.3] Deploy Genesis torpedo")
    a.ship.genesis = 1
    if a.sector_id in K.FEDSPACE_SECTORS:
        # warp out to non-fedspace
        for hop in [a.sector_id] + u.sectors[a.sector_id].warps:
            if hop not in K.FEDSPACE_SECTORS:
                a.sector_id = hop
                break
    a.sector_id = next(sid for sid in u.sectors if sid > 30)
    a.turns_today = 0
    pre_planets = len(u.planets)
    res = apply_action(u, "A", Action(kind=ActionKind.DEPLOY_GENESIS))
    check("genesis succeeded", res.ok, str(res.error))
    check("new planet created", len(u.planets) == pre_planets + 1)
    check("genesis count decremented", a.ship.genesis == 0)
    new_planet = max(u.planets.values(), key=lambda p: p.id)
    check("planet owned by deployer", new_planet.owner_id == "A")

    # --------- A.1 assign colonists ----------
    print("\n[A.1] Assign colonists from cargo to planet pools")
    a.ship.cargo[Commodity.COLONISTS] = 5000
    res = apply_action(u, "A", Action(kind=ActionKind.LAND_PLANET, args={"planet_id": new_planet.id}))
    check("land on own planet", res.ok, str(res.error))
    res = apply_action(u, "A", Action(
        kind=ActionKind.ASSIGN_COLONISTS,
        args={"planet_id": new_planet.id, "from": "ship", "to": "fuel_ore", "qty": 2000},
    ))
    check("assign 2000→fuel_ore", res.ok, str(res.error))
    check("planet has 2000 fuel-ore colonists", new_planet.colonists.get(Commodity.FUEL_ORE) == 2000)
    check("ship colonists drained", a.ship.cargo[Commodity.COLONISTS] == 3000)

    # --------- A.2 build_citadel ----------
    print("\n[A.2] Build Citadel L1 then complete")
    a.credits = 50_000
    res = apply_action(u, "A", Action(
        kind=ActionKind.ASSIGN_COLONISTS,
        args={"planet_id": new_planet.id, "from": "ship", "to": "colonists", "qty": 3000},
    ))
    check("assign 3000 def colonists", res.ok, str(res.error))
    res = apply_action(u, "A", Action(kind=ActionKind.BUILD_CITADEL, args={"planet_id": new_planet.id}))
    check("citadel L1 build started", res.ok, str(res.error))
    check("citadel target=1", new_planet.citadel_target == 1)
    # Tick days until completion
    for _ in range(3):
        tick_day(u)
    check("citadel L1 completed after days", new_planet.citadel_level == 1, f"level={new_planet.citadel_level}")

    # --------- A.6 Ferrengi roam & hunt ----------
    print("\n[A.6] Ferrengi roam & hunt step")
    # Inject high-aggression Ferrengi in same sector as Bob
    far_sid = next(sid for sid in u.sectors if sid > 50 and sid not in K.FEDSPACE_SECTORS)
    b.sector_id = far_sid
    # Move Bob into the new sector
    u.sectors[1].occupant_ids = [x for x in u.sectors[1].occupant_ids if x != "B"]
    u.sectors[far_sid].occupant_ids.append("B")
    pre_fighters = b.ship.fighters
    # Try across several days; Ferrengi has 60% chance of moving before attacking,
    # so re-seed the ferrengi each tick to keep it on bob's location.
    hit = False
    for _ in range(8):
        u.ferrengi.clear()
        u.ferrengi["ferr_test"] = FerrengiShip(
            id="ferr_test", name="Test Raider", sector_id=b.sector_id,
            aggression=9, fighters=400, shields=200,
        )
        tick_day(u)
        if b.ship.fighters < pre_fighters or not b.alive:
            hit = True
            break
    check("ferrengi eventually attacked bob", hit,
          f"bob.fighters {pre_fighters}->{b.ship.fighters} alive={b.alive}")

    # --------- A.4 player elimination ----------
    print("\n[A.4] Player elimination after MAX_DEATHS")
    from tw2k.engine.runner import _destroy_ship
    a.alive = True
    a.deaths = 0
    for _ in range(K.MAX_DEATHS_BEFORE_ELIM):
        _destroy_ship(u, "A", reason="test")
    check("player eliminated", a.alive is False, f"alive={a.alive} deaths={a.deaths}")

    # --------- B.1 plot_course ----------
    print("\n[B.1] Plot course autopilot")
    b.alive = True
    b.deaths = 0
    b.ship.fighters = 1000
    b.turns_today = 0
    target = next(sid for sid in u.sectors if sid > 100)
    res = apply_action(u, "B", Action(kind=ActionKind.PLOT_COURSE, args={"target": target}))
    check("plot_course ok", res.ok, str(res.error))
    res = apply_action(u, "B", Action(kind=ActionKind.PLOT_COURSE, args={"target": target, "execute": True}))
    check("plot_course executed", res.ok, str(res.error))
    check("bob actually moved closer", b.sector_id != far_sid, f"sector now {b.sector_id}")

    # --------- B.2 photon_missile ----------
    print("\n[B.2] Photon missile disables fighters")
    # put bob & carol together outside fedspace
    sid = next(sid for sid in u.sectors if sid > 50 and sid not in K.FEDSPACE_SECTORS)
    b.sector_id = sid
    c.sector_id = sid
    b.ship.photon_missiles = 1
    b.turns_today = 0
    res = apply_action(u, "B", Action(kind=ActionKind.PHOTON_MISSILE, args={"target": "C"}))
    check("photon fired", res.ok, str(res.error))
    check("carol photon-disabled", c.ship.photon_disabled_ticks > 0)

    # --------- B.3 atomic mine ----------
    print("\n[B.3] Atomic mine detonation")
    b.ship.mines[MineType.ATOMIC] = 3
    pre_align = b.alignment
    res = apply_action(u, "B", Action(kind=ActionKind.DEPLOY_MINES, args={"kind": "atomic", "qty": 1}))
    check("atomic detonated", res.ok, str(res.error))
    check("alignment crashed", b.alignment < pre_align)

    # --------- B.4 limpet ----------
    print("\n[B.4] Limpet attaches and reports")
    sid_l = next(sid for sid in u.sectors if sid > 60 and sid not in K.FEDSPACE_SECTORS)
    c.sector_id = sid_l
    u.sectors[sid_l].mines.append(__import__('tw2k.engine.models', fromlist=['MineDeployment']).MineDeployment(
        owner_id="B", kind=MineType.LIMPET, count=2,
    ))
    # warp Carol through that sector — pick a neighbor warp INTO it
    inbound_src = next((s.id for s in u.sectors.values() if sid_l in s.warps and s.id != sid_l), None)
    if inbound_src is not None:
        c.sector_id = inbound_src
        u.sectors[inbound_src].occupant_ids = list(set(u.sectors[inbound_src].occupant_ids + ["C"]))
        c.turns_today = 0
        res = apply_action(u, "C", Action(kind=ActionKind.WARP, args={"target": sid_l}))
        check("carol warped through limpet sector", res.ok, str(res.error))
        check("limpet stuck to carol", any(lt.target_id == "C" for lt in u.limpets.values()))
        # Move carol again, then query
        b.turns_today = 0
        res = apply_action(u, "B", Action(kind=ActionKind.QUERY_LIMPETS))
        check("query_limpets ok", res.ok, str(res.error))

    # --------- C.1 alliance ----------
    print("\n[C.1] Alliance proposal & accept")
    # reset all
    b.alive = True; b.deaths = 0; b.turns_today = 0
    c.alive = True; c.deaths = 0; c.turns_today = 0
    res = apply_action(u, "B", Action(kind=ActionKind.PROPOSE_ALLIANCE,
                                      args={"target": "C", "terms": "test pact"}))
    check("alliance proposed", res.ok, str(res.error))
    aid = next(iter(u.alliances))
    res = apply_action(u, "C", Action(kind=ActionKind.ACCEPT_ALLIANCE, args={"alliance_id": aid}))
    check("alliance accepted", res.ok, str(res.error))
    check("alliance now active", u.alliances[aid].active)
    # Now they can't attack each other
    sid2 = next(sid for sid in u.sectors if sid > 70 and sid not in K.FEDSPACE_SECTORS)
    b.sector_id = sid2
    c.sector_id = sid2
    res = apply_action(u, "B", Action(kind=ActionKind.ATTACK, args={"target": "C"}))
    check("ally cannot attack ally", not res.ok)

    # --------- C.3 corp treasury ----------
    print("\n[C.3] Corp treasury deposit / withdraw")
    a.alive = True; a.deaths = 0
    a.sector_id = K.STARDOCK_SECTOR
    a.credits = 1_000_000
    a.turns_today = 0
    res = apply_action(u, "A", Action(kind=ActionKind.CORP_CREATE, args={"ticker": "ZZZ", "name": "Zog"}))
    check("corp created", res.ok, str(res.error))
    res = apply_action(u, "A", Action(kind=ActionKind.CORP_DEPOSIT, args={"amount": 200_000}))
    check("deposit ok", res.ok, str(res.error))
    check("treasury 200000", u.corporations["ZZZ"].treasury == 200_000)
    res = apply_action(u, "A", Action(kind=ActionKind.CORP_WITHDRAW, args={"amount": 50_000}))
    check("withdraw ok", res.ok, str(res.error))
    check("treasury 150000", u.corporations["ZZZ"].treasury == 150_000)

    # ------- DONE -------
    print(f"\n=== {len(PASS)} passed, {len(FAIL)} failed ===")
    if FAIL:
        for n, d in FAIL:
            print(f"  - {n}: {d}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
