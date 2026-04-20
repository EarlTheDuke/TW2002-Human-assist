"""Command-line entry points for TW2K-AI.

Available commands:
    tw2k serve   — start the web server + auto-run a match (default 2 agents)
    tw2k replay  — replay a saved match in the spectator UI (Phase 6)
    tw2k sim     — run a headless simulation with heuristic agents (for testing)
    tw2k probe   — print a universe summary for a given seed
"""

from __future__ import annotations

import asyncio
import os as _bootstrap_os
from pathlib import Path as _BootstrapPath

import typer
import uvicorn
from rich.console import Console
from rich.table import Table


def _bootstrap_dotenv() -> None:
    """Populate os.environ from a project-root .env file if one exists.

    Intentionally lightweight — no python-dotenv dependency. The loader
    runs ONCE at CLI import time so every downstream component
    (`default_provider`, `_handle_*`, the LLM client) sees the keys
    without any per-process wiring. Existing environment variables
    always win over .env so CI / explicit shell exports still override.

    Format: KEY=VALUE per line, blank lines and `#` comments ignored.
    Optional surrounding quotes on VALUE are stripped. No interpolation.
    This is enough for API keys and model overrides; complex config
    stays in pyproject/typer.
    """
    try:
        root = _BootstrapPath(__file__).resolve().parents[2]
    except IndexError:
        return
    env_path = root / ".env"
    if not env_path.is_file():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in _bootstrap_os.environ:
                _bootstrap_os.environ[key] = value
    except OSError:
        return


_bootstrap_dotenv()

from .agents.llm import default_provider  # noqa: E402  imported after .env load
from .engine import GameConfig, generate_universe  # noqa: E402

app = typer.Typer(add_completion=False, no_args_is_help=True, help="TW2K-AI — TradeWars 2002 played by LLM agents.")
console = Console()


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind."),
    port: int = typer.Option(8000, help="Port to bind."),
    seed: int = typer.Option(42, help="Universe seed."),
    universe_size: int = typer.Option(1000, help="Number of sectors."),
    max_days: int = typer.Option(
        15,
        help=(
            "Max in-game days before time victory. Default 15 gives enough "
            "runway for a full economy arc: upgrade ship (~day 2-3), deploy "
            "first Genesis (~day 4-6), reach Citadel L2 (~day 8-10), L3 "
            "(~day 12-14). Bump higher for late-game raiding/corp dynamics."
        ),
    ),
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
    agent_providers: str = typer.Option(
        None,
        help=(
            "Comma-separated per-agent providers (slot N -> player PN+1). "
            "Example: 'xai,anthropic' runs P1 on Grok, P2 on Claude. "
            "Missing slots fall back to --provider. Use this for cross-model "
            "matches."
        ),
    ),
    agent_models: str = typer.Option(
        None,
        help=(
            "Comma-separated per-agent model slugs aligned to --agent-providers. "
            "Example: 'grok-4-1-fast-reasoning,claude-sonnet-4-5-20250929'. "
            "Leave a slot empty to use the provider default (e.g. ',claude-...' "
            "keeps Grok's default model)."
        ),
    ),
    agent_names: str = typer.Option(
        None,
        help="Comma-separated per-agent display names (slot N -> player PN+1).",
    ),
    action_delay_s: float = typer.Option(
        None,
        help=(
            "Override the per-action artificial delay (default 0.6 s). Set to "
            "0 for maximum throughput on long matches. LLM API latency still "
            "applies — this only controls the extra pacing delay."
        ),
    ),
    human: str = typer.Option(
        None,
        help=(
            "Comma-separated player IDs to flag as HUMAN (Phase H0). "
            "Example: '--human P1' makes P1 a human slot the scheduler "
            "blocks on every turn until POST /api/human/action delivers an "
            "Action for that player. '--human P1,P3' flags two slots. "
            "Unknown IDs are ignored with a warning. Implies kind=human on "
            "the listed slots, overriding --agent-kind and per-slot LLM "
            "overrides."
        ),
    ),
    human_deadline_s: float = typer.Option(
        None,
        "--human-deadline-s",
        help=(
            "Optional per-turn deadline for HUMAN slots, in seconds. "
            "If the human doesn't submit an action within this many "
            "seconds, the scheduler auto-submits a WAIT on their behalf "
            "and the match keeps moving. Default: no deadline (blocks "
            "indefinitely - good for dev; set 60-180s for demos). Has "
            "no effect on AI slots."
        ),
    ),
) -> None:
    """Start the spectator web server."""
    import os as _os

    from .server.app import create_app
    provider_display = provider or default_provider()

    # Parse per-agent overrides from comma lists. Blanks in a slot fall
    # back to the global --provider / --model, so 'xai,anthropic' + no
    # --agent-models means both agents take their provider's default
    # model. Lists are right-padded with empties so missing slots
    # silently default instead of raising.
    providers_list = [s.strip() or None for s in (agent_providers.split(",") if agent_providers else [])]
    models_list = [s.strip() or None for s in (agent_models.split(",") if agent_models else [])]
    names_list = [s.strip() for s in (agent_names.split(",") if agent_names else []) if s.strip()]

    # Parse --human into a set of player-id tags. Slot index is (id - 1),
    # so "P1,P3" -> {0, 2}. We tag by id (not index) at the CLI surface
    # because that's how spectators refer to players everywhere else.
    human_ids: set[str] = {
        s.strip().upper() for s in (human.split(",") if human else []) if s.strip()
    }
    human_slot_idx: set[int] = set()
    for pid in human_ids:
        if not (pid.startswith("P") and pid[1:].isdigit()):
            console.print(f"[yellow]warn:[/] ignoring malformed --human id {pid!r}")
            continue
        idx = int(pid[1:]) - 1
        if 0 <= idx < num_agents:
            human_slot_idx.add(idx)
        else:
            console.print(
                f"[yellow]warn:[/] --human {pid} out of range for {num_agents} agents — ignored"
            )

    overrides: list[dict] = []
    max_slots_src = num_agents if human_slot_idx else 0
    max_slots = max(
        len(providers_list), len(models_list), max_slots_src, num_agents
    ) if (providers_list or models_list or human_slot_idx) else 0
    for i in range(max_slots):
        entry: dict = {}
        if i < len(providers_list) and providers_list[i]:
            entry["provider"] = providers_list[i]
            # If the user set a specific provider for a slot, also force
            # kind=llm so agent_kind=auto doesn't downgrade to heuristic
            # on a slot that explicitly names an LLM.
            entry["kind"] = "llm"
        if i < len(models_list) and models_list[i]:
            entry["model"] = models_list[i]
        # --human takes precedence over any provider/model hint on this
        # slot: a human slot never has an LLM wired up.
        if i in human_slot_idx:
            entry["kind"] = "human"
            entry.pop("provider", None)
            entry.pop("model", None)
        if entry:
            overrides.append(entry)
        else:
            overrides.append({})
    console.rule("[bold cyan]TW2K-AI Server")
    console.print(f"[cyan]Host:[/] {host}:{port}")
    console.print(f"[cyan]Seed:[/] {seed}  [cyan]Sectors:[/] {universe_size}  [cyan]Max days:[/] {max_days}")
    console.print(f"[cyan]Agents:[/] {num_agents}  [cyan]Kind:[/] {agent_kind}  [cyan]LLM provider:[/] {provider_display}")
    any_human = any(ov.get("kind") == "human" for ov in overrides)
    if any_human:
        deadline_note = (
            f"auto-WAIT after {human_deadline_s:.0f}s idle"
            if human_deadline_s and human_deadline_s > 0
            else "no deadline"
        )
        console.print(
            f"[magenta]Human cockpit:[/] http://{host}:{port}/play   [dim]({deadline_note})[/]"
        )
    if overrides:
        for i, ov in enumerate(overrides[:num_agents]):
            if ov.get("kind") == "human":
                console.print(f"  [dim]P{i+1}:[/] [bold magenta]HUMAN[/] (awaits POST /api/human/action)")
            elif ov:
                tag_prov = ov.get("provider") or provider_display
                tag_model = ov.get("model") or "<provider default>"
                console.print(
                    f"  [dim]P{i+1}:[/] provider=[cyan]{tag_prov}[/]  model=[cyan]{tag_model}[/]"
                )
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
        agent_overrides=overrides or None,
        agent_names=names_list or None,
        action_delay_s=action_delay_s,
        human_deadline_s=human_deadline_s,
    )
    uvicorn.run(application, host=host, port=port, log_level="info")


