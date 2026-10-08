"""Scripted war lab. No LLM. Prints the capture and the refused estimate.

P1 is an N3 with 30,000 fighters. P2's level-2 planet has 2,000 fighters.
P3's level-5 planet has 1,700 shields and 40,000 fighters. The lab asks the
seat brain, then lets the engine land the shot the brain chose.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_phase_abc import _make_universe  # noqa: E402
from tw2k.agents.seat_brain import SeatBrain, SeatMemory, View  # noqa: E402
from tw2k.agents.war_brain import siege_estimate  # noqa: E402
from tw2k.engine import constants as K  # noqa: E402
from tw2k.engine.actions import Action, ActionKind  # noqa: E402
from tw2k.engine.models import Planet, PlanetClass  # noqa: E402
from tw2k.engine.observation import build_observation  # noqa: E402
from tw2k.engine.runner import apply_action  # noqa: E402


def _planet(pid: int, sector: int, owner: str, *, level: int, fighters: int, shields: int,
            treasury: int = 200) -> Planet:
    return Planet(
        id=pid, sector_id=sector, name=f"Lab{pid}", class_id=PlanetClass.M,
        owner_id=owner, fighters=fighters, shields=shields,
        citadel_level=level, citadel_target=level, treasury=treasury,
    )


def _move(u, player, sector_id: int) -> None:
    here = u.sectors[player.sector_id]
    if player.id in here.occupant_ids:
        here.occupant_ids.remove(player.id)
    player.sector_id = sector_id
    player.planet_landed = None
    u.sectors[sector_id].occupant_ids.append(player.id)


def main() -> int:
    K.BOTS_WAR_MODE = "tw2002"
    K.BOT_WAR_POLICY = "full"
    u, (p1, p2, p3) = _make_universe(seed=6301, players=3)
    u.day = 6
    p1.alignment = 200
    p2.alignment = -200
    p3.alignment = -200
    p1.ship.fighters = 30_000
    p1.ship.shields = 0
    fed = set(K.FEDSPACE_SECTORS)
    weak_sector = next(sid for sid in u.sectors if sid >= 40 and sid not in fed)
    strong_sector = next(sid for sid in u.sectors if sid >= 80 and sid not in fed and sid != weak_sector)
    weak = _planet(6302, weak_sector, p2.id, level=2, fighters=2_000, shields=0)
    strong = _planet(6303, strong_sector, p3.id, level=5, fighters=40_000, shields=1_700)
    strong.quasar_sector_pct = 30
    strong.quasar_atm_pct = 60
    u.planets[weak.id] = weak
    u.planets[strong.id] = strong
    u.sectors[weak_sector].planet_ids.append(weak.id)
    u.sectors[strong_sector].planet_ids.append(strong.id)
    _move(u, p1, weak_sector)

    brain = SeatBrain()
    brain.mem = SeatMemory()
    obs = build_observation(u, p1.id)
    raw = obs.model_dump(mode="json") if hasattr(obs, "model_dump") else obs
    action = brain._siege_here(View(raw))
    print(f"P2_CHOICE {None if action is None else action.get('kind')} {None if action is None else action.get('args')}")
    if action is None or action.get("kind") != "land_planet":
        print("LAB FAIL P1 did not choose to land on P2")
        return 1
    result = apply_action(u, p1.id, Action(kind=ActionKind.LAND_PLANET, args=action["args"]))
    print(
        f"P2_CAPTURE ok={result.ok} owner={weak.owner_id} level={weak.citadel_level} "
        f"treasury={weak.treasury} was=200 fighters_left={p1.ship.fighters}"
    )
    if not result.ok or weak.owner_id != p1.id or weak.citadel_level != 1:
        print("LAB FAIL capture did not drop the citadel")
        return 1

    refused = siege_estimate(
        {"fighters": 40_000, "shields": 1_700, "military_reaction_pct": 0},
        {"fighters": 30_000, "ship_class": "merchant_cruiser"},
    )
    print(f"P3_ESTIMATE survive={refused['survive']} needed={refused['fighters_needed']}")
    if refused["survive"]:
        print("LAB FAIL P3 estimate should refuse")
        return 1
    print("LAB PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
