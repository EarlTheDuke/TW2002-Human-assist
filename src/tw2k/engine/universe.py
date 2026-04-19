"""Universe generation — builds a connected sector graph, places ports and planets.

Deterministic given the config.seed. Produces a Universe with sectors, warps,
ports, planets, and pre-computed 2D layout coordinates for the map view.
"""

from __future__ import annotations

import math
import random

from . import constants as K
from .models import (
    Commodity,
    GameConfig,
    Planet,
    PlanetClass,
    Port,
    PortClass,
    PortStock,
    Sector,
    Universe,
)

# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def _build_connected_graph(rng: random.Random, n: int, avg_warps: float) -> dict[int, set[int]]:
    """Build a connected directed graph over sector IDs 1..n."""
    # Start with a random spanning tree rooted at sector 1.
    order = list(range(2, n + 1))
    rng.shuffle(order)

    # adjacency as undirected pairs first
    edges: set[tuple[int, int]] = set()
    available = [1]
    for sid in order:
        parent = rng.choice(available)
        a, b = sorted((sid, parent))
        edges.add((a, b))
        available.append(sid)

    # Target number of undirected edges
    target_edges = int(n * avg_warps / 2)
    tries = 0
    while len(edges) < target_edges and tries < target_edges * 10:
        a = rng.randint(1, n)
        b = rng.randint(1, n)
        if a == b:
            tries += 1
            continue
        pair = tuple(sorted((a, b)))
        if pair in edges:
            tries += 1
            continue
        edges.add(pair)  # type: ignore[arg-type]
        tries += 1

    adj: dict[int, set[int]] = {i: set() for i in range(1, n + 1)}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)

    return adj


def _one_way_some_edges(
    rng: random.Random, adj: dict[int, set[int]], fraction: float
) -> dict[int, set[int]]:
    """Convert a fraction of undirected edges to one-way, preserving global reachability from sector 1.

    Guarantees in addition to "sec 1 reaches everyone":
      - Every sector keeps ≥1 outbound warp (no dead-ends). A previous bug let a
        sector lose its sole outbound edge, stranding any player who spawned
        there (observed: Blake trapped 30 days in sector 3 with warps_out=[]).
      - FedSpace-internal edges (both endpoints in sectors 1..10) are never
        converted to one-way — FedSpace is meant to be a safe, fully-traversable
        hub where players can always return to StarDock.
      - FedSpace → deep-space edges also preserve the outbound direction from
        the FedSpace side (a player landing in FedSpace must be able to leave).
    """
    # Collect unique pairs
    pairs: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for a, neigh in adj.items():
        for b in neigh:
            p = tuple(sorted((a, b)))
            if p not in seen:
                seen.add(p)
                pairs.append(p)  # type: ignore[arg-type]

    rng.shuffle(pairs)
    target = int(len(pairs) * fraction)
    converted = 0

    for a, b in pairs:
        if converted >= target:
            break

        a_fed = a in K.FEDSPACE_SECTORS
        b_fed = b in K.FEDSPACE_SECTORS
        # Rule 1: FedSpace-internal edges stay bidirectional.
        if a_fed and b_fed:
            continue

        # Randomly pick which direction survives
        if rng.random() < 0.5:
            keep_from, keep_to = a, b
        else:
            keep_from, keep_to = b, a

        # Rule 2: if the losing side is a FedSpace sector, force the keep
        # direction to flow FedSpace → deep (so FedSpace retains the
        # outbound link and returning players can depart again).
        if keep_to in K.FEDSPACE_SECTORS and keep_from not in K.FEDSPACE_SECTORS:
            keep_from, keep_to = keep_to, keep_from

        adj[keep_to].discard(keep_from)

        # Rule 3: never leave ANY sector with zero outbound warps.
        if len(adj[keep_to]) == 0:
            adj[keep_to].add(keep_from)  # revert
            continue

        # Verify sector 1 still reaches everyone. If not, revert.
        if not _all_reachable_from(adj, 1, len(adj)):
            adj[keep_to].add(keep_from)  # revert
        else:
            converted += 1

    return adj


