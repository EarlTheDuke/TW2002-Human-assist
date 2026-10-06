"""Alien traders scenario lab (alien-traders-v1 MATCH CHECK e). No server, no paid call.

A good merchant meets an evil alien in sector 600, traps it, and kills it.
The bible award is half the alien's experience and half its alignment, on top of
the fighter-loss award the combat rules already pay. A replacement enters at
StarDock. A fedsafe alien in FedSpace pods the attacker. A minimum attack
captures. A corporation cannot invite an alien.
"""

from __future__ import annotations

from tw2k.engine import GameConfig, generate_universe
from tw2k.engine import constants as K
from tw2k.engine.actions import Action, ActionKind
from tw2k.engine.models import (
    EventKind,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Player,
    Ship,
    ShipClass,
)
from tw2k.engine.runner import apply_action, tick_day


def _act(u, pid: str, kind: str, **args):
    return apply_action(u, pid, Action(kind=ActionKind(kind), args=args))


def _move(u, pid: str, sid: int) -> None:
    for sector in u.sectors.values():
        if pid in sector.occupant_ids:
            sector.occupant_ids.remove(pid)
    u.players[pid].sector_id = sid
    u.sectors[sid].occupant_ids.append(pid)


def _fight_award(lost: int, mine: int, theirs: int) -> tuple[int, int]:
    kind = "neutral" if mine == 0 or theirs == 0 else ("same" if (mine > 0) == (theirs > 0) else "opposite")
    exp = lost // K.COMBAT_EXP_DIVISOR[kind]
    num = lost * theirs
    toward = (abs(num) // K.COMBAT_ALIGN_DIVISOR) * (1 if num >= 0 else -1)
    return exp, -toward


def main() -> dict:
    assert K.alien_on(), "run with ALIEN_MODE tw2002"
    u = generate_universe(GameConfig(
        seed=58, universe_size=1000, max_days=6, turns_per_day=80,
        starting_credits=50_000, enable_ferrengi=False,
    ))
    assert 600 in u.sectors, "sector 600 is the spec's meeting sector"
    for pid, name, align in (("A", "Ann", 100), ("B", "Bo", 400), ("C", "Cy", 100)):
        u.players[pid] = Player(
            id=pid, name=name, agent_kind="external", sector_id=1,
            credits=50_000, alignment=align, experience=0,
            ship=Ship(ship_class=ShipClass.MERCHANT_CRUISER, fighters=2_000, shields=400),
        )
        u.sectors[1].occupant_ids.append(pid)

    alien = next(iter(u.aliens.values()))
    alien.alignment = -250
    alien.experience = 400
    alien.credits = 5_000
    alien.ship.ship_class = ShipClass.MERCHANT_CRUISER
    alien.ship.fighters = 200
    alien.ship.shields = 50
    alien.ship.corbomite = 3
    alien.sector_id = 600
    for other in u.aliens.values():
        if other.id != alien.id and other.sector_id == 600:
            other.sector_id = 20
    _move(u, "A", 600)
    for dest in u.sectors[600].warps:
        u.sectors[dest].fighters = FighterDeployment(
            owner_id="A", count=1, mode=FighterMode.TOLL,
        )
    weak = _act(u, "A", "attack", target=alien.id, qty=40)
    assert weak.ok, weak.error
    assert alien.alive and alien.sector_id == 600
    assert int(alien.ship.fighters) < 200 or int(alien.ship.shields) < 50
    held_f, held_s = int(alien.ship.fighters), int(alien.ship.shields)
    assert (held_f, held_s) == (int(alien.ship.fighters), int(alien.ship.shields))

    before_exp, before_align, before_cr = u.players["A"].experience, u.players["A"].alignment, u.players["A"].credits
    killing = _act(u, "A", "attack", target=alien.id, qty=400)
    assert killing.ok and not alien.alive
    combat = next(ev for ev in reversed(u.events) if ev.kind == EventKind.COMBAT and ev.payload.get("defender") == alien.id)
    lost = int(combat.payload["attacker_losses"])
    fight_exp, fight_align = _fight_award(lost, before_align, -250)
    assert u.players["A"].experience - before_exp == fight_exp + 200
    assert u.players["A"].alignment - before_align == fight_align + 125
    assert u.players["A"].credits - before_cr == 5_000
    assert any(ev.kind == EventKind.CORBOMITE_BLAST for ev in u.events)
    assert not any(
        ev.kind == EventKind.SHIP_DESTROYED and ev.payload.get("bounty")
        for ev in u.events
    )
    out = {
        "bible_exp": 200,
        "fight_exp": fight_exp,
        "bible_align": 125,
        "fight_align": fight_align,
        "loot": 5_000,
        "weak_fighters": held_f,
        "weak_shields": held_s,
    }

    n_ev = len(u.events)
    tick_day(u)
    spawned = [
        ev for ev in u.events[n_ev:]
        if ev.kind == EventKind.ALIEN_SPAWN and ev.sector_id == K.STARDOCK_SECTOR
    ]
    assert spawned, "a replacement enters at StarDock"
    replacement = u.aliens[spawned[-1].payload["id"]]
    home = next(
        sid for sid, sector in u.sectors.items()
        if sid not in K.FEDSPACE_SECTORS and len(sector.warps) >= 2 and sid != 600
    )
    mine_sector = u.sectors[home].warps[0]
    for dest in u.sectors[home].warps:
        if dest != mine_sector:
            u.sectors[dest].fighters = FighterDeployment(owner_id="A", count=1, mode=FighterMode.TOLL)
    u.sectors[mine_sector].fighters = None
    u.sectors[mine_sector].mines.append(MineDeployment(owner_id="A", kind=MineType.ARMID, count=2))
    for dest in u.sectors[mine_sector].warps:
        if dest != home:
            u.sectors[dest].fighters = FighterDeployment(owner_id="A", count=1, mode=FighterMode.TOLL)
    trap = u.sectors[home].warps[1]
    for dest in u.sectors[trap].warps:
        u.sectors[dest].fighters = FighterDeployment(owner_id="A", count=1, mode=FighterMode.OFFENSIVE)
    for other in u.aliens.values():
        if other.id != replacement.id and other.alive:
            other.sector_id = trap
    replacement.sector_id = home
    replacement.ship.fighters = 500
    replacement.ship.shields = 0
    before_f = int(replacement.ship.fighters)
    tick_day(u)
    assert int(replacement.ship.fighters) < before_f
    assert u.sectors[replacement.sector_id].fighters is None
    out["mine_loss"] = before_f - int(replacement.ship.fighters)

    good = next(row for row in u.aliens.values() if row.alive and row.id != replacement.id)
    good.alignment, good.experience, good.sector_id = 200, 100, 3
    good.ship.fighters, good.ship.shields = 10, 0
    _move(u, "B", 3)
    align_b = u.players["B"].alignment
    refused = _act(u, "B", "attack", target=good.id, qty=1)
    assert not refused.ok and "Zyrain" in (refused.error or "")
    assert u.players["B"].alignment == align_b - 200
    assert u.players["B"].ship.ship_class.value == K.ESCAPE_POD
    assert good.alive
    out["zyrain"] = refused.error

    prey = next(row for row in u.aliens.values() if row.alive and row.id not in (good.id, replacement.id))
    prey.experience, prey.alignment, prey.credits = 80, -100, 1_000
    prey.ship.fighters = prey.ship.shields = 0
    prey.ship.corbomite = 3
    _move(u, "C", prey.sector_id)
    blasts = sum(1 for ev in u.events if ev.kind == EventKind.CORBOMITE_BLAST)
    assert _act(u, "C", "attack", target=prey.id, qty=1).ok
    assert not prey.alive
    assert any(rec.owner_id == "C" and rec.ship.ship_class == prey.ship.ship_class for rec in u.parked_ships.values())
    assert sum(1 for ev in u.events if ev.kind == EventKind.CORBOMITE_BLAST) == blasts
    assert u.players["C"].experience >= 40 and u.players["C"].credits >= 51_000

    assert _act(u, "A", "corp_create", ticker="ZZ", name="Zed").ok
    assert _act(u, "A", "corp_set_password", password="secret").ok
    invited = _act(u, "A", "corp_invite", target=replacement.id)
    assert not invited.ok and invited.error == "aliens cannot join corporations"
    print("alien_traders_scenario_lab: PASS")
    print(out)
    return out


if __name__ == "__main__":
    main()
