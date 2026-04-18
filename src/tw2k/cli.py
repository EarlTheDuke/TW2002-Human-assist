"""Command-line entry points for TW2K-AI.

Available commands:
    tw2k serve   — start the web server + auto-run a match (default 2 agents)
    tw2k sim     — run a headless simulation with heuristic agents (for testing)
    tw2k probe   — print a universe summary for a given seed
"""

from __future__ import annotations

import asyncio

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from .agents.llm import default_provider
from .engine import GameConfig, generate_universe

app = typer.Typer(add_completion=False, no_args_is_help=True, help="TW2K-AI — TradeWars 2002 played by LLM agents.")
console = Console()


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind."),
    port: int = typer.Option(8000, help="Port to bind."),
    seed: int = typer.Option(42, help="Universe seed."),
    universe_size: int = typer.Option(1000, help="Number of sectors."),
    max_days: int = typer.Option(10, help="Max in-game days before time victory."),
    num_agents: int = typer.Option(2, help="Number of agents (default 2)."),
    agent_kind: str = typer.Option("auto", help="auto | llm | heuristic"),
    provider: str = typer.Option(None, help="anthropic | openai | xai | deepseek | custom (else auto-detect)"),
    model: str = typer.Option(None, help="Override the LLM model name."),
    no_auto_start: bool = typer.Option(False, help="Don't auto-start the match at boot."),
    turns_per_day: int = typer.Option(
        None,
        help="Override per-player turns_per_day (default ~1000). Use ~80-120 "
             "for watchable sanity runs that still let agents make visible progress.",
    ),
    starting_credits: int = typer.Option(
        None,
        help="Override per-player starting credits (default 20,000). Raise to "
             "75-100k for sanity runs so agents can reach ship-upgrade / Genesis "
             "decisions inside the observation window.",
    ),
) -> None:
    """Start the spectator web server."""
    import os as _os

    from .server.app import create_app
    provider_display = provider or default_provider()
    console.rule("[bold cyan]TW2K-AI Server")
    console.print(f"[cyan]Host:[/] {host}:{port}")
    console.print(f"[cyan]Seed:[/] {seed}  [cyan]Sectors:[/] {universe_size}  [cyan]Max days:[/] {max_days}")
    console.print(f"[cyan]Agents:[/] {num_agents}  [cyan]Kind:[/] {agent_kind}  [cyan]LLM provider:[/] {provider_display}")
    if provider_display == "custom":
        base = _os.environ.get("TW2K_CUSTOM_BASE_URL", "<unset>")
        mdl = model or _os.environ.get("TW2K_CUSTOM_MODEL", "<default>")
        key = _os.environ.get("TW2K_CUSTOM_API_KEY") or _os.environ.get("OPENAI_API_KEY") or ""
        masked = (key[:6] + "***" + key[-4:]) if len(key) > 12 else ("<unset>" if not key else "<short>")
        console.print(f"[cyan]Custom URL:[/] {base}")
        console.print(f"[cyan]Custom model:[/] {mdl}  [cyan]Custom key:[/] {masked}")
    elif provider_display == "xai":
        mdl = model or _os.environ.get("TW2K_XAI_MODEL", "grok-4-1-fast-reasoning")
        key = _os.environ.get("XAI_API_KEY") or _os.environ.get("GROK_API_KEY") or ""
        masked = (key[:6] + "***" + key[-4:]) if len(key) > 12 else ("<unset>" if not key else "<short>")
        console.print(f"[cyan]xAI model:[/] {mdl}  [cyan]xAI key:[/] {masked}")
    console.print(f"[cyan]Open:[/] http://{host}:{port}")
    console.rule()

    application = create_app(
        seed=seed,
        universe_size=universe_size,
        max_days=max_days,
        num_agents=num_agents,
        agent_kind=agent_kind,
        provider=provider,
        model=model,
        auto_start=not no_auto_start,
        turns_per_day=turns_per_day,
        starting_credits=starting_credits,
    )
    uvicorn.run(application, host=host, port=port, log_level="info")


@app.command()
def sim(
    seed: int = typer.Option(42, help="Universe seed."),
    universe_size: int = typer.Option(1000),
    max_days: int = typer.Option(3, help="Days to simulate."),
    num_agents: int = typer.Option(2),
) -> None:
    """Run a quick headless simulation with heuristic agents (no LLM)."""
    from .agents import HeuristicAgent
    from .engine import apply_action, build_observation, is_finished, tick_day
    from .engine.models import Player, Ship

    config = GameConfig(seed=seed, universe_size=universe_size, max_days=max_days)
    universe = generate_universe(config)
    agents = []
    for i in range(num_agents):
        pid = f"P{i+1}"
        p = Player(id=pid, name=f"HBot-{i+1}", ship=Ship())
        universe.players[pid] = p
        universe.sectors[1].occupant_ids.append(pid)
        p.known_sectors.add(1)
        agents.append(HeuristicAgent(pid, p.name))

    async def loop():
        idx = 0
        while not is_finished(universe):
            agent = agents[idx]
            player = universe.players[agent.player_id]
            if player.turns_today >= player.turns_per_day:
                if all(universe.players[a.player_id].turns_today >= universe.players[a.player_id].turns_per_day for a in agents):
                    tick_day(universe)
                idx = (idx + 1) % len(agents)
                continue
            obs = build_observation(universe, agent.player_id)
            action = await agent.act(obs)
            apply_action(universe, agent.player_id, action)
            idx = (idx + 1) % len(agents)

    asyncio.run(loop())

    table = Table(title=f"Sim complete — day {universe.day}")
    table.add_column("Player"); table.add_column("Credits"); table.add_column("Fighters")
    table.add_column("Ship"); table.add_column("Sector")
    for p in universe.players.values():
        table.add_row(p.name, str(p.credits), str(p.ship.fighters), p.ship.ship_class.value, str(p.sector_id))
    console.print(table)
    if universe.winner_id:
        console.print(f"[bold green]Winner:[/] {universe.winner_id} ({universe.win_reason})")


@app.command()
def probe(seed: int = typer.Option(42), universe_size: int = typer.Option(1000)) -> None:
    """Print a short universe summary for a given seed (useful for tuning)."""
    config = GameConfig(seed=seed, universe_size=universe_size)
    u = generate_universe(config)
    port_counts = {}
    for s in u.sectors.values():
        if s.port is None:
            continue
        port_counts[s.port.code] = port_counts.get(s.port.code, 0) + 1
    total_ports = sum(port_counts.values())
    console.print(f"Seed {seed}: {len(u.sectors)} sectors, {total_ports} ports, {len(u.planets)} planets")
    for code, n in sorted(port_counts.items()):
        console.print(f"  {code:8s} {n}")


if __name__ == "__main__":
    app()