def _all_reachable_from(adj: dict[int, set[int]], start: int, n: int) -> bool:
    """BFS — are all n sectors reachable following directed edges from `start`?"""
    stack = [start]
    seen = {start}
    while stack:
        cur = stack.pop()
        for nxt in adj[cur]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return len(seen) == n


# ---------------------------------------------------------------------------
# Ports
# ---------------------------------------------------------------------------


def _make_port(rng: random.Random, class_id: PortClass, sector_id: int) -> Port:
    stock: dict[Commodity, PortStock] = {}
    mapping = {
        0: Commodity.FUEL_ORE,
        1: Commodity.ORGANICS,
        2: Commodity.EQUIPMENT,
    }
    trades = K.PORT_CLASS_TRADES[int(class_id)]
    for idx, deal in enumerate(trades):
        if deal is None:
            continue
        commodity = mapping[idx]
        maximum = K.PORT_DEFAULT_MAX_STOCK + rng.randint(-500, 1500)
        current = int(maximum * rng.uniform(0.35, 0.95))
        stock[commodity] = PortStock(current=current, maximum=maximum)

    name = _port_name(rng, sector_id)
    return Port(class_id=class_id, stock=stock, name=name)


def _port_name(rng: random.Random, sector_id: int) -> str:
    prefix = rng.choice([
        "Terra", "Andros", "Deneb", "Rigel", "Vega", "Orion", "Sol", "Alpha",
        "Beta", "Ceti", "Altair", "Polaris", "Cygnus", "Nova", "Hydra",
        "Kestrel", "Proxima", "Luyten", "Wolf", "Ross", "Kepler",
    ])
    return f"{prefix}-{sector_id}"


def _pick_port_class(rng: random.Random) -> PortClass:
    weights = K.PORT_CLASS_WEIGHTS
    roll = rng.random()
    cum = 0.0
    for class_num, w in weights.items():
        cum += w
        if roll <= cum:
            return PortClass(class_num)
    return PortClass(1)


# ---------------------------------------------------------------------------
# Planets
# ---------------------------------------------------------------------------


def _planet_name(rng: random.Random, planet_id: int) -> str:
    roots = ["New", "Old", "Great", "Little", "Lost", "Upper", "Lower", "Mid",
             "Northern", "Southern", "Eastern", "Western", "Greater"]
    names = ["Eden", "Haven", "Terra", "Arcadia", "Kairos", "Helion", "Ember",
             "Crescent", "Serenity", "Zephyr", "Kronos", "Pyre", "Concord",
             "Athena", "Triton", "Valkyrie", "Odyssey", "Meridian", "Requiem",
             "Obsidian", "Lumen", "Aurora", "Cinder", "Nebula"]
    return f"{rng.choice(roots)} {rng.choice(names)} #{planet_id}"


# ---------------------------------------------------------------------------
# Layout (for the map view)
# ---------------------------------------------------------------------------