@app.command()
def replay(
    run_dir: str = typer.Argument(
        ...,
        help=(
            "Path to a saved run directory containing meta.json + actions.jsonl. "
            "Relative paths resolve against CWD and then against TW2K_SAVES_DIR "
            "/ <repo>/saves. Pass the run-id (e.g. '20260419-120000-seed42') to "
            "resolve relative to the saves root."
        ),
    ),
    host: str = typer.Option("127.0.0.1", help="Host to bind."),
    port: int = typer.Option(8000, help="Port to bind."),
    speed: float = typer.Option(
        1.0,
        help=(
            "Playback speed multiplier. 1.0 plays at recorded pace, 2.0 = "
            "twice as fast, 0.5 = half speed. Honors live pause/resume/speed "
            "controls from the spectator UI too."
        ),
    ),
) -> None:
    """Replay a saved match (seed + actions.jsonl) in the spectator UI."""
    from pathlib import Path

    from .server.app import create_replay_app
    from .server.runner import _default_saves_root

    candidate = Path(run_dir)
    search = [candidate, Path.cwd() / run_dir]
    saves_root = _default_saves_root()
    search.append(saves_root / run_dir)
    resolved: Path | None = None
    for c in search:
        if (c / "meta.json").is_file():
            resolved = c.resolve()
            break
    if resolved is None:
        console.print(f"[red]No meta.json found under[/] {run_dir}")
        console.print(f"[dim]Searched: {[str(c) for c in search]}[/dim]")
        raise typer.Exit(code=1)

    meta = __import__("json").loads((resolved / "meta.json").read_text(encoding="utf-8"))
    console.rule(f"[bold magenta]TW2K-AI Replay — {meta.get('run_id', resolved.name)}")
    console.print(f"[magenta]Run dir:[/] {resolved}")
    console.print(
        f"[magenta]Seed:[/] {meta['config']['seed']}  "
        f"[magenta]Sectors:[/] {meta['config']['universe_size']}  "
        f"[magenta]Max days:[/] {meta['config']['max_days']}"
    )
    console.print(f"[magenta]Agents:[/] {len(meta.get('agents', []))}  [magenta]Speed:[/] {speed}x")
    console.print(f"[magenta]Open:[/] http://{host}:{port}")
    console.rule()

    application = create_replay_app(resolved, speed=speed)
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
        p.known_warps[1] = list(universe.sectors[1].warps)
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
