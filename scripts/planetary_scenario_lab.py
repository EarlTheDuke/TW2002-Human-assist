"""Headless planet-siege grid. No server, no paid call, not collected by pytest.

Each cell reseeds the combat dice, plants one defended planet, and calls
apply_action land_planet. reaction_pct is written onto the planet.
quasar still raises until a later slice.
"""

from __future__ import annotations

import argparse
import csv
import io
import random
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tw2k.engine import Action, ActionKind, GameConfig, apply_action, generate_universe
from tw2k.engine.models import Planet, PlanetClass, Player, Ship

SECTOR_ID = 40
PLANET_ID = 88001
ATTACKER_ID = "A"
DEFENDER_ID = "D"
PLANET_FIGHTERS = (0, 100, 1000, 10000)
PLANET_SHIELDS = (0, 10, 50, 200)
ATTACKER_FIGHTERS = (100, 1000, 10000)
DEFAULT_SEEDS = 30
DEFAULT_CITADEL_LEVEL = 2
DEFAULT_ATTACKER_SHIELDS = 0
REPEL_ERROR = "planetary defenses repelled landing"


@dataclass(frozen=True)
class SiegeCell:
    planet_fighters: int
    planet_shields: int
    attacker_fighters: int
    n: int
    captures: int
    repels: int
    attacker_destroyed: int
    other: int
    mean_fighters_left: float

    @property
    def capture_rate(self) -> float:
        return self.captures / self.n

    @property
    def repelled_rate(self) -> float:
        return self.repels / self.n

    @property
    def attacker_destroyed_rate(self) -> float:
        return self.attacker_destroyed / self.n


def build_lab_universe(seed: int = 1):
    """One small universe. Combat dice are reseeded per landing, not here."""
    universe = generate_universe(GameConfig(
        seed=seed,
        universe_size=50,
        max_days=3,
        enable_ferrengi=False,
        enable_planets=False,
        planet_spawn_probability=0,
    ))
    attacker = Player(id=ATTACKER_ID, name="Attacker", ship=Ship(), sector_id=1)
    defender = Player(id=DEFENDER_ID, name="Defender", ship=Ship(), sector_id=1)
    universe.players[ATTACKER_ID] = attacker
    universe.players[DEFENDER_ID] = defender
    universe.sectors[1].occupant_ids.extend([ATTACKER_ID, DEFENDER_ID])
    planet = plant_defender_planet(
        universe, owner_id=DEFENDER_ID, fighters=0, shields=0, citadel_level=DEFAULT_CITADEL_LEVEL,
    )
    return universe, attacker, planet


def plant_defender_planet(
    universe,
    *,
    owner_id: str,
    fighters: int,
    shields: int,
    citadel_level: int,
    reaction_pct: int = 0,
    quasar: bool = False,
) -> Planet:
    """Create the lab planet once. Later slices pass reaction_pct and quasar."""
    if PLANET_ID in universe.planets:
        planet = universe.planets[PLANET_ID]
    else:
        planet = Planet(
            id=PLANET_ID, sector_id=SECTOR_ID, name="LabHold", class_id=PlanetClass.M,
        )
        universe.planets[PLANET_ID] = planet
        universe.sectors[SECTOR_ID].planet_ids.append(PLANET_ID)
    configure_defender_planet(
        planet,
        owner_id=owner_id,
        fighters=fighters,
        shields=shields,
        citadel_level=citadel_level,
        reaction_pct=reaction_pct,
        quasar=quasar,
    )
    return planet


def configure_defender_planet(
    planet: Planet,
    *,
    owner_id: str,
    fighters: int,
    shields: int,
    citadel_level: int,
    reaction_pct: int = 0,
    quasar: bool = False,
) -> None:
    if quasar:
        raise NotImplementedError("quasar is a later slice")
    if reaction_pct < 0 or reaction_pct > 100:
        raise ValueError("reaction_pct must be from 0 to 100")
    planet.owner_id = owner_id
    planet.corp_ticker = None
    planet.fighters = fighters
    planet.shields = shields
    planet.citadel_level = citadel_level
    planet.citadel_target = citadel_level
    planet.citadel_complete_day = None
    planet.origin = "other"
    planet.military_reaction_pct = reaction_pct


def place_attacker(universe, attacker: Player, *, sector_id: int, fighters: int, shields: int) -> None:
    attacker.turns_today = 0
    attacker.planet_landed = None
    attacker.alive = True
    attacker.ship.fighters = fighters
    attacker.ship.shields = shields
    for sector in universe.sectors.values():
        while attacker.id in sector.occupant_ids:
            sector.occupant_ids.remove(attacker.id)
    attacker.sector_id = sector_id
    universe.sectors[sector_id].occupant_ids.append(attacker.id)


def land_on_planet(universe, attacker_id: str, planet_id: int, seed: int):
    # Combat reads universe.rng, which is backed by the private _rng.
    universe._rng = random.Random(seed)
    return apply_action(
        universe, attacker_id, Action(kind=ActionKind.LAND_PLANET, args={"planet_id": planet_id}),
    )


