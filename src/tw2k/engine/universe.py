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
from .rob_steal import seed_port_credits

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
    rng: random.Random,
    adj: dict[int, set[int]],
    fraction: float,
    allow_traps: bool = False,
) -> dict[int, set[int]]:
    """Convert a fraction of undirected edges to one-way, preserving STRONG connectivity to sector 1.

    Guarantees in addition to "sec 1 reaches everyone":
      - Every sector keeps ≥1 outbound warp (no dead-ends). A previous bug let a
        sector lose its sole outbound edge, stranding any player who spawned
        there (observed: Blake trapped 30 days in sector 3 with warps_out=[]).
      - FedSpace-internal edges (both endpoints in sectors 1..10) are never
        converted to one-way — FedSpace is meant to be a safe, fully-traversable
        hub where players can always return to StarDock.
      - FedSpace → deep-space edges also preserve the outbound direction from
        the FedSpace side (a player landing in FedSpace must be able to leave).
      - **Every sector can also reach sector 1.** Without this, a 0.15 default
        seed (e.g. seed 42) produces ~17 "stardock-trap" sectors with no path
        back to sec 1 — e.g. the {406, 475} pocket where a single one-way
        `1 → 406` edge funnels players in but nothing leads out. Match data
        showed P2 (LocalQwenA) burning 1k+ LLM calls trying to escape sec 648
        because the map literally had no return path. Now any conversion that
        breaks reverse reachability is reverted.
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
    n = len(adj)

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
        # Live topology allows a dead end (in, no out). The revert stays on
        # the legacy path so the recorded graph does not move.
        if not allow_traps and len(adj[keep_to]) == 0:
            adj[keep_to].add(keep_from)  # revert
            continue

        # Rule 4: sector 1 must still reach everyone. Legacy also requires
        # every sector can reach sector 1. Live topology drops that second
        # check, so a one-way can be a trap.
        trapped = not _all_reachable_from(adj, 1, n)
        if not allow_traps:
            trapped = trapped or not _all_can_reach(adj, 1, n)
        if trapped:
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


def _all_can_reach(adj: dict[int, set[int]], target: int, n: int) -> bool:
    """BFS on the reverse graph — can all n sectors reach `target` via directed warps?"""
    rev: dict[int, list[int]] = {i: [] for i in range(1, n + 1)}
    for a, neigh in adj.items():
        for b in neigh:
            rev[b].append(a)
    stack = [target]
    seen = {target}
    while stack:
        cur = stack.pop()
        for nxt in rev[cur]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return len(seen) == n


# ---------------------------------------------------------------------------
# Ports
# ---------------------------------------------------------------------------


def _hidden_port_stats(seed: int, sector_id: int, commodity: Commodity, buys: bool) -> tuple[int, int]:
    """MCIC and productivity from the game seed. Does not touch `rng`."""
    side = random.Random(f"tw2k-port-hidden:{seed}:{sector_id}:{commodity.value}")
    mcic = side.randint(K.PORT_MCIC_MIN, -1) if buys else side.randint(1, K.PORT_MCIC_MAX)
    productivity = side.randint(1, K.PORT_PRODUCTIVITY_MAX)
    return mcic, productivity


def _make_port(rng: random.Random, class_id: PortClass, sector_id: int, seed: int) -> Port:
    stock: dict[Commodity, PortStock] = {}
    mapping = {
        0: Commodity.FUEL_ORE,
        1: Commodity.ORGANICS,
        2: Commodity.EQUIPMENT,
    }
    trades = K.port_class_trades(int(class_id))
    mcic: dict[Commodity, int] = {}
    productivity: dict[Commodity, int] = {}
    for idx, deal in enumerate(trades):
        if deal is None:
            continue
        commodity = mapping[idx]
        maximum = K.PORT_DEFAULT_MAX_STOCK + rng.randint(-500, 1500)
        # The old 35-95% draw stays in the stream so later sectors do not move.
        rng.uniform(0.35, 0.95)
        if K.port_stock_fidelity_live():
            current = 0 if deal is True else maximum
        elif K.port_open_full():
            current = maximum
        else:
            current = int(maximum * K.PORT_START_STOCK_PERCENT)
        stock[commodity] = PortStock(current=current, maximum=maximum)
        hidden_mcic, hidden_prod = _hidden_port_stats(seed, sector_id, commodity, deal is True)
        mcic[commodity] = hidden_mcic
        productivity[commodity] = hidden_prod

    name = _port_name(rng, sector_id)
    port = Port(
        class_id=class_id,
        stock=stock,
        name=name,
        mcic=mcic,
        productivity=productivity,
    )
    if K.rob_tw2002() and class_id not in (PortClass.STARDOCK, PortClass.FEDERAL):
        port.credits = seed_port_credits(port)
    return port


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


def _add_tunnels(rng: random.Random, adj: dict[int, set[int]]) -> None:
    """Add a few one-way jumps between distant sectors.

    The handbook says Big Bang can build tunnels. It does not say how many.
    One per 250 sectors, and at least one on a map of 80 or more, is this
    game's count until a source names another.
    """
    n = len(adj)
    want = n // 250
    if n >= 80 and want < 1:
        want = 1
    added = 0
    tries = 0
    span = max(20, n // 10)
    while added < want and tries < want * 40:
        tries += 1
        a = rng.randint(11, n)
        b = rng.randint(11, n)
        if a == b or abs(a - b) < span:
            continue
        if b in adj[a] or a in adj[b]:
            continue
        adj[a].add(b)
        added += 1


def _cut_one_bubble(rng: random.Random, adj: dict[int, set[int]]) -> None:
    """Close one pair so ships can enter and cannot leave.

    A bubble is a cluster with a way in and no way out. FedSpace is left
    alone. If cutting the pair would hide a sector from sector 1, the cut
    is put back.
    """
    n = len(adj)
    pairs: list[tuple[int, int]] = []
    for a in range(11, n + 1):
        for b in adj[a]:
            if b >= 11 and a in adj.get(b, ()) and a < b:
                pairs.append((a, b))
    if not pairs:
        return
    rng.shuffle(pairs)
    for a, b in pairs[:40]:
        saved_a = set(adj[a])
        saved_b = set(adj[b])
        outside_in = False
        for sid, neigh in adj.items():
            if sid in (a, b):
                continue
            if a in neigh or b in neigh:
                outside_in = True
                break
        if not outside_in:
            continue
        adj[a].clear()
        adj[b].clear()
        if _all_reachable_from(adj, 1, n):
            return
        adj[a] = saved_a
        adj[b] = saved_b


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_universe(config: GameConfig) -> Universe:
    rng = random.Random(config.seed)
    n = config.universe_size

    adj = _build_connected_graph(rng, n, config.avg_warps)
    one_way = K.one_way_fraction_for(config)
    if K.universe_topology_live():
        adj = _one_way_some_edges(rng, adj, one_way, allow_traps=True)
        _add_tunnels(rng, adj)
        _cut_one_bubble(rng, adj)
    else:
        adj = _one_way_some_edges(rng, adj, one_way)
    layout = _compute_layout(adj, n, rng)

    sectors: dict[int, Sector] = {}
    for i in range(1, n + 1):
        warps_list = sorted(adj[i])
        x, y = layout[i]
        sectors[i] = Sector(id=i, warps=warps_list, x=x, y=y)

    # Place StarDock. Sector 1 stays the StarDock until Ben says otherwise.
    # Live mode gives that port a buy-all book from a side rng, so the main
    # stream (and every later port) stays on the same draws.
    sectors[K.STARDOCK_SECTOR].port = Port(
        class_id=PortClass.STARDOCK,
        name="Sol-1 StarDock",
    )
    if K.port_class_live():
        side = random.Random(f"tw2k-stardock-book:{config.seed}")
        booked = _make_port(side, PortClass.STARDOCK, K.STARDOCK_SECTOR, config.seed)
        booked.name = "Sol-1 StarDock"
        sectors[K.STARDOCK_SECTOR].port = booked

    # Place Federal ports in FedSpace (excluding sector 1). The live bang
    # skips these decorative ports; the clone path still draws them so the
    # main rng, and everything after it, stays put.
    _place_decorative_fed_ports(rng, sectors, config)

    # Place random ports in non-FedSpace sectors
    _place_trade_ports(rng, sectors, config, K.PORT_SPAWN_PROBABILITY)

    universe = Universe(config=config, sectors=sectors)

    # Seed planets (existing civilizations scattered through the galaxy)
    if config.enable_planets:
        _seed_planets(rng, universe)

    pinned_class0: tuple[int, int] | None = None
    if K.big_bang_density_live():
        # Class 0 is chosen on the clone layout, then the fill is replaced.
        # Sol (sector 1), Terra and StarDock are left where they are.
        if K.class0_tw2002():
            from .class0 import choose_class0_sectors
            pinned_class0 = choose_class0_sectors(universe)
        _strip_clone_fill(universe)
        side = random.Random(f"tw2k-big-bang-density:{config.seed}")
        skip = set(pinned_class0) if pinned_class0 else set()
        _place_trade_ports(side, universe.sectors, config, K.V311_PORT_DENSITY, skip)
        if config.enable_planets:
            _seed_planets(side, universe, K.V311_PLANET_DENSITY, skip)

    # Pre-seed Ferrengi raiders so the first day has genuine threat. Without
    # this the first Ferrengi don't appear until the end of day 1 (tick_day),
    # which historically gave agents a full safe day of grinding. Distributed
    # across deep space so they don't all cluster on one trade lane.
    # ferrengi-aliens-v1: Ferrengal home (isolated rng; no-op under legacy)
    from .ferrengi import place_ferrengal
    place_ferrengal(universe)

    if config.enable_ferrengi and K.FERRENGI_INITIAL_SPAWN > 0:
        _seed_initial_ferrengi(rng, universe)

    # CLASS0_TERRA.md: Terra + Alpha Centauri / Rylos + MSL. Uses a dedicated
    # rng keyed on the seed so generator / universe.rng draws stay identical
    # across CLASS0_MODE (legacy placement is a no-op that clears the fields).
    from .class0 import place_class0_ports
    place_class0_ports(universe, pinned=pinned_class0)

    # fedspace-police-v1: Federals (isolated rng; no-op under FED_MODE legacy)
    from .fed import place_federals, place_fed_starships
    place_federals(universe)
    place_fed_starships(universe)

    # alien-traders-v1: scatter classic aliens (isolated rng; no-op under legacy)
    from .alien import place_aliens
    place_aliens(universe)

    if K.port_upgrade_on():  # pu26: cap from the bang's finished port count
        from .port_build import stamp_port_cap
        stamp_port_cap(universe)

    return universe


def _seed_initial_ferrengi(rng: random.Random, universe: Universe) -> None:
    from .ferrengi import _make_ferrengi, _pick_spawn_sector

    initial = K.FERRENGI_INITIAL_SPAWN
    max_alive = getattr(universe.config, "ferrengi_max_alive", None)
    if max_alive is not None:
        initial = min(initial, max(0, int(max_alive)))
    for i in range(initial):
        # Legacy: deep-random via universe.rng (same draw order as before when
        # ferrengi_tw2002 is off — _pick_spawn_sector falls through to randint).
        sid = _pick_spawn_sector(universe, rng)
        aggr = rng.randint(2, K.FERRENGI_MAX_AGGRESSION)
        fid = f"ferr_d0_{i}_{sid}"
        ship = _make_ferrengi(universe, fid=fid, sid=sid, aggression=aggr)
        universe.ferrengi[fid] = ship


def _place_decorative_fed_ports(rng: random.Random, sectors: dict[int, Sector], config: GameConfig) -> None:
    """Ours-only Federal ports in sectors 2-10. No source in the original."""
    for fed_sid in K.FEDSPACE_SECTORS:
        if fed_sid == K.STARDOCK_SECTOR:
            continue
        if rng.random() < 0.6:
            port = _make_port(rng, PortClass.FEDERAL, fed_sid, config.seed)
            # Federal ports actually trade all three at fixed price — we model as class 7 (BBB) equivalent
            port = _make_port(rng, PortClass.CLASS_7_BBB, fed_sid, config.seed)
            port.class_id = PortClass.FEDERAL
            sectors[fed_sid].port = port


def _place_trade_ports(
    rng: random.Random,
    sectors: dict[int, Sector],
    config: GameConfig,
    probability: float,
    skip: set[int] | None = None,
) -> None:
    blocked = skip or set()
    n = config.universe_size
    for sid in range(max(K.FEDSPACE_SECTORS) + 1, n + 1):
        if sid in blocked:
            continue
        if rng.random() < probability:
            cls = _pick_port_class(rng)
            sectors[sid].port = _make_port(rng, cls, sid, config.seed)


def _strip_clone_fill(universe: Universe) -> None:
    """Remove clone ports and planets. Sector 1 (Sol / StarDock) stays."""
    for sid, sector in universe.sectors.items():
        if int(sid) == int(K.STARDOCK_SECTOR):
            continue
        sector.port = None
        sector.planet_ids.clear()
    universe.planets.clear()
    universe.next_planet_id = 1


def _seed_planets(
    rng: random.Random,
    universe: Universe,
    probability: float | None = None,
    skip: set[int] | None = None,
) -> None:
    n = universe.config.universe_size
    chance = universe.config.planet_spawn_probability if probability is None else probability
    blocked = skip or set()
    planet_id = 1
    for sid in range(max(K.FEDSPACE_SECTORS) + 1, n + 1):
        if sid in blocked:
            continue
        if rng.random() < chance:
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
