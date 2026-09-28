"""Approve or unapprove a clip take. Stand-ins stay unapproved.

    python scripts/media_approve_clips.py --key dock.port --variant dock_port_std_b --by ben
    python scripts/media_approve_clips.py --key dock.port --variant 2 --by ben
    python scripts/media_approve_clips.py --all-pending --by ben
    python scripts/media_approve_clips.py --key dock.port --variant dock_port_std_b --clear
    python scripts/media_approve_clips.py --all-pending --clear
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from media_clip_tools import (
    MANIFEST,
    _entry,
    approve_pending,
    find_variant,
    load_json,
    save_json,
    set_approval,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--key", help="clip key, or ambient.deep_space")
    ap.add_argument("--variant", help="variant id, or 1-based index among real takes")
    ap.add_argument("--by", default="ben")
    ap.add_argument("--all-pending", action="store_true")
    ap.add_argument("--clear", action="store_true", help="set approved_by back to null")
    args = ap.parse_args(argv)
    path = Path(args.manifest)
    data = load_json(path)
    if args.all_pending:
        n = approve_pending(data, args.by, clear=args.clear)
        save_json(path, data)
        print(f"{'cleared' if args.clear else 'approved'} {n} real take(s)")
        return 0
    if not args.key or not args.variant:
        ap.error("pass --key and --variant, or --all-pending")
    variant = find_variant(_entry(data, args.key), args.variant)
    set_approval(variant, None if args.clear else args.by)
    save_json(path, data)
    who = (variant.get("provenance") or {}).get("approved_by")
    print(f"{args.key} {variant['id']} approved_by={who!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
