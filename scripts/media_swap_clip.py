"""Replace or add a manifest variant, or wire the V3 pilot set.

    python scripts/media_swap_clip.py --wire-pilot
    python scripts/media_swap_clip.py --key warp.out --variant warp_out_a --webm clip.webm --mp4 clip.mp4

A new file path in the manifest is what the player loads. No player code change.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from media_clip_tools import CATALOG, MANIFEST, MEDIA, load_json, save_json, swap_variant, wire_pilot


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--media-root", default=str(MEDIA))
    ap.add_argument("--wire-pilot", action="store_true", help="stand-ins plus the v3-pilot catalog")
    ap.add_argument("--key")
    ap.add_argument("--variant")
    ap.add_argument("--webm")
    ap.add_argument("--mp4")
    ap.add_argument("--poster")
    args = ap.parse_args(argv)
    manifest_path = Path(args.manifest)
    media = Path(args.media_root)
    data = load_json(manifest_path)
    if args.wire_pilot:
        wire_pilot(data, load_json(CATALOG)["clips"], media)
        save_json(manifest_path, data)
        print(f"wired pilot clips into {manifest_path.name}")
        return 0
    if not args.key or not args.variant or not (args.webm or args.mp4 or args.poster):
        ap.error("pass --wire-pilot, or --key, --variant, and at least one of --webm/--mp4/--poster")
    variant = swap_variant(
        data, args.key, args.variant,
        webm=Path(args.webm) if args.webm else None,
        mp4=Path(args.mp4) if args.mp4 else None,
        poster=Path(args.poster) if args.poster else None,
        media_root=media,
    )
    save_json(manifest_path, data)
    print(f"{args.key} {variant['id']} -> {variant.get('webm') or variant.get('mp4')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