def run_landing(
    universe,
    attacker: Player,
    planet: Planet,
    *,
    seed: int,
    planet_fighters: int,
    planet_shields: int,
    attacker_fighters: int,
    attacker_shields: int = DEFAULT_ATTACKER_SHIELDS,
    citadel_level: int = DEFAULT_CITADEL_LEVEL,
    reaction_pct: int = 0,
    quasar: bool = False,
) -> tuple[str, int]:
    """Return (capture|repelled|attacker_destroyed|other, fighters left)."""
    configure_defender_planet(
        planet,
        owner_id=DEFENDER_ID,
        fighters=planet_fighters,
        shields=planet_shields,
        citadel_level=citadel_level,
        reaction_pct=reaction_pct,
        quasar=quasar,
    )
    place_attacker(
        universe, attacker, sector_id=SECTOR_ID, fighters=attacker_fighters, shields=attacker_shields,
    )
    deaths = attacker.deaths
    result = land_on_planet(universe, attacker.id, planet.id, seed)
    if attacker.deaths > deaths:
        return "attacker_destroyed", 0
    if planet.owner_id == attacker.id:
        return "capture", attacker.ship.fighters
    if (not result.ok) and result.error == REPEL_ERROR:
        return "repelled", attacker.ship.fighters
    return "other", attacker.ship.fighters


def run_grid(
    *,
    planet_fighters: tuple[int, ...] = PLANET_FIGHTERS,
    planet_shields: tuple[int, ...] = PLANET_SHIELDS,
    attacker_fighters: tuple[int, ...] = ATTACKER_FIGHTERS,
    seeds: int = DEFAULT_SEEDS,
    attacker_shields: int = DEFAULT_ATTACKER_SHIELDS,
    citadel_level: int = DEFAULT_CITADEL_LEVEL,
    reaction_pct: int = 0,
    quasar: bool = False,
) -> list[SiegeCell]:
    if seeds < 1:
        raise ValueError("seeds must be at least 1")
    universe, attacker, planet = build_lab_universe()
    cells: list[SiegeCell] = []
    for a_fighters in attacker_fighters:
        for p_fighters in planet_fighters:
            for p_shields in planet_shields:
                captures = repels = destroyed = other = 0
                left_sum = 0
                for seed in range(seeds):
                    outcome, left = run_landing(
                        universe, attacker, planet,
                        seed=seed,
                        planet_fighters=p_fighters,
                        planet_shields=p_shields,
                        attacker_fighters=a_fighters,
                        attacker_shields=attacker_shields,
                        citadel_level=citadel_level,
                        reaction_pct=reaction_pct,
                        quasar=quasar,
                    )
                    left_sum += left
                    if outcome == "capture":
                        captures += 1
                    elif outcome == "repelled":
                        repels += 1
                    elif outcome == "attacker_destroyed":
                        destroyed += 1
                    else:
                        other += 1
                cells.append(SiegeCell(
                    planet_fighters=p_fighters,
                    planet_shields=p_shields,
                    attacker_fighters=a_fighters,
                    n=seeds,
                    captures=captures,
                    repels=repels,
                    attacker_destroyed=destroyed,
                    other=other,
                    mean_fighters_left=left_sum / seeds,
                ))
    return cells


def format_markdown(cells: list[SiegeCell], *, seeds: int, citadel_level: int, attacker_shields: int) -> str:
    lines = [
        f"Citadel level {citadel_level}. Attacker shields {attacker_shields}. "
        f"{seeds} seeds per cell (combat dice reseeded 0..{seeds - 1}).",
        "",
        "| Planet fighters | Planet shields | Attacker fighters | Capture | Repelled | Attacker destroyed | Mean fighters left |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cell in cells:
        lines.append(
            f"| {cell.planet_fighters} | {cell.planet_shields} | {cell.attacker_fighters} | "
            f"{cell.capture_rate * 100:.1f}% | {cell.repelled_rate * 100:.1f}% | "
            f"{cell.attacker_destroyed_rate * 100:.1f}% | {cell.mean_fighters_left:.1f} |"
        )
    return "\n".join(lines)


def format_csv(cells: list[SiegeCell]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([
        "planet_fighters", "planet_shields", "attacker_fighters", "n",
        "capture_rate", "repelled_rate", "attacker_destroyed_rate", "mean_attacker_fighters_left",
    ])
    for cell in cells:
        writer.writerow([
            cell.planet_fighters, cell.planet_shields, cell.attacker_fighters, cell.n,
            f"{cell.capture_rate:.4f}", f"{cell.repelled_rate:.4f}",
            f"{cell.attacker_destroyed_rate:.4f}", f"{cell.mean_fighters_left:.2f}",
        ])
    return buf.getvalue()


def _ints(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split(",") if part.strip() != "")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Planet siege scenario lab")
    parser.add_argument("--csv", action="store_true", help="print CSV instead of a markdown table")
    parser.add_argument("--seeds", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--planet-fighters", type=_ints, default=PLANET_FIGHTERS)
    parser.add_argument("--planet-shields", type=_ints, default=PLANET_SHIELDS)
    parser.add_argument("--attacker-fighters", type=_ints, default=ATTACKER_FIGHTERS)
    parser.add_argument("--attacker-shields", type=int, default=DEFAULT_ATTACKER_SHIELDS)
    parser.add_argument("--citadel-level", type=int, default=DEFAULT_CITADEL_LEVEL)
    args = parser.parse_args(argv)
    cells = run_grid(
        planet_fighters=args.planet_fighters,
        planet_shields=args.planet_shields,
        attacker_fighters=args.attacker_fighters,
        seeds=args.seeds,
        attacker_shields=args.attacker_shields,
        citadel_level=args.citadel_level,
    )
    if args.csv:
        sys.stdout.write(format_csv(cells))
    else:
        print(format_markdown(
            cells, seeds=args.seeds, citadel_level=args.citadel_level, attacker_shields=args.attacker_shields,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
