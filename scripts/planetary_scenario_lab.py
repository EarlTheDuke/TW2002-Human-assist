"""Headless planet-siege grid. No server, no paid call, not collected by pytest.

Each cell reseeds the combat dice, plants one defended planet, and calls
apply_action land_planet. reaction_pct is written onto the planet.
--quasar prints a short sector-quasar warp table.
--gift prints citadel completion with the gift constants at 0.
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
from tw2k.engine.models import (
    Alliance,
    Commodity,
    Corporation,
    EventKind,
    FighterDeployment,
    FighterMode,
    MineDeployment,
    MineType,
    Planet,
    PlanetClass,
    Player,
    Ship,
)
from tw2k.engine.observation import event_facts
from tw2k.engine.planets import _complete_citadels

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
    quasar_sector_pct: int = 0,
    quasar_atm_pct: int = 0,
    fuel_ore: int = 0,
) -> None:
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
    planet.quasar_sector_pct = 10 if quasar and quasar_sector_pct <= 0 else quasar_sector_pct
    planet.quasar_atm_pct = quasar_atm_pct
    planet.stockpile[Commodity.FUEL_ORE] = fuel_ore


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
    mines: int = 0,
    sector_fighters: int = 0,
) -> tuple[str, int]:
    """Return (capture|repelled|attacker_destroyed|other, fighters left)."""
    sector = universe.sectors[SECTOR_ID]
    sector.mines.clear()
    sector.fighters = None
    if mines > 0:
        sector.mines.append(MineDeployment(owner_id=DEFENDER_ID, kind=MineType.ARMID, count=mines))
    if sector_fighters > 0:
        sector.fighters = FighterDeployment(
            owner_id=DEFENDER_ID, count=sector_fighters, mode=FighterMode.OFFENSIVE,
        )
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
    mines: int = 0,
    sector_fighters: int = 0,
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
                        mines=mines,
                        sector_fighters=sector_fighters,
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


def format_hazard_table(*, seeds: int = 30) -> str:
    """Short grid: clear sector, 10 armids, and 100 offensive sector fighters."""
    rows = (
        (100, 0, 0),
        (100, 100, 0),
        (1000, 0, 0),
        (1000, 100, 0),
    )
    lines = [
        "Citadel level 2. Attacker shields 0. Reaction 0. "
        f"{seeds} seeds. Mines are armids owned by the planet owner. "
        "Sector fighters are offensive and owned by the planet owner.",
        "",
        "| Attacker | Planet fighters | Planet shields | Clear capture | 10 mines capture | 100 sector fighters capture |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for attacker_f, planet_f, planet_s in rows:
        rates = []
        for mines, sector_f in ((0, 0), (10, 0), (0, 100)):
            cell = run_grid(
                planet_fighters=(planet_f,),
                planet_shields=(planet_s,),
                attacker_fighters=(attacker_f,),
                seeds=seeds,
                mines=mines,
                sector_fighters=sector_f,
            )[0]
            rates.append(f"{cell.capture_rate * 100:.1f}%")
        lines.append(
            f"| {attacker_f} | {planet_f} | {planet_s} | {rates[0]} | {rates[1]} | {rates[2]} |"
        )
    return "\n".join(lines)


def format_production_table() -> str:
    """Fighters per day for 1000 and 10000 colonists, one product pool at a time."""
    from tw2k.engine.planets import fighters_from_colonists

    counts = (1000, 10000)
    lines = [
        "Fighters per day from one product pool. Rate 100. Divisor 0 stays 0. "
        "Class U makes stock and no fighters. Cap is 1,000,000.",
        "",
        "| Class | Pool | 1000 colonists | 10000 colonists |",
        "|---|---|---:|---:|",
    ]
    for class_id in ("M", "K", "O", "L", "C", "H", "U"):
        for pool in ("fuel_ore", "organics", "equipment"):
            made = [fighters_from_colonists(class_id, {pool: count}) for count in counts]
            lines.append(f"| {class_id} | {pool} | {made[0]} | {made[1]} |")
    return "\n".join(lines)


def format_quasar_table() -> str:
    """One hostile warp per row. Percent is 0-100. Damage is burned fuel // 3."""
    universe, attacker, planet = build_lab_universe()
    origin = 1
    if SECTOR_ID not in universe.sectors[origin].warps:
        universe.sectors[origin].warps.append(SECTOR_ID)
    if origin not in universe.sectors[SECTOR_ID].warps:
        universe.sectors[SECTOR_ID].warps.append(origin)
    rows = (
        ("10% of 10000", 3, 10, 10000, 0, 1000),
        ("second shot", 3, 10, 9000, 0, 667),
        ("level 2", 2, 10, 10000, 0, 1000),
        ("pct 0", 3, 0, 10000, 0, 1000),
        ("no fuel", 3, 10, 0, 0, 1000),
        ("shields first", 3, 10, 10000, 100, 500),
    )
    lines = [
        "Sector quasar on a hostile warp. pct is 0-100. "
        "Burned fuel is fuel * pct // 100. Damage is that fuel // 3. "
        "Shields soak first, then fighters.",
        "",
        "| Case | Level | Pct | Fuel before | Shields | Fighters before | Damage | Fuel after | Fighters after | Shields after |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, level, pct, fuel, shields, fighters in rows:
        configure_defender_planet(
            planet, owner_id=DEFENDER_ID, fighters=0, shields=0, citadel_level=level,
            quasar_sector_pct=pct, fuel_ore=fuel,
        )
        place_attacker(universe, attacker, sector_id=origin, fighters=fighters, shields=shields)
        attacker.deaths = 0
        apply_action(universe, attacker.id, Action(kind=ActionKind.WARP, args={"target": SECTOR_ID}))
        fired = [ev for ev in universe.events if ev.kind.value == "quasar_fire"]
        damage = fired[-1].payload["damage"] if fired else 0
        universe.events.clear()
        lines.append(
            f"| {label} | {level} | {pct} | {fuel} | {shields} | {fighters} | {damage} | "
            f"{int(planet.stockpile.get(Commodity.FUEL_ORE, 0))} | {attacker.ship.fighters} | {attacker.ship.shields} |"
        )
    return "\n".join(lines)


def format_atmosphere_table() -> str:
    """Hostile landings. Damage is burned fuel times 2. Shields soak the ship first."""
    universe, attacker, planet = build_lab_universe()
    sector = universe.sectors[SECTOR_ID]
    rows = (
        ("both shots, shields already down", 0, 0, 10_000, 0),
        ("shields hold, one shot", 0, 500, 10, 8_000),
        ("first shot kills", 0, 0, 100, 0),
    )
    lines = [
        "Atmospheric quasar on a hostile landing. pct 10, citadel 3, fuel 10,000. "
        "Burned fuel is fuel * pct // 100. Damage is that fuel times 2. "
        "The second shot waits until planet shields are already down or fall.",
        "",
        "| Case | Planet shields | Ship fighters | Ship shields | Shots | Damage | Fuel after | Died |",
        "|---|---:|---:|---:|---:|---|---:|---|",
    ]
    for label, planet_f, planet_s, ship_f, ship_s in rows:
        sector.mines.clear()
        sector.fighters = None
        configure_defender_planet(
            planet, owner_id=DEFENDER_ID, fighters=planet_f, shields=planet_s,
            citadel_level=3, quasar_atm_pct=10, fuel_ore=10_000,
        )
        place_attacker(universe, attacker, sector_id=SECTOR_ID, fighters=ship_f, shields=ship_s)
        attacker.deaths = 0
        universe.events.clear()
        land_on_planet(universe, attacker.id, planet.id, seed=1)
        shots = [ev for ev in universe.events if ev.kind.value == "quasar_fire"]
        damage = ", ".join(str(ev.payload["damage"]) for ev in shots) or "0"
        died = "yes" if attacker.deaths else "no"
        lines.append(
            f"| {label} | {planet_s} | {ship_f} | {ship_s} | {len(shots)} | {damage} | "
            f"{int(planet.stockpile.get(Commodity.FUEL_ORE, 0))} | {died} |"
        )
    return "\n".join(lines)


def format_photon_table() -> str:
    """Photon damp skips a vulnerable planet's sector cannon for one warp-in."""
    universe, attacker, planet = build_lab_universe()
    origin = 1
    defender = universe.players[DEFENDER_ID]
    if SECTOR_ID not in universe.sectors[origin].warps:
        universe.sectors[origin].warps.append(SECTOR_ID)
    if origin not in universe.sectors[SECTOR_ID].warps:
        universe.sectors[SECTOR_ID].warps.append(origin)
    rows = (
        ("no photon", 3, 0, False),
        ("photon, citadel 3", 3, 0, True),
        ("L5 with 200 shields", 5, 200, True),
        ("L5 with 199 shields", 5, 199, True),
        ("L4 with 200 shields", 4, 200, True),
    )
    lines = [
        "Photon damp on one hostile warp. Fuel 10,000 at 10 percent. "
        "Damage is burned fuel // 3 when the cannon fires. "
        "L5 with 200 shields ignores the photon. Below L5 or below 200 shields is damped.",
        "",
        "| Case | Level | Planet shields | Photon | Damped | Sector damage | Fuel after |",
        "|---|---:|---:|---|---|---:|---:|",
    ]
    for label, level, shields, photon in rows:
        universe.sectors[SECTOR_ID].mines.clear()
        universe.sectors[SECTOR_ID].fighters = None
        configure_defender_planet(
            planet, owner_id=DEFENDER_ID, fighters=0, shields=shields,
            citadel_level=level, quasar_sector_pct=10, fuel_ore=10_000,
        )
        place_attacker(universe, attacker, sector_id=SECTOR_ID, fighters=2000, shields=0)
        attacker.photon_damped_sector_id = None
        attacker.deaths = 0
        defender.ship.photon_missiles = 1
        defender.turns_today = 0
        defender.sector_id = SECTOR_ID
        if DEFENDER_ID not in universe.sectors[SECTOR_ID].occupant_ids:
            universe.sectors[SECTOR_ID].occupant_ids.append(DEFENDER_ID)
        universe.events.clear()
        if photon:
            apply_action(
                universe, DEFENDER_ID,
                Action(kind=ActionKind.PHOTON_MISSILE, args={"target": ATTACKER_ID}),
            )
        damped = any(ev.kind.value == "quasar_damped" for ev in universe.events)
        place_attacker(universe, attacker, sector_id=origin, fighters=2000, shields=0)
        universe.events.clear()
        apply_action(universe, attacker.id, Action(kind=ActionKind.WARP, args={"target": SECTOR_ID}))
        fired = [ev for ev in universe.events if ev.kind.value == "quasar_fire"]
        damage = fired[-1].payload["damage"] if fired else 0
        lines.append(
            f"| {label} | {level} | {shields} | {'yes' if photon else 'no'} | "
            f"{'yes' if damped else 'no'} | {damage} | "
            f"{int(planet.stockpile.get(Commodity.FUEL_ORE, 0))} |"
        )
    return "\n".join(lines)


def format_interdict_table() -> str:
    """One attempted warp out. 500 fuel holds. The cannon uses the fuel left."""
    universe, attacker, planet = build_lab_universe()
    origin = 1
    if SECTOR_ID not in universe.sectors[origin].warps:
        universe.sectors[origin].warps.append(SECTOR_ID)
    if origin not in universe.sectors[SECTOR_ID].warps:
        universe.sectors[SECTOR_ID].warps.append(origin)
    rows = (
        ("500 fuel", 6, 500, 10),
        ("10000 fuel", 6, 10_000, 10),
        ("499 fuel", 6, 499, 10),
        ("level 5", 5, 10_000, 10),
    )
    lines = [
        "Interdictor on a hostile warp out. Citadel level 6 burns 500 fuel and holds the ship. "
        "The sector cannon then uses the fuel that remains. Below 500 fuel the warp leaves.",
        "",
        "| Case | Level | Fuel before | Held | Sector after | Damage | Fuel after |",
        "|---|---:|---:|---|---:|---:|---:|",
    ]
    for label, level, fuel, pct in rows:
        universe.sectors[SECTOR_ID].mines.clear()
        universe.sectors[SECTOR_ID].fighters = None
        configure_defender_planet(
            planet, owner_id=DEFENDER_ID, fighters=0, shields=0,
            citadel_level=level, quasar_sector_pct=pct, fuel_ore=fuel,
        )
        place_attacker(universe, attacker, sector_id=SECTOR_ID, fighters=2000, shields=0)
        attacker.deaths = 0
        universe.events.clear()
        apply_action(universe, attacker.id, Action(kind=ActionKind.WARP, args={"target": origin}))
        held = any(ev.kind.value == "interdict" for ev in universe.events)
        fired = [ev for ev in universe.events if ev.kind.value == "quasar_fire"]
        damage = fired[-1].payload["damage"] if fired else 0
        lines.append(
            f"| {label} | {level} | {fuel} | {'yes' if held else 'no'} | {attacker.sector_id} | "
            f"{damage} | {int(planet.stockpile.get(Commodity.FUEL_ORE, 0))} |"
        )
    return "\n".join(lines)


def format_transwarp_table() -> str:
    """Path length 2 costs 800 fuel. Short fuel and a missing fighter do not move."""
    universe, attacker, planet = build_lab_universe()
    mid = 41
    dest = 42
    universe.sectors[SECTOR_ID].warps = [mid]
    universe.sectors[mid].warps = [SECTOR_ID, dest]
    universe.sectors[dest].warps = [mid]
    rows = (
        ("2 hops, 1000 fuel", 4, 1000, True),
        ("2 hops, 799 fuel", 4, 799, True),
        ("no fighter at dest", 4, 1000, False),
        ("level 3", 3, 1000, True),
    )
    lines = [
        "Planet TransWarp. Distance is the warp path length. Fuel is 400 per sector. "
        "The destination needs a fighter of the owner. One move per day.",
        "",
        "| Case | Level | Fuel before | Fighter | Moved | Sector after | Fuel after |",
        "|---|---:|---:|---|---|---:|---:|",
    ]
    for label, level, fuel, fighters in rows:
        configure_defender_planet(
            planet, owner_id=ATTACKER_ID, fighters=0, shields=0,
            citadel_level=level, fuel_ore=fuel,
        )
        planet.sector_id = SECTOR_ID
        planet.last_transwarp_day = None
        if planet.id not in universe.sectors[SECTOR_ID].planet_ids:
            universe.sectors[SECTOR_ID].planet_ids.append(planet.id)
        universe.sectors[dest].planet_ids = [
            item for item in universe.sectors[dest].planet_ids if item != planet.id
        ]
        universe.sectors[dest].fighters = (
            FighterDeployment(owner_id=ATTACKER_ID, count=5, mode=FighterMode.DEFENSIVE)
            if fighters else None
        )
        place_attacker(universe, attacker, sector_id=SECTOR_ID, fighters=10, shields=0)
        attacker.planet_landed = planet.id
        universe.events.clear()
        apply_action(
            universe, attacker.id,
            Action(kind=ActionKind.PLANET_TRANSWARP, args={"planet_id": planet.id, "dest_sector": dest}),
        )
        lines.append(
            f"| {label} | {level} | {fuel} | {'yes' if fighters else 'no'} | "
            f"{'yes' if planet.sector_id == dest else 'no'} | {planet.sector_id} | "
            f"{int(planet.stockpile.get(Commodity.FUEL_ORE, 0))} |"
        )
    return "\n".join(lines)


def format_transporter_table() -> str:
    """One hop is 50000 credits and 10 fuel. Two hops add 25000 credits and 10 fuel."""
    universe, attacker, planet = build_lab_universe()
    mid = 41
    dest = 42
    universe.sectors[SECTOR_ID].warps = [mid]
    universe.sectors[mid].warps = [SECTOR_ID, dest]
    universe.sectors[dest].warps = [mid]
    rows = (
        ("buy", "buy", 0, 60_000, 0),
        ("1 hop", "hop", mid, 80_000, 100),
        ("2 hops", "hop", dest, 80_000, 100),
        ("short credits", "hop", mid, 40_000, 100),
        ("short fuel", "hop", mid, 80_000, 9),
    )
    lines = [
        "Planet Transporter. The player moves. The planet stays. "
        "The first hop is 50000 credits. Each extra hop is 25000. The planet pays 10 fuel per sector. "
        "A failed hop spends nothing.",
        "",
        "| Case | Credits before | Fuel before | Ok | Credits after | Fuel after | Sector |",
        "|---|---:|---:|---|---:|---:|---:|",
    ]
    for label, kind, target, credits, fuel in rows:
        configure_defender_planet(
            planet, owner_id=ATTACKER_ID, fighters=0, shields=0,
            citadel_level=1, fuel_ore=fuel,
        )
        planet.sector_id = SECTOR_ID
        planet.has_transporter = kind == "hop"
        if planet.id not in universe.sectors[SECTOR_ID].planet_ids:
            universe.sectors[SECTOR_ID].planet_ids.append(planet.id)
        universe.sectors[mid].fighters = FighterDeployment(
            owner_id=ATTACKER_ID, count=4, mode=FighterMode.DEFENSIVE,
        )
        universe.sectors[dest].fighters = FighterDeployment(
            owner_id=ATTACKER_ID, count=4, mode=FighterMode.DEFENSIVE,
        )
        place_attacker(universe, attacker, sector_id=SECTOR_ID, fighters=10, shields=0)
        attacker.planet_landed = planet.id
        attacker.credits = credits
        if kind == "buy":
            action = Action(kind=ActionKind.PLANET_BUY_TRANSPORTER, args={"planet_id": planet.id})
        else:
            action = Action(
                kind=ActionKind.PLANET_TRANSPORT,
                args={"planet_id": planet.id, "dest_sector": target},
            )
        res = apply_action(universe, attacker.id, action)
        lines.append(
            f"| {label} | {credits} | {fuel} | {'yes' if res.ok else 'no'} | {attacker.credits} | "
            f"{int(planet.stockpile.get(Commodity.FUEL_ORE, 0))} | {attacker.sector_id} |"
        )
    return "\n".join(lines)


def format_gift_table() -> str:
    """Completing L2-L6 with the gift constants at 0."""
    rows = [(level, 0, 0) for level in range(2, 7)]
    rows.append((3, 4000, 800))
    lines = [
        "Citadel completion. Gift constants are 0, so fighters and shields stay put.",
        "",
        "| Completed | Fighters before | Shields before | Fighters after | Shields after | Facts |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for level, fighters, shields in rows:
        universe, _attacker, planet = build_lab_universe()
        planet.fighters = fighters
        planet.shields = shields
        planet.citadel_level = level - 1
        planet.citadel_target = level
        planet.citadel_complete_day = universe.day
        universe.events.clear()
        _complete_citadels(universe)
        done = next(event for event in universe.events if event.kind is EventKind.CITADEL_COMPLETE)
        facts = ",".join(event_facts(done))
        lines.append(
            f"| {level} | {fighters} | {shields} | {planet.fighters} | {planet.shields} | {facts} |"
        )
    return "\n".join(lines)


def format_destroy_table() -> str:
    """Two destroy steps, then a defended planet and a corp planet that stay."""
    rows = []

    def once(label: str, *, fighters: int, shields: int, friendly: bool, steps: int) -> None:
        universe, attacker, planet = build_lab_universe()
        planet.fighters = fighters
        planet.shields = shields
        planet.colonists[Commodity.COLONISTS] = 12
        planet.treasury = 400
        if friendly:
            attacker.corp_ticker = "ZZ"
            universe.players[DEFENDER_ID].corp_ticker = "ZZ"
            planet.corp_ticker = "ZZ"
        place_attacker(universe, attacker, sector_id=SECTOR_ID, fighters=0, shields=0)
        attacker.planet_landed = planet.id
        align = attacker.alignment
        for step in range(steps):
            before = planet.id in universe.planets
            res = apply_action(
                universe, ATTACKER_ID,
                Action(kind=ActionKind.PLANET_DESTROY, args={"planet_id": planet.id}),
            )
            exists = planet.id in universe.planets
            colonists = sum(planet.colonists.values()) if exists else 0
            name = label if steps == 1 else f"{label} {step + 1}"
            ok = "yes" if res.ok else "no"
            had = "yes" if before else "no"
            left = "yes" if exists else "no"
            rows.append(
                f"| {name} | {ok} | {had} | {left} | {colonists} | "
                f"{attacker.alignment - align} | {attacker.sector_id} |"
            )
            if not res.ok:
                break

    once("kill", fighters=0, shields=0, friendly=False, steps=1)
    once("remove", fighters=0, shields=0, friendly=False, steps=2)
    once("defended", fighters=8, shields=0, friendly=False, steps=1)
    once("corp", fighters=0, shields=0, friendly=True, steps=1)
    lines = [
        "Planet destroy. The live siege grid does not call this action.",
        "",
        "| Step | Ok | Planet before | Planet after | Colonists | Alignment | Sector |",
        "|---|---|---|---|---:|---:|---:|",
        *rows,
    ]
    return "\n".join(lines)


def format_corp_table() -> str:
    """Leave, disband, and an allied landing. The siege grid does not call these."""
    rows: list[str] = []

    def blank():
        universe, attacker, planet = build_lab_universe()
        defender = universe.players[DEFENDER_ID]
        return universe, attacker, defender, planet

    universe, attacker, defender, planet = blank()
    universe.corporations["ZZ"] = Corporation(
        ticker="ZZ", name="ZZ", ceo_id=ATTACKER_ID, member_ids=[ATTACKER_ID, DEFENDER_ID],
    )
    attacker.corp_ticker = "ZZ"
    defender.corp_ticker = "ZZ"
    planet.corp_ticker = "ZZ"
    planet.owner_id = DEFENDER_ID
    planet.has_transporter = True
    planet.citadel_level = 4
    planet.stockpile[Commodity.FUEL_ORE] = 8000
    place_attacker(universe, attacker, sector_id=SECTOR_ID, fighters=0, shields=0)
    attacker.planet_landed = planet.id
    apply_action(universe, ATTACKER_ID, Action(kind=ActionKind.CORP_LEAVE, args={}))
    for kind, args in (
        (ActionKind.PLANET_TRANSWARP, {"planet_id": planet.id, "dest_sector": 41}),
        (ActionKind.PLANET_TRANSPORT, {"planet_id": planet.id, "dest_sector": 41}),
        (ActionKind.DEPOSIT_TREASURY, {"planet_id": planet.id, "amount": 100}),
    ):
        res = apply_action(universe, ATTACKER_ID, Action(kind=kind, args=args))
        rows.append(
            f"| leave {kind.value} | {planet.owner_id} | {planet.corp_ticker} | "
            f"{'yes' if res.ok else 'no'} | {res.turns_spent} | 0 |"
        )

    universe, attacker, defender, planet = blank()
    universe.corporations["ZZ"] = Corporation(
        ticker="ZZ", name="ZZ", ceo_id=ATTACKER_ID, member_ids=[ATTACKER_ID],
    )
    attacker.corp_ticker = "ZZ"
    planet.owner_id = ATTACKER_ID
    planet.corp_ticker = "ZZ"
    apply_action(universe, ATTACKER_ID, Action(kind=ActionKind.CORP_LEAVE, args={}))
    orphans = sum(1 for ev in universe.events if ev.kind is EventKind.PLANET_ORPHANED)
    ticker = planet.corp_ticker or "none"
    rows.append(f"| disband live | {planet.owner_id} | {ticker} |  |  | {orphans} |")

    universe, attacker, defender, planet = blank()
    universe.corporations["ZZ"] = Corporation(
        ticker="ZZ", name="ZZ", ceo_id=ATTACKER_ID, member_ids=[ATTACKER_ID],
    )
    attacker.corp_ticker = "ZZ"
    defender.alive = False
    planet.owner_id = DEFENDER_ID
    planet.corp_ticker = "ZZ"
    universe.events.clear()
    apply_action(universe, ATTACKER_ID, Action(kind=ActionKind.CORP_LEAVE, args={}))
    orphans = sum(1 for ev in universe.events if ev.kind is EventKind.PLANET_ORPHANED)
    owner = planet.owner_id or "none"
    ticker = planet.corp_ticker or "none"
    rows.append(f"| disband dead | {owner} | {ticker} |  |  | {orphans} |")

    universe, attacker, defender, planet = blank()
    ally = Alliance(
        id="A1", member_ids=[ATTACKER_ID, DEFENDER_ID], proposed_by=DEFENDER_ID,
        formed_day=universe.day, active=True,
    )
    universe.alliances["A1"] = ally
    attacker.alliances.append("A1")
    defender.alliances.append("A1")
    planet.owner_id = DEFENDER_ID
    planet.shields = 8
    planet.fighters = 0
    planet.citadel_level = 1
    universe.sectors[SECTOR_ID].fighters = None
    universe.sectors[SECTOR_ID].mines.clear()
    place_attacker(universe, attacker, sector_id=SECTOR_ID, fighters=0, shields=0)
    res = land_on_planet(universe, ATTACKER_ID, planet.id, seed=1)
    rows.append(
        f"| ally land | {planet.owner_id} | none | {'yes' if res.ok else 'no'} | "
        f"{res.turns_spent} | 0 |"
    )
    lines = [
        "Corp planets. The live siege grid does not call corp_leave.",
        "",
        "| Case | Owner | Ticker | Ok | Turns | Orphans |",
        "|---|---|---|---|---:|---:|",
        *rows,
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Planet siege scenario lab")
    parser.add_argument("--csv", action="store_true", help="print CSV instead of a markdown table")
    parser.add_argument("--production", action="store_true", help="print the fighter production table")
    parser.add_argument("--hazards", action="store_true", help="print the sector-hazard landing table")
    parser.add_argument("--quasar", action="store_true", help="print the sector quasar warp table")
    parser.add_argument("--atmosphere", action="store_true", help="print the atmospheric quasar landing table")
    parser.add_argument("--photon", action="store_true", help="print the photon damp warp table")
    parser.add_argument("--interdict", action="store_true", help="print the interdictor warp table")
    parser.add_argument("--transwarp", action="store_true", help="print the planet transwarp table")
    parser.add_argument("--transporter", action="store_true", help="print the planet transporter table")
    parser.add_argument("--gift", action="store_true", help="print the citadel completion gift table")
    parser.add_argument("--destroy", action="store_true", help="print the planet destruction table")
    parser.add_argument("--corp", action="store_true", help="print the corp planet table")
    parser.add_argument("--seeds", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--planet-fighters", type=_ints, default=PLANET_FIGHTERS)
    parser.add_argument("--planet-shields", type=_ints, default=PLANET_SHIELDS)
    parser.add_argument("--attacker-fighters", type=_ints, default=ATTACKER_FIGHTERS)
    parser.add_argument("--attacker-shields", type=int, default=DEFAULT_ATTACKER_SHIELDS)
    parser.add_argument("--citadel-level", type=int, default=DEFAULT_CITADEL_LEVEL)
    args = parser.parse_args(argv)
    if args.production:
        print(format_production_table())
        return 0
    if args.hazards:
        print(format_hazard_table(seeds=args.seeds))
        return 0
    if args.quasar:
        print(format_quasar_table())
        return 0
    if args.atmosphere:
        print(format_atmosphere_table())
        return 0
    if args.photon:
        print(format_photon_table())
        return 0
    if args.interdict:
        print(format_interdict_table())
        return 0
    if args.transwarp:
        print(format_transwarp_table())
        return 0
    if args.transporter:
        print(format_transporter_table())
        return 0
    if args.gift:
        print(format_gift_table())
        return 0
    if args.destroy:
        print(format_destroy_table())
        return 0
    if args.corp:
        print(format_corp_table())
        return 0
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