def _compute_layout(adj: dict[int, set[int]], n: int, rng: random.Random) -> dict[int, tuple[float, float]]:
    """Cheap force-directed layout. Pins sector 1 at center.

    Keeps it simple and fast; the UI can refine visually.
    """
    # Initialize on a spiral for a better starting configuration
    positions: dict[int, list[float]] = {}
    for i in range(1, n + 1):
        if i == 1:
            positions[i] = [0.0, 0.0]
            continue
        r = math.sqrt(i) * 14.0
        theta = i * 2.39996  # golden-angle spiral
        positions[i] = [r * math.cos(theta), r * math.sin(theta)]

    # Few rounds of force-directed relaxation (attraction-only; repulsion disabled
    # for n>>100 performance — grid-accelerated repulsion is a future optimization).
    k_attr = 0.02
    iterations = 60
    for _ in range(iterations):
        # Repulsion is expensive for n=1000; use neighbor-only approximation
        # plus a grid-based scheme would be ideal. For now, apply attraction only.
        for a, neigh in adj.items():
            for b in neigh:
                if b <= a:
                    continue
                dx = positions[b][0] - positions[a][0]
                dy = positions[b][1] - positions[a][1]
                dist = math.hypot(dx, dy) + 0.01
                # attract
                f = k_attr * (dist - 40.0)
                fx = f * dx / dist
                fy = f * dy / dist
                positions[a][0] += fx
                positions[a][1] += fy
                positions[b][0] -= fx
                positions[b][1] -= fy
        # gentle random jitter shrinking over time
        for i in range(2, n + 1):
            positions[i][0] += rng.uniform(-0.3, 0.3)
            positions[i][1] += rng.uniform(-0.3, 0.3)

    # Pin sector 1 at origin
    positions[1] = [0.0, 0.0]

    return {i: (positions[i][0], positions[i][1]) for i in range(1, n + 1)}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_universe(config: GameConfig) -> Universe:
    rng = random.Random(config.seed)
    n = config.universe_size

    adj = _build_connected_graph(rng, n, config.avg_warps)
    adj = _one_way_some_edges(rng, adj, config.one_way_fraction)
    layout = _compute_layout(adj, n, rng)

    sectors: dict[int, Sector] = {}
    for i in range(1, n + 1):
        warps_list = sorted(adj[i])
        x, y = layout[i]
        sectors[i] = Sector(id=i, warps=warps_list, x=x, y=y)

    # Place StarDock
    sectors[K.STARDOCK_SECTOR].port = Port(
        class_id=PortClass.STARDOCK,
        name="Sol-1 StarDock",
    )

    # Place Federal ports in FedSpace (excluding sector 1)
    for fed_sid in K.FEDSPACE_SECTORS:
        if fed_sid == K.STARDOCK_SECTOR:
            continue
        if rng.random() < 0.6:
            port = _make_port(rng, PortClass.FEDERAL, fed_sid)
            # Federal ports actually trade all three at fixed price — we model as class 7 (BBB) equivalent
            port = _make_port(rng, PortClass.CLASS_7_BBB, fed_sid)
            port.class_id = PortClass.FEDERAL
            sectors[fed_sid].port = port

    # Place random ports in non-FedSpace sectors
    for sid in range(max(K.FEDSPACE_SECTORS) + 1, n + 1):
        if rng.random() < K.PORT_SPAWN_PROBABILITY:
            cls = _pick_port_class(rng)
            sectors[sid].port = _make_port(rng, cls, sid)

    universe = Universe(config=config, sectors=sectors)

    # Seed planets (existing civilizations scattered through the galaxy)
    if config.enable_planets:
        _seed_planets(rng, universe)

    # Pre-seed Ferrengi raiders so the first day has genuine threat. Without
    # this the first Ferrengi don't appear until the end of day 1 (tick_day),
    # which historically gave agents a full safe day of grinding. Distributed
    # across deep space so they don't all cluster on one trade lane.
    if config.enable_ferrengi and K.FERRENGI_INITIAL_SPAWN > 0:
        _seed_initial_ferrengi(rng, universe)

    return universe


def _seed_initial_ferrengi(rng: random.Random, universe: Universe) -> None:
    from .models import FerrengiShip, ShipClass

    deep_start = max(K.FEDSPACE_SECTORS) + 1
    max_sid = universe.config.universe_size
    for i in range(K.FERRENGI_INITIAL_SPAWN):
        sid = rng.randint(deep_start, max_sid)
        aggr = rng.randint(2, K.FERRENGI_MAX_AGGRESSION)
        fid = f"ferr_d0_{i}_{sid}"
        ship = FerrengiShip(
            id=fid,
            name=f"Ferrengi Raider {fid[-4:].upper()}",
            sector_id=sid,
            aggression=aggr,
            fighters=100 + aggr * 300,
            shields=aggr * 50,
            ship_class=ShipClass.BATTLESHIP if aggr >= 8 else ShipClass.MISSILE_FRIGATE,
        )
        universe.ferrengi[fid] = ship


def _seed_planets(rng: random.Random, universe: Universe) -> None:
    n = universe.config.universe_size
    planet_id = 1
    for sid in range(max(K.FEDSPACE_SECTORS) + 1, n + 1):
        if rng.random() < universe.config.planet_spawn_probability:
            cls = rng.choice(list(PlanetClass))
            planet = Planet(
                id=planet_id,
                sector_id=sid,
                name=_planet_name(rng, planet_id),
                class_id=cls,
            )
            universe.planets[planet_id] = planet
            universe.sectors[sid].planet_ids.append(planet_id)
            planet_id += 1
    universe.next_planet_id = planet_id
