"""Play one Galaxy War Command seat from the rendered cockpit.

The process opens the seat link in a browser, reads the screen, and clicks or
types the way a person would. It does not import the game engine.

    python3 scripts/ai_cockpit_player.py \\
        --url 'http://127.0.0.1:8050/bot?seat=P2&mode=cu&token=...&layout=redesign' \\
        --provider scripted \\
        --max-turns 12 \\
        --run-dir runs/ai-cockpit

Live providers read a key from the environment and never print it:

    XAI_API_KEY=... python3 scripts/ai_cockpit_player.py --provider grok --url ...
    OPENAI_API_KEY=... python3 scripts/ai_cockpit_player.py --provider openai --url ...
    ANTHROPIC_API_KEY=... python3 scripts/ai_cockpit_player.py --provider anthropic --url ...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _import_root() -> None:
    root = Path(__file__).resolve().parent
    text = str(root)
    if text not in sys.path:
        sys.path.insert(0, text)


def check_imports() -> int:
    """Exit 3 when this process has loaded a tw2k module."""
    _import_root()
    import ai_cockpit.providers
    import ai_cockpit.runner
    from ai_cockpit.runner import engine_modules

    del ai_cockpit.providers, ai_cockpit.runner

    names = engine_modules()
    if names:
        print("engine modules loaded: " + ", ".join(names), file=sys.stderr)
        return 3
    print("engine import check: clean")
    return 0


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Play a cockpit seat from the rendered screen.")
    parser.add_argument("--url", default="", help="seat link, including token, mode=cu, and layout=redesign")
    parser.add_argument("--provider", default="scripted", help="scripted, mock, grok, openai, or anthropic")
    parser.add_argument("--model", default="", help="model name for a live provider; empty uses that provider's default")
    parser.add_argument("--mock-script", default="", help="JSON list of canned replies for --provider mock")
    parser.add_argument("--run-dir", default="runs/ai-cockpit", help="folder for screens and the action log")
    parser.add_argument("--max-turns", type=int, default=40, help="most actions to take")
    parser.add_argument("--min-interval", type=float, default=1.0, help="seconds between actions")
    parser.add_argument("--stop-file", default="", help="when this path exists, stop")
    parser.add_argument(
        "--level", default="hard",
        help="scripted difficulty: easy, normal, or hard (live providers ignore it)",
    )
    parser.add_argument("--headed", action="store_true", help="show the browser window")
    parser.add_argument("--check-imports", action="store_true", help="exit 3 if tw2k was imported")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    if args.check_imports:
        return check_imports()
    if not args.url:
        print("a seat url is required", file=sys.stderr)
        return 2
    _import_root()
    from ai_cockpit.redact import redact
    from ai_cockpit.runner import play

    stop = Path(args.stop_file) if args.stop_file else None
    try:
        return play(
            url=args.url,
            provider_name=args.provider,
            run_dir=Path(args.run_dir),
            max_turns=int(args.max_turns),
            min_interval=float(args.min_interval),
            stop_file=stop,
            headless=not args.headed,
            model=str(args.model or ""),
            mock_script=str(args.mock_script or ""),
            level=str(args.level or "hard"),
        )
    except Exception as exc:
        print(redact(f"{exc.__class__.__name__}: {exc}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
